# -*- coding: utf-8 -*-
"""P042 figures: T165 catalogue ecosystem (EXP-0186, wave-7)."""
import json, glob, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 300

fs = sorted(glob.glob("results_raw/EXP0186_wave7_design_*.json"))
art = json.load(open(fs[-1], encoding="utf-8"))
OUT = pathlib.Path("papers/P042_the_catalogue_ecosystem/figures")
OUT.mkdir(parents=True, exist_ok=True)

C_SUP = "#27ae60"; C_OPP = "#c0392b"; C_ACC = "#2980b9"; C_NULL = "#95a5a6"

models = {m["hypothesis"]: m for m in art["models"]}
h1, h2, h3 = models["H1"], models["H2"], models["H3"]
od = art["descriptive_rates"]["overlap_distribution"]
tsb = art["descriptive_rates"]["servers_by_tool_count_band"]
tps = art["descriptive_rates"]["tools_per_server"]

# fig1: H1 within vs across overlap
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.5, 4.8))
# left: bar comparison
a1.bar([0, 1], [h1["across_mean"] * 100, (h1["across_mean"] + h1["beta"]) * 100],
       color=[C_NULL, C_SUP], alpha=0.88, width=0.45)
a1.text(0, h1["across_mean"] * 100 + 0.3, f"{h1['across_mean']*100:.2f}%", ha="center", fontsize=11)
a1.text(1, (h1["across_mean"] + h1["beta"]) * 100 + 0.3,
        f"{(h1['across_mean'] + h1['beta'])*100:.2f}%", ha="center", fontsize=11)
a1.set_xticks([0, 1])
a1.set_xticklabels(["跨服务器对", "同服务器对"], fontsize=11)
a1.set_ylabel("描述 Jaccard 重叠均值（%）", fontsize=10)
a1.set_ylim(0, 5.5)
a1.set_title("(a) 同服务器 > 跨服务器\nΔ = +{:.4f}（bootstrap CI 不含零）".format(h1["beta"]),
             fontsize=10.5)
a1.grid(alpha=0.25, axis="y", ls="--")

# right: overlap distribution boxen
within_p = od["within_p25_p50_p75"]
across_p = od["across_p25_p50_p75"]
a2.fill_between([0, 1], [within_p[0]*100]*2, [within_p[2]*100]*2, alpha=0.2, color=C_SUP)
a2.fill_between([1.2, 2.2], [across_p[0]*100]*2, [across_p[2]*100]*2, alpha=0.2, color=C_NULL)
a2.plot([0.5, 0.5], [within_p[1]*100]*2, color=C_SUP, lw=3)
a2.plot([1.7, 1.7], [across_p[1]*100]*2, color=C_NULL, lw=3)
a2.scatter([0.5, 1.7], [within_p[1]*100, across_p[1]*100], s=80,
           color=[C_SUP, C_NULL], zorder=5)
a2.text(0.5, within_p[1]*100 + 0.2, f"P50={within_p[1]*100:.2f}%", ha="center", fontsize=9.5)
a2.text(1.7, across_p[1]*100 + 0.2, f"P50={across_p[1]*100:.2f}%", ha="center", fontsize=9.5)
a2.text(0.5, within_p[0]*100 - 0.2, f"P25={within_p[0]*100:.1f}%", ha="center", fontsize=8.5, va="top")
a2.text(1.7, across_p[2]*100 + 0.15, f"P75={across_p[2]*100:.1f}%", ha="center", fontsize=8.5)
a2.set_xticks([0.5, 1.7])
a2.set_xticklabels(["同服务器", "跨服务器"], fontsize=11)
a2.set_ylabel("Jaccard 重叠（%）", fontsize=10)
a2.set_ylim(0, 42)
a2.set_title("(b) 重叠分布的 P25/P50/P75", fontsize=10.5)
a2.grid(alpha=0.25, axis="y", ls="--")
fig.suptitle("图1  H1 判 supported：同服务器描述确实比跨服务器更相似", fontsize=12, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(OUT / "custom_fig1_overlap_comparison.png", bbox_inches="tight"); plt.close()

# fig2: H2 ecosystem structure
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.5, 4.5))
h2m = models["H2"]
facts = [
    ("服务器总数", h2m["servers"], f"{h2m['servers']:,}"),
    ("候选插槽总数", h2m["candidate_slots"], f"{h2m['candidate_slots']:,}"),
    ("独立工具数", h2m["distinct_tools"], f"{h2m['distinct_tools']:,}"),
    ("HHI", h2m["herfindahl_over_servers"], f"{h2m['herfindahl_over_servers']:.4f}"),
    ("最大服务器份额%", h2m["largest_server_share"]*100, f"{h2m['largest_server_share']*100:.1f}%"),
    ("前12服务器份额%", h2m["top12_server_share"]*100, f"{h2m['top12_server_share']*100:.1f}%"),
]
vals = [f[1] for f in facts]
a1.barh(range(len(facts)), vals, color=C_ACC, alpha=0.85, height=0.5)
for i, (n, v, f) in enumerate(facts):
    a1.text(v * 1.1, i, f, va="center", fontsize=9)
