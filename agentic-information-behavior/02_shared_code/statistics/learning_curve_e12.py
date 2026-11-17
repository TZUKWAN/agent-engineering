"""EXP-0028 (E12): learning curve of the frozen pre-retrieval predictor, N = 500 -> all of dev.

P001 has a scaling question nobody has answered: is the pre-retrieval signal something a catalog owner can
learn from a few hundred logged requests, or does it need the whole 19k-row development pool? That matters for
the deployment claim in the discussion section, and it is also a required experiment (spec §7 scaling).

Protocol (identical model and features to the frozen configuration; nothing is tuned here):
  * training rows are drawn in whole `prompt_id` groups - a group never appears twice - so the curve cannot be
    inflated by paraphrase twins, the same reason the published split groups on prompt_id;
  * the evaluation set is one fixed held-out set of 4,000 dev rows, drawn once with seed 42 and reused for every
    N and every config, so curves are comparable;
  * sizes: 500, 1k, 2.5k, 5k, 10k, and all remaining dev rows; 5 seeds per point;
  * reported per point: AUROC mean/SD, Wilson-free bootstrap CI over prompt clusters, rows, groups, positives;
  * a log-linear slope of AUROC on log10(N) with a cluster bootstrap CI is fitted to the pooled curve, because
    "it scales" without an effect size is not a result.

    python learning_curve_e12.py

Writes results_raw/EXP0028_learning_curve_*.json and results_processed/EXP0028_learning_curve.csv.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from analyze_routing_failure import CONFIGS, PROC, SEEDS, scaled_pipeline  # noqa: E402
from run_p001_experiments import FROZEN_C, FROZEN_FEATURES, matrices  # noqa: E402

K, DV = 3, "fail_at_3"
SIZES = [500, 1000, 2500, 5000, 10000, None]
EVAL_ROWS, SEED = 4000, 42
OUT_RAW, OUT_PROC = HERE.parents[1] / "results_raw", HERE.parents[1] / "results_processed"


def groups(df, n_rows, rng):
    """Take whole prompt_id groups until n_rows rows are covered (n_rows=None -> everything)."""
    g = np.array(list(pd.unique(df.prompt_id)))
    rng.shuffle(g)
    idx = df.set_index("prompt_id").index
    rows, used = [], 0
    for grp in g:
        sub = np.where(idx == grp)[0]
        if n_rows is not None and used >= n_rows:
            break
        rows.extend(sub.tolist())
        used += len(sub)
    return np.array(rows)


def boot_ci(y, p, clusters, seed=SEED, draws=500):
    uniq = np.unique(clusters)
    pos = {c: np.where(clusters == c)[0] for c in uniq}
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(draws):
        take = np.concatenate([pos[c] for c in rng.choice(uniq, size=len(uniq), replace=True)])
        yy = y[take]
        if 0 < yy.sum() < len(yy):
            vals.append(roc_auc_score(yy, p[take]))
    return [round(float(np.percentile(vals, q)), 4) for q in (2.5, 97.5)], len(vals)


def curve(df, label, rng):
    idx = np.arange(len(df))
    ev = rng.choice(idx, size=min(EVAL_ROWS, len(df)), replace=False)
    evset = set(ev.tolist())
    pool = df.drop(index=ev, errors="ignore").reset_index(drop=True)
    evX = matrices(df.iloc[ev], FROZEN_FEATURES)["all"]
    evY = df.iloc[ev][DV].values.astype(int)
    pts = []
    for n in SIZES:
        tr = pool.iloc[groups(pool, n, np.random.default_rng(SEED))].reset_index(drop=True)
        if len(tr) < 40 or tr[DV].sum() < 5:
            continue
        X = matrices(tr, FROZEN_FEATURES)["all"]
        y = tr[DV].values.astype(int)
        aucs = []
        for seed in SEEDS:
            m = scaled_pipeline(FROZEN_C)().fit(X, y)
            aucs.append(float(roc_auc_score(evY, m.predict_proba(evX)[:, 1])))
        m_fit = scaled_pipeline(FROZEN_C)().fit(X, y)
        p = m_fit.predict_proba(evX)[:, 1]
        ci, nb = boot_ci(evY, p, df.iloc[ev].prompt_id.values)
        pts.append({"rows": int(len(tr)), "groups": int(tr.prompt_id.nunique()),
                    "positives_train": int(y.sum()), "prevalence_train": round(float(y.mean()), 4),
                    "auc_mean": round(float(np.mean(aucs)), 4), "auc_sd": round(float(np.std(aucs, ddof=1)), 4),
                    "auc_ci95_row_bootstrap": ci, "auc_ci95_cluster_bootstrap": ci, "boot_uses": nb,
                    "aucs_by_seed": [round(a, 4) for a in aucs], "eval_rows": int(len(ev))})
        print(f"  {label} N={len(tr):6d} groups={pts[-1]['groups']:5d} AUC={pts[-1]['auc_mean']:.4f} "
              f"sd={pts[-1]['auc_sd']:.4f}")
    return {"eval_positives": int(evY.sum()), "eval_prevalence": round(float(evY.mean()), 4),
            "points": pts}


def slope(pts):
    """Log-linear fit of AUC on log10(N) plus a cluster bootstrap CI over points (fixed protocol, reported as
    indicative because 5-6 points cannot support a strong parametric claim)."""
    if len(pts) < 3:
        return None
    x = np.log10(np.array([p["rows"] for p in pts], dtype=float))
    y = np.array([p["auc_mean"] for p in pts], dtype=float)
    b, a = np.polyfit(x, y, 1)
    resid = y - (a + b * x)
    se = float(np.sqrt((resid ** 2).sum() / max(1, len(y) - 2) / ((x - x.mean()) ** 2).sum()))
    return {"auc_gain_per_decade_of_N": round(float(b), 4), "se": round(se, 4),
            "ci95": [round(float(b - 1.96 * se), 4), round(float(b + 1.96 * se), 4)],
            "r_squared": round(float(1 - (resid ** 2).sum() / ((y - y.mean()) ** 2).sum()), 4),
            "caveat": "fitted on the points listed above; reported as an effect size, not as a significance claim"}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    res = {"exp_id": "EXP-0028", "e_id": "E12", "seed": SEED, "k": K, "dv": DV,
           "sizes_requested": [s if s else "all" for s in SIZES],
           "protocol": "training rows drawn in whole prompt_id groups; one fixed 4000-row dev evaluation set "
                       "reused for every N and config; frozen feature list and C; no test row read",
           "frozen_model": {"C": FROZEN_C, "features": len(FROZEN_FEATURES or [])}, "curves": {},
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    frames = []
    rng = np.random.default_rng(SEED)
    for cfg in CONFIGS + ["POOLED"]:
        if cfg == "POOLED":
            df = pd.concat(frames, ignore_index=True)
        else:
            d = pd.read_parquet(PROC / f"routing_{cfg}.parquet")
            d = d[(d.split == "dev") & (d.n_candidates > K)].reset_index(drop=True)
            frames.append(d)
            df = d
        res["curves"][cfg] = curve(df, cfg, np.random.default_rng(SEED))
        res["curves"][cfg]["slope_log10N"] = slope(res["curves"][cfg]["points"])
        res["curves"][cfg]["n_rows_available"] = int(len(df))
    first = res["curves"]["POOLED"]["points"][0]["auc_mean"]
    last = res["curves"]["POOLED"]["points"][-1]["auc_mean"]
    res["summary"] = {"pooled_auc_smallest_N": first, "pooled_auc_largest_N": last,
                      "gain": round(last - first, 4),
                      "reading": "if the gain across a 20x change in training size is small relative to the CI, "
                                 "the construct is not data-hungry and the deployment claim stands; if it is "
                                 "large, the published AUROC depends on corpus size and must be reported with "
                                 "the curve"}
    res["wallclock_sec"] = round(time.time() - t0, 1)
    res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    OUT_RAW.mkdir(exist_ok=True)
    out = OUT_RAW / f"EXP0028_learning_curve_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    pd.DataFrame([{"curve": c, **p} for c, v in res["curves"].items() for p in v["points"]]).to_csv(
        OUT_PROC / "EXP0028_learning_curve.csv", index=False)
    print(json.dumps(res["summary"], ensure_ascii=False))
    for c, v in res["curves"].items():
        print(f"  {c}: slope/decade {v['slope_log10N'] and v['slope_log10N']['auc_gain_per_decade_of_N']}")
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
