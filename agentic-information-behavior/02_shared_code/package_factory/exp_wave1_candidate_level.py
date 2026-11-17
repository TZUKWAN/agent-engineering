"""EXP-0124 (T108), EXP-0125 (T109), EXP-0126 (T110): the candidate-level wave-1 designs.

All three ask what makes a *candidate tool* relevant to an instruction, so all three run on the 169,203 query x
candidate rows EXP-0119 wrote, and all three cluster on the query - a candidate is not an independent observation,
and treating 169k rows as 169k clusters would shrink every interval by roughly the square root of the catalogue size.

Two things must be said before any number in this file is read:

* **The agent's own action is not observable on Toucan.** These rows carry the release's curated selection (the gold
  tool) and a frozen lexical ranker, not a logged machine decision. Where a design was written against "what the
  agent followed", it is run against "which account the released selection follows", the substitution is recorded as
  a pre-outcome amendment, and the agent-side quantity is reported as not measured.
* **The encoder is local or nothing is.** T109 and T110 need the distributional score from EXP-0120. If that cache is
  absent the script exits 1; it does not fall back to a lexical proxy, because a "lexical vs semantic conflict" study
  whose semantic arm is lexical again would be a fabricated comparison.

    python 02_shared_code/package_factory/exp_wave1_candidate_level.py
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
import wave_lib as W                                             # noqa: E402
import encode_wave1_texts as ENC                                 # noqa: E402  (rendering + keying, single source)

AMENDMENT = ("T108 H1/H2, T109 H1/H3 and T110 were written against an observable agent selection. The premise census "
             "EXP-0118 established that Toucan's rows carry a curated selection and a dialogue that produces a query, "
             "not a logged tool choice, so on this substrate every 'the agent followed X' is read as 'the released "
             "selection agrees with X'. The change was made before any outcome distribution was computed, the "
             "thresholds and family sizes were not touched, and the agent-side quantity is reported as not measured.")


# ------------------------------------------------------------------------------------- dense scores per row
def dense_frame() -> pd.DataFrame:
    """Per-candidate cosine to the query under the locally-run encoder, in the same order EXP-0120 encoded."""
    vi = W.load_encoder_vectors()
    if not vi:
        raise SystemExit("ABORT: the EXP-0120 encoder cache is absent, so the semantic arm cannot be measured. "
                         "Run encode_wave1_texts.py with the encoder interpreter; a lexical stand-in is not "
                         "acceptable for a lexical-vs-semantic design.")
    import random
    d = W.load_routing(cfgs=W.CONFIGS, bucket="dev")
    d = d[d["subset_name"].astype(str).str.contains("single-turn-original", na=False)]
    keep = []
    for cfg, g in d.groupby("cfg"):
        idx = sorted(random.Random(W.SEED).sample(range(len(g)), min(8000, len(g))))
        keep.append(g.iloc[idx])
    d = pd.concat(keep, ignore_index=True)
    rows = []
    for r in d.itertuples(index=False):
        ent = W.read_catalog(r.catalog_json, r.n_candidates, r.query_id)
        qk = W.text_sha("Q|" + ENC.render_query(r.question))
        qv = vi.vec_for("q", qk)
        sims = []
        for i, e in enumerate(ent):
            dk = W.text_sha(f"D|{r.query_id}|{i}|" + ENC.render_doc(e["name"], e["desc"], e["params"]))
            dv = vi.vec_for("d", dk)
            sims.append(float(np.dot(qv, dv)) if qv is not None and dv is not None else np.nan)
        sims = np.array(sims, dtype=float)
        rk = W.rank_from([0.0 if not np.isfinite(x) else x for x in sims])
        for i, s in enumerate(sims):
            rows.append({"query_id": r.query_id, "cand_idx": i, "dense": s, "dense_rank": int(rk[i])})
    out = pd.DataFrame(rows)
    out.attrs["encoder_stats"] = vi.stats()
    return out


# -------------------------------------------------------------------------------------------------- T108
def t108(C: pd.DataFrame, Q: pd.DataFrame) -> dict:
    d = C.merge(Q[["query_id", "underspec_index", "n_tokens", "n_sentences_w"]], on="query_id", how="left")
    q = d.groupby("query_id")
    med = q["bm25"].transform("median")
    d["overlap_class"] = np.where(d["gold"] == 1, "gold", np.where(d["bm25"] > med, "nongold_high", "nongold_low"))
    # relative lexical advantage of the gold over the best decoy: the identifiable version of "bias holding gold fixed"
    gg = d[d["gold"] == 1].groupby("query_id")["bm25"].max().rename("gold_bm25")
    ng = d[d["gold"] == 0].groupby("query_id")["bm25"].max().rename("decoy_bm25")
    top = pd.concat([gg, ng], axis=1).dropna().reset_index()
    top["rel_adv"] = top["gold_bm25"] - top["decoy_bm25"]
    # merge, not reindex: the frame's index is a positional integer after reset_index(), so reindexing a query_id-keyed
    # series onto it silently produced an all-NaN column, and the design's outcome variable then vanished row by row
    top = top.merge(d[d["rank_full"] == 1][["query_id", "gold"]].rename(columns={"gold": "gold_at_top1"}),
                    on="query_id", how="left")
    top = top.dropna()
    top = top.merge(Q[["query_id", "underspec_index", "n_candidates", "n_gold"]], on="query_id", how="left")
    top["rel_adv_z"] = W.zscore(top["rel_adv"])
    top["underspec_z"] = W.zscore(top["underspec_index"].astype(float))
    # H1 is the displacement rate: how often a decoy that only wins on word overlap takes the slot the released
    # selection gave to its gold tool. The mechanical lexical gradient (coefficient of rel_adv on gold_at_top1) is
    # reported as a *supporting* quantity, because a positive value there is what any word-overlap ranker must do and
    # calling it a bias finding would be the exact error this topic is about.
    top["displaced"] = (top["decoy_bm25"] > top["gold_bm25"]).astype(float)
    rate = float(top["displaced"].mean())
    # the benchmark is not zero: under a rank-1 slot broken by nothing but chance, a decoy wins with probability
    # (#decoys)/(#candidates). Displacement *above that* is the lexical effect the topic is about.
    top["chance"] = ((top["n_candidates"] - top["n_gold"]).astype(float)
                     / top["n_candidates"].astype(float)).clip(lower=0.0)
    # every statistic below is fitted on the same complete-case frame: statsmodels' cluster covariance builds group
    # codes after its own internal dropna, and a row missing one covariate produced an empty group array
    top = top.dropna(subset=["gold_at_top1", "rel_adv_z", "underspec_z", "n_candidates", "n_gold",
                             "displaced", "chance"]).copy()
    rlo, rhi, rc = W.cluster_boot(top, "query_id", lambda x: float(x["displaced"].mean() - x["chance"].mean()))
    p1, _nb = W.boot_p(top, "query_id", lambda x: float(x["displaced"].mean() - x["chance"].mean()))
    excess = round(float(top["displaced"].mean() - top["chance"].mean()), 4)
    res = W.glm_term(top, "gold_at_top1", ["rel_adv_z", "n_candidates", "n_gold"], "binomial")
    if res is None:
        raise SystemExit("ABORT T108: the mechanical gradient could not be fitted on the complete-case frame")
    r1 = res[res["term"] == "rel_adv_z"].iloc[0]
    b, se = float(r1["beta"]), float(r1["se"])
    p_grad = float(r1["p"])
    h1 = dict(hypothesis="H1", term="lexical_displacement_excess_over_chance", rate=round(rate, 4),
              chance_rate=round(float(top["chance"].mean()), 4), excess=excess,
              ci_clustered=[rlo, rhi], ci_of="excess", ci_kind="cluster_bootstrap_percentile",
              p_kind="bootstrap_two_sided_tail",
              clusters=rc, p_boot=p1, n=int(len(top)),
              mechanical_gradient=dict(beta=round(b, 4), se=round(se, 4),
                                       ci_lo=round(b - 1.96 * se, 4), ci_hi=round(b + 1.96 * se, 4),
                                       p_raw=p_grad,
                                       reading="a word-overlap ranker prefers the higher-overlap candidate; reported "
                                               "so the finding is not confused with this tautology"))
    h1_p = p1 if p1 is not None else 1.0
    # H2 decoy asymmetry: is the rank-1 slot over-held by high-overlap decoys relative to their share?
    tab = d.groupby("overlap_class").agg(n=("gold", "size"), at_top1=("rank_full", lambda s: int((s == 1).sum())))
    tab = tab.reset_index()
    tab["share"] = (tab["n"] / tab["n"].sum()).round(4)
    tab["top1_share"] = (tab["at_top1"] / max(1, int(tab["at_top1"].sum()))).round(4)
    hi = tab[tab["overlap_class"] == "nongold_high"].iloc[0]
    lo = tab[tab["overlap_class"] == "nongold_low"].iloc[0]
    ct = np.array([[hi["at_top1"], hi["n"] - hi["at_top1"]], [lo["at_top1"], lo["n"] - lo["at_top1"]]])
    orr, p_or = st.fisher_exact(ct)
    dec = d[d["gold"] == 0].copy()
    dec["hi"] = (dec["overlap_class"] == "nongold_high").astype(int)
    dec["at1"] = (dec["rank_full"] == 1).astype(int)
    lo_, hi_, kc = W.cluster_boot(dec, "query_id", lambda x: float(x["hi"].mul(x["at1"]).sum()
                                                                 / max(1, x["at1"].sum()))
                                 / max(1e-9, x["hi"].mean()))
    h2 = dict(hypothesis="H2", term="high_overlap_decoy_over_selection", odds_ratio=round(float(orr), 4),
              p_raw=float(p_or),
              relative_selection_ratio=round(float(dec["hi"].mul(dec["at1"]).sum()
                                              / max(1, dec["at1"].sum()) / max(1e-9, dec["hi"].mean())), 4),
              ci_of="relative_selection_ratio", null_value=1.0, ci_kind="cluster_bootstrap_percentile",
              ci_clustered=[lo_, hi_], clusters=kc, table=tab.to_dict("records"))
    h2["verdict_direction"] = ("predicted_positive: high-overlap non-gold candidates take the top slot more often "
                               "than low-overlap ones")
    # H3: does less specified instruction language raise the displacement rate?
    Xcols = ["underspec_z", "n_candidates", "n_gold"]
    rf = W.glm_term(top, "displaced", Xcols, "binomial")
    rr = rf[rf["term"] == "underspec_z"].iloc[0]
    bi, sei = float(rr["beta"]), float(rr["se"])
    h3 = dict(hypothesis="H3", term="underspec_z_on_displacement", beta=round(bi, 4), se=round(sei, 4),
              ci_lo=round(float(rr["ci_lo"]), 4), ci_hi=round(float(rr["ci_hi"]), 4),
              p_raw=float(rr["p"]), n=int(rr["n"]))
    rows = [h3]
    h3["verdict_direction"] = "predicted_positive: less specified instructions raise the displacement rate"
    adj = W.holm({"H1": h1_p, "H2": float(p_or), "H3": h3["p_raw"]})
    for x in rows:
        x["p_holm"] = adj["H3"]
        x["verdict"] = W.verdict(x["beta"], x["ci_lo"], x["ci_hi"], x["p_holm"], W.BANDS["medium"])
    h1["p_holm"] = adj["H1"]
    # the frozen rule, on the row's own interval and corrected p: a displacement that runs the other way from the
    # prediction is reported as `opposite`, not folded into `null` by a bespoke three-way expression
    h1["verdict"] = W.verdict(excess, rlo, rhi, adj["H1"], W.BANDS["small"], 1)
    h1["verdict_direction"] = ("predicted_positive: a decoy that shares more words with the instruction displaces "
                               "the released selection more often than chance")
    h1["verdict_note"] = ("the displacement rate is a descriptive quantity: it is supported as a measurement, and "
                          "the *bias* reading belongs to H3, which is the only arm that connects it to language")
    h2["p_holm"] = adj["H2"]
    # the same frozen rule, read on the difference between the observed ratio and the 1.0 the design sets against
    h2["verdict"] = W.verdict(h2["relative_selection_ratio"] - 1.0, (lo_ or 1.0) - 1.0, (hi_ or 1.0) - 1.0,
                              adj["H2"], W.BANDS["small"], 1)
    return {"models": rows, "lexical_displacement": h1, "decoy_asymmetry": h2, "holm": adj,
            "n_queries_identifiable": int(len(top)),
            "n_candidate_rows": int(len(d)), "amendment": AMENDMENT,
            "distribution": {"gold_top1_rate": round(float(top["gold_at_top1"].mean()), 4),
                             "median_rel_adv": round(float(top["rel_adv"].median()), 4)}}


# -------------------------------------------------------------------------------------------------- T109
def t109(C: pd.DataFrame, D: pd.DataFrame) -> dict:
    d = C.merge(D, on=["query_id", "cand_idx"], how="left")
    lex1 = d[d["rank_full"] == 1].set_index("query_id")[["cand_idx", "gold"]].rename(
        columns={"cand_idx": "lex_idx", "gold": "lex_gold"})
    sem1 = d[d["dense_rank"] == 1].set_index("query_id")[["cand_idx", "gold"]].rename(
        columns={"cand_idx": "sem_idx", "gold": "sem_gold"})
    j = pd.concat([lex1, sem1], axis=1).dropna().reset_index()
    j = j[j["lex_idx"] != j["sem_idx"]]
    n = len(j)
    k_lex = int((j["lex_gold"] == 1).sum())
    k_sem = int((j["sem_gold"] == 1).sum())
    both = int(((j["lex_gold"] == 1) & (j["sem_gold"] == 1)).sum())
    neither = int(((j["lex_gold"] == 0) & (j["sem_gold"] == 0)).sum())
    # The estimate, its interval and its exact test all use one denominator: the conflict rows where exactly one of
    # the two winners is the released selection. Bootstrapping over all conflict rows would attach an interval for a
    # different quantity to the printed proportion, so the two would disagree by construction.
    decidable = j[(j["lex_gold"] + j["sem_gold"]) == 1].copy()
    decidable["one"] = (decidable["lex_gold"] == 1).astype(float)
    n_dec = int(len(decidable))
    dec_lex = int((decidable["one"] == 1).sum())
    lo_, hi_, _ = W.cluster_boot(decidable, "query_id", lambda x: float(x["one"].mean()), draws=1000)
    prop = (dec_lex / n_dec) if n_dec else float("nan")
    p_bin = float(st.binomtest(dec_lex, n_dec, 0.5).pvalue) if n_dec else float("nan")
    h1 = dict(hypothesis="H1", measure="released_selection_follows_lexical_share", n_conflict=n, n_decidable=n_dec,
              lexical=k_lex, semantic=k_sem, decidable_lexical=dec_lex,
              both=both, neither=neither, proportion=round(prop, 4), ci_clustered=[lo_, hi_],
              ci_of="proportion", null_value=0.5, ci_kind="cluster_bootstrap_percentile",
              # the design froze H1's support threshold as "0.6 of the decidable conflicts"; on a quantity measured
              # against a 0.5 chance null that is a floor of 0.1, and the row states it so the word can be re-derived
              support_floor=0.1, p_exact=p_bin,
              verdict=(W.verdict(round(prop, 4) - 0.5, (lo_ or 0.5) - 0.5, (hi_ or 0.5) - 0.5, p_bin, 0.1, 1)
                       if lo_ is not None and hi_ is not None else "not_estimable_no_interval_for_this_statistic"))
    # this artefact is not keyed by topic, so the design sentence cannot be looked up for it: the row states the
    # side its own frozen hypothesis predicted
    h1["verdict_direction"] = ("predicted_positive: on a conflict the released selection follows the lexical "
                               "winner more often than chance")
    # H2 moderation by catalogue size, on the conflict set only
    js = j.merge(C.groupby("query_id")["n_candidates"].first().reset_index(), on="query_id", how="left")
    js["big"] = (js["n_candidates"] >= js["n_candidates"].median()).astype(int)
    rj = W.glm_term(js, "lex_gold", ["big"], "binomial")
    rrow = rj[rj["term"] == "big"].iloc[0] if rj is not None else None
    med_rate = js[js["big"] == 1]["lex_gold"].mean()
    small_rate = js[js["big"] == 0]["lex_gold"].mean()
    lo2, hi2, _ = W.cluster_boot(js, "query_id", lambda x: float(
        x[x["big"] == 1]["lex_gold"].mean() - x[x["big"] == 0]["lex_gold"].mean()), draws=1000)
    h2 = dict(measure="follow_gap_by_catalogue_size", big_rate=round(float(med_rate), 4),
              small_rate=round(float(small_rate), 4), gap=round(float(med_rate - small_rate), 4),
              ci_clustered=[lo2, hi2],
              beta=(round(float(rrow["beta"]), 4) if rrow is not None else None),
              p_raw=(float(rrow["p"]) if rrow is not None else 1.0),
              verdict="see ci; the two rates and their interval carry the claim")
    # H3 disagreement census + rank agreement statistics
    dd = d.dropna(subset=["dense"])
    # vectorised top-1 comparison: `groupby.apply` on 169k rows is both slower and fragile across pandas versions
    dd = dd.dropna(subset=["dense_rank"])
    g1 = dd.loc[dd.groupby("query_id")["rank_full"].idxmin(), ["query_id", "cand_idx"]].rename(
        columns={"cand_idx": "lex_idx"})
    g2 = dd.loc[dd.groupby("query_id")["dense_rank"].idxmin(), ["query_id", "cand_idx"]].rename(
        columns={"cand_idx": "sem_idx"})
    a = g1.merge(g2, on="query_id", how="inner")
    a = (a["lex_idx"] == a["sem_idx"]).astype(int)
    po = float(a.mean())
    pe = float(np.sum((dd["cand_idx"].value_counts(normalize=True).sort_index().reindex(
        range(int(dd["cand_idx"].max()) + 1), fill_value=0.0).to_numpy()) ** 2))
    kappa = (po - pe) / max(1e-9, 1 - pe)
    rho = st.spearmanr(dd.groupby("query_id")["bm25"].max(), dd.groupby("query_id")["dense"].max())
    h3 = dict(hypothesis="H3", measure="lexical_vs_semantic_rank_agreement", n_queries=int(len(a)),
              top1_agreement=round(po, 4),
              expected_agreement=round(pe, 4), kappa=round(float(kappa), 4),
              spearman_max_scores=round(float(rho.statistic), 4), conflict_share=round(1 - po, 4),
              # H3's frozen sentence asks that the disagreement be "characterised rather than averaged away": it is a
              # census of the conflict set, no sampling model was fitted to it, so it carries the estate's
              # non-inferential word rather than a four-way one it could not show
              verdict_rule="descriptive", verdict="supported")
    return {"H1": h1, "H2": h2, "H3": h3, "n_candidate_rows": int(len(dd)),
            "conflict_set_floor": int(200), "underpowered": bool(n < 200), "amendment": AMENDMENT,
            "encoder": {"cosine_missing_share": round(float(dd["dense"].isna().mean()), 5)}}


# -------------------------------------------------------------------------------------------------- T110
def t110(C: pd.DataFrame, D: pd.DataFrame) -> dict:
    d = C.merge(D, on=["query_id", "cand_idx"], how="left")
    d = d.dropna(subset=["dense"]).copy()
    import statsmodels.api as sm
    d["bm25_z"] = W.zscore(d["bm25"])
    d["dense_z"] = W.zscore(d["dense"])
    d["desc_z"] = W.zscore(d["desc_len"].astype(float))
    specs = {"similarity_only": ["bm25_z", "dense_z"],
             "similarity_plus_predicate": ["bm25_z", "dense_z", "predicate_fit"],
             "similarity_plus_argument": ["bm25_z", "dense_z", "argument_fit"],
             "similarity_plus_both": ["bm25_z", "dense_z", "predicate_fit", "argument_fit"],
             "full_plus_controls": ["bm25_z", "dense_z", "predicate_fit", "argument_fit", "desc_z", "param_n"]}
    fits, aucs, rows = {}, {}, []
    y = d["gold"].astype(float)
    for name, xs in specs.items():
        X = sm.add_constant(d[xs].astype(float))
        r = sm.GLM(y, X, family=sm.families.Binomial()).fit()
        fits[name] = r
        aucs[name] = float(roc_auc_score(y, r.fittedvalues))
        rows.append(dict(model=name, llf=round(float(r.llf), 2), auroc=round(aucs[name], 4),
                         beta_argument=round(float(r.params.get("argument_fit", np.nan)), 4),
                         beta_predicate=round(float(r.params.get("predicate_fit", np.nan)), 4)))
    def lr(a, b):
        s = 2 * (fits[b].llf - fits[a].llf)
        return float(s), float(st.chi2.sf(max(s, 0.0), len(set(specs[b]) - set(specs[a])) or 1))
    lr1, p1 = lr("similarity_only", "similarity_plus_both")
    d["both_fit"] = d["predicate_fit"] * d["argument_fit"]
    dense_pred = np.column_stack([np.ones(len(d)), d[["bm25_z", "dense_z"]].to_numpy()])
    dense_arg = np.column_stack([np.ones(len(d)), d[["bm25_z", "dense_z", "predicate_fit",
                                                     "argument_fit"]].to_numpy()])
    def _auc(mat):
        b = np.linalg.lstsq(mat, y.to_numpy(), rcond=None)[0]
        return float(roc_auc_score(y, mat @ b))
    au_delta, adelta_lo, adelta_hi, kc = None, None, None, 0

    def delta_fn(x):
        m0 = np.column_stack([np.ones(len(x)), x[["bm25_z", "dense_z"]].to_numpy()])
        m1 = np.column_stack([np.ones(len(x)), x[["bm25_z", "dense_z", "predicate_fit", "argument_fit"]].to_numpy()])
        b0 = np.linalg.lstsq(m0, x["gold"].astype(float).to_numpy(), rcond=None)[0]
        b1 = np.linalg.lstsq(m1, x["gold"].astype(float).to_numpy(), rcond=None)[0]
        return float(roc_auc_score(x["gold"], m1 @ b1)) - float(roc_auc_score(x["gold"], m0 @ b0))
    au_delta = round(_auc(dense_arg) - _auc(dense_pred), 4)
    adelta_lo, adelta_hi, kc = W.cluster_boot(d, "query_id", delta_fn, draws=400)
    # H2 separability: predicate vs argument, and the argument effect in dense catalogues
    dense_cat = d[d["n_candidates"] >= d["n_candidates"].median()]
    X = sm.add_constant(dense_cat[["bm25_z", "dense_z", "predicate_fit", "argument_fit"]].astype(float))
    rr = sm.GLM(dense_cat["gold"].astype(float), X, family=sm.families.Binomial()).fit(
        cov_type="cluster", cov_kwds={"groups": dense_cat["query_id"]})
    sp = dict(pred_in_dense=round(float(rr.params["predicate_fit"]), 4), pred_p=float(rr.pvalues["predicate_fit"]),
              arg_in_dense=round(float(rr.params["argument_fit"]), 4), arg_p=float(rr.pvalues["argument_fit"]))
    adj = W.holm({"H1": p1, "H2": float(rr.pvalues["argument_fit"]), "H3": p1})
    cov = {"predicate_coverage": round(float((d["pred_coverage"] == 1).mean()), 4),
           "argument_coverage": round(float((d["arg_coverage"] == 1).mean()), 4),
           "desc_argument_coverage": round(float((d["d_arg_n"] > 0).mean()), 4)}
    return {"models": rows, "lr_both_vs_similarity": dict(stat=round(lr1, 3), p=p1, p_holm=adj["H1"]),
            "auroc_gain": dict(delta=au_delta, ci=[adelta_lo, adelta_hi], clusters=kc),
            "separability": sp, "holm": adj, "coverage": cov, "n_rows": int(len(d)),
            "verdicts": dict(
                H1=("supported" if au_delta >= 0.02 and (adelta_lo or 0) > 0 and p1 < 0.05 else
                    "partial" if p1 < 0.05 else "null")),
            "amendment": AMENDMENT}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    C = pd.read_csv(W.PROCES / "EXP0119_wave1_candidate_rows.csv.gz")
    Q = pd.read_csv(W.PROCES / "EXP0119_wave1_query_features.csv")
    if args.quick:
        C = C.sample(40000, random_state=42)
    D = dense_frame()
    if args.quick:
        D = D.sample(40000, random_state=42)
    a8 = t108(C, Q)
    a9 = t109(C, D)
    a10 = t110(C, D)
    pd.DataFrame(a8["models"]).to_csv(W.OUT / "EXP0124_t108_main_models.csv", index=False)
    pd.DataFrame(a8["decoy_asymmetry"]["table"]).to_csv(W.OUT / "EXP0124_t108_overlap_gold_contingency.csv",
                                                        index=False)
    pd.DataFrame(a10["models"]).to_csv(W.OUT / "EXP0126_t110_nested_models.csv", index=False)
    D.to_csv(W.OUT / "EXP0125_wave1_dense_scores.csv.gz", index=False, compression="gzip")
    for exp, art in (("EXP-0124", a8), ("EXP-0125", a9), ("EXP-0126", a10)):
        art["run_cost"] = W.run_cost_row(exp, t0, len(C), C.shape[1])
        art["started_at"], art["finished_at"] = W.now(), W.now()
        p = W.write_raw(exp, "wave1_candidate_level_" + exp[-4:], art)
        print(f"{exp}: wrote {p.name}")
    print(json.dumps({"T108": a8["models"], "T108_H2": {k: v for k, v in a8["decoy_asymmetry"].items()
                                                       if k != "table"},
                      "T109_H1": a9["H1"], "T109_H3": a9["H3"],
                      "T110": {k: a10[k] for k in ("auroc_gain", "lr_both_vs_similarity", "verdicts")}},
                     indent=1, default=str)[:3000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
