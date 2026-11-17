# -*- coding: utf-8 -*-
"""P012 定制图：基于 T115 (entity action constraint fit) 产物数据。"""
import json, glob, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 300

fs = [f for f in glob.glob("results_raw/EXP0137_*.json") if "summary" not in f]
art = json.load(open(max(fs, key=lambda x: pathlib.Path(x).stat().st_mtime), encoding="utf-8"))
OUT = pathlib.Path("papers/P012_entity_action_constraint_fit/figures")
OUT.mkdir(parents=True, exist_ok=True)

# ===== 图1: AUROC 阶梯 =====
ladder = art["auroc_ladder"]
names = [m["model"] for m in ladder]
aurocs = [m["auroc"] for m in ladder]
fig, ax = plt.subplots(figsize=(9, 4.5))
colors_l = ["#95a5a6", "#3498db", "#2ecc71", "#e74c3c", "#9b59b6"]
bars = ax.barh(range(len(names)), aurocs, color=colors_l, alpha=0.7, height=0.5)
ax.set_yticks(range(len(names)))
ax.set_yticklabels(names, fontsize=9)
ax.set_xlabel("AUROC", fontsize=10)
ax.set_title("图1  五个嵌套模型的 AUROC 阶梯", fontsize=12, fontweight="bold", pad=12)
ax.invert_yaxis()
for bar, a in zip(bars, aurocs):
    ax.text(bar.get_width() + 0.0005, bar.get_y() + bar.get_height()/2, f"{a:.4f}", va="center", fontsize=9)
fig.tight_layout()
fig.savefig(OUT / "custom_fig1_auroc_ladder.png", bbox_inches="tight")
plt.close()

# ===== 图2: 三个假设的系数森林图 =====
fig, ax = plt.subplots(figsize=(8, 4.5))
models = art["models"]
hyp_names = ["H1: 实体一致", "H2: 动作一致", "H3: 约束一致"]
for i, m in enumerate(models):
    b = m["beta"]; se = m["se"]
    lo, hi = b - 1.96 * se, b + 1.96 * se
    c = "#2980b9" if m["beta_sign_matches_hypothesis_sentence"] else "#e74c3c"
    ax.plot([lo, hi], [i, i], color=c, lw=2, alpha=0.7)
    ax.plot(b, i, "D", color=c, markersize=7)
    ax.text(hi + 0.02, i, f"β={b:.4f}, p_holm<0.001", va="center", fontsize=8)
ax.axvline(0, color="black", lw=0.8, ls="--")
ax.set_yticks(range(3)); ax.set_yticklabels(hyp_names, fontsize=9)
ax.set_xlabel("回归系数（β）", fontsize=10)
ax.set_title("图2  三个语义一致度假设的系数与置信区间", fontsize=12, fontweight="bold", pad=12)
ax.invert_yaxis()
fig.tight_layout()
fig.savefig(OUT / "custom_fig2_forest.png", bbox_inches="tight")
plt.close()

# ===== 图3: AUROC 增益瀑布图 =====
gains = art["gains"]
fig, ax = plt.subplots(figsize=(8, 4.5))
gain_labels = list(gains.keys())
gain_vals = [gains[k]["delta"] for k in gain_labels]
gain_cis = [gains[k]["ci"] for k in gain_labels]
gain_labels_cn = ["H1 实体\nΔAUROC", "H2 动作\nΔAUROC", "H3 约束\nΔAUROC"]
colors_g = ["#3498db", "#2ecc71", "#e74c3c"]
bars = ax.bar(range(3), gain_vals, color=colors_g, alpha=0.7, width=0.4)
ax.errorbar(range(3), gain_vals,
            yerr=[[g - c[0] for g, c in zip(gain_vals, gain_cis)],
                  [c[1] - g for g, c in zip(gain_vals, gain_cis)]],
            fmt="none", ecolor="black", capsize=5, lw=1.2)
ax.set_xticks(range(3)); ax.set_xticklabels(gain_labels_cn, fontsize=9)
ax.set_ylabel("Δ AUROC", fontsize=10)
ax.set_title("图3  三个语义一致度成分的增量预测力", fontsize=12, fontweight="bold", pad=12)
for bar, v in zip(bars, gain_vals):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.0003,
            f"{v:.4f}", ha="center", va="bottom", fontsize=9)
fig.tight_layout()
fig.savefig(OUT / "custom_fig3_gains.png", bbox_inches="tight")
plt.close()

# ===== 图4: VIF 共线性诊断 =====
vif = art["vif"]
fig, ax = plt.subplots(figsize=(6, 4))
vif_labels = list(vif.keys())
vif_vals = list(vif.values())
bars = ax.bar(vif_labels, vif_vals, color=["#2ecc71" if v < 2.5 else "#f39c12" for v in vif_vals], alpha=0.7, width=0.4)
ax.axhline(5, color="red", lw=1, ls="--", label="VIF = 5（严重共线）")
ax.axhline(2.5, color="orange", lw=1, ls=":", label="VIF = 2.5（中度）")
ax.set_ylabel("VIF", fontsize=10)
ax.set_title("图4  自变量共线性诊断", fontsize=12, fontweight="bold", pad=12)
for bar, v in zip(bars, vif_vals):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
            f"{v:.3f}", ha="center", va="bottom", fontsize=9)
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig(OUT / "custom_fig4_vif.png", bbox_inches="tight")
plt.close()

print("P012 定制图: 4 张已生成")
for f in sorted(OUT.glob("custom_*.png")):
    print(f"  {f.name} ({f.stat().st_size // 1024}KB)")
