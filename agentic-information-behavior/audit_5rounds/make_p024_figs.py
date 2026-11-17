# -*- coding: utf-8 -*-
"""P024 定制图：基于 T124 (认识-行为鸿沟, EXP-0155, wave-4) 产物数据。

本文的个性：一个 turn 的两张面孔（推理块 vs 用户正文）在"是否不确定"上分歧时，
行为跟随私人面孔（discordant 检验率 25.3%），公开正文犹豫反而伴随更少检验
（3.45%，H2 判 outside_the_frozen_rule_negative_contrast），
私人不确定维持搜索（H3 supported）。
"""
import json, glob, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 300

fs = sorted(glob.glob("results_raw/EXP0155_wave4_design_*.json"))
art = json.load(open(fs[-1], encoding="utf-8"))
OUT = pathlib.Path("papers/P024_epistemic_behavioural_gap/figures")
OUT.mkdir(parents=True, exist_ok=True)

C_SUP = "#27ae60"
C_OPP = "#c0392b"
C_ACC = "#2980b9"
C_GREY = "#95a5a6"

models = {m["hypothesis"]: m for m in art["models"]}
h1, h2, h3 = models["H1"], models["H2"], models["H3"]
desc = art["descriptive_rates"]["inspection_rate_by_pattern"]
cells = art["cell_sizes"]

# ===== 图1 四种面孔模式的检验率 =====
fig, ax = plt.subplots(figsize=(9.6, 5.0))
disc = desc["discordant"]["1"]; bo = desc["body_only"]["1"]
rest = desc["body_only"]["0"]
bars = ax.bar([0, 1, 2],
              [disc["rate"] * 100, rest["rate"] * 100, bo["rate"] * 100],
              color=[C_SUP, C_GREY, C_OPP], alpha=0.9, width=0.55)
labels = [f"分歧模式\n推理犹豫/正文自信\n(n={disc['n']:,})",
          f"其余 turn\n（以双不犹豫为主体）\n(n={rest['n']:,})",
          f"仅正文犹豫\n正文犹豫/推理自信\n(n={bo['n']:,})"]
for x, r in zip([0, 1, 2], [disc, rest, bo]):
    ax.text(x, r["rate"] * 100 + 0.5, f"{r['rate']*100:.2f}%", ha="center", fontsize=11,
            fontweight="bold")
ax.set_xticks([0, 1, 2]); ax.set_xticklabels(labels, fontsize=9.5)
ax.set_ylabel("下一动作是检验类调用的比率（%）", fontsize=10)
ax.set_ylim(0, 30)
ax.annotate("行为跟随私人面孔：\n分歧模式的检验率高于总体基线", xy=(0, disc["rate"] * 100),
            xytext=(0.55, 27.5), fontsize=9.5, color=C_SUP,
            arrowprops=dict(arrowstyle="->", color=C_SUP, lw=1.2))
ax.annotate("公开犹豫伴随最少检验：\n礼貌性缓冲而非认识信号", xy=(2, bo["rate"] * 100),
            xytext=(1.45, 8.5), fontsize=9.5, color=C_OPP,
            arrowprops=dict(arrowstyle="->", color=C_OPP, lw=1.2))
ax.set_title("图1  一个 turn 的两张脸：行为听推理块的，不听正文的",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="y", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig1_face_patterns.png", bbox_inches="tight")
plt.close()

# ===== 图2 三假设判定森林 =====
fig, ax = plt.subplots(figsize=(10, 4.8))
rows = [
    ("H1 分歧 vs 仅正文犹豫\n（检验率）", h1["beta"], h1["ci_lo"], h1["ci_hi"], C_SUP,
     f"判定 supported\nβ={h1['beta']:+.4f}，p_holm<0.001"),
    ("H2 仅正文犹豫 vs 其余\n（检验率）", h2["beta"], h2["ci_lo"], h2["ci_hi"], C_OPP,
     f"判定 outside_the_frozen_rule\nβ={h2['beta']:+.4f}，p_holm<0.001\n（冻结句预期近零，实测强负）"),
    ("H3 分歧 vs 仅正文犹豫\n（在此停止）", h3["beta"], h3["ci_lo"], h3["ci_hi"], C_SUP,
     f"判定 supported\nβ={h3['beta']:+.4f}，p_holm<0.001\n（私人不确定维持搜索）"),
]
for i, (lab, b, lo, hi, c, note) in enumerate(rows):
    ax.plot([lo, hi], [i, i], color=c, lw=3, alpha=0.85)
    ax.plot(b, i, "D", color=c, ms=9)
    ax.text(hi + 0.03, i, note, va="center", fontsize=8.8)
ax.axvline(0, color="black", lw=0.9, ls="--")
ax.set_yticks([0, 1, 2]); ax.set_yticklabels(["H1", "H2", "H3"], fontsize=11)
ax.set_xlim(-1.5, 1.15)
ax.set_xlabel("系数（logit 标度，聚类稳健）", fontsize=10)
ax.set_title("图2  三个预注册假设：私人面孔承载认识信号，公开面孔是表演",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="x", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig2_verdicts.png", bbox_inches="tight")
plt.close()

# ===== 图3 面孔模式的稀缺性 =====
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.4))
n_turns = art["n_turns"]
names = ["分歧\n(推理犹豫/正文自信)", "一致\n(两处都犹豫)", "仅正文犹豫\n(正文犹豫/推理自信)"]
sizes = [cells["disc"], cells["conc"], cells["bodyonly"]]
shares = [s / n_turns * 100 for s in sizes]
a1.bar(range(3), sizes, color=[C_SUP, C_ACC, C_OPP], alpha=0.88, width=0.5)
for i, (s, p) in enumerate(zip(sizes, shares)):
    a1.text(i, s + 250, f"{s:,}\n({p:.1f}%)", ha="center", fontsize=9.5)
