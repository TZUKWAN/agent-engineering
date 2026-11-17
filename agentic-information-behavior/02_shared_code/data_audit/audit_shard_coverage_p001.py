"""EXP-0034 (P001): does the published sample's shard coverage bias the outcome it reports?

Found while auditing our own limitation text. P001 says the routing sample is "15,000 rows/config from 10 shards",
and the registered command does pick 10 shards at random - but the row loop stops as soon as 15,000 rows are
collected, so only the FIRST 2 picked shards are ever read (measured: OSS 9,727+5,273 of 97,264 rows in the picked
pool; Qwen3 and Kimi-K2 likewise 2 of 10). Rows within those 2 files ARE drawn at random, so the standing
"head-of-shard" wording in P001's limitations is wrong about the mechanism. The real question is narrower and
answerable: do the 8 files that contribute nothing differ from the 2 that do?

Pre-registered decision rule, fixed before any comparison was computed:
  primary quantity = BM25 fail@3, scored by the same frozen code path that produced the published column;
  consumed vs un-consumed groups are compared with a prompt_id-clustered bootstrap CI on the difference;
  SHARD_COVERAGE_BIASED iff |difference| >= 1.0 pp AND the CI excludes 0; otherwise the coverage concern is
  answered on the measured quantities and stays a stated (but empirically inert) limitation.
Secondary, descriptive only: rejection rate, catalogue size, question length, the frozen linguistic feature
battery, and a contamination count of prompt_ids shared with the published dataset.

No row of the published test split is re-evaluated here: the un-consumed files were never part of any split.

    python 02_shared_code/data_audit/audit_shard_coverage_p001.py

Writes results_raw/EXP0034_shard_coverage_*.json and results_processed/EXP0034_shard_coverage.csv.
"""
from __future__ import annotations

import json, random, re, sys, time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "02_shared_code" / "trajectory_parser"))
import build_toucan_routing_dataset as B          # frozen scoring path, not a reimplementation

DATA = B.DATA
CONFIGS = ["OSS", "Qwen3", "Kimi-K2"]
SEED, ROWS_PER_CFG, DEV_BUCKET = 42, 15000, 700
N_PER_GROUP = 3000
OUT_RAW, OUT_PROC = ROOT / "results_raw", ROOT / "results_processed"


def consumed_files(picks):
    """Replicate the builder's fill rule: walk the picked shards, stop once 15k rows are covered."""
    used, need = [], ROWS_PER_CFG
    for p in picks:
        if need <= 0:
            break
        used.append(p)
        need -= pq.ParquetFile(p).metadata.num_rows
    return used


def score_group(files, per_file, col):
    rows = []
    rej = {"unparseable": 0, "no_gold": 0, "unresolved": 0}
    for f in files:
        tbl = pq.read_table(f, columns=[c for c in ["uuid", "question", col, "target_tools", "metadata",
                                                     "subset_name"]
                                        if c in pq.ParquetFile(f).schema_arrow.names])
        take = sorted(random.Random(SEED).sample(range(tbl.num_rows), min(per_file, tbl.num_rows)))
        for r in tbl.take(take).to_pylist():
            catalog = B.parse_catalog(r[col])
            if not catalog:
                rej["unparseable"] += 1
                continue
            items = [x.strip() for x in re.split(r",(?![^{]*\})", str(r["target_tools"] or "")) if x.strip()]
            if not items:
                rej["no_gold"] += 1
                continue
            srv_idx, srv_slugs = B.server_tool_index(r.get("metadata"))
            matched, why = B.resolve_gold_v2(items, catalog, srv_idx, srv_slugs)
            if matched is None:
                rej["unresolved"] += 1
                continue
            q = r["question"]
            qtok = B.toks(q)
            docs = [B.toks(d["name"].replace("-", " ").replace("_", " ")) + B.toks(d["desc"])
                    + B.toks(" ".join(d["params"])) for d in catalog]
            sc = B.BM25().scores(qtok, docs)
            ranked = sorted(range(len(sc)), key=lambda i: -sc[i])
            rb = min((ranked.index(i) + 1 for i in matched), default=len(catalog))
            try:
                pid = str(json.loads(r["metadata"]).get("prompt_id") or r["uuid"])
            except Exception:
                pid = str(r["uuid"])
            rows.append({"uuid": r["uuid"], "prompt_id": pid,
                         "file": Path(f).name, "fail_at_3": int(rb > 3), "n_candidates": len(catalog),
                         "n_gold": len(matched), "q_chars": len(str(q)),
                         "bm25_top1": round(max(sc) if sc else 0.0, 6),
                         **B.question_features(q)})
        del tbl
    return pd.DataFrame(rows), rej


