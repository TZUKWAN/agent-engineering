"""EXP-0192..EXP-0194: wave 8's three surviving pre-registered tests, run from the frozen sentences in topic_designs_wave8.

Wave 8 came to the estate with five designs; EXP-0190's own gates stopped two of them before a single association was
estimated (T175 and T176, at G5 and G13, recorded with the values that stopped them), and what runs here is the rest.
Nothing in this file decides a threshold: each hypothesis carries the band floor and the direction its freeze names,
Holm is applied to the three hypotheses of one design and to nothing else, and every interval is cluster-robust on
`traj_id` - the unit a turn is nested in, so two turns of one search are never treated as two observations.

The estimators are imported from wave 7 rather than restated, so a coefficient in wave 8 is computed exactly the way
one in wave 7 was: the same design-matrix guards, the same non-finite labels, the same descriptive-row handling.

    python 02_shared_code/package_factory/exp_wave8_designs.py [--quick] [--only EXP-0192]
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
import topic_designs_wave8 as TD8                                 # noqa: E402
import exp_wave7_designs as D7                                    # noqa: E402  the estimators, unchanged
import exp_wave5_features as EF5                                   # noqa: E402  one kappa, all waves

assert TD8.BANDS == W.BANDS, "the wave-8 freeze and wave_lib disagree about the effect bands"
BAND = W.BANDS["medium"]
BAND_SMALL = W.BANDS["small"]
CLUSTER = TD8.COMMON["sample"]["cluster_unit"]                    # "traj_id"
FRAME = "EXP0191_wave8_turn_features.csv.gz"
# the standard controls, one definition for the wave: how long the search was and how long the instruction was. A
# design that promises a further control adds that term itself, never silently.
CTRL = ["log_turns", "task_words_log"]
term, holm_and_verdict, z = D7.term, D7.holm_and_verdict, D7.z


# wave 7's estimators default to its own cluster column, so they are wrapped rather than called: a wave-8 interval is
# cluster-robust on traj_id unless a call says otherwise, and a silent fall back to `query_id` would fit a frame that
# has no such column and raise deep inside a bootstrap
def glm(d, y, xs, family="binomial", cluster=CLUSTER):
    return D7.glm(d, y, xs, family, cluster)


def baselines(d, y, specs, family="binomial", controls=None, cluster=CLUSTER):
    return D7.baselines(d, y, specs, family, controls, cluster)


def strata_rows(d, splits, y, xs, focus, min_rows=1000, family="binomial", cluster=CLUSTER):
    return D7.strata_rows(d, splits, y, xs, focus, min_rows, family, cluster)


def boot(d, cluster, fn, draws: int = 2000) -> dict:
    return W.cluster_boot_ci_and_p(d, cluster, fn, draws=draws, seed=TD8.SEED)


def _read(name: str) -> pd.DataFrame:
    search = []
    if os.environ.get("AIB_INPUT_DIR"):
        search.append(pathlib.Path(os.environ["AIB_INPUT_DIR"]) / name)
    search += [W.OUT / name, W.ROOT / "results_processed" / name]
    path = next((q for q in search if pathlib.Path(q).is_file()), None)
    if path is None:
        raise SystemExit(f"ABORT: {name} is not where the designs look ({', '.join(map(str, search))}) - run "
                         f"{TD8.FEATURE_EXP} (exp_wave8_features.py) first")
    F = pd.read_csv(gzip.open(path, "rt", encoding="utf-8"))
    F.attrs["frame_file"] = str(path)
    return F


def load() -> pd.DataFrame:
    """The wave-8 turn frame plus the derived contrasts the freeze names. Column names are checked, not guessed."""
    F = _read(FRAME)
    need = ["traj_id", "category", "turn_index", "n_turns", "position", "is_final_turn", "stops_here",
            "traj_ends_on_assistant", "body_chars", "body_chars_log", "turn_words", "hypo", "plan", "suffic",
            "uncert", "uncert_z", "correct", "n_calls", "first_call_name", "call_changed", "repeat_call",
            "repeat_name_prev", "prior_error", "obs_new_share", "obs_new_z", "obs_error_next", "hypo_overlap",
            "hypo_overlap_z", "alien_overlap", "alien_overlap_z", "task_overlap", "has_early_hypo", "log_turns",
            "task_words_log", "repeat_share", "error_share", "final_obs_clean", "spec_sum", "spec_sum_z",
            "first_entities", "first_verbs", "first_ordering", "first_constraint", "first_entities_z",
            "first_verbs_z", "first_ordering_z", "first_constraint_z", "first_chars_log", "turn_quartile",
            "position_third", "early_hypo"]
    miss = [c for c in need if c not in F.columns]
    if miss:
        raise SystemExit(f"ABORT: the wave-8 frame lacks {miss}; the designs would drop those terms in silence")
    F["ritual"] = ((F["correct"] > 0) & (F["call_changed"] == 0.0)).astype(int)
    F["spoke_correction"] = (F["correct"] > 0).astype(int)
    F["after_error"] = F["prior_error"].astype(int)
    F["first_turn"] = (F["turn_index"] == 1).astype(int)
    F["later_turn"] = (F["turn_index"] > 2).astype(int)
    return F


def t171(F: pd.DataFrame) -> dict:
    """Primacy lock-in: does later language keep returning to the trajectory's own early hypothesis?"""
    d = F[(F["has_early_hypo"] == 1) & (F["later_turn"] == 1)].dropna(subset=["hypo_overlap"]).copy()
    h1 = term(glm(d, "hypo_overlap_z", ["position"] + CTRL, "gaussian"), "position")
    h1.update(hypothesis="H1", term="turn_position_on_overlap_with_the_trajectorys_own_early_hypothesis",
              trajectories_in_the_cell=int(d["traj_id"].nunique()), turns_in_the_cell=int(len(d)),
              early_hypothesis_trajectories_in_release=int(F["early_hypo"].sum()),
              mean_overlap=round(float(d["hypo_overlap"].mean()), 4))
    h1["verdict_direction"] = "predicted_positive: later turns keep returning to what the trajectory first guessed"
    n = F.dropna(subset=["obs_new_share"]).copy()
    h2 = term(glm(n, "obs_new_z", ["has_early_hypo", "position"] + CTRL, "gaussian"), "has_early_hypo")
    h2.update(hypothesis="H2", term="an_early_hypothesis_on_the_newness_of_what_comes_next",
              turns_with_an_observation=int(len(n)),
              mean_new_share_with=round(float(n.loc[n["has_early_hypo"] == 1, "obs_new_share"].mean()), 4),
              mean_new_share_without=round(float(n.loc[n["has_early_hypo"] == 0, "obs_new_share"].mean()), 4))
    h2["verdict_direction"] = "predicted_negative: an anchored search is told less that is new"
    both = n.dropna(subset=["alien_overlap"]).copy()
    own = term(glm(both, "obs_new_z", ["hypo_overlap_z", "alien_overlap_z", "position"] + CTRL, "gaussian"),
               "hypo_overlap_z")
    alien = term(glm(both, "obs_new_z", ["hypo_overlap_z", "alien_overlap_z", "position"] + CTRL, "gaussian"),
                 "alien_overlap_z")

    def separates(t, sign):
        return t.get("beta") is not None and t.get("ci_lo") is not None and (
            (t["ci_hi"] < 0 if sign < 0 else t["ci_lo"] > 0))
    h3 = dict(hypothesis="H3", term="own_anchor_versus_a_seed_chosen_alien_anchor",
              verdict_rule="specificity", own_anchor=own, alien_anchor=alien, rows=int(len(both)),
              trajectories=int(both["traj_id"].nunique()),
              note="the freeze asks whether the concentration is on the hypothesis rather than on early text in "
                   "general, so the two anchors are estimated in one specification and the alien one is the control")
    h3.update({k: v for k, v in own.items() if k != "cluster"})
    h3["verdict"] = ("supported" if separates(own, -1) and not separates(alien, -1) and
                     abs(own.get("beta") or 0) >= BAND_SMALL else
                     "not_specific_the_alien_anchor_tracks_the_same_variance" if own.get("beta") is not None else
                     "not_testable_no_coefficient_estimated")
    rows = holm_and_verdict([h1, h2, h3], {"H1": 1.0, "H2": -1.0, "H3": -1.0})
    prof = {}
    for lab, g in d.groupby("position_third", observed=True):
        prof[str(lab)] = {"mean_hypo_overlap": round(float(g["hypo_overlap"].mean()), 4),
                          "mean_alien_overlap": round(float(g["alien_overlap"].mean()), 4), "rows": int(len(g))}
    return dict(n_turns=int(len(F)), n_trajectories=int(F["traj_id"].nunique()),
                n_clusters=int(F["traj_id"].nunique()), cluster_unit=CLUSTER, models=rows,
                strata=strata_rows(d, ["turn_quartile", "category"], "hypo_overlap_z", ["position"] + CTRL,
                                   "position", family="gaussian", cluster=CLUSTER, min_rows=300),
                baselines=baselines(d, "hypo_overlap_z", [("controls_plus_position", ["position"] + CTRL,
                                                           "position"),
                                                          ("controls_plus_alien_anchor",
                                                           ["position", "alien_overlap_z"] + CTRL,
                                                           "alien_overlap_z")],
                                    family="gaussian", cluster=CLUSTER, controls=CTRL),
                descriptive_rates={"overlap_by_position_third": prof,
                                   "overlap_by_category": {
                                       str(k)[:34]: {"mean_hypo_overlap": round(float(g["hypo_overlap"].mean()), 4),
                                                     "rows": int(len(g))}
                                       for k, g in d.groupby("category", observed=True) if len(g) >= 100},
                                   "newness_by_early_hypothesis": {
                                       str(int(k)): {"mean_obs_new_share": round(float(g["obs_new_share"].mean()), 4),
                                                    "trajectories": int(g["traj_id"].nunique())}
                                       for k, g in n.groupby("has_early_hypo", observed=True)}},
                gate_scope=TD8.DESIGNS["T171"]["gate_scope"])


