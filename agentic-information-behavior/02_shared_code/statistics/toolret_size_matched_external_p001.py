"""EXP-0094 (E08, fourth external test): the same external queries on catalogues whose size matches the dev data.

EXP-0086 settled why the third external test could not be read: two of the frozen model's 33 inputs
(`log_n_candidates`, `qpp_ecle`) are functions of pool size, the dev catalogues span about 4-70 tools, the ToolRet
eval pool is a fixed 44,452 documents, so *no* external row was inside the fitted support and neither transfer nor
non-transfer was admissible. It named the follow-up: rebuild the external rows over pools of dev-comparable size.

This is that follow-up. Queries, gold labels, the frozen model, the frozen feature list, the frozen bands and the
frozen support rule are all unchanged; only the candidate pool each row is scored against is resampled - its size
drawn from the empirical dev distribution of `n_candidates`, always including every gold of that query, the rest
uniform from the union catalogue. That makes the comparison like-for-like on the one axis EXP-0086 identified.

Pre-declared decision rule, fixed here before any AUROC is computed:

  1. the support gate from EXP-0086 is reused verbatim: proceed only if the in-support fraction >= 0.25 **and** the
     in-support subset has >= 30 positives and >= 30 negatives; otherwise the verdict is again "not testable with
     this feature set", now with the matched-pool evidence, and no transfer language is admissible;
  2. if it proceeds, the frozen bands decide: AUROC >= 0.65 transfers, >= 0.55 partial, below that "does not
     transfer" - judged on the in-support subset, and the all-rows number is reported alongside, never instead;
  3. the length-only baseline (single feature `n_tokens`, same fit, same rows) is reported with every arm, because a
     predictor that beats nothing but document length has not shown transfer of the routing construct;
  4. prevalence is reported next to the dev prevalence: if matched pools make the external task much easier than the
     dev task (fail@3 far below dev), the AUROC is read as a within-regime number and labelled as such;
  5. nothing is refitted on external data, and the support rule is not relaxed because the first attempt failed it.

    python toolret_size_matched_external_p001.py [--rows 800] [--draws 2000]

Writes results_raw/EXP0094_size_matched_external_*.json and results_processed/EXP0094_*.csv.
"""
from __future__ import annotations

import argparse, json, pathlib, random, sys, time
from collections import Counter

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_p001_experiments as R                    # noqa: E402
import toolret_eval_transfer_e08 as TR              # noqa: E402
from analyze_routing_failure import CONFIGS, PROC, scaled_pipeline      # noqa: E402
from run_p001_experiments import FROZEN_C, FROZEN_FEATURES, matrices    # noqa: E402
from build_toucan_routing_dataset import (collection_qpp_features, question_features, toks,  # noqa: E402
                                          hyper_chance)

ROOT = R.ROOT
OUT_RAW, OUT_PROC = ROOT / "results_raw", ROOT / "results_processed"
DV = "fail_at_3"
IN_SUPPORT_MIN_FRACTION = 0.25      # reused verbatim from EXP-0086
MIN_EACH_CLASS = 30                 # the same floor EXP-0086 fixed


def build_matched(rows, corp, stat, rng):
    """One record per external query, scored inside a pool whose size is drawn from the dev pool-size distribution."""
    ids, names, id2ix, bm = corp["ids"], corp["names"], corp["id2ix"], corp["bm"]
    toks_full = corp["toks_full"]
    kept = []
    for r in rows:
        try:
            labels = json.loads(r["labels"]) if isinstance(r["labels"], str) else list(r["labels"] or [])
        except (json.JSONDecodeError, TypeError):
            stat["reject_labels_unparseable"] += 1
            continue
        gold = [l.get("id") for l in labels if isinstance(l, dict) and l.get("id")]
        pos = sorted({id2ix[g] for g in gold if g in id2ix})
        if not pos:
            stat["reject_no_gold_in_union"] += 1
            continue
        text = str(r.get("query") or "").strip()
        if not text:
            stat["reject_empty_query"] += 1
            continue
        n_c = int(rng.choice(SIZE_POOL))            # dev-comparable catalogue size
        n_c = max(n_c, len(pos))
        others = [i for i in range(len(ids)) if i not in set(pos)]
        pool = sorted(pos + [int(x) for x in rng.sample(others, n_c - len(pos))])
        pool_toks = [toks_full[i] for i in pool]
        rec = {"cfg": "TOOLRET_EVAL_MATCHED", "subset_name": str(r["subset"]), "prompt_id": str(r["id"]),
               "split": "external", "n_gold": len(pos), "gold_idx": json.dumps(pos[:200]),
               "n_servers_in_row": 0, "n_candidates": len(pool),
               "chance_hit_1": hyper_chance(len(pos), len(pool), 1),
               "chance_hit_3": hyper_chance(len(pos), len(pool), 3),
               "catalog_json": json.dumps([{"n": names[i], "d": "", "p": []} for i in pos[:5]], ensure_ascii=False)}
        for arm, txt in (("query", text), ("instruction", str(r.get("instruction") or "").strip() or text)):
            qtok = toks(txt)
            sc = bm.scores(qtok, pool_toks)
            ranked = sorted(range(len(sc)), key=lambda j: -sc[j])
            rb = min((ranked.index(j) + 1 for j in (pool.index(p) for p in pos)), default=len(pool))
            srt = sorted(sc, reverse=True)
            rec[f"{arm}_bm25_best_rank"] = rb
            rec[f"{arm}_bm25_top1_score"] = round(float(max(sc)), 6)
            rec[f"{arm}_bm25_margin"] = round(float((srt[0] - srt[1]) if len(srt) > 1 else srt[0]), 6)
            rec[f"{arm}_fail_at_1"] = int(rb > 1)
            rec[f"{arm}_fail_at_3"] = int(rb > TR.K)
            rec[f"{arm}_fail_at_5"] = int(rb > 5)
            rec[f"{arm}_norm_rank"] = (rb - 1) / max(1, len(pool) - 1)
            rec[f"{arm}_question"] = txt[:4000]
            for k_, v_ in collection_qpp_features(qtok, pool_toks).items():
                rec[f"{arm}_{k_}"] = v_
            for k_, v_ in question_features(txt).items():
                rec[f"{arm}_{k_}"] = v_
        kept.append(rec)
    return pd.DataFrame(kept)