def clustered_diff(a, b, draws=2000):
    """Bootstrap CI for mean(a) - mean(b), resampling prompt_ids (the catalogue/cue unit)."""
    out = []
    for df in (a, b):
        df["_g"] = df.prompt_id.astype(str)
    ga = [grp.to_numpy() for _, grp in a.groupby("_g").fail_at_3]
    gb = [grp.to_numpy() for _, grp in b.groupby("_g").fail_at_3]
    rng = np.random.default_rng(SEED)
    for _ in range(draws):
        sa = np.concatenate([ga[i] for i in rng.choice(len(ga), len(ga), True)])
        sb = np.concatenate([gb[i] for i in rng.choice(len(gb), len(gb), True)])
        out.append(sa.mean() - sb.mean())
    return [round(float(np.percentile(out, 2.5)) * 100, 3), round(float(np.percentile(out, 97.5)) * 100, 3)]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    res = {"exp_id": "EXP-0034", "paper_id": "P001", "seed": SEED, "rows_per_group": N_PER_GROUP,
           "rule": "BIASED iff |fail@3 gap| >= 1.0 pp and prompt_id-clustered CI excludes 0",
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "configs": {}}
    feats = ["constraint_density", "n_subtasks_by_punctuation", "imperative_start", "vague_word_n"]
    for cfg in CONFIGS:
        col = B.CONFIGS[cfg]
        picks = sorted(random.Random(SEED).sample(sorted((DATA / cfg).glob("*.parquet")), 10))
        used = consumed_files(picks)
        unused = [p for p in picks if p not in used]
        pub = pd.read_parquet(ROOT / "01_datasets" / "processed" / f"routing_{cfg}.parquet")
        groups, frames = {}, {}
        for name, fl in (("consumed", used), ("un_consumed", unused)):
            per = max(1, N_PER_GROUP // len(fl))
            df, rej = score_group(fl, per, col)
            frames[name] = df
            dev = df[df.prompt_id.map(B.bucket) < DEV_BUCKET]
            groups[name] = {"files": len(fl), "rows_scored": int(len(df)), "rows_dev": int(len(dev)),
                            "rejects": rej,
                            "fail_at_3_dev": round(float(dev.fail_at_3.mean()), 4),
                            "mean_n_candidates": round(float(df.n_candidates.mean()), 2),
                            "mean_n_gold": round(float(df.n_gold.mean()), 3),
                            "mean_q_chars": round(float(df.q_chars.mean()), 1),
                            "mean_bm25_top1": round(float(df.bm25_top1.mean()), 4),
                            "features": {f: round(float(df[f].mean()), 5) for f in feats if f in df},
                            "prompt_ids": int(df.prompt_id.nunique())}
        a, b = frames["consumed"], frames["un_consumed"]
        gap = round((float(a.fail_at_3.mean()) - float(b.fail_at_3.mean())) * 100, 3)
        ci = clustered_diff(a, b)
        shared = len(set(a.prompt_id) & set(pub.prompt_id.astype(str)))
        res["configs"][cfg] = {**groups, "gap_consumed_minus_unconsumed_pp": gap, "ci95_prompt_clustered_pp": ci,
                               "published_dev_fail_at_3": round(float(pub[pub.split == "dev"].fail_at_3.mean()), 4),
                               "prompt_ids_shared_with_published": shared}
        print(f"  {cfg}: consumed {[Path(p).name for p in used]} -> fail@3 {groups['consumed']['fail_at_3_dev']} "
              f"vs un-consumed {groups['un_consumed']['fail_at_3_dev']}; gap {gap} pp CI {ci}")
    gaps = [abs(v["gap_consumed_minus_unconsumed_pp"]) for v in res["configs"].values()]
    excl = [v["ci95_prompt_clustered_pp"][0] > 0 or v["ci95_prompt_clustered_pp"][1] < 0
            for v in res["configs"].values()]
    res["verdict"] = {"max_abs_gap_pp": max(gaps), "any_ci_excludes_zero": any(excl),
                      "decision": ("SHARD_COVERAGE_BIASED" if (max(gaps) >= 1.0 and any(excl))
                                   else "coverage gap measured and inert on the primary outcome")}
    res["wallclock_sec"] = round(time.time() - t0, 1)
    res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    OUT_RAW.mkdir(exist_ok=True)
    out = OUT_RAW / f"EXP0034_shard_coverage_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    pd.DataFrame([{"cfg": c, "group": g, **{k: v for k, v in d.items() if not isinstance(v, dict)},
                   **{f"feat_{k}": v for k, v in d.get("features", {}).items()}}
                  for c, v in res["configs"].items() for g, d in v.items()
                  if g in ("consumed", "un_consumed")]).to_csv(OUT_PROC / "EXP0034_shard_coverage.csv", index=False)
    print(json.dumps(res["verdict"], ensure_ascii=False))
    print("wrote", out, f"({res['wallclock_sec']}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
