# -*- coding: utf-8 -*-
"""P036 定制图：基于 T168 (工具切换成本, EXP-0177, wave-6) 产物数据。

本文的个性：切换不是成本而是红利——换家族的步新信息率更高
（H1 opposite +0.2234），高切换率 rollout 更早完成（H2 opposite -0.0251），
族内符号 0/9 复现（H3）。附加：转移矩阵热图揭示觅食循环
（search_name→read_file→search_content→edit）。
"""
import json, glob, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 300

fs = sorted(glob.glob("results_raw/EXP0177_wave6_design_*.json"))
art = json.load(open(fs[-1], encoding="utf-8"))
OUT = pathlib.Path("papers/P036_command_family_switching_cost/figures")
OUT.mkdir(parents=True, exist_ok=True)

C_SUP = "#27ae60"
C_OPP = "#c0392b"
C_ACC = "#2980b9"
C_NULL = "#95a5a6"

models = {m["hypothesis"]: m for m in art["models"]}
h1, h2, h3 = models["H1"], models["H2"], models["H3"]
trans = art["descriptive_rates"]["family_transitions"]
ns = art["descriptive_rates"]["newness_by_switch_state"]

# ===== 图1 三假设判定森林 =====
fig, ax = plt.subplots(figsize=(10, 4.6))
rows = [
    ("H1 切换 → 新信息", h1["beta"], h1["ci_lo"], h1["ci_hi"], C_OPP,
     f"判定 opposite\nβ={h1['beta']:+.4f}，p_holm<0.001\n（预测负，实测强正：切换红利）"),
    ("H2 切换率 → 深度", h2["beta"], h2["ci_lo"], h2["ci_hi"], C_OPP,
     f"判定 opposite\nβ={h2['beta']:+.4f}，p_holm=0.0014\n（预测正，实测负：高切换更早完成）"),
]
for i, (lab, b, lo, hi, c, note) in enumerate(rows):
    ax.plot([lo, hi], [i, i], color=c, lw=3, alpha=0.85)
    ax.plot(b, i, "D", color=c, ms=9)
    ax.text(hi + 0.004, i, note, va="center", fontsize=8.6)
ax.axvline(0, color="black", lw=0.9, ls="--")
ax.set_yticks([0, 1]); ax.set_yticklabels(["H1", "H2"], fontsize=11)
ax.set_xlim(-0.065, 0.30)
ax.set_xlabel("系数（H1：标准化新信息；H2：log 步数）", fontsize=10)
ax.set_title("图1  两个主假设：切换成本假说两个方向都被数据反转",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="x", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig1_verdicts.png", bbox_inches="tight")
plt.close()

# ===== 图2 切换 vs 留守的新信息率 + H1 =====
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.5, 4.5))
a1.bar([0, 1], [ns["0"]["mean_newness"] * 100, ns["1"]["mean_newness"] * 100],
       color=["#aab7b8", C_SUP], alpha=0.88, width=0.45)
for x, k in [(0, "0"), (1, "1")]:
    a1.text(x, ns[k]["mean_newness"] * 100 + 0.8, f"{ns[k]['mean_newness']*100:.2f}%\n(n={ns[k]['rows']:,})",
            ha="center", fontsize=9.5)
a1.set_xticks([0, 1]); a1.set_xticklabels(["留守（同家族重复）", "切换（家族改变）"], fontsize=10)
a1.set_ylabel("步的新信息率（%）", fontsize=10)
a1.set_ylim(0, 70)
a1.set_title("(a) 描述性：切换步的新信息率高出 5.9 个百分点", fontsize=10.5)
a1.grid(alpha=0.25, axis="y", ls="--")

a2.plot([h1["ci_lo"], h1["ci_hi"]], [0, 0], color=C_SUP, lw=4, alpha=0.9, solid_capstyle="round")
a2.plot(h1["beta"], 0, "D", color=C_SUP, ms=11)
a2.axvline(0, color="black", lw=0.9, ls="--")
a2.text(h1["ci_lo"] - 0.004, 0,
        f"切换对标准化新信息的系数\nβ = {h1['beta']:+.4f}\n"
        f"95% CI [{h1['ci_lo']:.4f}, {h1['ci_hi']:.4f}]\nLR χ2 = 5,131（df=1）\n判定 opposite：切换红利",
        va="center", ha="right", fontsize=9.3, color="#145a32")
