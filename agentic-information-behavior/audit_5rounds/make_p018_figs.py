# -*- coding: utf-8 -*-
"""P018 定制图：基于 T113 (功能式 vs 用例式描述, EXP-0145) 产物数据。

本文的个性：一个 kill gate 履职的设计——改写臂中位长度变化 66.7% 越过 40%
阈值，自然长度对比被冻结规则判为不可解释；匹配长度臂显示用例框架的代价
(-0.0226) 及其随原长衰减的斜率。四张图围绕"不可解释→诚实替代比较"展开。
"""
import json, glob, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 300

fs = sorted(glob.glob("results_raw/EXP0145_wave3_design_*.json"))
art = json.load(open(fs[-1], encoding="utf-8"))
OUT = pathlib.Path("papers/P018_function_vs_usecase_description/figures")
OUT.mkdir(parents=True, exist_ok=True)

C_SUP = "#27ae60"
C_PART = "#e67e22"
C_NULL = "#95a5a6"
C_ACC = "#2980b9"
C_GATE = "#c0392b"

models = {m["hypothesis"]: m for m in art["models"]}
h1, h2, h3 = models["H1"], models["H2"], models["H3"]
strata = art["strata"]

# ===== 图1 kill gate 诊断：长度混杂 vs 构念操作 =====
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.4))
med = art["measured_length_change_median"]
a1.barh([1], [med * 100], color=C_GATE, alpha=0.85, height=0.45)
a1.barh([0], [40], color="#d5d8dc", alpha=0.9, height=0.45)
a1.axvline(40, color="black", lw=1.2, ls="--")
a1.text(med * 100 + 1.5, 1, f"实测中位长度变化 {med*100:.1f}%", va="center", fontsize=9.5, color=C_GATE)
a1.text(41.5, 0, "冻结阈值 40%", va="center", fontsize=9.5)
a1.set_yticks([0, 1]); a1.set_yticklabels(["kill gate 阈值", "改写臂实测"], fontsize=10)
a1.set_xlabel("token 数变化幅度（%）", fontsize=10)
a1.set_xlim(0, 105)
a1.set_title("(a) gate 触发：改写改变长度的幅度\n远超构念（表述框架）所需", fontsize=10.5)
a1.grid(alpha=0.25, axis="x", ls="--")

n = art["n_queries"]
share = [h1["n_changed_rows"] / n * 100, h3["n_changed_rows"] / n * 100]
a2.bar([0, 1], share, color=[C_NULL, C_ACC], alpha=0.85, width=0.5)
for i, s in enumerate(share):
    a2.text(i, s + 0.25, f"{s:.1f}%\n({models['H1' if i==0 else 'H3']['n_changed_rows']:,}/{n:,})",
            ha="center", fontsize=9)
