"""EXP-0006: does instruction-only, pre-retrieval text predict lexical tool-routing failure?

Reads the routing parquets written by build_toucan_routing_dataset.py (EXP-0005) and never
re-derives them, so re-analysis does not require rebuilding 45k rows.

Two corrections over EXP-0005's embedded block:
  1. fail@k is undefined when the catalog has <= k entries: EXP-0005 measured that stratum
     (cand<=3) at fail@3 = 0.0000 and chance_hit@3 = 0.0000, i.e. top-3 is the whole catalog.
     Those rows are structurally uninformative, so every metric here is computed on
     n_candidates > k and the uninformative fraction is reported (spec T04.05 selection bias).
  2. EXP-0005's in-sample logistic died with `LinAlgError: Singular matrix` from zero-variance
     feature columns. Predictions are now out-of-fold (5-fold stratified CV, repeated seeds),
     which also removes the in-sample optimism a held-out claim must not carry.

Comparators follow the spec's B0-B5 ladder: B0 trivial (length, constant), B1 classic
(BM25 score margin = post-retrieval quasi-local QPP), B1b regularised logistic on
pre-retrieval features, B2 gradient-boosted trees on the same features.

    python analyze_routing_failure.py --dv fail_at_3 --repeats 3

Writes results_raw/EXP0006_*.json and results_processed/EXP0006_*.csv.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "01_datasets" / "processed"
CONFIGS = ["OSS", "Qwen3", "Kimi-K2"]
SEEDS = [42, 43, 44, 45, 46]

FEATURE_COLS = ["n_tokens", "n_chars", "n_sentences", "mean_sentence_len", "lex_diversity_mtld_proxy",
                "constraint_density", "n_constraint_words", "sequence_marker_n", "epistemic_marker_n",
                "vague_word_n", "demonstrative_n", "pronoun_clause_start", "quoted_span_n",
                "proper_entity_n", "file_reference_n", "url_n", "number_n", "named_app_n",
                "imperative_start", "question_mark", "n_subtasks_by_punctuation", "n_lines",
                "has_bullet_list", "char_per_subtask",
                "qpp_coverage", "qpp_idf_weighted_coverage", "qpp_clarity_meanmax", "qpp_clarity_sd",
                "qpp_max_doc_sim", "qpp_mean_doc_sim", "qpp_doc_sim_spread", "qpp_ecle",
                "qpp_missing_term_n", "qpp_n_query_terms"]
LINGUISTIC_COLS = [c for c in FEATURE_COLS if not c.startswith("qpp_")]
QPP_COLS = [c for c in FEATURE_COLS if c.startswith("qpp_")]


def oof_auc(X: np.ndarray, y: np.ndarray, make_model, seed: int) -> tuple[float, np.ndarray]:
    """Out-of-fold scores; returns (AUC, pooled OOF probability vector)."""
    proba = np.zeros(len(y))
    for tr, te in StratifiedKFold(n_splits=5, shuffle=True, random_state=seed).split(X, y):
        m = make_model()
        if hasattr(m, "fit"):
            m.fit(X[tr], y[tr])
        proba[te] = m.predict_proba(X[te])[:, 1]
    return float(roc_auc_score(y, proba)), proba


def scaled_pipeline(C: float):
    def make():
        class Pre:
            """Median-impute + standardise + logistic, all fitted inside the training fold.

            EXP-0007's feature set contains boundary NaNs (mean over an empty sentence list,
            entropy of an all-zero term distribution), so imputation is part of the model,
            not a preprocessing shortcut on the full sample.
            """

            def fit(self, X, y):
                X = np.asarray(X, dtype=float)
                self.med = np.nanmedian(X, axis=0)
                self.med[~np.isfinite(self.med)] = 0.0
                Z = self._imp(X)
                self.sc = StandardScaler().fit(Z)
                self.m = LogisticRegression(C=C, max_iter=2000, solver="lbfgs").fit(self.sc.transform(Z), y)
                return self

            def _imp(self, X):
                X = np.asarray(X, dtype=float).copy()
                bad = ~np.isfinite(X)
                if bad.any():
                    X[bad] = np.take(self.med, np.where(bad)[1])
                return X

            def predict_proba(self, X):
                return self.m.predict_proba(self.sc.transform(self._imp(X)))
        return Pre()
    return make


def holm(pmap: dict) -> dict:
    ordered = sorted(pmap.items(), key=lambda kv: kv[1])
    m, running, out = len(ordered), 0.0, {}
    for rank, (k, p) in enumerate(ordered, start=1):
        running = max(running, min(1.0, (m - rank + 1) * p))
        out[k] = running
    return out


def univariate_or(x: np.ndarray, y: np.ndarray) -> dict:
    """Single-feature logistic OR: immune to the collinearity that sank the joint fit."""
    ok = np.isfinite(x)
    x, y = np.asarray(x, dtype=float)[ok], np.asarray(y)[ok]
    sd = x.std(ddof=0)
    if len(x) < 30 or sd == 0 or y.sum() == 0 or y.sum() == len(y):
        return {"OR": None, "p": None, "n_used": int(len(x))}
    z = (x - x.mean()) / sd
    # ridge-regularised Newton steps on the standardised single predictor
    beta = 0.0
    for _ in range(60):
        eta = z * beta
        p = 1 / (1 + np.exp(-eta))
        w = np.clip(p * (1 - p), 1e-8, None)
        grad = (z * (y - p)).sum() - 1.0 * beta
        hess = (z * z * w).sum() + 1.0
        step = grad / hess
        beta += step
        if abs(step) < 1e-9:
            break
    p = 1 / (1 + np.exp(-(z * beta)))
    w = np.clip(p * (1 - p), 1e-8, None)
    se = 1.0 / np.sqrt((z * z * w).sum() + 1.0)
    zst = beta / se
    pv = 2 * stats.norm.sf(abs(zst))
    return {"OR": round(float(np.exp(beta)), 4),
            "ci95_OR": [round(float(np.exp(beta - 1.96 * se)), 4), round(float(np.exp(beta + 1.96 * se)), 4)],
            "p": float(pv), "cohen_d_binary": round(float(abs(x[y == 1].mean() - x[y == 0].mean()) /
                                                       (np.sqrt((x[y == 1].var(ddof=1) + x[y == 0].var(ddof=1)) / 2) or 1)), 4)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dv", default="fail_at_3")
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--max-rows", type=int, default=0)
    args = ap.parse_args()

    t0 = time.time()
    exp = {"exp_id": "EXP-0006", "dv": args.dv, "k": args.k, "cv": "5-fold stratified, out-of-fold",
           "repeats": args.repeats, "seeds": SEEDS[:args.repeats],
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "configs": {}, "pooled": {}}
    print(f"EXP-0006 pre-retrieval prediction of {args.dv} | repeats={args.repeats}")

    pooled_frames = []
    for cfg in CONFIGS:
        f = PROC / f"routing_{cfg}.parquet"
        if not f.exists():
            print(f"  !! missing {f}")
            continue
        df = pd.read_parquet(f)
        if args.max_rows:
            df = df.head(args.max_rows)
        dev = df[df.split == "dev"].copy()
        n_all = len(dev)
        dev = dev[dev.n_candidates > args.k].copy()       # structurally informative only
        y = dev[args.dv].values.astype(int)
        if y.sum() < 30:
            exp["configs"][cfg] = {"error": f"only {y.sum()} positives after restriction"}
            continue
        feats = [c for c in FEATURE_COLS if c in dev.columns]
        Xall = dev[feats].astype(float).values
        keep = (np.nanstd(Xall, axis=0) > 0) & (~np.all(~np.isfinite(Xall), axis=0))
        dropped = [feats[i] for i, kk in enumerate(keep) if not kk]
        X = Xall[:, keep]
        feats_kept = [feats[i] for i, kk in enumerate(keep) if kk]
        Xsize = np.column_stack([X, np.log(dev.n_candidates.values.astype(float))])
        Xlenonly = dev[["n_tokens"]].astype(float).values
        Xpost = dev[["bm25_margin", "bm25_top1_score"]].astype(float).values
        qcols = [c for c in QPP_COLS if c in dev.columns]
        lcols = [c for c in LINGUISTIC_COLS if c in dev.columns]
        Xqpp = np.column_stack([dev[qcols].astype(float).values, np.log(dev.n_candidates.values.astype(float))])
        Xlang = np.column_stack([dev[lcols].astype(float).values, np.log(dev.n_candidates.values.astype(float))])

        res = {"n_dev_all": n_all, "n_dev_informative": int(len(dev)),
               "uninformative_fraction": round(1 - len(dev) / n_all, 4),
               "positives": int(y.sum()), "prevalence": round(float(y.mean()), 4),
               "dropped_zero_variance": dropped,
               "nan_rate_per_feature": {feats[i]: round(float(np.mean(~np.isfinite(Xall[:, i]))), 4)
                                        for i in range(Xall.shape[1])
                                        if np.any(~np.isfinite(Xall[:, i]))},
               "auc": {}}
        for name, Xm, mk in [
                ("B0_constant_chance", np.zeros((len(dev), 1)), None),
                ("B0_length_only", Xlenonly, scaled_pipeline(1e6)),
                ("B1_postretrieval_margin", Xpost, scaled_pipeline(1.0)),
                ("B1b_preretrieval_logistic", Xsize, scaled_pipeline(1.0)),
                ("B1c_linguistic_only_nosize", Xlang, scaled_pipeline(1.0)),
                ("B1d_collection_qpp_only", Xqpp, scaled_pipeline(1.0)),
                ("B2_trees_preretrieval", Xsize, lambda: HistGradientBoostingClassifier(
                    max_iter=200, learning_rate=0.06, max_depth=4, random_state=42,
                    early_stopping=True, validation_fraction=0.15))]:
            if mk is None:
                res["auc"][name] = {"mean": 0.5, "std": 0.0, "note": "reference"}
                continue
            aucs = [oof_auc(Xm, y, mk, s)[0] for s in SEEDS[:args.repeats]]
            res["auc"][name] = {"mean": round(float(np.mean(aucs)), 4),
                                "std": round(float(np.std(aucs, ddof=1)), 4) if len(aucs) > 1 else None,
                                "per_seed": [round(a, 4) for a in aucs]}
            if name == "B1b_preretrieval_logistic":
                last = oof_auc(Xm, y, mk, 42)[1]
                res["brier"] = round(float(np.mean((last - y) ** 2)), 5)
        # mechanism-readable univariate table with Holm correction
        uni = {}
        for j, name in enumerate(feats_kept):
            uni[name] = univariate_or(X[:, j], y)
        ps = {k: v["p"] for k, v in uni.items() if v.get("p") is not None}
        adj = holm(ps)
        for k2, v2 in uni.items():
            if k2 in adj:
                v2["p_holm"] = round(adj[k2], 6)
                v2["sig_holm_005"] = bool(adj[k2] < 0.05)
        res["univariate_OR_holm"] = uni
        # does the pre-retrieval model beat length alone? DeLong-free bootstrap on OOF AUC diff
        a_pre = np.asarray(res["auc"]["B1b_preretrieval_logistic"]["per_seed"])
        a_len = np.asarray(res["auc"]["B0_length_only"]["per_seed"])
        res["auc_delta_pre_minus_length"] = [round(float(x), 4) for x in (a_pre - a_len)]
        exp["configs"][cfg] = res
        print(f"\n[{cfg}] informative dev n={len(dev)} (uninformative {res['uninformative_fraction']:.1%}) "
              f"positives={y.sum()} prevalence={res['prevalence']}")
        for k3, v3 in res["auc"].items():
            print(f"   {k3:32s} AUC={v3['mean']:.4f}" + (f" ±{v3['std']:.4f}" if v3.get('std') else ""))
        sig = sorted(((kk, vv) for kk, vv in uni.items() if vv.get("sig_holm_005")),
                     key=lambda kv: kv[1]["p_holm"])
        print(f"   Holm-significant univariates: {[(kk, vv['OR']) for kk, vv in sig][:10]}")
        pooled_frames.append(dev.assign(cfg=cfg))

    if len(pooled_frames) > 1:
        pool = pd.concat(pooled_frames, ignore_index=True)
        y = pool[args.dv].values.astype(int)
        feats = [c for c in FEATURE_COLS if c in pool.columns]
        X = pool[feats].astype(float).values
        keep = X.std(axis=0) > 0
        X = X[:, keep]
        X = np.column_stack([X, np.log(pool.n_candidates.values.astype(float)),
                             (pool.cfg == "Qwen3").astype(float), (pool.cfg == "Kimi-K2").astype(float)])
        aucs = [oof_auc(X, y, scaled_pipeline(1.0), s)[0] for s in SEEDS[:args.repeats]]
        aucs_len = [oof_auc(pool[["n_tokens"]].values.astype(float), y, scaled_pipeline(1e6), s)[0]
                    for s in SEEDS[:args.repeats]]
        aucs_post = [oof_auc(pool[["bm25_margin", "bm25_top1_score"]].values.astype(float), y,
                            scaled_pipeline(1.0), s)[0] for s in SEEDS[:args.repeats]]
        exp["pooled"] = {"n": int(len(pool)), "positives": int(y.sum()), "prevalence": round(float(y.mean()), 4),
                         "auc_pre_logistic": {"mean": round(float(np.mean(aucs)), 4),
                                              "std": round(float(np.std(aucs, ddof=1)), 4) if len(aucs) > 1 else None,
                                              "per_seed": [round(a, 4) for a in aucs]},
                         "auc_length": {"mean": round(float(np.mean(aucs_len)), 4)},
                         "auc_post_margin": {"mean": round(float(np.mean(aucs_post)), 4)}}
        print(f"\n[POOLED] n={len(pool)} prev={y.mean():.4f} "
              f"AUC pre={exp['pooled']['auc_pre_logistic']['mean']} "
              f"length={exp['pooled']['auc_length']['mean']} post={exp['pooled']['auc_post_margin']['mean']}")

    exp["wallclock_sec"] = round(time.time() - t0, 1)
    exp["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    exp["interpretation_limits"] = ("association only; DV is failure of a lexical ranker on non-exhaustive gold labels; "
                                   "queries are forward-synthesised from the tool set (Toucan paper §3.1)")
    out = ROOT / "results_raw" / f"EXP0006_preretrieval_prediction_{args.dv}_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(exp, indent=1, ensure_ascii=False), encoding="utf-8")
    tbl = []
    for cfg, r in exp["configs"].items():
        if "auc" not in r:
            continue
        for m, v in r["auc"].items():
            tbl.append({"cfg": cfg, "model": m, "auc_mean": v["mean"], "auc_std": v.get("std"),
                        "n": r["n_dev_informative"], "positives": r["positives"]})
    tp = ROOT / "results_processed" if (ROOT / "results_processed").exists() else ROOT / "results_raw"
    pd.DataFrame(tbl).to_csv(tp / f"EXP0006_auc_table_{args.dv}.csv", index=False)
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
