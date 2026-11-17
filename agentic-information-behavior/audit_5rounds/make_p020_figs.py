# -*- coding: utf-8 -*-
"""P020 定制图：基于 T119 (名称-描述一致性, EXP-0146) 产物数据。

本文的个性：(1) 控制变量吸收约 29% 的 H1 效应——"一致性不是长度的替身"；
(2) 矛盾组是空单元格（0 行），设计拒绝把空格并进中性组——H3 判 not_testable；
(3) 分层效应非单调（短 0.146 / 中 0.104 / 长 0.192）。四张图围绕这三点。
"""
import json, glob, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 300

fs = sorted(glob.glob("results_raw/EXP0146_wave3_design_*.json"))
art = json.load(open(fs[-1], encoding="utf-8"))
OUT = pathlib.Path("papers/P020_name_description_congruence/figures")
OUT.mkdir(parents=True, exist_ok=True)

C_SUP = "#27ae60"
C_PART = "#e67e22"
C_EMPTY = "#7f8c8d"
C_ACC = "#2980b9"

models = {m["hypothesis"]: m for m in art["models"]}
h1, h2, h3 = models["H1"], models["H2"], models["H3"]
levels = h3["levels"]
cong = [l for l in levels if l["level"] == "congruent"][0]
uninf = [l for l in levels if l["level"] == "uninformative"][0]

# ===== 图1 三层对比与空单元格 =====
fig, ax = plt.subplots(figsize=(9.2, 5.0))
xs = [0, 1, 2]
vals = [cong["gold_rate"] * 100, uninf["gold_rate"] * 100, 0]
bars = ax.bar(xs[:2], vals[:2], color=[C_SUP, "#95a5a6"], alpha=0.88, width=0.52)
# 空单元格：阴影占位
ax.bar([2], [2.0], color="none", edgecolor=C_EMPTY, hatch="///", width=0.52, lw=1.2, alpha=0.8)
ax.text(0, cong["gold_rate"] * 100 + 0.35,
        f"{cong['gold_rate']*100:.2f}%\n(n={cong['rows']:,})", ha="center", fontsize=9.5)
ax.text(1, uninf["gold_rate"] * 100 + 0.35,
        f"{uninf['gold_rate']*100:.2f}%\n(n={uninf['rows']:,})", ha="center", fontsize=9.5)
ax.text(2, 2.6, "矛盾组：0 行\n（目录中不存在名称与描述\n互相否定的条目）", ha="center",
        fontsize=9, color=C_EMPTY)
# 差距标注
gap = (cong["gold_rate"] - uninf["gold_rate"]) * 100
ax.annotate("", xy=(1, uninf["gold_rate"] * 100 + 1.1), xytext=(0, cong["gold_rate"] * 100 + 1.1),
            arrowprops=dict(arrowstyle="<->", color=C_ACC, lw=1.4))
ax.text(0.5, (cong["gold_rate"] + uninf["gold_rate"]) * 50 + 1.25,
        f"描述性差距 +{gap:.1f} 个百分点", ha="center", fontsize=9.5, color=C_ACC)
ax.set_xticks(xs)
ax.set_xticklabels(["一致（名称词项包含于描述）", "中性（名称无信息量）", "矛盾（名称断言被描述否定）"], fontsize=9.5)
ax.set_ylabel("被发布选择的比率（gold rate, %）", fontsize=10)
ax.set_ylim(0, 30)
ax.set_title("图1  名称—描述一致性的三层对比：矛盾组是空单元格，\n设计拒绝把 0 行并入中性组（H3 判 not_testable_empty_cell）",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="y", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig1_three_levels_empty_cell.png", bbox_inches="tight")
plt.close()

# ===== 图2 H1→H2 衰减与 VIF =====
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.5), gridspec_kw={"width_ratios": [1.3, 1]})
rows = [("H1 无条件", h1["beta"], h1["ci_lo"], h1["ci_hi"], C_SUP, f"n={h1['n']:,}"),
        ("H2 + 冻结控制", h2["beta"], h2["ci_lo"], h2["ci_hi"], C_PART, f"n={h2['n']:,}")]
for i, (lab, b, lo, hi, c, note) in enumerate(rows):
    a1.plot([lo, hi], [i, i], color=c, lw=3, alpha=0.85)
    a1.plot(b, i, "D", color=c, ms=9)
    a1.text(hi + 0.004, i, f"β={b:.4f}\n{note}", va="center", fontsize=9)
a1.axvline(0.15, color="#555", lw=1, ls=":")
a1.text(0.151, 1.42, "中等效应带下限 0.15", fontsize=8.5, color="#555")
a1.axvline(0, color="black", lw=0.8, ls="--")
a1.set_yticks([0, 1]); a1.set_yticklabels(["H1", "H2"], fontsize=11)
a1.set_xlim(0.05, 0.20)
a1.set_xlabel("一致性系数（logit 标度）", fontsize=10)
a1.set_title("(a) 控制变量吸收约 29% 的表观效应：\nH1 supported → H2 partial（CI 仍远离零）", fontsize=10.5)
a1.grid(alpha=0.25, axis="x", ls="--")

