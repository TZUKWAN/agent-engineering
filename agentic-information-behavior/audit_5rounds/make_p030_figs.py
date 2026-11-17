# -*- coding: utf-8 -*-
"""P030 定制图：基于 T134 (因果连接词与证据, EXP-0168, wave-5) 产物数据。

本文的个性：因果连接词 turn 与观察重叠更高（H1 partial, +0.096 SD），
推理族与解释族无可靠差（H2 null——推理族仅 0.34% turn 稀缺），
功能词对照零关联（H3 描述性）；效应集中在短 turn（q1 +0.160 → q3 -0.024）。
"""
import json, glob, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 300

fs = sorted(glob.glob("results_raw/EXP0168_wave5_design_*.json"))
art = json.load(open(fs[-1], encoding="utf-8"))
OUT = pathlib.Path("papers/P030_causal_connectives_and_evidence/figures")
OUT.mkdir(parents=True, exist_ok=True)

C_SUP = "#27ae60"
C_PART = "#e67e22"
C_NULL = "#95a5a6"
C_ACC = "#2980b9"

models = {m["hypothesis"]: m for m in art["models"]}
h1, h2, h3 = models["H1"], models["H2"], models["H3"]
desc = art["descriptive_rates"]["mean_overlap_by_connective_use"]

# ===== 图1 三假设判定森林 =====
fig, ax = plt.subplots(figsize=(10, 4.8))
rows = [
    ("H1 因果连接词 → 重叠", h1["beta"], h1["ci_lo"], h1["ci_hi"], C_PART,
     f"判定 partial\nβ={h1['beta']:+.4f}，p_holm<0.001\n（显著为正，低于中等带 0.15）"),
    ("H2 推理族 - 解释族", h2["beta"], h2["ci_lo"], h2["ci_hi"], C_NULL,
     f"判定 null\nβ={h2['beta']:+.4f}，p_holm={h2['p_holm']:.3f}\n（点估计方向符合预期，幅度近零）"),
    ("H3 功能词对照", h3["beta"], h3["ci_lo"], h3["ci_hi"], C_ACC,
     f"判定 measured_descriptively\nβ={h3['beta']:+.4f}\n（对照近零：特异性方向成立）"),
]
for i, (lab, b, lo, hi, c, note) in enumerate(rows):
    ax.plot([lo, hi], [i, i], color=c, lw=3, alpha=0.85)
    ax.plot(b, i, "D", color=c, ms=9)
    ax.text(hi + 0.004, i, note, va="center", fontsize=8.6)
ax.axvline(0, color="black", lw=0.9, ls="--")
ax.set_yticks([0, 1, 2]); ax.set_yticklabels(["H1", "H2", "H3"], fontsize=11)
ax.set_xlim(-0.02, 0.20)
ax.set_xlabel("标准化词汇重叠的系数（聚类稳健）", fontsize=10)
ax.set_title("图1  三个预注册假设：连接词确实伴随证据取材，但特异性分层各有保留",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="x", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig1_verdicts.png", bbox_inches="tight")
plt.close()

# ===== 图2 描述性对比 + H1 =====
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.5, 4.5))
a1.bar([0, 1], [desc["0"]["mean"] * 100, desc["1"]["mean"] * 100],
       color=["#aab7b8", C_PART], alpha=0.88, width=0.45)
for x, k in [(0, "0"), (1, "1")]:
    a1.text(x, desc[k]["mean"] * 100 + 0.35, f"{desc[k]['mean']*100:.2f}%\n(n={desc[k]['n']:,})",
            ha="center", fontsize=9.5)
a1.set_xticks([0, 1]); a1.set_xticklabels(["无因果连接词", "有因果连接词"], fontsize=10)
a1.set_ylabel("与已返回观察的词汇重叠率（%）", fontsize=10)
a1.set_ylim(0, 24)
a1.set_title("(a) 原始对比：连接词 turn 取材更多\n（14.70% → 19.79%）", fontsize=10.5)
a1.grid(alpha=0.25, axis="y", ls="--")

a2.barh([0], [h1["beta"]], height=0.4, color=C_PART, alpha=0.85)
a2.errorbar(h1["beta"], 0, xerr=[[h1["beta"] - h1["ci_lo"]], [h1["ci_hi"] - h1["beta"]]],
            color="#7e5109", capsize=6, lw=1.5, fmt="none")
a2.axvline(0.15, color="black", lw=1.1, ls="--")
a2.text(0.152, 0.18, "中等带 0.15", fontsize=9)
a2.axvline(0, color="black", lw=0.9)
a2.text(h1["ci_lo"] - 0.005, 0,
        f"控制后：β = {h1['beta']:+.4f}\n95% CI [{h1['ci_lo']:.4f}, {h1['ci_hi']:.4f}]\n"
        f"p_holm < 0.001（判定 partial）",
        va="center", ha="right", fontsize=9.3, color="#7e5109")