def t182(F: pd.DataFrame) -> dict:
    """Plan specificity: does an opening turn that names more entities, actions, order and constraints go with a
    search that repeats itself less and collects fewer errors?"""
    T = F.drop_duplicates("traj_id").copy()
    cs = ["spec_sum_z", "first_chars_log"] + CTRL
    h1 = term(glm(T, "repeat_share", cs, "gaussian"), "spec_sum_z")
    h1.update(hypothesis="H1", term="first_turn_plan_specificity_on_the_repeated_call_share",
              trajectories=int(len(T)), mean_repeat_share=round(float(T["repeat_share"].mean()), 4),
              median_spec_sum=float(T["spec_sum"].median()))
    h1["verdict_direction"] = "predicted_negative: a more specific opening plan repeats fewer calls"
    h2 = term(glm(T, "error_share", cs, "gaussian"), "spec_sum_z")
    h2.update(hypothesis="H2", term="first_turn_plan_specificity_on_the_error_marked_observation_share",
              mean_error_share=round(float(T["error_share"].mean()), 4),
              trajectories_with_any_error=int((T["error_share"] > 0).sum()))
    h2["verdict_direction"] = "predicted_negative: a more specific plan walks into fewer failed observations"
    parts = ["first_entities_z", "first_verbs_z", "first_ordering_z", "first_constraint_z"]
    joint = glm(T, "repeat_share", parts + ["first_chars_log"] + CTRL, "gaussian")
    sep = {p: term(joint, p) for p in parts}
    length = term(joint, "first_chars_log")
    clean = term(glm(T, "final_obs_clean", ["spec_sum_z"] + CTRL, "binomial"), "spec_sum_z")
    hits = [p for p, t in sep.items() if t.get("beta") is not None and t.get("ci_lo") is not None
            and (t["ci_lo"] > 0 or t["ci_hi"] < 0)]
    len_null = length.get("beta") is not None and length.get("ci_lo") is not None and \
        length["ci_lo"] <= 0 <= length["ci_hi"]
    h3 = dict(hypothesis="H3", term="the_specificity_parts_against_opening_turn_length",
              verdict_rule="specificity", parts=sep, length_term=length, separated_parts=hits,
              secondary_reading_on_a_clean_final_observation=clean,
              note="the freeze asks whether specificity is anything but verbosity, so the four counts and the "
                   "opening turn's character length compete in one specification")
    h3.update({k: v for k, v in (sep.get("first_entities_z") or {}).items() if k != "cluster"})
    h3["verdict"] = ("supported" if hits and len_null else
                     "not_specific_length_carries_the_same_signal" if sep else
                     "not_testable_no_coefficient_estimated")
    rows = holm_and_verdict([h1, h2, h3], {"H1": -1.0, "H2": -1.0, "H3": -1.0})
    q = {}
    for lab, g in T.assign(sq=pd.qcut(T["spec_sum"].rank(method="first"), 4,
                                      labels=["s1_least", "s2", "s3", "s4_most"]).astype(str)
                          ).groupby("sq", observed=True):
        q[str(lab)] = {"mean_repeat_share": round(float(g["repeat_share"].mean()), 4),
                       "mean_error_share": round(float(g["error_share"].mean()), 4),
                       "final_clean_share": round(float(g["final_obs_clean"].mean()), 4),
                       "trajectories": int(len(g))}
    return dict(n_turns=int(len(F)), n_trajectories=int(len(T)), n_clusters=int(T["traj_id"].nunique()),
                cluster_unit=CLUSTER, models=rows,
                strata=strata_rows(T, ["category", "turn_quartile"], "repeat_share", cs, "spec_sum_z",
                                   family="gaussian", cluster=CLUSTER, min_rows=300),
                baselines=baselines(T, "repeat_share", [("controls_plus_specificity_composite", cs, "spec_sum_z"),
                                                        ("controls_plus_length_only",
                                                         ["first_chars_log"] + CTRL, "first_chars_log")],
                                    family="gaussian", cluster=CLUSTER, controls=CTRL),
                descriptive_rates={"outcomes_by_specificity_quartile": q,
                                   "specificity_parts": {p: {"mean": round(float(T[c].mean()), 3),
                                                             "median": float(T[c].median())}
                                                         for p, c in [("entities", "first_entities"),
                                                                     ("action_verbs", "first_verbs"),
                                                                     ("ordering", "first_ordering"),
                                                                     ("constraints", "first_constraint")]},
                                   "error_share_by_category": {
                                       str(k)[:34]: {"mean_error_share": round(float(g["error_share"].mean()), 4),
                                                     "mean_repeat_share": round(float(g["repeat_share"].mean()), 4),
                                                     "trajectories": int(len(g))}
                                       for k, g in T.groupby("category", observed=True) if len(g) >= 100}},
                gate_scope=TD8.DESIGNS["T182"]["gate_scope"])


