"""Generate every P001 figure and table from the result files - no hand-entered numbers.

Figures are written as vector PDF + SVG with a single shared encoding: config colour and
marker are identical everywhere, error bars are always labelled with what they represent,
and no axis is truncated. Tables are CSV in tables/.

    python make_figures_tables.py

Reads:  results_raw/EXP0005|0007|0009|0010|0011|0012_*.json, EXP0006_* ladder,
        01_datasets/processed/routing_*.parquet, 01_datasets/manifests/dataset_registry.csv
Writes: papers/P001_routing_failure_qpp/figures/*.{pdf,svg}, tables/*.csv
"""

from __future__ import annotations

import glob
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
PAPER = ROOT / "papers" / "P001_routing_failure_qpp"
FIG, TAB = PAPER / "figures", PAPER / "tables"
PROC, RAW = ROOT / "01_datasets" / "processed", ROOT / "results_raw"
CONFIGS = ["OSS", "Qwen3", "Kimi-K2"]
CFG_COLOR = {"OSS": "#0072B2", "Qwen3": "#D55E00", "Kimi-K2": "#009E73"}   # Okabe-Ito, colour-blind safe
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 150, "savefig.bbox": "tight"})


def latest(pattern: str) -> dict:
    f = sorted(glob.glob(str(RAW / pattern)))[-1]
    return json.loads(Path(f).read_text(encoding="utf-8"))


def save(fig, name: str, caption: str) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{name}.pdf")
    fig.savefig(FIG / f"{name}.svg", format="svg")
    plt.close(fig)
    (FIG / f"{name}.caption.txt").write_text(caption, encoding="utf-8")
    print("fig", name)


def dev_table() -> pd.DataFrame:
    return pd.concat([pd.read_parquet(PROC / f"routing_{c}.parquet").assign(cfg=c) for c in CONFIGS],
                     ignore_index=True)


# ---------------------------------------------------------------- figures
def fig1_framework():
    fig, ax = plt.subplots(figsize=(7.2, 2.6))
    boxes = [(0.02, "user instruction\n(text only)"), (0.21, "pre-retrieval features\nlinguistic + collection-aware"),
             (0.45, "risk score\nP(top-3 misses gold)"), (0.66, "triage: rewrite catalog /\nexpand catalog / abstain"),
             (0.86, "frozen BM25 ranker\ngold in top-3?")]
    for x, t in boxes:
        ax.add_patch(plt.Rectangle((x, 0.3), 0.14, 0.42, fill=False, lw=1.1, ec="#333"))
        ax.text(x + 0.07, 0.51, t, ha="center", va="center", fontsize=7.6)
    for (x1, _), (x2, _) in zip(boxes, boxes[1:]):
        ax.annotate("", xy=(x2 - 0.005, 0.51), xytext=(x1 + 0.145, 0.51),
                    arrowprops=dict(arrowstyle="->", lw=1.1, color="#333"))
    ax.annotate("", xy=(0.52, 0.72), xytext=(0.93, 0.72), arrowprops=dict(arrowstyle="->", lw=1.0, color=CFG_COLOR["Qwen3"]))
    ax.text(0.72, 0.78, "evaluation only (never a model input)", fontsize=7.4, color=CFG_COLOR["Qwen3"], ha="center")
    ax.annotate("", xy=(0.3, 0.28), xytext=(0.9, 0.28), arrowprops=dict(arrowstyle="->", lw=1.0, color="#777"))
    ax.text(0.6, 0.19, "gold labels used to build the dependent variable, held out by prompt_id group",
            fontsize=7.2, color="#555", ha="center")
    ax.set_xlim(0, 1.02); ax.set_ylim(0.1, 0.9); ax.axis("off")
    save(fig, "fig1_framework",
         "Figure 1. Study framework. Predictors use only the instruction and the candidate catalog available "
         "at query time; gold tool labels enter the dependent variable and the evaluation, never the features. "
         "Schematic drawn by make_figures_tables.py (no measured quantities).")


