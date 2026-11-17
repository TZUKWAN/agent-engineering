"""EXP-0165..EXP-0170: wave 5's six pre-registered tests, run from the frozen sentences in topic_designs_wave5.

Nothing here decides a threshold. Each hypothesis carries the band floor and the direction its freeze names, Holm is
applied to the three hypotheses a design declares (and to nothing else), and every interval is a cluster-robust one on
`traj_id` - the unit a turn is computed within, per the rule that a feature computed from a set must be clustered by
that set. A cell a premise gate said was too thin is reported as `not_testable_*` with its measured count, which is a
result, not a gap to fill by moving the floor.

    python 02_shared_code/package_factory/exp_wave5_designs.py [--quick] [--only EXP-0165]
"""
from __future__ import annotations

import argparse
import gzip
import json
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np                                              # noqa: E402
import pandas as pd                                             # noqa: E402
import wave_lib as W                                            # noqa: E402
import exp_wave4_designs as D4                                   # noqa: E402  (family_of: one classifier, both waves)
import exp_wave5_features as EF                                 # noqa: E402
import topic_designs_wave5 as TD5                               # noqa: E402

assert TD5.BANDS == W.BANDS, "the wave-5 freeze and wave_lib disagree about the effect bands"
BAND = W.BANDS["medium"]
BAND_SMALL = W.BANDS["small"]
CLUSTER = TD5.SAMPLE["cluster_unit"]
CTRL = ["log_turn", "log_body", "prior_inspections", "prior_non_inspections", "prev_obs_error"]
FRAME_NAME = "EXP0164_wave5_step_features.csv.gz"


def load() -> pd.DataFrame:
    """The wave-5 frame, with the derived contrasts the freeze names. Column names are checked, not guessed."""
    name = FRAME_NAME
    search = []
    import os
    if os.environ.get("AIB_INPUT_DIR"):
        search.append(pathlib.Path(os.environ["AIB_INPUT_DIR"]) / name)
    search += [W.OUT / name, W.ROOT / "results_processed" / name]
    path = next((q for q in search if pathlib.Path(q).is_file()), None)
    if path is None:
        raise SystemExit(f"ABORT: {name} is not where the designs look ({', '.join(map(str, search))}) - run "
                         f"{TD5.FEATURE_EXP} (exp_wave5_features.py) first")
    F = pd.read_csv(gzip.open(path, "rt"))
    F.attrs["frame_file"] = str(path)
    need = ["traj_id", "turn_index", "body_len", "prev_obs_error", "prior_inspections", "prior_non_inspections",
            "next_is_inspect", "next_action_kind", "emits_call", "category", "n_turns_traj",
            "act_hypothesis", "act_question", "act_plan", "act_evidence_request", "act_conclusion",
            "act_hypothesis_b", "act_question_b", "act_plan_b", "act_evidence_request_b", "act_conclusion_b",
            "n_causal", "n_inferential", "n_explanatory", "control_count", "evidence_overlap", "has_prior_evidence",
            "concl_after_inspect", "repair_diagnose", "repair_reissue", "repair_abandon",
            "align_next", "align_perm_mean", "prev_obs_error_next", "first_call_name",
            "prev_obs_tool", "n_turns_traj"]
    miss = [c for c in need if c not in F.columns]
    if miss:
        raise SystemExit(f"ABORT: the wave-5 frame lacks {miss}; the designs would drop those terms in silence")
    F["log_body"] = np.log1p(F["body_len"].astype(float))
    F["log_turn"] = np.log1p(F["turn_index"].astype(float))
    F["stops_here"] = (F["next_action_kind"] != "call").astype(int)
    F["chain"] = (F["n_causal"] >= 2).astype(int)
    F["has_causal"] = (F["n_causal"] >= 1).astype(int)
    F["last_third"] = 0
    mx = float(F["turn_index"].max() or 0)
    if mx > 0:
        F.loc[F["turn_index"] / mx > 2.0 / 3.0, "last_third"] = 1
    F["first_third"] = (F["turn_index"] / max(mx, 1.0) <= 1.0 / 3.0).astype(int)
    F["ov_z"] = z(F["evidence_overlap"].astype(float))
    F["infer_z"] = z(F["n_inferential"].astype(float))
    F["expl_z"] = z(F["n_explanatory"].astype(float))
    F["control_z"] = z(F["control_count"].astype(float))
    F["align_z"] = z(F["align_next"].astype(float))
    # sum/difference coding, so the coefficient on the difference IS the family contrast the freeze asks for
    F["fam_sum"] = F["infer_z"] + F["expl_z"]
    F["fam_diff"] = F["infer_z"] - F["expl_z"]
    F["align_diff"] = F["align_next"] - F["align_perm_mean"]
    F["has_align"] = F["align_next"].notna().astype(int)
    # the stratifications the freezes name, derived here so the frame stays one shared measurement
    mx = float(F["turn_index"].max() or 0)
    F["position_third"] = pd.cut(F["turn_index"] / max(mx, 1.0), [0.0, 1 / 3, 2 / 3, 1.0001],
                                 labels=["first_third", "middle_third", "last_third"]).astype(str)
    F["body_quartile"] = pd.qcut(F["body_len"].rank(method="first"), 4,
                                 labels=["q1_shortest", "q2", "q3", "q4_longest"]).astype(str)
    F["prev_obs_family"] = F["prev_obs_tool"].fillna("").astype(str).map(D4.family_of)
    F["first_call_family"] = F["first_call_name"].fillna("").astype(str).map(D4.family_of)
    return F


