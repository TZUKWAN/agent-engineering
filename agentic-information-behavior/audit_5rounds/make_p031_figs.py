# -*- coding: utf-8 -*-
"""P031 定制图：基于 T135 (解释连贯性与证据缺口, EXP-0169, wave-5) 产物数据。

本文的个性：三重 null 的"担忧未成真"论文——多步因果链不隐藏证据缺口
（H1 null），不推高停止（H2 null），长度分层不复现符号（H3）。
"""
import json, glob, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 300

fs = sorted(glob.glob("results_raw/EXP0169_wave5_design_*.json"))
art = json.load(open(fs[-1], encoding="utf-8"))
OUT = pathlib.Path("papers/P031_explanatory_coherence_and_evidential_gaps/figures")
OUT.mkdir(parents=True, exist_ok=True)

C_SUP = "#27ae60"
C_NULL = "#95a5a6"
C_ACC = "#2980b9"

models = {m["hypothesis"]: m for m in art["models"]}
h1, h2, h3 = models["H1"], models["H2"], models["H3"]
chainlen = art["descriptive_rates"]["mean_overlap_by_chain_length"]

# ===== 图1 三假设判定森林（三重 null） =====
fig, ax = plt.subplots(figsize=(10, 4.6))
rows = [
    ("H1 因果链 → 重叠（隐藏方向）", h1["beta"], h1["ci_lo"], h1["ci_hi"],
     f"判定 null\nβ={h1['beta']:+.4f}，p_holm=1.0\n（隐藏假说的方向未获支持）"),
    ("H2 因果链 → 停止", h2["beta"], h2["ci_lo"], h2["ci_hi"],
     f"判定 null\nβ={h2['beta']:+.4f}，p_holm={h2['p_holm']:.3f}\n（自我支撑的收官未出现）"),
]
for i, (lab, b, lo, hi, note) in enumerate(rows):
    ax.plot([lo, hi], [i, i], color=C_NULL, lw=3.5, alpha=0.9, solid_capstyle="round")
    ax.plot(b, i, "D", color=C_NULL, ms=10)
    ax.text(hi + 0.006, i, note, va="center", fontsize=8.8)
ax.axvline(0, color="black", lw=0.9, ls="--")
ax.set_yticks([0, 1]); ax.set_yticklabels(["H1", "H2"], fontsize=11)
ax.set_xlim(-0.11, 0.40)
ax.set_xlabel("系数（聚类稳健）", fontsize=10)
ax.set_title("图1  两个主假设的判定：CI 都骑在零上——担忧未成真",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="x", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig1_nulls.png", bbox_inches="tight")
plt.close()

# ===== 图2 链长与重叠：平坦的曲线 =====
fig, ax = plt.subplots(figsize=(9.2, 4.9))
lens = sorted(chainlen.keys(), key=int)
vals = [chainlen[k]["mean"] * 100 for k in lens]
ns = [chainlen[k]["n"] for k in lens]
ax.plot(range(len(lens)), vals, "o-", color=C_ACC, lw=2, ms=9)
for i, (v, n) in enumerate(zip(vals, ns)):
    ax.text(i, v + 0.12, f"{v:.2f}%\n(n={n:,})", ha="center", fontsize=9)
ax.set_xticks(range(len(lens)))
ax.set_xticklabels([f"{k} 个连接词" for k in lens], fontsize=10)
ax.set_ylabel("与已返回观察的词汇重叠率（%）", fontsize=10)
ax.set_ylim(17.4, 21.6)
ax.axhline(np.mean(vals), color=C_NULL, lw=1, ls=":")
ax.text(len(lens) - 0.4, np.mean(vals) + 0.1, f"均值 {np.mean(vals):.2f}%", fontsize=9, color=C_NULL, ha="right")
ax.set_title("图2  链长与取材的描述性曲线：1→4 个连接词，重叠率几乎不动\n（隐藏假说期待的下滑并不存在）",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="y", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig2_chain_length_curve.png", bbox_inches="tight")
plt.close()

# ===== 图3 H1 的零点估计与功效 =====
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.5, 4.5))
a1.bar([0, 1], [5941, 1538], color=["#aab7b8", C_ACC], alpha=0.88, width=0.45)
for x, v, lab in [(0, 5941, "单连接词 turn"), (1, 1538, "因果链 turn（≥2 个连接词）")]:
    a1.text(x, v + 90, f"{v:,}", ha="center", fontsize=10)
