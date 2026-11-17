# -*- coding: utf-8 -*-
"""P043 figures: T166 irrelevant candidate contamination (EXP-0187, wave-7)."""
import json, glob, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 300

fs = sorted(glob.glob("results_raw/EXP0187_wave7_design_*.json"))
art = json.load(open(fs[-1], encoding="utf-8"))
OUT = pathlib.Path("papers/P043_irrelevant_candidate_contamination/figures")
OUT.mkdir(parents=True, exist_ok=True)

C_SUP = "#27ae60"; C_OPP = "#c0392b"; C_ACC = "#2980b9"; C_NULL = "#95a5a6"
dr = art["descriptive_rates"]

# fig1: margin by contamination
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.5, 4.5))
mc = dr["mean_margin_by_contamination"]
a1.bar([0, 1], [mc["0"]["mean_margin"], mc["1"]["mean_margin"]],
       color=[C_ACC, C_OPP], alpha=0.88, width=0.45)
for x, k in [(0, "0"), (1, "1")]:
    a1.text(x, mc[k]["mean_margin"] + 0.04, f"{mc[k]['mean_margin']:.3f}\n(n={mc[k]['rows']:,})",
            ha="center", fontsize=10)
a1.set_xticks([0, 1])
a1.set_xticklabels(["无污染 query", "有污染 query"], fontsize=11)
a1.set_ylabel("BM25 margin 均值", fontsize=10)
a1.set_ylim(0, 2.8)
a1.set_title("(a) 污染 query 的 margin 更低\n（2.19 → 0.94，下降 57%）", fontsize=10.5)
a1.grid(alpha=0.25, axis="y", ls="--")

h1 = [m for m in art["models"] if m.get("hypothesis") == "H1"][0]
a2.errorbar([0], [h1["beta"]], yerr=[[h1["beta"] - h1["ci_lo"]], [h1["ci_hi"] - h1["beta"]]],
            fmt="D", color=C_OPP, ms=11, capsize=6, lw=2)
a2.axhline(0, color="black", lw=0.9, ls="--")
a2.text(0.015, h1["beta"],
        f"污染指标对 margin_z 的系数\nβ = {h1['beta']:+.4f}\n"
        f"95% CI [{h1['ci_lo']:.4f}, {h1['ci_hi']:.4f}]\n"
        f"LR χ2 = 1,852.1，p < 0.001\n"
        f"（判定 not_testable：前提底线未达标）",
        va="center", fontsize=9.3, color=C_OPP)
a2.set_xlim(-0.04, 0.08); a2.set_ylim(-0.80, -0.48)
a2.set_ylabel("系数", fontsize=10)
a2.set_title("(b) H1 系数：方向为负（污染拉低 margin）", fontsize=10.5)
a2.grid(alpha=0.25, axis="y", ls="--")
fig.suptitle("图1  污染 query 的排序质量：margin 更低但 H1 判 not_testable",
             fontsize=12, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(OUT / "custom_fig1_margin_contamination.png", bbox_inches="tight"); plt.close()

# fig2: irrelevant_above_gold distribution
fig, ax = plt.subplots(figsize=(9.6, 5.0))
iad = dr["irrelevant_above_gold_distribution"]
ks = sorted(iad.keys(), key=int)
vs = [iad[k] for k in ks]
ax.bar(range(len(ks)), vs, color=C_OPP, alpha=0.85, width=0.6)
for i, v in enumerate(vs):
    ax.text(i, v + 300, f"{v:,}", ha="center", fontsize=9.5)
ax.set_xticks(range(len(ks)))
ax.set_xticklabels([f"{k} 个" for k in ks], fontsize=10)
ax.set_ylabel("query 数", fontsize=10)
ax.set_ylim(0, 32000)
ax.set_title("图2  排在金标之上的无关候选数分布：\n大多数 query 无污染（28,689），但 2,953 条有 1-7 个无关候选排在金标之前",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="y", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig2_contamination_dist.png", bbox_inches="tight"); plt.close()

# fig3: per-config contamination share
fig, ax = plt.subplots(figsize=(8.5, 4.5))
cs = dr["contaminated_share_by_config"]
cfgs = list(cs.keys())
vals = [cs[c] * 100 for c in cfgs]
ax.bar(range(len(cfgs)), vals, color=C_ACC, alpha=0.88, width=0.45)
for i, v in enumerate(vals):
    ax.text(i, v + 0.15, f"{v:.2f}%", ha="center", fontsize=10)
ax.set_xticks(range(len(cfgs))); ax.set_xticklabels(cfgs, fontsize=10)
ax.set_ylabel("污染 query 占比（%）", fontsize=10)
ax.set_ylim(0, 13)
ax.set_title("图3  各配置的污染率：跨配置差异不大（8.7%–9.8%）",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="y", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig3_per_config.png", bbox_inches="tight"); plt.close()

# fig4: H3 Poisson coefficient
fig, ax = plt.subplots(figsize=(9.2, 4.5))
h3 = [m for m in art["models"] if m.get("hypothesis") == "H3"][0]
ax.barh([0], [h3["beta"]], height=0.4, color=C_SUP, alpha=0.85)
ax.errorbar(h3["beta"], 0,
            xerr=[[h3["beta"] - h3["ci_lo"]], [h3["ci_hi"] - h3["beta"]]],
            color="#145a32", capsize=6, lw=1.6, fmt="none")
ax.axvline(0, color="black", lw=0.9, ls="--")
ax.text(h3["ci_hi"] + 0.02, 0,
        f"候选数对排在金标之上\n的无关候选数的效应\n"
        f"β = {h3['beta']:+.4f}，p_holm < 0.001\n"
        f"（候选集越大，排在金标之上的\n无关候选越多——过载效应）",
        va="center", fontsize=9.5, color="#145a32")
ax.set_yticks([])
ax.set_xlabel("log_candidates 对 irrelevant_above_gold 的 Poisson 系数", fontsize=10)
ax.set_xlim(0.2, 0.65)
ax.set_title("图4  H3 判 supported：候选集越大，排在金标之上的\n无关候选越多——污染是过载现象",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="x", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig4_h3_poisson.png", bbox_inches="tight"); plt.close()

print("P043 figures done:", [p.name for p in sorted(OUT.glob("custom_*.png"))])
