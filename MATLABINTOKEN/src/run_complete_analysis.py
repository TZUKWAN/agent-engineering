"""
解析完整的AgentNet数据并运行完整分析
"""

import os
import json
import pandas as pd
import numpy as np
from tqdm import tqdm
import re

def extract_features_from_text(text):
    """
    从任务文本中提取操作显性度特征
    严格基于规则，不使用任何模型
    """
    if not isinstance(text, str):
        text = str(text) if text is not None else ""

    text_lower = text.lower()

    features = {}

    # 1. 是否明确指出应用或软件
    app_keywords = [
        'excel', 'word', 'powerpoint', 'ppt', 'outlook',
        'chrome', 'firefox', 'edge', 'safari', 'browser',
        'windows', 'mac', 'linux', 'ubuntu',
        'file', 'folder', 'explorer', 'finder',
        'notepad', 'textedit',
        'photoshop', 'illustrator', 'gimp',
        'wps', 'office', 'google docs', 'googledocs',
        'terminal', 'command', 'cmd', 'shell'
    ]
    features['has_application'] = any(kw in text_lower for kw in app_keywords)

    # 2. 是否明确指出操作对象
    object_keywords = [
        'file', 'folder', 'document', 'sheet', 'worksheet', 'page',
        'table', 'column', 'row', 'cell', 'data',
        'text', 'image', 'picture', 'photo',
        'link', 'url', 'website', 'webpage',
        'button', 'menu', 'icon', 'tab', 'window',
        'email', 'message', 'chat'
    ]
    features['has_operation_object'] = any(kw in text_lower for kw in object_keywords)

    # 3. 是否明确指出目标动作
    action_keywords = [
        'click', 'open', 'close', 'save', 'delete', 'remove',
        'copy', 'paste', 'cut', 'move', 'rename',
        'select', 'choose', 'find', 'search', 'look',
        'download', 'upload', 'install', 'uninstall',
        'create', 'make', 'new', 'add', 'insert',
        'edit', 'modify', 'change', 'update',
        'sort', 'filter', 'arrange', 'organize',
        'send', 'share', 'forward', 'reply',
        'print', 'export', 'import', 'convert'
    ]
    features['has_target_action'] = any(kw in text_lower for kw in action_keywords)

    # 4. 是否明确指出目标状态
    state_keywords = [
        'finished', 'done', 'completed', 'ready',
        'sorted', 'organized', 'arranged',
        'saved', 'stored', 'downloaded',
        'installed', 'set up', 'configured',
        'same', 'different', 'new', 'old',
        'correct', 'right', 'proper', 'appropriate'
    ]
    features['has_target_state'] = any(kw in text_lower for kw in state_keywords)

    # 5. 是否提供文件名、路径、工作表名或页面名
    # 检查是否有引号内容、大写的名字，或路径特征
    has_quotes = bool(re.search(r'["\'][^"\']{3,}["\']', text))
    has_path = bool(re.search(r'[A-Za-z]:[\\/]|/[A-Za-z0-9]|\.[a-z]{2,4}\b', text))
    has_sheet = bool(re.search(r'\bsheet\s+\d+|\btab\s+\d+', text_lower))
    features['has_file_reference'] = has_quotes or has_path or has_sheet

    # 6. 是否给出对象属性（颜色、位置、格式、数量、排序方式）
    property_keywords = [
        'red', 'blue', 'green', 'yellow', 'orange', 'purple', 'black', 'white',
        'color', 'colour', 'font', 'size', 'bold', 'italic', 'underline',
        'top', 'bottom', 'left', 'right', 'middle', 'center', 'above', 'below',
        'format', 'style', 'layout', 'template',
        'first', 'second', 'third', 'last', 'next', 'previous',
        'ascending', 'descending', 'sort', 'order', 'filter',
        'one', 'two', 'three', 'four', 'five', 'ten',
        '1', '2', '3', '4', '5', '6', '7', '8', '9', '10'
    ]
    features['has_object_properties'] = any(kw in text_lower for kw in property_keywords)

    # 7. 是否说明操作顺序
    order_keywords = [
        'first', 'then', 'next', 'after', 'before', 'finally', 'lastly',
        'step', 'follow', 'sequence', 'order', 'begin', 'start', 'end'
    ]
    features['has_operation_order'] = any(kw in text_lower for kw in order_keywords)

    # 8. 是否包含多个可区分的子任务
    # 检查是否有and、then、also等连接词，或多个句子
    num_sentences = text.count('.') + text.count('!') + text.count('?')
    num_conjunctions = len(re.findall(r'\band\b|\bthen\b|\balso\b|\bor\b', text_lower))
    features['has_multiple_subtasks'] = (num_sentences >= 2) or (num_conjunctions >= 2)

    # 9. 是否包含约束词
    constraint_keywords = [
        'only', 'just', 'not', "don't", "don’t", 'do not',
        'never', 'avoid', 'keep', 'stay', 'maintain',
        'without', 'except', 'but', 'however', 'must',
        'should', 'need to', 'have to', 'required'
    ]
    features['has_constraint_words'] = any(kw in text_lower for kw in constraint_keywords)

    # 10. 是否给出完成或验收标准
    criteria_keywords = [
        'until', 'when', 'once', 'after',
        'make sure', 'ensure', 'check', 'verify',
        'confirm', 'validate', 'test', 'done',
        'complete', 'finished', 'ready', 'successful'
    ]
    features['has_completion_criteria'] = any(kw in text_lower for kw in criteria_keywords)

    # 11. 是否说明当前初始状态
    state_desc_keywords = [
        'current', 'existing', 'already', 'currently',
        'there is', 'there are', 'we have', 'you have',
        'open', 'opened', 'closed', 'visible', 'showing',
        'in', 'on', 'at', 'with', 'using'
    ]
    features['has_initial_state'] = any(kw in text_lower for kw in state_desc_keywords)

    # 计算显性度分数
    binary_features = [
        'has_application', 'has_operation_object', 'has_target_action',
        'has_target_state', 'has_file_reference', 'has_object_properties',
        'has_operation_order', 'has_multiple_subtasks', 'has_constraint_words',
        'has_completion_criteria', 'has_initial_state'
    ]
    features['explicitness_score'] = sum(features.get(f, False) for f in binary_features)

    # 确定显性度级别
    if features['explicitness_score'] <= 3:
        features['explicitness_level'] = 'low'
    elif features['explicitness_score'] <= 6:
        features['explicitness_level'] = 'medium'
    else:
        features['explicitness_level'] = 'high'

    # 文本长度特征
    features['word_count'] = len(text.split())
    features['char_count'] = len(text)

    return features

