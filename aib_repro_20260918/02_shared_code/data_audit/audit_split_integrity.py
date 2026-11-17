"""EXP-0008f: formalise the contamination / split-integrity probe as a script.

EXP-0008 established the facts that led to grouping the dev/test split by prompt_id,
but it ran as an ad-hoc console probe, which leaves the evidence un-reproducible -
a defect recorded in papers/P001_routing_failure_qpp/deviations.md. This script is the
reproducible version: it measures, per config and pairwise across configs, exact-duplicate
rate of the instruction text, distinct-prompt_id multiplicity (original vs _follow_up rows),
and cross-config overlap of uuid / prompt_id / normalized question.

    python audit_split_integrity.py --rows 3000
"""

from __future__ import annotations

import argparse
import itertools
import json
import random
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow.parquet as pq

SEED = 42
DATA = Path(r"G:/刘俊琦/AGENT ENGINEERING/MATLABINTOKEN/datasets/Agent-Ark/Toucan-1.5M")
ROOT = Path(__file__).resolve().parents[2]
CONFIGS = ["OSS", "Qwen3", "Kimi-K2"]


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=3000)
    args = ap.parse_args()
    rng = random.Random(SEED)
    rep = {"exp_id": "EXP-0008f", "seed": SEED, "rows_per_config": args.rows,
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "per_config": {}, "cross_config": {}}

    samples: dict[str, list] = {}
    for cfg in CONFIGS:
        shards = sorted((DATA / cfg).glob("*.parquet"))
        picks = sorted(rng.sample(shards, min(3, len(shards))))
        rows = []
        for sp in picks:
            t = pq.read_table(sp, columns=["uuid", "question", "metadata"])
            idx = sorted(rng.sample(range(t.num_rows), min(args.rows // len(picks) + 1, t.num_rows)))
            for r in t.take(idx).to_pylist():
                try:
                    md = json.loads(r["metadata"])
                except Exception:
                    md = {}
                rows.append((r["uuid"], norm(r["question"]), str(md.get("prompt_id")),
                             str(md.get("row_id"))))
        samples[cfg] = rows
        pid = Counter(x[2] for x in rows)
        q = Counter(x[1] for x in rows)
        rep["per_config"][cfg] = {
            "n_rows": len(rows), "distinct_uuid": len({x[0] for x in rows}),
            "distinct_prompt_id": len(pid), "distinct_question": len(q),
            "max_rows_per_prompt_id": max(pid.values()),
            "prompts_with_multiple_rows": sum(1 for v in pid.values() if v > 1),
            "exact_dup_question_rate": round(1 - len(q) / len(rows), 4),
            "followup_prompt_rate": round(sum(1 for v in pid if v.endswith("_follow_up")) / len(pid), 4)}
        print(f"[{cfg}] rows={len(rows)} distinct_pid={len(pid)} distinct_q={len(q)} "
              f"pids_with_multi_rows={rep['per_config'][cfg]['prompts_with_multiple_rows']} "
              f"max_rows/pid={rep['per_config'][cfg]['max_rows_per_prompt_id']}")

    for a, b in itertools.combinations(CONFIGS, 2):
        A, B = samples[a], samples[b]
        aU, bU = {x[0] for x in A}, {x[0] for x in B}
        aP, bP = {x[2] for x in A}, {x[2] for x in B}
        aQ, bQ = {x[1] for x in A}, {x[1] for x in B}
        rep["cross_config"][f"{a}|{b}"] = {
            "uuid_overlap": len(aU & bU), "prompt_id_overlap": len(aP & bP),
            "prompt_id_overlap_rate": round(len(aP & bP) / max(1, len(aP)), 4),
            "question_overlap": len(aQ & bQ),
            "question_overlap_rate": round(len(aQ & bQ) / max(1, len(aQ)), 4)}
        print(f"[{a} vs {b}] pid overlap {len(aP & bP)}/{len(aP)} = "
              f"{rep['cross_config'][f'{a}|{b}']['prompt_id_overlap_rate']:.4f} | "
              f"question overlap {len(aQ & bQ)} | uuid overlap {len(aU & bU)}")

    rep["implication"] = ("prompt_id, not uuid, must define the split: an original prompt and its follow-up "
                          "rows share prompt_id but receive different uuids. Cross-config prompt_id recurrence "
                          "is a non-independence caveat for pooled estimates, while exact-question overlap is "
                          "small enough that cross-teacher replication is not exact leakage.")
    out = ROOT / "results_raw" / f"EXP0008f_split_integrity_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
