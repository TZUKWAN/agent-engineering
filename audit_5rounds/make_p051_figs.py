# -*- coding: utf-8 -*-
"""P051 early_signals_of_agent_search_failure — 定制图（非模板）。"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import os

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

OUT = r"G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P051_early_signals_of_agent_search_failure"
os.makedirs(OUT, exist_ok=True)

C_SUP = "#1a5276"
C_OPP = "#c0392b"
C_NS  = "#b7950b"
C_GY  = "#95a5a6"
C_FN  = "#117a65"

# ============ 图 1 ============
fig, axs = plt.subplots(2, 2, figsize=(11.5, 8.6))
fig.suptitle("图 1  轨迹前 20% 能否预告最终失败：AUC 阶梯与标签力学（EXP-0199，19,654 条 rollout）",
             fontsize=12.5, y=0.985)

# (a) AUC 阶梯
a = axs[0, 0]
labels = ["机遇水平\n(冻结地板 0.5)", "前 1/5 行为特征\n(H1, supported)", "双时段特征\n(H2 模型)", "仅轨迹长度\n(基线)"]
vals = [0.5, 0.6857, 0.694, 0.8604]
cis = [(None, None), (0.6598, 0.7116), (None, None), (None, None)]
cols = [C_GY, C_SUP, C_FN, C_OPP]
y = np.arange(4)
for i, (lab, v, c) in enumerate(zip(labels, vals, cols)):
    a.barh(i, v, height=0.5, color=c, alpha=0.88)
    lo, hi = cis[i]
    if lo is not None:
        a.plot([lo, hi], [i, i], color="black", lw=1.6)
        a.plot([lo, lo], [i - 0.12, i + 0.12], color="black", lw=1.6)
        a.plot([hi, hi], [i - 0.12, i + 0.12], color="black", lw=1.6)
    a.text(v + 0.008, i, f"{v:.4f}" + (f"  [{lo:.4f}, {hi:.4f}]" if lo else ""),
           va="center", fontsize=9)
a.axvline(0.65, color=C_NS, lw=1.6, ls="--")
a.text(0.652, 3.45, "冻结 AUC 地板 0.65", fontsize=8.5, color=C_NS)
a.set_yticks(y)
a.set_yticklabels(labels, fontsize=9)
a.invert_yaxis()
a.set_xlim(0.42, 1.0)
a.set_xlabel("交叉验证 AUC（实例不相交折叠）", fontsize=9.5)
a.set_title("(a) AUC 阶梯：行为特征过地板，但被'数步数'基线远远压过", fontsize=10.5)
a.grid(alpha=0.25, axis="x", ls="--")

# (b) H2 增量
a = axs[0, 1]
a.errorbar([0], [0.6857], yerr=[[0.6857 - 0.6598], [0.7116 - 0.6857]], fmt="o",
           color=C_SUP, capsize=7, lw=1.8, ms=9, label="仅前 1/5 特征")
a.errorbar([1], [0.694], yerr=[[0.004], [0.004]], fmt="s", color=C_FN,
           capsize=7, lw=1.8, ms=9, label="前 1/5 + 后 1/5")
a.annotate("", xy=(1, 0.694), xytext=(0, 0.6857),
           arrowprops=dict(arrowstyle="->", lw=1.4, color=C_OPP))
a.text(0.5, 0.735, "ΔAUC = +0.0083", ha="center", fontsize=10, color=C_OPP)
a.text(0.5, 0.60, "末五分之一几乎不携带\n前五分之一没有的信息", ha="center", fontsize=9.5)
a.set_xticks([0, 1])
a.set_xticklabels(["前 1/5", "双时段"], fontsize=10)
a.set_ylabel("AUC", fontsize=9.5)
a.set_ylim(0.60, 0.76)
a.set_title("(b) H2 判 not_specific：后段增量不足 0.01 AUC", fontsize=10.5)
a.legend(fontsize=9, loc="lower right")
a.grid(alpha=0.25, axis="y", ls="--")

# (c) 标签力学：长度 × 提交份额
a = axs[1, 0]
qs = ["q1 最短", "q2", "q3", "q4 最长"]
sh = [9.51, 0.56, 0.56, 0.58]
bars = a.bar(qs, sh, width=0.55, color=[C_OPP, C_GY, C_GY, C_GY], alpha=0.88)
for b_, v in zip(bars, sh):
    a.text(b_.get_x() + b_.get_width() / 2, v + 0.18, f"{v:.2f}%", ha="center", fontsize=9.5)
a.annotate("17 倍", xy=(0, 9.51), xytext=(0.85, 8.4), fontsize=11, color=C_OPP,
           arrowprops=dict(arrowstyle="->", lw=1.2, color=C_OPP))
a.text(1.5, 6.2, "'已完成'标签几乎全部落在最短四分位：\n提交 = 提前结束。长度不是信号之一，\n长度就是标签本身", fontsize=9)
a.set_ylabel("提交（完成）份额 %", fontsize=9.5)
a.set_xlabel("轨迹长度四分位（各 4,997 条）", fontsize=9.5)
a.set_ylim(0, 11)
a.set_title("(c) 标签力学：正例率 2.8%，且几乎全是最短轨迹", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (d) 前 1/5 特征画像
a = axs[1, 1]
feats = [("切换率\nff_switch_rate", 0.3488, 0.2157),
         ("不同命令家族数\nff_distinct_families", 1.965, 0.5842),
         ("新词份额\nff_newness_mean", 0.8847, 0.1129),
         ("重复份额\nff_repeat_share", 0.0004, 0.0115)]
y = np.arange(4)
for i, (lab, m, s) in enumerate(feats):
    a.barh(i, m, height=0.5, color=C_SUP, alpha=0.85)
    a.plot([m - s, m + s], [i, i], color="black", lw=1.4)
    a.text(m + s + 0.04, i, f"{m:.4f} ± {s:.4f}", va="center", fontsize=9)
a.set_yticks(y)
a.set_yticklabels([f[0] for f in feats], fontsize=9)
a.invert_yaxis()
a.set_xlim(0, 1.75)
a.set_xlabel("前 1/5 特征的均值 ± 标准差", fontsize=9.5)
a.text(1.05, 3.0, "重复份额在开局段几乎为零\n（0.0004）——重复是中后段现象；\n另一特征 ff_cmd_words：\n25.0 ± 6.4 词（未画入同轴）", fontsize=8.5)
a.set_title("(d) 开局特征画像：高新鲜度、中等切换、零重复", fontsize=10.5)
a.grid(alpha=0.25, axis="x", ls="--")

fig.tight_layout(rect=[0, 0, 1, 0.955])
fig.savefig(os.path.join(OUT, "fig1_auc_ladder.png"), dpi=200)
plt.close(fig)

# ============ 图 2 ============
fig, axs = plt.subplots(2, 2, figsize=(11.5, 8.6))
fig.suptitle("图 2  家族内复现失败与信号的本体（EXP-0199）",
             fontsize=12.5, y=0.985)

# (a) 家族内 AUC
a = axs[0, 0]
fams = [("kubernetes-sigs\n350 条 / 16 正例", 0.5002, 0.3779, 0.7248),
        ("google\n288 条 / 29 正例", 0.507, None, None),
        ("第三家族\n199 条 / ~10 正例", 0.4577, None, None)]
for i, (lab, v, lo, hi) in enumerate(fams):
    a.bar(i, v, width=0.5,
          color=C_OPP if v < 0.65 else C_SUP, alpha=0.85)
    if lo is not None:
        a.errorbar(i, v, yerr=[[v - lo], [hi - v]], fmt="none", ecolor="#333333", capsize=6, lw=1.5)
    a.text(i, 0.735, f"AUC={v:.4f}", ha="center", fontsize=9.5)
a.axhline(0.65, color=C_NS, lw=1.6, ls="--")
a.text(0.02, 0.657, "冻结地板 0.65（需 ≥3 个家族达标）", fontsize=8.5, color=C_NS)
a.axhline(0.5, color="black", lw=0.9, ls=":")
a.text(2.1, 0.507, "机遇 0.5", fontsize=8.5)
a.set_xticks(range(3))
a.set_xticklabels([f[0] for f in fams], fontsize=9)
a.set_ylabel("家族内 AUC", fontsize=9.5)
a.set_ylim(0.38, 0.80)
a.set_title("(a) H3 判 not_reproduced：三个家族全部落在机遇水平", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (b) 每家族正例的功效解剖
a = axs[0, 1]
names = ["kubernetes-sigs", "google", "第三家族"]
ns = [350, 288, 199]
poss = [16, 29, 10]
x = np.arange(3)
a.bar(x, ns, width=0.5, color=C_GY, alpha=0.7, label="rollout 数")
for i in range(3):
    a.bar(x[i], poss[i] * 5, width=0.5, color=C_OPP, alpha=0.9, label="正例数（×5 放大）" if i == 0 else "")
    a.text(x[i], poss[i] * 5 + 12, f"{poss[i]} 例", ha="center", fontsize=9.5, color=C_OPP)
a.set_xticks(x)
a.set_xticklabels(names, fontsize=9.5)
a.set_ylabel("条数", fontsize=9.5)
a.text(0.02, 320, "每个家族的正例不足 30：\n在 2.8% 基率下，任何家族内\nAUC≈0.65 的检测都需要\n数千条正例级别的样本", fontsize=9)
a.set_title("(b) 功效解剖：H3 的失败混合了'信号不迁移'与'样本不够'", fontsize=10.5)
a.legend(fontsize=9)
a.set_ylim(0, 420)
a.grid(alpha=0.25, axis="y", ls="--")

# (c) 信号本体的分解示意
a = axs[1, 0]
a.axis("off")
rows = [
    ("H1 supported 的字面内容", "开局行为特征含 0.686 AUC 的完成判别力，超过 0.65 地板"),
    ("长度基线的事实", "仅'轨迹长度'一项达 0.860 AUC，比行为特征高 0.166"),
    ("标签力学", "提交标签 2.8%，97% 集中在最短四分位——标签由长度机制产生"),
    ("家族内的事实", "三个家族 AUC≈0.50——合并信号是家族间/长度构成，非家族内早期预警"),
    ("诚实的结论", "开局段能预测'这条轨迹会很快结束'，不等于能预测'任务会成功'"),
]
y0 = 0.95
for k, v in rows:
    a.text(0.02, y0, k, fontsize=10, weight="bold", color=C_SUP, va="top")
    a.text(0.24, y0, v, fontsize=9.2, va="top")
    y0 -= 0.17
a.set_title("(c) 信号本体：五句话拆完", fontsize=10.5, loc="right")

# (d) 判定汇总卡
a = axs[1, 1]
a.axis("off")
rows = [
    ("H1", "supported", "AUC 0.6857 [0.6598, 0.7116]，p_holm=0.0025，过 0.65 地板"),
    ("H2", "not_specific", "后 1/5 增量 +0.0083 AUC——前段几乎承载全部行为信号"),
    ("H3", "not_reproduced", "0/3 家族达 0.65：k8s 0.500、google 0.507、第三 0.458"),
    ("基线警告", "length_only 0.8604", "所有行为模型必须与它同台，否则读数无效"),
    ("前提", "G2=1.0 / G4=19,713", "标签全覆盖；≥10 步的 rollout 充裕——门全过，败因不在门"),
]
y0 = 0.92
for k, v1, v2 in rows:
    a.text(0.02, y0, k, fontsize=10, weight="bold", color=C_FN, va="top")
    a.text(0.15, y0, v1, fontsize=9.5, weight="bold", va="top", color=C_OPP)
    a.text(0.36, y0, v2, fontsize=8.8, va="top")
    y0 -= 0.165
a.set_title("(d) 判定卡", fontsize=10.5, loc="right")

fig.tight_layout(rect=[0, 0, 1, 0.955])
fig.savefig(os.path.join(OUT, "fig2_families.png"), dpi=200)
plt.close(fig)
print("P051 figs done")
