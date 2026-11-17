"""EXP-0196: the wave-9 premise census - can the step corpora carry six designs about structure, transitions and value?

The substrate is the same 12-file draw, the same seeded trajectory sample, the same command parser and the same
family classifier that waves 6 measured on: 292,992 commanded assistant steps in 19,988 rollouts over 1,784 task
instances, this time **with** the two things hermes turned out not to have - a per-rollout outcome
(`exit_status`, plus the release's own `Submitted` label) and a per-rollout cost (`duration_sec`).

Wave 9's six designs ask for six different things, so the census measures six prevalences and each gate names the
topic it stops:

* T151 wants a behaviour taxonomy, which needs enough command families to be a taxonomy rather than a split of two;
* T153 wants a cross-task grammar, which needs both enough task families and enough recurring family bigrams;
* T156 wants an exploration-to-exploitation transition, which needs trajectories long enough to have a second half
  and switchy enough for a curve to exist;
* T178 wants to predict the final outcome from the first fifth of a rollout, which needs a real outcome label and
  rollouts with a fifth that contains more than one step;
* T179 wants a recovery window, which needs a failed observation followed by a further command;
* T193 wants to say which rollouts deserve reuse, which needs repeated rollouts of one instance so a selection rule
  can be compared against what actually happened.

Every rule, threshold and scope below was written before a row was opened, and the pass reports structure and
prevalence only - no design's dependent variable is associated with anything here.

    python 02_shared_code/package_factory/probe_wave9_premises.py [--traj-cap 400]
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np                                                # noqa: E402
import pandas as pd                                               # noqa: E402
import wave_lib as W                                              # noqa: E402
import exp_wave6_features as EF6                                  # noqa: E402  the same reader, the same sample
import probe_wave6_premises as P6                                 # noqa: E402  the same families and markers

EXP = "EXP-0196"
SEED = 42
CAP = int(__import__("topic_designs_wave6").COMMON["sample"]["traj_cap"])


def selftest() -> int:
    """The census's own counts proven on a hand-built rollout before any release row is read."""
    fence = "```bash\n"
    traj = {"instance_id": "i1", "exit_status": "resolved", "duration_sec": 90.0,
            "messages": [
                {"role": "user", "content": "fix the parser in repo/x.py"},
                {"role": "assistant", "content": "look at it\n" + fence + "cat x.py\n```"},
                {"role": "user", "content": "Output: no such file x.py"},
                {"role": "assistant", "content": "try the right path\n" + fence + "ls -la\n```"},
                {"role": "user", "content": "Output: total 3\nx.py"},
                {"role": "assistant", "content": "search it\n" + fence + "grep -n parser x.py\n```"},
                {"role": "user", "content": "Output: def f(): pass"},
                {"role": "assistant", "content": "Submitted"}]}
    rows = EF6.step_rows(traj, "t1")
    assert len(rows) >= 3, len(rows)
    fams = [r["family"] for r in rows]
    assert len(set(fams)) >= 2 and any(r["failed_observation"] for r in rows), fams
    # `switched` and `continues` are derived, not stored: the step spine keeps the family and the index, and this
    # census decides what a switch and a following step are, so the derivation is tested here rather than assumed
    assert sum(1 for a, b in zip(fams, fams[1:]) if a != b) >= 1
    assert any(r["failed_observation"] and r["step_index"] < len(rows) for r in rows)
    assert all(r["new_information"] == r["new_information"] for r in rows)
    print("SELFTEST OK: the step spine, its families, its failure marker and its switches all land on a built rollout")
    return 0


