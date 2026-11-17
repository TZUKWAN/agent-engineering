"""
用全量AgentNet数据重新分析
使用全部18k Windows/Mac + 5k Ubuntu = 23,000条任务
"""

import os
import json
import pandas as pd
import numpy as np
from tqdm import tqdm
from collections import Counter
import re

def main():
    print("=" * 70)
    print("用全量AgentNet数据重新分析")
    print("=" * 70)
    
    # 1. 解析所有数据
    print("\n[1/6] 解析全量数据...")
    
    data_files = [
        ("data/raw/agentnet_win_mac_18k.jsonl", "win_mac"),
        ("data/raw/agentnet_ubuntu_5k.jsonl", "ubuntu")
    ]
    
    all_tasks = []
    all_steps = []

    # 原始轨迹文件含 93 个重复 task_id（官方 meta_data_merged.jsonl 为 22,532 条 = 唯一 task_id 数）。
    # 裁决规则与 03_parse_trajectories 一致：保留 traj 长度与官方 step_num 一致的记录；无法唯一判定时
    # 保留末次出现。重复记录的标签互相冲突（76/91），必须只保留一条，否则 merge 膨胀且任务被重复计数。
    meta_stepnums = {}
    meta_path = "data/raw/meta_data_merged.jsonl"
    if os.path.exists(meta_path):
        with open(meta_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    m = json.loads(line)
                    sn = m.get('step_num')
                    if m.get('task_id') and isinstance(sn, int):
                        meta_stepnums[m['task_id']] = sn

    raw_by_id = {}
    task_os = {}
    for file_path, os_type in data_files:
        if not os.path.exists(file_path):
            print(f"  跳过: 找不到 {file_path}")
            continue

        print(f"\n  解析 {file_path}...")
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_idx, line in enumerate(tqdm(f, desc=f"  解析{os_type}数据")):
                try:
                    task = json.loads(line.strip())
                    tid = task.get('task_id', '')
                    raw_by_id.setdefault(tid, []).append(task)
                    task_os[tid] = os_type
                except Exception as e:
                    continue

    # 按 task_id 裁决保留哪条记录
    kept_tasks = []
    dropped_records = []
    for tid, recs in raw_by_id.items():
        if len(recs) == 1:
            kept_tasks.append(recs[0])
            continue
        sn = meta_stepnums.get(tid)
        lens = [len(r.get('traj') or []) if isinstance(r.get('traj'), list) else None for r in recs]
        matches = [i for i, l in enumerate(lens) if l is not None and sn is not None and l == sn]
        if len(matches) == 1:
            keep_idx, reason = matches[0], f"meta_step_num_match(step_num={sn})"
        elif len(matches) > 1:
            keep_idx, reason = matches[-1], f"meta_step_num_match_ambiguous_keep_last(step_num={sn})"
        else:
            keep_idx, reason = len(recs) - 1, "no_unique_step_num_match_keep_last"
        kept_tasks.append(recs[keep_idx])
        label_fields = ['task_completed', 'alignment_score', 'efficiency_score', 'task_difficulty']
        conflicts = {fld: [r.get(fld) for r in recs] for fld in label_fields
                     if len({repr(r.get(fld)) for r in recs}) > 1}
        for i, r in enumerate(recs):
            if i != keep_idx:
                dropped_records.append({
                    'task_id': tid, 'dropped_index': i, 'kept_index': keep_idx, 'reason': reason,
                    'dropped_traj_len': lens[i], 'labels_of_duplicates': conflicts or 'identical'})

    dedup_audit = {
        'raw_record_count': sum(len(v) for v in raw_by_id.values()),
        'unique_task_count': len(kept_tasks),
        'dropped_count': len(dropped_records),
        'rule': 'keep the record whose traj length equals meta_data_merged.jsonl step_num; '
                'if not uniquely decidable keep the last occurrence',
        'dropped': dropped_records,
    }
    os.makedirs("data/interim", exist_ok=True)
    with open("data/interim/dedup_audit.json", 'w', encoding='utf-8') as f:
        json.dump(dedup_audit, f, ensure_ascii=False, indent=1)
    print(f"  去重: {dedup_audit['raw_record_count']} -> {dedup_audit['unique_task_count']} "
          f"(丢弃 {dedup_audit['dropped_count']} 条重复记录)")

    for task in kept_tasks:
        task_info = {
            'task_id': task.get('task_id', ''),
            'instruction': task.get('instruction', ''),
            'natural_language_task': task.get('natural_language_task', ''),
            'actual_task': task.get('actual_task', ''),
            'task_completed': task.get('task_completed'),
            'alignment_score': task.get('alignment_score'),
            'efficiency_score': task.get('efficiency_score'),
            'task_difficulty': task.get('task_difficulty'),
            'os': task_os.get(task.get('task_id', ''), 'unknown'),
        }
        all_tasks.append(task_info)

    print(f"\n  解析完成!")
    print(f"  任务数: {len(all_tasks)}")

    for task in kept_tasks:
        traj = task.get('traj') or []
        for step_idx, step in enumerate(traj):
            value = step.get('value', {}) if isinstance(step.get('value'), dict) else {}
            all_steps.append({
                'task_id': task.get('task_id', ''),
                'step_index': step_idx,
                'last_step_correct': value.get('last_step_correct'),
                'last_step_redundant': value.get('last_step_redundant')
            })
    print(f"\n  解析完成!")
    print(f"  任务数: {len(all_tasks)}")
    print(f"  步骤数: {len(all_steps)}")
    
    # 2. 保存tasks和steps
    print("\n[2/6] 保存解析后的数据...")
    os.makedirs("data/interim", exist_ok=True)
    
    tasks_df = pd.DataFrame(all_tasks)
    tasks_df.to_parquet("data/interim/tasks.parquet")
    tasks_df.to_csv("data/interim/tasks.csv", index=False, encoding='utf-8-sig')
    print(f"  ✓ tasks.parquet ({len(tasks_df)} 任务)")
    
    steps_df = pd.DataFrame(all_steps)
    steps_df.to_parquet("data/interim/steps.parquet")
    steps_df.to_csv("data/interim/steps.csv", index=False, encoding='utf-8-sig')
    print(f"  ✓ steps.parquet ({len(steps_df)} 步骤)")
    
    # 3. 提取指令特征
    print("\n[3/6] 提取操作显性度特征...")
    instruction_features = extract_instruction_features(tasks_df)
    instruction_features.to_parquet("data/interim/instruction_features.parquet")
    print(f"  ✓ instruction_features.parquet")
    
    # 4. 提取过程特征
    print("\n[4/6] 提取过程质量特征...")
    process_features = extract_process_features(steps_df)
    process_features.to_parquet("data/interim/process_features.parquet")
    print(f"  ✓ process_features.parquet")
    
    # 5. 构建分析数据集
    print("\n[5/6] 构建分析数据集...")
    analysis_df = build_analysis_data(tasks_df, instruction_features, process_features)
    
    os.makedirs("data/processed", exist_ok=True)
    analysis_df.to_parquet("data/processed/analysis_data.parquet")
    analysis_df.to_csv("data/processed/analysis_data.csv", index=False, encoding='utf-8-sig')
    print(f"  ✓ analysis_data.parquet ({len(analysis_df)} 样本)")
    
    # 6. 统计分析
    print("\n[6/6] 进行统计分析...")
    analysis_results = do_statistical_analysis(analysis_df)
    
    os.makedirs("results", exist_ok=True)
    with open("results/analysis_results.json", 'w', encoding='utf-8') as f:
        json.dump(analysis_results, f, indent=2, ensure_ascii=False)
    print(f"  ✓ analysis_results.json")
    
    # 更新main_results.json
    update_main_results(analysis_results, len(analysis_df))
    
    print("\n" + "=" * 70)
    print("全量数据分析完成!")
    print(f"总任务数: {len(analysis_df)}")
    print(f"总步骤数: {len(all_steps)}")
    print("=" * 70)
    
    return 0

def extract_instruction_features(tasks_df):
    """提取操作显性度特征"""
    features_list = []
    
    application_words = ['excel', 'word', 'chrome', 'firefox', 'safari', 'edge', 'powerpoint',
                        'outlook', 'notepad', 'explorer', 'finder', 'terminal', 'cmd']
    constraint_words = ['only', 'just', 'must', 'should', 'need', 'have to', 'don\'t',
                       'not', 'keep', 'ensure', 'check', 'confirm']
    sequence_words = ['first', 'then', 'next', 'finally', 'after', 'before', 'while']
    
    for _, row in tasks_df.iterrows():
        text = str(row.get('instruction', '')).lower()
        
        features = {
            'task_id': row['task_id'],
            'has_application': int(any(w in text for w in application_words)),
            'has_operation_object': int(('file' in text or 'document' in text or
                                        'button' in text or 'link' in text or
                                        'folder' in text or 'window' in text)),
            'has_target_action': int(('open' in text or 'save' in text or 'delete' in text or
                                      'click' in text or 'type' in text or 'enter' in text or
                                      'select' in text or 'copy' in text or 'paste' in text)),
            'has_target_state': int(('done' in text or 'complete' in text or 'correct' in text)),
            'has_file_reference': int(('.' in text and ('xls' in text or 'doc' in text or
                                                        'pdf' in text or 'jpg' in text or
                                                        '/' in text or '\\' in text))),
            'has_object_properties': int(('color' in text or 'red' in text or 'blue' in text or
                                          'size' in text or 'position' in text or 'left' in text or
                                          'right' in text or 'top' in text or 'bottom' in text)),
            'has_operation_order': int(any(w in text for w in sequence_words)),
            'has_multiple_subtasks': int(text.count('.') >= 2 or text.count(',') >= 3),
            'has_constraint_words': int(any(w in text for w in constraint_words)),
            'has_completion_criteria': int(('check' in text or 'ensure' in text or 'confirm' in text)),
            'has_initial_state': int(('current' in text or 'already' in text or 'existing' in text or
                                    'now' in text)),
            'word_count': len(text.split()),
            'char_count': len(text)
        }
        
        features['explicitness_score'] = sum([
            features['has_application'],
            features['has_operation_object'],
            features['has_target_action'],
            features['has_target_state'],
            features['has_file_reference'],
            features['has_object_properties'],
            features['has_operation_order'],
            features['has_multiple_subtasks'],
            features['has_constraint_words'],
            features['has_completion_criteria'],
            features['has_initial_state']
        ])
        
        if features['explicitness_score'] <= 3:
            features['explicitness_level'] = 'Low'
        elif features['explicitness_score'] <= 6:
            features['explicitness_level'] = 'Medium'
        else:
            features['explicitness_level'] = 'High'
        
        features_list.append(features)
    
    return pd.DataFrame(features_list)

def extract_process_features(steps_df):
    """提取过程质量特征"""
    task_steps = steps_df.groupby('task_id').agg(
        total_steps=('step_index', 'count'),
        correct_steps=('last_step_correct', lambda x: (x == True).sum()),
        incorrect_steps=('last_step_correct', lambda x: (x == False).sum()),
        redundant_steps=('last_step_redundant', lambda x: (x == True).sum())
    ).reset_index()
    
    task_steps['correct_ratio'] = task_steps['correct_steps'] / task_steps['total_steps']
    task_steps['incorrect_ratio'] = task_steps['incorrect_steps'] / task_steps['total_steps']
    task_steps['redundant_ratio'] = task_steps['redundant_steps'] / task_steps['total_steps']
    
    return task_steps

def build_analysis_data(tasks_df, instruction_features, process_features):
    """构建最终分析数据集"""
    df = tasks_df.merge(instruction_features, on='task_id', how='left')
    df = df.merge(process_features, on='task_id', how='left')
    return df

def do_statistical_analysis(df):
    """进行统计分析"""
    from scipy import stats
    
    results = {
        'sample_info': {
            'n': len(df),
            'n_win_mac': len(df[df['os'] == 'win_mac']),
            'n_ubuntu': len(df[df['os'] == 'ubuntu']),
            'completion_rate': float(df['task_completed'].mean()),
            'mean_explicitness': float(df['explicitness_score'].mean()),
            'sd_explicitness': float(df['explicitness_score'].std())
        }
    }
    
    # RQ1: 显性度与完成率
    valid_rq1 = df[df['task_completed'].notna()]
    if len(valid_rq1) > 0:
        corr_rq1 = stats.pointbiserialr(valid_rq1['explicitness_score'], 
                                        valid_rq1['task_completed'])
        results['rq1'] = {
            'correlation': {'coefficient': float(corr_rq1[0]), 'p_value': float(corr_rq1[1])}
        }
        
        by_level = valid_rq1.groupby('explicitness_level')['task_completed'].agg(['mean', 'count'])
        results['rq1']['completion_rates'] = {
            level: {'rate': float(row['mean']), 'n': int(row['count'])}
            for level, row in by_level.iterrows()
        }
    
    # RQ2: 效率
    valid_eff = df[df['efficiency_score'].notna()]
    if len(valid_eff) > 0:
        corr_eff = stats.pearsonr(valid_eff['explicitness_score'], valid_eff['efficiency_score'])
        corr_steps = stats.pearsonr(valid_eff['explicitness_score'], valid_eff['total_steps'])
        results['rq2'] = {
            'efficiency_correlation': {'coefficient': float(corr_eff[0]), 'p_value': float(corr_eff[1])},
            'steps_correlation': {'coefficient': float(corr_steps[0]), 'p_value': float(corr_steps[1])}
        }
    
    # RQ3: 对齐度
    valid_align = df[df['alignment_score'].notna()]
    if len(valid_align) > 0:
        corr_align = stats.pearsonr(valid_align['explicitness_score'], valid_align['alignment_score'])
        results['rq3'] = {
            'alignment_correlation': {'coefficient': float(corr_align[0]), 'p_value': float(corr_align[1])}
        }
    
    # RQ4: 过程质量
    valid_proc = df[df['correct_ratio'].notna()]
    if len(valid_proc) > 0:
        corr_incorr = stats.pearsonr(valid_proc['explicitness_score'], valid_proc['incorrect_ratio'])
        corr_red = stats.pearsonr(valid_proc['explicitness_score'], valid_proc['redundant_ratio'])
        results['rq4'] = {
            'incorrect_ratio_correlation': {'coefficient': float(corr_incorr[0]), 'p_value': float(corr_incorr[1])},
            'redundant_ratio_correlation': {'coefficient': float(corr_red[0]), 'p_value': float(corr_red[1])}
        }
    
    # RQ5: 单个特征
    feature_cols = [c for c in df.columns if c.startswith('has_')]
    feature_effects = {}
    for feat in feature_cols:
        with_feat = df[df[feat] == 1]['task_completed'].mean()
        without_feat = df[df[feat] == 0]['task_completed'].mean()
        feature_effects[feat] = {
            'with_feature': float(with_feat),
            'without_feature': float(without_feat),
            'difference': float(with_feat - without_feat)
        }
    results['rq5'] = {'feature_effects': feature_effects}
    
    return results

def update_main_results(analysis_results, n):
    """更新main_results.json"""
    main_results = {
        "rq1": {
            "correlation": analysis_results.get("rq1", {}).get("correlation", {}).get("coefficient", 0),
            "p_value": analysis_results.get("rq1", {}).get("correlation", {}).get("p_value", 1),
            "n": n,
            "by_level": {}
        },
        "rq2": {
            "efficiency_score": {
                "correlation": analysis_results.get("rq2", {}).get("efficiency_correlation", {}).get("coefficient", 0),
                "p_value": analysis_results.get("rq2", {}).get("efficiency_correlation", {}).get("p_value", 1),
                "n": n
            },
            "alignment_score": {
                "correlation": analysis_results.get("rq3", {}).get("alignment_correlation", {}).get("coefficient", 0),
                "p_value": analysis_results.get("rq3", {}).get("alignment_correlation", {}).get("p_value", 1),
                "n": n
            }
        },
        "rq3": {
            "incorrect_ratio": {
                "correlation": analysis_results.get("rq4", {}).get("incorrect_ratio_correlation", {}).get("coefficient", 0),
                "p_value": analysis_results.get("rq4", {}).get("incorrect_ratio_correlation", {}).get("p_value", 1),
                "n": n
            },
            "redundant_ratio": {
                "correlation": analysis_results.get("rq4", {}).get("redundant_ratio_correlation", {}).get("coefficient", 0),
                "p_value": analysis_results.get("rq4", {}).get("redundant_ratio_correlation", {}).get("p_value", 1),
                "n": n
            }
        },
        "rq4": {
            "error_mediation": {},
            "redundant_mediation": {}
        },
        "correlation_matrix": {}
    }
    
    completion_rates = analysis_results.get("rq1", {}).get("completion_rates", {})
    for level, data in completion_rates.items():
        main_results["rq1"]["by_level"][level] = {
            "rate": data.get("rate", 0),
            "n": data.get("n", 0)
        }
    
    os.makedirs("results/models", exist_ok=True)
    with open("results/models/main_results.json", 'w', encoding='utf-8') as f:
        json.dump(main_results, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    import sys
    sys.exit(main())
