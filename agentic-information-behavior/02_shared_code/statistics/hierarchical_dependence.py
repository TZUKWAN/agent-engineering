"""EXP-0017: is the statistical unit independent? ICC, design effect, and a group-aware CV leakage test.

Spec §10.04 forbids treating correlated rows as independent observations. P001 already clusters its
bootstrap on `prompt_id`, but that is only one possible grouping: in this corpus many queries share the
SAME candidate catalog, and a random 5-fold CV then lets the model see the competition structure of a
held-out row through its twins. If the pre-retrieval signal partly comes from memorising catalogues
rather than from query-catalog reachability, a group-aware split would expose it. This script measures
that directly instead of asserting independence.

Groupings examined
  prompt_id            the cluster already used for all bootstrap inference (EXP-0008f)
  subset_name          task/domain label carried by the corpus
  catalog_fingerprint  sha1 of the sorted tool-name list - the row's competitive situation
  gold_stem            name stem of the first gold tool - the answer's "family"

Outputs per grouping: cluster-size distribution, an ANOVA intraclass correlation on the binary outcome,
the resulting design effect DEFF = 1 + (m~ - 1)·ICC and effective sample size, and - the decisive test -
the frozen model's OOF AUROC under GroupKFold versus the published StratifiedKFold.

Also re-estimates the primary association four ways (naive GLM, GLM with domain fixed effects, GEE with
exchangeable working correlation clustered on the catalogue, and a Bayesian logistic mixed model with a
random catalogue intercept where cardinality allows) so a coefficient that survives all four cannot be
called a dependence artifact.

Development split only.

    python hierarchical_dependence.py
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM
from statsmodels.genmod.families import Binomial
import statsmodels.formula.api as smf
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold, StratifiedKFold

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from analyze_routing_failure import CONFIGS, PROC, SEEDS, oof_auc, scaled_pipeline  # noqa: E402
from run_p001_experiments import FROZEN_C, FROZEN_FEATURES, matrices  # noqa: E402

K = 3
DV = "fail_at_3"
OUT_RAW = HERE.parents[1] / "results_raw"
OUT_PROC = HERE.parents[1] / "results_processed"
PREDICTORS = ["qpp_idf_weighted_coverage", "qpp_coverage", "n_tokens"]


def fingerprint(names_json: str) -> str:
    cat = json.loads(names_json)
    return hashlib.sha1("|".join(sorted(d["n"] for d in cat)).encode()).hexdigest()[:16]


def gold_stem(gold_idx_json: str, names_json: str) -> str:
    cat, g = json.loads(names_json), json.loads(gold_idx_json)
    if not g:
        return "none"
    nm = str(cat[g[0]]["n"]).lower()
    parts = [p for p in nm.replace("_", "-").split("-") if not p.isdigit()]
    return "-".join(parts[:max(1, len(parts) - 1)])


def anova_icc(y: np.ndarray, groups: np.ndarray) -> dict:
    """Snedecar/Wilton one-way ANOVA ICC for a binary outcome with unequal cluster sizes."""
    df = pd.DataFrame({"y": y, "g": groups})
    stat = df.groupby("g").y.agg(["size", "mean", "var"])
    n = len(y)
    k = len(stat)
    if k < 2:
        # a one-level grouping carries no between-cluster information at all; report it as
        # degenerate instead of dividing by k-1 and emitting NaN
        return {"n": int(n), "k_groups": int(k), "degenerate": True,
                "mean_cluster": float(n), "median_cluster": float(n), "max_cluster": int(n),
                "share_rows_in_multiples": 1.0, "icc": None, "design_effect": None,
                "effective_n": None}
    m_tilde = n * (1 - (stat["size"] ** 2).sum() / n ** 2) / (k - 1)          # effective cluster size
    p_bar = float(y.mean())
    ssw = float((stat["var"].fillna(0.0) * (stat["size"] - 1)).sum())
    ssb = float((stat["size"] * (stat["mean"] - p_bar) ** 2).sum())
    msw = ssw / max(1.0, n - k)
    msb = ssb / max(1.0, k - 1)
    denom = msb + (m_tilde - 1) * msw
    icc = float((msb - msw) / denom) if (denom > 0 and msw > 0) else 0.0
    icc = max(0.0, min(0.999, icc))
    deff = 1.0 + (m_tilde - 1.0) * icc
    return {"n": int(n), "k_groups": int(k), "mean_cluster": round(float(stat["size"].mean()), 3),
            "median_cluster": float(stat["size"].median()), "max_cluster": int(stat["size"].max()),
            "share_rows_in_multiples": round(float(stat.loc[stat["size"] > 1, "size"].sum() / n), 4),
            "icc": round(icc, 5), "design_effect": round(deff, 3),
            "effective_n": int(round(n / deff)) if deff > 0 else int(n)}


def group_kfold_auc(X, y, groups, C):
    proba = np.zeros(len(y))
    gkf = GroupKFold(n_splits=5)
    for tr, te in gkf.split(X, y, groups):
        m = scaled_pipeline(C)()
        m.fit(X[tr], y[tr])
        proba[te] = m.predict_proba(X[te])[:, 1]
    return float(roc_auc_score(y, proba)), proba


def main() -> int:
    t0 = time.time()
    per_cfg, rows = {}, []
    for cfg in CONFIGS:
        df = pd.read_parquet(PROC / f"routing_{cfg}.parquet")
        dev = df[(df.split == "dev") & (df.n_candidates > K)].reset_index(drop=True)
        dev["catalog_fingerprint"] = dev.catalog_json.map(fingerprint)
        dev["gold_stem"] = [gold_stem(g, c) for g, c in zip(dev.gold_idx, dev.catalog_json)]
        y = dev[DV].values.astype(int)
        X = matrices(dev, FROZEN_FEATURES)["all"]
        res = {"groups": {}, "auc": {}}
        for g in ("prompt_id", "subset_name", "catalog_fingerprint", "gold_stem"):
            grp = dev[g].astype(str).values
            st = anova_icc(y, grp)
            st["distinct"] = int(dev[g].nunique())
            res["groups"][g] = st
            if st.get("degenerate"):
                print(f"[{cfg}] {g:20s} k=1 DEGENERATE: this field has a single level inside the "
                      f"corpus, so no clustering statistic exists")
            else:
                print(f"[{cfg}] {g:20s} k={st['k_groups']:6d} m~={st['mean_cluster']:5.2f} "
                      f"ICC={st['icc']:.4f} DEFF={st['design_effect']:.2f} n_eff={st['effective_n']}")
        # the decisive leakage test: does grouping the CV change the published AUROC?
        strat = np.mean([oof_auc(X, y, scaled_pipeline(FROZEN_C), s)[0] for s in SEEDS])
        fps = dev.catalog_fingerprint.values
        pids = dev.prompt_id.values
        res["auc"]["stratified_5fold_published"] = round(float(strat), 4)
        stem = dev.gold_stem.astype(str).values
        for label, groups in (("groupkfold_catalog", fps), ("groupkfold_prompt", pids),
                             ("groupkfold_gold_stem", stem),
                             ("groupkfold_catalog_AND_gold_stem",
                              np.char.add(np.char.add(fps.astype(str), "|"), stem.astype(str)))):
            # GroupKFold is deterministic; jittering the labels would make every group a singleton and
            # silently turn this back into a random split, which is exactly the thing being tested.
            a, _ = group_kfold_auc(X, y, groups, FROZEN_C)
            res["auc"][label] = round(float(a), 4)
            res["auc"][label + "_delta"] = round(float(a - strat), 4)
            print(f"[{cfg}] AUC {label:20s} {res['auc'][label]:.4f} (Δ {res['auc'][label+'_delta']:+.4f})")
        res["auc"]["groupkfold_same_catalog_as_test"] = int(pd.Series(fps).duplicated().sum())
        # coefficient stability across four estimators
        d = dev.copy()
        # in-fold imputation belongs to the classifier, but these are single-shot regressions, so the
        # boundary NaNs documented in D4 are median-filled here and the count is reported
        res["nan_cells_filled"] = int(sum(int(d[c].isna().sum()) for c in PREDICTORS))
        for p in PREDICTORS:
            d[p] = d[p].astype(float)
            d[p] = d[p].fillna(d[p].median())
            d[p + "_z"] = (d[p] - d[p].mean()) / (d[p].std(ddof=0) + 1e-12)
        d["log_size_z"] = ((np.log(d.n_candidates) - np.log(d.n_candidates).mean())
                           / (np.log(d.n_candidates).std(ddof=0) + 1e-12))
        dv = d[PREDICTORS[0] + "_z"] + d[PREDICTORS[1] + "_z"] + d["n_tokens_z"] + d["log_size_z"]
        Z = sm.add_constant(dv.values)
        naive = sm.GLM(y, Z, family=Binomial()).fit()
        dom_dummies = pd.get_dummies(d.gold_stem, prefix="fam", drop_first=True).astype(float).values
        # subset_name has exactly ONE level inside a config (measured), so the domain fixed effects
        # that the research plan specified are not estimable within a corpus; the answer-family
        # dummies are the non-degenerate blocking factor and are used instead, and that substitution
        # is reported rather than hidden.
        dom = sm.GLM(y, np.column_stack([Z, dom_dummies]), family=Binomial()).fit()
        gee = sm.GEE(y, Z, groups=fps, family=Binomial(), cov_struct=sm.cov_struct.Exchangeable()).fit()
        sub = d.groupby("catalog_fingerprint").filter(lambda g: len(g) >= 5)
        mix = None
        if len(sub) >= 300 and sub.catalog_fingerprint.nunique() >= 5 and int(sub[DV].sum()) >= 20:
            f = smf.glm(f"{DV} ~ {PREDICTORS[0]}_z + {PREDICTORS[1]}_z + n_tokens_z + log_size_z",
                        data=sub, family=Binomial())
            form = (f"{DV} ~ {PREDICTORS[0]}_z + {PREDICTORS[1]}_z + n_tokens_z + log_size_z")
            md = sub.assign(g=pd.Categorical(sub.catalog_fingerprint).codes)
            mix = BinomialBayesMixedGLM.from_formula(form, {"catalog": "1 + g - 1"}, md).fit_vb()
        res["coefficients"] = {
            "predictors": PREDICTORS + ["log_size"],
            "naive_glm": [round(float(v), 4) for v in naive.params[1:]],
            "naive_glm_se": [round(float(v), 4) for v in naive.bse[1:]],
            "fixed_effects_block": "gold_stem (subset_name is constant within a config)",
            "domain_fixed_effects": [round(float(v), 4) for v in dom.params[1:5]],
            "gee_exchangeable_by_catalog": [round(float(v), 4) for v in gee.params[1:]],
            "gee_robust_se": [round(float(v), 4) for v in gee.bse[1:]],
            "se_inflation_gee_over_naive": [round(float(a / b), 3) for a, b in zip(gee.bse[1:], naive.bse[1:])],
            "mixed_glm_random_catalog": (None if mix is None else
                                         [round(float(v), 4) for v in mix.fe_mean[1:]]),
            "mixed_glm_sd": (None if mix is None else [round(float(v), 4) for v in mix.fe_sd[1:]]),
            "n_rows_for_mixed": int(len(sub)) if mix is not None else None}
        for k_, v in res["groups"].items():
            for kk, vv in v.items():
                rows.append({"config": cfg, "block": f"group_{k_}", "stat": kk, "value": vv})
        for kk, vv in res["auc"].items():
            rows.append({"config": cfg, "block": "auc", "stat": kk, "value": vv})
        per_cfg[cfg] = res

    # k==1 groupings report design_effect=None (no between-cluster information), so they must be
    # skipped rather than compared against floats
    deffs = [r["design_effect"] for c in per_cfg for r in per_cfg[c]["groups"].values()
             if r.get("design_effect") is not None]
    max_deff = max(deffs)
    deltas = [v for c in per_cfg for k, v in per_cfg[c]["auc"].items()
              if k.endswith("_delta") and v is not None]
    worst_delta = min(deltas) if deltas else 0.0
    verdict = {
        "max_design_effect": max_deff,
        "criterion": "if ANY group-aware CV lowers AUROC by more than 0.02 versus the published stratified split, catalogue/prompt memorisation contributed materially to the headline number",
        "worst_groupkfold_auc_delta_vs_published": worst_delta,
        "leakage_concern_confirmed": bool(worst_delta < -0.02),
        "independence_note": "bootstrap inference already clusters on prompt_id; this run adds the "
                             "catalogue-level design effect and a catalogue-grouped CV, which is the "
                             "stronger dependence structure in this corpus",
        "gee_se_inflation_max": max(float(max(per_cfg[c]["coefficients"]["se_inflation_gee_over_naive"]))
                                    for c in per_cfg),
        "test_split_read": False, "llm_api_used": False}
    out = {"exp_id": "EXP-0017", "stage": "hierarchical_dependence_dev_only", "k": K, "dv": DV,
           "frozen_model": {"feature_set": "all", "C": FROZEN_C}, "configs": per_cfg,
           "verdict": verdict, "runtime_sec": round(time.time() - t0, 1),
           "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    p = OUT_RAW / f"EXP0017_hierarchical_dependence_{time.strftime('%Y%m%dT%H%M%S')}.json"
    p.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    pd.DataFrame(rows).to_csv(OUT_PROC / "EXP0017_dependence_table.csv", index=False)
    (OUT_PROC / "EXP0017_dependence_verdict.json").write_text(json.dumps(verdict, indent=1), encoding="utf-8")
    print("\nverdict:", json.dumps(verdict, indent=1))
    print("wrote", p.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
