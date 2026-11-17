"""EXP-0035 (P001): does the frozen predictor survive the query subsets P001 never sampled?

Found by EXP-0034 and then confirmed against the published artefacts: `routing_{OSS,Qwen3,Kimi-K2}.parquet` are
100% `single-turn-original`, because the builder fills 15,000 rows from the first two randomly picked shards and
Toucan's shards are subset-homogeneous. The OSS corpus itself is 25.7% single-turn-original, 25.8%
single-turn-diversify, 38.4% multi-turn, 10.1% irrelevant. So every published P001 number - dev and test alike -
describes one quarter of one corpus, and the omitted `diversify` subset is precisely the paraphrase /
vocabulary-varied condition that a lexical-reachability mechanism is supposed to be about.

This measures what that costs, WITHOUT touching the single-use test split. Rows are drawn only from the two absent
subsets and only scored with the frozen pipeline; the model is fitted on the published DEV rows (which are
themselves original-sample dev, never test).

Pre-registered decision rule, fixed before any AUROC was computed. For each config x subset:
  transfer AUC   = fit frozen `all_C0.1` on published dev (single-turn-original), score the new subset;
  own-subset AUC = 5-fold grouped-by-prompt_id OOF inside the new subset (upper reference for that subset);
  length-only    = the paper's B0 baseline recomputed on the same rows.
  COVERAGE_HOLE_IS_BOUNDED iff, for all 6 cells: transfer >= 0.65, transfer >= own-subset - 0.05, and
  transfer > length-only. Otherwise the predictor is SUBSET-SPECIFIC and H1-H3 must be labelled as estimates on
  single-turn-original instructions only.

    python 02_shared_code/statistics/subset_sensitivity_p001.py

Writes results_raw/EXP0035_subset_sensitivity_*.json and results_processed/EXP0035_subset_sensitivity.csv.
"""
from __future__ import annotations

import json, random, re, sys, time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "02_shared_code" / "trajectory_parser"))
sys.path.insert(0, str(ROOT / "02_shared_code" / "statistics"))
import build_toucan_routing_dataset as B           # frozen parser + BM25 + feature battery
import run_p001_experiments as R                   # frozen model, feature list, pipeline, OOF helper

SEED, ROWS_PER_CELL, K = 42, 4000, 3
SUBSETS = ["single-turn-diversify", "multi-turn"]
CONFIGS = ["OSS", "Qwen3", "Kimi-K2"]
OUT_RAW, OUT_PROC = ROOT / "results_raw", ROOT / "results_processed"


def files_for(cfg, subset):
    """Toucan shards are subset-homogeneous: keep the files whose rows are all of one subset."""
    keep = []
    for f in sorted((B.DATA / cfg).glob("*.parquet")):
        sn = pq.read_table(f, columns=["subset_name"]).column("subset_name").to_pylist()
        if sn.count(subset) == len(sn):
            keep.append(f)
    return keep


