"""EXP-0195: the E00-E19 battery for wave 8, run by the same step loop as waves 2, 4, 5, 6 and 7.

The single-frame steps (ablation, scaling, replication, error taxonomy, per-config headline) come from
`exp_wave1_battery` through `exp_wave2_battery.run_battery`, so an ablation in wave 8 is the computation it is in
wave 2. What wave 8 supplies is its frames and the steps whose subject is a recorded search: a second instrument for
each marker family, the transfer of the whole marker set to a corpus written by a *different author* (the routing
release's human task instructions, so a plan marker counted in an agent's turn can be compared with one counted in a
user's request), the within-stratum permutation as the counterfactual this corpus can run, and the duplication audit
that says how much of this release is the same instruction, the same call and the same observation recycled.

    python 02_shared_code/package_factory/exp_wave8_battery.py [--quick]
"""
from __future__ import annotations

import collections
import hashlib
import pathlib
import re
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np                                                # noqa: E402
import pandas as pd                                               # noqa: E402
import wave_lib as W                                              # noqa: E402
import exp_wave2_battery as B2                                    # noqa: E402
import exp_wave5_features as EF5                                  # noqa: E402  (kappa: one statistic, all waves)
import exp_wave7_designs as D7                                    # noqa: E402  (rho_ci helpers, one implementation)
import exp_wave8_designs as D8                                    # noqa: E402
import exp_wave8_features as E8                                   # noqa: E402  the release reader, unchanged
import probe_wave8_premises as P8                                 # noqa: E402
import topic_designs_wave8 as TD8                                 # noqa: E402

EXP = "EXP-0195"
CTRL = D8.CTRL
CLUSTER = D8.CLUSTER
ROUTING_FRAME = "P001 routing release, dev split"
E06_DRAWS = 200                        # cluster-bootstrap draws for an agreement statistic, fixed before reading


def frames() -> dict:
    F = D8.load()
    calls = F[(F["n_calls"] > 0)].dropna(subset=["call_changed"])
    return {"turns": F, "trajectories": F.drop_duplicates("traj_id").copy(),
            "call_turns": calls, "after_error": calls[calls["after_error"] == 1],
            "anchored_later_turns": F[(F["has_early_hypo"] == 1) & (F["later_turn"] == 1)]}


def e06_second_instrument(fr: dict) -> dict:
    """Each wave-8 marker measured a second way, and the list of constructs that have only one form.

    Two pairs below are deliberately *discriminant*: a marker and the thing it must not be confused with, whose
    agreement is exactly what a design's control assumes.
    """
    out = []

    def rho(d, label, a, b, note, cluster=CLUSTER):
        dd = d[[a, b, cluster]].dropna()
        if dd.empty or dd[a].nunique() < 3 or dd[b].nunique() < 3:
            out.append({"construct": label, "status": "one instrument is near-degenerate on these rows, so no rank "
                        "correlation is claimed", "n": int(len(dd)), "note": note})
            return
        r = dict(W.rho_ci(dd, cluster, a, b))
        r.update(construct=label, n=int(len(dd)), clusters=int(dd[cluster].nunique()), note=note)
        out.append(r)

    def kappa(d, label, a, b, note, cluster=CLUSTER):
        dd = d[[a, b, cluster]].dropna()
        if dd.empty or dd[a].nunique() < 2 or dd[b].nunique() < 2:
            out.append({"construct": label, "status": "one instrument is constant on these rows, so no agreement "
                        "statistic exists", "n": int(len(dd)), "note": note})
            return
        kb = W.cluster_boot_ci_and_p(dd, cluster, lambda x: EF5.kappa(x[a], x[b]), draws=E06_DRAWS, seed=TD8.SEED)
        rec = {"construct": label, "kappa": EF5.kappa(dd[a], dd[b]),
               "agreement": round(float((dd[a] == dd[b]).mean()), 4), "n": int(len(dd)),
               "clusters": int(dd[cluster].nunique()), "note": note}
        rec["ci"] = ([round(float(v), 4) for v in kb["ci"]] if "ci" in kb else None)
        if "error" in kb:
            rec["boot_note"] = kb["error"]
        out.append(rec)

    T, C, A = fr["turns"], fr["call_turns"], fr["anchored_later_turns"]
    rho(A, "anchor concentration: own-hypothesis overlap against task overlap (discriminant)", "hypo_overlap_z",
        "task_overlap", "T171's claim is concentration on the hypothesis, not on the instruction's vocabulary: a "
                       "strong positive here means the two are the same signal and the design cannot separate them")
    rho(A, "anchor concentration: own-hypothesis overlap against the seeded alien anchor", "hypo_overlap_z",
        "alien_overlap_z", "T171's H3 rests on this pair; the alien arm is the same instrument on text the "
                           "trajectory never saw")
    kappa(C, "a correction marker against an error marker in the observation before it (discriminant)",
          "spoke_correction", "after_error", "T190's two instruments must come apart: agreement near one would mean "
                                              "an admission and a failed observation are the same event")
    rho(T, "uncertainty language against sufficiency language", "uncert_z", "suffic",
        "one hedges, the other closes; if they moved together neither could condition the other")
    rho(fr["trajectories"], "plan specificity composite against opening-turn length", "spec_sum_z", "first_chars_log",
        "T182's H3 is exactly the question of whether specificity is verbosity in another name")
    rho(fr["trajectories"], "the repeated-call share against the error share", "repeat_share", "error_share",
        "the two productivity quantities wave 8 uses; a strong link means H1 and H2 of T182 read one signal twice")
    rho(A, "a turn's own length against its anchor overlap", "body_chars_log", "hypo_overlap_z",
        "an overlap share is computed over the turn's own words, so length is the denominator the concentration "
        "claim has to survive")
    kappa(T, "a hypothesis marker against a plan marker in the same turn (discriminant)", "hypo", "plan",
          "T171 anchors on hypotheses while T182 counts plans: if the two markers landed on the same sentences the "
          "two designs would be measuring one construct")
    return {"pairs": out,
            "single_instrument_constructs": [
                "stopping (the release records only that an assistant turn is the last one; there is no explicit stop "
                "act, and 53.5% of trajectories end mid-exchange, which is what stopped T175)",
                "task success (no column of the release carries it - EXP-0190's G13 measured 0 - so no quantity in "
                "this wave is labelled with it)",
                "the call arguments (compared as canonical JSON strings; a semantic equality between two different "
                "spellings of the same path would need a model)"],
            "note": "a construct with one operationalisation is listed, not silently dropped"}


