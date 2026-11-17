"""EXP-0183..EXP-0188: wave 7's six pre-registered tests, run from the frozen sentences in topic_designs_wave7.

No threshold is decided here. Each hypothesis carries the band floor and direction its freeze names, Holm is applied to
the hypotheses of one design together and to nothing else, and every interval is cluster-robust on the unit that
hypothesis's own sentence names: the query for the six ranker-behaviour tests, the server for T165's specialisation
difference, the tool pair for T169's. A cell a premise gate scoped out is reported as `not_testable_*` with the count
that produced it beside it, which is a result rather than a gap to close by moving a floor - T166's H1 is exactly that
case, and its coefficient is still printed so the reader can see what the limited claim would have been.

One boundary governs the whole wave and is repeated in each artifact: the release records a frozen lexical ranker's
ordering of a candidate catalogue, not an agent's choice, so every dependent variable here is what BM25 did with the
catalogue's language (deviation W7-D02 in the freeze).

    python 02_shared_code/package_factory/exp_wave7_designs.py [--quick] [--only EXP-0183]
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np                                                # noqa: E402
import pandas as pd                                               # noqa: E402
import wave_lib as W                                              # noqa: E402
import topic_designs_wave7 as TD7                                  # noqa: E402

assert TD7.BANDS == W.BANDS, "the wave-7 freeze and wave_lib disagree about the effect bands"
BAND = W.BANDS["medium"]
BAND_SMALL = W.BANDS["small"]
CLUSTER = TD7.COMMON["sample"]["cluster_unit"]                    # "query_id"
FRAMES = {"query": "EXP0182_wave7_candidate_features.csv.gz", "server": "EXP0182_wave7_server_pairs.csv.gz",
          "pair": "EXP0182_wave7_gold_pairs.csv.gz", "roster": "EXP0182_wave7_tool_roster.csv.gz",
          "overlap": "EXP0182_wave7_overlap_pairs.csv.gz"}
# The freeze's "standard controls", one definition for the wave: how many tools the query was offered and how long the
# instruction was. Nothing else is a control anywhere in this wave - where a hypothesis names a further control (T161's
# description length, T164's server count) that term is added by the design that promised it, never silently.
CTRL = ["log_candidates", "question_words_log"]
# the controls on the drawn-overlap frame: a pair's overlap can only be read against how much text each side has
CTRL_PAIR = ["log_tool_words", "log_partner_words"]


def z(s: pd.Series) -> pd.Series:
    v = pd.to_numeric(s, errors="coerce")
    sd = float(v.std(ddof=0))
    return (v - float(v.mean())) / sd if sd > 0 else v * 0.0


def _frame(kind: str) -> pd.DataFrame:
    name = FRAMES[kind]
    search = []
    if os.environ.get("AIB_INPUT_DIR"):
        search.append(pathlib.Path(os.environ["AIB_INPUT_DIR"]) / name)
    search += [W.OUT / name, W.ROOT / "results_processed" / name]
    path = next((q for q in search if pathlib.Path(q).is_file()), None)
    if path is None:
        raise SystemExit(f"ABORT: {name} is not where the designs look ({', '.join(map(str, search))}) - run "
                         f"{TD7.FEATURE_EXP} (exp_wave7_features.py) first")
    # encoding is explicit because the release carries non-ASCII tool names and this platform's locale default is not
    # UTF-8: without it the same script reads fine here and dies on the rebuild machine.
    F = pd.read_csv(gzip.open(path, "rt", encoding="utf-8"))
    F.attrs["frame_file"] = str(path)
    return F


def load() -> dict:
    """The four wave-7 frames with the derived contrasts the freeze names. Column names are checked, not guessed."""
    F = _frame("query")
    need = ["query_id", "cfg", "n_candidates", "n_gold", "fail_at_1", "bm25_best_rank", "bm25_margin", "margin_z",
            "decoy_present", "decoy_count", "max_similarity", "control_similarity", "affordance_density",
            "afford_density_z", "gold_has_params", "gold_param_words", "desc_words", "namespaced_share",
            "distinct_servers", "server_concentration", "irrelevant_share", "irrelevant_above_gold", "contaminated",
            "log_candidates", "question_words_log", "cand_quartile", "server_quartile", "top_pair",
            "max_pair_frequency", "pair_frequent", "multi_gold", "gold_names"]
    miss = [c for c in need if c not in F.columns]
    if miss:
        raise SystemExit(f"ABORT: the wave-7 frame lacks {miss}; the designs would drop those terms in silence")
    F["desc_words_log"] = np.log1p(F["desc_words"].astype(float))
    F["decoy_count_capped"] = F["decoy_count"].clip(upper=5).astype(int)
    F["ctrl_sim_z"] = z(F["control_similarity"].astype(float))
    F["max_sim_z"] = z(F["max_similarity"].astype(float))
    F["irrelevant_share_z"] = z(F["irrelevant_share"].astype(float))
    F["param_words_z"] = z(F["gold_param_words"].astype(float))
    F["namespaced_z"] = z(F["namespaced_share"].astype(float))
    F["servers_z"] = z(F["distinct_servers"].astype(float))
    F["conc_z"] = z(F["server_concentration"].astype(float))
    for q in ("q2", "q3", "q4_largest"):
        F[f"cand_{q}"] = (F["cand_quartile"] == q).astype(int)
    P = _frame("pair")
    if [c for c in ("pair", "frequency", "overlap", "random_overlap") if c not in P.columns]:
        raise SystemExit("ABORT: the gold-pair frame lacks a column T169's H2 bootstraps over")
    S = _frame("server")
    if [c for c in ("server", "tools", "within_overlap", "across_overlap", "diff") if c not in S.columns]:
        raise SystemExit("ABORT: the server frame lacks a column T165's H1 bootstraps over")
    R = _frame("roster")
    if [c for c in ("name", "server", "local_name", "desc_words", "n_params", "times_offered", "queries")
            if c not in R.columns]:
        raise SystemExit("ABORT: the tool roster lacks a column T165's H2 and H3 count")
    # the query's strongest co-needed pair, carried back onto the query rows it came from
    F["pair_overlap"] = F["top_pair"].map(P.set_index("pair")["overlap"])
    F["pair_random_overlap"] = F["top_pair"].map(P.set_index("pair")["random_overlap"])
    F["pair_freq_band"] = pd.cut(F["max_pair_frequency"], [-0.5, 0.5, 9.5, 1e9],
                                 labels=["0_no_pair_or_once", "1_2to9_queries", "2_10plus_queries"]).astype(str)
    S["log_tools"] = np.log1p(S["tools"].astype(float))
    S["size_decile"] = pd.qcut(S["tools"].rank(method="first"), 10, labels=False, duplicates="drop").astype(int)
    multi = R.assign(multi=R.groupby("local_name")["server"].transform("nunique") >= 2)
    S["reused_names"] = S["server"].map(multi[multi["multi"]].groupby("server").size()).fillna(0).astype(int)
    O = _frame("overlap")
    if [c for c in ("tool", "server", "partner", "partner_server", "same_server", "jaccard", "tool_words",
                    "partner_words") if c not in O.columns]:
        raise SystemExit("ABORT: the drawn-overlap frame lacks a column T165's regression reads")
    O["log_tool_words"] = np.log1p(O["tool_words"].astype(float))
    O["log_partner_words"] = np.log1p(O["partner_words"].astype(float))
    return {"F": F, "S": S, "P": P, "R": R, "O": O}


def glm(d: pd.DataFrame, y: str, xs, family="binomial", cluster=CLUSTER) -> pd.DataFrame:
    """The frozen model for one term, with the outcome never allowed to be its own regressor.

    A design that names a control equal to its dependent variable (T166's H1 standardises the margin it then controls
    on) would otherwise arrive at a two-column design matrix that is not identified at all. Zero-variance terms are
    dropped and named in attrs, which `term()` copies into the reported row.
    """
    xs = [c for c in dict.fromkeys(xs) if c in d.columns and c != y]
    d = d.dropna(subset=[y] + xs)
    if d.empty:
        return pd.DataFrame()
    const = [c for c in xs if d[c].nunique(dropna=False) <= 1]
    xs = [c for c in xs if c not in const]
    if not xs:
        return pd.DataFrame()
    if family == "binomial":
        vals = set(np.unique(d[y].astype(float)))
        if not vals <= {0.0, 1.0}:
            raise SystemExit(f"ABORT: {y} takes {len(vals)} distinct values and is not 0/1, so the binomial link "
                             f"would model a quantity that has no probability reading - pass family='gaussian'")
        if len(vals) < 2:
            return pd.DataFrame()
    f = W.glm_term(d, y, xs, family, cluster=cluster)
    if f is not None and not f.empty:
        f.attrs["dropped_constant_terms"] = "+".join(const) or "none"
        f.attrs["cluster"] = cluster
    return f


def term(f: pd.DataFrame, name: str) -> dict:
    if f is None or f.empty or "term" not in f.columns:
        return {}
    r = f[f["term"] == name]
    if r.empty:
        return {}
    out = {}
    for k in ("beta", "se", "ci_lo", "ci_hi", "p", "n"):
        if k in r.columns:
            out[k] = int(r.iloc[0][k]) if k == "n" else (None if r.iloc[0][k] is None or
                                                         (isinstance(r.iloc[0][k], float) and not np.isfinite(
                                                             r.iloc[0][k])) else round(float(r.iloc[0][k]), 4))
    if f.attrs.get("dropped_constant_terms"):
        out["dropped_constant_terms"] = f.attrs["dropped_constant_terms"]
    if f.attrs.get("cluster"):
        out["cluster"] = f.attrs["cluster"]
    return out


def boot(d: pd.DataFrame, cluster: str, fn, draws: int = 2000) -> dict:
    return W.cluster_boot_ci_and_p(d, cluster, fn, draws=draws, seed=TD7.SEED)


def _finite(v) -> bool:
    try:
        return bool(np.isfinite(float(v)))
    except (TypeError, ValueError):
        return False


def holm_and_verdict(rows: list, direction: dict, band: float = BAND) -> list:
    """Holm over the hypotheses of this design that produced a p-value, then the frozen three-way rule.

    A row whose verdict its own freeze sentence already decides - a descriptive quantity T165 asks to be reported
    rather than tested, or a cell EXP-0181's gate scoped out - keeps that verdict and stays out of the family, because
    multiplying a real p by the count of untestable rows would move a verdict without measuring anything.
    """
    fam = {r["hypothesis"]: float(r["p"]) for r in rows
           if r.get("p") is not None and _finite(r.get("p")) and not r.get("verdict")}
    adj = W.holm(fam) if fam else {}
    for r in rows:
        if r.get("verdict"):
            r.setdefault("p_holm", adj.get(r["hypothesis"]))
            continue
        r["p_holm"] = adj.get(r["hypothesis"], 1.0)
        if r.get("verdict_rule") in ("specificity", "sign_reproduction", "dose_response", "descriptive"):
            continue
        if r.get("beta") is None:
            r["verdict"] = "not_testable_no_coefficient_estimated"
            continue
        if not all(_finite(v) for v in (r["beta"], r.get("ci_lo"), r.get("ci_hi"), r.get("p"))):
            r["verdict"] = "not_estimable_non_finite_interval"
            r.setdefault("note", "the interval or the coefficient is not finite on these rows, so no direction is "
                                 "claimed; the raw values are kept in this row")
            continue
        r["verdict"] = W.verdict(r["beta"], r.get("ci_lo"), r.get("ci_hi"), r["p_holm"], band,
                                 direction=direction.get(r["hypothesis"], 1.0))
    return rows


def baselines(d: pd.DataFrame, y: str, specs, family="binomial", controls=None, cluster=CLUSTER) -> list:
    """The controls-only model, then each construct added, with the deviance drop between them."""
    from scipy import stats as SP
    controls = controls or CTRL
    base = glm(d, y, controls, family, cluster)
    if base is None or base.empty:
        return [dict(model="controls_only", dv=y, note="not fitted on these rows")]
    dev0 = float(base["deviance"].iloc[0])
    kept = lambda cols: [c for c in dict.fromkeys(cols) if c in d.columns and c != y]
    rows = [dict(model="controls_only", dv=y, terms="+".join(controls), n=int(base["n"].iloc[0]),
                 clusters=int(d[cluster].nunique()), deviance=round(dev0, 2))]
    for name, xs, focus in specs:
        f = glm(d, y, xs, family, cluster)
        if f is None or f.empty:
            rows.append(dict(model=name, dv=y, terms="+".join(dict.fromkeys(xs)),
                             note="not fitted: the design matrix cannot be estimated on these rows"))
            continue
        dev1 = float(f["deviance"].iloc[0])
        dfree = max(1, len(kept(xs)) - len(kept(controls)))
        lr = 2.0 * (dev0 - dev1)
        rows.append(dict(model=name, dv=y, terms="+".join(dict.fromkeys(xs)), n=int(f["n"].iloc[0]),
                         deviance=round(dev1, 2), added_term=focus, deviance_drop=round(dev0 - dev1, 2),
                         lr_chi2=round(lr, 2), lr_df=dfree,
                         lr_p=round(float(SP.chi2.sf(max(lr, 0.0), dfree)), 6),
                         **{f"{focus}_{k}": v for k, v in term(f, focus).items() if k != "n"}))
    return rows


def strata_rows(d: pd.DataFrame, splits, y: str, xs, focus: str, min_rows: int = 1000, family="binomial",
                cluster=CLUSTER) -> list:
    rows = []
    for col in splits:
        for lab, g in d.groupby(col, observed=True):
            if len(g) < min_rows or g[y].nunique() < 2:
                continue
            kept = [c for c in xs if c in g.columns and g[c].nunique(dropna=False) > 1]
            dropped = [c for c in xs if c not in kept]
            t = term(glm(g, y, kept, family, cluster), focus)
            t.pop("dropped_constant_terms", None)
            rows.append(dict(stratification=col, stratum=str(lab)[:40], rows=int(len(g)),
                             clusters=int(g[cluster].nunique()),
                             dropped_constant_terms="+".join(dropped) or "none",
                             identifiable=focus in kept, **t))
    return rows


def share_by(d: pd.DataFrame, col, y: str, cluster=CLUSTER, draws: int = 500) -> dict:
    out = {}
    for lab, g in d.groupby(col, observed=True):
        b = boot(g, cluster, lambda x: float(pd.to_numeric(x[y], errors="coerce").mean()), draws)
        out[str(lab)[:40]] = {"rate": round(float(g[y].mean()), 4), "rows": int(len(g)),
                              "clusters": int(g[cluster].nunique()),
                              "ci": b.get("ci"), "p": b.get("p")}
    return out


# ------------------------------------------------------------------ the six designs
def t161(fr: dict) -> dict:
    F = fr["F"]
    h1 = term(glm(F, "fail_at_1", ["decoy_present"] + CTRL), "decoy_present")
    h1.update(hypothesis="H1", term="near_synonym_decoy_present_on_missing_the_gold_at_rank_1",
              queries_with_a_decoy=int(F["decoy_present"].sum()), decoy_share=round(float(F["decoy_present"].mean()), 4))
    h1["verdict_direction"] = "predicted_positive: a look-alike in the list is associated with the gold not coming first"
    prof = []
    for k in sorted(F["decoy_count_capped"].unique()):
        g = F[F["decoy_count_capped"] == k]
        b = boot(g, CLUSTER, lambda x: float(x["fail_at_1"].mean()), 1000)
        if "ci" in b:
            prof.append(dict(decoy_count=int(k), rows=int(len(g)),
                             fail_at_1_rate=round(float(g["fail_at_1"].mean()), 4),
                             ci_lo=round(float(b["ci"][0]), 4), ci_hi=round(float(b["ci"][1]), 4),
                             clusters=int(b["clusters"])))
    rank_term = term(glm(F, "bm25_best_rank", ["decoy_count_capped"] + CTRL, "poisson"), "decoy_count_capped")
    used = [p for p in prof if p["rows"] >= 500]
    rising = all(a["fail_at_1_rate"] <= b["fail_at_1_rate"] for a, b in zip(used, used[1:])) and len(used) >= 3 \
        and any(a["fail_at_1_rate"] < b["fail_at_1_rate"] for a, b in zip(used, used[1:]))
    h2 = dict(hypothesis="H2", term="fail_at_1_profile_by_number_of_decoys_in_the_catalogue",
              verdict_rule="dose_response", profile=prof, levels_with_500plus_rows=len(used),
              rank_model_under_the_same_count=rank_term,
              verdict=("supported" if rising else
                       f"not_monotone_in_{len(used)}_measured_levels" if used else "not_testable_no_decoy_levels"))
    h2["note"] = ("the frozen claim is a dose-response rather than a threshold, so the verdict is the monotonicity of "
                  "the measured profile; the rank model is printed beside it, not as the test")
    a3 = term(glm(F, "fail_at_1", ["decoy_present", "log_candidates", "question_words_log", "desc_words_log"]),
              "decoy_present")
    b3 = term(glm(F.dropna(subset=["control_similarity"]), "fail_at_1",
                  ["ctrl_sim_z", "log_candidates", "question_words_log", "desc_words_log"]), "ctrl_sim_z")
    c3 = term(glm(F, "fail_at_1", ["irrelevant_share_z", "log_candidates", "question_words_log", "desc_words_log"]),
              "irrelevant_share_z")

    def null_ci(t):
        return t.get("beta") is not None and t.get("ci_lo") is not None and t["ci_lo"] <= 0 <= t["ci_hi"]
    h3 = dict(hypothesis="H3", term="decoy_presence_against_a_random_candidate_and_question_overlap",
              verdict_rule="specificity", decoy_arm=a3, random_candidate_arm=b3, question_overlap_arm=c3,
              rows_in_random_arm=int(F["control_similarity"].notna().sum()),
              note="H3 is supported when the decoy still separates with count and description length held and the "
                   "randomly chosen candidate's similarity produces nothing; the question-overlap arm is the second "
                   "reading of the same sentence (deviation W7-D07)")
    sep = a3.get("beta") is not None and abs(a3["beta"]) >= BAND_SMALL and a3.get("ci_lo") is not None \
        and (a3["ci_lo"] > 0 or a3["ci_hi"] < 0)
    h3["verdict"] = ("supported" if sep and null_ci(b3) and null_ci(c3) else
                     "not_specific_a_control_tracks_the_same_variance" if a3 else
                     "not_testable_no_coefficient_estimated")
    # the arm the rule turns on is also what carries this row's p into the design's declared Holm family of three
    h3.update({k: a3.get(k) for k in ("beta", "se", "ci_lo", "ci_hi", "p")})
    rows = holm_and_verdict([h1, h2, h3], {"H1": 1.0, "H3": 1.0})
    return dict(n_queries=int(len(F)), n_clusters=int(F[CLUSTER].nunique()),
                n_candidates_offered=int(F["n_candidates"].sum()), cluster_unit=CLUSTER, models=rows,
                strata=strata_rows(F, ["cand_quartile", "cfg"], "fail_at_1", ["decoy_present"] + CTRL,
                                   "decoy_present"),
                baselines=baselines(F, "fail_at_1", [("controls_plus_decoy_indicator", ["decoy_present"] + CTRL,
                                                      "decoy_present"),
                                                     ("controls_plus_continuous_similarity", ["max_sim_z"] + CTRL,
                                                      "max_sim_z"),
                                                     ("controls_plus_random_candidate_similarity",
                                                      ["ctrl_sim_z"] + CTRL, "ctrl_sim_z")]),
                descriptive_rates={"fail_at_1_by_decoy_count": share_by(F, "decoy_count_capped", "fail_at_1"),
                                   "decoy_count_distribution": {str(int(k)): int(v) for k, v in
                                                                F["decoy_count_capped"].value_counts().sort_index()
                                                                .items()},
                                   "mean_max_similarity_by_config": {
                                       str(k): {"max_similarity": round(float(g["max_similarity"].mean()), 4),
                                                "fail_at_1": round(float(g["fail_at_1"].mean()), 4),
                                                "rows": int(len(g))}
                                       for k, g in F.groupby("cfg", observed=True)},
                                   "fail_at_1_by_candidate_quartile": share_by(F, "cand_quartile", "fail_at_1")},
                gate_scope=TD7.DESIGNS["T161"]["gate_scope"])


def t162(fr: dict) -> dict:
    F = fr["F"]
    h1 = term(glm(F, "fail_at_1", ["afford_density_z"] + CTRL), "afford_density_z")
    h1.update(hypothesis="H1", term="affordance_verb_density_in_the_gold_description_on_missing_at_rank_1",
              gold_descriptions_without_a_verb=int((F["affordance_verbs"] if "affordance_verbs" in F else
                                                    (F["affordance_density"] > 0)).sum()),
              density_mean=round(float(F["affordance_density"].mean()), 4))
    h1["verdict_direction"] = "predicted_negative: a description that says what it does is easier to rank first"
    h2 = term(glm(F, "fail_at_1", ["gold_has_params"] + CTRL), "gold_has_params")
    h2.update(hypothesis="H2", term="gold_candidate_naming_its_parameters_on_missing_at_rank_1",
              queries_without_params_on_the_gold=int((F["gold_has_params"] == 0).sum()),
              gold_has_params_share=round(float(F["gold_has_params"].mean()), 4),
              param_words_mean=round(float(F["gold_param_words"].mean()), 3))
    h2["verdict_direction"] = "predicted_negative: the words an agent searches with are parameter names"
    joint = term(glm(F, "fail_at_1", ["afford_density_z", "gold_has_params", "desc_words_log"] + CTRL),
                 "gold_has_params")
    length = term(glm(F, "fail_at_1", ["desc_words_log"] + CTRL), "desc_words_log")
    length_together = term(glm(F, "fail_at_1", ["afford_density_z", "gold_has_params", "desc_words_log"] + CTRL),
                           "desc_words_log")
    rho = W.rho_ci(F[[("affordance_density"), ("gold_has_params"), CLUSTER]].dropna(), CLUSTER, "affordance_density",
                   "gold_has_params")
    h3 = dict(hypothesis="H3", term="parameters_and_affordance_language_are_not_the_same_signal",
              verdict_rule="specificity", joint_model_parameter_term=joint, length_alone=length,
              length_in_the_joint_model=length_together, collinearity_of_the_two_measures=rho,
              note="the freeze scopes H3 to whether parameter presence still adds once density is in and description "
                   "length adds nothing once both are; the correlation of the two measures is reported whether or not "
                   "it bites, as the kill-gate sentence promised")
    adds = joint.get("beta") is not None and joint.get("ci_lo") is not None and (
        joint["ci_lo"] > 0 or joint["ci_hi"] < 0)
    len_null = length_together.get("beta") is not None and length_together["ci_lo"] is not None and \
        length_together["ci_lo"] <= 0 <= length_together["ci_hi"]
    h3["verdict"] = ("supported" if adds and len_null else
                     "not_specific_length_carries_the_same_signal" if joint else "not_testable_no_coefficient_estimated")
    h3.update({k: joint.get(k) for k in ("beta", "se", "ci_lo", "ci_hi", "p")})
    rows = holm_and_verdict([h1, h2, h3], {"H1": -1.0, "H2": -1.0, "H3": -1.0})
    return dict(n_queries=int(len(F)), n_clusters=int(F[CLUSTER].nunique()),
                n_candidates_offered=int(F["n_candidates"].sum()), cluster_unit=CLUSTER, models=rows,
                strata=strata_rows(F, ["cand_quartile", "cfg"], "fail_at_1", ["afford_density_z"] + CTRL,
                                   "afford_density_z"),
                baselines=baselines(F, "fail_at_1", [("controls_plus_affordance_density", ["afford_density_z"] + CTRL,
                                                      "afford_density_z"),
                                                     ("controls_plus_parameter_indicator",
                                                      ["gold_has_params"] + CTRL, "gold_has_params"),
                                                     ("controls_plus_both_plus_length",
                                                      ["afford_density_z", "gold_has_params", "desc_words_log"] + CTRL,
                                                      "desc_words_log")]),
                descriptive_rates={"fail_at_1_by_density_quartile": share_by(
                    F.assign(dq=pd.qcut(F["affordance_density"].rank(method="first"), 4,
                                         labels=["d1_tersest", "d2", "d3", "d4_densest"]).astype(str)),
                    "dq", "fail_at_1"),
                    "fail_at_1_by_parameter_presence": share_by(F, F["gold_has_params"].astype(str), "fail_at_1"),
                    "margin_by_density_quartile": {
                        str(k): {"mean_margin": round(float(g["bm25_margin"].mean()), 4), "rows": int(len(g))}
                        for k, g in F.assign(dq=pd.qcut(F["affordance_density"].rank(method="first"), 4,
                                                        labels=["d1_tersest", "d2", "d3",
                                                                "d4_densest"]).astype(str)).groupby("dq",
                                                                                                   observed=True)},
                    "verbs_per_gold_description": {str(int(k)): int(v) for k, v in
                                                   F["affordance_verbs"].value_counts().sort_index().head(8).items()}},
                gate_scope=TD7.DESIGNS["T162"]["gate_scope"])


def t164(fr: dict) -> dict:
    F = fr["F"]
    h1 = term(glm(F, "fail_at_1", ["namespaced_z"] + CTRL), "namespaced_z")
    h1.update(hypothesis="H1", term="namespace_separator_share_within_a_catalogue_on_missing_at_rank_1",
              fully_grouped_queries=int((F["namespaced_share"] == 1).sum()),
              fully_ungrouped_queries=int((F["namespaced_share"] == 0).sum()),
              mean_namespaced_share=round(float(F["namespaced_share"].mean()), 4))
    h1["verdict_direction"] = "predicted_negative: a grouped candidate set is easier to rank correctly"
    h2 = term(glm(F, "fail_at_1", ["cand_q2", "cand_q3", "cand_q4_largest"] + CTRL), "cand_q4_largest")
    h2.update(hypothesis="H2", term="fourth_versus_first_candidate_count_quartile_on_missing_at_rank_1",
              q1_rate=round(float(F[F["cand_quartile"] == "q1_smallest"]["fail_at_1"].mean()), 4),
              q4_rate=round(float(F[F["cand_quartile"] == "q4_largest"]["fail_at_1"].mean()), 4),
              verdict_note="estimated without the namespace share, because the frozen sentence asks for the count "
                           "association separately so that one cannot be credited to the other")
    h2["verdict_direction"] = "predicted_positive: a larger candidate set is missed more often"
    full = term(glm(F, "fail_at_1", ["namespaced_z", "servers_z", "conc_z"] + CTRL), "namespaced_z")
    conc = term(glm(F, "fail_at_1", ["namespaced_z", "servers_z", "conc_z"] + CTRL), "conc_z")
    margin = term(glm(F, "margin_z", ["namespaced_z", "servers_z", "conc_z"] + CTRL, "gaussian"),
                  "conc_z")
    h3 = dict(hypothesis="H3", term="the_namespace_share_after_server_concentration_enters",
              verdict_rule="specificity", namespace_in_the_competing_model=full, concentration_term=conc,
              secondary_reading_on_the_rankers_margin=margin,
              note="H3 is supported when the namespace share falls to nothing once the number of distinct sources and "
                   "their concentration are in the same specification")
    gone = full.get("beta") is not None and full.get("ci_lo") is not None and full["ci_lo"] <= 0 <= full["ci_hi"]
    was = h1.get("beta") is not None and h1.get("ci_lo") is not None and (h1["ci_lo"] > 0 or h1["ci_hi"] < 0)
    h3["verdict"] = ("supported" if gone and was else
                     "not_specific_namespace_share_still_separates" if full else
                     "not_testable_no_coefficient_estimated")
    h3.update({k: full.get(k) for k in ("beta", "se", "ci_lo", "ci_hi", "p")})
    rows = holm_and_verdict([h1, h2, h3], {"H1": -1.0, "H2": 1.0})
    return dict(n_queries=int(len(F)), n_clusters=int(F[CLUSTER].nunique()),
                n_candidates_offered=int(F["n_candidates"].sum()), cluster_unit=CLUSTER, models=rows,
                strata=strata_rows(F, ["cand_quartile", "server_quartile"], "fail_at_1",
                                   ["namespaced_z"] + CTRL, "namespaced_z"),
                baselines=baselines(F, "fail_at_1", [("controls_plus_namespace_share", ["namespaced_z"] + CTRL,
                                                      "namespaced_z"),
                                                     ("controls_plus_candidate_count_as_a_quartile_factor",
                                                      ["cand_q2", "cand_q3", "cand_q4_largest"] + CTRL,
                                                      "cand_q4_largest"),
                                                     ("controls_plus_namespace_and_servers",
                                                      ["namespaced_z", "servers_z", "conc_z"] + CTRL,
                                                      "conc_z")]),
                descriptive_rates={"fail_at_1_by_grouping_arm": share_by(
                    F.assign(arm=pd.cut(F["namespaced_share"], [-0.01, 0.001, 0.999, 1.01],
                                        labels=["ungrouped", "mixed", "all_namespaced"]).astype(str)),
                    "arm", "fail_at_1"),
                    "fail_at_1_by_candidate_quartile": share_by(F, "cand_quartile", "fail_at_1"),
                    "fail_at_1_by_server_quartile": share_by(F, "server_quartile", "fail_at_1"),
                    "mean_servers_and_concentration_by_grouping": {
                        str(k): {"distinct_servers": round(float(g["distinct_servers"].mean()), 3),
                                 "concentration": round(float(g["server_concentration"].mean()), 4),
                                 "rows": int(len(g))}
                        for k, g in F.assign(arm=pd.cut(F["namespaced_share"], [-0.01, 0.001, 0.999, 1.01],
                                                        labels=["ungrouped", "mixed",
                                                                "all_namespaced"]).astype(str)).groupby("arm",
                                                                                                       observed=True)}},
                gate_scope=TD7.DESIGNS["T164"]["gate_scope"])


def t165(fr: dict) -> dict:
    S, R = fr["S"], fr["R"]
    obs = float(S["diff"].mean())
    b = boot(S, "server", lambda x: float(x["diff"].mean()))
    h1 = dict(hypothesis="H1", term="within_server_minus_across_server_description_overlap",
              beta=round(obs, 4), ci_lo=(b.get("ci") or [None, None])[0], ci_hi=(b.get("ci") or [None, None])[1],
              p=b.get("p"), n=int(len(S)), clusters=b.get("clusters"),
              within_mean=round(float(S["within_overlap"].mean()), 4),
              across_mean=round(float(S["across_overlap"].mean()), 4),
              note="the estimand is a bootstrapped difference over servers, not a regression coefficient; the "
                   "frozen band is applied to it in the same units. No regression is fitted on the 184 servers "
                   "themselves, because wave_lib's shared 200-row guard - the instrument every earlier wave cleared "
                   "- refuses a cluster-robust fit that thin; the drawn-pair reading below is the second estimate")
    h1["verdict_direction"] = "predicted_positive: a server's own tools share vocabulary with each other"
    h1["second_reading_on_drawn_pairs"] = term(glm(fr["O"], "jaccard", ["same_server"] + CTRL_PAIR, "gaussian",
                                                   cluster="tool"), "same_server")
    slots = float(R["times_offered"].sum())
    srv_share = R.groupby("server")["times_offered"].sum().sort_index().sort_values(ascending=False,
                                                                                     kind="mergesort")
    h2 = dict(hypothesis="H2", term="the_catalogue_population_is_not_concentrated", verdict_rule="descriptive",
              servers=int(R["server"].nunique()), distinct_tools=int(len(R)), candidate_slots=int(slots),
              herfindahl_over_servers=round(float(((srv_share / slots) ** 2).sum()), 4),
              top12_server_share=round(float(srv_share.head(12).sum() / slots), 4),
              largest_server=str(srv_share.index[0]), largest_server_share=round(float(srv_share.iloc[0] / slots), 4),
              p=None, verdict="measured_descriptively_no_band_was_frozen")
    h2["note"] = ("the frozen sentence asks for the concentration facts as structure rather than as a hypothesis "
                  "about a rank, so no band applies and none is invented")
    ln = R.groupby("local_name")["server"].nunique()
    h3 = dict(hypothesis="H3", term="local_tool_names_published_by_more_than_one_server",
              verdict_rule="descriptive", distinct_local_names=int(ln.size),
              local_names_under_2plus_servers=int((ln >= 2).sum()),
              share_of_local_names_reused_across_servers=round(float((ln >= 2).mean()), 4),
              most_reused_local_names={str(k): int(v) for k, v in
                                       ln.sort_index().sort_values(ascending=False, kind="mergesort")
                                       .head(10).items()},
              p=None, verdict="measured_descriptively_no_band_was_frozen")
    h3["note"] = ("'many sources' and 'many distinct services' are different counts, and this row is the place the "
                  "freeze fixes the difference")
    rows = holm_and_verdict([h1, h2, h3], {"H1": 1.0})
    dec = []
    for k, g in S.groupby("size_decile", observed=True):
        bb = boot(g, "server", lambda x: float(x["diff"].mean()), 1000)
        dec.append(dict(stratification="server_size_decile", stratum=f"d{int(k) + 1}", servers=int(len(g)),
                        median_tools=float(g["tools"].median()),
                        within_overlap=round(float(g["within_overlap"].mean()), 4),
                        across_overlap=round(float(g["across_overlap"].mean()), 4),
                        diff=round(float(g["diff"].mean()), 4), ci_lo=(bb.get("ci") or [None, None])[0],
                        ci_hi=(bb.get("ci") or [None, None])[1],
                        clusters=bb.get("clusters"), note=("a decile of the 184 usable servers holds fewer than the "
                                                           "30 clusters the bootstrap requires, and that is reported "
                                                           "as an error rather than as a silence")
                        if "error" in bb else ""))
    return dict(n_queries=int(len(fr["F"])), n_clusters=int(S["server"].nunique()),
                n_candidates_offered=int(slots), cluster_unit="server (the unit T165's difference is computed from)",
                models=rows, strata=dec,
                baselines=[dict(model="why_the_regression_is_on_drawn_pairs", dv="jaccard",
                                note="T165's three frozen models are a bootstrap and two censuses, none of them a "
                                     "regression, and the 184 usable servers are below the 200-row floor wave_lib "
                                     "applies to every cluster-robust fit in the programme. The same comparison is "
                                     "therefore estimated a second way, on the 20 same-server and 20 "
                                     "different-server description pairs EXP-0182 drew around each named tool, so a "
                                     "specialisation claim here carries a bootstrap and a coefficient instead of only "
                                     "one of them."),
                           *baselines(fr["O"], "jaccard",
                                      [("drawn_pair_controls", CTRL_PAIR, "log_tool_words"),
                                       ("controls_plus_same_server_partner", CTRL_PAIR + ["same_server"],
                                        "same_server")], family="gaussian", controls=CTRL_PAIR, cluster="tool")],
                descriptive_rates={"largest_servers_by_candidate_slots": {
                    str(k): {"slots": int(v), "share_of_all_slots": round(float(v / slots), 4)}
                    for k, v in srv_share.head(12).items()},
                    "servers_by_tool_count_band": {
                        str(k): {"servers": int(len(g)), "mean_within": round(float(g["within_overlap"].mean()), 4),
                                 "mean_diff": round(float(g["diff"].mean()), 4)}
                        for k, g in S.groupby(pd.cut(S["tools"], [2, 5, 10, 25, 1e9],
                                                     labels=["3to5_tools", "6to10", "11to25", "26plus"]).astype(str),
                                              observed=True)},
                    "overlap_distribution": {"within_p25_p50_p75": [round(float(x), 4) for x in
                                                                    np.percentile(S["within_overlap"],
                                                                                  [25, 50, 75])],
                                             "across_p25_p50_p75": [round(float(x), 4) for x in
                                                                    np.percentile(S["across_overlap"],
                                                                                  [25, 50, 75])]},
                    "tools_per_server": {"mean": round(float(R.groupby("server").size().mean()), 2),
                                         "median": float(R.groupby("server").size().median()),
                                         "max": int(R.groupby("server").size().max())}},
                gate_scope=TD7.DESIGNS["T165"]["gate_scope"])


def t166(fr: dict) -> dict:
    F = fr["F"]
    m = TD7.PREMISES["measured"]
    share = float(F["contaminated"].mean())
    h1 = term(glm(F, "margin_z", ["contaminated"] + CTRL, "gaussian"), "contaminated")
    lim = ((TD7.PREMISES.get("verdict") or {}).get("claim_limited") or {})
    h1.update(hypothesis="H1", term="a_zero_overlap_candidate_ranked_above_the_gold_on_the_rankers_margin",
              contaminated_queries=int(F["contaminated"].sum()), contaminated_share=round(share, 4),
              frozen_floor_share=0.10, census_share_measured=round(float(m["contaminated_queries"]) / float(m["dev_rows"]), 4),
              verdict_direction="predicted_negative: a ranking that puts an irrelevant candidate first is flatter")
    if "G8_contaminated_rankings" in lim:
        h1["verdict"] = "not_testable_premise_floor_share_0p10_measured_" + f"{share:.4f}".replace(".", "p")
        h1["note"] = ("EXP-0181's G8 froze a share floor this cell does not reach, so H1 is limited by its own "
                      f"sentence; the count behind it is {int(F['contaminated'].sum())} queries of {len(F)}, the "
                      "coefficient is printed and is not a test of the scoped claim (deviation W7-D03)")
    cfg = []
    for k, g in F.groupby("cfg", observed=True):
        b1 = boot(g, CLUSTER, lambda x: float(x["contaminated"].mean()), 1000)
        b2 = boot(g, CLUSTER, lambda x: float(x["irrelevant_share"].mean()), 1000)
        cfg.append(dict(config=str(k), queries=int(len(g)),
                        contaminated_share=round(float(g["contaminated"].mean()), 4),
                        contaminated_ci=b1.get("ci"), irrelevant_share_mean=round(float(g["irrelevant_share"].mean()), 4),
                        irrelevant_ci=b2.get("ci"), clusters=int(g[CLUSTER].nunique())))
    h2 = dict(hypothesis="H2", term="contamination_measured_inside_each_config_rather_than_pooled",
              verdict_rule="descriptive", by_config=cfg, p=None,
              spread_across_configs=round(float(max(c["contaminated_share"] for c in cfg) -
                                                 min(c["contaminated_share"] for c in cfg)), 4),
              verdict="measured_per_config_no_band_was_frozen",
              note="the frozen sentence asks for the shares per config and the reason - the configs share the "
                   "candidate sets but not the instructions - so a pooled coefficient would answer a different "
                   "question than the one promised")
    sub = F[F["contaminated"] == 1]
    h3 = term(glm(sub, "irrelevant_above_gold", ["log_candidates", "question_words_log"], "poisson"),
              "log_candidates")
    h3.update(hypothesis="H3", term="catalogue_size_on_the_number_of_contaminating_candidates_above_the_gold",
              contaminated_queries=int(len(sub)), mean_above=round(float(sub["irrelevant_above_gold"].mean()), 3))
    h3["verdict_direction"] = "predicted_positive: contamination is an overload phenomenon"
    rows = holm_and_verdict([h1, h2, h3], {"H1": -1.0, "H3": 1.0})
    return dict(n_queries=int(len(F)), n_clusters=int(F[CLUSTER].nunique()),
                n_candidates_offered=int(F["n_candidates"].sum()), cluster_unit=CLUSTER, models=rows,
                strata=strata_rows(F, ["cfg", "cand_quartile"], "margin_z", ["contaminated"] + CTRL, "contaminated",
                                    family="gaussian", min_rows=500),
                baselines=baselines(F, "margin_z", [("controls_plus_indicator", ["contaminated"] + CTRL,
                                                     "contaminated"),
                                                    ("controls_plus_irrelevant_share", ["irrelevant_share_z"] + CTRL,
                                                     "irrelevant_share_z")], family="gaussian"),
                descriptive_rates={"contaminated_share_by_config": {c["config"]: c["contaminated_share"] for c in cfg},
                                   "irrelevant_above_gold_distribution": {
                                       str(int(k)): int(v) for k, v in
                                       F["irrelevant_above_gold"].value_counts().sort_index().head(8).items()},
                                   "margin_by_contamination": share_by(F, F["contaminated"].astype(str), "fail_at_1"),
                                   "mean_margin_by_contamination": {
                                       str(int(k)): {"mean_margin": round(float(g["bm25_margin"].mean()), 4),
                                                     "rows": int(len(g))}
                                       for k, g in F.groupby("contaminated", observed=True)}},
                gate_scope=TD7.DESIGNS["T166"]["gate_scope"])


def t169(fr: dict) -> dict:
    F, P = fr["F"], fr["P"]
    d = F[F["top_pair"].fillna("") != ""].copy()
    h1 = term(glm(d, "fail_at_1", ["pair_frequent"] + CTRL), "pair_frequent")
    h1.update(hypothesis="H1", term="a_frequently_co_needed_gold_pair_on_missing_at_rank_1",
              queries_with_a_usable_pair=int(len(d)), frequent_pair_queries=int(d["pair_frequent"].sum()),
              frozen_recurrence_floor_queries=10)
    h1["verdict_direction"] = "predicted_negative: a pair the release has needed before is easier to find"
    fp = P[P["frequency"] >= 10].dropna(subset=["random_overlap"]).copy()
    fp["diff"] = fp["overlap"].astype(float) - fp["random_overlap"].astype(float)
    obs = float(fp["diff"].mean())
    b = boot(fp, "pair", lambda x: float(x["diff"].mean()))
    h2 = dict(hypothesis="H2", term="frequent_pair_minus_random_pair_description_overlap",
              beta=round(obs, 4), ci_lo=(b.get("ci") or [None, None])[0], ci_hi=(b.get("ci") or [None, None])[1],
              p=b.get("p"), n=int(len(fp)), clusters=b.get("clusters"),
              frequent_pairs_usable=int(len(fp)), pairs_in_release=int(P.shape[0]),
              frequent_pair_overlap=round(float(fp["overlap"].mean()), 4),
              random_pair_overlap=round(float(fp["random_overlap"].mean()), 4),
              note="each tool pair is its own cluster, so resampling clusters is resampling edges; the usable edge "
                   "count is printed with the estimate because G7's sentence scopes this hypothesis to it")
    h2["verdict_direction"] = "predicted_positive: tools needed together describe themselves alike"
    gold = set()
    for s in F["gold_names"].fillna(""):
        gold.update(x for x in str(s).split("|") if x)
    possible = len(gold) * (len(gold) - 1) / 2
    tot = float(P["frequency"].sum())
    top = P.sort_values(["frequency", "pair"], ascending=[False, True])
    h3 = dict(hypothesis="H3", term="the_network_is_sparse_and_its_degree_is_concentrated",
              verdict_rule="descriptive", distinct_gold_tools=len(gold), pairs_observed=int(P.shape[0]),
              pairs_possible=int(possible), sparsity=round(float(P.shape[0] / possible), 6) if possible else None,
              top10_pair_share_of_cooccurrences=round(float(top["frequency"].head(10).sum() / tot), 4),
              pairs_needing_10plus_queries=int((P["frequency"] >= 10).sum()),
              mean_queries_per_pair=round(float(tot / max(1, P.shape[0])), 3), p=None,
              verdict="measured_descriptively_no_band_was_frozen",
              note="degree and sparsity are counts of the release's own co-need structure, and the freeze asks for "
                   "them as reported rather than as tested")
    rows = holm_and_verdict([h1, h2, h3], {"H1": -1.0, "H2": 1.0})
    return dict(n_queries=int(len(F)), n_clusters=int(d[CLUSTER].nunique()),
                n_candidates_offered=int(F["n_candidates"].sum()),
                cluster_unit="query_id for H1 and the tool pair for H2, as each sentence names",
                models=rows,
                strata=strata_rows(d, ["pair_freq_band", "cfg"], "fail_at_1", ["pair_frequent"] + CTRL,
                                   "pair_frequent"),
                baselines=baselines(d, "fail_at_1", [("controls_plus_frequent_pair_indicator", ["pair_frequent"] + CTRL,
                                                      "pair_frequent"),
                                                     ("controls_plus_continuous_frequency",
                                                      ["max_pair_frequency"] + CTRL,
                                                      "max_pair_frequency"),
                                                     ("controls_plus_number_of_gold_tools",
                                                      ["pair_frequent", "n_gold"] + CTRL, "n_gold")]),
                descriptive_rates={"fail_at_1_by_pair_frequency_band": share_by(d, "pair_freq_band", "fail_at_1"),
                                   "pair_frequency_distribution": {
                                       str(int(k)): int(v) for k, v in
                                       P["frequency"].value_counts().sort_index().head(10).items()},
                                   "overlap_by_frequency_band": {
                                       str(k): {"overlap": round(float(g["overlap"].mean()), 4),
                                                "random_overlap": round(float(g["random_overlap"].mean()), 4),
                                                "pairs": int(len(g))}
                                       for k, g in P.assign(
                                           band=pd.cut(P["frequency"], [-0.5, 0.5, 9.5, 1e9],
                                                       labels=["once", "2to9", "10plus"]).astype(str)
                                       ).groupby("band", observed=True)},
                                   "most_frequent_gold_pairs": {
                                       str(r["pair"])[:70]: int(r["frequency"]) for _, r in top.head(8).iterrows()}},
                gate_scope=TD7.DESIGNS["T169"]["gate_scope"])


DESIGN_FN = {"EXP-0183": ("T161", t161), "EXP-0184": ("T162", t162), "EXP-0185": ("T164", t164),
             "EXP-0186": ("T165", t165), "EXP-0187": ("T166", t166), "EXP-0188": ("T169", t169)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--only", action="append", default=[])
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    fr = load()
    if a.quick:
        keep = fr["F"][CLUSTER].drop_duplicates().sample(900, random_state=TD7.SEED)
        fr["F"] = fr["F"][fr["F"][CLUSTER].isin(set(keep))]
    todo = {k: v for k, v in DESIGN_FN.items() if not a.only or k in a.only}
    bad = [k for k in (a.only or []) if k not in DESIGN_FN]
    if bad:
        raise SystemExit(f"ABORT: --only names no design: {bad}; valid ids are {sorted(DESIGN_FN)}")
    for exp, (topic, fn) in todo.items():
        art = fn(fr)
        lack = [k for k in ("models", "strata", "descriptive_rates", "baselines") if not art.get(k)]
        if lack:
            raise SystemExit(f"ABORT {exp} ({topic}): the design produced no {lack}, so the package tables that read "
                             f"those blocks would ship a header with no numbers - measure it or drop the table")
        nofv = [m.get("hypothesis") or m.get("term") for m in art["models"] if not m.get("verdict")]
        if nofv:
            raise SystemExit(f"ABORT {exp} ({topic}): hypotheses {nofv} carry no verdict, and a pre-registered test "
                             f"that was not decided is not a deliverable")
        art.update(exp_id=exp, topic=topic, seed=TD7.SEED, quick=a.quick, started_at=W.now(),
                   frame_files_read={k: v.attrs.get("frame_file") for k, v in fr.items()},
                   invocation=" ".join([sys.executable] + sys.argv),
                   run_cost=W.run_cost_row(exp, t0, int(len(fr["F"])), int(fr["F"].shape[1]), "wave-7 design"),
                   finished_at=W.now())
        print(f"{exp} ({topic}): wrote {W.write_raw(exp, f'wave7_design_{exp[-4:]}', art).name}", flush=True)
        pd.DataFrame(art.get("models") or []).to_csv(W.OUT / f"EXP{exp[-4:]}_{topic.lower()}_models.csv",
                                                     index=False, encoding="utf-8")
        if art.get("strata"):
            pd.DataFrame(art["strata"]).to_csv(W.OUT / f"EXP{exp[-4:]}_{topic.lower()}_strata.csv", index=False,
                                               encoding="utf-8")
        print("  " + json.dumps({m.get("hypothesis"): m.get("verdict") for m in art["models"]}, default=str)[:240],
              flush=True)
    print(f"wallclock {round(time.time() - t0, 1)}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
