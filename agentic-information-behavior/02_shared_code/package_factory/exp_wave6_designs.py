"""EXP-0174..EXP-0179: wave 6's six pre-registered tests, run from the frozen sentences in topic_designs_wave6.

Nothing here decides a threshold. Each hypothesis carries the band floor and direction its freeze names, Holm is
applied to the three hypotheses a design declares and to nothing else, and every interval is cluster-robust on
`instance_id` - the unit a rollout is drawn within, so rollouts of the same task are never treated as independent.
A cell a premise gate scoped out is reported as `not_testable_*` with the count that produced it, which is a result
rather than a gap to close by moving a floor.

    python 02_shared_code/package_factory/exp_wave6_designs.py [--quick] [--only EXP-0174]
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
import numpy as np                                                # noqa: E402
import pandas as pd                                               # noqa: E402
import wave_lib as W                                              # noqa: E402
import exp_wave6_features as EF                                   # noqa: E402
import topic_designs_wave6 as TD6                                 # noqa: E402

assert TD6.BANDS == W.BANDS, "the wave-6 freeze and wave_lib disagree about the effect bands"
BAND = W.BANDS["medium"]
BAND_SMALL = W.BANDS["small"]
CLUSTER = TD6.COMMON["sample"]["cluster_unit"]
FRAME_NAME = "EXP0173_wave6_step_features.csv.gz"
# the standard control set, one definition for the wave: how deep the rollout is, where in it this step sits, how
# complex the stated need is, how much text the observation returned, and whether the step before it failed
CTRL = ["log_steps", "step_position", "need_words_z", "obs_chars_log", "prev_failed"]
# `continues` is 1 exactly when the step is not the rollout's last, which is `step_position < 1`. A model of
# continuation therefore cannot hold position fixed - the outcome would be a deterministic function of its own
# regressor, the likelihood separates and the cluster-robust covariance comes back singular - so T158 estimates
# against the rest of the control set (deviation W6-D08).
CTRL_CONTINUATION = [c for c in CTRL if c != "step_position"]


def z(s: pd.Series) -> pd.Series:
    v = pd.to_numeric(s, errors="coerce")
    sd = float(v.std(ddof=0))
    return (v - float(v.mean())) / sd if sd > 0 else v * 0.0


def load() -> pd.DataFrame:
    """The wave-6 frame with the derived contrasts the freeze names. Column names are checked, not guessed."""
    import os
    name = FRAME_NAME
    search = []
    if os.environ.get("AIB_INPUT_DIR"):
        search.append(pathlib.Path(os.environ["AIB_INPUT_DIR"]) / name)
    search += [W.OUT / name, W.ROOT / "results_processed" / name]
    path = next((q for q in search if pathlib.Path(q).is_file()), None)
    if path is None:
        raise SystemExit(f"ABORT: {name} is not where the designs look ({', '.join(map(str, search))}) - run "
                         f"{TD6.FEATURE_EXP} (exp_wave6_features.py) first")
    F = pd.read_csv(gzip.open(path, "rt"))
    F.attrs["frame_file"] = str(path)
    need = ["instance_id", "traj_key", "step_index", "n_steps", "log_steps", "step_position", "family",
            "first_family", "instance_modal_first", "off_modal_first", "stays_in_family", "switched",
            "is_repeat", "repeat_index", "has_exact_repeat", "new_information", "cumulative_newness",
            "failed_observation", "obs_chars", "scent_jaccard", "scent_contain", "step_words", "continues",
            "submitted", "switch_rate", "family_concentration", "need_words", "need_words_z", "step_budget",
            "task_family", "single_rollout_instance"]
    miss = [c for c in need if c not in F.columns]
    if miss:
        raise SystemExit(f"ABORT: the wave-6 frame lacks {miss}; the designs would drop those terms in silence")
    F["obs_chars_log"] = np.log1p(F["obs_chars"].astype(float))
    F["prev_failed"] = F.sort_values(["traj_key", "step_index"]).groupby("traj_key")["failed_observation"].shift(1)
    F["prev_failed"] = F["prev_failed"].fillna(0).astype(int)
    F["prev_newness"] = F.sort_values(["traj_key", "step_index"]).groupby("traj_key")["new_information"].shift(1)
    F["prev_continues"] = F["continues"].astype(int)
    F["new_z"] = z(F["new_information"].astype(float))
    F["scent_z"] = z(F["scent_jaccard"].astype(float))
    F["scent_contain_z"] = z(F["scent_contain"].astype(float))
    F["step_words_log"] = np.log1p(F["step_words"].astype(float))
    F["cum_new_z"] = z(F["cumulative_newness"].astype(float))
    F["prev_new_z"] = z(F["prev_newness"].astype(float))
    F["repeat_index_capped"] = F["repeat_index"].clip(upper=3).astype(int)
    F["step_budget_log"] = np.log1p(F["step_budget"].astype(float))
    F["is_search_first"] = F["first_family"].isin(["search_name", "search_content"]).astype(int)
    F["len_quartile"] = pd.qcut(F["n_steps"].rank(method="first"), 4,
                                labels=["q1_shortest", "q2", "q3", "q4_longest"]).astype(str)
    F["position_third"] = pd.cut(F["step_position"], [0.0, 1 / 3, 2 / 3, 1.0001],
                                 labels=["first_third", "middle_third", "last_third"]).astype(str)
    return F


def glm(d: pd.DataFrame, y: str, xs, family="binomial") -> pd.DataFrame:
    """The frozen model for one term, with the outcome never allowed to be its own regressor.

    T155's H1 is a depth equation whose right-hand side is the wave's standard control set, and that set contains
    depth. A column repeated in the design matrix makes the dependent variable a two-column frame, the fit is not
    identified at all, and wave_lib's own degenerate-cell test fails on an ambiguous truth value. The term is
    dropped here and the drop is reported, because the alternative is a coefficient that means nothing.

    The same applies to a control that is constant on the rows a design actually estimates on - `prev_failed` is
    identically 0 at a rollout's first step, so every trajectory-level model that reaches for it arrives at a
    singular design matrix. Constant terms are dropped and named in the result's attrs, which `term()` copies into
    the reported row, so a reader sees which control the cell could support.
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
    f = W.glm_term(d, y, xs, family, cluster=CLUSTER)
    if f is not None and not f.empty:
        f.attrs["dropped_constant_terms"] = "+".join(const) or "none"
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
    return out


