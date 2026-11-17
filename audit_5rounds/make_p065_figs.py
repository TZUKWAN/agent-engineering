# -*- coding: utf-8 -*-
"""P065 what_a_compression_loses_first — 定制图（非模板）。"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import os

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

OUT = r"G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P065_what_a_compression_loses_first"
os.makedirs(OUT, exist_ok=True)

C_SUP = "#1a5276"
C_OPP = "#c0392b"
C_NS  = "#b7950b"
C_GY  = "#95a5a6"
C_FN  = "#117a65"

# 数据：25% 预算下的存活率（bottom→top 排序）
cats = [
    ("result 结果", 0.0336, 0.3987, 0.6),
    ("negcon 负向约束", 0.0917, 0.4358, None),
    ("exception 异常", 0.1187, 0.5412, 0.5333),
    ("context 背景", 0.1235, 0.4547, 0.4667),
    ("uncert 不确定性", 0.1391, 0.5726, None),
    ("observation 观察", 0.2052, 0.6210, 0.4),
    ("condition 条件", 0.2561, 0.8694, 0.3333),
    ("rationale 理由", 0.3645, 0.7665, 0.2667),
    ("provenance 出处", 0.4805, 0.8608, 0.2),
    ("procedure 过程", 1.0000, 1.0000, 0.0),
]

# ============ 图 1 ============
fig, axs = plt.subplots(2, 2, figsize=(11.5, 8.8))
fig.suptitle("图 1  压缩到开头 25% 时谁先死：结果话语几乎全灭，出处反而最耐压（EXP-0212，20,000 条 rollout）",
             fontsize=12.5, y=0.985)

# (a) 25% 预算存活排序
a = axs[0, 0]
names = [c[0] for c in cats]
vals = [c[1] for c in cats]
cols = [C_OPP if v < 0.15 else (C_NS if v < 0.30 else C_SUP) for v in vals]
y = np.arange(len(cats))
a.barh(y, vals, color=cols, alpha=0.88)
for i, v in enumerate(vals):
    a.text(v + 0.012, i, f"{v*100:.1f}%", va="center", fontsize=9)
a.set_yticks(y)
a.set_yticklabels(names, fontsize=9)
a.invert_yaxis()
a.set_xlabel("保留开头 25% 后该类话语仍存活的比率", fontsize=9.5)
a.axvline(0.25, color="black", lw=0.9, ls=":")
a.text(0.255, 0.1, "基线 25%（若均匀分布）", fontsize=8, rotation=90)
a.set_title("(a) 存活排行：结果 3.4% / 过程 100%，极差 96.6 个百分点", fontsize=10.5)
a.grid(alpha=0.25, axis="x", ls="--")

# (b) 存活曲线
a = axs[0, 1]
budgets = [10, 25, 50]
sel = [("result 结果", [0.81, 3.36, 14.64], C_OPP),
       ("negcon 负向约束", [3.26, 9.17, 21.08], "#e67e22"),
       ("exception 异常", [5.44, 11.87, 26.92], C_NS),
       ("condition 条件", [6.30, 25.61, 59.47], C_GY),
       ("provenance 出处", [26.46, 48.05, 69.06], C_SUP),
       ("procedure 过程", [99.94, 100.0, 100.0], C_FN)]
for lab, ys, c in sel:
    a.plot(budgets, ys, "o-", color=c, lw=1.8, ms=5, label=lab)
a.set_xticks(budgets)
a.set_xticklabels(["10%", "25%", "50%"], fontsize=10)
a.set_xlabel("压缩预算（保留开头比例）", fontsize=9.5)
a.set_ylabel("存活率 %", fontsize=9.5)
a.set_title("(b) 存活曲线：结果话语在所有预算下都垫底", fontsize=10.5)
a.legend(fontsize=7.8, loc="upper left")
a.grid(alpha=0.25, ls="--")

# (c) 首现位置 vs 存活
a = axs[1, 0]
pts = [(lab.split()[0], pos, s25*100) for lab, s25, pres, pos in cats if pos is not None]
for lab, pos, s25 in pts:
    a.scatter(pos, s25, s=70, color=C_SUP, alpha=0.75, edgecolor="white")
    a.annotate(lab, (pos, s25), textcoords="offset points", xytext=(6, 4), fontsize=8.5)
z = np.polyfit([p for _, p, _ in pts], [s for _, _, s in pts], 1)
xs = np.linspace(0, 0.65, 20)
a.plot(xs, np.polyval(z, xs), "--", color=C_OPP, lw=1.4)
a.text(0.33, 62, "首现位置越晚，存活越低\n（斜率 ≈ -75pp/单位位置）", fontsize=9, color=C_OPP)
a.set_xlabel("该类话语的中位首现位置（0=开头，1=结尾）", fontsize=9.5)
a.set_ylabel("25% 预算存活率 %", fontsize=9.5)
a.set_xlim(0, 0.68)
a.set_title("(c) 位置决定命运：结果话语首现在 0.60，出处首现在 0.20", fontsize=10.5)
a.grid(alpha=0.25, ls="--")

# (d) 预测记分卡
a = axs[1, 1]
a.axis("off")
rows = [
    ("预测的最先死亡", "exception / condition / provenance / uncert"),
    ("实测的最先死亡", "result (3.4%) / negcon (9.2%) / exception (11.9%)"),
    ("最大错判", "provenance：预测垫底，实测第 9/10（48.1%）"),
    ("判对的部分", "exception 确实位列死亡前三"),
    ("判定", "not_the_predicted_ordering（极差 0.9664）"),
    ("机制", "首现位置主导：晚说的一切先死"),
]
y0 = 0.93
for k, v in rows:
    a.text(0.02, y0, k, fontsize=10, weight="bold", color=C_FN, va="top")
    a.text(0.26, y0, v, fontsize=9.2, va="top", color=C_OPP if "判定" in k or "错判" in k or "实测" in k else "#333333")
    y0 -= 0.155
a.set_title("(d) 预测 vs 实测记分卡", fontsize=10.5, loc="right")

fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(os.path.join(OUT, "fig1_survival.png"), dpi=200)
plt.close(fig)

# ============ 图 2 ============
fig, axs = plt.subplots(2, 2, figsize=(11.5, 8.8))
fig.suptitle("图 2  位置伪影的剥离、丢失的代价与判定（EXP-0212）", fontsize=12.5, y=0.985)

# (a) H3 丢失异常的代价
a = axs[0, 0]
a.errorbar([0.2199], [0], xerr=[[0.2199 - (-0.0081)], [0.4479 - 0.2199]], fmt="o",
           color=C_GY, capsize=7, lw=2, ms=10)
a.axvline(0, color="black", lw=1.0, ls="--")
a.text(0.2199, 0.30, "β=+0.2199 [-0.0081, +0.4479]\np=0.0587 → null\nn=7,669 个删除对", ha="center", fontsize=9.5)
a.text(0.2199, -0.32, "压缩丢失异常话语后，下次提交率 3.4% vs 保留时 2.37%\n点估计反而为正——丢失异常没有可检出的代价", ha="center", fontsize=9)
a.set_xlim(-0.25, 0.65)
a.set_ylim(-0.55, 0.55)
a.set_yticks([])
a.set_xlabel("删除异常话语对下次提交的 β（实例聚类）", fontsize=9.5)
a.set_title("(a) H3 判 null：丢了异常，下次照样活", fontsize=10.5)
a.grid(alpha=0.25, axis="x", ls="--")

# (b) 长度分层的异常存活
a = axs[0, 1]
qs = ["q1", "q2", "q3", "q4"]
sv = [12.68, 11.86, 11.18, 11.76]
a.bar(qs, sv, width=0.5, color=C_SUP, alpha=0.85)
for i, v in enumerate(sv):
    a.text(i, v + 0.2, f"{v:.2f}%", ha="center", fontsize=10)
a.set_xticklabels(["q1 最短", "q2", "q3", "q4 最长"], fontsize=9.5)
a.set_ylabel("异常话语在 25% 预算下的平均存活", fontsize=9.5)
a.set_ylim(0, 15)
a.text(1.0, 13.2, "异常话语的存活率跨长度四分位几乎恒定（11-13%）——\n压缩伤害不挑轨迹长度；\n（全部 rollout 均为 15 回合截断，长度变异本身有限）", fontsize=9)
a.set_title("(b) 分层：异常存活的长度稳定性", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (c) 基率 vs 存活
a = axs[1, 0]
for lab, s25, pres, pos in cats:
    if lab.startswith("procedure"):
        continue
    a.scatter(pres * 100, s25 * 100, s=70, color=C_FN, alpha=0.75, edgecolor="white")
    a.annotate(lab.split()[0], (pres * 100, s25 * 100), textcoords="offset points",
               xytext=(5, 4), fontsize=8.5)
a.set_xlabel("该类话语的基础出现率 %", fontsize=9.5)
a.set_ylabel("25% 预算存活率 %", fontsize=9.5)
a.text(55, 55, "出现率高不保证存活（条件 87% 出现 → 26% 存活）；\n出现率低也不注定死亡——位置才是主裁判", fontsize=9)
a.set_title("(c) 基率不是命运：位置才是", fontsize=10.5)
a.grid(alpha=0.25, ls="--")

# (d) 判定卡
a = axs[1, 1]
a.axis("off")
rows = [
    ("H1", "not_the_predicted_ordering", "实测死亡顺序与预测不符；极差 0.9664"),
    ("H2", "measured（描述性）", "位置进入模型：β=-0.5225——排序的机制是首现位置"),
    ("H3", "null", "丢失异常话语对下次提交无可检出代价（p=0.059）"),
    ("压缩画像", "保开头 = 保设定、丢收成", "过程/出处/理由幸存；结果/负约束/异常先死"),
    ("设计约束", "15 回合截断", "长度变异极小（p10-p90 均为 15）"),
]
y0 = 0.92
for k, v1, v2 in rows:
    a.text(0.02, y0, k, fontsize=10, weight="bold", color=C_FN, va="top")
    a.text(0.15, y0, v1, fontsize=9.3, weight="bold", va="top", color=C_OPP)
    a.text(0.36, y0, v2, fontsize=8.7, va="top")
    y0 -= 0.185
a.set_title("(d) 判定卡", fontsize=10.5, loc="right")

fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(os.path.join(OUT, "fig2_mechanism.png"), dpi=200)
plt.close(fig)
print("P065 figs done")
