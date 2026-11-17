"""EXP-0085: why did EXP-0084's arm B return AUROC exactly 0.5000 with zero-width intervals?

A bootstrap that never moves across 500 resamples means the score vector has no variation - every row got the same
predicted probability. That is a pipeline signature, not a null result, and it matters beyond arm B: if the frozen
model saturates on this corpus because its features sit far outside the range it was trained on, then the **arm A**
number that now governs P001's external-validation gate may be measuring extrapolation rather than the absence of
signal. So this step measures three things on a small re-run of the same builder:

  1. NaN / inf in the frozen feature matrices, per arm;
  2. the predicted-probability distribution (unique values, spread, share pinned near 0 or 1);
  3. the extrapolation share - how many external rows have at least one frozen feature outside the min/max range
     observed on the Toucan dev rows the model was fitted on.

The verdict it can support is narrow and it is written as such: either arm B's 0.5000 is explained and arm A stands,
or arm A is confounded and the external verdict has to be restated as "not testable with this frozen model on this
pool" rather than "does not transfer".

    python diagnose_toolret_score_collapse.py [--rows 4]
"""
from __future__ import annotations

import argparse, json, pathlib, sys, time

import numpy as np
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "statistics"))
sys.path.insert(0, str(HERE.parent / "trajectory_parser"))
from analyze_routing_failure import CONFIGS, PROC, SEEDS, scaled_pipeline        # noqa: E402
from build_toucan_routing_dataset import BM25, collection_qpp_features, toks     # noqa: E402
from run_p001_experiments import FROZEN_C, FROZEN_FEATURES, matrices             # noqa: E402
import toolret_eval_transfer_e08 as TR                                           # noqa: E402

ROOT = HERE.parents[1]   # repository root (data_audit -> 02_shared_code -> repo)
OUT_RAW = ROOT / "results_raw"