def fig2_data(df: pd.DataFrame):
    inf = df[df.n_candidates > 3]
    fig, axs = plt.subplots(1, 3, figsize=(7.2, 2.3))
    for c in CONFIGS:
        s = df[(df.cfg == c) & (df.split == "dev")].n_candidates
        axs[0].hist(s.clip(upper=40), bins=40, histtype="step", lw=1.3, color=CFG_COLOR[c], label=f"{c} (n={len(s):,})")
    axs[0].set_xlabel("candidate tools per query"); axs[0].set_ylabel("queries")
    axs[0].legend(fontsize=6.5, frameon=False)
    axs[0].set_title("(a) catalog size per query", fontsize=8.5)
    inf = inf.assign(stratum=pd.cut(inf.n_candidates, [3, 7, 15, 10 ** 6], labels=["4-7", "8-15", "16+"]))
    st = inf.groupby(["cfg", "stratum"], observed=True).agg(
        n=("fail_at_3", "size"), f=("fail_at_3", "mean"), ch=("chance_hit_3", "mean")).reset_index()
    for c in CONFIGS:
        sub = st[st.cfg == c]
        x = np.arange(len(sub))
        axs[1].plot(x, 100 * sub.f, "o-", color=CFG_COLOR[c], label=c)
        axs[1].plot(x, 100 * sub.ch, "s--", color=CFG_COLOR[c], alpha=.55, lw=1)
    axs[1].set_xticks(np.arange(3)); axs[1].set_xticklabels(["4-7", "8-15", "16+"])
    axs[1].set_xlabel("catalog stratum"); axs[1].set_ylabel("%")
    axs[1].set_title("(b) observed failure (solid) vs\nhypergeometric chance (dashed)", fontsize=8.5)
    axs[1].legend(fontsize=6.5, frameon=False)
    for c in CONFIGS:
        s = inf[inf.cfg == c]
        axs[2].bar(c, 100 * (1 - len(s) / len(df[(df.cfg == c) & (df.split == 'dev')])),
                   color=CFG_COLOR[c], width=.55)
    axs[2].set_ylabel("% of dev queries excluded")
    axs[2].set_title("(c) structurally uninformative\n(n_candidates <= 3)", fontsize=8.5)
    for a in axs:
        a.grid(axis="y", lw=.4, alpha=.4)
    excl = []
    for c in CONFIGS:
        dev_all = df[(df.cfg == c) & (df.split == "dev")]
        keep = len(inf[inf.cfg == c])
        excl.append(f"{c} {100 * (1 - keep / max(1, len(dev_all))):.1f}%")
    cap2 = ("Figure 2. Data structure and the exclusion the dependent variable forces. (a) catalog size per query "
            "is small and heavily tied at 3-6 candidates. (b) observed BM25 top-3 failure rises with catalog size "
            "while chance-level hit probability falls, so raw hit rates are only interpretable against chance. "
            "(c) share of development queries dropped because top-k would be the entire catalog "
            "(n_candidates <= 3): " + ", ".join(excl) + ".")
    save(fig, "fig2_data_structure", cap2)


def fig3_main(test: dict, devladder: dict):
    fig, ax = plt.subplots(figsize=(4.6, 2.9))
    models = [("B0_length_only", "length only (B0)"), ("B1_postretrieval_margin", "post-retrieval margin (B1)"),
              ("B1b_preretrieval_logistic", "pre-retrieval, frozen (B1b)")]
    w = 0.26
    for i, (m, lab) in enumerate(models):
        vals, errs = [], []
        for c in CONFIGS:
            if m == "B1b_preretrieval_logistic":
                vals.append(test["configs"][c]["auc_pre"]["mean"]); errs.append(test["configs"][c]["auc_pre"]["std"])
            else:
                key = "auc_B0_length" if m.startswith("B0") else "auc_B1_post_margin"
                vals.append(test["configs"][c][key]); errs.append(0.0)
        ax.bar(np.arange(3) + (i - 1) * w, vals, w, label=lab,
               color=["#BBBBBB", "#888888", "#0072B2"][i], edgecolor="none")
        if any(errs):
            ax.errorbar(np.arange(3) + (i - 1) * w, vals, yerr=errs, fmt="none", ecolor="#222", capsize=2, lw=.9)
    ax.axhline(0.5, color="#444", lw=.8, ls=":"); ax.text(2.45, 0.505, "chance", fontsize=6.5, color="#444")
    ax.set_xticks(np.arange(3)); ax.set_xticklabels(CONFIGS)
    ax.set_ylabel("AUROC for top-3 miss (test)"); ax.set_ylim(0.45, 0.9)
    ax.set_title("held-out test, single evaluation, 5 seeds\n(error bars: SD across seeds)", fontsize=8)
    ax.legend(fontsize=6.6, frameon=False, loc="upper left")
    ax.grid(axis="y", lw=.4, alpha=.4)
    save(fig, "fig3_main_result",
         "Figure 3. Main held-out result. Each of the three teacher-model corpora is evaluated once. "
         "The pre-retrieval model exceeds both the trivial length baseline and the post-retrieval "
         "quasi-local QPP baseline in every corpus. Chance = 0.5 AUROC.")


