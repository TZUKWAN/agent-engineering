"""EXP-0180: the E00-E19 battery for wave 6, run by the same step loop as waves 2, 4 and 5.

The single-frame steps (ablation, scaling, replication, error taxonomy, contamination-by-row) come from
`exp_wave1_battery` through `exp_wave2_battery.run_battery`, so an ablation in wave 6 is the computation it is in
wave 2. What wave 6 supplies is its frames - one population per design's own subject - and the steps whose subject is
the search process: a second instrument for each structural marker, an external transfer of the whole instrument set
to the other local transcript release, a within-trajectory permutation as the counterfactual this corpus can run, and
the command-duplication audit.

    python 02_shared_code/package_factory/exp_wave6_battery.py [--quick]
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np                                                # noqa: E402
import pandas as pd                                               # noqa: E402
import wave_lib as W                                              # noqa: E402
import exp_wave2_battery as B2                                    # noqa: E402
import exp_wave5_designs as D5                                    # noqa: E402  (kappa: one statistic, both waves)
import exp_wave6_designs as D6                                    # noqa: E402
import exp_wave4_designs as D4                                    # noqa: E402  (family_of: one classifier, both corpora)
import probe_wave6_premises as P6                                 # noqa: E402
import topic_designs_wave6 as TD6                                 # noqa: E402

EXP = "EXP-0180"
CTRL = D6.CTRL
HERMES_FRAME = "EXP0164_wave5_step_features.csv.gz"
E06_DRAWS = 200                        # cluster-bootstrap draws for an agreement statistic, fixed before reading

SPEC = {
    "T155": dict(frame="steps", y="log_steps", x="need_words_z", family="gaussian", covars=CTRL,
                 cluster="instance_id"),
    "T157": dict(frame="obs_steps", y="new_z", x="scent_z", family="gaussian", covars=CTRL, cluster="instance_id"),
    "T158": dict(frame="obs_steps", y="continues", x="new_z", family="binomial",
                 covars=D6.CTRL_CONTINUATION, cluster="instance_id"),   # step_position determines `continues`
    "T168": dict(frame="switch_steps", y="new_z", x="switched", family="gaussian", covars=CTRL,
                 cluster="instance_id"),
    "T170": dict(frame="trajectories", y="family_concentration", x="off_modal_first", family="gaussian",
                 covars=[c for c in CTRL if c != "step_position"], cluster="instance_id"),
    "T174": dict(frame="switch_steps", y="new_z", x="is_repeat", family="gaussian", covars=CTRL,
                 cluster="instance_id"),
}


def frames() -> dict:
    F = D6.load()
    steps = F
    obs = F[F["obs_chars"] > 0].dropna(subset=["new_information"])
    return {"steps": steps,
            "obs_steps": obs,
            "switch_steps": obs[obs["step_index"] > 1],
            "trajectories": steps.drop_duplicates("traj_key")}


def e06_second_instrument(fr: dict) -> dict:
    """Each wave-6 structural marker measured a second way, and the list of constructs that have only one form.

    A pair is two ways of deciding the same thing on the same rows. Two of the pairs below are deliberately
    *discriminant* rather than convergent: a marker and a construct it must not be confused with, whose agreement is
    the thing the design's control assumes.
    """
    out = []

    def rho(F, label, a, b, note):
        d = F[[a, b, D6.CLUSTER]].dropna()
        if d[a].nunique() < 3 or d[b].nunique() < 3:
            out.append({"construct": label, "status": "one instrument is near-degenerate on these rows, so no rank "
                        "correlation is claimed", "share_a": round(float(d[a].mean()), 4),
                        "share_b": round(float(d[b].mean()), 4), "n": int(len(d)), "note": note})
            return
        r = dict(W.rho_ci(d, D6.CLUSTER, a, b))
        r.update(construct=label, n=int(len(d)), clusters=int(d[D6.CLUSTER].nunique()), note=note)
        out.append(r)

    def kappa(F, label, a, b, note):
        d = F[[a, b, D6.CLUSTER]].dropna()
        if d.empty or d[a].nunique() < 2 or d[b].nunique() < 2:
            out.append({"construct": label, "status": "one instrument is constant on these rows, so no agreement "
                        "statistic exists", "n": int(len(d)), "note": note})
            return
        boot = W.cluster_boot_ci_and_p(d, D6.CLUSTER, lambda x: D5.EF.kappa(x[a], x[b]), draws=E06_DRAWS,
                                        seed=TD6.SEED)
        rec = {"construct": label, "kappa": D5.EF.kappa(d[a], d[b]),
               "agreement": round(float((d[a] == d[b]).mean()), 4), "n": int(len(d)),
               "clusters": int(d[D6.CLUSTER].nunique()), "note": note}
        rec["ci"] = ([round(float(v), 4) for v in boot["ci"]] if "ci" in boot else None)
        if "error" in boot:
            rec["boot_note"] = boot["error"]
        out.append(rec)

    obs = fr["obs_steps"]
    sw = fr["switch_steps"]
    traj = fr["trajectories"]
    rho(obs, "information scent: symmetric overlap vs asymmetric containment", "scent_z", "scent_contain_z",
        "T157's H2 rests on this pair: the same two strings compared two ways")
    rho(obs, "new information vs the size of the output it was computed from", "new_z", "obs_chars_log",
        "the confound the design's control is there for: a bigger output has more words that could be new")
    kappa(obs, "failure markers vs success markers in the same observation", "failed_observation", "success_language",
          "a discriminant pair, not a convergent one: agreement here would mean the two lexicons read the same "
          "sentence and neither could condition on the other")
    rho(sw, "family concentration vs the switching rate it is the complement of", "family_concentration",
        "switch_rate", "the two are computed from the same family sequence, so a strong negative is expected and is "
                       "reported as such rather than as corroboration")
    rho(traj, "repetition present vs the maximum number of prior runs of any command", "has_exact_repeat",
        "max_repeat_index", "a binary reading of the same count, so this is an aggregation check")
    rho(fr["steps"], "rollout depth vs the step budget its instance reached", "log_steps", "step_budget_log",
        "T155's H2 controls for one to estimate the other; near-independence would mean the budget is not a "
        "property of the rollout")
    return {"pairs": out,
            "single_instrument_constructs": [
                "new information (only the content-word share against everything the rollout had seen; a second "
                "form would need a different tokeniser or a per-document novelty, neither of which the frame stores)",
                "repetition (only exact equality of the whitespace-normalised command string; a near-duplicate "
                "reading would need pairwise command comparisons the frame does not carry)",
                "termination (only the release's own exit_status field, which has two values and no second record "
                "in this corpus)"],
            "note": "a construct with one operationalisation is listed, not silently dropped"}


def e08_external(fr: dict) -> dict:
    """The same instruments run on the other local transcript release, which has actions but no shell commands.

    hermes carries a named tool call per turn rather than a command string, so the family classifier, the switch
    count and the repetition count all transfer as definitions - but its outcome is a following call, not a
    termination label, and its observations are returned to a different harness. Prevalences transfer; no association
    does.
    """
    import gzip
    path = next((p for p in (W.OUT / HERMES_FRAME, W.ROOT / "results_processed" / HERMES_FRAME) if p.is_file()), None)
    if path is None:
        return {"status": "not attempted: the wave-5 frame is not on disk, so the other release was not read",
                "looked_for": [str(W.OUT / HERMES_FRAME)], "arms": {}}
    H = pd.read_csv(gzip.open(path, "rt"))
    H = H.sort_values(["traj_id", "turn_index"]).reset_index(drop=True)   # one order for both within-trajectory
    H["fam"] = H["first_call_name"].fillna("").astype(str).map(D4.family_of)                                             # scans
    hsteps = int(len(H))
    g = H.groupby("traj_id", sort=False)
    switched = (H["fam"] != g["fam"].shift(1)).astype(int)
    keep = g["turn_index"].shift(1).notna().astype(bool)
    dup = pd.Series(False, index=H.index)
    for _, gg in H.groupby("traj_id", sort=False):
        seen = set()
        for i, c in zip(gg.index, gg["first_call_name"].astype(str)):
            if c and c != "" and c in seen:
                dup.at[i] = True
            seen.add(c)
    inst = fr["steps"]
    named_external = {"inspection", "execution", "production"}
    named_internal = set(P6.FAMILY) - {"other"}
    return {"corpus": "hermes-agent-reasoning-traces as measured for waves 4-5 (EXP-0164 frame): one named tool call "
                      "per assistant turn, no shell command string",
            "rows_read": hsteps, "trajectories": int(H["traj_id"].nunique()),
            "classifiers": {"external": "exp_wave4_designs.family_of: inspection / execution / production / other",
                            "wave6": "probe_wave6_premises.family_of: twelve command families, or other/unparsed"},
            "prevalences_external": {
                "action_carries_a_named_behaviour_family": round(float(H["fam"].isin(named_external).mean()), 4),
                "family_switch_from_previous_turn": round(float(switched[keep].mean()), 4),
                "repeated_action_within_trajectory": round(float(dup[keep].mean()), 4),
                "distinct_families_per_trajectory_mean": round(float(H.groupby("traj_id")["fam"].nunique().mean()), 3)},
            "prevalences_wave6": {
                "action_carries_a_named_behaviour_family": round(
                    float(inst["family"].isin(named_internal & set(inst["family"].unique())).mean()), 4),
                "family_switch_from_previous_step": round(float(inst["switched"].mean()), 4),
                "repeated_action_within_trajectory": round(float(inst.groupby("traj_key")["has_exact_repeat"]
                                                                 .first().mean()), 4),
                "distinct_families_per_trajectory_mean": round(float(inst.groupby("traj_key")["family"]
                                                                     .nunique().mean()), 3)},
            "what_transfers": "the instrument set: a family classifier over action names, a switch against the "
                              "previous action, a repeat against the same rollout - each computed independently on "
                              "each corpus's own text",
            "what_does_not": "no association transfers. The other release has no command string, so `new_information` "
                             "has no text to compare against its own action, no `Submitted`-versus-ran-out label, and "
                             "its step count is bounded by a different harness; the design quantities here are "
                             "defined on this corpus's step object only",
            "arms": {}}


def e17_counterfactual(fr: dict) -> dict:
    """The intervention this wave can run: destroy the marker's placement, keep its dose.

    A recorded rollout cannot be re-run without a model, which the programme forbids, so each design's manipulated
    term is redistributed *within* the trajectory instead. A structural fact about a step - that it switched, that
    it repeated, how deep it sits - survives that in a different way than a lexical one, and the arms say which.
    """
    rng = np.random.default_rng(42)

    def fit(d, x, y, family):
        f = D6.glm(d, y, [x] + CTRL, family)
        if f is None or f.empty:
            return None
        r = f[f["term"] == x]
        return None if r.empty else [round(float(r.iloc[0]["beta"]), 4), round(float(r.iloc[0]["ci_lo"]), 4),
                                     round(float(r.iloc[0]["ci_hi"]), 4)]
    arms = []
    for topic, sp in SPEC.items():
        F = fr[sp["frame"]]
        perm = F.copy()
        perm[sp["x"]] = F.groupby(D6.CLUSTER)[sp["x"]].transform(lambda s: rng.permutation(s.to_numpy()))
        arms.append({"topic": topic, "term": sp["x"], "on_outcome": sp["y"], "as_frozen": fit(F, sp["x"], sp["y"],
                                                                                             sp["family"]),
                     "marker_permitted_within_trajectory": fit(perm, sp["x"], sp["y"], sp["family"]),
                     "rows": int(len(F))})
    return {"instrument": "the same frozen model on the same rows, with the marker permuted inside each trajectory",
            "arms": arms,
            "note": "a rewrite arm is not offered because recorded behaviour cannot be re-simulated without a model; "
                    "permuting within the trajectory also destroys any ordering fact the term encodes, which is "
                    "exactly what a structural marker is, so a coefficient that survives is one that does not come "
                    "from the position of the step alone"}


def e19_text_duplication(fr: dict) -> dict:
    """How many distinct commands stand behind a switch count or a repetition count."""
    d = fr["steps"]
    vc = d["command_sha"].value_counts()
    rep = d["command_sha"].map(vc)
    return {"steps_scanned": int(len(d)), "distinct_command_strings": int(vc.size),
            "share_of_steps_that_repeat_a_string_seen_elsewhere": round(float(1 - vc.size / max(1, len(d))), 4),
            "most_repeated_command_rows": int(vc.iloc[0]) if len(vc) else 0,
            "switch_share_among_the_most_repeated_20_commands": round(float(
                d[d["command_sha"].isin(vc.head(20).index)]["switched"].mean()), 4),
            "switch_share_among_all_other_steps": round(float(d[~d["command_sha"].isin(vc.head(20).index)]
                                                              ["switched"].mean()), 4),
            "newness_among_the_most_repeated_20_commands": round(float(
                d[d["command_sha"].isin(vc.head(20).index)]["new_information"].mean()), 4),
            "rule": "one digest per whitespace-normalised command string; a repeat is the same string in any "
                    "rollout, so a corpus-wide concentration in a handful of commands is visible here rather than "
                    "assumed away"}


def shared(fr: dict, quick: bool = False) -> dict:
    return {"e06_second_instrument": e06_second_instrument(fr),
            "e08_external": e08_external(fr),
            "e17_counterfactual": e17_counterfactual(fr),
            "e19_contamination": e19_text_duplication(fr)}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    B2.run_battery(EXP, "wave6_battery_0180", frames, SPEC, shared, quick="--quick" in sys.argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
