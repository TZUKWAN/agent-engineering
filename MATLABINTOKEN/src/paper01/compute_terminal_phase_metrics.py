"""
compute_terminal_phase_metrics.py - 计算终止阶段过程指标
"""
import os
import numpy as np
import pandas as pd
from scipy import stats


def compute_terminal_metrics(df, steps):
    """为每条任务计算终止阶段指标。"""
    # 确保 steps 的布尔列是 bool 类型（None 视为缺失，不计入）
    steps = steps.copy()
    steps["last_step_correct_bool"] = steps["last_step_correct"].map({True: True, False: False, None: pd.NA})
    steps["last_step_redundant_bool"] = steps["last_step_redundant"].map({True: True, False: False, None: pd.NA})

    # 定义：incorrect = last_step_correct 明确为 False；redundant = last_step_redundant 明确为 True
    steps["is_incorrect"] = steps["last_step_correct_bool"] == False
    steps["is_redundant"] = steps["last_step_redundant_bool"] == True

    # 按任务聚合
    grouped = steps.groupby("task_id").agg(
        n_steps=("step_index", "count"),
        max_step_index=("step_index", "max"),
    ).reset_index()

    def last_quartile_props(sub):
        """计算任务最后 25% 步的冗余/错误比例。"""
        total = sub["step_index"].nunique()
        # 向上取整，至少 1 步
        n_last = max(1, int(np.ceil(total * 0.25)))
        last_indices = sub["step_index"].nlargest(n_last)
        last_sub = sub[sub["step_index"].isin(last_indices)]
        # 仅使用非缺失观测计算比例
        n_redundant = last_sub["is_redundant"].sum()
        n_incorrect = last_sub["is_incorrect"].sum()
        n_total_redundant = last_sub["is_redundant"].notna().sum()
        n_total_incorrect = last_sub["is_incorrect"].notna().sum()
        return pd.Series({
            "last25_redundant_prop": n_redundant / n_total_redundant if n_total_redundant > 0 else np.nan,
            "last25_incorrect_prop": n_incorrect / n_total_incorrect if n_total_incorrect > 0 else np.nan,
            "last25_any_redundant": n_redundant > 0,
            "last25_any_incorrect": n_incorrect > 0,
        })

    try:
        quartile_props = steps.groupby("task_id").apply(last_quartile_props, include_groups=False).reset_index()
    except TypeError:
        # pandas < 2.2 的 groupby.apply 没有 include_groups 参数（pandas 2.1.4 实测）
        quartile_props = steps.groupby("task_id").apply(last_quartile_props).reset_index()

    # 最后一步指标
    final_steps = steps.sort_values(["task_id", "step_index"]).groupby("task_id").tail(1).copy()
    final_steps = final_steps[["task_id", "last_step_correct_bool", "last_step_redundant_bool"]].rename(
        columns={
            "last_step_correct_bool": "final_step_correct",
            "last_step_redundant_bool": "final_step_redundant",
        }
    )
    final_steps["final_step_incorrect"] = final_steps["final_step_correct"] == False
    final_steps["final_step_redundant"] = final_steps["final_step_redundant"] == True

    # 合并
    task_metrics = grouped.merge(quartile_props, on="task_id", how="left")
    task_metrics = task_metrics.merge(final_steps, on="task_id", how="left")

    # 与主数据合并
    merged = df[["task_id", "has_completion_criteria", "task_completed", "total_steps", "redundant_ratio", "incorrect_ratio"]].merge(
        task_metrics, on="task_id", how="left"
    )

    # 异常短的未完成任务：步数 <= 已完成任务总步数的 5% 分位数
    completed_total_steps = merged.loc[merged["task_completed"] == True, "total_steps"]
    short_threshold = completed_total_steps.quantile(0.05)
    merged["abnormal_short"] = (merged["task_completed"] == False) & (merged["total_steps"] <= short_threshold)

    return merged, short_threshold


