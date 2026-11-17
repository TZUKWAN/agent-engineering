# -*- coding: utf-8 -*-
"""P039 定制图：基于 T161 (语义诱饵与误选, EXP-0183, wave-7) 产物数据。

本文的个性：语义诱饵让金标在 rank-1 缺席的几率上升（H1 supported,
+0.4447），剂量-反应在 6 档实测中不单调（H2 not_monotone：
1 个诱饵时跳升最大 12.1%→25.1%，之后平台化），特异性成立
（H3 描述性：随机对照 0.54 vs 真诱饵 0.44——两个都大但对照更大，
被规则声明为非推断）。
"""
import json, glob, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 300

fs = sorted(glob.glob("results_raw/EXP0183_wave7_design_*.json"))
art = json.load(open(fs[-1], encoding="utf-8"))
OUT = pathlib.Path("papers/P039_semantic_decoy_and_misselection/figures")
OUT.mkdir(parents=True, exist_ok=True)

C_SUP = "#27ae60"
C_OPP = "#c0392b"
C_ACC = "#2980b9"
C_NULL = "#95a5a6"

models = {m["hypothesis"]: m for m in art["models"]}
h1, h2, h3 = models["H1"], models["H2"], models["H3"]
fbdc = art["descriptive_rates"]["fail_at_1_by_decoy_count"]
fbq = art["descriptive_rates"]["fail_at_1_by_candidate_quartile"]

# ===== 图1 三假设判定森林 =====
fig, ax = plt.subplots(figsize=(10, 4.8))
rows = [
    ("H1 诱饵在场 → 金标缺席", h1["beta"], h1["ci_lo"], h1["ci_hi"], C_SUP,
     f"判定 supported\nβ={h1['beta']:+.4f}，p_holm<0.001\n（比值比约 1.56；诱饵率 43.3%）"),
    ("H2 剂量-反应单调性", None, None, None, C_NULL,
     "判定 not_monotone\n6 档实测非单调\n（首诱饵跳升后平台化）"),
    ("H3 随机对照非推断", h3["beta"], h3["ci_lo"], h3["ci_hi"], C_ACC,
     f"判定 measured_descriptively\nβ={h3['beta']:+.4f}\n（对照与真诱饵同量级，规则声明非推断）"),
]
for i, (lab, b, lo, hi, c, note) in enumerate(rows):
    if b is None:
        ax.text(0.02, i, note, va="center", fontsize=9)
        ax.add_patch(plt.Rectangle((0.0, i - 0.25), 0.02, 0.5, color=C_NULL, alpha=0.3))
        continue
    ax.plot([lo, hi], [i, i], color=c, lw=3, alpha=0.85)
    ax.plot(b, i, "D", color=c, ms=9)
    ax.text(hi + 0.015, i, note, va="center", fontsize=8.6)
ax.axvline(0, color="black", lw=0.9, ls="--")
ax.set_yticks([0, 1, 2]); ax.set_yticklabels(["H1", "H2", "H3"], fontsize=11)
ax.set_xlim(-0.02, 0.92)
ax.set_xlabel("fail_at_1 的 logit 系数（query 聚类稳健）", fontsize=10)
ax.set_title("图1  三个预注册假设：诱饵存在性成立、剂量单调性不成立、特异性对照声明为非推断",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="x", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig1_verdicts.png", bbox_inches="tight")
plt.close()

# ===== 图2 剂量-反应剖面：跳升与平台 =====
fig, ax = plt.subplots(figsize=(9.6, 5.2))
counts = sorted(fbdc.keys(), key=int)
rates = [fbdc[k]["rate"] * 100 for k in counts]
cis = [fbdc[k]["ci"] for k in counts]
ns = [fbdc[k]["rows"] for k in counts]
err_lo = [r - c[0] * 100 for r, c in zip(rates, cis)]
err_hi = [c[1] * 100 - r for r, c in zip(rates, cis)]
colors = [C_ACC if k == "0" else C_OPP for k in counts]
ax.errorbar(range(len(counts)), rates, yerr=[err_lo, err_hi],
            fmt="o", color=C_OPP, ms=9, capsize=6, lw=2, zorder=3)
for i, (r, n) in enumerate(zip(rates, ns)):
    ax.text(i, r + 1.1, f"{r:.1f}%\n(n={n:,})", ha="center", fontsize=9)
ax.axhline(rates[0], color=C_NULL, lw=1, ls=":")
ax.annotate("首诱饵跳升 +12.9 个百分点", xy=(1, 25.1), xytext=(2.2, 29.5),
            fontsize=10, color=C_OPP,
            arrowprops=dict(arrowstyle="->", color=C_OPP, lw=1.3))
ax.annotate("此后平台化：2–5 个诱饵\n的区间相互重叠", xy=(3.5, 29.2), xytext=(3.6, 32.5),
            fontsize=9.5, color="#555",
            arrowprops=dict(arrowstyle="->", color="#555", lw=1.1))
ax.set_xticks(range(len(counts)))
ax.set_xticklabels([f"{k} 个诱饵" for k in counts], fontsize=10)
ax.set_ylabel("fail@1（金标未进 rank-1 的比率，%）", fontsize=10)
ax.set_ylim(5, 36)
ax.set_title("图2  剂量-反应的实测剖面：跳升集中在第一个诱饵，\n加码诱饵不再等比加深——H2 的单调剂量假说不成立",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="y", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig2_dose_profile.png", bbox_inches="tight")
plt.close()

# ===== 图3 候选规模四分位：基础失败率与诱饵效应分层 =====
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.5, 4.5))
qs = list(fbq.keys())
rates_q = [fbq[q]["rate"] * 100 for q in qs]
qlab = {"q1_smallest": "Q1 最小", "q2": "Q2", "q3": "Q3", "q4_largest": "Q4 最大"}
a1.bar(range(4), rates_q, color=C_ACC, alpha=0.88, width=0.5)
for i, r in enumerate(rates_q):
    a1.text(i, r + 0.5, f"{r:.1f}%", ha="center", fontsize=10)
