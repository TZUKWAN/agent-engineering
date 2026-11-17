# -*- coding: utf-8 -*-
"""P027 定制图：基于 T130 (话语语法, EXP-0165, wave-5) 产物数据。

本文的个性：五种言语行为有强位置结构（plan 62%→77%、conclusion 0.65%→1.90%），
但 H1 的冻结方向被反（plan 上升而非下降），且 H3 双词表 Kappa 全军覆没
（最高 0.083）——语法可能是单一词表的产物。工具批判是本文的主角。
"""
import json, glob, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 300

fs = sorted(glob.glob("results_raw/EXP0165_wave5_design_*.json"))
art = json.load(open(fs[-1], encoding="utf-8"))
OUT = pathlib.Path("papers/P027_discourse_grammar_of_seeking/figures")
OUT.mkdir(parents=True, exist_ok=True)

C_SUP = "#27ae60"
C_ACC = "#2980b9"
C_OPP = "#c0392b"
C_NULL = "#95a5a6"

models = {m["hypothesis"]: m for m in art["models"]}
h1, h2, h3 = models["H1"], models["H2"], models["H3"]
shares = art["descriptive_rates"]["act_share_by_position_third"]
kappa = h3["kappa"]

ACTS = [("plan", "计划"), ("evidence_request", "请求证据"), ("question", "提问"),
        ("conclusion", "结论"), ("hypothesis", "假设")]
POS = ["first_third", "middle_third", "last_third"]
POS_LABEL = ["前三分之一", "中三分之一", "后三分之一"]

# ===== 图1 五种言语行为的位置结构 =====
fig, ax = plt.subplots(figsize=(10.5, 5.2))
x = np.arange(len(ACTS))
w = 0.25
colors = [C_ACC, "#7fb3d5", "#1f3f66"]
for j, (pos, lab, c) in enumerate(zip(POS, POS_LABEL, colors)):
    vals = [shares[pos][a] * 100 for a, _ in ACTS]
    ax.bar(x + (j - 1) * w, vals, width=w, color=c, alpha=0.9, label=lab)
    for xi, v in zip(x + (j - 1) * w, vals):
        ax.text(xi, v + 0.8, f"{v:.1f}", ha="center", fontsize=7.8)
ax.set_xticks(x)
ax.set_xticklabels([f"{en}\n{cn}" for en, cn in ACTS], fontsize=9.5)
ax.set_ylabel("turn 中该言语行为词表触发率（%）", fontsize=10)
ax.set_ylim(0, 88)
ax.legend(fontsize=9.5, title="轨迹位置", title_fontsize=9.5)
ax.set_title("图1  五种言语行为的位置结构：plan 与 evidence_request 向后段集聚，\n"
             "question 向前段集聚——结构存在，但它的方向要靠图 3 来审",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="y", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig1_position_structure.png", bbox_inches="tight")
plt.close()

# ===== 图2 H1/H2 判定森林 =====
fig, ax = plt.subplots(figsize=(9.6, 4.6))
rows = [
    ("H1 plan 位置系数\n（last_third 项）", h1["beta"], h1["ci_lo"], h1["ci_hi"], C_SUP,
     f"判定 supported（direction-free）\nβ={h1['beta']:+.4f}\n冻结方向为前段更多，实测后段更多\n（轮2注：方向自由规则裁定）"),
    ("H2 conclusion 位置系数\n（last_third 项）", h2["beta"], h2["ci_lo"], h2["ci_hi"], C_SUP,
     f"判定 supported\nβ={h2['beta']:+.4f}\n后段更多结论，与冻结方向一致"),
]
for i, (lab, b, lo, hi, c, note) in enumerate(rows):
    ax.plot([lo, hi], [i, i], color=c, lw=3, alpha=0.85)
    ax.plot(b, i, "D", color=c, ms=9)
    ax.text(hi + 0.03, i, note, va="center", fontsize=8.6)
ax.axvline(0, color="black", lw=0.9, ls="--")
ax.set_yticks([0, 1]); ax.set_yticklabels(["H1", "H2"], fontsize=11)
ax.set_xlim(0.55, 2.35)
ax.set_xlabel("logit 系数（last_third，聚类稳健）", fontsize=10)
ax.set_title("图2  H1/H2：位置效应巨大——但 H1 的方向与冻结句相反\n（诚实呈现：结构真实，方向预判错了）",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="x", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig2_verdicts.png", bbox_inches="tight")
plt.close()

# ===== 图3 双词表一致性：高一致率、近零 Kappa =====
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.5, 4.6))
acts_en = [en for en, _ in ACTS]
acts_cn = [cn for _, cn in ACTS]
agree = [kappa[a]["agreement"] * 100 for a in acts_en]
kaps = [kappa[a]["kappa"] for a in acts_en]
a1.bar(range(5), agree, color=C_ACC, alpha=0.85, width=0.55)
for i, v in enumerate(agree):
    a1.text(i, v + 1.2, f"{v:.1f}%", ha="center", fontsize=9)
