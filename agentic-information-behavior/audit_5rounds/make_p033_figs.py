# -*- coding: utf-8 -*-
"""P033 定制图：基于 T155 (搜索深度与需求复杂度, EXP-0174, wave-6 多次 rollout) 产物数据。

本文的个性（全系列最硬的结构发现）：步数天花板 15、rollout 中位数就是 15——
所有 rollout 顶格跑满，深度不是任务属性而是预算属性（H1 opposite 负号、
需求四分位均值 14.83→14.68 挤在天花板下）；提交的 rollout 远早于天花板
（H2 supported, -6.54）；更长需求让提交率崩塌（5.79%→0.52%）。
"""
import json, glob, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 300

fs = sorted(glob.glob("results_raw/EXP0174_wave6_design_*.json"))
art = json.load(open(fs[-1], encoding="utf-8"))
OUT = pathlib.Path("papers/P033_search_depth_vs_need_complexity/figures")
OUT.mkdir(parents=True, exist_ok=True)

C_SUP = "#27ae60"
C_OPP = "#c0392b"
C_ACC = "#2980b9"
C_NULL = "#95a5a6"

models = {m["hypothesis"]: m for m in art["models"]}
h1, h2, h3 = models["H1"], models["H2"], models["H3"]
dq = art["descriptive_rates"]["depth_by_need_quartile"]
budget = art["descriptive_rates"]["step_budget_by_instance"]

# ===== 图1 天花板：四分位均值挤在 15 步线下 =====
fig, ax = plt.subplots(figsize=(9.6, 5.0))
quarts = ["n1_shortest", "n2", "n3", "n4_longest"]
qlab = ["Q1 最短需求", "Q2", "Q3", "Q4 最长需求"]
means = [dq[q]["mean_steps"] for q in quarts]
ceiling = budget["max_observed"]
ax.bar(range(4), means, color=C_ACC, alpha=0.88, width=0.55)
for i, (m, q) in enumerate(zip(means, quarts)):
    ax.text(i, m + 0.12, f"{m:.2f} 步\n(n={dq[q]['rows']:,})", ha="center", fontsize=9.5)
ax.axhline(ceiling, color=C_OPP, lw=2, ls="--")
ax.text(3.42, ceiling + 0.12, f"步数天花板 = {ceiling}\n（rollout 中位数同为 {budget['median']:.0f}）",
        fontsize=10, color=C_OPP, ha="right")
ax.set_xticks(range(4)); ax.set_xticklabels(qlab, fontsize=10)
ax.set_ylabel("rollout 平均 assistant 步数", fontsize=10)
ax.set_ylim(0, 17.5)
ax.set_title("图1  深度的真相：四种需求长度下 rollout 全部顶格跑到 14.7–14.8 步，\n"
             "距天花板不足 2%——深度是预算属性，不是任务属性",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="y", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig1_ceiling.png", bbox_inches="tight")
plt.close()

# ===== 图2 H1 opposite：需求越长步数越少（微弱但确定） =====
fig, ax = plt.subplots(figsize=(9.2, 4.8))
ax.errorbar([h1["beta"]], [0], xerr=[[h1["beta"] - h1["ci_lo"]], [h1["ci_hi"] - h1["beta"]]],
            fmt="D", color=C_OPP, ms=11, capsize=6, lw=2)
ax.axvline(0, color="black", lw=0.9, ls="--")
ax.text(h1["ci_hi"] + 0.0004, 0,
        f"需求长度（实例内标准化）对步数的系数\nβ = {h1['beta']:+.4f}（预测正，实测负）\n"
        f"95% CI [{h1['ci_lo']:.4f}, {h1['ci_hi']:.4f}]，p_holm = {h1['p_holm']:.4f}\n"
        f"（n = {h1['n']:,} 步 / {h1['instances_with_2plus_rollouts']:,} 个多 rollout 实例）",
        va="center", fontsize=9.5, color=C_OPP)
ax.set_yticks([])
ax.set_xlabel("need_words_z 系数", fontsize=10)
ax.set_xlim(-0.0095, 0.001)
ax.set_title("图2  H1 判 opposite：在任务固定、只有措辞长度变化时，\n更长的需求描述对应更少的步数——深度不回答需求",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="x", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig2_h1_opposite.png", bbox_inches="tight")
plt.close()

# ===== 图3 H2 supported：提交的 rollout 远早收工 =====
fig, ax = plt.subplots(figsize=(9.2, 4.8))
ax.barh([0], [abs(h2["beta"])], height=0.42, color=C_SUP, alpha=0.85)
ax.errorbar(abs(h2["beta"]), 0,
            xerr=[[abs(h2["beta"]) - abs(h2["ci_hi"])], [abs(h2["ci_lo"]) - abs(h2["beta"])]],
            color="#145a32", capsize=6, lw=1.6, fmt="none")
ax.axvline(0, color="black", lw=0.9, ls="--")
ax.text(abs(h2["beta"]) + 0.3, 0,
        f"提交 rollout 相对未提交（跑满）rollout 的步数差\n"
        f"β = {h2['beta']:+.4f}（log 步数口径；提交者远早于天花板收工）\n"
        f"95% CI [{h2['ci_lo']:.2f}, {h2['ci_hi']:.2f}]，p_holm < 0.001\n"
        f"（提交轨迹 {h2['submitted_trajectories']:,} / 全部 {h2['n']:,}）",
        va="center", fontsize=9.5, color="#145a32")
ax.set_yticks([])
ax.set_xlabel("|log 步数差|（方向：提交者更少步数）", fontsize=10)
ax.set_xlim(0, 11.5)
ax.set_title("图3  H2 判 supported：唯一显著改变深度的变量是\"是否提交\"——\n提交者提前收工，跑满者顶格用完预算",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="x", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig3_h2_submit.png", bbox_inches="tight")
plt.close()

# ===== 图4 提交率崩塌：需求越长越难交卷 =====
fig, ax = plt.subplots(figsize=(9.2, 4.9))
shares = [dq[q]["submitted_share"] * 100 for q in quarts]
ax.bar(range(4), shares, color=[C_SUP, "#f1c40f", "#e67e22", C_OPP], alpha=0.9, width=0.55)
for i, s in enumerate(shares):
    ax.text(i, s + 0.1, f"{s:.2f}%", ha="center", fontsize=10.5, fontweight="bold")
ax.annotate("", xy=(3, 1.1), xytext=(0, 6.2),
            arrowprops=dict(arrowstyle="->", color="black", lw=1.4))
ax.text(1.5, 4.4, "需求长度每升一档，提交率大致减半\n（5.79% → 0.52%，约 11 倍落差）",
        ha="center", fontsize=10)
ax.set_xticks(range(4)); ax.set_xticklabels(qlab, fontsize=10)
ax.set_ylabel("rollout 以提交终止的比率（%）", fontsize=10)
ax.set_ylim(0, 7.2)
ax.set_title("图4  深度的代价侧：顶格跑满意味着极少提交，\n而需求越长的任务提交率崩塌得越彻底",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="y", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig4_submission_collapse.png", bbox_inches="tight")
plt.close()

print("P033 figures done:", [p.name for p in sorted(OUT.glob("custom_*.png"))])
