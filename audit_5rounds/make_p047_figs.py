# -*- coding: utf-8 -*-
"""P047 verbal_versus_behavioural_correction — 定制图（非模板）。"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import os

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

OUT = r"G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P047_verbal_versus_behavioural_correction"
os.makedirs(OUT, exist_ok=True)

C_OPP = "#c0392b"
C_SUP = "#1a5276"
C_NS  = "#b7950b"
C_GY  = "#95a5a6"
C_GN  = "#1e8449"

# ============ 图 1 ============
fig, axs = plt.subplots(2, 2, figsize=(11.5, 8.6))
fig.suptitle("图 1  口头纠正与行为变化：承认几乎总伴随换调用，但对换调用没有正向判别力（EXP-0194）",
             fontsize=12.5, y=0.985)

# (a) H1 森林：口头纠正 vs 位置
a = axs[0, 0]
items = [
    ("口头纠正 spoke_correction", -0.7342, -1.3415, -0.1269, C_OPP),
    ("轨迹内位置 position", 2.0414, 1.6021, 2.4808, C_SUP),
]
for i, (lab, b, lo, hi, c) in enumerate(items):
    a.errorbar(b, i, xerr=[[b - lo], [hi - b]], fmt="o", color=c, capsize=5, lw=1.8, ms=7)
    a.text(hi + 0.12, i, f"β={b:+.4f}\n[{lo:.4f}, {hi:.4f}]", va="center", fontsize=8.5)
a.axvline(0, color="black", lw=0.9, ls="--")
a.set_yticks(range(2))
a.set_yticklabels([i[0] for i in items], fontsize=9.5)
a.set_xlabel("β（log-odds，轨迹级聚类，n=77,963 回合）", fontsize=9.5)
a.set_title("(a) H1 判 opposite：承认对换调用是负向判别项，位置才是正向主驱动", fontsize=10.5)
a.set_xlim(-1.9, 3.6)
a.grid(alpha=0.25, axis="x", ls="--")

# (b) 仪式率 vs 冻结地板
a = axs[0, 1]
a.bar([0], [1.55], width=0.38, color=C_SUP, alpha=0.88)
a.errorbar([0], [1.55], yerr=[[1.55 - 0.74], [2.47 - 1.55]], fmt="none",
           ecolor="#333333", capsize=6, lw=1.5)
a.axhline(20.0, color=C_OPP, lw=1.8, ls="--")
a.text(0.22, 20.6, "冻结地板 20%", fontsize=9.5, color=C_OPP)
a.annotate("测得 1.55%\n[0.74%, 2.47%]\n仅地板的 1/13", xy=(0, 1.55), xytext=(0.16, 9.5),
           fontsize=9, arrowprops=dict(arrowstyle="->", lw=1.0, color="#555555"))
a.set_xticks([0])
a.set_xticklabels(["承认且无行为变化\n（空口仪式）"], fontsize=9.5)
a.set_ylabel("口头纠正中的份额（%）", fontsize=9.5)
a.set_title("(b) H2 判 not_at_floor：'说了不改'的仪式率远低于 20% 地板（n=906 例纠正）", fontsize=10.5)
a.set_ylim(0, 24)
a.grid(alpha=0.25, axis="y", ls="--")

# (c) 偏差阶梯
a = axs[1, 0]
mods = ["仅控制项", "+位置", "+承认"]
dev = [11718.68, 11456.23, 11450.83]
bars = a.bar(mods, dev, width=0.5, color=[C_GY, C_SUP, C_OPP], alpha=0.88)
for b_, dv in zip(bars, dev):
    a.text(b_.get_x() + b_.get_width() / 2, dv + 6, f"{dv:,.2f}", ha="center", fontsize=9)
a.set_ylim(11400, 11760)
a.annotate("加入位置：Δ=262.45\nLR χ²(1)=524.9, p<0.001", xy=(1, 11456.2), xytext=(0.02, 11425),
           fontsize=8.5, arrowprops=dict(arrowstyle="->", lw=1.0, color="#555555"))
a.annotate("再加承认：总 Δ=267.84\n增量仅 5.40", xy=(2, 11450.8), xytext=(1.42, 11560),
           fontsize=8.5, arrowprops=dict(arrowstyle="->", lw=1.0, color="#555555"))
a.set_ylabel("轨迹级聚类准偏差", fontsize=9.5)
a.set_title("(c) 偏差阶梯：承认的增量贡献只有位置的 1/50", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (d) 纠正的时点分布与伴随变化率
a = axs[1, 1]
thirds = ["前 1/3", "中 1/3", "后 1/3"]
share = [0.40, 0.76, 0.87]
chrate = [100.0, 98.5, 98.01]
x = np.arange(3)
b1 = a.bar(x - 0.18, share, width=0.36, color=C_SUP, alpha=0.85, label="纠正发生率 %")
for xi, yi in zip(x, share):
    a.text(xi - 0.18, yi + 2, f"{yi:.2f}", ha="center", fontsize=9, color=C_SUP)
b2 = a.bar(x + 0.18, chrate, width=0.36, color=C_NS, alpha=0.85, label="纠正伴随变化率 %")
for xi, yi in zip(x, chrate):
    a.text(xi + 0.18, yi + 2, f"{yi:.1f}", ha="center", fontsize=9, color="#8a6d00")
a.axhline(100, color="black", lw=0.8, ls=":")
a.set_xticks(x)
a.set_xticklabels(thirds, fontsize=10)
a.set_ylabel("百分比", fontsize=9.5)
a.set_title("(d) 纠正随轨迹推进变密（0.40%→0.87%），且 98% 以上伴随调用变化", fontsize=10.5)
a.legend(fontsize=9, loc="upper left")
a.set_ylim(0, 118)
a.grid(alpha=0.25, axis="y", ls="--")

fig.tight_layout(rect=[0, 0, 1, 0.955])
fig.savefig(os.path.join(OUT, "fig1_correction_vs_change.png"), dpi=200)
plt.close(fig)

# ============ 图 2 ============
fig, axs = plt.subplots(2, 2, figsize=(11.5, 8.6))
fig.suptitle("图 2  承认仪表与错误仪表的解剖：不对称的失败记录与分层的病态尺度（EXP-0194）",
             fontsize=12.5, y=0.985)

# (a) 906 例承认的前置错误构成
a = axs[0, 0]
a.barh([0], [633], color=C_SUP, alpha=0.85, height=0.42, label="有前置错误标记（633 例）")
a.barh([0], [273], left=[633], color=C_NS, alpha=0.85, height=0.42, label="无前置错误标记（273 例）")
a.text(300, 0, "633（69.9%）", va="center", ha="center", fontsize=10, color="white", weight="bold")
a.text(633 + 136, 0, "273（30.1%）", va="center", ha="center", fontsize=9.5, color="white", weight="bold")
a.set_yticks([0])
a.set_yticklabels(["906 例口头纠正"], fontsize=10)
a.set_xlabel("例数", fontsize=9.5)
a.text(633, 0.34, "承认多发生在机器可见错误之后，\n但三成承认找不到任何机器可见的前置错误——\n'承认'不是'错误'的简单读出",
       fontsize=8.5, ha="left")
a.set_xlim(0, 1000)
a.set_ylim(-0.55, 0.75)
a.set_title("(a) 承认的错误前置构成：三成承认'无错认错'", fontsize=10.5)
a.legend(fontsize=8.5, loc="lower right")
a.grid(alpha=0.25, axis="x", ls="--")

# (b) Kappa vs 可分阈值
a = axs[0, 1]
a.bar([0], [0.0018], width=0.3, color=C_SUP, alpha=0.88)
a.errorbar([0], [0.0018], yerr=[[0.0018 - 0.0009], [0.0026 - 0.0018]], fmt="none",
           ecolor="#333333", capsize=6, lw=1.5)
a.axhline(0.50, color=C_OPP, lw=1.8, ls="--")
a.text(0.16, 0.505, "冻结可分性阈值 κ=0.50", fontsize=9.5, color=C_OPP)
a.annotate("κ=0.0018\n[0.0009, 0.0026]\n两仪表几乎零重合", xy=(0, 0.0018), xytext=(0.1, 0.22),
           fontsize=9, arrowprops=dict(arrowstyle="->", lw=1.0, color="#555555"))
a.set_xticks([0])
a.set_xticklabels(["承认标记 × 前置错误标记"], fontsize=9.5)
a.set_ylabel("Cohen's κ", fontsize=9.5)
a.set_title("(b) H3 判可分：承认仪表与错误仪表不能互相读出（n=125,712 回合）", fontsize=10.5)
a.set_ylim(0, 0.58)
a.grid(alpha=0.25, axis="y", ls="--")

# (c) 类别分层森林（标注准分离）
a = axs[1, 0]
cats = [
    ("Agent Tools", -2.5574, -3.3933, -1.7216, C_SUP, ""),
    ("Browser Automation", 17.6897, 16.9715, 18.4079, C_OPP, "准分离"),
    ("Multi-Tool", -1.7237, -3.1451, -0.3022, C_SUP, ""),
    ("Repository Tasks", -0.5142, -2.4414, 1.4129, C_GY, ""),
    ("Scheduling", 16.5279, 14.8918, 18.1640, C_OPP, "准分离"),
    ("Terminal & Coding", 1.4673, -0.5265, 3.4610, C_GY, ""),
]
for i, (lab, b, lo, hi, c, flag) in enumerate(cats):
    a.errorbar(b, i, xerr=[[b - lo], [hi - b]], fmt="o", color=c, capsize=4, lw=1.6, ms=6)
    if flag:
        a.text(hi + 0.9, i, "病态尺度：" + flag, fontsize=8, color=C_OPP)
a.axvline(0, color="black", lw=0.9, ls="--")
a.set_yticks(range(len(cats)))
a.set_yticklabels([c[0] for c in cats], fontsize=9)
a.invert_yaxis()
a.set_xlabel("β（分层重拟合，log-odds）", fontsize=9.5)
a.set_title("(c) 类别分层：两类准完全分离致系数膨胀，只可读方向不可读幅度", fontsize=10.5)
a.set_xlim(-6, 25)
a.grid(alpha=0.25, axis="x", ls="--")

# (d) 位置分层 + 重复份额对照
a = axs[1, 1]
pos = [("first_third", 20.0603, 19.7198, 20.4007), ("middle_third", -0.5023, -1.5122, 0.5075),
       ("last_third", -1.1424, -1.8448, -0.44)]
xp = np.arange(3)
for i, (lab, b, lo, hi) in enumerate(pos):
    flag = b > 10
    a.bar(xp[i], b, width=0.45, color=C_OPP if flag else (C_SUP if lo > 0 or hi < 0 else C_GY), alpha=0.85)
    a.errorbar(xp[i], b, yerr=[[b - lo], [hi - b]], fmt="none", ecolor="#333333", capsize=5, lw=1.4)
a.text(0, 20.9, "准分离", ha="center", fontsize=9, color=C_OPP)
a.text(2, -2.6, "CI 排除零\nβ=-1.14", ha="center", fontsize=8.5, color=C_SUP)
a.axhline(0, color="black", lw=0.9)
a.set_xticks(xp)
a.set_xticklabels(["前 1/3", "中 1/3", "后 1/3"], fontsize=10)
a.set_ylabel("β（分层重拟合）", fontsize=9.5)
a.set_title("(d) 位置分层：前段准分离，后段承认的负判别显著", fontsize=10.5)
a.set_ylim(-4.5, 23)
a.grid(alpha=0.25, axis="y", ls="--")

fig.tight_layout(rect=[0, 0, 1, 0.955])
fig.savefig(os.path.join(OUT, "fig2_instruments.png"), dpi=200)
plt.close(fig)
print("P047 figs done")
