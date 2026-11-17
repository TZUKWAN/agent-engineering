# -*- coding: utf-8 -*-
"""P016 定制图：基于 T116 (描述粒度, EXP-0140) 产物数据。

本文的个性：参数化斜率为正且显著，但冻结要求的"先升后平"凹形剂量反应
模式未被满足（monotone_then_flat=false, spearman=-0.067, 高低对比 CI 为负）。
四张图全部围绕这一张力展开，不套用任何其他论文的图式。
"""
import json, glob, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 300

fs = sorted(glob.glob("results_raw/EXP0140_wave2_design_*.json"))
art = json.load(open(fs[-1], encoding="utf-8"))
OUT = pathlib.Path("papers/P016_description_granularity/figures")
OUT.mkdir(parents=True, exist_ok=True)

C_SUP = "#27ae60"   # supported
C_PART = "#e67e22"  # partial
C_NULL = "#95a5a6"  # null / not_testable
C_ACC = "#2980b9"   # accent
C_COST = "#c0392b"  # cost side

dose = art["dose_response"]
dec = [r["len_decile"] for r in dose]
tok = [r["gold_desc_tokens"] for r in dose]
reach = [r["reachable"] for r in dose]
fail3 = [r["fail_at_3"] for r in dose]
pn = [r["param_n"] for r in dose]
pat = art["pattern"]

# ===== 图1 十分位剂量反应：波动形态 vs 参数化斜率 =====
fig, ax = plt.subplots(figsize=(9.5, 5.2))
ax.plot(dec, reach, "o-", color=C_ACC, lw=1.8, ms=6, zorder=3, label="各十分位可达率")
mean_r = np.mean(reach)
ax.axhline(mean_r, color=C_NULL, lw=1, ls=":", alpha=0.9)
ax.text(0.3, mean_r + 0.002, f"总体均值 {mean_r:.3f}", fontsize=8.5, color="#666")

# 下半/上半斜率线（从产物 pattern 块原样绘出）
half = len(dec) // 2
lx, ly = np.array(dec[:half]), np.array(reach[:half])
ux, uy = np.array(dec[half:]), np.array(reach[half:])
bl, bu = pat["lower_half_slope_per_decile"], pat["upper_half_slope_per_decile"]
ax.plot(lx, ly[0] + bl * (lx - lx[0]), "--", color="#8e44ad", lw=1.6,
        label=f"前半段斜率 {bl:+.4f}/档")
ax.plot(ux, uy[0] + bu * (ux - ux[0]), "--", color="#16a085", lw=1.6,
        label=f"后半段斜率 {bu:+.4f}/档")

# 每档标注平均 token 数（放在点的上方，避开折线）
for d, t, r in zip(dec, tok, reach):
    ax.annotate(f"{t:.0f}tok", (d, r), textcoords="offset points",
                xytext=(0, 9), ha="center", fontsize=7.5, color="#555")

ax.set_xticks(dec)
ax.set_xlabel("金标工具描述长度十分位（标注为该档平均 token 数）", fontsize=10)
ax.set_ylabel("rank-1 可达率", fontsize=10)
ax.set_ylim(0.70, 0.96)
ax.set_title("图1  描述长度的剂量反应：线性斜率为正，但十分位曲线波动、\n"
             "未满足预注册的“先升后平”模式（Spearman = "
             f"{pat['spearman_decile_vs_reachability']:.3f}）",
             fontsize=12, fontweight="bold", pad=12)
ax.legend(fontsize=8.5, loc="lower left", framealpha=0.9)
ax.grid(alpha=0.25, ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig1_dose_response.png", bbox_inches="tight")
plt.close()

# ===== 图2 成本侧：参数量与 fail@3 随长度上升 =====
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.4))
a1.bar(dec, pn, color=C_ACC, alpha=0.85, edgecolor="white")
a1.plot(dec, pn, "o", color="#1f3f66", ms=4, zorder=3)
a1.set_xlabel("描述长度十分位", fontsize=10)
a1.set_ylabel("平均候选参数数", fontsize=10)
a1.set_title("(a) 候选参数量随描述长度单调上升\n（1.21 → 7.86，约 6.5 倍）", fontsize=10.5)
a1.set_xticks(dec)
a1.grid(alpha=0.25, axis="y", ls="--")

bars = a2.bar(dec, fail3, color=[C_COST if f == max(fail3) else "#e6b0aa" for f in fail3],
              alpha=0.9, edgecolor="white")
a2.annotate(f"峰值 {max(fail3):.3f}\n（第 4 档）", (4, max(fail3)),
            textcoords="offset points", xytext=(18, 4), fontsize=8.5, color=C_COST,
            arrowprops=dict(arrowstyle="->", color=C_COST, lw=1))
a2.annotate(f"第10档最低 {fail3[-1]:.3f}", (10, fail3[-1]),
            textcoords="offset points", xytext=(-30, 22), fontsize=8.5, color="#555")
cs = art["cost_side"]
a2.set_xlabel("描述长度十分位", fontsize=10)
a2.set_ylabel("非金标挤占率（displaces_others）", fontsize=10)
a2.set_title(f"(b) 挤占率的长度梯度\nlen_z β={cs['beta']:.4f} "
             f"[{cs['ci_lo']:.4f}, {cs['ci_hi']:.4f}]，n={cs['n']:,}", fontsize=10.5)
