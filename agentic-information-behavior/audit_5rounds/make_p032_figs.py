# -*- coding: utf-8 -*-
"""P032 定制图：基于 T136 (言语计划与行动对齐, EXP-0170, wave-5) 产物数据。

本文的个性：置换对照揭示测量饱和——真实对齐与跨轨迹对照同为 0.7534
（H1 null），更高对齐反而更常失败（H2 opposite, +0.091，预测为负），
工具族分层不可估（H3，4/20 可估）。
"""
import json, glob, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 300

fs = sorted(glob.glob("results_raw/EXP0170_wave5_design_*.json"))
art = json.load(open(fs[-1], encoding="utf-8"))
OUT = pathlib.Path("papers/P032_plan_action_alignment/figures")
OUT.mkdir(parents=True, exist_ok=True)

C_SUP = "#27ae60"
C_OPP = "#c0392b"
C_NULL = "#95a5a6"
C_ACC = "#2980b9"

models = {m["hypothesis"]: m for m in art["models"]}
h1, h2, h3 = models["H1"], models["H2"], models["H3"]
dist = art["descriptive_rates"]["alignment_distribution"]

# ===== 图1 三假设判定森林 =====
fig, ax = plt.subplots(figsize=(10, 4.8))
rows = [
    ("H1 对齐 - 置换对照", h1["beta"], h1["ci_lo"], h1["ci_hi"], C_NULL,
     f"判定 null\nβ={h1['beta']:+.4f}，p_holm=1.0\n（真实与对照同为 0.7534：测量饱和）"),
    ("H2 对齐 → 下次调用失败", h2["beta"], h2["ci_lo"], h2["ci_hi"], C_OPP,
     f"判定 opposite\nβ={h2['beta']:+.4f}，p_holm<0.001\n（预测负，实测正：高对齐更常失败）"),
]
for i, (lab, b, lo, hi, c, note) in enumerate(rows):
    ax.plot([lo, hi], [i, i], color=c, lw=3, alpha=0.85)
    ax.plot(b, i, "D", color=c, ms=9)
    ax.text(hi + 0.002, i, note, va="center", fontsize=8.6)
