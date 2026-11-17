"""EXP-0062 (E03c): a PRETRAINED dense comparator, run inside P001's frozen development protocol.

EXP-0024 could only answer the "weak baseline / no trained retriever" attack with a two-tower model trained from
scratch on this dataset, and it said so: "Pretrained encoders are unavailable in this environment". EXP-0061 measured
that premise to be FALSE - the canonical HF host is blocked, but hf-mirror.com serves real weight bytes and the
Tsinghua index installs sentence-transformers, so all-MiniLM-L6-v2 is obtainable. This experiment closes that gap
with a run rather than a note.

Everything that could be held fixed is held fixed against EXP-0024: the same pooled development rows, the same
candidate lists, the same gold sets, the same K=3, the same `best_ranks` tie-handling (imported, not rewritten), the
same frozen feature set / C / prompt_id GroupKFold for the pre-retrieval model, and the same textual renderings, so
the only thing that changes is the representation.

Fixed before the first encoding:
  * model: sentence-transformers/all-MiniLM-L6-v2, used **unmodified**. No fine-tuning - a tuned encoder would answer
    a different question and would leak label information into the baseline;
  * renderings (both scored, because a reviewer may object that the token-joined rendering was built for TF-IDF and
    handicaps a natural-language encoder):
      R1 "tfidf_style" = the exact EXP-0024 renderings (whitespace-joined lowercased tokens);
      R2 "prose"       = untouched query text, and document = name words + description + "Parameters: ..." prose;
    the variant with the HIGHER hit@3 defines the comparator used for the transfer test, which is the conservative
    choice against this paper's own claim, and both variants are reported either way;
  * retrieval outcome: cosine over the row's own candidates, best gold rank, fail@3;
  * cross-ranker transfer: the frozen pre-retrieval model trained on BM25 failure is scored against the PRETRAINED
    ranker's fail@3; bar AUROC >= 0.65, identical to the pre-registered EXP-0024 bar, unchanged here;
  * because a strong ranker makes fail@3 rare, every AUROC carries a prompt_id-clustered bootstrap CI and the failure
    sets carry exact counts with Wilson intervals - a point estimate alone would be read as more precise than it is;
  * the EXP-0024 dense ranks are READ FROM ITS PUBLISHED TABLE, not re-derived, and the join is asserted row by row;
  * no test-split row is read anywhere here, so the test ledger stays at exactly one evaluation.

    python ../../02_shared_code/statistics/pretrained_dense_comparator_p001.py   # needs .venv_e0062 + HF_ENDPOINT

Outputs results_raw/EXP0062_pretrained_dense_comparator_*.json and
results_processed/EXP0062_pretrained_vs_bm25_vs_scratch.csv.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "trajectory_parser"))
from analyze_routing_failure import CONFIGS, PROC, SEEDS, oof_auc, scaled_pipeline  # noqa: E402
from build_toucan_routing_dataset import toks  # noqa: E402
from dense_comparator_e03b import best_ranks, d_text, margin_per_row, q_text  # noqa: E402
from run_p001_experiments import FROZEN_C, FROZEN_FEATURES, cluster_boot_auc, matrices  # noqa: E402

K = 3
DV = "fail_at_3"
MODEL = "sentence-transformers/all-MiniLM-L6-v2"
BATCH = 256
TRANSFER_BAR = 0.65
SEED_LAYOUT = 20260920
ROOT = HERE.parents[1]
OUT_RAW = ROOT / "results_raw"
OUT_PROC = ROOT / "results_processed"
CACHE = ROOT / ".cache_exp0062"
E0024_TABLE = OUT_PROC / "EXP0024_dense_vs_bm25.csv"


def prose_doc(doc) -> str:
    name = doc["n"].replace("-", " ").replace("_", " ")
    params = ", ".join(doc["p"])
    return f"{name}. {doc['d']}" + (f" Parameters: {params}." if params else "")


def prose_query(q: str) -> str:
    return " ".join(str(q).split())


def cache_key(*parts: str) -> str:
    return hashlib.sha1("\x1f".join(parts).encode("utf-8")).hexdigest()[:16]


def embed(model, texts: list[str], tag: str, log):
    """Encode unique texts, with a content-addressed cache so a re-run cannot silently use different vectors.

    Also audits truncation: a ranker whose score was computed on a clipped text is not the ranker the paper claims.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    key = cache_key(MODEL, tag, *texts)
    fep = CACHE / f"{tag}_{key}.npy"
    tk = model.tokenizer
    over = mx = 0
    for s in range(0, len(texts), 2000):
        ids = tk(texts[s:s + 2000], add_special_tokens=True, truncation=False,
                 return_attention_mask=False)["input_ids"]
        for x in ids:
            n = len(x)
            mx = max(mx, n)
            over += n > model.max_seq_length
    trunc = {"max_tokens": int(mx), "limit": int(model.max_seq_length),
             "n_over_limit": int(over), "frac_over_limit": round(over / max(1, len(texts)), 6)}
    if over:
        log(f"  [{tag}] NOTE {over}/{len(texts)} texts exceed the model's {model.max_seq_length}-token window "
            f"and are clipped by the encoder")
    if fep.exists():
        log(f"  [{tag}] cache hit {fep.name} ({len(texts)} texts)")
        return np.load(fep), trunc
    t0 = time.time()
    vec = model.encode(texts, batch_size=BATCH, convert_to_numpy=True,
                       normalize_embeddings=True).astype(np.float32)
    log(f"  [{tag}] encoded {len(texts)} unique texts in {time.time() - t0:.1f}s "
        f"({len(texts) / max(1e-9, time.time() - t0):.0f} texts/s) dim={vec.shape[1]}")
    np.save(fep, vec)
    return vec, trunc


