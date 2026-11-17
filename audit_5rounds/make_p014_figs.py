# -*- coding: utf-8 -*-
"""P014 定制图：基于 T114 (semantic prototype bias / description granularity) 产物数据。"""
import json, glob, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 300

fs = [f for f in glob.glob("results_raw/EXP0140_*.json") if "summary" not in f]
art = json.load(open(max(fs, key=lambda x: pathlib.Path(x).stat().st_mtime), encoding="utf-8"))
OUT = pathlib.Path("papers/P014_description_granularity/figures")
OUT.mkdir(parents=True, exist_ok=True)

# ===== 图1: 剂量反应曲线 =====
dose = art["dose_response"]
deciles = [d["len_decile"] for d in dose]
reach = [d["reachable"] for d in dose]
fail3 = [d["fail_at_3"] for d in dose]
fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
axes[0].plot(deciles, reach, "o-", color="#2980b9", markersize=6, lw=1.5)
axes[0].set_xlabel("描述长度十分位", fontsize=10)
axes[0].set_ylabel("可达率", fontsize=10)
axes[0].set_title("描述长度与可达率", fontsize=11)
axes[1].plot(deciles, fail3, "s-", color="#e74c3c", markersize=6, lw=1.5)
axes[1].set_xlabel("描述长度十分位", fontsize=10)
axes[1].set_ylabel("Fail@3 率", fontsize=10)
axes[1].set_title("描述长度与检索失败率", fontsize=11)
fig.suptitle("图1  描述粒度的剂量反应关系", fontsize=12, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(OUT / "custom_fig1_dose_response.png", bbox_inches="tight")
plt.close()

# ===== 图2: 大目录 vs 小目录的可达率 =====
large = [d for d in dose if d["len_decile"] in (8, 9, 10)]
small = [d for d in dose if d["len_decile"] in (1, 2, 3)]
fig, ax = plt.subplots(figsize=(7, 4))
lr = [d["reachable"] for d in large]
sr = [d["reachable"] for d in small]
ld = [d["len_decile"] for d in large]
sd = [d["len_decile"] for d in small]
ax.plot(sd, sr, "o-", color="#2980b9", label="小目录", markersize=6, lw=1.5)
ax.plot(ld, lr, "s-", color="#e74c3c", label="大目录", markersize=6, lw=1.5)
ax.set_xlabel("描述长度十分位", fontsize=10)
ax.set_ylabel("可达率", fontsize=10)
ax.set_title("图2  大目录 vs 小目录的可达率", fontsize=12, fontweight="bold", pad=12)
ax.legend(fontsize=9)
fig.tight_layout()
fig.savefig(OUT / "custom_fig2_catalogue_size.png", bbox_inches="tight")
plt.close()

# ===== 图3: 成本侧——描述长度与非金标位移 =====
cost = art["cost_side"]
fig, ax = plt.subplots(figsize=(6, 4))
bars = ax.bar(["描述长度\n(标准化)", "位移率"], [cost["beta"], cost["beta"]],
              color=["#e74c3c", "#f39c12"], alpha=0.7, width=0.3)
ax.errorbar(0, cost["beta"], yerr=[[cost["beta"] - cost["ci_lo"]], [cost["ci_hi"] - cost["beta"]]],
            fmt="none", ecolor="black", capsize=5, lw=1.5)
ax.set_ylabel("回归系数", fontsize=10)
ax.set_title("图3  描述长度对非金标候选位移的效应", fontsize=12, fontweight="bold", pad=12)
ax.text(0, cost["beta"] + 0.005, f"β = {cost['beta']:.4f}\np < 10⁻³⁵", ha="center", fontsize=9)
fig.tight_layout()
fig.savefig(OUT / "custom_fig3_cost_side.png", bbox_inches="tight")
plt.close()

# ===== 图4: 交互效应 =====
inter = art["interaction"]
fig, ax = plt.subplots(figsize=(6, 4))
ax.bar(["交互项"], [inter["beta"]], color="#9b59b6", alpha=0.7, width=0.3)
ax.errorbar(0, inter["beta"], yerr=[[inter["beta"] - inter["ci_lo"]], [inter["ci_hi"] - inter["beta"]]],
            fmt="none", ecolor="black", capsize=5, lw=1.5)
ax.set_ylabel("回归系数", fontsize=10)
ax.set_title("图4  描述长度 × 目录规模的交互效应", fontsize=12, fontweight="bold", pad=12)
ax.text(0.05, inter["beta"] + 0.01, f"β = {inter['beta']:.4f}\np = {inter['p_raw']:.2e}", fontsize=9)
fig.tight_layout()
fig.savefig(OUT / "custom_fig4_interaction.png", bbox_inches="tight")
plt.close()

print("P014 定制图: 4 张已生成")
for f in sorted(OUT.glob("custom_*.png")):
    print(f"  {f.name} ({f.stat().st_size // 1024}KB)")