a2.set_yticks([]); a2.set_xlim(0.185, 0.275)
a2.set_xlabel("switched 系数", fontsize=10)
a2.set_ylim(-0.5, 0.5)
a2.set_title("(b) 条件化后的切换红利（系列强效应之一）", fontsize=10.5)
a2.grid(alpha=0.25, axis="x", ls="--")
fig.suptitle("图2  H1 的两种口径：换家族的步带来更多新知", fontsize=12, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(OUT / "custom_fig2_switch_bonus.png", bbox_inches="tight")
plt.close()

# ===== 图3 转移矩阵热图（觅食循环） =====
fig, ax = plt.subplots(figsize=(9.8, 7.2))
keys = list(trans.keys())
pairs = [k.split("->") for k in keys]
srcs = sorted(set(p[0] for p in pairs))
dsts = sorted(set(p[1] for p in pairs))
M = np.zeros((len(srcs), len(dsts)))
for k, v in trans.items():
    s, d = k.split("->")
    M[srcs.index(s), dsts.index(d)] = v
Mlog = np.log10(M + 1)
im = ax.imshow(Mlog, cmap="YlGnBu", aspect="auto")
ax.set_xticks(range(len(dsts)))
ax.set_xticklabels([d.replace("_", " ") for d in dsts], fontsize=8.5, rotation=30, ha="right")
ax.set_yticks(range(len(srcs)))
ax.set_yticklabels([s.replace("_", " ") for s in srcs], fontsize=8.5)
for i in range(len(srcs)):
    for j in range(len(dsts)):
        if M[i, j] > 0:
            ax.text(j, i, f"{int(M[i,j]):,}", ha="center", va="center",
                    fontsize=7, color="white" if Mlog[i, j] > 3.4 else "#333")
ax.set_xlabel("下一步的命令族", fontsize=10)
ax.set_ylabel("上一步的命令族", fontsize=10)
ax.set_title("图3  命令族转移矩阵（步数，对数色标）：\n"
             "search_name→read_file（20,057）与 read_file→search_content（12,274）\n勾勒出「搜索→读取→再搜索」的觅食循环",
             fontsize=12, fontweight="bold", pad=12)
fig.colorbar(im, ax=ax, label="log10(步数+1)", shrink=0.8)
fig.tight_layout()
fig.savefig(OUT / "custom_fig3_transition_matrix.png", bbox_inches="tight")
plt.close()

# ===== 图4 位置分层 + H2 =====
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.5, 4.5))
stra = [s for s in art["strata"] if s.get("stratification") == "position_third"]
plab = {"first_third": "前三分之一", "middle_third": "中三分之一", "last_third": "后三分之一"}
for i, s in enumerate(stra):
    nm = plab.get(s["stratum"], s["stratum"])
    a1.plot([s["ci_lo"], s["ci_hi"]], [i, i], color=C_SUP, lw=3, alpha=0.85)
    a1.plot(s["beta"], i, "D", color=C_SUP, ms=10)
    a1.text(s["ci_hi"] + 0.004, i, f"β={s['beta']:+.4f}", va="center", fontsize=9.5)
a1.axvline(0, color="black", lw=0.9, ls="--")
a1.set_yticks(range(len(stra)))
a1.set_yticklabels([plab.get(s["stratum"], s["stratum"]) for s in stra], fontsize=10.5)
a1.set_xlabel("切换红利系数（位置分层，描述性）", fontsize=10)
a1.set_xlim(0.14, 0.30)
a1.set_title("(a) H3 的分层数据：红利在三段全程显著、量级稳定\n（符号 9/9 为正但族内判定词仍为 not_reproduced）", fontsize=10)
a1.grid(alpha=0.25, axis="x", ls="--")

a2.barh([0], [abs(h2["beta"])], height=0.4, color=C_SUP, alpha=0.85)
a2.errorbar(abs(h2["beta"]), 0, xerr=[[abs(h2["beta"]) - abs(h2["ci_hi"])], [abs(h2["ci_lo"]) - abs(h2["beta"])]],
            color="#145a32", capsize=6, lw=1.5, fmt="none")
a2.axvline(0, color="black", lw=0.9, ls="--")
a2.text(abs(h2["beta"]) + 0.003, 0,
        f"切换率对 rollout 深度的系数\nβ = {h2['beta']:+.4f}（预测正，实测负）\n"
        f"95% CI [{h2['ci_lo']:.4f}, {h2['ci_hi']:.4f}]，p_holm = {h2['p_holm']:.4f}\n（n = {h2['trajectories']:,} 条 rollout）",
        va="center", fontsize=9.3, color="#145a32")
a2.set_yticks([]); a2.set_xlim(0, 0.065)
a2.set_xlabel("|切换率对 log 步数的系数|（方向：更浅）", fontsize=10)
a2.set_ylim(-0.5, 0.5)
a2.set_title("(b) H2 判 opposite：高切换率的 rollout\n更早到达终点——切换是效率而非浪费", fontsize=10.5)
a2.grid(alpha=0.25, axis="x", ls="--")
fig.suptitle("图4  红利的全段稳定性与效率读数", fontsize=12, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(OUT / "custom_fig4_position_h2.png", bbox_inches="tight")
plt.close()

print("P036 figures done:", [p.name for p in sorted(OUT.glob("custom_*.png"))])
