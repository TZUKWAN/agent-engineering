"""
01_parse_agentnet.py - 解析 AgentNet 原始轨迹数据（论文四专用）

读取 data/raw/ 下的 agentnet_*.jsonl 文件，保留 thought/reflection/action/observation
等显式推理链相关字段，输出到 data/interim/paper04/。
"""

import os
import json
import pandas as pd
from pathlib import Path
from datetime import datetime

RAW_DIR = Path("data/raw")
INTERIM_DIR = Path("data/interim/paper04")
INTERIM_DIR.mkdir(parents=True, exist_ok=True)


def infer_os(filepath: str) -> str:
    """根据文件名推断操作系统"""
    name = os.path.basename(filepath).lower()
    if "ubuntu" in name:
        return "ubuntu"
    if "win_mac" in name or "winmac" in name:
        return "win_mac"
    return "unknown"


def read_jsonl_records(filepath: str):
    records = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def extract_task_info(record: dict, os_label: str):
    return {
        "task_id": record.get("task_id"),
        "instruction": record.get("instruction", ""),
        "natural_language_task": record.get("natural_language_task", ""),
        "actual_task": record.get("actual_task", ""),
        "task_completed": record.get("task_completed"),
        "alignment_score": record.get("alignment_score"),
        "efficiency_score": record.get("efficiency_score"),
        "task_difficulty": record.get("task_difficulty"),
        "reason": record.get("reason", ""),
        "domain": record.get("domain", ""),
        "os": os_label,
    }


def extract_step_info(step: dict, task_id: str, step_index: int):
    value = step.get("value", {}) if isinstance(step.get("value"), dict) else {}
    return {
        "task_id": task_id,
        "step_index": step_index,
        "observation": value.get("observation", ""),
        "thought": value.get("thought", ""),
        "action": value.get("action", ""),
        "code": value.get("code", ""),
        "reflection": value.get("reflection", ""),
        "last_step_correct": value.get("last_step_correct"),
        "last_step_redundant": value.get("last_step_redundant"),
    }


def main():
    print("=" * 60)
    print("论文四：解析 AgentNet 轨迹数据")
    print("=" * 60)

    files = sorted(RAW_DIR.glob("agentnet_*.jsonl"))
    if not files:
        print(f"未在 {RAW_DIR} 找到 agentnet_*.jsonl 文件")
        return 1

    # 先收集全部记录，按 task_id 去重（原始文件含 93 个重复 id，标签互相冲突）
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from shared_dedup import load_meta_stepnums, dedup_records, write_audit

    collected = []
    for filepath in files:
        os_label = infer_os(str(filepath))
        print(f"\n读取: {filepath.name} (os={os_label})")
        records = read_jsonl_records(str(filepath))
        print(f"  记录数: {len(records)}")
        collected.extend((rec, os_label) for rec in records)

    raw_count = len(collected)
    kept, dropped = dedup_records(collected, load_meta_stepnums())
    write_audit(INTERIM_DIR, raw_count, len(kept), dropped)
    print(f"  去重: {raw_count} -> {len(kept)} (丢弃 {len(dropped)} 条重复记录)")

    all_tasks = []
    all_steps = []
    for rec, os_label in kept:
        task = extract_task_info(rec, os_label)
        task_id = task["task_id"]
        all_tasks.append(task)

        traj = rec.get("traj", []) or []
        for j, step in enumerate(traj):
            all_steps.append(extract_step_info(step, task_id, j))

    tasks_df = pd.DataFrame(all_tasks)
    steps_df = pd.DataFrame(all_steps)

    tasks_path = INTERIM_DIR / "tasks.parquet"
    steps_path = INTERIM_DIR / "steps.parquet"
    tasks_df.to_parquet(tasks_path)
    steps_df.to_parquet(steps_path)

    print(f"\n总计: {len(tasks_df)} 个任务, {len(steps_df)} 个步骤")
    print(f"任务数据保存: {tasks_path}")
    print(f"步骤数据保存: {steps_path}")

    report = {
        "timestamp": datetime.now().isoformat(),
        "total_tasks": len(tasks_df),
        "total_steps": len(steps_df),
        "tasks_with_trajectory": int((tasks_df["task_id"].isin(steps_df["task_id"])).sum()),
    }
    with open(INTERIM_DIR / "parse_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
