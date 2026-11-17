"""
04_extract_instruction_features.py - 提取任务表达特征

从任务文本中提取操作显性度特征（规则型，不调用语言模型）
"""

import os
import re
import json
import pandas as pd
from pathlib import Path
from datetime import datetime


def load_tasks():
    """加载任务数据"""
    tasks_path = "data/interim/tasks.parquet"
    if os.path.exists(tasks_path):
        return pd.read_parquet(tasks_path)
    return None


def has_application(text):
    """是否明确指出应用或软件"""
    if not text:
        return False
    apps = [
        "word", "excel", "powerpoint", "outlook",
        "chrome", "firefox", "safari", "edge", "browser",
        "notepad", "paint", "calculator",
        "photoshop", "illustrator", "indesign",
        "windows", "mac", "linux",
        "file", "explorer", "finder",
        "email", "mail",
    ]
    text_lower = text.lower()
    return any(app in text_lower for app in apps)


def has_operation_object(text):
    """是否明确指出操作对象"""
    if not text:
        return False
    object_indicators = [
        r"the \w+", r"this \w+", r"that \w+",
        r"\bfile\b", r"\bfolder\b", r"\bdocument\b", r"\bimage\b", r"\bphoto\b",
        r"\btable\b", r"\bcolumn\b", r"\brow\b", r"\bcell\b",
        r"\btext\b", r"\bparagraph\b", r"\bsentence\b", r"\bword\b",
        r"\bbutton\b", r"\blink\b", r"\bmenu\b", r"\btab\b",
    ]
    for pattern in object_indicators:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def has_target_action(text):
    """是否明确指出目标动作"""
    if not text:
        return False
    action_verbs = [
        "open", "close", "save", "delete", "remove", "copy", "paste", "cut",
        "create", "make", "new", "edit", "modify", "change", "update",
        "find", "search", "look", "select", "choose", "click", "press",
        "type", "write", "enter", "input", "fill",
        "move", "drag", "go", "navigate",
        "download", "upload", "send", "receive",
        "print", "share", "export", "import",
    ]
    text_lower = text.lower()
    return any(verb in text_lower for verb in action_verbs)


def has_target_state(text):
    """是否明确指出目标状态"""
    if not text:
        return False
    state_indicators = [
        r"should be", r"needs to be", r"must be", r"has to be",
        r"so that", r"such that", r"result in", r"to have",
        r"completed", r"finished", r"done", r"ready",
        r"correct", r"right", r"proper", r"appropriate",
    ]
    for pattern in state_indicators:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def has_file_reference(text):
    """是否提供文件名、路径、工作表名或页面名"""
    if not text:
        return False
    file_patterns = [
        r"\w+\.(txt|doc|docx|xls|xlsx|csv|pdf|png|jpg|jpeg|gif|ppt|pptx)",
        r"sheet \d+", r"sheet ['\"]\w+['\"]", r"worksheet",
        r"page \d+", r"tab \w+",
        r"folder \w+", r"directory \w+",
        r"/[\w/]+", r"\\[\w\\]+",  # 路径
    ]
    for pattern in file_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def has_object_properties(text):
    """是否给出对象属性"""
    if not text:
        return False
    property_patterns = [
        r"red|blue|green|yellow|black|white|orange|purple|pink|gray|grey",  # 颜色
        r"top|bottom|left|right|middle|center|first|last|next|previous",  # 位置
        r"bold|italic|underline|strikethrough",  # 格式
        r"\d+ (rows?|columns?|lines?|pages?|items?|files?)",  # 数量
        r"sorted|ordered|arranged|grouped",  # 排序
        r"size \d+|width \d+|height \d+",  # 尺寸
    ]
    for pattern in property_patterns:
        if re.search(r"\b" + pattern + r"\b", text, re.IGNORECASE):
            return True
    return False


def has_operation_order(text):
    """是否说明操作顺序"""
    if not text:
        return False
    order_words = [
        "first", "second", "third", "then", "next", "after", "before",
        "finally", "lastly", "subsequently", "following",
    ]
    text_lower = text.lower()
    return any(word in text_lower for word in order_words)


def has_multiple_subtasks(text):
    """是否包含多个可区分的子任务"""
    if not text:
        return False
    separators = [
        r"\band\b", r"\bthen\b", r"\bnext\b", r"\bafter that\b",
        r";", r"\.", r"!",
        r"1\.", r"2\.", r"3\.", r"- ", r"\* ",
    ]
    count = 0
    for sep in separators:
        count += len(re.findall(sep, text, re.IGNORECASE))
    return count >= 2


