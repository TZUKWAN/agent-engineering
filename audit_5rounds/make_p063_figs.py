# -*- coding: utf-8 -*-
"""P063 which_components_carry_forward — 定制图（非模板）。"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import os

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

OUT = r"G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P063_which_components_of_a_trace_carry_forward"
os.makedirs(OUT, exist_ok=True)

C_SUP = "#1a5276"
C_OPP = "#c0392b"
C_NS  = "#b7950b"
C_GY  = "#95a5a6"
C_FN  = "#117a65"

# ============ 图 1 ============
fig, axs = plt.subplots(2, 2, figsize=(11.5, 8.8))
fig.suptitle("图 1  话语成分的跨尝试携带：第一次说过的话，第二次更可能再说（EXP-0210，18,216 个尝试对）",
             fontsize=12.5, y=0.985)

# (a) 各类别 lift 排序
a = axs[0, 0]
cats = [("exception 异常", 0.3201, 0.2976, 0.3396),
        ("context 背景", 0.2861, 0.2688, 0.3081),
        ("result 结果", 0.2356, 0.2150, 0.2538),
        ("rationale 理由", 0.1749, 0.1541, 0.1915),
        ("provenance 出处", 0.1537, 0.1331, 0.1767),
        ("condition 条件", 0.1500, 0.1279, 0.1738),
        ("observation 观察", 0.1265, 0.1089, 0.1430)]
cats.sort(key=lambda x: -x[1])
y = np.arange(len(cats))
for i, (lab, l, lo, hi) in enumerate(cats):
    col = C_OPP if l > 0.25 else (C_SUP if l > 0.17 else C_NS)
    a.errorbar(l, i, xerr=[[l - lo], [hi - l]], fmt="o", color=col,
               capsize=4, lw=1.6, ms=7)
    a.text(hi + 0.008, i, f"{l:.3f}", va="center", fontsize=9)
a.axvline(0, color="black", lw=1.0, ls="--")
a.set_yticks(y)
a.set_yticklabels([c[0] for c in cats], fontsize=9)
a.invert_yaxis()
a.set_xlabel("携带提升 lift（前次出现→后次出现率的提升，400 次 cluster bootstrap）", fontsize=9)
a.set_xlim(0.09, 0.37)
a.set_title("(a) 七类话语全部正携带：异常最强、观察最弱", fontsize=10.5)
a.grid(alpha=0.25, axis="x", ls="--")

# (b) 哑铃：缺席 vs 在场时后次出现率
a = axs[0, 1]
cats2 = [("condition 条件", 73.94, 88.94), ("provenance 出处", 72.86, 88.22),
         ("rationale 理由", 63.39, 80.88), ("observation 观察", 54.32, 66.98),
         ("exception 异常", 36.83, 68.84), ("context 背景", 32.46, 61.07)]
y = np.arange(len(cats2))
for i, (lab, ab, pr) in enumerate(cats2):
    a.plot([ab, pr], [i, i], color="#cccccc", lw=3, zorder=1)
    a.scatter(ab, i, color=C_GY, s=55, zorder=2, label="前次缺席" if i == 0 else "")
    a.scatter(pr, i, color=C_OPP, s=55, zorder=2, label="前次在场" if i == 0 else "")
    a.text(max(ab, pr) + 1.2, i, f"+{pr-ab:.1f}pp", va="center", fontsize=8.5, color="#555555")
a.set_yticks(y)
a.set_yticklabels([c[0] for c in cats2], fontsize=9)
a.set_xlim(25, 102)
a.set_xlabel("后一尝试中该话语类别的出现率 %", fontsize=9.5)
a.set_title("(b) 条件与出处本就常见（高位），异常与背景的携带最戏剧化", fontsize=10.5)
a.legend(fontsize=8.5, loc="lower right")
a.grid(alpha=0.25, axis="x", ls="--")

# (c) H2 类间差
a = axs[1, 0]
a.axis("off")
rows = [
    ("最强", "exception 异常", "lift = 0.3201 [0.2976, 0.3396]"),
    ("最弱", "observation 观察", "lift = 0.1265 [0.1089, 0.1430]"),
    ("极差", "spread = 0.1936", "两类的 CI 不重叠 → 类间差异真实"),
    ("判定", "not_uniform_enough_to_claim", "类别不均匀，'均匀携带'的主张不成立"),
    ("分层读法", "内容类 > 锚定类", "异常/背景/结果（0.24-0.32）>\n理由/出处/条件（0.15-0.17）> 观察（0.13）"),
]
y0 = 0.93
for k, v1, v2 in rows:
    a.text(0.02, y0, k, fontsize=10.5, weight="bold", color=C_FN, va="top")
    a.text(0.17, y0, v1, fontsize=10, weight="bold", va="top", color=C_OPP)
    a.text(0.42, y0, v2, fontsize=8.8, va="top")
    y0 -= 0.18
a.set_title("(c) H2：携带强度分层为三档", fontsize=10.5, loc="right")

# (d) H3 三臂
a = axs[1, 1]
arms = [("own 自类臂\n前次异常→后次异常", 0.3111, 0.2867, 0.3354, C_OPP),
        ("alien 异类臂\n前次他类→后次异常", 0.0282, 0.0102, 0.0461, C_NS),
        ("overlap 文本重合臂", -0.0122, -0.0210, -0.0034, C_GY)]
y = np.arange(3)
for i, (lab, b, lo, hi, c) in enumerate(arms):
    a.errorbar(b, i, xerr=[[b - lo], [hi - b]], fmt="o", color=c,
               capsize=5, lw=1.8, ms=9)
    a.text(hi + 0.01, i, f"β={b:+.4f}" + ("\nCI 排除零" if lo > 0 or hi < 0 else ""),
           va="center", fontsize=9)
a.axvline(0, color="black", lw=1.0, ls="--")
a.set_yticks(y)
a.set_yticklabels([a_[0] for a_ in arms], fontsize=9)
a.invert_yaxis()
a.set_xlabel("对后次异常话语的 β（联合模型，n=13,554）", fontsize=9.5)
a.text(0.10, 1.9, "自类效应是异类效应的 11 倍；\n但异类臂也显著——特异性判 not_specific：\n携带大部分内容特异、小部分泛化", fontsize=9)
a.set_xlim(-0.04, 0.42)
a.set_ylim(-0.6, 2.6)
a.set_title("(d) H3 的三臂解剖：主效应特异，少量泛化", fontsize=10.5)
a.grid(alpha=0.25, axis="x", ls="--")

fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(os.path.join(OUT, "fig1_carryforward.png"), dpi=200)
plt.close(fig)

# ============ 图 2 ============
fig, axs = plt.subplots(2, 2, figsize=(11.5, 8.8))
fig.suptitle("图 2  携带的结构：基率、机制与判定（EXP-0210）", fontsize=12.5, y=0.985)

# (a) 前次出现基率
a = axs[0, 0]
cats3 = [("condition", 15848), ("provenance", 15663), ("observation", 11289),
         ("exception", 9836), ("context", 8274), ("rationale", 13941),
         ("result", 12500)]
tot = 18216
names = [c[0] for c in cats3]
vals = [c[1] / tot * 100 for c in cats3]
a.barh(range(len(cats3)), vals, color=C_SUP, alpha=0.8)
for i, v in enumerate(vals):
    a.text(v + 0.8, i, f"{v:.1f}%", va="center", fontsize=9)
a.set_yticks(range(len(cats3)))
a.set_yticklabels(names, fontsize=9)
a.invert_yaxis()
a.set_xlabel("尝试对中前次已含该类话语的比例 %（result 为近似值）", fontsize=9)
a.set_xlim(0, 105)
a.set_title("(a) 携带的基率：条件与出处近九成在场，背景不足半数", fontsize=10.5)
a.grid(alpha=0.25, axis="x", ls="--")

# (b) 机制分解
a = axs[0, 1]
a.axis("off")
rows = [
    ("总携带", "lift ≈ 0.32（异常类）", "第一次讨论异常 → 第二次出现率 +32pp"),
    ("内容特异部分", "自类臂 β=0.3111", "同类别跨尝试传递——任务记忆"),
    ("泛化部分", "异类臂 β=0.0282", "他类话语也小幅抬升——风格惯性"),
    ("文本重合", "β=-0.0122", "控制字面重合后为弱负——不是抄写"),
    ("读法", "≈91% 特异 + 9% 泛化", "程序性知识以内容为载体，\n风格搭了便车"),
]
y0 = 0.93
for k, v1, v2 in rows:
    a.text(0.02, y0, k, fontsize=10, weight="bold", color=C_FN, va="top")
    a.text(0.20, y0, v1, fontsize=9.5, weight="bold", va="top", color=C_OPP)
    a.text(0.44, y0, v2, fontsize=8.8, va="top")
    y0 -= 0.185
a.set_title("(b) 携带机制的三成分分解", fontsize=10.5, loc="right")

# (c) 三档分层可视化
a = axs[1, 0]
groups = [("内容类\n异常/背景/结果", [0.3201, 0.2861, 0.2356], C_OPP),
          ("锚定类\n理由/出处/条件", [0.1749, 0.1537, 0.1500], C_SUP),
          ("观察类", [0.1265], C_GY)]
x = 0
ticks = []
for lab, ls, col in groups:
    for l in ls:
        a.bar(x, l, width=0.6, color=col, alpha=0.85)
        a.text(x, l + 0.006, f"{l:.3f}", ha="center", fontsize=9)
        ticks.append((x, ""))
        x += 1
    x += 0.7
a.set_xticks([t[0] for t in ticks])
a.set_xticklabels(["异常", "背景", "结果", "理由", "出处", "条件", "观察"], fontsize=9.5)
a.set_ylabel("携带 lift", fontsize=9.5)
a.set_ylim(0, 0.38)
a.axhline(0.1936 / 2, color=C_NS, lw=0, ls="")
a.text(2.1, 0.33, "三档结构：内容类约是观察类的 2.5 倍\n——越接近'任务的发现'，越容易被下次复述", fontsize=9.5)
a.set_title("(c) 携带的三档结构", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (d) 判定卡
a = axs[1, 1]
a.axis("off")
rows = [
    ("H1", "supported", "七类话语全部正携带（lift 0.13-0.32），β=0.3201"),
    ("H2", "not_uniform", "极差 0.1936——类别间携带强度不同"),
    ("H3", "not_specific", "异类臂也显著（0.0282）——携带不纯内容特异"),
    ("样本", "18,216 对", "1,775 个实例的成对尝试；400 次 cluster bootstrap"),
    ("设计", "成对差分", "同一任务内前后对照，剥离任务难度"),
]
y0 = 0.92
for k, v1, v2 in rows:
    a.text(0.02, y0, k, fontsize=10, weight="bold", color=C_FN, va="top")
    a.text(0.14, y0, v1, fontsize=9.5, weight="bold", va="top", color=C_OPP)
    a.text(0.32, y0, v2, fontsize=8.8, va="top")
    y0 -= 0.175
a.set_title("(d) 判定卡", fontsize=10.5, loc="right")

fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(os.path.join(OUT, "fig2_structure.png"), dpi=200)
plt.close(fig)
print("P063 figs done")
