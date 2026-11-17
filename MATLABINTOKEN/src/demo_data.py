"""
demo_data.py - 生成演示数据

在无法下载真实数据时，生成模拟数据用于演示
"""

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime


def generate_demo_data():
    """生成演示数据"""
    np.random.seed(42)

    n_tasks = 200

    # 生成任务数据
    tasks = []
    for i in range(n_tasks):
        # 随机生成显性度相关特征
        has_application = np.random.choice([True, False], p=[0.6, 0.4])
        has_operation_object = np.random.choice([True, False], p=[0.7, 0.3])
        has_target_action = np.random.choice([True, False], p=[0.8, 0.2])
        has_target_state = np.random.choice([True, False], p=[0.5, 0.5])
        has_file_reference = np.random.choice([True, False], p=[0.4, 0.6])
        has_object_properties = np.random.choice([True, False], p=[0.3, 0.7])
        has_operation_order = np.random.choice([True, False], p=[0.4, 0.6])
        has_multiple_subtasks = np.random.choice([True, False], p=[0.5, 0.5])
        has_constraint_words = np.random.choice([True, False], p=[0.3, 0.7])
        has_completion_criteria = np.random.choice([True, False], p=[0.2, 0.8])
        has_initial_state = np.random.choice([True, False], p=[0.4, 0.6])

        # 计算显性度分数
        explicitness_score = sum([
            has_application, has_operation_object, has_target_action,
            has_target_state, has_file_reference, has_object_properties,
            has_operation_order, has_multiple_subtasks, has_constraint_words,
            has_completion_criteria, has_initial_state
        ])

        # 显性度影响结果
        # 更高的显性度 → 更高的完成率、更高的评分、更低的错误/冗余
        completion_prob = 0.3 + 0.4 * (explicitness_score / 11)
        efficiency_score = 3 + 3 * (explicitness_score / 11) + np.random.normal(0, 1)
        alignment_score = 3 + 3 * (explicitness_score / 11) + np.random.normal(0, 1)

        # 任务完成
        task_completed = np.random.choice([True, False], p=[completion_prob, 1-completion_prob])

        # 过程特征
        total_steps = np.random.randint(5, 50)
        incorrect_ratio = 0.4 - 0.25 * (explicitness_score / 11) + np.random.normal(0, 0.1)
        incorrect_ratio = np.clip(incorrect_ratio, 0, 1)
        redundant_ratio = 0.3 - 0.2 * (explicitness_score / 11) + np.random.normal(0, 0.1)
        redundant_ratio = np.clip(redundant_ratio, 0, 1)

        word_count = int(20 + 50 * (explicitness_score / 11) + np.random.normal(0, 20))

        # 显性度级别
        if explicitness_score <= 3:
            explicitness_level = "low"
        elif explicitness_score <= 6:
            explicitness_level = "medium"
        else:
            explicitness_level = "high"

        task = {
            "task_id": f"task_{i:03d}",
            "instruction": f"演示任务描述 {i}",
            "task_completed": task_completed,
            "efficiency_score": np.clip(efficiency_score, 1, 7),
            "alignment_score": np.clip(alignment_score, 1, 7),
            "task_difficulty": np.random.randint(1, 4),
            "os": np.random.choice(["Windows", "Mac", "Linux"]),
            "explicitness_score": explicitness_score,
            "explicitness_level": explicitness_level,
            "has_application": has_application,
            "has_operation_object": has_operation_object,
            "has_target_action": has_target_action,
            "has_target_state": has_target_state,
            "has_file_reference": has_file_reference,
            "has_object_properties": has_object_properties,
            "has_operation_order": has_operation_order,
            "has_multiple_subtasks": has_multiple_subtasks,
            "has_constraint_words": has_constraint_words,
            "has_completion_criteria": has_completion_criteria,
            "has_initial_state": has_initial_state,
            "total_steps": total_steps,
            "correct_ratio": 1 - incorrect_ratio,
            "incorrect_ratio": incorrect_ratio,
            "redundant_ratio": redundant_ratio,
            "word_count": word_count,
        }
        tasks.append(task)

    return pd.DataFrame(tasks)


def save_demo_data():
    """保存演示数据"""
    df = generate_demo_data()

    # 创建目录
    os.makedirs("data/interim", exist_ok=True)
    os.makedirs("data/processed", exist_ok=True)

    # 保存分析数据
    df.to_parquet("data/processed/analysis_data.parquet")

    # 也保存为CSV便于查看
    df.to_csv("data/processed/analysis_data.csv", index=False, encoding="utf-8-sig")

    print(f"已生成演示数据: {len(df)} 个任务")

    return df


if __name__ == "__main__":
    save_demo_data()