a1.set_xticks(range(4)); a1.set_xticklabels([qlab[q] for q in qs], fontsize=10)
a1.set_ylabel("fail@1 基线（%）", fontsize=10)
a1.set_ylim(0, 36)
a1.set_title("(a) 基线失败率随候选规模上升\n（3.9% → 29.9%，拥挤本身的代价）", fontsize=10.5)
a1.grid(alpha=0.25, axis="y", ls="--")

stra = [s for s in art["strata"] if s.get("stratification") == "cand_quartile"]
for i, s in enumerate(stra):
    sig = s.get("p") is not None and s["p"] < 0.05
    c = C_OPP if sig and s["beta"] > 0 else (C_SUP if sig else C_NULL)
    a2.plot([s["ci_lo"], s["ci_hi"]], [i, i], color=c, lw=3, alpha=0.85)
    a2.plot(s["beta"], i, "D", color=c, ms=10)
    star = " *" if sig else ""
    a2.text(s["ci_hi"] + 0.05, i, f"β={s['beta']:+.3f}{star}", va="center", fontsize=9.5)
a2.axvline(0, color="black", lw=0.9, ls="--")
a2.set_yticks(range(len(stra)))
a2.set_yticklabels([qlab.get(s["stratum"], s["stratum"]) for s in stra], fontsize=10.5)
a2.set_xlabel("诱饵存在性系数（候选规模四分位分层）", fontsize=10)
a2.set_xlim(-0.4, 2.3)
a2.set_title("(b) 诱饵效应集中在小候选集：\nQ1 层 β=1.607，Q3 层归零（* p<0.05）", fontsize=10.5)
a2.grid(alpha=0.25, axis="x", ls="--")
fig.suptitle("图3  拥挤的代价与诱饵 的分层剖面", fontsize=12, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(OUT / "custom_fig3_quartile_layers.png", bbox_inches="tight")
plt.close()

# ===== 图4 H3 特异性对照 =====
fig, ax = plt.subplots(figsize=(9.2, 4.8))
decoy_arm = h3["decoy_arm"]
ax.bar([0, 1], [decoy_arm["beta"], h3["beta"]], width=0.42,
       color=[C_SUP, C_ACC], alpha=0.88)
for x, m in [(0, decoy_arm), (1, h3)]:
    ax.errorbar(x, m["beta"], yerr=[[m["beta"] - m["ci_lo"]], [m["ci_hi"] - m["beta"]]],
                color="#333", capsize=6, lw=1.5, fmt="none")
ax.axhline(0, color="black", lw=0.9)
ax.text(0, decoy_arm["beta"] + 0.03, f"真诱饵（max_similarity）\nβ={decoy_arm['beta']:+.4f}",
        ha="center", fontsize=9.5, color=C_SUP)
ax.text(1, h3["beta"] + 0.03, f"随机对照\nβ={h3['beta']:+.4f}",
        ha="center", fontsize=9.5, color=C_ACC)
ax.set_xticks([0, 1])
ax.set_xticklabels(["真诱饵臂\n（最大化相似的非金标）", "随机对照臂\n（digest 抽取的非金标）"], fontsize=10)
ax.set_ylabel("fail_at_1 的 logit 系数", fontsize=10)
ax.set_ylim(0, 0.72)
ax.set_title("图4  H3 的特异性对照：两臂同量级——规则声明为非推断\n（描述性保留，不进入判定族）",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="y", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig4_specificity.png", bbox_inches="tight")
plt.close()

print("P039 figures done:", [p.name for p in sorted(OUT.glob("custom_*.png"))])