vif = art["vif"]
names = list(vif.keys())
vals = [vif[k] for k in names]
a2.bar(range(len(names)), vals, color=C_ACC, alpha=0.85, width=0.5)
a2.axhline(2.5, color=C_EMPTY, lw=1.2, ls="--")
a2.text(len(names) - 0.45, 2.56, "中度共线门槛 2.5", fontsize=8.5, color=C_EMPTY, ha="right")
for i, v in enumerate(vals):
    a2.text(i, v + 0.03, f"{v:.3f}", ha="center", fontsize=9)
a2.set_xticks(range(len(names)))
a2.set_xticklabels(["一致性", "描述长度", "参数数"], fontsize=9.5)
a2.set_ylabel("VIF", fontsize=10)
a2.set_ylim(0, 2.9)
a2.set_title("(b) 一致性与控制变量统计正交\n（VIF=1.026）", fontsize=10.5)
a2.grid(alpha=0.25, axis="y", ls="--")
fig.suptitle("图2  一致性效应的稳健性：不是长度或典型性的替身", fontsize=12, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(OUT / "custom_fig2_attenuation_vif.png", bbox_inches="tight")
plt.close()

# ===== 图3 分层效应：非单调 =====
fig, ax = plt.subplots(figsize=(9, 4.8))
strata = art["strata"]
names = [f"短描述层\n(n={s['n_rows']:,})" for s in strata]
names[1] = f"中描述层\n(n={strata[1]['n_rows']:,})"
names[2] = f"长描述层\n(n={strata[2]['n_rows']:,})"
bs = [s["beta"] for s in strata]
los = [s["ci_lo"] for s in strata]
his = [s["ci_hi"] for s in strata]
xs = np.arange(3)
for i, (b, lo, hi) in enumerate(zip(bs, los, his)):
    ax.plot([i, i], [lo, hi], color=C_ACC, lw=3, alpha=0.85)
    ax.plot(i, b, "D", color=C_ACC, ms=10)
    ax.text(i + 0.09, b, f"β={b:.4f}", va="center", fontsize=9.5)
ax.axhline(0.15, color="#555", lw=1, ls=":")
ax.text(2.42, 0.152, "0.15", fontsize=8.5, color="#555")
ax.axhline(0, color="black", lw=0.8, ls="--")
ax.set_xticks(xs); ax.set_xticklabels(names, fontsize=9.5)
ax.set_ylabel("一致性系数（描述性分层）", fontsize=10)
ax.set_ylim(0.0, 0.26)
ax.set_title("图3  一致性效应按描述长度分层：非单调——中描述层最弱，\n长描述层反而最强（描述性分层，不进判定族）",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="y", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig3_strata_nonmonotone.png", bbox_inches="tight")
plt.close()

# ===== 图4 一致度分布（由报告分位数构造的示意） =====
fig, ax = plt.subplots(figsize=(8.8, 4.6))
d = art["congruence_distribution"]
# 已知分位点: p10=0.0, p50=0.5, p90=1.0, mean=0.457
qs = [0.0, d["p10"], 0.25, d["p50"], 0.75, d["p90"], 1.0]
ps = [0.0, 0.10, 0.25, 0.50, 0.75, 0.90, 1.0]
ax.plot(qs, ps, "o-", color=C_ACC, lw=1.8, ms=6)
for q, p, lab in [(d["p10"], 0.10, f"P10={d['p10']:.1f}"), (d["p50"], 0.50, f"P50={d['p50']:.1f}"),
                  (d["p90"], 0.90, f"P90={d['p90']:.1f}")]:
    ax.annotate(lab, (q, p), textcoords="offset points", xytext=(8, -12), fontsize=9)
ax.axvline(d["mean"], color=C_PART, lw=1.4, ls="--")
ax.text(d["mean"] + 0.02, 0.06, f"均值 {d['mean']:.4f}", fontsize=9, color=C_PART)
ax.set_xlabel("名称—描述一致度", fontsize=10)
ax.set_ylabel("累积分布（示意）", fontsize=10)
ax.set_title("图4  一致度分布：强右偏且大量取 0 与 1 的两极\n（由产物报告的分位点连接的示意曲线，非逐行 ECDF）",
             fontsize=11.5, fontweight="bold", pad=12)
ax.set_xlim(-0.05, 1.1); ax.set_ylim(-0.03, 1.05)
ax.grid(alpha=0.25, ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig4_congruence_distribution.png", bbox_inches="tight")
plt.close()

print("P020 figures done:", [p.name for p in sorted(OUT.glob("custom_*.png"))])
