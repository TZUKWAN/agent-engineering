"""EXP-0137 (T111), EXP-0138 (T114), EXP-0139 (T115), EXP-0140 (T116): the frozen wave-2 designs.

Wave 2 reads the description side of the same encounter on the same 24,000 dev queries. Every model here uses the
frozen covariate sets, the frozen bands (small .05 / medium .15 / large .30), Holm over each design's declared family
of three, and intervals clustered on `query_id` - the instance the feature is computed from, never the candidate row.

Two things are already decided by measurements made before these runs, and both are carried into the packages as
deviations rather than as quiet edits:

* T115's coverage gate fired for the entity-specificity block (present in 43.97% of candidates, below the frozen 50%
  floor), so that block is dropped from the composite - the composite is four blocks, not five;
* T112 and T117 never run at all: their kill gates fired on the premise census (EXP-0135), and a fired gate stops the
  claim instead of being renegotiated after an estimate exists.

    python 02_shared_code/package_factory/exp_wave2_designs.py [--quick]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

import numpy as np
import pandas as pd
from scipy import stats as st
from sklearn.metrics import roc_auc_score

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import wave_lib as W                                              # noqa: E402

BAND = W.BANDS["medium"]


def z(s):
    s = pd.Series(s, dtype=float)
    sd = float(s.std(ddof=0))
    return (s - float(s.mean())) / (sd if sd and np.isfinite(sd) else 1.0)


def load() -> tuple:
    Q = pd.read_csv(W.PROCES / "EXP0136_wave2_query_features.csv")
    C = pd.read_csv(W.PROCES / "EXP0136_wave2_candidate_features.csv.gz")
    W1 = pd.read_csv(W.PROCES / "EXP0119_wave1_candidate_rows.csv.gz")
    D = pd.read_csv(W.PROCES / "EXP0125_wave1_dense_scores.csv.gz")
    C = (C.merge(W1[["query_id", "cand_idx", "bm25", "rank_full", "q_doc_overlap", "n_candidates",
                      "n_gold", "desc_len"]], on=["query_id", "cand_idx"], how="left")
          .merge(D, on=["query_id", "cand_idx"], how="left"))
    C["bm25_z"] = z(C["bm25"])
    C["dense_z"] = z(C["dense"])
    C["overlap_z"] = z(C["q_doc_overlap"])
    return Q, C


def term(fit, name):
    if fit is None:
        return None
    r = fit[fit["term"] == name]
    if r.empty:
        return None
    row = r.iloc[0]
    return dict(term=name, beta=round(float(row["beta"]), 4), se=round(float(row["se"]), 4),
                ci_lo=round(float(row["ci_lo"]), 4), ci_hi=round(float(row["ci_hi"]), 4),
                p_raw=float(row["p"]), n=int(row["n"]))


def auroc(y, p):
    y = np.asarray(y, dtype=float)
    if len(np.unique(y)) < 2:
        return float("nan")
    return float(roc_auc_score(y, p))


def clustered_auroc_delta(d, xs_full, xs_part, draws=400, y="gold"):
    """AUROC(full) - AUROC(reduced) with a cluster bootstrap, both refitted inside each resample."""
    import statsmodels.api as sm

    def fit_predict(x, cols):
        X = sm.add_constant(x[cols].astype(float))
        r = sm.GLM(x[y].astype(float), X, family=sm.families.Binomial()).fit()
        return auroc(x[y], np.asarray(r.fittedvalues))
    base = fit_predict(d, xs_part)
    full = fit_predict(d, xs_full)
    def fn(x):
        try:
            return fit_predict(x, xs_full) - fit_predict(x, xs_part)
        except Exception:                                          # noqa: BLE001 - degenerate resample
            return np.nan
    bp = W.cluster_boot_ci_and_p(d, "query_id", fn, draws=draws)
    return dict(delta=round(full - base, 4), ci=bp.get("ci"), clusters=bp.get("clusters"),
                auroc_reduced=round(base, 4), auroc_full=round(full, 4),
                p_boot=bp.get("p"), draws_used=bp.get("draws_used"), error=bp.get("error"))


# ------------------------------------------------------------------------------------------------ T111 / 0137
def t111(C: pd.DataFrame) -> dict:
    d = C.dropna(subset=["bm25_z", "dense_z", "gold"]).copy()
    fam = {"similarity_only": ["bm25_z", "dense_z"],
           "plus_entity": ["bm25_z", "dense_z", "entity_agree"],
           "plus_action": ["bm25_z", "dense_z", "entity_agree", "action_agree"],
           "plus_constraint": ["bm25_z", "dense_z", "entity_agree", "action_agree", "constraint_agree"],
           "plus_object": ["bm25_z", "dense_z", "entity_agree", "action_agree", "constraint_agree", "object_agree"]}
    rows, aucs, fam_llf = [], {}, {}
    import statsmodels.api as sm
    for name, xs in fam.items():
        X = sm.add_constant(d[xs].astype(float))
        r = sm.GLM(d["gold"].astype(float), X, family=sm.families.Binomial()).fit()
        aucs[name] = auroc(d["gold"], np.asarray(r.fittedvalues))
        fam_llf[name] = float(r.llf)                             # captured here: an earlier version refitted all five
        rows.append(dict(model=name, llf=round(float(r.llf), 2), auroc=round(aucs[name], 4),
                         terms=";".join(xs)))                     # models a second time for the same number
    def lr(a, b):
        s = 2 * (fam_llf[b] - fam_llf[a])
        return float(s), float(st.chi2.sf(max(s, 0.0), 1))
    gains = {
        "H1_entity": clustered_auroc_delta(d, fam["plus_entity"], fam["similarity_only"]),
        "H2_action": clustered_auroc_delta(d, fam["plus_action"], fam["plus_entity"]),
        "H3_constraint": clustered_auroc_delta(d, fam["plus_constraint"], fam["plus_action"])}
    fits = {}
    for h, xs in (("H1", ["entity_agree", "bm25_z", "dense_z"]),
                  ("H2", ["action_agree", "entity_agree", "bm25_z", "dense_z"]),
                  ("H3", ["constraint_agree", "entity_agree", "action_agree", "bm25_z", "dense_z"])):
        f = W.glm_term(d, "gold", xs, "binomial")
        key = {"H1": "entity_agree", "H2": "action_agree", "H3": "constraint_agree"}[h]
        t = term(f, key) or {}
        t["hypothesis"] = h
        fits[h] = t
    ps = {h: float(fits[h].get("p_raw", 1.0)) for h in fits}
    adj = W.holm(ps)
    out_rows = []
    for h in ("H1", "H2", "H3"):
        t = dict(fits[h])
        t["p_holm"] = adj[h]
        g = gains[{"H1": "H1_entity", "H2": "H2_action", "H3": "H3_constraint"}[h]]
        t["delta_auroc"] = g["delta"]
        t["delta_auroc_ci"] = g["ci"]
        t["delta_auroc_p_boot"] = g.get("p_boot")        # bootstrap p for the same quantity the CI describes
        # The frozen support rule for T111 is written only about delta AUROC ("each component's incremental delta
        # AUROC >= 0.02 with CI excluding 0 and p_holm < 0.05"), so this is the pre-registered verdict and is not
        # touched after the read. The hypothesis *sentence* is directional ("raises", "adds on top"), and a negative
        # conditional coefficient is therefore a separate finding the verdict cannot express - it is recorded here
        # rather than folded into the label, so the package states both and the reader can see they differ.
        t["verdict"] = ("supported" if (g["ci"][0] or 0) > 0 and g["delta"] >= 0.02 and adj[h] < 0.05 else
                        "partial" if (g["ci"][0] or 0) > 0 else "null")
        t["beta_sign"] = "positive" if (t.get("beta") or 0) > 0 else "negative"
        t["beta_sign_matches_hypothesis_sentence"] = bool((t.get("beta") or 0) > 0)
        t["lr_vs_previous"] = None
        out_rows.append(t)
    v = W.vif(d[["entity_agree", "action_agree", "constraint_agree"]].astype(float))
    # `wave_lib.vif` returns {column: value}; a NaN means a constant column, which the gate cannot evaluate and
    # which is reported rather than read as "not collinear".
    collinear = any(np.isfinite(x) and x >= 10 for x in v.values())
    return {"models": out_rows, "auroc_ladder": rows, "gains": gains, "holm": adj, "vif": v,
            "kill_gate_vif_ge_10": {"fired": bool(collinear), "value": v,
                                    "nan_columns": [k for k, x in v.items() if not np.isfinite(x)],
                                    "consequence": "reported as three separable components" if not collinear
                                    else "single composite only: the three agreements are not separable on this corpus"},
            "amendment": "beta_sign and beta_sign_matches_hypothesis_sentence added after the first read: the frozen "
                         "delta-AUROC rule cannot express a sign reversal, and changing it now would move the goal "
                         "posts. Both quantities are reported; neither replaces the pre-registered verdict.",
            "n_rows": int(len(d)), "n_queries": int(d["query_id"].nunique())}


# ------------------------------------------------------------------------------------------------ T114 / 0138
def t114(C: pd.DataFrame) -> dict:
    d = C.dropna(subset=["prototype_centrality", "dense", "bm25"]).copy()
    d["centr_z"] = z(d["prototype_centrality"])
    d["fit_z"] = z(d["dense"])
    d["at_rank1"] = (d["rank_full"] == 1).astype(int)
    rows = []
    # H1, as frozen: centrality raises the chance of occupying rank 1 *independently of the query match*.
    f = W.glm_term(d, "at_rank1", ["centr_z", "fit_z", "bm25_z", "n_candidates"], "binomial")
    t = term(f, "centr_z") or {}
    t["hypothesis"], t["dv"] = "H1", "at_rank1"
    rows.append(t)
    # H2, as frozen: "low-prototype non-gold candidates are displaced downward relative to high-prototype ones".
    # The freeze is about non-gold candidates competing for the top slot, so the model is fitted on the non-gold
    # rows with a median-split centrality indicator. A previous version ran H2 on the `gold` outcome instead, which
    # is a different question; that model is kept below as a labelled supplementary row, not as H2.
    ng = d[d["gold"] == 0].copy()
    med = float(ng["prototype_centrality"].median())
    ng["hi"] = (ng["prototype_centrality"] > med).astype(int)
    f2 = W.glm_term(ng, "at_rank1", ["hi", "fit_z", "bm25_z", "n_candidates", "desc_len"], "binomial")
    t2 = term(f2, "hi") or {}
    t2["hypothesis"], t2["dv"], t2["frame"] = "H2", "at_rank1", "non-gold candidates only"
    rows.append(t2)
    tab = ng.groupby("hi").agg(n=("hi", "size"), at_rank1=("at_rank1", "sum"))
    orr, p_or = st.fisher_exact([[tab.loc[1, "at_rank1"], tab.loc[1, "n"] - tab.loc[1, "at_rank1"]],
                                 [tab.loc[0, "at_rank1"], tab.loc[0, "n"] - tab.loc[0, "at_rank1"]]])
    lo_, hi_, _ = W.cluster_boot(ng, "query_id", lambda x: float(x[x.hi == 1]["at_rank1"].mean()
                                                                 / max(1e-9, x[x.hi == 0]["at_rank1"].mean())),
                                 draws=600)
    # supplementary: does a candidate's own centrality predict that it is the released selection? Not one of the
    # three frozen hypotheses, so it carries no family membership and gets no Holm-adjusted p.
    fs = W.glm_term(d, "gold", ["centr_z", "fit_z", "bm25_z"], "binomial")
    sup = term(fs, "centr_z") or {}
    sup.update(hypothesis="S1_supplementary", dv="gold",
               note="not a frozen hypothesis: no Holm entry, no claim, reported so the earlier model is visible")
    # H3: the disagreement set, characterised
    d["cent_rank"] = d.groupby("query_id")["prototype_centrality"].rank(ascending=False)
    dis = d[(d["cent_rank"] == 1) != (d["rank_full"] == 1)]
    q_dis = int(dis["query_id"].nunique())
    # vectorised per-query Spearman (rank, then Pearson within the group): `groupby.apply` with a spearman call is
    # both slower over 169k rows and fragile across pandas versions
    R = d.assign(rc=d.groupby("query_id")["prototype_centrality"].rank(),
                 rd=d.groupby("query_id")["dense"].rank(),
                 ng=d.groupby("query_id")["cand_idx"].transform("size"))
    R = R[(R["ng"] > 2) & R["prototype_centrality"].notna() & R["dense"].notna()]
    cov = (R["rc"] * R["rd"]).groupby(R["query_id"]).mean()
    mr, dr_ = R.groupby("query_id")["rc"].mean(), R.groupby("query_id")["rd"].mean()
    vr, vd = R.groupby("query_id")["rc"].var(), R.groupby("query_id")["rd"].var()
    per = ((cov - mr * dr_) / (vr * vd).pow(0.5).replace(0, np.nan)).dropna()
    ps = {"H1": float(rows[0].get("p_raw", 1.0)), "H2": float(rows[1].get("p_raw", 1.0)), "H3": 1.0}
    adj = W.holm(ps)
    for i, h in ((0, "H1"), (1, "H2")):
        rows[i]["p_holm"] = adj[h]
        rows[i]["verdict"] = W.verdict(rows[i].get("beta"), rows[i].get("ci_lo"), rows[i].get("ci_hi"),
                                       rows[i]["p_holm"], BAND)
    rows.append(sup)
    rows.append(dict(term="H3_disagreement_census", hypothesis="H3", n_queries_disagreeing=q_dis,
                     disagreement_rows=int(len(dis)),
                     spearman_centrality_vs_query_fit=round(float(per.mean()), 4),
                     spearman_iqr=[round(float(per.quantile(.25)), 4), round(float(per.quantile(.75)), 4)],
                     underpowered=bool(q_dis < 200),
                     verdict=("reported descriptively, no directional claim" if q_dis < 200 else "characterised")))
    return {"models": rows, "holm": adj, "fisher_decoy_table": tab.reset_index().to_dict("records"),
            "odds_ratio": round(float(orr), 4), "p_fisher": float(p_or), "ratio_ci": [lo_, hi_],
            "family_note": "Holm is over the three frozen labels; H3 has no sampling test (a characterisation) so it "
                           "enters at p=1, which is the conservative choice and inflates neither of the tested p's.",
            "n_rows": int(len(d)), "n_queries": int(d["query_id"].nunique())}


# ------------------------------------------------------------------------------------------------ T115 / 0139
def t115(Q: pd.DataFrame) -> dict:
    d = Q.copy()
    d["reachable"] = 1 - d["fail_at_1"]
    blocks = {"length": ["gold_desc_tokens", "gold_param_n"],
              "enumeration": ["gold_enum_share"],
              "verb": ["gold_verb_coverage"],
              "agreement": ["gold_action_agree", "gold_entity_agree", "gold_constraint_agree"]}
    dropped = ["specificity"]        # dropped by the frozen coverage gate at EXP-0136 (43.97% < 50%)
    order = ["length", "agreement", "verb", "enumeration"]
    # the hierarchy is explicit: length first, then each remaining block added in the frozen order
    seq = ["length"]
    specs = {"length": blocks["length"]}
    for b in order[1:]:
        specs[b] = specs[seq[-1]] + blocks[b]
        seq.append(b)
    specs["full"] = specs[seq[-1]]
    seq = seq + ["full"]
    # which blocks are actually inside each rung - kept as data so the table label cannot drift from the model
    rungs = {"length": ["length"]}
    for i, b in enumerate(order[1:], start=1):
        rungs[b] = rungs[order[i - 1]] + [b]
    rungs["full"] = rungs[order[-1]]
    import statsmodels.api as sm
    rows, aucs, lls = [], {}, {}
    for name in seq:
        xs = specs[name]
        d2 = d.dropna(subset=xs + ["reachable", "query_id"])
        X = sm.add_constant(d2[xs].astype(float))
        r = sm.GLM(d2["reachable"].astype(float), X, family=sm.families.Binomial()).fit()
        aucs[name] = auroc(d2["reachable"], np.asarray(r.fittedvalues))
        lls[name] = float(r.llf)
        rows.append(dict(model=name, blocks="+".join(rungs[name]), k_terms=len(xs),
                         auroc=round(aucs[name], 4), llf=round(float(r.llf), 2), n=int(len(d2))))
    deltas = {}
    for i in range(1, len(seq)):
        a, b = seq[i - 1], seq[i]
        lr = 2 * (lls[b] - lls[a])
        deltas[f"{a}->{b}"] = dict(added_block=b, auroc_delta=round(aucs[b] - aucs[a], 4), lr=round(lr, 3),
                                   p=float(st.chi2.sf(max(lr, 0.0), 1)))
    # per-config weight stability of the full model
    full = blocks["length"] + [x for b in order[1:] for x in blocks[b]]
    coefs = {}
    for cfg, g in d.groupby("cfg"):
        gg = g.dropna(subset=full + ["reachable"])
        try:
            r = sm.GLM(gg["reachable"].astype(float), sm.add_constant(gg[full].astype(float)),
                       family=sm.families.Binomial()).fit()
            coefs[cfg] = {c: float(v) for c, v in r.params.items() if c != "const"}
        except Exception:                                          # noqa: BLE001 - separation in one config
            continue
    rho_pairs = []
    ks = sorted({k for v in coefs.values() for k in v})
    for a in coefs:
        for b in coefs:
            if a < b:
                va = [coefs[a].get(k, np.nan) for k in ks]
                vb = [coefs[b].get(k, np.nan) for k in ks]
                ok = [i for i in range(len(ks)) if np.isfinite(va[i]) and np.isfinite(vb[i])]
                if len(ok) > 3:
                    rho_pairs.append(round(float(st.spearmanr([va[i] for i in ok], [vb[i] for i in ok]).statistic), 4))
    # H1 is the conjunction "each block carries incremental information", so the binding p is the *largest* step p:
    # taking the smallest would let one lucky block carry a claim about all four.
    step_ps = {k: v["p"] for k, v in deltas.items()}
    h1_p = max(step_ps.values()) if step_ps else 1.0
    h2 = clustered_auroc_delta(d.dropna(subset=specs["full"] + ["reachable"]), specs["full"], blocks["length"],
                               draws=400, y="reachable")
    ps = {"H1": float(h1_p), "H2": float(h2.get("p_boot") or 1.0), "H3": 1.0}
    # H2's test is the clustered bootstrap of the composite-vs-length-only AUROC delta: the interval and the p come
    # from the same draws, p floored at 1/draws so it can never print 0.
    adj = W.holm(ps)
    h1v = ("supported" if adj["H1"] < 0.05 and all(v["p"] < 1.0 for v in deltas.values()) else
           "null" if adj["H1"] >= 0.05 else "partial")
    h2v = ("supported" if (h2["ci"][0] or 0) > 0 and h2["delta"] >= 0.02 and adj["H2"] < 0.05 else
           "partial" if (h2["ci"][0] or 0) > 0 else "null")
    h3v = ("supported" if rho_pairs and min(rho_pairs) >= 0.6 else
           "partial" if rho_pairs and min(rho_pairs) >= 0.4 else "null")
    # The ladder rows above carry no hypothesis; these three do, so the package can cite a verdict per claim instead
    # of leaving H1-H3 to be inferred from a table of AUROCs.
    hyps = [dict(kind="hypothesis", hypothesis="H1", term="binding_nested_step_" + str(
                max(step_ps, key=lambda k: step_ps[k]) if step_ps else "none"),
                p_raw=round(float(h1_p), 6), p_holm=adj["H1"], verdict=h1v,
                note="H1 is the conjunction that each block carries incremental information, so the binding step is "
                     "the largest of the four step p-values; a block whose LR statistic is <= 0 has no evidence to "
                     "contribute and its p is 1, which is what Holm then carries."),
            dict(kind="hypothesis", hypothesis="H2", term="composite_minus_length_only_auroc",
                 beta=h2["delta"], ci_lo=h2["ci"][0], ci_hi=h2["ci"][1], p_raw=h2.get("p_boot"),
                 p_holm=adj["H2"], verdict=h2v, auroc_reduced=h2["auroc_reduced"], auroc_full=h2["auroc_full"]),
            dict(kind="hypothesis", hypothesis="H3", term="min_pairwise_weight_spearman_across_configs",
                 beta=(min(rho_pairs) if rho_pairs else None), p_raw=None, p_holm=adj["H3"], verdict=h3v,
                 note="a frozen correlation threshold, not a sampling test: the threshold is 0.6 for support and "
                      "0.4 for partial, and the pairs measured are in weight_stability")]
    rows.extend(hyps)
    return {"models": rows, "hypotheses": hyps, "nested_deltas": deltas, "holm": adj, "dropped_blocks": dropped,
            "h1_binding_step": max(step_ps, key=lambda k: step_ps[k]) if step_ps else None,
            "h2_composite_vs_length_only": h2,
            "p_entries": {"H1": h1_p, "H2": ps["H2"], "H3": 1.0},
            "family_note": "H2's p is the two-sided cluster-bootstrap p of the AUROC delta against 0 (floored at "
                           "1/draws), from the same draws as its interval; H3 has no sampling distribution (it is a "
                           "correlation threshold) so it enters Holm at p=1, the conservative choice that leaves the "
                           "other two adjusted values' ranks unchanged.",
            "weight_stability": {"pairwise_spearman": rho_pairs, "min": (min(rho_pairs) if rho_pairs else None),
                                 "configs": list(coefs)},
            "h2_verdict": ("supported" if (h2["ci"][0] or 0) > 0 and h2["delta"] >= 0.02 and adj["H2"] < 0.05 else
                           "partial" if (h2["ci"][0] or 0) > 0 else "null"),
            "h3_verdict": ("supported" if rho_pairs and min(rho_pairs) >= 0.6 else
                           "partial" if rho_pairs and min(rho_pairs) >= 0.4 else "null"),
            "n_rows": int(len(d))}


# ------------------------------------------------------------------------------------------------ T116 / 0140
def t116(Q: pd.DataFrame, C: pd.DataFrame) -> dict:
    d = Q.copy()
    d["reachable"] = 1 - d["fail_at_1"]
    d["len_decile"] = pd.qcut(d["gold_desc_tokens"].rank(method="first"), 10, labels=False) + 1
    dose = d.groupby("len_decile").agg(n=("query_id", "size"), gold_desc_tokens=("gold_desc_tokens", "mean"),
                                       reachable=("reachable", "mean"), fail_at_3=("fail_at_3", "mean"),
                                       param_n=("gold_param_n", "mean")).reset_index()
    dose["reachable"] = dose["reachable"].round(4)
    lo_, hi_, k, p_gap = _gap(d)
    # "monotone then flat" is two slopes, not one: an increasing lower half and a flatter upper half. A previous
    # version wrote `monotone = abs(sum(diff)) >= 0`, which is True for every possible table and so tested nothing.
    def half_slope(sel):
        g = d[sel]
        f = W.glm_term(g.assign(x=g["len_decile"].astype(float)), "reachable", ["x"], "binomial")
        return term(f, "x") or {}
    lower, upper = half_slope(d["len_decile"] <= 5), half_slope(d["len_decile"] > 5)
    diffs = dose["reachable"].diff().dropna()
    pattern = dict(lower_half_slope_per_decile=lower.get("beta"), upper_half_slope_per_decile=upper.get("beta"),
                   non_decreasing_deciles=int((diffs >= -1e-9).sum()), decreasing_deciles=int((diffs < -1e-9).sum()),
                   spearman_decile_vs_reachability=round(float(st.spearmanr(dose["len_decile"],
                                                                           dose["reachable"]).statistic), 4))
    pattern["monotone_then_flat"] = bool((lower.get("beta") or 0) > 0 and abs(upper.get("beta") or 0)
                                         < abs(lower.get("beta") or 0) and pattern["decreasing_deciles"] <= 2)
    big = d[d["n_candidates"] >= d["n_candidates"].median()]
    small = d[d["n_candidates"] < d["n_candidates"].median()]
    def slope(fr):
        f = W.glm_term(fr.assign(t=z(fr["gold_desc_tokens"])), "reachable", ["t"], "binomial")
        return term(f, "t") or {}
    rows = [dict(stratum="all_queries", **slope(d)), dict(stratum="large_catalogue", **slope(big)),
            dict(stratum="small_catalogue", **slope(small))]
    for r in rows:
        r["dv"] = "reachable"
    # H2 as frozen ("the turning point differs between short-list and long-list catalogues") is a moderation claim,
    # so it needs an interaction term with a clustered standard error - not the arithmetic difference of two slopes,
    # which has no interval and cannot be tested.
    dd = d.assign(t=z(d["gold_desc_tokens"]), large=(d["n_candidates"] >= d["n_candidates"].median()).astype(float))
    dd["txlarge"] = dd["t"] * dd["large"]
    fi = W.glm_term(dd, "reachable", ["t", "large", "txlarge"], "binomial")
    inter = term(fi, "txlarge") or {}
    gap = float(rows[1].get("beta", 0)) - float(rows[2].get("beta", 0))
    # cost side: does a longer gold description displace more non-gold candidates? measured at candidate level
    cc = C.dropna(subset=["desc_tokens"]).copy()
    cc["displaces"] = ((cc["rank_full"] == 1) & (cc["gold"] == 0)).astype(int)
    cc["len_z"] = z(cc["desc_tokens"])
    f = W.glm_term(cc, "displaces", ["len_z"], "binomial")
    cost = term(f, "len_z") or {}
    cost["dv"] = "displaces"
    ps = {"H1": float(rows[0].get("p_raw", 1.0)), "H2": float(inter.get("p_raw", 1.0)),
          "H3": float(cost.get("p_raw", 1.0))}
    adj = W.holm(ps)
    rows[0]["p_holm"] = adj["H1"]
    # The frozen support rule for H1 needs *both* halves: a slope of the size the band asks for, and a
    # monotone-then-flat dose-response. The measured pattern is not monotone-then-flat - deciles 1-9 hover between
    # .77 and .88 and the .90 of decile 10 (mean 192 tokens) carries the pooled slope - so the significant slope
    # alone cannot carry the claim, and `verdict` is the frozen rule's answer. The band-only label is kept beside it,
    # named for what it is, so a reader can see both and knows which one the pre-registration decides.
    band_only = W.verdict(rows[0].get("beta"), rows[0].get("ci_lo"), rows[0].get("ci_hi"),
                          adj["H1"], BAND)
    rows[0]["verdict_band_only"] = band_only
    rows[0]["verdict"] = ("supported" if band_only == "supported" and pattern["monotone_then_flat"] else
                          "partial" if band_only == "supported" and not pattern["monotone_then_flat"] else band_only)
    rows[0]["frozen_support_needs_pattern"] = pattern["monotone_then_flat"]
    for i in (1, 2):
        rows[i]["p_holm"] = None
        rows[i]["verdict"] = "descriptive stratum slope, not a family member"
    h2row = dict(inter)
    h2row.update(stratum="H2_interaction_length_x_catalogue_size", dv="reachable", p_holm=adj["H2"],
                 two_slope_difference_descriptive=round(gap, 4),
                 verdict=W.verdict(inter.get("beta"), inter.get("ci_lo"), inter.get("ci_hi"),
                                   adj["H2"], BAND))
    rows.append(h2row)
    cost["p_holm"] = adj["H3"]
    cost["verdict"] = W.verdict(cost.get("beta"), cost.get("ci_lo"), cost.get("ci_hi"), adj["H3"], BAND,
                                direction=1.0)          # frozen H3 predicts displacement RISES with length
    return {"dose_response": dose.to_dict("records"), "pattern": pattern,
            "high_minus_low_reachability_ci": [lo_, hi_], "high_minus_low_p_boot": p_gap, "clusters": k,
            "models": rows, "interaction": inter, "cost_side": cost, "holm": adj,
            "n_rows": int(len(d))}


def _gap(d):
    """Decile 8-10 minus decile 1-3 reachability, with a cluster bootstrap interval and p from the same draws."""
    def fn(x):
        return float(x[x.len_decile >= 8]["reachable"].mean() - x[x.len_decile <= 3]["reachable"].mean())
    r = W.cluster_boot_ci_and_p(d, "query_id", fn, draws=1000)
    return (r.get("ci", [None, None])[0], r.get("ci", [None, None])[1], r.get("clusters"), r.get("p"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--only", action="append", default=[],
                    help="run just these designs (EXP-0137..EXP-0140). Each writes its own artefact, and the "
                         "bootstrap arms cost minutes, so correcting a later design must not re-run them all.")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    Q, C = load()
    if a.quick:
        C = C.sample(60000, random_state=42)
        Q = Q.sample(6000, random_state=42)
    arts = {}
    # each design is written and flushed the moment it finishes, and the run records its own argv: a crash in a later
    # design must not cost the earlier measurements, and a verdict nobody can re-derive from a recorded command line
    # is not evidence (the pre-fix run of this script proved both the loss and the gap).
    todo = {"EXP-0137": lambda: t111(C), "EXP-0138": lambda: t114(C),
            "EXP-0139": lambda: t115(Q), "EXP-0140": lambda: t116(Q, C)}
    if a.only:
        unknown = [x for x in a.only if x not in todo]
        if unknown:
            raise SystemExit(f"ABORT: --only names no design: {unknown}; valid ids are {sorted(todo)}")
        todo = {k: v for k, v in todo.items() if k in a.only}
    for exp, fn in todo.items():
        art = fn()
        art.update(exp_id=exp, seed=W.SEED, quick=a.quick, started_at=W.now(),
                   invocation=" ".join([sys.executable] + sys.argv),
                   run_cost=W.run_cost_row(exp, t0, 0, 0, "wave-2 design"), finished_at=W.now())
        arts[exp] = art
        p = W.write_raw(exp, "wave2_design_" + exp[-4:], art)
        print(f"{exp}: wrote {p.name}", flush=True)
    want = {"EXP-0137": [("EXP0137_t111_nested_models.csv", "models"),
                         ("EXP0137_t111_auroc_ladder.csv", "auroc_ladder")],
            "EXP-0138": [("EXP0138_t114_models.csv", "models")],
            "EXP-0139": [("EXP0139_t115_models.csv", "models"), ("EXP0139_t115_hypotheses.csv", "hypotheses")],
            "EXP-0140": [("EXP0140_t116_dose_response.csv", "dose_response"),
                         ("EXP0140_t116_models.csv", "models")]}
    for exp, tabs in want.items():
        for tab, key in tabs:
            if exp in arts and arts[exp].get(key):
                pd.DataFrame(arts[exp][key]).to_csv(W.OUT / tab, index=False)
    print(json.dumps({k: {kk: v.get(kk) for kk in ("models", "holm", "n_rows", "h2_verdict", "h3_verdict")}
                      for k, v in arts.items()}, indent=1, default=str)[:2600])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
