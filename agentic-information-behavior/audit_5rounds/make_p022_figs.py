# -*- coding: utf-8 -*-
"""P022 定制图：基于 T122 (判别性与可发现性, EXP-0148) 产物数据。

本文的个性：判别性（区别于完整性的功能性元数据质量）总体无效（H1 null、
H2 平阶梯），但作用集中在候选共享查询词汇的大目录（H3 supported 交互 0.323；
大目录层 0.292 vs 小目录层 -0.031）；双仪器分歧（词面 null vs 稠密 +0.1）。
"""
import json, glob, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 300

fs = sorted(glob.glob("results_raw/EXP0148_wave3_design_*.json"))
art = json.load(open(fs[-1], encoding="utf-8"))
OUT = pathlib.Path("papers/P022_discriminability_and_discoverability/figures")
OUT.mkdir(parents=True, exist_ok=True)

C_SUP = "#27ae60"
C_NULL = "#95a5a6"
C_ACC = "#2980b9"
C_DENSE = "#8e44ad"

models = {m["hypothesis"]: m for m in art["models"]}
h1, h2, h3 = models["H1"], models["H2"], models["H3"]
e06 = art["second_instrument"]
strata = {s["stratum"]: s for s in art["strata"]}

# ===== 图1 三假设判定森林 =====
fig, ax = plt.subplots(figsize=(10, 4.8))
rows = [
    ("H1 词面判别性 → 可达", h1["beta"], h1["ci_lo"], h1["ci_hi"], C_NULL,
     f"判定 null\nβ={h1['beta']:+.4f}，p={h1['p_holm']:.3f}"),
    ("H3 判别性 × 大目录", h3["beta"], h3["ci_lo"], h3["ci_hi"], C_SUP,
     f"判定 supported\nβ={h3['beta']:+.4f}，p_holm<0.001\n（拟合交互项，非两组斜率差）"),
]
for i, (lab, b, lo, hi, c, note) in enumerate(rows):
    ax.plot([lo, hi], [i, i], color=c, lw=3, alpha=0.85)
    ax.plot(b, i, "D", color=c, ms=9)
    ax.text(hi + 0.008, i, note, va="center", fontsize=8.8)
# H2 的 ΔAUROC 换行画
ax.plot([h2["ci"][0], h2["ci"][1]], [2.35, 2.35], color=C_NULL, lw=3, alpha=0.85)
ax.plot(h2["delta"], 2.35, "D", color=C_NULL, ms=9)
ax.axvline(0, color="black", lw=0.9, ls="--")
ax.text(h2["ci"][1] + 0.004, 2.35,
        f"H2 增量 ΔAUROC = {h2['delta']:+.4f}\nCI [{h2['ci'][0]:.4f}, {h2['ci'][1]:.4f}]，p_holm={h2['p_holm']:.2f}\n判定 null（支持线 0.02 远在右侧）",
        va="center", fontsize=8.8)
ax.set_yticks([0, 1, 2.35]); ax.set_yticklabels(["H1", "H3", "H2"], fontsize=11)
ax.set_xlim(-0.06, 0.56)
ax.set_xlabel("系数 / AUROC 增量", fontsize=10)
ax.set_title("图1  三个预注册假设：判别性总体无效，只在拥挤的目录里起作用",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="x", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig1_verdicts.png", bbox_inches="tight")
plt.close()

# ===== 图2 平坦的 AUROC 阶梯 =====
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.4), gridspec_kw={"width_ratios": [1.2, 1]})
lad = art["ladder"]
rungs = [l["rung"] for l in lad]
aurocs = [l["auroc"] for l in lad]
ks = [l["k"] for l in lad]
a1.plot([0, 1], aurocs, "o-", color=C_ACC, lw=2, ms=9)
for x, (a, k) in enumerate(zip(aurocs, ks)):
    a1.text(x, a + 0.0006, f"{a:.4f}\n(k={k})", ha="center", fontsize=9.5)
a1.set_xticks([0, 1])
a1.set_xticklabels(["完整性集\n(参数数/枚举/动词/长度)", "+ 词面判别性"], fontsize=9.5)
a1.set_ylabel("AUROC", fontsize=10)
a1.set_ylim(0.5840, 0.5895)
a1.set_title("(a) 阶梯几乎水平：加入判别性\nAUROC 只动 0.0018", fontsize=10.5)
a1.grid(alpha=0.25, axis="y", ls="--")

lo, hi = h2["ci"]
a2.bar([0], [h2["delta"]], width=0.4, color=C_NULL, alpha=0.85)
a2.errorbar(0, h2["delta"], yerr=[[h2["delta"] - lo], [hi - h2["delta"]]],
            color="#555", capsize=6, lw=1.4)
