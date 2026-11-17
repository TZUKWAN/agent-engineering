# -*- coding: utf-8 -*-
"""P052 the_recovery_window_after_a_failed_step — 定制图（非模板）。"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import os

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

OUT = r"G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P052_the_recovery_window_after_a_failed_step"
os.makedirs(OUT, exist_ok=True)

C_NULL = "#b7950b"
C_OPP  = "#c0392b"
C_SUP  = "#1a5276"
C_GY   = "#95a5a6"
C_FN   = "#117a65"

# ============ 图 1 ============
fig, axs = plt.subplots(2, 2, figsize=(11.5, 8.6))
fig.suptitle("图 1  失败后的恢复窗口：换命令的速度几乎无变异，速度优势不可检出（EXP-0200，17,229 条含失败 rollout）",
             fontsize=12.5, y=0.985)

# (a) H1 森林
a = axs[0, 0]
a.errorbar([0.4048], [0], xerr=[[0.4048 - (-1.8505)], [2.6601 - 0.4048]],
           fmt="o", color=C_NULL, capsize=7, lw=2, ms=9)
a.axvline(0, color="black", lw=1.0, ls="--")
a.text(-1.8, 0.32, "CI 下界 -1.85", fontsize=9)
a.text(2.0, 0.32, "CI 上界 +2.66", fontsize=9)
a.text(0.4048, -0.32, "β=+0.4048, p=0.725", ha="center", fontsize=10)
a.text(0.4048, 0.55, "换命令几乎人人做到（17,185/17,229），\n对照臂只剩 44 条不换者——\n速度的判别区间宽到没有可用信息",
       ha="center", fontsize=9, color="#555555")
a.set_xlim(-3.0, 3.4)
a.set_ylim(-0.7, 1.0)
a.set_yticks([])
a.set_xlabel("lag-1 换命令对提交的 β（log-odds，实例级聚类）", fontsize=9.5)
a.set_title("(a) H1 判 null：快速换命令的完成优势不可检出", fontsize=10.5)
a.grid(alpha=0.25, axis="x", ls="--")

# (b) 首次换命令的滞后分布
a = axs[0, 1]
lags = ["lag 0", "lag 1", "lag 2", "lag 3", "lag 4"]
cnt = [5, 17185, 35, 3, 1]
a.bar(lags, cnt, width=0.55, color=[C_GY, C_SUP, C_GY, C_GY, C_GY], alpha=0.88)
for i, c in enumerate(cnt):
    a.text(i, c + 300, f"{c:,}", ha="center", fontsize=9.5)
a.text(2.2, 9000, "99.7% 在失败后下一步立即换命令\n——'快慢'这个变量几乎没有方差，\n恢复窗口在 15 步上限下窄到只剩一格",
       fontsize=9, color=C_SUP)
a.set_ylabel("rollout 数", fontsize=9.5)
a.set_xlabel("首次换命令相对失败的滞后步数", fontsize=9.5)
a.set_ylim(0, 19500)
a.set_title("(b) 换命令的速度分布：极端集中于 lag-1", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (c) 各滞后的提交份额
a = axs[1, 0]
lags2 = ["lag 0\n(n=5)", "lag 1\n(n=17,185)", "lag 2\n(n=35)", "lag 3\n(n=3)", "lag 4\n(n=1)"]
sh = [0.0, 2.46, 2.86, 0.0, 0.0]
a.bar(lags2, sh, width=0.55, color=[C_GY, C_SUP, C_GY, C_GY, C_GY], alpha=0.88)
for i, v in enumerate(sh):
    a.text(i, v + 0.07, f"{v:.2f}%", ha="center", fontsize=9.5)
a.text(1.0, 4.4, " lag2 的 2.86% 高于 lag1，但 n=35——\n 原始份额的比较在小分子层无意义，\n 这正是回归控制必须存在的原因",
       fontsize=9, color="#555555")
a.set_ylabel("提交份额 %", fontsize=9.5)
a.set_ylim(0, 5.4)
a.set_title("(c) 原始提交份额：未控制的 lag 比较是陷阱", fontsize=10.5)
a.tick_params(axis="x", labelsize=8.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (d) 每 rollout 失败数分布
a = axs[1, 1]
f = [1, 2, 3, 4, 5, 6, 7, 8]
fc = [3692, 3937, 3921 if False else 3421, 2512, 1635, 973, 537, 308]
a.bar(f, fc, width=0.6, color=C_FN, alpha=0.85)
for x_, c in zip(f, fc):
    a.text(x_, c + 60, f"{c:,}", ha="center", fontsize=8.5)
a.text(5.5, 3200, "失败是常态而非事件：\n均值超过 2 次失败/rollout，\n26% 的 rollout 有 5 次以上", fontsize=9.5)
a.set_xlabel("每 rollout 的失败观察次数", fontsize=9.5)
a.set_ylabel("rollout 数", fontsize=9.5)
a.set_ylim(0, 4600)
a.set_title("(d) 失败的普遍性：恢复问题在每条轨迹上反复发生", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

fig.tight_layout(rect=[0, 0, 1, 0.955])
fig.savefig(os.path.join(OUT, "fig1_recovery.png"), dpi=200)
plt.close(fig)

# ============ 图 2 ============
fig, axs = plt.subplots(2, 2, figsize=(11.5, 8.6))
fig.suptitle("图 2  剂量反应的失败、长度分层的病态与真正起作用的预测元（EXP-0200）",
             fontsize=12.5, y=0.985)

# (a) lag 剂量反应剖面
a = axs[0, 0]
lag_x = [1, 3, 5]
lag_b = [0.4048, -0.6773, -0.3841]
lag_lo = [-1.8505, -1.2346, -0.8733]
lag_hi = [2.6601, -0.12, 0.105]
a.axhline(0, color="black", lw=1.0, ls="--")
a.plot([1, 3, 5], [0, 0, 0], color=C_GY, lw=1.2, ls=":", label="冻结的预期：单调衰减到零")
for i, (x_, b_, lo, hi) in enumerate(zip(lag_x, lag_b, lag_lo, lag_hi)):
    sig = lo > 0 or hi < 0
    a.errorbar(x_, b_, yerr=[[b_ - lo], [hi - b_]], fmt="o",
               color=C_OPP if sig else C_NULL, capsize=6, lw=1.8, ms=9)
    a.text(x_ + 0.12, b_, f"β={b_:+.4f}" + ("\n显著" if sig else "\nCI 含零"),
           fontsize=9, va="center")
a.text(1.15, 1.9, "lag2、lag4 因样本（35 条、1 条）不可估——\n剂量反应曲线在 3 个可估点上断裂", fontsize=9, color="#555555")
a.set_xticks(lag_x)
a.set_xticklabels(["lag 1", "lag 3", "lag 5"], fontsize=10)
a.set_ylabel("换命令对提交的 β", fontsize=9.5)
a.set_ylim(-2.6, 3.3)
a.set_title("(a) H2 判 not_monotone：滞后优势无衰减结构", fontsize=10.5)
a.legend(fontsize=8.5, loc="lower left")
a.grid(alpha=0.25, axis="y", ls="--")

# (b) 长度分层的病态画廊
a = axs[0, 1]
qs = ["q1 最短\n+20.34\n准分离", "q2\n+17.09\nlog_steps 被丢\n无 CI", "q3\n-3.02\nCI [-5.38, -0.67]\n显著为负", "q4 最长\n+17.97\nCI [-64, +100]\n无信息"]
cols = [C_OPP, C_GY, C_SUP, C_GY]
vals = [20.3365, 17.0893, -3.0237, 17.9748]
a.bar(range(4), vals, width=0.55, color=cols, alpha=0.85)
a.axhline(0, color="black", lw=1.0)
a.text(2, -6.5, "唯一可用的一层给出负号——\n与 q1 的 +20 直接矛盾；\n符号复现判据因此不可执行", fontsize=9, ha="center")
for i, v in enumerate(vals):
    a.text(i, v + 0.6 if v > 0 else v - 1.8, f"{v:+.2f}", ha="center", fontsize=9)
a.set_xticks(range(4))
a.set_xticklabels(qs, fontsize=8.5)
a.set_ylabel("lag-1 优势的分层 β", fontsize=9.5)
a.set_ylim(-9, 25)
a.set_title("(b) H3 判 not_estimable：四层里三层病态", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (c) 偏差阶梯
a = axs[1, 0]
mods = ["仅控制项", "+lag1 换命令", "+重复/切换结构"]
dev = [3045.24, 3045.08, 2906.31]
bars = a.bar(mods, dev, width=0.5, color=[C_GY, C_NULL, C_FN], alpha=0.88)
for b_, dv in zip(bars, dev):
    a.text(b_.get_x() + b_.get_width() / 2, dv + 12, f"{dv:,.2f}", ha="center", fontsize=9)
a.annotate("Δ=0.17（p=0.56）\n换命令速度不带增量", xy=(1, 3045.08), xytext=(0.02, 2940),
           fontsize=9, arrowprops=dict(arrowstyle="->", lw=1.0, color="#555555"))
a.annotate("Δ=138.93\nLR χ²(3)=277.87\n重复份额与切换率\n才是提交的预测元", xy=(2, 2906.31),
           xytext=(1.35, 2965), fontsize=9, arrowprops=dict(arrowstyle="->", lw=1.0, color="#555555"))
a.set_ylim(2880, 3095)
a.set_ylabel("实例级聚类准偏差", fontsize=9.5)
a.set_title("(c) 偏差阶梯：速度无增量，行为结构是主驱动", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (d) 判定卡
a = axs[1, 1]
a.axis("off")
rows = [
    ("H1", "null", "β=+0.4048 [-1.85, +2.66]，p=0.725；对照臂仅 44 条"),
    ("H2", "not_monotone", "3 个可估滞后：+0.40 / -0.68* / -0.38，无衰减结构"),
    ("H3", "not_estimable", "长度四分层三层病态、一层负号——符号复现不可执行"),
    ("结构事实", "99.7% 立即换", "恢复窗口实际只有一格：下一步换或不换"),
    ("真正驱动", "repeat/switch", "Δdeviance 138.9 对比速度项的 0.17"),
    ("设计约束", "15 步截断", "log_steps 几乎无变异，长度控制失效"),
]
y0 = 0.95
for k, v1, v2 in rows:
    a.text(0.02, y0, k, fontsize=10, weight="bold", color=C_FN, va="top")
    a.text(0.16, y0, v1, fontsize=9.5, weight="bold", va="top", color=C_OPP)
    a.text(0.34, y0, v2, fontsize=8.8, va="top")
    y0 -= 0.15
a.set_title("(d) 判定卡", fontsize=10.5, loc="right")

fig.tight_layout(rect=[0, 0, 1, 0.955])
fig.savefig(os.path.join(OUT, "fig2_structure.png"), dpi=200)
plt.close(fig)
print("P052 figs done")
