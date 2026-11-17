"""EXP-0046 (P001 E15): what is actually inside the predictor's errors, on dev rows only.

P001 reports AUROC and a learning curve but its error analysis was thin, which is a documented pre-submission item
("larger manual error review"). This classifies every dev error of the frozen model by rule and, critically, applies
the SAME rules to the rows the model got right, so a category only counts as explanatory if it is *enriched* among
errors relative to correct predictions.

Scope discipline: dev rows only, from the published sample; the test split (single evaluation, ledger-enforced) is
never read here. The model is the frozen `all_C0.1` logistic pipeline, scored out-of-fold with GroupKFold on
`prompt_id` so no catalogue leaks between fit and score.

Rule categories, first match wins in exactly this order (frozen before the run). None of them may reference
`bm25_best_rank` or `fail_at_3`: those two define the label, so a category built from them cannot explain the error.
  R1 no_lexical_bridge     no content word of the instruction occurs in any gold tool's own name+description
  R7 tiny_catalogue        n_candidates <= 3 (hit@3 near-vacuous; counted, not assumed to be empty)
  R5 sibling_confusion     >= 3 gold tools and more than one server in the row (competing sub-goals)
  R2 crowded_catalogue     n_candidates > 10
  R3 multi_subtask_long    n_subtasks_by_punctuation >= 3 and n_tokens above the config median
  R4 terse_instruction     n_tokens below the config 10th percentile
  R6 other                 everything else - the residual is reported, not hidden
Each category is computed for false negatives AND for true positives, and reported as a risk ratio, because a
category that is merely common among failures explains nothing: it has to be *more* common among misses.

Schema guard: `catalog_json` on disk stores the short keys the builder writes (n=name, d=description, p=params),
as documented in cross_pipeline_transfer_e08.py. The first version of this script looked up "name"/"desc" instead,
which returned empty token lists for every row; `bridge()` then returned False for every row and the taxonomy
reported 100% of false negatives as "no lexical bridge" - a broken-key artifact. `cat_tokens()` now raises on an
unexpected schema and `check_tokens()` refuses to score a run whose catalogues tokenise to nothing.

    python 02_shared_code/statistics/error_analysis_p001.py
"""
from __future__ import annotations

import json, pathlib, sys, time
from collections import Counter

import numpy as np
import pandas as pd
from scipy.stats import fisher_exact
from sklearn.model_selection import GroupKFold

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "02_shared_code" / "statistics"))
sys.path.insert(0, str(ROOT / "02_shared_code" / "trajectory_parser"))
import run_p001_experiments as R                    # noqa: E402
import build_toucan_routing_dataset as B            # noqa: E402

K = 3
CASES_PER_CELL = 8
# --census re-runs the identical frozen analysis and writes every case instead of a read sample (EXP-0093). The
# rules, thresholds, model and split are untouched, so the census and EXP-0046 must agree cell by cell - which the
# per-group reconciliation below asserts rather than assumes.
CENSUS = "--census" in sys.argv
EXPID = "EXP-0093" if CENSUS else "EXP-0046"
CATS = ["R1 no_lexical_bridge", "R5 sibling_confusion", "R2 crowded_catalogue",
        "R3 multi_subtask_long", "R4 terse_instruction", "R7 tiny_catalogue", "R6 other"]


STOP = {"the", "and", "for", "with", "from", "that", "this", "will", "you", "your", "are", "can",
        "should", "please", "then", "into", "using", "use", "all", "get", "have", "has", "not", "but"}


def tool_field(d, short):
    """Read one catalogue element written with the builder's persisted short keys."""
    if short not in d:
        raise KeyError(f"catalogue element has no '{short}' key; got {sorted(d)}. "
                       "catalog_json persists n/d/p - see the docstring.")
    return d[short]


def cat_tokens(cat):
    """Tokenise a stored catalogue the way the frozen builder does, so ranks here equal ranks in the dataset."""
    return [B.toks(str(tool_field(d, "n")).replace("-", " ").replace("_", " ")) + B.toks(str(tool_field(d, "d")))
            + B.toks(" ".join(tool_field(d, "p")) if isinstance(tool_field(d, "p"), list) else []) for d in cat]


