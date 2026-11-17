"""EXP-0086 (E08, support-respecting external test): is the external failure a lack of signal, or a saturated model?

EXP-0084 scored the frozen P001 predictor on ToolRet's eval release and got AUROC 0.4671, below the length-only
baseline; EXP-0085 showed why that reading is unsafe - on the probed rows **every** frozen feature set was inside the
dev min/max range for neither arm, and the predicted probability collapsed to a constant 1.0. A logistic that saturates
cannot rank, so "does not transfer" was never demonstrated. This step separates the two explanations with the **same
fitted model and the same frozen features** - nothing is refitted on external data:

  * **arm S1 - in-support subset.** Score only the external rows whose frozen features all lie inside the dev min/max
    range, and report what fraction of the sample that is. Pre-registered decision rule, fixed before any AUROC:
    if the in-support fraction is below 0.25, or the subset has fewer than 30 positives, the correct verdict is
    **"not testable at this pool scale with this feature set"**, not a transfer or non-transfer claim.
  * **arm S2 - saturation-free score.** Take the identical dev-fitted coefficients, drop the link function, and rank by
    the linear predictor `z(X) @ beta`. Ranking does not need calibrated probabilities, so if the information is
    present at all this arm can show it; if it also fails, the deficit is in the features, not in the sigmoid.
  * **mechanism table** - per-feature external min/max/median against the dev range, so the reader can see which
    features leave support rather than being told in prose.

The expensive part (BM25 + corpus QPP over a 44,452-document pool, ~15 s/row) is done once and persisted to
`01_datasets/processed/toolret_eval_features.parquet` so later arms cost nothing.

    python toolret_support_respecting_external.py --rows 300

Outputs results_raw/EXP0086_*_support_respecting_external.json, results_processed/EXP0086_*_per_feature_support.csv
"""
from __future__ import annotations

import argparse, json, pathlib, sys, time
from collections import Counter

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "statistics"))
sys.path.insert(0, str(HERE.parent / "trajectory_parser"))
from analyze_routing_failure import CONFIGS, PROC, SEEDS, scaled_pipeline        # noqa: E402
from run_p001_experiments import FROZEN_C, FROZEN_FEATURES, matrices             # noqa: E402
import toolret_eval_transfer_e08 as TR                                           # noqa: E402

def _repo_root() -> pathlib.Path:
    """Root found by marker directory, not by counting `parents[N]` - four scripts in this programme wrote artefacts
    one level above the repository that way."""
    here = pathlib.Path(__file__).resolve()
    for anc in [here.parent, *here.parents]:
        if (anc / "00_program_registry").is_dir():
            return anc
    raise SystemExit("ABORT: cannot locate the repository root from " + str(here))


ROOT = _repo_root()
OUT_RAW, OUT_PROC = ROOT / "results_raw", ROOT / "results_processed"
CACHE = ROOT / "01_datasets" / "processed" / "toolret_eval_features.parquet"
DV = "fail_at_3"
IN_SUPPORT_MIN_FRACTION = 0.25       # fixed here, before any AUROC is computed
MIN_POSITIVES = 30                    # same standard used by EXP-0021/0044 for an estimable AUROC


def build_or_load(rows_total, seed):
    if CACHE.is_file():
        df = pd.read_parquet(CACHE)
        if len(df) >= 50:
            print(f"  reusing cached external features: {len(df)} rows from {CACHE.name}", flush=True)
            return df, {"cached": True}
    n_sub = len([f for f in TR.QDIR.rglob("*.parquet")])
    per_subset = max(2, int(np.ceil(rows_total / max(1, n_sub))))   # --rows is a TOTAL, not a per-subset cap
    stat = Counter()
    corp = TR.load_corpus(stat)
    picked = TR.load_queries(per_subset, seed, stat)
    t0 = time.time()
    df = TR.build(picked, corp, stat)
    print(f"  built {len(df)} rows ({per_subset}/subset over {n_sub} subsets) in {round(time.time()-t0,1)}s", flush=True)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(CACHE, index=False)
    return df, dict(stat)


