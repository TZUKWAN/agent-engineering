# -*- coding: utf-8 -*-
"""P046 plan_specificity_and_search_quality — 定制图（非模板）。"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import os

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

OUT = r"G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P046_plan_specificity_and_search_quality"
os.makedirs(OUT, exist_ok=True)

C_SUP = "#1a5276"   # supported 方向
C_OPP = "#c0392b"   # opposite
C_NS  = "#b7950b"   # not_specific
C_NS2 = "#7d8a96"   # ns gray
C_GN  = "#1e8449"

# ============ 图 1 ============
fig, axs = plt.subplots(2, 2, figsize=(11.5, 8.6))
fig.suptitle("图 1  开篇特异性与搜索产出：反向主效应与长度分离（EXP-0193，n=14,701 条轨迹）",
             fontsize=12.5, y=0.985)

# (a) 三个假设的森林图
a = axs[0, 0]
hs = [
    ("H1 重复份额", 0.0054, 0.0035, 0.0074, C_OPP),
    ("H2 错误份额", 0.0378, 0.0307, 0.0449, C_OPP),
    ("H3 长度分离", 0.0030, 0.0011, 0.0049, C_NS),
]
for i, (lab, b, lo, hi, c) in enumerate(hs):
    a.errorbar(b, i, xerr=[[b - lo], [hi - b]], fmt="o", color=c,
               capsize=5, lw=1.8, ms=7)
    a.text(hi + 0.0016, i, f"β={b:+.4f}\n[{lo:.4f}, {hi:.4f}]", va="center", fontsize=8.5)
a.axvline(0, color="black", lw=0.9, ls="--")
a.set_yticks(range(3))
a.set_yticklabels([h[0] for h in hs], fontsize=10)
a.set_xlabel("β（对轨迹级聚类稳健，95% CI）", fontsize=9.5)
a.set_title("(a) 三个预注册假设的估计：两项反向、一项无法与长度分离", fontsize=10.5)
a.set_xlim(-0.006, 0.062)
a.grid(alpha=0.25, axis="x", ls="--")

# (b) 特异性四分位的原始产出
a = axs[0, 1]
qs = ["s1\n最不特异", "s2", "s3", "s4\n最特异"]
rep = [11.67, 4.46, 2.60, 2.72]
err = [59.57, 59.35, 62.43, 51.85]
cln = [35.58, 29.69, 24.95, 26.78]
x = np.arange(4)
a.plot(x, rep, "o-", color=C_OPP, lw=2, ms=6, label="重复份额 %")
a.plot(x, err, "s-", color=C_NS, lw=2, ms=6, label="错误观察份额 %")
a.plot(x, cln, "^-", color=C_SUP, lw=2, ms=6, label="终末干净观察份额 %")
for xi, yi in zip(x, rep):
    a.annotate(f"{yi:.1f}", (xi, yi), textcoords="offset points", xytext=(0, 7),
               ha="center", fontsize=8.5, color=C_OPP)
for xi, yi in zip(x, err):
    a.annotate(f"{yi:.1f}", (xi, yi), textcoords="offset points", xytext=(0, 7),
               ha="center", fontsize=8.5, color="#8a6d00")
for xi, yi in zip(x, cln):
    a.annotate(f"{yi:.1f}", (xi, yi), textcoords="offset points", xytext=(0, -13),
               ha="center", fontsize=8.5, color=C_SUP)
a.set_xticks(x)
a.set_xticklabels(qs, fontsize=9.5)
a.set_ylabel("轨迹内份额（%）", fontsize=9.5)
a.set_title("(b) 特异性四分位的产出：重复骤降后走平，终末干净份额反而下行", fontsize=10.5)
a.legend(fontsize=8.5, loc="center right")
a.set_ylim(0, 78)
a.grid(alpha=0.25, ls="--")

# (c) 符号翻转：长度 vs 特异性
a = axs[1, 0]
labels = ["仅长度模型\nfirst_chars_log", "长度+特异性模型\nspec_sum_z"]
bets = [-0.0085, 0.0054]
los = [-0.0100, 0.0035]
his = [-0.0071, 0.0074]
cols = [C_SUP, C_OPP]
xx = np.arange(2)
for i in range(2):
    a.bar(xx[i], bets[i], width=0.45, color=cols[i], alpha=0.85)
    a.errorbar(xx[i], bets[i], yerr=[[bets[i] - los[i]], [his[i] - bets[i]]],
               fmt="none", ecolor="#333333", capsize=6, lw=1.5)
a.axhline(0, color="black", lw=1.0)
a.text(0, -0.0118, "β=-0.0085\n[-0.0100, -0.0071]\n开篇更长 → 重复更少", ha="center", fontsize=8.5)
a.text(1, 0.0098, "β=+0.0054\n[+0.0035, +0.0074]\n固定长度后更特异 → 重复更多", ha="center", fontsize=8.5)
a.set_xticks(xx)
a.set_xticklabels(labels, fontsize=9.5)
a.set_ylabel("对 repeat_share 的 β", fontsize=9.5)
a.set_title("(c) 同一因变量的符号翻转：边际上长度保护，条件于长度后特异性有害", fontsize=10.5)
a.set_ylim(-0.014, 0.014)
a.grid(alpha=0.25, axis="y", ls="--")

# (d) 模型比较：似然比 vs 聚类稳健推断
a = axs[1, 1]
mods = ["仅控制项", "+特异性复合", "仅长度"]
dev = [165.64, 164.15, 164.34]
bars = a.bar(mods, dev, width=0.5, color=["#95a5a6", C_OPP, C_SUP], alpha=0.85)
for b_, dv in zip(bars, dev):
    a.text(b_.get_x() + b_.get_width() / 2, dv + 0.05, f"{dv:.2f}",
           ha="center", fontsize=9.5)
a.set_ylim(163.0, 166.4)
a.set_ylabel("轨迹级聚类的准偏差", fontsize=9.5)
a.annotate("加入特异性：Δdeviance=1.49\n似然比 χ²(2)=2.98, p=0.225（不显著）\n但聚类稳健 CI 排除零（p<0.001）",
           xy=(1, 164.15), xytext=(0.02, 163.25), fontsize=8.5,
           arrowprops=dict(arrowstyle="->", lw=1.0, color="#555555"))
a.annotate("加入长度：Δdeviance=1.30\n似然比 χ²(1)=2.60, p=0.107",
           xy=(2, 164.34), xytext=(1.55, 165.6), fontsize=8.5,
           arrowprops=dict(arrowstyle="->", lw=1.0, color="#555555"))
a.set_title("(d) 两种推断口径的分裂：精确估计的微弱效应", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

fig.tight_layout(rect=[0, 0, 1, 0.955])
fig.savefig(os.path.join(OUT, "fig1_main.png"), dpi=200)
plt.close(fig)

# ============ 图 2：异质性 ============
fig, axs = plt.subplots(2, 2, figsize=(11.5, 8.6))
fig.suptitle("图 2  汇总反向效应的解剖：它由长轨迹驱动、并随任务类别变号（EXP-0193）",
             fontsize=12.5, y=0.985)

# (a) 类别分层的 H1 森林
a = axs[0, 0]
cats = [
    ("Agent Tools", 0.0030, -0.0024, 0.0083, "#95a5a6"),
    ("Browser Automation", -0.0262, -0.1620, 0.1096, "#95a5a6"),
    ("File Operations", 0.0022, 0.0006, 0.0037, C_OPP),
    ("Multi-Tool", 0.0147, -0.0030, 0.0324, "#95a5a6"),
    ("Repository Tasks", 0.0035, -0.0207, 0.0276, "#95a5a6"),
    ("Scheduling", -0.0104, -0.0530, 0.0322, "#95a5a6"),
    ("Terminal & Coding", -0.0053, -0.0077, -0.0029, C_GN),
]
for i, (lab, b, lo, hi, c) in enumerate(cats):
    a.errorbar(b, i, xerr=[[b - lo], [hi - b]], fmt="o", color=c, capsize=4, lw=1.6, ms=6)
a.axvline(0, color="black", lw=0.9, ls="--")
a.set_yticks(range(len(cats)))
a.set_yticklabels([c[0] for c in cats], fontsize=9)
a.invert_yaxis()
a.set_xlabel("β（repeat_share，按类别分层）", fontsize=9.5)
a.text(0.038, 2.0, "文件操作：+\np<0.01", fontsize=8, color=C_OPP)
a.text(0.038, 6.0, "终端与编码：−\np<0.001", fontsize=8, color=C_GN)
a.set_title("(a) 类别分层：效应在类别间变号，其余类别不可区分于零", fontsize=10.5)
a.set_xlim(-0.19, 0.13)
a.grid(alpha=0.25, axis="x", ls="--")

# (b) 轨迹长度分层的单调梯度
a = axs[0, 1]
ql = ["q1 最短", "q2", "q3", "q4 最长"]
qb = [0.0012, 0.0128, 0.0166, 0.0231]
qlo = [-0.0005, 0.0079, 0.0077, 0.0112]
qhi = [0.0028, 0.0177, 0.0256, 0.0351]
x = np.arange(4)
for i in range(4):
    sig = qlo[i] > 0
    a.bar(x[i], qb[i], width=0.5, color=C_OPP if sig else "#b3bcc5", alpha=0.88)
    a.errorbar(x[i], qb[i], yerr=[[qb[i] - qlo[i]], [qhi[i] - qb[i]]],
               fmt="none", ecolor="#333333", capsize=5, lw=1.4)
    a.text(x[i], qhi[i] + 0.0012, f"{qb[i]:.4f}" + ("*" if sig else ""),
           ha="center", fontsize=9)
a.axhline(0, color="black", lw=0.9)
a.set_xticks(x)
a.set_xticklabels(ql, fontsize=9.5)
a.set_ylabel("β（repeat_share）", fontsize=9.5)
a.text(0.02, 0.021, "* = CI 排除零\n汇总效应随轨迹长度单调走强，\n最短四分位中完全消失",
       fontsize=8.5, color="#555555")
a.set_title("(b) 长度分层：反向效应是长轨迹的产物", fontsize=10.5)
a.set_ylim(-0.002, 0.042)
a.grid(alpha=0.25, axis="y", ls="--")

# (c) 特异性四个成分：均值 vs 中位数
a = axs[1, 0]
parts = ["实体数\nentities", "动作动词\naction_verbs", "顺序标记\nordering", "约束短语\nconstraints"]
mean_v = [25.976, 2.068, 2.546, 0.259]
med_v = [10.0, 2.0, 3.0, 0.0]
x = np.arange(4)
a.bar(x - 0.18, mean_v, width=0.36, color=C_SUP, alpha=0.85, label="均值")
a.bar(x + 0.18, med_v, width=0.36, color=C_NS, alpha=0.85, label="中位数")
for i in range(4):
    a.text(x[i] - 0.18, mean_v[i] + 0.4, f"{mean_v[i]:.2f}", ha="center", fontsize=8.5)
    a.text(x[i] + 0.18, med_v[i] + 0.4, f"{med_v[i]:.1f}", ha="center", fontsize=8.5)
a.text(3, 4.2, "约束短语中位数=0：\n过半开篇完全不含约束词", fontsize=8.5, color="#7d6608")
a.set_xticks(x)
a.set_xticklabels(parts, fontsize=9)
a.set_ylabel("首回合计数值", fontsize=9.5)
a.set_title("(c) 特异性的成分解剖：重尾的实体枚举主导复合分数", fontsize=10.5)
a.legend(fontsize=9)
a.set_ylim(0, 29)
a.grid(alpha=0.25, axis="y", ls="--")

# (d) 类别层面的错误率 × 重复率散点
a = axs[1, 1]
cat_pts = [
    ("Agent Tools", 4.35, 59.50, 4249),
    ("Browser Auto.", 25.16, 30.44, 1687),
    ("File Operations", 0.36, 32.62, 891),
    ("Multi-Tool", 2.07, 54.47, 859),
    ("Planning & Org.", 0.78, 36.58, 293),
    ("Repository Tasks", 2.95, 83.87, 2131),
    ("Scheduling", 1.24, 65.40, 308),
    ("Terminal & Coding", 2.11, 62.72, 4247),
]
for lab, rp, ep, n in cat_pts:
    a.scatter(rp, ep, s=n / 12, color=C_SUP, alpha=0.65, edgecolor="white", lw=1.2)
offs = {
    "Agent Tools": (6, 4), "Browser Auto.": (6, -2), "File Operations": (6, 4),
    "Multi-Tool": (6, 4), "Planning & Org.": (6, 4), "Repository Tasks": (-74, 4),
    "Scheduling": (6, -10), "Terminal & Coding": (-104, -4),
}
for lab, rp, ep, n in cat_pts:
    dx, dy = offs[lab]
    a.annotate(f"{lab}\n(n={n:,})", (rp, ep), textcoords="offset points",
               xytext=(dx, dy), fontsize=7.8)
a.set_xlabel("平均重复份额（%）", fontsize=9.5)
a.set_ylabel("平均错误观察份额（%）", fontsize=9.5)
a.set_xlim(-2, 34)
a.set_ylim(22, 95)
a.text(15, 82, "浏览器自动化：高重复、低错误（交互式试错环境）\n仓库任务：低重复、最高错误（83.9%）——\n重复与错误由工具环境分别决定，不共享一个'质量'轴",
       fontsize=8.2, color="#555555")
a.set_title("(d) 类别定位：两个'负面产出'在类别平面上几乎正交", fontsize=10.5)
a.grid(alpha=0.25, ls="--")

fig.tight_layout(rect=[0, 0, 1, 0.955])
fig.savefig(os.path.join(OUT, "fig2_heterogeneity.png"), dpi=200)
plt.close(fig)
print("P046 figs done")
