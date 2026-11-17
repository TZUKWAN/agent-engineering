# -*- coding: utf-8 -*-
"""P050 a_cross_task_grammar_of_agent_search — 定制图（非模板）。"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import os

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

OUT = r"G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P050_a_cross_task_grammar_of_agent_search"
os.makedirs(OUT, exist_ok=True)

C_UNI = "#95a5a6"
C_1G  = "#5d8aa8"
C_PB  = "#1a5276"
C_FB  = "#0b3d5c"
C_SH  = "#c0392b"
C_NS  = "#b7950b"

# ============ 图 1：似然阶梯 ============
fig, axs = plt.subplots(2, 2, figsize=(11.5, 8.6))
fig.suptitle("图 1  智能体搜索的跨任务语法：似然阶梯与增益分解（EXP-0198，19,981 条含转移 rollout）",
             fontsize=12.5, y=0.985)

# (a) 似然阶梯
a = axs[0, 0]
labels = ["均匀基线", "unigram", "合并 bigram", "家族 bigram", "shuffle 对照"]
vals = [-2.5649, -1.8362, -1.5043, -1.4238, -1.8615]
cols = [C_UNI, C_1G, C_PB, C_FB, C_SH]
bars = a.bar(labels, vals, width=0.55, color=cols, alpha=0.9)
for b_, v in zip(bars, vals):
    a.text(b_.get_x() + b_.get_width() / 2, v + 0.03, f"{v:.4f}", ha="center", fontsize=9)
a.annotate("Δ=0.7288", xy=(0.5, -2.2), fontsize=9, ha="center", color=C_1G)
a.annotate("Δ=0.3319", xy=(1.5, -1.66), fontsize=9, ha="center", color=C_PB)
a.annotate("Δ=0.0805", xy=(2.5, -1.46), fontsize=9, ha="center", color=C_FB)
a.annotate("比 unigram 还差 0.0253：\n打乱顺序 = 摧毁全部排序增益",
           xy=(4, -1.8615), xytext=(2.7, -2.35), fontsize=8.5,
           arrowprops=dict(arrowstyle="->", lw=1.0, color="#555555"))
a.set_ylim(-2.75, -1.30)
a.set_ylabel("平均对数似然（nats / 转移）", fontsize=9.5)
a.tick_params(axis="x", labelsize=9)
a.set_title("(a) 五级似然阶梯：词频占 64%，顺序占 29%，方言占 7%", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (b) 增益分解
a = axs[0, 1]
sizes = [63.9, 29.1, 7.1]
labs = ["unigram（词频）\n0.7288 nats", "合并排序（bigram）\n0.3319 nats", "家族方言\n0.0805 nats"]
colors = [C_1G, C_PB, C_FB]
w, _ = a.pie(sizes, colors=colors, startangle=90, counterclock=False,
             wedgeprops=dict(width=0.42, edgecolor="white"))
for i, (s, l) in enumerate(zip(sizes, labs)):
    ang = 90 - (sum(sizes[:i]) + s / 2) * 3.6
    x = 1.12 * np.cos(np.radians(ang)); y = 1.12 * np.sin(np.radians(ang))
    a.text(x, y, f"{l}\n{s:.1f}%", ha="center", va="center", fontsize=9)
a.text(0, 0, "总增益\n1.1411 nats\n/转移", ha="center", va="center", fontsize=10, weight="bold")
a.set_title("(b) 从均匀基线到家族 bigram：每转移 1.1411 nats 的来源分解", fontsize=10.5)

# (c) H2 家族方言增益与 partial 带
a = axs[1, 0]
a.axhspan(0, 0.15, color="#f6d55c", alpha=0.25)
a.axhline(0.15, color=C_NS, lw=1.5, ls="--")
a.text(1.02, 0.152, "medium 带 0.15", fontsize=8.5, color=C_NS)
a.errorbar([0], [0.0805], yerr=[[0.0805 - 0.0752], [0.0855 - 0.0805]], fmt="o",
           color=C_FB, capsize=6, lw=1.8, ms=8)
a.errorbar([1], [0.0216], yerr=[[0.0216 - 0.0075], [0.0348 - 0.0216]], fmt="s",
           color=C_PB, capsize=6, lw=1.6, ms=7)
a.scatter([2], [0.0261], marker="^", color=C_1G, s=70)
a.text(0.04, 0.0830, "汇总 β=0.0805\n[0.0752, 0.0855]\np_holm=0.001", fontsize=8.5)
a.text(1.04, 0.0240, "kubernetes-sigs\n0.0216 [0.0075, 0.0348]\n352 rollouts / 30 实例", fontsize=8.5)
a.text(2.04, 0.0270, "google\n0.0261（点估计）\n288 rollouts", fontsize=8.5)
a.set_xticks([0, 1, 2])
a.set_xticklabels(["汇总", "kubernetes-sigs", "google"], fontsize=9.5)
a.set_ylabel("方言增益（nats / 转移）", fontsize=9.5)
a.set_xlim(-0.4, 3.1)
a.set_ylim(0, 0.19)
a.set_title("(c) H2 判 partial：方言增益真实但只到 medium 带的一半", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (d) rollout 长度分布
a = axs[1, 1]
steps = [1, 2, 3, 4, 5, 6, 7, 8]
cnt = [4, 3, 4, 15, 34, 44, 67, 97]
a.bar(steps, cnt, width=0.6, color=C_PB, alpha=0.85)
for s, c in zip(steps, cnt):
    a.text(s, c + 2, str(c), ha="center", fontsize=8.5)
a.axvline(13.66, color=C_SH, lw=1.6, ls="--")
a.text(13.8, 60, "均值 13.66\n（直方仅展示 ≤8；\n长尾延伸至 30+）", fontsize=8.5, color=C_SH)
a.set_xlabel("rollout 内转移步数", fontsize=9.5)
a.set_ylabel("rollout 数", fontsize=9.5)
a.set_title("(d) 长度分布：多数 rollout 有 8 步以上，短 rollout 是小分子层", fontsize=10.5)
a.set_xlim(0, 18)
a.grid(alpha=0.25, axis="y", ls="--")

fig.tight_layout(rect=[0, 0, 1, 0.955])
fig.savefig(os.path.join(OUT, "fig1_ladder.png"), dpi=200)
plt.close(fig)

# ============ 图 2：前提门与异质性 ============
fig, axs = plt.subplots(2, 2, figsize=(11.5, 8.6))
fig.suptitle("图 2  前提门、异质性与 shuffle 对照的解剖（EXP-0198）",
             fontsize=12.5, y=0.985)

# (a) G6 前提门
a = axs[0, 0]
a.bar([0], [805], width=0.4, color="#d5dbdb", alpha=0.9)
a.bar([0], [2], width=0.4, color=C_SH, alpha=0.9)
a.text(0, 760, "805 个组织级任务家族", ha="center", fontsize=10)
a.text(0.24, 30, "仅 2 个达标\n(≥200 rollouts)：\ngoogle 288、\nkubernetes-sigs 352", fontsize=9, color=C_SH)
a.axhline(10, color=C_NS, lw=1.6, ls="--")
a.text(0.2, 16, "冻结地板：≥10 家族", fontsize=9, color=C_NS)
a.set_xticks([])
a.set_ylabel("任务家族数", fontsize=9.5)
a.set_ylim(0, 860)
a.set_title("(a) H1 的前提门：冻结要求 10 个家族，实测 2/805 → not_testable", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (b) 长度带异质性
a = axs[0, 1]
bands = ["1-5 步\n(60 rollouts)", "6-15 步\n(19,921 rollouts)"]
pg = [0.2308, 0.3322]
fg = [0.1327, 0.0803]
x = np.arange(2)
a.bar(x - 0.18, pg, width=0.36, color=C_PB, alpha=0.88, label="合并 bigram 增益")
a.bar(x + 0.18, fg, width=0.36, color=C_FB, alpha=0.88, label="家族方言增益")
for xi, v in zip(x, pg):
    a.text(xi - 0.18, v + 0.006, f"{v:.4f}", ha="center", fontsize=9)
for xi, v in zip(x, fg):
    a.text(xi + 0.18, v + 0.006, f"{v:.4f}", ha="center", fontsize=9)
a.set_xticks(x)
a.set_xticklabels(bands, fontsize=9.5)
a.set_ylabel("增益（nats / 转移）", fontsize=9.5)
a.text(0.0, 0.37, "短 rollout 的方言份额更高\n（0.1327/0.3635=36% vs 0.0803/0.4125=19%），\n但短层只有 60 条——不稳定", fontsize=8.5)
a.set_title("(b) 长度带异质性：方言相对份额在短 rollout 中翻倍", fontsize=10.5)
a.legend(fontsize=9)
a.set_ylim(0, 0.42)
a.grid(alpha=0.25, axis="y", ls="--")

# (c) shuffle 对照解剖
a = axs[1, 0]
a.axhline(0, color="black", lw=1.0)
a.errorbar([0], [0.3319], yerr=[[0.3319 - 0.3223], [0.3410 - 0.3319]], fmt="o",
           color=C_PB, capsize=6, lw=1.8, ms=8)
a.errorbar([1], [-0.0253], yerr=[[-0.0253 - (-0.0342)], [(-0.0161) - (-0.0253)]], fmt="s",
           color=C_SH, capsize=6, lw=1.8, ms=8)
a.annotate("", xy=(1, -0.0253), xytext=(0, 0.3319),
           arrowprops=dict(arrowstyle="<->", lw=1.2, color="#555555", ls="--"))
a.text(0.5, 0.16, "破坏成本 0.3572 nats", ha="center", fontsize=9.5, rotation=0)
a.text(0.04, 0.345, "bigram − unigram\n+0.3319 [0.3223, 0.3410]", fontsize=8.5)
a.text(1.04, -0.045, "shuffle − unigram\n-0.0253 [-0.0342, -0.0161]\n（CI 排除零→特异性规则判 not_specific）", fontsize=8.5)
a.set_xticks([0, 1])
a.set_xticklabels(["真顺序 bigram 的增益", "打乱顺序后的增益"], fontsize=9.5)
a.set_ylabel("相对 unigram 的增益（nats）", fontsize=9.5)
a.set_ylim(-0.09, 0.40)
a.set_title("(c) H3 的对照结构：顺序增益真实，且打乱的伤害也可检出", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (d) 字母表与判定卡
a = axs[1, 1]
a.axis("off")
rows = [
    ("字母表", "13 个命令家族；77 个高频 bigram（≥100 次）通过 G12 支撑地板"),
    ("H1", "not_testable_premise：合并矩阵 +0.3319 nats 优于均匀，但跨任务前提 2/805 未达"),
    ("H2", "partial：方言增益 +0.0805 nats [0.0752, 0.0855]，p_holm=0.001，低于 medium 带"),
    ("H3", "not_specific（机械）：shuffle 对照 CI 排除零；实质上排序信息真实（破坏成本 0.357 nats）"),
    ("结论", "存在共同的命令字母表与部分共享的转移语法；方言层薄而真实；跨任务普适性主张无前提支撑"),
]
y0 = 0.92
for k, v in rows:
    a.text(0.02, y0, k, fontsize=10.5, weight="bold", color=C_FB, va="top")
    a.text(0.16, y0, v, fontsize=9.3, va="top", wrap=True)
    y0 -= 0.17
a.set_title("(d) 判定卡：一行一个冻结判定", fontsize=10.5, loc="right")

fig.tight_layout(rect=[0, 0, 1, 0.955])
fig.savefig(os.path.join(OUT, "fig2_premise.png"), dpi=200)
plt.close(fig)
print("P050 figs done")