def boot_ci_mean(d: pd.DataFrame, stat: str, draws: int = 300) -> dict:
    return W.cluster_boot_ci_and_p(d, CLUSTER, lambda x: float(pd.to_numeric(x[stat], errors="coerce").mean()),
                                   draws=draws, seed=TD6.SEED)


def _finite(v) -> bool:
    try:
        return bool(np.isfinite(float(v)))
    except (TypeError, ValueError):
        return False


def holm_and_verdict(rows: list, direction: dict, band: float = BAND) -> list:
    ps = {r["hypothesis"]: (1.0 if r.get("p") is None else float(r["p"])) for r in rows}
    adj = W.holm(ps)
    for r in rows:
        if r.get("verdict"):
            r.setdefault("p_holm", adj.get(r["hypothesis"], 1.0))
            continue
        r["p_holm"] = adj.get(r["hypothesis"], 1.0)
        if r.get("verdict_rule") in ("specificity", "sign_reproduction"):
            continue
        if r.get("beta") is None:
            r["verdict"] = "not_testable_no_coefficient_estimated"
            continue
        if not all(_finite(v) for v in (r["beta"], r.get("ci_lo"), r.get("ci_hi"), r.get("p"))):
            r["verdict"] = "not_estimable_non_finite_interval"
            r.setdefault("note", "the cluster-robust interval or the coefficient is not finite on these rows, so no "
                                 "direction is claimed; the raw values are kept in this row")
            continue
        r["verdict"] = W.verdict(r["beta"], r.get("ci_lo"), r.get("ci_hi"), r["p_holm"], band,
                                 direction=direction.get(r["hypothesis"], 1.0))
    return rows


