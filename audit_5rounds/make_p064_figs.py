# -*- coding: utf-8 -*-
"""P064 abstraction_level — 定制图（非模板）。"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import os

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

OUT = r"G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P064_abstraction_level_of_a_trace_and_transfer"
os.makedirs(OUT, exist_ok=True)

C_SUP = "#1a5276"
C_OPP = "#c0392b"
C_NS  = "#b7950b"
C_GY  = "#95a5a6"
C_FN  = "#117a65"
C_GI  = "#6c3483"

# ============ 图 1 ============
fig, axs = plt.subplots(2, 2, figsize=(11.5, 8.8))
fig.suptitle("图 1  语言具体性的跨尝试传递：写实的第二次仍然写实，但不决定成败（EXP-0211，18,216 个尝试对）",
             fontsize=12.5, y=0.985)

# (a) H1 森林 + 分布
a = axs[0, 0]
a.errorbar([0.4805], [0], xerr=[[0.4805 - 0.3996], [0.5614 - 0.4805]], fmt="o",
           color=C_SUP, capsize=6, lw=2, ms=10)
a.axvline(0, color="black", lw=1.0, ls="--")
a.text(0.4805, 0.28, "β=+0.4805 [0.3996, 0.5614]\np_holm<0.001；Pearson r=0.4809\nn=18,216 对，实例聚类", ha="center", fontsize=9.5)
a.text(0.20, -0.30, "具体性水平（标识符/路径/数字密度）\n前次每升 1 SD，后次升 0.48 SD——\n同任务重试保持相同的写实程度", ha="center", fontsize=9.5)
a.set_xlim(-0.1, 0.75)
a.set_ylim(-0.55, 0.55)
a.set_yticks([])
a.set_xlabel("前次具体性对后次具体性的 β", fontsize=9.5)
a.set_title("(a) H1 判 supported：具体性水平跨尝试稳定", fontsize=10.5)
a.grid(alpha=0.25, axis="x", ls="--")

# (b) 标记均值与分布
a = axs[0, 1]
a.bar([0, 1], [18.095, 2.071], width=0.45, color=[C_SUP, C_GY], alpha=0.88)
for i, v in enumerate([18.095, 2.071]):
    a.text(i, v + 0.35, f"{v:.2f}", ha="center", fontsize=11)
a.set_xticks([0, 1])
a.set_xticklabels(["具体标记\n（标识符/路径/数字）", "抽象标记\n（指代/泛称）"], fontsize=10)
a.set_ylabel("每 rollout 平均标记数", fontsize=9.5)
a.set_ylim(0, 21)
a.text(0.5, 12.5, "语料整体生活在具体端：\n具体:抽象 ≈ 8.7 : 1；\n分布 p10/p50/p90 = -1 / 7 / 34\n（右偏，多数轨迹低标记、少数高密集）",
       ha="center", fontsize=9.5)
a.set_title("(b) 具体性轴的原始分布：右偏的写实世界", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (c) H2 null
a = axs[1, 0]
a.bar([0, 1], [3.32, 2.27], width=0.42, color=[C_GY, C_GY], alpha=0.85)
a.errorbar([0], [3.32], yerr=[[0.5], [0.5]], fmt="none", ecolor="#333333", capsize=5, lw=1.4)
a.errorbar([1], [2.27], yerr=[[0.4], [0.4]], fmt="none", ecolor="#333333", capsize=5, lw=1.4)
a.text(0, 4.1, "3.32%", ha="center", fontsize=10.5)
a.text(1, 2.95, "2.27%", ha="center", fontsize=10.5)
a.text(0.5, 5.2, "前次具体性高于中位 vs 低于中位的后次提交率：\n1.05 个百分点的差距（β=-0.0702, p=0.296）\n→ H2 判 null：写实程度不决定成败", ha="center", fontsize=9.5)
a.set_xticks([0, 1])
a.set_xticklabels(["前次高具体", "前次低具体"], fontsize=10)
a.set_ylabel("后次提交率 %", fontsize=9.5)
a.set_ylim(0, 6.2)
a.set_title("(c) H2 判 null：具体性与完成无关", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (d) 分层：重叠带
a = axs[1, 1]
bands = ["高文本重叠\n(n=11,558)", "中文本重叠\n(n=6,644)", "google 仓库\n(n=261)", "k8s 仓库\n(n=322)"]
bs = [0.6514, 0.2232, 0.2606, 0.0733]
los = [0.5613, 0.1426, 0.0168, -0.0261]
his = [0.7414, 0.3038, 0.5045, 0.1726]
x = np.arange(4)
for i in range(4):
    sig = los[i] > 0
    a.bar(x[i], bs[i], width=0.5, color=C_SUP if sig else C_GY, alpha=0.88)
    a.errorbar(x[i], bs[i], yerr=[[bs[i] - los[i]], [his[i] - bs[i]]],
               fmt="none", ecolor="#333333", capsize=5, lw=1.4)
    a.text(x[i], his[i] + 0.02, f"{bs[i]:.3f}" + ("*" if sig else ""), ha="center", fontsize=9.5)
a.axhline(0, color="black", lw=0.9)
a.text(1.5, 0.80, "* CI 排除零。文本重叠越高，具体性传递越强（0.65 vs 0.22）——\n传递随内容连续性增强；仓库间的差异（0.26/0.07）提示\n任务类型也设定具体的基线水位", fontsize=9)
a.set_xticks(x)
a.set_xticklabels(bands, fontsize=8.5)
a.set_ylabel("具体性传递 β", fontsize=9.5)
a.set_ylim(-0.05, 0.92)
a.set_title("(d) 分层：传递随文本重叠增强", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(os.path.join(OUT, "fig1_concreteness.png"), dpi=200)
plt.close(fig)

# ============ 图 2 ============
fig, axs = plt.subplots(2, 2, figsize=(11.5, 8.8))
fig.suptitle("图 2  尝试间的关系结构与 H3 的三臂解剖（EXP-0211）", fontsize=12.5, y=0.985)

# (a) 关系类别
a = axs[0, 0]
rel = [("refinement 精炼", 15732, C_SUP), ("new 重起", 2468, C_NS), ("restatement 复述", 16, C_GY)]
tot = 18216
bars = a.bar([r[0] for r in rel], [r[1] for r in rel], width=0.5, color=[r[2] for r in rel], alpha=0.88)
for b_, (lab, v, c) in zip(bars, rel):
    a.text(b_.get_x() + b_.get_width() / 2, v + 300, f"{v:,}\n({v/tot*100:.1f}%)", ha="center", fontsize=10)
a.set_ylabel("尝试对数", fontsize=9.5)
a.set_ylim(0, 18500)
a.text(1.0, 8000, "86% 的第二次尝试是在第一次基础上的精炼——\n复述几乎不存在（16 对）：\n模型不会把同一段话再说一遍，\n它会在旧笔记上继续写", fontsize=9.5, ha="center")
a.set_title("(a) 尝试间关系：精炼主导，复述绝迹", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (b) H3 三臂
a = axs[0, 1]
arms = [("own 同对臂\n前次→后次", 0.4674, 0.3949, 0.5400, C_SUP),
        ("alien 实例臂\n同实例他对→后次", 0.0958, 0.0573, 0.1344, C_NS)]
y = np.arange(2)
for i, (lab, b, lo, hi, c) in enumerate(arms):
    a.errorbar(b, i, xerr=[[b - lo], [hi - b]], fmt="o", color=c, capsize=6, lw=2, ms=10)
    a.text(hi + 0.015, i, f"β={b:+.4f}", va="center", fontsize=10)
a.axvline(0, color="black", lw=1.0, ls="--")
a.set_yticks(y)
a.set_yticklabels([a_[0] for a_ in arms], fontsize=9.5)
a.invert_yaxis()
a.set_xlabel("对后次具体性的 β（n=13,554）", fontsize=9.5)
a.text(0.18, 1.35, "同对效应是实例效应的 4.9 倍——\n传递主体是紧邻记忆；\n但实例层倾向也显著（任务本身决定具体的基线水位），\n特异性判 not_specific", fontsize=9)
a.set_xlim(-0.05, 0.68)
a.set_ylim(-0.7, 1.9)
a.set_title("(b) H3：紧邻记忆 + 实例倾向的双成分", fontsize=10.5)
a.grid(alpha=0.25, axis="x", ls="--")

# (c) 门槛与测量
a = axs[1, 0]
a.axis("off")
rows = [
    ("G6 门", "≥1,000 条含代码标识符", "实测 18,711 条——具体端样本充裕"),
    ("标记均值", "18.1 具体 / 2.1 抽象", "每 rollout 的具体:抽象 ≈ 8.7:1"),
    ("G3 门", "≥300 重复实例", "实测 1,775——成对结构成立"),
    ("G10 范围", "智能体多样性", "仅在分层层触发——跨脚手架广度不被主张"),
]
y0 = 0.9
for k, v1, v2 in rows:
    a.text(0.02, y0, k, fontsize=10.5, weight="bold", color=C_FN, va="top")
    a.text(0.18, y0, v1, fontsize=9.8, weight="bold", va="top", color=C_OPP)
    a.text(0.46, y0, v2, fontsize=9, va="top")
    y0 -= 0.21
a.set_title("(c) 测量基础", fontsize=10.5, loc="right")

# (d) 判定卡
a = axs[1, 1]
a.axis("off")
rows = [
    ("H1", "supported", "具体性跨尝试传递 β=0.4805（r=0.48）"),
    ("H2", "null", "具体性不预测完成（p=0.296）"),
    ("H3", "not_specific", "实例层 alien 臂 0.0958 显著——非纯成对传递"),
    ("结构", "精炼 86%", "第二次是旧笔记的续写，不是重写"),
    ("工程读法", "具体性是任务属性", "选型含义：抽象/具体的写作规范\n应按任务类型定制，而非全局统一"),
]
y0 = 0.92
for k, v1, v2 in rows:
    a.text(0.02, y0, k, fontsize=10, weight="bold", color=C_FN, va="top")
    a.text(0.14, y0, v1, fontsize=9.5, weight="bold", va="top", color=C_OPP)
    a.text(0.32, y0, v2, fontsize=8.8, va="top")
    y0 -= 0.18
a.set_title("(d) 判定卡", fontsize=10.5, loc="right")

fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(os.path.join(OUT, "fig2_relations.png"), dpi=200)
plt.close(fig)
print("P064 figs done")
