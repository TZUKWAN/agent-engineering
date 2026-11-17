# -*- coding: utf-8 -*-
"""P068 corrective_vs_ritual — 定制图（非模板）。"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import os

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

OUT = r"G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P068_corrective_and_ritual_reflection"
os.makedirs(OUT, exist_ok=True)

C_SUP = "#1a5276"
C_OPP = "#c0392b"
C_NS  = "#b7950b"
C_GY  = "#95a5a6"
C_FN  = "#117a65"

# ============ 图 1 ============
fig, axs = plt.subplots(2, 2, figsize=(11.5, 8.8))
fig.suptitle("图 1  纠错式还是仪式式反思：标记之后的想法真的不同（EXP-0217，3,975 段多模态对话）",
             fontsize=12.5, y=0.985)

# (a) H2 重合崩塌
a = axs[0, 0]
a.bar([0, 1], [14.30, 3.13], width=0.42, color=[C_GY, C_SUP], alpha=0.88)
a.errorbar([0], [14.30], yerr=[[0.6], [0.6]], fmt="none", ecolor="#333333", capsize=5, lw=1.4)
a.errorbar([1], [3.13], yerr=[[0.25], [0.25]], fmt="none", ecolor="#333333", capsize=5, lw=1.4)
a.text(0, 15.4, "14.30%", ha="center", fontsize=11)
a.text(1, 4.2, "3.13%", ha="center", fontsize=11)
a.annotate("β=-0.1117 [-0.1188, -0.1034]\np_holm=0.005 → supported", xy=(0.5, 9), xytext=(0.62, 12),
           fontsize=9.5, arrowprops=dict(arrowstyle="->", lw=1.1, color=C_OPP))
a.set_xticks([0, 1])
a.set_xticklabels(["无标记的相邻想法\n（n=7,509 转移）", "标记后的下一想法\n（n=208 转移）"], fontsize=9.5)
a.set_ylabel("与前一想法的内容词 Jaccard 重合", fontsize=9.5)
a.set_ylim(0, 17.5)
a.set_title("(a) H2 判 supported：说'重新考虑'之后，想法换血 78%", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (b) H3 仪式率
a = axs[0, 1]
a.bar([0], [0.0], width=0.35, color=C_FN, alpha=0.9)
a.bar([1], [20.0], width=0.35, color=C_GY, alpha=0.35)
a.axhline(20, color=C_OPP, lw=1.8, ls="--")
a.text(1.24, 20.5, "冻结地板 20%", fontsize=9.5, color=C_OPP)
a.text(0, 1.2, "实测 0.00%\n（208 次标记转移中\n无一为高重合复述）", ha="center", fontsize=10)
a.text(1, 22.6, "地板", ha="center", fontsize=9.5, color=C_GY)
a.set_xticks([0, 1])
a.set_xticklabels(["仪式式反思份额\n（标记后重合未降）", "地板参考"], fontsize=9.5)
a.set_ylabel("份额 %", fontsize=9.5)
a.set_ylim(0, 26)
a.set_title("(b) H3 判 below_floor_measured_0.0000：仪式式反思为零", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (c) 标记随想法位置的分布
a = axs[1, 0]
pos = [1, 2, 3, 4, 5, 6]
prev = [0.18, 1.06, 5.71, 2.51, 24.58, 6.02]
a.bar(pos, prev, width=0.55, color=[C_GY, C_GY, C_NS, C_NS, C_OPP, C_NS], alpha=0.9)
for p, v in zip(pos, prev):
    a.text(p, v + 0.4, f"{v:.2f}%", ha="center", fontsize=9)
a.annotate("第 5 个想法是反思高峰\n（占该位置的 24.6%）", xy=(5, 24.58), xytext=(3.1, 20),
           fontsize=9.5, arrowprops=dict(arrowstyle="->", lw=1.2, color=C_OPP))
a.set_xticks(pos)
a.set_xticklabels([f"第{i}个" for i in pos], fontsize=9.5)
a.set_ylabel("该位置含反思标记的比例 %", fontsize=9.5)
a.set_ylim(0, 29)
a.set_title("(c) 反思的位置学：集中在第 5 个想法", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (d) H1 稀有性
a = axs[1, 1]
a.bar([0], [208], width=0.35, color=C_SUP, alpha=0.88)
a.axhline(200, color=C_OPP, lw=1.8, ls="--")
a.text(0.2, 202, "冻结可行性地板 200", fontsize=9.5, color=C_OPP)
a.text(0, 214, "208 次标记转移", ha="center", fontsize=10.5)
a.text(0, 90, "占全部 7,717 次相邻想法转移的 2.7%\n——反思标记稀有但可测\n（普查口径 267 次，偏差 W12-D05 双口径并印）",
       ha="center", fontsize=9)
a.set_xticks([0])
a.set_xticklabels(["标记转移数"], fontsize=10)
a.set_ylabel("次数", fontsize=9.5)
a.set_ylim(0, 240)
a.set_title("(d) H1 判 supported：高于 200 的可行性地板", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(os.path.join(OUT, "fig1_reflection.png"), dpi=200)
plt.close(fig)

# ============ 图 2 ============
fig, axs = plt.subplots(2, 2, figsize=(11.5, 8.8))
fig.suptitle("图 2  反思的位置分层、下游算子与判定（EXP-0217）", fontsize=12.5, y=0.985)

# (a) 位置带分层
a = axs[0, 0]
bands = ["第1个", "第2-3个", "第4-6个", "第7个+"]
ms = [0.18, 2.44, 12.48, 5.15]
js = [15.42, 15.22, 8.32, 10.83]
x = np.arange(4)
b1 = a.bar(x - 0.18, ms, width=0.36, color=C_SUP, alpha=0.88, label="标记份额 %")
for xi, v in zip(x, ms):
    a.text(xi - 0.18, v + 0.3, f"{v:.2f}", ha="center", fontsize=9)
a2 = a.twinx()
b2 = a2.bar(x + 0.18, js, width=0.36, color=C_NS, alpha=0.75, label="平均重合 %")
for xi, v in zip(x, js):
    a2.text(xi + 0.18, v + 0.3, f"{v:.1f}", ha="center", fontsize=9, color="#8a6d00")
a.set_xticks(x)
a.set_xticklabels(bands, fontsize=10)
a.set_ylabel("标记份额 %", fontsize=9.5)
a2.set_ylabel("相邻想法平均重合 %", fontsize=9.5, color="#8a6d00")
a.set_ylim(0, 15.5)
a2.set_ylim(0, 19)
a.text(1.6, 13.6, "第 4-6 个想法：标记最多（12.5%）\n且重合最低（8.3%）——\n反思带正是内容变动带", fontsize=9)
a.set_title("(a) 位置带：反思高峰与内容变动同域", fontsize=10.5)
h1, l1 = a.get_legend_handles_labels()
h2, l2 = a2.get_legend_handles_labels()
a.legend(h1 + h2, l1 + l2, fontsize=8.5, loc="upper right")
a.grid(alpha=0.25, axis="y", ls="--")

# (b) 下游算子
a = axs[0, 1]
ops = ["image_caption\n图注", "object_detection\n目标检测", "ocr\n文字识别"]
ms2 = [1.75, 1.64, 0.67]
a.bar(ops, ms2, width=0.45, color=[C_SUP, C_NS, C_GY], alpha=0.88)
for i, v in enumerate(ms2):
    a.text(i, v + 0.04, f"{v:.2f}%", ha="center", fontsize=10)
a.set_xticklabels(ops, fontsize=9.5)
a.set_ylabel("转移后跟随该算子的标记份额 %", fontsize=9.5)
a.set_ylim(0, 2.3)
a.text(1.0, 1.95, "反思之后的三种视觉操作里，\n图注与检测平分秋色，OCR 少见——\n反思多伴随'再看一遍图'而非'再读一遍字'", fontsize=9, ha="center")
a.set_title("(b) 反思的下游：重看图多于重读字", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (c) Jaccard 分布
a = axs[1, 0]
a.barh([0], [25.0 - 3.33], left=[3.33], height=0.3, color=C_NS, alpha=0.4)
a.plot([3.33, 13.33, 25.0], [0, 0, 0], "D", color=C_NS, ms=8)
a.text(3.33, 0.12, "p10=3.3%", fontsize=9, ha="center")
a.text(13.33, 0.12, "p50=13.3%", fontsize=9, ha="center")
a.text(25.0, 0.12, "p90=25.0%", fontsize=9, ha="center")
a.plot([3.13], [0], "o", color=C_SUP, ms=12, zorder=5)
a.text(3.13, -0.22, "标记后均值 3.1%", fontsize=9.5, ha="center", color=C_SUP, weight="bold")
a.axvline(14.3, color=C_OPP, lw=1.5, ls="--")
a.text(14.4, -0.22, "无标记均值 14.3%", fontsize=9.5, color=C_OPP)
a.set_xlim(0, 30)
a.set_ylim(-0.5, 0.5)
a.set_yticks([])
a.set_xlabel("相邻想法的内容词 Jaccard（%）", fontsize=9.5)
a.set_title("(c) 重合的分布：标记后均值落在全体 p10 之下", fontsize=10.5)
a.grid(alpha=0.25, axis="x", ls="--")

# (d) 判定卡
a = axs[1, 1]
a.axis("off")
rows = [
    ("H1", "supported", "标记转移 208 次 ≥ 可行性地板 200（普查口径 267）"),
    ("H2", "supported", "标记后重合 3.1% vs 无标记 14.3%——想法确实不同"),
    ("H3", "below_floor_measured_0.0000", "仪式式反思（重合未降）为零，远低于 20% 地板"),
    ("关键免责", "无正确性标签", "'仪式'指文字未变，不涉及答案对错（G7 触发）"),
    ("口径备注", "208 对 267", "设计句问标记后的想法（前位），普查数后位——双口径并印"),
]
y0 = 0.92
for k, v1, v2 in rows:
    a.text(0.02, y0, k, fontsize=10, weight="bold", color=C_FN, va="top")
    a.text(0.15, y0, v1, fontsize=9.3, weight="bold", va="top", color=C_OPP)
    a.text(0.38, y0, v2, fontsize=8.7, va="top")
    y0 -= 0.185
a.set_title("(d) 判定卡", fontsize=10.5, loc="right")

fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(os.path.join(OUT, "fig2_layers.png"), dpi=200)
plt.close(fig)
print("P068 figs done")
