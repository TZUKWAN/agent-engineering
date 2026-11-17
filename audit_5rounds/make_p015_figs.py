# -*- coding: utf-8 -*-
"""P015 定制图：基于 T115 (metadata quality model) 产物数据。"""
import json, glob, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 300

fs = sorted(glob.glob("results_raw/EXP0139_wave2_design_*.json"))
art = json.load(open(fs[-1], encoding="utf-8"))
OUT = pathlib.Path("papers/P015_metadata_quality_model/figures")
OUT.mkdir(parents=True, exist_ok=True)

# ===== 图1: 嵌套模型 AUROC 阶梯 =====
models = [m for m in art["models"] if "model" in m and "auroc" in m]
names = [m["model"] for m in models]
aurocs = [m["auroc"] for m in models]
fig, ax = plt.subplots(figsize=(9, 4.5))
colors_m = ["#95a5a6", "#3498db", "#2ecc71", "#e74c3c", "#9b59b6"]
bars = ax.barh(range(len(names)), aurocs, color=colors_m, alpha=0.7, height=0.5)
ax.set_yticks(range(len(names)))
ax.set_yticklabels(names, fontsize=9)
ax.set_xlabel("AUROC", fontsize=10)
ax.set_title("图1  嵌套模型的 AUROC 阶梯", fontsize=12, fontweight="bold", pad=12)
ax.invert_yaxis()
for bar, a in zip(bars, aurocs):
    ax.text(bar.get_width() + 0.002, bar.get_y() + bar.get_height()/2, f"{a:.4f}", va="center", fontsize=9)
fig.tight_layout()
fig.savefig(OUT / "custom_fig1_auroc_ladder.png", bbox_inches="tight")
plt.close()

# ===== 图2: 嵌套增量瀑布图 =====
nd = art["nested_deltas"]
steps = ["length→agreement", "agreement→verb", "verb→enumeration"]
deltas = [nd["length->agreement"]["auroc_delta"], nd["agreement->verb"]["auroc_delta"],
          nd["verb->enumeration"]["auroc_delta"]]
lr_ps = [nd["length->agreement"]["p"], nd["agreement->verb"]["p"], nd["verb->enumeration"]["p"]]
fig, ax = plt.subplots(figsize=(8, 4.5))
colors_s = ["#2ecc71" if d > 0 else "#e74c3c" for d in deltas]
bars = ax.bar(range(len(steps)), deltas, color=colors_s, alpha=0.7, width=0.4)
ax.set_xticks(range(len(steps)))
ax.set_xticklabels([s.replace("->", " → ") for s in steps], fontsize=8, rotation=15, ha="right")
ax.set_ylabel("Δ AUROC", fontsize=10)
ax.set_title("图2  嵌套模型的 AUROC 增量", fontsize=12, fontweight="bold", pad=12)
for bar, d, lp in zip(bars, deltas, lr_ps):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.001,
            f"Δ={d:.4f}\np={lp:.1e}", ha="center", va="bottom", fontsize=8)
fig.tight_layout()
fig.savefig(OUT / "custom_fig2_nested_deltas.png", bbox_inches="tight")
plt.close()

# ===== 图3: 假设的 p_holm =====
holm = art["holm"]
fig, ax = plt.subplots(figsize=(6, 4))
hyp_names = list(holm.keys())
p_vals = [-np.log10(max(v, 1e-300)) for v in holm.values()]
bars = ax.bar(hyp_names, p_vals, color=["#2980b9", "#2ecc71", "#e74c3c"], alpha=0.7, width=0.4)
ax.axhline(-np.log10(0.05), color="red", lw=1, ls="--", label="α = 0.05")
ax.set_ylabel("-log10(p_holm)", fontsize=10)
ax.set_title("图3  三个假设的 Holm 校正后 p 值", fontsize=12, fontweight="bold", pad=12)
for bar, name in zip(bars, hyp_names):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
            f"p={holm[name]:.4f}", ha="center", va="bottom", fontsize=9)
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig(OUT / "custom_fig3_holm.png", bbox_inches="tight")
plt.close()

# ===== 图4: 权重稳定性 =====
ws = art.get("weight_stability", {})
if ws:
    fig, ax = plt.subplots(figsize=(6, 4))
    configs = ws["configs"]
    spearman = ws["pairwise_spearman"]
    pairs = [f"{configs[0]}-{configs[1]}", f"{configs[0]}-{configs[2]}", f"{configs[1]}-{configs[2]}"]
    bars = ax.bar(pairs, spearman, color="#3498db", alpha=0.7, width=0.4)
    ax.set_ylabel("Spearman ρ", fontsize=10)
    ax.set_title("图4  跨配置的权重稳定性", fontsize=12, fontweight="bold", pad=12)
    for bar, s in zip(bars, spearman):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                f"{s:.3f}", ha="center", va="bottom", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "custom_fig4_weight_stability.png", bbox_inches="tight")
    plt.close()

print("P015 定制图: 4 张已生成")
for f in sorted(OUT.glob("custom_*.png")):
    print(f"  {f.name} ({f.stat().st_size // 1024}KB)")