def measure(drawn: list) -> dict:
    n_traj = len(drawn)
    parsed = with_outcome = 0
    steps_total = steps_with_newness = 0
    long10 = switchy = post_fail = 0
    dur_present = 0
    inst_rollouts = collections.Counter()
    fam_steps = collections.Counter()
    task_trajs = collections.Counter()
    bigrams = collections.Counter()
    outcome_counts = collections.Counter()
    steps_per_traj, switches_per_traj = [], []
    for k, t in enumerate(drawn):
        key = f"{t.get('instance_id')}|{k}"
        rows = EF6.step_rows(t, key)
        if not rows:
            continue
        parsed += 1
        ex = str(t.get("exit_status") or "")
        if ex and ex.lower() not in ("none", "nan", "unknown"):
            with_outcome += 1
        outcome_counts[ex or "empty"] += 1
        inst_rollouts[str(t.get("instance_id"))] += 1
        if t.get("duration_sec") is not None:
            dur_present += 1
        steps_total += len(rows)
        steps_with_newness += sum(1 for r in rows if r["new_information"] == r["new_information"])
        fams = [r["family"] for r in rows]
        fam_steps.update(fams)
        task_trajs[str(t.get("repo") or "").split("/")[0]] += 1
        bigrams.update(zip(fams, fams[1:]))
        nsw = sum(1 for a, b in zip(fams, fams[1:]) if a != b)
        switches_per_traj.append(nsw)
        steps_per_traj.append(len(rows))
        long10 += int(len(rows) >= 10)
        switchy += int(nsw >= 2)
        post_fail += int(any(r["failed_observation"] and r["step_index"] < len(rows) for r in rows))
    cats = {str(k): int(v) for k, v in fam_steps.items() if v >= 500}
    tasks = {str(k): int(v) for k, v in task_trajs.items() if v >= 200}
    bg = {str(k): int(v) for k, v in bigrams.items() if v >= 100}
    multi = int(sum(1 for v in inst_rollouts.values() if v >= 2))
    return {"corpus": "the same 12 files of SWE-ZERO / AgentTrove step rollouts wave 6 drew",
            "trajectories": n_traj, "trajectories_parsed": parsed,
            "trajectory_parse_share": round(parsed / max(1, n_traj), 4),
            "outcome_label_share": round(with_outcome / max(1, parsed), 4),
            "outcome_values": {k: int(v) for k, v in outcome_counts.most_common(8)},
            "steps_total": steps_total, "mean_steps": round(float(np.mean(steps_per_traj)), 2) if steps_per_traj else None,
            "median_steps": float(np.median(steps_per_traj)) if steps_per_traj else None,
            "newness_available_share": round(steps_with_newness / max(1, steps_total), 4),
            "trajectories_with_10plus_steps": long10,
            "trajectories_with_2plus_switches": switchy,
            "trajectories_with_a_failure_then_a_further_command": post_fail,
            "duration_present_share": round(dur_present / max(1, parsed), 4),
            "instances": int(len(inst_rollouts)), "instances_with_2plus_rollouts": multi,
            "distinct_command_families": int(len(fam_steps)),
            "families_with_500plus_steps": len(cats), "family_step_counts": cats,
            "distinct_task_prefixes": int(len(task_trajs)), "task_prefixes_with_200plus_trajectories": len(tasks),
            "distinct_family_bigrams": int(len(bigrams)),
            "bigrams_with_100plus_occurrences": int(len(bg)),
            "mean_switches_per_trajectory": round(float(np.mean(switches_per_traj)), 2) if switches_per_traj else None,
            "successful_trajectories": int(sum(v for k, v in outcome_counts.items()
                                               if any(s in k.lower() for s in ("resolve", "success", "fixed", "true")))),
            "failed_trajectories": int(sum(v for k, v in outcome_counts.items()
                                           if any(s in k.lower() for s in ("fail", "unresolved", "false", "error"))))}


GATES = {   # rule, threshold, and the topic(s) the sentence scopes - all frozen before any row was opened
 "G1_rollouts_parseable": {
     "rule": ">= 0.95 of drawn rollouts yield at least one commanded step", "threshold": 0.95, "scope": "design",
     "blocks": ["T151", "T153", "T156", "T178", "T179", "T193"]},
 "G2_outcome_label_present": {
     "rule": ">= 0.95 of rollouts carry a non-empty exit_status, which is the only final-outcome label this release "
             "has and three designs condition on it", "threshold": 0.95, "scope": "design",
     "blocks": ["T156", "T178", "T193"]},
 "G3_command_families_for_a_taxonomy": {
     "rule": ">= 12 command families with >= 500 steps each, below which a taxonomy of agent information behaviour "
             "would be a split of two bins", "threshold": 12, "scope": "H1", "blocks": ["T151"]},
 "G4_rollouts_long_enough_for_a_first_fifth": {
     "rule": ">= 1,000 rollouts have >= 10 commanded steps, so a first-fifth feature is more than one step",
     "threshold": 1000, "scope": "H1", "blocks": ["T178"]},
 "G5_failure_then_a_further_command": {
     "rule": ">= 500 rollouts contain a failed observation followed by another command - the window T179 measures",
     "threshold": 500, "scope": "H1", "blocks": ["T179"]},
 "G6_task_families_for_a_cross_task_grammar": {
     "rule": ">= 10 task families with >= 200 rollouts each, which is the minimum for comparing a grammar across "
             "tasks rather than within one", "threshold": 10, "scope": "H1", "blocks": ["T153"]},
 "G7_trajectories_with_switches": {
     "rule": ">= 1,000 rollouts make >= 2 family switches, so a transition curve has variation to fit",
     "threshold": 1000, "scope": "H1", "blocks": ["T156"]},
 "G8_instances_with_repeated_rollouts": {
     "rule": ">= 300 task instances attempted more than once, the comparison T193 needs to ask which rollout "
             "deserved reuse", "threshold": 300, "scope": "H1", "blocks": ["T193"]},
 "G9_newness_available": {
     "rule": ">= 0.90 of steps have an observation whose new-word share is computable", "threshold": 0.90,
     "scope": "design", "blocks": ["T151", "T156"]},
 "G10_duration_available": {
     "rule": ">= 0.90 of rollouts carry a duration, the cost axis of T179's window and T193's value trade-off",
     "threshold": 0.90, "scope": "H2", "blocks": ["T193"]},
 "G11_cluster_count": {
     "rule": ">= 500 task instances, so an instance-clustered interval exists for every design in the wave",
     "threshold": 500, "scope": "design", "blocks": ["T151", "T153", "T156", "T178", "T179", "T193"]},
 "G12_bigram_support": {
     "rule": ">= 50 family bigrams occurring >= 100 times, the support a transition matrix has to be estimated on",
     "threshold": 50, "scope": "H2", "blocks": ["T153"]},
}


