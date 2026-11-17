"""EXP-0039 (T024 pilot): are the quality scores shipped inside Toucan valid instruments?

Toucan-1.5M carries vendor-computed LLM quality assessments as two top-level JSON columns
(`question_quality_assessment`, `response_quality_assessment`) with 6 question-side and 5 response-side numeric
dimensions plus per-dimension reasoning text. A 1.5M-row public corpus that ships its own automatic scores is an
instrument in circulation, and nobody has audited it against criteria that do not come from a model.

Ground truth here is objective and already computable without any model API: whether a BM25 ranker with the frozen
parameters can reach the gold tool at all (fail@3, best rank) and how many candidates were offered. Internal
structure is measured with Cronbach alpha and item-total rank correlations; `overall_score` is tested against its
own stated components.

Pre-registered promotion rule for the pilot (fixed before running): T024 becomes a paper candidate iff
 (a) the dimensions vary (no zero-variance item) and >=1,000 rows join to an objective outcome,
 (b) at least one question-side dimension shows |Spearman rho| < 0.15 against fail@3 (weak criterion validity -
     either direction is a finding), and
 (c) the catalogue-size confound is separable, i.e. stratified rho collapses to |rho| < 0.10 in the two largest
     strata while the pooled rho is larger.
A negative answer is a publishable answer; the numbers are written out whichever way they fall.

    python 02_shared_code/statistics/quality_score_pilot_t024.py
Writes results_raw/EXP0039_quality_score_pilot_*.json and results_processed/EXP0039_*.csv.
"""
from __future__ import annotations

import json, pathlib, sys, time
from collections import defaultdict

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.stats import spearmanr

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA = pathlib.Path(r"G:/刘俊琦/AGENT ENGINEERING/MATLABINTOKEN/datasets/Agent-Ark/Toucan-1.5M")
CONFIGS = ["OSS", "Qwen3", "Kimi-K2"]
SHARDS = 3
QD = ["q_tool_selection_difficulty", "q_tool_selection_uniqueness", "q_question_quality", "q_scenario_realism",
      "q_verifiable", "q_stability"]


def load_scores(cfg):
    rows = []
    d = DATA / cfg
    for f in sorted(d.glob("*.parquet"))[:SHARDS]:
        for r in pq.read_table(f, columns=["uuid", "question_quality_assessment",
                                           "response_quality_assessment"]).to_pylist():
            try:
                q = json.loads(r["question_quality_assessment"])
                a = json.loads(r["response_quality_assessment"])
            except Exception:                                     # noqa: BLE001 - malformed vendor JSON is a finding
                rows.append({"uuid": r["uuid"], "_parse_failed": True})
                continue
            rec = {"uuid": r["uuid"], "_parse_failed": False}
            for k, v in q.items():
                rec["q_" + k] = v.get("score") if isinstance(v, dict) else v
            for k, v in a.items():
                rec["r_" + k] = v.get("score") if isinstance(v, dict) else v
            rows.append(rec)
    return pd.DataFrame(rows)


