# -*- coding: utf-8 -*-
"""P021 定制图：基于 T120 (同义词规范化, EXP-0147) 产物数据。

本文的个性：IR 经典药方（词汇控制/同义词映射）在机器检索上反向——
总体轻微变差（H1 partial, -0.0031）、一致性机制未发生（H2 null）、
伤害集中在词表错配处（H3 opposite, -0.5953）。四张图围绕"反向"展开。
"""
import json, glob, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 300

fs = sorted(glob.glob("results_raw/EXP0147_wave3_design_*.json"))
art = json.load(open(fs[-1], encoding="utf-8"))
OUT = pathlib.Path("papers/P021_synonym_normalisation_consistency/figures")
OUT.mkdir(parents=True, exist_ok=True)

C_PART = "#e67e22"
C_NULL = "#95a5a6"
C_OPP = "#c0392b"
C_ACC = "#2980b9"

models = {m["hypothesis"]: m for m in art["models"]}
h1, h2, h3 = models["H1"], models["H2"], models["H3"]

# ===== 图1 三假设判定森林 =====
fig, ax = plt.subplots(figsize=(10, 5.0))
# H1: hit1 差 + 秩差次证据（双刻度示意：分两行画）
rows = [
    ("H1 hit1 差", h1["mean_difference"], h1["ci"][0], h1["ci"][1], C_PART,
     f"判定 partial\nΔ={h1['mean_difference']:+.4f}，p_holm={h1['p_holm']:.3f}\n（CI 全在零负侧）"),
    ("H1 秩差（次证据）", h1["rank_difference"], h1["rank_difference_ci"][0], h1["rank_difference_ci"][1], "#8e44ad",
     f"金标秩平均变差 +{h1['rank_difference']:.4f} 位\np_boot={h1['rank_difference_p_boot']:.3f}"),
]
for i, (lab, b, lo, hi, c, note) in enumerate(rows):
    ax.plot([lo, hi], [i, i], color=c, lw=3, alpha=0.85)
    ax.plot(b, i, "D", color=c, ms=9)
    ax.text(hi + 0.0006, i, note, va="center", fontsize=8.8)
# H3 交互项（量级大，单独一行）
ax.plot([h3["ci_lo"], h3["ci_hi"]], [2.6, 2.6], color=C_OPP, lw=3, alpha=0.85)
ax.plot(h3["beta"], 2.6, "D", color=C_OPP, ms=9)
ax.text(h3["ci_hi"] + 0.03, 2.6,
        f"H3 交互（词表错配 × 规范化臂）\n判定 opposite：β={h3['beta']:+.4f}，p_holm={h3['p_holm']:.4f}\n（错配处伤害最大，与预测方向相反）",
        va="center", fontsize=8.8, color=C_OPP)
ax.axvline(0, color="black", lw=0.9, ls="--")
ax.set_yticks([0, 1, 2.6]); ax.set_yticklabels(["H1", "H1次", "H3"], fontsize=11)
ax.set_xlim(-1.3, 0.35)
ax.set_xlabel("效应量", fontsize=10)
ax.set_title("图1  三个预注册假设：全部站在经典药方的反面", fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="x", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig1_verdicts_forest.png", bbox_inches="tight")
plt.close()

# ===== 图2 一致性机制未发生：家族内秩距 =====
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.4))
iqr_b = h2["mean_iqr_baseline"]
iqr_s = h2["mean_iqr_synonym"]
a1.bar([0, 1], [iqr_b, iqr_s], color=["#95a5a6", C_ACC], alpha=0.88, width=0.45)
for x, v in [(0, iqr_b), (1, iqr_s)]:
    a1.text(x, v + 0.04, f"{v:.4f}", ha="center", fontsize=10)
a1.set_xticks([0, 1])
a1.set_xticklabels(["基线目录", "规范化目录"], fontsize=10)
a1.set_ylabel("家族内秩距（秩的 IQR，均值）", fontsize=10)
a1.set_ylim(2.9, 3.25)
a1.set_title("(a) 25,341 个 (动词词元, 宾语名词) 家族\n平均每家族 6.26 个成员：秩距几乎不动", fontsize=10.5)
a1.grid(alpha=0.25, axis="y", ls="--")

lo, hi = h2["ci"]
a2.plot([0, 0], [lo, hi], color=C_NULL, lw=4, alpha=0.8, solid_capstyle="round")
a2.plot(0, h2["mean_difference"], "D", color=C_NULL, ms=10)
a2.axhline(0, color="black", lw=0.9)
a2.text(0.06, h2["mean_difference"],
        f"Δ = {h2['mean_difference']:+.4f}\n95% CI [{lo:.4f}, {hi:.4f}]\np_holm={h2['p_holm']:.3f}",
        va="center", fontsize=9.5)