def apply_gates(m: dict) -> dict:
    checks = {"G1_rollouts_parseable": m["trajectory_parse_share"],
              "G2_outcome_label_present": m["outcome_label_share"],
              "G3_command_families_for_a_taxonomy": m["families_with_500plus_steps"],
              "G4_rollouts_long_enough_for_a_first_fifth": m["trajectories_with_10plus_steps"],
              "G5_failure_then_a_further_command": m["trajectories_with_a_failure_then_a_further_command"],
              "G6_task_families_for_a_cross_task_grammar": m["task_prefixes_with_200plus_trajectories"],
              "G7_trajectories_with_switches": m["trajectories_with_2plus_switches"],
              "G8_instances_with_repeated_rollouts": m["instances_with_2plus_rollouts"],
              "G9_newness_available": m["newness_available_share"],
              "G10_duration_available": m["duration_present_share"],
              "G11_cluster_count": m["instances"], "G12_bigram_support": m["bigrams_with_100plus_occurrences"]}
    out = {}
    for k, g in GATES.items():
        v = checks[k]
        out[k] = {"measured": v, "fires": bool(v < g["threshold"]), "threshold": g["threshold"],
                  "scope": g["scope"], "blocks": list(g["blocks"]), "rule": g["rule"]}
    fired = [k for k, v in out.items() if v["fires"]]
    whole = sorted({t for k in fired if out[k]["scope"] == "design" for t in out[k]["blocks"]})
    limited = {k: out[k]["scope"] for k in fired if out[k]["scope"] != "design"}
    return {"gates": out, "verdict": {"blocked_gates": fired, "blocked_whole_design": whole,
                                      "claim_limited": limited}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--traj-cap", type=int, default=0, help="draw at most this many rollouts (0 = the wave's frozen "
                                                            "sample, which is what the gates were written against)")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    selftest()
    drawn, picks, rows_in_files, dupes = EF6.load_trajectories(a.traj_cap or CAP)
    m = measure(drawn)
    g = apply_gates(m)
    art = {"exp_id": EXP, "seed": SEED, "files_read": picks, "rows_in_files": rows_in_files,
           "duplicate_rollout_rows_dropped_before_sampling": dupes,
           "rows_requested": a.traj_cap or f"the frozen cap of {CAP} rollouts", "measured": m,
           "gate_rules": {k: v["rule"] for k, v in GATES.items()}, **g,
           "cluster_unit": "instance_id", "started_at": W.now(),
           "wallclock_sec": round(time.time() - t0, 1), "invocation": " ".join([sys.executable] + sys.argv),
           "run_cost": W.run_cost_row(EXP, t0, len(drawn), 0, "wave-9 premise census")}
    dest = W.write_raw(EXP, "wave9_premise_census", art)
    print(json.dumps({"measured": m, "verdict": art["verdict"],
                      "gates": {k: [v["measured"], v["fires"]] for k, v in art["gates"].items()}},
                     indent=1, ensure_ascii=False, default=str)[:2600])
    print("\nwrote", dest.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
