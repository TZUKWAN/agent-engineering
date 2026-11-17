# -*- coding: utf-8 -*-
"""P070 structural aggregation — 定制图（收官包，非模板）。"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import os

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

OUT = r"G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P070_agent_trajectory_corpora_as_intelligence_sources"
os.makedirs(OUT, exist_ok=True)

C_SUP = "#1a5276"
C_OPP = "#c0392b"
C_NS  = "#b7950b"
C_GY  = "#95a5a6"
C_FN  = "#117a65"

corpora = ["MMAT-1M", "AgentTrove", "code-act", "Toucan-1.5M", "SWE-ZERO", "hermes", "AgentBank", "AgentInstruct"]
rows = [1659279, 180240, 78385, 51852, 40000, 22347, 15737, 1320]
ncols = [2, 21, 2, 9, 6, 6, 2, 2]
labelled = [0, 1, 0, 1, 1, 0, 0, 0]

constructs = ["source-attribution", "effort-and-budget", "tool-catalogue", "repair-after-failure",
              "contradiction-across-sources", "grounding-in-evidence", "outcome-or-quality-label", "stopping-decision"]
matrix = {
    "AgentBank":    [0,0,0,0,0,0,0,0],
    "AgentInstruct":[0,0,0,0,0,0,0,0],
    "AgentTrove":   [1,0,0,1,0,0,1,0],
    "MMAT-1M":      [0,0,0,0,1,1,0,1],
    "SWE-ZERO":     [0,1,0,1,1,1,1,1],
    "Toucan-1.5M":  [0,0,1,0,1,1,1,1],
    "code-act":     [0,0,0,0,0,0,0,0],
    "hermes":       [0,0,1,0,0,0,0,0],
}

# ============ 图 1 ============
fig, axs = plt.subplots(2, 2, figsize=(11.5, 8.8))
fig.suptitle("图 1  八个本地语料库的结构普查：三个数量级的规模差、3/8 的标签覆盖（EXP-0219）",
             fontsize=12.5, y=0.985)

# (a) 规模（对数轴）
a = axs[0, 0]
y = np.arange(len(corpora))
cols = [C_SUP if l else C_GY for l in labelled]
a.barh(y, rows, color=cols, alpha=0.88)
for i, v in enumerate(rows):
    a.text(v * 1.15, i, f"{v:,}", va="center", fontsize=8.5)
a.set_xscale("log")
a.set_xlim(800, 8e6)
a.set_yticks(y)
a.set_yticklabels(corpora, fontsize=9)
a.invert_yaxis()
a.axvline(1000, color=C_OPP, lw=0, ls="")
a.text(2.4e6, 7.5, "最大/最小 ≈ 1,257 倍\n（3.1 个数量级）", fontsize=9.5, color=C_OPP, ha="center")
a.set_xlabel("前四个分片的行数（对数轴；非语料总量）", fontsize=9)
a.set_title("(a) 规模差三个数量级：合并即比较苹果与问题", fontsize=10.5)
a.grid(alpha=0.25, axis="x", ls="--")

# (b) 标签覆盖
a = axs[0, 1]
a.bar([0], [3], width=0.4, color=C_NS, alpha=0.9)
a.bar([1], [8], width=0.4, color=C_GY, alpha=0.4)
a.axhline(4, color=C_OPP, lw=1.8, ls="--")
a.text(1.25, 4.1, "冻结地板 4", fontsize=9.5, color=C_OPP)
a.text(0, 3.15, "3", ha="center", fontsize=12, weight="bold")
a.text(1, 8.15, "8", ha="center", fontsize=12, color=C_GY)
a.set_xticks([0, 1])
a.set_xticklabels(["带结局/质量标签\n（SWE、Toucan、AgentTrove）", "全部语料库"], fontsize=9.5)
a.set_ylabel("语料库数", fontsize=9.5)
a.set_ylim(0, 9.5)
a.text(0.5, 6.6, "G12 门失火：3 < 4\n——关于标签证据的一切跨库主张\n强度不得超过这个计数（W12-D03）", ha="center", fontsize=9.5, color=C_OPP)
a.set_title("(b) H1 判 measured（受限）：标签覆盖 3/8", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (c) 列数
a = axs[1, 0]
a.barh(y, ncols, color=[C_SUP if n > 5 else C_GY for n in ncols], alpha=0.88)
for i, v in enumerate(ncols):
    a.text(v + 0.3, i, str(v), va="center", fontsize=9)
a.set_yticks(y)
a.set_yticklabels(corpora, fontsize=9)
a.invert_yaxis()
a.set_xlabel("每个语料录得的列数", fontsize=9.5)
a.set_xlim(0, 24)
a.text(10, 1.0, "AgentTrove 21 列 vs 多数 2 列：\n模式鸿沟比规模鸿沟更难弥合", fontsize=9)
a.set_title("(c) 模式宽度：2 列到 21 列", fontsize=10.5)
a.grid(alpha=0.25, axis="x", ls="--")

# (d) 判定卡
a = axs[1, 1]
a.axis("off")
rows = [
    ("H1", "measured（受限）", "标签覆盖 3/8，G12 门失火（地板 4）"),
    ("H2", "measured", "规模比 3.1 个数量级——合并池无共同单位"),
    ("H3", "measured", "构念可用率：每库平均 2.25/8（28%）"),
    ("最全语料", "SWE-ZERO 6/8", "缺来源归属与工具目录"),
    ("空白语料", "4 个全零", "AgentBank / AgentInstruct / code-act / MMAT 之外的对照"),
]
y0 = 0.92
for k, v1, v2 in rows:
    a.text(0.02, y0, k, fontsize=10, weight="bold", color=C_FN, va="top")
    a.text(0.15, y0, v1, fontsize=9.3, weight="bold", va="top", color=C_OPP)
    a.text(0.34, y0, v2, fontsize=8.7, va="top")
    y0 -= 0.185
a.set_title("(d) 判定卡", fontsize=10.5, loc="right")

fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(os.path.join(OUT, "fig1_census.png"), dpi=200)
plt.close(fig)

# ============ 图 2：构念矩阵 ============
fig, axs = plt.subplots(1, 2, figsize=(11.5, 5.6), gridspec_kw={"width_ratios": [1.55, 1]})
fig.suptitle("图 2  构念 × 语料库支持矩阵：八大信息行为构念谁能测（EXP-0219）", fontsize=12.5, y=0.99)

a = axs[0]
corp_order = ["SWE-ZERO", "Toucan-1.5M", "AgentTrove", "MMAT-1M", "hermes", "AgentBank", "AgentInstruct", "code-act"]
M = np.array([matrix[c] for c in corp_order])
im = a.imshow(M, cmap="RdYlGn", vmin=-0.4, vmax=1.4, aspect="auto")
a.set_xticks(range(len(constructs)))
a.set_xticklabels([c.replace("-", "\n").replace("across sources", "×src").replace("or quality label", "or quality").replace("and budget", "+budget").replace("in evidence", "in evid.").replace("after failure", "after fail").replace("catalogue", "cat.").replace("attribution", "attr.").replace("decision", "dec.").replace("contradiction", "contra.").replace("grounding", "ground.").replace("repair", "repair") for c in constructs], fontsize=7.2, rotation=0)
a.set_yticks(range(len(corp_order)))
a.set_yticklabels(corp_order, fontsize=9)
for i in range(len(corp_order)):
    for j in range(len(constructs)):
        a.text(j, i, "√" if M[i, j] else "·", ha="center", va="center",
               fontsize=11, color="white" if M[i, j] else "#999999", weight="bold")
a.set_title("八构念支持矩阵（√=列名可支持）", fontsize=10.5)
a.tick_params(axis="x", bottom=False)

a = axs[1]
totals = [sum(matrix[c][k] for c in matrix) for k in range(len(constructs))]
b = axs[1]
y = np.arange(len(constructs))
b.barh(y, totals, color=[C_SUP if t >= 3 else (C_NS if t >= 2 else C_OPP) for t in totals], alpha=0.88)
for i, v in enumerate(totals):
    b.text(v + 0.05, i, f"{v}/8", va="center", fontsize=9.5)
b.set_yticks(y)
b.set_yticklabels([c.split("-")[0] for c in constructs], fontsize=8.5)
b.invert_yaxis()
b.set_xlim(0, 9)
b.set_xlabel("可支持的语料库数 / 8", fontsize=9.5)
b.set_title("构念级合计：最好成绩 3/8", fontsize=10.5)
b.grid(alpha=0.25, axis="x", ls="--")

fig.tight_layout(rect=[0, 0, 1, 0.93])
fig.savefig(os.path.join(OUT, "fig2_matrix.png"), dpi=200)
plt.close(fig)
print("P070 figs done")
