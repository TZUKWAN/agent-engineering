# -*- coding: utf-8 -*-
"""P044 tool_dependency_network — 补做定制图。"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import os

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

OUT = r"G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P044_tool_dependency_network"
C_SUP = "#1a5276"; C_OPP = "#c0392b"; C_NS = "#b7950b"; C_GY = "#95a5a6"; C_FN = "#117a65"

fig, axs = plt.subplots(2, 2, figsize=(11.5, 8.8))
fig.suptitle("图 1  工具依赖网络：高频共需对在排序第一位就失败得更少（EXP-0188，14,520 查询）",
             fontsize=12.5, y=0.985)

# (a) H1 森林
a = axs[0, 0]
a.errorbar([-0.3774], [0], xerr=[[-0.3774 - (-0.5024)], [(-0.2525) - (-0.3774)]], fmt="o",
           color=C_SUP, capsize=7, lw=2, ms=10)
a.errorbar([-0.019], [1], xerr=[[-0.019 - (-0.0245)], [(-0.0136) - (-0.019)]], fmt="s",
           color=C_FN, capsize=7, lw=2, ms=10)
a.axvline(0, color="black", lw=1.0, ls="--")
a.text(-0.3774, 0.32, "高频对指示项\nβ=-0.3774 [-0.5024, -0.2524]\np_holm<0.001 → supported", ha="center", fontsize=9)
a.text(-0.019, 1.32, "连续对频次\nβ=-0.019 [-0.0245, -0.0136]\n（每次共需再降 1.9% 失败几率的 log-odds）", ha="center", fontsize=9)
a.set_yticks([0, 1]); a.set_yticklabels(["高频对指示项", "连续频次"], fontsize=9.5)
a.invert_yaxis(); a.set_xlim(-0.56, 0.06)
a.set_xlabel("对 rank-1 失败的 β（query 聚类）", fontsize=9.5)
a.set_title("(a) H1 判 supported：共需对是排序的护身符", fontsize=10.5)
a.grid(alpha=0.25, axis="x", ls="--")

# (b) 失败率按频次带
a = axs[0, 1]
a.bar([0, 1], [18.91, 10.64], width=0.42, color=[C_GY, C_SUP], alpha=0.88)
a.errorbar([0], [18.91], yerr=[[0.7], [0.7]], fmt="none", ecolor="#333333", capsize=5, lw=1.4)
a.errorbar([1], [10.64], yerr=[[1.0], [1.0]], fmt="none", ecolor="#333333", capsize=5, lw=1.4)
a.text(0, 19.9, "18.91%", ha="center", fontsize=11)
a.text(1, 11.6, "10.64%", ha="center", fontsize=11)
a.text(0.5, 22.5, "高频共需对（≥10 次共现）的查询\nrank-1 失败率比普通对低 8.3 个百分点\n——目录学会了把它们排在一起", ha="center", fontsize=9.5)
a.set_xticks([0, 1]); a.set_xticklabels(["普通对 (2-9 次)\nn=11,259", "高频对 (≥10 次)\nn=3,261"], fontsize=9.5)
a.set_ylabel("rank-1 失败率 %", fontsize=9.5); a.set_ylim(0, 25)
a.set_title("(b) 频次带对比：高频对失败率低 44%", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (c) H2 网络重叠 vs 随机
a = axs[1, 0]
a.bar([0, 1], [19.77, 5.25], width=0.4, color=[C_SUP, C_GY], alpha=0.88)
a.bar([2, 3], [1.65, 1.39], width=0.4, color=[C_OPP, C_GY], alpha=0.6)
a.text(0, 20.6, "19.8%", ha="center", fontsize=10.5)
a.text(1, 6.1, "5.3%", ha="center", fontsize=10)
a.text(2, 2.5, "1.65%\n(随机)", ha="center", fontsize=9)
a.text(3, 2.2, "1.39%\n(随机)", ha="center", fontsize=9)
a.set_xticks([0, 1, 2, 3])
a.set_xticklabels(["高频对\n实际重叠", "普通对\n实际重叠", "高频对\n随机基线", "普通对\n随机基线"], fontsize=8.5)
a.set_ylabel("两工具的查询集重叠 %", fontsize=9.5); a.set_ylim(0, 24)
a.text(1.5, 14.5, "高频对的实际重叠是随机基线的 12 倍\n——共需结构是真实的网络属性，\n不是词面巧合（304 条边为簇）", ha="center", fontsize=9.5)
a.set_title("(c) H2：网络重叠远超随机（12 倍）", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (d) 偏差阶梯
a = axs[1, 1]
mods = ["仅控制项", "+高频对指示", "+连续频次"]
dev = [12414.8, 12377.84, 12355.86]
bars = a.bar(mods, dev, width=0.5, color=[C_GY, C_SUP, C_FN], alpha=0.88)
for b_, dv in zip(bars, dev):
    a.text(b_.get_x() + b_.get_width() / 2, dv + 8, f"{dv:,.1f}", ha="center", fontsize=9)
a.annotate("Δ=36.96\nLR χ²=73.9", xy=(1, 12377.8), xytext=(0.02, 12330), fontsize=9,
           arrowprops=dict(arrowstyle="->", lw=1.0, color="#555555"))
a.annotate("再 Δ=21.98", xy=(2, 12355.9), xytext=(1.35, 12305), fontsize=9,
           arrowprops=dict(arrowstyle="->", lw=1.0, color="#555555"))
a.set_ylim(12290, 12445)
a.set_ylabel("query 聚类准偏差", fontsize=9.5)
a.set_title("(d) 偏差阶梯：两个口径增量同向", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(os.path.join(OUT, "fig1_network.png"), dpi=200)
plt.close(fig)

# ============ 图 2 ============
fig, axs = plt.subplots(2, 2, figsize=(11.5, 8.8))
fig.suptitle("图 2  网络解剖：稀疏性、顶级共需对与模型栈（EXP-0188）", fontsize=12.5, y=0.985)

# (a) 对频次分布（长尾）
a = axs[0, 0]
ks = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
vs = [7424, 1500, 435, 228, 128, 73, 69, 52, 39, 40]
a.bar(ks, vs, width=0.6, color=[C_GY] * 9 + [C_SUP], alpha=0.9)
for k, v in zip(ks, vs):
    a.text(k, v + 90, str(v), ha="center", fontsize=8.5)
a.text(5.5, 4500, "10,252 个实际共现对 / 350 万可能对\n稀疏度 0.29%——网络极稀疏，\n但头部 304 条边（≥10 次）承载了\n全部的排序优势", fontsize=9.5, ha="center")
a.set_xlabel("工具对被共同需要的查询数", fontsize=9.5)
a.set_ylabel("工具对数（对数感）", fontsize=9.5)
a.set_yscale("log"); a.set_ylim(20, 30000)
a.set_title("(a) 共现频次长尾：稀疏网 + 重头部", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (b) 顶级共需对
a = axs[0, 1]
pairs = [("clear-thought: mentalmodel\n+ sequentialthinking", 77),
         ("clear-thought: designpattern\n+ sequentialthinking", 63),
         ("clear-thought: designpattern\n+ mentalmodel", 55),
         ("pinterest: get_image_info\n+ (姊妹接口)", 48),
         ("get_live_temp + get_weather", 47),
         ("time-mcp: convert_time\n+ current_time", 43),
         ("drawing: fillRectangle\n+ (姊妹接口)", 41)]
y = np.arange(len(pairs))
a.barh(y, [p[1] for p in pairs], color=C_SUP, alpha=0.88)
for i, (lab, v) in enumerate(pairs):
    a.text(v + 0.8, i, str(v), va="center", fontsize=9)
a.set_yticks(y); a.set_yticklabels([p[0] for p in pairs], fontsize=7.8)
a.invert_yaxis()
a.set_xlabel("共同需要的查询数", fontsize=9.5)
a.set_xlim(0, 88)
a.text(55, 5.8, "顶级对清一色是同一服务器内的姊妹接口\n——'依赖'的实体是套件内聚，不是跨厂商搭配", fontsize=9)
a.set_title("(b) 七大高频对：姊妹接口统治", fontsize=10.5)
a.grid(alpha=0.25, axis="x", ls="--")

# (c) 模型栈分层
a = axs[1, 0]
cfgs = ["Kimi-K2\n(n=8,971)", "OSS\n(n=4,035)", "Qwen3\n(n=1,514)"]
bs = [-0.2794, -1.4764, 0.3427]
los = [-0.4176, -2.0608, -0.9338]
his = [-0.1412, -0.892, 1.6192]
x = np.arange(3)
for i in range(3):
    sig = los[i] > 0 or his[i] < 0
    a.bar(x[i], bs[i], width=0.5, color=C_SUP if sig else C_GY, alpha=0.88)
    a.errorbar(x[i], bs[i], yerr=[[bs[i] - los[i]], [his[i] - bs[i]]],
               fmt="none", ecolor="#333333", capsize=5, lw=1.4)
    a.text(x[i], his[i] + 0.08, f"{bs[i]:+.3f}" + ("*" if sig else ""), ha="center", fontsize=9.5)
a.axhline(0, color="black", lw=0.9)
a.text(2, -2.5, "* CI 排除零。OSS 的优势最强（-1.48），\nQwen3 无信号——网络红利是栈相关的", fontsize=9, ha="center")
a.set_xticks(x); a.set_xticklabels(cfgs, fontsize=9.5)
a.set_ylabel("高频对对失败率的 β", fontsize=9.5)
a.set_ylim(-2.8, 2.2)
a.set_title("(c) 模型栈：网络红利不平权", fontsize=10.5)
a.grid(alpha=0.25, axis="y", ls="--")

# (d) 判定卡
a = axs[1, 1]; a.axis("off")
rows = [
    ("H1", "supported", "高频对 → rank-1 失败 β=-0.3774；失败率 18.9%→10.6%"),
    ("H2", "supported", "重叠 19.8% 对随机 1.65%（12 倍）；304 边为簇"),
    ("H3", "measured", "稀疏度 0.29%；2,649 工具、均值 2.0 查询/对"),
    ("实体发现", "姊妹接口", "顶级对全是同服务器内聚——'依赖'的主语是套件"),
    ("栈差异", "OSS 最受益", "Kimi 次之、Qwen3 无信号"),
]
y0 = 0.92
for k, v1, v2 in rows:
    a.text(0.02, y0, k, fontsize=10, weight="bold", color=C_FN, va="top")
    a.text(0.15, y0, v1, fontsize=9.3, weight="bold", va="top", color=C_OPP)
    a.text(0.34, y0, v2, fontsize=8.7, va="top")
    y0 -= 0.185
a.set_title("(d) 判定卡", fontsize=10.5, loc="right")

fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(os.path.join(OUT, "fig2_network.png"), dpi=200)
plt.close(fig)
print("P044 figs done")
