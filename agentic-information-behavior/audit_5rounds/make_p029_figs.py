# -*- coding: utf-8 -*-
"""P029 定制图：基于 T133 (失败后的话语修复, EXP-0167, wave-5) 产物数据。

本文的个性：失败触发诊断语言（H1 supported），重试语言兑现为再次调用（H2 supported），
而"放弃"语言反而伴随继续（H3 opposite, -0.52）——口头放弃是修辞不是决定。
描述层还有一个悖论：放弃与重试词表在非失败 turn 上触发更多。
"""
import json, glob, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 300

fs = sorted(glob.glob("results_raw/EXP0167_wave5_design_*.json"))
art = json.load(open(fs[-1], encoding="utf-8"))
OUT = pathlib.Path("papers/P029_discourse_repair_after_failure/figures")
OUT.mkdir(parents=True, exist_ok=True)

C_SUP = "#27ae60"
C_OPP = "#c0392b"
C_ACC = "#2980b9"
C_NULL = "#95a5a6"

models = {m["hypothesis"]: m for m in art["models"]}
h1, h2, h3 = models["H1"], models["H2"], models["H3"]
rep = art["descriptive_rates"]["repair_share_by_failure_state"]

# ===== 图1 三假设判定森林 =====
fig, ax = plt.subplots(figsize=(10, 4.8))
rows = [
    ("H1 失败 → 诊断语言", h1["beta"], h1["ci_lo"], h1["ci_hi"], C_SUP,
     f"判定 supported\nβ={h1['beta']:+.4f}，p_holm<0.001\n（失败后更常说出问题所在）"),
    ("H2 重试语言 → 再次调用", h2["beta"], h2["ci_lo"], h2["ci_hi"], C_SUP,
     f"判定 supported\nβ={h2['beta']:+.4f}，p_holm<0.001\n（失败后，说重试就真的重试）"),
    ("H3 放弃语言 → 终止", h3["beta"], h3["ci_lo"], h3["ci_hi"], C_OPP,
     f"判定 opposite\nβ={h3['beta']:+.4f}，p_holm<0.001\n（预测正，实测负：说放弃不终止）"),
]
for i, (lab, b, lo, hi, c, note) in enumerate(rows):
    ax.plot([lo, hi], [i, i], color=c, lw=3, alpha=0.85)
    ax.plot(b, i, "D", color=c, ms=9)
    ax.text(hi + 0.035, i, note, va="center", fontsize=8.8)
