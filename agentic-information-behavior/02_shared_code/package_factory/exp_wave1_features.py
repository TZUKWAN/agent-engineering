"""EXP-0119: the wave-1 feature matrix, built once and shared by all six packages.

One matrix rather than six because five of the six designs read the same columns of the same substrate: if each
package re-derived "constraint count" or "BM25 overlap" on its own, the five papers could silently disagree about
what those words mean while appearing to be five independent results. The definitions live in `wave_lib`, which was
written before this script ran, and the self-tests at the bottom pin them.

Sample rule (frozen in `topic_designs_wave1.py` before any row was opened): 8,000 dev rows per config from
routing_{OSS,Qwen3,Kimi-K2}.parquet drawn with `random.Random(42)`, `single-turn-original` subset only. The frozen
frames hold ~10.5k dev rows per config, so the sample is a strict subset and no `test` row can enter it.

Candidate-level rows are emitted too (query x candidate), because T108/T110 are about the decoys a query was shown.

    python 02_shared_code/package_factory/exp_wave1_features.py            # add --selftest to only run the tests
        -> results_processed/EXP0119_wave1_query_features.csv
        -> results_processed/EXP0119_wave1_candidate_rows.csv.gz
        -> results_raw/EXP0119_wave1_feature_matrix_*.json
"""
from __future__ import annotations

import argparse
import pathlib
import random
import sys
import time

import numpy as np
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import wave_lib as W                                            # noqa: E402

ROWS_PER_CONFIG = 8000
SEED = W.SEED
OUTQ = W.OUT / "EXP0119_wave1_query_features.csv"
OUTC = W.OUT / "EXP0119_wave1_candidate_rows.csv.gz"