a1.axhline(50, color=C_NULL, lw=1, ls=":")
a1.set_xticks(range(5)); a1.set_xticklabels(acts_cn, fontsize=10)
a1.set_ylabel("双词表原始一致率（%）", fontsize=10)
a1.set_ylim(0, 110)
a1.set_title("(a) 原始一致率看似很高\n（尤其稀有行为的 90%+ 一致）", fontsize=10.5)
a1.grid(alpha=0.25, axis="y", ls="--")

a2.bar(range(5), kaps, color=C_OPP, alpha=0.85, width=0.55)
a2.axhline(0.60, color="black", lw=1.3, ls="--")
a2.text(4.4, 0.615, "冻结的合格线 0.60", fontsize=9, ha="right")
for i, v in enumerate(kaps):
    a2.text(i, v + 0.012, f"{v:.3f}", ha="center", fontsize=9)
a2.set_xticks(range(5)); a2.set_xticklabels(acts_cn, fontsize=10)
a2.set_ylabel("Cohen Kappa", fontsize=10)
a2.set_ylim(0, 0.72)
a2.set_title("(b) Kappa 全部低于 0.09——校正 chance 后\n两套词表几乎没有共识（H3 判 not_invariant）", fontsize=10.5)
a2.grid(alpha=0.25, axis="y", ls="--")
fig.suptitle("图3  H3 的工具审判：高一致率是低基率的假象，五种行为全部 tagger-dependent",
             fontsize=12, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(OUT / "custom_fig3_kappa_panel.png", bbox_inches="tight")
plt.close()

# ===== 图4 基率陷阱：一致率 vs 触发率 =====
fig, ax = plt.subplots(figsize=(9.2, 5.0))
prev_all = [(shares["first_third"][a] + shares["middle_third"][a] + shares["last_third"][a]) / 3 * 100
            for a in acts_en]
ax.scatter(prev_all, agree, s=140, color=C_ACC, alpha=0.85, zorder=3)
for a, cn, px, py in zip(acts_en, acts_cn, prev_all, agree):
    ax.annotate(f"{cn}\n(κ={kappa[a]['kappa']:.3f})", (px, py),
                textcoords="offset points", xytext=(10, 6), fontsize=9)
ax.axhline(60, color=C_OPP, lw=1.2, ls="--")
ax.text(52, 61.5, "kappa 合格线（换算前）", fontsize=8.5, color=C_OPP)
ax.set_xlabel("行为平均触发率（%，三段均值）", fontsize=10)
ax.set_ylabel("双词表原始一致率（%）", fontsize=10)
ax.set_xlim(0, 62); ax.set_ylim(35, 103)
ax.set_title("图4  基率陷阱：越罕见的行为一致率越高——\n原始一致率在稀有事件上不构成效度证据",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig4_base_rate_trap.png", bbox_inches="tight")
plt.close()

print("P027 figures done:", [p.name for p in sorted(OUT.glob("custom_*.png"))])
