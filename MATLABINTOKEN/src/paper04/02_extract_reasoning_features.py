"""
02_extract_reasoning_features.py - 提取显式推理链特征（论文四，向量化版）

基于 thought + reflection + action + observation 文本，构建推理链特征体系。
"""

import re
import pandas as pd
import numpy as np
from pathlib import Path

INTERIM_DIR = Path("data/interim/paper04")
OUTPUT_PATH = INTERIM_DIR / "reasoning_features.parquet"


def make_pattern(words):
    return "|".join(f"(?:{w})" for w in words)


STRUCTURE_MARKERS = [
    r"\bplan\b", r"\bgoal\b", r"\bobjective\b", r"\bstep\b",
    r"\bfirst\b", r"\bsecond\b", r"\bthird\b", r"\bthen\b",
    r"\bnext\b", r"\bafter\b", r"\bbefore\b", r"\bfinally\b",
    r"\blastly\b", r"\bsubtask\b", r"\bsub-task\b",
]
DECOMPOSITION_WORDS = [
    r"\bstep\b", r"\bstage\b", r"\bphase\b", r"\bsubtask\b",
    r"\bsub-task\b", r"\bpart\b", r"\bportion\b",
]
CONSTRAINT_WORDS = [
    r"\bonly\b", r"\bjust\b", r"\bmerely\b",
    r"\bdon'?t\b", r"\bdo not\b", r"\bnever\b", r"\bno\b",
    r"\bkeep\b", r"\bleave\b", r"\bmaintain\b", r"\bretain\b",
    r"\bwithout\b", r"\bavoid\b",
    r"\bshould not\b", r"\bmust not\b", r"\bcannot\b",
    r"\bmust\b", r"\bshould\b", r"\bneed\b", r"\bhave to\b",
    r"\brequired\b",
]
VERIFICATION_WORDS = [
    r"\bcheck\b", r"\bverify\b", r"\bconfirm\b", r"\bvalidate\b",
    r"\bensure\b", r"\bmake sure\b", r"\btest\b", r"\binspect\b",
    r"\bexamine\b",
]
FEEDBACK_PHRASES = [
    r"\bthe screen shows\b", r"\bthe result shows?\b", r"\bthe output shows?\b",
    r"\bthe observation\b", r"\bi can see\b", r"\bthis indicates\b",
    r"\bthis means\b",
]
SELF_CORRECTION_PHRASES = [
    r"\bcorrect\b", r"\bfix\b", r"\bfixing\b", r"\bretry\b",
    r"\bretried\b", r"\btry again\b", r"\binstead\b", r"\brather\b",
    r"\breevaluate\b", r"\breconsider\b", r"\brevise\b", r"\bmistake\b",
    r"\bwrong\b", r"\berror\b", r"\bnot quite\b", r"\bneed to adjust\b",
]
TERMINATION_WORDS = [
    r"\bcompleted\b", r"\bdone\b", r"\bfinished\b", r"\bready\b",
    r"\bfinal\b", r"\bfinish\b", r"\bterminate\b", r"\bend\b",
    r"\bconclude\b",
]

PATTERN_STRUCTURE = make_pattern(STRUCTURE_MARKERS)
PATTERN_DECOMP = make_pattern(DECOMPOSITION_WORDS)
PATTERN_CONSTRAINT = make_pattern(CONSTRAINT_WORDS)
PATTERN_VERIFY = make_pattern(VERIFICATION_WORDS)
PATTERN_FEEDBACK = make_pattern(FEEDBACK_PHRASES)
PATTERN_SELF_CORR = make_pattern(SELF_CORRECTION_PHRASES)
PATTERN_TERMINATION = make_pattern(TERMINATION_WORDS)


def count_text_series(series, pattern):
    return series.fillna("").str.lower().str.count(pattern)


def token_set_from_text(text):
    return set(re.findall(r"\b[a-z]{4,}\b", str(text).lower()))


