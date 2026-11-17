# -*- coding: utf-8 -*-
"""P037 定制图：基于 T170 (首步路径依赖, EXP-0178, wave-6) 产物数据。

本文的个性：开局不锁局——97.89% 的 rollout 以 search_name 开局（首步
几乎无变异），首步家族不影响后续家族混合（H1 null，两行混合分布
几乎重合），留守首家族预示跑满失败（H2 opposite β=-0.946）。
"""
import json, glob, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 300

fs = sorted(glob.glob("results_raw/EXP0178_wave6_design_*.json"))
art = json.load(open(fs[-1], encoding="utf-8"))
OUT = pathlib.Path("papers/P037_first_action_path_dependence/figures")
OUT.mkdir(parents=True, exist_ok=True)

C_SUP = "#27ae60"
C_OPP = "#c0392b"
C_ACC = "#2980b9"
C_NULL = "#95a5a6"

models = {m["hypothesis"]: m for m in art["models"]}
h1, h2, h3 = models["H1"], models["H2"], models["H3"]
mix = art["descriptive_rates"]["family_mix_after_the_first_step_by_first_family"]
conc = art["descriptive_rates"]["concentration_by_first_family"]
h1m = models["H1"]
share = h1m["first_family_share"]

# ===== 图1 首步家族的压倒性分布 =====
fig, ax = plt.subplots(figsize=(9.2, 4.8))
fams = sorted(share.keys(), key=lambda k: -share[k])
vals = [share[k] * 100 for k in fams]
ax.bar(range(len(fams)), vals, color=[C_ACC if v > 1 else C_NULL for v in vals],
       alpha=0.88, width=0.55)
for i, v in enumerate(vals):
    ax.text(i, v + 1.2, f"{v:.2f}%", ha="center", fontsize=9.5)