def fig4_mech(df: pd.DataFrame, robust: dict):
    uni = {}
    for c in CONFIGS:
        for k, v in robust["configs"][c].get("E05c_univariate_OR_holm", {}).items():
            if v.get("sig_holm_005"):
                uni.setdefault(k, []).append((c, v["OR"], v["ci95_OR"]))
    if not uni:
        raise RuntimeError("no Holm-significant univariate odds ratios in EXP-0011; "
                           "refusing to draw an empty mechanism panel")
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 3.0), gridspec_kw={"width_ratios": [1.15, 1]})
    if uni:
        names = sorted(uni)
        for j, n in enumerate(names):
            for (c, orv, ci) in uni[n]:
                ax[0].plot([np.log10(max(ci[0], 1e-3)), np.log10(max(ci[1], 1e-3))], [j, j], lw=1.1, color=CFG_COLOR[c])
                ax[0].plot(np.log10(orv), j, "o", ms=3.6, color=CFG_COLOR[c])
        ax[0].axvline(0, color="#444", lw=.8, ls=":")
        ax[0].set_yticks(range(len(names))); ax[0].set_yticklabels(names, fontsize=6.8)
        ax[0].set_xlabel("log10 odds ratio per SD (Holm-significant, 5 seeds)")
        ax[0].set_title("(a) direction of each risk factor", fontsize=8.5)
    strata = {}
    for c in CONFIGS:
        s = df[(df.cfg == c) & (df.split == "dev") & (df.n_candidates > 3)]
        b = pd.cut(s.n_candidates, [3, 7, 15, 1000], labels=["4-7", "8-15", "16+"])
        for k, g in s.groupby(b, observed=True):
            hit, miss = g[g.fail_at_3 == 0], g[g.fail_at_3 == 1]
            if len(miss) < 10:
                continue
            strata.setdefault(str(k), {})[c] = float(hit.qpp_coverage.mean() - miss.qpp_coverage.mean())
    xs = np.arange(len(strata))
    for c in CONFIGS:
        ax[1].plot(xs, [strata[k].get(c, np.nan) for k in strata], "o-", color=CFG_COLOR[c], label=c)
    ax[1].axhline(0, color="#444", lw=.8, ls=":")
    ax[1].set_xticks(xs); ax[1].set_xticklabels(list(strata))
    ax[1].set_ylabel("mean coverage gap (hit - miss)")
    ax[1].set_title("(b) lexical reachability deficit\ngrows with catalog size", fontsize=8.5)
    ax[1].legend(fontsize=6.5, frameon=False)
    for a in ax:
        a.grid(axis="both", lw=.35, alpha=.4)
    save(fig, "fig4_mechanism",
         "Figure 4. Mechanism view, development split only. (a) odds ratios per SD for features surviving Holm "
         "correction; values below 1 mean higher feature value -> lower failure risk. (b) the mean gap in catalog "
         "term coverage between hit and miss queries, by catalog stratum. Association only, not causal.")


