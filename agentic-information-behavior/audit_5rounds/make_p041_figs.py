# -*- coding: utf-8 -*-
"""P041 figures: T164 namespace and candidate overload (EXP-0185, wave-7)."""
import json, glob, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 300

fs = sorted(glob.glob("results_raw/EXP0185_wave7_design_*.json"))
art = json.load(open(fs[-1], encoding="utf-8"))
OUT = pathlib.Path("papers/P041_tool_namespace_and_candidate_overload/figures")
OUT.mkdir(parents=True, exist_ok=True)

C_SUP = "#27ae60"; C_OPP = "#c0392b"; C_ACC = "#2980b9"; C_NULL = "#95a5a6"
models = {m["hypothesis"]: m for m in art["models"]}
h1, h2, h3 = models["H1"], models["H2"], models["H3"]
dr = art["descriptive_rates"]
fq = dr["fail_at_1_by_candidate_quartile"]
fg = dr["fail_at_1_by_grouping_arm"]

# fig1: verdicts forest
fig, ax = plt.subplots(figsize=(10, 4.6))
rows = [
    ("H1 namespace share", h1["beta"], h1["ci_lo"], h1["ci_hi"], C_SUP,
     f"supported\nβ={h1['beta']:+.4f}\np_holm<0.001"),
    ("H2 Q4 vs Q1 cand count", h2["beta"], h2["ci_lo"], h2["ci_hi"], C_SUP,
     f"supported\nβ={h2['beta']:+.4f}\np_holm<0.001"),
    ("H3 namespace w/ servers", h3["beta"], h3["ci_lo"], h3["ci_hi"], C_OPP,
     f"not_specific\nβ={h3['beta']:+.4f}\np_holm<0.001"),
]
for i, (lab, b, lo, hi, c, note) in enumerate(rows):
    ax.plot([lo, hi], [i, i], color=c, lw=3, alpha=0.85)
    ax.plot(b, i, "D", color=c, ms=9)
    ax.text(hi + 0.02, i, note, va="center", fontsize=8.5)
ax.axvline(0, color="black", lw=0.9, ls="--")
ax.set_yticks([0, 1, 2]); ax.set_yticklabels(["H1", "H2", "H3"], fontsize=11)
ax.set_xlim(-0.35, 1.45)
ax.set_xlabel("logit coefficient", fontsize=10)
ax.set_title("图1  三个假设的判定", fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="x", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig1_verdicts.png", bbox_inches="tight"); plt.close()

# fig2: fail@1 by grouping arm + candidate quartile
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.5, 4.5))
arms = list(fg.keys()); arm_labs = ["all_namespaced", "mixed", "ungrouped"]
arm_v = [fg[a]["rate"] * 100 for a in arm_labs]
a1.bar(range(3), arm_v, color=[C_SUP, C_ACC, C_OPP], alpha=0.88, width=0.5)
for i, v in enumerate(arm_v):
    a1.text(i, v + 0.4, f"{v:.1f}%", ha="center", fontsize=10)
a1.set_xticks(range(3))
a1.set_xticklabels(["全命名空间", "混合", "全无命名空间"], fontsize=10)
a1.set_ylabel("fail@1（%）", fontsize=10); a1.set_ylim(0, 25)
a1.set_title("(a) 按分组状态", fontsize=10.5); a1.grid(alpha=0.25, axis="y", ls="--")
qs = list(fq.keys()); qv = [fq[q]["rate"] * 100 for q in qs]
a2.bar(range(4), qv, color=C_ACC, alpha=0.88, width=0.5)
for i, v in enumerate(qv):
    a2.text(i, v + 0.5, f"{v:.1f}%", ha="center", fontsize=10)
