# -*- coding: utf-8 -*-
"""P025 定制图：基于 T126 (矛盾证据与认识情态, EXP-0156, wave-4) 产物数据。

本文的个性：矛盾证据不升级犹豫、反而降低（H1 opposite, -0.1058）；
矛盾与新信息的特异性成立但同在负侧（H2 supported, -0.0363）；
充分性语言 null；重复观察后情态最高（15.28%）。
"""
import json, glob, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 300

fs = sorted(glob.glob("results_raw/EXP0156_wave4_design_*.json"))
art = json.load(open(fs[-1], encoding="utf-8"))
OUT = pathlib.Path("papers/P025_contradiction_and_modality/figures")
OUT.mkdir(parents=True, exist_ok=True)

C_SUP = "#27ae60"
C_NULL = "#95a5a6"
C_OPP = "#c0392b"
C_ACC = "#2980b9"

models = {m["hypothesis"]: m for m in art["models"]}
h1, h2, h3 = models["H1"], models["H2"], models["H3"]
desc = art["descriptive_rates"]

# ===== 图1 三假设判定森林 =====
fig, ax = plt.subplots(figsize=(10, 4.8))
rows = [
    ("H1 矛盾 vs 重复观察\n（情态率）", h1["beta"], h1["ci_lo"], h1["ci_hi"], C_OPP,
     f"判定 opposite\nβ={h1['beta']:+.4f}，p_holm={h1['p_holm']:.4f}\n（预测为正，实测为负）"),
    ("H2 矛盾 vs 新工具信息\n（情态率）", h2["beta"], h2["ci_lo"], h2["ci_hi"], C_ACC,
     f"判定 supported\nβ={h2['beta']:+.4f}，p_holm={h2['p_holm']:.4f}\n（特异性成立，方向同为负）"),
    ("H3 充分性语言同向", h3["beta"], h3["ci_lo"], h3["ci_hi"], C_NULL,
     f"判定 null\nβ={h3['beta']:+.4f}，p_holm={h3['p_holm']:.3f}"),
]
for i, (lab, b, lo, hi, c, note) in enumerate(rows):
    ax.plot([lo, hi], [i, i], color=c, lw=3, alpha=0.85)
    ax.plot(b, i, "D", color=c, ms=9)
    ax.text(hi + 0.012, i, note, va="center", fontsize=8.8)
ax.axvline(0, color="black", lw=0.9, ls="--")
ax.set_yticks([0, 1, 2]); ax.set_yticklabels(["H1", "H2", "H3"], fontsize=11)
ax.set_xlim(-0.30, 0.32)
ax.set_xlabel("系数（logit 标度，聚类稳健）", fontsize=10)
ax.set_title("图1  三个预注册假设：矛盾之后，犹豫收敛而非升级",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="x", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig1_verdicts.png", bbox_inches="tight")
plt.close()

# ===== 图2 四状态描述率：情态与充分性语言 =====
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.5, 4.5))
states = ["same_tool_same", "same_tool_changed", "different_tool", "first_observation"]
labels = ["重复观察\n（同工具同内容）", "矛盾观察\n（同工具变内容）", "新信息\n（不同工具）", "首次观察"]
mrate = [desc["modality_rate_by_state"][s]["rate"] * 100 for s in states]
srate = [desc["sufficiency_rate_by_state"][s]["rate"] * 100 for s in states]
ns = [desc["modality_rate_by_state"][s]["n"] for s in states]
colors_m = [C_SUP, C_OPP, C_ACC, "#aab7b8"]
a1.bar(range(4), mrate, color=colors_m, alpha=0.88, width=0.55)
for i, (r, n) in enumerate(zip(mrate, ns)):
    a1.text(i, r + 0.15, f"{r:.2f}%\n(n={n:,})", ha="center", fontsize=8.8)
a1.set_xticks(range(4)); a1.set_xticklabels(labels, fontsize=8.5)
a1.set_ylabel("下一 turn 情态标记率（%）", fontsize=10)
a1.set_ylim(0, 19)
a1.set_title("(a) 情态率：重复观察后最高（15.28%），\n矛盾之后反而更低（13.58%）——与预测相反", fontsize=10.5)
a1.grid(alpha=0.25, axis="y", ls="--")