def z(s: pd.Series) -> pd.Series:
    v = pd.to_numeric(s, errors="coerce")
    sd = float(v.std(ddof=0))
    return (v - float(v.mean())) / sd if sd > 0 else v * 0.0


def term(f: pd.DataFrame, name: str) -> dict:
    if f is None or f.empty or "term" not in f.columns:
        return {}
    r = f[f["term"] == name]
    if r.empty:
        return {}
    out = {}
    for k in ("beta", "se", "ci_lo", "ci_hi", "p", "n"):
        if k in r.columns:
            out[k] = int(r.iloc[0][k]) if k == "n" else (round(float(r.iloc[0][k]), 4)
                                                         if r.iloc[0][k] is not None else None)
    return out


def glm(d: pd.DataFrame, y: str, xs, family="binomial") -> pd.DataFrame:
    xs = [c for c in dict.fromkeys(xs) if c in d.columns]
    d = d.dropna(subset=[y] + xs)
    if family == "binomial":
        vals = set(np.unique(d[y].astype(float)))
        if not vals <= {0.0, 1.0}:
            # A logit link on a continuous outcome is what produced a -3e15 coefficient with a NaN interval in the
            # first wave-5 run, and the verdict machinery then read that interval as a null. The link has to match
            # the outcome, so the mistake stops the build instead of shipping a number.
            raise SystemExit(f"ABORT: {y} takes {len(vals)} distinct values and is not 0/1, so the binomial link "
                             f"would model a quantity that has no probability reading - pass family='gaussian'")
    if d.empty or d[y].nunique() < 2 and family == "binomial":
        return pd.DataFrame()
    return W.glm_term(d, y, xs, family, cluster=CLUSTER)


def boot_ci_mean(d: pd.DataFrame, stat: str, draws: int = 400) -> dict:
    """Cluster bootstrap of a column mean - used where the estimand is a difference of rates, not a coefficient."""
    return W.cluster_boot_ci_and_p(d, CLUSTER, lambda x: float(pd.to_numeric(x[stat], errors="coerce").mean()),
                                   draws=draws)


def holm_and_verdict(rows: list, direction: dict, band: float = BAND) -> list:
    ps = {r["hypothesis"]: (1.0 if r.get("p") is None else float(r["p"])) for r in rows}
    adj = W.holm(ps)
    for r in rows:
        if r.get("verdict"):
            r.setdefault("p_holm", adj[r["hypothesis"]])
            continue
        r["p_holm"] = adj[r["hypothesis"]]
        if r.get("verdict_rule") in ("specificity", "sign_reproduction"):
            continue
        if r.get("beta") is None:
            # a fit that produced no row for its term is not a null result; it is a cell the design cannot estimate
            r["verdict"] = "not_testable_no_coefficient_estimated"
            continue
        if not all(_finite(v) for v in (r.get("beta"), r.get("ci_lo"), r.get("ci_hi"), r.get("p"))):
            # an interval that is not a number cannot include or exclude zero, so the four-way rule does not apply
            r["verdict"] = "not_estimable_non_finite_interval"
            r.setdefault("note", "the cluster-robust interval or the coefficient is not finite on these rows, so no "
                                 "direction is claimed; the raw values are kept in this row")
            continue
        r["verdict"] = W.verdict(r.get("beta"), r.get("ci_lo"), r.get("ci_hi"), r["p_holm"], band,
                                 direction=direction.get(r["hypothesis"], 1.0))
    return rows


