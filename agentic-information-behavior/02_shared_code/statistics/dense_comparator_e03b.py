"""EXP-0024 (E03b): a learned dense comparator trained from scratch, against the "weak baseline" attack.

P001 defines routing failure against a frozen BM25 ranker, so a reviewer can object that no *trained* retriever
was ever compared. Pretrained encoders were unavailable at run time (project policy forbids inference APIs; the
installed torch is a CPU-only build; no encoder library or model weights could be downloaded - all measured in
EXP-0022 and recorded in the deviations correction). The honest substitute is a dense model trained from scratch
under the same information the paper already has, compared on identical rows rather than quoted from a leaderboard.

CORRECTION, added to this docstring after the run (nothing executable was touched): EXP-0061 measured the
"no downloadable weights" premise to be FALSE (hf-mirror.com serves real weight bytes), and EXP-0062 (`pretrained_dense_comparator_p001.py`, E03c) ran the
pretrained comparator this script's environment note ruled out. Only this docstring was edited afterwards: no executable
line here changed, because EXP-0062 imports `best_ranks`/`margin_per_row` from this file and a behavioural edit would
silently change what the published `results_raw/EXP0024_dense_comparator_*.json` run means.

Fixed before the first training run:
  * representation: TF-IDF (sublinear tf, l2) over tool-name tokens + description + parameter names for documents
    and over the instruction for queries; vocabulary fitted on TRAINING folds only;
  * model: two linear towers to DIM=128, cosine score, softmax over each row's own candidates with every gold tool
    as a positive (a ranking objective matched to hit@k), Adam, full-batch steps, seed 42;
  * evaluation: GroupKFold by prompt_id over the pooled development splits, so every dense rank is out-of-fold;
    BM25 ranks are the frozen ones already stored for exactly the same rows;
  * the claim-relevant test: redefine the outcome as fail@3 for the DENSE ranker, then ask (a) whether the frozen
    pre-retrieval model trained on BM25-failure still separates dense-failure and (b) whether a model trained on
    dense-failure reaches a comparable AUROC. Pre-registered reading: AUROC >= 0.65 against the dense outcome
    means the construct is not a BM25 artifact; below that it is reported as ranker-specific;
  * no test-split row is read anywhere here, so the test ledger stays at exactly one evaluation.

    python dense_comparator_e03b.py

Outputs results_raw/EXP0024_dense_comparator_*.json and results_processed/EXP0024_dense_vs_bm25.csv.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from scipy import stats
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "trajectory_parser"))
from analyze_routing_failure import CONFIGS, PROC, SEEDS, oof_auc, scaled_pipeline  # noqa: E402
from build_toucan_routing_dataset import toks  # noqa: E402
from run_p001_experiments import FROZEN_C, FROZEN_FEATURES, matrices  # noqa: E402

K = 3
DV = "fail_at_3"
DIM, STEPS, LR = 128, 80, 5e-3
SEED = 42
MIN_DF, MAX_FEATURES = 3, 30_000
N_FOLDS = 5
OUT_RAW = HERE.parents[1] / "results_raw"
OUT_PROC = HERE.parents[1] / "results_processed"


def q_text(q: str) -> str:
    return " ".join(toks(q))


def d_text(doc) -> str:
    return " ".join(toks(doc["n"].replace("-", " ").replace("_", " ")) + toks(doc["d"])
                    + toks(" ".join(doc["p"])))


def coo(mat):
    """A scipy CSR matrix as a torch COO tensor whose values are constants (only the weight gets grads)."""
    m = mat.tocoo()
    idx = torch.from_numpy(np.vstack([m.row, m.col]).astype(np.int64))
    val = torch.from_numpy(m.data.astype(np.float32))
    return torch.sparse_coo_tensor(idx, val, size=(m.shape[0], m.shape[1])).coalesce()


def best_ranks(row_sizes, scores, golds, cat_lengths):
    """Rank docs inside each row by dense score (ties by slot, as the frozen BM25 sort does); take best gold rank."""
    n_rows, W = len(row_sizes), int(max(row_sizes))
    rd = np.repeat(np.arange(n_rows), row_sizes)
    sl = np.concatenate([np.arange(n) for n in row_sizes])
    order = np.lexsort((sl, -scores, rd))
    r_sorted, s_sorted = rd[order], sl[order]
    first = np.flatnonzero(np.r_[True, r_sorted[1:] != r_sorted[:-1]])
    row_start = np.zeros(n_rows, dtype=int)
    row_start[r_sorted[first]] = first
    rank_sorted = np.arange(1, len(r_sorted) + 1) - row_start[r_sorted]
    rank_of = np.full((n_rows, W), 10 ** 6, dtype=int)
    rank_of[r_sorted, s_sorted] = rank_sorted
    return np.array([int(min(rank_of[p, list(g)])) if len(g) else cat_lengths[p]
                     for p, g in enumerate(golds)])


def train_and_score(train_idx, eval_idx, df, cats, golds, steps, lr):
    train_idx = np.asarray(train_idx); eval_idx = np.asarray(eval_idx)
    tr_doc_texts = [d_text(d) for i in train_idx for d in cats[i]]
    tr_q_texts = [q_text(df.question[i]) for i in train_idx]
    vec = TfidfVectorizer(min_df=MIN_DF, max_features=MAX_FEATURES, sublinear_tf=True,
                          token_pattern=r"[^\s]+", dtype=np.float32)
    vec.fit(tr_doc_texts + tr_q_texts)
    Dt = vec.transform(tr_doc_texts); Qt = vec.transform(tr_q_texts)
    rd = np.repeat(np.arange(len(train_idx)), [len(cats[i]) for i in train_idx])
    sl = np.concatenate([np.arange(len(cats[i])) for i in train_idx])
    gr = np.repeat(np.arange(len(train_idx)), [len(golds[i]) for i in train_idx])
    gs = np.concatenate([list(golds[i]) for i in train_idx])
    SQt, SDt = coo(Qt), coo(Dt)
    torch.manual_seed(SEED)
    Wq = torch.nn.Parameter(torch.randn(SQt.shape[1], DIM, dtype=torch.float32) / np.sqrt(SQt.shape[1]))
    Wd = torch.nn.Parameter(torch.randn(SDt.shape[1], DIM, dtype=torch.float32) / np.sqrt(SDt.shape[1]))
    opt = torch.optim.Adam([Wq, Wd], lr=lr)
    W = int(max(np.bincount(rd)))
    logits0 = torch.full((len(train_idx), W), float("-inf"))
    rd_t, sl_t, gr_t, gs_t = (torch.from_numpy(x) for x in (rd, sl, gr, gs))
    losses = []
    for step in range(steps):
        Eq = torch.nn.functional.normalize(torch.sparse.mm(SQt, Wq), dim=1)
        Ed = torch.nn.functional.normalize(torch.sparse.mm(SDt, Wd), dim=1)
        s = (Eq[rd_t] * Ed).sum(1)
        logits = logits0.clone()
        logits[rd_t, sl_t] = s
        lp = torch.log_softmax(logits, dim=1)
        loss = -lp[gr_t, gs_t].mean()
        opt.zero_grad(); loss.backward(); opt.step()
        losses.append(float(loss))
        if step % 20 == 0 or step == steps - 1:
            print(f"    step {step:3d} loss {float(loss):.4f}")
    with torch.no_grad():
        ev_doc_texts = [d_text(d) for i in eval_idx for d in cats[i]]
        ev_q_texts = [q_text(df.question[i]) for i in eval_idx]
        De, Qe = coo(vec.transform(ev_doc_texts)), coo(vec.transform(ev_q_texts))
        Eq = torch.nn.functional.normalize(torch.sparse.mm(Qe, Wq), dim=1)
        Ed = torch.nn.functional.normalize(torch.sparse.mm(De, Wd), dim=1)
        erd = torch.from_numpy(np.repeat(np.arange(len(eval_idx)), [len(cats[i]) for i in eval_idx]))
        sc = (Eq[erd] * Ed).sum(1).numpy()
    sizes = [len(cats[i]) for i in eval_idx]
    ranks = best_ranks(sizes, sc, [golds[i] for i in eval_idx], sizes)
    # the ranker's own score margin: the fair post-retrieval comparator under the DENSE ranker
    mrg = margin_per_row(sizes, sc)
    return (dict(zip(eval_idx.tolist(), ranks.tolist())), dict(zip(eval_idx.tolist(), mrg.tolist())),
            losses[-1], int(SQt.shape[1]))


def margin_per_row(row_sizes, scores):
    n = len(row_sizes)
    rd = np.repeat(np.arange(n), row_sizes)
    order = np.lexsort((-scores, rd))
    r_s, s_s = rd[order], scores[order]
    first = np.flatnonzero(np.r_[True, r_s[1:] != r_s[:-1]])
    top = np.full(n, np.nan); second = np.full(n, np.nan)
    for pos, rr in zip(first, r_s[first]):
        top[rr] = s_s[pos]
        if pos + 1 < len(s_s) and r_s[pos + 1] == rr:
            second[rr] = s_s[pos + 1]
    return top - np.nan_to_num(second)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    df = pd.concat([pd.read_parquet(PROC / f"routing_{c}.parquet") for c in CONFIGS], ignore_index=True)
    df = df[(df.split == "dev") & (df.n_candidates > K)].reset_index(drop=True)
    cats = [json.loads(c) for c in df.catalog_json]
    golds = [json.loads(g) for g in df.gold_idx]
    n_docs = int(sum(len(c) for c in cats))
    print(f"EXP-0024 dense comparator | dev rows={len(df)} docs={n_docs} "
          f"configs={CONFIGS} dim={DIM} steps={STEPS} lr={LR}")

    rank_oof = np.zeros(len(df), dtype=int)
    margin_oof = np.full(len(df), np.nan)
    losses, vocab = [], set()
    for f, (tr, te) in enumerate(GroupKFold(n_splits=N_FOLDS).split(df, groups=df.prompt_id)):
        r, mg, loss, V = train_and_score(tr, te, df, cats, golds, STEPS, LR)
        for i, v in r.items():
            rank_oof[i] = v
        for i, v in mg.items():
            margin_oof[i] = v
        losses.append(loss); vocab.add(V)
        print(f"  fold {f + 1}/{N_FOLDS}: held-out rows={len(te)} final loss={loss:.4f} vocab={V}")

    dense_fail = (rank_oof > K).astype(int)
    bm25_fail = df[DV].values.astype(int)
    y_bm25 = bm25_fail
    X = matrices(df, FROZEN_FEATURES)["all"]
    auc_bm25_oof = [oof_auc(X, y_bm25, scaled_pipeline(FROZEN_C), s) for s in SEEDS[:2]]
    auc_dense_oof = [oof_auc(X, dense_fail, scaled_pipeline(FROZEN_C), s) for s in SEEDS[:2]]
    p_bm25 = auc_bm25_oof[0][1]
    both = np.asarray([(a, b) for a, b in zip(bm25_fail, dense_fail)])
    rho = stats.spearmanr(rank_oof, df.bm25_best_rank.values)
    res = {
        "exp_id": "EXP-0024", "e_id": "E03b", "seed": SEED, "k": K,
        "model": {"dim": DIM, "steps": STEPS, "lr": LR, "loss": "per-row softmax over own candidates, "
                  "all golds as positives", "framework": f"torch {torch.__version__}, sparse CPU matmul",
                  "vocab_size_per_fold": sorted(vocab), "final_loss_per_fold": [round(l, 4) for l in losses]},
        "protocol": {"rows": int(len(df)), "grouping": "prompt_id GroupKFold", "folds": N_FOLDS,
                     "vocabulary_fitted_on": "training fold documents and queries only",
                     "test_split_read": False},
        "retrieval_quality": {
            "hit_at_3_bm25_frozen": round(float(1 - bm25_fail.mean()), 4),
            "hit_at_3_dense_trained": round(float(1 - dense_fail.mean()), 4),
            "mean_bm25_best_rank": round(float(df.bm25_best_rank.mean()), 3),
            "mean_dense_best_rank": round(float(rank_oof.mean()), 3),
            "chance_hit_at_3": round(float(df.chance_hit_3.mean()), 4),
            "spearman_dense_vs_bm25_rank": round(float(rho.statistic), 4),
            "positive_set_overlap_jaccard": round(float(
                np.logical_and(both[:, 0], both[:, 1]).sum() /
                max(1, np.logical_or(both[:, 0], both[:, 1]).sum())), 4),
            "discordant_rows": int(np.sum(both[:, 0] != both[:, 1]))},
        "construct_transfer_to_a_trained_ranker": {
            "prevalence_fail_at_3_dense": round(float(dense_fail.mean()), 4),
            "auc_frozen_model_trained_on_bm25_failure__scored_on_dense_failure":
                round(float(roc_auc_score(dense_fail, p_bm25)), 4),
            "auc_model_trained_on_dense_failure_oof": [round(a[0], 4) for a in auc_dense_oof],
            "auc_model_trained_on_bm25_failure_oof": [round(a[0], 4) for a in auc_bm25_oof],
            "auc_length_only_vs_dense_failure": round(float(roc_auc_score(dense_fail, -df.n_tokens.values)), 4),
            "auc_post_margin_bm25_ranker_vs_dense_failure":
                round(float(roc_auc_score(dense_fail, -df.bm25_margin.values)), 4),
            "auc_post_margin_dense_ranker_vs_dense_failure":
                round(float(roc_auc_score(dense_fail, -np.nan_to_num(margin_oof, nan=-np.inf))), 4),
            "note_on_margins": "the BM25 margin is the wrong post-retrieval signal once the ranker is dense, so "
                               "the dense model's own top1-top2 cosine margin is reported alongside it"},
    }
    a = res["construct_transfer_to_a_trained_ranker"]
    res["verdict"] = {
        "dense_is_stronger_ranker": bool(res["retrieval_quality"]["hit_at_3_dense_trained"]
                                         > res["retrieval_quality"]["hit_at_3_bm25_frozen"] + 0.01),
        "construct_survives_trained_ranker": bool(a[
            "auc_frozen_model_trained_on_bm25_failure__scored_on_dense_failure"] >= 0.65),
        "rule": "AUROC >= 0.65 against the dense-ranker outcome (fixed before training) means the pre-retrieval "
                "signal is not a BM25 artifact; the dense-vs-BM25 hit@3 gap is reported either way"}
    res["wallclock_sec"] = round(time.time() - t0, 1)
    res["started_at"] = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t0))
    res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    OUT_RAW.mkdir(parents=True, exist_ok=True)
    out = OUT_RAW / f"EXP0024_dense_comparator_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    pd.DataFrame({"row": np.arange(len(df)), "prompt_id": df.prompt_id, "cfg": df.cfg,
                  "bm25_best_rank": df.bm25_best_rank, "dense_best_rank": rank_oof,
                  "fail_at_3": bm25_fail, "fail_at_3_dense": dense_fail,
                  "dense_margin": margin_oof, "p_preretrieval": p_bm25}).to_csv(OUT_PROC / "EXP0024_dense_vs_bm25.csv", index=False)
    print(json.dumps(res["retrieval_quality"], indent=1))
    print(json.dumps(res["construct_transfer_to_a_trained_ranker"], indent=1))
    print("verdict:", res["verdict"])
    print("wrote", out, f"({res['wallclock_sec']}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