def parse_and_analyze():
    """解析完整数据并运行分析"""
    print("=" * 60)
    print("AgentNet完整数据分析")
    print("=" * 60)

    # 使用agentnet_win_mac_18k.jsonl
    data_path = "data/raw/agentnet_win_mac_18k.jsonl"

    if not os.path.exists(data_path):
        print(f"文件不存在: {data_path}")
        return

    print(f"\n正在解析: {data_path}")

    # 解析数据
    tasks_data = []
    steps_data = []

    with open(data_path, 'r', encoding='utf-8') as f:
        for line_idx, line in enumerate(tqdm(f, desc="解析任务")):
            try:
                task = json.loads(line.strip())

                # 任务级数据
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

                # 提取指令特征
                instruction = task.get('instruction', '') or ''
                features = extract_features_from_text(instruction)
                task_info.update(features)

                # 处理轨迹
                traj = task.get('traj', [])
                total_steps = len(traj)
                correct_steps = 0
                incorrect_steps = 0
                redundant_steps = 0

                for step in traj:
                    step_idx = step.get('index', -1)
                    value = step.get('value', {})

                    is_correct = value.get('last_step_correct')
                    is_redundant = value.get('last_step_redundant')

                    if is_correct is True:
                        correct_steps += 1
                    if is_correct is False:
                        incorrect_steps += 1
                    if is_redundant is True:
                        redundant_steps += 1

                    # 步骤数据
                    steps_data.append({
                        'task_id': task.get('task_id', ''),
                        'step_index': step_idx,
                        'last_step_correct': is_correct,
                        'last_step_redundant': is_redundant
                    })

                # 计算过程特征
                task_info['total_steps'] = total_steps
                task_info['correct_ratio'] = correct_steps / total_steps if total_steps > 0 else None
                task_info['incorrect_ratio'] = incorrect_steps / total_steps if total_steps > 0 else None
                task_info['redundant_ratio'] = redundant_steps / total_steps if total_steps > 0 else None

                tasks_data.append(task_info)

                # 限制在200-500个样本进行分析（与研究计划一致）
                if len(tasks_data) >= 500:
                    break

            except Exception as e:
                continue

    print(f"\n解析完成: {len(tasks_data)} 个任务, {len(steps_data)} 个步骤")

    # 创建DataFrame
    df = pd.DataFrame(tasks_data)

    # 保存数据
    os.makedirs("data/interim", exist_ok=True)
    os.makedirs("data/processed", exist_ok=True)

    df.to_parquet("data/interim/tasks.parquet")
    df.to_csv("data/interim/tasks.csv", index=False, encoding='utf-8-sig')

    pd.DataFrame(steps_data).to_parquet("data/interim/steps.parquet")

    # 保存分析数据
    analysis_cols = [
        'task_id', 'instruction', 'task_completed',
        'efficiency_score', 'alignment_score', 'task_difficulty',
        'explicitness_score', 'explicitness_level',
        'has_application', 'has_operation_object', 'has_target_action',
        'has_target_state', 'has_file_reference', 'has_object_properties',
        'has_operation_order', 'has_multiple_subtasks', 'has_constraint_words',
        'has_completion_criteria', 'has_initial_state',
        'total_steps', 'correct_ratio', 'incorrect_ratio', 'redundant_ratio',
        'word_count', 'char_count', 'os'
    ]
    available_cols = [c for c in analysis_cols if c in df.columns]
    df_analysis = df[available_cols].copy()
    df_analysis.to_parquet("data/processed/analysis_data.parquet")
    df_analysis.to_csv("data/processed/analysis_data.csv", index=False, encoding='utf-8-sig')

    print(f"\n分析数据已保存: data/processed/analysis_data.parquet")
    print(f"样本数: {len(df_analysis)}")

    return df_analysis

if __name__ == "__main__":
    parse_and_analyze()