a1.set_xticks([0, 1]); a1.set_xticklabels(["单连接词", "因果链"], fontsize=10)
a1.set_ylabel("turn 数", fontsize=10)
a1.set_ylim(0, 6800)
a1.set_title("(a) 对比两格：因果链 1,538 对\n单连接词 5,941（合计 7,479）", fontsize=10.5)
a1.grid(alpha=0.25, axis="y", ls="--")

lo, hi = h1["ci_lo"], h1["ci_hi"]
a2.plot([lo, hi], [0, 0], color=C_NULL, lw=5, alpha=0.9, solid_capstyle="round")
a2.plot(h1["beta"], 0, "D", color=C_NULL, ms=11)
a2.axvline(0, color="black", lw=0.9, ls="--")
a2.axvline(-0.15, color=C_OPP if "C_OPP" in dir() else "#c0392b", lw=1.2, ls=":")
a2.text(-0.148, 0.18, "隐藏假说的中带线 -0.15", fontsize=8.5, ha="center", color="#c0392b")
a2.text(hi + 0.005, 0,
        f"β = {h1['beta']:+.4f}\n95% CI [{lo:.4f}, {hi:.4f}]\np_holm = 1.0，LR χ2 = 0.15\n"
        f"（CI 未触及中带线：既无隐藏效应\n也无反向效应的迹象）",
        va="center", fontsize=9.2)
a2.set_yticks([]); a2.set_xlim(-0.20, 0.14)
a2.set_xlabel("因果链对标准化重叠的系数", fontsize=10)
a2.set_ylim(-0.5, 0.5)
a2.set_title("(b) H1 判 null：零点估计 + 紧 CI\n= 干净的空结果", fontsize=10.5)
a2.grid(alpha=0.25, axis="x", ls="--")
fig.suptitle("图3  H1 的解剖：两格、零点、紧置信区间", fontsize=12, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(OUT / "custom_fig3_h1_anatomy.png", bbox_inches="tight")
plt.close()

# ===== 图4 长度四分位分层：符号不复现 =====
fig, ax = plt.subplots(figsize=(9.2, 4.6))
strata = [s for s in art["strata"] if s.get("beta") is not None]
qlab = {"q2": "Q2", "q3": "Q3", "q4_longest": "Q4 最长"}
for i, s in enumerate(strata):
    nm = qlab.get(s["stratum"], s["stratum"])
    c = C_ACC if s["beta"] > 0 else C_NULL
    ax.plot([s["ci_lo"], s["ci_hi"]], [i, i], color=c, lw=3, alpha=0.85)
    ax.plot(s["beta"], i, "D", color=c, ms=10)
    ax.text(s["ci_hi"] + 0.008, i, f"β={s['beta']:+.4f}，p={s['p']:.2f}", va="center", fontsize=9)
ax.axvline(0, color="black", lw=0.9, ls="--")
ax.set_yticks(range(len(strata)))
ax.set_yticklabels([qlab.get(s["stratum"], s["stratum"]) for s in strata], fontsize=10.5)
ax.set_xlabel("因果链系数（正文四分位分层，描述性）", fontsize=10)
ax.set_xlim(-0.24, 0.42)
ax.set_title("图4  H3 的分层复核：三个四分位的系数两正一负、全部不显著——\n"
             "隐藏效应的符号在任何长度层都未复现（判定 not_reproduced）",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="x", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig4_quartile_strata.png", bbox_inches="tight")
plt.close()

print("P031 figures done:", [p.name for p in sorted(OUT.glob("custom_*.png"))])
