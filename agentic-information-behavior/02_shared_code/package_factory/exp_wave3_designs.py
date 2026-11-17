"""EXP-0145 (T113), EXP-0146 (T119), EXP-0147 (T120), EXP-0148 (T122): the frozen wave-3 designs.

Wave 3 reads the catalogue text itself. Two designs are interventions - the catalogue is rewritten by a checked-in
rule and re-scored by the frozen BM25 - and two are associations over columns the matrix computed. Everything shared
with wave 2 is *imported*, not rewritten: `term`, `auroc` and `clustered_auroc_delta` come from
`exp_wave2_designs.py`, so an interval, a band or an AUROC ladder means the same thing in both waves.

Two hypotheses are already dead before any estimate is read, because their own pre-registered kill gates fired at
EXP-0142: T113's H1 (the use-case frame changes description length by 66.7% on median, above the 40% tolerance the
design set for itself) and T119's H3 (zero candidate rows carry the name-versus-description contradiction, below the
200-row floor it set). Both are still computed - the measurement is what the gate fired on - but they are labelled
`not_interpretable` / `not_testable` and no verdict word is spent on them. Their designs' other hypotheses stand.

    python 02_shared_code/package_factory/exp_wave3_designs.py [--only EXP-0145] [--quick]
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

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import wave_lib as W                                              # noqa: E402
import exp_wave2_designs as D2                                    # noqa: E402
import topic_designs_wave3 as TD3                                 # noqa: E402

BAND = W.BANDS["medium"]
term, auroc = D2.term, D2.auroc
clustered_auroc_delta = D2.clustered_auroc_delta


def z(s):
    return D2.z(s)


def load() -> tuple:
    Q = pd.read_csv(W.PROCES / "EXP0143_wave3_query_features.csv")
    C = pd.read_csv(W.PROCES / "EXP0143_wave3_candidate_features.csv.gz")
    W2 = pd.read_csv(W.PROCES / "EXP0136_wave2_candidate_features.csv.gz")
    # the candidate frame carries only wave 3's own columns; the agreement and centrality measures wave 2 froze are
    # merged in, because T119 controls with them and re-deriving them here would make two numbers for one construct
    want = [c for c in ("entity_agree", "action_agree", "constraint_agree", "desc_tokens", "param_n",
                        "prototype_centrality", "enum_share", "verb_coverage") if c not in C.columns]
    C = C.merge(W2[["query_id", "cand_idx"] + want], on=["query_id", "cand_idx"], how="left")
    if any(c.endswith(("_x", "_y")) for c in C.columns):
        raise SystemExit(f"ABORT: the candidate merge produced suffixes "
                         f"{[c for c in C.columns if c.endswith(('_x', '_y'))]}; a name exists in both frames")
    W2q = pd.read_csv(W.PROCES / "EXP0136_wave2_query_features.csv",
                      usecols=lambda c: c in ("query_id", "gold_param_n", "gold_enum_share",
                                              "gold_verb_coverage", "gold_desc_tokens", "fail_at_1", "fail_at_3",
                                              "underspec_index", "constraint_total", "n_tokens"))
    # `fail_at_1` is the wave-1/wave-2 outcome column every reachability claim in this programme is built from, so
    # wave 3 reads the frozen one rather than re-deriving it from its own arm ranks - the two waves then describe the
    # same outcome. A missing column here would have surfaced as a KeyError deep inside T122 instead.
    if Q["query_id"].astype(str).nunique() != len(Q):
        raise SystemExit("ABORT: query_id is not unique in the wave-3 query frame, so the merge below would "
                         "duplicate rows rather than describe them")
    # Only the columns the wave-3 matrix does not already carry: merging a frame over a name that exists on both
    # sides renames them to `..._x` / `..._y`, and the design would then die on a KeyError for the plain name (or,
    # worse for a numeric column, quietly read the wrong one).
    add = [c for c in W2q.columns if c != "query_id" and c not in Q.columns]
    before = len(Q)
    Q = Q.merge(W2q[["query_id"] + add], on="query_id", how="left") if add else Q
    if len(Q) != before or any(c.endswith(("_x", "_y")) for c in Q.columns):
        raise SystemExit(f"ABORT: the completeness merge did not behave as a 1:1 join "
                         f"({before} -> {len(Q)}, suffixes={[c for c in Q.columns if c.endswith(('_x','_y'))]})")
    if C["entity_agree"].isna().mean() > 0.01:
        raise SystemExit(f"ABORT: {C['entity_agree'].isna().mean():.3f} of candidate rows lost their wave-2 merge, so "
                         f"the controls would silently drop those rows")
    return Q, C


def paired(Q: pd.DataFrame, a: str, b: str, draws: int = 1000) -> dict:
    """Mean of (a - b) within query, with a cluster bootstrap interval and p from the same draws."""
    d = Q.dropna(subset=[a, b, "query_id"]).copy()
    d["dif"] = d[a].astype(float) - d[b].astype(float)
    r = W.cluster_boot_ci_and_p(d, "query_id", lambda x: float(x["dif"].mean()), draws=draws)
    return dict(arm_a=a, arm_b=b, mean_difference=round(float(d["dif"].mean()), 4), ci=r.get("ci"),
                p_boot=r.get("p"), clusters=r.get("clusters"), draws_used=r.get("draws_used"),
                rows=int(len(d)), n_changed_rows=int((d["dif"] != 0).sum()), error=r.get("error"))


# ------------------------------------------------------------------------------------------------ T113 / 0145
def need(df: pd.DataFrame, cols, who: str) -> None:
    miss = [c for c in cols if c not in df.columns]
    if miss:
        raise SystemExit(f"ABORT {who}: the frame has no column(s) {miss}; the design's outcome or moderator is "
                         f"not in the matrix, and running on would drop it silently")


def t113(Q: pd.DataFrame) -> dict:
    need(Q, ("baseline_hit1", "usecase_hit1", "usecase_matched_hit1", "synonym_hit1", "baseline_rank",
             "gold_desc_tokens", "query_id", "cfg"), "EXP-0145")
    gate = TD3.PREMISES["gates"].get("T113_rewrite_length_within_tolerance")
    change = TD3.PREMISES["measured"].get("T113_median_abs_token_change_of_usecase_rewrite_pct")
    out = {"gate_fired_at_EXP0142": bool(gate is False), "measured_length_change_median": change,
           "n_queries": int(len(Q))}
    # H1: the frame contrast as frozen. Its own gate says a >40% length change makes the contrast uninterpretable,
    # and the measured change is 66.7%, so the number is reported and the claim is withheld - not renegotiated.
    h1 = paired(Q, "usecase_hit1", "baseline_hit1")
    h1.update(hypothesis="H1", term="usecase_minus_baseline_hit1",
              verdict="not_interpretable_length_confound",
              note="the frozen gate defines this arm pair as uninterpretable at this length change; reporting the "
                   "difference as a framing effect would attribute to the frame what the token count produced")
    h1r = paired(Q, "usecase_rank", "baseline_rank")
    h1["rank_difference"] = h1r["mean_difference"]
    h1["rank_difference_ci"] = h1r["ci"]
    h1["rank_difference_p_boot"] = h1r["p_boot"]
    # H2: short descriptions should gain more from the frame - a moderation test, not a subgroup average
    d = Q.dropna(subset=["usecase_hit1", "baseline_hit1", "gold_desc_tokens"]).copy()
    d["short"] = (d["gold_desc_tokens"] <= d["gold_desc_tokens"].median()).astype(float)
    d["gain"] = d["usecase_hit1"].astype(float) - d["baseline_hit1"].astype(float)
    f = W.glm_term(d.assign(t=z(d["gold_desc_tokens"])), "gain", ["t", "short"], "gaussian")
    h2 = term(f, "t") or {}
    h2.update(hypothesis="H2", term="gain_by_description_length", dv="usecase_minus_baseline_hit1")
    # H3: the same frame truncated to the baseline's token count - the comparison that is actually at matched length
    h3 = paired(Q, "usecase_matched_hit1", "baseline_hit1")
    f3 = W.glm_term(Q.assign(gain=(Q["usecase_matched_hit1"].astype(float)
                                   - Q["baseline_hit1"].astype(float)), len_z=z(Q["gold_desc_tokens"])),
                    "gain", ["len_z"], "gaussian")
    h3m = term(f3, "len_z") or {}
    h3.update(hypothesis="H3", term="usecase_matched_minus_baseline_hit1", **{"slope_on_length": h3m})
    matched_len = float((Q["usecase_matched_hit1"].notna()).mean())
    ps = {"H1": float(h1.get("p_boot") or 1.0), "H2": float(h2.get("p_raw", h2.get("p", 1.0))),
          "H3": float(h3.get("p_boot") or 1.0)}
    adj = W.holm(ps)
    h1["p_holm"] = adj["H1"]
    h2["p_holm"] = adj["H2"]
    h2["verdict"] = W.verdict(h2.get("beta"), h2.get("ci_lo"), h2.get("ci_hi"), adj["H2"], BAND, direction=-1.0)
    h3["p_holm"] = adj["H3"]
    # The freeze says "the two frames still differ" (no direction) and its support clause names a floor for a
    # coefficient or a rank shift, not for a matched-length proportion difference, so `supported` is not available
    # for this row: an interval that excludes zero is reported `partial`, which is exactly what the frozen
    # partial clause says. Deviation W3-D11.
    h3["verdict"] = W.magnitude_verdict(h3.get("mean_difference"), (h3.get("ci") or [None, None])[0],
                                        (h3.get("ci") or [None, None])[1], adj["H3"], floor=None, side="abs")
    h3["matched_arm_present_share"] = round(matched_len, 4)
    # table4_strata_by_length: the gain inside each description-length tercile, with a clustered interval per stratum
    # rather than a single pooled slope - that is what "the frame adds what the text omitted" would look like.
    terc = pd.qcut(d["gold_desc_tokens"].rank(method="first"), 3, labels=["short", "middle", "long"])
    strat = []
    for lab in ("short", "middle", "long"):
        g = d[terc == lab]
        if len(g) < 100:
            strat.append(dict(stratum=lab, n_rows=int(len(g)), note="too few rows to stratify"))
            continue
        b = W.cluster_boot_ci_and_p(g, "query_id",
                                    lambda x: float((x["usecase_hit1"].astype(float)
                                                     - x["baseline_hit1"].astype(float)).mean()), draws=600)
        strat.append(dict(stratum=lab, n_rows=int(len(g)), n_queries=int(g["query_id"].nunique()),
                          mean_tokens=round(float(g["gold_desc_tokens"].mean()), 2),
                          hit1_gain=round(float((g["usecase_hit1"].astype(float)
                                                 - g["baseline_hit1"].astype(float)).mean()), 4),
                          gain_ci=b.get("ci"), gain_p_boot=b.get("p")))
    out["strata"] = strat
    out["models"] = [h1, h2, h3]
    out["holm"] = adj
    return out


# ------------------------------------------------------------------------------------------------ T119 / 0146
def t119(C: pd.DataFrame) -> dict:
    need(C, ("name_desc_congruence", "gold", "desc_tokens", "param_n", "prototype_centrality", "contradiction",
             "entity_agree", "action_agree", "constraint_agree"), "EXP-0146")
    d = C.dropna(subset=["name_desc_congruence", "gold", "desc_tokens"]).copy()
    d["congr_z"] = z(d["name_desc_congruence"])
    d["len_z"] = z(d["desc_tokens"])
    d["param_z"] = z(d["param_n"].astype(float))
    d["centr_z"] = z(d["prototype_centrality"].astype(float))
    rows = []
    f1 = W.glm_term(d, "gold", ["congr_z"], "binomial")
    h1 = term(f1, "congr_z") or {}
    h1.update(hypothesis="H1", term="congruence_unconditional", dv="gold")
    f2 = W.glm_term(d, "gold", ["congr_z", "len_z", "param_z", "centr_z", "entity_agree", "action_agree",
                                "constraint_agree"], "binomial")
    h2 = term(f2, "congr_z") or {}
    h2.update(hypothesis="H2", term="congruence_with_frozen_controls", dv="gold",
              controls_kept=int((~d[["len_z", "param_z", "centr_z"]].isna()).all(axis=1).sum()))
    contra = int(d["contradiction"].sum())
    gate = TD3.PREMISES["gates"].get("T119_contradiction_cell_testable")
    # H3 as frozen compares three congruence levels. The contradiction level has zero rows - the gate fired on the
    # census - so the comparison is reported as not testable, and the two populated levels are shown for what they
    # are worth instead of the empty cell being folded into the neutral one.
    lev = d.assign(level=np.where(d["contradiction"] == 1, "contradictory",
                          np.where(d["name_desc_congruence"] >= 0.5, "congruent", "uninformative")))
    tab = lev.groupby("level").agg(rows=("gold", "size"), gold_rate=("gold", "mean")).reset_index()
    h3 = dict(hypothesis="H3", term="congruence_level_contrast", rows_on_table=int(tab["rows"].sum()),
              levels=tab.to_dict("records"), contradiction_rows=contra,
              gate_fired_at_EXP0142=bool(gate is False),
              verdict="not_testable_empty_cell" if contra < 200 else "computed",
              note="the design refuses to fold an empty contradiction cell into the neutral one; with 0 rows the "
                   "three-level claim this package pre-registered cannot be made")
    ps = {"H1": float(h1.get("p_raw", 1.0)), "H2": float(h2.get("p_raw", 1.0)), "H3": 1.0}
    adj = W.holm(ps)
    h1["p_holm"], h2["p_holm"] = adj["H1"], adj["H2"]
    h1["verdict"] = W.verdict(h1.get("beta"), h1.get("ci_lo"), h1.get("ci_hi"), adj["H1"], BAND)
    h2["verdict"] = W.verdict(h2.get("beta"), h2.get("ci_lo"), h2.get("ci_hi"), adj["H2"], BAND)
    h3["p_holm"] = adj["H3"]
    terc = pd.qcut(d["desc_tokens"].rank(method="first"), 3, labels=["short", "middle", "long"])
    strat = []
    for lab in ("short", "middle", "long"):
        g = d[terc == lab]
        if len(g) < 200:
            strat.append(dict(stratum=lab, n_rows=int(len(g)), note="too few rows to stratify"))
            continue
        t = term(W.glm_term(g, "gold", ["congr_z"], "binomial"), "congr_z") or {}
        strat.append(dict(stratum=lab, n_rows=int(len(g)), n_queries=int(g["query_id"].nunique()),
                          **{k: t.get(k) for k in ("beta", "se", "ci_lo", "ci_hi", "p")}))
    rows = [h1, h2, h3]
    return {"models": rows, "strata": strat, "holm": adj, "n_rows": int(len(d)),
            "n_queries": int(d["query_id"].nunique()),
            "congruence_distribution": {"mean": round(float(d["name_desc_congruence"].mean()), 4),
                                        "p10": round(float(d["name_desc_congruence"].quantile(.10)), 4),
                                        "p50": round(float(d["name_desc_congruence"].quantile(.50)), 4),
                                        "p90": round(float(d["name_desc_congruence"].quantile(.90)), 4)},
            "vif": W.vif(d[["name_desc_congruence", "desc_tokens", "param_n"]].astype(float))}


# ------------------------------------------------------------------------------------------------ T120 / 0147
def _family_iqr(f: pd.DataFrame, col: str) -> pd.Series:
    # Per (query, agreement-family) interquartile range of a rank column, without a groupby.apply.
    keys = ["query_id", "family_id"]
    return f.groupby(keys)[col].quantile(.75) - f.groupby(keys)[col].quantile(.25)


def t120(Q: pd.DataFrame, C: pd.DataFrame) -> dict:
    # Vocabulary control: does canonicalising the catalogue wording make *which* tool is found more consistent?
    h1 = paired(Q, "synonym_hit1", "baseline_hit1")
    rk = paired(Q, "synonym_rank", "baseline_rank")
    h1.update(hypothesis="H1", term="synonym_minus_baseline_hit1", rank_difference=rk["mean_difference"],
              rank_difference_ci=rk["ci"], rank_difference_p_boot=rk["p_boot"])
    f = C.dropna(subset=["baseline_rank", "synonym_rank", "action_agree", "entity_agree"]).copy()
    f["family_id"] = f["query_id"].astype(str) + "|" + f["action_agree"].astype(int).astype(str) + "|" \
        + f["entity_agree"].astype(int).astype(str)
    keys = ["query_id", "family_id"]
    fam = pd.DataFrame({"n_members": f.groupby(keys).size(),
                        "iqr_baseline_rank": _family_iqr(f, "baseline_rank"),
                        "iqr_synonym_rank": _family_iqr(f, "synonym_rank")}).reset_index()
    fam = fam[fam["n_members"] >= 2]
    per_q = fam.groupby("query_id")[["iqr_baseline_rank", "iqr_synonym_rank"]].mean().reset_index()
    per_q["dif"] = per_q["iqr_synonym_rank"] - per_q["iqr_baseline_rank"]
    boot = W.cluster_boot_ci_and_p(per_q, "query_id", lambda x: float(x["dif"].mean()), draws=1000)
    h2 = dict(hypothesis="H2", term="within_family_rank_spread_synonym_minus_baseline",
              families=int(len(fam)), queries_with_families=int(len(per_q)),
              mean_iqr_baseline=round(float(per_q["iqr_baseline_rank"].mean()), 4) if len(per_q) else None,
              mean_iqr_synonym=round(float(per_q["iqr_synonym_rank"].mean()), 4) if len(per_q) else None,
              mean_difference=round(float(per_q["dif"].mean()), 4) if len(per_q) else None,
              ci=boot.get("ci"), p_boot=boot.get("p"), clusters=boot.get("clusters"),
              members_per_family=round(float(fam["n_members"].mean()), 3) if len(fam) else None)
    # H3 as frozen is a question about *where* the benefit sits, so the rows the arm could not affect are excluded
    # and counted rather than averaged in as zeros.
    ch = Q[(Q["gold_synonym_changed"] == 1) | (Q["query_has_mapped_surface"] == 1)].copy()
    ch["gain"] = ch["synonym_hit1"].astype(float) - ch["baseline_hit1"].astype(float)
    moved = ch[ch["gain"] != 0].copy()
    moved["improved"] = (moved["gain"] > 0).astype(int)
    moved["mismatch"] = ((moved["gold_synonym_changed"] == 1) & (moved["query_has_mapped_surface"] == 1)).astype(float)
    n_untouched, n_tied = int(len(Q) - len(ch)), int(len(ch) - len(moved))
    if len(moved) < 200 or moved["mismatch"].nunique() < 2:
        h3 = dict(hypothesis="H3", term="benefit_where_vocabulary_differs", rows_usable=int(len(moved)),
                  rows_arm_did_not_touch=n_untouched, rows_no_change=n_tied, verdict="not_testable",
                  note="the moderator has only one populated level, so there is nothing for it to moderate")
    else:
        h3 = dict(term(W.glm_term(moved, "improved", ["mismatch"], "binomial"), "mismatch") or {})
        h3.update(hypothesis="H3", term="benefit_where_vocabulary_differs", rows_usable=int(len(moved)),
                  rows_arm_did_not_touch=n_untouched, rows_no_change=n_tied, dv="rank1_improved")
    ps = {"H1": float(h1.get("p_boot") or 1.0), "H2": float(h2.get("p_boot") or 1.0),
          "H3": float(h3.get("p_raw", 1.0))}
    adj = W.holm(ps)
    h1["p_holm"], h2["p_holm"], h3["p_holm"] = adj["H1"], adj["H2"], adj["H3"]
    spread_falls = bool((h2.get("ci") or [None, None])[1] is not None and (h2["ci"][1] < 0))
    h1["frozen_support_also_needs_H2"] = spread_falls
    h1["verdict"] = W.magnitude_verdict(h1.get("mean_difference"), (h1.get("ci") or [None, None])[0],
                                        (h1.get("ci") or [None, None])[1], adj["H1"], floor=0.05, side="abs")
    # The frozen support clause needs both halves; a one-sided reading of either is what mislabelled this row
    # before, so the second condition demotes rather than promotes. Deviation W3-D11.
    if h1["verdict"] == "supported" and not spread_falls:
        h1["verdict"] = "partial"
        h1["note"] = (h1.get("note") or "") + " | support also needs the within-family spread reduction, whose "                                               "interval does not exclude 0"
    h2["verdict"] = W.magnitude_verdict(h2.get("mean_difference"), (h2.get("ci") or [None, None])[0],
                                        (h2.get("ci") or [None, None])[1], adj["H2"], floor=0.0, side="neg")
    h2["note"] = ("a negative difference means the normalised catalogue ranks same-family candidates more alike, "
                  "which is the consistency claim; the sign is not free")
    if "verdict" not in h3:
        h3["verdict"] = W.verdict(h3.get("beta"), h3.get("ci_lo"), h3.get("ci_hi"), adj["H3"], BAND)
    return {"models": [h1, h2, h3], "holm": adj, "n_queries": int(len(Q)),
            "coverage": {"queries_the_arm_could_touch": int(len(ch)),
                         "share_of_queries_the_arm_could_touch": round(len(ch) / max(1, len(Q)), 4)}}


# ------------------------------------------------------------------------------------------------ T122 / 0148
def _fit(d, xs):
    import statsmodels.api as sm
    return sm.GLM(d["reachable"].astype(float), sm.add_constant(d[xs].astype(float)),
                  family=sm.families.Binomial()).fit()


def t122(Q: pd.DataFrame, C: pd.DataFrame) -> dict:
    need(Q, ("fail_at_1", "n_candidates", "query_id"), "EXP-0148")
    # Discriminability against completeness: does telling your tool apart from its neighbours get it found?
    g = C[C["gold"] == 1].groupby("query_id")[["discrimin_lexical", "discrimin_dense"]].mean().reset_index()
    d = Q.merge(g, on="query_id", how="left")
    d["reachable"] = 1 - d["fail_at_1"]
    thin = d["n_candidates"] < 3                 # a catalogue of one has no neighbours: excluded and counted
    n_thin = int(thin.sum())
    d = d[~thin].dropna(subset=["reachable", "discrimin_lexical"]).copy()
    if len(d) < 1000:
        raise SystemExit(f"ABORT: only {len(d)} queries carry a gold discriminability value")
    d["lex_z"] = z(d["discrimin_lexical"])
    have_dense = bool(d["discrimin_dense"].notna().sum() >= 0.5 * len(d))
    rows = []
    h1 = dict(term(W.glm_term(d, "reachable", ["lex_z"], "binomial"), "lex_z") or {})
    h1.update(hypothesis="H1", term="discriminability_lexical", dv="reachable", n_queries=int(len(d)),
              queries_excluded_no_neighbours=n_thin)
    second = None
    if have_dense:
        d["den_z"] = z(d["discrimin_dense"])
        dd = d.dropna(subset=["den_z"])
        second = dict(term(W.glm_term(dd, "reachable", ["den_z"], "binomial"), "den_z") or {})
        second.update(hypothesis="E06", term="discriminability_dense", construct="discriminability",
                      term_name="discriminability_dense",
                      second_instrument="mean cosine distance to the other entries of the same catalogue",
                      spearman_with_lexical=round(float(st.spearmanr(dd["lex_z"], dd["den_z"]).statistic), 4),
                      n_queries=int(len(dd)))
    comp = [c for c in ("gold_param_n", "gold_enum_share", "gold_verb_coverage", "gold_desc_tokens") if c in d]
    if not comp:
        raise SystemExit("ABORT: no completeness comparator column survived the merge, so H2 would compare the "
                         "discriminability score against nothing")
    d = d.dropna(subset=comp + ["reachable"])
    ladder = [dict(rung="completeness_only", terms=comp, k=len(comp),
                   auroc=round(auroc(d["reachable"], np.asarray(_fit(d, comp).fittedvalues)), 4)),
              dict(rung="plus_lexical_discriminability", terms=comp + ["lex_z"], k=len(comp) + 1,
                   auroc=round(auroc(d["reachable"], np.asarray(_fit(d, comp + ["lex_z"]).fittedvalues)), 4))]
    delta = clustered_auroc_delta(d, comp + ["lex_z"], comp, draws=400, y="reachable")
    d["big"] = (d["n_candidates"] >= d["n_candidates"].median()).astype(float)
    d["lex_x_big"] = d["lex_z"] * d["big"]
    hi = term(W.glm_term(d, "reachable", ["lex_z", "big", "lex_x_big"], "binomial"), "lex_x_big") or {}
    # H3 is a fitted interaction, so its own clustered p belongs to the family. It had been entered as 1.0, which
    # made a term whose CI is far from zero print p_holm = 1 - a wrong statement in the package, not a conservative one.
    ps = {"H1": float(h1.get("p_raw", 1.0)), "H2": float(delta.get("p_boot") or 1.0),
          "H3": float(hi.get("p_raw", 1.0))}
    adj = W.holm(ps)
    h1["p_holm"] = adj["H1"]
    h1["verdict"] = W.verdict(h1.get("beta"), h1.get("ci_lo"), h1.get("ci_hi"), adj["H1"], BAND)
    h2 = dict(hypothesis="H2", term_name="discriminability_over_completeness_auroc",
              term="discriminability_over_completeness_auroc", **delta)
    h2["p_holm"] = adj["H2"]
    h2["verdict"] = W.magnitude_verdict(delta.get("delta"), (delta.get("ci") or [None, None])[0],
                                        (delta.get("ci") or [None, None])[1], adj["H2"], floor=0.02, side="pos")
    h3 = dict(hi)
    h3.update(hypothesis="H3", term="discriminability_x_catalogue_size", dv="reachable", p_holm=adj["H3"],
              note="a fitted interaction with a clustered standard error, not the difference of two subgroup slopes")
    h3["verdict"] = W.verdict(h3.get("beta"), h3.get("ci_lo"), h3.get("ci_hi"), adj["H3"], BAND)
    for i, h in ((0, "H1"), (1, "H2")):
        h_ = dict(h1 if i == 0 else h2)
        h_["hypothesis"] = h_["hypothesis"] if "hypothesis" in h_ else h
        rows.append(h_)
    half = []
    for lab, g in (("small_catalogue", d[d["big"] == 0]), ("large_catalogue", d[d["big"] == 1])):
        t = term(W.glm_term(g, "reachable", ["lex_z"], "binomial"), "lex_z") or {}
        half.append(dict(stratum=lab, n_rows=int(len(g)), n_queries=int(g["query_id"].nunique()),
                          reachable_rate=round(float(g["reachable"].mean()), 4),
                          **{k: t.get(k) for k in ("beta", "se", "ci_lo", "ci_hi", "p")}))
    strat = half
    rows += [h3] + ([second] if second else [])
    return {"models": rows, "strata": strat, "holm": adj, "ladder": ladder, "completeness_terms": comp,
            "n_queries": int(len(d)), "queries_excluded_no_neighbours": n_thin,
            "dense_instrument_available": have_dense, "second_instrument": second,
            "ladder_note": "H2 is the clustered bootstrap of the AUROC step from the completeness set to that set "
                           "plus lexical discriminability; the two rungs are in `ladder`"}

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--only", action="append", default=[])
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    Q, C = load()
    arts = {}
    todo = {"EXP-0145": lambda: t113(Q), "EXP-0146": lambda: t119(C),
            "EXP-0147": lambda: t120(Q, C), "EXP-0148": lambda: t122(Q, C)}
    if a.only:                                    # declared but not honoured in the first version, so --only ran all four
        unknown = [x for x in a.only if x not in todo]
        if unknown:
            raise SystemExit(f"ABORT: --only names no design: {unknown}; valid ids are {sorted(todo)}")
        todo = {k: v for k, v in todo.items() if k in a.only}
    for exp, fn in todo.items():
        art = fn()
        art.update(exp_id=exp, seed=W.SEED, quick=a.quick, started_at=W.now(),
                   invocation=" ".join([sys.executable] + sys.argv),
                   run_cost=W.run_cost_row(exp, t0, 0, 0, "wave-3 design"), finished_at=W.now())
        arts[exp] = art
        print(f"{exp}: wrote {W.write_raw(exp, 'wave3_design_' + exp[-4:], art).name}", flush=True)
    stems = {"EXP-0145": "t113", "EXP-0146": "t119", "EXP-0147": "t120", "EXP-0148": "t122"}
    for exp, art in arts.items():
        st = stems[exp]
        pd.DataFrame(art.get("models") or []).to_csv(W.OUT / f"EXP{exp[-4:]}_{st}_models.csv", index=False)
        if art.get("ladder"):
            pd.DataFrame(art["ladder"]).to_csv(W.OUT / f"EXP{exp[-4:]}_{st}_auroc_ladder.csv", index=False)
        if art.get("second_instrument"):
            pd.DataFrame([art["second_instrument"]]).to_csv(W.OUT / f"EXP{exp[-4:]}_{st}_second_instrument.csv",
                                                            index=False)
    for exp, art in arts.items():
        vs = {(m.get("hypothesis") or m.get("term")): m.get("verdict") for m in (art.get("models") or [])
              if isinstance(m, dict)}
        print(f"  {exp}: {json.dumps(vs, default=str)[:220]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
