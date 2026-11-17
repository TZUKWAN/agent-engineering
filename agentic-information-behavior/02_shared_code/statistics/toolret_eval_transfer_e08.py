"""EXP-0083 (E08, decisive external arm): the frozen predictor on ToolRet's EVAL split, over its real catalogue.

EXP-0082 scored the benchmark's TRAINING partition, whose per-query candidate set is 10 NV-embed-mined hard negatives
(magnitude ~17 tools, near-zero variance). This step uses the release that actually defines the benchmark:

  * `mangopy/ToolRet-Queries` - 7,961 rows over 35 task subsets, columns id/query/instruction/labels/category;
  * `mangopy/ToolRet-Tools`   - 44,453 tool documents in three category partitions (code, customized, web).

so each query faces a **production-scale catalogue** (thousands of candidate tools, not ten), which is the construct
P001's `fail_at_3` was defined on. Same discipline as EXP-0023 and EXP-0082:

  * the frozen model is fitted on the published Toucan DEV rows only and merely scored here; no feature, threshold or
    C value is chosen from external rows;
  * BM25 is the frozen implementation (k1=1.4, b=0.4) and the frozen tokeniser and feature functions - no
    reimplementation, so no chance of a fast-but-different ranker;
  * every row is stratified-sampled with a recorded seed, and every rejection is counted and reported;
  * verdict bands were frozen in EXP-0021: >=0.65 transfers, 0.55-0.65 partial, <0.55 does not transfer;
  * a gold tool that is not present in its own category corpus is a rejection, not a silent miss - it would otherwise
    inflate fail@3 and look like a retrieval failure.

    python toolret_eval_transfer_e08.py [--per-subset 60] [--limit-catalogue 0]

Outputs results_raw/EXP0083_toolret_eval_transfer_*.json and
        results_processed/EXP0083_toolret_eval_*.csv
"""
from __future__ import annotations

import argparse, json, pathlib, sys, time
from collections import Counter, defaultdict

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from sklearn.metrics import roc_auc_score

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "trajectory_parser"))
from analyze_routing_failure import CONFIGS, PROC, SEEDS, oof_auc, scaled_pipeline   # noqa: E402
from build_toucan_routing_dataset import (BM25, collection_qpp_features, hyper_chance,  # noqa: E402
                                          question_features, toks)
from run_p001_experiments import FROZEN_C, FROZEN_FEATURES, matrices                  # noqa: E402

ROOT = HERE.parents[1]
BASE = ROOT / "01_datasets" / "raw" / "toolret"
QDIR, TDIR = BASE / "queries", BASE / "tools"
OUT_RAW, OUT_PROC = ROOT / "results_raw", ROOT / "results_processed"
K, DV = 3, "fail_at_3"
BANDS = {"transfers": 0.65, "partial": 0.55}


def doc_text(d):
    """The released `documentation` blob carries at least three tool-record dialects (measured in EXP-0082); name,
    description and parameter names are pulled from whichever keys exist."""
    name = str(d.get("name") or d.get("api_name") or "").strip()
    desc = str(d.get("description") or d.get("api_description") or "")
    keys = [str(x) for x in d.get("parameters") or []]
    da = d.get("doc_arguments")
    if isinstance(da, dict):
        keys += list((da.get("properties") or {}).keys())
    if isinstance(d.get("parameters"), dict):
        keys += [str(x) for x in d["parameters"]]
    for lst in (d.get("required_parameters"), d.get("optional_parameters")):
        if isinstance(lst, list):
            keys += [str(p.get("name")) for p in lst if isinstance(p, dict) and p.get("name")]
    return name, desc, keys