a2.set_yticks([]); a2.set_xlim(0.0, 0.20)
a2.set_xlabel("has_causal 对标准化重叠的系数", fontsize=10)
a2.set_ylim(-0.55, 0.55)
a2.set_title("(b) 控制后：效应真实但低于中等带\n（LR χ2 = 124.0，df = 1）", fontsize=10.5)
a2.grid(alpha=0.25, axis="x", ls="--")
fig.suptitle("图2  H1 的两种口径：连接词与证据取材共舞，但不是大步", fontsize=12, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(OUT / "custom_fig2_h1_two_scalings.png", bbox_inches="tight")
plt.close()

# ===== 图3 正文长度四分位分层 =====
fig, ax = plt.subplots(figsize=(9.4, 4.9))
strata = [s for s in art["strata"] if s.get("stratification") == "body_quartile" and s.get("beta") is not None]
qlab = {"q1_shortest": "Q1 最短", "q2": "Q2", "q3": "Q3", "q4_longest": "Q4 最长"}
for i, s in enumerate(strata):
    nm = qlab.get(s["stratum"], s["stratum"])
    sig = s.get("p") is not None and s["p"] < 0.05
    c = C_ACC if sig else C_NULL
    ax.plot([s["ci_lo"], s["ci_hi"]], [i, i], color=c, lw=3, alpha=0.85)
    ax.plot(s["beta"], i, "D", color=c, ms=10)
    star = " *" if sig else ""
    ax.text(s["ci_hi"] + 0.008, i, f"β={s['beta']:+.4f}{star}", va="center", fontsize=9.5)
ax.axvline(0, color="black", lw=0.9, ls="--")
ax.set_yticks(range(len(strata)))
ax.set_yticklabels([qlab.get(s["stratum"], s["stratum"]) for s in strata], fontsize=10.5)
ax.set_xlabel("连接词效应对标准化重叠的系数（正文四分位分层，描述性）", fontsize=10)
ax.set_xlim(-0.13, 0.30)
ax.set_title("图3  效应的长度梯度：短 turn 里连接词与证据取材强耦合，\n"
             "长 turn 里耦合消失——连接词的语义在长文本里被结构性用法稀释\n（* p<0.05）",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="x", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig3_length_gradient.png", bbox_inches="tight")
plt.close()

# ===== 图4 两族稀有度与 H2 =====
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.5, 4.5))
h2m = h2
a1.bar([0, 1], [h2m["inferential_turn_share"] * 100, h2m["explanatory_turn_share"] * 100],
       color=[C_PART, C_ACC], alpha=0.88, width=0.45)
for x, v, n_lab in [(0, h2m["inferential_turn_share"], "约 450 个 turn"),
                    (1, h2m["explanatory_turn_share"], "约 7,300 个 turn")]:
    a1.text(x, v * 100 + 0.1, f"{v*100:.2f}%\n{n_lab}", ha="center", fontsize=9.5)
a1.set_xticks([0, 1])
a1.set_xticklabels(["推理族\n(therefore/thus/hence)", "解释族\n(because/since/given)"], fontsize=9.5)
a1.set_ylabel("turn 占比（%）", fontsize=10)
a1.set_ylim(0, 6.5)
a1.set_title("(a) 两族的存量极不均衡：推理族稀缺\n（1:16，H2 的功效先天受限）", fontsize=10.5)
a1.grid(alpha=0.25, axis="y", ls="--")

lo, hi = h2["ci_lo"], h2["ci_hi"]
a2.plot([lo, hi], [0, 0], color=C_NULL, lw=4, alpha=0.85, solid_capstyle="round")
a2.plot(h2["beta"], 0, "D", color=C_NULL, ms=10)
a2.axvline(0, color="black", lw=0.9, ls="--")
a2.text(hi + 0.0008, 0,
        f"β = {h2['beta']:+.4f}\n95% CI [{lo:.4f}, {hi:.4f}]\np_holm = {h2['p_holm']:.3f}（判定 null）\n"
        f"点估计方向符合预期（推理族重叠更少）\n但幅度近零且 CI 跨零",
        va="center", fontsize=9)
a2.set_yticks([]); a2.set_xlim(-0.010, 0.012)
a2.set_xlabel("推理族 - 解释族的重叠差", fontsize=10)
a2.set_ylim(-0.5, 0.5)
a2.set_title("(b) H2 判 null：预期的方向留了个影，\n证据不足以兑现它", fontsize=10.5)
a2.grid(alpha=0.25, axis="x", ls="--")
fig.suptitle("图4  H2 的两族对比：一个稀缺的对比与一个近零的差",
             fontsize=12, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(OUT / "custom_fig4_families.png", bbox_inches="tight")
plt.close()

print("P030 figures done:", [p.name for p in sorted(OUT.glob("custom_*.png"))])