def _finite(v) -> bool:
    try:
        return bool(np.isfinite(float(v)))
    except (TypeError, ValueError):
        return False


def baselines(d: pd.DataFrame, y: str, specs, family="binomial") -> list:
    """The controls-only model, then each construct added, with the deviance drop between them."""
    from scipy import stats as SP
    base = glm(d, y, CTRL, family)
    if base is None or base.empty:
        return [dict(model="controls_only", dv=y, note="not fitted on these rows")]
    dev0 = float(base["deviance"].iloc[0])
    rows = [dict(model="controls_only", dv=y, terms="+".join(CTRL), n=int(base["n"].iloc[0]),
                 clusters=int(d[CLUSTER].nunique()), deviance=round(dev0, 2))]
    for name, xs, focus in specs:
        f = glm(d, y, xs, family)
        if f is None or f.empty:
            rows.append(dict(model=name, dv=y, terms="+".join(dict.fromkeys(xs)),
                             note="not fitted: the design matrix cannot be estimated on these rows"))
            continue
        dev1 = float(f["deviance"].iloc[0])
        dfree = max(1, len([c for c in dict.fromkeys(xs) if c in d.columns]) - len(CTRL))
        lr = 2.0 * (dev0 - dev1)
        t = {k: v for k, v in term(f, focus).items() if k != "n"}
        rows.append(dict(model=name, dv=y, terms="+".join(dict.fromkeys(xs)), n=int(f["n"].iloc[0]),
                         deviance=round(dev1, 2), added_term=focus, deviance_drop=round(dev0 - dev1, 2),
                         lr_chi2=round(lr, 2), lr_df=dfree, lr_p=round(float(SP.chi2.sf(max(lr, 0.0), dfree)), 6),
                         **{f"{focus}_{k}": v for k, v in t.items()}))
    return rows


def strata_rows(d: pd.DataFrame, splits, y: str, xs, focus: str, min_rows: int = 500, family="binomial") -> list:
    rows = []
    for col in splits:
        for lab, g in d.groupby(col, observed=True):
            if len(g) < min_rows or g[y].nunique() < 2:
                continue
            kept = [c for c in xs if c in g.columns and g[c].nunique(dropna=False) > 1]
            dropped = [c for c in xs if c not in kept]
            rows.append(dict(stratification=col, stratum=str(lab)[:40], rows=int(len(g)),
                             trajectories=int(g[CLUSTER].nunique()),
                             dropped_constant_terms="+".join(dropped) or "none",
                             identifiable=focus in kept, **term(glm(g, y, kept, family), focus)))
    return rows


# ------------------------------------------------------------------ the six designs
def act_shares(d: pd.DataFrame, splits) -> list:
    """Act shares per stratum: the grammar paper describes its cells, it does not fit slopes inside them."""
    rows = []
    for col in splits:
        for lab, g in d.groupby(col, observed=True):
            if len(g) < 500:
                continue
            rows.append(dict(stratification=col, stratum=str(lab)[:40], rows=int(len(g)),
                             trajectories=int(g[CLUSTER].nunique()),
                             **{f"share_{a}": round(float(g[f"act_{a}"].mean()), 4) for a in EF.P5.ACT}))
    return rows