def load_corpus(stat):
    """ONE merged catalogue over all three released partitions.

    The first version of this step gave each query the partition named by its own `category` field, and that was
    wrong: measured against the released ids, only 1,749/2,274 code-, 982/2,281 customized- and 5,230/9,551 web-category
    gold ids were present in their own partition, so the majority of queries would have been dropped for a defect in
    *my* join rather than a property of the benchmark. The paper's protocol is one pool of ~43k tools, which is what
    the union is, and every query is now scored against it; queries whose golds are in no partition at all are
    counted as `reject_gold_not_in_union` and reported, never silently treated as retrieval failures.
    """
    ids, names, toks_full, toks_desc, part = [], [], [], [], []
    for f in sorted(p for p in TDIR.rglob("*.parquet")):
        cat = f.parent.name
        tbl = pq.read_table(f, columns=["id", "documentation"]).to_pydict()
        n0 = len(ids)
        for tid, blob in zip(tbl["id"], tbl["documentation"]):
            try:
                d = json.loads(blob)
            except (json.JSONDecodeError, TypeError):
                stat["tool_blob_unparseable"] += 1
                continue
            name, desc, keys = doc_text(d)
            if not name and not desc:
                stat["tool_doc_empty"] += 1
                continue
            ids.append(tid)
            names.append(name)
            toks_full.append(toks(name.replace("-", " ").replace("_", " ")) + toks(desc) + toks(" ".join(keys)))
            toks_desc.append(toks(desc))
            part.append(cat)
        stat[f"partition_{cat}_docs"] = len(ids) - n0
    if len(set(ids)) != len(ids):
        raise SystemExit(f"ABORT: {len(ids) - len(set(ids))} duplicate tool ids across partitions")
    stat["union_docs"] = len(ids)
    return {"ids": ids, "names": names, "toks_full": toks_full, "toks_desc": toks_desc, "partition": part,
            "bm": BM25(k1=1.4, b=0.4), "id2ix": {t: i for i, t in enumerate(ids)}}


def load_queries(per_subset, seed, stat):
    rows = []
    for f in sorted(p for p in QDIR.rglob("*.parquet")):
        subset = f.parent.name
        tbl = pq.read_table(f, columns=["id", "query", "instruction", "labels", "category"]).to_pandas()
        stat["query_rows_seen"] += len(tbl)
        if per_subset and len(tbl) > per_subset:
            idx = np.random.default_rng(seed + abs(hash(subset)) % 10_000).permutation(len(tbl))[:per_subset]
            tbl = tbl.iloc[np.sort(idx)]
        for r in tbl.to_dict("records"):
            r["subset"] = subset
            rows.append(r)
    return rows


def build(rows, corp, stat):
    ids, names, toks_full, id2ix, bm = (corp["ids"], corp["names"], corp["toks_full"], corp["id2ix"], corp["bm"])
    kept = []
    for r in rows:
        cat = str(r.get("category") or "")
        try:
            labels = json.loads(r["labels"]) if isinstance(r["labels"], str) else list(r["labels"] or [])
        except (json.JSONDecodeError, TypeError):
            stat["reject_labels_unparseable"] += 1
            continue
        gold_ids = [l.get("id") for l in labels if isinstance(l, dict) and l.get("id")]
        if not gold_ids:
            stat["reject_no_gold"] += 1
            continue
        pos = sorted({id2ix[g] for g in gold_ids if g in id2ix})
        stat["gold_ids_total"] += len(gold_ids)
        stat["gold_ids_found_in_union"] += len([g for g in gold_ids if g in id2ix])
        if not pos:
            # the gold tools are absent from the released corpus: a release-construct problem, not a retrieval
            # failure, so it must never be allowed to raise fail@3
            stat["reject_gold_not_in_union"] += 1
            continue
        q = str(r.get("query") or "").strip()
        ins = str(r.get("instruction") or "").strip()
        if not q:
            stat["reject_empty_instruction"] += 1
            continue
        n_c = len(ids)
        rec = {"cfg": "TOOLRET_EVAL", "subset_name": str(r["subset"]), "category": cat,
               "prompt_id": str(r["id"]), "split": "external", "n_gold": len(pos),
               "gold_idx": json.dumps(pos[:200]), "n_servers_in_row": 0,
               "gold_partition": ",".join(sorted({corp["partition"][i] for i in pos})),
               "n_candidates": n_c, "chance_hit_1": hyper_chance(len(pos), n_c, 1),
               "chance_hit_3": hyper_chance(len(pos), n_c, 3), "chance_hit_5": hyper_chance(len(pos), n_c, 5),
               "catalog_json": json.dumps([{"n": names[i], "d": "", "p": []} for i in pos[:5]],
                                          ensure_ascii=False)}
        for arm, text in (("query", q), ("instruction", ins or q)):
            qtok = toks(text)
            sc = bm.scores(qtok, toks_full)
            ranked = sorted(range(len(sc)), key=lambda j: -sc[j])
            rb = min((ranked.index(j) + 1 for j in pos), default=n_c)
            srt = sorted(sc, reverse=True)
            rec[f"{arm}_bm25_best_rank"] = rb
            rec[f"{arm}_bm25_top1_score"] = round(max(sc), 6)
            rec[f"{arm}_bm25_margin"] = round((srt[0] - srt[1]) if len(srt) > 1 else srt[0], 6)
            rec[f"{arm}_fail_at_1"] = int(rb > 1)
            rec[f"{arm}_fail_at_3"] = int(rb > K)
            rec[f"{arm}_fail_at_5"] = int(rb > 5)
            rec[f"{arm}_norm_rank"] = (rb - 1) / max(1, n_c - 1)
            rec[f"{arm}_question"] = text[:4000]
            for k_, v_ in collection_qpp_features(qtok, toks_full).items():
                rec[f"{arm}_{k_}"] = v_
            for k_, v_ in question_features(text).items():
                rec[f"{arm}_{k_}"] = v_
        kept.append(rec)
    return pd.DataFrame(kept)


