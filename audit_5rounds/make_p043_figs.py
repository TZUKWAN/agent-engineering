# -*- coding: utf-8 -*-
"""P043 contamination — 补做定制图。"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import os

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

OUT = r"G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P043_irrelevant_candidate_contamination"
C_SUP = "#1a5276"; C_OPP = "#c0392b"; C_NS = "#b7950b"; C_GY = "#95a5a6"; C_FN = "#117a65"

fig, axs = plt.subplots(2, 2, figsize=(11.5, 8.8))
fig.suptitle("图 1  无关候选污染：9.33% 的查询被污染、污染摧毁选择余量（EXP-0187，31,642 查询）",
             fontsize=12.5, y=0.985)

# (a) 污染率 vs 地板
a = axs[0, 0]
a.bar([0], [9.33], width=0.4, color=C_NS, alpha=0.9)
a.errorbar([0], [9.33], yerr=[[0.35], [0.35]], fmt="none", ecolor="#333333", capsize=6, lw=1.5)
a.axhline(10, color=C_OPP, lw=1.8, ls="--")
a.text(0.24, 10.2, "冻结地板 10%", fontsize=9.5, color=C_OPP)
a.text(0, 11.3, "9.33%（2,953 / 31,642）", ha="center", fontsize=11)
a.text(0, 4.0, "差 0.67 个百分点未达地板：\nH1 判 measured（受限）——\n数字照印、主张降级", ha="center", fontsize=9.5)
a.set_xticks([0]); a.set_xticklabels(["被污染查询份额"], fontsize=10)
a.set_ylabel("份额 %", fontsize=9.5); a.set_ylim(0, 13.5)
a.set_title("(a) 污染率：贴着地板线下方", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (b) H1 森林：margin 效应
a = axs[0, 1]
a.errorbar([-0.6066], [0], xerr=[[-0.6066 - (-0.6305)], [(-0.5828) - (-0.6066)]], fmt="o",
           color=C_OPP, capsize=7, lw=2, ms=10)
a.errorbar([-0.0922], [1], xerr=[[-0.0922 - (-0.1008)], [(-0.0835) - (-0.0922)]], fmt="s",
           color=C_NS, capsize=7, lw=2, ms=10)
a.axvline(0, color="black", lw=1.0, ls="--")
a.text(-0.6066, 0.3, "污染指示项\nβ=-0.6066 [-0.6305, -0.5828]", ha="center", fontsize=9)
a.text(-0.0922, 1.3, "无关份额（连续）\nβ=-0.0922 [-0.1008, -0.0835]", ha="center", fontsize=9)
a.text(-0.35, 2.0, "两个口径同向：污染使选择余量\n(margin) 急剧收窄；指示项的效应\n是连续份额的 6.6 倍", ha="center", fontsize=9)
a.set_yticks([0, 1]); a.set_yticklabels(["指示项口径", "连续份额口径"], fontsize=9.5)
a.invert_yaxis(); a.set_xlim(-0.72, 0.08)
a.set_xlabel("对 margin_z 的 β（query 聚类）", fontsize=9.5)
a.set_title("(b) H1：污染压垮选择余量", fontsize=10.5)
a.grid(alpha=0.25, axis="x", ls="--")

# (c) margin 对比
a = axs[1, 0]
a.bar([0, 1], [2.189, 0.938], width=0.42, color=[C_GY, C_OPP], alpha=0.88)
a.text(0, 2.25, "2.19", ha="center", fontsize=11)
a.text(1, 1.0, "0.94", ha="center", fontsize=11)
a.text(0.5, 2.75, "有污染查询的余量只有干净查询的 43%\n——金标准之上只剩一个候选可依赖", ha="center", fontsize=9.5)
a.set_xticks([0, 1]); a.set_xticklabels(["无污染 (n=28,689)", "有污染 (n=2,953)"], fontsize=10)
a.set_ylabel("金标准之上的平均选择余量", fontsize=9.5); a.set_ylim(0, 3.2)
a.set_title("(c) 余量对比：污染把余量砍掉 57%", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (d) H3 目录规模
a = axs[1, 1]
a.errorbar([0.4375], [0], xerr=[[0.4375 - 0.3877], [0.4872 - 0.4375]], fmt="o",
           color=C_SUP, capsize=7, lw=2, ms=10)
a.axvline(0, color="black", lw=1.0, ls="--")
a.text(0.4375, 0.3, "β=+0.4375 [0.3877, 0.4872]\np_holm<0.001 → supported\n污染候选数均值 2.663", ha="center", fontsize=9.5)
a.text(0.4375, -0.32, "目录每扩一档，挤进来的无关候选更多——\n污染是规模化的副产品", ha="center", fontsize=9.5)
a.set_xlim(-0.1, 0.62); a.set_ylim(-0.55, 0.55); a.set_yticks([])
a.set_xlabel("目录规模对污染候选数的 β", fontsize=9.5)
a.set_title("(d) H3 判 supported：污染随目录增长", fontsize=10.5)
a.grid(alpha=0.25, axis="x", ls="--")

fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(os.path.join(OUT, "fig1_contamination.png"), dpi=200)
plt.close(fig)

# ============ 图 2 ============
fig, axs = plt.subplots(2, 2, figsize=(11.5, 8.8))
fig.suptitle("图 2  污染的分布解剖：栈梯度、模型一致性假象与金上候选计数（EXP-0187）", fontsize=12.5, y=0.985)

# (a) 模型栈分层
a = axs[0, 0]
cfgs = ["Kimi-K2", "OSS", "Qwen3"]
sh = [9.55, 8.69, 9.75]
bs = [-0.487, -0.6496, -0.7217]
x = np.arange(3)
b1 = a.bar(x - 0.18, sh, width=0.36, color=C_NS, alpha=0.85, label="污染率 %")
for xi, v in zip(x, sh): a.text(xi - 0.18, v + 0.15, f"{v:.2f}%", ha="center", fontsize=9)
a2 = a.twinx()
b2 = a2.bar(x + 0.18, [-v for v in bs], width=0.36, color=C_OPP, alpha=0.8, label="|β|（污染→余量）")
for xi, v in zip(x, bs): a2.text(xi + 0.18, -v + 0.02, f"{v:.2f}", ha="center", fontsize=9, color=C_OPP)
a.set_xticks(x); a.set_xticklabels(cfgs, fontsize=10)
a.set_ylabel("污染率 %", fontsize=9.5); a2.set_ylabel("污染效应 |β|", fontsize=9.5, color=C_OPP)
a.set_ylim(0, 12); a2.set_ylim(0, 0.9)
a.text(0.9, 10.6, "污染率三栈几乎相同（8.7-9.8%），\n但伤害差异大：Qwen3 的余量损失最重", fontsize=9, ha="center")
a.set_title("(a) 模型栈：发生率一致、伤害不一", fontsize=10.5)
h1, l1 = a.get_legend_handles_labels(); h2, l2 = a2.get_legend_handles_labels()
a.legend(h1 + h2, l1 + l2, fontsize=8.5, loc="upper right")
a.grid(alpha=0.25, axis="y", ls="--")

# (b) 候选池四分位
a = axs[0, 1]
qs = ["q1 最小", "q2", "q3", "q4 最大"]
bv = [-0.385, -0.4112, -0.6231, -0.75]
x = np.arange(4)
a.bar(x, [-v for v in bv], width=0.5, color=C_OPP, alpha=0.85)
for xi, v in zip(x, bv): a.text(xi, -v + 0.015, f"{v:.3f}", ha="center", fontsize=9.5)
a.set_xticks(x); a.set_xticklabels(qs, fontsize=10)
a.set_ylabel("污染对余量的 |β|", fontsize=9.5)
a.text(1.0, 0.68, "目录越大，一次污染的伤害越重\n——大池子给了污染更多藏身处", fontsize=9.5, ha="center")
a.set_title("(b) 候选池四分位：污染伤害随池深加重", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (c) 金上无关候选计数分布
a = axs[1, 0]
ks = list(range(8))
vs = [28689, 946, 1133, 329, 213, 106, 59, 32]
a.bar(ks, vs, width=0.6, color=[C_GY] + [C_OPP] * 7, alpha=0.88)
for k, v in zip(ks, vs):
    a.text(k, v + 350, f"{v:,}", ha="center", fontsize=8.5)
a.text(3.5, 12000, "90.7% 的查询零污染；\n被污染的 2,953 个查询平均\n带 2.66 个金标准之上的无关候选\n——不是一对一，是围剿", fontsize=9.5, ha="center")
a.set_xlabel("金标准之上的无关候选数", fontsize=9.5)
a.set_ylabel("查询数", fontsize=9.5)
a.set_ylim(0, 32000)
a.set_title("(c) 围剿形态：污染以多打一", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (d) 判定卡
a = axs[1, 1]; a.axis("off")
rows = [
    ("H1", "measured（受限）", "污染率 9.33% < 地板 10%；余量效应 β=-0.6066"),
    ("H3", "supported", "目录规模 → 污染候选数 β=+0.4375"),
    ("栈一致性", "发生率同、伤害异", "Qwen3 伤害最重（-0.72）、OSS 居中、Kimi 最轻"),
    ("两个口径", "指示项 6.6 倍于份额", "污染是质变事件，不是渐变剂量"),
]
y0 = 0.9
for k, v1, v2 in rows:
    a.text(0.02, y0, k, fontsize=10.5, weight="bold", color=C_FN, va="top")
    a.text(0.17, y0, v1, fontsize=9.5, weight="bold", va="top", color=C_OPP)
    a.text(0.40, y0, v2, fontsize=9, va="top")
    y0 -= 0.21
a.set_title("(d) 判定卡", fontsize=10.5, loc="right")

fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(os.path.join(OUT, "fig2_contamination.png"), dpi=200)
plt.close(fig)
print("P043 figs done")
