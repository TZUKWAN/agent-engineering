"""EXP-0209..EXP-0213: wave 11's five pre-registered tests, from the frozen sentences in topic_designs_wave11.

Nothing here decides a threshold. Each hypothesis carries the floor, direction and comparison its freeze names; Holm
is applied to the three hypotheses of one design and to nothing else; every interval is cluster-robust or bootstrapped
on `instance_id`, because a rollout is an attempt at a task and attempts of the same task are not independent.

Two operational facts are stated where they are used rather than hidden. The release interleaves one observation with
each assistant command turn - checked on 300 rollouts of the first shard, where user and assistant counts were equal
or differed by one in every case - so the assistant-turn count *is* the observation count a control needs. And the
release's completion label is rare (560 Submitted of 20,000, EXP-0207), so every success-flavoured estimate prints its
positive count beside itself.

    python 02_shared_code/package_factory/exp_wave11_designs.py [--quick] [--only EXP-0209]
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
import topic_designs_wave11 as TD11                               # noqa: E402
import exp_wave9_designs as D9                                    # noqa: E402  the estimator chain
import probe_wave11_premises as P11                                    # noqa: E402  the estimator chain

assert TD11.BANDS == W.BANDS, "the wave-11 freeze and wave_lib disagree about the effect bands"
BAND = W.BANDS["medium"]
BAND_SMALL = W.BANDS["small"]
CLUSTER = TD11.COMMON["sample"]["cluster_unit"]                   # "instance_id"
FRAMES = {"rollout": "EXP0208_wave11_rollout_features.csv.gz", "pairs": "EXP0208_wave11_attempt_pairs.csv.gz"}
CTRL = ["n_turns", "prose_chars_log"]                             # length and prose volume, one definition
CATS = list(P11.COMPONENT)                              # the eight categories, from the census instruments
term, holm_and_verdict, z = D9.term, D9.holm_and_verdict, D9.z


def glm(d, y, xs, family="binomial", cluster=CLUSTER):
    return D9.glm(d, y, xs, family, cluster)


def baselines(d, y, specs, family="binomial", controls=None, cluster=CLUSTER):
    return D9.baselines(d, y, specs, family, controls or CTRL, cluster)


def strata_rows(d, splits, y, xs, focus, min_rows=1000, family="binomial", cluster=CLUSTER):
    return D9.strata_rows(d, splits, y, xs, focus, min_rows, family, cluster)


def boot(d, cluster, fn, draws: int = 600) -> dict:
    return W.cluster_boot_ci_and_p(d, cluster, fn, draws=draws, seed=TD11.SEED)


def _read(kind: str) -> pd.DataFrame:
    name = FRAMES[kind]
    search = []
    if os.environ.get("AIB_INPUT_DIR"):
        search.append(pathlib.Path(os.environ["AIB_INPUT_DIR"]) / name)
    search += [W.OUT / name, W.ROOT / "results_processed" / name]
    path = next((q for q in search if pathlib.Path(q).is_file()), None)
    if path is None:
        raise SystemExit(f"ABORT: {name} is not where the designs look ({', '.join(map(str, search))}) - run "
                         f"{TD11.FEATURE_EXP} (exp_wave11_features.py) first")
    F = pd.read_csv(gzip.open(path, "rt", encoding="utf-8"))
    F.attrs["frame_file"] = str(path)
    return F


def load() -> dict:
    R, P = _read("rollout"), _read("pairs")
    need_r = ["rollout_key", "instance_id", "repo_prefix", "submitted", "n_turns", "prose_chars", "attempt_index",
              "n_attempts", "concreteness", "concrete_n", "abstract_n", "uncert_n", "negcon_n", "turn_words"]
    need_p = ["pair_key", "instance_id", "repo_prefix", "jaccard", "relation_class", "alien_jaccard",
              "alien_relation_class", "earlier_submitted", "later_submitted", "earlier_turns", "later_turns",
              "negcon_diff", "contradiction", "concreteness_earlier", "concreteness_later",
              "alien_concreteness_earlier"]
    CAT = list(CATS)
    miss = [f"rollout:{c}" for c in need_r if c not in R.columns] \
        + [f"rollout:comp_{c}" for c in CAT if f"comp_{c}" not in R.columns] \
        + [f"rollout:surv25_{c}" for c in CAT if f"surv25_{c}" not in R.columns] \
        + [f"pairs:{c}" for c in need_p if c not in P.columns] \
        + [f"pairs:earlier_{c}" for c in CAT if f"earlier_{c}" not in P.columns]
    if miss:
        raise SystemExit(f"ABORT: the wave-11 frames lack {miss[:8]} of {len(miss)}; the designs would drop those "
                         f"terms in silence")
    R["prose_chars_log"] = np.log1p(R["prose_chars"].astype(float))
    R["balance"] = R["comp_result"] - R["comp_exception"]
    R["length_quartile"] = pd.qcut(R["n_turns"].rank(method="first"), 4,
                                   labels=["q1_shortest", "q2", "q3", "q4_longest"]).astype(str)
    P["later_turns_log"] = np.log1p(P["later_turns"].astype(float))
    P["earlier_turns_log"] = np.log1p(P["earlier_turns"].astype(float))
    P["concreteness_earlier_z"] = z(P["concreteness_earlier"].astype(float))
    P["concreteness_later_z"] = z(P["concreteness_later"].astype(float))
    P["alien_concreteness_earlier_z"] = z(P["alien_concreteness_earlier"].astype(float))
    P["jaccard_z"] = z(P["jaccard"].astype(float))
    P["overlap_band"] = pd.cut(P["jaccard"].astype(float), [-0.001, 0.1, 0.3, 1.001],
                               labels=["overlap_low", "overlap_mid", "overlap_high"]).astype(str)
    for lab in ("refinement", "new", "restatement"):
        P[f"is_{lab}"] = (P["relation_class"] == lab).astype(int)
    return {"R": R, "P": P, "CAT": CAT}


def t131(fr: dict) -> dict:
    """Does a rollout that ends by submitting carry a different discourse than one that runs out?"""
    R = fr["R"]
    h1 = term(glm(R, "submitted", ["balance"] + CTRL, "binomial"), "balance")
    exc = term(glm(R, "submitted", ["comp_result", "comp_exception"] + CTRL, "binomial"), "comp_exception")
    h1.update(hypothesis="H1", term="result_minus_exception_balance_on_submitting",
              submitted_rollouts=int(R["submitted"].sum()), balance_positive_share=round(float(R["balance"].mean()), 4),
              result_term=term(glm(R, "submitted", ["comp_result", "comp_exception"] + CTRL, "binomial"),
                               "comp_result"), exception_term=exc)
    h1["verdict_direction"] = "predicted_positive: a submitted rollout states a result more and an exception less"
    sub = R.dropna(subset=["first_pos_procedure"])
    h2 = term(glm(sub, "first_pos_procedure", ["submitted"] + CTRL, "gaussian"), "submitted")
    h2.update(hypothesis="H2", term="submitting_on_the_position_of_the_first_procedure_statement",
              rollouts_with_procedure=int(len(sub)),
              mean_position_when_submitted=round(float(sub.loc[sub["submitted"] == 1, "first_pos_procedure"].mean()), 4),
              mean_position_when_not=round(float(sub.loc[sub["submitted"] == 0, "first_pos_procedure"].mean()), 4),
              observation_arm=term(glm(R.dropna(subset=["first_pos_observation"]), "first_pos_observation",
                                       ["submitted"] + CTRL, "gaussian"), "submitted"))
    h2["verdict_direction"] = "predicted_negative: a submitted rollout gets to its procedure earlier in itself"
    with_balance = glm(R, "submitted", ["balance"] + CTRL, "binomial")
    obs_only = glm(R, "submitted", ["n_turns"], "binomial")
    b_arm = term(with_balance, "balance")
    o_arm = term(obs_only, "n_turns")
    h3 = dict(hypothesis="H3", term="the_balance_against_an_observation_count_only_model",
              verdict_rule="specificity", balance_in_full_model=b_arm, observation_count_only=o_arm,
              deviance_with_balance=round(float(with_balance["deviance"].iloc[0]), 2) if with_balance is not None and
              not with_balance.empty else None,
              note="H3 is the step-count check: the balance must separate with the observation count - the assistant "
                   "turn count, which the release interleaves one for one with observations - and prose volume in the "
                   "model, while a model carrying the observation count alone must not separate on its own")
    h3.update({k: v for k, v in b_arm.items() if k != "cluster"})
    sep = b_arm.get("beta") is not None and b_arm.get("ci_lo") is not None and (
        b_arm["ci_lo"] > 0 or b_arm["ci_hi"] < 0)
    count_null = o_arm.get("beta") is not None and o_arm.get("ci_lo") is not None and \
        o_arm["ci_lo"] <= 0 <= o_arm["ci_hi"]
    h3["verdict"] = ("supported" if sep and count_null else
                     "not_specific_the_observation_count_alone_separates" if sep else
                     "null" if b_arm.get("beta") is not None else "not_testable_no_coefficient_estimated")
    rows = holm_and_verdict([h1, h2, h3], {"H1": 1.0, "H2": -1.0})
    return dict(n_rollouts=int(len(R)), n_clusters=int(R["instance_id"].nunique()), cluster_unit=CLUSTER,
                models=rows,
                strata=strata_rows(R, ["repo_prefix", "length_quartile"], "submitted", ["balance"] + CTRL,
                                   "balance", min_rows=500),
                baselines=baselines(R, "submitted", [("controls_only", CTRL, "n_turns"),
                                                     ("controls_plus_balance", ["balance"] + CTRL, "balance"),
                                                     ("controls_plus_both_categories",
                                                      ["comp_result", "comp_exception"] + CTRL, "comp_result")]),
                descriptive_rates={"category_presence_by_outcome": {
                    str(int(k)): {c: round(float(g[f"comp_{c}"].mean()), 4) for c in fr["CAT"]}
                    for k, g in R.groupby("submitted", observed=True)},
                    "balance_distribution": {"mean": round(float(R["balance"].mean()), 4),
                                             "p10_p50_p90": [round(float(x), 4) for x in
                                                             np.percentile(R["balance"], [10, 50, 90])]},
                    "turns_and_prose_by_outcome": {
                        str(int(k)): {"mean_turns": round(float(g["n_turns"].mean()), 2),
                                      "mean_prose_chars": round(float(g["prose_chars"].mean()), 0),
                                      "rollouts": int(len(g))}
                        for k, g in R.groupby("submitted", observed=True)}},
                gate_scope=TD11.DESIGNS["T131"]["gate_scope"])
def _lift_table(P: pd.DataFrame, cats: list) -> dict:
    """Within-pair carry-forward lift per category, with a cluster bootstrap on the instance."""
    out = {}
    for c in cats:
        e, l = f"earlier_{c}", f"later_{c}"
        d = P.dropna(subset=[e, l])
        sub = d[[e, l, "instance_id"]]
        if sub[e].nunique() < 2:
            out[c] = {"lift": None, "note": "the category is constant in this corpus"}
            continue

        def fn(x, e=e, l=l):
            a, b = x[x[e] == 1], x[x[e] == 0]
            if not len(a) or not len(b):
                return None
            return float(a[l].mean() - b[l].mean())

        base = fn(sub)
        b = boot(sub, "instance_id", fn, 400)
        out[c] = {"lift": round(base, 4) if base == base else None,
                  "ci_lo": (b.get("ci") or [None, None])[0], "ci_hi": (b.get("ci") or [None, None])[1],
                  "ci_kind": b.get("ci_kind"), "p_kind": b.get("p_kind"), "draws_used": b.get("draws_used"),
                  "p": b.get("p"), "pairs_with_earlier_present": int((sub[e] == 1).sum()),
                  "pairs_with_earlier_absent": int((sub[e] == 0).sum()),
                  "later_rate_when_present": round(float(d.loc[d[e] == 1, l].mean()), 4),
                  "later_rate_when_absent": round(float(d.loc[d[e] == 0, l].mean()), 4)}
    return out


def t137(fr: dict) -> dict:
    """Which kinds of thing an attempt said make the next attempt of the same task say them too?"""
    P, CAT = fr["P"], fr["CAT"]
    lifts = _lift_table(P, CAT)
    usable = {k: v for k, v in lifts.items() if v.get("lift") is not None}
    top = max(usable, key=lambda k: usable[k]["lift"]) if usable else None
    low = min(usable, key=lambda k: usable[k]["lift"]) if usable else None
    h1 = dict(hypothesis="H1", term="carry_forward_lift_per_component_category",
              category_lifts=lifts, strongest_category=top, weakest_category=low,
              usable_categories=len(usable), attempt_pairs=int(len(P)), pairs_with_both_categories_present=None,
              n=int(len(P)))
    if top:
        h1.update(term_name=top, beta=usable[top]["lift"], ci_lo=usable[top]["ci_lo"], ci_hi=usable[top]["ci_hi"],
                  p=usable[top]["p"], ci_kind=usable[top].get("ci_kind"), p_kind=usable[top].get("p_kind"),
                  draws_used=usable[top].get("draws_used"), clusters=int(P["instance_id"].nunique()))
    h1["verdict_direction"] = "predicted_positive: a category said earlier is said again next time"
    h1["verdict"] = ("supported" if top and usable[top]["lift"] >= BAND_SMALL and (usable[top]["ci_lo"] or -1) > 0
                     else "not_at_or_above_the_frozen_lift" if top else "not_testable_no_category_estimable")
    spread = round(usable[top]["lift"] - usable[low]["lift"], 4) if usable else None
    h2 = dict(hypothesis="H2", term="the_spread_of_carry_forward_across_categories",
              verdict_rule="descriptive", spread=spread, strongest=top, weakest=low,
              beta=spread, n=int(len(P)),
              note="H2 claims the categories differ among themselves, so the reported quantity is the spread between "
                   "the strongest and weakest lift, with each category's interval above")
    # the spread has no interval of its own here: the two extreme categories' intervals are what the verdict reads,
    # and they are printed per category rather than merged into a range that would look like one interval
    h2["ci_lo"] = h2["ci_hi"] = h2["p"] = None
    h2["extreme_intervals"] = {"strongest": {k: usable[top][k] for k in ("ci_lo", "ci_hi", "p")},
                               "weakest": {k: usable[low][k] for k in ("ci_lo", "ci_hi", "p")} if low else None}
    h2["verdict"] = ("supported" if usable and spread is not None and spread >= BAND_SMALL
                     and (usable[top]["ci_lo"] or -1) > 0 and (usable[low]["ci_hi"] or 1) < 0 else
                     "not_uniform_enough_to_claim" if usable else "not_testable_no_category_estimable")
    xs = [f"earlier_{top}", f"alien_earlier_{top}", "jaccard_z", "earlier_turns_log", "later_turns_log"]
    dj = P.dropna(subset=[x for x in xs if x in P.columns])
    own = term(glm(dj, f"later_{top}", xs, "gaussian"), f"earlier_{top}") if top else {}
    alien = term(glm(dj, f"later_{top}", xs, "gaussian"), f"alien_earlier_{top}") if top else {}

    def ex(t):
        return t.get("beta") is not None and t.get("ci_lo") is not None and (t["ci_lo"] > 0 or t["ci_hi"] < 0)

    h3 = dict(hypothesis="H3", term="own_earlier_category_against_an_alien_one_and_the_text_overlap",
              verdict_rule="specificity", own_arm=own, alien_arm=alien, overlap_arm=term(
                  glm(dj, f"later_{top}", xs, "gaussian"), "jaccard_z"), rows=int(len(dj)),
              note="H3 is supported when the instance's own earlier category separates with the overlap band and the "
                   "alien category in the model, and the alien arm does not")
    h3.update({k: v for k, v in own.items() if k != "cluster"})
    h3["verdict"] = ("supported" if ex(own) and not ex(alien) and abs(own.get("beta") or 0) >= BAND_SMALL else
                     "not_specific_the_alien_category_carries_it_too" if own.get("beta") is not None else
                     "not_testable_no_coefficient_estimated")
    rows = holm_and_verdict([h1, h2, h3], {"H1": 1.0, "H2": 1.0, "H3": 1.0})
    return dict(n_rollouts=int(fr["R"].shape[0]), n_pairs=int(len(P)),
                n_clusters=int(P["instance_id"].nunique()), cluster_unit=CLUSTER, models=rows,
                strata=[{"stratification": "component category", "stratum": str(k),
                         "lift": (usable.get(k) or {}).get("lift"), "ci_lo": (usable.get(k) or {}).get("ci_lo"),
                         "ci_hi": (usable.get(k) or {}).get("ci_hi"),
                         "pairs": int(len(P))} for k in CAT],
                baselines=[{"model": "controls_only", "dv": f"later_{top}", "n": int(len(dj))},
                           {"model": "plus_alien_category", "dv": f"later_{top}",
                            "term": "alien_earlier_" + str(top), **{k: v for k, v in alien.items() if k != "cluster"}},
                           {"model": "plus_own_category", "dv": f"later_{top}", "term": "earlier_" + str(top),
                            **{k: v for k, v in own.items() if k != "cluster"}}],
                descriptive_rates={"carry_forward_lift_by_category": lifts,
                                   "relation_class_prevalence": {
                                       str(k): round(float(v / max(1, len(P))), 4) for k, v in
                                       P["relation_class"].value_counts().items()},
                                   "pairs_per_instance": {"mean": round(float(P.groupby("instance_id").size().mean()),
                                                                        3) if len(P) else None,
                                                          "instances": int(P["instance_id"].nunique())}},
                gate_scope=TD11.DESIGNS["T137"]["gate_scope"])


def t138(fr: dict) -> dict:
    """Does the level of abstraction one attempt is written at carry to the next, and does it predict finishing?"""
    P = fr["P"]
    xs = ["concreteness_earlier_z", "jaccard_z", "earlier_turns_log", "later_turns_log"]
    d = P.dropna(subset=[c for c in ["concreteness_earlier_z", "concreteness_later_z"] + xs if c in P.columns])
    h1 = term(glm(d, "concreteness_later_z", xs, "gaussian"), "concreteness_earlier_z")
    h1.update(hypothesis="H1", term="the_earlier_attempt_s_concreteness_on_the_later_attempt_s",
              pairs=int(len(d)), mean_earlier=round(float(d["concreteness_earlier"].mean()), 2),
              mean_later=round(float(d["concreteness_later"].mean()), 2),
              pearson_r=round(float(np.corrcoef(d["concreteness_earlier"].astype(float),
                                                d["concreteness_later"].astype(float))[0, 1]), 4))
    h1["verdict_direction"] = "predicted_positive: consecutive attempts of one task are written at a similar level"
    ds = d.dropna(subset=["later_submitted"])
    h2 = term(glm(ds, "later_submitted", ["concreteness_earlier_z"] + ["jaccard_z", "earlier_turns_log",
                                                                       "later_turns_log"], "binomial"),
              "concreteness_earlier_z")
    h2.update(hypothesis="H2", term="the_earlier_attempt_s_concreteness_on_the_later_attempt_finishing",
              pairs=int(len(ds)), later_submitted=int(ds["later_submitted"].sum()),
              submitted_rate_above_median=round(float(ds.loc[ds["concreteness_earlier"] >= ds["concreteness_earlier"]
                                                            .median(), "later_submitted"].mean()), 4),
              submitted_rate_below_median=round(float(ds.loc[ds["concreteness_earlier"] < ds["concreteness_earlier"]
                                                            .median(), "later_submitted"].mean()), 4))
    h2["verdict_direction"] = "predicted_positive: a concrete earlier attempt precedes a finishing later one"
    da = P.dropna(subset=["alien_concreteness_earlier_z", "concreteness_later_z"]).copy()
    alien = term(glm(da, "concreteness_later_z", ["alien_concreteness_earlier_z", "jaccard_z", "earlier_turns_log",
                                                  "later_turns_log"], "gaussian"), "alien_concreteness_earlier_z") \
        if len(da) else {}
    own = term(glm(da, "concreteness_later_z", ["concreteness_earlier_z", "alien_concreteness_earlier_z"]
                   + ["jaccard_z", "earlier_turns_log", "later_turns_log"], "gaussian"), "concreteness_earlier_z") \
        if len(da) else {}

    def ex(t):
        return t.get("beta") is not None and t.get("ci_lo") is not None and (t["ci_lo"] > 0 or t["ci_hi"] < 0)

    def nullish(t):
        return t.get("beta") is not None and t.get("ci_lo") is not None and t["ci_lo"] <= 0 <= t["ci_hi"]
    h3 = dict(hypothesis="H3", term="own_earlier_level_against_a_seeded_other_instance_s_level",
              verdict_rule="specificity", own_arm=own, alien_arm=alien, rows=int(len(da)),
              note="H3 claims the transmission is not generic similarity: the instance's own earlier level must "
                   "separate with the alien level and the overlap band in the model, and the alien level must not")
    h3.update({k: v for k, v in own.items() if k != "cluster"})
    h3["verdict"] = ("supported" if ex(own) and nullish(alien) else
                     "not_specific_the_alien_level_carries_it_too" if own.get("beta") is not None else
                     "not_testable_no_coefficient_estimated")
    rows = holm_and_verdict([h1, h2, h3], {"H1": 1.0, "H2": 1.0})
    return dict(n_rollouts=int(fr["R"].shape[0]), n_pairs=int(len(P)),
                n_clusters=int(P["instance_id"].nunique()), cluster_unit=CLUSTER, models=rows,
                strata=strata_rows(d, ["overlap_band", "repo_prefix"], "concreteness_later_z", xs,
                                   "concreteness_earlier_z", family="gaussian", min_rows=250),
                baselines=baselines(d, "concreteness_later_z",
                                    [("controls_only", ["jaccard_z", "earlier_turns_log", "later_turns_log"],
                                      "jaccard_z"),
                                     ("plus_alien_level", ["alien_concreteness_earlier_z", "jaccard_z",
                                                          "earlier_turns_log", "later_turns_log"],
                                      "alien_concreteness_earlier_z"),
                                     ("plus_own_level", xs, "concreteness_earlier_z")],
                                    family="gaussian",
                                    controls=["jaccard_z", "earlier_turns_log", "later_turns_log"]),
                descriptive_rates={"concreteness_distribution": {
                    "earlier_p10_p50_p90": [round(float(x), 2) for x in
                                            np.percentile(P["concreteness_earlier"], [10, 50, 90])],
                    "later_p10_p50_p90": [round(float(x), 2) for x in
                                          np.percentile(P["concreteness_later"], [10, 50, 90])]},
                    "marker_means": {"concrete": round(float(fr["R"]["concrete_n"].mean()), 3),
                                     "abstract": round(float(fr["R"]["abstract_n"].mean()), 3)},
                    "pairs_by_relation_class": {str(k): int(v) for k, v in
                                                P["relation_class"].value_counts().items()}},
                gate_scope=TD11.DESIGNS["T138"]["gate_scope"])
def t140(fr: dict) -> dict:
    """Which kinds of what a search said survive keeping only its opening fraction?"""
    R, CAT = fr["R"], fr["CAT"]
    cats = CAT + ["uncert", "negcon"]
    surv = {}
    for c in cats:
        col = f"surv25_{c}"
        if col not in R.columns:
            continue
        d = R[["instance_id", col]].dropna()
        b = boot(d, "instance_id", lambda x, k=col: float(x[k].mean()), 400)
        whole = float(R[f"comp_{c}"].mean()) if f"comp_{c}" in R.columns else float((R["uncert_n"] > 0).mean()) \
            if c == "uncert" else float((R["negcon_n"] > 0).mean())
        surv[c] = {"presence": round(whole, 4), "survival_at_25pct": round(float(d[col].mean()), 4),
                   "ci_lo": (b.get("ci") or [None, None])[0], "ci_hi": (b.get("ci") or [None, None])[1],
                   "survival_at_10pct": round(float(R[f"surv10_{c}"].mean()), 4) if f"surv10_{c}" in R.columns
                   else None,
                   "survival_at_50pct": round(float(R[f"surv50_{c}"].mean()), 4) if f"surv50_{c}" in R.columns
                   else None,
                   "rollouts": int(len(d))}
    ranked = sorted(surv, key=lambda k: surv[k]["survival_at_25pct"])
    named = [c for c in ("exception", "condition", "provenance", "uncert") if c in surv]
    h1 = dict(hypothesis="H1", term="survival_of_each_component_category_under_a_25pct_budget",
              survival=surv, ranking_bottom_to_top=ranked, named_lowest=named,
              bottom_four_are_named=bool(named) and ranked[:len(named)] == named,
              spread=round(surv[ranked[-1]]["survival_at_25pct"] - surv[ranked[0]]["survival_at_25pct"], 4)
              if surv else None,
              n=int(len(R)), clusters=int(R["instance_id"].nunique()))
    if named and ranked[:len(named)] == named:
        h1["beta"] = surv[named[0]]["survival_at_25pct"]
        h1["ci_lo"], h1["ci_hi"] = surv[named[0]]["ci_lo"], surv[named[0]]["ci_hi"]
    h1["verdict_direction"] = "predicted_lowest: exceptions, conditions, provenance and uncertainty go first"
    h1["verdict"] = ("supported" if h1.get("bottom_four_are_named") and h1.get("spread") is not None
                     and h1["spread"] >= BAND_SMALL else
                     "not_the_predicted_ordering" if surv else "not_testable_no_survival_estimable")
    late = R[R.get("first_pos_exception", pd.Series(dtype=float)).notna()].copy() if len(R) else R
    arms = {}
    for c in named:
        pos, sv = f"first_pos_{c}", f"surv25_{c}"
        if pos not in R.columns or sv not in R.columns:
            continue
        d = R[[pos, sv, "instance_id", "n_turns"]].dropna()
        if len(d) < 200 or d[pos].nunique() < 2:
            arms[c] = {"note": "the category is mentioned in too few rollouts, or always at the same position"}
            continue
        t = term(glm(d, sv, [pos, "n_turns"], "gaussian"), pos)
        late_half = d[d[pos] >= 0.5]
        early_half = d[d[pos] < 0.5]
        arms[c] = {"position_coefficient": t,
                   "survival_when_late_mention": round(float(late_half[sv].mean()), 4) if len(late_half) else None,
                   "survival_when_early_mention": round(float(early_half[sv].mean()), 4) if len(early_half) else None,
                   "rollouts": int(len(d))}
    kept = [a for a in arms.values() if isinstance(a.get("survival_when_late_mention"), float)]
    h2 = dict(hypothesis="H2", term="survival_within_a_stratum_of_first_mention_position",
              verdict_rule="descriptive", per_category=arms,
              note="H2 asks whether the ordering is only an artefact of where a category tends to appear, so each "
                   "category's survival is recomputed among rollouts that mention it late, position held in the "
                   "model; the claim is about the ordering surviving, not about a coefficient")
    h2["beta"] = round(float(np.mean([a["survival_when_late_mention"] - a["survival_when_early_mention"]
                                      for a in kept])), 4) if kept else None
    h2["n"] = int(sum(a["rollouts"] for a in kept)) if kept else 0
    h2["verdict"] = ("supported" if kept and all((a["survival_when_late_mention"] or 0)
                                                 <= (a["survival_when_early_mention"] or 1) + 0.05 for a in kept)
                     else "not_explained_by_position_for_every_category" if kept else
                     "not_testable_too_few_rollouts_mention_the_categories_late")
    P = fr["P"].merge(R[["rollout_key", "removal_exception", "removal_uncert"] if "removal_uncert" in R.columns
                        else ["rollout_key", "removal_exception"]],
                      left_on="earlier", right_on="rollout_key", how="left")
    P["removed_exception"] = P["removal_exception"].fillna(0).astype(int)
    rem = P.dropna(subset=["later_submitted"])
    h3 = term(glm(rem, "later_submitted", ["removed_exception"] + ["jaccard_z", "earlier_turns_log",
                                                                   "later_turns_log", "earlier_submitted"],
                  "binomial"), "removed_exception")
    h3.update(hypothesis="H3", term="a_compression_that_removes_the_exception_category_on_the_next_attempt_finishing",
              pairs=int(len(rem)), pairs_with_removal=int(rem["removed_exception"].sum()),
              submitted_rate_with_removal=round(float(rem.loc[rem["removed_exception"] == 1, "later_submitted"]
                                                      .mean()), 4),
              submitted_rate_without=round(float(rem.loc[rem["removed_exception"] == 0, "later_submitted"].mean()), 4),
              clusters=int(rem["instance_id"].nunique()))
    h3["verdict_direction"] = "predicted_negative: losing the exception is followed by a later attempt that fails"
    rows = holm_and_verdict([h1, h2, h3], {"H1": -1.0, "H3": -1.0})
    return dict(n_rollouts=int(len(R)), n_pairs=int(len(P)), n_clusters=int(R["instance_id"].nunique()),
                cluster_unit=CLUSTER, models=rows,
                strata=[{"stratification": "rollout-length quartile", "stratum": str(k),
                         "mean_survival_exception": round(float(g["surv25_exception"].mean()), 4),
                         "rollouts": int(len(g))}
                        for k, g in R.groupby("length_quartile", observed=True) if len(g) >= 500],
                baselines=[{"model": "presence_only", "dv": "surv25_exception",
                            "presence": round(float(R["comp_exception"].mean()), 4), "n": int(len(R))},
                           {"model": "plus_uncertainty_removed", "dv": "later_submitted", "term": "removed_exception",
                            **{k: v for k, v in h3.items() if k in ("beta", "ci_lo", "ci_hi", "p", "clusters")}}],
                descriptive_rates={"survival_by_budget": {c: {k: surv[c][k] for k in ("survival_at_10pct",
                                                                                      "survival_at_25pct",
                                                                                      "survival_at_50pct",
                                                                                      "presence")}
                                                          for c in surv},
                                   "median_first_mention_position": {
                                       c: (round(float(R[f"first_pos_{c}"].median(numeric_only=True)), 4)
                                           if f"first_pos_{c}" in R.columns and R[f"first_pos_{c}"].notna().any()
                                           else None) for c in CAT},
                                   "turns_distribution": {"p10_p50_p90": [round(float(x), 1) for x in
                                                                          np.percentile(R["n_turns"],
                                                                                        [10, 50, 90])]}},
                gate_scope=TD11.DESIGNS["T140"]["gate_scope"])


def t142(fr: dict) -> dict:
    """Are the attempts of one task restatements, refinements or new approaches, and does that predict finishing?"""
    P = fr["P"]
    d = P.dropna(subset=["relation_class", "later_submitted"]).copy()
    floors = {"refinement": 0.05, "new": 0.05}
    prev, boot_ci = {}, {}
    for lab in ("restatement", "refinement", "new"):
        sub = d.assign(flag=(d["relation_class"] == lab).astype(int))[["instance_id", "flag"]]
        b = boot(sub, "instance_id", lambda x: float(x["flag"].mean()), 400)
        prev[lab] = round(float(sub["flag"].mean()), 4)
        boot_ci[lab] = {"ci": (b.get("ci") or [None, None]), "p": b.get("p")}
    h1 = dict(hypothesis="H1", term="prevalence_of_each_relation_class_among_consecutive_attempts",
              prevalence=prev, intervals=boot_ci, pairs=int(len(d)),
              instances=int(d["instance_id"].nunique()), frozen_floors=floors,
              verdict_rule="descriptive",
              beta=min(prev.get("refinement", 0), prev.get("new", 0)),
              n=int(len(d)), clusters=int(d["instance_id"].nunique()),
              note="H1 is a prevalence claim with a floor on the two named classes, so the smaller of the two shares "
                   "is the coefficient and its interval is read against the floor")
    ok = all(prev.get(lab, 0) >= floors[lab] and ((boot_ci[lab]["ci"] or [0, 0])[0] or 0) >= floors[lab]
             for lab in floors)
    # each class carries its own interval in the `intervals` field; no single interval is claimed for the pair of
    # floors, because a range across two different quantities is not an interval of anything
    h1["ci_lo"] = h1["ci_hi"] = h1["p"] = None
    h1["verdict"] = "supported" if ok else "not_all_classes_meet_the_frozen_floor"
    xs = ["is_refinement", "is_new", "earlier_submitted", "jaccard_z", "earlier_turns_log", "later_turns_log"]
    h2a = term(glm(d, "later_submitted", xs, "binomial"), "is_refinement")
    h2b = term(glm(d, "later_submitted", xs, "binomial"), "is_new")
    h2 = dict(hypothesis="H2", term="refinement_versus_new_on_the_later_attempt_finishing",
              refinement=h2a, new=h2b, beta=h2a.get("beta"), se=h2a.get("se"), ci_lo=h2a.get("ci_lo"),
              ci_hi=h2a.get("ci_hi"), p=h2a.get("p"), n=int(h2a.get("n") or len(d)),
              clusters=h2a.get("clusters"),
              submitted_rate_by_class={str(k): round(float(g["later_submitted"].mean()), 4)
                                       for k, g in d.groupby("relation_class", observed=True)},
              counts_by_class={str(k): int(len(g)) for k, g in d.groupby("relation_class", observed=True)})
    h2["verdict_direction"] = "predicted_positive: a refinement of the earlier attempt finishes more often than new"
    rows = holm_and_verdict([h1, h2], {"H2": 1.0})
    without = term(glm(d, "later_submitted", ["earlier_submitted", "jaccard_z", "earlier_turns_log",
                                              "later_turns_log"], "binomial"), "earlier_submitted")
    with_cls = glm(d, "later_submitted", xs, "binomial")
    no_cls = glm(d, "later_submitted", [c for c in xs if c not in ("is_refinement", "is_new")], "binomial")
    h3 = dict(hypothesis="H3", term="the_relation_class_beyond_overlap_and_the_earlier_outcome",
              verdict_rule="specificity", class_term=h2a, alien_like_overlap=term(
                  glm(d, "later_submitted", xs, "binomial"), "jaccard_z"),
              earlier_outcome_term=without,
              deviance_with_class=round(float(with_cls["deviance"].iloc[0]), 2) if with_cls is not None and
              not with_cls.empty else None,
              deviance_without_class=round(float(no_cls["deviance"].iloc[0]), 2) if no_cls is not None and
              not no_cls.empty else None,
              beta=h2a.get("beta"), se=h2a.get("se"), ci_lo=h2a.get("ci_lo"), ci_hi=h2a.get("ci_hi"),
              p=h2a.get("p"), n=int(len(d)),
              note="H3 is supported while the class term separates with both the overlap band and the earlier "
                   "attempt's own outcome in the model, and the deviance falls by at least the frozen band when the "
                   "classes enter")
    h3["verdict"] = ("supported" if h2a.get("beta") is not None and h2a.get("ci_lo") is not None
                     and (h2a["ci_lo"] > 0 or h2a["ci_hi"] < 0)
                     and (h3["deviance_without_class"] or 0) - (h3["deviance_with_class"] or 0) >= BAND_SMALL else
                     "not_specific_the_overlap_and_earlier_outcome_cover_it" if h2a.get("beta") is not None else
                     "not_testable_no_coefficient_estimated")
    rows = holm_and_verdict([h1, h2, h3], {"H2": 1.0})
    return dict(n_rollouts=int(fr["R"].shape[0]), n_pairs=int(len(d)),
                n_clusters=int(d["instance_id"].nunique()), cluster_unit=CLUSTER, models=rows,
                strata=[{"stratification": "relation class", "stratum": str(k),
                         "later_submitted_rate": round(float(g["later_submitted"].mean()), 4),
                         "mean_jaccard": round(float(g["jaccard"].mean()), 4), "pairs": int(len(g)),
                         "instances": int(g["instance_id"].nunique())}
                        for k, g in d.groupby("relation_class", observed=True) if len(g) >= 20] +
                       [{"stratification": "repository prefix", "stratum": str(k)[:30],
                         "refinement_share": round(float((g["relation_class"] == "refinement").mean()), 4),
                         "later_submitted_rate": round(float(g["later_submitted"].mean()), 4), "pairs": int(len(g))}
                        for k, g in d.groupby("repo_prefix", observed=True) if len(g) >= 200][:12],
                baselines=[{"model": "earlier_outcome_and_overlap", "dv": "later_submitted",
                            **{k: v for k, v in without.items() if k != "cluster"}},
                           {"model": "plus_relation_class", "dv": "later_submitted",
                            **{k: v for k, v in h2a.items() if k != "cluster"}}],
                descriptive_rates={"relation_class_prevalence": prev,
                                   "contradiction_flag_share": round(float(d["contradiction"].mean()), 4),
                                   "alien_relation_class_prevalence": {
                                       str(k): round(float(v / max(1, len(d))), 4) for k, v in
                                       d["alien_relation_class"].value_counts().items()},
                                   "jaccard_distribution": {"p10_p50_p90": [round(float(x), 4) for x in
                                                                            np.percentile(d["jaccard"],
                                                                                          [10, 50, 90])]}},
                gate_scope=TD11.DESIGNS["T142"]["gate_scope"])


DESIGN_FN = {"EXP-0209": ("T131", t131), "EXP-0210": ("T137", t137), "EXP-0211": ("T138", t138),
             "EXP-0212": ("T140", t140), "EXP-0213": ("T142", t142)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--only", action="append", default=[])
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    fr = load()
    if a.quick:
        keep = fr["R"]["instance_id"].drop_duplicates().sample(600, random_state=TD11.SEED)
        fr["R"] = fr["R"][fr["R"]["instance_id"].isin(set(keep))]
        fr["P"] = fr["P"][fr["P"]["instance_id"].isin(set(keep))]
    todo = {k: v for k, v in DESIGN_FN.items() if not a.only or k in a.only}
    bad = [k for k in (a.only or []) if k not in DESIGN_FN]
    if bad:
        raise SystemExit(f"ABORT: --only names no design: {bad}; valid ids are {sorted(DESIGN_FN)}")
    def separable(m):
        # a logit coefficient of tens with an interval of hundreds is quasi-separation, not an effect: the cell does
        # not identify the term, and saying so is the honest output rather than shipping the number (wave 6's lesson)
        try:
            return m.get("beta") is not None and (abs(float(m["beta"])) > 8.0
                                                  or (m.get("se") or 0) > 8.0)
        except (TypeError, ValueError):
            return False
    for exp, (topic, fn) in todo.items():
        art = fn(fr)
        for m in art.get("models") or []:
            for k in ("beta", "se", "ci_lo", "ci_hi", "p", "p_holm", "n", "clusters"):
                m.setdefault(k, None)
            if separable(m):
                m["unidentified_estimate"] = {k: m.get(k) for k in ("beta", "se", "ci_lo", "ci_hi")}
                m["beta"] = m["se"] = m["ci_lo"] = m["ci_hi"] = None
                m["verdict"] = "not_estimable_quasi_separation_in_this_cell"
                m["note"] = (m.get("note") or "") + (" the term is perfectly predicted by the outcome in this cell, so "
                                                       "the fitted coefficient is not an effect size and is withheld").strip()
        lack = [k for k in ("models", "strata", "descriptive_rates", "baselines") if not art.get(k)]
        if lack:
            raise SystemExit(f"ABORT {exp} ({topic}): the design produced no {lack}, so the package tables that read "
                             f"those blocks would ship a header with no numbers - measure it or drop the table")
        nofv = [m.get("hypothesis") or m.get("term") for m in art["models"] if not m.get("verdict")]
        if nofv:
            raise SystemExit(f"ABORT {exp} ({topic}): hypotheses {nofv} carry no verdict, and a pre-registered test "
                             f"that was not decided is not a deliverable")
        art.update(exp_id=exp, topic=topic, seed=TD11.SEED, quick=a.quick, started_at=W.now(),
                   frame_files_read={k: v.attrs.get("frame_file") for k, v in fr.items() if isinstance(v, pd.DataFrame)},
                   blocked_designs_in_this_wave=list(TD11.BLOCKED_BY_GATE),
                   invocation=" ".join([sys.executable] + sys.argv),
                   run_cost=W.run_cost_row(exp, t0, int(len(fr["R"])), int(fr["R"].shape[1]), "wave-11 design"),
                   finished_at=W.now())
        print(f"{exp} ({topic}): wrote {W.write_raw(exp, f'wave11_design_{exp[-4:]}', art).name}", flush=True)
        pd.DataFrame(art.get("models") or []).to_csv(W.OUT / f"EXP{exp[-4:]}_{topic.lower()}_models.csv",
                                                     index=False, encoding="utf-8")
        if art.get("strata"):
            pd.DataFrame(art["strata"]).to_csv(W.OUT / f"EXP{exp[-4:]}_{topic.lower()}_strata.csv", index=False,
                                               encoding="utf-8")
        print("  " + json.dumps({m.get("hypothesis"): m.get("verdict") for m in art["models"]},
                                default=str)[:280], flush=True)
    print(f"wallclock {round(time.time() - t0, 1)}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