def alpha(df):
    X = df.dropna()
    k = X.shape[1]
    if k < 2 or len(X) < 50 or X.sum(axis=1).var(ddof=1) == 0:
        return None, k, len(X)
    return round(float(k / (k - 1) * (1 - X.var(axis=0, ddof=1).sum() / X.sum(axis=1).var(ddof=1))), 3), k, len(X)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    res = {"exp_id": "EXP-0039", "paper_id": "T024", "stage": "pilot", "shards_per_config": SHARDS,
           "ground_truth": "objective BM25 outcome from the published routing dataset; no model in the loop",
           "rule": "promote iff dimensions vary, >=1000 joined rows, a question-side |rho vs fail@3| < 0.15, and "
                   "the pooled relation collapses to |rho|<0.10 in the two largest catalogue-size strata",
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "configs": {}}
    per = defaultdict(list)
    for cfg in CONFIGS:
        S = load_scores(cfg)
        routed = pd.read_parquet(ROOT / "01_datasets" / "processed" / f"routing_{cfg}.parquet")
        M = S.merge(routed[["uuid", "split", "fail_at_3", "bm25_best_rank", "n_candidates"]], on="uuid", how="inner")
        M = M[M.split == "dev"].copy()
        parse_fail = float(S._parse_failed.mean())
        num = S.select_dtypes(include=[np.number])
        a, k, n = alpha(S[QD])
        itm = {}
        for c in QD:
            sub = S[[c] + [o for o in QD if o != c]].dropna()
            if len(sub) > 50:
                itm[c] = round(float(spearmanr(sub[c], sub[[o for o in QD if o != c]].mean(axis=1)).statistic), 3)
        crit = {}
        for c in [x for x in QD if x in M and M[x].std() > 0]:
            sub = M[[c, "fail_at_3"]].dropna()
            if sub.fail_at_3.std() > 0 and len(sub) > 50:
                crit[c] = round(float(spearmanr(sub[c], sub.fail_at_3).statistic), 3)
        strata = {}
        sub = M[["q_tool_selection_difficulty", "n_candidates", "fail_at_3"]].dropna()
        for lo, hi in ((4, 5), (6, 9), (10, 20), (21, 999)):
            g = sub[(sub.n_candidates >= lo) & (sub.n_candidates <= hi)]
            if len(g) > 100 and g.fail_at_3.std() > 0 and g.q_tool_selection_difficulty.std() > 0:
                strata[f"{lo}-{hi}"] = {"n": int(len(g)),
                                        "rho": round(float(spearmanr(g.q_tool_selection_difficulty,
                                                                     g.fail_at_3).statistic), 3)}
        resp = {}
        for c in [x for x in num.columns if x.startswith("r_") and x in M and M[x].std() > 0]:
            g = M[[c, "fail_at_3"]].dropna()
            m = g.groupby("fail_at_3")[c].mean()
            if len(m) == 2:
                resp[c] = {"mean_when_gold_reached": round(float(m.get(0, np.nan)), 3),
                           "mean_when_failed": round(float(m.get(1, np.nan)), 3)}
        ov = {}
        for tgt, srcs in (("q_overall_score", QD), ("r_overall_score", ["r_completeness", "r_conciseness"])):
            s = M[[tgt] + [x for x in srcs if x in M]].dropna()
            if len(s) > 100 and tgt in s:
                ov[tgt] = {c: round(float(spearmanr(s[tgt], s[c]).statistic), 3) for c in s.columns if c != tgt}
        res["configs"][cfg] = {"source_rows": int(len(S)), "json_parse_failure_rate": round(parse_fail, 4),
                               "joined_dev_rows": int(len(M)), "distinct_scores": {c: int(num[c].nunique())
                                                                                   for c in num.columns},
                               "zero_variance_items": [c for c in num.columns if num[c].std() == 0],
                               "cronbach_alpha_question_side": a, "k_items": k, "n_alpha_rows": n,
                               "item_total_rho": itm, "criterion_rho_vs_fail_at_3": crit,
                               "difficulty_by_catalogue_stratum": strata, "overall_vs_components": ov,
                               "response_scores_by_objective_outcome": resp}
        for c, v in crit.items():
            per["crit"].append({"cfg": cfg, "item": c, "rho": v})
        print(f"  {cfg}: joined={len(M):5d} alpha={a} crit(difficulty)={crit.get('q_tool_selection_difficulty')} "
              f"strata={[x['rho'] for x in strata.values()]}")
    big = [v for cfg in res["configs"] for v in res["configs"][cfg]["difficulty_by_catalogue_stratum"].values()]
    small = sorted(big, key=lambda x: -x["n"])[:2]
    pooled = [res["configs"][c]["criterion_rho_vs_fail_at_3"].get("q_tool_selection_difficulty", 0) for c in CONFIGS]
    crit_met = {"variability_and_join": all(v["joined_dev_rows"] >= 1000 for v in res["configs"].values()),
                "weak_criterion_validity": max(abs(x) for x in pooled) < 0.15,
                "confound_separable": bool(small) and max(abs(x["rho"]) for x in small) < 0.10}
    res["verdict"] = {
        "pooled_rho_abs_max": max(abs(x) for x in pooled),
        "largest_two_strata_abs_rho_max": max(abs(x["rho"]) for x in small) if small else None,
        "alpha_range": [res["configs"][c]["cronbach_alpha_question_side"] for c in CONFIGS],
        "criteria_met": crit_met,
        "decision": ("PROMOTE T024 to a full study: the shipped scores are weak as a difficulty instrument and "
                     "their apparent relation to routing failure is catalogue size"
                     if all(crit_met.values()) else
                     "criteria not met on the pilot - report the numbers as they are and do not promote")}
    res["wallclock_sec"], res["finished_at"] = round(time.time() - t0, 1), time.strftime("%Y-%m-%dT%H:%M:%S")
    (ROOT / "results_raw").mkdir(exist_ok=True)
    out = ROOT / "results_raw" / f"EXP0039_quality_score_pilot_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    (ROOT / "results_processed").mkdir(exist_ok=True)
    pd.DataFrame(per["crit"]).to_csv(ROOT / "results_processed" / "EXP0039_criterion_validity.csv", index=False)
    print(json.dumps(res["verdict"], ensure_ascii=False)[:500])
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