def t130(F: pd.DataFrame) -> dict:
    d = F[F["body_len"] >= 20]
    h1 = term(glm(d, "act_plan", ["last_third"] + CTRL), "last_third")
    h1.update(hypothesis="H1", term="last_third_on_act_plan")
    h2 = term(glm(d, "act_conclusion", ["last_third"] + CTRL), "last_third")
    h2.update(hypothesis="H2", term="last_third_on_act_conclusion")
    kap = {}
    for a in EF.P5.ACT:
        b = W.cluster_boot_ci_and_p(d, CLUSTER,
                                    lambda x, a=a: EF.kappa(x[f"act_{a}"], x[f"act_{a}_b"]), draws=200)
        kap[a] = {"kappa": EF.kappa(d[f"act_{a}"], d[f"act_{a}_b"]),
                  "ci": b.get("ci"), "n": int(len(d)), "agreement": round(float((d[f"act_{a}"] == d[f"act_{a}_b"])
                                                                                .mean()), 4)}
    weak = sorted(a for a, v in kap.items() if not (isinstance(v["kappa"], float) and v["kappa"] >= 0.60))
    h3 = dict(hypothesis="H3", term="tagger_a_vs_tagger_b_kappa_per_act",
              kappa=kap, weak_acts=weak,
              verdict=("supported" if not weak else
                       "not_invariant_kappa_below_0p60_for_" + "_".join(weak) if weak else "not_testable"))
    rows = holm_and_verdict([h1, h2, h3], {"H1": -1.0, "H2": 1.0})
    return dict(n_turns=int(len(d)), n_trajectories=int(d[CLUSTER].nunique()), models=rows,
                strata=act_shares(d, ["position_third", "category"]),
                baselines=baselines(d, "act_plan", [("controls_plus_last_third", ["last_third"] + CTRL,
                                                     "last_third")]),
                descriptive_rates={"act_share_by_position_third": {
                    t: {a: round(float(g[f"act_{a}"].mean()), 4) for a in EF.P5.ACT}
                    for t, g in d.groupby("position_third", observed=True)}},
                gate_scope=TD5.DESIGNS["T130"]["gate_scope"])


def t132(F: pd.DataFrame) -> dict:
    d = F[F["body_len"] >= 20]
    early = d[(d["act_conclusion"] == 1) & (d["concl_after_inspect"] == 0)]
    n_traj_early = int(early[CLUSTER].nunique())
    h1 = dict(hypothesis="H1", term="conclusion_before_first_inspection_vs_after",
              trajectories_concluding_before_inspection=n_traj_early,
              conclusion_turns_before_inspection=int(len(early)),
              frozen_floor_trajectories=200, cell_total_conclusion_turns=int(d["act_conclusion"].sum()))
    floor_measured = int((TD5.PREMISES.get("measured") or {})["conclusion_before_first_inspection_trajectories"])
    h1["premise_census_trajectories"] = floor_measured
    if floor_measured < h1["frozen_floor_trajectories"]:
        # The frozen sentence names EXP-0161's measured cell as the thing the floor is tested against, and that census
        # ran on its own 4,000-trajectory sample. The design's frame is the full frozen sample and carries more
        # trajectories in the same cell; both numbers ship, and the larger one does not un-stop a hypothesis the
        # pre-registration stopped.
        h1["verdict"] = f"not_testable_premise_floor_with_{floor_measured}_trajectories"
        h1["note"] = (f"EXP-0161's census measured {floor_measured} trajectories in this cell on its 4,000-trajectory "
                      f"sample against a floor of 200, which is the sentence this hypothesis froze; the design's own "
                      f"frame of {TD5.SAMPLE['traj_cap']} sampled trajectories carries {n_traj_early} in the same "
                      "cell, and the per-cell rates are reported below rather than used to reopen the test")
    late = d[(d["act_conclusion"] == 1) & (d["concl_after_inspect"] == 1)]
    h2 = term(glm(d[d["act_conclusion"] == 1].dropna(subset=["ov_z"]), "ov_z",
                  ["concl_after_inspect"] + CTRL, "gaussian"), "concl_after_inspect")
    h2.update(hypothesis="H2", term="concluded_after_inspection_on_standardised_evidence_overlap",
              cell_early=n_traj_early, cell_late=int(late[CLUSTER].nunique()),
              cell_preceding_turns_with_no_observation_returned_yet=int(
                  (d[(d["act_conclusion"] == 1) & (d["concl_after_inspect"] == 0)]["has_prior_evidence"] == 0).sum()),
              note="the cell that precedes an inspection contains turns written before any observation was returned "
                   "at all, which is what the frozen comparison asks for and is stated here rather than averaged away")
    h3 = term(glm(d, "stops_here", ["act_conclusion"] + CTRL), "act_conclusion")
    h3.update(hypothesis="H3", term="act_conclusion_on_stopping_here")
    rows = [h1, h2, h3]
    if not h1.get("verdict"):
        rows = holm_and_verdict(rows, {"H1": 1.0, "H2": 1.0, "H3": 1.0})
    else:
        rows = holm_and_verdict([h2, h3], {"H2": 1.0, "H3": 1.0})
        h1.setdefault("p", None)
        rows = [h1] + rows
    return dict(n_turns=int(len(d)), n_trajectories=int(d[CLUSTER].nunique()), models=rows,
                strata=strata_rows(d[d["act_conclusion"] == 1].dropna(subset=["ov_z"]),
                                   ["position_third", "category"], "ov_z", ["concl_after_inspect"] + CTRL,
                                   "concl_after_inspect", family="gaussian"),
                baselines=baselines(d.dropna(subset=["ov_z"]), "ov_z",
                                    [("controls_plus_inspection_order", ["concl_after_inspect"] + CTRL,
                                      "concl_after_inspect")], "gaussian"),
                descriptive_rates={"mean_overlap_by_order": {
                    k: {"mean": round(float(g["evidence_overlap"].mean()), 4), "n": int(len(g))}
                    for k, g in d[d["act_conclusion"] == 1].groupby("concl_after_inspect", observed=True)}},
                gate_scope=TD5.DESIGNS["T132"]["gate_scope"])


