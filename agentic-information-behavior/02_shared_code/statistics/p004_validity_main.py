"""EXP-0042 (P004 main): E2 structure, E3 executed-tool criterion, E4 confound audit, E5 gating consequence.

Implements papers/P004_shipped_quality_score_validity/protocol_freeze.md section by section, on the frozen sample
(seed 42, 10 random shards per config, <=2,000 rows per shard, dev rows only, test never read). All decision bands
were written before this script ran; the script only computes and labels, and every label can go either way.

    python 02_shared_code/statistics/p004_validity_main.py
Writes results_raw/EXP0042_p004_validity_main_*.json and results_processed/EXP0042_*.csv.
"""
from __future__ import annotations

import json, sys, time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p004_common as C

ROOT = Path(__file__).resolve().parents[2]
CRIT = {                                        # dimension -> (objective criterion, direction note) from the freeze
    "q_tool_selection_difficulty": "fail_at_3",
    "q_tool_selection_uniqueness": "fail_at_3",
    "q_question_quality": "bm25_best_rank",
    "q_scenario_realism": "bm25_best_rank",
    "q_verifiable": "executed_tool_agreement",
    "q_stability": "bm25_best_rank",
    "q_overall_score": "fail_at_3",
    "r_desired_tools_used_percentage": "executed_tool_agreement",
    "r_completeness": "executed_tool_agreement",
    "r_conciseness": "q_chars",
    "r_order_correctness": "bm25_best_rank",
    "r_overall_score": "executed_tool_agreement",
}
STRATA = [(4, 5), (6, 9), (10, 20), (21, 10 ** 6)]


def classify_alpha(a, lo, hi):
    if not np.isfinite(a):
        return "UNESTIMABLE"
    if a >= 0.70 and lo is not None and lo > 0.60:
        return "SCALE_COHERENT"
    if a < 0.40:
        return "NOT_COHERENT"
    return "AMBIGUOUS"