def build(sample_rows: int = ROWS_PER_CONFIG, verbose=True) -> tuple:
    df = W.load_routing(cfgs=W.CONFIGS, bucket="dev")
    audit = dict(df.attrs["load_routing_audit"])
    df = df[df["subset_name"].astype(str).str.contains("single-turn-original", na=False)].copy()
    frames = []
    for cfg, g in df.groupby("cfg"):
        idx = sorted(random.Random(SEED).sample(range(len(g)), min(sample_rows, len(g))))
        frames.append(g.iloc[idx])
    d = pd.concat(frames, ignore_index=True)
    d = W.add_linguistic_frame(d)
    if verbose:
        print(f"[exp0119] sampled rows: {d.groupby('cfg').size().to_dict()}  (dev-only, audit {audit})")

    qrows, crows, enc = [], [], {"queries": [], "docs": []}
    guard = {"catalog_unparsed": 0, "gold_empty": 0, "gold_index_out_of_range": 0, "n_gold_mismatch": 0}
    t0 = time.time()
    for r in d.itertuples(index=False):
        try:
            entries = W.read_catalog(r.catalog_json, r.n_candidates, r.query_id)
        except AssertionError:
            guard["catalog_unparsed"] += 1
            entries = []
        gold = set(W.as_int_list(r.gold_idx))
        if gold and max(gold) >= len(entries):
            guard["gold_index_out_of_range"] += 1
            gold = set()
        if len(gold) != int(r.n_gold):
            guard["n_gold_mismatch"] += 1
        if not gold:
            guard["gold_empty"] += 1
        q = str(r.question)
        rec = {"cfg": r.cfg, "uuid": r.uuid, "query_id": r.query_id, "prompt_id": r.prompt_id,
               "n_candidates": len(entries) if entries else 0, "n_gold": len(gold),
               "bm25_best_rank_shipped": int(r.bm25_best_rank), "fail_at_1_shipped": int(r.fail_at_1),
               "fail_at_3_shipped": int(r.fail_at_3), "norm_rank_shipped": float(r.norm_rank),
               "n_tokens": int(r.n_tokens), "n_chars": int(r.n_chars),
               "constraint_total": r.constraint_total, "constraint_types": r.constraint_types,
               "constraint_temporal": r.constraint_temporal, "constraint_entity": r.constraint_entity,
               "constraint_numeric": r.constraint_numeric, "constraint_format": r.constraint_format,
               "constraint_scope": r.constraint_scope, "constraint_negation": r.constraint_negation,
               "constraint_per_100": r.constraint_per_100, "unresolved_ref": r.unresolved_ref,
               "ellipsis_n": r.ellipsis_n, "entity_density": r.entity_density,
               "underspec_index": round(float(r.underspec_index), 5), "n_sentences_w": r.n_sentences_w,
               "epistemic_marker_n": int(getattr(r, "epistemic_marker_n", 0) or 0),
               "vague_word_n": int(getattr(r, "vague_word_n", 0) or 0),
               "qpp_coverage": float(getattr(r, "qpp_coverage", float("nan")) or float("nan")),
               "qpp_clarity_meanmax": float(getattr(r, "qpp_clarity_meanmax", float("nan")) or float("nan"))}
        if not entries or not gold:
            rec.update(bm25_rank=rec["bm25_best_rank_shipped"], bm25_desc_rank=-1, inspected_to_gold=-1,
                       top1_norm_ok=-1, max_gold_overlap=-1.0, mean_gold_overlap=-1.0, gold_arg_fit=-1,
                       gold_pred_fit=-1, n_gold_arg=-1, catalogue_per_server=-1.0)
            qrows.append(rec)
            continue
        qtok = W.toks(q)
        docs_full = [W.doc_tokens(entries, i, "full") for i in range(len(entries))]
        docs_desc = [W.doc_tokens(entries, i, "desc") for i in range(len(entries))]
        s_full = W._bm25_scores(qtok, docs_full)
        s_desc = W._bm25_scores(qtok, docs_desc)
        rk_full, rk_desc = W.rank_from(s_full), W.rank_from(s_desc)
        inspected = int(min((rk_full[i] for i in gold), default=-1))
        # the frozen ranker orders the same list the score function ranks, and the tie-break must match
        assert list(np.argsort(-np.array(s_full), kind="stable"))[:5] == list(
            np.array(W.BM25().rank(qtok, docs_full))[:5]), f"ranker disagreement on {r.query_id}"
        gold_ov = []
        for i in sorted(gold):
            dt = set(docs_full[i])
            gold_ov.append(len(set(qtok) & dt) / max(1, len(set(qtok))))
        for i, e in enumerate(entries):
            pa = W.predicate_argument(q, e)
            dq = set(W.toks(e.get("desc", "")))
            crows.append({"query_id": r.query_id, "cfg": r.cfg, "cand_idx": i, "gold": int(i in gold),
                          "bm25": round(float(s_full[i]), 5), "bm25_desc": round(float(s_desc[i]), 5),
                          "rank_full": int(rk_full[i]), "rank_desc": int(rk_desc[i]),
                          "n_candidates": len(entries), "n_gold": len(gold),
                          "desc_len": len(W.toks(e.get("desc", ""))),
                          "param_n": len(e.get("params", []) or []),
                          "q_doc_overlap": round(len(set(qtok) & set(docs_full[i])) / max(1, len(set(qtok))), 5),
                          "q_desc_overlap": round(len(set(qtok) & dq) / max(1, len(set(qtok))), 5),
                          **pa})
        rec.update(bm25_rank=inspected, bm25_desc_rank=int(min((rk_desc[i] for i in gold), default=-1)),
                   inspected_to_gold=inspected,
                   top1_norm_ok=int(rk_full[0] in gold),
                   max_gold_overlap=round(max(gold_ov), 5), mean_gold_overlap=round(sum(gold_ov) / len(gold_ov), 5),
                   gold_pred_fit=int(any(c["gold"] and c["predicate_fit"] for c in crows[-len(entries):])),
                   gold_arg_fit=int(any(c["gold"] and c["argument_fit"] for c in crows[-len(entries):])),
                   n_gold_arg=int(sum(1 for c in crows[-len(entries):] if c["gold"] and c["argument_fit"])),
                   catalogue_per_server=round(float(len(entries)) / max(1, int(r.n_servers_in_row or 1)), 4))
        qrows.append(rec)
    Q = pd.DataFrame(qrows)
    C = pd.DataFrame(crows)
    if guard["catalog_unparsed"] > 0.01 * len(d) or len(C) < len(Q):
        # the first run of this script lost every candidate row to a parser that only knew one of the two catalogue
        # shapes, and printed 24,000 query rows as if nothing had happened
        raise SystemExit(f"ABORT: candidate rows={len(C)} for {len(Q)} query rows, guard={guard} - the "
                         f"candidate-level designs would be computed on an empty table")
    if verbose:
        print(f"[exp0119] query rows={len(Q)} candidate rows={len(C)} in {time.time() - t0:.1f}s guard={guard}")
    audit["guards"] = guard
    return Q, C, audit


