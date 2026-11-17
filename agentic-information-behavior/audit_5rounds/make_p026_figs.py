# -*- coding: utf-8 -*-
"""P026 定制图：基于 T127 (充分性语言与停止, EXP-0157, wave-4) 产物数据。

本文的个性：充分性宣称与停止的原始联结 3.5 倍，但增量效度 null（H1）；
宣称后的停止搜集了更多信息（H2 opposite, +1.71）——语言是收尾的报道，不是收尾的原因。
"""
import json, glob, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 300

fs = sorted(glob.glob("results_raw/EXP0157_wave4_design_*.json"))
art = json.load(open(fs[-1], encoding="utf-8"))
OUT = pathlib.Path("papers/P026_sufficiency_language_and_stopping/figures")
OUT.mkdir(parents=True, exist_ok=True)

C_SUP = "#27ae60"
C_NULL = "#95a5a6"
C_OPP = "#c0392b"
C_ACC = "#2980b9"

models = {m["hypothesis"]: m for m in art["models"]}
h1, h2, h3 = models["H1"], models["H2"], models["H3"]
desc = art["descriptive_rates"]
strata = art["strata"]

# ===== 图1 描述性：停止率与先验检验 =====
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.4))
sc = desc["stop_rate_by_claim"]
a1.bar([0, 1], [sc["0"]["rate"] * 100, sc["1"]["rate"] * 100],
       color=["#aab7b8", C_ACC], alpha=0.88, width=0.45)
for x, k in [(0, "0"), (1, "1")]:
    a1.text(x, sc[k]["rate"] * 100 + 0.3, f"{sc[k]['rate']*100:.2f}%\n(n={sc[k]['n']:,})",
            ha="center", fontsize=9.5)
a1.set_xticks([0, 1]); a1.set_xticklabels(["无充分性宣称", "有充分性宣称"], fontsize=10)
a1.set_ylabel("该 turn 终止轨迹的比率（%）", fontsize=10)
a1.set_ylim(0, 18)
a1.set_title("(a) 原始联结：宣称后停止率 3.5 倍\n（但这是共存的表象，见图 2）", fontsize=10.5)
a1.grid(alpha=0.25, axis="y", ls="--")

mi = desc["mean_prior_inspections_by_claim"]
a2.bar([0, 1], [mi["0"], mi["1"]], color=["#aab7b8", C_SUP], alpha=0.88, width=0.45)
for x, k in [(0, "0"), (1, "1")]:
    a2.text(x, mi[k] + 0.04, f"{mi[k]:.2f} 次", ha="center", fontsize=10)
a2.set_xticks([0, 1]); a2.set_xticklabels(["其他停止\n（无宣称）", "宣称后停止"], fontsize=10)
a2.set_ylabel("停止前的平均检验调用次数", fontsize=10)
a2.set_ylim(0, 3.2)
a2.set_title("(b) 宣称后的停止搜集了更多信息\n（2.57 vs 1.72 次——与过早终止相反）", fontsize=10.5)
a2.grid(alpha=0.25, axis="y", ls="--")
fig.suptitle("图2  充分性宣称与停止的两个描述性切面", fontsize=12, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(OUT / "custom_fig1_descriptives.png", bbox_inches="tight")
plt.close()

# ===== 图2 H1：原始差距 vs 增量 null =====
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.5, 4.6), gridspec_kw={"width_ratios": [1, 1.25]})
raw_gap = (sc["1"]["rate"] - sc["0"]["rate"]) * 100
a1.bar([0], [raw_gap], width=0.4, color=C_ACC, alpha=0.88)
a1.text(0, raw_gap + 0.25, f"+{raw_gap:.1f} 个百分点", ha="center", fontsize=11, fontweight="bold")
a1.set_xticks([]); a1.set_xlim(-0.5, 0.5)
a1.set_ylabel("宣称后停止率的原始提升", fontsize=10)
a1.set_ylim(0, 13)
a1.set_title("(a) 不控制时：联结巨大", fontsize=10.5)
a1.grid(alpha=0.25, axis="y", ls="--")