def check_tokens(df, cfg):
    """A comparison is only meaningful if both sides are non-empty and full-shaped (deviations D33 lesson)."""
    toks = [t for c in df.catalog_json.head(200) for t in cat_tokens(json.loads(c))]
    non_empty = sum(1 for t in toks if t)
    if not toks or non_empty == 0:
        raise SystemExit(f"[EXP-0046] ABORT {cfg}: {len(toks)} catalogue element(s) tokenised, "
                         f"{non_empty} non-empty. Tokenisation is broken; every downstream rate would be vacuous.")
    return {"catalogue_elements_sampled": len(toks), "non_empty": non_empty}


def content(toks):
    return {x for x in toks if len(x) > 3 and x not in STOP}


def gold_text_tokens(row):
    cat = json.loads(row.catalog_json)
    out = set()
    for i in json.loads(row.gold_idx):
        d = cat[i] if i < len(cat) else {}
        out |= content(B.toks(str(tool_field(d, "n")).replace("-", " ") + " " + str(tool_field(d, "d"))))
    return out


def has_bridge(row, qtoks):
    """Is there any content-word bridge between the instruction and at least one gold tool's own text?"""
    return bool(gold_text_tokens(row) & qtoks)


def rule_inputs(row, med, p10):
    """Every quantity the rules look at, for one row, computed once.

    EXP-0093 puts these next to the label in the per-row census table so a reader can check any single case without
    re-running anything; having them in one place is also what keeps the label and the evidence from drifting apart.
    """
    qtok = content(B.toks(str(row.question)))
    gt = gold_text_tokens(row)
    return {"n_tokens": int(row.n_tokens), "content_tokens": len(qtok), "bridge_tokens": len(gt & qtok),
            "n_candidates": int(row.n_candidates), "n_gold": len(json.loads(row.gold_idx)),
            "n_servers": int(row.n_servers_in_row), "n_subtasks": int(row.n_subtasks_by_punctuation),
            # unrounded: the comparisons below are against a continuous median/percentile, and rounding a 41.999999
            # to 42.0 would flip which side an integer row-count falls on
            "median_tokens": float(med), "p10_tokens": float(p10)}


def label_from_inputs(i):
    """The frozen first-match order as a pure function of `rule_inputs` - the single implementation of the rules."""
    if i["bridge_tokens"] == 0:
        return "R1 no_lexical_bridge"
    if i["n_candidates"] <= 3:
        return "R7 tiny_catalogue"
    if i["n_gold"] >= 3 and i["n_servers"] > 1:
        return "R5 sibling_confusion"
    if i["n_candidates"] > 10:
        return "R2 crowded_catalogue"
    if i["n_subtasks"] >= 3 and i["n_tokens"] > i["median_tokens"]:
        return "R3 multi_subtask_long"
    if i["n_tokens"] < i["p10_tokens"]:
        return "R4 terse_instruction"
    return "R6 other"


def classify_row(row, med, p10):
    return label_from_inputs(rule_inputs(row, med, p10))


def taxonomy(df):
    med, p10 = float(df.n_tokens.median()), float(df.n_tokens.quantile(.10))
    return Counter(classify_row(r, med, p10) for r in df.itertuples())


def contingency(df):
    """P(fail | bridge) vs P(fail | no bridge), plus the 2x2 that lets a reader judge tautology themselves."""
    nb = 1 - np.asarray([has_bridge(r, content(B.toks(str(q))))
                         for r, q in zip(df.itertuples(), df.question)], dtype=int)   # 1 = no bridge
    fail = df.fail_at_3.values.astype(int)
    tab = [[int(((nb == i) & (fail == j)).sum()) for j in (0, 1)] for i in (0, 1)]
    odds, p = fisher_exact(np.array(tab))
    p_f_nb = tab[1][1] / max(1, sum(tab[1]))
    p_f_b = tab[0][1] / max(1, sum(tab[0]))
    return {"bridge__fail0": tab[0][0], "bridge__fail1": tab[0][1],
            "no_bridge__fail0": tab[1][0], "no_bridge__fail1": tab[1][1],
            "fail_rate_given_no_bridge": round(p_f_nb, 4), "fail_rate_given_bridge": round(p_f_b, 4),
            "risk_difference_pp": round((p_f_nb - p_f_b) * 100, 2),
            "odds_ratio": round(float(odds), 3), "fisher_p": float(f"{p:.3g}"),
            "phi": round(float(np.corrcoef(nb, fail)[0, 1]), 4)}