def t190(F: pd.DataFrame) -> dict:
    """Verbal versus behavioural correction: does saying it was wrong change what the agent next does?"""
    d = F[(F["n_calls"] > 0)].dropna(subset=["call_changed"]).copy()
    after = d[d["after_error"] == 1]
    h1 = term(glm(after, "call_changed", ["spoke_correction", "position"] + CTRL, "binomial"), "spoke_correction")
    h1.update(hypothesis="H1", term="a_verbal_correction_after_an_error_marked_observation_on_changing_the_call",
              turns_after_an_error=int(len(after)), turns_with_a_correction=int(after["spoke_correction"].sum()),
              changed_rate_with=round(float(after.loc[after["spoke_correction"] == 1, "call_changed"].mean()), 4),
              changed_rate_without=round(float(after.loc[after["spoke_correction"] == 0, "call_changed"].mean()), 4))
    h1["verdict_direction"] = "predicted_positive: an admission is followed by different behaviour"
    cor = d[d["spoke_correction"] == 1]
    rate = float(cor["ritual"].mean()) if len(cor) else float("nan")
    b = boot(cor, CLUSTER, lambda x: float(x["ritual"].mean()))
    floor = 0.20
    h2 = dict(hypothesis="H2", term="the_share_of_verbal_corrections_with_no_behavioural_change",
              ritual_rate=round(rate, 4), ci_lo=(b.get("ci") or [None, None])[0],
              ci_hi=(b.get("ci") or [None, None])[1], p=b.get("p"), clusters=b.get("clusters"),
              corrections=int(len(cor)), trajectories=int(cor["traj_id"].nunique()), frozen_floor=floor,
              beta=round(rate, 4), n=int(len(cor)),
              note="the frozen sentence puts the floor on the measured rate rather than on a coefficient, so the "
                   "bootstrap interval is read against 0.20 directly and no band is invented")
    h2["verdict"] = ("supported" if rate == rate and rate >= floor and (b.get("ci") or [0, 0])[0] >= floor else
                     f"not_at_or_above_the_frozen_floor_measured_{f'{rate:.4f}'.replace('.', 'p')}"
                     if rate == rate else "not_testable_no_corrections_on_these_rows")
    k = d[["spoke_correction", "after_error", CLUSTER]].dropna()
    kb = W.cluster_boot_ci_and_p(k, CLUSTER, lambda x: EF5.kappa(x["spoke_correction"], x["after_error"]),
                                 draws=200, seed=TD8.SEED) if len(k) else {}
    kap = EF5.kappa(k["spoke_correction"], k["after_error"]) if len(k) else float("nan")
    h3 = dict(hypothesis="H3", term="agreement_between_an_admission_and_a_preceding_error_marker",
              verdict_rule="specificity", kappa=round(float(kap), 4) if kap == kap else None,
              agreement=round(float((k["spoke_correction"] == k["after_error"]).mean()), 4) if len(k) else None,
              corrected_without_error=int(((k["spoke_correction"] == 1) & (k["after_error"] == 0)).sum())
              if len(k) else 0,
              error_without_correction=int(((k["spoke_correction"] == 0) & (k["after_error"] == 1)).sum())
              if len(k) else 0,
              ci=(kb.get("ci") if "ci" in kb else None), clusters=kb.get("clusters"), turns=int(len(k)),
              p=kb.get("p"), beta=round(float(kap), 4) if kap == kap else None, n=int(len(k)),
              note="H3 claims the two instruments are separable; kappa < 0.50 on these rows is what the freeze "
                   "fixed as the reading of that claim, and the two off-diagonal counts say in which direction "
                   "they come apart")
    h3["verdict"] = ("supported" if kap == kap and kap < 0.50 else
                     "not_separable_the_two_instruments_agree_too_much" if kap == kap else
                     "not_testable_no_rows_for_an_agreement_statistic")
    rows = holm_and_verdict([h1, h2, h3], {"H1": 1.0, "H2": 1.0})
    return dict(n_turns=int(len(F)), n_trajectories=int(F["traj_id"].nunique()),
                n_clusters=int(d["traj_id"].nunique()), cluster_unit=CLUSTER, models=rows,
                strata=strata_rows(after, ["category", "position_third"], "call_changed",
                                   ["spoke_correction", "position"] + CTRL, "spoke_correction",
                                   cluster=CLUSTER, min_rows=1500),
                baselines=baselines(after, "call_changed",
                                    [("controls_plus_position", ["position"] + CTRL, "position"),
                                     ("controls_plus_admission", ["spoke_correction", "position"] + CTRL,
                                      "spoke_correction")], cluster=CLUSTER, controls=CTRL),
                descriptive_rates={"correction_by_position_third": {
                    str(lab): {"correction_share": round(float(g["spoke_correction"].mean()), 4),
                               "changed_rate_after_correction":
                                   round(float(g.loc[g["spoke_correction"] == 1, "call_changed"].mean()), 4),
                               "rows": int(len(g))}
                    for lab, g in d.groupby("position_third", observed=True)},
                    "admissions_without_an_error_before": int(((d["spoke_correction"] == 1) &
                                                               (d["after_error"] == 0)).sum()),
                    "repeat_call_share_by_correction": {
                        str(int(k2)): {"repeat_share": round(float(g["repeat_call"].mean()), 4),
                                       "rows": int(len(g))}
                        for k2, g in d.groupby("spoke_correction", observed=True)}},
                gate_scope=TD8.DESIGNS["T190"]["gate_scope"])


