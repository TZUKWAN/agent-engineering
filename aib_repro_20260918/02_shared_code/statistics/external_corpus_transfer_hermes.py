"""EXP-0023 (E08, decisive arm): transfer of the frozen pre-retrieval model to an INDEPENDENT corpus.

EXP-0022 scanned the eight local corpora for a per-query candidate-tool catalogue and found exactly
one outside Toucan: lambda/hermes-agent-reasoning-traces, whose trajectories carry a `tools` JSON
array plus the assistant's own invocations encoded as <tool_call>{"name": ...}
inside the `gpt` messages. Unlike the Toucan `SFT` config (EXP-0021 measured that it reuses 100% of
the source tool names), hermes is a DIFFERENT tool universe - a fixed coding-agent toolbox
(patch, process, read_file, search_files, terminal, write_file, ...) collected by a different pipeline
from a different model family - so a model fitted on Toucan and scored here faces tools it has never
seen in any form. That is the measurement D13 could only bound.

Discipline
  * the source is the three published DEV splits only; the published test split is not read here;
  * hermes rows are never used for fitting, feature selection or threshold choice, so nothing in the
    frozen configuration can have been tuned on them;
  * features are produced by the SAME frozen functions as the published dataset (question_features,
    collection_qpp_features, BM25 k1=1.4 b=0.4, toks), so a difference in AUROC cannot be a pipeline
    artifact;
  * gold = the tool the reference model actually invoked, which is also what Toucan's target_tools
    records; the DV (BM25 misses the gold tool in its top 3) is therefore the same construct;
  * extraction rejects are reported, not silently dropped.

    python external_corpus_transfer_hermes.py [--shard-rows 6000]

Outputs results_raw/EXP0023_hermes_transfer_*.json, results_processed/EXP0023_hermes_*.csv,
        01_datasets/processed/routing_HERMES.parquet, logs/EXP-0023_hermes_transfer.txt
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import re
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "trajectory_parser"))
from analyze_routing_failure import CONFIGS, PROC, SEEDS, oof_auc, scaled_pipeline  # noqa: E402
from build_toucan_routing_dataset import (BM25, collection_qpp_features, hyper_chance,  # noqa: E402
                                          question_features, toks)
from run_p001_experiments import FROZEN_C, FROZEN_FEATURES, matrices  # noqa: E402

HERMES = Path(r"G:/刘俊琦/AGENT ENGINEERING/MATLABINTOKEN/datasets/lambda/hermes-agent-reasoning-traces")
K = 3
DV = "fail_at_3"
OUT_RAW = HERE.parents[1] / "results_raw"
OUT_PROC = HERE.parents[1] / "results_processed"
# the assistant turn's invocation blocks; DOTALL because the JSON payload is pretty-printed
CALL_RE = re.compile("<" + r"tool_call" + r"\s*>\s*(\{.*?\})\s*<" + r"/tool_call" + r">", re.S)


def build(shard_rows: int) -> tuple[pd.DataFrame, dict]:
    files = [f for f in sorted(glob.glob(str(HERMES / "**/*.parquet"), recursive=True)) if ".cache" not in f]
    stat, kept = Counter(), []
    bm = BM25()
    for f in files:
        tbl = pq.read_table(f, columns=["id", "conversations", "tools", "category", "task"])
        for r in tbl.slice(0, min(shard_rows, tbl.num_rows)).to_pylist():
            stat["rows_seen"] += 1
            try:
                raw_cat = json.loads(r["tools"]) if isinstance(r["tools"], str) else r["tools"]
            except Exception:
                stat["reject_catalog_unparseable"] += 1
                continue
            catalog = [{"name": str(d.get("name")), "desc": str(d.get("description") or ""),
                        "params": list(((d.get("parameters") or {}).get("properties") or {}).keys())}
                       for d in raw_cat if isinstance(d, dict) and d.get("name")]
            if not catalog:
                stat["reject_catalog_empty"] += 1
                continue
            by_name = {d["name"]: i for i, d in enumerate(catalog)}
            calls = []
            for m in r["conversations"]:
                if m.get("from") != "gpt":
                    continue
                for blk in CALL_RE.findall(str(m.get("value"))):
                    try:
                        nm = json.loads(blk).get("name")
                    except Exception:
                        stat["reject_call_block_unparseable"] += 1
                        continue
                    if nm:
                        calls.append(str(nm))
            if not calls:
                stat["reject_no_invocation_parsed"] += 1
                continue
            idx = sorted({by_name[c] for c in calls if c in by_name})
            if not idx:
                stat["reject_gold_not_in_own_catalog"] += 1
                continue
            q = str(r.get("task") or "")
            if not q.strip():
                stat["reject_empty_instruction"] += 1
                continue
            qtok = toks(q)
            docs_full = [toks(d["name"].replace("-", " ").replace("_", " ")) + toks(d["desc"])
                         + toks(" ".join(d["params"])) for d in catalog]
            docs_desc = [toks(d["desc"]) for d in catalog]
            sc_full, sc_desc = bm.scores(qtok, docs_full), bm.scores(qtok, docs_desc)
            ranked_full = sorted(range(len(sc_full)), key=lambda i: -sc_full[i])
            ranked_desc = sorted(range(len(sc_desc)), key=lambda i: -sc_desc[i])
            srt = sorted(sc_full, reverse=True)
            margin = (srt[0] - srt[1]) if len(srt) > 1 else (srt[0] if srt else 0.0)
            n_c = len(catalog)
            rb = min((ranked_full.index(i) + 1 for i in idx), default=n_c)
            rb_desc = min((ranked_desc.index(i) + 1 for i in idx), default=n_c)
            kept.append({"uuid": str(r["uuid"]) if "uuid" in r else str(r["id"]),
                         "cfg": "HERMES", "subset_name": str(r.get("category") or ""),
                         "prompt_id": str(r["id"]), "split": "external",
                         "n_candidates": n_c, "n_gold": len(idx), "gold_idx": json.dumps(idx),
                         "bm25_best_rank": rb, "bm25_desc_best_rank": rb_desc,
                         "bm25_top1_score": round(max(sc_full) if sc_full else 0.0, 6),
                         "bm25_margin": round(margin, 6),
                         "norm_rank": (rb - 1) / max(1, n_c - 1),
                         "fail_at_1": int(rb > 1), "fail_at_3": int(rb > 3), "fail_at_5": int(rb > 5),
                         "chance_hit_1": hyper_chance(len(idx), n_c, 1),
                         "chance_hit_3": hyper_chance(len(idx), n_c, 3),
                         "chance_hit_5": hyper_chance(len(idx), n_c, 5),
                         "n_servers_in_row": 0, "question": q[:4000],
                         "catalog_json": json.dumps([{"n": d["name"], "d": d["desc"], "p": d["params"]}
                                                     for d in catalog], ensure_ascii=False),
                         **collection_qpp_features(qtok, docs_full), **question_features(q)})
    df = pd.DataFrame(kept)
    return df, dict(stat)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard-rows", type=int, default=6000)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    exp = {"exp_id": "EXP-0023", "e_id": "E08", "seed": SEEDS[0], "k": K, "dv": DV,
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S")}

    ext, stat = build(args.shard_rows)
    exp["corpus_extraction"] = {"rows_seen": stat.get("rows_seen", 0), "rows_kept": int(len(ext)),
                                "rejection_accounting": {k: v for k, v in sorted(stat.items())
                                                         if k.startswith("reject_")}}
    ext = ext[ext.n_candidates > K].reset_index(drop=True)
    exp["corpus_after_inclusion_rule"] = {
        "n_rows": int(len(ext)), "fail_at_3_prevalence": round(float(ext[DV].mean()), 4),
        "n_positives": int(ext[DV].sum()), "chance_hit_3": round(float(ext.chance_hit_3.mean()), 4),
        "mean_catalogue": round(float(ext.n_candidates.mean()), 2),
        "distinct_catalogues": int(ext.catalog_json.nunique()),
        "mean_instruction_tokens": round(float(ext.n_tokens.mean()), 1),
        "categories": {k: int(v) for k, v in Counter(ext.subset_name).most_common(8)}}
    print(f"hermes rows kept={len(ext)}  fail@3 prevalence={exp['corpus_after_inclusion_rule']['fail_at_3_prevalence']}"
          f"  distinct catalogues={exp['corpus_after_inclusion_rule']['distinct_catalogues']}")

    src = pd.concat([pd.read_parquet(PROC / f"routing_{c}.parquet") for c in CONFIGS], ignore_index=True)
    src = src[(src.split == "dev") & (src.n_candidates > K)].reset_index(drop=True)
    Xs = matrices(src, FROZEN_FEATURES)["all"]
    model = scaled_pipeline(FROZEN_C)().fit(Xs, src[DV].values.astype(int))

    Xe = matrices(ext, FROZEN_FEATURES)["all"]
    ye = ext[DV].values.astype(int)
    p_ext = model.predict_proba(Xe)[:, 1]
    auc_ext = float(roc_auc_score(ye, p_ext))
    # cluster bootstrap on the catalogue, which here is nearly a single cluster -> also report the
    # row-level interval and say which is which instead of quoting whichever looks better
    rng = np.random.default_rng(42)
    boots = [roc_auc_score(ye[i], p_ext[i]) for i in
             (rng.integers(0, len(ye), size=(len(ye),)) for _ in range(500))
             if 0 < ye[i].sum() < len(i)]
    within = [oof_auc(Xe, ye, scaled_pipeline(FROZEN_C), s)[0] for s in SEEDS]

    overlap_names = {d["n"] for cj in src.catalog_json for d in json.loads(cj)}
    ext_names = {d["n"] for cj in ext.catalog_json for d in json.loads(cj)}
    src_toks = set()
    for cj in src.catalog_json:
        for d in json.loads(cj):
            src_toks.update(toks(d["n"].replace("-", " ").replace("_", " ")) + toks(d["d"])
                            + toks(" ".join(d["p"])))
    tt = Counter()
    for cj in ext.catalog_json:
        for d in json.loads(cj):
            for t in toks(d["n"].replace("-", " ").replace("_", " ")) + toks(d["d"]) + toks(" ".join(d["p"])):
                tt[t] += 1
    tot = sum(tt.values()) or 1
    exp["independence_audit"] = {
        "external_tool_names": len(ext_names),
        "names_also_in_source": len(ext_names & overlap_names),
        "unseen_tool_name_share": round(1 - len(ext_names & overlap_names) / max(1, len(ext_names)), 4),
        "external_catalog_tokens_covered_by_source": round(
            sum(v for t, v in tt.items() if t in src_toks) / tot, 4)}
    strata = []
    for cat, g in ext.groupby("subset_name"):
        yg = g[DV].values.astype(int)
        if len(g) < 50 or 0 < yg.sum() < len(yg):
            pg = model.predict_proba(matrices(g, FROZEN_FEATURES)["all"])[:, 1]
            strata.append({"category": cat, "n": int(len(g)), "positives": int(yg.sum()),
                           "auc_transfer": round(float(roc_auc_score(yg, pg)), 4),
                           "auc_length_only": round(float(roc_auc_score(yg, -g.n_tokens.values)), 4)})
    exp["per_category"] = strata
    exp["transfer"] = {
        "auc_source_dev_to_hermes": round(auc_ext, 4),
        "ci95_row_bootstrap": [round(float(np.percentile(boots, q)), 4) for q in (2.5, 97.5)],
        "auc_within_hermes_oof": [round(a, 4) for a in within],
        "auc_source_reference_oof_dev": round(float(np.mean(
            [oof_auc(Xs, src[DV].values.astype(int), scaled_pipeline(FROZEN_C), s)[0] for s in SEEDS])), 4),
        "auc_hermes_length_only_B0": round(float(roc_auc_score(ye, -ext.n_tokens.values)), 4),
        "auc_hermes_post_retrieval_margin": round(float(roc_auc_score(ye, -ext.bm25_margin.values)), 4),
        "auc_hermes_idf_coverage_only": round(float(roc_auc_score(ye, ext.qpp_idf_weighted_coverage.values)), 4),
        "verdict": ("transfers" if auc_ext >= 0.65 else "partial" if auc_ext >= 0.55
                    else "does not transfer"),
        "beats_length_baseline": bool(auc_ext > float(roc_auc_score(ye, -ext.n_tokens.values))),
        "ci_note": "interval is a ROW bootstrap because this corpus has only "
                   f"{exp['corpus_after_inclusion_rule']['distinct_catalogues']} distinct catalogues, "
                   "so a catalogue-clustered interval is not estimable here; disclosed rather than hidden"}
    exp["wallclock_sec"] = round(time.time() - t0, 1)
    exp["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")

    OUT_RAW.mkdir(parents=True, exist_ok=True)
    ext["uuid_digest"] = "hermes-" + str(abs(hash(tuple(ext.uuid))) % 10 ** 16)
    ext.to_parquet(PROC / "routing_HERMES.parquet", index=False)
    out = OUT_RAW / f"EXP0023_hermes_transfer_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(exp, indent=1, ensure_ascii=False), encoding="utf-8")
    pd.DataFrame(strata).to_csv(OUT_PROC / "EXP0023_hermes_per_category.csv", index=False)
    print("independence:", exp["independence_audit"])
    print(f"[E08] hermes transfer AUROC={exp['transfer']['auc_source_dev_to_hermes']} "
          f"CI{exp['transfer']['ci95_row_bootstrap']} within-hermes OOF={np.mean(within):.4f} "
          f"length-only={exp['transfer']['auc_hermes_length_only_B0']} -> {exp['transfer']['verdict']}")
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