a2.plot([h1["ci_lo"], h1["ci_hi"]], [0, 0], color=C_NULL, lw=4, alpha=0.85, solid_capstyle="round")
a2.plot(h1["beta"], 0, "D", color=C_NULL, ms=10)
a2.axvline(0, color="black", lw=0.9, ls="--")
a2.text(h1["ci_hi"] + 0.008, 0,
        f"控制证据状态后：β = {h1['beta']:+.4f}\n95% CI [{h1['ci_lo']:.4f}, {h1['ci_hi']:.4f}]\n"
        f"p_holm = {h1['p_holm']:.3f}（判定 null）\nLR χ2 = 5.22（df=1，边缘）",
        va="center", fontsize=9.3)
a2.set_yticks([]); a2.set_xlim(-0.26, 0.16)
a2.set_xlabel("充分性宣称对停止的增量系数", fontsize=10)
a2.set_ylim(-0.6, 0.6)
a2.set_title("(b) 控制后：增量消失——宣称是\n证据状态的转述，不是额外的停止原因", fontsize=10.5)
a2.grid(alpha=0.25, axis="x", ls="--")
fig.suptitle("图3  H1 的两种口径：联结全部被证据状态吸收", fontsize=12, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(OUT / "custom_fig2_h1_two_scalings.png", bbox_inches="tight")
plt.close()

# ===== 图3 H2 opposite =====
fig, ax = plt.subplots(figsize=(9.2, 4.8))
ax.barh([0], [h2["beta"]], height=0.42, color=C_SUP, alpha=0.85)
ax.errorbar(h2["beta"], 0,
            xerr=[[h2["beta"] - h2["ci_lo"]], [h2["ci_hi"] - h2["beta"]]],
            color="#145a32", capsize=6, lw=1.5, fmt="none")
ax.axvline(0, color="black", lw=0.9, ls="--")
ax.text(h2["ci_hi"] + 0.06, 0,
        f"宣称后停止相对其他停止的先验检验差\nβ = {h2['beta']:+.4f}（正 = 更多先验检验）\n"
        f"95% CI [{h2['ci_lo']:.4f}, {h2['ci_hi']:.4f}]，p_holm = {h2['p_holm']:.3f}\n"
        f"（931 个宣称停止 vs 5,910 个其他停止）",
        va="center", fontsize=9.5, color="#145a32")
ax.set_yticks([])
ax.set_xlabel("先验检验次数的对比系数", fontsize=10)
ax.set_xlim(0, 3.6)
ax.set_title("图4  H2 判 opposite：充分性宣称标记的是\"取证充分\"的停止，\n不是\"取证不足\"的过早放弃",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="x", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig3_h2_opposite.png", bbox_inches="tight")
plt.close()

# ===== 图4 任务类目分层 =====
fig, ax = plt.subplots(figsize=(9.6, 4.8))
rows = [(s["stratum"], s) for s in strata]
for i, (name, s) in enumerate(rows):
    c = C_SUP if (s["p"] is not None and s["p"] < 0.05 and s["beta"] > 0) else (
        C_OPP if (s["p"] is not None and s["p"] < 0.05 and s["beta"] < 0) else C_NULL)
    ax.plot([s["ci_lo"], s["ci_hi"]], [i, i], color=c, lw=3, alpha=0.85)
    ax.plot(s["beta"], i, "D", color=c, ms=9)
    star = " *" if (s["p"] is not None and s["p"] < 0.05) else ""
    ax.text(s["ci_hi"] + 0.03, i, f"β={s['beta']:+.4f}{star}  (n={s['rows']:,})", va="center", fontsize=8.8)
ax.axvline(0, color="black", lw=0.9, ls="--")
ax.set_yticks(range(len(rows)))
ax.set_yticklabels([r[0].replace("_", " ").title() for r in rows], fontsize=9.5)
ax.set_xlabel("充分性宣称 × 停止的类目分层系数（描述性）", fontsize=10)
ax.set_xlim(-1.8, 1.2)
ax.set_title("图5  H3 的类目剖面：多数类目内联结弱化，个别类目显著为负\n（描述性分层，不进判定族；* p<0.05）",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="x", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig4_category_strata.png", bbox_inches="tight")
plt.close()

print("P026 figures done:", [p.name for p in sorted(OUT.glob("custom_*.png"))])