a2.axhline(0.02, color=C_SUP, lw=1.3, ls="--")
a2.text(0.22, 0.0204, "冻结支持线 0.02", fontsize=9, color=C_SUP)
a2.axhline(0, color="black", lw=0.9)
a2.text(0.22, 0.0012, f"Δ = {h2['delta']:+.4f}\np_boot={h2['p_boot']:.2f}", fontsize=9.5)
a2.set_xticks([]); a2.set_xlim(-0.4, 0.8)
a2.set_ylabel("ΔAUROC（+判别性 - 完整性集）", fontsize=10)
a2.set_ylim(-0.004, 0.028)
a2.set_title("(b) 增量与支持线差一个数量级", fontsize=10.5)
a2.grid(alpha=0.25, axis="y", ls="--")
fig.suptitle("图2  H2 的平坦阶梯：判别性不比完整性指标多携带任何可达性信息",
             fontsize=12, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(OUT / "custom_fig2_flat_ladder.png", bbox_inches="tight")
plt.close()

# ===== 图3 目录规模分层：判别性的拥挤条件 =====
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.5))
sml, lrg = strata["small_catalogue"], strata["large_catalogue"]
a1.bar([0, 1], [sml["reachable_rate"] * 100, lrg["reachable_rate"] * 100],
       color=["#aab7b8", C_ACC], alpha=0.88, width=0.45)
for x, s in [(0, sml), (1, lrg)]:
    a1.text(x, s["reachable_rate"] * 100 + 0.8,
            f"{s['reachable_rate']*100:.1f}%\n(n={s['n_queries']:,})",
            ha="center", fontsize=9.5)
a1.set_xticks([0, 1]); a1.set_xticklabels(["小目录查询", "大目录查询"], fontsize=10)
a1.set_ylabel("rank-1 可达率（%）", fontsize=10)
a1.set_ylim(0, 100)
a1.set_title("(a) 大目录天然更难：可达率低 9.4 个百分点\n（拥挤本身是代价）", fontsize=10.5)
a1.grid(alpha=0.25, axis="y", ls="--")

for i, (lab, s, c) in enumerate([("小目录", sml, "#aab7b8"), ("大目录", lrg, C_ACC)]):
    a2.plot([s["ci_lo"], s["ci_hi"]], [i, i], color=c, lw=3, alpha=0.85)
    a2.plot(s["beta"], i, "D", color=c, ms=10)
    a2.text(s["ci_hi"] + 0.012, i, f"β={s['beta']:+.4f}", va="center", fontsize=9.5)
a2.axvline(0, color="black", lw=0.9, ls="--")
a2.set_yticks([0, 1]); a2.set_yticklabels(["小目录", "大目录"], fontsize=11)
a2.set_xlabel("判别性斜率（描述性分层）", fontsize=10)
a2.set_xlim(-0.14, 0.48)
a2.set_title("(b) 判别性斜率：小目录为零，大目录显著为正\n——判别性是拥挤场景的货币", fontsize=10.5)
a2.grid(alpha=0.25, axis="x", ls="--")
fig.suptitle("图3  H3 的调节结构：判别性只在候选共享查询词汇的大目录里兑现",
             fontsize=12, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(OUT / "custom_fig3_catalogue_size.png", bbox_inches="tight")
plt.close()

# ===== 图4 双仪器对照 =====
fig, ax = plt.subplots(figsize=(9.2, 4.8))
rows = [("词面判别性\n(IDF 加权相异度)", h1["beta"], h1["ci_lo"], h1["ci_hi"], C_NULL,
         f"H1 主仪器：判定 null\nβ={h1['beta']:+.4f}"),
        ("稠密判别性\n(1-平均余弦，E06)", e06["beta"], e06["ci_lo"], e06["ci_hi"], C_DENSE,
         f"第二仪器：β={e06['beta']:+.4f}\nCI [{e06['ci_lo']:.4f}, {e06['ci_hi']:.4f}]，p={e06['p_raw']:.1e}")]
for i, (lab, b, lo, hi, c, note) in enumerate(rows):
    ax.plot([lo, hi], [i, i], color=c, lw=3, alpha=0.85)
    ax.plot(b, i, "D", color=c, ms=9)
    ax.text(hi + 0.008, i, note, va="center", fontsize=9)
ax.axvline(0, color="black", lw=0.9, ls="--")
ax.set_yticks([0, 1]); ax.set_yticklabels(["词面", "稠密"], fontsize=11)
ax.set_xlabel("对可达性的系数", fontsize=10)
ax.set_xlim(-0.06, 0.22)
ax.text(0.13, 0.5,
        f"两仪器相关：Spearman ρ = {e06['spearman_with_lexical']:.4f}\n（测的是同一构念，兑现通道不同）",
        fontsize=9.5, color="#555",
        bbox=dict(boxstyle="round,pad=0.35", fc="#f4f6f7", ec="#aab7b8"))
ax.set_title("图4  双仪器对照：词面判别性无效，稠密判别性正相关——\n构念的效度取决于它与检索栈的通道是否同源",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="x", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig4_two_instruments.png", bbox_inches="tight")
plt.close()

print("P022 figures done:", [p.name for p in sorted(OUT.glob("custom_*.png"))])