def t133(F: pd.DataFrame) -> dict:
    d = F[F["body_len"] >= 20]
    after = d[d["prev_obs_error"] == 1]
    h1 = term(glm(d, "repair_diagnose", ["prev_obs_error"] + CTRL), "prev_obs_error")
    h1.update(hypothesis="H1", term="failure_preceded_turn_on_diagnostic_language",
              cell_after_failure=int(len(after)))
    h2 = term(glm(after, "emits_call", ["repair_reissue"] + CTRL), "repair_reissue")
    h2.update(hypothesis="H2", term="reissue_language_on_calling_again_after_failure")
    h3 = term(glm(after, "stops_here", ["repair_abandon"] + CTRL), "repair_abandon")
    h3.update(hypothesis="H3", term="abandon_language_on_stopping_after_failure")
    rows = holm_and_verdict([h1, h2, h3], {"H1": 1.0, "H2": 1.0, "H3": 1.0})
    return dict(n_turns=int(len(d)), n_trajectories=int(d[CLUSTER].nunique()), models=rows,
                strata=strata_rows(d, ["category", "prev_obs_family"], "repair_diagnose",
                                   ["prev_obs_error"] + CTRL, "prev_obs_error"),
                baselines=baselines(d, "repair_diagnose",
                                    [("controls_plus_failure_indicator", ["prev_obs_error"] + CTRL,
                                      "prev_obs_error")]),
                descriptive_rates={"repair_share_by_failure_state": {
                    str(k): {r: round(float(g[r].mean()), 4) for r in
                             ("repair_diagnose", "repair_reissue", "repair_abandon")} | {"n": int(len(g))}
                    for k, g in d.groupby("prev_obs_error", observed=True)}},
                gate_scope=TD5.DESIGNS["T133"]["gate_scope"])


def t134(F: pd.DataFrame) -> dict:
    d = F[(F["body_len"] >= 20) & (F["has_prior_evidence"] == 1)].dropna(subset=["ov_z"])
    h1 = term(glm(d, "ov_z", ["has_causal"] + CTRL, "gaussian"), "has_causal")
    h1.update(hypothesis="H1", term="causal_connective_on_standardised_evidence_overlap",
              cell_connective_turns=int(d["has_causal"].sum()))
    h2 = term(glm(d, "ov_z", ["fam_sum", "fam_diff", "control_z"] + CTRL, "gaussian"), "fam_diff")
    h2.update(hypothesis="H2", term="inferential_minus_explanatory_on_evidence_overlap",
              inferential_turn_share=round(float((d["n_inferential"] > 0).mean()), 4),
              explanatory_turn_share=round(float((d["n_explanatory"] > 0).mean()), 4))
    h2["verdict_direction"] = "predicted_negative: an inferential connective bridges further than it cites"
    h3 = term(glm(d, "ov_z", ["control_z", "has_causal"] + CTRL, "gaussian"), "control_z")
    h3.update(hypothesis="H3", term="causal_control_lexicon_on_evidence_overlap", verdict_rule="specificity",
              control_prevalence=round(float((d["control_count"] > 0).mean()), 4))
    specific = (abs(h3.get("beta") or 0) < BAND_SMALL and abs(h1.get("beta") or 0) >= BAND_SMALL
                and h3.get("ci_lo") is not None and h3["ci_lo"] <= 0 <= h3["ci_hi"])
    h3["verdict"] = ("supported" if specific else
                     "not_specific_control_tracks_the_same_variance" if h3.get("beta") else "not_testable")
    rows = holm_and_verdict([h1, h2, h3], {"H1": 1.0, "H2": -1.0})
    return dict(n_turns=int(len(d)), n_trajectories=int(d[CLUSTER].nunique()), models=rows,
                strata=strata_rows(d, ["body_quartile", "category"], "ov_z", ["has_causal"] + CTRL,
                                   "has_causal", family="gaussian"),
                baselines=baselines(d, "ov_z", [("controls_plus_causal_indicator", ["has_causal"] + CTRL,
                                                 "has_causal")], "gaussian"),
                descriptive_rates={"mean_overlap_by_connective_use": {
                    str(k): {"mean": round(float(g["evidence_overlap"].mean()), 4), "n": int(len(g))}
                    for k, g in d.groupby("has_causal", observed=True)}},
                gate_scope=TD5.DESIGNS["T134"]["gate_scope"])


