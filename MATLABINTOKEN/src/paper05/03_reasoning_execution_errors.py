"""
03_reasoning_execution_errors.py - 构建推理错误与执行错误指标（论文五，向量化版）

基于显式推理链文本与步骤级 correctness/redundancy 标签，构建推理错误和执行错误代理指标。
"""

import re
import pandas as pd
import numpy as np
from pathlib import Path

INTERIM_DIR = Path("data/interim/paper05")


def make_pattern(words):
    return "|".join(f"(?:{w})" for w in words)


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
]
DECOMPOSITION_WORDS = [
    r"\bstep\b", r"\bstage\b", r"\bphase\b", r"\bsubtask\b",
    r"\bsub-task\b", r"\bpart\b",
]
SELF_CORRECTION_WORDS = [
    r"\bcorrect\b", r"\bfix\b", r"\bfixing\b", r"\bretry\b",
    r"\bretried\b", r"\btry again\b", r"\binstead\b", r"\brather\b",
    r"\breevaluate\b", r"\breconsider\b", r"\brevise\b", r"\bmistake\b",
    r"\bwrong\b", r"\berror\b",
]
TERMINATION_WORDS = [
    r"\bcompleted\b", r"\bdone\b", r"\bfinished\b", r"\bready\b",
    r"\bfinal\b", r"\bfinish\b", r"\bend\b",
]
ASSUMPTION_WORDS = [
    r"\bassuming\b", r"\bprobably\b", r"\blikely\b", r"\bshould be\b",
    r"\bmight be\b", r"\bexpected to be\b",
]
UNCERTAINTY_RE = r"\b(i think|i guess|maybe|perhaps|not sure|unclear|ambiguous)\b"
MISUNDERSTANDING_RE = r"\b(misunderstood|wrong task|not what the user wanted|incorrectly interpreted)\b"
OBSERVATION_ERROR_RE = r"\b(error|fail|failed|invalid|unable|not found|no such|cannot|exception)\b"

PATTERN_CONSTRAINT = make_pattern(CONSTRAINT_WORDS)
PATTERN_VERIFY = make_pattern(VERIFICATION_WORDS)
PATTERN_DECOMP = make_pattern(DECOMPOSITION_WORDS)
PATTERN_SELF_CORR = make_pattern(SELF_CORRECTION_WORDS)
PATTERN_TERMINATION = make_pattern(TERMINATION_WORDS)
PATTERN_ASSUMPTION = make_pattern(ASSUMPTION_WORDS)


def count_series(series, pattern):
    return series.fillna("").str.lower().str.count(pattern)


def count_pattern_text(text, pattern):
    return len(re.findall(pattern, str(text).lower()))


