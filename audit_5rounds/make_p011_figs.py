# -*- coding: utf-8 -*-
"""P011 定制图：基于 T110 (predicate-argument relevance) 产物数据。"""
import json, glob, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 300

fs = [f for f in glob.glob("results_raw/EXP0126_*.json") if "summary" not in f]
art = json.load(open(max(fs, key=lambda x: pathlib.Path(x).stat().st_mtime), encoding="utf-8"))
OUT = pathlib.Path("papers/P011_predicate_argument_relevance/figures")
OUT.mkdir(parents=True, exist_ok=True)

C_SUP = "#2980b9"; C_OPP = "#c0392b"; C_NULL = "#7f8c8d"; C_PART = "#f39c12"

# ===== 图1: 模型 AUROC 阶梯图 =====
models = art["models"]
model_names = [m["model"] for m in models]
aurocs = [m["auroc"] for m in models]
fig, ax = plt.subplots(figsize=(9, 4.5))
colors_m = ["#95a5a6", "#3498db", "#2ecc71", "#e74c3c", "#9b59b6"]
bars = ax.barh(range(len(model_names)), aurocs, color=colors_m, alpha=0.7, height=0.5)
ax.set_yticks(range(len(model_names)))
ax.set_yticklabels(model_names, fontsize=9)
ax.set_xlabel("AUROC", fontsize=10)
ax.set_title("图1  五个嵌套模型的 AUROC 阶梯", fontsize=12, fontweight="bold", pad=12)
ax.invert_yaxis()
for bar, a in zip(bars, aurocs):
    ax.text(bar.get_width() + 0.001, bar.get_y() + bar.get_height()/2, f"{a:.4f}",
            va="center", fontsize=9)
fig.tight_layout()
fig.savefig(OUT / "custom_fig1_auroc_ladder.png", bbox_inches="tight")
plt.close()

# ===== 图2: AUROC 增益与 CI =====
gain = art["auroc_gain"]
fig, ax = plt.subplots(figsize=(6, 4))
ax.errorbar(gain["delta"], 0, xerr=[[gain["delta"] - gain["ci"][0]], [gain["ci"][1] - gain["delta"]]],
            fmt="D", color="#2980b9", markersize=8, capsize=5, lw=2)
ax.axvline(0, color="gray", lw=0.8, ls="--")
ax.set_xlabel("AUROC 增益（Δ）", fontsize=10)
ax.set_title("图2  谓词—论元特征对 AUROC 的增益", fontsize=12, fontweight="bold", pad=12)
ax.text(gain["delta"] + 0.0005, 0, f"Δ = {gain['delta']:.4f}\n95% CI [{gain['ci'][0]:.4f}, {gain['ci'][1]:.4f}]",
        fontsize=9, va="center")
fig.tight_layout()
fig.savefig(OUT / "custom_fig2_auroc_gain.png", bbox_inches="tight")
plt.close()

# ===== 图3: 可分离性指标 =====
sep = art["separability"]
fig, ax = plt.subplots(figsize=(6, 4))
sep_labels = ["谓词在语义嵌入中\n的可分离性", "论元在语义嵌入中\n的可分离性"]
sep_vals = [sep["pred_in_dense"], sep["arg_in_dense"]]
sep_ps = [sep["pred_p"], sep["arg_p"]]
bars = ax.bar(sep_labels, sep_vals, color=["#3498db", "#2ecc71"], alpha=0.7, width=0.4)
ax.set_ylabel("效应量（标准化差异）", fontsize=10)
ax.set_title("图3  谓词与论元在语义嵌入空间中的可分离性", fontsize=12, fontweight="bold", pad=12)
for bar, v, pv in zip(bars, sep_vals, sep_ps):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.002,
            f"{v:.4f}\np={pv:.2e}", ha="center", va="bottom", fontsize=9)
fig.tight_layout()
fig.savefig(OUT / "custom_fig3_separability.png", bbox_inches="tight")
plt.close()

# ===== 图4: 特征覆盖率 =====
cov = art["coverage"]
fig, ax = plt.subplots(figsize=(7, 4))
cov_labels = ["谓词覆盖率", "论元覆盖率", "描述中论元覆盖"]
cov_vals = [cov["predicate_coverage"], cov["argument_coverage"], cov["desc_argument_coverage"]]
bars = ax.bar(cov_labels, cov_vals, color=["#3498db", "#2ecc71", "#f39c12"], alpha=0.7, width=0.4)
ax.set_ylabel("覆盖率", fontsize=10)
ax.set_title("图4  谓词与论元特征的覆盖率", fontsize=12, fontweight="bold", pad=12)
for bar, v in zip(bars, cov_vals):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
            f"{v:.3f}", ha="center", va="bottom", fontsize=10)
fig.tight_layout()
fig.savefig(OUT / "custom_fig4_coverage.png", bbox_inches="tight")
plt.close()

print("P011 定制图: 4 张已生成")
for f in sorted(OUT.glob("custom_*.png")):
    print(f"  {f.name} ({f.stat().st_size // 1024}KB)")