def classify_rho(r, ci):
    if r is None or not np.isfinite(r) or ci is None:
        return "UNESTIMABLE"
    lo, hi = ci
    band = sorted([abs(lo), abs(hi)])
    if abs(r) >= 0.30 and band[0] > 0.15:
        return "VALID"
    if abs(r) <= 0.10 and band[1] < 0.15:
        return "NOT_VALID"
    return "INCONCLUSIVE"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    res = {"exp_id": "EXP-0043", "paper_id": "P004", "e_id": "E2-E5", "seed": C.SEED,
           "supersedes": "EXP-0042 (joined P001's routing table for the criterion: sample collapsed to 4,322 "
                         "rows and inherited its 2-of-10-shard coverage defect; see papers/"
                         "P004_shipped_quality_score_validity/deviations.md D31). Both raw files are kept.",
           "protocol": "papers/P004_shipped_quality_score_validity/protocol_freeze.md",
           "sample_rule": f"{C.SHARDS} random shards x <= {C.ROWS_PER_SHARD} rows per config; dev only; "
                          "test never read",
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "configs": {}}
    frames = []
    for cfg in C.CONFIGS:
        m, meta = C.frame(cfg)
        frames.append(m)
        res["configs"][cfg] = {"sample": meta, "rows": int(len(m)),
                               "prevalence_fail_at_3": round(float(m.fail_at_3.mean()), 4)}
        print(f"  {cfg}: dev rows={len(m)} prev={m.fail_at_3.mean():.4f} parse_fail={meta['score_json_parse_failures']}")
    A = pd.concat(frames, ignore_index=True)

    # ---- E3: is the rule-extracted executed-tool criterion usable at all? -----------------------------
    no_calls = float((A.n_called == 0).mean())
    nan_agree = float(A.executed_tool_agreement.isna().mean())
    ex = A[A.executed_tool_agreement.notna()].sample(min(6, len(A[A.executed_tool_agreement.notna()])),
                                                     random_state=C.SEED)
    res["E3_executed_tool_criterion"] = {
        "rows_with_no_extracted_call": round(no_calls, 4), "rows_without_gold": round(nan_agree, 4),
        "agreement_mean": round(float(A.executed_tool_agreement.mean()), 4),
        "share_at_unity": round(float((A.executed_tool_agreement == 1).mean()), 4),
        "examples": [{"uuid": r.uuid[:10], "n_gold": int(r.n_gold), "n_called": int(r.n_called),
                      "agreement": round(float(r.executed_tool_agreement), 3)} for r in ex.itertuples()],
        "note": "the criterion is a rule extraction, not a judgement; if it cannot see calls, the completeness "
                "audit is void and must be reported as such"}

    # ---- E2 / RQ1: internal structure per config and pooled ------------------------------------------
    def rq1(df, tag):
        a = C.alpha(df, ["q_" + x for x in C.QD])
        lo, hi, n = C.clustered_ci(df, ["q_" + x for x in C.QD],
                                   lambda s: C.alpha(s, ["q_" + x for x in C.QD]), draws=500)
        itm = {}
        for x in C.QD:
            others = ["q_" + o for o in C.QD if o != x]
            sub = df[["q_" + x] + others].dropna()
            if len(sub) > 50:
                itm["q_" + x] = round(float(spearmanr(sub["q_" + x], sub[others].mean(axis=1)).statistic), 3)
        ov = {c: round(C.rho(df, "q_overall_score", c), 3) for c in ["q_" + x for x in C.QD]}
        return {"tag": tag, "alpha": None if not np.isfinite(a) else round(a, 3),
                "alpha_ci_prompt_clustered": [lo, hi], "draws": n, "verdict": classify_alpha(a, lo, hi),
                "item_total_rho": itm, "overall_vs_components": ov}

    res["RQ1"] = {"per_config": {cfg: rq1(m, cfg) for cfg, m in zip(C.CONFIGS, frames)}, "pooled": rq1(A, "pooled")}
    print("  RQ1 alpha:", {k: v["alpha"] for k, v in res["RQ1"]["per_config"].items()}, "pooled",
          res["RQ1"]["pooled"]["alpha"], res["RQ1"]["pooled"]["verdict"])

    # ---- E2 / RQ2: criterion validity with Holm inside the family ------------------------------------
    raw_p, entries = {}, {}
    from scipy.stats import spearmanr as _s
    for dim, crit in CRIT.items():
        if dim not in A.columns:
            continue
        sub = A[[dim, crit]].dropna()
        if len(sub) < 50 or sub[dim].std() == 0 or sub[crit].std() == 0:
            entries[dim] = {"error": "not estimable", "n": int(len(sub))}
            continue
        r = float(_s(sub[dim], sub[crit]).statistic)
        n_obs = len(sub)
        lo, hi, nd = C.clustered_ci(A, [dim, crit], lambda s: float(_s(s[dim], s[crit]).statistic), draws=1000)
        # two-sided p from the bootstrap CI width (normal approximation on Fisher-z), then Holm over the family
        z = 0.5 * np.log((1 + r) / (1 - r)) * np.sqrt(max(1, n_obs - 3))
        from math import erfc, sqrt
        p = float(erfc(abs(z) / sqrt(2)))
        key = f"{dim}|{crit}"
        raw_p[key] = min(max(p, 1e-300), 1.0)
        entries[dim] = {"criterion": crit, "n": n_obs, "rho": round(r, 4), "ci95_prompt_clustered": [lo, hi],
                        "p_raw": p}
    adj = C.holm(raw_p)
    for dim, e in entries.items():
        if "rho" in e:
            k = f"{dim}|{e['criterion']}"
            e["p_holm"] = adj[k]
            e["verdict"] = classify_rho(e["rho"], e["ci95_prompt_clustered"])
    res["RQ2"] = entries
    print("  RQ2 verdicts:", {d: e.get("verdict") for d, e in entries.items()})

    # ---- E4 / RQ3: confound audit - partial and stratified, no pass/fail ------------------------------
    conf = {}
    for dim in ["q_tool_selection_difficulty", "q_overall_score", "r_desired_tools_used_percentage"]:
        if dim not in A.columns:
            continue
        A["_res_" + dim] = C.residual(A, dim, ["n_candidates", "q_chars"])
        A["_resc"] = C.residual(A, "fail_at_3", ["n_candidates", "q_chars"])
        pooled = C.rho(A, dim, "fail_at_3")
        partial = C.rho(A.dropna(subset=["_res_" + dim, "_resc"]), "_res_" + dim, "_resc")
        strat = {}
        for lo, hi in STRATA:
            g = A[(A.n_candidates >= lo) & (A.n_candidates <= hi)]
            if len(g) > 100 and g[dim].std() > 0 and g.fail_at_3.std() > 0:
                strat[f"{lo}-{hi if hi < 10**5 else 'max'}"] = {"n": int(len(g)),
                                                               "rho": round(float(C.rho(g, dim, "fail_at_3")), 3)}
        conf[dim] = {"pooled_rho_vs_fail_at_3": None if not np.isfinite(pooled) else round(pooled, 3),
                     "partial_rho_given_catalogue_and_length": None if not np.isfinite(partial) else round(partial, 3),
                     "rho_by_catalogue_stratum": strat,
                     "r2_of_ranks_on_n_candidates":
                         round(float(np.corrcoef(A["n_candidates"].rank(), A[dim].rank())[0, 1] ** 2), 3)}
    res["RQ3"] = conf
    print("  RQ3 pooled vs partial:", {k: (v["pooled_rho_vs_fail_at_3"],
                                           v["partial_rho_given_catalogue_and_length"]) for k, v in conf.items()})

    # ---- E5 / RQ4: what the customary gate actually does ---------------------------------------------
    gate = {}
    for cfg, m in zip(C.CONFIGS, frames):
        if "q_overall_score" not in m.columns:
            continue
        keep = m[m.q_overall_score >= 4]
        d = {"rows_all": int(len(m)), "rows_kept": int(len(keep)), "kept_share": round(len(keep) / max(1, len(m)), 4),
             "fail_at_3_all": round(float(m.fail_at_3.mean()), 4),
             "fail_at_3_kept": round(float(keep.fail_at_3.mean()), 4) if len(keep) else None,
             "mean_n_candidates_all": round(float(m.n_candidates.mean()), 2),
             "mean_n_candidates_kept": round(float(keep.n_candidates.mean()), 2) if len(keep) else None,
             "instances_all": int(m.prompt_id.nunique()), "instances_kept": int(keep.prompt_id.nunique())}
        rel = lambda a, b: None if (a in (None, 0) or b is None) else round(abs(b - a) / abs(a), 4)
        d["relative_shift"] = {"prevalence": rel(d["fail_at_3_all"], d["fail_at_3_kept"]),
                               "catalogue_size": rel(d["mean_n_candidates_all"], d["mean_n_candidates_kept"]),
                               "instances_lost": rel(d["instances_all"], d["instances_kept"])}
        s = d["relative_shift"]
        d["verdict"] = ("GATING_DISTORTS" if (s["prevalence"] or 0) >= 0.20 or (s["catalogue_size"] or 0) >= 0.20
                        or (s["instances_lost"] or 0) >= 0.30 else
                        "GATING_NEUTRAL" if all((x or 0) < 0.05 for x in s.values()) else "REPORT_ONLY")
        gate[cfg] = d
    res["RQ4"] = gate
    print("  RQ4 gating:", {k: (v["kept_share"], v["verdict"]) for k, v in gate.items()})

    res["wallclock_sec"] = round(time.time() - t0, 1)
    res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    (ROOT / "results_raw").mkdir(exist_ok=True)
    out = ROOT / "results_raw" / f"EXP0043_p004_validity_main_{time.strftime('%Y%m%dT%H%M%S')}.json"

    def default(o):
        if isinstance(o, (np.floating, np.integer)):
            return o.item()
        if isinstance(o, np.ndarray):
            return o.tolist()
        return str(o)

    out.write_text(json.dumps(res, indent=1, ensure_ascii=False, default=default), encoding="utf-8")
    pd.DataFrame([{"config": cfg, "dimension": d, **{k: v for k, v in e.items() if k != "examples"}}
                  for d, e in res["RQ2"].items() for cfg in ["pooled"]]).to_csv(
        ROOT / "results_processed" / "EXP0043_criterion_validity.csv", index=False)
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