def arm_frame(df, arm):
    a = df.copy()
    for c in df.columns:
        if c.startswith(arm + "_"):
            a[c[len(arm) + 1:]] = a[c]
    return a


def verdict(auc):
    return ("transfers" if auc >= BANDS["transfers"] else
            ("partial" if auc >= BANDS["partial"] else "does not transfer"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-subset", type=int, default=60)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    if not QDIR.is_dir() or not TDIR.is_dir():
        raise SystemExit(f"ABORT: eval release not on disk under {BASE} - run the download step first")
    exp = {"exp_id": "EXP-0083", "e_id": "E08", "seed": SEEDS[0], "k": K, "dv": DV, "bands": BANDS,
           "per_subset_cap": args.per_subset,
           "frozen_model": {"C": FROZEN_C, "n_features": len(FROZEN_FEATURES or []),
                            "features_file": "papers/P001_routing_failure_qpp/configs/P001_frozen_model.json"},
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    stat = Counter()
    corp = load_corpus(stat)
    exp["corpora"] = {k2: v for k2, v in sorted(stat.items()) if k2.startswith("partition_") or k2 == "union_docs"}
    exp["union_catalogue_docs"] = len(corp["ids"])
    print(f"  union catalogue: {len(corp['ids']):,} tools ("
          + ", ".join(f"{k2.split('_',1)[1]}={v:,}" for k2, v in sorted(stat.items())
                      if k2.startswith("partition_")) + ")", flush=True)
    rows = load_queries(args.per_subset, SEEDS[0], stat)
    print(f"  query rows selected: {len(rows):,} (seen {stat['query_rows_seen']:,})", flush=True)
    df = build(rows, corp, stat)
    print(f"  rows built: {len(df):,}  rejects: "
          f"{json.dumps({k2: v for k2, v in sorted(stat.items()) if k2.startswith('reject_')})}", flush=True)
    if len(df) < 200:
        raise SystemExit(f"ABORT: only {len(df)} usable rows - too few to score an AUROC honestly")
    exp["extraction"] = {"rows_seen": int(stat["query_rows_seen"]), "rows_selected": len(rows),
                         "rows_built": int(len(df)),
                         "rejection_accounting": {k2: v for k2, v in sorted(stat.items()) if k2.startswith("reject_")},
                         "tool_blob_issues": {k2: v for k2, v in sorted(stat.items()) if k2.startswith("tool_")}}
    exp["construct"] = {"n_candidates_mean": round(float(df.n_candidates.mean()), 1),
                        "n_candidates_min": int(df.n_candidates.min()), "n_candidates_max": int(df.n_candidates.max()),
                        "n_gold_mean": round(float(df.n_gold.mean()), 2),
                        "subsets": len(set(df.subset_name)),
                        "category_shares": {k2: int(v) for k2, v in Counter(df.category).most_common()}}
    src = pd.concat([pd.read_parquet(PROC / f"routing_{c}.parquet") for c in CONFIGS], ignore_index=True)
    src = src[(src.split == "dev") & (src.n_candidates > K)].reset_index(drop=True)
    Xs = matrices(src, FROZEN_FEATURES)["all"]
    exp["source"] = {"n_dev_rows": int(len(src)), "configs": list(CONFIGS),
                     "fail_at_3_prevalence": round(float(src[DV].mean()), 4)}
    exp["arms"] = []
    for arm in ("query", "instruction"):
        a = arm_frame(df, arm)
        model = scaled_pipeline(FROZEN_C)().fit(Xs, src[DV].values.astype(int))
        X = matrices(a, FROZEN_FEATURES)["all"]
        y = a[DV].values.astype(int)
        p = model.predict_proba(X)[:, 1]
        auc = float(roc_auc_score(y, p))
        rng = np.random.default_rng(SEEDS[0])
        boots = [roc_auc_score(y[i], p[i]) for i in
                 (rng.integers(0, len(y), size=(len(y),)) for _ in range(500)) if 0 < y[i].sum() < len(i)]
        lo, hi = (float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5)))
        # the honest dependence group here is the task subset: 35 corpora, each contributing many rows
        subsets = a.subset_name.values
        uniq = np.array(sorted(set(subsets)))
        crow = {s: np.where(subsets == s)[0] for s in uniq}
        cboot = []
        for _ in range(500):
            pick = rng.choice(uniq, size=len(uniq), replace=True)
            ii = np.concatenate([crow[s] for s in pick])
            if 0 < y[ii].sum() < len(ii):
                cboot.append(roc_auc_score(y[ii], p[ii]))
        clo, chi = (float(np.percentile(cboot, 2.5)), float(np.percentile(cboot, 97.5))) if cboot else (None, None)
        res = {"arm": arm, "n_rows": int(len(a)), "positives": int(y.sum()),
               "fail_at_3_prevalence": round(float(y.mean()), 4),
               "frozen_auroc": round(auc, 4), "row_bootstrap_ci95": [round(lo, 4), round(hi, 4)],
               "subset_clustered_ci95": [round(clo, 4), round(chi, 4)] if cboot else None,
               "verdict_by_frozen_bands": verdict(auc),
               "length_only_baseline": round(float(roc_auc_score(y, -a["n_chars"].values)), 4),
               "post_retrieval_margin_baseline": round(float(roc_auc_score(y, -a["bm25_margin"].values)), 4),
               "bm25_hit_at_3": round(float(1 - y.mean()), 4),
               "chance_hit_3_mean": round(float(a["chance_hit_3"].mean()), 6),
               "mean_n_candidates": round(float(a["n_candidates"].mean()), 1),
               "within_corpus_oof_aucroc": [round(float(v), 4) for v in
                                            oof_auc(X, y, scaled_pipeline(FROZEN_C), SEEDS[0])[:1]]}
        exp["arms"].append(res)
        print(f"  {arm}: n={res['n_rows']} pos={res['positives']} fail@3={res['fail_at_3_prevalence']} "
              f"AUROC={res['frozen_auroc']} rowCI={res['row_bootstrap_ci95']} "
              f"subsetCI={res['subset_clustered_ci95']} -> {res['verdict_by_frozen_bands']} "
              f"(length {res['length_only_baseline']}, margin {res['post_retrieval_margin_baseline']})", flush=True)
    pd.DataFrame(exp["arms"]).T.to_csv(OUT_PROC / "EXP0083_toolret_eval_arms.csv")
    per = (df.assign(**{("ok_" + a): (1 - df[f"{a}_fail_at_3"]) for a in ("query", "instruction")})
             .groupby(["category", "subset_name"])
             .agg(rows=("prompt_id", "size"), mean_candidates=("n_candidates", "mean"),
                  fail3_query=("query_fail_at_3", "mean"), fail3_inst=("instruction_fail_at_3", "mean"),
                  mean_rank=("query_bm25_best_rank", "mean")).reset_index())
    per.to_csv(OUT_PROC / "EXP0083_toolret_eval_per_subset.csv", index=False)
    exp["per_subset_file"] = "results_processed/EXP0083_toolret_eval_per_subset.csv"
    prim = exp["arms"][0]
    exp["what_this_answers"] = (
        f"the frozen predictor's ability to rank externally-failing rows ahead of hitting rows on a benchmark whose "
        f"candidate sets are production-scale (mean {prim['mean_n_candidates']:,.0f} tools per query, "
        f"{exp['construct']['subsets']} task subsets, {exp['construct']['category_shares']} by partition): "
        f"AUROC {prim['frozen_auroc']} with a subset-clustered interval "
        f"{prim['subset_clustered_ci95']}, against bands frozen at {BANDS['transfers']}/{BANDS['partial']}")
    exp["what_this_does_not_answer"] = [
        "the leaderboard: ToolRet reports nDCG@10 over per-subset corpora, this is pre-retrieval fail@3 over category "
        "corpora, so the two numbers are not comparable and neither is quoted against the other",
        "whether the benchmark's own candidate-selection convention was reproduced exactly - this step gives each "
        "query its whole category partition, which is a superset of any per-subset candidate list, so BM25 faces a "
        "harder task here than in the original protocol",
        "any claim about instruction-following behaviour: arm B is scored with the benchmark's target-aware "
        "instruction, which the paper says was generated with knowledge of the gold tools"]
    exp["wallclock_sec"] = round(time.time() - t0, 1)
    OUT_RAW.mkdir(parents=True, exist_ok=True)
    fp = OUT_RAW / f"EXP0083_toolret_eval_transfer_{time.strftime('%Y%m%dT%H%M%S')}.json"
    fp.write_text(json.dumps(exp, indent=1, ensure_ascii=False), encoding="utf-8", newline="")
    print(f"  wrote {fp.name} in {exp['wallclock_sec']}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