ax.set_xticks(range(len(fams)))
ax.set_xticklabels([k.replace("_", " ") for k in fams], fontsize=8.5, rotation=20, ha="right")
ax.set_ylabel("首步为该命令族的 rollout 占比（%）", fontsize=10)
ax.set_ylim(0, 108)
ax.set_title("图1  开局的压倒性共识：97.89% 的 rollout 以 search_name 起手\n"
             "（首步家族几乎没有变异——路径依赖的检验先天缺原料）",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="y", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig1_first_family_shares.png", bbox_inches="tight")
plt.close()

# ===== 图2 两行家族混合几乎重合 =====
fig, ax = plt.subplots(figsize=(10, 5.0))
fam_order = ["edit", "list", "other", "read_file", "search_content", "search_name"]
mix_list = mix["list"]
mix_sn = mix["search_name"]
x = np.arange(len(fam_order))
w = 0.35
ax.bar(x - w / 2, [mix_list[f] * 100 for f in fam_order], width=w,
       color=C_OPP, alpha=0.85, label="list 开局的 rollout（n=394）")
ax.bar(x + w / 2, [mix_sn[f] * 100 for f in fam_order], width=w,
       color=C_ACC, alpha=0.85, label="search_name 开局的 rollout（n=19,566）")
for xi, f in zip(x - w / 2, fam_order):
    ax.text(xi, mix_list[f] * 100 + 0.4, f"{mix_list[f]*100:.1f}", ha="center", fontsize=8.5)
for xi, f in zip(x + w / 2, fam_order):
    ax.text(xi, mix_sn[f] * 100 + 0.4, f"{mix_sn[f]*100:.1f}", ha="center", fontsize=8.5)
ax.set_xticks(x)
ax.set_xticklabels([f.replace("_", " ") for f in fam_order], fontsize=9.5)
ax.set_ylabel("首步之后各命令族的步占比（%）", fontsize=10)
ax.set_ylim(0, 32)
ax.legend(fontsize=9.5)
ax.set_title("图2  H1 的核心证据：两种开局之后的后继行为几乎重合\n"
             "（任务决定形状，开局不锁局）",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="y", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig2_family_mix.png", bbox_inches="tight")
plt.close()

# ===== 图3 三假设判定森林 =====
fig, ax = plt.subplots(figsize=(10, 4.8))
rows = [
    ("H1 离模开局 → 家族集中度", h1["beta"], h1["ci_lo"], h1["ci_hi"], C_NULL,
     f"判定 null\nβ={h1['beta']:+.4f}，p_holm={h1['p_holm']:.3f}\n（离模 rollout 仅 450 条）"),
    ("H2 留守首家族 → 提交", h2["beta"], h2["ci_lo"], h2["ci_hi"], C_OPP,
     f"判定 opposite\nβ={h2['beta']:+.4f}，p_holm<0.001\n（留守预示跑满失败）"),
    ("H3 搜索开局 → 集中度", h3["beta"], h3["ci_lo"], h3["ci_hi"], C_NULL,
     f"判定 null\nβ={h3['beta']:+.4f}，p_holm={h3['p_holm']:.3f}\n（锁定机制不存在）"),
]
for i, (lab, b, lo, hi, c, note) in enumerate(rows):
    ax.plot([lo, hi], [i, i], color=c, lw=3, alpha=0.85)
    ax.plot(b, i, "D", color=c, ms=9)
    ax.text(hi + 0.05, i, note, va="center", fontsize=8.6)
ax.axvline(0, color="black", lw=0.9, ls="--")
ax.set_yticks([0, 1, 2]); ax.set_yticklabels(["H1", "H2", "H3"], fontsize=11)
ax.set_xlim(-1.5, 0.5)
ax.set_xlabel("系数（聚类稳健）", fontsize=10)
ax.set_title("图3  三个预注册假设：开局是可替换的第一步，留守是失败的签名",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="x", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig3_verdicts.png", bbox_inches="tight")
plt.close()

# ===== 图4 H2：留守=跑满的对比 =====
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.5, 4.5))
conc_fams = list(conc.keys())
cs = [conc[k]["mean"] for k in conc_fams]
subs = [conc[k]["submitted_share"] * 100 for k in conc_fams]
a1.bar([0, 1], [cs[0] * 100, cs[1] * 100], color=["#aab7b8", C_ACC], alpha=0.88, width=0.45)
for x, k in zip([0, 1], conc_fams):
    a1.text(x, conc[k]["mean"] * 100 + 0.5, f"{conc[k]['mean']*100:.2f}%", ha="center", fontsize=10)
a1.set_xticks([0, 1])
a1.set_xticklabels([f"{k.replace('_',' ')} 开局" for k in conc_fams], fontsize=10)
a1.set_ylabel("首步后留守首家族的步占比（%）", fontsize=10)
a1.set_ylim(0, 30)
a1.set_title("(a) 集中度：两种开局的留守率几乎相同\n（22.35% 对 23.96%）", fontsize=10.5)
a1.grid(alpha=0.25, axis="y", ls="--")

a2.barh([0], [abs(h2["beta"])], height=0.4, color=C_OPP, alpha=0.85)
a2.errorbar(abs(h2["beta"]), 0, xerr=[[abs(h2["beta"]) - abs(h2["ci_hi"])], [abs(h2["ci_lo"]) - abs(h2["beta"])]],
            color="#641e16", capsize=6, lw=1.5, fmt="none")
a2.axvline(0, color="black", lw=0.9, ls="--")
a2.text(abs(h2["beta"]) - 0.06, 0,
        f"留守首家族对提交的系数\nβ = {h2['beta']:+.4f}（预测正，实测强负）\n"
        f"95% CI [{h2['ci_lo']:.4f}, {h2['ci_hi']:.4f}]，p_holm < 0.001\n"
        f"（深度已入模：不是短路径的搭车效应）",
        va="center", ha="right", fontsize=9.3, color="#641e16")
a2.set_yticks([]); a2.set_xlim(0, 1.7)
a2.set_xlabel("|stays_in_family 对 submitted 的系数|", fontsize=10)
a2.set_ylim(-0.5, 0.5)
a2.set_title("(b) H2 判 opposite：死守开局的 rollout 跑满失败", fontsize=10.5)
a2.grid(alpha=0.25, axis="x", ls="--")
fig.suptitle("图4  集中度的对称与留守的代价", fontsize=12, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(OUT / "custom_fig4_concentration_h2.png", bbox_inches="tight")
plt.close()

print("P037 figures done:", [p.name for p in sorted(OUT.glob("custom_*.png"))])