def t135(F: pd.DataFrame) -> dict:
    d = F[(F["body_len"] >= 20) & (F["has_causal"] == 1) & (F["has_prior_evidence"] == 1)].dropna(subset=["ov_z"])
    h1 = term(glm(d, "ov_z", ["chain"] + CTRL, "gaussian"), "chain")
    h1.update(hypothesis="H1", term="causal_chain_on_standardised_evidence_overlap",
              cell_chain_turns=int(d["chain"].sum()), cell_single_turns=int((d["chain"] == 0).sum()))
    h1["verdict_direction"] = "predicted_negative: more connectives, not more citations"
    h2 = term(glm(d, "stops_here", ["chain"] + CTRL), "chain")
    h2.update(hypothesis="H2", term="causal_chain_on_stopping_here")
    q = []
    for lab, g in d.groupby("body_quartile", observed=True):
        if len(g) < 500:
            continue
        t = term(glm(g, "ov_z", ["chain"] + CTRL, "gaussian"), "chain")
        q.append(dict(stratum=str(lab), rows=int(len(g)), **t))
    same = [x for x in q if x.get("beta") is not None and x["beta"] < 0]
    h3 = dict(hypothesis="H3", term="sign_of_the_chain_contrast_within_body_length_quartiles",
              verdict_rule="sign_reproduction", quartiles=q,
              verdict=("supported" if len(same) >= 3 else
                       "not_reproduced_in_three_of_four_quartiles" if q else "not_testable_thin_strata"))
    rows = holm_and_verdict([h1, h2, h3], {"H1": -1.0, "H2": 1.0})
    return dict(n_turns=int(len(d)), n_trajectories=int(d[CLUSTER].nunique()), models=rows,
                strata=q, baselines=baselines(d, "ov_z", [("controls_plus_chain_indicator", ["chain"] + CTRL,
                                                           "chain")], "gaussian"),
                descriptive_rates={"mean_overlap_by_chain_length": {
                    str(k): {"mean": round(float(g["evidence_overlap"].mean()), 4), "n": int(len(g))}
                    for k, g in d.groupby("n_causal", observed=True) if len(g) >= 50}},
                gate_scope=TD5.DESIGNS["T135"]["gate_scope"])