a1.set_xticks(range(3)); a1.set_xticklabels(names, fontsize=9)
a1.set_ylabel("turn 数", fontsize=10)
a1.set_ylim(0, 15500)
a1.set_title("(a) 三种分歧/一致模式的存量：\n分歧模式占 15.2%，是稀缺但充足的样本", fontsize=10.5)
a1.grid(alpha=0.25, axis="y", ls="--")

base_dev = 74210.46
new_dev = 74024.66
a2.bar([0, 1], [base_dev, new_dev], color=["#aab7b8", C_ACC], alpha=0.88, width=0.45)
a2.text(0, base_dev + 40, f"{base_dev:,.1f}", ha="center", fontsize=9.5)
a2.text(1, new_dev + 40, f"{new_dev:,.1f}", ha="center", fontsize=9.5)
a2.annotate("", xy=(1, new_dev - 60), xytext=(0, base_dev - 60),
            arrowprops=dict(arrowstyle="->", color=C_OPP, lw=1.4))
a2.text(0.5, 73850, "Δdeviance = -185.8\n(LR χ2=371.6, df=3, p<0.001)",
        ha="center", fontsize=9.5, color=C_OPP)
a2.set_xticks([0, 1]); a2.set_xticklabels(["证据状态基线", "+ 面孔模式项"], fontsize=10)
a2.set_ylabel("deviance", fontsize=10)
a2.set_ylim(73750, 74400)
a2.set_title("(b) 面孔模式在证据状态之外\n携带独立的行为信息", fontsize=10.5)
a2.grid(alpha=0.25, axis="y", ls="--")
fig.suptitle("图3  分歧模式的存量与增量价值", fontsize=12, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(OUT / "custom_fig3_cells_deviance.png", bbox_inches="tight")
plt.close()

# ===== 图4 H3 停止行为 =====
fig, ax = plt.subplots(figsize=(9, 4.8))
ax.bar([0], [abs(h3["beta"])], width=0.42, color=C_SUP, alpha=0.88)
ax.errorbar(0, abs(h3["beta"]), yerr=[[abs(h3["beta"]) - abs(h3["ci_hi"])], [abs(h3["ci_lo"]) - abs(h3["beta"])]],
            color="#145a32", capsize=6, lw=1.5)
ax.axhline(0, color="black", lw=0.9, ls="--")
ax.text(0.24, abs(h3["beta"]),
        f"分歧模式相对仅正文犹豫的停止 logit\nβ = {h3['beta']:+.4f}（负 = 更少停止）\n"
        f"95% CI [{h3['ci_lo']:.4f}, {h3['ci_hi']:.4f}]，p_holm<0.001",
        va="center", fontsize=9.8, color="#145a32")
ax.set_xticks([0]); ax.set_xticklabels(["H3：私人不确定维持搜索"], fontsize=10.5)
ax.set_ylabel("|logit 系数|（指向更少停止）", fontsize=10)
ax.set_ylim(0, 0.62)
ax.set_title("图4  推理里的犹豫让搜索继续：分歧模式显著降低在该 turn 终止的几率",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="y", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig4_stopping.png", bbox_inches="tight")
plt.close()

print("P024 figures done:", [p.name for p in sorted(OUT.glob("custom_*.png"))])
