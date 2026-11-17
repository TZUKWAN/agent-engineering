"""EXP-0202: the E00-E19 battery for wave 9, run by the same step loop as waves 2, 4, 5, 6, 7 and 8.

The single-frame steps (ablation, scaling, replication, error taxonomy, per-config headline) come from
`exp_wave1_battery` through `exp_wave2_battery.run_battery`, so an ablation in wave 9 is the computation it is in
wave 2. What wave 9 supplies is its frames and the steps whose subject is a rollout: a second instrument for each
behavioural quantity, the transfer of the whole instrument set to the corpus that has actions but no shell commands
(the hermes traces), the within-stratum permutation as the counterfactual this release can run, and the command
duplication audit that says how much of the 292,992-step alphabet is the same handful of commands repeated.

    python 02_shared_code/package_factory/exp_wave9_battery.py [--quick]
"""
from __future__ import annotations

import collections
import gzip
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np                                                # noqa: E402
import pandas as pd                                               # noqa: E402
import wave_lib as W                                              # noqa: E402
import exp_wave2_battery as B2                                    # noqa: E402
import exp_wave5_features as EF5                                  # noqa: E402  (kappa: one statistic, all waves)
import exp_wave8_features as E8                                   # noqa: E402  the hermes reader, unchanged
import exp_wave9_designs as D9                                    # noqa: E402
import probe_wave6_premises as P6                                  # noqa: E402  the family classifier
import probe_wave8_premises as P8                                   # noqa: E402 hermes instruments
import topic_designs_wave9 as TD9                                   # noqa: E402

EXP = "EXP-0202"
CTRL = D9.CTRL
CLUSTER = D9.CLUSTER
HERMES_FRAME = "EXP0164_wave5_step_features.csv.gz"
HERMES_CALL_FRAME = "EXP0153_wave4_step_features.csv.gz"
E06_DRAWS = 200


def frames() -> dict:
    fr = D9.load()
    T, S = fr["T"], fr["S"]
    L = D9.transition_loglik(S)
    T = T.merge(L.drop(columns=["instance_id", "task_family"]), on="traj_key", how="left")
    for c in ("ll_bigram", "ll_family", "ll_unigram"):
        T[c + "_z"] = D9.z(T[c].astype(float))
    T["ll_gain_family"] = T["ll_family"] - T["ll_bigram"]
    return {"rollouts": T, "steps": S,
            "failure_cell": T[T["failure_then_a_further_command"] == 1].copy(),
            "multi_rollout_instances": T[T["rollouts_per_instance"] >= 2].copy()}


