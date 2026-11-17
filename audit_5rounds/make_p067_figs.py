# -*- coding: utf-8 -*-
"""P067 information_density — 定制图（非模板）。"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import os

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

OUT = r"G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P067_information_density_of_language_and_code_actions"
os.makedirs(OUT, exist_ok=True)

C_SUP = "#1a5276"
C_OPP = "#c0392b"
C_NS  = "#b7950b"
C_GY  = "#95a5a6"
C_FN  = "#117a65"

# ============ 图 1 ============
fig, axs = plt.subplots(2, 2, figsize=(11.5, 8.8))
fig.suptitle("图 1  自然语言与代码动作的信息密度：语言更稠密、代码更有回声（EXP-0216，4,000 段对话）",
             fontsize=12.5, y=0.985)

# (a) 密度
a = axs[0, 0]
kinds = ["自然语言", "代码", "工具调用"]
dens = [81.053, 68.857, 49.159]
cols = [C_SUP, C_OPP, C_GY]
bars = a.bar(kinds, dens, width=0.5, color=cols, alpha=0.88)
for b_, v in zip(bars, dens):
    a.text(b_.get_x() + b_.get_width() / 2, v + 1.2, f"{v:.2f}", ha="center", fontsize=10.5)
a.annotate("差 = -12.20 [-12.91, -11.50]\np_holm=0.005 → opposite\n（Cohen's d ≈ -0.68）",
           xy=(0.5, 75), xytext=(0.9, 90), fontsize=9.5,
           arrowprops=dict(arrowstyle="->", lw=1.1, color=C_OPP))
a.set_ylabel("内容词密度 / 千字符", fontsize=9.5)
a.set_ylim(0, 100)
a.set_title("(a) H1 判 opposite：每字符的语言比代码更稠密", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (b) 回应份额
a = axs[0, 1]
ans = [88.95, 30.78, 22.14]
bars = a.bar(kinds, ans, width=0.5, color=[C_FN, C_GY, C_GY], alpha=0.88)
for b_, v in zip(bars, ans):
    a.text(b_.get_x() + b_.get_width() / 2, v + 1.6, f"{v:.1f}%", ha="center", fontsize=10.5)
a.annotate("Δ=+58.2pp [57.0, 59.6]\np_holm=0.005 → supported", xy=(0.5, 60), xytext=(0.85, 72),
           fontsize=9.5, arrowprops=dict(arrowstyle="->", lw=1.1, color=C_FN))
a.set_ylabel("该动作被观察回应的回合份额 %", fontsize=9.5)
a.set_ylim(0, 100)
a.set_title("(b) H2 判 supported：代码 89% 有回声，语言 31%", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (c) 观察字符
a = axs[1, 0]
obs = [493.3, 50.4, 40.0]
bars = a.bar(kinds, obs, width=0.5, color=[C_FN, C_GY, C_GY], alpha=0.88)
for b_, v in zip(bars, obs):
    a.text(b_.get_x() + b_.get_width() / 2, v + 8, f"{v:.0f}", ha="center", fontsize=10.5)
a.text(1.0, 300, "环境对一个代码块平均回复 493 字符，\n对一句话只回 50 字符——\n代码买到的不是密度，是环境的注意力", fontsize=9.5, ha="center")
a.set_ylabel("被回应时的平均观察字符数", fontsize=9.5)
a.set_ylim(0, 560)
a.set_title("(c) 回应的体量：代码的回声是语言的 10 倍", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (d) 判定卡
a = axs[1, 1]
a.axis("off")
rows = [
    ("H1", "opposite", "预测代码更密，实测语言更密（-12.2/千字符）"),
    ("H2", "supported", "代码动作 88.9% 被回应，语言 30.8%（+58pp）"),
    ("H3", "measured", "多语句块 79.6%；修正环 19.9%"),
    ("样本", "4,000 对话 / 14,582 回合", "G1-G4 门全过；语料无结局标签"),
    ("密度悖论", "语言稠密但少回声", "代码字符薄（标识符撑密度底）\n但每字符买到环境响应"),
]
y0 = 0.92
for k, v1, v2 in rows:
    a.text(0.02, y0, k, fontsize=10, weight="bold", color=C_FN, va="top")
    a.text(0.15, y0, v1, fontsize=9.5, weight="bold", va="top", color=C_OPP)
    a.text(0.36, y0, v2, fontsize=8.8, va="top")
    y0 -= 0.185
a.set_title("(d) 判定卡", fontsize=10.5, loc="right")

fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(os.path.join(OUT, "fig1_density.png"), dpi=200)
plt.close(fig)

# ============ 图 2 ============
fig, axs = plt.subplots(2, 2, figsize=(11.5, 8.8))
fig.suptitle("图 2  代码块的结构、修正环与语料的边界（EXP-0216）", fontsize=12.5, y=0.985)

# (a) 漏斗：4,000 → 错误 → 修正
a = axs[0, 0]
stages = ["全部对话\n4,000", "含代码\n3,990", "自述出错\n567", "出错后改块\n792*"]
vals = [4000, 3990, 567, 792]
cols = [C_GY, C_SUP, C_NS, C_FN]
bars = a.bar(stages, vals, width=0.55, color=cols, alpha=0.88)
for b_, v in zip(bars, vals):
    a.text(b_.get_x() + b_.get_width() / 2, v + 60, f"{v:,}", ha="center", fontsize=10)
a.text(3, 1500, "*792 为出错后修改过\n代码块的对话数\n（占含代码对话 19.9%）；\n与 567 的差含未报错也改块的", fontsize=8.5)
a.set_ylabel("对话数", fontsize=9.5)
a.set_ylim(0, 4600)
a.set_title("(a) 修正环：567 段自述出错，792 段改了代码", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (b) 多语句块
a = axs[0, 1]
a.bar([0], [79.63], width=0.35, color=C_SUP, alpha=0.88)
a.errorbar([0], [79.63], yerr=[[79.63 - 78.43], [80.75 - 79.63]], fmt="none",
           ecolor="#333333", capsize=6, lw=1.6)
a.bar([1], [20.37], width=0.35, color=C_GY, alpha=0.7)
a.text(0, 82.5, "79.6% [78.4, 80.8]", ha="center", fontsize=10.5)
a.text(1, 23, "20.4%", ha="center", fontsize=10)
a.set_xticks([0, 1])
a.set_xticklabels(["多语句代码块\n（均值 6.44 语句/块）", "单语句块"], fontsize=9.5)
a.set_ylabel("代码块份额 %", fontsize=9.5)
a.set_ylim(0, 95)
a.set_title("(b) H3：代码块以多语句批量投递为主", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (c) 密度悖论的解释面板
a = axs[1, 0]
a.axis("off")
rows = [
    ("直觉预测", "代码更密：标识符/符号占满字符"),
    ("实测", "语言更密（81 vs 69/千字符）"),
    ("为什么", "代码的空格、缩进、标点、短标识符\n稀释了内容词计数；语言句法紧凑"),
    ("代码真正买到", "回应率（89% 对 31%）与回应体量（493 对 50 字符）"),
    ("修正的读法", "'代码信息密度高'的直觉错在量尺：\n代码的密度单位是回应，不是内容词"),
]
y0 = 0.93
for k, v in rows:
    a.text(0.02, y0, k, fontsize=10.5, weight="bold", color=C_FN, va="top")
    a.text(0.17, y0, v, fontsize=9.2, va="top")
    y0 -= 0.185
a.set_title("(c) 密度悖论的四步解剖", fontsize=10.5, loc="right")

# (d) 边界卡
a = axs[1, 1]
a.axis("off")
rows = [
    ("G1 门", "≥200 代码对话", "实测 4,000"),
    ("G2 门", "≥200 有执行块", "实测 3,990"),
    ("G3 门", "≥100 报错对话", "实测 567"),
    ("G4 门", "≥100 多语句块", "实测 3,171"),
    ("语料缺口", "无结局标签", "全部读数为份额与密度，无成功主张"),
]
y0 = 0.9
for k, v1, v2 in rows:
    a.text(0.02, y0, k, fontsize=10.5, weight="bold", color=C_FN, va="top")
    a.text(0.16, y0, v1, fontsize=9.5, weight="bold", va="top", color=C_OPP)
    a.text(0.42, y0, v2, fontsize=9, va="top")
    y0 -= 0.18
a.set_title("(d) 门槛与边界", fontsize=10.5, loc="right")

fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(os.path.join(OUT, "fig2_blocks.png"), dpi=200)
plt.close(fig)
print("P067 figs done")