ax.axvline(0, color="black", lw=0.9, ls="--")
ax.set_yticks([0, 1, 2]); ax.set_yticklabels(["H1", "H2", "H3"], fontsize=11)
ax.set_xlim(-0.95, 1.45)
ax.set_xlabel("系数（logit 标度，traj 聚类稳健）", fontsize=10)
ax.set_title("图1  三个预注册假设：诊断与重试按剧本走，放弃语言反着走",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="x", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig1_verdicts.png", bbox_inches="tight")
plt.close()

# ===== 图2 修复家族触发率 by 失败状态 =====
fig, ax = plt.subplots(figsize=(10, 5.0))
fams = ["repair_reissue", "repair_diagnose", "repair_abandon"]
fam_cn = ["重试语言", "诊断语言", "放弃语言"]
no_f = [rep["0"][f] * 100 for f in fams]
wi_f = [rep["1"][f] * 100 for f in fams]
x = np.arange(3)
w = 0.32
ax.bar(x - w / 2, no_f, width=w, color="#aab7b8", alpha=0.9, label="无失败标记 turn（n=65,270）")
ax.bar(x + w / 2, wi_f, width=w, color=C_OPP, alpha=0.9, label="失败标记后 turn（n=81,978）")
for xi, v in zip(x - w / 2, no_f):
    ax.text(xi, v + 1.2, f"{v:.1f}%", ha="center", fontsize=9)
for xi, v in zip(x + w / 2, wi_f):
    ax.text(xi, v + 1.2, f"{v:.1f}%", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(fam_cn, fontsize=11)
ax.set_ylabel("词表触发率（%）", fontsize=10)
ax.set_ylim(0, 85)
ax.legend(fontsize=9.5)
ax.set_title("图2  修复词表的触发率剖面：诊断语言随失败上升（1.76%→2.17%），\n"
             "而放弃语言反而随失败下降（5.57%→2.37%）——口头放弃不在失败点上",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="y", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig2_family_rates.png", bbox_inches="tight")
plt.close()

# ===== 图3 H2/H3 双面板：语言兑现 vs 语言反兑 =====
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.5, 4.6))
# H2
a1.barh([0], [h2["beta"]], height=0.4, color=C_SUP, alpha=0.85)
a1.errorbar(h2["beta"], 0, xerr=[[h2["beta"] - h2["ci_lo"]], [h2["ci_hi"] - h2["beta"]]],
            color="#145a32", capsize=6, lw=1.5, fmt="none")
a1.axvline(0, color="black", lw=0.9, ls="--")
a1.text(h2["ci_hi"] + 0.03, 0, f"β = {h2['beta']:+.4f}\n比值比约 e^0.81 ≈ 2.25",
        va="center", fontsize=9.5, color="#145a32")
a1.set_yticks([])
a1.set_xlabel("重试语言对再次调用的系数", fontsize=10)
a1.set_xlim(0, 1.35)
a1.set_title("(a) H2 supported：说重试 → 概率翻倍地\n再发起一次调用（n=81,978）", fontsize=10.5)
a1.grid(alpha=0.25, axis="x", ls="--")
# H3
a2.barh([0], [h3["beta"]], height=0.4, color=C_OPP, alpha=0.85)
a2.errorbar(h3["beta"], 0, xerr=[[h3["beta"] - h3["ci_lo"]], [h3["ci_hi"] - h3["beta"]]],
            color="#641e16", capsize=6, lw=1.5, fmt="none")
a2.axvline(0, color="black", lw=0.9, ls="--")
a2.text(h3["ci_lo"] - 0.04, 0, f"β = {h3['beta']:+.4f}\n（预测正，实测负）\n比值比约 e^0.52 ≈ 0.60",
        va="center", ha="right", fontsize=9.5, color=C_OPP)
a2.set_yticks([])
a2.set_xlabel("放弃语言对在该 turn 终止的系数", fontsize=10)
a2.set_xlim(-1.05, 0.35)
a2.set_title("(b) H3 opposite：说放弃 → 终止几率\n反而降至六成——修辞性放弃", fontsize=10.5)
a2.grid(alpha=0.25, axis="x", ls="--")
fig.suptitle("图4  修复语言的兑现不对称：重试语言兑现为行动，放弃语言兑现为继续",
             fontsize=12, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(OUT / "custom_fig3_h2_h3_panel.png", bbox_inches="tight")
plt.close()

# ===== 图4 类目分层：诊断语言的领域性 =====
fig, ax = plt.subplots(figsize=(9.8, 5.0))
strata = [x for x in art["strata"] if x.get("stratification") == "category" and x.get("beta") is not None]
for i, s in enumerate(strata):
    sig = s.get("p") is not None and s["p"] < 0.05
    c = C_ACC if sig and s.get("beta") > 0 else C_NULL
    ax.plot([s.get("ci_lo"), s.get("ci_hi")], [i, i], color=c, lw=3, alpha=0.85)
    ax.plot(s.get("beta"), i, "D", color=c, ms=9)
    star = " *" if sig else ""
    ax.text(s.get("ci_hi") + 0.04, i, f"β={s['beta']:+.4f}{star}  (n={s['rows']:,})", va="center", fontsize=8.5)
ax.axvline(0, color="black", lw=0.9, ls="--")
ax.set_yticks(range(len(strata)))
ax.set_yticklabels([s["stratum"].replace("_", " ").title() for s in strata], fontsize=9.5)
ax.set_xlabel("失败 → 诊断语言的系数（类目分层，描述性）", fontsize=10)
ax.set_xlim(-1.1, 2.1)
ax.set_title("图5  诊断语言效应的类目剖面：Agent Tools / File Operations / Multi-Tool 显著，\n"
             "Browser Automation 等类目近零——诊断是领域性实践（* p<0.05）",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="x", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig4_category_strata.png", bbox_inches="tight")
plt.close()

print("P029 figures done:", [p.name for p in sorted(OUT.glob("custom_*.png"))])