def baselines(d: pd.DataFrame, y: str, specs, family="binomial", controls=None) -> list:
    """The controls-only model, then each construct added, with the deviance drop between them.

    The control set is a parameter because a design can need a different one from the wave default: T158 estimates
    continuation, whose outcome is determined by `step_position`, so that column is not a usable control there and
    the nested comparison has to be built on the same terms the hypothesis model uses.
    """
    from scipy import stats as SP
    controls = controls or CTRL
    base = glm(d, y, controls, family)
    if base is None or base.empty:
        return [dict(model="controls_only", dv=y, note="not fitted on these rows")]
    dev0 = float(base["deviance"].iloc[0])
    kept = lambda cols: [c for c in dict.fromkeys(cols) if c in d.columns and c != y]
    rows = [dict(model="controls_only", dv=y, terms="+".join(controls), n=int(base["n"].iloc[0]),
                 clusters=int(d[CLUSTER].nunique()), deviance=round(dev0, 2))]
    for name, xs, focus in specs:
        f = glm(d, y, xs, family)
        if f is None or f.empty:
            rows.append(dict(model=name, dv=y, terms="+".join(dict.fromkeys(xs)),
                             note="not fitted: the design matrix cannot be estimated on these rows"))
            continue
        dev1 = float(f["deviance"].iloc[0])
        kept = lambda cols: [c for c in dict.fromkeys(cols) if c in d.columns and c != y]
        dfree = max(1, len(kept(xs)) - len(kept(controls)))
        lr = 2.0 * (dev0 - dev1)
        rows.append(dict(model=name, dv=y, terms="+".join(dict.fromkeys(xs)), n=int(f["n"].iloc[0]),
                         deviance=round(dev1, 2), added_term=focus, deviance_drop=round(dev0 - dev1, 2),
                         lr_chi2=round(lr, 2), lr_df=dfree,
                         lr_p=round(float(SP.chi2.sf(max(lr, 0.0), dfree)), 6),
                         **{f"{focus}_{k}": v for k, v in term(f, focus).items() if k != "n"}))
    return rows


def strata_rows(d: pd.DataFrame, splits, y: str, xs, focus: str, min_rows: int = 1000, family="binomial") -> list:
    rows = []
    for col in splits:
        for lab, g in d.groupby(col, observed=True):
            if len(g) < min_rows or g[y].nunique() < 2:
                continue
            kept = [c for c in xs if c in g.columns and g[c].nunique(dropna=False) > 1]
            dropped = [c for c in xs if c not in kept]
            t = term(glm(g, y, kept, family), focus)
            # the cell's own constant list is the one computed above: `glm()` also drops zero-variance terms, but it
            # sees the already-filtered list here, so its report would say "none" while a control was in fact removed
            t.pop("dropped_constant_terms", None)
            rows.append(dict(stratification=col, stratum=str(lab)[:40], rows=int(len(g)),
                             instances=int(g[CLUSTER].nunique()),
                             dropped_constant_terms="+".join(dropped) or "none",
                             identifiable=focus in kept, **t))
    return rows


