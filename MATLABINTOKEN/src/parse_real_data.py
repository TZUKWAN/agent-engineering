"""
解析AgentNet真实数据
"""

import os
import json
import pandas as pd
from tqdm import tqdm

def parse_metadata():
    """解析元数据文件"""
    print("=" * 60)
    print("解析AgentNet元数据")
    print("=" * 60)

    metadata_path = "data/raw/meta_data_merged.jsonl"

    if not os.path.exists(metadata_path):
        print(f"文件不存在: {metadata_path}")
        return None

    tasks = []
    print(f"\n正在读取: {metadata_path}")

    with open(metadata_path, 'r', encoding='utf-8') as f:
        for line in tqdm(f, desc="解析任务"):
            try:
                task = json.loads(line.strip())
                tasks.append(task)
            except Exception as e:
                continue

    print(f"\n解析完成: {len(tasks)} 个任务")

    # 提取任务级数据
    task_data = []
    for task in tasks:
        task_info = {
            'task_id': task.get('task_id', ''),
            'instruction': task.get('instruction', ''),
            'natural_language_task': task.get('natural_language_task', ''),
            'actual_task': task.get('actual_task', ''),
            'task_completed': task.get('task_completed'),
            'alignment_score': task.get('alignment_score'),
            'efficiency_score': task.get('efficiency_score'),
            'task_difficulty': task.get('task_difficulty'),
            'num_steps': len(task.get('traj', []))
        }
        task_data.append(task_info)

    df_tasks = pd.DataFrame(task_data)
    print(f"\n任务数据: {len(df_tasks)} 行")
    print(f"\n列: {list(df_tasks.columns)}")

    # 保存
    os.makedirs("data/interim", exist_ok=True)
    df_tasks.to_parquet("data/interim/tasks.parquet")
    df_tasks.to_csv("data/interim/tasks.csv", index=False, encoding='utf-8-sig')
    print(f"\n已保存: data/interim/tasks.parquet")

    # 提取步骤数据
    step_data = []
    for task in tasks:
        task_id = task.get('task_id', '')
        traj = task.get('traj', [])

        for step in traj:
            step_idx = step.get('index', -1)
            value = step.get('value', {})

            step_info = {
                'task_id': task_id,
                'step_index': step_idx,
                'last_step_correct': value.get('last_step_correct'),
                'last_step_redundant': value.get('last_step_redundant'),
                'has_thought': bool(value.get('thought')),
                'has_observation': bool(value.get('observation')),
                'has_action': bool(value.get('action')),
                'has_code': bool(value.get('code'))
            }
            step_data.append(step_info)

    df_steps = pd.DataFrame(step_data)
    print(f"步骤数据: {len(df_steps)} 行")

    df_steps.to_parquet("data/interim/steps.parquet")
    df_steps.to_csv("data/interim/steps.csv", index=False, encoding='utf-8-sig')
    print(f"已保存: data/interim/steps.parquet")

    # 显示基本统计
    print("\n" + "=" * 60)
    print("基本统计")
    print("=" * 60)

    print(f"\n总任务数: {len(df_tasks)}")

    if 'task_completed' in df_tasks.columns:
        completion_rate = df_tasks['task_completed'].mean()
        print(f"任务完成率: {completion_rate:.1%}")
        print(f"  完成: {df_tasks['task_completed'].sum()}")
        print(f"  未完成: {(~df_tasks['task_completed']).sum()}")

    if 'efficiency_score' in df_tasks.columns:
        print(f"\n效率评分:")
        print(f"  均值: {df_tasks['efficiency_score'].mean():.2f}")
        print(f"  标准差: {df_tasks['efficiency_score'].std():.2f}")

    if 'alignment_score' in df_tasks.columns:
        print(f"\n对齐评分:")
        print(f"  均值: {df_tasks['alignment_score'].mean():.2f}")
        print(f"  标准差: {df_tasks['alignment_score'].std():.2f}")

    if 'task_difficulty' in df_tasks.columns:
        print(f"\n任务难度分布:")
        print(df_tasks['task_difficulty'].value_counts().sort_index())

    if 'num_steps' in df_tasks.columns:
        print(f"\n步骤数:")
        print(f"  均值: {df_tasks['num_steps'].mean():.1f}")
        print(f"  总步骤: {df_tasks['num_steps'].sum()}")

    return df_tasks, df_steps

if __name__ == "__main__":
    parse_metadata()