def dense_scores(q_emb, d_emb, q_idx, d_idx, chunk=20_000):
    """Cosine of every (row, candidate) pair, normalised embeddings so dot == cosine.

    Chunked because materialising the gathered document block would be 200k x 384 floats.
    """
    out = np.empty(len(d_idx), dtype=np.float32)
    for s in range(0, len(d_idx), chunk):
        e = min(s + chunk, len(d_idx))
        out[s:e] = (q_emb[q_idx[s:e]] * d_emb[d_idx[s:e]]).sum(1)
    return out


def brute_ranks(sizes, scores, golds, rows, k=K):
    """Recompute the best gold rank for a sample of rows with a plain per-row loop.

    The vectorised path lays 200k scores out row-major and gathers by index arrays; a silent off-by-one there would
    produce a plausible-looking hit@3, so the layout is checked against an independent implementation.
    """
    off = np.cumsum([0] + list(sizes))
    out = []
    for p in rows:
        s, e = off[p], off[p] + sizes[p]
        sc = scores[s:e]
        order = np.lexsort((np.arange(sizes[p]), -sc))
        rank_of = np.empty(sizes[p], dtype=int)
        rank_of[order] = np.arange(1, sizes[p] + 1)
        g = list(golds[p])
        out.append(int(min(rank_of[i] for i in g)) if g else sizes[p])
    return np.asarray(out)


