# -*- coding: utf-8 -*-
"""P056 the_implicit_information_need — 定制图（非模板）。"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import os

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

OUT = r"G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P056_the_implicit_information_need"
os.makedirs(OUT, exist_ok=True)

C_SUP = "#1a5276"
C_OPP = "#c0392b"
C_NS  = "#b7950b"
C_GY  = "#95a5a6"
C_FN  = "#117a65"
C_GI  = "#6c3483"

# ============ 图 1 ============
fig, axs = plt.subplots(2, 2, figsize=(11.5, 8.6))
fig.suptitle("图 1  隐含信息需求的覆盖：67% 的宽读覆盖、微弱的欠明确性效应、被候选池规模主导的梯度（EXP-0204）",
             fontsize=12.5, y=0.985)

# (a) H1 森林
a = axs[0, 0]
a.axhspan(0, 0.15, color="#f6d55c", alpha=0.0)
a.errorbar([-0.0141], [0], xerr=[[0.0141 - (-0.0266)], [(-0.0015) - (-0.0141)]],
           fmt="o", color=C_NS, capsize=6, lw=1.8, ms=9)
a.axvline(0, color="black", lw=1.0, ls="--")
a.text(-0.0141, 0.3, "β=-0.0141 [-0.0266, -0.0015]\np_holm=0.0285\n方向与预测一致，量级不足 medium 带 → partial",
       ha="center", fontsize=9)
a.text(0.0, -0.35, "每 1 SD 欠明确性只损失 1.4 个百分点的覆盖", ha="center", fontsize=9.5, color=C_NS)
a.set_xlim(-0.05, 0.03)
a.set_ylim(-0.55, 0.55)
a.set_yticks([])
a.set_xlabel("欠明确性指数对需求覆盖的 β（query 聚类，n=19,716）", fontsize=9.5)
a.set_title("(a) H1 判 partial：负向但微弱", fontsize=10.5)
a.grid(alpha=0.25, axis="x", ls="--")

# (b) 欠明确性四分位的覆盖
a = axs[0, 1]
qs = ["u1\n最明确", "u2", "u3", "u4\n最欠明确"]
cov = [69.77, 67.53, 65.46, 66.44]
a.plot(range(4), cov, "o-", color=C_SUP, lw=2, ms=7)
for i, v in enumerate(cov):
    a.annotate(f"{v:.2f}%", (i, v), textcoords="offset points", xytext=(0, 9),
               ha="center", fontsize=9, color=C_SUP)
a.set_xticks(range(4))
a.set_xticklabels(qs, fontsize=9.5)
a.set_ylabel("平均需求覆盖 %（宽松读法）", fontsize=9.5)
a.set_ylim(62, 72)
a.text(1.5, 63.2, "梯度几乎平：从最明确到最欠明确只降 3.3 个百分点，\n且尾部回升——欠明确性不是覆盖的主开关", fontsize=9)
a.set_title("(b) 欠明确性四分位的覆盖：微弱下行后反弹", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (c) H2 宽读 vs 严读
a = axs[1, 0]
a.bar([0], [67.3], width=0.4, color=C_FN, alpha=0.88)
a.errorbar([0], [67.3], yerr=[[67.3 - 66.75], [67.93 - 67.3]], fmt="none",
           ecolor="#333333", capsize=6, lw=1.6)
a.bar([1], [12.03], width=0.4, color=C_NS, alpha=0.88)
a.axhline(30, color=C_OPP, lw=1.8, ls="--")
a.text(1.35, 30.5, "冻结地板 30%", fontsize=9.5, color=C_OPP)
a.text(0, 70.5, "67.3% [66.8, 67.9]", ha="center", fontsize=10, color=C_FN)
a.text(1, 15.2, "12.0%（严格内容词读法）", ha="center", fontsize=9.5, color="#8a6d00")
a.text(0.5, 47, "两种读法的实例级相关 ρ=0.27：\n宽读被词面重合抬高，\n严读才逼近语义覆盖", fontsize=9)
a.set_xticks([0, 1])
a.set_xticklabels(["宽松读法\n（词面重合即算）", "严格读法\n（内容词匹配）"], fontsize=9.5)
a.set_ylabel("需求被候选目录覆盖的份额 %", fontsize=9.5)
a.set_ylim(0, 76)
a.set_title("(c) H2 描述性：宽读 67.3% 远超 0.3 地板，严读仅 12%", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (d) 候选池规模的覆盖梯度
a = axs[1, 1]
cqs = ["q1 最小\n(n=4,602)", "q2\n(n=4,968)", "q3\n(n=4,822)", "q4 最大\n(n=5,324)"]
ccov = [50.75, 65.31, 71.12, 80.0]
a.bar(range(4), ccov, width=0.55, color=C_GI, alpha=0.85)
for i, v in enumerate(ccov):
    a.text(i, v + 1.2, f"{v:.2f}%", ha="center", fontsize=10)
a.text(1.0, 38, "候选目录每升一个四分位，覆盖升 7-15 个百分点——\n池子越大，隐含需求越容易被顺带覆盖；\n这个梯度比欠明确性效应大一个数量级", fontsize=9)
a.set_xticks(range(4))
a.set_xticklabels(cqs, fontsize=9)
a.set_ylabel("平均需求覆盖 %", fontsize=9.5)
a.set_ylim(0, 92)
a.set_title("(d) 候选池规模四分位的覆盖：真正的量级所在", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

fig.tight_layout(rect=[0, 0, 1, 0.955])
fig.savefig(os.path.join(OUT, "fig1_coverage.png"), dpi=200)
plt.close(fig)

# ============ 图 2 ============
fig, axs = plt.subplots(2, 2, figsize=(11.5, 8.6))
fig.suptitle("图 2  特异性检验：词汇歧义才是覆盖的主导（EXP-0204）",
             fontsize=12.5, y=0.985)

# (a) 偏差阶梯
a = axs[0, 0]
mods = ["仅控制项", "+欠明确性", "+指代标记", "+词汇歧义"]
dev = [18437.94, 18433.84, 18430.03, 17047.80]
bars = a.bar(mods, dev, width=0.5, color=[C_GY, C_NS, C_SUP, C_OPP], alpha=0.9)
for b_, dv in zip(bars, dev):
    a.text(b_.get_x() + b_.get_width() / 2, dv + 25, f"{dv:,.1f}", ha="center", fontsize=9)
a.annotate("Δ=4.09 (p=0.004)", xy=(1, 18433.8), xytext=(0.02, 17600), fontsize=9,
           arrowprops=dict(arrowstyle="->", lw=1.0, color="#555555"))
a.annotate("Δ=7.90 (p<0.001)", xy=(2, 18430.0), xytext=(1.1, 17900), fontsize=9,
           arrowprops=dict(arrowstyle="->", lw=1.0, color="#555555"))
a.annotate("Δ=1390.14\nLR χ²=2780 —— 巨人登场", xy=(3, 17047.8), xytext=(1.7, 17250),
           fontsize=10, color=C_OPP, arrowprops=dict(arrowstyle="->", lw=1.2, color=C_OPP))
a.set_ylim(16800, 18800)
a.set_ylabel("query 聚类准偏差", fontsize=9.5)
a.tick_params(axis="x", labelsize=9)
a.set_title("(a) 偏差阶梯：词汇歧义的贡献是欠明确性的 340 倍", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (b) 联合模型系数
a = axs[0, 1]
terms = ["词汇歧义\nlex_amb_z", "指代标记\nref_mark_z", "约束计数\nconstraint_count", "欠明确性\nunderspec_z"]
bets = [0.2843, 0.0229, -0.0216, -0.0303]
los  = [0.2693, 0.0088, -0.0355, -0.0460]
his  = [0.2993, 0.0370, -0.0077, -0.0146]
y = np.arange(4)
for i, (b_, lo, hi) in enumerate(zip(bets, los, his)):
    sig = lo > 0 or hi < 0
    a.errorbar(b_, i, xerr=[[b_ - lo], [hi - b_]], fmt="o",
               color=C_OPP if i == 0 else (C_SUP if sig else C_GY),
               capsize=5, lw=1.6, ms=8)
a.axvline(0, color="black", lw=1.0, ls="--")
a.set_yticks(y)
a.set_yticklabels(terms, fontsize=9)
a.invert_yaxis()
a.set_xlabel("联合模型中对覆盖的 β", fontsize=9.5)
a.text(0.10, 2.6, "四种不确定性同台：词汇歧义一家独大；\n欠明确性在控制后仍负但更小——\nH3 判 not_specific：信号由他者承载", fontsize=9)
a.set_title("(b) 联合模型：欠明确性不是自己的信号", fontsize=10.5)
a.set_xlim(-0.09, 0.36)
a.grid(alpha=0.25, axis="x", ls="--")

# (c) 分层：候选池与模型栈
a = axs[1, 0]
labels = ["q1 最小池", "q2", "q3", "q4 最大池", "Kimi-K2", "OSS", "Qwen3"]
sbs = [-0.0252, 0.0142, 0.0169, -0.0587, -0.0246, -0.0087, -0.0126]
slo = [-0.056, -0.015, -0.0056, -0.0786, -0.0449, -0.0307, -0.0354]
shi = [0.0055, 0.0433, 0.0394, -0.0388, -0.0043, 0.0133, 0.0102]
x = np.arange(7)
for i in range(7):
    sig = slo[i] > 0 or shi[i] < 0
    a.bar(x[i], sbs[i], width=0.55, color=C_OPP if sig else C_GY, alpha=0.85)
    a.errorbar(x[i], sbs[i], yerr=[[sbs[i] - slo[i]], [shi[i] - sbs[i]]],
               fmt="none", ecolor="#333333", capsize=4, lw=1.3)
a.axhline(0, color="black", lw=0.9)
a.text(3, -0.088, "唯一显著的大池层\nβ=-0.0587", ha="center", fontsize=8.5, color=C_OPP)
a.text(4, 0.030, "Kimi-K2 显著；\nOSS/Qwen3 不显著", fontsize=8.5)
a.set_xticks(x)
a.set_xticklabels(labels, fontsize=8.5, rotation=20)
a.set_ylabel("欠明确性 β（分层）", fontsize=9.5)
a.set_title("(c) 异质性：负效应集中于最大候选池与单一模型栈", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (d) 需求计数分布与覆盖带
a = axs[1, 1]
reqs = ["0", "1", "2", "3", "4", "5+"]
cnt = [11926, 11472, 5691, 1927, 524, 102]
a.bar(reqs, cnt, width=0.55, color=C_FN, alpha=0.85)
for i, c in enumerate(cnt):
    a.text(i, c + 160, f"{c:,}", ha="center", fontsize=9)
a.text(3.3, 7000, "38% 的指令不含任何可数需求（0 需求）；\n含需求的 19,716 条中，覆盖随需求数\n几乎不变（66.7%/68.1%/68.4%）；\n半数覆盖严读仅 11-15%", fontsize=9)
a.set_xlabel("每条指令的可数需求数", fontsize=9.5)
a.set_ylabel("指令数", fontsize=9.5)
a.set_ylim(0, 13500)
a.set_title("(d) 需求的分布：稀疏而均匀地被覆盖", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

fig.tight_layout(rect=[0, 0, 1, 0.955])
fig.savefig(os.path.join(OUT, "fig2_specificity.png"), dpi=200)
plt.close(fig)
print("P056 figs done")
