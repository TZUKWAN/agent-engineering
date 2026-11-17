# -*- coding: utf-8 -*-
"""P069 case_based_reuse — 定制图（非模板）。"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import os

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

OUT = r"G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P069_case_based_reuse_of_historical_trajectories"
os.makedirs(OUT, exist_ok=True)

C_SUP = "#1a5276"
C_OPP = "#c0392b"
C_NS  = "#b7950b"
C_GY  = "#95a5a6"
C_FN  = "#117a65"

# ============ 图 1 ============
fig, axs = plt.subplots(2, 2, figsize=(11.5, 8.8))
fig.suptitle("图 1  基于案例的复用：相似性结构存在、复用证据缺席（EXP-0218，20,000 条 rollout）",
             fontsize=12.5, y=0.985)

# (a) 邻居相似度
a = axs[0, 0]
a.bar([0], [11.03], width=0.4, color=C_SUP, alpha=0.88)
a.errorbar([0], [11.03], yerr=[[11.03 - 9.50], [12.56 - 11.03]], fmt="none",
           ecolor="#333333", capsize=6, lw=1.6)
a.text(0.23, 11.0, "11.03% [9.50, 12.56]\n实例的最相似邻居 ≥0.3 的份额", fontsize=9.5, va="center")
a.axhline(0, color="black", lw=0.8)
a.text(0, 14.5, "全体实例的最佳邻居相似度均值：0.248\n（相似度 = 任务文本的词面重合）", ha="center", fontsize=10)
a.text(0, 2.2, "G9 门失火：\n冻结句要 1,000 条 rollout，\n普查按实例只测得 200——\n主张受限，只作描述", ha="center", fontsize=9, color=C_OPP)
a.set_xticks([0])
a.set_xticklabels(["高相似邻居份额"], fontsize=10)
a.set_ylabel("实例份额 %", fontsize=9.5)
a.set_ylim(0, 17)
a.set_title("(a) H1 判 measured：相似性结构存在但主张受限", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (b) H2 退化的量尺
a = axs[0, 1]
a.bar([0, 1], [100.0, 0.04], width=0.45, color=[C_NS, C_GY], alpha=0.85)
a.text(0, 101, "1.000", ha="center", fontsize=11)
a.text(1, 1.4, "0.0004", ha="center", fontsize=10)
a.set_xticks([0, 1])
a.set_xticklabels(["同实例兄弟对的\nissue 文本相似度", "同实例兄弟对的\n命令序列相似度"], fontsize=9.5)
a.set_ylabel("相似度（0-1）", fontsize=9.5)
a.set_ylim(0, 112)
a.text(0.5, 62, "同一实例的所有尝试共享同一份 issue 文本——\nissue 相似度恒为 1.0，无变异；\n命令相似度近零（0.0004）。\nH2 要求的相关两侧皆废：一侧常数、一侧噪声\n→ not_testable（拒绝以代理指标顶替）", ha="center", fontsize=9)
a.set_title("(b) H2 判 not_testable：退化的量尺", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (c) H3 关联
a = axs[1, 0]
a.errorbar([-0.243], [0], xerr=[[-0.243 - (-0.3809)], [(-0.1051) - (-0.243)]], fmt="o",
           color=C_NS, capsize=7, lw=2, ms=10)
a.axvline(0, color="black", lw=1.0, ls="--")
a.text(-0.243, 0.3, "β=-0.243 [-0.381, -0.105]\np=0.0006，n=20,000", ha="center", fontsize=9.5)
a.text(-0.243, -0.32, "邻居相似度每升 1，步数少 0.24 步\n（实际量程 0-0.3 → 约 0.07 步/全程量程）\n关联真实但复用机制不可观察：\n无时序记录、无案例库字段（W12-D02）", ha="center", fontsize=9)
a.set_xlim(-0.5, 0.15)
a.set_ylim(-0.55, 0.55)
a.set_yticks([])
a.set_xlabel("邻居相似度对步数的 β", fontsize=9.5)
a.set_title("(c) H3 判 not_testable：关联在、机制无", fontsize=10.5)
a.grid(alpha=0.25, axis="x", ls="--")

# (d) 判定卡
a = axs[1, 1]
a.axis("off")
rows = [
    ("H1", "measured（受限）", "最佳邻居相似度 0.248；≥0.3 者仅 11.0%；G9 门失火"),
    ("H2", "not_testable", "issue 相似度恒 1.0（构造使然）——拒绝代理顶替"),
    ("H3", "not_testable", "相似→步数少关联成立，但无时序/案例库，复用不可主张"),
    ("梯度", "0.34% → 7.37%", "相似带间的完成率 21 倍差——但可由任务易度解释"),
    ("立场", "诚实的三连否定", "本包的全部结论是：复用无法被证实或证伪"),
]
y0 = 0.92
for k, v1, v2 in rows:
    a.text(0.02, y0, k, fontsize=10, weight="bold", color=C_FN, va="top")
    a.text(0.14, y0, v1, fontsize=9.3, weight="bold", va="top", color=C_OPP)
    a.text(0.34, y0, v2, fontsize=8.7, va="top")
    y0 -= 0.185
a.set_title("(d) 判定卡", fontsize=10.5, loc="right")

fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(os.path.join(OUT, "fig1_reuse.png"), dpi=200)
plt.close(fig)

# ============ 图 2 ============
fig, axs = plt.subplots(2, 2, figsize=(11.5, 8.8))
fig.suptitle("图 2  相似带梯度、易度替代解释与边界（EXP-0218）", fontsize=12.5, y=0.985)

# (a) 相似带梯度
a = axs[0, 0]
bands = ["b1 低相似\n(n=1,744)", "b2 中相似\n(n=16,099)", "b3+ 高相似\n(n=2,157)"]
ss = [0.34, 2.45, 7.37]
st = [14.98, 14.89, 14.72]
x = np.arange(3)
b1 = a.bar(x - 0.18, ss, width=0.36, color=C_SUP, alpha=0.88, label="提交率 %")
for xi, v in zip(x, ss):
    a.text(xi - 0.18, v + 0.15, f"{v:.2f}%", ha="center", fontsize=9.5)
a2 = a.twinx()
b2 = a2.bar(x + 0.18, st, width=0.36, color=C_GY, alpha=0.7, label="平均步数")
for xi, v in zip(x, st):
    a2.text(xi + 0.18, v + 0.05, f"{v:.2f}", ha="center", fontsize=9, color="#666666")
a.set_xticks(x)
a.set_xticklabels(bands, fontsize=9.5)
a.set_ylabel("提交率 %", fontsize=9.5)
a2.set_ylabel("平均步数", fontsize=9.5, color="#666666")
a.set_ylim(0, 9.5)
a2.set_ylim(14.4, 15.2)
a.text(0.9, 8.0, "高相似带的完成率是低相似带的 21 倍（7.37% 对 0.34%），\n步数只差 0.26——\n完成率的梯度远强于效率的梯度，\n提示'熟悉的任务'更容易走到终点", fontsize=9)
a.set_title("(a) 相似带的 21 倍完成率梯度", fontsize=10.5)
h1, l1 = a.get_legend_handles_labels()
h2, l2 = a2.get_legend_handles_labels()
a.legend(h1 + h2, l1 + l2, fontsize=8.5, loc="upper left")
a.grid(alpha=0.25, axis="y", ls="--")

# (b) 尝试次数分布
a = axs[0, 1]
ks = [1, 2, 3, 4, 5, 6, 7, 8]
ns = [9, 10, 30, 61, 92, 132, 142, 179]
a.bar(ks, ns, width=0.6, color=C_FN, alpha=0.85)
for k, n in zip(ks, ns):
    a.text(k, n + 3, str(n), ha="center", fontsize=9)
a.text(4.0, 130, "多数实例被尝试 5 次以上\n（该统计只覆盖少量尝试的实例段）——\n仓库内的重复尝试是常态，\n'相似邻居'的土壤极其肥沃，\n只是复用的证据无法提取", fontsize=9)
a.set_xlabel("实例的尝试次数", fontsize=9.5)
a.set_ylabel("实例数", fontsize=9.5)
a.set_ylim(0, 210)
a.set_title("(b) 重复尝试的土壤", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (c) 易度替代解释
a = axs[1, 0]
a.axis("off")
rows = [
    ("复用叙事", "任务像已见过的 → 智能体借旧例 → 步数少、完成多"),
    ("易度叙事", "热门区域的任务本来就简单 → 谁做都快、都成"),
    ("本帧证据", "两者无法分离：无时序（谁先谁后？）、无检索记录（用没用旧例？）"),
    ("关键缺口", "G10：全部 20,000 条 rollout 无时间戳、无 retrieved-case 列"),
    ("判决", "关联照印，复用一词退场"),
]
y0 = 0.93
for k, v in rows:
    a.text(0.02, y0, k, fontsize=10.5, weight="bold", color=C_FN, va="top")
    a.text(0.16, y0, v, fontsize=9.2, va="top", color=C_OPP if k == "判决" else "#333333")
    y0 -= 0.185
a.set_title("(c) 两个叙事、一份证据", fontsize=10.5, loc="right")

# (d) 边界与偏差
a = axs[1, 1]
a.axis("off")
rows = [
    ("W12-D02", "无时间戳、无案例库列", "复用机制不可观察——H3 claim-limited"),
    ("W12-D04", "G9 单位错位", "句子要 rollout、普查按实例——双计数并印"),
    ("W12-D01", "（姊妹包）无正确性", "本波全部无结局质量标签"),
    ("结论强度", "全部受限", "三判定无一自由身：measured-limited / not_testable ×2"),
]
y0 = 0.9
for k, v1, v2 in rows:
    a.text(0.02, y0, k, fontsize=10.5, weight="bold", color=C_FN, va="top")
    a.text(0.17, y0, v1, fontsize=9.5, weight="bold", va="top", color=C_OPP)
    a.text(0.40, y0, v2, fontsize=9, va="top")
    y0 -= 0.21
a.set_title("(d) 偏差与边界档案", fontsize=10.5, loc="right")

fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(os.path.join(OUT, "fig2_bands.png"), dpi=200)
plt.close(fig)
print("P069 figs done")