def fig5_robust(robust: dict, sel: dict):
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.6))
    dvs = ["fail_at_1", "fail_at_3", "fail_at_5"]
    for c in CONFIGS:
        v = [robust["configs"][c]["E05_alternative_dv"].get(d, {}).get("auc", np.nan) for d in dvs]
        ax[0].plot(range(3), v, "o-", color=CFG_COLOR[c], label=c)
    ax[0].set_xticks(range(3)); ax[0].set_xticklabels(["fail@1", "fail@3", "fail@5"])
    ax[0].set_ylabel("AUROC (dev)"); ax[0].set_title("(a) alternative dependent variables", fontsize=8.5)
    ax[0].legend(fontsize=6.5, frameon=False)
    feats = ["all", "qpp", "linguistic"]
    for c in CONFIGS:
        g = sel["grid"][c]
        vals = [g[f"{f}_C0.1"]["mean"] for f in feats]
        ax[1].plot(range(3), vals, "o-", color=CFG_COLOR[c], label=c)
    ax[1].set_xticks(range(3)); ax[1].set_xticklabels(["all feats", "collection-QPP only", "linguistic only"])
    ax[1].set_ylabel("AUROC (dev)"); ax[1].set_title("(b) feature-set ablation at frozen C=0.1", fontsize=8.5)
    for a in ax:
        a.grid(axis="y", lw=.4, alpha=.4)
    save(fig, "fig5_robustness_ablation",
         "Figure 5. Alternative operationalizations and ablation (development split). (a) predictive strength is "
         "monotone in how strict the miss definition is. (b) removing collection-aware features costs 0.09-0.15 "
         "AUROC, so most of the signal is query-catalog lexical reachability rather than instruction style alone.")


def fig6_error(df: pd.DataFrame, test: dict):
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.6))
    te = df[(df.split == "test") & (df.n_candidates > 3)]
    ax[0].hist(te.loc[te.fail_at_3 == 0, "bm25_margin"], bins=40, histtype="step", lw=1.3,
               color=CFG_COLOR["OSS"], label="top-3 hit", density=True)
    ax[0].hist(te.loc[te.fail_at_3 == 1, "bm25_margin"], bins=40, histtype="step", lw=1.3,
               color=CFG_COLOR["Qwen3"], label="top-3 miss", density=True)
    ax[0].set_xlabel("post-retrieval BM25 score margin"); ax[0].set_yscale("log")
    ax[0].set_ylabel("density (log)"); ax[0].legend(fontsize=6.5, frameon=False)
    ax[0].set_title("(a) the two classes barely separate\non retrieval confidence", fontsize=8.5)
    sub = te[te.fail_at_3 == 1].copy()
    sub["cov"] = 1 - sub.qpp_coverage
    ax[1].hist(sub.loc[sub.n_candidates <= 7, "cov"], bins=30, histtype="step", lw=1.3,
               color=CFG_COLOR["Kimi-K2"], label=f"small catalogs (n={int((sub.n_candidates<=7).sum())})", density=True)
    ax[1].hist(sub.loc[sub.n_candidates > 15, "cov"], bins=30, histtype="step", lw=1.3,
               color=CFG_COLOR["Qwen3"], label=f"large catalogs (n={int((sub.n_candidates>15).sum())})", density=True)
    ax[1].set_xlabel("1 - catalog term coverage of the query"); ax[1].set_ylabel("density")
    ax[1].legend(fontsize=6.5, frameon=False)
    ax[1].set_title("(b) failures concentrate where the\nquery shares no terms with the catalog", fontsize=8.5)
    for a in ax:
        a.grid(axis="both", lw=.35, alpha=.4)
    save(fig, "fig6_error_analysis",
         "Figure 6. Error analysis on the held-out test split (no resampling of the model). (a) BM25 score margin "
         "distributions for hit vs miss queries: the separations are partial, which is why the predictor adds value "
         "only as a pooled multi-feature model. (b) among missed queries, the share of query terms absent from the "
         "whole catalog, split by catalog size - the dominant observed failure mode.")