def has_constraint_words(text):
    """是否包含约束词"""
    if not text:
        return False
    constraints = [
        r"\bonly\b", r"\bjust\b", r"\bmerely\b",
        r"\bdon.?t\b", r"\bdo not\b", r"\bnever\b", r"\bno\b",
        r"\bkeep\b", r"\bleave\b", r"\bmaintain\b", r"\bretain\b",
        r"\bwithout\b", r"\bavoid\b",
        r"\bshould not\b", r"\bmust not\b", r"\bcannot\b",
    ]
    for pattern in constraints:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def has_completion_criteria(text):
    """是否给出完成或验收标准"""
    if not text:
        return False
    criteria_patterns = [
        r"until", r"when", r"once", r"after",
        r"check", r"verify", r"confirm", r"ensure", r"make sure",
        r"correct", r"complete", r"done", r"finished", r"ready",
        r" satisfies", r" meets", r" fulfills",
    ]
    for pattern in criteria_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def has_initial_state(text):
    """是否说明当前初始状态"""
    if not text:
        return False
    initial_patterns = [
        r"current(ly)?", r"now", r"already", r"existing", r"present",
        r"there is|there are", r"you have", r"we have",
        r"starts? with", r"begins? with",
        r"assuming", r"given that",
    ]
    for pattern in initial_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def has_vague_reference(text):
    """是否包含指代不明或省略表达"""
    if not text:
        return False
    vague_patterns = [
        r"\bit\b", r"\bthis\b", r"\bthat\b", r"\bthese\b", r"\bthose\b",
        r"\bthe same\b", r"\blike that\b", r"\bas before\b",
        r"\betc\b", r"\band so on\b", r"\band the like\b",
        r"\byou know\b", r"\bas usual\b",
    ]
    for pattern in vague_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def count_words(text):
    """文本词数"""
    if not text:
        return 0
    return len(re.findall(r"\w+", text))


def count_chars(text):
    """文本字符数"""
    if not text:
        return 0
    return len(text)


def count_verbs(text):
    """动词数量（基于常见动词列表）"""
    if not text:
        return 0
    common_verbs = [
        "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did",
        "will", "would", "could", "should", "may", "might", "must", "can",
        "open", "close", "save", "delete", "copy", "paste", "cut",
        "create", "make", "edit", "modify", "change", "update",
        "find", "search", "look", "select", "choose", "click", "press",
        "type", "write", "enter", "input", "fill",
        "move", "drag", "go", "navigate",
        "download", "upload", "send", "receive",
        "print", "share", "export", "import",
        "see", "view", "read", "show", "display",
        "use", "using", "used",
    ]
    text_lower = text.lower()
    count = 0
    for verb in common_verbs:
        count += len(re.findall(r"\b" + verb + r"\b", text_lower))
    return count


def count_conditionals(text):
    """条件从句数量"""
    if not text:
        return 0
    conditional_patterns = [
        r"\bif\b", r"\bwhen\b", r"\bunless\b", r"\buntil\b", r"\bwhile\b",
        r"\bprovided that\b", r"\bas long as\b", r"\bin case\b",
    ]
    count = 0
    for pattern in conditional_patterns:
        count += len(re.findall(pattern, text, re.IGNORECASE))
    return count


def count_sequence_connectors(text):
    """顺序连接词数量"""
    if not text:
        return 0
    connectors = [
        r"\bfirst\b", r"\bsecond\b", r"\bthird\b", r"\bthen\b", r"\bnext\b",
        r"\bafter\b", r"\bbefore\b", r"\bfinally\b", r"\blastly\b",
        r"\bsubsequently\b", r"\bfollowing\b",
    ]
    count = 0
    for pattern in connectors:
        count += len(re.findall(pattern, text, re.IGNORECASE))
    return count


def extract_features_from_text(text):
    """从文本中提取所有特征"""
    if pd.isna(text) or text is None:
        text = ""
    text = str(text)

    features = {}

    # 二元特征
    features["has_application"] = has_application(text)
    features["has_operation_object"] = has_operation_object(text)
    features["has_target_action"] = has_target_action(text)
    features["has_target_state"] = has_target_state(text)
    features["has_file_reference"] = has_file_reference(text)
    features["has_object_properties"] = has_object_properties(text)
    features["has_operation_order"] = has_operation_order(text)
    features["has_multiple_subtasks"] = has_multiple_subtasks(text)
    features["has_constraint_words"] = has_constraint_words(text)
    features["has_completion_criteria"] = has_completion_criteria(text)
    features["has_initial_state"] = has_initial_state(text)
    features["has_vague_reference"] = has_vague_reference(text)

    # 计数特征
    features["word_count"] = count_words(text)
    features["char_count"] = count_chars(text)
    features["verb_count"] = count_verbs(text)
    features["conditional_count"] = count_conditionals(text)
    features["sequence_connector_count"] = count_sequence_connectors(text)

    # 综合指数（排除vague_reference，因为它是负向指标）
    positive_features = [
        "has_application", "has_operation_object", "has_target_action",
        "has_target_state", "has_file_reference", "has_object_properties",
        "has_operation_order", "has_multiple_subtasks", "has_constraint_words",
        "has_completion_criteria", "has_initial_state",
    ]
    features["explicitness_score"] = sum(features[f] for f in positive_features)

    # 三级分组
    score = features["explicitness_score"]
    if score <= 3:
        features["explicitness_level"] = "low"
    elif score <= 6:
        features["explicitness_level"] = "medium"
    else:
        features["explicitness_level"] = "high"

    return features