a2.set_xticks(dec)
a2.grid(alpha=0.25, axis="y", ls="--")
fig.suptitle("图2  更长描述的成本侧：同一条旋钮把更多无关候选推上前来",
             fontsize=12, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(OUT / "custom_fig2_cost_side.png", bbox_inches="tight")
plt.close()

# ===== 图3 目录规模分层：斜率差 =====
models = {m["stratum"]: m for m in art["models"]}
large = models.get("large_catalogue")
small = models.get("small_catalogue")
inter = art["interaction"]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.4), gridspec_kw={"width_ratios": [1.15, 1]})
rows = [("大目录（长清单）", large["beta"], large["ci_lo"], large["ci_hi"], C_ACC),
        ("小目录（短清单）", small["beta"], small["ci_lo"], small["ci_hi"], "#7fb3d5")]
for i, (lab, b, lo, hi, c) in enumerate(rows):
    a1.plot([lo, hi], [i, i], color=c, lw=3, alpha=0.85)
    a1.plot(b, i, "D", color=c, ms=9)
    a1.text(hi + 0.006, i, f"β={b:.4f}\nn={large['n'] if i==0 else small['n']:,}",
            va="center", fontsize=9)
a1.axvline(0, color="black", lw=0.8, ls="--")
a1.set_yticks([0, 1]); a1.set_yticklabels([r[0] for r in rows], fontsize=10)
a1.set_xlabel("描述长度斜率 β（query 聚类稳健）", fontsize=10)
a1.set_xlim(-0.05, 0.42)
a1.set_title("(a) 分层斜率：大目录约为小目录的 2.8 倍", fontsize=10.5)
a1.grid(alpha=0.25, axis="x", ls="--")

a2.barh([1], [inter["beta"]], xerr=[[inter["beta"]-inter["ci_lo"]], [inter["ci_hi"]-inter["beta"]]],
        color="#8e44ad", alpha=0.85, height=0.45,
        error_kw=dict(capsize=5, lw=1.4, ecolor="#4a235a"))
a2.axvline(0, color="black", lw=0.8, ls="--")
a2.text(inter["ci_hi"] + 0.008, 1,
        f"β={inter['beta']:.4f} [{inter['ci_lo']:.4f}, {inter['ci_hi']:.4f}]\n"
        f"两斜率差（描述性）= 0.1614", va="center", fontsize=9)
a2.set_yticks([1]); a2.set_yticklabels(["长度 × 目录规模"], fontsize=10)
a2.set_xlabel("交互项系数", fontsize=10)
a2.set_xlim(-0.02, 0.62)
a2.set_title("(b) 交互项：清单越长，长描述的边际收益越大\n（但拐点差仍不可估）", fontsize=10.5)
a2.grid(alpha=0.25, axis="x", ls="--")
fig.suptitle("图3  目录规模的调节作用（H2 材料：描述性分层 + 交互项）",
             fontsize=12, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(OUT / "custom_fig3_catalogue_strata.png", bbox_inches="tight")
plt.close()

# ===== 图4 判定面板：参数化证据 vs 模式证据 =====
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.5, 4.6), gridspec_kw={"width_ratios": [1.1, 1]})
m1 = models["all_queries"]
ev = [("H1 主斜率（query 级）", m1["beta"], m1["ci_lo"], m1["ci_hi"], C_SUP, "supported"),
      ("H3 挤占率（候选级）", cs["beta"], cs["ci_lo"], cs["ci_hi"], C_PART, "partial")]
for i, (lab, b, lo, hi, c, v) in enumerate(ev):
    a1.plot([lo, hi], [i, i], color=c, lw=3, alpha=0.85)
    a1.plot(b, i, "D", color=c, ms=9)
    a1.text(hi + 0.006, i, f"{lab}\nβ={b:.4f}，判定 {v}", va="center", fontsize=9)
a1.axvline(0, color="black", lw=0.8, ls="--")
a1.set_yticks([0, 1]); a1.set_yticklabels(["H1", "H3"], fontsize=11)
a1.set_xlim(-0.02, 0.45)
a1.set_xlabel("系数（β）与 95% CI", fontsize=10)
a1.set_title("(a) 预注册假设的参数化证据\n（Holm 校正后均 p<0.001）", fontsize=10.5)
a1.grid(alpha=0.25, axis="x", ls="--")

# 右面板：模式诊断——高低十分位对比的 bootstrap CI
hl = art["high_minus_low_reachability_ci"]
a2.axhline(0, color="black", lw=0.8)
a2.plot([0, 0], [hl[0], hl[1]], color=C_COST, lw=3.5, alpha=0.8, solid_capstyle="round")
a2.plot(0, np.mean(hl), "o", color=C_COST, ms=10)
a2.text(0.06, np.mean(hl), f"高10档 - 低10档 = {np.mean(hl):+.4f}\n"
        f"95% bootstrap CI [{hl[0]:.4f}, {hl[1]:.4f}]\np_boot = {art['high_minus_low_p_boot']:.3f}",
        va="center", fontsize=9, color=C_COST)
a2.text(0.06, hl[0] - 0.004,
        f"诊断：monotone_then_flat = {pat['monotone_then_flat']}\n"
        f"降档数 {pat['decreasing_deciles']} / 升档数 {pat['non_decreasing_deciles']}",
        va="top", fontsize=9, color="#555")
a2.set_xlim(-0.5, 1.0)
a2.set_xticks([])
a2.set_ylabel("可达率差（高 - 低）", fontsize=10)
a2.set_title("(b) 模式证据与参数化证据相反：\n非参数高低对比略微为负", fontsize=10.5)
a2.grid(alpha=0.25, axis="y", ls="--")
fig.suptitle("图4  判定的完整画面：H1 的“supported”只建立在斜率区间上，模式检验未通过",
             fontsize=12, fontweight="bold", y=1.03)
fig.tight_layout()
fig.savefig(OUT / "custom_fig4_verdict_panel.png", bbox_inches="tight")
plt.close()

print("P016 figures done:", [p.name for p in sorted(OUT.glob("custom_*.png"))])