colors_s = [C_SUP, C_OPP, C_ACC, "#aab7b8"]
a2.bar(range(4), srate, color=colors_s, alpha=0.88, width=0.55)
for i, r in enumerate(srate):
    a2.text(i, r + 0.06, f"{r:.2f}%", ha="center", fontsize=9)
a2.set_xticks(range(4)); a2.set_xticklabels(labels, fontsize=8.5)
a2.set_ylabel("下一 turn 充分性语言率（%）", fontsize=10)
a2.set_ylim(0, 5.6)
a2.set_title("(b) 充分性语言：矛盾后翻倍（1.92%→4.48%）\n——信息状态陈述与犹豫词汇分道扬镳", fontsize=10.5)
a2.grid(alpha=0.25, axis="y", ls="--")
fig.suptitle("图2  四种观察状态下的语言反应：情态与充分性讲述相反的故事",
             fontsize=12, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(OUT / "custom_fig2_state_rates.png", bbox_inches="tight")
plt.close()

# ===== 图3 前次观察族分层 =====
fig, ax = plt.subplots(figsize=(9.4, 4.6))
strata = [s for s in art["strata"] if s["stratification"] == "prev_obs_family"]
name_map = {"execution": "前次为执行类调用", "inspection": "前次为检验类调用"}
rows = []
for s in strata:
    if s["stratum"] in name_map:
        rows.append((name_map[s["stratum"]], s))
# 若有第三层（如 none），也画
for s in strata:
    if s["stratum"] not in name_map:
        rows.append((f"前次无观察（{s['stratum']}）", s))
for i, (lab, s) in enumerate(rows):
    c = C_OPP if s["beta"] < 0 else C_SUP
    ax.plot([s["ci_lo"], s["ci_hi"]], [i, i], color=c, lw=3, alpha=0.85)
    ax.plot(s["beta"], i, "D", color=c, ms=10)
    ax.text(s["ci_hi"] + 0.02, i, f"β={s['beta']:+.4f}\n(n={s['rows']:,})",
            va="center", fontsize=9)
ax.axvline(0, color="black", lw=0.9, ls="--")
ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[0] for r in rows], fontsize=10.5)
ax.set_xlabel("矛盾观察（相对重复观察）对情态率的系数（描述性分层）", fontsize=10)
ax.set_xlim(-0.75, 1.0)
ax.set_title("图3  按前次观察类型的分层：负效应跨执行与检验两类前次都成立\n（描述性分层，不进判定族）",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="x", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig3_family_strata.png", bbox_inches="tight")
plt.close()

# ===== 图4 预期 vs 实测 =====
fig, ax = plt.subplots(figsize=(9, 4.8))
ax.barh([1], [0.4], color="#27ae60", alpha=0.4, hatch="//", edgecolor="white")
ax.text(0.2, 1.32, "预测方向：矛盾 → 犹豫升级（正）", ha="center", fontsize=10, color="#1e8449")
ax.plot([h1["ci_lo"], h1["ci_hi"]], [0, 0], color=C_OPP, lw=4, alpha=0.85, solid_capstyle="round")
ax.plot(h1["beta"], 0, "D", color=C_OPP, ms=11)
ax.axvline(0, color="black", lw=0.9)
ax.text(h1["ci_lo"] - 0.02, 0, f"实测：β = {h1['beta']:+.4f}\n95% CI [{h1['ci_lo']:.4f}, {h1['ci_hi']:.4f}]\n"
        f"p_holm = {h1['p_holm']:.4f}（判定 opposite）",
        va="center", ha="right", fontsize=9.8, color=C_OPP)
ax.set_yticks([0, 1]); ax.set_yticklabels(["实测", "预测"], fontsize=11)
ax.set_xlabel("同工具内容变化对下一 turn 情态率的效应", fontsize=10)
ax.set_xlim(-0.35, 0.55)
ax.set_title("图4  经典预期的反向：矛盾的证据没有让智能体嘴上更犹豫\n（第 5 节论证：它让智能体直接行动）",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="x", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig4_prediction_vs_observed.png", bbox_inches="tight")
plt.close()

print("P025 figures done:", [p.name for p in sorted(OUT.glob("custom_*.png"))])