# ------------------------------------------------------------------ the six designs
def t155(F: pd.DataFrame) -> dict:
    d = F.copy()
    h1 = term(glm(d, "log_steps", ["need_words_z"] + CTRL, "gaussian"), "need_words_z")
    h1.update(hypothesis="H1", term="need_length_within_instance_on_log_steps",
              instances_with_2plus_rollouts=int(d.drop_duplicates("traj_key").groupby("instance_id")[
                  "traj_key"].nunique().ge(2).sum()))
    h1["verdict_direction"] = "predicted_positive: a longer stated need goes with a deeper search"
    budget = float(d["n_steps"].max())
    h2 = term(glm(d.drop_duplicates("traj_key"), "submitted",
                  ["log_steps", "need_words_z", "step_budget_log", "prev_failed"], "binomial"), "log_steps")
    h2.update(hypothesis="H2", term="depth_on_submitting_rather_than_running_out",
              step_ceiling_observed_in_frame=int(budget),
              submitted_trajectories=int(d.drop_duplicates("traj_key")["submitted"].sum()))
    h2["verdict_direction"] = "predicted_negative: a deeper search is one that has not yet ended by submission"
    q = []
    for lab, g in d.drop_duplicates("traj_key").groupby("task_family", observed=True):
        if len(g) < 200 or g[CLUSTER].nunique() < 30:
            continue
        t = term(glm(g, "log_steps", ["need_words_z"] + CTRL, "gaussian"), "need_words_z")
        if t.get("beta") is not None:
            q.append(dict(stratum=str(lab)[:40], rows=int(len(g)), instances=int(g[CLUSTER].nunique()), **t))
    pos = [x for x in q if (x.get("beta") or 0) > 0]
    h3 = dict(hypothesis="H3", term="sign_of_the_depth_need_association_by_task_family",
              verdict_rule="sign_reproduction", families=q, families_tested=len(q),
              verdict=("supported" if len(pos) >= min(10, len(q)) and len(q) >= 10 else
                       f"not_reproduced_in_{len(pos)}_of_{len(q)}_families_below_the_10_frozen_floor" if q else
                       "not_testable_no_family_large_enough"))
    rows = holm_and_verdict([h1, h2, h3], {"H1": 1.0, "H2": -1.0})
    return dict(n_steps=int(len(d)), n_trajectories=int(d["traj_key"].nunique()),
                n_instances=int(d[CLUSTER].nunique()), models=rows,
                strata=strata_rows(d, ["len_quartile", "position_third"], "log_steps",
                                   ["need_words_z"] + CTRL, "need_words_z", family="gaussian"),
                baselines=baselines(d, "log_steps", [("controls_plus_need_length", ["need_words_z"] + CTRL,
                                                      "need_words_z")], "gaussian"),
                descriptive_rates={"depth_by_need_quartile": {
                    str(k): {"mean_steps": round(float(g["n_steps"].mean()), 3),
                             "submitted_share": round(float(g.drop_duplicates("traj_key")["submitted"].mean()), 4),
                             "rows": int(len(g))}
                    for k, g in d.groupby(pd.qcut(d["need_words"], 4, labels=["n1_shortest", "n2", "n3",
                                                                              "n4_longest"]).astype(str),
                                          observed=True)},
                    "step_budget_by_instance": {
                        "median": float(d.groupby("instance_id")["step_budget"].median().median()),
                        "max_observed": int(d["n_steps"].max())}},
                gate_scope=TD6.DESIGNS["T155"]["gate_scope"])