a2.text(0.06, lo - 0.0012, "一致性主张要求 Δ<0（规范化后家族内更整齐）：\n点估计反而为正——机制没有发生",
        va="top", fontsize=9, color="#555")
a2.set_xlim(-0.4, 0.9); a2.set_xticks([])
a2.set_ylabel("秩距差（规范化 - 基线）", fontsize=10)
a2.set_title("(b) H2 判 null：CI 跨零", fontsize=10.5)
a2.grid(alpha=0.25, axis="y", ls="--")
fig.suptitle("图2  一致性机制的直接测量：规范化没有让同族候选的排名更整齐",
             fontsize=12, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(OUT / "custom_fig2_family_spread.png", bbox_inches="tight")
plt.close()

# ===== 图3 H3 反向交互 =====
fig, ax = plt.subplots(figsize=(9.2, 5.0))
ax.bar([0], [0.4], width=0.4, color="#27ae60", alpha=0.55, hatch="//", edgecolor="white")
ax.text(0, 0.44, "预测：词表错配处\n规范化收益更集中（正向交互）", ha="center", fontsize=10, color="#1e8449")
ax.plot([1, 1], [h3["ci_lo"], h3["ci_hi"]], color=C_OPP, lw=4, alpha=0.85, solid_capstyle="round")
ax.plot(1, h3["beta"], "D", color=C_OPP, ms=11)
ax.axhline(0, color="black", lw=0.9)
ax.text(1.12, h3["beta"],
        f"实测：β = {h3['beta']:+.4f}\n95% CI [{h3['ci_lo']:.4f}, {h3['ci_hi']:.4f}]\np_holm={h3['p_holm']:.4f}\n（rank1_improved 的 logit，n={h3['rows_usable']} 条可判行）",
        va="center", fontsize=9.5, color=C_OPP)
ax.set_xticks([0, 1])
ax.set_xticklabels(["假设方向", "实测方向"], fontsize=10.5)
ax.set_ylabel("词表错配交互项的系数", fontsize=10)
ax.set_ylim(-1.35, 0.85)
ax.set_title("图3  H3 判 opposite：规范化没有帮到词表错配的查询——\n伤害恰恰集中在那里", fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="y", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig3_opposite_interaction.png", bbox_inches="tight")
plt.close()

# ===== 图4 覆盖与变更解剖 =====
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.4))
cov = art["coverage"]
n = art["n_queries"]
touch = cov["queries_the_arm_could_touch"]
changed = h1["n_changed_rows"]
stage_n = [n, touch, changed]
stage_lab = ["全部查询", "改写臂可触及", "hit1 实际变动"]
colors = ["#aab7b8", C_ACC, C_PART]
bars = a1.bar(range(3), stage_n, color=colors, alpha=0.9, width=0.55)
for i, (v, lab) in enumerate(zip(stage_n, stage_lab)):
    share = v / n * 100
    a1.text(i, v + 400, f"{v:,}\n({share:.1f}%)", ha="center", fontsize=9.5)
a1.set_xticks(range(3)); a1.set_xticklabels(stage_lab, fontsize=9.5)
a1.set_ylabel("查询数", fontsize=10)
a1.set_ylim(0, 26000)
a1.set_title("(a) 操纵的传播漏斗：触及 88.5%，\n但 rank-1 结果只变动 447 条（1.9%）", fontsize=10.5)
a1.grid(alpha=0.25, axis="y", ls="--")

h3rows = [h3["rows_usable"], h3["rows_no_change"], h3["rows_arm_did_not_touch"]]
a2.bar(range(3), h3rows, color=[C_OPP, "#aab7b8", "#d5d8dc"], alpha=0.9, width=0.55)
for i, v in enumerate(h3rows):
    a2.text(i, v + 300, f"{v:,}", ha="center", fontsize=10)
a2.set_xticks(range(3))
a2.set_xticklabels(["可判行\n（rank1 有变化）", "无变化行", "臂未触及行"], fontsize=9.5)
a2.set_ylabel("行数", fontsize=10)
a2.set_ylim(0, 24000)
a2.set_title("(b) H3 的估计基础：447 条可判行上\n的 logit（小样本，CI 宽）", fontsize=10.5)
a2.grid(alpha=0.25, axis="y", ls="--")
fig.suptitle("图4  操纵的传播解剖：规范化是低接触、低穿透的操纵", fontsize=12, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(OUT / "custom_fig4_coverage_anatomy.png", bbox_inches="tight")
plt.close()

print("P021 figures done:", [p.name for p in sorted(OUT.glob("custom_*.png"))])
