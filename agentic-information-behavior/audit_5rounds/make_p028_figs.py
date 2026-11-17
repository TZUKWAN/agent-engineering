# -*- coding: utf-8 -*-
"""P028 定制图：基于 T132 (结论先于证据, EXP-0166, wave-5) 产物数据。

本文的个性：H1 因前提普查（114 条 < 冻结底线 200）判 not_testable，
即使设计帧里有 472 条也不重开——冻结纪律的范本；
H2 opposite（控制后先检验后结论的词汇重叠反而更低）；H3 supported。
"""
import json, glob, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 300

fs = sorted(glob.glob("results_raw/EXP0166_wave5_design_*.json"))
art = json.load(open(fs[-1], encoding="utf-8"))
OUT = pathlib.Path("papers/P028_conclusion_before_evidence/figures")
OUT.mkdir(parents=True, exist_ok=True)

C_SUP = "#27ae60"
C_OPP = "#c0392b"
C_NULL = "#95a5a6"
C_ACC = "#2980b9"

models = {m["hypothesis"]: m for m in art["models"]}
h1, h2, h3 = models["H1"], models["H2"], models["H3"]
desc = art["descriptive_rates"]["mean_overlap_by_order"]

# ===== 图1 H1 前提底线：两次测量与冻结规则 =====
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.5, 4.6))
a1.bar([0, 1], [114, 200], color=[C_OPP, "#d5d8dc"], width=0.5)
a1.axhline(200, color="black", lw=1.2, ls="--")
a1.text(1, 204, "冻结底线 200 条", fontsize=9.5, ha="center")
a1.text(0, 120, "114 条\n（EXP-0161 普查\n4,000 轨迹样本）", ha="center", fontsize=9.5, color=C_OPP)
a1.set_xticks([0, 1]); a1.set_xticklabels(["普查实测", "冻结底线"], fontsize=10)
a1.set_ylabel("先结论后检验的轨迹数", fontsize=10)
a1.set_ylim(0, 240)
a1.set_title("(a) 普查口径：低于底线\n→ H1 判 not_testable", fontsize=10.5)
a1.grid(alpha=0.25, axis="y", ls="--")

a2.bar([0, 1], [472, 200], color=[C_ACC, "#d5d8dc"], width=0.5)
a2.axhline(200, color="black", lw=1.2, ls="--")
a2.text(1, 204, "冻结底线 200 条", fontsize=9.5, ha="center")
a2.text(0, 478, "472 条\n（设计帧 20,000 轨迹\n的同格计数）", ha="center", fontsize=9.5, color=C_ACC)
a2.set_xticks([0, 1]); a2.set_xticklabels(["设计帧实测", "冻结底线"], fontsize=10)
a2.set_ylabel("先结论后检验的轨迹数", fontsize=10)
a2.set_ylim(0, 560)
a2.set_title("(b) 设计帧口径：高于底线——\n但冻结句指名普查测量，检验不重开", fontsize=10.5)
a2.grid(alpha=0.25, axis="y", ls="--")
fig.suptitle("图1  H1 的前提底线：两个口径、一句冻结、一次不重开",
             fontsize=12, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(OUT / "custom_fig1_premise_floor.png", bbox_inches="tight")
plt.close()

# ===== 图2 描述性重叠：先 vs 后 =====
fig, ax = plt.subplots(figsize=(8.8, 4.8))
vals = [desc["0"]["mean"] * 100, desc["1"]["mean"] * 100]
ax.bar([0, 1], vals, color=[C_OPP, C_SUP], alpha=0.88, width=0.45)
for x, r in zip([0, 1], [desc["0"], desc["1"]]):
    ax.text(x, r["mean"] * 100 + 0.5, f"{r['mean']*100:.2f}%\n(n={r['n']:,})",
            ha="center", fontsize=10)
ax.set_xticks([0, 1])
ax.set_xticklabels(["先下结论\n（首次检验前）", "后下结论\n（已有检验之后）"], fontsize=10)
ax.set_ylabel("结论 turn 与已返回观察的词汇重叠率（%）", fontsize=10)
ax.set_ylim(0, 30)
ax.set_title("图2  原始对比：先下的结论与已有证据的词汇重叠只有后下结论的一半\n（但这是未控制的表象，见图 3）",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="y", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig2_overlap_descriptive.png", bbox_inches="tight")
plt.close()

# ===== 图3 H2 opposite =====
fig, ax = plt.subplots(figsize=(9.4, 4.8))
ax.plot([h2["ci_lo"], h2["ci_hi"]], [0, 0], color=C_OPP, lw=4, alpha=0.85, solid_capstyle="round")
ax.plot(h2["beta"], 0, "D", color=C_OPP, ms=11)
ax.axvline(0, color="black", lw=0.9, ls="--")
ax.text(h2["ci_hi"] + 0.02, 0,
        f"H2：控制位置与长度后\n结论-证据重叠的顺序效应\nβ = {h2['beta']:+.4f}（预测为正，实测为负）\n"
        f"95% CI [{h2['ci_lo']:.4f}, {h2['ci_hi']:.4f}]，p_holm = {h2['p_holm']:.4f}",
        va="center", fontsize=9.5, color=C_OPP)
ax.set_yticks([])
ax.set_xlabel("concl_after_inspect 对标准化词汇重叠的系数", fontsize=10)
ax.set_xlim(-0.56, 0.30)
ax.set_title("图3  H2 判 opposite：原始的后发优势是位置与长度的影子，\n"
             "条件化之后先检验的结论反而更少取材于已有观察",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="x", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig3_h2_opposite.png", bbox_inches="tight")
plt.close()

# ===== 图4 H3：结论行为推高停止 =====
fig, ax = plt.subplots(figsize=(9, 4.8))
ax.barh([0], [h3["beta"]], height=0.42, color=C_SUP, alpha=0.85)
ax.errorbar(h3["beta"], 0,
            xerr=[[h3["beta"] - h3["ci_lo"]], [h3["ci_hi"] - h3["beta"]]],
            color="#145a32", capsize=6, lw=1.5, fmt="none")
ax.axvline(0, color="black", lw=0.9, ls="--")
ax.text(h3["ci_hi"] + 0.03, 0,
        f"结论行为对在该 turn 终止的增量效应\nβ = {h3['beta']:+.4f}（比值比约 e^0.83 ≈ 2.3）\n"
        f"95% CI [{h3['ci_lo']:.4f}, {h3['ci_hi']:.4f}]，p_holm < 0.001",
        va="center", fontsize=9.5, color="#145a32")
ax.set_yticks([])
ax.set_xlabel("act_conclusion 对 stops_here 的系数（logit，聚类稳健）", fontsize=10)
ax.set_xlim(0, 1.75)
ax.set_title("图4  H3 判 supported：说出结论的 turn 终止轨迹的几率翻倍——\n结论话语是收束行为的强信号",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="x", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig4_h3_stopping.png", bbox_inches="tight")
plt.close()

print("P028 figures done:", [p.name for p in sorted(OUT.glob("custom_*.png"))])
