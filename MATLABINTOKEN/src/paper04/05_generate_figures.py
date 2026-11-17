"""
05_generate_figures.py - 生成论文四图表
"""

import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

plt.rcParams["font.sans-serif"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False

RESULTS_DIR = Path("paper04_reasoning_typology/results")
TABLES_DIR = RESULTS_DIR / "tables"
FIGURES_DIR = RESULTS_DIR / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)


def set_chinese_font():
    # 优先使用系统已有中文字体，避免 SimHei 缺失时报错
    import matplotlib.font_manager as fm
    candidates = ["SimHei", "Microsoft YaHei", "SimSun", "Arial Unicode MS"]
    available = {f.name for f in fm.fontManager.ttflist}
    for font in candidates:
        if font in available:
            plt.rcParams["font.sans-serif"] = [font]
            break


def plot_cluster_selection():
    df = pd.read_csv(TABLES_DIR / "cluster_selection.csv")
    fig, ax1 = plt.subplots(figsize=(8, 5))
    color = "tab:blue"
    ax1.plot(df["k"], df["silhouette"], marker="o", color=color, label="轮廓系数")
    ax1.set_xlabel("聚类数 k")
    ax1.set_ylabel("轮廓系数", color=color)
    ax1.tick_params(axis="y", labelcolor=color)
    ax1.axvline(x=4, color="red", linestyle="--", alpha=0.5, label="选定 k=4")

    ax2 = ax1.twinx()
    color = "tab:orange"
    ax2.plot(df["k"], df["bic"], marker="s", color=color, label="BIC")
    ax2.set_ylabel("BIC", color=color)
    ax2.tick_params(axis="y", labelcolor=color)

    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "fig1_cluster_selection.png", dpi=300)
    plt.close()


def plot_cluster_profiles():
    df = pd.read_csv(TABLES_DIR / "cluster_profiles_labeled.csv")
    features = [
        "reasoning_words_log1p", "structure_markers_log1p", "decomposition_words_log1p",
        "constraint_mentions_log1p", "verification_mentions_log1p", "feedback_phrases_log1p",
        "self_correction_phrases_log1p", "termination_last20_mentions_log1p",
        "reasoning_action_alignment", "tool_mentions_in_reasoning_log1p",
    ]
    labels = df["reasoning_type_label"].tolist()
    data = df[features].values
    data_z = (data - data.mean(axis=0)) / data.std(axis=0)

    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(data_z, cmap="RdYlGn", aspect="auto", vmin=-1.5, vmax=1.5)
    ax.set_xticks(range(len(features)))
    ax.set_xticklabels([f.replace("_log1p", "").replace("_", "\n") for f in features], rotation=45, ha="right")
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels)
    plt.colorbar(im, ax=ax, label="Z-score")
    ax.set_title("显式推理链类型画像（标准化特征）")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "fig2_cluster_profiles.png", dpi=300)
    plt.close()


def plot_outcomes():
    df = pd.read_parquet(Path("data/interim/paper04/analysis_ready.parquet"))
    order = ["简洁直觉型", "常规综合型", "详细展开型", "结构化分解型"]
    df["reasoning_type_label"] = pd.Categorical(df["reasoning_type_label"], categories=order, ordered=True)

    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    axes = axes.flatten()

    # 完成率
    comp = df.groupby("reasoning_type_label")["task_completed"].mean().reset_index()
    sns.barplot(data=comp, x="reasoning_type_label", y="task_completed", ax=axes[0], order=order)
    axes[0].set_ylim(0, 1)
    axes[0].set_title("任务完成率")
    axes[0].set_ylabel("完成率")

    # 总步数
    sns.barplot(data=df, x="reasoning_type_label", y="total_steps", ax=axes[1], order=order, estimator=np.mean)
    axes[1].set_title("平均总步数")
    axes[1].set_ylabel("步数")

    # 错误率
    sns.barplot(data=df, x="reasoning_type_label", y="incorrect_ratio", ax=axes[2], order=order, estimator=np.mean)
    axes[2].set_title("平均错误步比例")
    axes[2].set_ylabel("错误比例")

    # 冗余率
    sns.barplot(data=df, x="reasoning_type_label", y="redundant_ratio", ax=axes[3], order=order, estimator=np.mean)
    axes[3].set_title("平均冗余步比例")
    axes[3].set_ylabel("冗余比例")

    # 对齐评分
    sns.barplot(data=df, x="reasoning_type_label", y="alignment_score", ax=axes[4], order=order, estimator=np.mean)
    axes[4].set_title("平均任务对齐评分")
    axes[4].set_ylabel("对齐评分")

    # 效率评分
    sns.barplot(data=df, x="reasoning_type_label", y="efficiency_score", ax=axes[5], order=order, estimator=np.mean)
    axes[5].set_title("平均执行效率评分")
    axes[5].set_ylabel("效率评分")

    for ax in axes:
        ax.set_xlabel("")
        ax.tick_params(axis="x", rotation=20)

    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "fig3_outcome_comparison.png", dpi=300)
    plt.close()


def main():
    print("=" * 60)
    print("论文四：生成图表")
    print("=" * 60)
    set_chinese_font()
    plot_cluster_selection()
    plot_cluster_profiles()
    plot_outcomes()
    print(f"图表已保存到 {FIGURES_DIR}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