def t157(F: pd.DataFrame) -> dict:
    d = F[F["obs_chars"] > 0].dropna(subset=["new_information"]).copy()
    h1 = term(glm(d, "new_z", ["scent_z"] + CTRL, "gaussian"), "scent_z")
    h1.update(hypothesis="H1", term="scent_on_new_information_returned",
              steps_with_an_observation=int(len(d)))
    h1["verdict_direction"] = "predicted_positive: a step that names what it expects gets information it did not have"
    h2 = term(glm(d, "new_z", ["scent_contain_z"] + CTRL, "gaussian"), "scent_contain_z")
    h2.update(hypothesis="H2", term="same_model_under_the_asymmetric_scent_instrument")
    agree = W.rho_ci(d[[("scent_z"), ("scent_contain_z"), CLUSTER]].dropna(), CLUSTER, "scent_z", "scent_contain_z") \
        if d["scent_z"].nunique() > 2 and d["scent_contain_z"].nunique() > 2 else {}
    h2["instruments_agree"] = agree
    h3 = term(glm(d, "new_z", ["step_words_log"] + CTRL, "gaussian"), "step_words_log")
    h3.update(hypothesis="H3", term="verbosity_control_on_new_information",
              verdict_rule="specificity")
    specific = (abs(h3.get("beta") or 0) < BAND_SMALL and abs(h1.get("beta") or 0) >= BAND_SMALL
                and h3.get("ci_lo") is not None and h3["ci_lo"] <= 0 <= h3["ci_hi"])
    h3["verdict"] = ("supported" if specific else
                     "not_specific_control_tracks_the_same_variance" if h3.get("beta") is not None else
                     "not_testable_no_coefficient_estimated")
    h3["note"] = ("the freeze asks whether scent is only verbosity: H3 is supported when the control produces no "
                  "association while H1 does, so a positive coefficient here is the negative result for scent")
    rows = holm_and_verdict([h1, h2, h3], {"H1": 1.0, "H2": 1.0})
    return dict(n_steps=int(len(d)), n_trajectories=int(d["traj_key"].nunique()),
                n_instances=int(d[CLUSTER].nunique()), models=rows,
                strata=strata_rows(d, ["position_third", "family"], "new_z", ["scent_z"] + CTRL, "scent_z",
                                   family="gaussian"),
                baselines=baselines(d, "new_z", [("controls_plus_scent", ["scent_z"] + CTRL, "scent_z"),
                                                 ("controls_plus_verbosity", ["step_words_log"] + CTRL,
                                                  "step_words_log")], "gaussian"),
                descriptive_rates={"newness_by_scent_decile": {
                    str(k): {"mean_newness": round(float(g["new_information"].mean()), 4), "rows": int(len(g))}
                    for k, g in d.groupby(pd.qcut(d["scent_jaccard"].rank(method="first"), 10,
                                                  labels=False, duplicates="drop").astype(str), observed=True)},
                    "mean_scent_by_command_family": {
                        str(k): {"scent": round(float(g["scent_jaccard"].mean()), 4),
                                 "newness": round(float(g["new_information"].mean()), 4), "rows": int(len(g))}
                        for k, g in d.groupby("family", observed=True) if len(g) >= 500}},
                gate_scope=TD6.DESIGNS["T157"]["gate_scope"])


def t158(F: pd.DataFrame) -> dict:
    # the unit H1 and H2 share: a step whose observation came back, whose `continues` records whether the search
    # took another step after it. The frozen "newness of the last step" is therefore this step's own observation -
    # it is the observation the next step would be continuing past - and the last step of a rollout contributes a 0.
    d = F[F["obs_chars"] > 0].dropna(subset=["new_information"]).copy()
    h1 = term(glm(d, "continues", ["new_z"] + CTRL_CONTINUATION, "binomial"), "new_z")
    h1.update(hypothesis="H1", term="newness_of_the_observation_just_returned_on_continuing",
              steps_following_an_observation=int(len(d)),
              last_steps_in_this_cell=int((d["step_index"] == d["n_steps"]).sum()))
    h1["verdict_direction"] = "predicted_negative: a rich haul ends the search sooner"
    lim = (TD6.PREMISES.get("verdict") or {}).get("claim_limited") or {}
    after_obs = d
    h2 = term(glm(after_obs, "continues", ["failed_observation"] + CTRL_CONTINUATION, "binomial"), "failed_observation")
    h2.update(hypothesis="H2", term="failed_observation_on_continuing_the_search",
              failed_observations=int(after_obs["failed_observation"].sum()),
              failure_marker_share=round(float(after_obs["failed_observation"].mean()), 4),
              frozen_floor_share_of_observations=0.20,
              census_share_measured=float((TD6.PREMISES.get("measured") or {}).get(
                  "failure_marker_share_of_observations")))
    if "G11_failure_marker_present" in lim:
        h2["verdict"] = "not_testable_premise_floor_share_0p20_measured_0p1855"
        h2["note"] = ("EXP-0172's census measured the failure-marker share on every row of the twelve drawn files; "
                      "the frame's own share is printed beside it, and the frozen sentence - not the size of the "
                      "cell - decides that H2 is limited")
        h2.setdefault("p", None)
    quartiles = []
    for lab, g in after_obs.groupby("len_quartile", observed=True):
        if len(g) < 1000:
            continue
        t = term(glm(g, "submitted", ["cum_new_z"] + CTRL, "binomial"), "cum_new_z")
        if t.get("beta") is not None:
            quartiles.append(dict(stratum=str(lab), rows=int(len(g)), instances=int(g[CLUSTER].nunique()), **t))
    pos = [x for x in quartiles if (x.get("beta") or 0) > 0]
    h3 = dict(hypothesis="H3", term="cumulative_newness_on_submitting_within_length_quartile",
              verdict_rule="sign_reproduction", strata=quartiles, quartiles_tested=len(quartiles),
              verdict=("supported" if len(pos) >= min(3, len(quartiles)) and len(quartiles) >= 3 else
                       f"not_reproduced_in_{len(pos)}_of_{len(quartiles)}_quartiles" if quartiles else
                       "not_testable_no_quartile_large_enough"))
    estimable = [x for x in (h1, h2, h3) if not x.get("verdict")]
    holm_and_verdict(estimable, {"H1": -1.0, "H3": 1.0})
    ordered = [h1, h2, h3]
    return dict(n_steps=int(len(d)), n_trajectories=int(d["traj_key"].nunique()),
                n_instances=int(d[CLUSTER].nunique()), models=ordered,
                strata=strata_rows(after_obs, ["family", "len_quartile"], "continues",
                                   ["new_z"] + CTRL_CONTINUATION, "new_z", family="binomial"),
                baselines=baselines(after_obs, "continues",
                                    [("controls_plus_observation_newness", ["new_z"] + CTRL_CONTINUATION, "new_z"),
                                     ("controls_plus_failure", ["failed_observation"] + CTRL_CONTINUATION,
                                      "failed_observation")], family="binomial",
                                    controls=CTRL_CONTINUATION),
                descriptive_rates={"continuation_by_observation_newness_decile": {
                    str(k): {"continue_share": round(float(g["continues"].mean()), 4), "rows": int(len(g))}
                    for k, g in after_obs.groupby(
                        pd.qcut(after_obs["new_information"].rank(method="first"), 10, labels=False,
                                duplicates="drop").astype(str), observed=True)},
                    "newness_by_repetition": {
                        str(int(k)): {"mean_newness": round(float(g["new_information"].mean()), 4),
                                      "rows": int(len(g))}
                        for k, g in F.dropna(subset=["new_information"]).groupby("repeat_index_capped",
                                                                                observed=True)}},
                gate_scope=TD6.DESIGNS["T158"]["gate_scope"])


