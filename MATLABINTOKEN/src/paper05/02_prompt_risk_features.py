"""
02_prompt_risk_features.py - 构建用户指令风险特征（论文五）

继承前三篇论文的提示语用特征，并扩展构建提示风险特征。
"""

import re
import pandas as pd
import numpy as np
from pathlib import Path

INTERIM_DIR = Path("data/interim/paper05")
RESULTS_DIR = Path("paper05_prompt_risk_failure/results/tables")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def count_words(text):
    return len(re.findall(r"\w+", str(text)))


def count_constraint_words(text):
    constraints = [
        r"\bonly\b", r"\bjust\b", r"\bmerely\b",
        r"\bdon'?t\b", r"\bdo not\b", r"\bnever\b", r"\bno\b",
        r"\bkeep\b", r"\bleave\b", r"\bmaintain\b", r"\bretain\b",
        r"\bwithout\b", r"\bavoid\b",
        r"\bshould not\b", r"\bmust not\b", r"\bcannot\b",
        r"\bmust\b", r"\bshould\b", r"\bneed\b", r"\bhave to\b",
        r"\brequired\b",
    ]
    text = str(text).lower()
    return sum(len(re.findall(p, text)) for p in constraints)


def has_requirement_and_prohibition(text):
    t = str(text).lower()
    req = bool(re.search(r"\b(must|should|need to|have to|required)\b", t))
    pro = bool(re.search(r"\b(don'?t|do not|never|avoid|without|must not|should not|cannot)\b", t))
    return req and pro


def extract_instruction_features(text):
    t = str(text)
    lower = t.lower()

    has_application = bool(re.search(r"\b(word|excel|powerpoint|outlook|chrome|firefox|safari|edge|browser|notepad|paint|calculator|photoshop|illustrator|windows|mac|linux|file explorer|finder|email|mail)\b", lower))
    has_operation_object = bool(re.search(r"\b(the \w+|this \w+|that \w+|file|folder|document|image|photo|table|column|row|cell|text|paragraph|sentence|word|button|link|menu|tab)\b", lower))
    has_target_action = bool(re.search(r"\b(open|close|save|delete|remove|copy|paste|cut|create|make|new|edit|modify|change|update|find|search|look|select|choose|click|press|type|write|enter|input|fill|move|drag|go|navigate|download|upload|send|receive|print|share|export|import)\b", lower))
    has_target_state = bool(re.search(r"\b(should be|needs to be|must be|has to be|so that|such that|result in|to have|completed|finished|done|ready|correct|right|proper|appropriate)\b", lower))
    has_file_reference = bool(re.search(r"\w+\.(txt|doc|docx|xls|xlsx|csv|pdf|png|jpg|jpeg|gif|ppt|pptx)|sheet \d+|worksheet|page \d+|tab \w+|folder \w+|directory \w+|/[\w/]+|\\\\[\w\\\\]+", lower))
    has_operation_order = bool(re.search(r"\b(first|second|third|then|next|after|before|finally|lastly|subsequently|following)\b", lower))
    has_multiple_subtasks = len(re.findall(r"\band\b|\bthen\b|\bnext\b|\bafter that\b|;|\.|!|1\.|2\.|3\.|- |\* ", t, flags=re.IGNORECASE)) >= 2
    has_completion_criteria = bool(re.search(r"\b(until|when|once|after|check|verify|confirm|ensure|make sure|correct|complete|done|finished|ready|satisfies|meets|fulfills)\b", lower))
    has_explicit_verification = bool(re.search(r"\b(check|verify|confirm|test|inspect|examine|validate)\b", lower))
    has_initial_state = bool(re.search(r"\b(current(ly)?|now|already|existing|present|there is|there are|you have|we have|starts? with|begins? with|assuming|given that)\b", lower))
    has_vague_reference = bool(re.search(r"\b(it|this|that|these|those|the same|like that|as before|etc|and so on|and the like)\b", lower))

    word_count = count_words(t)
    constraint_count = count_constraint_words(t)
    constraint_density = (constraint_count / max(word_count, 1)) * 100

    return {
        "word_count": word_count,
        "has_application": has_application,
        "has_operation_object": has_operation_object,
        "has_target_action": has_target_action,
        "has_target_state": has_target_state,
        "has_file_reference": has_file_reference,
        "has_operation_order": has_operation_order,
        "has_multiple_subtasks": has_multiple_subtasks,
        "has_completion_criteria": has_completion_criteria,
        "has_explicit_verification": has_explicit_verification,
        "has_initial_state": has_initial_state,
        "has_vague_reference": has_vague_reference,
        "constraint_count": constraint_count,
        "constraint_density": constraint_density,
    }


def main():
    print("=" * 60)
    print("论文五：构建提示风险特征")
    print("=" * 60)

    tasks = pd.read_parquet(INTERIM_DIR / "tasks.parquet")
    print(f"加载任务 {len(tasks)}")

    # 提取基础语用特征
    features = tasks["instruction"].apply(extract_instruction_features).apply(pd.Series)
    df = pd.concat([tasks[["task_id", "instruction", "natural_language_task", "actual_task",
                            "task_completed", "task_difficulty", "alignment_score",
                            "efficiency_score", "os", "domain"]], features], axis=1)

    # 构建显性度分数（沿用前三篇正向指标）
    positive = ["has_application", "has_operation_object", "has_target_action",
                "has_target_state", "has_file_reference", "has_operation_order",
                "has_multiple_subtasks", "has_completion_criteria", "has_initial_state"]
    df["explicitness_score"] = df[positive].sum(axis=1)

    # 构建风险特征
    df["goal_abstraction"] = df["has_target_action"] & (~df["has_operation_object"]) & (~df["has_target_state"])
    df["object_missing"] = ~df["has_operation_object"]
    df["completion_standard_missing"] = ~df["has_completion_criteria"]
    df["constraint_missing"] = df["constraint_count"] == 0
    # 约束密度 > 5% 视为过密，缺失与过密均可能增加理解难度
    df["constraint_overdense"] = df["constraint_density"] > 5.0
    df["constraint_missing_or_dense"] = df["constraint_missing"] | df["constraint_overdense"]
    df["multi_subtask_no_order"] = df["has_multiple_subtasks"] & (~df["has_operation_order"])
    df["constraint_conflict"] = df["instruction"].apply(has_requirement_and_prohibition)
    df["vague_reference"] = df["has_vague_reference"]
    df["initial_state_missing"] = ~df["has_initial_state"]
    df["verification_missing"] = ~df["has_explicit_verification"]

    # 风险指数：风险特征数量
    risk_features = [
        "goal_abstraction", "object_missing", "completion_standard_missing",
        "constraint_missing", "constraint_overdense", "multi_subtask_no_order",
        "constraint_conflict", "vague_reference", "initial_state_missing", "verification_missing",
    ]
    df["risk_index"] = df[risk_features].sum(axis=1)

    df.to_parquet(INTERIM_DIR / "prompt_risk_features.parquet")
    print(f"提示风险特征已保存: {INTERIM_DIR / 'prompt_risk_features.parquet'}")
    print(f"特征维度: {df.shape}")
    print("\n风险特征分布:")
    for f in risk_features + ["risk_index"]:
        if f == "risk_index":
            print(f"  {f}: mean={df[f].mean():.2f}, sd={df[f].std():.2f}")
        else:
            print(f"  {f}: {df[f].mean()*100:.1f}%")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
