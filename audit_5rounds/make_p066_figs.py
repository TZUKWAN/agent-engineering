# -*- coding: utf-8 -*-
"""P066 relation_classes — 定制图（非模板）。"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import os

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

OUT = r"G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P066_relation_classes_between_attempts_of_one_task"
os.makedirs(OUT, exist_ok=True)

C_SUP = "#1a5276"
C_OPP = "#c0392b"
C_NS  = "#b7950b"
C_GY  = "#95a5a6"
C_FN  = "#117a65"

# ============ 图 1 ============
fig, axs = plt.subplots(2, 2, figsize=(11.5, 8.8))
fig.suptitle("图 1  尝试间的语义关系：流行度清晰、预测力缺席（EXP-0213，18,216 个尝试对）",
             fontsize=12.5, y=0.985)

# (a) 流行度
a = axs[0, 0]
cls = [("refinement 精炼", 86.36, 85.67, 87.09, C_SUP),
       ("new 重起", 13.55, 12.83, 14.30, C_NS),
       ("restatement 复述", 0.09, 0.02, 0.19, C_GY)]
x = np.arange(3)
for i, (lab, v, lo, hi, c) in enumerate(cls):
    a.bar(i, v, width=0.5, color=c, alpha=0.88)
    a.errorbar(i, v, yerr=[[v - lo], [hi - v]], fmt="none", ecolor="#333333",
               capsize=5, lw=1.4)
    a.text(i, hi + 1.5, f"{v:.2f}%\n[{lo:.2f}, {hi:.2f}]", ha="center", fontsize=9)
a.axhline(5, color=C_OPP, lw=1.4, ls="--")
a.text(2.3, 5.6, "冻结地板 5%", fontsize=8.5, color=C_OPP)
a.set_xticks(x)
a.set_xticklabels([c[0] for c in cls], fontsize=10)
a.set_ylabel("尝试对中的份额 %", fontsize=9.5)
a.set_ylim(0, 100)
a.set_title("(a) H1 描述性：精炼 86.4%、重起 13.6%、复述近零", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (b) 词面重合按类别
a = axs[0, 1]
a.bar([0, 1], [21.44, 33.46], width=0.42, color=[C_NS, C_SUP], alpha=0.88)
a.text(0, 22.4, "21.4%", ha="center", fontsize=11)
a.text(1, 34.4, "33.5%", ha="center", fontsize=11)
a.set_xticks([0, 1])
a.set_xticklabels(["重起对\n(n=2,468)", "精炼对\n(n=15,732)"], fontsize=10)
a.set_ylabel("两次散文的平均 Jaccard 重合", fontsize=9.5)
a.set_ylim(0, 40)
a.text(0.5, 37, "全对分布 p10/p50/p90 = 0.237/0.321/0.393：\n重起不是白纸（重合 21%），\n精炼也只是部分连续——三分类是词面连续度的粗档",
       ha="center", fontsize=9)
a.set_title("(b) 类别的词面基础：重合差 12 个百分点", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (c) 原始提交率与强预测元
a = axs[1, 0]
a.bar([0, 1], [1.66, 2.99], width=0.42, color=[C_NS, C_SUP], alpha=0.88)
a.text(0, 1.85, "1.66%", ha="center", fontsize=10.5)
a.text(1, 3.18, "2.99%", ha="center", fontsize=10.5)
a.set_xticks([0, 1])
a.set_xticklabels(["重起后的下次", "精炼后的下次"], fontsize=10)
a.set_ylabel("下次提交率 %（原始）", fontsize=9.5)
a.set_ylim(0, 4.2)
a.text(0.5, 3.75, "但模型的强预测元不是类别——\n是前次结局：β=+2.804 [2.386, 3.222]\n（前次提交过 → 下次提交赔率 ×16.5）", ha="center", fontsize=9.5)
a.set_title("(c) 原始差异与真正的预测元", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (d) 仓库分层
a = axs[1, 1]
a.errorbar([0], [10.73], yerr=[[1.9], [1.9]], fmt="o", color=C_SUP, capsize=6, lw=1.8, ms=9)
a.errorbar([1], [4.35], yerr=[[1.1], [1.1]], fmt="s", color=C_NS, capsize=6, lw=1.8, ms=9)
a.text(0, 13.1, "google：提交率 10.73%\n精炼份额 88.5%（n=261）", ha="center", fontsize=9)
a.text(1, 6.6, "kubernetes-sigs：提交率 4.35%\n精炼份额 81.1%（n=322）", ha="center", fontsize=9)
a.text(0.5, 1.2, "仓库间提交率差 2.5 倍、精炼份额差 7 个百分点——\n任务域设定重试形态与成功率的共同背景", fontsize=9, ha="center")
a.set_xticks([0, 1])
a.set_xticklabels(["google 仓库", "kubernetes-sigs"], fontsize=10)
a.set_xlim(-0.5, 1.5)
a.set_ylim(0, 15)
a.set_ylabel("对内提交率 %", fontsize=9.5)
a.set_title("(d) 仓库分层：任务域是背景板", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(os.path.join(OUT, "fig1_relations.png"), dpi=200)
plt.close(fig)

# ============ 图 2 ============
fig, axs = plt.subplots(2, 2, figsize=(11.5, 8.8))
fig.suptitle("图 2  准分离的解剖、实例异质性与判定（EXP-0213）", fontsize=12.5, y=0.985)

# (a) 准分离解剖
a = axs[0, 0]
a.axis("off")
rows = [
    ("病灶", "restatement 格：16 对中结局几乎完美预测类别"),
    ("症状", "new 类系数 17.94，CI [-222, +258]，SE=122.6"),
    ("处理", "系数按冻结规则扣留（withheld）——不是效应量"),
    ("判定", "H2/H3 均 not_estimable_quasi_separation"),
    ("教训", "稀有格 + 完全共现 = logistic 病态；\n系数必须扣留，方向也不可读"),
]
y0 = 0.93
for k, v in rows:
    a.text(0.02, y0, k, fontsize=10.5, weight="bold", color=C_FN, va="top")
    a.text(0.15, y0, v, fontsize=9.2, va="top", color=C_OPP if k in ("症状", "判定") else "#333333")
    y0 -= 0.185
a.set_title("(a) 准分离的病案记录", fontsize=10.5, loc="right")

# (b) 模型组件
a = axs[0, 1]
items = [("前次结局\nearlier_outcome", 2.804, 2.386, 3.222, C_SUP),
         ("类目项\n（扣留）", 18.89, -283.15, 320.93, C_GY)]
y = np.arange(2)
for i, (lab, b, lo, hi, c) in enumerate(items):
    a.errorbar(b, i, xerr=[[b - lo], [hi - b]], fmt="o", color=c, capsize=6, lw=1.8, ms=9)
a.text(2.9, 0, "β=+2.804 [2.386, 3.222]\np<0.001——模型中唯一健康的项", fontsize=9, va="center")
a.text(19, 1, "β=18.89，CI 横跨 ±300：\n病态，扣留", fontsize=9, va="center", color=C_GY)
a.axvline(0, color="black", lw=1.0, ls="--")
a.set_yticks(y)
a.set_yticklabels([i[0] for i in items], fontsize=9.5)
a.invert_yaxis()
a.set_xlabel("对下次提交的 β（log-odds）", fontsize=9.5)
a.set_xlim(-40, 120)
a.set_ylim(-0.7, 1.9)
a.set_title("(b) 模型体检：一项健康、一项病态", fontsize=10.5)
a.grid(alpha=0.25, axis="x", ls="--")

# (c) 实例异质性：alien 类别流行度
a = axs[1, 0]
al = [("以重起为主", 67.49, C_NS), ("无多次尝试结构", 25.59, C_GY), ("以精炼为主", 6.92, C_SUP)]
x = np.arange(3)
for i, (lab, v, c) in enumerate(al):
    a.bar(i, v, width=0.5, color=c, alpha=0.88)
    a.text(i, v + 1.2, f"{v:.1f}%", ha="center", fontsize=10.5)
a.set_xticks(x)
a.set_xticklabels([a_[0] for a_ in al], fontsize=9.5)
a.set_ylabel("实例的份额 %", fontsize=9.5)
a.set_ylim(0, 78)
a.text(1.0, 60, "三分之二的实例以重起为多数关系——\n重试风格是实例属性：\n有的任务反复推倒重来，有的持续精炼", fontsize=9.5, ha="center")
a.set_title("(c) 重试风格的实例异质性", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (d) 判定卡
a = axs[1, 1]
a.axis("off")
rows = [
    ("H1", "measured（描述性）", "86.4 / 13.6 / 0.09，两地板（5%）一过一不过"),
    ("H2", "not_estimable", "类别→完成：准分离，系数扣留"),
    ("H3", "not_estimable", "同上；Δdeviance 仅 17.6"),
    ("强信号", "前次结局 β=2.80", "上一次成了，下一次大概率成——\n实例难度主导一切"),
    (" contradiction", "8.6% 的对含矛盾标记", "两次尝试的结论冲突率"),
]
y0 = 0.92
for k, v1, v2 in rows:
    a.text(0.02, y0, k, fontsize=10, weight="bold", color=C_FN, va="top")
    a.text(0.16, y0, v1, fontsize=9.3, weight="bold", va="top", color=C_OPP)
    a.text(0.40, y0, v2, fontsize=8.7, va="top")
    y0 -= 0.185
a.set_title("(d) 判定卡", fontsize=10.5, loc="right")

fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(os.path.join(OUT, "fig2_verdicts.png"), dpi=200)
plt.close(fig)
print("P066 figs done")
