# -*- coding: utf-8 -*-
"""P034 定制图：基于 T157 (信息气味与下一步选择, EXP-0175, wave-6) 产物数据。

本文的个性：命名期待 → 收获新信息（H1 partial），双仪器一致（H2 partial,
rho=0.995），但特异性失败——冗长度对照更强（H3 failed, 0.052 vs 0.027）；
效应集中在前中段；search_name 命令的新信息率最高（83.7%）。
"""
import json, glob, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 300

fs = sorted(glob.glob("results_raw/EXP0175_wave6_design_*.json"))
art = json.load(open(fs[-1], encoding="utf-8"))
OUT = pathlib.Path("papers/P034_information_scent_and_the_next_choice/figures")
OUT.mkdir(parents=True, exist_ok=True)

C_SUP = "#27ae60"
C_PART = "#e67e22"
C_OPP = "#c0392b"
C_ACC = "#2980b9"

models = {m["hypothesis"]: m for m in art["models"]}
h1, h2, h3 = models["H1"], models["H2"], models["H3"]
fam = art["descriptive_rates"]["mean_scent_by_command_family"]

# ===== 图1 三假设判定森林 =====
fig, ax = plt.subplots(figsize=(10, 4.8))
rows = [
    ("H1 气味 → 新信息", h1["beta"], h1["ci_lo"], h1["ci_hi"], C_PART,
     f"判定 partial\nβ={h1['beta']:+.4f}，p_holm<0.001\n（显著为正，低于中等带）"),
    ("H2 含式仪器重估", h2["beta"], h2["ci_lo"], h2["ci_hi"], C_PART,
     f"判定 partial\nβ={h2['beta']:+.4f}，p_holm<0.001\n（双仪器 ρ=0.9953）"),
    ("H3 冗长度对照", h3["beta"], h3["ci_lo"], h3["ci_hi"], C_OPP,
     f"判定 not_specific\nβ={h3['beta']:+.4f}，p_holm<0.001\n（对照更强：特异性失败）"),
]
for i, (lab, b, lo, hi, c, note) in enumerate(rows):
    ax.plot([lo, hi], [i, i], color=c, lw=3, alpha=0.85)
    ax.plot(b, i, "D", color=c, ms=9)
    ax.text(hi + 0.002, i, note, va="center", fontsize=8.6)
ax.axvline(0, color="black", lw=0.9, ls="--")
ax.set_yticks([0, 1, 2]); ax.set_yticklabels(["H1", "H2", "H3"], fontsize=11)
ax.set_xlim(0.012, 0.075)
ax.set_xlabel("对标准化新信息量的系数（聚类稳健）", fontsize=10)
ax.set_title("图1  三个预注册假设：气味有效、仪器稳健、但特异性栽在冗长度上",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="x", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig1_verdicts.png", bbox_inches="tight")
plt.close()

# ===== 图2 命令族画像：气味 vs 新信息率 =====
fig, ax1 = plt.subplots(figsize=(10.5, 5.2))
fams = sorted(fam.keys(), key=lambda k: -fam[k]["newness"])
names = [k.replace("_", " ") for k in fams]
newn = [fam[k]["newness"] * 100 for k in fams]
sc = [fam[k]["scent"] * 100 for k in fams]
x = np.arange(len(fams))
ax1.bar(x - 0.2, newn, width=0.38, color=C_ACC, alpha=0.88, label="新信息率（观察中未见内容的占比）")
ax1.set_ylabel("新信息率（%）", fontsize=10, color=C_ACC)
ax1.set_ylim(0, 100)
ax2 = ax1.twinx()
ax2.bar(x + 0.2, sc, width=0.38, color=C_PART, alpha=0.88, label="气味均值（%）")
ax2.set_ylabel("气味均值（%）", fontsize=10, color=C_PART)
ax2.set_ylim(0, 10)
ax1.set_xticks(x)
ax1.set_xticklabels([f"{n}\n(n={fam[k]['rows']:,})" for n, k in zip(names, fams)],
                    fontsize=8, rotation=30, ha="right")
ax1.annotate("search_name：新信息率最高 83.7%", xy=(0, 84), xytext=(2.2, 92),
             fontsize=9.5, color=C_ACC,
             arrowprops=dict(arrowstyle="->", color=C_ACC, lw=1.2))
ax1.annotate("edit：新信息率最低 29.8%\n（改文件很少带来新知）", xy=(len(fams) - 2, 30),
             xytext=(len(fams) - 4.5, 55), fontsize=9.5, color="#555",
             arrowprops=dict(arrowstyle="->", color="#555", lw=1.2))
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, fontsize=9, loc="upper right")
ax1.set_title("图2  十个命令族的画像：命名搜索带来最多新知，编辑带来最少",
              fontsize=12, fontweight="bold", pad=12)