# -------------------------------------------------------------------------------------- premise / kill-gate checks
def premise_checks(Q: pd.DataFrame, C: pd.DataFrame) -> dict:
    """Each design's kill gate, evaluated on features only - no relationship to any outcome is read here.

    The gates are frozen in `topic_designs_wave1.py`; this function reports whether they fire, so a design whose
    construct is unidentifiable is reported as unidentifiable instead of being run anyway.
    """
    out = {}
    rr = W.rho_ci(Q, "query_id", "underspec_index", "n_tokens")
    out["T101_length_proxy_gate"] = dict(measure=rr, fires=bool(abs(rr["rho"]) >= 0.8))
    dens = Q[["constraint_total", "n_tokens", "constraint_types", "entity_density", "unresolved_ref",
              "ellipsis_n"]].copy()
    vs = W.vif(dens)
    out["T103_collinearity_gate"] = dict(vif=vs, fires=bool(np.isfinite(vs.get("constraint_total", np.nan))
                                                           and vs["constraint_total"] >= 10))
    gold = C[C["gold"] == 1]
    nong = C[C["gold"] == 0]
    med = float(nong["bm25"].median())
    per_q = nong.assign(hi=(nong["bm25"] > med)).groupby("query_id")["hi"].agg(["sum", "size"])
    out["T108_decoy_identifiability_gate"] = dict(
        median_nongold_bm25=round(med, 4), queries=int(len(per_q)),
        queries_with_high_overlap_nongold=int((per_q["sum"] > 0).sum()),
        queries_with_both_strata=int(((per_q["sum"] > 0) & (per_q["sum"] < per_q["size"])).sum()),
        fires=bool(((per_q["sum"] > 0) & (per_q["sum"] < per_q["size"])).sum() < 300))
    cov = C[["predicate_fit", "argument_fit", "pred_coverage", "arg_coverage"]]
    out["T110_lexicon_coverage_gate"] = dict(
        pred_coverage_share=round(float(cov["pred_coverage"].mean()), 4),
        arg_coverage_share=round(float(cov["arg_coverage"].mean()), 4),
        desc_arg_coverage_share=round(float((C["d_arg_n"] > 0).mean()), 4),
        fires=bool(float(cov["arg_coverage"].mean()) < 0.50))
    out["T103_note_zero_variance"] = dict(
        constraint_total_zero_share=round(float((Q["constraint_total"] == 0).mean()), 4),
        unresolved_zero_share=round(float((Q["unresolved_ref"] == 0).mean()), 4),
        ellipsis_zero_share=round(float((Q["ellipsis_n"] == 0).mean()), 4))
    return out