def summarize_by_group(merged):
    """按 has_completion_criteria 分组描述。"""
    rows = []
    for flag in [0, 1]:
        sub = merged[merged["has_completion_criteria"] == flag]
        rows.append({
            "has_completion_criteria": flag,
            "n_tasks": int(len(sub)),
            "last25_redundant_prop_mean": float(sub["last25_redundant_prop"].mean()),
            "last25_redundant_prop_std": float(sub["last25_redundant_prop"].std()),
            "last25_incorrect_prop_mean": float(sub["last25_incorrect_prop"].mean()),
            "last25_incorrect_prop_std": float(sub["last25_incorrect_prop"].std()),
            "last25_any_redundant_rate": float(sub["last25_any_redundant"].mean()),
            "last25_any_incorrect_rate": float(sub["last25_any_incorrect"].mean()),
            "final_step_redundant_rate": float(sub["final_step_redundant"].mean()),
            "final_step_incorrect_rate": float(sub["final_step_incorrect"].mean()),
            "abnormal_short_rate": float(sub["abnormal_short"].mean()),
            "mean_total_steps": float(sub["total_steps"].mean()),
            "mean_redundant_ratio": float(sub["redundant_ratio"].mean()),
            "mean_incorrect_ratio": float(sub["incorrect_ratio"].mean()),
        })

    # 组间比较：t 检验（连续比例）与卡方/比例 Z 检验（二分类）
    comparisons = []
    sub0 = merged[merged["has_completion_criteria"] == 0]
    sub1 = merged[merged["has_completion_criteria"] == 1]

    # t 检验
    for col in ["last25_redundant_prop", "last25_incorrect_prop", "redundant_ratio", "incorrect_ratio"]:
        t, p = stats.ttest_ind(sub1[col].dropna(), sub0[col].dropna(), equal_var=False)
        comparisons.append({"metric": col, "test": "Welch t", "statistic": float(t), "p_value": float(p)})

    # 比例 Z 检验（手动）
    for col in ["last25_any_redundant", "last25_any_incorrect", "final_step_redundant", "final_step_incorrect", "abnormal_short"]:
        n1 = int(sub1[col].sum())
        N1 = int(sub1[col].notna().sum())
        n0 = int(sub0[col].sum())
        N0 = int(sub0[col].notna().sum())
        p_pool = (n1 + n0) / (N1 + N0)
        se = np.sqrt(p_pool * (1 - p_pool) * (1 / N1 + 1 / N0))
        z = (n1 / N1 - n0 / N0) / se if se > 0 else np.nan
        p = 2 * (1 - stats.norm.cdf(abs(z))) if not np.isnan(z) else np.nan
        comparisons.append({"metric": col, "test": "two-proportion Z", "statistic": float(z), "p_value": float(p)})

    return pd.DataFrame(rows), pd.DataFrame(comparisons)


def main():
    print("Computing terminal-phase process indicators...")
    df = pd.read_parquet("data/processed/analysis_data.parquet")
    steps = pd.read_parquet("data/interim/steps.parquet")

    merged, short_threshold = compute_terminal_metrics(df, steps)

    os.makedirs("results/papers/paper01", exist_ok=True)
    os.makedirs("revised/paper01_tables", exist_ok=True)
    os.makedirs("revised/paper01_figures", exist_ok=True)

    # 保存每条任务的指标
    out_csv = "revised/paper01_tables/terminal_phase_metrics_by_task.csv"
    merged.to_csv(out_csv, index=False)
    print(f"Saved terminal-phase metrics per task: {out_csv}")

    # 保存描述性汇总
    summary_df, comp_df = summarize_by_group(merged)
    summary_csv = "revised/paper01_tables/terminal_phase_summary_by_criteria.csv"
    summary_df.to_csv(summary_csv, index=False)
    print(f"Saved summary by has_completion_criteria: {summary_csv}")

    comp_csv = "revised/paper01_tables/terminal_phase_group_comparisons.csv"
    comp_df.to_csv(comp_csv, index=False)
    print(f"Saved group comparisons: {comp_csv}")

    print(f"\nAbnormal-short threshold (5th percentile of completed tasks total_steps): {short_threshold}")
    print("\nSummary:")
    print(summary_df.to_string(index=False))
    print("\nComparisons:")
    print(comp_df.to_string(index=False))

    # 论文图 7：按是否含完成标准比较终止阶段指标（R1 审计前该图无生成脚本）
    plot_terminal_comparison(summary_df)


def plot_terminal_comparison(summary_df) -> None:
    """按组绘制终止阶段关键指标对比图，输出到 revised/paper01_figures/。"""
    import os

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "revised", "paper01_figures"
    )
    os.makedirs(out_dir, exist_ok=True)

    metrics = [
        ("last25_redundant_prop_mean", "最后25%步冗余比例"),
        ("last25_incorrect_prop_mean", "最后25%步错误比例"),
        ("last25_any_redundant_rate", "最后25%步出现冗余"),
        ("last25_any_incorrect_rate", "最后25%步出现错误"),
        ("final_step_incorrect_rate", "最后一步错误率"),
        ("abnormal_short_rate", "异常短轨迹率"),
    ]
    labels = [m[1] for m in metrics]
    no_crit = [summary_df.loc[0, m[0]] for m in metrics]
    with_crit = [summary_df.loc[1, m[0]] for m in metrics]

    x = np.arange(len(labels))
    width = 0.38
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x - width / 2, no_crit, width, label="无完成标准")
    ax.bar(x + width / 2, with_crit, width, label="有完成标准")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_ylabel("比例")
    ax.set_title("终止阶段指标按是否含完成标准的比较")
    ax.legend()
    fig.tight_layout()
    out = os.path.join(out_dir, "fig_terminal_phase_comparison.png")
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved figure: {out}")


if __name__ == "__main__":
    main()