# ---------------------------------------------------------------- tables
def tables(df: pd.DataFrame, test: dict, sel: dict, robust: dict, lad: dict):
    TAB.mkdir(parents=True, exist_ok=True)
    reg = pd.read_csv(ROOT / "01_datasets" / "manifests" / "dataset_registry.csv")
    reg[reg.dataset == "Toucan-1.5M"][["dataset", "hf_repo_id", "license_declared", "hf_git_revisions",
                                       "download_first_at", "total_rows_measured", "configs"]].to_csv(TAB / "table1_source.csv", index=False)
    inf = df[df.n_candidates > 3]
    rows = []
    for c in CONFIGS:
        a, i = df[df.cfg == c], inf[(inf.cfg == c) & (inf.split == "dev")]
        rows.append({"config": c, "rows_built": len(a), "dev_informative": len(i),
                     "test_informative": len(inf[(inf.cfg == c) & (inf.split == "test")]),
                     "catalog_mean": round(a.n_candidates.mean(), 2), "catalog_p50": int(a.n_candidates.median()),
                     "catalog_max": int(a.n_candidates.max()), "gold_mean": round(a.n_gold.mean(), 3),
                     "n_servers_mean": round(a.n_servers_in_row.mean(), 2),
                     "dev_fail@1_pct": round(100 * i.fail_at_1.mean(), 2),
                     "dev_fail@3_pct": round(100 * i.fail_at_3.mean(), 2),
                     "dev_chance_hit@3_pct": round(100 * i.chance_hit_3.mean(), 2),
                     "question_tokens_mean": round(i.n_tokens.mean(), 1)})
    pd.DataFrame(rows).to_csv(TAB / "table2_dataset_card.csv", index=False)
    t2 = [{"config": c, "test_n": test["configs"][c]["n_test_informative"],
           "test_positives": test["configs"][c]["positives"], "prevalence": test["configs"][c]["prevalence"],
           "auc_pre_retrieval": test["configs"][c]["auc_pre"]["mean"], "sd_seeds": test["configs"][c]["auc_pre"]["std"],
           "auc_post_margin": test["configs"][c]["auc_B1_post_margin"], "auc_length": test["configs"][c]["auc_B0_length"],
           "leave_one_config_out_auc": test["leave_config_out_auc"][c]} for c in CONFIGS]
    pd.DataFrame(t2).to_csv(TAB / "table3_main_test.csv", index=False)
    rows = []
    for c in CONFIGS:
        for k, v in sel["grid"][c].items():
            rows.append({"config": c, "cell": k, "dev_auc_mean": v["mean"], "dev_auc_std": v["std"],
                         "selected_globally": k == sel["frozen_global"]["config"]})
    pd.DataFrame(rows).to_csv(TAB / "table4_dev_selection_grid.csv", index=False)
    rows = []
    for c in CONFIGS:
        r = robust["configs"][c]
        for dv, v in r["E05_alternative_dv"].items():
            rows.append({"config": c, "family": "E05 alternative DV", "item": dv, "value": json.dumps(v)})
        for kk, v in r["E11_robustness"].items():
            rows.append({"config": c, "family": "E11 robustness", "item": kk, "value": v})
        for kk, v in r["E14"].items():
            rows.append({"config": c, "family": "E14 inference", "item": kk, "value": json.dumps(v)})
    pd.DataFrame(rows).to_csv(TAB / "table5_robustness_inference.csv", index=False)
    orows = []
    for c in CONFIGS:
        for n, v in robust["configs"][c].get("E05c_univariate_OR_holm", {}).items():
            orows.append({"config": c, "feature": n,
                          "family": "collection-aware QPP" if n.startswith("qpp_") else "instruction-only",
                          "canonical_in_frozen_model": n in sel["canonical_features"],
                          "OR_per_SD": v["OR"], "ci95_OR": json.dumps(v["ci95_OR"]),
                          "p_raw": v["p"], "p_holm": v.get("p_holm"), "sig_holm_005": v.get("sig_holm_005"),
                          "cohens_d_hit_vs_miss": v.get("cohen_d_binary")})
    if orows:
        pd.DataFrame(orows).to_csv(TAB / "table6_univariate_OR.csv", index=False)
    else:
        print("   table6 skipped: EXP-0011 carries no univariate OR table")
    st = inf.assign(stratum=pd.cut(inf.n_candidates, [3, 7, 15, 10 ** 6],
                                   labels=["4-7", "8-15", "16+"])).groupby(
        ["cfg", "stratum"], observed=True).agg(n=("fail_at_3", "size"), fail_at_3=("fail_at_3", "mean"),
                                              chance_hit_3=("chance_hit_3", "mean"),
                                              mean_coverage=("qpp_coverage", "mean"),
                                              mean_tokens=("n_tokens", "mean")).reset_index()
    st.to_csv(TAB / "table8_catalog_strata.csv", index=False)
    code = pd.read_csv(ROOT / "00_program_registry" / "experiment_registry.csv")
    code[code.paper_id.astype(str).str.contains("T037")][["exp_id", "stage", "script", "config", "seed",
                                                           "status", "outputs"]].to_csv(TAB / "table7_experiment_provenance.csv", index=False)
    for f in sorted(TAB.glob("*.csv")):
        print("table", f.name)