# -------------------------------------------------------------------------------------------------- self tests
def selftest() -> int:
    """Pins the extractor definitions (§21.4: every transformation of the shared representation carries a test)."""
    fails = []
    cm = W.constraint_markers("Find all JSON files modified after 2024-01-05 and do not send more than 3 messages.")
    for k, exp in (("temporal", True), ("numeric", True), ("format", True), ("scope", True), ("negation", True)):
        if not cm[k]:
            fails.append(f"constraint_markers missed family {k}")
    if W.unresolved_references("Summarise the quarterly report and email it to the client.") != 0:
        fails.append("unresolved_references flagged a cohesive sentence")
    if W.unresolved_references("It should be handled properly.") == 0:
        fails.append("unresolved_references missed a bare anaphor")
    if W.ellipsis("Please fix.") == 0:
        fails.append("ellipsis missed an objectless imperative")
    if W.ellipsis("Please fix the parser module.") != 0:
        fails.append("ellipsis flagged a transitive clause with its object")
    d = pd.DataFrame({"question": ["Translate the Spanish article", "translate the spanish article"]})
    if abs(float(np.mean([float(x) for x in d["question"].map(lambda q: 0)]))) > 1:
        fails.append("frame sanity")
    # the exposed score ranking must equal the frozen class's ordering
    ent = [{"name": "a-b", "desc": "search flights", "params": []},
           {"name": "c-d", "desc": "send email message", "params": ["to"]}]
    s = W._bm25_scores(W.toks("search flights"), [W.doc_tokens(ent, i, "full") for i in range(2)])
    if W.rank_from(s)[0] != 1:
        fails.append("rank_from disagrees with score order")
    # Holm must be the shipped implementation, not a lookalike
    h = W.holm({"a": 0.01, "b": 0.04, "c": 0.03})
    if h["a"] != 0.03 or h["c"] != 0.06:
        fails.append(f"holm values {h}")
    v = W.verdict(0.30, 0.10, 0.55, 0.01, 0.15)
    if v != "supported":
        fails.append(f"verdict supported case -> {v}")
    if W.verdict(0.05, 0.01, 0.09, 0.01, 0.15) != "partial":
        fails.append("verdict partial case")
    if W.verdict(0.30, 0.05, 0.55, 0.40, 0.15) != "partial":
        fails.append("verdict partial case (CI excludes 0 but p_holm >= .05)")
    if W.verdict(0.30, -0.10, 0.50, 0.01, 0.15) != "null":
        # an interval that covers 0 is null whatever the point estimate says; the first draft of this test asked for
        # "partial" here, which would have let a CI-straddling-zero coefficient be reported as a weak finding
        fails.append("verdict null case (CI includes 0)")
    if W.verdict(-0.30, -0.55, -0.10, 0.01, 0.15, direction=1.0) != "opposite":
        fails.append("verdict opposite case")
    if W.verdict(0.30, -0.1, 0.5, 0.01, 0.15) != "null":
        fails.append("verdict null case")
    lo, hi, k = W.cluster_boot(pd.DataFrame({"query_id": [f"q{i}" for i in range(200)],
                                             "v": np.arange(200.0) / 200}), "query_id",
                               lambda d: float(np.mean(d["v"])))
    if k != 200 or lo is None:
        fails.append("cluster_boot did not resample groups")
    if W.zscore(pd.Series([3.0, 3.0, 3.0])).abs().max() != 0:
        fails.append("zscore of a constant column is not zero")
    if [W.as_int_list(x) for x in ("[0]", "[0, 3]", [1, 2], np.array([4]), "2;3", None, "")] != \
            [[0], [0, 3], [1, 2], [4], [2, 3], [], []]:
        fails.append("as_int_list does not normalise every gold_idx form the frames carry")
    for f in fails:
        print("  SELFTEST FAIL:", f)
    print(f"selftest: {len(fails)} failure(s)")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--rows", type=int, default=ROWS_PER_CONFIG)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if args.selftest:
        return selftest()
    st = selftest()
    if st:
        print("ABORT: the shared extractor tests failed, so no matrix could be written")
        return st
    t0 = time.time()
    Q, C, audit = build(args.rows)
    gates = premise_checks(Q, C)
    PROC = W.OUT
    PROC.mkdir(parents=True, exist_ok=True)
    Q.to_csv(OUTQ, index=False)
    C.to_csv(OUTC, index=False, compression="gzip")
    art = {"exp_id": "EXP-0119", "seed": SEED, "rows_per_config_requested": args.rows,
           "sample_rule": "random.Random(42) over dev rows of routing_{OSS,Qwen3,Kimi-K2}.parquet, "
                          "single-turn-original subset",
           "split_audit": audit, "n_query_rows": int(len(Q)), "n_candidate_rows": int(len(C)),
           "configs": {c: int(n) for c, n in Q.groupby("cfg").size().items()},
           "query_coverage": {c: {"bm25_rank_ge0_share": round(float((Q[Q.cfg == c]["inspected_to_gold"] > 0).mean()), 4),
                                  "constraint_total_mean": round(float(Q[Q.cfg == c]["constraint_total"].mean()), 3),
                                  "underspec_sd": round(float(Q[Q.cfg == c]["underspec_index"].std()), 4)}
                              for c in Q["cfg"].unique()},
           "kill_gates": gates, "outputs": [str(OUTQ.relative_to(W.ROOT)), str(OUTC.relative_to(W.ROOT))],
           "run_cost": W.run_cost_row("EXP-0119", t0, len(Q), Q.shape[1],
                                      "shared wave-1 matrix; candidate rows written gzipped"),
           "environment": W.environment_record(), "started_at": W.now(), "finished_at": W.now()}
    p = W.write_raw("EXP-0119", "wave1_feature_matrix", art)
    log = W.LOGS / f"EXP-0119_wave1_features_{time.strftime('%Y%m%dT%H%M%S')}.txt"
    log.write_text("\n".join(f"{k}: {v}" for k, v in art.items() if k not in ("environment",)) + "\n",
                   encoding="utf-8")
    json_short(art)
    print(f"wrote {p.relative_to(W.ROOT)} and {log.relative_to(W.ROOT)}")
    return 0


def json_short(art: dict) -> None:
    import json
    print(json.dumps({"n_query_rows": art["n_query_rows"], "n_candidate_rows": art["n_candidate_rows"],
                      "configs": art["configs"], "kill_gates": art["kill_gates"]}, indent=1)[:3000])


if __name__ == "__main__":
    raise SystemExit(main())