a2.set_xticks([0, 1])
a2.set_xticklabels(["自然长度对比\n（hit1 变动的行）", "匹配长度对比\n（hit1 变动的行）"], fontsize=9)
a2.set_ylabel("hit1 发生变动的查询占比（%）", fontsize=10)
a2.set_title("(b) 自然长度下仅 2.0% 的查询\n其 rank-1 结果因改写而变动", fontsize=10.5)
a2.grid(alpha=0.25, axis="y", ls="--")
fig.suptitle("图1  kill gate 诊断：H1 的自然长度对比为何判为不可解释",
             fontsize=12, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(OUT / "custom_fig1_gate_panel.png", bbox_inches="tight")
plt.close()

# ===== 图2 三假设判定森林图（含 H1 的秩差次证据） =====
fig, ax = plt.subplots(figsize=(9.8, 4.8))
rows = [
    ("H1 hit1（自然长度）", h1["ci"][0], h1["ci"][1], h1["mean_difference"], C_NULL,
     f"判定 not_interpretable\nΔ={h1['mean_difference']:+.4f}，CI 压在零上"),
    ("H2 增益 ~ 原长", h2["ci_lo"], h2["ci_hi"], h2["beta"], C_NULL,
     f"判定 null（β={h2['beta']:+.4f}，p_holm=0.892）"),
    ("H3 hit1（匹配长度）", h3["ci"][0], h3["ci"][1], h3["mean_difference"], C_PART,
     f"判定 partial\nΔ={h3['mean_difference']:+.4f}，CI 全在零负侧"),
]
for i, (lab, lo, hi, b, c, note) in enumerate(rows):
    ax.plot([lo, hi], [i, i], color=c, lw=3, alpha=0.85)
    ax.plot(b, i, "D", color=c, ms=9)
    ax.text(hi + 0.0012, i + 0.16, note, va="bottom", fontsize=8.5, color="#333")
# H1 的秩差次证据
rd = h1["rank_difference"]; rlo, rhi = h1["rank_difference_ci"]
ax.plot([rlo, rhi], [-0.45, -0.45], color="#8e44ad", lw=2.4, alpha=0.85)
ax.plot(rd, -0.45, "D", color="#8e44ad", ms=8)
ax.text(rhi + 0.0012, -0.45, f"H1 的次证据：BM25 秩差 {rd:+.4f} 位\nCI [{rlo:.4f}, {rhi:.4f}]，p_boot=0.016\n（秩变差，hit1 几乎不动）",
        va="center", fontsize=8.5, color="#8e44ad")
ax.axvline(0, color="black", lw=0.9, ls="--")
ax.set_yticks([0, 1, 2]); ax.set_yticklabels(["H1", "H2", "H3"], fontsize=11)
ax.set_ylim(-0.9, 2.6)
ax.set_xlabel("效应量（hit1 差 / 秩差 / β）", fontsize=10)
ax.set_title("图2  三个预注册假设的判定：一条不可解释、一个零、一个显著的负效应",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="x", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig2_verdict_forest.png", bbox_inches="tight")
plt.close()

# ===== 图3 分层描述性梯度：增益随原描述长度衰减 =====
fig, ax = plt.subplots(figsize=(9, 4.8))
names = [f"{s['stratum']}\n(均值 {s['mean_tokens']:.1f} tok)" for s in strata]
gains = [s["hit1_gain"] for s in strata]
glo = [s["gain_ci"][0] for s in strata]
ghi = [s["gain_ci"][1] for s in strata]
xs = np.arange(3)
for i, (g, lo, hi) in enumerate(zip(gains, glo, ghi)):
    c = C_ACC if g >= 0 else C_PART
    ax.plot([i, i], [lo, hi], color=c, lw=3, alpha=0.85)
    ax.plot(i, g, "D", color=c, ms=10)
    ax.text(i + 0.09, g, f"{g:+.4f}\np_boot={strata[i]['gain_p_boot']:.3f}",
            va="center", fontsize=9)
ax.axhline(0, color="black", lw=0.9, ls="--")
ax.set_xticks(xs); ax.set_xticklabels(names, fontsize=9.5)
ax.set_ylabel("用例改写的 hit1 增益（自然长度）", fontsize=10)
ax.set_ylim(-0.008, 0.009)
ax.set_title("图3  H2 的描述性材料：增益随原描述变长单调衰减、在长描述层转负，\n"
             "但三层均未过显著性（这是描述性分层，不构成 H2 的检验结论）",
             fontsize=11.5, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="y", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig3_strata_gradient.png", bbox_inches="tight")
plt.close()

# ===== 图4 匹配长度的代价及其长度斜率 =====
fig, ax = plt.subplots(figsize=(9, 4.9))
b0 = h3["mean_difference"]
sl = h3["slope_on_length"]
z = np.linspace(-1.8, 1.8, 100)
fit = b0 + sl["beta"] * z
ax.plot(z, fit, color=C_PART, lw=2.2)
ax.fill_between(z, b0 + sl["ci_lo"] * z, b0 + sl["ci_hi"] * z, color=C_PART, alpha=0.15)
zx = -b0 / sl["beta"]
ax.axhline(0, color="black", lw=0.9, ls="--")
ax.text(-1.7, -0.002,
        f"截距（平均长度处）：Δ = {b0:+.4f}\n95% CI [{h3['ci'][0]:.4f}, {h3['ci'][1]:.4f}]\n"
        f"len_z 斜率 β = {sl['beta']:+.4f} [{sl['ci_lo']:.4f}, {sl['ci_hi']:.4f}]，p_raw={sl['p_raw']:.2e}\n"
        f"线性外推的伤害归零点在 len_z≈{zx:.1f}，远超观测范围\n（z 在 [-1.8, 1.8] 内）：观测范围内代价恒为负",
        fontsize=9, color=C_PART)
ax.annotate("观测范围内代价\n处处显著为负", (1.5, b0 + sl["beta"] * 1.5),
            textcoords="offset points", xytext=(-10, 26), fontsize=9, color="#1f3f66", ha="right",
            arrowprops=dict(arrowstyle="->", color="#1f3f66", lw=1))
ax.set_xlabel("原描述长度（标准化 z）", fontsize=10)
ax.set_ylabel("匹配长度下用例框架的 hit1 变化", fontsize=10)
ax.set_title("图4  H3 的完整形状：同长度下用例框架平均差 -0.0226，\n"
             "且代价随原描述变长而显著衰减（交互斜率 0.0058）",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig4_matched_cost_slope.png", bbox_inches="tight")
plt.close()

print("P018 figures done:", [p.name for p in sorted(OUT.glob("custom_*.png"))])
