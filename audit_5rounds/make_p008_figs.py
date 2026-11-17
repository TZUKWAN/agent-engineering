# -*- coding: utf-8 -*-
"""P008 定制图：基于 T106 (query reformulation fidelity) 产物数据。"""
import json, glob, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 300

fs = [f for f in glob.glob("results_raw/EXP0123_*.json") if "summary" not in f]
art = json.load(open(max(fs, key=lambda x: pathlib.Path(x).stat().st_mtime), encoding="utf-8"))
OUT = pathlib.Path("papers/P008_query_reformulation_fidelity/figures")
OUT.mkdir(parents=True, exist_ok=True)

C_SUP = "#2980b9"; C_OPP = "#c0392b"; C_NULL = "#7f8c8d"

# ===== 图1: 森林图 =====
fig, ax = plt.subplots(figsize=(8, 4.5))
for i, (hyp, block) in enumerate([("H1", art["H1"]), ("H2", art["H2"]), ("H3", art["H3"])]):
    v = block.get("verdict", "not_testable")
    b = block.get("beta")
    lo, hi = block.get("ci_lo"), block.get("ci_hi")
    if b is None:  # H3 block
        ic = block.get("ic", {})
        b = ic.get("beta"); lo = ic.get("ci_lo"); hi = ic.get("ci_hi")
    color = C_OPP if v == "opposite" else C_SUP if v == "partial" else C_NULL
    if b is not None:
        if lo is not None and hi is not None:
            ax.plot([lo, hi], [i, i], color=color, lw=2, alpha=0.7)
        ax.plot(b, i, "D", color=color, markersize=7)
    label = f"{hyp}: {v}" + (f"\n(β={b:.4f}, p_holm={art['holm'].get(hyp, 'N/A')})" if b is not None else "")
    x_pos = max(b, hi, 0) if b is not None else 0
    ax.text(x_pos + 0.005, i, label, va="center", fontsize=8.5)
ax.axvline(0, color="black", lw=0.8, ls="--")
ax.set_yticks(range(3)); ax.set_yticklabels(["H1", "H2", "H3"], fontsize=10)
ax.set_xlabel("系数（β）", fontsize=10)
ax.set_title("图1  三个预注册假设的改写保真度效应", fontsize=12, fontweight="bold", pad=12)
ax.invert_yaxis()
fig.tight_layout()
fig.savefig(OUT / "custom_fig1_forest.png", bbox_inches="tight")
plt.close()

# ===== 图2: 信息损失阶梯 =====
ladder = art["loss_ladder"]
levels = [l["level"] for l in ladder]
rets = [l["retention"] for l in ladder]
level_cn = {"entity": "实体保留", "constraint_family": "约束族保留", "predicate_argument_relation": "谓词论元保留"}
fig, ax = plt.subplots(figsize=(7, 4))
bars = ax.barh(range(len(levels)), rets, color=["#2980b9", "#e74c3c", "#f39c12"], alpha=0.7, height=0.5)
ax.set_yticks(range(len(levels)))
ax.set_yticklabels([level_cn.get(l, l) for l in levels], fontsize=10)
ax.set_xlabel("保留率", fontsize=10)
ax.set_title("图2  改写保真度：信息损失阶梯", fontsize=12, fontweight="bold", pad=12)
ax.invert_yaxis()
for bar, r in zip(bars, rets):
    ax.text(bar.get_width() + 0.005, bar.get_y() + bar.get_height() / 2,
            f"{r:.1%}", va="center", fontsize=10)
fig.tight_layout()
fig.savefig(OUT / "custom_fig2_loss_ladder.png", bbox_inches="tight")
plt.close()

# ===== 图3: 双臂对比 =====
arms = art.get("arms", [])
if arms:
    a = arms[0]
    fig, ax = plt.subplots(figsize=(6, 4))
    cats = ["实体保留率", "约束保留率", "错误工具率"]
    vals = [a["entity"], a["constraint"], a["wrong"]]
    bars = ax.bar(range(3), vals, color=["#2980b9", "#e74c3c", "#95a5a6"], alpha=0.7, width=0.5)
    ax.set_xticks(range(3)); ax.set_xticklabels(cats, fontsize=10)
    ax.set_ylabel("比率", fontsize=10)
    ax.set_title(f"图3  {a['trace_arm']} 臂的保留率与错误率（n={a['n']}）", fontsize=12, fontweight="bold", pad=12)
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.005,
                f"{v:.3f}", ha="center", va="bottom", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "custom_fig3_arms.png", bbox_inches="tight")
    plt.close()

# ===== 图4: H3 逐通道效应 =====
h3 = art.get("H3", {})
ic = h3.get("ic", {}); length = h3.get("length", {})
fig, ax = plt.subplots(figsize=(7, 4))
channels = ["指代/省略 (ic)", "指令长度"]
betas = [ic.get("beta", 0), length.get("beta", 0)]
cis_lo = [ic.get("ci_lo", 0), length.get("ci_lo", 0)]
cis_hi = [ic.get("ci_hi", 0), length.get("ci_hi", 0)]
colors_h = [C_NULL if lo <= 0 <= hi else C_OPP for lo, hi in zip(cis_lo, cis_hi)]
for i, (b, lo, hi, c) in enumerate(zip(betas, cis_lo, cis_hi, colors_h)):
    ax.plot([lo, hi], [i, i], color=c, lw=2, alpha=0.7)
    ax.plot(b, i, "D", color=c, markersize=7)
ax.axvline(0, color="black", lw=0.8, ls="--")
ax.set_yticks(range(2)); ax.set_yticklabels(channels, fontsize=10)
ax.set_xlabel("β 指数 vs 完成率", fontsize=10)
ax.set_title("图4  H3：指代/省略 vs 指令长度对完成的效应", fontsize=12, fontweight="bold", pad=12)
fig.tight_layout()
fig.savefig(OUT / "custom_fig4_h3_channels.png", bbox_inches="tight")
plt.close()

print("P008 定制图: 4 张已生成")
for f in sorted(OUT.glob("custom_*.png")):
    print(f"  {f.name} ({f.stat().st_size // 1024}KB)")
