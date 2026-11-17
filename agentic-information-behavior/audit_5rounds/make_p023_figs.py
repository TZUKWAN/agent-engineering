# -*- coding: utf-8 -*-
"""P023 定制图：基于 T123 (认识情态与验证行为, EXP-0154, wave-4) 产物数据。

本文的个性：情态标记预示检验（H1 supported），但非失败响应（H2 null），
特异性检验因对照词表退化（99.98% 触发率）而不可判（H3）；
位置分层显示效应集中在轨迹前段并在中后段反转。
"""
import json, glob, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 300

fs = sorted(glob.glob("results_raw/EXP0154_wave4_design_*.json"))
art = json.load(open(fs[-1], encoding="utf-8"))
OUT = pathlib.Path("papers/P023_modality_and_verification/figures")
OUT.mkdir(parents=True, exist_ok=True)

C_SUP = "#27ae60"
C_NULL = "#95a5a6"
C_OPP = "#c0392b"
C_ACC = "#2980b9"

models = {m["hypothesis"]: m for m in art["models"]}
h1, h2, h3 = models["H1"], models["H2"], models["H3"]
desc = art["descriptive_rates"]

# ===== 图1 三假设判定森林 =====
fig, ax = plt.subplots(figsize=(10, 4.9))
rows = [
    ("H1 情态 → 检验", h1["beta"], h1["ci_lo"], h1["ci_hi"], C_SUP,
     f"判定 supported\nβ={h1['beta']:+.4f}，p_holm<0.001\n（n={h1['n']:,} turns）"),
    ("H2 情态 × 前次失败", h2["beta"], h2["ci_lo"], h2["ci_hi"], C_NULL,
     f"判定 null\nβ={h2['beta']:+.4f}，p_holm={h2['p_holm']:.3f}\n（cell_n={h2['cell_n']:,}）"),
    ("H3 主题对照词表", h3["beta"], h3["ci_lo"], h3["ci_hi"], C_OPP,
     f"判定 not_specific\nβ={h3['beta']:+.4f}\n（对照词表退化：触发率 99.98%）"),
]
for i, (lab, b, lo, hi, c, note) in enumerate(rows):
    ax.plot([lo, hi], [i, i], color=c, lw=3, alpha=0.85)
    ax.plot(b, i, "D", color=c, ms=9)
    ax.text(hi + 0.02, i, note, va="center", fontsize=8.8)
ax.axvline(0, color="black", lw=0.9, ls="--")
ax.set_yticks([0, 1, 2]); ax.set_yticklabels(["H1", "H2", "H3"], fontsize=11)
ax.set_xlim(-0.95, 0.72)
ax.set_xlabel("系数（logit 标度，聚类稳健）", fontsize=10)
ax.set_title("图1  三个预注册假设：情态-检验联结成立，但其特异性主张未能成立",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="x", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig1_verdicts.png", bbox_inches="tight")
plt.close()

# ===== 图2 描述性率：情态与失败前因 =====
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.4))
mb = desc["inspection_rate_by_modality"]
a1.bar([0, 1], [mb["0"]["rate"] * 100, mb["1"]["rate"] * 100],
       color=["#aab7b8", C_SUP], alpha=0.88, width=0.45)
for x, k in [(0, "0"), (1, "1")]:
    a1.text(x, mb[k]["rate"] * 100 + 0.3, f"{mb[k]['rate']*100:.1f}%\n(n={mb[k]['n']:,})",
            ha="center", fontsize=9.5)
a1.annotate("", xy=(1, mb["1"]["rate"] * 100 + 1.6), xytext=(0, mb["0"]["rate"] * 100 + 1.6),
            arrowprops=dict(arrowstyle="<->", color=C_ACC, lw=1.3))
a1.text(0.5, 21.3, f"+{(mb['1']['rate']-mb['0']['rate'])*100:.1f} 个百分点", ha="center",
        fontsize=9.5, color=C_ACC)
a1.set_xticks([0, 1]); a1.set_xticklabels(["无情态标记 turn", "有情态标记 turn"], fontsize=10)
a1.set_ylabel("下一动作是检验类调用的比率（%）", fontsize=10)
a1.set_ylim(0, 24)
a1.set_title("(a) 情态标记与检验率", fontsize=10.5)
a1.grid(alpha=0.25, axis="y", ls="--")

eb = desc["inspection_rate_by_error_preceded"]
a2.bar([0, 1], [eb["0"]["rate"] * 100, eb["1"]["rate"] * 100],
       color=["#aab7b8", C_OPP], alpha=0.88, width=0.45)