def cluster_auc(y, s, groups, draws, rng):
    auc = float(roc_auc_score(y, s)) if 0 < sum(y) < len(y) else None
    idx = []
    uniq = np.unique(groups)
    of = {g: np.where(groups == g)[0] for g in uniq}
    for _ in range(draws):
        take = np.concatenate([of[g] for g in rng.choice(uniq, size=len(uniq), replace=True)])
        yy = y[take]
        if 0 < yy.sum() < len(take):
            idx.append(float(roc_auc_score(yy, s[take])))
    ci = [round(float(np.percentile(idx, 2.5)), 4), round(float(np.percentile(idx, 97.5)), 4)] if idx else None
    return (round(auc, 4) if auc is not None else None), ci


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=800, help="total external queries to draw")
    ap.add_argument("--draws", type=int, default=2000)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()

    dev = pd.concat([R.load(c, "dev", TR.K) for c in CONFIGS], ignore_index=True)
    global SIZE_POOL
    SIZE_POOL = dev.n_candidates.values.astype(int)
    src = dev.reset_index(drop=True)
    Xs = np.asarray(matrices(src, FROZEN_FEATURES)["all"], dtype=float)
    names = list(matrices(src, FROZEN_FEATURES)["feature_names"]) + ["log_n_candidates"]
    if len(names) != Xs.shape[1]:
        raise SystemExit(f"ABORT: {len(names)} names for {Xs.shape[1]} columns")
    lo, hi = np.nanmin(Xs, axis=0), np.nanmax(Xs, axis=0)
    pipe = scaled_pipeline(FROZEN_C)().fit(Xs, src[DV].values.astype(int))
    lenpipe = scaled_pipeline(FROZEN_C)().fit(Xs[:, [names.index("n_tokens")]], src[DV].values.astype(int))

    stat = Counter()
    corp = TR.load_corpus(stat)
    n_sub = len([f for f in TR.QDIR.rglob("*.parquet")])
    per_subset = max(2, int(np.ceil(args.rows / max(1, n_sub))))
    picked = TR.load_queries(per_subset, R.SEED, stat)
    rng = random.Random(R.SEED)
    ext = build_matched(picked, corp, stat, rng)
    if len(ext) < 100:
        raise SystemExit(f"ABORT: only {len(ext)} matched rows built - too few for any verdict")
    a = TR.arm_frame(ext, "query")
    X = np.asarray(matrices(a, FROZEN_FEATURES)["all"], dtype=float)
    Xi = pipe._imp(X)
    y = a[DV].values.astype(int)
    groups = a.prompt_id.values
    support = (Xi >= lo - 1e-12) & (Xi <= hi + 1e-12)
    in_row = support.all(axis=1)
    frac = float(in_row.mean())
    p = pipe.predict_proba(X)[:, 1]
    lin = pipe.sc.transform(Xi) @ pipe.m.coef_[0]
    pl = lenpipe.predict_proba(X[:, [names.index("n_tokens")]])[:, 1]
    r2 = np.random.default_rng(R.SEED)

    res = {"exp_id": "EXP-0094", "paper_id": "P001", "e_id": "E08", "seed": R.SEED, "dv": DV,
           "pre_declared_rule": "see module docstring (support gate reused verbatim from EXP-0086)",
           "bands": TR.BANDS, "model": "identical dev-fitted frozen model; nothing refitted on external data",
           "pool_size_source": "empirical dev n_candidates distribution (resampled per query, golds always included)",
           "dev_pool_size_range": [int(SIZE_POOL.min()), int(SIZE_POOL.max())],
           "dev_pool_size_median": float(np.median(SIZE_POOL)),
           "external_pool_size_range": [int(ext.n_candidates.min()), int(ext.n_candidates.max())],
           "external_pool_size_median": float(ext.n_candidates.median()),
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "sample": {"rows_built": int(len(ext)), "queries_drawn": int(len(picked)),
                      "fail_at_3_prevalence_external": round(float(y.mean()), 4),
                      "fail_at_3_prevalence_dev": round(float(src[DV].mean()), 4),
                      "chance_hit_3_mean": round(float(ext.chance_hit_3.mean()), 4)},
           "support": {"rows": int(len(X)), "in_support_rows": int(in_row.sum()), "in_support_fraction": round(frac, 4),
                       "positives_in_support": int(y[in_row].sum()),
                       "negatives_in_support": int((1 - y[in_row]).sum()),
                       "mean_features_outside_per_row": round(float((~support).sum(axis=1).mean()), 2),
                       "raw_nan_cells_imputed": int((~np.isfinite(X)).sum())}}
    marg = pd.DataFrame({"feature": names, "dev_min": lo, "dev_max": hi,
                         "external_min": np.nanmin(Xi, axis=0), "external_max": np.nanmax(Xi, axis=0),
                         "share_rows_outside": (~support).mean(axis=0)})
    marg.sort_values("share_rows_outside", ascending=False).to_csv(OUT_PROC / "EXP0094_per_feature_support.csv",
                                                                   index=False)
    res["features_still_outside"] = [
        {"feature": r.feature, "share_rows_outside": round(float(r.share_rows_outside), 3),
         "dev_range": [round(float(r.dev_min), 3), round(float(r.dev_max), 3)],
         "external_range": [round(float(r.external_min), 3), round(float(r.external_max), 3)]}
        for r in marg[marg.share_rows_outside > 0].sort_values("share_rows_outside", ascending=False).head(8).itertuples()]

    gate_ok = (frac >= IN_SUPPORT_MIN_FRACTION
               and res["support"]["positives_in_support"] >= MIN_EACH_CLASS
               and res["support"]["negatives_in_support"] >= MIN_EACH_CLASS)
    arms = []
    for label, score in (("frozen probability", p), ("linear predictor (no link)", lin),
                         ("length-only baseline", pl)):
        est = {"arm": label}
        est_all, ci_all = cluster_auc(y, score, groups, args.draws, r2)
        est.update({"auroc_all_rows": est_all, "ci95_all_rows": ci_all})
        if in_row.sum() >= 20 and gate_ok:
            est_sub, ci_sub = cluster_auc(y[in_row], score[in_row], groups[in_row], args.draws, r2)
            est.update({"auroc_in_support": est_sub, "ci95_in_support": ci_sub, "n_in_support": int(in_row.sum())})
        else:
            est.update({"auroc_in_support": None,
                        "why": f"in_support_fraction={frac} positives={res['support']['positives_in_support']} "
                               f"negatives={res['support']['negatives_in_support']}"})
        arms.append(est)
    res["arms"] = arms

    if not gate_ok:
        res["verdict"] = (f"STILL NOT TESTABLE with the frozen feature set even after pool sizes are matched: "
                          f"in-support fraction {frac} (gate {IN_SUPPORT_MIN_FRACTION}), "
                          f"{res['support']['positives_in_support']} positives / "
                          f"{res['support']['negatives_in_support']} negatives in support. The features that keep "
                          f"rows outside are {', '.join(chr(96) + x['feature'] + chr(96) for x in res['features_still_outside'][:3])}")
    else:
        main_auc = arms[0].get("auroc_in_support")
        band = TR.verdict(main_auc) if main_auc is not None else "not computable"
        lb = arms[2].get("auroc_in_support")
        res["verdict"] = (f"SUPPORT GATE PASSED (in-support fraction {frac}, "
                          f"{res['support']['positives_in_support']} positives): frozen probability AUROC on the "
                          f"in-support subset {main_auc} (CI {arms[0]['ci95_in_support']}) -> band '{band}'; "
                          f"length-only baseline {lb} (CI {arms[2]['ci95_in_support']}). "
                          + ("The frozen construct transfers at dev-comparable pool scale."
                             if main_auc is not None and lb is not None and main_auc >= TR.BANDS["transfers"]
                             and main_auc > lb else
                             "This is not evidence of transfer of the routing construct: the criterion is the band "
                             "AND being above the length-only baseline, and one of the two is not met."))
    res["wallclock_sec"] = round(time.time() - t0, 1)
    res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    out = OUT_RAW / f"EXP0094_size_matched_external_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("sample", "support", "external_pool_size_median")}, ensure_ascii=False)[:600])
    for x in arms:
        print(" ", x["arm"], "all:", x.get("auroc_all_rows"), x.get("ci95_all_rows"),
              "| in-support:", x.get("auroc_in_support"), x.get("ci95_in_support"))
    print("verdict:", res["verdict"])
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