def t168(F: pd.DataFrame) -> dict:
    d = F[(F["step_index"] > 1) & (F["obs_chars"] > 0)].dropna(subset=["new_information"]).copy()
    h1 = term(glm(d, "new_z", ["switched"] + CTRL, "gaussian"), "switched")
    h1.update(hypothesis="H1", term="family_switch_on_new_information", switch_steps=int(d["switched"].sum()),
              stayed_steps=int((d["switched"] == 0).sum()))
    h1["verdict_direction"] = "predicted_negative: the step after a switch returns less that is new"
    traj = d.drop_duplicates("traj_key")
    h2 = term(glm(traj, "log_steps", ["switch_rate", "need_words_z", "step_budget_log"], "gaussian"), "switch_rate")
    h2.update(hypothesis="H2", term="switch_rate_on_rollout_depth", trajectories=int(len(traj)))
    h2["verdict_direction"] = "predicted_positive: switching is exploration, not inefficiency"
    q = []
    for lab, g in d.groupby("family", observed=True):
        if len(g) < 1000 or int(g["switched"].sum()) < 200:
            continue
        t = term(glm(g, "new_z", ["switched"] + CTRL, "gaussian"), "switched")
        if t.get("beta") is not None:
            q.append(dict(stratum=str(lab)[:40], rows=int(len(g)), switches=int(g["switched"].sum()), **t))
    neg = [x for x in q if (x.get("beta") or 0) < 0]
    h3 = dict(hypothesis="H3", term="sign_of_the_switching_cost_by_command_family", verdict_rule="sign_reproduction",
              families=q, families_tested=len(q),
              verdict=("supported" if len(neg) >= min(5, len(q)) and len(q) >= 5 else
                       f"not_reproduced_in_{len(neg)}_of_{len(q)}_families_below_the_5_frozen_floor" if q else
                       "not_testable_no_family_large_enough"))
    rows = holm_and_verdict([h1, h2, h3], {"H1": -1.0, "H2": 1.0})
    return dict(n_steps=int(len(d)), n_trajectories=int(d["traj_key"].nunique()),
                n_instances=int(d[CLUSTER].nunique()), models=rows,
                strata=strata_rows(d, ["position_third", "family"], "new_z", ["switched"] + CTRL, "switched",
                                   family="gaussian"),
                baselines=baselines(d, "new_z", [("controls_plus_switch", ["switched"] + CTRL, "switched")],
                                     "gaussian"),
                descriptive_rates={"newness_by_switch_state": {
                    str(int(k)): {"mean_newness": round(float(g["new_information"].mean()), 4), "rows": int(len(g))}
                    for k, g in d.groupby("switched", observed=True)},
                    "family_transitions": {
                        f"{a}->{b}": int(n) for (a, b), n in
                        d.groupby(["prev_family", "family"], observed=True).size().sort_values(ascending=False)
                        .head(16).items()}},
                gate_scope=TD6.DESIGNS["T168"]["gate_scope"])