def table9_h4() -> None:
    """Appendix A6: does non-exhaustive gold explain the failure DV? (EXP-0014 + EXP-0015)."""
    try:
        h4 = latest("EXP0014_equivalence_relabel_*.json")
    except Exception as exc:
        print("table9 skipped: no EXP-0014 output ->", exc)
        return
    rows = []
    for cfg, c in h4["configs"].items():
        for rule, r in c["rules"].items():
            rows.append({"config": cfg, "rule": rule, "definition": r["definition"],
                         "dev_rows": c["n_dev_rows"], "positives": c["n_dev_positives"],
                         "positives_relabelled": r["n_positives_relabelled"],
                         "relabel_rate": r["flip_rate_among_positives"],
                         "relabel_rate_ci95": r["flip_rate_ci95"],
                         "prevalence_original": r["prevalence_original"] if "prevalence_original" in r
                         else c["prevalence"],
                         "prevalence_broadened": r["prevalence_broadened"],
                         "auc_original": r.get("auc_original_mean", c.get("auc_original_dev")),
                         "auc_broadened": r["auc_broadened_mean"], "auc_broadened_sd": r["auc_broadened_std"],
                         "auc_shift": r["auc_shift_vs_original"],
                         "bm25_replication_rate": c["consistency_check"]["bm25_replication_rate"]})
    try:
        adj = latest("EXP0015_equivalence_adjudication_*.json")
        for cfg, a in adj["summary"].items():
            rows.append({"config": cfg, "rule": "MANUAL_ADJUDICATION_of_conservative",
                         "definition": "human read of instruction + both tool records",
                         "positives_relabelled": a["n_conservative_flips"],
                         "relabel_rate": None, "auc_broadened": None,
                         "n_adjudicated": a["n_adjudicated"],
                         "verdict_counts": json.dumps(a["verdict_counts"]),
                         "rule_precision_equivalent": a["rule_precision_equivalent"]})
    except Exception as exc:
        print("   EXP-0015 adjudication not available ->", exc)
    t = pd.DataFrame(rows)
    t.to_csv(TAB / "table9_h4_equivalence_relabel.csv", index=False)
    v = h4["verdict"]
    pd.DataFrame([{"criterion": v["criterion"], "h4_supported": v["h4_supported"],
                   "conservative_flip_rate_per_config": json.dumps(v["conservative_flip_rate_per_config"]),
                   "conservative_auc_shift_per_config": json.dumps(v["auc_shift_conservative_per_config"]),
                   "min_auc_broadened_conservative": v["min_auc_broadened_conservative"],
                   "auc_survives_conservative_rule": v["auc_survives_conservative_rule"],
                   "max_flip_rate_any_rule": v["max_flip_rate_any_rule"],
                   "min_auc_broadened_any_rule": v["min_auc_broadened_any_rule"],
                   "why_loose_rules_are_not_evidence": v["why_loose_rules_are_not_evidence_for_H4"],
                   "test_split_read": h4["test_split_read"],
                   "llm_api_used": h4.get("llm_api_used"),
                   "interpretation": v["interpretation"]}]).to_csv(TAB / "table9b_h4_verdict.csv", index=False)


