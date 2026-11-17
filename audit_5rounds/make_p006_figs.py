# -*- coding: utf-8 -*-
"""P006 定制图：基于 T101 (underspecified needs) 产物数据，每张图独立设计。
输出: papers/P006_underspecified_needs/figures/custom_fig{1-4}.png (300 DPI)
"""
import json, glob, pathlib, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np

# 中文字体
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "SimSun"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 300

# 数据
fs = [f for f in glob.glob("results_raw/EXP0121_*.json") if "summary" not in f]
art = json.load(open(max(fs, key=lambda x: pathlib.Path(x).stat().st_mtime), encoding="utf-8"))
OUT = pathlib.Path("papers/P006_underspecified_needs/figures")
OUT.mkdir(parents=True, exist_ok=True)

models = art["models"]
tertiles = art["tertiles"]
robust = art["robustness"]
baselines = art["baselines"]
holm = art["holm"]

C_NULL = "#7f8c8d"
C_OPP = "#c0392b"
C_SUP = "#2980b9"

# ===== 图1: 森林图（三个假设系数 + 95% CI）=====
fig, ax = plt.subplots(figsize=(8, 4.5))
labels = []
betas, los, his, colors = [], [], [], []
hyp_names = ["H1: 搜索深度", "H2: 澄清率", "H3: 错误工具率"]
for i, m in enumerate(models):
    betas.append(m["beta"])
    los.append(m["ci_lo"])
    his.append(m["ci_hi"])
    v = m["verdict"]
    colors.append(C_SUP if v == "supported" else C_OPP if v == "opposite" else C_NULL)
    labels.append(f"{hyp_names[i]}\n(β={m['beta']:.4f}, p_holm={m['p_holm']:.3f})")

y_pos = range(len(labels))
ax.barh(y_pos, betas, color=colors, alpha=0.6, height=0.4)
ax.errorbar(betas, y_pos, xerr=[np.array(betas) - np.array(los), np.array(his) - np.array(betas)],
            fmt="none", ecolor="black", capsize=4, lw=1.2)
ax.axvline(0, color="black", lw=0.8, ls="--")
ax.set_yticks(y_pos)
ax.set_yticklabels(labels, fontsize=9)
ax.set_xlabel("回归系数（β）及 95% CI", fontsize=10)
ax.set_title("图1  三个预注册假设的效应量与置信区间", fontsize=12, fontweight="bold", pad=12)
ax.invert_yaxis()
# 判定词标注
for i, m in enumerate(models):
    v = m["verdict"]
    cn = {"null": "零效应", "opposite": "反向", "supported": "支持"}[v]
    ax.text(max(m["ci_hi"], 0.01) + 0.005, i, cn, va="center", fontsize=9, color=colors[i])
fig.tight_layout()
fig.savefig(OUT / "custom_fig1_forest.png", bbox_inches="tight")
plt.close()

# ===== 图2: 三分位分析（欠 specification 三分位组的关键指标对比）=====
fig, axes = plt.subplots(1, 3, figsize=(12, 4))
tert_labels = [t["tert"] for t in tertiles]
tert_cn = {"low": "低欠 specification", "mid": "中", "high": "高欠 specification"}
metrics = [("depth", "搜索深度"), ("clarify", "澄清率"), ("wrong_tool", "错误工具率")]
for ax_i, (key, label) in enumerate(metrics):
    vals = [t[key] for t in tertiles]
    bars = axes[ax_i].bar(range(3), vals, color=["#3498db", "#2ecc71", "#e74c3c"], alpha=0.7, width=0.5)
    axes[ax_i].set_xticks(range(3))
    axes[ax_i].set_xticklabels([tert_cn[t] for t in tert_labels], fontsize=8)
    axes[ax_i].set_title(label, fontsize=10)
    axes[ax_i].set_ylabel("均值" if ax_i == 0 else "")
    for bar, val in zip(bars, vals):
        axes[ax_i].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(vals) * 0.01,
                        f"{val:.4f}", ha="center", va="bottom", fontsize=8)
fig.suptitle("图2  按欠 specification 三分位分组的关键指标", fontsize=12, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(OUT / "custom_fig2_tertiles.png", bbox_inches="tight")
plt.close()

# ===== 图3: 稳健性检验森林图 =====
fig, ax = plt.subplots(figsize=(8, 6))
rob_labels = [r["robustness"] for r in robust]
rob_betas = [r["beta"] for r in robust]
rob_los = [r["ci_lo"] for r in robust]
rob_his = [r["ci_hi"] for r in robust]
y_pos = range(len(rob_labels))
for i, (b, lo, hi) in enumerate(zip(rob_betas, rob_los, rob_his)):
    color = C_OPP if hi < 0 else C_NULL
    ax.plot([lo, hi], [i, i], color=color, lw=1.5)
    ax.plot(b, i, "o", color=color, markersize=5)
ax.axvline(art["models"][2]["beta"], color=C_OPP, lw=1, ls=":", label=f"主模型 β={art['models'][2]['beta']:.4f}")
ax.axvline(0, color="black", lw=0.8, ls="--")
ax.set_yticks(y_pos)
ax.set_yticklabels(rob_labels, fontsize=8)
ax.set_xlabel("wrong_tool 回归系数（β）", fontsize=10)
ax.set_title("图3  稳健性检验：H3 效应在 9 种设定下的估计", fontsize=12, fontweight="bold", pad=12)
ax.invert_yaxis()
ax.legend(fontsize=8, loc="lower right")
fig.tight_layout()
fig.savefig(OUT / "custom_fig3_robustness.png", bbox_inches="tight")
plt.close()

# ===== 图4: 基线模型偏差对比 =====
fig, ax = plt.subplots(figsize=(7, 4))
bl_labels = [b["model"] for b in baselines]
bl_dev = [b["deviance"] for b in baselines]
bl_n = [b["n"] for b in baselines]
bars = ax.bar(range(len(bl_labels)), bl_dev, color=["#95a5a6", "#3498db", "#e74c3c", "#2ecc71"], alpha=0.7, width=0.5)
ax.set_xticks(range(len(bl_labels)))
ax.set_xticklabels(bl_labels, fontsize=8, rotation=15, ha="right")
ax.set_ylabel("偏差 (Deviance)", fontsize=10)
ax.set_title("图4  基线模型偏差对比（n=24,000）", fontsize=12, fontweight="bold", pad=12)
for bar, dev, n in zip(bars, bl_dev, bl_n):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 200,
            f"{dev:.0f}", ha="center", va="bottom", fontsize=8)
fig.tight_layout()
fig.savefig(OUT / "custom_fig4_baselines.png", bbox_inches="tight")
plt.close()

print("P006 定制图: 4 张已生成")
for f in sorted(OUT.glob("custom_*.png")):
    print(f"  {f.name} ({f.stat().st_size // 1024}KB)")