def main():
    print("=" * 60)
    print("论文五：构建推理错误与执行错误指标")
    print("=" * 60)

    steps = pd.read_parquet(INTERIM_DIR / "steps.parquet")
    tasks = pd.read_parquet(INTERIM_DIR / "tasks.parquet")
    print(f"加载任务 {len(tasks)}，步骤 {len(steps)}")

    steps = steps.sort_values(["task_id", "step_index"]).reset_index(drop=True)
    steps["reasoning_text"] = (steps["thought"].fillna("") + " " + steps["reflection"].fillna("")).str.strip()

    # 向量化步骤级计数
    steps["reasoning_constraint_mentions"] = count_series(steps["reasoning_text"], PATTERN_CONSTRAINT)
    steps["reasoning_verification_mentions"] = count_series(steps["reasoning_text"], PATTERN_VERIFY)
    steps["reasoning_decomp_mentions"] = count_series(steps["reasoning_text"], PATTERN_DECOMP)
    steps["reasoning_self_corr"] = count_series(steps["reasoning_text"], PATTERN_SELF_CORR)
    steps["reasoning_termination"] = count_series(steps["reasoning_text"], PATTERN_TERMINATION)
    steps["reasoning_assumption"] = count_series(steps["reasoning_text"], PATTERN_ASSUMPTION)
    steps["observation_error"] = steps["observation"].fillna("").str.lower().str.count(OBSERVATION_ERROR_RE)

    steps["last_step_correct"] = steps["last_step_correct"].fillna(True).astype(bool)
    steps["last_step_redundant"] = steps["last_step_redundant"].fillna(False).astype(bool)

    # 聚合到任务级
    agg = {
        "total_steps": ("step_index", "count"),
        "incorrect_steps": ("last_step_correct", lambda s: (~s).sum()),
        "redundant_steps": ("last_step_redundant", lambda s: s.sum()),
        "reasoning_text_all": ("reasoning_text", lambda s: " ".join(s.fillna("").astype(str))),
        "action_text_all": ("action", lambda s: " ".join(s.fillna("").astype(str))),
        "observation_text_all": ("observation", lambda s: " ".join(s.fillna("").astype(str))),
        "reasoning_constraint_total": ("reasoning_constraint_mentions", "sum"),
        "reasoning_verification_total": ("reasoning_verification_mentions", "sum"),
        "reasoning_decomp_total": ("reasoning_decomp_mentions", "sum"),
        "reasoning_self_corr_total": ("reasoning_self_corr", "sum"),
        "reasoning_termination_total": ("reasoning_termination", "sum"),
        "reasoning_assumption_total": ("reasoning_assumption", "sum"),
        "observation_error_count": ("observation_error", "sum"),
        "action_nonempty_count": ("action", lambda s: s.notna().sum()),
        "action_unique_count": ("action", lambda s: s.dropna().astype(str).nunique()),
    }
    err = steps.groupby("task_id").agg(**agg).reset_index()

    err["incorrect_ratio"] = err["incorrect_steps"] / err["total_steps"]
    err["redundant_ratio"] = err["redundant_steps"] / err["total_steps"]

    # 合并任务信息
    err = err.merge(tasks[["task_id", "instruction", "task_completed", "reason",
                           "task_difficulty", "alignment_score", "efficiency_score", "os"]],
                    on="task_id", how="left")
    err["task_completed_bool"] = err["task_completed"].fillna(False).astype(bool)

    # 指令级特征
    err["instruction_constraint_count"] = err["instruction"].apply(lambda x: count_pattern_text(x, PATTERN_CONSTRAINT))
    err["instruction_has_completion"] = err["instruction"].str.contains(
        r"\b(until|when|once|after|check|verify|confirm|ensure|make sure|correct|complete|done|finished|ready|satisfies|meets|fulfills)\b",
        case=False, na=False)
    err["instruction_has_multiple_subtasks"] = err["instruction"].apply(
        lambda x: len(re.findall(r"\band\b|\bthen\b|\bnext\b|\bafter that\b|;|\.|!|1\.|2\.|3\.|- |\* ", str(x), flags=re.IGNORECASE)) >= 2)

    # 推理错误指标（二元）
    err["err_goal_misunderstanding"] = (
        (~err["task_completed_bool"]) &
        ((err["reason"].str.lower().str.contains(MISUNDERSTANDING_RE, na=False)) |
         (err["reasoning_text_all"].str.lower().str.contains(UNCERTAINTY_RE, na=False)))
    ).astype(int)

    err["err_constraint_omission"] = (
        (err["instruction_constraint_count"] > 0) & (err["reasoning_constraint_total"] == 0)
    ).astype(int)

    err["err_wrong_env_assumption"] = (
        (err["reasoning_assumption_total"] > 0) & (err["reasoning_verification_total"] == 0)
    ).astype(int)

    err["err_task_decomposition"] = (
        (err["instruction_has_multiple_subtasks"]) & (err["reasoning_decomp_total"] == 0)
    ).astype(int)

    err["err_no_correction_after_error"] = (
        (err["incorrect_steps"] > 0) & (err["reasoning_self_corr_total"] == 0)
    ).astype(int)

    # 重复动作策略：存在动作重复且存在错误步骤
    err["err_repeat_strategy"] = (
        (err["incorrect_steps"] > 0) & (err["action_unique_count"] < err["action_nonempty_count"])
    ).astype(int)

    err["err_premature_completion"] = (
        (~err["task_completed_bool"]) & (err["reasoning_termination_total"] > 0)
    ).astype(int)

    err["err_lack_verification"] = (
        (err["instruction_has_completion"]) & (err["reasoning_verification_total"] == 0)
    ).astype(int)

    # 执行错误指标
    err["exec_wrong_tool_action"] = (err["incorrect_steps"] > 0).astype(int)
    err["exec_invalid_operation"] = (err["observation_error_count"] > 0).astype(int)
    err["exec_repeated_action"] = (err["redundant_steps"] > 0).astype(int)
    err["exec_failed_termination"] = (~err["task_completed_bool"]).astype(int)
    err["exec_task_incomplete"] = (~err["task_completed_bool"]).astype(int)

    reasoning_error_cols = [
        "err_goal_misunderstanding", "err_constraint_omission", "err_wrong_env_assumption",
        "err_task_decomposition", "err_no_correction_after_error", "err_repeat_strategy",
        "err_premature_completion", "err_lack_verification",
    ]
    execution_error_cols = [
        "exec_wrong_tool_action", "exec_invalid_operation", "exec_repeated_action",
        "exec_failed_termination", "exec_task_incomplete",
    ]
    err["reasoning_error_index"] = err[reasoning_error_cols].sum(axis=1)
    err["execution_error_index"] = err[execution_error_cols].sum(axis=1)

    err.to_parquet(INTERIM_DIR / "reasoning_execution_errors.parquet")
    print(f"\n错误指标已保存: {INTERIM_DIR / 'reasoning_execution_errors.parquet'}")
    print(f"特征维度: {err.shape}")
    print("\n推理错误指标均值:")
    for c in reasoning_error_cols:
        print(f"  {c}: {err[c].mean()*100:.1f}%")
    print(f"  reasoning_error_index: mean={err['reasoning_error_index'].mean():.2f}")
    print("\n执行错误指标均值:")
    for c in execution_error_cols:
        print(f"  {c}: {err[c].mean()*100:.1f}%")
    print(f"  execution_error_index: mean={err['execution_error_index'].mean():.2f}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
