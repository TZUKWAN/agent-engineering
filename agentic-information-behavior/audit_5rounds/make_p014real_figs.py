# -*- coding: utf-8 -*-
"""P014 定制图：基于 T114 (语义原型偏置, EXP-0138) 产物数据。

本文的个性：原型中心性是"诱饵属性"——H1（对全体候选）为 null，H2（仅非金标
候选）supported（+0.5625），补充分析 S1（金标归属）反向（-0.1441）。
四张图围绕"位置与正确性的分离"展开。
"""
import json, glob, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 300

fs = sorted(glob.glob("results_raw/EXP0138_wave2_design_*.json"))
art = json.load(open(fs[-1], encoding="utf-8"))
OUT = pathlib.Path("papers/P014_semantic_prototype_bias/figures")
OUT.mkdir(parents=True, exist_ok=True)

C_SUP = "#27ae60"
C_NULL = "#95a5a6"
C_DECOY = "#c0392b"
C_GOLD = "#b8860b"
C_ACC = "#2980b9"

models = {m["hypothesis"]: m for m in art["models"]}
h1, h2, s1 = models["H1"], models["H2"], models["S1_supplementary"]
h3row = [m for m in art["models"] if m["hypothesis"] == "H3"][0]

# ===== 图1 三系数森林：全体 / 非金标 / 金标归属 =====
fig, ax = plt.subplots(figsize=(9.8, 4.6))
rows = [
    ("H1 全体候选\nat_rank1 ~ centr_z", h1["beta"], h1["ci_lo"], h1["ci_hi"], C_NULL,
     f"判定 null\nβ={h1['beta']:+.4f}, p_holm={h1['p_holm']:.3f}"),
    ("H2 仅非金标候选\nat_rank1 ~ hi", h2["beta"], h2["ci_lo"], h2["ci_hi"], C_SUP,
     f"判定 supported\nβ={h2['beta']:+.4f}, p_holm<0.001"),
    ("S1 补充（非冻结）\ngold ~ centr_z", s1["beta"], s1["ci_lo"], s1["ci_hi"], C_DECOY,
     f"补充估计\nβ={s1['beta']:+.4f}, p_raw={s1['p_raw']:.1e}"),
]
for i, (lab, b, lo, hi, c, note) in enumerate(rows):
    ax.plot([lo, hi], [i, i], color=c, lw=3, alpha=0.85)
    ax.plot(b, i, "D", color=c, ms=9)
    ax.text(hi + 0.02, i, note, va="center", fontsize=8.8, color="#333")
ax.axvline(0, color="black", lw=0.9, ls="--")
ax.set_yticks([0, 1, 2])
ax.set_yticklabels(["H1", "H2", "S1"], fontsize=11)
ax.set_xlabel("系数（logit 标度）与 95% CI", fontsize=10)
ax.set_xlim(-0.42, 1.05)
ax.set_title("图1  原型中心性的三张面孔：对全体无效、对非金标候选有效、对金标归属为负",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="x", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig1_three_faces.png", bbox_inches="tight")
plt.close()

# ===== 图2 诱饵表：非金标候选中高/低原型占据 rank1 的比例 =====
tab = art["fisher_decoy_table"]
low = [r for r in tab if r["hi"] == 0][0]
high = [r for r in tab if r["hi"] == 1][0]
p_low = low["at_rank1"] / low["n"] * 100
p_high = high["at_rank1"] / high["n"] * 100
fig, ax = plt.subplots(figsize=(8.6, 4.9))
bars = ax.bar([0, 1], [p_low, p_high], color=["#aab7b8", C_DECOY], alpha=0.88, width=0.5)
for x, r in [(0, low), (1, high)]:
    ax.text(x, r["at_rank1"] / r["n"] * 100 + 0.06,
            f"{r['at_rank1']:,} / {r['n']:,}\n= {r['at_rank1']/r['n']*100:.2f}%",
            ha="center", fontsize=9.5)
ax.set_xticks([0, 1])
ax.set_xticklabels(["低原型非金标候选", "高原型非金标候选"], fontsize=10)
ax.set_ylabel("占据 rank-1 的比例（%）", fontsize=10)
ax.set_ylim(0, 4.4)
ax.text(0.5, 3.9,
        f"Fisher 精确检验 p = {art['p_fisher']:.1e}\n"
        f"优势比 OR = {art['odds_ratio']:.4f}，95% CI [{art['ratio_ci'][0]:.4f}, {art['ratio_ci'][1]:.4f}]",
        ha="center", fontsize=10, color=C_DECOY,
        bbox=dict(boxstyle="round,pad=0.4", fc="#fdf2e9", ec=C_DECOY, alpha=0.9))
ax.set_title("图2  诱饵效应的直接测量：同样不是答案，长得像目录原型的候选\n"
             "占据 rank-1 的几率高约 43%", fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="y", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig2_decoy_table.png", bbox_inches="tight")
plt.close()

# ===== 图3 分歧集普查：中心性与查询适配的秩相关分布 =====
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.4))
a1.bar([0], [h3row["n_queries_disagreeing"]], color=C_ACC, alpha=0.85, width=0.45)
a1.text(0, h3row["n_queries_disagreeing"] + 300,
        f"{h3row['n_queries_disagreeing']:,} 条查询\n（候选行 {h3row['disagreement_rows']:,}）",
        ha="center", fontsize=10)