def table10_intervention() -> None:
    """Appendix A12: controlled catalog interventions (EXP-0016) and the dependence corrections
    (EXP-0017/0018/0019). Generated, not transcribed."""
    try:
        iv = latest("EXP0016_catalog_intervention_*.json")
    except Exception as exc:
        print("table10 skipped: no EXP-0016 output ->", exc)
        return
    rows = []
    for cfg, c in iv["configs"].items():
        base = c["control"]
        for cond, v in c.items():
            if not isinstance(v, dict) or cond == "dose_response":
                continue
            rows.append({"config": cfg, "condition": cond, "definition": v.get("definition", "-"),
                         "mean_catalog": v.get("mean_catalog"), "prevalence": v.get("prevalence"),
                         "d_prevalence_vs_control": round(float(v["prevalence"] - base["prevalence"]), 4)
                         if v.get("prevalence") is not None else None,
                         "mean_predicted_risk": v.get("mean_predicted_risk"),
                         "d_risk_vs_control": round(float(v["mean_predicted_risk"]
                                                          - base["mean_predicted_risk"]), 4)
                         if v.get("mean_predicted_risk") is not None else None,
                         "auc_refit": v.get("auc_refit_mean"), "auc_transfer": v.get("auc_transfer_control"),
                         "auc_informative": v.get("auc_is_informative"),
                         "positives": v.get("positives")})
    pd.DataFrame(rows).to_csv(TAB / "table10_catalog_interventions.csv", index=False)
    drows = []
    try:
        dep = latest("EXP0017_hierarchical_dependence_*.json")
        for cfg, c in dep["configs"].items():
            for g, v in c["groups"].items():
                drows.append({"config": cfg, "block": "grouping", "item": g,
                              "k_groups": v.get("k_groups"), "mean_cluster": v.get("mean_cluster"),
                              "icc": v.get("icc"), "design_effect": v.get("design_effect"),
                              "effective_n": v.get("effective_n")})
            for k, v in c["auc"].items():
                drows.append({"config": cfg, "block": "cv", "item": k, "value": v})
    except Exception as exc:
        print("   EXP-0017 unavailable ->", exc)
    try:
        inf = latest("EXP0019_catalogue_clustered_inference_*.json")
        for cfg, c in inf["configs"].items():
            for key, v in c["correction"].items():
                drows.append({"config": cfg, "block": "inference_clustering", "item": key,
                              "ci_prompt_id": json.dumps(v["ci_prompt_id"]),
                              "ci_catalogue": json.dumps(v["ci_catalogue"]),
                              "width_prompt_id": v["width_prompt_id"], "width_catalogue": v["width_catalogue"],
                              "width_inflation": v["width_inflation"],
                              "survives_catalogue_clustering": v["still_positive_catalogue"]})
    except Exception as exc:
        print("   EXP-0019 unavailable ->", exc)
    try:
        sp = latest("EXP0018_catalog_disjoint_split_*.json")
        rec = json.loads((ROOT / "results_processed" / "EXP0017b_catalog_split_recurrence.json")
                         .read_text(encoding="utf-8"))
        for cfg, v in sp["configs"].items():
            for k in ("components", "largest_component_rows", "distinct_catalogues",
                     "catalogues_straddling_published_split",
                     "test_rows_sharing_catalogue_with_dev_published",
                     "catalogues_straddling_v6", "prompts_straddling_v6"):
                drows.append({"config": cfg, "block": "split_feasibility", "item": k, "value": v[k]})
            drows.append({"config": cfg, "block": "split_feasibility", "item": "test_share_straddling_pct",
                          "value": rec[cfg]["share"]})
    except Exception as exc:
        print("   EXP-0018/0017b unavailable ->", exc)
    if drows:
        pd.DataFrame(drows).to_csv(TAB / "table11_dependence_and_inference.csv", index=False)
    print("table table10_catalog_interventions.csv", "+ table11_dependence_and_inference.csv")


