"""EXP-0154..0157: the four frozen wave-4 designs, run on the EXP-0153 step matrix.

Every estimate here is a logistic or a cluster bootstrap on `traj_id`, on the covariate sets the freeze names, with
the bands .05/.15/.30 and Holm across each design's three hypotheses. Nothing is re-tuned after a number exists:
where a term is unidentified because its indicator does not vary, that is reported as such.

    python 02_shared_code/package_factory/exp_wave4_designs.py [--quick] [--only EXP-0154]
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
import numpy as np                                              # noqa: E402
import pandas as pd                                             # noqa: E402
import wave_lib as W                                            # noqa: E402
import topic_designs_wave4 as TD4                               # noqa: E402

# the same scalar support floor every earlier wave used: the medium band, with the small band
# reserved for the specificity control
assert TD4.BANDS == W.BANDS, "the wave-4 freeze and wave_lib disagree about the effect bands"
BAND = W.BANDS["medium"]
BAND_SMALL = W.BANDS["small"]
FRAME = TD4.MATRIX.replace("results_raw/", "results_processed/").replace(".json", "")
CLUSTER = "traj_id"


def load() -> pd.DataFrame:
    """The step matrix, with the derived contrasts the freeze names. Column names are checked, not guessed."""
    name = "EXP0153_wave4_step_features.csv.gz"
    # The clean-room re-run points AIB_PROCESSED_DIR at a scratch directory so its outputs cannot overwrite the
    # shipped artefacts - but its *input* is still the matrix in the repository. Reading the input from the same
    # redirected directory is what made every wave-4 clean-room record fail with "matrix is missing".
    search = []
    if os.environ.get("AIB_INPUT_DIR"):
        search.append(pathlib.Path(os.environ["AIB_INPUT_DIR"]) / name)
    search += [W.OUT / name, W.ROOT / "results_processed" / name]
    path = next((p for p in search if pathlib.Path(p).is_file()), None)
    if path is None:
        raise SystemExit(f"ABORT: {name} is not where the designs look ({', '.join(map(str, search))}) - run "
                         f"{TD4.FEATURE_EXP} (exp_wave4_features.py) first")
    F = pd.read_csv(gzip.open(path, "rt"))
    F.attrs["frame_file"] = str(path)
    need = ["traj_id", "turn_index", "body_len", "modal_turn", "modal_body", "modal_think", "suffic_turn",
            "topical_control", "topical_count", "emits_call", "next_is_inspect", "next_is_exec", "prev_obs_error",
            "prev_state", "prior_inspections", "prior_non_inspections", "next_action_kind", "category", "has_think"]
    miss = [c for c in need if c not in F.columns]
    if miss:
        raise SystemExit(f"ABORT: the step frame lacks {miss}; the designs would drop those terms in silence")
    F["log_body"] = np.log1p(F["body_len"].astype(float))
    F["log_turn"] = np.log1p(F["turn_index"].astype(float))
    F["control_z"] = z(F["topical_count"].astype(float))
    F["stops_here"] = (F["next_action_kind"] != "call").astype(int)
    F["disc"] = ((F["modal_think"] == 1) & (F["modal_body"] == 0)).astype(int)
    F["conc"] = ((F["modal_think"] == 1) & (F["modal_body"] == 1)).astype(int)
    F["bodyonly"] = ((F["modal_think"] == 0) & (F["modal_body"] == 1)).astype(int)
    # sum/difference coding: with `hedge_diff` in place of the two indicators, its coefficient IS the
    # discordant-minus-body-only contrast the freeze asks for, so no post-hoc linear combination is needed
    F["hedge_sum"] = F["disc"] + F["bodyonly"]
    F["hedge_diff"] = F["disc"] - F["bodyonly"]
    F["st_changed"] = (F["prev_state"] == "same_tool_changed").astype(int)
    F["st_same"] = (F["prev_state"] == "same_tool_same").astype(int)
    F["st_diff_tool"] = (F["prev_state"] == "different_tool").astype(int)
    F["state_sum"] = F["st_changed"] + F["st_diff_tool"]
    F["state_diff"] = F["st_changed"] - F["st_diff_tool"]
    F["mxi"] = F["modal_turn"] * F["prev_obs_error"]
    # T126's frozen strata are by tool *family* and T127's by trajectory length, so the grouping the freeze names is
    # computed here with the same classifiers - and the same precedence - that label the next action.
    F["prev_obs_family"] = F["prev_obs_tool"].fillna("").astype(str).map(family_of)
    F["traj_quartile"] = pd.qcut(F["n_turns_traj"].rank(method="first"), 4,
                                 labels=["q1_shortest", "q2", "q3", "q4_longest"]).astype(str)
    return F


def family_of(name: str) -> str:
    """inspection / execution / production / none, by the lexicons `exp_wave4_features` labels calls with."""
    import exp_wave4_features as EF
    if not str(name).strip():
        return "none"
    if EF.INSPECT.search(name):
        return "inspection"
    if EF.EXEC.search(name):
        return "execution"
    return "production" if EF.WRITE.search(name) else "other"


CTRL = ["log_turn", "log_body", "prior_inspections", "prior_non_inspections", "prev_obs_error"]


def z(s: pd.Series) -> pd.Series:
    sd = float(s.std(ddof=0))
    return (s - float(s.mean())) / sd if sd > 0 else s * 0.0


def term(f: pd.DataFrame, name: str) -> dict:
    if f is None or f.empty:
        return {}
    r = f[f["term"] == name]
    return {} if r.empty else {k: (round(float(r.iloc[0][k]), 4) if k != "n" else int(r.iloc[0][k]))
                               for k in ("beta", "se", "ci_lo", "ci_hi", "p", "n") if k in r.columns}


def glm(d: pd.DataFrame, y: str, xs) -> pd.DataFrame:
    # a term repeated across an interaction list and CTRL enters the design matrix twice, and the cluster-robust
    # covariance then raises Singular matrix - which the fit helper reports as a bare None, indistinguishable from
    # "the data cannot carry this". Deduplicate, and say so where a model still cannot be fitted.
    return W.glm_term(d, y, list(dict.fromkeys(xs)), "binomial", cluster=CLUSTER)


def holm_and_verdict(rows: list, direction: dict) -> list:
    # `p or 1.0` turns a genuine p = 0.0 into 1.0, which inflated every Holm entry in the first run
    ps = {r["hypothesis"]: (1.0 if r.get("p") is None else float(r["p"])) for r in rows}
    adj = W.holm(ps)
    for r in rows:
        r["p_holm"] = adj[r["hypothesis"]]
        if r.get("verdict_rule") == "specificity":
            continue                                  # the H3 rule is its own sentence, set by the caller
        r["verdict"] = W.verdict(r.get("beta"), r.get("ci_lo"), r.get("ci_hi"), r["p_holm"], BAND,
                                 direction=direction.get(r["hypothesis"], 1.0))
    return rows


def rates(F: pd.DataFrame, col: str, target: str) -> dict:
    """The raw cell rates behind a coefficient, so a reader can see what the model is talking about."""
    g = F.groupby(col, dropna=False)[target].agg(["mean", "size"])
    return {str(k): {"rate": round(float(v), 4), "n": int(g.loc[k, "size"])} for k, v in g["mean"].items()}


def baselines(d: pd.DataFrame, y: str, specs) -> list:
    """The evidence-state model on its own, then with each construct term added, and the deviance drop between them.

    Every wave-4 design ships `table6_baseline_comparison.csv`, and the question that table answers is what the
    marker adds over a model that already knows the turn's position, length and evidence state. The reduced model is
    fitted here rather than described in the package, so the table is two estimates on the same rows plus the
    likelihood-ratio statistic between them, not a sentence about a comparison nobody ran.
    """
    from scipy import stats as SP
    base = glm(d, y, CTRL)
    if base is None or base.empty:
        return [dict(model="evidence_state_only", dv=y, note="not fitted on these rows")]
    dev0 = float(base["deviance"].iloc[0])
    rows = [dict(model="evidence_state_only", dv=y, terms="+".join(CTRL), n=int(base["n"].iloc[0]),
                 clusters=int(d[CLUSTER].nunique()), deviance=round(dev0, 2))]
    for name, xs, focus in specs:
        f = glm(d, y, xs)
        if f is None or f.empty:
            rows.append(dict(model=name, dv=y, terms="+".join(dict.fromkeys(xs)),
                             note="not fitted: the design matrix cannot be estimated on these rows"))
            continue
        dev1 = float(f["deviance"].iloc[0])
        dfree = max(1, len(list(dict.fromkeys(xs))) - len(CTRL))
        lr = 2.0 * (dev0 - dev1)
        t = {k: v for k, v in term(f, focus).items() if k != "n"}
        rows.append(dict(model=name, dv=y, terms="+".join(dict.fromkeys(xs)), n=int(f["n"].iloc[0]),
                         deviance=round(dev1, 2), added_term=focus, deviance_drop=round(dev0 - dev1, 2),
                         lr_chi2=round(lr, 2), lr_df=dfree, lr_p=round(float(SP.chi2.sf(max(lr, 0.0), dfree)), 6),
                         **{f"{focus}_{k}": v for k, v in t.items()}))
    return rows


def strata_rows(d: pd.DataFrame, splits, y: str, xs, focus: str, min_rows: int = 500) -> list:
    """One slope per level of each stratification the freeze names, on the same specification as the main model.

    A stratum thinner than `min_rows` is skipped rather than fitted, and the row count is printed next to every slope
    so a reader can see which cells the table does and does not cover.
    """
    rows = []
    for col in splits:
        for lab, g in d.groupby(col, observed=True):
            if len(g) < min_rows:
                continue
            # a stratum defined by a term that is also a control is constant inside itself, and fitting that control
            # returns a singular matrix; the constant term is dropped and the drop is named in the row.
            kept = [c for c in xs if g[c].nunique(dropna=False) > 1]
            dropped = [c for c in xs if c not in kept]
            rows.append(dict(stratification=col, stratum=str(lab)[:40], rows=int(len(g)),
                             trajectories=int(g[CLUSTER].nunique()),
                             dropped_constant_terms="+".join(dropped) or "none",
                             identifiable=bool(focus in kept), **term(glm(g, y, kept), focus)))
    return rows


def t123(F: pd.DataFrame) -> dict:
    d = F.dropna(subset=["next_is_inspect", "modal_turn"] + CTRL)
    h1 = term(glm(d, "next_is_inspect", ["modal_turn"] + CTRL), "modal_turn")
    h1.update(hypothesis="H1", term="modal_turn_on_next_inspection")
    # H2 needs the interaction to be identifiable: a cell with no error-preceded hedged turns cannot carry it
    cell = int(((d["modal_turn"] == 1) & (d["prev_obs_error"] == 1)).sum())
    if cell >= 200:
        h2 = term(glm(d, "next_is_inspect", ["modal_turn", "prev_obs_error", "mxi"] + CTRL), "mxi")
        h2["cell_n"] = cell
    else:
        h2 = {"cell_n": cell, "verdict": "not_testable_empty_cell"}
    h2.update(hypothesis="H2", term="modal_x_error_interaction")
    # H3: the frozen indicator was degenerate at prevalence 0.9998, so the control enters as its standardised
    # count; both facts are reported and the indicator itself is shown as measured, not quietly dropped.
    fc = term(glm(d, "next_is_inspect", ["control_z", "modal_turn"] + CTRL), "control_z")
    fc.update(hypothesis="H3", term="topical_control_count_z_on_next_inspection", verdict_rule="specificity",
              frozen_indicator_prevalence=round(float(d["topical_control"].mean()), 4),
              indicator_is_degenerate=bool(float(d["topical_control"].mean()) > 0.99),
              control_count_sd=round(float(d["topical_count"].std(ddof=0)), 3))
    specific = (abs(fc.get("beta") or 0) < BAND_SMALL and abs(h1.get("beta") or 0) >= BAND_SMALL
                and (fc.get("ci_lo") is not None and fc.get("ci_hi") is not None
                     and fc["ci_lo"] <= 0 <= fc["ci_hi"]))
    fc["verdict"] = ("supported" if specific else
                     "not_specific_control_tracks_the_same_variance" if fc.get("beta") else "not_testable")
    rows = holm_and_verdict([h1, h2, fc], {"H1": 1.0, "H2": 1.0})
    thirds = pd.cut(d["turn_index"] / d["turn_index"].max(), [0, 1 / 3, 2 / 3, 1.0],
                    labels=["first_third", "middle_third", "last_third"])
    d = d.assign(position_third=thirds.astype(str))
    strat = strata_rows(d, ["position_third", "category"], "next_is_inspect", ["modal_turn"] + CTRL, "modal_turn")
    return dict(n_turns=int(len(d)), n_trajectories=int(d[CLUSTER].nunique()), gate_scope=TD4.DESIGNS["T123"][
        "gate_scope"], models=rows, strata=strat,
        baselines=baselines(d, "next_is_inspect", [
            ("evidence_state_plus_modality_marker", ["modal_turn"] + CTRL, "modal_turn"),
            ("evidence_state_plus_marker_x_error", ["modal_turn", "prev_obs_error", "mxi"] + CTRL, "mxi"),
            ("evidence_state_plus_control_lexicon", ["control_z", "modal_turn"] + CTRL, "control_z")]),
        descriptive_rates={"inspection_rate_by_modality": rates(d, "modal_turn", "next_is_inspect"),
                           "inspection_rate_by_error_preceded": rates(d, "prev_obs_error", "next_is_inspect")})


def t124(F: pd.DataFrame) -> dict:
    d = F[(F["has_think"] == 1) & (F["body_len"] >= 20)].dropna(subset=["next_is_inspect"])
    if int(d["disc"].sum()) < 200:
        return dict(n_turns=int(len(d)), models=[dict(hypothesis=h, verdict="not_testable_empty_cell")
                                                 for h in ("H1", "H2", "H3")], gate_scope="H1")
    # H1 asks for a difference between two categories, so it is fitted on the sum/difference coding, where
    # the coefficient on `hedge_diff` IS that difference. H2 asks for a level against the reference
    # category, which the indicator coding gives directly; mixing the two codings in one model is
    # collinear, so each hypothesis gets the coding its sentence implies.
    xs = ["hedge_sum", "hedge_diff", "conc"] + CTRL
    ind = ["disc", "bodyonly", "conc"] + CTRL
    h1 = term(glm(d, "next_is_inspect", xs), "hedge_diff")
    h1.update(hypothesis="H1", term="discordant_minus_body_only_on_next_inspection")
    h2 = term(glm(d, "next_is_inspect", ind), "bodyonly")
    h2.update(hypothesis="H2", term="body_only_vs_no_hedge_on_next_inspection")
    h3 = term(glm(d, "stops_here", xs), "hedge_diff")
    h3.update(hypothesis="H3", term="discordant_minus_body_only_on_stopping")
    rows = holm_and_verdict([h1, h2, h3], {"H1": 1.0, "H2": -1.0, "H3": -1.0})
    # H2's frozen sentence enumerates two outcomes: the contrast is null (the conversational reading holds) or it
    # is positive (evidence against it). A negative contrast is neither, so it is reported as outside the frozen
    # rule with its number, rather than folded into the null that the rule would have called a support.
    rows[1]["support_rule"] = ("supported only when this contrast is null: a positive here is evidence against the "
                               "reading that a public hedge is conversational")
    b2, l2, u2 = rows[1].get("beta"), rows[1].get("ci_lo"), rows[1].get("ci_hi")
    if l2 is None:
        rows[1]["verdict"] = "not_testable"
    elif l2 <= 0 <= u2:
        rows[1]["verdict"] = "supported"
    elif (b2 or 0) > 0:
        rows[1]["verdict"] = "opposite"
    else:
        rows[1]["verdict"] = "outside_the_frozen_rule_negative_contrast"
        rows[1]["note"] = ("the body-only hedge is followed by inspection significantly LESS often, which the "
                           "frozen sentence did not anticipate")
    strat = strata_rows(d, ["category", "prev_obs_error"], "next_is_inspect", xs, "hedge_diff")
    return dict(n_turns=int(len(d)), n_trajectories=int(d[CLUSTER].nunique()), models=rows, strata=strat,
                cell_sizes={k: int(d[k].sum()) for k in ("disc", "conc", "bodyonly")},
                baselines=(baselines(d, "next_is_inspect",
                                     [("evidence_state_plus_face_sum_and_diff", xs, "hedge_diff"),
                                      ("evidence_state_plus_face_indicators", ind, "bodyonly")])
                           + baselines(d, "stops_here",
                                       [("evidence_state_plus_face_sum_and_diff", xs, "hedge_diff")])),
                descriptive_rates={"face_pattern_cell_rows": {k: int(d[k].sum()) for k in ("disc", "conc", "bodyonly")},
                                   "face_pattern_share_of_turns": {
                                       k: round(float(d[k].mean()), 4) for k in ("disc", "conc", "bodyonly")},
                                   "inspection_rate_by_pattern": {
                    "discordant": rates(d, "disc", "next_is_inspect"), "body_only": rates(d, "bodyonly",
                                                                                           "next_is_inspect")}})


def t126(F: pd.DataFrame) -> dict:
    d = F[F["prev_state"] != "none"].dropna(subset=["modal_turn"])
    h1 = term(glm(d, "modal_turn", ["st_changed", "st_same", "st_diff_tool"] + CTRL), "st_changed")
    h1.update(hypothesis="H1", term="same_tool_content_change_on_modality")
    h2 = term(glm(d, "modal_turn", ["state_diff", "state_sum", "st_same"] + CTRL), "state_diff")
    h2.update(hypothesis="H2", term="changed_minus_different_tool_on_modality")
    h3 = term(glm(d, "suffic_turn", ["st_changed", "st_same", "st_diff_tool"] + CTRL), "st_changed")
    h3.update(hypothesis="H3", term="same_tool_content_change_on_sufficiency_language")
    rows = holm_and_verdict([h1, h2, h3], {"H1": 1.0, "H2": 1.0, "H3": 1.0})
    # The freeze's own H2 clause overrides the magnitude band for this row: "H2 is supported when the
    # changed-vs-different difference has CI excluding 0" (topic_designs_wave4.T126 thresholds.h2). The row
    # declares that rule so the statistical-consistency auditor re-derives the word from the same sentence
    # rather than from the H1/H3 band, which names a floor this contrast never froze.
    lo, hi = rows[1].get("ci_lo"), rows[1].get("ci_hi")
    if lo is not None and hi is not None:
        rows[1]["verdict_rule"] = "h2_ci_excludes_zero"
        rows[1]["verdict"] = "null" if (lo <= 0 <= hi) else "supported"
    cell = int((d["prev_state"] == "same_tool_changed").sum())
    for r in rows:
        r["cell_rows"] = cell
    if cell < 200:
        rows[2]["verdict"] = "not_testable_empty_cell"
    strat = strata_rows(d, ["prev_obs_family", "prev_state"], "modal_turn",
                        ["st_changed", "st_same", "st_diff_tool"] + CTRL, "st_changed")
    return dict(n_turns=int(len(d)), n_trajectories=int(d[CLUSTER].nunique()), models=rows, strata=strat,
                baselines=(baselines(d, "modal_turn",
                                     [("evidence_state_plus_state_indicators",
                                       ["st_changed", "st_same", "st_diff_tool"] + CTRL, "st_changed"),
                                      ("evidence_state_plus_state_sum_and_diff",
                                       ["state_diff", "state_sum", "st_same"] + CTRL, "state_diff")])
                           + baselines(d, "suffic_turn",
                                       [("evidence_state_plus_state_indicators",
                                         ["st_changed", "st_same", "st_diff_tool"] + CTRL, "st_changed")])),
                descriptive_rates={"modality_rate_by_state": rates(d, "prev_state", "modal_turn"),
                                   "sufficiency_rate_by_state": rates(d, "prev_state", "suffic_turn")})


def t127(F: pd.DataFrame) -> dict:
    d = F.dropna(subset=["stops_here", "suffic_turn"] + CTRL)
    base = term(glm(d, "stops_here", CTRL), "prior_inspections")
    full = term(glm(d, "stops_here", ["suffic_turn"] + CTRL), "suffic_turn")
    full.update(hypothesis="H1", term="sufficiency_claim_added_to_the_evidence_state_baseline",
                baseline_prior_inspections=base)
    claim = d[(d["stops_here"] == 1) & (d["suffic_turn"] == 1)]["prior_inspections"].mean()
    other = d[(d["stops_here"] == 1) & (d["suffic_turn"] == 0)]["prior_inspections"].mean()
    dif = d.assign(is_stop=(d["stops_here"] == 1).astype(int),
                   grp=np.where((d["stops_here"] == 1) & (d["suffic_turn"] == 1), "claim",
                                np.where(d["stops_here"] == 1, "other", "")))              .loc[lambda x: x["grp"] != ""].copy()
    dif["dif"] = np.where(dif["grp"] == "claim", dif["prior_inspections"], -dif["prior_inspections"])
    # the same bootstrap draws give the interval and the p, and the statistic is a per-cluster mean difference
    bt = W.cluster_boot_ci_and_p(dif, CLUSTER, lambda x: float(x.loc[x["grp"] == "claim", "prior_inspections"].mean()
                                                                 - x.loc[x["grp"] == "other",
                                                                       "prior_inspections"].mean()))
    if "ci" not in bt:
        h2 = dict(hypothesis="H2", term="prior_inspections_at_claim_stops_minus_other_stops",
                  verdict="not_testable", boot_note=bt.get("error"))
    else:
        lo, hi, p = float(bt["ci"][0]), float(bt["ci"][1]), float(bt["p"])
        h2 = dict(hypothesis="H2", term="prior_inspections_at_claim_stops_minus_other_stops",
                  beta=round(float(claim - other), 4), ci_lo=lo, ci_hi=hi, p_boot=p, p=p,
                  n=int(len(dif)), clusters=bt["clusters"], is_bootstrap_mean=True,
                  claim_stops=int((dif["grp"] == "claim").sum()), other_stops=int((dif["grp"] == "other").sum()))
        lower = hi < 0
        h2["verdict"] = ("supported" if lower and abs(h2["beta"]) >= BAND_SMALL else
                         "partial" if lower else
                         "null" if lo <= 0 <= hi else "opposite")
    h3 = dict(hypothesis="H3", term="category_strata_of_the_claim_effect", verdict="descriptive stratum slopes, "
                                                                                   "not a family member")
    strat = strata_rows(d, ["category", "traj_quartile"], "stops_here", ["suffic_turn"] + CTRL, "suffic_turn")
    rows = holm_and_verdict([full, h2], {"H1": 1.0, "H2": -1.0})
    rows.append(h3)
    return dict(n_turns=int(len(d)), n_trajectories=int(d[CLUSTER].nunique()), models=rows, strata=strat,
                baselines=baselines(d, "stops_here",
                                    [("evidence_state_plus_sufficiency_claim", ["suffic_turn"] + CTRL,
                                      "suffic_turn")]),
                stops_total=int(d["stops_here"].sum()),
                descriptive_rates={"stop_rate_by_claim": rates(d, "suffic_turn", "stops_here"),
                                   "mean_prior_inspections_by_claim": {
                                       str(k): round(float(g["prior_inspections"].mean()), 2)
                                       for k, g in d.groupby("suffic_turn")}})


DESIGN_FN = {"EXP-0154": ("T123", t123), "EXP-0155": ("T124", t124),
             "EXP-0156": ("T126", t126), "EXP-0157": ("T127", t127)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--only", action="append", default=[])
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    F = load()
    if a.quick:
        keep = F[CLUSTER].drop_duplicates().sample(2000, random_state=TD4.SEED)
        F = F[F[CLUSTER].isin(set(keep))]
    todo = {k: v for k, v in DESIGN_FN.items() if not a.only or k in a.only}
    bad = [k for k in (a.only or []) if k not in DESIGN_FN]
    if bad:
        raise SystemExit(f"ABORT: --only names no design: {bad}; valid ids are {sorted(DESIGN_FN)}")
    arts = {}
    for exp, (topic, fn) in todo.items():
        art = fn(F)
        lack = [k for k in ("models", "strata", "descriptive_rates", "baselines") if not art.get(k)]
        if lack:
            raise SystemExit(f"ABORT {exp} ({topic}): the design produced no {lack}, so the package tables that read "
                             f"those blocks would ship a file with a header and no numbers - measure it, or remove "
                             f"the table from the freeze")
        art.update(exp_id=exp, topic=topic, seed=TD4.SEED, quick=a.quick, started_at=W.now(),
                   frame_file_read=F.attrs.get("frame_file"),
                   invocation=" ".join([sys.executable] + sys.argv),
                   run_cost=W.run_cost_row(exp, t0, int(len(F)), int(F.shape[1]), "wave-4 design"),
                   finished_at=W.now())
        arts[exp] = art
        print(f"{exp} ({topic}): wrote {W.write_raw(exp, f'wave4_design_{exp[-4:]}', art).name}", flush=True)
        pd.DataFrame(art.get("models") or []).to_csv(W.OUT / f"EXP{exp[-4:]}_{topic.lower()}_models.csv",
                                                     index=False)
        if art.get("strata"):
            pd.DataFrame(art["strata"]).to_csv(W.OUT / f"EXP{exp[-4:]}_{topic.lower()}_strata.csv", index=False)
    for exp, art in arts.items():
        vs = {(m.get("hypothesis") or m.get("term")): m.get("verdict") for m in (art.get("models") or [])}
        print(f"  {exp}: {json.dumps(vs, default=str)[:220]}")
    print(f"wallclock {round(time.time() - t0, 1)}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
