"""
05_generate_figures.py - 生成论文五图表
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

plt.rcParams["font.sans-serif"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False

RESULTS_DIR = Path("paper05_prompt_risk_failure/results")
TABLES_DIR = RESULTS_DIR / "tables"
FIGURES_DIR = RESULTS_DIR / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)


def set_chinese_font():
    import matplotlib.font_manager as fm
    candidates = ["SimHei", "Microsoft YaHei", "SimSun", "Arial Unicode MS"]
    available = {f.name for f in fm.fontManager.ttflist}
    for font in candidates:
        if font in available:
            plt.rcParams["font.sans-serif"] = [font]
            break


def plot_correlation_heatmap():
    corr = pd.read_csv(TABLES_DIR / "correlation_matrix.csv", index_col=0)
    fig, ax = plt.subplots(figsize=(7, 6))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r", center=0, ax=ax,
                vmin=-1, vmax=1)
    ax.set_title("提示风险、推理错误、执行错误与任务完成的相关矩阵")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "fig1_correlation_heatmap.png", dpi=300)
    plt.close()


def plot_path_diagram():
    """简化的路径系数图"""
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")

    # 节点位置
    nodes = {
        "提示风险": (1, 2.5),
        "推理错误": (4, 4),
        "执行错误": (7, 2.5),
        "任务失败": (9.5, 2.5),
    }

    for label, (x, y) in nodes.items():
        ax.scatter(x, y, s=3000, c="lightblue", zorder=2)
        ax.text(x, y, label, ha="center", va="center", fontsize=12, zorder=3)

    # 箭头与系数
    ax.annotate("", xy=(3.2, 3.7), xytext=(1.8, 2.8),
                arrowprops=dict(arrowstyle="->", lw=2, color="black"))
    ax.text(2.3, 3.5, "+0.025***", fontsize=10)

    ax.annotate("", xy=(6.2, 2.8), xytext=(4.8, 3.7),
                arrowprops=dict(arrowstyle="->", lw=2, color="black"))
    ax.text(5.3, 3.4, "+0.966***", fontsize=10)

    ax.annotate("", xy=(9.0, 2.5), xytext=(7.8, 2.5),
                arrowprops=dict(arrowstyle="->", lw=2, color="black"))
    ax.text(8.2, 2.8, "OR=0.025***", fontsize=10)

    # 直接效应（风险 -> 失败）
    ax.annotate("", xy=(9.0, 2.2), xytext=(1.8, 2.2),
                arrowprops=dict(arrowstyle="->", lw=1.5, color="gray", linestyle="--"))
    ax.text(5, 1.8, "直接效应 OR=0.987（n.s.）", fontsize=10, color="gray")

    ax.set_title("观察性统计路径：提示风险 → 推理错误 → 执行错误 → 任务失败")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "fig2_path_diagram.png", dpi=300)
    plt.close()


def plot_risk_feature_effects():
    df = pd.read_csv(TABLES_DIR / "single_risk_feature_to_reasoning.csv")
    df = df.sort_values("coef")
    fig, ax = plt.subplots(figsize=(9, 6))
    colors = ["red" if p < 0.05 else "gray" for p in df["p"]]
    ax.barh(df["feature"], df["coef"], color=colors)
    ax.axvline(x=0, color="black", linewidth=0.8)
    ax.set_xlabel("对推理错误指数的回归系数")
    ax.set_title("单独提示风险特征与推理错误指数的关联")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "fig3_risk_feature_effects.png", dpi=300)
    plt.close()


def plot_completion_by_error_index():
    df = pd.read_parquet(Path("data/interim/paper05/analysis_ready.parquet"))
    df["execution_error_group"] = pd.cut(df["execution_error_index"], bins=[-1, 0, 1, 2, 5],
                                         labels=["0", "1", "2", "3+"])
    comp = df.groupby("execution_error_group", observed=True)["completed_num"].mean().reset_index()

    fig, ax = plt.subplots(figsize=(7, 5))
    sns.barplot(data=comp, x="execution_error_group", y="completed_num", ax=ax)
    ax.set_xlabel("执行错误指数")
    ax.set_ylabel("任务完成率")
    ax.set_title("执行错误指数与任务完成率")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "fig4_completion_by_execution_error.png", dpi=300)
    plt.close()


def main():
    print("=" * 60)
    print("论文五：生成图表")
    print("=" * 60)
    set_chinese_font()
    plot_correlation_heatmap()
    plot_path_diagram()
    plot_risk_feature_effects()
    plot_completion_by_error_index()
    print(f"图表已保存到 {FIGURES_DIR}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