def main():
    """主函数"""
    print("=" * 60)
    print("提取任务表达特征")
    print("=" * 60)

    # 加载任务数据
    tasks_df = load_tasks()

    if tasks_df is None or len(tasks_df) == 0:
        print("\n未找到任务数据，请先运行 03_parse_trajectories.py")
        return 1

    print(f"\n加载了 {len(tasks_df)} 个任务")

    # 确定使用哪个文本字段
    text_fields = []
    for field in ["instruction", "natural_language_task", "actual_task"]:
        if field in tasks_df.columns:
            non_null = tasks_df[field].notna().sum()
            if non_null > 0:
                text_fields.append((field, non_null))
                print(f"  - {field}: {non_null} 非空值")

    if not text_fields:
        print("\n错误: 未找到任务文本字段")
        return 1

    # 对每个文本字段提取特征
    all_features = []

    for idx, row in tasks_df.iterrows():
        task_features = {}

        # 确保有task_id
        if "task_id" in row:
            task_features["task_id"] = row["task_id"]
        else:
            task_features["task_id"] = f"task_{idx}"

        # 从各个文本字段提取特征
        for field, _ in text_fields:
            text = row.get(field, "")
            features = extract_features_from_text(text)

            # 加前缀保存
            for key, value in features.items():
                task_features[f"{field}_{key}"] = value

        # 使用主要字段的特征（优先instruction，然后natural_language_task，然后actual_task）
        primary_field = None
        for field in ["instruction", "natural_language_task", "actual_task"]:
            if field in tasks_df.columns:
                if pd.notna(row.get(field)) and str(row.get(field)).strip():
                    primary_field = field
                    break

        if primary_field:
            text = row[primary_field]
            primary_features = extract_features_from_text(text)

            # 保存为主特征（无前缀）
            for key, value in primary_features.items():
                task_features[key] = value

            task_features["primary_text_field"] = primary_field
        else:
            task_features["primary_text_field"] = None

        all_features.append(task_features)

    # 保存特征
    features_df = pd.DataFrame(all_features)
    output_path = "data/interim/instruction_features.parquet"
    features_df.to_parquet(output_path)

    print(f"\n特征已保存: {output_path}")

    # 显示统计
    print("\n特征统计:")
    if "explicitness_score" in features_df.columns:
        print(f"  显性度分数:")
        print(f"    最小值: {features_df['explicitness_score'].min()}")
        print(f"    最大值: {features_df['explicitness_score'].max()}")
        print(f"    平均值: {features_df['explicitness_score'].mean():.2f}")

    if "explicitness_level" in features_df.columns:
        level_counts = features_df["explicitness_level"].value_counts()
        print(f"  显性度级别:")
        for level, count in level_counts.items():
            print(f"    {level}: {count}")

    # 保存特征定义
    feature_definitions = {
        "binary_features": {
            "has_application": "是否明确指出应用或软件",
            "has_operation_object": "是否明确指出操作对象",
            "has_target_action": "是否明确指出目标动作",
            "has_target_state": "是否明确指出目标状态",
            "has_file_reference": "是否提供文件名、路径、工作表名或页面名",
            "has_object_properties": "是否给出对象属性（颜色、位置、格式、数量、排序）",
            "has_operation_order": "是否说明操作顺序",
            "has_multiple_subtasks": "是否包含多个可区分的子任务",
            "has_constraint_words": "是否包含约束词（只、不要、保持）",
            "has_completion_criteria": "是否给出完成或验收标准",
            "has_initial_state": "是否说明当前初始状态",
            "has_vague_reference": "是否包含指代不明或省略表达",
        },
        "count_features": {
            "word_count": "文本词数",
            "char_count": "文本字符数",
            "verb_count": "动词数量",
            "conditional_count": "条件从句数量",
            "sequence_connector_count": "顺序连接词数量",
        },
        "composite_features": {
            "explicitness_score": "操作显性度加总指数（正向特征之和）",
            "explicitness_level": "操作显性度三级分组（low/medium/high）",
        },
    }

    def_path = "data/interim/feature_definitions.json"
    with open(def_path, "w", encoding="utf-8") as f:
        json.dump(feature_definitions, f, ensure_ascii=False, indent=2)

    print(f"\n特征定义已保存: {def_path}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
