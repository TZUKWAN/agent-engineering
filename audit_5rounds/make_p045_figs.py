# -*- coding: utf-8 -*-
"""P045 primacy lock-in — 补做定制图。"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import os

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

OUT = r"G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P045_primacy_lock_in_and_later_search"
C_SUP = "#1a5276"; C_OPP = "#c0392b"; C_NS = "#b7950b"; C_GY = "#95a5a6"; C_FN = "#117a65"

fig, axs = plt.subplots(2, 2, figsize=(11.5, 8.8))
fig.suptitle("图 1  首因锁定：开篇假设的引力随回合衰减、且锁定的是假设而非泛泛开篇（EXP-0192）",
             fontsize=12.5, y=0.985)

# (a) H1 森林
a = axs[0, 0]
a.errorbar([-0.6391], [0], xerr=[[-0.6391 - (-0.7386)], [(-0.5397) - (-0.6391)]], fmt="o",
           color=C_OPP, capsize=7, lw=2, ms=10)
a.axvline(0, color="black", lw=1.0, ls="--")
a.text(-0.6391, 0.3, "回合位置 → 与自身早期假设的重合\nβ=-0.6391 [-0.7386, -0.5397]\np_holm<0.001 → supported\nn=3,764 回合（515 条轨迹）", ha="center", fontsize=9)
a.text(-0.6391, -0.32, "轨迹越往后，行为与开篇假设的重合越低——\n引力在衰减，但全程未归零（均值 0.556）", ha="center", fontsize=9)
a.set_xlim(-0.85, -0.42); a.set_ylim(-0.55, 0.55); a.set_yticks([])
a.set_xlabel("β（traj_id 聚类）", fontsize=9.5)
a.set_title("(a) H1 判 supported：位置每推一步，重合下滑", fontsize=10.5)
a.grid(alpha=0.25, axis="x", ls="--")

# (b) H2 null
a = axs[0, 1]
a.bar([0, 1], [52.02, 54.23], width=0.42, color=[C_GY, C_NS], alpha=0.88)
a.errorbar([0], [52.02], yerr=[[0.8], [0.8]], fmt="none", ecolor="#333333", capsize=5, lw=1.4)
a.errorbar([1], [54.23], yerr=[[0.8], [0.8]], fmt="none", ecolor="#333333", capsize=5, lw=1.4)
a.text(0, 53.4, "52.0%", ha="center", fontsize=10.5)
a.text(1, 55.4, "54.2%", ha="center", fontsize=10.5)
a.text(0.5, 58.5, "有早期假设 vs 无：后续新词份额差 2.2 个百分点\nβ=+0.0241 [-0.0069, +0.0552]，p=0.128 → null\n锁定不关闭探索的大门", ha="center", fontsize=9.5)
a.set_xticks([0, 1]); a.set_xticklabels(["无早期假设 (n=14,131)", "有早期假设 (n=570)"], fontsize=9.5)
a.set_ylabel("后续观察的平均新词份额 %", fontsize=9.5); a.set_ylim(48, 61)
a.set_title("(b) H2 判 null：锁定 ≠ 停止探索", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (c) H3 own vs alien
a = axs[1, 0]
a.errorbar([0.2376], [0], xerr=[[0.2376 - 0.1905], [0.2846 - 0.2376]], fmt="o",
           color=C_SUP, capsize=7, lw=2, ms=10)
a.errorbar([-0.2774], [1], xerr=[[-0.2774 - (-0.3239)], [(-0.231) - (-0.2774)]], fmt="s",
           color=C_OPP, capsize=7, lw=2, ms=10)
a.axvline(0, color="black", lw=1.0, ls="--")
a.text(0.2376, 0.32, "自身早期假设锚\nβ=+0.2376 [0.1905, 0.2846]", ha="center", fontsize=9)
a.text(-0.2774, 1.32, "外星锚（同长度他源开篇）\nβ=-0.2774 [-0.3239, -0.2310]", ha="center", fontsize=9)
a.text(0.0, 2.0, "符号相反：与自身假设的重合随位置下降得更慢、\n与外星开篇的下降得更快——锁定的对象是假设内容，\n不是'开篇都长那样'的词面惯性", ha="center", fontsize=9)
a.set_yticks([0, 1]); a.set_yticklabels(["自身假设锚", "外星开篇锚"], fontsize=9.5)
a.invert_yaxis(); a.set_xlim(-0.42, 0.42)
a.set_xlabel("位置对重合的 β（对照模型，n=4,595）", fontsize=9.5)
a.set_title("(c) H3：锁定的是内容，不是文体", fontsize=10.5)
a.grid(alpha=0.25, axis="x", ls="--")

# (d) 偏差阶梯
a = axs[1, 1]
mods = ["仅控制项", "+位置", "+外星锚"]
dev = [3271.05, 3186.53, 351.64]
bars = a.bar(mods, dev, width=0.5, color=[C_GY, C_NS, C_SUP], alpha=0.88)
for b_, dv in zip(bars, dev):
    a.text(b_.get_x() + b_.get_width() / 2, dv + 60, f"{dv:,.1f}", ha="center", fontsize=9)
a.annotate("Δ=84.5（位置）", xy=(1, 3186.5), xytext=(0.02, 800), fontsize=9,
           arrowprops=dict(arrowstyle="->", lw=1.0, color="#555555"))
a.annotate("Δ=2,919（外星锚！）\n外星锚才是重合的主解释变量", xy=(2, 351.6), xytext=(1.0, 1400),
           fontsize=9.5, arrowprops=dict(arrowstyle="->", lw=1.1, color=C_SUP))
a.set_ylim(0, 3700)
a.set_ylabel("traj_id 聚类准偏差", fontsize=9.5)
a.set_title("(d) 偏差阶梯：重合的主引擎是词面惯性", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(os.path.join(OUT, "fig1_lockin.png"), dpi=200)
plt.close(fig)

# ============ 图 2 ============
fig, axs = plt.subplots(2, 2, figsize=(11.5, 8.8))
fig.suptitle("图 2  锁定的解剖：三分位对照、类别差异、长度分层与判定（EXP-0192）", fontsize=12.5, y=0.985)

# (a) 三分位 hypo vs alien
a = axs[0, 0]
thirds = ["前 1/3", "中 1/3", "后 1/3"]
hypo = [52.85, 60.05, 53.36]
alien = [44.22, 54.67, 48.74]
x = np.arange(3)
a.plot(x, hypo, "o-", color=C_SUP, lw=2, ms=7, label="与自身早期假设的重合")
a.plot(x, alien, "s--", color=C_OPP, lw=2, ms=7, label="与外星开篇的重合")
for xi, v in zip(x, hypo):
    a.annotate(f"{v:.1f}", (xi, v), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=9, color=C_SUP)
for xi, v in zip(x, alien):
    a.annotate(f"{v:.1f}", (xi, v), textcoords="offset points", xytext=(0, -14), ha="center", fontsize=9, color=C_OPP)
a.set_xticks(x); a.set_xticklabels(thirds, fontsize=10)
a.set_ylabel("内容词重合 %", fontsize=9.5); a.set_ylim(38, 66)
a.text(1.0, 41.5, "两条曲线在三分位上同步起伏（中段同峰）——\n重合的主要波动由共享的词面惯性驱动；\n自身假设始终高出外星锚 5-9 个百分点", fontsize=9, ha="center")
a.set_title("(a) 三分位：双曲线同构、假设恒在上", fontsize=10.5)
a.legend(fontsize=9, loc="upper right")
a.grid(alpha=0.25, ls="--")

# (b) 类别差异
a = axs[1, 0]
cats = [("Agent Tools", 67.26, 1341), ("Terminal & Coding", 60.98, 704),
        ("File Operations", 47.99, 189), ("Repository Tasks", 46.45, 719),
        ("Planning & Org.", 46.00, 158), ("Scheduling", 45.08, 157),
        ("Browser Automation", 40.64, 151), ("Multi-Tool", 38.64, 344)]
cats.sort(key=lambda c: -c[1])
y = np.arange(len(cats))
a.barh(y, [c[1] for c in cats], color=[C_SUP if c[1] > 55 else C_GY for c in cats], alpha=0.88)
for i, (lab, v, n) in enumerate(cats):
    a.text(v + 0.6, i, f"{v:.1f}% (n={n:,})", va="center", fontsize=8.5)
a.set_yticks(y); a.set_yticklabels([c[0] for c in cats], fontsize=9)
a.invert_yaxis()
a.set_xlabel("与自身早期假设的平均重合", fontsize=9.5)
a.set_xlim(30, 80)
a.text(58, 6.8, "智能体工具类锁定最强（67.3%）、\n多工具最弱（38.6%）——\n单工具任务的开篇假设更有粘性", fontsize=9)
a.set_title("(b) 类别：单工具任务的假设更粘", fontsize=10.5)
a.grid(alpha=0.25, axis="x", ls="--")

# (c) 长度四分位分层
a = axs[1, 1]
qs = ["q1 最短", "q2", "q3", "q4 最长"]
bs = [-1.1495, -0.38, -0.4492, -0.5487]
x = np.arange(4)
a.bar(x, bs, width=0.5, color=C_OPP, alpha=0.85)
for xi, v in zip(x, bs):
    a.text(xi, v - 0.09, f"{v:.3f}", ha="center", fontsize=9.5)
a.axhline(0, color="black", lw=0.9)
a.text(1.5, 0.15, "最短四分位衰减最陡（-1.15）：\n短轨迹里位置每推一步，假设影响力损失更大；\n长轨迹的衰减平缓——引力被拉长", fontsize=9)
a.set_xticks(x); a.set_xticklabels(qs, fontsize=10)
a.set_ylabel("位置对假设重合的 β（分层）", fontsize=9.5)
a.set_ylim(-1.35, 0.35)
a.set_title("(c) 长度分层：短轨迹的引力衰减最急", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (d) 判定卡
a = axs[1, 1]; a.axis("off")
rows = [
    ("H1", "supported", "位置→重合 β=-0.6391；锁定在衰减"),
    ("H2", "null", "锁定不改变探索新词率（+2.2pp, ns）"),
    ("H3", "supported", "自身锚 +0.24 vs 外星锚 -0.28：内容锁定"),
    ("主引擎", "外星锚 Δ=2,919", "重合的大头是词面惯性；假设只贡献增量"),
    ("样本", "515 轨迹 / 3,764 回合", "稀有构念（有显式早期假设的 570 条中 515 可用）"),
]
y0 = 0.92
for k, v1, v2 in rows:
    a.text(0.02, y0, k, fontsize=10, weight="bold", color=C_FN, va="top")
    a.text(0.15, y0, v1, fontsize=9.3, weight="bold", va="top", color=C_OPP)
    a.text(0.35, y0, v2, fontsize=8.7, va="top")
    y0 -= 0.185
a.set_title("(d) 判定卡", fontsize=10.5, loc="right")

fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(os.path.join(OUT, "fig2_lockin.png"), dpi=200)
plt.close(fig)
print("P045 figs done")
