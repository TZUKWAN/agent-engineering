# -*- coding: utf-8 -*-
"""P040 定制图：基于 T162 (可供性语言与选择, EXP-0184, wave-7) 产物数据。

本文的个性：可供性动词密度与参数命名双双无效（H1/H2 双 null），
长度才是真正的信号（length_alone β=-0.208 显著），而 H3 的联合模型
被 not_specific 判定封存（参数项 p=0.13、长度项仍 -0.217）。
附加：密度四分位的 fail@1 呈 U 型（d2 最低 15.7%）。
"""
import json, glob, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 300

fs = sorted(glob.glob("results_raw/EXP0184_wave7_design_*.json"))
art = json.load(open(fs[-1], encoding="utf-8"))
OUT = pathlib.Path("papers/P040_affordance_language_and_selection/figures")
OUT.mkdir(parents=True, exist_ok=True)

C_SUP = "#27ae60"
C_OPP = "#c0392b"
C_ACC = "#2980b9"
C_NULL = "#95a5a6"

models = {m["hypothesis"]: m for m in art["models"]}
h1, h2, h3 = models["H1"], models["H2"], models["H3"]
dr = art["descriptive_rates"]
dq = dr["fail_at_1_by_density_quartile"]
mq = dr["margin_by_density_quartile"]
pp = dr["fail_at_1_by_parameter_presence"]

# ===== 图1 三假设判定森林 =====
fig, ax = plt.subplots(figsize=(10.5, 4.8))
rows = [
    ("H1 可供性密度", h1["beta"], h1["ci_lo"], h1["ci_hi"], C_NULL,
     f"判定 null\nβ={h1['beta']:+.4f}，p_holm=1.0"),
    ("H2 参数命名", h2["beta"], h2["ci_lo"], h2["ci_hi"], C_NULL,
     f"判定 null\nβ={h2['beta']:+.4f}，p_holm=1.0"),
    ("H3 联合模型参数项", h3["joint_model_parameter_term"]["beta"],
     h3["joint_model_parameter_term"]["ci_lo"], h3["joint_model_parameter_term"]["ci_hi"], C_ACC,
     f"判定 not_specific\n参数项 β={h3['joint_model_parameter_term']['beta']:+.4f}，p=0.13\n（长度才是信号：-0.217***）"),
]
for i, (lab, b, lo, hi, c, note) in enumerate(rows):
    ax.plot([lo, hi], [i, i], color=c, lw=3, alpha=0.85)
    ax.plot(b, i, "D", color=c, ms=9)
    ax.text(hi + 0.012, i, note, va="center", fontsize=8.6)
ax.axvline(0, color="black", lw=0.9, ls="--")
ax.set_yticks([0, 1, 2]); ax.set_yticklabels(["H1", "H2", "H3"], fontsize=11)
ax.set_xlim(-0.34, 0.42)
ax.set_xlabel("fail_at_1 的 logit 系数（负 = 更少缺席，query 聚类稳健）", fontsize=10)
ax.set_title("图1  三个预注册假设：可供性与参数双 null，长度才是真信号",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="x", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig1_verdicts.png", bbox_inches="tight")
plt.close()

# ===== 图2 密度四分位的 U 型 fail@1 =====
fig, ax = plt.subplots(figsize=(9.4, 5.0))
qs = list(dq.keys())
qlab = {"d1_tersest": "Q1 最简", "d2": "Q2", "d3": "Q3", "d4_densest": "Q4 最密"}
rates = [dq[q]["rate"] * 100 for q in qs]
cis = [dq[q]["ci"] for q in qs]
err_lo = [r - c[0] * 100 for r, c in zip(rates, cis)]
err_hi = [c[1] * 100 - r for r, c in zip(rates, cis)]
ax.errorbar(range(4), rates, yerr=[err_lo, err_hi], fmt="o", color=C_ACC,
            ms=10, capsize=6, lw=2, zorder=3)
for i, r in enumerate(rates):
    ax.text(i, r + 0.8, f"{r:.1f}%", ha="center", fontsize=10)
ax.set_xticks(range(4))
ax.set_xticklabels([qlab[q] for q in qs], fontsize=10.5)
ax.set_ylabel("fail@1（金标未进 rank-1，%）", fontsize=10)
ax.set_ylim(12, 24)
ax.set_title("图2  密度四分位的 U 型：最简与最密的缺席率都高于中间档\n"
             "（U 型的曲线解释了线性 H1 为何是 null——两端的效应互抵）",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="y", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig2_u_shape.png", bbox_inches="tight")
plt.close()

# ===== 图3 长度才是信号 =====
fig, ax = plt.subplots(figsize=(9.4, 4.8))
la = h3["length_alone"]
lj = h3["length_in_the_joint_model"]
ax.plot([la["ci_lo"], la["ci_hi"]], [0, 0], color=C_OPP, lw=4, alpha=0.85, solid_capstyle="round")
ax.plot(la["beta"], 0, "D", color=C_OPP, ms=11)
ax.plot([lj["ci_lo"], lj["ci_hi"]], [1, 1], color=C_OPP, lw=4, alpha=0.85, solid_capstyle="round")
ax.plot(lj["beta"], 1, "D", color=C_OPP, ms=11)
ax.axvline(0, color="black", lw=0.9, ls="--")
ax.text(la["ci_lo"] - 0.008, 0, f"单独入模：β={la['beta']:+.4f}***", va="center", ha="right", fontsize=9.5, color=C_OPP)
ax.text(lj["ci_lo"] - 0.008, 1, f"联合模型：β={lj['beta']:+.4f}***", va="center", ha="right", fontsize=9.5, color=C_OPP)
ax.set_yticks([0, 1]); ax.set_yticklabels(["长度单独", "长度（联合）"], fontsize=11)
ax.set_xlim(-0.30, 0.02)
ax.set_xlabel("描述长度对 fail_at_1 的系数", fontsize=10)
ax.set_title("图3  真信号是长度：描述越长，金标缺席 rank-1 的几率越低\n（单独与联合两种口径下都显著，符号稳定）",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="x", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig3_length_signal.png", bbox_inches="tight")
plt.close()

# ===== 图4 BM25 margin 的密度剖面 =====
fig, ax = plt.subplots(figsize=(9.2, 4.8))
mq_labs = [qlab[q] for q in qs]
margins = [mq[q]["mean_margin"] for q in qs]
ax.bar(range(4), margins, color=[C_NULL, C_SUP, C_ACC, C_NULL], alpha=0.88, width=0.5)
for i, m in enumerate(margins):
    ax.text(i, m + 0.05, f"{m:.2f}", ha="center", fontsize=10)
ax.set_xticks(range(4)); ax.set_xticklabels(mq_labs, fontsize=10.5)
ax.set_ylabel("BM25 margin 均值（第一名与第二名的分差）", fontsize=10)
ax.set_ylim(0, 3.8)
ax.set_title("图4  BM25 分差剖面：Q2 的 margin 最大且 fail@1 最低——\n适中的密度给出最稳定的排序",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="y", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig4_margin_profile.png", bbox_inches="tight")
plt.close()

print("P040 figures done:", [p.name for p in sorted(OUT.glob("custom_*.png"))])