def wilson(k: int, n: int, z: float = 1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0.0, c - h), 4), round(min(1.0, c + h), 4)]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()

    def log(*a):
        print(*a, flush=True)

    import torch
    from sentence_transformers import SentenceTransformer

    df = pd.concat([pd.read_parquet(PROC / f"routing_{c}.parquet") for c in CONFIGS], ignore_index=True)
    df = df[(df.split == "dev") & (df.n_candidates > K)].reset_index(drop=True)
    cats = [json.loads(c) for c in df.catalog_json]
    golds = [json.loads(g) for g in df.gold_idx]
    sizes = [len(c) for c in cats]
    n_rows, n_doc_inst = len(df), int(sum(sizes))
    log(f"EXP-0062 pretrained dense comparator | model={MODEL} rows={n_rows} doc_instances={n_doc_inst}")

    # --- EXP-0024 published from-scratch ranks, joined by position and asserted, never re-derived ---
    # prompt_id is a zero-padded string in the parquet; read_csv would coerce it to int64 and the join assertion
    # below would then fail on every row (measured), so the column is read as text on purpose.
    e24 = pd.read_csv(E0024_TABLE, dtype={"prompt_id": str})
    assert len(e24) == n_rows, f"EXP-0024 table has {len(e24)} rows, dev pool has {n_rows}: not the same protocol"
    assert (e24["prompt_id"].values == df["prompt_id"].values).all(), "prompt_id order differs from EXP-0024"
    assert (e24["cfg"].values == df["cfg"].values).all(), "cfg order differs from EXP-0024"
    assert (e24["bm25_best_rank"].values == df["bm25_best_rank"].values).all(), "BM25 ranks differ from EXP-0024"
    assert (e24["fail_at_3"].values == df[DV].values).all(), "fail@3 labels differ from EXP-0024"
    scratch_rank = e24["dense_best_rank"].values.astype(int)
    log(f"  EXP-0024 table joined and asserted row-by-row ({n_rows} rows)")

    emb_model = SentenceTransformer(MODEL, device="cpu")
    dim = (emb_model.get_embedding_dimension() if hasattr(emb_model, "get_embedding_dimension")
           else emb_model.get_sentence_embedding_dimension())
    log(f"  loaded {MODEL} (dim={dim}, "
        f"max_seq={emb_model.max_seq_length}, torch {torch.__version__} cuda={torch.cuda.is_available()})")

    bm25_fail = df[DV].values.astype(int)
    scratch_fail = (scratch_rank > K).astype(int)
    renderings = {
        "R1_tfidf_style": ([q_text(q) for q in df.question],
                           [[d_text(d) for d in c] for c in cats]),
        "R2_prose": ([prose_query(q) for q in df.question],
                     [[prose_doc(d) for d in c] for c in cats]),
    }

    out, ranks_by, fails_by, margins_by = {}, {}, {}, {}
    for tag, (qtexts, dtexts_per_row) in renderings.items():
        flat_d = [t for row in dtexts_per_row for t in row]
        uq = sorted(set(qtexts)); ud = sorted(set(flat_d))
        iq = {t: i for i, t in enumerate(uq)}; idd = {t: i for i, t in enumerate(ud)}
        qe, tq = embed(emb_model, uq, f"q_{tag}", log)
        de, td = embed(emb_model, ud, f"d_{tag}", log)
        q_idx = np.fromiter((iq[t] for t in qtexts), dtype=np.int64, count=len(qtexts))
        d_idx = np.fromiter((idd[t] for t in flat_d), dtype=np.int64, count=len(flat_d))
        t1 = time.time()
        # one embedding pair per (row, candidate): the query vector repeats across its own candidate list
        scores = dense_scores(qe, de, np.repeat(q_idx, sizes), d_idx)
        assert len(scores) == n_doc_inst, f"{len(scores)} pair scores, expected {n_doc_inst}"
        ranks = best_ranks(sizes, scores, golds, sizes)
        sample = np.random.default_rng(SEED_LAYOUT).choice(n_rows, 300, replace=False)
        brute = brute_ranks(sizes, scores, golds, sample)
        layout_diff = int(np.abs(brute - ranks[sample]).max())
        assert layout_diff == 0, f"vectorised and brute-force ranks differ by {layout_diff}: score layout is wrong"
        mrg = margin_per_row(sizes, scores)
        log(f"  [{tag}] scored {n_doc_inst} pairs in {time.time() - t1:.1f}s")
        f3 = (ranks > K).astype(int)
        hit = 1 - f3.mean()
        out[tag] = {
            "unique_queries_encoded": len(uq), "unique_documents_encoded": len(ud),
            "hit_at_3": round(float(hit), 4),
            "fail_at_3": round(float(f3.mean()), 4),
            "fail_at_3_count": int(f3.sum()),
            "fail_at_3_wilson95": wilson(int(f3.sum()), n_rows),
            "mean_best_rank": round(float(ranks.mean()), 3),
            "spearman_vs_bm25_rank": round(float(stats.spearmanr(ranks, df.bm25_best_rank.values).statistic), 4),
            "spearman_vs_scratch_rank": round(float(stats.spearmanr(ranks, scratch_rank).statistic), 4),
            "truncation_audit_queries": tq, "truncation_audit_documents": td,
            "layout_selfcheck": {"rows": 300, "seed": SEED_LAYOUT,
                               "max_abs_rank_difference_vs_brute_force": layout_diff},
            "cache_sha1": {"queries": cache_key(MODEL, f"q_{tag}", *uq), "documents": cache_key(MODEL, f"d_{tag}", *ud)},
        }
        ranks_by[tag], fails_by[tag], margins_by[tag] = ranks, f3, mrg

    best_tag = max(out, key=lambda t: out[t]["hit_at_3"])
    log(f"  comparator variant fixed by pre-registered rule: {best_tag} (higher hit@3)")

    def overlap(tag):
        a, b = bm25_fail, fails_by[tag]
        inter = int(np.logical_and(a, b).sum()); union = int(np.logical_or(a, b).sum())
        tab = np.array([[inter, a.sum() - inter], [b.sum() - inter, n_rows - union]])
        return {"jaccard_fail_at_3_vs_bm25": round(inter / max(1, union), 4),
                "both_fail_n": inter, "discordant_rows": int(np.sum(a != b)),
                "fisher_odds_ratio_vs_bm25_failure": round(float(stats.fisher_exact(tab)[0]), 3),
                "fisher_p": float(f"{stats.fisher_exact(tab)[1]:.3g}")}

    # --- construct transfer: frozen pre-retrieval model, trained on BM25 failure, scored on the other outcomes ---
    X = matrices(df, FROZEN_FEATURES)["all"]
    auc_bm25_oof = [oof_auc(X, bm25_fail, scaled_pipeline(FROZEN_C), s) for s in SEEDS[:2]]
    p_bm25 = auc_bm25_oof[0][1]
    groups = df["prompt_id"].values
    transfer = {}
    for tag in renderings:
        pf = fails_by[tag]
        auc_scr = roc_auc_score(pf, p_bm25)
        mu, lo, hi, nb = cluster_boot_auc(pf, p_bm25, groups, boot=2000)
        auc_self = [oof_auc(X, pf, scaled_pipeline(FROZEN_C), s) for s in SEEDS[:2]]
        auc_len = roc_auc_score(pf, -df.n_tokens.values)
        m = np.nan_to_num(margins_by[tag], nan=-np.inf)
        transfer[tag] = {
            "prevalence_fail_at_3": round(float(pf.mean()), 4), "fail_at_3_count": int(pf.sum()),
            "auc_frozen_model_trained_on_bm25_failure__scored_on_this_outcome": round(float(auc_scr), 4),
            "cluster_bootstrap": {"mean": round(mu, 4), "ci95": [round(lo, 4), round(hi, 4)],
                                  "resamples_used": nb, "resampled_by": "prompt_id"},
            "auc_model_trained_on_this_failure_oof": [round(a[0], 4) for a in auc_self],
            "auc_length_only": round(float(auc_len), 4),
            "auc_post_margin_bm25_ranker": round(float(roc_auc_score(pf, -df.bm25_margin.values)), 4),
            "auc_post_margin_this_ranker": round(float(roc_auc_score(pf, -m)), 4),
            "meets_pre_registered_0_65_bar": bool(auc_scr >= TRANSFER_BAR),
            "overlap_with_bm25_failure": overlap(tag),
        }
    # same quantity for the EXP-0024 scratch ranker, for the three-way row in the table
    auc_scr_24 = roc_auc_score(scratch_fail, p_bm25)
    mu24, lo24, hi24, nb24 = cluster_boot_auc(scratch_fail, p_bm25, groups, boot=2000)

    res = {
        "exp_id": "EXP-0062", "e_id": "E03c", "k": K, "model": MODEL,
        "why": "EXP-0061 falsified the premise recorded in EXP-0024 that pretrained encoders are unobtainable; "
               "this run replaces that note with a measured pretrained baseline.",
        "protocol": {
            "rows": n_rows, "configs": CONFIGS, "split": "dev", "test_split_read": False,
            "encoder_fitting": "none - the encoder is used unmodified and saw no label of this dataset",
            "tie_handling": "imported best_ranks/margin_per_row from EXP-0024 unchanged",
            "pre_retrieval_model": {"features": "FROZEN_FEATURES", "C": FROZEN_C, "seeds": SEEDS[:2],
                                    "folds": "prompt_id GroupKFold via oof_auc"},
            "pre_registered_rules": {
                "comparator_variant": "the rendering with the higher hit@3 defines the transfer comparator "
                                      "(conservative against this paper's claim); both are reported",
                "transfer_bar": f"AUROC >= {TRANSFER_BAR} for the BM25-trained model scored on the other "
                                "ranker's fail@3 - the same bar EXP-0024 fixed, unchanged",
                "precision_of_estimates": "every AUROC carries a prompt_id-clustered bootstrap CI and every "
                                          "fail@3 rate a Wilson interval, because a strong ranker makes the "
                                          "outcome rare"},
            "torch": {"version": torch.__version__, "cuda_available": bool(torch.cuda.is_available()),
                      "threads": int(torch.get_num_threads())},
            "sentence_transformers_version": sys.modules["sentence_transformers"].__version__,
        },
        "retrieval_quality": {
            "hit_at_3_bm25_frozen": round(float(1 - bm25_fail.mean()), 4),
            "hit_at_3_scratch_dense_exp0024": round(float(1 - scratch_fail.mean()), 4),
            "chance_hit_at_3": round(float(df.chance_hit_3.mean()), 4),
            "pretrained_by_rendering": out,
            "comparator_variant_selected": best_tag,
        },
        "failure_set_agreement": {t: overlap(t) for t in renderings} | {
            "scratch_exp0024_vs_bm25": {"jaccard_fail_at_3_vs_bm25": round(float(
                np.logical_and(bm25_fail, scratch_fail).sum() /
                max(1, np.logical_or(bm25_fail, scratch_fail).sum())), 4),
                "both_fail_n": int(np.logical_and(bm25_fail, scratch_fail).sum()),
                "discordant_rows": int(np.sum(bm25_fail != scratch_fail))}},
        "construct_transfer_to_pretrained_ranker": transfer | {
            "exp0024_scratch_ranker_reference": {
                "prevalence_fail_at_3": round(float(scratch_fail.mean()), 4),
                "auc_frozen_model_trained_on_bm25_failure__scored_on_dense_failure": round(float(auc_scr_24), 4),
                "cluster_bootstrap": {"mean": round(mu24, 4), "ci95": [round(lo24, 4), round(hi24, 4)],
                                      "resamples_used": nb24, "resampled_by": "prompt_id"},
                "meets_pre_registered_0_65_bar": bool(auc_scr_24 >= TRANSFER_BAR)}},
    }
    t_best = transfer[best_tag]
    res["verdict"] = {
        "pretrained_beats_bm25": bool(out[best_tag]["hit_at_3"] > res["retrieval_quality"]["hit_at_3_bm25_frozen"] + 0.01),
        "pretrained_beats_scratch_dense": bool(out[best_tag]["hit_at_3"] > res["retrieval_quality"]["hit_at_3_scratch_dense_exp0024"] + 0.01),
        "construct_survives_pretrained_ranker": bool(t_best["meets_pre_registered_0_65_bar"]),
        "ci_lower_bound_also_clears_bar": bool(t_best["cluster_bootstrap"]["ci95"][1] >= TRANSFER_BAR
                                               and t_best["cluster_bootstrap"]["ci95"][0] >= TRANSFER_BAR),
        "rule": f"the transfer verdict uses {best_tag}, the stronger pretrained rendering, against the unchanged "
                f"EXP-0024 bar of {TRANSFER_BAR}; a point estimate above the bar whose CI crosses it is reported as "
                "underpowered rather than as a pass",
    }
    res["wallclock_sec"] = round(time.time() - t0, 1)
    res["started_at"] = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t0))
    res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")

    OUT_RAW.mkdir(parents=True, exist_ok=True)
    out_path = OUT_RAW / f"EXP0062_pretrained_dense_comparator_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out_path.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    tbl = pd.DataFrame({"row": np.arange(n_rows), "prompt_id": df.prompt_id, "cfg": df.cfg,
                        "bm25_best_rank": df.bm25_best_rank, "scratch_best_rank": scratch_rank,
                        "fail_at_3": bm25_fail, "fail_at_3_scratch": scratch_fail})
    for tag in renderings:
        tbl[f"pretrained_best_rank_{tag}"] = ranks_by[tag]
        tbl[f"fail_at_3_pretrained_{tag}"] = fails_by[tag]
        tbl[f"pretrained_margin_{tag}"] = margins_by[tag]
    tbl["p_preretrieval_bm25_trained"] = p_bm25
    tbl.to_csv(OUT_PROC / "EXP0062_pretrained_vs_bm25_vs_scratch.csv", index=False)
    log(json.dumps(res["retrieval_quality"], indent=1))
    log(json.dumps(res["construct_transfer_to_pretrained_ranker"], indent=1))
    log(f"verdict: {json.dumps(res['verdict'], indent=1)}")
    log(f"wrote {out_path} ({res['wallclock_sec']}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
