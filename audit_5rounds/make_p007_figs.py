# -*- coding: utf-8 -*-
"""P007 定制图：基于 T103 (constraint density → retrieval quality) 产物数据。
输出: papers/P007_constraint_density/figures/custom_fig{1-4}.png (300 DPI)
"""
import json, glob, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 300

fs = [f for f in glob.glob("results_raw/EXP0122_*.json") if "summary" not in f]
art = json.load(open(max(fs, key=lambda x: pathlib.Path(x).stat().st_mtime), encoding="utf-8"))
OUT = pathlib.Path("papers/P007_constraint_density/figures")
OUT.mkdir(parents=True, exist_ok=True)

models = art["models"]
dose = art["dose_response"]

C_NULL = "#7f8c8d"
C_OPP = "#c0392b"
C_FLOOR = "#f39c12"

# ===== 图1: 森林图 =====
fig, ax = plt.subplots(figsize=(8, 4.5))
hyp_names = ["H1: 密度→检索位次", "H2: 密度→BM25 描述排名", "H3: 嵌套增益（ΔR²）"]
for i, m in enumerate(models):
    b = m.get("beta", 0)
    lo, hi = m.get("ci_lo"), m.get("ci_hi")
    v = m["verdict"]
    if v == "opposite":
        c = C_OPP
    elif v == "null":
        c = C_NULL
    else:
        c = "#2980b9"
    if lo is not None and hi is not None:
        ax.plot([lo, hi], [i, i], color=c, lw=2, alpha=0.7)
    ax.plot(b, i, "D", color=c, markersize=7)
    label = f"{hyp_names[i]}\n(β={b:.4f}"
    if m.get("p_holm") is not None:
        label += f", p_holm={m['p_holm']:.3f}"
    label += ")"
    ax.text(max((hi if hi is not None else b), b, 0) + 0.005, i, label, va="center", fontsize=8.5)

ax.axvline(0, color="black", lw=0.8, ls="--")
ax.set_yticks(range(len(models)))
ax.set_yticklabels(["H1", "H2", "H3"], fontsize=10)
ax.set_xlabel("回归系数（β）", fontsize=10)
ax.set_title("图1  三个预注册假设的效应量与置信区间", fontsize=12, fontweight="bold", pad=12)
ax.invert_yaxis()
fig.tight_layout()
fig.savefig(OUT / "custom_fig1_forest.png", bbox_inches="tight")
plt.close()

# ===== 图2: 剂量反应曲线（constraint_total vs fail_at_3 和 top1_ok）=====
fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
ct = [d["constraint_total"] for d in dose]
fail3 = [d["fail_at_3"] for d in dose]
top1 = [d["top1_ok"] for d in dose]

axes[0].plot(ct, fail3, "o-", color="#e74c3c", markersize=5, lw=1.5)
axes[0].set_xlabel("约束词总数（十分位均值）", fontsize=10)
axes[0].set_ylabel("Fail@3 率", fontsize=10)
axes[0].set_title("约束密度与检索失败率", fontsize=11)
for x, y in zip(ct, fail3):
    axes[0].annotate(f"{y:.3f}", (x, y), textcoords="offset points", xytext=(0, 8), fontsize=7, ha="center")

axes[1].plot(ct, top1, "s-", color="#2980b9", markersize=5, lw=1.5)
axes[1].set_xlabel("约束词总数（十分位均值）", fontsize=10)
axes[1].set_ylabel("Top-1 正确率", fontsize=10)
axes[1].set_title("约束密度与 Top-1 正确率", fontsize=11)
for x, y in zip(ct, top1):
    axes[1].annotate(f"{y:.3f}", (x, y), textcoords="offset points", xytext=(0, 8), fontsize=7, ha="center")

fig.suptitle("图2  约束密度与检索质量的剂量反应关系", fontsize=12, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(OUT / "custom_fig2_dose_response.png", bbox_inches="tight")
plt.close()

# ===== 图3: 共线性诊断（VIF 柱状图）=====
collin = art.get("collinearity", {})
if collin:
    fig, ax = plt.subplots(figsize=(7, 4))
    vifs = list(collin.values())
    labels = list(collin.keys())
    colors_v = ["#e74c3c" if v > 5 else "#f39c12" if v > 2.5 else "#2ecc71" for v in vifs]
    bars = ax.bar(range(len(labels)), vifs, color=colors_v, alpha=0.7, width=0.5)
    ax.axhline(5, color="red", lw=1, ls="--", label="VIF = 5（严重共线）")
    ax.axhline(2.5, color="orange", lw=1, ls=":", label="VIF = 2.5（中度共线）")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=9, rotation=15, ha="right")
    ax.set_ylabel("VIF", fontsize=10)
    ax.set_title("图3  自变量共线性诊断", fontsize=12, fontweight="bold", pad=12)
    for bar, v in zip(bars, vifs):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                f"{v:.2f}", ha="center", va="bottom", fontsize=9)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "custom_fig3_collinearity.png", bbox_inches="tight")
    plt.close()

# ===== 图4: 嵌套模型增益（partial R² 与阈值）=====
fig, ax = plt.subplots(figsize=(6, 4))
pr2 = art.get("partial_r2_gain", 0)
floor = 0.005  # 冻结的下限
bars = ax.barh([0], [pr2], color=C_FLOOR, alpha=0.7, height=0.4)
ax.axvline(floor, color="red", lw=1.5, ls="--", label=f"冻结下限 = {floor}")
ax.axvline(pr2, color=C_FLOOR, lw=0, label=f"实际 ΔR² = {pr2:.5f}")
ax.set_xlabel("Partial R² 增益", fontsize=10)
ax.set_yticks([0])
ax.set_yticklabels(["约束密度"], fontsize=10)
ax.set_title("图4  约束密度的嵌套模型 R² 增益 vs. 冻结下限", fontsize=12, fontweight="bold", pad=12)
ax.text(pr2 + 0.00005, 0, f"ΔR²={pr2:.5f}\n低于下限 {floor}", fontsize=9, va="center")
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig(OUT / "custom_fig4_nested_gain.png", bbox_inches="tight")
plt.close()

print("P007 定制图: 4 张已生成")
for f in sorted(OUT.glob("custom_*.png")):
    print(f"  {f.name} ({f.stat().st_size // 1024}KB)")
