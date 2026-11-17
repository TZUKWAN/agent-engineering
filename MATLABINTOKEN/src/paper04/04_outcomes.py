"""
04_outcomes.py - 显式推理链类型与执行结果的关系（论文四）

比较不同推理链类型在行动步数、错误率、冗余率、任务完成上的差异。
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats
import statsmodels.api as sm
import statsmodels.formula.api as smf

INTERIM_DIR = Path("data/interim/paper04")
RESULTS_DIR = Path("paper04_reasoning_typology/results/tables")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def compute_process_metrics(steps: pd.DataFrame) -> pd.DataFrame:
    steps["last_step_correct"] = steps["last_step_correct"].fillna(True)
    steps["last_step_redundant"] = steps["last_step_redundant"].fillna(False)

    metrics = steps.groupby("task_id").agg(
        total_steps=("step_index", "count"),
        incorrect_steps=("last_step_correct", lambda s: (~s.astype(bool)).sum()),
        redundant_steps=("last_step_redundant", lambda s: s.astype(bool).sum()),
        action_steps=("action", lambda s: s.notna().sum()),
    ).reset_index()
    metrics["incorrect_ratio"] = metrics["incorrect_steps"] / metrics["total_steps"]
    metrics["redundant_ratio"] = metrics["redundant_steps"] / metrics["total_steps"]
    return metrics


def anova_table(df, outcome, group_col="reasoning_type_label"):
    groups = [g[outcome].dropna().values for _, g in df.groupby(group_col)]
    f, p = stats.f_oneway(*groups)
    # eta-squared
    ss_between = sum(len(g) * (np.mean(g) - np.mean(df[outcome].dropna())) ** 2 for g in groups)
    ss_total = np.nansum((df[outcome] - np.nanmean(df[outcome])) ** 2)
    eta2 = ss_between / ss_total if ss_total > 0 else np.nan
    return {"f": float(f), "p": float(p), "eta_squared": float(eta2)}


def main():
    print("=" * 60)
    print("论文四：推理链类型与执行结果")
    print("=" * 60)

    df = pd.read_parquet(INTERIM_DIR / "reasoning_features_typed.parquet")
    steps = pd.read_parquet(INTERIM_DIR / "steps.parquet")
    metrics = compute_process_metrics(steps)
    df = df.merge(metrics, on="task_id", how="left")

    # 基本描述：各类型的结果均值
    outcomes = ["total_steps", "incorrect_ratio", "redundant_ratio",
                "task_completed", "alignment_score", "efficiency_score"]
    desc = df.groupby("reasoning_type_label")[outcomes].agg(["mean", "std", "count"])
    desc.to_csv(RESULTS_DIR / "outcome_descriptives.csv")
    print("\n各类型结果描述统计:")
    print(desc)

    # 方差分析（连续变量）
    anova_results = {}
    for var in ["total_steps", "incorrect_ratio", "redundant_ratio", "alignment_score", "efficiency_score"]:
        anova_results[var] = anova_table(df, var)
    with open(RESULTS_DIR / "anova_results.json", "w", encoding="utf-8") as f:
        json.dump(anova_results, f, ensure_ascii=False, indent=2)
    print("\nANOVA 结果:")
    for k, v in anova_results.items():
        print(f"  {k}: F={v['f']:.2f}, p={v['p']:.4f}, eta²={v['eta_squared']:.4f}")

    # 卡方检验（任务完成）
    ct = pd.crosstab(df["reasoning_type_label"], df["task_completed"])
    chi2, p_chi, dof, expected = stats.chi2_contingency(ct)
    chi_res = {"chi2": float(chi2), "p": float(p_chi), "dof": int(dof)}
    ct.to_csv(RESULTS_DIR / "completion_crosstab.csv")
    with open(RESULTS_DIR / "chi2_results.json", "w", encoding="utf-8") as f:
        json.dump(chi_res, f, ensure_ascii=False, indent=2)
    print(f"\n任务完成率卡方检验: chi2={chi2:.2f}, p={p_chi:.4f}")
    print(ct)

    # Logistic 回归：类型对任务完成的预测（控制任务难度、os、指令词数）
    reg_df = df.dropna(subset=["task_completed", "task_difficulty", "reasoning_words", "os"]).copy()
    reg_df["completed_num"] = reg_df["task_completed"].astype(int)
    reg_df["reasoning_words_c"] = reg_df["reasoning_words"] - reg_df["reasoning_words"].mean()

    formula = (
        "completed_num ~ C(reasoning_type_label, Treatment(reference='常规综合型')) "
        "+ task_difficulty + reasoning_words_c + C(os)"
    )
    logit = smf.logit(formula, data=reg_df).fit(disp=False)
    logit_summary = pd.DataFrame({
        "coef": logit.params,
        "se": logit.bse,
        "z": logit.tvalues,
        "p": logit.pvalues,
        "OR": np.exp(logit.params),
    })
    logit_summary.to_csv(RESULTS_DIR / "logistic_type_completion.csv")
    with open(RESULTS_DIR / "logistic_type_completion.json", "w", encoding="utf-8") as f:
        json.dump({
            "pseudo_r2": logit.prsquared,
            "aic": logit.aic,
            "bic": logit.bic,
            "coef": logit.params.to_dict(),
            "or": np.exp(logit.params).to_dict(),
            "pvalues": logit.pvalues.to_dict(),
        }, f, ensure_ascii=False, indent=2)
    print("\nLogistic 回归（类型 → 任务完成）:")
    print(logit_summary)

    # 保存用于后续图表的聚合数据
    df.to_parquet(INTERIM_DIR / "analysis_ready.parquet")
    print(f"\n分析就绪数据保存到 {INTERIM_DIR / 'analysis_ready.parquet'}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