def enrichment(fn_c, tp_c, n_fn, n_tp):
    """Risk ratio of each category among false negatives vs among correctly-detected failures."""
    out = {}
    for c in CATS:
        a, b = fn_c.get(c, 0), tp_c.get(c, 0)
        pa, pb = a / max(1, n_fn), b / max(1, n_tp)
        out[c] = {"fn_n": a, "fn_rate": round(pa, 4), "tp_n": b, "tp_rate": round(pb, 4),
                  "rr_fn_over_tp": round(pa / pb, 3) if pb > 0 else None,
                  "fisher_p": float(f"{fisher_exact([[a, n_fn - a], [b, n_tp - b]])[1]:.3g}")}
    return out


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    frozen = json.loads((ROOT / "papers/P001_routing_failure_qpp/configs/P001_frozen_model.json")
                        .read_text(encoding="utf-8"))
    fs, C = frozen["model"].split("_C")[0], frozen["C"]
    res = {"exp_id": EXPID, "paper_id": "P001",
           "e_id": "E15_error_analysis_census" if CENSUS else "E15_error_analysis",
           "model": frozen["model"], "scope": "dev rows only; the single-use test split is not read",
           "oof": "GroupKFold(5) grouped by prompt_id",
           "rules": "see CATS / classify_row; no rule may use bm25_best_rank or fail_at_3",
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "configs": {}}
    cases = []
    for cfg in R.CONFIGS:
        dev = R.load(cfg, "dev", K)
        guard = check_tokens(dev, cfg)
        M = R.matrices(dev, R.FROZEN_FEATURES)
        y = dev[R.DV_PRIMARY].values.astype(int)
        proba = np.zeros(len(y))
        for a, b in GroupKFold(n_splits=5).split(M[fs], y, groups=dev.prompt_id.values):
            proba[b] = R.scaled_pipeline(C)().fit(M[fs][a], y[a]).predict_proba(M[fs][b])[:, 1]
        dev = dev.assign(oof_proba=proba, pred_fail=(proba >= 0.5).astype(int))
        fn = dev[(dev.fail_at_3 == 1) & (dev.pred_fail == 0)]      # failed, but predicted safe
        tp = dev[(dev.fail_at_3 == 1) & (dev.pred_fail == 1)]      # failed, and predicted so
        fp = dev[(dev.fail_at_3 == 0) & (dev.pred_fail == 1)]      # reachable, but predicted failure
        tn = dev[(dev.fail_at_3 == 0) & (dev.pred_fail == 0)]
        fn_c, tp_c, fp_c = taxonomy(fn), taxonomy(tp), taxonomy(fp)
        n_neg = int(len(dev) - y.sum())
        res["configs"][cfg] = {
            "tokenisation_guard": guard,
            "dev_rows": int(len(dev)), "positives": int(y.sum()),
            "auroc_oof": round(float(R.roc_auc_score(y, proba)), 4),
            "threshold_0.5": {"TP": int(len(tp)), "FP": int(len(fp)), "FN": int(len(fn)), "TN": int(len(tn)),
                              "recall": round(len(tp) / max(1, int(y.sum())), 4),
                              "specificity": round(1 - len(fp) / max(1, n_neg), 4),
                              "precision": round(len(tp) / max(1, len(tp) + len(fp)), 4),
                              "prevalence_at_0.5": round(len(fp) / max(1, len(dev)), 4)},
            "bridge_contingency_all_dev": contingency(dev),
            "fn_taxonomy": {c: int(fn_c.get(c, 0)) for c in CATS},
            "tp_taxonomy": {c: int(tp_c.get(c, 0)) for c in CATS},
            "fp_taxonomy": {c: int(fp_c.get(c, 0)) for c in CATS},
            "fn_vs_tp_enrichment": enrichment(fn_c, tp_c, len(fn), len(tp))}
        cc = res["configs"][cfg]
        print(f"  {cfg}: dev={cc['dev_rows']} AUROC={cc['auroc_oof']} TP/FP/FN/TN="
              f"{cc['threshold_0.5']['TP']}/{len(fp)}/{len(fn)}/{len(tn)} "
              f"| fail-rate no-bridge {cc['bridge_contingency_all_dev']['fail_rate_given_no_bridge']} "
              f"vs bridge {cc['bridge_contingency_all_dev']['fail_rate_given_bridge']}")
        for sub, kind in ((fn, "FN"), (fp, "FP"), (tp, "TP")):
            if not len(sub):
                continue
            # --census writes one row per error/correct case instead of a read sample, so the taxonomy is no longer
            # something the reader takes on trust: every case carries the inputs the rules looked at.
            s = sub if CENSUS else sub.sample(min(CASES_PER_CELL, len(sub)), random_state=R.SEED)
            med_, p10_ = float(sub.n_tokens.median()), float(sub.n_tokens.quantile(.10))
            n0 = len(cases)
            for r in s.itertuples():
                cat = json.loads(r.catalog_json)
                gl = [i for i in json.loads(r.gold_idx) if i < len(cat)]
                sc = B.BM25().scores(B.toks(str(r.question)), cat_tokens(cat))
                order = [int(i) for i in np.argsort([-float(x) for x in sc])[:3] if i < len(cat)]
                inp = rule_inputs(r, med_, p10_)
                cases.append({"cfg": cfg, "uuid": r.uuid, "kind": kind,
                              "category": label_from_inputs(inp),
                              "n_cand": inp["n_candidates"], "bm25_rank": int(r.bm25_best_rank),
                              "proba": round(float(r.oof_proba), 3), "question": str(r.question)[:220],
                              "gold_tools": [str(tool_field(cat[i], "n"))[:34] for i in gl][:3],
                              "top_retrieved": [str(tool_field(cat[i], "n"))[:34] for i in order],
                              "gold_in_bm25_top10": int(any(i in order for i in gl[:1])) if order else 0,
                              **inp})
            if CENSUS:
                n_written = len(cases) - n0
                if n_written != len(sub):
                    raise SystemExit(f"ABORT: {cfg}/{kind} census wrote {n_written} rows for {len(sub)} cases")
                tkey = f"{kind.lower()}_taxonomy"
                recount = {c: int(Counter(x["category"] for x in cases[n0:]).get(c, 0)) for c in CATS}
                if recount != res["configs"][cfg][tkey]:
                    raise SystemExit(f"ABORT: {cfg}/{kind} per-row labels disagree with the taxonomy counts: "
                                     f"{recount} vs {res['configs'][cfg][tkey]}")
                res.setdefault("census", {})[f"{cfg}:{kind}"] = {"rows": n_written, "labels_reconcile": True,
                                                                "taxonomy_key": tkey}

    if CENSUS:
        # the printed table keeps its size; the census CSV keeps every case
        res["cases_read"] = [c for _cfg in R.CONFIGS for _k in ("FN", "FP", "TP")
                             for c in sorted((x for x in cases if x["cfg"] == _cfg and x["kind"] == _k),
                                             key=lambda x: x["proba"])[:CASES_PER_CELL]]
    else:
        res["cases_read"] = cases
    res["aggregate"] = {k: {c: sum(res["configs"][cfg][f"{k}_taxonomy"][c] for cfg in R.CONFIGS)
                            for c in CATS} for k in ("fn", "tp", "fp")}
    res["wallclock_sec"] = round(time.time() - t0, 1)
    res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    tag = "error_census" if CENSUS else "error_analysis"
    out = ROOT / "results_raw" / f"{EXPID.replace('-', '')}_{tag}_{time.strftime('%Y%m%dT%H%M%S')}.json"

    def default(o):
        return o.item() if isinstance(o, (np.floating, np.integer)) else str(o)

    out.write_text(json.dumps(res, indent=1, ensure_ascii=False, default=default), encoding="utf-8")
    pd.DataFrame(cases).to_csv(ROOT / "results_processed"
                               / (f"{EXPID.replace('-', '')}_{'error_census' if CENSUS else 'read_cases'}.csv"),
                               index=False)
    pd.DataFrame([{"cfg": c, "kind": k, "category": cat, "n": res["configs"][c][f"{k}_taxonomy"][cat]}
                  for c in R.CONFIGS for k in ("fn", "tp", "fp") for cat in CATS]
                 ).to_csv(ROOT / "results_processed" / "EXP0046_error_taxonomy.csv", index=False)
    ct = [{"cfg": c, **res["configs"][c]["bridge_contingency_all_dev"]} for c in R.CONFIGS]
    ct.append({"cfg": "AGGREGATE", **contingency(pd.concat([R.load(c, "dev", K) for c in R.CONFIGS]))})
    pd.DataFrame(ct).to_csv(ROOT / "results_processed" / "EXP0046_bridge_contingency.csv", index=False)
    print(json.dumps(res["aggregate"], ensure_ascii=False)[:600])
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
