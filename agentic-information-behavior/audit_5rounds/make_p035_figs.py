# -*- coding: utf-8 -*-
"""P035 定制图：基于 T158 (边际收益与搜索坚持, EXP-0176, wave-6) 产物数据。

本文的个性：丰收不停手——新信息越多越继续（H1 opposite, +0.63，
LR χ²=10,418；十分位延续率 86.8%→97.6% 单调上升），与觅食理论
"丰产区块停留"一致（设计者把自家理论的预言写反了）；
H2 前提普查 18.55%<20% 判 not_testable；H3 四分位全不复现。
"""
import json, glob, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 300

fs = sorted(glob.glob("results_raw/EXP0176_wave6_design_*.json"))
art = json.load(open(fs[-1], encoding="utf-8"))
OUT = pathlib.Path("papers/P035_marginal_gain_and_search_persistence/figures")
OUT.mkdir(parents=True, exist_ok=True)

C_SUP = "#27ae60"
C_OPP = "#c0392b"
C_ACC = "#2980b9"
C_NULL = "#95a5a6"

models = {m["hypothesis"]: m for m in art["models"]}
h1, h2, h3 = models["H1"], models["H2"], models["H3"]
dec = art["descriptive_rates"]["continuation_by_observation_newness_decile"]
rep = art["descriptive_rates"]["newness_by_repetition"]

# ===== 图1 三假设判定森林 =====
fig, ax = plt.subplots(figsize=(10, 4.6))
rows = [
    ("H1 新信息 → 继续", h1["beta"], h1["ci_lo"], h1["ci_hi"], C_OPP,
     f"判定 opposite\nβ={h1['beta']:+.4f}，p_holm<0.001\n（预测负，实测强正：丰收不停手）"),
    ("H2 失败 → 继续", h2["beta"], h2["ci_lo"], h2["ci_hi"], C_NULL,
     f"判定 not_testable\n前提普查 18.55% < 底线 20%\n（β=−0.0302，CI 跨零，不入结论）"),
]
for i, (lab, b, lo, hi, c, note) in enumerate(rows):
    ax.plot([lo, hi], [i, i], color=c, lw=3, alpha=0.85)
    ax.plot(b, i, "D", color=c, ms=9)
    ax.text(hi + 0.015, i, note, va="center", fontsize=8.6)
ax.axvline(0, color="black", lw=0.9, ls="--")
ax.set_yticks([0, 1]); ax.set_yticklabels(["H1", "H2"], fontsize=11)
ax.set_xlim(-0.14, 0.86)
ax.set_xlabel("对继续概率的系数（logit，聚类稳健）", fontsize=10)
ax.set_title("图1  两个可估假设：丰收加剧坚持，失败检验因前提不足封存",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="x", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig1_verdicts.png", bbox_inches="tight")
plt.close()

# ===== 图2 新信息十分位与延续率：单调上升的钱图 =====
fig, ax = plt.subplots(figsize=(9.6, 5.0))
deciles = sorted(dec.keys(), key=int)
share = [dec[k]["continue_share"] * 100 for k in deciles]
ax.plot(range(10), share, "o-", color=C_ACC, lw=2.2, ms=8)
for i, (s, k) in enumerate(zip(share, deciles)):
    ax.text(i, s + 0.22, f"{s:.1f}%\n(n={dec[k]['rows']:,})", ha="center", fontsize=8.2)
ax.set_xticks(range(10))
ax.set_xticklabels([f"D{int(k)+1}" for k in deciles], fontsize=10)
ax.set_xlabel("上一步观察的新信息率十分位（D1 最低 → D10 最高）", fontsize=10)
ax.set_ylabel("继续下一步的比率（%）", fontsize=10)
ax.set_ylim(84, 100)
ax.set_title("图2  核心发现：上一步收获越丰富，越可能继续——\n延续率从 86.8% 单调爬升到 97.6%（与冻结预期完全反向）",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="y", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig2_decile_curve.png", bbox_inches="tight")
plt.close()

# ===== 图3 新信息量的效度检验：重复观察近零 =====
fig, ax = plt.subplots(figsize=(9.2, 4.8))
reps = sorted(rep.keys(), key=int)
means = [rep[k]["mean_newness"] for k in reps]
ns = [rep[k]["rows"] for k in reps]
ax.bar(range(len(reps)), means, color=C_ACC, alpha=0.88, width=0.5)
for i, (m, n) in enumerate(zip(means, ns)):
    ax.text(i, m + 0.012, f"{m:.3f}\n(n={n:,})", ha="center", fontsize=9.5)
ax.set_xticks(range(len(reps)))
ax.set_xticklabels([f"第 {int(k)} 次\n重复" for k in reps], fontsize=10)
ax.set_ylabel("平均新信息率", fontsize=10)
ax.set_ylim(0, 0.72)
ax.set_title("图3  测量效度检验：同一调用的重复返回，新信息率从 0.611\n骤降至 0.017——量尺对\"新\"敏感、对\"复读\"盲",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="y", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig3_repetition_validity.png", bbox_inches="tight")
plt.close()

# ===== 图4 H2 前提底线 + 家族分层 =====
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.5, 4.6))
a1.bar([0, 1], [h2["census_share_measured"] * 100, h2["frozen_floor_share_of_observations"] * 100],
       color=[C_OPP, "#d5d8dc"], width=0.45)
a1.axhline(20, color="black", lw=1.2, ls="--")
a1.text(1, 20.6, "冻结底线 20%", fontsize=9.5, ha="center")
a1.text(0, h2["census_share_measured"] * 100 - 2.4,
        f"{h2['census_share_measured']*100:.2f}%\n（EXP-0172 普查）", ha="center",
        fontsize=10, color=C_OPP)
a1.set_xticks([0, 1]); a1.set_xticklabels(["普查实测", "冻结底线"], fontsize=10)
a1.set_ylabel("带失败标记观察的占比（%）", fontsize=10)
a1.set_ylim(0, 26)
a1.set_title("(a) H2 前提：失败观察占比 18.55% < 20%\n→ 检验封存（not_testable）", fontsize=10.5)
a1.grid(alpha=0.25, axis="y", ls="--")

fams = [s for s in art["strata"] if s.get("stratification") == "family" and s.get("beta") is not None]
fams = sorted(fams, key=lambda s: -s["beta"])[:8]
fig2, a2 = plt.subplots(figsize=(9.2, 4.6))
for i, s in enumerate(fams):
    c = C_SUP if s["beta"] > 0 else C_OPP
    a2.plot([s["ci_lo"], s["ci_hi"]], [i, i], color=c, lw=3, alpha=0.85)
    a2.plot(s["beta"], i, "D", color=c, ms=9)
    a2.text(s["ci_hi"] + 0.03, i, f"β={s['beta']:+.3f}", va="center", fontsize=8.5)
a2.set_yticks(range(len(fams)))
a2.set_yticklabels([s["stratum"].replace("_", " ").title() for s in fams], fontsize=9.5)
a2.axvline(0, color="black", lw=0.9, ls="--")
a2.set_xlabel("新信息 → 继续的族内系数（前 8 族，描述性）", fontsize=10)
a2.set_xlim(0, 1.05)
a2.set_title("(b) 丰收效应跨命令族全部为正", fontsize=10.5)
a2.grid(alpha=0.25, axis="x", ls="--")
fig.suptitle("图4  H2 的前提封存与 H1 的族内稳健性", fontsize=12, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(OUT / "custom_fig4_floor_families.png", bbox_inches="tight")
plt.close()

print("P035 figures done:", [p.name for p in sorted(OUT.glob("custom_*.png"))])