ax1.grid(alpha=0.25, axis="y", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig2_family_profile.png", bbox_inches="tight")
plt.close()

# ===== 图3 双仪器对照 =====
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.5, 4.5), gridspec_kw={"width_ratios": [1.25, 1]})
a1.barh([0, 1], [h1["beta"], h2["beta"]],
        xerr=[[h1["beta"] - h1["ci_lo"], h2["beta"] - h2["ci_lo"]],
              [h1["ci_hi"] - h1["beta"], h2["ci_hi"] - h2["beta"]]],
        height=0.42, color=[C_PART, C_ACC], alpha=0.88,
        error_kw=dict(capsize=6, lw=1.5))
a1.axvline(0, color="black", lw=0.9, ls="--")
a1.text(0.036, 0, f"Jaccard 对称仪器\nβ={h1['beta']:+.4f}", va="center", fontsize=9.5)
a1.text(0.0395, 1, f"含式非对称仪器\nβ={h2['beta']:+.4f}", va="center", fontsize=9.5)
a1.set_yticks([0, 1]); a1.set_yticklabels(["H1", "H2"], fontsize=11)
a1.set_xlim(0, 0.055)
a1.set_xlabel("对标准化新信息量的系数", fontsize=10)
a1.set_title("(a) 两台仪器的系数几乎重合", fontsize=10.5)
a1.grid(alpha=0.25, axis="x", ls="--")

rho = h2["instruments_agree"]["rho"]
rho_ci = h2["instruments_agree"]["ci"]
a2.bar([0], [rho], width=0.35, color=C_SUP, alpha=0.85)
a2.errorbar(0, rho, yerr=[[rho - rho_ci[0]], [rho_ci[1] - rho]],
            color="#145a32", capsize=6, lw=1.5, fmt="none")
a2.text(0, rho - 0.004, f"ρ = {rho:.4f}\nCI [{rho_ci[0]:.4f}, {rho_ci[1]:.4f}]",
        ha="center", fontsize=10, color="#145a32")
a2.set_xticks([]); a2.set_ylim(0.95, 1.005)
a2.set_ylabel("两仪器评分的相关 ρ", fontsize=10)
a2.set_title("(b) 仪器一致性近乎完美（n=229,893）\n（与 P027 kappa=0.03 的对照）", fontsize=10.5)
a2.grid(alpha=0.25, axis="y", ls="--")
fig.suptitle("图3  H2 的双仪器复核：本包的词表家族第一次通过信度检验",
             fontsize=12, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(OUT / "custom_fig3_two_instruments.png", bbox_inches="tight")
plt.close()

# ===== 图4 特异性失败 + 位置分层 =====
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.5, 4.6))
a1.bar([0, 1], [h1["beta"], h3["beta"]], width=0.45,
       color=[C_PART, C_OPP], alpha=0.88)
for x, m in [(0, h1), (1, h3)]:
    a1.text(x, m["beta"] + 0.0015, f"β={m['beta']:+.4f}", ha="center", fontsize=10.5)
a1.axhline(0, color="black", lw=0.9)
a1.set_xticks([0, 1])
a1.set_xticklabels(["气味（H1）", "冗长度对照（H3）"], fontsize=10)
a1.set_ylabel("对标准化新信息量的系数", fontsize=10)
a1.set_ylim(0, 0.075)
a1.set_title("(a) 特异性失败：对照词表（无指认内容）\n的系数反而约为气味系数的两倍", fontsize=10.5)
a1.grid(alpha=0.25, axis="y", ls="--")

stra = [s for s in art["strata"] if s.get("stratification") == "position_third"]
plab = {"first_third": "前三分之一", "middle_third": "中三分之一", "last_third": "后三分之一"}
for i, s in enumerate(stra):
    nm = plab.get(s["stratum"], s["stratum"])
    sig = s.get("p") is not None and s["p"] < 0.05
    c = C_ACC if sig else C_ACC
    a2.plot([s["ci_lo"], s["ci_hi"]], [i, i], color=c, lw=3, alpha=0.85)
    a2.plot(s["beta"], i, "D", color=c, ms=10)
    star = " *" if sig else ""
    a2.text(s["ci_hi"] + 0.004, i, f"β={s['beta']:+.4f}{star}", va="center", fontsize=9)
a2.axvline(0, color="black", lw=0.9, ls="--")
a2.set_yticks(range(len(stra)))
a2.set_yticklabels([plab.get(s["stratum"], s["stratum"]) for s in stra], fontsize=10.5)
a2.set_xlabel("气味系数（位置分层，描述性）", fontsize=10)
a2.set_xlim(-0.02, 0.075)
a2.set_title("(b) 效应随轨迹推进衰减：后三分之一归零\n——气味只在探索前中期起作用（* p<0.05）", fontsize=10.5)
a2.grid(alpha=0.25, axis="x", ls="--")
fig.suptitle("图4  H3 的特异性失败与位置衰减", fontsize=12, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(OUT / "custom_fig4_specificity_position.png", bbox_inches="tight")
plt.close()

print("P034 figures done:", [p.name for p in sorted(OUT.glob("custom_*.png"))])