def auroc(y, s, rng, draws=500):
    auc = float(roc_auc_score(y, s))
    idx = []
    for _ in range(draws):
        i = rng.integers(0, len(y), size=len(y))
        if 0 < y[i].sum() < len(i):
            idx.append(roc_auc_score(y[i], s[i]))
    ci = [round(float(np.percentile(idx, 2.5)), 4), round(float(np.percentile(idx, 97.5)), 4)] if idx else None
    return auc, ci


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=300)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    res = {"exp_id": "EXP-0086", "e_id": "E08", "seed": SEEDS[0], "dv": DV,
           "rules_fixed_before_any_auroc": {"in_support_min_fraction": IN_SUPPORT_MIN_FRACTION,
                                            "min_positives_for_an_auc": MIN_POSITIVES,
                                            "bands": TR.BANDS,
                                            "model": "identical dev-fitted frozen model and frozen feature set; "
                                                     "nothing refitted, no threshold re-chosen"},
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S")}

    ext_all, stat = build_or_load(args.rows, SEEDS[0])
    ext = ext_all[ext_all.n_candidates > TR.K].reset_index(drop=True)
    # The arm prefix carries the DV (`query_fail_at_3`), so `arm_frame` has to run before anything reads `fail_at_3`.
    # The first version of this line read the bare name off the built frame and raised only after the feature build -
    # 108 minutes of BM25 over a 44,452-document pool - because the build is the expensive part.
    a = TR.arm_frame(ext, "query")
    for col in (DV, "gold_idx", "catalog_json", "n_candidates"):
        if col not in a.columns:
            raise SystemExit(f"ABORT: arm frame has no {col!r} column (columns: {list(a.columns)[:12]})")
    res["sample"] = {"rows_built": int(len(ext_all)), "rows_after_inclusion": int(len(ext)),
                     "fail_at_3_prevalence": round(float(a[DV].mean()), 4),
                     "mean_n_candidates": round(float(ext.n_candidates.mean()), 1)}

    src = pd.concat([pd.read_parquet(PROC / f"routing_{c}.parquet") for c in CONFIGS], ignore_index=True)
    src = src[(src.split == "dev") & (src.n_candidates > TR.K)].reset_index(drop=True)
    Xs = np.asarray(matrices(src, FROZEN_FEATURES)["all"], dtype=float)
    # `all` is the frozen feature block with log catalogue size appended, so the per-feature table needs one name per
    # column of Xs - the frozen list alone is short by exactly that column.
    names = list(matrices(src, FROZEN_FEATURES)["feature_names"]) + ["log_n_candidates"]
    if len(names) != Xs.shape[1]:
        raise SystemExit(f"ABORT: {len(names)} feature names for a {Xs.shape[1]}-column matrix - the frozen block "
                         "gained or lost a column and the per-feature support table would be mislabelled")
    lo, hi = np.nanmin(Xs, axis=0), np.nanmax(Xs, axis=0)
    pipe = scaled_pipeline(FROZEN_C)().fit(Xs, src[DV].values.astype(int))
    # `scaled_pipeline` returns the frozen `Pre` object (median-impute + standardise + logistic as one estimator),
    # not an sklearn Pipeline, so the weights come from its own attributes.
    scaler, beta = pipe.sc, pipe.m.coef_[0]

    X = np.asarray(matrices(a, FROZEN_FEATURES)["all"], dtype=float)
    y = a[DV].values.astype(int)
    # Support is judged on the matrix the frozen model actually sees: `Pre` median-imputes boundary NaNs before
    # standardising, so an imputed cell is inside the dev range by construction and calling it "outside support"
    # would report an artefact of missingness rather than of extrapolation. The raw NaN count is reported next to it.
    Xi = pipe._imp(X)
    n_nan_cells = int((~np.isfinite(X)).sum())
    support = (Xi >= lo - 1e-12) & (Xi <= hi + 1e-12)
    in_row = support.all(axis=1)
    frac = float(in_row.mean())
    res["support"] = {"rows": int(len(X)), "in_support_rows": int(in_row.sum()), "in_support_fraction": round(frac, 4),
                      "positives_in_support": int(y[in_row].sum()),
                      "raw_nan_cells_imputed": n_nan_cells,
                      "mean_features_outside_per_row": round(float((~support).sum(axis=1).mean()), 2)}
    rng = np.random.default_rng(SEEDS[0])

    p = pipe.predict_proba(X)[:, 1]
    lin = scaler.transform(Xi) @ beta                     # same weights, no link function: ranking only
    out_of = (~support)
    per_feat = pd.DataFrame({
        "feature": names,
        "dev_min": lo, "dev_max": hi,
        "external_min": np.nanmin(Xi, axis=0), "external_median": np.median(Xi, axis=0),
        "external_max": np.nanmax(Xi, axis=0),
        "share_rows_outside": out_of.mean(axis=0)})
    per_feat["outside"] = per_feat["share_rows_outside"] > 0
    per_feat.sort_values("share_rows_outside", ascending=False).to_csv(
        OUT_PROC / "EXP0086_per_feature_support.csv", index=False)
    res["features_leaving_support"] = [
        {"feature": r.feature, "share_rows_outside": round(float(r.share_rows_outside), 3),
         "dev_range": [round(float(r.dev_min), 3), round(float(r.dev_max), 3)],
         "external_range": [round(float(r.external_min), 3), round(float(r.external_max), 3)]}
        for r in per_feat[per_feat["share_rows_outside"] > 0].head(8).itertuples()]

    arms = []
    for label, score in (("frozen probability", p), ("linear predictor (no link)", lin)):
        full_auc, full_ci = auroc(y, score, rng)
        est = {"arm": label, "scope": "all in-support rows" if frac >= IN_SUPPORT_MIN_FRACTION else
                                         "not estimable - in-support fraction below the pre-registered floor",
               "auroc_all_rows": round(full_auc, 4), "ci95_all_rows": full_ci,
               "score_unique_values": int(len(np.unique(np.round(score, 12)))),
               "score_constant": bool(len(np.unique(np.round(score, 12))) <= 1)}
        if in_row.sum() >= 20 and MIN_POSITIVES <= y[in_row].sum() <= in_row.sum() - MIN_POSITIVES:
            s_auc, s_ci = auroc(y[in_row], score[in_row], rng)
            est.update({"auroc_in_support": round(s_auc, 4), "ci95_in_support": s_ci,
                        "n_in_support": int(in_row.sum()), "positives_in_support": int(y[in_row].sum())})
        else:
            est.update({"auroc_in_support": None,
                        "why": f"n_in_support={int(in_row.sum())}, positives={int(y[in_row].sum())}; "
                               f"needs >= {MIN_POSITIVES} of each class"})
        arms.append(est)
        print(f"  {label}: AUROC(all)={est['auroc_all_rows']} CI={est['ci95_all_rows']} "
              f"in-support={est.get('auroc_in_support')} constant={est['score_constant']}", flush=True)
    res["arms"] = arms

    prob, linarm = arms[0], arms[1]
    if frac < IN_SUPPORT_MIN_FRACTION or prob["auroc_in_support"] is None:
        verdict = ("NOT TESTABLE at this pool scale with this feature set: the frozen features leave the dev support on "
                   f"{1-frac:.1%} of external rows, so EXP-0084's below-chance AUROC measured extrapolation")
    elif linarm["auroc_all_rows"] >= TR.BANDS["transfers"]:
        verdict = ("SIGNAL PRESENT, link function at fault: the same frozen weights rank external failures at "
                   f"{linarm['auroc_all_rows']} once the sigmoid is removed")
    elif linarm["auroc_all_rows"] < TR.BANDS["partial"]:
        verdict = ("SIGNAL ABSENT: with saturation removed the identical feature set still cannot rank external "
                   f"failures ({linarm['auroc_all_rows']}) - the features themselves do not carry the construct "
                   "outside the training pool")
    else:
        verdict = f"PARTIAL: {linarm['auroc_all_rows']} without a link, against bands {TR.BANDS}"
    res["verdict"] = verdict
    res["saturation_evidence"] = {
        "probability_constant_on_all_rows": prob["score_constant"],
        "probability_unique_values": prob["score_unique_values"],
        "linear_unique_values": linarm["score_unique_values"]}
    res["wallclock_sec"] = round(time.time() - t0, 1)
    OUT_RAW.mkdir(parents=True, exist_ok=True)
    fp = OUT_RAW / f"EXP0086_support_respecting_external_{time.strftime('%Y%m%dT%H%M%S')}.json"
    fp.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8", newline="")
    print("  verdict:", verdict)
    print(f"  wrote {fp.name} in {res['wallclock_sec']}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