for x, k in [(0, "0"), (1, "1")]:
    a2.text(x, eb[k]["rate"] * 100 + 0.3, f"{eb[k]['rate']*100:.1f}%\n(n={eb[k]['n']:,})",
            ha="center", fontsize=9.5)
a2.set_xticks([0, 1]); a2.set_xticklabels(["前次观察无失败标记", "前次观察有失败标记"], fontsize=10)
a2.set_ylabel("检验率（%）", fontsize=10)
a2.set_ylim(0, 24)
a2.set_title("(b) 失败前因与检验率：失败后检验反而更少\n（H2 的交互 null 与此一致）", fontsize=10.5)
a2.grid(alpha=0.25, axis="y", ls="--")
fig.suptitle("图2  检验行为的两个描述性切面", fontsize=12, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(OUT / "custom_fig2_descriptive_rates.png", bbox_inches="tight")
plt.close()

# ===== 图3 位置分层：效应的反转 =====
fig, ax = plt.subplots(figsize=(9.2, 4.9))
strata = [s for s in art["strata"] if s["stratification"] == "position_third"]
names = {"first_third": "前三分之一", "middle_third": "中三分之一", "last_third": "后三分之一"}
xs = []
for i, s in enumerate([s for s in strata if s["stratum"] in names]):
    nm = names[s["stratum"]]
    c = C_SUP if s["beta"] > 0 else C_OPP
    ax.plot([s["ci_lo"], s["ci_hi"]], [i, i], color=c, lw=3, alpha=0.85)
    ax.plot(s["beta"], i, "D", color=c, ms=10)
    ax.text(s["ci_hi"] + 0.02, i, f"β={s['beta']:+.4f}\n(n={s['n']:,})",
            va="center", fontsize=9.2)
    xs.append(nm)
ax.axvline(0, color="black", lw=0.9, ls="--")
ax.set_yticks(range(len(xs))); ax.set_yticklabels(xs, fontsize=11)
ax.set_xlabel("情态标记对下一动作是检验的系数（描述性分层）", fontsize=10)
ax.set_xlim(-0.45, 0.85)
ax.set_title("图3  效应的轨迹位置剖面：集中在轨迹前段（β=+0.54），\n中后段反号为负——hedging 的含义随任务阶段变化",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="x", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig3_position_profile.png", bbox_inches="tight")
plt.close()

# ===== 图4 H3 对照词表的退化 =====
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.4))
prev = h3["frozen_indicator_prevalence"]
a1.bar([0, 1], [prev * 100, 100 - prev * 100], color=[C_OPP, "#d5d8dc"], width=0.45)
a1.text(0, prev * 100 - 6, f"{prev*100:.2f}%", ha="center", fontsize=13, color="white", fontweight="bold")
a1.text(1, 0.05 + 0.02 * 100 * 0.02, "0.02%", ha="center", fontsize=9)
a1.set_xticks([0, 1]); a1.set_xticklabels(["含对照词表词项的 turn", "不含"], fontsize=10)
a1.set_ylabel("turn 占比（%）", fontsize=10)
a1.set_ylim(0, 105)
a1.set_title("(a) 冻结的主题对照词表近乎处处触发\n（indicator_is_degenerate = true）", fontsize=10.5)

a2.bar([0, 1], [h3["control_count_sd"], 1.0], color=[C_OPP, "#aab7b8"], width=0.45)
a2.text(0, h3["control_count_sd"] + 1, f"SD = {h3['control_count_sd']:.1f} 个词项/turn",
        ha="center", fontsize=9.5)
a2.set_xticks([0, 1]); a2.set_xticklabels(["对照词表计数", "情态标记（0/1，参照）"], fontsize=9.5)
a2.set_ylabel("标准差", fontsize=10)
a2.set_ylim(0, 60)
a2.set_title("(b) 对照变量是高方差计数而非指示变量：\n它追踪的是 turn 长度/冗余度，不是所谓主题对照", fontsize=10.5)
a2.grid(alpha=0.25, axis="y", ls="--")
fig.suptitle("图4  H3 判定词的来历：一个退化的对照使特异性主张不可判",
             fontsize=12, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(OUT / "custom_fig4_degenerate_control.png", bbox_inches="tight")
plt.close()

print("P023 figures done:", [p.name for p in sorted(OUT.glob("custom_*.png"))])