def main():
    print("=" * 60)
    print("论文四：提取显式推理链特征")
    print("=" * 60)

    steps_path = INTERIM_DIR / "steps.parquet"
    tasks_path = INTERIM_DIR / "tasks.parquet"
    if not steps_path.exists() or not tasks_path.exists():
        print("请先运行 01_parse_agentnet.py")
        return 1

    steps = pd.read_parquet(steps_path)
    tasks = pd.read_parquet(tasks_path)
    print(f"加载任务 {len(tasks)}，步骤 {len(steps)}")

    steps = steps.sort_values(["task_id", "step_index"]).reset_index(drop=True)

    # 合并推理文本
    steps["reasoning_text"] = (steps["thought"].fillna("") + " " + steps["reflection"].fillna("")).str.strip()

    # 基础计数
    steps["reasoning_chars"] = steps["reasoning_text"].str.len()
    steps["reasoning_words"] = steps["reasoning_text"].str.count(r"\w+")

    steps["structure_markers"] = count_text_series(steps["reasoning_text"], PATTERN_STRUCTURE)
    steps["decomposition_words"] = count_text_series(steps["reasoning_text"], PATTERN_DECOMP)
    steps["constraint_mentions"] = count_text_series(steps["reasoning_text"], PATTERN_CONSTRAINT)
    steps["verification_mentions"] = count_text_series(steps["reasoning_text"], PATTERN_VERIFY)
    steps["feedback_phrases"] = count_text_series(steps["reasoning_text"], PATTERN_FEEDBACK)
    steps["self_correction_phrases"] = count_text_series(steps["reasoning_text"], PATTERN_SELF_CORR)
    steps["termination_mentions"] = count_text_series(steps["reasoning_text"], PATTERN_TERMINATION)

    # 任务最后 20% 步骤的终止词
    steps["steps_in_task"] = steps.groupby("task_id")["step_index"].transform("count")
    steps["is_last_20pct"] = steps["step_index"] >= (steps["steps_in_task"] * 0.8)
    steps["termination_last20_mentions"] = steps["termination_mentions"] * steps["is_last_20pct"].astype(int)

    # 聚合到任务级
    agg_spec = {
        "n_steps": ("step_index", "count"),
        "n_thought_steps": ("thought", lambda s: s.notna().sum()),
        "n_reflection_steps": ("reflection", lambda s: s.notna().sum()),
        "reasoning_chars": ("reasoning_chars", "sum"),
        "reasoning_words": ("reasoning_words", "sum"),
        "avg_thought_chars": ("reasoning_chars", lambda s: s.sum() / max(s.gt(0).sum(), 1)),
        "avg_thought_words": ("reasoning_words", lambda s: s.sum() / max(s.gt(0).sum(), 1)),
        "structure_markers": ("structure_markers", "sum"),
        "decomposition_words": ("decomposition_words", "sum"),
        "constraint_mentions": ("constraint_mentions", "sum"),
        "verification_mentions": ("verification_mentions", "sum"),
        "feedback_phrases": ("feedback_phrases", "sum"),
        "self_correction_phrases": ("self_correction_phrases", "sum"),
        "termination_mentions": ("termination_mentions", "sum"),
        "termination_last20_mentions": ("termination_last20_mentions", "sum"),
    }
    feat = steps.groupby("task_id").agg(**agg_spec).reset_index()

    # 推理—行动对齐：任务级 action tokens 与 reasoning tokens 的交集比例
    task_texts = steps.groupby("task_id").agg(
        action_text_all=("action", lambda s: " ".join(s.fillna("").astype(str))),
        reasoning_text_all=("reasoning_text", lambda s: " ".join(s.fillna("").astype(str))),
    ).reset_index()

    task_texts["action_tokens"] = task_texts["action_text_all"].apply(token_set_from_text)
    task_texts["reasoning_tokens"] = task_texts["reasoning_text_all"].apply(token_set_from_text)
    task_texts["tool_mentions_in_reasoning"] = task_texts.apply(
        lambda r: len(r["action_tokens"] & r["reasoning_tokens"]), axis=1)
    action_token_counts = task_texts["action_tokens"].apply(len).clip(lower=1)
    task_texts["reasoning_action_alignment"] = task_texts.apply(
        lambda r: len(r["action_tokens"] & r["reasoning_tokens"]) / max(len(r["action_tokens"]), 1), axis=1)

    feat = feat.merge(
        task_texts[["task_id", "tool_mentions_in_reasoning", "reasoning_action_alignment"]],
        on="task_id", how="left"
    )

    # 合并任务元数据
    feat = feat.merge(
        tasks[["task_id", "instruction", "natural_language_task", "actual_task",
               "task_completed", "task_difficulty", "alignment_score",
               "efficiency_score", "os", "domain"]],
        on="task_id", how="left"
    )

    # log1p 变换备用
    count_cols = ["reasoning_chars", "reasoning_words", "structure_markers",
                  "decomposition_words", "constraint_mentions", "verification_mentions",
                  "feedback_phrases", "self_correction_phrases", "termination_mentions",
                  "termination_last20_mentions", "tool_mentions_in_reasoning"]
    for c in count_cols:
        feat[f"{c}_log1p"] = np.log1p(feat[c])

    feat.to_parquet(OUTPUT_PATH)
    print(f"\n推理链特征已保存: {OUTPUT_PATH}")
    print(f"特征维度: {feat.shape}")
    print("\n关键描述统计:")
    print(feat[["reasoning_words", "structure_markers", "decomposition_words",
                "verification_mentions", "self_correction_phrases",
                "reasoning_action_alignment"]].describe())
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