def e06_second_instrument(fr: dict) -> dict:
    """Each wave-9 behavioural quantity measured a second way, and the list of constructs with only one form."""
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
        kb = W.cluster_boot_ci_and_p(dd, cluster, lambda x: EF5.kappa(x[a], x[b]), draws=E06_DRAWS, seed=TD9.SEED)
        rec = {"construct": label, "kappa": EF5.kappa(dd[a], dd[b]),
               "agreement": round(float((dd[a] == dd[b]).mean()), 4), "n": int(len(dd)),
               "clusters": int(dd[cluster].nunique()), "note": note}
        rec["ci"] = ([round(float(v), 4) for v in kb["ci"]] if "ci" in kb else None)
        if "error" in kb:
            rec["boot_note"] = kb["error"]
        out.append(rec)

    T, S = fr["rollouts"], fr["steps"]
    rho(T, "exploration: the family-switch rate against the family-concentration it complements", "switch_rate_z",
        "family_concentration_z", "two readings of the same sequence, so a strong negative is expected and is "
                                   "reported as an aggregation check rather than as corroboration")
    rho(T, "alphabet breadth: distinct families against the switch rate that produces them", "distinct_families_z",
        "switch_rate_z", "T153's grammar and T178's early block both use one of these; if they were the same number "
                         "the two designs would be fitting it twice")
    rho(T, "repetition: the exact-repeat share against the failure count it is supposed to track (discriminant)",
        "repeat_share_z", "failures", "wave 9 reads repetition as unproductive search and failure as an event; "
                                       "agreement would mean one instrument doing both jobs")
    rho(T, "newness against the share of steps that received no observation at all (discriminant)", "newness_mean_z",
        "steps_without_observation", "this is the pair EXP-0196's G9 turned on: 21% of steps have no observation, and "
                                      "if newness were merely their absence the two would move together")
    rho(T, "grammar: a rollout's pooled bigram likelihood against its own family's matrix", "ll_bigram_z",
        "ll_gain_family", "T153's H2 gain is a difference of these two; a large correlation would mean the gain is "
                          "just the pooled level again")
    kappa(S, "a failed observation against a switch on the next step (discriminant)", "failed_observation",
          "switched", "T179 needs the failure and the change to be different events; agreement near one would make "
                      "the recovery window a restatement of switching")
    rho(T, "cost: duration against the number of commanded steps", "duration_z", "log_steps",
        "T193's cost-adjusted ranking uses both, so how far apart they are here is how much the ranking has two "
        "axes rather than one")
    return {"pairs": out,
            "single_instrument_constructs": [
                "completion (the release's own exit_status, with two values and no second record; 560 of 19,988 "
                "rollouts are Submitted, which is the sparsity EXP-0196 recorded)",
                "the family of a step (one classifier over the command's first executable token; a second reading "
                "would need a parsed argument structure the release does not provide uniformly)",
                "a rollout's value for reuse (ranked on the release's own label plus its steps, repetition and "
                "duration; there is no downstream task in this corpus that a kept rollout is measured against)"],
            "note": "a construct with one operationalisation is listed, not silently dropped"}


def e08_external(fr: dict) -> dict:
    """The wave's instruments run on the corpus that records actions but no shell command.

    hermes names a tool call per turn instead of writing a command line, so `family_of` transfers as a definition and
    mostly returns `other` - which is the finding, not a failure: a step-family grammar is a property of a shell
    corpus, and the same instruments over a tool-call corpus give prevalences, not a shared alphabet.
    """
    path = next((p for p in (W.OUT / HERMES_FRAME, W.ROOT / "results_processed" / HERMES_FRAME) if p.is_file()), None)
    if path is None:
        return {"status": "not attempted: the wave-5 hermes frame is not on disk", "looked_for": [str(path)],
                "arms": {}}
    H = pd.read_csv(gzip.open(path, "rt", encoding="utf-8"))
    names = H["first_call_name"].fillna("").astype(str)
    fam = names.map(P6.family_of)
    S, T = fr["steps"], fr["rollouts"]
    cmd_fam = S["family"].fillna("other")
    return {"corpus": "hermes-agent-reasoning-traces as measured for waves 4, 5 and 8 (EXP-0164 frame): one named "
                      "tool call per assistant turn, no shell command line",
            "steps_read": int(len(H)), "trajectories": int(H["traj_id"].nunique()),
            "instruments": {"family_classifier": "probe_wave6_premises.family_of, applied to the named call",
                            "failure_markers": "wave 4's list, unchanged",
                            "new_word_share": "wave 6's content-word share"},
            "prevalences_external": {
                "a_named_call_maps_to_a_command_family": round(float((fam != "other").mean()), 4),
                "distinct_families_among_calls": int(fam.nunique()),
                "distinct_call_names": int(names.nunique()),
                "family_switch_from_previous_turn": round(float((fam.values[1:] != fam.values[:-1]).mean()), 4),
                "observation_carries_a_failure_marker": round(float(H["prev_obs_error"].fillna(0).mean()), 4)},
            "prevalences_wave9_steps": {
                "a_command_maps_to_a_command_family": round(float((cmd_fam != "other").mean()), 4),
                "distinct_families_among_steps": int(cmd_fam.nunique()),
                "distinct_commands": int(S["command_sha"].nunique()),
                "family_switch_from_previous_step": round(float(S["switched"].mean()), 4),
                "step_level_failure_marker_share": round(float(S["failed_observation"].mean()), 4)},
            "what_transfers": "the classifier and the marker lists, unchanged, applied to a different release's "
                              "action names",
            "what_does_not": "the alphabet. A tool-call corpus has no command line, so the shell-name lookup that "
                             "gives wave 9 its transition matrix cannot name most of its steps - which is exactly "
                             "why T153's claim is about this release's step sequences and not about agent behaviour "
                             "in general; no association transfers either, because the other corpus has no outcome "
                             "label at all (EXP-0190 measured that)",
            "arms": {}}


