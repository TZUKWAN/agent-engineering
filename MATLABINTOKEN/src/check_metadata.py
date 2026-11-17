"""
检查元数据结构并提取样本
"""

import json

metadata_path = "data/raw/meta_data_merged.jsonl"

with open(metadata_path, 'r', encoding='utf-8') as f:
    # 读取前3个任务
    for i in range(3):
        line = f.readline()
        if not line:
            break
        task = json.loads(line.strip())
        print(f"\n{'='*60}")
        print(f"任务 {i+1}")
        print(f"{'='*60}")
        print(f"task_id: {task.get('task_id')}")
        print(f"instruction: {task.get('instruction')}")
        print(f"natural_language_task: {task.get('natural_language_task')}")
        print(f"actual_task: {task.get('actual_task')}")
        print(f"task_completed: {task.get('task_completed')}")
        print(f"alignment_score: {task.get('alignment_score')}")
        print(f"efficiency_score: {task.get('efficiency_score')}")
        print(f"task_difficulty: {task.get('task_difficulty')}")
        traj = task.get('traj', [])
        print(f"traj长度: {len(traj)}")
        if traj:
            print(f"第一个traj键: {list(traj[0].keys())}")
            if 'value' in traj[0]:
                print(f"value键: {list(traj[0]['value'].keys())}")