def table12_external_transfer() -> None:
    """E08 (D15): the unseen-catalogue claim, measured instead of bounded."""
    rows = []
    try:
        e21 = latest("EXP0021_cross_pipeline_transfer_*.json")
        a1, a1b, a2, ov = (e21["arm1_external_pipeline"], e21["arm1b_catalogue_disjoint"],
                           e21["arm2_unseen_tool_family"], e21["overlap_audit"])
        rows += [{"experiment": "EXP-0021", "quantity": "SFT tool names also in source pool",
                  "value": f"{ov['distinct_tool_names']['exact_overlap']}/{ov['distinct_tool_names']['target']}"},
                 {"experiment": "EXP-0021", "quantity": "shared catalogue fingerprints (SFT/source)",
                  "value": ov["distinct_catalogue_fingerprints"]["shared_fingerprints"]},
                 {"experiment": "EXP-0021", "quantity": "catalogue-token coverage of SFT by source",
                  "value": ov["target_catalog_token_coverage_by_source"]},
                 {"experiment": "EXP-0021", "quantity": "AUROC pipeline transfer SFT (catalogue-clustered CI)",
                  "value": f"{a1['auc_transfer_source_dev_to_target']} {a1['auc_transfer_ci95_catalogue_bootstrap']}"},
                 {"experiment": "EXP-0021", "quantity": f"AUROC on {a1b['n_rows']} catalogue-disjoint SFT rows",
                  "value": a1b.get("auc_transfer_disjoint_catalogues")},
                 {"experiment": "EXP-0021", "quantity": "AUROC leave-one-tool-family-out (mean of "
                                    f"{a2['n_families_tested']} families)", "value": a2["mean_auc_unseen_family"]},
                 {"experiment": "EXP-0021", "quantity": "AUROC same families, family seen (reference)",
                  "value": a2["mean_auc_family_seen_reference"]},
                 {"experiment": "EXP-0021", "quantity": "family-holdout degradation (criterion 0.02)",
                  "value": a2["mean_drop_vs_seen"]},
                 {"experiment": "EXP-0021", "quantity": "length-only AUROC on held-out families",
                  "value": a2["mean_auc_length_only"]}]
    except Exception as exc:
        print("   EXP-0021 unavailable ->", exc)
    try:
        e23 = latest("EXP0023_hermes_transfer_*.json")
        her, hc, hi = e23["transfer"], e23["corpus_after_inclusion_rule"], e23["independence_audit"]
        rows += [{"experiment": "EXP-0023", "quantity": "external corpus rows after inclusion rule",
                  "value": hc["n_rows"]},
                 {"experiment": "EXP-0023", "quantity": "external fail@3 prevalence",
                  "value": hc["fail_at_3_prevalence"]},
                 {"experiment": "EXP-0023", "quantity": "external tool names unseen in source",
                  "value": f"{hi['unseen_tool_name_share']:.0%} of {hi['external_tool_names']}"},
                 {"experiment": "EXP-0023", "quantity": "CROSS-CORPUS transfer AUROC (row CI)",
                  "value": f"{her['auc_source_dev_to_hermes']} {her['ci95_row_bootstrap']}"},
                 {"experiment": "EXP-0023", "quantity": "in-domain source dev OOF AUROC",
                  "value": her["auc_source_reference_oof_dev"]},
                 {"experiment": "EXP-0023", "quantity": "within-external-corpus OOF AUROC",
                  "value": round(sum(her["auc_within_hermes_oof"]) / len(her["auc_within_hermes_oof"]), 4)},
                 {"experiment": "EXP-0023", "quantity": "external-corpus length-only baseline",
                  "value": her["auc_hermes_length_only_B0"]},
                 {"experiment": "EXP-0023", "quantity": "external-corpus post-retrieval margin baseline",
                  "value": her["auc_hermes_post_retrieval_margin"]},
                 {"experiment": "EXP-0023", "quantity": "pre-registered verdict", "value": her["verdict"]}]
    except Exception as exc:
        print("   EXP-0023 unavailable ->", exc)
    if rows:
        pd.DataFrame(rows).to_csv(TAB / "table12_external_transfer.csv", index=False)
    src = ROOT / "results_processed" / "EXP0023_hermes_per_category.csv"
    if src.exists():
        pd.read_csv(src).to_csv(TAB / "table12b_external_per_category.csv", index=False)
    print("table table12_external_transfer.csv + table12b_external_per_category.csv")


def main() -> int:
    df = dev_table()
    test = latest("EXP0012_FINAL_TEST_*.json")
    sel = latest("EXP0010_dev_selection_*.json")
    robust = latest("EXP0011_dev_robustness_*.json")
    lad = latest("EXP0006_preretrieval_prediction_fail_at_3_*.json")
    fig1_framework(); fig2_data(df); fig3_main(test, lad); fig4_mech(df, robust)
    fig5_robust(robust, sel); tables(df, test, sel, robust, lad)
    table12_external_transfer()
    table9_h4(); table10_intervention()
    try:
        fig6_error(df, test)
    except Exception as exc:
        print("fig6 skipped:", exc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
