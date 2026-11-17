"""
03_parse_trajectories.py - 解析轨迹数据

读取原始轨迹数据，提取任务和轨迹信息
"""

import os
import json
import pandas as pd
from pathlib import Path
from datetime import datetime


def load_inspection_results():
    """加载文件检查结果"""
    inspection_path = "data/interim/file_inspection.json"
    if os.path.exists(inspection_path):
        with open(inspection_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def read_data_file(filepath):
    """根据文件类型读取数据"""
    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".json":
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    elif ext == ".jsonl":
        records = []
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records
    elif ext == ".parquet":
        df = pd.read_parquet(filepath)
        return df.to_dict("records")
    elif ext == ".csv":
        df = pd.read_csv(filepath)
        return df.to_dict("records")
    else:
        return None


def extract_task_info(record):
    """从记录中提取任务信息"""
    task_info = {}

    # 尝试常见的字段名
    field_mapping = {
        "task_id": ["task_id", "id", "task", "sample_id"],
        "instruction": ["instruction", "prompt", "query", "user_input"],
        "natural_language_task": ["natural_language_task", "task_description", "task", "goal"],
        "actual_task": ["actual_task", "ground_truth", "true_task"],
        "task_completed": ["task_completed", "completed", "success", "is_success"],
        "alignment_score": ["alignment_score", "align_score", "alignment"],
        "efficiency_score": ["efficiency_score", "eff_score", "efficiency"],
        "task_difficulty": ["task_difficulty", "difficulty", "level"],
        "OS": ["OS", "os", "platform", "system"],
        "traj": ["traj", "trajectory", "steps", "history"],
    }

    for target_field, possible_names in field_mapping.items():
        for name in possible_names:
            if name in record:
                task_info[target_field] = record[name]
                break

    # 如果traj是字符串，尝试解析
    if "traj" in task_info and isinstance(task_info["traj"], str):
        try:
            task_info["traj"] = json.loads(task_info["traj"])
        except:
            pass

    return task_info


def extract_step_info(step):
    """从步骤中提取信息"""
    # AgentNet 的步级字段嵌套在 value 里；直接读顶层会得到全 None 的列
    value = step.get("value") if isinstance(step.get("value"), dict) else {}
    step = {**{k: v for k, v in step.items() if k != "value"}, **value}
    step_info = {}

    field_mapping = {
        "index": ["index", "step_idx", "id", "num"],
        "observation": ["observation", "obs", "state"],
        "thought": ["thought", "reasoning", "thinking"],
        "action": ["action", "act", "operation"],
        "code": ["code", "script", "program"],
        "last_step_correct": ["last_step_correct", "correct", "is_correct"],
        "last_step_redundant": ["last_step_redundant", "redundant", "is_redundant"],
        "reflection": ["reflection", "feedback", "review"],
    }

    for target_field, possible_names in field_mapping.items():
        for name in possible_names:
            if name in step:
                step_info[target_field] = step[name]
                break

    return step_info


def parse_records(records):
    """解析记录列表"""
    tasks = []
    all_steps = []

    for i, record in enumerate(records):
        task_info = extract_task_info(record)

        # 确保有task_id
        if "task_id" not in task_info:
            task_info["task_id"] = f"task_{i}"

        tasks.append(task_info)

        # 解析轨迹
        if "traj" in task_info and task_info["traj"]:
            traj = task_info["traj"]
            if isinstance(traj, list):
                for j, step in enumerate(traj):
                    step_info = extract_step_info(step)
                    step_info["task_id"] = task_info["task_id"]
                    step_info["step_index"] = j
                    all_steps.append(step_info)

    return tasks, all_steps


def load_meta_stepnums():
    """官方 meta_data_merged.jsonl 的 {task_id: step_num}，作为重复记录的裁决基准"""
    meta_path = "data/raw/meta_data_merged.jsonl"
    meta = {}
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    r = json.loads(line)
                    sn = r.get("step_num")
                    if r.get("task_id") is not None and isinstance(sn, int):
                        meta[r["task_id"]] = sn
    return meta


def dedup_records(all_records, meta_stepnums):
    """按 task_id 去重：保留 traj 长度与官方 meta.step_num 一致的记录；无法唯一判定时保留末次出现。

    返回 (kept_records, audit_list)。audit_list 记录每个被丢弃记录的裁决理由与标签冲突情况，
    这是原始文件含 93 个重复 task_id（且 76 个标签互相冲突）时的审计痕迹。
    """
    by_id = {}
    for rec in all_records:
        if not isinstance(rec, dict) or not isinstance(rec.get("traj"), list):
            continue                                                  # 非轨迹记录（meta/download 索引等）不参与
        by_id.setdefault(rec.get("task_id"), []).append(rec)

    kept, dropped = [], []
    for tid, recs in by_id.items():
        if len(recs) == 1:
            kept.append(recs[0])
            continue
        sn = meta_stepnums.get(tid)
        lens = [len(r.get("traj")) if isinstance(r.get("traj"), list) else None for r in recs]
        matches = [i for i, l in enumerate(lens) if l is not None and sn is not None and l == sn]
        if len(matches) == 1:
            keep_idx, reason = matches[0], f"meta_step_num_match(step_num={sn})"
        elif len(matches) > 1:
            keep_idx, reason = matches[-1], f"meta_step_num_match_ambiguous_keep_last(step_num={sn})"
        else:
            keep_idx, reason = len(recs) - 1, "no_unique_step_num_match_keep_last"
        kept.append(recs[keep_idx])
        label_fields = ["task_completed", "alignment_score", "efficiency_score", "task_difficulty"]
        conflicts = {f: [r.get(f) for r in recs] for f in label_fields
                     if len({repr(r.get(f)) for r in recs}) > 1}
        for i, r in enumerate(recs):
            if i != keep_idx:
                dropped.append({
                    "task_id": tid,
                    "dropped_index": i,
                    "kept_index": keep_idx,
                    "reason": reason,
                    "dropped_traj_len": lens[i],
                    "labels_of_duplicates": conflicts or "identical",
                })
    return kept, dropped


def main():
    """主函数"""
    print("=" * 60)
    print("解析轨迹数据")
    print("=" * 60)

    # 查找数据文件
    inspection = load_inspection_results()

    if inspection is None:
        print("\n未找到文件检查结果，先查找数据文件...")
        import importlib.util
        spec = importlib.util.spec_from_file_location("inspect_files", "src/02_inspect_files.py")
        inspect_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(inspect_module)
        data_files = inspect_module.find_data_files()
    else:
        data_files = [f["file"] for f in inspection.get("files", []) if f.get("readable")]

    if not data_files:
        print("未找到可读的数据文件")
        return 1

    # 先读取全部原始记录，按 task_id 去重后再解析轨迹
    all_records = []
    for filepath in data_files:
        print(f"\n读取: {os.path.basename(filepath)}")

        try:
            records = read_data_file(filepath)
            if records is None:
                print("  跳过: 无法读取")
                continue

            if isinstance(records, dict):
                # 如果是单个字典，尝试找到记录列表
                for key, value in records.items():
                    if isinstance(value, list) and value:
                        records = value
                        break

            if not isinstance(records, list):
                print("  跳过: 不是记录列表")
                continue

            print(f"  记录数: {len(records)}")
            if "agentnet" not in os.path.basename(filepath).lower():
                print("  跳过: 非轨迹数据文件（仅索引/元数据）")
                continue
            all_records.extend(records)

        except Exception as e:
            print(f"  错误: {e}")

    meta_stepnums = load_meta_stepnums()
    raw_count = len(all_records)
    all_records, dropped = dedup_records(all_records, meta_stepnums)
    print(f"\n原始记录: {raw_count}; 唯一 task_id: {len(all_records)}; 丢弃重复记录: {len(dropped)}")

    tasks, steps = parse_records(all_records)
    all_tasks, all_steps = tasks, steps

    print(f"\n总计: {len(all_tasks)} 个任务, {len(all_steps)} 个步骤")

    # 唯一性断言：去重后 task_id 必须唯一，否则下游 merge 会再次膨胀
    _ids = [t.get("task_id") for t in all_tasks]
    assert len(_ids) == len(set(_ids)), "去重后仍存在重复 task_id，禁止写盘"

    # 保存解析结果
    os.makedirs("data/interim", exist_ok=True)

    # 保存去重审计文件
    audit_path = "data/interim/dedup_audit.json"
    with open(audit_path, "w", encoding="utf-8") as f:
        json.dump({
            "raw_record_count": raw_count,
            "unique_task_count": len(all_tasks),
            "dropped_count": len(dropped),
            "rule": "keep the record whose traj length equals meta_data_merged.jsonl step_num; "
                    "if not uniquely decidable keep the last occurrence",
            "dropped": dropped,
        }, f, ensure_ascii=False, indent=1)
    print(f"去重审计已保存: {audit_path}")

    # 保存任务数据
    tasks_df = pd.DataFrame(all_tasks)
    tasks_path = "data/interim/tasks.parquet"
    tasks_df.to_parquet(tasks_path)
    print(f"\n任务数据已保存: {tasks_path}")

    # 保存步骤数据
    if all_steps:
        steps_df = pd.DataFrame(all_steps)
        steps_path = "data/interim/steps.parquet"
        steps_df.to_parquet(steps_path)
        print(f"步骤数据已保存: {steps_path}")

    # 生成数据流程报告
    flow_report = {
        "timestamp": datetime.now().isoformat(),
        "total_tasks_loaded": len(all_tasks),
        "total_steps_loaded": len(all_steps),
        "tasks_without_id": sum(1 for t in all_tasks if not t.get("task_id")),
        "tasks_without_instruction": sum(1 for t in all_tasks if not t.get("instruction") and not t.get("natural_language_task")),
        "tasks_without_completion": sum(1 for t in all_tasks if t.get("task_completed") is None),
        "tasks_without_trajectory": sum(1 for t in all_tasks if not t.get("traj")),
        "tasks_with_zero_steps": sum(1 for t in all_tasks if isinstance(t.get("traj"), list) and len(t.get("traj")) == 0),
    }

    flow_path = "data/interim/data_flow.json"
    with open(flow_path, "w", encoding="utf-8") as f:
        json.dump(flow_report, f, ensure_ascii=False, indent=2)

    print(f"\n数据流程报告已保存: {flow_path}")

    # 显示报告
    print("\n数据流程报告:")
    for key, value in flow_report.items():
        if key != "timestamp":
            print(f"  {key}: {value}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