def score_rows(cfg, subset, col, n_rows):
    rows, per = [], max(1, n_rows // 4)
    for f in random.Random(SEED).sample(files_for(cfg, subset), min(4, len(files_for(cfg, subset)))):
        tbl = pq.read_table(f, columns=["uuid", "question", col, "target_tools", "metadata", "subset_name"])
        take = sorted(random.Random(SEED).sample(range(tbl.num_rows), min(per, tbl.num_rows)))
        for r in tbl.take(take).to_pylist():
            catalog = B.parse_catalog(r[col])
            if not catalog:
                continue
            items = [x.strip() for x in re.split(r",(?![^{]*\})", str(r["target_tools"] or "")) if x.strip()]
            if not items:
                continue
            srv_idx, srv_slugs = B.server_tool_index(r.get("metadata"))
            matched, _ = B.resolve_gold_v2(items, catalog, srv_idx, srv_slugs)
            if matched is None:
                continue
            q = str(r["question"])
            qtok = B.toks(q)
            docs = [B.toks(d["name"].replace("-", " ").replace("_", " ")) + B.toks(d["desc"])
                    + B.toks(" ".join(d["params"])) for d in catalog]
            sc = B.BM25().scores(qtok, docs)
            ranked = sorted(range(len(sc)), key=lambda i: -sc[i])
            rb = min((ranked.index(i) + 1 for i in matched), default=len(catalog))
            srt = sorted(sc, reverse=True)
            try:
                pid = str(json.loads(r["metadata"]).get("prompt_id") or r["uuid"])
            except Exception:
                pid = str(r["uuid"])
            rows.append({"uuid": r["uuid"], "prompt_id": pid, "cfg": cfg, "subset_name": subset,
                         "n_candidates": len(catalog), "n_gold": len(matched),
                         "fail_at_3": int(rb > 3), "bm25_best_rank": rb,
                         "bm25_margin": round((srt[0] - srt[1]) if len(srt) > 1 else srt[0], 6),
                         "bm25_top1_score": round(max(sc) if sc else 0.0, 6),
                         **B.collection_qpp_features(qtok, docs), **B.question_features(q)})
        del tbl
    df = pd.DataFrame(rows)
    return df[df.n_candidates > K].reset_index(drop=True)          # same informative population as the paper


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    frozen = json.loads((ROOT / "papers/P001_routing_failure_qpp/configs/P001_frozen_model.json")
                        .read_text(encoding="utf-8"))
    fs, C = frozen["model"].split("_C")[0], frozen["C"]
    res = {"exp_id": "EXP-0035", "paper_id": "P001", "seed": SEED, "frozen_model": frozen["model"],
           "rows_per_cell_target": ROWS_PER_CELL, "population": "n_candidates > 3 (as in the published analysis)",
           "rule": "BOUNDED iff all cells: transfer>=0.65 and transfer>=own-subset-0.05 and transfer>length-only",
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "cells": {}}
    ok_all = True
    for cfg in CONFIGS:
        tr = R.load(cfg, "dev", K)
        Mtr = R.matrices(tr, R.FROZEN_FEATURES)
        ytr = tr[R.DV_PRIMARY].values.astype(int)
        pipe = R.scaled_pipeline(C)().fit(Mtr[fs], ytr)      # scaled_pipeline returns a FACTORY; call it first
        res[f"{cfg}_train"] = {"published_dev_rows": int(len(tr)), "positives": int(ytr.sum()),
                              "subset": sorted(tr.subset_name.unique()) if "subset_name" in tr else None,
                              "in_sample_auc": round(float(R.roc_auc_score(ytr, pipe.predict_proba(Mtr[fs])[:, 1])), 4)}
        for sub in SUBSETS:
            new = score_rows(cfg, sub, B.CONFIGS[cfg], ROWS_PER_CELL)
            M = R.matrices(new, R.FROZEN_FEATURES)
            y = new[R.DV_PRIMARY].values.astype(int)
            p_tr = pipe.predict_proba(M[fs])[:, 1]
            auc_tr = float(R.roc_auc_score(y, p_tr))
            p_own = np.zeros(len(y))
            for a, b in GroupKFold(n_splits=5).split(M[fs], y, groups=new.prompt_id.values):
                p_own[b] = R.scaled_pipeline(C)().fit(M[fs][a], y[a]).predict_proba(M[fs][b])[:, 1]
            auc_own = float(R.roc_auc_score(y, p_own))
            p_len = -new.n_tokens.values.astype(float)                     # longer = more failure (B0 sign)
            auc_len = max(float(R.roc_auc_score(y, p_len)), float(R.roc_auc_score(y, -p_len)))
            post = R.matrices(new, None)["post"]
            auc_post = float(R.roc_auc_score(y, -post[:, 0]))
            keep = (auc_tr >= 0.65) and (auc_tr >= auc_own - 0.05) and (auc_tr > auc_len)
            ok_all &= bool(keep)
            res["cells"][f"{cfg}|{sub}"] = {
                "rows": int(len(new)), "prompt_ids": int(new.prompt_id.nunique()), "prevalence": round(float(y.mean()), 4),
                "mean_n_candidates": round(float(new.n_candidates.mean()), 2),
                "auc_transfer_original_dev": round(auc_tr, 4), "auc_own_subset_oof": round(auc_own, 4),
                "auc_length_only": round(auc_len, 4), "auc_post_retrieval_margin": round(auc_post, 4),
                "meets_rule": bool(keep)}
            print(f"  {cfg:8s} {sub:22s} n={len(new):5d} prev={y.mean():.4f} "
                  f"transfer={auc_tr:.4f} own={auc_own:.4f} len={auc_len:.4f} {'OK' if keep else 'FAIL'}")
    res["verdict"] = {"decision": "COVERAGE_HOLE_IS_BOUNDED" if ok_all else
                     "PREDICTOR_IS_SUBSET_SPECIFIC: label H1-H3 as estimated on single-turn-original instructions",
                     "cells_tested": len(res["cells"])}
    res["wallclock_sec"] = round(time.time() - t0, 1)
    res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    OUT_RAW.mkdir(exist_ok=True)
    out = OUT_RAW / f"EXP0035_subset_sensitivity_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    pd.DataFrame([{"cell": c, **v} for c, v in res["cells"].items()]).to_csv(
        OUT_PROC / "EXP0035_subset_sensitivity.csv", index=False)
    print(json.dumps(res["verdict"], ensure_ascii=False))
    print("wrote", out, f"({res['wallclock_sec']}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
