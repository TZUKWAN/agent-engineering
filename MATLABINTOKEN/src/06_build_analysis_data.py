"""
06_build_analysis_data.py - 构建分析数据集

合并任务、指令特征和过程特征，构建最终分析数据集
"""

import os
import json
import pandas as pd
from datetime import datetime


def load_data():
    """加载所有数据"""
    data = {}

    # 任务数据
    tasks_path = "data/interim/tasks.parquet"
    if os.path.exists(tasks_path):
        data["tasks"] = pd.read_parquet(tasks_path)

    # 指令特征
    instruction_path = "data/interim/instruction_features.parquet"
    if os.path.exists(instruction_path):
        data["instruction"] = pd.read_parquet(instruction_path)

    # 过程特征
    process_path = "data/interim/process_features.parquet"
    if os.path.exists(process_path):
        data["process"] = pd.read_parquet(process_path)

    return data


def extract_outcome_variables(task_row):
    """从任务行中提取结果变量"""
    outcome = {}

    # 任务完成
    task_completed = None
    for field in ["task_completed", "completed", "success", "is_success"]:
        if field in task_row:
            val = task_row[field]
            if pd.isna(val):
                continue
            if isinstance(val, bool):
                task_completed = val
            elif isinstance(val, (int, float)):
                task_completed = bool(val)
            elif isinstance(val, str):
                task_completed = val.lower() in ["true", "yes", "1", "success"]
            break

    outcome["task_completed"] = task_completed

    # 效率评分
    efficiency_score = None
    for field in ["efficiency_score", "eff_score", "efficiency"]:
        if field in task_row:
            val = task_row[field]
            if pd.notna(val) and isinstance(val, (int, float)):
                efficiency_score = float(val)
                break
    outcome["efficiency_score"] = efficiency_score

    # 对齐评分
    alignment_score = None
    for field in ["alignment_score", "align_score", "alignment"]:
        if field in task_row:
            val = task_row[field]
            if pd.notna(val) and isinstance(val, (int, float)):
                alignment_score = float(val)
                break
    outcome["alignment_score"] = alignment_score

    # 任务难度
    task_difficulty = None
    for field in ["task_difficulty", "difficulty", "level"]:
        if field in task_row:
            val = task_row[field]
            if pd.notna(val):
                if isinstance(val, (int, float)):
                    task_difficulty = float(val)
                elif isinstance(val, str):
                    # 尝试转换字符串难度
                    val_lower = val.lower()
                    if "easy" in val_lower or "1" in val_lower:
                        task_difficulty = 1.0
                    elif "medium" in val_lower or "2" in val_lower or "normal" in val_lower:
                        task_difficulty = 2.0
                    elif "hard" in val_lower or "3" in val_lower or "difficult" in val_lower:
                        task_difficulty = 3.0
            break
    outcome["task_difficulty"] = task_difficulty

    # 操作系统
    os_value = None
    for field in ["OS", "os", "platform", "system"]:
        if field in task_row:
            val = task_row[field]
            if pd.notna(val):
                os_value = str(val)
                break
    outcome["os"] = os_value

    return outcome


def main():
    """主函数"""
    print("=" * 60)
    print("构建分析数据集")
    print("=" * 60)

    # 加载数据
    data = load_data()

    if "tasks" not in data or len(data["tasks"]) == 0:
        print("\n未找到任务数据")
        return 1

    tasks_df = data["tasks"]
    print(f"\n任务数: {len(tasks_df)}")

    # 构建分析数据集
    analysis_records = []

    for idx, task_row in tasks_df.iterrows():
        record = {}

        # 任务ID
        if "task_id" in task_row:
            record["task_id"] = task_row["task_id"]
        else:
            record["task_id"] = f"task_{idx}"

        # 原始文本字段透传：paper01 的验证分类与 paper02 的约束分类直接读 instruction
        for text_field in ["instruction", "natural_language_task", "actual_task"]:
            if text_field in task_row:
                record[text_field] = task_row[text_field]

        # 结果变量
        outcome = extract_outcome_variables(task_row)
        record.update(outcome)

        # 合并指令特征
        if "instruction" in data:
            feat_df = data["instruction"]
            matching = feat_df[feat_df["task_id"] == record["task_id"]]
            if len(matching) > 0:
                for col in matching.columns:
                    if col != "task_id":
                        record[col] = matching.iloc[0][col]

        # 合并过程特征
        if "process" in data:
            proc_df = data["process"]
            matching = proc_df[proc_df["task_id"] == record["task_id"]]
            if len(matching) > 0:
                for col in matching.columns:
                    if col != "task_id":
                        record[col] = matching.iloc[0][col]

        analysis_records.append(record)

    # 创建DataFrame
    analysis_df = pd.DataFrame(analysis_records)

    # 保存
    os.makedirs("data/processed", exist_ok=True)
    output_path = "data/processed/analysis_data.parquet"
    analysis_df.to_parquet(output_path)

    print(f"\n分析数据已保存: {output_path}")
    print(f"样本数: {len(analysis_df)}")
    print(f"字段数: {len(analysis_df.columns)}")

    # 显示字段列表
    print("\n字段列表:")
    for col in sorted(analysis_df.columns):
        non_null = analysis_df[col].notna().sum()
        print(f"  - {col}: {non_null}/{len(analysis_df)} 非空")

    # 保存数据报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_samples": len(analysis_df),
        "columns": list(analysis_df.columns),
        "missing_data": {},
    }

    for col in analysis_df.columns:
        missing = analysis_df[col].isna().sum()
        report["missing_data"][col] = {
            "missing": int(missing),
            "missing_ratio": float(missing / len(analysis_df)),
        }

    report_path = "data/processed/analysis_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n分析报告已保存: {report_path}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