def profile(X, names, src_lo, src_hi, label, out):
    """Saturation and extrapolation profile for one arm's frozen feature matrix."""
    X = np.asarray(X, dtype=float)
    nan = int(np.isnan(X).sum())
    inf = int(np.isposinf(X).sum() + np.isneginf(X).sum())
    with np.errstate(invalid="ignore"):
        outside = ((X < src_lo) | (X > src_hi))
    outside_any = int(np.nansum(outside.any(axis=1)))
    per_feat = []
    for i, nm in enumerate(names):
        col = X[:, i]
        sd = float(np.nanstd(col))
        if sd == 0:
            per_feat.append({"feature": nm, "std": 0.0, "share_below_dev_min": round(float(np.nanmean(col < src_lo[i])), 3),
                             "share_above_dev_max": round(float(np.nanmean(col > src_hi[i])), 3)})
        elif nm in ("n_chars", "n_tokens"):
            per_feat.append({"feature": nm, "std": round(sd, 2),
                             "share_below_dev_min": round(float(np.nanmean(col < src_lo[i])), 3),
                             "share_above_dev_max": round(float(np.nanmean(col > src_hi[i])), 3)})
    out[label] = {"nan_cells": nan, "inf_cells": inf,
                  "rows_with_any_feature_outside_dev_range": outside_any,
                  "n_rows": int(X.shape[0]),
                  "zero_variance_features": per_feat}
    return outside_any


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=4, help="queries per category partition")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    res = {"exp_id": "EXP-0085", "seed": SEEDS[0], "rows_per_category": args.rows,
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "question": "is EXP-0084 arm B's AUROC exactly 0.5 a pipeline artifact, and is arm A affected too?"}

    stat = __import__("collections").Counter()
    corp = TR.load_corpus(stat)
    print(f"  catalogue {len(corp['ids']):,} docs", flush=True)
    # take a few queries from each category so both partitions and both arms are represented
    rows = TR.load_queries(99, SEEDS[0], stat)
    picked, seen = [], {}
    for r in rows:
        c = str(r.get("category") or "")
        if seen.get(c, 0) < args.rows:
            picked.append(r)
            seen[c] = seen.get(c, 0) + 1
    print(f"  picked {len(picked)} rows across categories {seen}", flush=True)
    df = TR.build(picked, corp, stat)
    if not len(df):
        raise SystemExit("ABORT: builder returned no rows - the diagnosis cannot proceed")
    res["rows_built"] = int(len(df))

    src = pd.concat([pd.read_parquet(PROC / f"routing_{c}.parquet") for c in CONFIGS], ignore_index=True)
    src = src[(src.split == "dev") & (src.n_candidates > TR.K)].reset_index(drop=True)
    Xs = np.asarray(matrices(src, FROZEN_FEATURES)["all"], dtype=float)
    names = list(getattr(matrices(src, FROZEN_FEATURES), "keys", lambda: [])()) or []
    src_lo, src_hi = np.nanmin(Xs, axis=0), np.nanmax(Xs, axis=0)
    model = scaled_pipeline(FROZEN_C)().fit(Xs, src[TR.DV].values.astype(int))
    res["source"] = {"n_dev_rows": int(len(src)), "n_features_probed": int(Xs.shape[1])}

    res["arms"] = {}
    for arm in ("query", "instruction"):
        a = TR.arm_frame(df, arm)
        M = matrices(a, FROZEN_FEATURES)["all"]
        names_a = list(M.columns) if hasattr(M, "columns") else [f"f{i}" for i in range(M.shape[1])]
        prof = {}
        profile(M, names_a, src_lo, src_hi, "features", prof)
        p = model.predict_proba(np.asarray(M, dtype=float))[:, 1]
        y = a[TR.DV].values.astype(int)
        from sklearn.metrics import roc_auc_score
        auc = float(roc_auc_score(y, p)) if 0 < y.sum() < len(y) else None
        prof["score_vector"] = {"n_rows": int(len(p)), "unique_values": int(len(np.unique(np.round(p, 12)))),
                                "min": round(float(p.min()), 6), "max": round(float(p.max()), 6),
                                "std": round(float(p.std()), 6),
                                "share_above_0.99": round(float((p > 0.99).mean()), 3),
                                "share_below_0.01": round(float((p < 0.01).mean()), 3),
                                "auroc": round(auc, 4) if auc is not None else None}
        prof["feature_ranges"] = {"mean_n_chars": round(float(a["n_chars"].mean()), 1),
                                  "dev_n_chars_min_max": [float(np.nanmin(src["n_chars"])), float(np.nanmax(src["n_chars"]))]
                                  if "n_chars" in src else None,
                                  "mean_n_candidates": round(float(a["n_candidates"].mean()), 1)}
        res["arms"][arm] = prof
        sv = prof["score_vector"]
        ft = prof["features"]
        uvv, stdv, mnv, mxv = sv["unique_values"], sv["std"], sv["min"], sv["max"]
        s_hi, s_lo, aurocv = sv["share_above_0.99"], sv["share_below_0.01"], sv["auroc"]
        nanc, infl, outc = ft["nan_cells"], ft["inf_cells"], ft["rows_with_any_feature_outside_dev_range"]
        print(f"  {arm:12s} unique={uvv}/{sv['n_rows']} std={stdv} range=[{mnv},{mxv}] "
              f">0.99:{s_hi} <0.01:{s_lo} AUROC={aurocv} | NaN={nanc} inf={infl} "
              f"rows_outside_dev_range={outc}", flush=True)

    q, i = res["arms"]["query"]["score_vector"], res["arms"]["instruction"]["score_vector"]
    res["reading"] = {
        "arm_B_collapse_explained": bool(i["unique_values"] <= 2 or i["std"] == 0.0),
        "arm_A_also_saturated": bool(q["unique_values"] <= 2 or q["std"] == 0.0),
        "arm_A_has_spread_but_extrapolates": bool(q["unique_values"] > 2
                                                  and res["arms"]["query"]["features"]
                                                  ["rows_with_any_feature_outside_dev_range"] > 0),
    }
    res["what_this_changes"] = (
        "if arm_A_also_saturated is true, EXP-0084's below-chance AUROC is an extrapolation artifact and the external "
        "verdict must be restated as not testable with this frozen model on this pool; if arm A has spread, the "
        "negative stands and arm B is a separate, now-explained collapse")
    res["wallclock_sec"] = round(time.time() - t0, 1)
    OUT_RAW.mkdir(parents=True, exist_ok=True)
    fp = OUT_RAW / f"EXP0085_toolret_score_collapse_{time.strftime('%Y%m%dT%H%M%S')}.json"
    fp.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8", newline="")
    print("  reading:", json.dumps(res["reading"]), "| wrote", fp.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