a1.axhline(200, color=C_DECOY, lw=1.4, ls="--")
a1.text(0.22, 900, "kill gate 下限 200 条", fontsize=9, color=C_DECOY)
a1.set_xlim(-0.6, 0.6)
a1.set_xticks([])
a1.set_ylabel("查询数", fontsize=10)
a1.set_title("(a) 分歧集规模：远超 gate 下限，\n可作刻画性分析", fontsize=10.5)
a1.grid(alpha=0.25, axis="y", ls="--")

med = h3row["spearman_centrality_vs_query_fit"]
iqr = h3row["spearman_iqr"]
a2.axhline(0, color="black", lw=0.9)
a2.plot([0, 0], [iqr[0], iqr[1]], color=C_ACC, lw=6, alpha=0.35, solid_capstyle="round")
a2.plot(0, med, "D", color=C_ACC, ms=10)
a2.text(0.06, med, f"中位 Spearman ρ = {med:.4f}", va="center", fontsize=9.5)
a2.text(0.06, iqr[1] - 0.02, f"IQR [{iqr[0]:.4f}, {iqr[1]:.4f}]", va="top", fontsize=9.5, color="#555")
a2.text(0.06, iqr[0] + 0.01, "四分位距跨越零：多数查询弱耦合，\n少数查询强耦合甚至反向",
        va="bottom", fontsize=9, color="#555")
a2.set_xlim(-0.4, 0.9)
a2.set_xticks([])
a2.set_ylabel("中心性 vs 查询适配的秩相关（每查询）", fontsize=10)
a2.set_title("(b) 耦合强度：弱正、跨度极大——\n分歧不是少数查询的怪癖", fontsize=10.5)
a2.grid(alpha=0.25, axis="y", ls="--")
fig.suptitle("图3  H3 分歧集普查（刻画，无抽样检验）", fontsize=12, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(OUT / "custom_fig3_disagreement_census.png", bbox_inches="tight")
plt.close()

# ===== 图4 位置与正确性的分离 =====
fig, ax = plt.subplots(figsize=(9.2, 5.0))
# 左：位置（H2 OR），右：正确性（S1 负系数）
ax.bar([0], [art["odds_ratio"]], width=0.42, color=C_DECOY, alpha=0.85)
ax.errorbar(0, art["odds_ratio"],
            yerr=[[art["odds_ratio"] - art["ratio_ci"][0]], [art["ratio_ci"][1] - art["odds_ratio"]]],
            color="#641e16", capsize=6, lw=1.6)
ax.axhline(1.0, color="black", lw=0.9, ls="--")
ax.text(0.24, art["odds_ratio"], f"位置：高原型非金标候选\n占 rank-1 的优势比\nOR = {art['odds_ratio']:.4f}",
        va="center", fontsize=9.5, color=C_DECOY)
ax2 = ax.twinx()
ax2.bar([1], [s1["beta"]], width=0.42, color=C_GOLD, alpha=0.85)
ax2.errorbar(1, s1["beta"],
             yerr=[[s1["beta"] - s1["ci_lo"]], [s1["ci_hi"] - s1["beta"]]],
             color="#5d4037", capsize=6, lw=1.6)
ax2.axhline(0, color="black", lw=0.9, ls="--")
ax2.text(0.72, s1["beta"] + 0.025, f"正确性：高原型候选进入\n发布选择的系数\nβ = {s1['beta']:+.4f}",
         va="center", ha="right", fontsize=9.5, color=C_GOLD)
ax.set_xticks([0, 1])
ax.set_xticklabels(["位置效应（H2，非金标内）", "正确性效应（S1，全体）"], fontsize=10)
ax.set_ylabel("优势比（OR，左轴）", fontsize=10, color=C_DECOY)
ax2.set_ylabel("logit 系数（右轴）", fontsize=10, color=C_GOLD)
ax.set_ylim(0.8, 1.75)
ax2.set_ylim(-0.30, 0.10)
ax.set_title("图4  中心性买得到位置、买不到正确性：原型偏置作为诱饵机制的完整画面",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.2, axis="y", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig4_position_vs_correctness.png", bbox_inches="tight")
plt.close()

print("P014 figures done:", [p.name for p in sorted(OUT.glob("custom_*.png"))])