def t170(F: pd.DataFrame) -> dict:
    traj = F.drop_duplicates("traj_key").copy()
    usable = traj[traj["single_rollout_instance"] == 0]
    h1 = term(glm(usable, "family_concentration", ["off_modal_first"] + [c for c in CTRL if c != "step_position"],
                  "gaussian"), "off_modal_first")
    h1.update(hypothesis="H1", term="off_modal_first_action_on_family_concentration",
              rollouts_with_a_modal_contrast=int(len(usable)),
              off_modal_rollouts=int(usable["off_modal_first"].sum()),
              first_family_share=usable["first_family"].value_counts(normalize=True).head(6).round(4).to_dict())
    h1["verdict_direction"] = "predicted_positive: an off-modal opening keeps the rollout in its own first family " \
                              "less, if the path is set by the action rather than by the task"
    step = F[F["step_index"] > 1].copy()
    h2 = term(glm(step, "submitted", ["stays_in_family", "log_steps", "need_words_z", "prev_failed"], "binomial"),
              "stays_in_family")
    h2.update(hypothesis="H2", term="staying_in_the_first_family_on_submitting_with_depth_held")
    h3 = term(glm(step, "stays_in_family", ["is_search_first"] + CTRL, "binomial"), "is_search_first")
    h3.update(hypothesis="H3", term="search_first_opening_on_staying_in_family")
    h3["verdict_direction"] = "predicted_positive: opening with a search concentrates the path more than opening " \
                              "with a read or an edit"
    rows = holm_and_verdict([h1, h2, h3], {"H1": 1.0, "H2": 1.0, "H3": 1.0})
    return dict(n_steps=int(len(step)), n_trajectories=int(traj["traj_key"].nunique()),
                n_instances=int(traj[CLUSTER].nunique()), models=rows,
                strata=strata_rows(step, ["first_family", "len_quartile"], "stays_in_family",
                                   ["is_search_first"] + CTRL, "is_search_first", family="binomial"),
                baselines=baselines(step, "stays_in_family",
                                    [("controls_plus_search_first", ["is_search_first"] + CTRL, "is_search_first")],
                                    "binomial"),
                descriptive_rates={"family_mix_after_the_first_step_by_first_family": {
                    str(k): {fam: round(float(v), 4) for fam, v in
                             g[g["step_index"] > 1]["family"].value_counts(normalize=True).head(6).items()}
                    for k, g in step.groupby("first_family", observed=True) if len(g) >= 1000},
                    "concentration_by_first_family": {
                        str(k): {"mean": round(float(g["family_concentration"].mean()), 4),
                                 "submitted_share": round(float(g["submitted"].mean()), 4),
                                 "trajectories": int(len(g))}
                        for k, g in traj.groupby("first_family", observed=True) if len(g) >= 200}},
                gate_scope=TD6.DESIGNS["T170"]["gate_scope"])


