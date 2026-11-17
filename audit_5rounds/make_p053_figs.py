# -*- coding: utf-8 -*-
"""P053 which_rollouts_deserve_reuse — 定制图（非模板）。"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import os

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

OUT = r"G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P053_which_rollouts_deserve_reuse"
os.makedirs(OUT, exist_ok=True)

C_SUP = "#1a5276"
C_OPP = "#c0392b"
C_NS  = "#b7950b"
C_GY  = "#95a5a6"
C_FN  = "#117a65"

# ============ 图 1 ============
fig, axs = plt.subplots(2, 2, figsize=(11.5, 8.6))
fig.suptitle("图 1  哪条 rollout 配得上成为组织知识：两条挑选规则几乎完全分歧（EXP-0201，1,775 个多次尝试实例）",
             fontsize=12.5, y=0.985)

# (a) tau vs 天花板
a = axs[0, 0]
a.errorbar([0.0414], [0], xerr=[[0.0414 - 0.026], [0.056 - 0.0414]],
           fmt="o", color=C_SUP, capsize=7, lw=2, ms=10)
a.axvline(0.8, color=C_OPP, lw=2, ls="--")
a.axvline(0, color="black", lw=0.9, ls=":")
a.text(0.805, -0.32, "冻结一致天花板 τ=0.80", fontsize=9.5, color=C_OPP, rotation=90, va="center")
a.text(0.0414, 0.28, "τ=0.0414\n[0.026, 0.056]\np_holm=0.0033", ha="center", fontsize=9.5)
a.text(0.42, 0.05, "一致度只有天花板的 5%：\n按成功挑与按成本挑，\n几乎选中不同的轨迹", ha="center",
       fontsize=9.5, color="#555555")
a.set_xlim(-0.08, 1.0)
a.set_ylim(-0.55, 0.55)
a.set_yticks([])
a.set_xlabel(" Kendall τ（成功排序 × 成本调整排序，实例级 bootstrap）", fontsize=9.5)
a.set_title("(a) H1 判 supported：两规则的一致性远低于 0.80 天花板", fontsize=10.5)
a.grid(alpha=0.25, axis="x", ls="--")

# (b) tau 实例分布
a = axs[0, 1]
a.barh([0], [0.4187 - (-0.3333)], left=[-0.3333], height=0.34, color=C_NS, alpha=0.45)
a.errorbar([0.0277], [0], xerr=[[0.0277 - (-0.3333)], [0.4187 - 0.0277]], fmt="D",
           color=C_NS, capsize=6, lw=1.6, ms=8)
a.errorbar([0.0414], [0], xerr=[[0.0154], [0.0146]], fmt="o", color=C_SUP,
           capsize=7, lw=2.2, ms=10)
a.axvline(0.8, color=C_OPP, lw=2, ls="--")
a.text(-0.3333 - 0.02, 0.22, "p10", fontsize=9, ha="center", color="#8a6d00")
a.text(0.4187 + 0.02, 0.22, "p90", fontsize=9, ha="center", color="#8a6d00")
a.text(0.0277, -0.30, "p50=0.028", fontsize=9, ha="center", color="#8a6d00")
a.text(0.0414, -0.42, "均值 0.0414", fontsize=9.5, ha="center", color=C_SUP, weight="bold")
a.text(0.30, -0.16, "实例间的 τ 分布横跨 -0.33 到 0.42：\n少数实例两规则一致，多数接近零，\n还有两规则完全反目的（τ=-1）的实例", fontsize=9)
a.set_xlim(-0.55, 1.0)
a.set_ylim(-0.6, 0.5)
a.set_yticks([])
a.set_xlabel("τ 的分布（p10 / p50 / p90 与均值）", fontsize=9.5)
a.set_title("(b) 分歧不是个别实例：中位实例的 τ 也只有 0.028", fontsize=10.5)
a.grid(alpha=0.25, axis="x", ls="--")

# (c) H2 更便宜的成功
a = axs[1, 0]
a.bar([0], [86.81], width=0.4, color=C_FN, alpha=0.88)
a.errorbar([0], [86.81], yerr=[[86.81 - 82.55], [91.06 - 86.81]], fmt="none",
           ecolor="#333333", capsize=7, lw=1.8)
a.text(0.22, 86.8, "86.8%\n[82.6%, 91.1%]\n(204/235)", fontsize=10, va="center")
a.text(0, 96.5, "存在比最长成功更便宜的成功", ha="center", fontsize=10.5)
a.bar([1], [13.19], width=0.4, color=C_GY, alpha=0.7)
a.text(1, 14.8, "13.2% (31)", ha="center", fontsize=10)
a.text(1, 5.5, "最长成功\n已是唯一/最便宜", ha="center", fontsize=9)
a.set_xticks([0, 1])
a.set_xticklabels(["有更便宜的成功", "没有"], fontsize=10)
a.set_ylabel("有成功实例的份额 %", fontsize=9.5)
a.set_ylim(0, 105)
a.set_title("(c) H2 描述性：86.8% 的成功实例里，最长的那次不是最省的", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (d) 三种挑选规则的成本
a = axs[1, 1]
rules = ["按成功挑\n(成功优先)", "按成本挑\n(成功→短步→低重复)", "最笨规则\n(挑最长的)"]
steps = [14.43, 13.49, 14.98]
cols = [C_SUP, C_FN, C_OPP]
bars = a.bar(rules, steps, width=0.5, color=cols, alpha=0.88)
for b_, v in zip(bars, steps):
    a.text(b_.get_x() + b_.get_width() / 2, v + 0.06, f"{v:.2f} 步", ha="center", fontsize=10)
a.text(1, 15.9, "成本规则挑中的轨迹平均少 0.94 步（-6.5%），\n重复份额仅 1.16%；\n被挑中的轨迹平均时长反而更长（59.9 vs 55.1 s）——\n省步数不等于省时钟，复用定价要分开算", fontsize=9)
a.set_ylabel("被选中轨迹的平均步数", fontsize=9.5)
a.set_ylim(12.5, 16.8)
a.set_title("(d) 三种挑选规则的实际成本对比（1,775 实例）", fontsize=10.5)
a.tick_params(axis="x", labelsize=9)
a.grid(alpha=0.25, axis="y", ls="--")

fig.tight_layout(rect=[0, 0, 1, 0.955])
fig.savefig(os.path.join(OUT, "fig1_selection.png"), dpi=200)
plt.close(fig)

# ============ 图 2 ============
fig, axs = plt.subplots(2, 2, figsize=(11.5, 8.6))
fig.suptitle("图 2  分歧的结构：尝试越多分歧越深、限制越多分歧仍在（EXP-0201）",
             fontsize=12.5, y=0.985)

# (a) 分层 tau
a = axs[0, 0]
bands = ["2 次\n(n=11)", "3-5 次\n(n=182)", "6-10 次\n(n=742)", "11+ 次\n(n=840)"]
mt = [0.2727, 0.0806, 0.0329, 0.0375]
a.bar(bands, mt, width=0.55, color=[C_GY, C_NS, C_SUP, C_SUP], alpha=0.88)
for i, v in enumerate(mt):
    a.text(i, v + 0.006, f"{v:.4f}", ha="center", fontsize=9.5)
a.axhline(0.8, color=C_OPP, lw=1.8, ls="--")
a.text(0.02, 0.81, "天花板 0.80", fontsize=9, color=C_OPP)
a.text(1.8, 0.12, "尝试次数越多，两规则越分歧：\n2 次尝试的实例 τ=0.27，\n11+ 次的实例 τ=0.037", fontsize=9)
a.set_ylabel("平均 Kendall τ", fontsize=9.5)
a.set_ylim(0, 0.9)
a.set_title("(a) 按尝试次数分层：丰富经验加剧分歧", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (b) H3 限制下的 tau
a = axs[1, 0]
conds = ["全部实例\n(1,775)", "去掉每实例最长\n(1,764)", "仅有成功实例\n(235)"]
taus = [0.0414, 0.051, 0.3081]
a.bar(conds, taus, width=0.5, color=[C_SUP, C_SUP, C_NS], alpha=0.88)
for i, v in enumerate(taus):
    a.text(i, v + 0.008, f"{v:.4f}", ha="center", fontsize=10)
a.axhline(0.8, color=C_OPP, lw=1.8, ls="--")
a.text(0.02, 0.815, "天花板 0.80", fontsize=9, color=C_OPP)
a.text(1.0, 0.55, "三种限制下一致度都低于天花板：\n分歧不是长尾轨迹的产物；\n限制到成功实例后 τ 升至 0.31——\n成功内部仍大量分歧", fontsize=9)
a.set_ylabel("Kendall τ", fontsize=9.5)
a.set_ylim(0, 0.92)
a.set_title("(b) H3 描述性：剔除长尾与聚焦成功都不恢复一致", fontsize=10.5)
a.tick_params(axis="x", labelsize=9)
a.grid(alpha=0.25, axis="y", ls="--")

# (c) 实例的尝试次数分布
a = axs[0, 1]
k = [2, 3, 4, 5, 6, 7, 8, 9, 10]
n = [11, 29, 63, 90, 132, 143, 178, 168, 121]
a.bar(k, n, width=0.6, color=C_SUP, alpha=0.85)
for x_, c in zip(k, n):
    a.text(x_, c + 3, str(c), ha="center", fontsize=8.5)
a.text(6.2, 150, "11+ 次的实例合计 840 个\n(47%)——发布集几乎全部\n是反复尝试的任务", fontsize=9.5)
a.set_xlabel("每实例的尝试（rollout）次数", fontsize=9.5)
a.set_ylabel("实例数", fontsize=9.5)
a.set_ylim(0, 210)
a.set_title("(c) 重复尝试是常态：G8 门测得 1,775/1,784", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (d) 判定卡
a = axs[1, 1]
a.axis("off")
rows = [
    ("H1", "supported", "τ=0.0414 [0.026, 0.056]，远低于 0.80 天花板；两规则分歧"),
    ("H2", "measured", "86.8% [82.6, 91.1] 的成功实例存在更便宜的成功 (204/235)"),
    ("H3", "measured", "三种限制下 τ 都低于天花板——分歧是结构性、非长尾"),
    ("前提", "G8 门通过", "≥300 重复实例要求，实测 1,775/1,784 (99.6%)"),
    ("成本读数", "13.49 vs 14.98 步", "成本规则比挑最长省 10%；但时钟时长反而多 8.9%"),
    ("实践规则", "成本调整排序", "成功→更少步→更少重复，应作为知识入库的默认排序"),
]
y0 = 0.95
for kk, v1, v2 in rows:
    a.text(0.02, y0, kk, fontsize=10, weight="bold", color=C_FN, va="top")
    a.text(0.14, y0, v1, fontsize=9.5, weight="bold", va="top", color=C_OPP)
    a.text(0.33, y0, v2, fontsize=8.6, va="top")
    y0 -= 0.15
a.set_title("(d) 判定卡", fontsize=10.5, loc="right")

fig.tight_layout(rect=[0, 0, 1, 0.955])
fig.savefig(os.path.join(OUT, "fig2_structure.png"), dpi=200)
plt.close(fig)
print("P053 figs done")