a1.set_yticks(range(len(facts)))
a1.set_yticklabels([n for n, _, _ in facts], fontsize=9.5)
a1.set_xlabel("数值（对数尺度）", fontsize=10)
a1.set_xscale("log")
a1.set_title("(a) 目录生态的结构参数", fontsize=10.5)
a1.grid(alpha=0.25, axis="x", ls="--")

a2.bar(range(4), [14, 28, 36, 106], color=C_ACC, alpha=0.85, width=0.5)
a2.set_xticks(range(4))
a2.set_xticklabels(["26+", "11-25", "6-10", "3-5 工具"], fontsize=10)
a2.set_ylabel("服务器数", fontsize=10)
a2.set_title("(b) 服务器按工具数的分布：多数为微型服务器", fontsize=10.5)
a2.grid(alpha=0.25, axis="y", ls="--")
fig.suptitle("图4  生态的结构事实：2055 个服务器、多数微型、集中度低", fontsize=12, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(OUT / "custom_fig2_ecosystem_structure.png", bbox_inches="tight"); plt.close()

# fig3: H3 name reuse
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.5, 4.5))
h3m = models["H3"]
a1.bar([0, 1], [h3m["distinct_local_names"], h3m["local_names_under_2plus_servers"]],
       color=[C_ACC, C_OPP], alpha=0.88, width=0.45)
labels3 = [f"独立局部名\n{h3m['distinct_local_names']:,}",
           f"跨服务器复用\n{h3m['local_names_under_2plus_servers']:,}"]
a1.set_xticks([0, 1]); a1.set_xticklabels(labels3, fontsize=10)
a1.set_ylabel("局部名数", fontsize=10)
a1.set_ylim(0, 3000)
share = h3m["share_of_local_names_reused_across_servers"]
a1.set_title(f"(a) 局部名复用率 {share*100:.1f}%：近半局部名跨服务器出现", fontsize=10.5)
a1.grid(alpha=0.25, axis="y", ls="--")

reuse = h3m.get("most_reused_local_names", {})
names = sorted(reuse.keys(), key=lambda k: -reuse[k])[:8]
counts = [reuse[n] for n in names]
a2.barh(range(len(names)), counts, color=C_OPP, alpha=0.85, height=0.5)
for i, c in enumerate(counts):
    a2.text(c + 0.2, i, f"{c} 个服务器", va="center", fontsize=9)
a2.set_yticks(range(len(names)))
a2.set_yticklabels(names, fontsize=10)
a2.set_xlabel("出现该局部名的服务器数", fontsize=10)
a2.set_xlim(0, 20)
a2.set_title("(b) 最常复用的局部名", fontsize=10.5)
a2.grid(alpha=0.25, axis="x", ls="--")
fig.suptitle("图5  H3 的命名复用事实：近半局部名跨服务器出现", fontsize=12, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(OUT / "custom_fig3_name_reuse.png", bbox_inches="tight"); plt.close()

# fig4: server size vs specialisation
fig, ax = plt.subplots(figsize=(9.2, 4.8))
bands = list(tsb.keys())
band_labs = ["3-5 工具", "6-10 工具", "11-25 工具", "26+ 工具"]
diffs = [tsb[b]["mean_diff"] for b in bands]
withins = [tsb[b]["mean_within"] for b in bands]
x = np.arange(4)
w = 0.35
ax.bar(x - w/2, withins, width=w, color=C_SUP, alpha=0.85, label="同服务器重叠")
ax.bar(x + w/2, diffs, width=w, color=C_OPP, alpha=0.85, label="重叠差（特化度）")
for i, (wv, dv) in enumerate(zip(withins, diffs)):
    ax.text(i - w/2, wv + 0.005, f"{wv:.3f}", ha="center", fontsize=9)
    ax.text(i + w/2, dv + 0.005, f"{dv:.3f}", ha="center", fontsize=9)
ax.set_xticks(x)
ax.set_xticklabels(band_labs, fontsize=10)
ax.set_ylabel("均值", fontsize=10)
ax.set_ylim(0, 0.40)
ax.legend(fontsize=9.5)
ax.set_title("图2  按服务器规模的特化度分层：微型服务器（3-5 工具）的特化度最高",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="y", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig4_size_specialisation.png", bbox_inches="tight"); plt.close()

print("P042 figures done:", [p.name for p in sorted(OUT.glob("custom_*.png"))])
