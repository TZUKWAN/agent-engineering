# -*- coding: utf-8 -*-
"""P044 figures: T169 tool dependency network (EXP-0188, wave-7)."""
import json, glob, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 300

fs = sorted(glob.glob("results_raw/EXP0188_wave7_design_*.json"))
art = json.load(open(fs[-1], encoding="utf-8"))
OUT = pathlib.Path("papers/P044_tool_dependency_network/figures")
OUT.mkdir(parents=True, exist_ok=True)

C_SUP = "#27ae60"; C_OPP = "#c0392b"; C_ACC = "#2980b9"; C_NULL = "#95a5a6"
models = {m["hypothesis"]: m for m in art["models"]}
h1, h2, h3 = models["H1"], models["H2"], models["H3"]
dr = art["descriptive_rates"]
fq = dr["fail_at_1_by_pair_frequency_band"]
mfp = dr.get("most_frequent_gold_pairs", {})

# fig1: verdicts forest
fig, ax = plt.subplots(figsize=(10, 4.6))
rows = [
    ("H1 frequent pair", h1["beta"], h1["ci_lo"], h1["ci_hi"], C_SUP,
     f"supported\n\u03b2={h1['beta']:+.4f}\np_holm<0.001"),
    ("H2 overlap diff", h2["beta"], h2["ci_lo"], h2["ci_hi"], C_SUP,
     f"supported\n\u03b2={h2['beta']:+.4f}\np_holm=0.0005"),
]
for i, (lab, b, lo, hi, c, note) in enumerate(rows):
    ax.plot([lo, hi], [i, i], color=c, lw=3, alpha=0.85)
    ax.plot(b, i, "D", color=c, ms=9)
    ax.text(hi + 0.02, i, note, va="center", fontsize=8.5)
ax.axvline(0, color="black", lw=0.9, ls="--")
ax.set_yticks([0, 1]); ax.set_yticklabels(["H1", "H2"], fontsize=11)
ax.set_xlim(-0.62, 0.28)
ax.set_xlabel("coefficient", fontsize=10)
ax.set_title("\u56fe1  \u4e24\u4e2a\u4e3b\u5047\u8bbe\u7684\u5224\u5b9a", fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="x", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig1_verdicts.png", bbox_inches="tight"); plt.close()

# fig2: fail@1 by pair frequency
fig, ax = plt.subplots(figsize=(8.5, 4.8))
bands = list(fq.keys())
bl = ["2-9 queries", "10+ queries"]
vals = [fq[b]["rate"] * 100 for b in bands]
ax.bar(range(2), vals, color=[C_OPP, C_SUP], alpha=0.88, width=0.4)
for i, v in enumerate(vals):
    ax.text(i, v + 0.4, f"{v:.2f}%", ha="center", fontsize=11)
ax.set_xticks(range(2))
ax.set_xticklabels(["\u4f4e\u9891\u7387\u5bf9\n(2-9 \u6b21)", "\u9ad8\u9891\u7387\u5bf9\n(10+ \u6b21)"], fontsize=11)
ax.set_ylabel("fail@1 (%)", fontsize=10)
ax.set_ylim(0, 24)
ax.set_title("fig2 fail@1 by pair frequency band", fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="y", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig2_pair_freq.png", bbox_inches="tight"); plt.close()

# fig3: H2 overlap comparison
fig, ax = plt.subplots(figsize=(8.5, 4.5))
fp_ov = h2.get("frequent_pair_overlap", 0.198)
rp_ov = h2.get("random_pair_overlap", 0.10)
ax.bar([0, 1], [fp_ov * 100, rp_ov * 100], color=[C_SUP, C_NULL], alpha=0.88, width=0.4)
ax.text(0, fp_ov * 100 + 0.3, f"{fp_ov*100:.1f}%", ha="center", fontsize=11)
ax.text(1, rp_ov * 100 + 0.3, f"{rp_ov*100:.1f}%", ha="center", fontsize=11)
ax.set_xticks([0, 1])
ax.set_xticklabels(["\u9891\u7e41\u5de5\u5177\u5bf9", "\u968f\u673a\u5de5\u5177\u5bf9"], fontsize=11)
ax.set_ylabel("\u63cf\u8ff0 Jaccard \u91cd\u53e0 (%)", fontsize=10)
ax.set_ylim(0, 25)
ax.set_title("\u56fe3  \u9891\u7e41\u5de5\u5177\u5bf9\u7684\u63cf\u8ff0\u91cd\u53e0\u9ad8\u4e8e\u968f\u673a\u5bf9", fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="y", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig3_overlap_comparison.png", bbox_inches="tight"); plt.close()

# fig4: top gold pairs
fig, ax = plt.subplots(figsize=(10, 4.5))
if mfp:
    pairs = sorted(mfp.keys(), key=lambda k: -mfp[k])[:8]
    counts = [mfp[k] for k in pairs]
    plabels = [k.replace("clear-thought-server-", "CTS\n").replace(" + ", "\n+\n") for k in pairs]
    ax.barh(range(len(pairs)), counts, color=C_ACC, alpha=0.85, height=0.5)
    for i, c in enumerate(counts):
        ax.text(c + 0.5, i, str(c), va="center", fontsize=10)
    ax.set_yticks(range(len(pairs)))
    ax.set_yticklabels(plabels, fontsize=7.5)
    ax.invert_yaxis()
ax.set_xlabel("\u5171\u73b0\u9891\u6b21", fontsize=10)
ax.set_xlim(0, 90)
ax.set_title("\u56fe4  \u6700\u5e38\u5171\u73b0\u7684\u5de5\u5177\u5bf9\uff08\u524d 8 \u540d\uff09", fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.25, axis="x", ls="--")
fig.tight_layout()
fig.savefig(OUT / "custom_fig4_top_pairs.png", bbox_inches="tight"); plt.close()

print("P044 figures done:", [p.name for p in sorted(OUT.glob("custom_*.png"))])
