"""
shared_dedup.py - AgentNet 原始轨迹记录按 task_id 去重的共享规则

原始两个轨迹文件共 22,625 行，唯一 task_id 22,532 个（官方 meta_data_merged.jsonl 恰为 22,532 条）。
93 个重复 id 中 91 个指令相同、76 个标签互相冲突（task_completed/alignment_score 等），
因此重复记录必须只保留一条，否则任务被重复计数、按 task_id 的 merge 会多对多膨胀。

裁决规则（与 src/reanalyze_full_data.py、src/03_parse_trajectories.py 保持一致）：
  1. 保留 traj 长度与官方 step_num 一致的记录（91/93 可由此唯一判定）；
  2. 无法唯一判定时保留末次出现。
被丢弃记录连同裁决理由写入 <interim_dir>/dedup_audit.json。
"""

import json
from pathlib import Path

META_PATH = Path("data/raw/meta_data_merged.jsonl")

RULE = ("keep the record whose traj length equals meta_data_merged.jsonl step_num; "
        "if not uniquely decidable keep the last occurrence")


def load_meta_stepnums(meta_path: Path = META_PATH) -> dict:
    meta = {}
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    m = json.loads(line)
                    sn = m.get("step_num")
                    if m.get("task_id") and isinstance(sn, int):
                        meta[m["task_id"]] = sn
    return meta


def dedup_records(records_with_meta, meta_stepnums: dict):
    """records_with_meta: [(record, payload), ...]，payload 为调用方需要随记录保留的任意对象（如 os 标签）。

    返回 (kept: [(record, payload)], dropped: [dict])，dropped 每项含裁决理由与重复记录的标签冲突清单。
    """
    by_id = {}
    order = []
    for rec, payload in records_with_meta:
        tid = rec.get("task_id", "")
        if tid not in by_id:
            order.append(tid)
            by_id[tid] = []
        by_id[tid].append((rec, payload))

    kept, dropped = [], []
    label_fields = ["task_completed", "alignment_score", "efficiency_score", "task_difficulty"]
    for tid in order:
        recs = by_id[tid]
        if len(recs) == 1:
            kept.append(recs[0])
            continue
        sn = meta_stepnums.get(tid)
        lens = [len(r.get("traj") or []) if isinstance(r.get("traj"), list) else None for r, _ in recs]
        matches = [i for i, l in enumerate(lens) if l is not None and sn is not None and l == sn]
        if len(matches) == 1:
            keep_idx, reason = matches[0], f"meta_step_num_match(step_num={sn})"
        elif len(matches) > 1:
            keep_idx, reason = matches[-1], f"meta_step_num_match_ambiguous_keep_last(step_num={sn})"
        else:
            keep_idx, reason = len(recs) - 1, "no_unique_step_num_match_keep_last"
        kept.append(recs[keep_idx])
        conflicts = {fld: [r.get(fld) for r, _ in recs] for fld in label_fields
                     if len({repr(r.get(fld)) for r, _ in recs}) > 1}
        for i in range(len(recs)):
            if i != keep_idx:
                dropped.append({
                    "task_id": tid, "dropped_index": i, "kept_index": keep_idx, "reason": reason,
                    "dropped_traj_len": lens[i], "labels_of_duplicates": conflicts or "identical"})
    return kept, dropped


def write_audit(interim_dir: Path, raw_count: int, kept_count: int, dropped: list):
    audit = {
        "raw_record_count": raw_count,
        "unique_task_count": kept_count,
        "dropped_count": len(dropped),
        "rule": RULE,
        "dropped": dropped,
    }
    interim_dir.mkdir(parents=True, exist_ok=True)
    with open(interim_dir / "dedup_audit.json", "w", encoding="utf-8") as f:
        json.dump(audit, f, ensure_ascii=False, indent=1)
    return audit
