"""Register wave 8 from its artefacts, so a status string is never typed by hand.

Like the wave-6 and wave-7 recorders this reads only measured JSON. Wave 8 adds one thing worth saying out loud: two
of its five designs never ran, because their own premise gates stopped them, so the census row carries the fired gates
with the scope and value each sentence fixed, and the blocked topics themselves are recorded by
`record_blocked.py` - which writes the evidence row and the BLOCKED.md that keeps the audit from reading an empty
design directory as a package missing every deliverable.

    python 02_shared_code/registry/record_wave8.py [--only EXP-0192]
"""
from __future__ import annotations

import argparse
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "02_shared_code" / "package_factory"))
import record_wave4 as R4                                          # noqa: E402
import topic_designs_wave8 as TD8                                  # noqa: E402

MATRIX_PAPERS = "P045;P046;P047;P048;P049"
TOPICS = ";".join(TD8.RUNNABLE)


def gate_status(c: dict) -> str:
    """`no_gate_fired`, or each fired gate with the scope and the blocks its own frozen sentence names."""
    v = c.get("verdict") or {}
    fired = v.get("blocked_gates") or []
    if not fired:
        return "no_gate_fired"
    gates = c.get("gates") or {}
    parts = []
    for g in fired:
        r = gates.get(g) or {}
        parts.append(f"{g}[scope={r.get('scope', '?')}|measured={r.get('measured')}|"
                     f"blocks={';'.join(r.get('blocks') or [])}]" if r else str(g))
    return ("gates_fired__" + "__".join(parts)
            + "__stopped_designs_" + ("_".join(v.get("blocked_whole_design") or []) or "none")
            + f"__claim_limited_{len(v.get('claim_limited') or {})}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", action="append", default=[], help="register just these experiment ids")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    want = set(a.only)

    if not want or "EXP-0190" in want:
        c = R4.load("results_raw/EXP0190_wave8_premise_census_*.json")
        m = c.get("measured") or {}
        R4.call("EXP-0190", MATRIX_PAPERS, TOPICS, "wave8_premise_census",
                "02_shared_code/package_factory/probe_wave8_premises.py",
                f"trajectories read={m.get('trajectories')} after dropping "
                f"{c.get('duplicate_traj_ids_dropped_before_sampling')} duplicate rows; assistant turns="
                f"{m.get('assistant_turns_total')}; observations={m.get('observations_total')}; seed {c.get('seed')}; "
                f"structure and prevalence only, no outcome is associated with anything",
                gate_status(c),
                "results_raw/EXP0190_wave8_premise_census_*.json", str(c.get("seed") or "42"),
                "the census that sets this wave's thirteen gates; two of them (G5 terminal-turn identifiability at "
                "0.4649 against a 0.95 floor, G13 the absence of any task-outcome field) stopped T175 and T176 as "
                "whole designs, and the pass was run twice over the whole release with identical output",
                "yes - the premise section of each package")

    if not want or "EXP-0191" in want:
        m = R4.load("results_raw/EXP0191_wave8_turn_matrix_*.json")
        xk = m.get("census_cross_check") or {}
        R4.call("EXP-0191", MATRIX_PAPERS, TOPICS, "wave8_turn_matrix",
                "02_shared_code/package_factory/exp_wave8_features.py",
                f"seed={m.get('seed')}; one row per assistant turn of >= 20 characters, with the trajectory's own "
                f"history resolved per turn; turns={m.get('turns_measured')} of {m.get('turns_in_release')} in "
                f"release ({m.get('turns_dropped_below_20_chars')} below the floor); "
                f"trajectories={m.get('trajectories')}; observations={m.get('observations_total')}",
                f"matrix_built_{m.get('turns_measured')}_turns_in_{m.get('trajectories')}_trajectories__"
                + "__".join(f"census_agreement_{k}_{v[0]}_vs_{v[1]}" for k, v in sorted(xk.items())) +
                f"__mean_hypo_overlap_{m.get('mean_hypo_overlap')}__mean_obs_new_share_{m.get('mean_obs_new_share')}"
                f"__mean_repeat_share_{m.get('mean_repeat_share')}__mean_error_share_{m.get('mean_error_share')}",
                "results_raw/EXP0191_wave8_turn_matrix_*.json", str(m.get("seed") or "42"),
                "the shared substrate for all five designs: each turn's markers, its own trajectory's early "
                "hypothesis and its overlap with a seeded alien one, the newness and error state of the observation "
                "either side of it, how its call relates to the previous and to every earlier one, and the "
                "trajectory-level productivity quantities - cross-checked against EXP-0190 aggregate by aggregate",
                "yes - the sample, instrument and provenance tables of every wave-8 package")

    for tid, exp in TD8.EXP_OF.items():
        if want and exp not in want:
            continue
        key = exp[-4:]
        art = R4.load(f"results_raw/EXP{key}_wave8_design_{key}_*.json")
        R4.call(exp, TD8.DESIGNS[tid]["pkg"][:4], tid, "wave8_main",
                "02_shared_code/package_factory/exp_wave8_designs.py",
                f"seed={TD8.SEED}; clustered on {TD8.COMMON['sample']['cluster_unit']}; Holm over the design's three "
                f"declared hypotheses; bands .05/.15/.30; turns={art.get('n_turns')}; trajectories="
                f"{art.get('n_trajectories')}; clusters={art.get('n_clusters')}; the run's own argv is recorded in "
                f"the artefact",
                R4.verdicts(art) or "no_hypothesis_row_returned",
                f"results_raw/EXP{key}_wave8_design_{key}_*.json", str(TD8.SEED),
                "the pre-registered test for this topic; the release carries no task outcome, so every quality or "
                "failure quantity here is defined on the trajectory's own observable behaviour (deviation W8-D01), "
                "and a cell a premise gate scoped out is reported as not_testable_* with its measured count",
                "yes - the whole result set")

    if not want or "EXP-0195" in want:
        b = R4.load("results_raw/EXP0195_wave8_battery_0195_*.json")
        sh = b.get("_shared") or {}
        e06 = (sh.get("e06_second_instrument") or {}).get("pairs") or []
        e17 = sh.get("e17_counterfactual") or {}
        e19 = sh.get("e19_contamination") or {}
        R4.call("EXP-0195", MATRIX_PAPERS, TOPICS,
                "e04_ablation_e06_second_instrument_e08_external_e12_scaling_e15_16_errors_"
                "e17_counterfactual_e18_replication_e19_contamination_e_by_config",
                "02_shared_code/package_factory/exp_wave8_battery.py",
                "spec 9 E-step battery on the wave-8 turn frame; the step loop is imported from "
                "exp_wave2_battery.run_battery and the estimators from wave 7, so an ablation here is the same "
                "computation as in wave 2 and a coefficient the same arithmetic",
                f"battery_executed_for_{len([k for k in b if k in TD8.EXP_OF])}_topics_of_five_"
                f"two_blocked_at_premise__e06_pairs_{len(e06)}__e17_arms_{len(e17.get('arms') or [])}__"
                f"distinct_tasks_{e19.get('distinct_task_instructions')}__distinct_call_strings_"
                f"{e19.get('distinct_call_strings_across_the_release')}__observations_seen_elsewhere_"
                f"{e19.get('share_of_observations_seen_elsewhere')}",
                "results_raw/EXP0195_wave8_battery_0195_*.json", str(TD8.SEED),
                "the E-step record for all five packages; the author-transfer and the duplication audit are what "
                "license reading a marker prevalence as a property of agent prose rather than of the phrase list, and "
                "of a handful of repeated tasks and reused observations",
                "yes - the E-coverage table of every wave-8 package")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
