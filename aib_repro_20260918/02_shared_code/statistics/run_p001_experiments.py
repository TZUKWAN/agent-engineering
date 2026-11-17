"""P001 main experiment driver (E05/E06/E11/E14 on dev, then a single gated test evaluation).

Freeze compliance notes
-----------------------
* Hyperparameter search is limited to the CLASSIFIER penalty C and the feature-set choice.
  The BM25 parameters (k1=1.4, b=0.4) are NOT searched: the dependent variable is defined as
  "the frozen ranker misses the gold tool", so tuning the ranker to move the metric would be
  circular. Ranker variation is therefore reported under E11 robustness (alternative ranker =
  description-only BM25, already stored) rather than as tuning. Logged as D8 in deviations.md.
* The test split is evaluated by `--stage test` at most once. A ledger file records every
  test evaluation with timestamp and config hash; a second invocation refuses to run unless
  --override-reason is supplied, mirroring the spec's leaderboard-submission discipline
  (T01.02 / §12 "严禁根据 final test set 反复修改方法").
* Bootstrap inference clusters on prompt_id, because EXP-0008f measured that 4.5-9.4% of
  prompt_ids recur across configs and up to 3 rows share one prompt_id inside a config.

    python run_p001_experiments.py --stage dev-select
    python run_p001_experiments.py --stage robust
    python run_p001_experiments.py --stage test --override-reason "<why>"   # gated

Outputs results_raw/EXP0010..12_*.json plus results_processed/ tables.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, roc_auc_score

HERE = Path(__file__).resolve().parent
import itertools
sys.path.insert(0, str(HERE))
from analyze_routing_failure import (CONFIGS, FEATURE_COLS, LINGUISTIC_COLS, QPP_COLS, SEEDS,  # noqa: E402
                                     PROC, ROOT, holm, oof_auc, scaled_pipeline, univariate_or)

SEED = 42
PAPER_DIR = ROOT / "papers" / "P001_routing_failure_qpp"
LEDGER = PAPER_DIR / "test_eval_ledger.json"
DV_PRIMARY = "fail_at_3"


def _frozen_c():
    f = PAPER_DIR / "configs" / "P001_frozen_model.json"
    return json.loads(f.read_text(encoding='utf-8'))["C"] if f.exists() else 1.0


FROZEN_C = _frozen_c()


def _frozen_features():
    f = PAPER_DIR / "configs" / "P001_frozen_model.json"
    return json.loads(f.read_text(encoding="utf-8")).get("canonical_features") or None


FROZEN_FEATURES = _frozen_features()
K_PRIMARY = 3


def load(cfg: str, split: str, k: int) -> pd.DataFrame:
    df = pd.read_parquet(PROC / f"routing_{cfg}.parquet")
    df = df[(df.split == split) & (df.n_candidates > k)].copy()
    return df


def matrices(df: pd.DataFrame, canonical: list[str] | None = None):
    """Build feature blocks. `canonical`, when given, is THE frozen column list.

    Without it every call dropped columns that were constant or all-NaN in that particular
    frame, so a pooled-train / single-config-test comparison silently used different
    feature counts (33 vs 32) and crashed, and per-config dev fits could differ in columns.
    The list is now decided on dev once and reused everywhere; absent columns become NaN and
    are imputed inside each training fold.
    """
    if canonical is not None:
        X = df.reindex(columns=canonical).astype(float).values
        names = list(canonical)
    else:
        feats = [c for c in FEATURE_COLS if c in df.columns]
        Xall = df[feats].astype(float).values
        keep = (np.nanstd(Xall, axis=0) > 0) & (~np.all(~np.isfinite(Xall), axis=0))
        names = [feats[i] for i, kk in enumerate(keep) if kk]
        X = Xall[:, keep]
    size = np.log(df.n_candidates.values.astype(float))
    all_X = np.column_stack([X, size])
    qpp = np.column_stack([df[[c for c in QPP_COLS if c in df.columns]].astype(float).values, size])
    ling = np.column_stack([df[[c for c in LINGUISTIC_COLS if c in df.columns]].astype(float).values, size])
    post = df[["bm25_margin", "bm25_top1_score"]].astype(float).values
    length = df[["n_tokens"]].astype(float).values
    return {"all": all_X, "qpp": qpp, "linguistic": ling, "post": post, "length": length,
            "feature_names": names}


def cluster_boot_auc(y, proba, clusters, boot=2000, seed=SEED, alpha=0.05):
    """Cluster bootstrap over prompt_id groups; also gives a paired diff CI when passed a second score."""
    rng = np.random.default_rng(seed)
    groups = pd.unique(clusters)
    idx_of = {g: np.where(clusters == g)[0] for g in groups}
    out = []
    for _ in range(boot):
        take = np.concatenate([idx_of[g] for g in rng.choice(groups, size=len(groups), replace=True)])
        yy = y[take]
        if yy.sum() == 0 or yy.sum() == len(yy):
            continue
        out.append(roc_auc_score(yy, proba[take]))
    lo, hi = np.percentile(out, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(np.mean(out)), float(lo), float(hi), len(out)


def paired_boot(y, p_a, p_b, clusters, boot=1000, seed=SEED):
    """Bootstrap AUC(A) - AUC(B) with clusters resampled jointly."""
    rng = np.random.default_rng(seed)
    groups = pd.unique(clusters)
    idx_of = {g: np.where(clusters == g)[0] for g in groups}
    d = []
    for _ in range(boot):
        take = np.concatenate([idx_of[g] for g in rng.choice(groups, size=len(groups), replace=True)])
        yy = y[take]
        if yy.sum() == 0 or yy.sum() == len(yy):
            continue
        d.append(roc_auc_score(yy, p_a[take]) - roc_auc_score(yy, p_b[take]))
    d = np.asarray(d)
    obs = roc_auc_score(y, p_a) - roc_auc_score(y, p_b)
    p_two = 2 * min((d <= 0).mean(), (d >= 0).mean())
    return {"observed_delta_auc": round(float(obs), 4),
            "ci95": [round(float(np.percentile(d, 2.5)), 4), round(float(np.percentile(d, 97.5)), 4)],
            "p_two_sided_cluster_bootstrap": round(float(p_two), 6), "n_valid_resamples": int(len(d)),
            "boot_requested": boot}


def oof_proba(X, y, C, seed):
    """Out-of-fold probabilities from the same recipe as oof_auc, returned for inference."""
    from sklearn.model_selection import StratifiedKFold
    proba = np.zeros(len(y))
    for tr, te in StratifiedKFold(n_splits=5, shuffle=True, random_state=seed).split(X, y):
        m = scaled_pipeline(C)()
        m.fit(X[tr], y[tr])
        proba[te] = m.predict_proba(X[te])[:, 1]
    return proba


def stage_dev_select(args) -> dict:
    out = {"exp_id": "EXP-0010", "stage": "dev hyperparameter / feature-set selection",
           "dv": DV_PRIMARY, "seeds": SEEDS[:args.repeats], "search_space": {"C": [0.1, 1.0, 10.0],
           "feature_set": ["all", "qpp", "linguistic"]}, "grid": {}, "selected": {}}
    canonical_per_cfg = {}
    for cfg in CONFIGS:
        dev = load(cfg, "dev", K_PRIMARY)
        canonical_per_cfg[cfg] = matrices(dev)["feature_names"]
    canonical = sorted(set.intersection(*(set(v) for v in canonical_per_cfg.values())))
    out["canonical_features"] = canonical
    out["feature_differences_between_configs"] = {
        f"{a}|{b}": sorted(set(canonical_per_cfg[a]) ^ set(canonical_per_cfg[b]))
        for a, b in itertools.combinations(canonical_per_cfg, 2)}
    print(f"canonical feature set (dev intersection): {len(canonical)} columns")
    for cfg in CONFIGS:
        dev = load(cfg, "dev", K_PRIMARY)
        y = dev[VARIANT_DV].values.astype(int)
        grid = {}
        Mc = matrices(dev, canonical)
        for fs in ("all", "qpp", "linguistic"):
            for C in (0.1, 1.0, 10.0):
                aucs = [oof_auc(Mc[fs], y, scaled_pipeline(C), s)[0] for s in SEEDS[:args.repeats]]
                grid[f"{fs}_C{C}"] = {"mean": round(float(np.mean(aucs)), 4),
                                      "std": round(float(np.std(aucs, ddof=1)), 4) if len(aucs) > 1 else None,
                                      "per_seed": [round(a, 4) for a in aucs]}
        best = max(grid, key=lambda k: grid[k]["mean"])
        out["grid"][cfg] = grid
        out["selected"][cfg] = {"config": best, "dev_auc": grid[best]["mean"], "n": int(len(dev))}
        print(f"[{cfg}] best on dev = {best} AUC={grid[best]['mean']} (n={len(dev)})")
        print("   " + "  ".join(f"{k}:{v['mean']:.4f}" for k, v in sorted(grid.items(), key=lambda kv: -kv[1]['mean'])))
    # A single global configuration is frozen, not one per config: picking the per-config winner
    # would be best-config selection across datasets, which the spec forbids reporting as the model.
    keys = sorted({k for g in out["grid"].values() for k in g})
    glob = {k: float(np.mean([out["grid"][c][k]["mean"] for c in out["grid"]])) for k in keys}
    win = max(glob, key=lambda k: glob[k])
    out["global_mean_dev_auc"] = {k: round(v, 4) for k, v in sorted(glob.items(), key=lambda kv: -kv[1])}
    out["frozen_global"] = {"config": win, "dev_auc_mean_over_configs": round(glob[win], 4),
                            "rule": "max mean dev AUROC(fail@3) across the three configs, 5 seeds"}
    cfgdir = PAPER_DIR / "configs"
    cfgdir.mkdir(parents=True, exist_ok=True)
    (cfgdir / "P001_frozen_model.json").write_text(json.dumps(
        {"frozen_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "selection_source": "EXP-0010 dev grid",
         "model": win, "feature_set": win.split("_C")[0], "C": float(win.split("_C")[1]),
         "dv": DV_PRIMARY, "k": K_PRIMARY, "seeds": SEEDS[:args.repeats],
         "canonical_features": canonical,
         "note": "BM25 k1/b deliberately NOT tuned; see deviations.md D8"}, indent=1, ensure_ascii=False),
        encoding="utf-8")
    print(f"\nFROZEN GLOBAL MODEL: {win} (mean dev AUC {glob[win]:.4f})")
    return out


VARIANT_DV = DV_PRIMARY   # module-level so helpers see the active DV


def stage_robust(args) -> dict:
    """E05 alternative operationalizations + E11 robustness + E14 inference, all on dev."""
    out = {"exp_id": "EXP-0011", "stage": "dev robustness / inference", "selected_model": "all_C1.0",
           "configs": {}}
    can = FROZEN_FEATURES or None
    for cfg in CONFIGS:
        dev = load(cfg, "dev", K_PRIMARY)
        M = matrices(dev, can)
        res = {"n": int(len(dev))}
        # E05: alternative dependent variables
        dvs = {}
        for dv in ("fail_at_1", "fail_at_3", "fail_at_5"):
            yy = dev[dv].values.astype(int)
            if yy.sum() < 20:
                dvs[dv] = {"skipped": f"only {yy.sum()} positives"}
                continue
            a = [oof_auc(M["all"], yy, scaled_pipeline(FROZEN_C), s)[0] for s in SEEDS[:args.repeats]]
            dvs[dv] = {"positives": int(yy.sum()), "prevalence": round(float(yy.mean()), 4),
                       "auc": round(float(np.mean(a)), 4)}
        yy = dev["norm_rank"].values
        _, _p = oof_auc(M["all"], dev[VARIANT_DV].values.astype(int), scaled_pipeline(0.1), SEEDS[0])
        rho, prho = stats.spearmanr(dev["norm_rank"].values, _p)
        dvs["norm_rank_vs_predicted_prob_spearman"] = {"rho": round(float(rho), 4),
                                                       "p": float(prho),
                                                       "note": "alternative continuous DV: does the "
                                                               "predicted risk track ordinal best-rank?"}
        res["E05_alternative_dv"] = dvs
        # E05b: alternative coverage operationalizations (single-feature AUCs)
        alt = {}
        for col in ("qpp_coverage", "qpp_idf_weighted_coverage", "qpp_clarity_meanmax",
                    "qpp_ecle", "qpp_missing_term_n", "n_tokens"):
            x = dev[col].astype(float).values
            ok = np.isfinite(x)
            if ok.sum() < 100 or np.nanstd(x) == 0:
                continue
            sgn = -1.0 if col == "qpp_missing_term_n" else 1.0
            alt[col] = round(float(roc_auc_score(dev[VARIANT_DV].values[ok].astype(int), sgn * x[ok])), 4)
        res["E05b_single_feature_auc"] = alt
        # E05c: univariate odds ratios with Holm correction - the mechanism-readable table.
        # Single-predictor fits are used because the joint model is ill-conditioned on this
        # feature set (EXP-0005 hit LinAlgError: Singular matrix), and per-feature ORs are the
        # quantity a reviewer can actually interpret alongside the ablation.
        uni = {}
        for col in [c for c in (can or feats) if c in dev.columns]:
            v = univariate_or(dev[col].astype(float).values, yy)
            if v.get("p") is not None:
                uni[col] = v
        padd = holm({k: v["p"] for k, v in uni.items()})
        for k, v in uni.items():
            v["p_holm"] = round(padd[k], 6)
            v["sig_holm_005"] = bool(padd[k] < 0.05)
        res["E05c_univariate_OR_holm"] = uni
        # E11: alternative ranker (description-only BM25 already materialised) + noise + subsampling
        yy = dev[VARIANT_DV].values.astype(int)
        alt_rank = dev.assign(f=(dev["bm25_desc_best_rank"] > K_PRIMARY).astype(int))["f"].values.astype(int)
        a_alt = [oof_auc(M["all"], alt_rank, scaled_pipeline(FROZEN_C), s)[0] for s in SEEDS[:2]]
        rng = np.random.default_rng(SEED)
        flip = yy.copy()
        idx = rng.choice(len(yy), size=int(0.05 * len(yy)), replace=False)
        flip[idx] = 1 - flip[idx]
        a_noise = [oof_auc(M["all"], flip, scaled_pipeline(FROZEN_C), s)[0] for s in SEEDS[:2]]
        sub = dev.sample(frac=0.5, random_state=SEED)
        Ms = matrices(sub, can)
        a_sub = [oof_auc(Ms["all"], sub[VARIANT_DV].values.astype(int), scaled_pipeline(FROZEN_C), s)[0]
                 for s in SEEDS[:2]]
        res["E11_robustness"] = {
            "auc_desc_only_ranker_dv": round(float(np.mean(a_alt)), 4),
            "auc_with_5pct_label_noise": round(float(np.mean(a_noise)), 4),
            "auc_50pct_subsample": round(float(np.mean(a_sub)), 4),
            "auc_desc_vs_full_dv_overlap": round(float(np.mean([
                100 * np.mean((alt_rank == 1) & (yy == 1)) / max(1, np.mean(yy == 1))])), 2)}
        # E14: cluster-bootstrap inference for the two headline contrasts
        p_all = oof_proba(M["all"], yy, 1.0, SEEDS[0])
        p_len = oof_proba(M["length"], yy, 1e6, SEEDS[0])
        p_post = oof_auc(M["post"], yy, scaled_pipeline(FROZEN_C), SEEDS[0])[1]
        clusters = dev["prompt_id"].values.astype(str)
        m, lo, hi, nv = cluster_boot_auc(yy, p_all, clusters)
        res["E14"] = {
            "auc_preretrieval": {"point": round(float(roc_auc_score(yy, p_all)), 4),
                                 "cluster_boot_mean": round(m, 4), "ci95": [round(lo, 4), round(hi, 4)],
                                 "n_valid_resamples": nv},
            "ap_preretrieval": round(float(average_precision_score(yy, p_all)), 4),
            "delta_vs_B0_length": paired_boot(yy, p_all, p_len, clusters),
            "delta_vs_B1_post_margin": paired_boot(yy, p_all, p_post, clusters),
            "n_clusters": int(pd.Series(clusters).nunique()),
            "brier": round(float(np.mean((p_all - yy) ** 2)), 5)}
        out["configs"][cfg] = res
        print(f"[{cfg}] E14 delta vs length {res['E14']['delta_vs_B0_length']['observed_delta_auc']} "
              f"(p={res['E14']['delta_vs_B0_length']['p_two_sided_cluster_bootstrap']}), "
              f"vs post {res['E14']['delta_vs_B1_post_margin']['observed_delta_auc']} "
              f"(p={res['E14']['delta_vs_B1_post_margin']['p_two_sided_cluster_bootstrap']})")
        print(f"   E05 dvs: {dvs}")
        print(f"   E11: {res['E11_robustness']}")
    return out


def stage_test(args) -> dict:
    if LEDGER.exists():
        led = json.loads(LEDGER.read_text(encoding="utf-8"))
        if led.get("evaluations") and not args.override_reason:
            print("REFUSED: test split already evaluated. Ledger:\n"
                  + json.dumps(led, indent=1, ensure_ascii=False))
            print("Re-run with --override-reason '<why>' and record it in deviations.md.")
            return {"exp_id": "EXP-0012", "refused": True, "ledger": led}
    else:
        led = {"evaluations": []}
    src = sorted((ROOT / "results_raw").glob("EXP0010_dev_selection_*.json"))
    if not src:
        return {"exp_id": "EXP-0012", "error": "run --stage dev-select before --stage test"}
    sel = json.loads(src[-1].read_text(encoding="utf-8"))
    frozen = json.loads((PAPER_DIR / "configs" / "P001_frozen_model.json").read_text(encoding="utf-8"))
    chosen, C = frozen["model"], frozen["C"]
    fs = chosen.split("_C")[0]
    print(f"using frozen global model: {chosen} (feature set {fs}, C={C}, "
          f"{len(FROZEN_FEATURES)} canonical features)")
    out = {"exp_id": "EXP-0012", "stage": "FINAL TEST (single evaluation)", "dv": DV_PRIMARY,
           "frozen_model": frozen, "per_config_dev_best_not_used": sel["selected"], "configs": {}}
    frames = []
    for cfg in CONFIGS:
        te = load(cfg, "test", K_PRIMARY)
        y = te[DV_PRIMARY].values.astype(int)
        M = matrices(te, FROZEN_FEATURES)
        aucs = [oof_auc(M[fs], y, scaled_pipeline(C), s)[0] for s in SEEDS[:args.repeats]]
        aucs_len = [oof_auc(M["length"], y, scaled_pipeline(1e6), s)[0] for s in SEEDS[:args.repeats]]
        aucs_post = [oof_auc(M["post"], y, scaled_pipeline(FROZEN_C), s)[0] for s in SEEDS[:args.repeats]]
        out["configs"][cfg] = {"n_test_informative": int(len(te)), "positives": int(y.sum()),
                               "prevalence": round(float(y.mean()), 4),
                               "auc_pre": {"mean": round(float(np.mean(aucs)), 4),
                                           "std": round(float(np.std(aucs, ddof=1)), 4),
                                           "per_seed": [round(a, 4) for a in aucs]},
                               "auc_B0_length": round(float(np.mean(aucs_len)), 4),
                               "auc_B1_post_margin": round(float(np.mean(aucs_post)), 4),
                               "leave_one_config_out": None}
        frames.append(te.assign(cfg=cfg))
        print(f"[TEST {cfg}] n={len(te)} pos={y.sum()} AUC pre={out['configs'][cfg]['auc_pre']['mean']} "
              f"±{out['configs'][cfg]['auc_pre']['std']} | length={out['configs'][cfg]['auc_B0_length']} "
              f"| post={out['configs'][cfg]['auc_B1_post_margin']}")
    # E09 cross-teacher: train on two configs, test on the third (still test-split only)
    pool = pd.concat(frames, ignore_index=True)
    for held in CONFIGS:
        tr = pool[pool.cfg != held]
        ts = pool[pool.cfg == held]
        Mtr, Mts = matrices(tr, FROZEN_FEATURES), matrices(ts, FROZEN_FEATURES)
        ytr, yts = tr[DV_PRIMARY].values.astype(int), ts[DV_PRIMARY].values.astype(int)
        m = scaled_pipeline(FROZEN_C)()
        m.fit(Mtr["all"], ytr)
        p = m.predict_proba(Mts["all"])[:, 1]
        out["leave_config_out_auc"] = out.get("leave_config_out_auc", {})
        out["leave_config_out_auc"][held] = round(float(roc_auc_score(yts, p)), 4)
        print(f"[TEST leave-one-config-out -> {held}] AUC={out['leave_config_out_auc'][held]}")
    out["config_hash"] = hashlib.sha256(json.dumps({"sel": sel["selected"],
                                                    "seeds": SEEDS[:args.repeats]}, sort_keys=True,
                                                   ensure_ascii=False).encode()).hexdigest()[:16]
    led["evaluations"].append({"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "config_hash": out["config_hash"],
                               "override_reason": args.override_reason or None})
    LEDGER.write_text(json.dumps(led, indent=1, ensure_ascii=False), encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["dev-select", "robust", "test"])
    ap.add_argument("--repeats", type=int, default=5)
    ap.add_argument("--override-reason", default=None)
    args = ap.parse_args()
    t0 = time.time()
    if args.stage == "dev-select":
        res = stage_dev_select(args)
        name = "EXP0010_dev_selection"
    elif args.stage == "robust":
        res = stage_robust(args)
        name = "EXP0011_dev_robustness"
    else:
        res = stage_test(args)
        name = "EXP0012_FINAL_TEST"
        if res.get("refused") or res.get("error"):
            print(json.dumps(res, indent=1, ensure_ascii=False)[:800])
            return 3
    res["wallclock_sec"] = round(time.time() - t0, 1)
    res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    out = ROOT / "results_raw" / f"{name}_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    if args.stage == "robust":
        rows = []
        for cfg, r in res["configs"].items():
            for dv, v in r["E05_alternative_dv"].items():
                rows.append({"cfg": cfg, "family": "E05_dv", "variant": dv, "value": json.dumps(v)})
            for kk, v in r["E05b_single_feature_auc"].items():
                rows.append({"cfg": cfg, "family": "E05b_feature", "variant": kk, "value": v})
            for kk, v in r["E11_robustness"].items():
                rows.append({"cfg": cfg, "family": "E11", "variant": kk, "value": v})
            for kk, v in r["E14"].items():
                rows.append({"cfg": cfg, "family": "E14", "variant": kk, "value": json.dumps(v)})
        (ROOT / "results_processed" / "P001_dev_robustness_table.csv").parent.mkdir(exist_ok=True)
        pd.DataFrame(rows).to_csv(ROOT / "results_processed" / "P001_dev_robustness_table.csv", index=False)
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