ax.axvline(0, color="black", lw=0.9, ls="--")
ax.set_yticks([0, 1]); ax.set_yticklabels(["H1", "H2"], fontsize=11)
ax.set_xlim(-0.006, 0.14)
ax.set_xlabel("系数（聚类稳健）", fontsize=10)
ax.set_title("图1  两个主假设：对齐测不出特异性，高对齐反而是失败签名",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="x", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig1_verdicts.png", bbox_inches="tight")
plt.close()

# ===== 图2 对齐分布：饱和的直方图 =====
fig, ax = plt.subplots(figsize=(9.6, 5.0))
bins = list(dist.keys())
vals = [dist[b] for b in bins]
total = sum(vals)
shares = [v / total * 100 for v in vals]
colors = ["#c0392b", "#e67e22", "#f1c40f", "#2ecc71", "#27ae60"]
bars = ax.bar(range(len(bins)), shares, color=colors, alpha=0.9, width=0.6)
for i, (s, v) in enumerate(zip(shares, vals)):
    ax.text(i, s + 1.2, f"{s:.1f}%\n(n={v:,})", ha="center", fontsize=9.5)
ax.set_xticks(range(len(bins)))
ax.set_xticklabels([b.replace("-", "–") for b in bins], fontsize=10)
ax.set_ylabel("turn 占比（%）", fontsize=10)
ax.set_ylim(0, 100)
ax.set_xlabel("计划 turn 与下一调用的词汇对齐率分箱", fontsize=10)
ax.set_title("图2  对齐率的分布：91.4% 的 turn 落在 0.4+ 的最高档——\n测量在领域词汇的底噪上饱和了",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="y", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig2_alignment_distribution.png", bbox_inches="tight")
plt.close()

# ===== 图3 真实 vs 置换：退化的对比 =====
fig, ax = plt.subplots(figsize=(8.8, 4.8))
ma = h1["mean_alignment"]; mn = h1["mean_null"]
ax.bar([0, 1], [ma, mn], color=[C_ACC, C_NULL], alpha=0.88, width=0.45)
for x, v in [(0, ma), (1, mn)]:
    ax.text(x, v + 0.012, f"{v:.4f}", ha="center", fontsize=11, fontweight="bold")
ax.set_xticks([0, 1])
ax.set_xticklabels(["真实下一调用\n的对齐均值", "置换对照\n（他轨迹调用）的对齐均值"], fontsize=10)
ax.set_ylabel("计划语言与调用的词汇对齐均值", fontsize=10)
ax.set_ylim(0, 0.92)
ax.annotate("差 = 0.0000\n（H1 的对比在饱和底噪上退化为零）", xy=(0.5, 0.79),
            xytext=(0.5, 0.55), ha="center", fontsize=10.5, color=C_OPP,
            arrowprops=dict(arrowstyle="<->", color=C_OPP, lw=1.4))
ax.set_title("图3  H1 的解剖：随机换一个轨迹的调用，对齐率同样 75.34%\n——计划语言没有携带超出领域词汇的调用特异性",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="y", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig3_degenerate_contrast.png", bbox_inches="tight")
plt.close()

# ===== 图4 H2 opposite + 工具族剖面 =====
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.5, 4.6))
a1.barh([0], [h2["beta"]], height=0.4, color=C_OPP, alpha=0.85)
a1.errorbar(h2["beta"], 0, xerr=[[h2["beta"] - h2["ci_lo"]], [h2["ci_hi"] - h2["beta"]]],
            color="#641e16", capsize=6, lw=1.5, fmt="none")
a1.axvline(0, color="black", lw=0.9, ls="--")
a1.text(h2["ci_hi"] + 0.004, 0,
        f"对齐 z 对下次调用失败的系数\nβ = {h2['beta']:+.4f}（预测负，实测正）\n"
        f"95% CI [{h2['ci_lo']:.4f}, {h2['ci_hi']:.4f}]\nLR χ2 = 331.2，p_holm < 0.001",
        va="center", fontsize=9, color="#641e16")
a1.set_yticks([]); a1.set_xlim(0.04, 0.155)
a1.set_xlabel("对齐系数", fontsize=10)
a1.set_ylim(-0.5, 0.5)
a1.set_title("(a) H2 判 opposite：高对齐 turn 的下次调用\n失败几率显著更高", fontsize=10.5)
a1.grid(alpha=0.25, axis="x", ls="--")

fams = [f for f in h3["families"]]
names = [f["stratum"] for f in fams]
bs = [f["beta"] for f in fams]
los = [f["ci_lo"] for f in fams]
his = [f["ci_hi"] for f in fams]
for i, (b, lo, hi) in enumerate(zip(bs, los, his)):
    sig = lo > 0 or hi < 0
    c = C_ACC if sig else C_NULL
    a2.plot([lo, hi], [i, i], color=c, lw=3, alpha=0.85)
    a2.plot(b, i, "D", color=c, ms=9)
    a2.text(hi + 0.004, i, f"β={b:+.4f}", va="center", fontsize=9)
a2.axvline(0, color="black", lw=0.9, ls="--")
a2.set_yticks(range(len(fams)))
a2.set_yticklabels([n.replace("_", " ").title() for n in names], fontsize=9.5)
a2.set_xlabel("对齐 → 失败的族内系数（描述性）", fontsize=10)
a2.set_xlim(-0.16, 0.26)
a2.set_title("(b) 可估的 4 个工具族（其余 16 族格子稀疏）：\nproduction 正、inspection/other 负——符号不统一", fontsize=10.5)
a2.grid(alpha=0.25, axis="x", ls="--")
fig.suptitle("图5  H2 的反向效应与它的族内剖面", fontsize=12, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(OUT / "custom_fig4_h2_families.png", bbox_inches="tight")
plt.close()

print("P032 figures done:", [p.name for p in sorted(OUT.glob("custom_*.png"))])