def e08_external(fr: dict) -> dict:
    """The same marker instruments run on text written by a different author.

    The routing release's dev rows carry a human task instruction and no agent prose, so the plan, hypothesis,
    sufficiency and correction markers transfer as definitions and their prevalences are measurable - while the
    quantities that need a trajectory, a call or an observation do not exist there at all. Prevalences transfer; no
    association does.
    """
    df = W.load_routing(cols=None)
    inst = fr["turns"]

    def prev(s, terms):
        low = s.astype(str).str.lower()
        return round(float(sum(1 for v in low if any(t in v for t in terms)) / max(1, len(low))), 4)

    def agentprev(col):
        return round(float((inst[col] > 0).mean()), 4)

    return {"corpus": ROUTING_FRAME + ": one human task instruction per row, no assistant turn, no tool call, no "
                                       "observation",
            "rows_read": int(len(df)),
            "instruments": {"plan_markers": "P8.PLAN (wave 5's two lexicons)",
                            "hypothesis_markers": "P8.HYPOTHESIS", "sufficiency_markers": "P8.SUFFICIENCY",
                            "correction_markers": "P8.CORRECTION", "failure_markers": "P8.FAILURE"},
            "prevalences_human_instructions": {
                "carries_a_plan_marker": prev(df["question"], P8.PLAN),
                "carries_a_hypothesis_marker": prev(df["question"], P8.HYPOTHESIS),
                "carries_a_sufficiency_marker": prev(df["question"], P8.SUFFICIENCY),
                "carries_a_correction_marker": prev(df["question"], P8.CORRECTION),
                "mean_content_words": round(float(np.mean([len(P8.words(q)) for q in df["question"]])), 2)},
            "prevalences_agent_turns": {
                "carries_a_plan_marker": agentprev("plan"),
                "carries_a_hypothesis_marker": agentprev("hypo"),
                "carries_a_sufficiency_marker": agentprev("suffic"),
                "carries_a_correction_marker": agentprev("correct"),
                "mean_content_words": round(float(inst["turn_words"].mean()), 2)},
            "prevalences_agent_observations": {
                "carries_a_failure_marker": None,
                "note": "the turn frame stores whether the observation before a turn carried a failure marker, not the "
                        "observation text; the census measured that share over all 174,545 observations as 0.5893 and "
                        "the frame reproduces it in its own cross-check"},
            "what_transfers": "the marker lists themselves, unchanged, applied to prose with a different author",
            "what_does_not": "nothing trajectory-shaped: the routing rows have no assistant turn, no emitted call, no "
                             "observation and no end, so a wave-8 coefficient cannot be reproduced there",
            "arms": {}}