DESIGN_FN = {"EXP-0192": ("T171", t171), "EXP-0193": ("T182", t182), "EXP-0194": ("T190", t190)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--only", action="append", default=[])
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    F = load()
    if a.quick:
        keep = F[CLUSTER].drop_duplicates().sample(900, random_state=TD8.SEED)
        F = F[F[CLUSTER].isin(set(keep))]
    todo = {k: v for k, v in DESIGN_FN.items() if not a.only or k in a.only}
    bad = [k for k in (a.only or []) if k not in DESIGN_FN]
    if bad:
        raise SystemExit(f"ABORT: --only names no design: {bad}; valid ids are {sorted(DESIGN_FN)}")
    for exp, (topic, fn) in todo.items():
        art = fn(F)
        lack = [k for k in ("models", "strata", "descriptive_rates", "baselines") if not art.get(k)]
        if lack:
            raise SystemExit(f"ABORT {exp} ({topic}): the design produced no {lack}, so the package tables that read "
                             f"those blocks would ship a header with no numbers - measure it or drop the table")
        nofv = [m.get("hypothesis") or m.get("term") for m in art["models"] if not m.get("verdict")]
        if nofv:
            raise SystemExit(f"ABORT {exp} ({topic}): hypotheses {nofv} carry no verdict, and a pre-registered test "
                             f"that was not decided is not a deliverable")
        art.update(exp_id=exp, topic=topic, seed=TD8.SEED, quick=a.quick, started_at=W.now(),
                   frame_file_read=F.attrs.get("frame_file"), blocked_designs_in_this_wave=["T175", "T176"],
                   invocation=" ".join([sys.executable] + sys.argv),
                   run_cost=W.run_cost_row(exp, t0, int(len(F)), int(F.shape[1]), "wave-8 design"),
                   finished_at=W.now())
        print(f"{exp} ({topic}): wrote {W.write_raw(exp, f'wave8_design_{exp[-4:]}', art).name}", flush=True)
        pd.DataFrame(art.get("models") or []).to_csv(W.OUT / f"EXP{exp[-4:]}_{topic.lower()}_models.csv",
                                                     index=False, encoding="utf-8")
        if art.get("strata"):
            pd.DataFrame(art["strata"]).to_csv(W.OUT / f"EXP{exp[-4:]}_{topic.lower()}_strata.csv", index=False,
                                               encoding="utf-8")
        print("  " + json.dumps({m.get("hypothesis"): m.get("verdict") for m in art["models"]},
                                default=str)[:260], flush=True)
    print(f"wallclock {round(time.time() - t0, 1)}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
