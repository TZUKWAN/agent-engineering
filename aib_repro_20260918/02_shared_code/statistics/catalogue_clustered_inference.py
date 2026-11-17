"""EXP-0019: correct the headline inference for CATALOGUE clustering (protocol amendment D14).

EXP-0017 found that the dominant dependence structure in this corpus is not the prompt but the
catalogue: rows reuse identical candidate catalogues (design effect up to 4.39, GEE robust standard
errors up to 7.33x the naive ones), and EXP-0018 showed this cannot be removed by re-splitting, because
one connected component of the catalogue-prompt graph contains 86-98% of all rows. All previously
reported confidence intervals cluster on prompt_id, which understates uncertainty for every
catalogue-derived feature.

This run re-computes the three headline development contrasts with a bootstrap that resamples
catalogue fingerprints, and reports each interval next to the prompt_id-clustered version so the size of
the correction is visible rather than buried:

  pre-retrieval model vs length-only baseline
  pre-retrieval model vs post-retrieval quasi-local margin baseline
  pre-retrieval model vs linguistic-features-only model

Out-of-fold predictions are recomputed from the frozen configuration; only the resampling unit changes.

    python catalogue_clustered_inference.py

Outputs results_raw/EXP0019_catalogue_clustered_inference_*.json and
results_processed/EXP0019_inference_correction.csv.
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
from analyze_routing_failure import CONFIGS, PROC, SEEDS, oof_auc, scaled_pipeline  # noqa: E402
from run_p001_experiments import FROZEN_C, FROZEN_FEATURES, matrices  # noqa: E402

K = 3
DV = "fail_at_3"
N_BOOT = 1000
SEED = 42
OUT_RAW = HERE.parents[1] / "results_raw"
OUT_PROC = HERE.parents[1] / "results_processed"


def fingerprint(catalog_json: str) -> str:
    return "|".join(sorted(d["n"] for d in json.loads(catalog_json)))


CONTRASTS = [("pre", "length"), ("pre", "post"), ("pre", "linguistic")]


def cluster_boot(y, probs: dict, clusters: np.ndarray, n_boot: int = N_BOOT):
    """Resample whole clusters; one mean and 95% CI per declared contrast."""
    rng = np.random.default_rng(SEED)
    uniq = np.unique(clusters)
    idx_of = {c: np.where(clusters == c)[0] for c in uniq}
    names = list(probs)
    draws = {f"vs_{a}__{b}": [] for a, b in CONTRASTS}
    ok = 0
    for _ in range(n_boot):
        take = np.concatenate([idx_of[c] for c in rng.choice(uniq, len(uniq), True)])
        yy = y[take]
        if yy.sum() < 5 or yy.sum() == len(yy):
            continue
        au = {n: roc_auc_score(yy, probs[n][take]) for n in names}
        for (a, b) in CONTRASTS:
            draws[f"vs_{a}__{b}"].append(au[a] - au[b])
        ok += 1
    out = {}
    for key, vals in draws.items():
        a, b = key.replace("vs_", "").split("__")
        v = np.array(vals)
        out[key] = {"mean": round(float(v.mean()), 4),
                    "ci95": [round(float(np.percentile(v, q)), 4) for q in (2.5, 97.5)],
                    "excludes_zero": bool((v > 0).all() or (v < 0).all()),
                    "p_two_sided_bootstrap": round(float(2 * min((v <= 0).mean(), (v >= 0).mean())), 5)}
    out["_n_usable_resamples"] = ok
    out["_n_clusters"] = int(len(uniq))
    return out


def main() -> int:
    t0 = time.time()
    per_cfg, rows = {}, []
    for cfg in CONFIGS:
        df = pd.read_parquet(PROC / f"routing_{cfg}.parquet")
        dev = df[(df.split == "dev") & (df.n_candidates > K)].reset_index(drop=True)
        M = matrices(dev, FROZEN_FEATURES)
        y = dev[DV].values.astype(int)
        probs = {}
        for label, block in (("pre", M["all"]), ("length", M["length"]), ("post", M["post"]),
                             ("linguistic", M["linguistic"]), ("qpp", M["qpp"])):
            probs[label] = np.mean([oof_auc(block, y, scaled_pipeline(FROZEN_C), s)[1]
                                    for s in SEEDS], axis=0)
        base_auc = {k: round(float(roc_auc_score(y, v)), 4) for k, v in probs.items()}
        res = {"n_dev": int(len(dev)), "positives": int(y.sum()), "oof_auc": base_auc,
               "bootstrap_prompt_id": cluster_boot(y, probs, dev.prompt_id.values),
               "bootstrap_catalogue": cluster_boot(y, probs, dev.catalog_json.map(fingerprint).values)}
        res["correction"] = {}
        for key in (f"vs_{a}__{b}" for a, b in CONTRASTS):
            p, c = res["bootstrap_prompt_id"][key], res["bootstrap_catalogue"][key]
            w = lambda d: d["ci95"][1] - d["ci95"][0]
            res["correction"][key] = {
                "ci_prompt_id": p["ci95"], "ci_catalogue": c["ci95"],
                "width_prompt_id": round(w(p), 4), "width_catalogue": round(w(c), 4),
                "width_inflation": round(w(c) / max(1e-9, w(p)), 3),
                "still_positive_catalogue": bool(c["mean"] > 0 and c["ci95"][0] > 0),
                "p_catalogue": c["p_two_sided_bootstrap"], "p_prompt_id": p["p_two_sided_bootstrap"]}
            rows.append({"config": cfg, "contrast": key, **res["correction"][key]})
        res["n_distinct_catalogues"] = int(dev.catalog_json.map(fingerprint).nunique())
        per_cfg[cfg] = res
        print(f"[{cfg}] catalogues={res['n_distinct_catalogues']} of {len(dev)} rows")
        for key, v in res["correction"].items():
            print(f"   {key:22s} CI width {v['width_prompt_id']:.4f} -> {v['width_catalogue']:.4f} "
                  f"(x{v['width_inflation']})  positive after correction: {v['still_positive_catalogue']}")

    verdict = {
        "criterion": "a contrast survives only if its catalogue-clustered 95% CI excludes zero",
        "surviving_contrasts_per_config": {
            c: [k for k, v in per_cfg[c]["correction"].items() if v["still_positive_catalogue"]]
            for c in CONFIGS},
        "max_ci_width_inflation": max(float(v["width_inflation"]) for c in per_cfg
                                      for v in per_cfg[c]["correction"].values()),
        "headline_still_survives_everywhere": all(
            per_cfg[c]["correction"]["vs_pre__length"]["still_positive_catalogue"]
            and per_cfg[c]["correction"]["vs_pre__post"]["still_positive_catalogue"] for c in CONFIGS),
        "consequence": "prompt_id clustering understated uncertainty for catalogue-derived features; "
                       "all confidence intervals quoted from this run onward are catalogue-clustered",
        "test_split_read": False, "llm_api_used": False}
    out = {"exp_id": "EXP-0019", "stage": "catalogue_clustered_inference_dev_only", "dv": DV, "k": K,
           "seeds_used": SEEDS, "frozen_model": {"C": FROZEN_C, "n_features": len(FROZEN_FEATURES)},
           "n_bootstrap": N_BOOT, "configs": per_cfg, "verdict": verdict,
           "runtime_sec": round(time.time() - t0, 1),
           "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    p = OUT_RAW / f"EXP0019_catalogue_clustered_inference_{time.strftime('%Y%m%dT%H%M%S')}.json"
    p.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    pd.DataFrame(rows).to_csv(OUT_PROC / "EXP0019_inference_correction.csv", index=False)
    (OUT_PROC / "EXP0019_inference_verdict.json").write_text(json.dumps(verdict, indent=1), encoding="utf-8")
    print("\nverdict:", json.dumps(verdict, indent=1))
    print("wrote", p.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