def e17_counterfactual(fr: dict) -> dict:
    """The intervention this wave can run: destroy the marker's placement, keep its dose."""
    rng = np.random.default_rng(TD9.SEED)
    spec = {"T178": dict(frame="rollouts", y="submitted", x="ff_switch_rate_z", family="binomial", covars=CTRL,
                         cluster=CLUSTER, permute_within="length_quartile"),
            "T179": dict(frame="failure_cell", y="submitted", x="changed_at_lag_1", family="binomial",
                         covars=CTRL, cluster=CLUSTER, permute_within="task_family"),
            "T193": dict(frame="multi_rollout_instances", y="n_steps", x="submitted", family="gaussian",
                         covars=["log_steps"], cluster=CLUSTER, permute_within="task_family")}

    def fit(d, sp):
        f = D9.glm(d, sp["y"], [sp["x"]] + sp["covars"], sp["family"], cluster=sp["cluster"])
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
            "note": "a rollout cannot be re-recorded against a different world without a model, which the programme "
                    "forbids; permuting inside the task family or the length quartile keeps the dose and destroys "
                    "only which rollout the marker belongs to"}


def e19_command_duplication(fr: dict) -> dict:
    """How many distinct commands stand behind 292,992 steps, and how much of the alphabet is one or two tools?"""
    S, T = fr["steps"], fr["rollouts"]
    vc = S["command_sha"].value_counts()
    fam = S["family"].value_counts()
    top = set(vc.head(20).index)
    return {"steps_scanned": int(len(S)), "distinct_command_strings": int(vc.size),
            "share_of_steps_repeating_a_string_seen_elsewhere": round(float(1 - vc.size / max(1, len(S))), 4),
            "most_repeated_command_rows": int(vc.iloc[0]) if len(vc) else 0,
            "share_of_steps_in_the_twenty_most_repeated_commands": round(float(S["command_sha"].isin(top).mean()), 4),
            "alphabet_top_families": {str(k): int(v) for k, v in fam.head(8).items()},
            "share_of_steps_in_the_single_most_common_family": round(float(fam.iloc[0] / max(1, len(S))), 4),
            "instances": int(T["instance_id"].nunique()),
            "rollouts": int(len(T)),
            "rule": "one digest per whitespace-normalised command string, counted across the whole sample: a corpus "
                    "whose grammar is really three tools used many ways is visible here rather than assumed away"}


def shared(fr: dict, quick: bool = False) -> dict:
    return {"e06_second_instrument": e06_second_instrument(fr),
            "e08_external": e08_external(fr),
            "e17_counterfactual": e17_counterfactual(fr),
            "e19_contamination": e19_command_duplication(fr)}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    B2.run_battery(EXP, "wave9_battery_0202", frames, {
        "T178": dict(frame="rollouts", y="submitted", x="ff_switch_rate_z", family="binomial", covars=CTRL,
                     cluster=CLUSTER),
        "T179": dict(frame="failure_cell", y="submitted", x="changed_at_lag_1", family="binomial", covars=CTRL,
                     cluster=CLUSTER),
        "T193": dict(frame="multi_rollout_instances", y="n_steps", x="submitted", family="gaussian",
                     covars=["log_steps"], cluster=CLUSTER)}, shared, quick="--quick" in sys.argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
