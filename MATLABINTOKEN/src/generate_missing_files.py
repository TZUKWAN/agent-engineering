"""
快速生成缺失的中间文件
从已有的analysis_data.parquet中提取所需内容
"""

import os
import pandas as pd
import json

def main():
    print("=" * 60)
    print("生成缺失的中间文件")
    print("=" * 60)
    
    # 加载已有的完整分析数据
    analysis_path = "data/processed/analysis_data.parquet"
    if not os.path.exists(analysis_path):
        print(f"错误: 找不到 {analysis_path}")
        return 1
    
    df = pd.read_parquet(analysis_path)
    print(f"\n加载了 {len(df)} 个样本")
    
    # 1. 生成 instruction_features.parquet
    instruction_cols = [
        'task_id',
        'has_application', 'has_operation_object', 'has_target_action',
        'has_target_state', 'has_file_reference', 'has_object_properties',
        'has_operation_order', 'has_multiple_subtasks', 'has_constraint_words',
        'has_completion_criteria', 'has_initial_state',
        'explicitness_score', 'explicitness_level',
        'word_count', 'char_count'
    ]
    available_instruction_cols = [c for c in instruction_cols if c in df.columns]
    instruction_df = df[available_instruction_cols].copy()
    instruction_path = "data/interim/instruction_features.parquet"
    instruction_df.to_parquet(instruction_path)
    print(f"\n✓ 已保存: {instruction_path}")
    
    # 2. 生成 process_features.parquet
    process_cols = [
        'task_id',
        'total_steps', 'correct_ratio', 'incorrect_ratio', 'redundant_ratio'
    ]
    available_process_cols = [c for c in process_cols if c in df.columns]
    process_df = df[available_process_cols].copy()
    process_path = "data/interim/process_features.parquet"
    process_df.to_parquet(process_path)
    print(f"✓ 已保存: {process_path}")
    
    # 3. 同时确保 tasks.parquet 和 steps.parquet 存在且有500样本
    # 从我们的实际数据重新生成
    print("\n重新生成完整的 tasks.parquet 和 steps.parquet...")
    
    # 加载原始数据来生成完整的tasks和steps
    import json
    from tqdm import tqdm
    
    raw_data_path = "data/raw/agentnet_win_mac_18k.jsonl"
    tasks_data = []
    steps_data = []
    
    if os.path.exists(raw_data_path):
        with open(raw_data_path, 'r', encoding='utf-8') as f:
            for line_idx, line in enumerate(tqdm(f, desc="解析任务")):
                try:
                    task = json.loads(line.strip())
                    
                    task_info = {
                        'task_id': task.get('task_id', ''),
                        'instruction': task.get('instruction', ''),
                        'natural_language_task': task.get('natural_language_task', ''),
                        'actual_task': task.get('actual_task', ''),
                        'task_completed': task.get('task_completed'),
                        'alignment_score': task.get('alignment_score'),
                        'efficiency_score': task.get('efficiency_score'),
                        'task_difficulty': task.get('task_difficulty'),
                        'os': 'win_mac'
                    }
                    tasks_data.append(task_info)
                    
                    # 解析步骤
                    traj = task.get('traj', [])
                    for step_idx, step in enumerate(traj):
                        value = step.get('value', {})
                        steps_data.append({
                            'task_id': task.get('task_id', ''),
                            'step_index': step_idx,
                            'last_step_correct': value.get('last_step_correct'),
                            'last_step_redundant': value.get('last_step_redundant')
                        })
                    
                    if len(tasks_data) >= 500:
                        break
                except:
                    continue
    
    # 保存tasks
    tasks_df = pd.DataFrame(tasks_data)
    tasks_df.to_parquet("data/interim/tasks.parquet")
    tasks_df.to_csv("data/interim/tasks.csv", index=False, encoding='utf-8-sig')
    print(f"✓ 已保存 tasks.parquet ({len(tasks_df)} 样本)")
    
    # 保存steps
    steps_df = pd.DataFrame(steps_data)
    steps_df.to_parquet("data/interim/steps.parquet")
    steps_df.to_csv("data/interim/steps.csv", index=False, encoding='utf-8-sig')
    print(f"✓ 已保存 steps.parquet ({len(steps_df)} 步骤)")
    
    print("\n" + "=" * 60)
    print("所有缺失的中间文件已生成!")
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
