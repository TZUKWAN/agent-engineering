"""
05_extract_process_features.py - 提取过程特征

从轨迹数据中计算过程变量
"""

import os
import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime


def load_steps():
    """加载步骤数据"""
    steps_path = "data/interim/steps.parquet"
    if os.path.exists(steps_path):
        return pd.read_parquet(steps_path)
    return None


def load_tasks():
    """加载任务数据"""
    tasks_path = "data/interim/tasks.parquet"
    if os.path.exists(tasks_path):
        return pd.read_parquet(tasks_path)
    return None


def calculate_task_features(steps_df, task_id):
    """计算单个任务的过程特征"""
    task_steps = steps_df[steps_df["task_id"] == task_id].copy()

    if len(task_steps) == 0:
        return {}

    # 按步骤索引排序
    if "step_index" in task_steps.columns:
        task_steps = task_steps.sort_values("step_index")
    elif "index" in task_steps.columns:
        task_steps = task_steps.sort_values("index")

    features = {}
    features["task_id"] = task_id
    features["total_steps"] = len(task_steps)

    # 正确/错误/冗余步骤计数
    correct_count = 0
    incorrect_count = 0
    redundant_count = 0

    # 尝试多种字段名
    for field in ["last_step_correct", "correct", "is_correct"]:
        if field in task_steps.columns:
            values = task_steps[field]
            if pd.api.types.is_bool_dtype(values):
                correct_count = values.sum()
                incorrect_count = (~values).sum()
            elif pd.api.types.is_numeric_dtype(values):
                correct_count = (values == 1).sum()
                incorrect_count = (values == 0).sum()
            break

    for field in ["last_step_redundant", "redundant", "is_redundant"]:
        if field in task_steps.columns:
            values = task_steps[field]
            if pd.api.types.is_bool_dtype(values):
                redundant_count = values.sum()
            elif pd.api.types.is_numeric_dtype(values):
                redundant_count = (values == 1).sum()
            break

    features["correct_steps"] = correct_count
    features["incorrect_steps"] = incorrect_count
    features["redundant_steps"] = redundant_count

    # 比例
    features["correct_ratio"] = correct_count / max(1, len(task_steps))
    features["incorrect_ratio"] = incorrect_count / max(1, len(task_steps))
    features["redundant_ratio"] = redundant_count / max(1, len(task_steps))

    # 首次错误位置
    first_error_pos = None
    for field in ["last_step_correct", "correct", "is_correct"]:
        if field in task_steps.columns:
            for i, (_, row) in enumerate(task_steps.iterrows()):
                val = row[field]
                if (isinstance(val, bool) and not val) or (isinstance(val, (int, float)) and val == 0):
                    first_error_pos = i
                    break
            break
    features["first_error_position"] = first_error_pos if first_error_pos is not None else -1

    # 首次冗余位置
    first_redundant_pos = None
    for field in ["last_step_redundant", "redundant", "is_redundant"]:
        if field in task_steps.columns:
            for i, (_, row) in enumerate(task_steps.iterrows()):
                val = row[field]
                if (isinstance(val, bool) and val) or (isinstance(val, (int, float)) and val == 1):
                    first_redundant_pos = i
                    break
            break
    features["first_redundant_position"] = first_redundant_pos if first_redundant_pos is not None else -1

    # 连续错误的最长长度
    max_consecutive_errors = 0
    current_errors = 0
    for field in ["last_step_correct", "correct", "is_correct"]:
        if field in task_steps.columns:
            for _, row in task_steps.iterrows():
                val = row[field]
                is_error = (isinstance(val, bool) and not val) or (isinstance(val, (int, float)) and val == 0)
                if is_error:
                    current_errors += 1
                    max_consecutive_errors = max(max_consecutive_errors, current_errors)
                else:
                    current_errors = 0
            break
    features["max_consecutive_errors"] = max_consecutive_errors

    # 连续冗余的最长长度
    max_consecutive_redundant = 0
    current_redundant = 0
    for field in ["last_step_redundant", "redundant", "is_redundant"]:
        if field in task_steps.columns:
            for _, row in task_steps.iterrows():
                val = row[field]
                is_redundant = (isinstance(val, bool) and val) or (isinstance(val, (int, float)) and val == 1)
                if is_redundant:
                    current_redundant += 1
                    max_consecutive_redundant = max(max_consecutive_redundant, current_redundant)
                else:
                    current_redundant = 0
            break
    features["max_consecutive_redundant"] = max_consecutive_redundant

    # 动作相关特征
    action_types = set()
    mouse_actions = 0
    keyboard_actions = 0
    shortcuts = 0
    app_switches = 0
    repeat_clicks = 0
    repeat_inputs = 0

    # 检查action字段
    for field in ["action", "act", "operation"]:
        if field in task_steps.columns:
            for _, row in task_steps.iterrows():
                action = str(row[field]).lower() if pd.notna(row[field]) else ""

                # 识别动作类型
                if "click" in action or "press" in action:
                    mouse_actions += 1
                if "type" in action or "input" in action or "write" in action:
                    keyboard_actions += 1
                if "ctrl" in action or "alt" in action or "cmd" in action or "shortcut" in action:
                    shortcuts += 1
                if "open" in action and ("app" in action or "application" in action):
                    app_switches += 1

            break

    features["distinct_action_types"] = len(action_types)
    features["mouse_actions"] = mouse_actions
    features["keyboard_actions"] = keyboard_actions
    features["shortcuts"] = shortcuts
    features["app_switches"] = app_switches

    # 反思文本相关
    has_reflection = 0
    reflection_length = 0

    for field in ["reflection", "feedback", "thought", "reasoning"]:
        if field in task_steps.columns:
            has_reflection = task_steps[field].notna().sum()
            reflection_length = task_steps[field].apply(
                lambda x: len(str(x)) if pd.notna(x) else 0
            ).sum()
            break

    features["has_reflection"] = has_reflection > 0
    features["reflection_count"] = has_reflection
    features["reflection_total_length"] = reflection_length

    return features


def main():
    """主函数"""
    print("=" * 60)
    print("提取过程特征")
    print("=" * 60)

    # 加载数据
    steps_df = load_steps()
    tasks_df = load_tasks()

    if steps_df is None or len(steps_df) == 0:
        print("\n未找到步骤数据，请先运行 03_parse_trajectories.py")
        return 1

    print(f"\n加载了 {len(steps_df)} 个步骤")

    # 获取所有任务ID
    if "task_id" in steps_df.columns:
        task_ids = steps_df["task_id"].unique()
    else:
        print("\n错误: 步骤数据中没有task_id字段")
        return 1

    print(f"来自 {len(task_ids)} 个任务")

    # 计算每个任务的特征
    all_features = []

    print("\n计算任务特征...")
    for i, task_id in enumerate(task_ids):
        if i % 100 == 0:
            print(f"  处理 {i}/{len(task_ids)}...")

        features = calculate_task_features(steps_df, task_id)
        all_features.append(features)

    # 保存特征
    process_features_df = pd.DataFrame(all_features)
    output_path = "data/interim/process_features.parquet"
    process_features_df.to_parquet(output_path)

    print(f"\n过程特征已保存: {output_path}")

    # 显示统计
    print("\n过程特征统计:")
    for col in ["total_steps", "correct_ratio", "incorrect_ratio", "redundant_ratio"]:
        if col in process_features_df.columns:
            print(f"  {col}:")
            print(f"    最小值: {process_features_df[col].min()}")
            print(f"    最大值: {process_features_df[col].max()}")
            print(f"    平均值: {process_features_df[col].mean():.2f}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