def t174(F: pd.DataFrame) -> dict:
    d = F[(F["step_index"] > 1) & (F["obs_chars"] > 0)].dropna(subset=["new_information"]).copy()
    h1 = term(glm(d, "new_z", ["is_repeat"] + CTRL, "gaussian"), "is_repeat")
    h1.update(hypothesis="H1", term="repeated_command_on_new_information", repeated_steps=int(d["is_repeat"].sum()),
              first_run_steps=int((d["is_repeat"] == 0).sum()))
    h1["verdict_direction"] = "predicted_negative: a command already run returns nothing new"
    traj = F.drop_duplicates("traj_key")
    h2 = term(glm(traj, "submitted", ["has_exact_repeat", "log_steps", "need_words_z", "step_budget_log"],
                  "binomial"), "has_exact_repeat")
    h2.update(hypothesis="H2", term="exact_repeat_present_on_submitting_with_depth_held",
              trajectories_with_repeat=int(traj["has_exact_repeat"].sum()))
    h2["verdict_direction"] = "predicted_negative: a rollout that repeats is less likely to end by submission"
    prof = []
    for k, g in d.groupby("repeat_index_capped", observed=True):
        b = boot_ci_mean(g, "new_information")
        if "ci" in b:
            prof.append(dict(repeat_index=int(k), rows=int(len(g)),
                             mean_newness=round(float(g["new_information"].mean()), 4),
                             ci_lo=round(float(b["ci"][0]), 4), ci_hi=round(float(b["ci"][1]), 4),
                             clusters=int(b["clusters"])))
    mono = [p for p in prof if p["repeat_index"] >= 1]
    falling = all(a["mean_newness"] >= b["mean_newness"] for a, b in zip(prof, prof[1:])) and len(prof) >= 3
    h3 = dict(hypothesis="H3", term="newness_profile_by_number_of_prior_runs", verdict_rule="dose_response",
              profile=prof,
              verdict=("supported" if falling and mono else
                       "not_monotone_in_" + str(len(prof)) + "_measured_levels" if prof else
                       "not_testable_no_repeat_levels"))
    rows = holm_and_verdict([h1, h2, h3], {"H1": -1.0, "H2": -1.0})
    return dict(n_steps=int(len(d)), n_trajectories=int(F["traj_key"].nunique()),
                n_instances=int(F[CLUSTER].nunique()), models=rows,
                strata=strata_rows(d, ["family", "len_quartile"], "new_z", ["is_repeat"] + CTRL, "is_repeat",
                                   family="gaussian"),
                baselines=baselines(d, "new_z", [("controls_plus_repeat", ["is_repeat"] + CTRL, "is_repeat")],
                                     "gaussian"),
                descriptive_rates={"newness_by_repeat_count": {
                    str(int(k)): {"mean_newness": round(float(g["new_information"].mean()), 4), "rows": int(len(g))}
                    for k, g in d.groupby("repeat_index", observed=True) if len(g) >= 20},
                    "most_repeated_commands": {
                        str(k)[:70]: int(v) for k, v in
                        F.groupby("command_sha")["command_sha"].size().sort_values(ascending=False).head(8).items()}},
                gate_scope=TD6.DESIGNS["T174"]["gate_scope"])


DESIGN_FN = {"EXP-0174": ("T155", t155), "EXP-0175": ("T157", t157), "EXP-0176": ("T158", t158),
             "EXP-0177": ("T168", t168), "EXP-0178": ("T170", t170), "EXP-0179": ("T174", t174)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--only", action="append", default=[])
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    F = load()
    if a.quick:
        keep = F[CLUSTER].drop_duplicates().sample(900, random_state=TD6.SEED)
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
        art.update(exp_id=exp, topic=topic, seed=TD6.SEED, quick=a.quick, started_at=W.now(),
                   frame_file_read=F.attrs.get("frame_file"),
                   invocation=" ".join([sys.executable] + sys.argv),
                   run_cost=W.run_cost_row(exp, t0, int(len(F)), int(F.shape[1]), "wave-6 design"),
                   finished_at=W.now())
        arts[exp] = art
        print(f"{exp} ({topic}): wrote {W.write_raw(exp, f'wave6_design_{exp[-4:]}', art).name}", flush=True)
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
