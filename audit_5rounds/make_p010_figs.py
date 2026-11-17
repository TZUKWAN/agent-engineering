# -*- coding: utf-8 -*-
"""P010 定制图：基于 T109 (lexical-semantic conflict) 产物数据。"""
import json, glob, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 300

fs = [f for f in glob.glob("results_raw/EXP0125_*.json") if "summary" not in f]
art = json.load(open(max(fs, key=lambda x: pathlib.Path(x).stat().st_mtime), encoding="utf-8"))
OUT = pathlib.Path("papers/P010_lexical_semantic_conflict/figures")
OUT.mkdir(parents=True, exist_ok=True)

# ===== 图1: 冲突解决分布 =====
h1 = art["H1"]
fig, ax = plt.subplots(figsize=(7, 4.5))
cats = ["词法胜出", "语义胜出", "两者一致", "均不一致"]
vals = [h1["lexical"], h1["semantic"], h1["both"], h1["neither"]]
colors = ["#e74c3c", "#2980b9", "#2ecc71", "#95a5a6"]
bars = ax.bar(range(4), vals, color=colors, alpha=0.7, width=0.5)
ax.set_xticks(range(4)); ax.set_xticklabels(cats, fontsize=10)
ax.set_ylabel("查询数", fontsize=10)
ax.set_title("图1  词法与语义检索器冲突时的选择分布", fontsize=12, fontweight="bold", pad=12)
for bar, v in zip(bars, vals):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 50,
            f"{v}", ha="center", va="bottom", fontsize=10)
# 加参考线：机会率 50%
ax.axhline(h1["n_decidable"] * 0.5, color="gray", lw=1, ls="--", label="机会率 50%")
ax.legend(fontsize=9)
fig.tight_layout()
fig.savefig(OUT / "custom_fig1_conflict_resolution.png", bbox_inches="tight")
plt.close()

# ===== 图2: H1 比例图 =====
fig, ax = plt.subplots(figsize=(6, 4))
prop = h1["proportion"]
null_val = h1["null_value"]
ci_lo, ci_hi = h1["ci_clustered"]
bar = ax.bar([0], [prop], color="#2980b9", alpha=0.7, width=0.3)
ax.errorbar(0, prop, yerr=[[prop - ci_lo], [ci_hi - prop]], fmt="none", ecolor="black", capsize=5, lw=1.5)
ax.axhline(null_val, color="red", lw=1, ls="--", label=f"机会率 = {null_val}")
ax.set_xticks([0]); ax.set_xticklabels(["词法胜出比例"], fontsize=10)
ax.set_ylabel("比例", fontsize=10)
ax.set_title("图2  H1：冲突时选择遵循词法胜出者的比例", fontsize=12, fontweight="bold", pad=12)
ax.text(0.05, prop + 0.01, f"{prop:.4f} (95% CI [{ci_lo:.4f}, {ci_hi:.4f}])", fontsize=10)
ax.legend(fontsize=9)
ax.set_xlim(-0.5, 0.5)
fig.tight_layout()
fig.savefig(OUT / "custom_fig2_h1_proportion.png", bbox_inches="tight")
plt.close()

# ===== 图3: H2 目录大小调节 =====
h2 = art["H2"]
fig, ax = plt.subplots(figsize=(6, 4))
cats2 = ["小目录", "大目录"]
rates = [h2["small_rate"], h2["big_rate"]]
bars = ax.bar(cats2, rates, color=["#2980b9", "#e74c3c"], alpha=0.7, width=0.4)
ax.set_ylabel("词法跟随率", fontsize=10)
ax.set_title("图3  H2：按目录大小的词法跟随率", fontsize=12, fontweight="bold", pad=12)
for bar, r in zip(bars, rates):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
            f"{r:.4f}", ha="center", va="bottom", fontsize=10)
# gap 标注
gap = h2["gap"]
ax.annotate(f"差值 = {gap:.4f}\np = {h2['p_raw']:.2e}",
            xy=(0.5, (rates[0] + rates[1]) / 2), fontsize=10, ha="center",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", edgecolor="gray"))
fig.tight_layout()
fig.savefig(OUT / "custom_fig3_catalogue_size.png", bbox_inches="tight")
plt.close()

# ===== 图4: H3 一致性指标 =====
h3 = art["H3"]
fig, ax = plt.subplots(figsize=(6, 4))
metrics = ["Kappa 一致性", "Top-1 一致率", "Spearman ρ"]
vals = [h3["kappa"], h3["top1_agreement"], h3["spearman_max_scores"]]
colors_h = ["#2980b9", "#2ecc71", "#f39c12"]
bars = ax.bar(metrics, vals, color=colors_h, alpha=0.7, width=0.4)
ax.set_ylabel("一致性/相关性", fontsize=10)
ax.set_title("图4  H3：词法与语义检索排名的一致性", fontsize=12, fontweight="bold", pad=12)
for bar, v in zip(bars, vals):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
            f"{v:.4f}", ha="center", va="bottom", fontsize=10)
fig.tight_layout()
fig.savefig(OUT / "custom_fig4_agreement.png", bbox_inches="tight")
plt.close()

print("P010 定制图: 4 张已生成")
for f in sorted(OUT.glob("custom_*.png")):
    print(f"  {f.name} ({f.stat().st_size // 1024}KB)")