a2.set_xticks(range(4))
a2.set_xticklabels(["Q1 最小", "Q2", "Q3", "Q4 最大"], fontsize=10)
a2.set_ylabel("fail@1（%）", fontsize=10); a2.set_ylim(0, 36)
a2.set_title("(b) 按候选规模四分位", fontsize=10.5)
a2.grid(alpha=0.25, axis="y", ls="--")
fig.suptitle("图2  fail@1 的两个描述性切面", fontsize=12, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(OUT / "custom_fig2_descriptives.png", bbox_inches="tight"); plt.close()

# fig3: namespace coefficient by candidate quartile
fig, ax = plt.subplots(figsize=(9.2, 4.8))
stra = [s for s in art["strata"] if s.get("stratification") == "cand_quartile" and s.get("beta") is not None]
qlab = {"q1_smallest": "Q1 最小", "q2": "Q2", "q3": "Q3", "q4_largest": "Q4 最大"}
for i, s in enumerate(stra):
    nm = qlab.get(s["stratum"], s["stratum"])
    sig = s.get("p") is not None and s["p"] < 0.05
    c = C_SUP if sig and s["beta"] < 0 else C_NULL
    ax.plot([s["ci_lo"], s["ci_hi"]], [i, i], color=c, lw=3, alpha=0.85)
    ax.plot(s["beta"], i, "D", color=c, ms=10)
    star = " *" if sig else ""
    ax.text(s["ci_hi"] + 0.02, i, f"β={s['beta']:+.4f}{star}", va="center", fontsize=9.5)
ax.axvline(0, color="black", lw=0.9, ls="--")
ax.set_yticks(range(len(stra)))
ax.set_yticklabels([qlab.get(s["stratum"], s["stratum"]) for s in stra], fontsize=10.5)
ax.set_xlabel("命名空间份额对 fail@1 的系数", fontsize=10)
ax.set_xlim(-1.05, 0.15)
ax.set_title("图3  命名空间效应的候选规模分层\n（负值 = 命名空间减少缺席；* p<0.05）",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="x", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig3_quartile_layers.png", bbox_inches="tight"); plt.close()

# fig4: H3 competing model
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.5, 4.5))
ns_model = h3.get("namespace_in_the_competing_model", h3)
conc = h3.get("concentration_term", {})
if conc:
    a1.barh([0, 1], [ns_model.get("beta", 0), conc["beta"]],
            height=0.4, color=[C_SUP, C_ACC], alpha=0.85)
    for i, (m, lab) in enumerate([(ns_model, "命名空间份额"), (conc, "服务器集中度")]):
        a1.text(abs(m["beta"]) + 0.01, i, f"β={m['beta']:+.4f}", va="center", fontsize=9.5)
    a1.set_yticks([0, 1]); a1.set_yticklabels(["命名空间", "集中度"], fontsize=10)
    a1.set_xlabel("系数", fontsize=10)
    a1.set_title("(a) 竞争模型：两变量并存时的系数", fontsize=10.5)
    a1.axvline(0, color="black", lw=0.9, ls="--")
    a1.grid(alpha=0.25, axis="x", ls="--")
else:
    a1.text(0.5, 0.5, "竞争模型数据不可用", ha="center", fontsize=12)
    a1.set_title("(a) 竞争模型", fontsize=10.5)

a2 = fig.add_subplot(1, 2, 2)
a2.bar([0], [h3["beta"]], width=0.4, color=C_OPP, alpha=0.85)
a2.errorbar(0, h3["beta"], yerr=[[h3["beta"] - h3["ci_lo"]], [h3["ci_hi"] - h3["beta"]]],
            color="#641e16", capsize=6, lw=1.5, fmt="none")
a2.axhline(0, color="black", lw=0.9, ls="--")
a2.text(0.03, h3["beta"] + 0.01,
        f"H3 判 not_specific\nβ = {h3['beta']:+.4f}\nCI [{h3['ci_lo']:.4f}, {h3['ci_hi']:.4f}]\n"
        f"（命名空间份额在控制服务器数后仍分离）",
        va="center", fontsize=9.3, color="#641e16")
a2.set_xticks([]); a2.set_xlim(-0.05, 0.35)
a2.set_ylabel("logit 系数", fontsize=10)
a2.set_ylim(-0.32, 0.05)
a2.set_title("(b) 特异性存疑：命名空间仍有独立效应", fontsize=10.5)
a2.grid(alpha=0.25, axis="y", ls="--")
fig.suptitle("图4  H3 的竞争模型：命名空间与服务器集中度的分离", fontsize=12, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(OUT / "custom_fig4_h3_competing.png", bbox_inches="tight"); plt.close()

print("P041 figures done:", [p.name for p in sorted(OUT.glob("custom_*.png"))])