def t136(F: pd.DataFrame) -> dict:
    d = F[(F["body_len"] >= 20) & (F["has_align"] == 1)].dropna(subset=["align_diff"])
    bt = boot_ci_mean(d, "align_diff")
    if "ci" not in bt:
        h1 = dict(hypothesis="H1", term="plan_alignment_minus_other_trajectory_null", verdict="not_testable",
                  boot_note=bt.get("error"))
    else:
        lo, hi, p = float(bt["ci"][0]), float(bt["ci"][1]), float(bt["p"])
        h1 = dict(hypothesis="H1", term="plan_alignment_minus_other_trajectory_null",
                  beta=round(float(d["align_diff"].mean()), 4), ci_lo=round(lo, 4), ci_hi=round(hi, 4), p=p,
                  n=int(len(d)), clusters=bt["clusters"], is_bootstrap_mean=True,
                  mean_alignment=round(float(d["align_next"].mean()), 4),
                  mean_null=round(float(d["align_perm_mean"].mean()), 4))
        h1["verdict"] = ("supported" if lo > 0 and abs(h1["beta"]) >= BAND else
                         "partial" if lo > 0 else "null" if lo <= 0 <= hi else "opposite")
    h2 = term(glm(d, "prev_obs_error_next", ["align_z"] + CTRL), "align_z")
    h2.update(hypothesis="H2", term="alignment_on_the_next_call_failing",
              verdict_direction="predicted_negative: a plan that matches its call gets a result that works")
    # the freeze names the 20 most frequent tool families, so the families are ranked by rows and not by whichever
    # ones happen to clear a size cut; a family whose bootstrap cannot run is reported as unestimable, not skipped
    sizes = d.groupby("first_call_family", observed=True).size().sort_values(ascending=False)
    top = list(sizes.index[:20])
    q = []
    for lab in top:
        g = d[d["first_call_family"] == lab]
        b = boot_ci_mean(g, "align_diff", draws=200)
        row = dict(stratum=str(lab)[:40], rows=int(len(g)), trajectories=int(g[CLUSTER].nunique()))
        if "ci" in b:
            row.update(beta=round(float(g["align_diff"].mean()), 4), ci_lo=round(float(b["ci"][0]), 4),
                       ci_hi=round(float(b["ci"][1]), 4))
        else:
            row.update(beta=None, unestimable=b.get("error") or "too few clusters for a bootstrap")
        q.append(row)
    est = [x for x in q if x.get("beta") is not None]
    pos = [x for x in est if x["beta"] > 0]
    h3 = dict(hypothesis="H3", term="sign_of_the_alignment_contrast_by_tool_family",
              verdict_rule="sign_reproduction", families=q, families_named=20, families_estimable=len(est),
              families_positive=len(pos),
              verdict=("supported" if len(est) >= 14 and len(pos) >= 14 else
                       f"not_testable_only_{len(est)}_of_20_families_estimable" if len(est) < 14 else
                       f"not_reproduced_in_{len(pos)}_of_{len(est)}_families_below_the_14_frozen_floor"))
    rows = holm_and_verdict([h1, h2, h3], {"H1": 1.0, "H2": -1.0})
    return dict(n_turns=int(len(d)), n_trajectories=int(d[CLUSTER].nunique()), models=rows,
                strata=q, baselines=baselines(d, "prev_obs_error_next",
                                              [("controls_plus_alignment", ["align_z"] + CTRL, "align_z")]),
                descriptive_rates={"alignment_distribution": {
                    str(k): int(v) for k, v in
                    pd.cut(d["align_next"], [0, .05, .1, .2, .4, 1.0],
                           labels=["0-0.05", "0.05-0.1", "0.1-0.2", "0.2-0.4", "0.4+"]).value_counts().items()}},
                gate_scope=TD5.DESIGNS["T136"]["gate_scope"])


DESIGN_FN = {"EXP-0165": ("T130", t130), "EXP-0166": ("T132", t132), "EXP-0167": ("T133", t133),
             "EXP-0168": ("T134", t134), "EXP-0169": ("T135", t135), "EXP-0170": ("T136", t136)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--only", action="append", default=[])
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    F = load()
    if a.quick:
        keep = F[CLUSTER].drop_duplicates().sample(2000, random_state=TD5.SEED)
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
                             f"those blocks would ship a header with no numbers - measure it or drop the table")
        art.update(exp_id=exp, topic=topic, seed=TD5.SEED, quick=a.quick, started_at=W.now(),
                   frame_file_read=F.attrs.get("frame_file"),
                   invocation=" ".join([sys.executable] + sys.argv),
                   run_cost=W.run_cost_row(exp, t0, int(len(F)), int(F.shape[1]), "wave-5 design"),
                   finished_at=W.now())
        arts[exp] = art
        print(f"{exp} ({topic}): wrote {W.write_raw(exp, f'wave5_design_{exp[-4:]}', art).name}", flush=True)
        pd.DataFrame(art.get("models") or []).to_csv(W.OUT / f"EXP{exp[-4:]}_{topic.lower()}_models.csv",
                                                     index=False)
        if art.get("strata"):
            pd.DataFrame(art["strata"]).to_csv(W.OUT / f"EXP{exp[-4:]}_{topic.lower()}_strata.csv", index=False)
    for exp, art in arts.items():
        vs = {(m.get("hypothesis") or m.get("term")): m.get("verdict") for m in (art.get("models") or [])}
        print(f"  {exp}: {json.dumps(vs, default=str)[:240]}")
    print(f"wallclock {round(time.time() - t0, 1)}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
