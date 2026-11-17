# -*- coding: utf-8 -*-
"""P009 定制图：基于 T108 (lexical match bias) 产物数据。"""
import json, glob, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 300

fs = [f for f in glob.glob("results_raw/EXP0124_*.json") if "summary" not in f]
art = json.load(open(max(fs, key=lambda x: pathlib.Path(x).stat().st_mtime), encoding="utf-8"))
OUT = pathlib.Path("papers/P009_lexical_match_bias/figures")
OUT.mkdir(parents=True, exist_ok=True)

C_SUP = "#2980b9"; C_OPP = "#c0392b"; C_NULL = "#7f8c8d"

# ===== 图1: 森林图（三个假设）=====
fig, ax = plt.subplots(figsize=(8, 5))
# H1: displacement excess
h1 = art["lexical_displacement"]
ax.plot([h1["excess"] + h1["ci_clustered"][0], h1["excess"] + h1["ci_clustered"][1]], [0, 0],
        color=C_OPP, lw=2, alpha=0.7)
ax.plot(h1["excess"], 0, "D", color=C_OPP, markersize=7)
ax.axvline(0, color="gray", lw=0.8, ls=":")
ax.text(h1["excess"] + h1["ci_clustered"][1] + 0.02, 0,
        f"H1: displacement excess = {h1['excess']:.4f}\n(opposite, p_holm={h1['p_holm']:.3f})",
        va="center", fontsize=8)

# H2: decoy asymmetry (relative selection ratio)
h2 = art["decoy_asymmetry"]
rsr = h2["relative_selection_ratio"]
ci = h2["ci_clustered"]
ax.plot([ci[0], ci[1]], [1, 1], color=C_SUP, lw=2, alpha=0.7)
ax.plot(rsr, 1, "D", color=C_SUP, markersize=7)
ax.axvline(1.0, color="blue", lw=0.8, ls=":", label="无偏好基线 (=1)")
ax.text(ci[1] + 0.05, 1, f"H2: 相对选择比 = {rsr:.3f}\n(supported, p_holm<0.001)",
        va="center", fontsize=8)

# H3: bias term
h3 = art["models"][0]
b, lo, hi = h3["beta"], h3["ci_lo"], h3["ci_hi"]
ax.plot([lo, hi], [2, 2], color=C_NULL, lw=2, alpha=0.7)
ax.plot(b, 2, "D", color=C_NULL, markersize=7)
ax.text(hi + 0.005, 2, f"H3: bias term = {b:.4f}\n(null, p_holm={h3['p_holm']:.3f})",
        va="center", fontsize=8)

ax.set_yticks(range(3)); ax.set_yticklabels(["H1\n位移超量", "H2\n诱饵不对称", "H3\n偏倚项"], fontsize=9)
ax.set_xlabel("效应量", fontsize=10)
ax.set_title("图1  三个预注册假设的效应量与置信区间", fontsize=12, fontweight="bold", pad=12)
ax.invert_yaxis()
ax.legend(fontsize=8, loc="lower right")
fig.tight_layout()
fig.savefig(OUT / "custom_fig1_forest.png", bbox_inches="tight")
plt.close()

# ===== 图2: 诱饵不对称（按重叠类别的选择份额）=====
table = h2.get("table", [])
if table:
    classes = [t["overlap_class"] for t in table]
    shares = [t["share"] for t in table]
    top1_shares = [t["top1_share"] for t in table]
    class_cn = {"gold": "金标工具", "nongold_high": "高重叠非金标", "nongold_low": "低重叠非金标"}
    x = np.arange(len(classes))
    width = 0.35
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars1 = ax.bar(x - width/2, shares, width, label="候选列表占比", color="#95a5a6", alpha=0.7)
    bars2 = ax.bar(x + width/2, top1_shares, width, label="Top-1 占比", color="#e74c3c", alpha=0.7)
    ax.set_xticks(x); ax.set_xticklabels([class_cn.get(c, c) for c in classes], fontsize=9)
    ax.set_ylabel("比例", fontsize=10)
    ax.set_title("图2  按词汇重叠类别的候选分布 vs Top-1 选中分布", fontsize=12, fontweight="bold", pad=12)
    ax.legend(fontsize=9)
    for bars in (bars1, bars2):
        for bar in bars:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005,
                    f"{bar.get_height():.3f}", ha="center", va="bottom", fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "custom_fig2_decoy.png", bbox_inches="tight")
    plt.close()

# ===== 图3: 位移率 vs 机会率 =====
fig, ax = plt.subplots(figsize=(6, 4.5))
bars = ax.bar([0, 1], [h1["rate"], h1["chance_rate"]], color=[C_OPP, "#95a5a6"], alpha=0.7, width=0.4)
ax.set_xticks([0, 1]); ax.set_xticklabels(["实际位移率", "机会率（基线）"], fontsize=10)
ax.set_ylabel("比例", fontsize=10)
ax.set_title("图3  高重叠非金标候选的位移率 vs 机会率", fontsize=12, fontweight="bold", pad=12)
ax.text(0, h1["rate"] + 0.01, f"{h1['rate']:.4f}", ha="center", fontsize=10)
ax.text(1, h1["chance_rate"] + 0.01, f"{h1['chance_rate']:.4f}", ha="center", fontsize=10)
# 标注 excess
excess = h1["rate"] - h1["chance_rate"]
ax.annotate(f"excess = {excess:.4f}", xy=(0.5, (h1["rate"] + h1["chance_rate"]) / 2),
            fontsize=10, ha="center", color=C_OPP,
            arrowprops=dict(arrowstyle="->", color=C_OPP, lw=1))
fig.tight_layout()
fig.savefig(OUT / "custom_fig3_displacement.png", bbox_inches="tight")
plt.close()

# ===== 图4: H1-H2-H3 逻辑关系图 =====
fig, ax = plt.subplots(figsize=(8, 4))
ax.axis("off")
boxes = [
    (0.15, 0.7, "H1 位移率\n低于机会\n(opposite)", C_OPP),
    (0.5, 0.7, "H2 诱饵不对称\n高重叠更常被选中\n(supported)", C_SUP),
    (0.85, 0.7, "H3 控制金标后\n偏倚消失\n(null)", C_NULL),
]
for x, y, txt, c in boxes:
    ax.add_patch(plt.Rectangle((x-0.12, y-0.12), 0.24, 0.24, fill=True,
                                facecolor=c, alpha=0.15, edgecolor=c, lw=2))
    ax.text(x, y, txt, ha="center", va="center", fontsize=9, color=c, fontweight="bold")
# 箭头
ax.annotate("", xy=(0.38, 0.7), xytext=(0.27, 0.7), arrowprops=dict(arrowstyle="->", color="gray"))
ax.annotate("", xy=(0.73, 0.7), xytext=(0.62, 0.7), arrowprops=dict(arrowstyle="->", color="gray"))
ax.text(0.5, 0.3, "表面层面的诱饵不对称（H2）在控制金标相关性后消失（H3），\n表明词汇重叠本身不是偏倚来源，真正的驱动力是金标相关性",
        ha="center", fontsize=9, style="italic")
ax.set_xlim(0, 1); ax.set_ylim(0, 1)
ax.set_title("图4  三个假设的逻辑关系", fontsize=12, fontweight="bold")
fig.tight_layout()
fig.savefig(OUT / "custom_fig4_logic.png", bbox_inches="tight")
plt.close()

print("P009 定制图: 4 张已生成")
for f in sorted(OUT.glob("custom_*.png")):
    print(f"  {f.name} ({f.stat().st_size // 1024}KB)")