def e17_counterfactual(fr: dict) -> dict:
    """The intervention this wave can run: destroy the marker's placement, keep its dose.

    A recorded search cannot be re-run against a different world without a model, which the programme forbids, so each
    design's manipulated term is redistributed *within* the stratum its own model conditions on. Which call repeated
    or which turn hedged is then preserved in the marginal and broken in the pairing, and a coefficient that survives
    is not a property of the stratum.
    """
    rng = np.random.default_rng(TD8.SEED)
    spec = {"T171": dict(frame="anchored_later_turns", y="hypo_overlap_z", x="position", family="gaussian",
                         covars=CTRL, cluster=CLUSTER, permute_within="position_third"),
            "T182": dict(frame="trajectories", y="repeat_share", x="spec_sum_z", family="gaussian",
                         covars=CTRL, cluster=CLUSTER, permute_within="category"),
            "T190": dict(frame="after_error", y="call_changed", x="spoke_correction", family="binomial",
                         covars=CTRL, cluster=CLUSTER, permute_within="category")}

    def fit(d, sp):
        f = D8.glm(d, sp["y"], [sp["x"]] + sp["covars"], sp["family"], cluster=sp["cluster"])
        if f is None or f.empty:
            return None
        r = f[f["term"] == sp["x"]]
        return None if r.empty else [round(float(r.iloc[0]["beta"]), 4), round(float(r.iloc[0]["ci_lo"]), 4),
                                     round(float(r.iloc[0]["ci_hi"]), 4)]
    arms = []
    for topic, sp in spec.items():
        F = fr[sp["frame"]]
        w = sp["permute_within"]
        if w not in F.columns:
            arms.append({"topic": topic, "term": sp["x"],
                         "note": f"the permutation stratum {w!r} is not a column of this frame, so no arm is offered"})
            continue
        perm = F.copy()
        perm[sp["x"]] = F.groupby(w, observed=True)[sp["x"]].transform(lambda s: rng.permutation(s.to_numpy()))
        arms.append({"topic": topic, "term": sp["x"], "on_outcome": sp["y"], "permuted_within": w,
                     "as_frozen": fit(F, sp), "marker_permuted_within_stratum": fit(perm, sp),
                     "rows": int(len(F)), "strata": int(F[w].nunique())})
    return {"instrument": "the same frozen model on the same rows, with the marker permuted inside each stratum the "
                          "model already conditions on",
            "arms": arms,
            "note": "a rewrite arm is not offered because a recorded trajectory cannot be re-acted without a model; "
                    "permuting within the stratum keeps the dose and the composition and destroys only which turn or "
                    "which task the marker belongs to"}


def e19_duplication(fr: dict) -> dict:
    """How much of this release is the same instruction, call and observation over again?

    Computed from the release itself in one pass, because the turn frame keeps word counts rather than text: a task
    stated verbatim twice, a call string issued in two trajectories, or an observation whose content already appeared
    elsewhere is the contamination a per-turn count cannot see.
    """
    t0 = time.time()
    df, n_files = E8.EF.load_trajectories(10 ** 9)
    tasks, calls, obs = collections.Counter(), collections.Counter(), collections.Counter()
    traj_with_dup_call = 0
    rows = 0
    for r in df.itertuples(index=False):
        rows += 1
        tasks[str(r.task).strip().lower()] += 1
        f = E8.parse(r)
        cs = [f"{n}|{a}" for t in f["evs"] if t[0] == "t" for (n, a) in [
            (c[0], hashlib.sha1(c[1].encode("utf-8")).hexdigest()[:12]) for c in t[1]["calls"]]]
        calls.update(set(cs))
        traj_with_dup_call += int(len(cs) != len(set(cs)))
        for o in f["obs"]:
            obs[hashlib.sha1(re.sub(r"\s+", " ", o[1]).strip().lower().encode("utf-8")).hexdigest()[:16]] += 1
    return {"trajectories_scanned": rows, "files_read": n_files,
            "distinct_task_instructions": int(len(tasks)),
            "share_of_trajectories_sharing_a_verbatim_task":
                round(float(1 - len(tasks) / max(1, rows)), 4),
            "most_repeated_task_rows": int(max(tasks.values())) if tasks else 0,
            "distinct_call_strings_across_the_release": int(len(calls)),
            "total_call_slots": int(sum(calls.values())),
            "trajectories_repeating_a_call_internally": traj_with_dup_call,
            "distinct_observation_contents": int(len(obs)),
            "total_observations": int(sum(obs.values())),
            "share_of_observations_seen_elsewhere": round(float(1 - len(obs) / max(1, sum(obs.values()))), 4),
            "wallclock_sec": round(time.time() - t0, 1),
            "rule": "a call string is a name plus the sha1 of its canonical arguments; an observation is its "
                    "whitespace-normalised lower-cased text; both are compared across the whole release, so a "
                    "concentration in a few repeated tasks or reused observations is measured rather than assumed"}


def shared(fr: dict, quick: bool = False) -> dict:
    return {"e06_second_instrument": e06_second_instrument(fr),
            "e08_external": e08_external(fr),
            "e17_counterfactual": e17_counterfactual(fr),
            "e19_contamination": e19_duplication(fr)}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    B2.run_battery(EXP, "wave8_battery_0195", frames, {
        "T171": dict(frame="anchored_later_turns", y="hypo_overlap_z", x="position", family="gaussian",
                     covars=CTRL, cluster=CLUSTER),
        "T182": dict(frame="trajectories", y="repeat_share", x="spec_sum_z", family="gaussian", covars=CTRL,
                     cluster=CLUSTER),
        "T190": dict(frame="after_error", y="call_changed", x="spoke_correction", family="binomial", covars=CTRL,
                     cluster=CLUSTER)}, shared, quick="--quick" in sys.argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
