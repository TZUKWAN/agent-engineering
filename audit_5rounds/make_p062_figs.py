# -*- coding: utf-8 -*-
"""P062 discourse_structure — 定制图（非模板）。"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import os

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

OUT = r"G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P062_discourse_structure_of_successful_and_failed_searches"
os.makedirs(OUT, exist_ok=True)

C_SUP = "#1a5276"
C_OPP = "#c0392b"
C_NS  = "#b7950b"
C_GY  = "#95a5a6"
C_FN  = "#117a65"

# ============ 图 1 ============
fig, axs = plt.subplots(2, 2, figsize=(11.5, 8.8))
fig.suptitle("图 1  成功与失败搜索的话语结构：结果话语是最大的分水岭（EXP-0209，20,000 条 rollout）",
             fontsize=12.5, y=0.985)

# (a) 类别出现率哑铃图
a = axs[0, 0]
cats = [("result 结果", 38.45, 89.11), ("exception 异常", 53.45, 77.14),
        ("provenance 出处", 85.80, 95.71), ("condition 条件", 86.74, 93.93),
        ("rationale 理由", 76.46, 83.21), ("context 背景", 45.34, 50.18),
        ("observation 观察", 62.10, 62.14), ("procedure 过程", 100.0, 100.0)]
cats.sort(key=lambda x: x[2] - x[1])
y = np.arange(len(cats))
for i, (lab, fail, succ) in enumerate(cats):
    a.plot([fail, succ], [i, i], color="#cccccc", lw=2.5, zorder=1)
    a.scatter(fail, i, color=C_GY, s=55, zorder=2, label="失败 (n=19,440)" if i == 0 else "")
    a.scatter(succ, i, color=C_OPP, s=55, zorder=2, label="提交 (n=560)" if i == 0 else "")
    a.text(max(fail, succ) + 1.5, i, f"+{succ-fail:.1f}pp" if succ > fail else "±0",
           va="center", fontsize=8.5,
           color=C_OPP if succ - fail > 15 else ("#555555" if succ > fail else "#999999"))
a.set_yticks(y)
a.set_yticklabels([c[0] for c in cats], fontsize=9)
a.set_xlim(25, 118)
a.set_xlabel("该话语类别在 rollout 文本中的出现率 %", fontsize=9.5)
a.set_title("(a) 八类话语的出现率落差：结果话语 +50.6 个百分点", fontsize=10.5)
a.legend(fontsize=8.5, loc="lower right")
a.grid(alpha=0.25, axis="x", ls="--")

# (b) 模型的四个声音
a = axs[0, 1]
items = [("结果话语\ncomp_result", 3.1071, 2.3775, 3.8368, C_OPP),
         ("话语平衡\nbalance", 0.8112, 0.6053, 1.0171, C_SUP),
         ("异常话语\ncomp_exception", 0.7118, 0.3093, 1.1144, C_NS),
         ("回合数\nn_turns", -0.9733, -1.2010, -0.7457, C_GY)]
y = np.arange(4)
for i, (lab, b, lo, hi, c) in enumerate(items):
    a.errorbar(b, i, xerr=[[b - lo], [hi - b]], fmt="o", color=c,
               capsize=5, lw=1.7, ms=8)
    a.text(hi + 0.12, i, f"β={b:+.4f}", va="center", fontsize=9)
a.axvline(0, color="black", lw=1.0, ls="--")
a.set_yticks(y)
a.set_yticklabels([i[0] for i in items], fontsize=9)
a.invert_yaxis()
a.set_xlabel("对提交的 β（log-odds，实例聚类，控制文本量）", fontsize=9.5)
a.text(2.6, 3.1, "提到结果 = 赔率 ×22；\n回合越少越可能提交（-0.97）；\n提到异常也是正向信号（+0.71）", fontsize=8.5)
a.set_title("(b) 四个声音：结果话语一骑绝尘", fontsize=10.5)
a.set_xlim(-1.7, 4.6)
a.grid(alpha=0.25, axis="x", ls="--")

# (c) 成功轨迹"更短但更多话"
a = axs[1, 0]
x = np.arange(2)
turns = [14.95, 12.39]
prose = [4882, 5593]
b1 = a.bar(x - 0.18, turns, width=0.36, color=C_GY, alpha=0.88, label="平均回合数")
for xi, v in zip(x, turns):
    a.text(xi - 0.18, v + 0.25, f"{v:.2f}", ha="center", fontsize=9.5)
a2 = a.twinx()
b2 = a2.bar(x + 0.18, prose, width=0.36, color=C_FN, alpha=0.88, label="平均散文字符")
for xi, v in zip(x, prose):
    a2.text(xi + 0.18, v + 90, f"{v:,}", ha="center", fontsize=9.5, color=C_FN)
a.set_xticks(x)
a.set_xticklabels(["未提交 (n=19,440)", "提交 (n=560)"], fontsize=10)
a.set_ylabel("平均回合数", fontsize=9.5)
a2.set_ylabel("平均散文字符", fontsize=9.5, color=C_FN)
a.set_ylim(0, 17.5)
a2.set_ylim(0, 6600)
a.text(0.5, 16.3, "提交的轨迹更短（12.4 vs 15.0 回合）却写得更满\n（5,593 vs 4,882 字符）——少绕路、多交代", fontsize=9.5, ha="center")
a.set_title("(c) 成功的形状：短而满", fontsize=10.5)
h1, l1 = a.get_legend_handles_labels()
h2, l2 = a2.get_legend_handles_labels()
a.legend(h1 + h2, l1 + l2, fontsize=8.5, loc="center left")
a.grid(alpha=0.25, axis="y", ls="--")

# (d) 长度分层的 balance 效应
a = axs[1, 1]
qs = ["q1 最短\n(n_turns 保留)", "q2", "q3", "q4 最长"]
bs = [0.8082, 0.5972, 0.8659, 0.7202]
los = [0.5874, -0.0043, 0.2707, 0.2313]
his = [1.0289, 1.1987, 1.4612, 1.2091]
x = np.arange(4)
for i in range(4):
    sig = los[i] > 0
    a.bar(x[i], bs[i], width=0.5, color=C_SUP if sig else C_GY, alpha=0.88)
    a.errorbar(x[i], bs[i], yerr=[[bs[i] - los[i]], [his[i] - bs[i]]],
               fmt="none", ecolor="#333333", capsize=5, lw=1.4)
    a.text(x[i], his[i] + 0.06, f"{bs[i]:.3f}" + ("*" if sig else ""), ha="center", fontsize=9.5)
a.axhline(0, color="black", lw=0.9)
a.text(1, 1.62, "* CI 排除零。话语平衡的效应在四个长度层全部为正——\n不是短轨迹或长轨迹的局部现象", fontsize=9)
a.set_xticks(x)
a.set_xticklabels(qs, fontsize=9)
a.set_ylabel("balance 对提交的 β", fontsize=9.5)
a.set_ylim(-0.3, 2.0)
a.set_title("(d) 长度分层：话语效应跨长度稳定", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(os.path.join(OUT, "fig1_discourse.png"), dpi=200)
plt.close(fig)

# ============ 图 2 ============
fig, axs = plt.subplots(2, 2, figsize=(11.5, 8.8))
fig.suptitle("图 2  位置无关、偏差阶梯与 H3 的特异性检验（EXP-0209）",
             fontsize=12.5, y=0.985)

# (a) H2 位置
a = axs[0, 0]
a.errorbar([0], [-0.0015], yerr=[[0.0035], [0.0035]], fmt="o", color=C_GY,
           capsize=6, lw=1.8, ms=9)
a.errorbar([1], [-0.0499], yerr=[[0.0357], [0.0358]], fmt="s", color=C_NS,
           capsize=6, lw=1.8, ms=9)
a.axhline(0, color="black", lw=1.0, ls="--")
a.text(0, 0.028, "观察提及的位置 β=-0.0015\np=0.393 → null\n（提交 0.0014 vs 未提交 0.0011）", ha="center", fontsize=9)
a.text(1, -0.105, "观察臂 β=-0.0499\np=0.006（弱负）", ha="center", fontsize=9, color="#8a6d00")
a.set_xticks([0, 1])
a.set_xticklabels(["提及位置", "观察臂指标"], fontsize=10)
a.set_ylabel("β", fontsize=9.5)
a.set_ylim(-0.14, 0.06)
a.set_title("(a) H2 判 null：观察写在哪里不重要", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (b) 偏差阶梯
a = axs[0, 1]
mods = ["仅控制项", "+话语平衡", "+结果/异常两分类"]
dev = [3547.78, 3462.41, 3093.38]
bars = a.bar(mods, dev, width=0.5, color=[C_GY, C_SUP, C_OPP], alpha=0.88)
for b_, dv in zip(bars, dev):
    a.text(b_.get_x() + b_.get_width() / 2, dv + 12, f"{dv:,.2f}", ha="center", fontsize=9)
a.annotate("Δ=85.37\nLR χ²(1)=170.74", xy=(1, 3462.4), xytext=(0.02, 3230),
           fontsize=9, arrowprops=dict(arrowstyle="->", lw=1.0, color="#555555"))
a.annotate("Δ=454.40\nLR χ²(2)=908.8", xy=(2, 3093.4), xytext=(1.28, 3300),
           fontsize=9.5, arrowprops=dict(arrowstyle="->", lw=1.1, color=C_OPP))
a.set_ylim(3050, 3620)
a.set_ylabel("实例聚类准偏差", fontsize=9.5)
a.set_title("(b) 偏差阶梯：两分类话语的总贡献 454 个偏差单位", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (c) H3 特异性
a = axs[1, 0]
a.axis("off")
rows = [
    ("冻结主张", "balance 在控制回合数与文本量后仍分离；\n仅回合数的模型不应自行分离"),
    ("实测一", "balance 加入后 Δdeviance=85.37 ——分离成立（前半句通过）"),
    ("实测二", "仅回合数模型 n_turns β=-0.9733, p<0.001\nLR p=0.0 ——回合数自己就会分离（后半句失败）"),
    ("判定", "not_specific_the_observation_count_alone_separates"),
    ("解读", "话语平衡携带回合数之外的 85 个偏差单位增量，\n但冻结句把它与'回合数不自分离'绑定，\n后半句的失败让整句判 not_specific"),
]
y0 = 0.95
for k, v in rows:
    a.text(0.02, y0, k, fontsize=10, weight="bold", color=C_FN, va="top")
    a.text(0.17, y0, v, fontsize=9, va="top")
    y0 -= 0.19
a.set_title("(c) H3 的两段式判定", fontsize=10.5, loc="right")

# (d) 判定卡
a = axs[1, 1]
a.axis("off")
rows = [
    ("H1", "supported", "balance β=0.8112 [0.6053, 1.0171]；结果话语 β=3.1071"),
    ("H2", "null", "观察位置 β=-0.0015, p=0.393——位置无关"),
    ("H3", "not_specific", "回合数自身分离触发特异性规则的保守分支"),
    ("前提", "G1/G2 全过", "20,000 条可读 rollout；标签稀疏 2.8% 照印"),
    ("头部信号", "result 89% vs 38%", "成功轨迹把'拿到了什么'写进文本；\n失败轨迹写的是过程与出处"),
]
y0 = 0.92
for k, v1, v2 in rows:
    a.text(0.02, y0, k, fontsize=10, weight="bold", color=C_FN, va="top")
    a.text(0.15, y0, v1, fontsize=9.5, weight="bold", va="top", color=C_OPP)
    a.text(0.37, y0, v2, fontsize=8.8, va="top")
    y0 -= 0.185
a.set_title("(d) 判定卡", fontsize=10.5, loc="right")

fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(os.path.join(OUT, "fig2_verdicts.png"), dpi=200)
plt.close(fig)
print("P062 figs done")
