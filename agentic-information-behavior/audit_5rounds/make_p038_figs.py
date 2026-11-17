# -*- coding: utf-8 -*-
"""P038 定制图：基于 T174 (重复搜索与反刍, EXP-0179, wave-6) 产物数据。

本文的个性：双面结果——精确重复的命令新知率暴跌 34 倍（H1 supported,
β=-1.344, LR χ²=17,319 系列最大），但含重复的 rollout 更常提交
（H2 opposite +0.756）——重复是复核动作不是反刍；悬崖后不单调（H3）。
"""
import json, glob, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 300

fs = sorted(glob.glob("results_raw/EXP0179_wave6_design_*.json"))
art = json.load(open(fs[-1], encoding="utf-8"))
OUT = pathlib.Path("papers/P038_repetition_and_rumination/figures")
OUT.mkdir(parents=True, exist_ok=True)

C_SUP = "#27ae60"
C_OPP = "#c0392b"
C_ACC = "#2980b9"
C_NULL = "#95a5a6"

models = {m["hypothesis"]: m for m in art["models"]}
h1, h2, h3 = models["H1"], models["H2"], models["H3"]
nrc = art["descriptive_rates"]["newness_by_repeat_count"]
mrc = art["descriptive_rates"]["most_repeated_commands"]

# ===== 图1 三假设判定森林 =====
fig, ax = plt.subplots(figsize=(10, 4.8))
rows = [
    ("H1 重复 → 新信息", h1["beta"], h1["ci_lo"], h1["ci_hi"], C_SUP,
     f"判定 supported\nβ={h1['beta']:+.4f}，p_holm<0.001\n（LR χ2=17,319：系列最大单变量效应）"),
    ("H2 含重复 → 提交", h2["beta"], h2["ci_lo"], h2["ci_hi"], C_OPP,
     f"判定 opposite\nβ={h2['beta']:+.4f}，p_holm<0.001\n（预测负，实测正：重复伴随提交）"),
]
for i, (lab, b, lo, hi, c, note) in enumerate(rows):
    ax.plot([lo, hi], [i, i], color=c, lw=3, alpha=0.85)
    ax.plot(b, i, "D", color=c, ms=9)
    ax.text(hi + 0.06, i, note, va="center", fontsize=8.8)
ax.axvline(0, color="black", lw=0.9, ls="--")
ax.set_yticks([0, 1]); ax.set_yticklabels(["H1", "H2"], fontsize=11)
ax.set_xlim(-1.6, 1.4)
ax.set_xlabel("系数（H1：标准化新信息；H2：提交 logit）", fontsize=10)
ax.set_title("图1  两个主假设：重复零新知（supported）与重复伴随提交（opposite）并存",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="x", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig1_verdicts.png", bbox_inches="tight")
plt.close()

# ===== 图2 新信息率悬崖 =====
fig, ax = plt.subplots(figsize=(9.4, 5.0))
reps = sorted(nrc.keys(), key=int)
means = [nrc[k]["mean_newness"] for k in reps]
ns = [nrc[k]["rows"] for k in reps]
labels = ["首次运行", "第 1 次重复", "第 2 次重复", "第 3 次重复", "第 4 次重复"]
bars = ax.bar(range(len(reps)), means, color=[C_ACC, C_OPP, C_OPP, C_OPP, C_OPP],
              alpha=0.88, width=0.55)
for i, (m, n) in enumerate(zip(means, ns)):
    ax.text(i, m + 0.012, f"{m:.3f}\n(n={n:,})", ha="center", fontsize=9.5)
ax.annotate("", xy=(1, 0.10), xytext=(0, 0.52),
            arrowprops=dict(arrowstyle="->", color="black", lw=1.6))
ax.text(0.5, 0.36, "悬崖：-97%\n（0.583 → 0.017）", ha="center", fontsize=10.5,
        fontweight="bold")
ax.set_xticks(range(len(reps))); ax.set_xticklabels(labels, fontsize=10)
ax.set_ylabel("平均新信息率", fontsize=10)
ax.set_ylim(0, 0.68)
ax.set_title("图2  新信息率的悬崖：重复命令几乎零回报，\n且悬崖之后不再继续下滑（H3 判 not_monotone）",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="y", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig2_cliff.png", bbox_inches="tight")
plt.close()

# ===== 图3 H2 opposite：重复伴随提交 =====
fig, ax = plt.subplots(figsize=(9.2, 4.8))
ax.barh([0], [h2["beta"]], height=0.42, color=C_SUP, alpha=0.85)
ax.errorbar(h2["beta"], 0, xerr=[[h2["beta"] - h2["ci_lo"]], [h2["ci_hi"] - h2["beta"]]],
            color="#145a32", capsize=6, lw=1.6, fmt="none")
ax.axvline(0, color="black", lw=0.9, ls="--")
ax.text(h2["ci_hi"] + 0.05, 0,
        f"含精确重复 → 提交终止的系数（步数已入模）\n"
        f"β = {h2['beta']:+.4f}，比值比约 e^0.76 ≈ 2.13\n"
        f"95% CI [{h2['ci_lo']:.4f}, {h2['ci_hi']:.4f}]，p_holm < 0.001\n"
        f"（含重复轨迹 4,503 条 / 全部 {h2['n']:,} 条）",
        va="center", fontsize=9.5, color="#145a32")
ax.set_yticks([])
ax.set_xlabel("has_exact_repeat 对 submitted 的系数（logit）", fontsize=10)
ax.set_xlim(0, 1.7)
ax.set_title("图3  H2 判 opposite：含重复的 rollout 更常以提交终止——\n重复是成功轨迹里的复核动作，不是反刍",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="x", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig3_h2_opposite.png", bbox_inches="tight")
plt.close()

# ===== 图4 极端重复命令的跨轨迹共性 =====
fig, ax = plt.subplots(figsize=(9.6, 4.8))
cmds = sorted(mrc.keys(), key=lambda k: -mrc[k])
counts = [mrc[k] for k in cmds]
ax.bar(range(len(counts)), counts, color=C_ACC, alpha=0.85, width=0.55)
for i, c in enumerate(counts):
    ax.text(i, c + 90, f"{c:,}", ha="center", fontsize=9.5)
ax.set_xticks(range(len(counts)))
ax.set_xticklabels([k[:8] + "…" for k in cmds], fontsize=8.5, rotation=30, ha="right")
ax.set_ylabel("同一命令串的全数据出现次数", fontsize=10)
ax.set_ylim(0, 7200)
ax.set_title("图4  重复次数最高的 8 条命令串（跨 rollout 计数）：\n"
             "最高 6,291 次——通用命令（如目录列举）的跨轨迹共性，\n与轨迹内的反刍是两种现象",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="y", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig4_common_commands.png", bbox_inches="tight")
plt.close()

print("P038 figures done:", [p.name for p in sorted(OUT.glob("custom_*.png"))])
