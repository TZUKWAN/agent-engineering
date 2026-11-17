"""Register wave 6 from its artefacts, so a status string is never typed by hand.

The wave-4 recorder supplies the registry call, the verdict string and the sampling sentences; only the artefact
names, the paper ids this wave owns and the gate reading are wave-6 specific. Wave 6's census carries each gate's
scope inside its own `gates` block rather than in a separate `gate_scopes`, so that is what the status line reads.

    python 02_shared_code/registry/record_wave6.py [--only EXP-0174]
"""
from __future__ import annotations

import argparse
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "02_shared_code" / "package_factory"))
import record_wave4 as R4                                                # noqa: E402
import topic_designs_wave6 as TD6                                       # noqa: E402

MATRIX_PAPERS = "P033;P034;P035;P036;P037;P038"
TOPICS = ";".join(TD6.RUNNABLE)


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

    if not want or "EXP-0172" in want:
        c = R4.load("results_raw/EXP0172_wave6_premise_census_*.json")
        m = c.get("measured") or {}
        R4.call("EXP-0172", MATRIX_PAPERS, TOPICS, "wave6_premise_census",
                "02_shared_code/package_factory/probe_wave6_premises.py",
                f"files drawn={len(m.get('files_read') or [])} of the release's parquet; "
                f"trajectories read={m.get('trajectories')}; seed {c.get('seed')}; structure and prevalence only, "
                f"no outcome is associated with anything",
                gate_status(c),
                "results_raw/EXP0172_wave6_premise_census_*.json", str(c.get("seed") or "42"),
                "the census that sets this wave's twelve gates; every one of them names the topic it scopes and the "
                "value it fired on, and the pass was run twice with identical output",
                "yes - the premise section of each package")

    if not want or "EXP-0173" in want:
        m = R4.load("results_raw/EXP0173_wave6_step_matrix_*.json")
        R4.call("EXP-0173", MATRIX_PAPERS, TOPICS, "wave6_step_matrix",
                "02_shared_code/package_factory/exp_wave6_features.py",
                f"traj_cap={m.get('sample_cap')}; seed={m.get('seed')}; one row per commanded assistant step; "
                f"n_steps={m.get('steps')} n_trajectories={m.get('trajectories')} "
                f"n_instances={m.get('instances')}",
                f"matrix_built_{m.get('steps')}_steps_in_{m.get('trajectories')}_rollouts_in_"
                f"{m.get('instances')}_instances__duplicate_rollout_rows_dropped_before_sampling_"
                f"{m.get('duplicate_rollout_rows_dropped_before_sampling')}__unparsed_family_steps_"
                f"{m.get('unparsed_family_steps')}__new_information_mean_{m.get('new_information_mean')}",
                "results_raw/EXP0173_wave6_step_matrix_*.json", str(m.get("seed") or "42"),
                "the shared substrate for all six designs: the command family of each step, whether it switched or "
                "repeated, how new its observation was, the scent of the text before it, and how the rollout ended",
                "yes - the sample, instrument and provenance tables of every wave-6 package")

    for tid, exp in TD6.EXP_OF.items():
        if want and exp not in want:
            continue
        key = exp[-4:]
        art = R4.load(f"results_raw/EXP{key}_wave6_design_{key}_*.json")
        R4.call(exp, TD6.DESIGNS[tid]["pkg"][:4], tid, "wave6_main",
                "02_shared_code/package_factory/exp_wave6_designs.py",
                f"seed={TD6.SEED}; clustered on {TD6.COMMON['sample']['cluster_unit']}; Holm over the design's three "
                f"declared hypotheses; bands .05/.15/.30; steps={art.get('n_steps')}; rollouts="
                f"{art.get('n_trajectories')}; instances={art.get('n_instances')}; the run's own argv is recorded in "
                f"the artefact",
                R4.verdicts(art) or "no_hypothesis_row_returned",
                f"results_raw/EXP{key}_wave6_design_{key}_*.json", str(TD6.SEED),
                "the pre-registered test for this topic; a cell a premise gate scoped out is reported as "
                "not_testable_* with its measured count, and a fit whose interval is not a number is reported as "
                "not_estimable_* rather than as a null",
                "yes - the whole result set")

    if not want or "EXP-0180" in want:
        b = R4.load("results_raw/EXP0180_wave6_battery_0180_*.json")
        sh = b.get("_shared") or {}
        e06 = (sh.get("e06_second_instrument") or {}).get("pairs") or []
        e17 = sh.get("e17_counterfactual") or {}
        e19 = sh.get("e19_contamination") or {}
        R4.call("EXP-0180", MATRIX_PAPERS, TOPICS,
                "e04_ablation_e06_second_instrument_e08_external_e12_scaling_e15_16_errors_"
                "e17_counterfactual_e18_replication_e19_contamination_e_by_config",
                "02_shared_code/package_factory/exp_wave6_battery.py",
                "spec 9 E-step battery on the wave-6 step frame; the step loop is imported from "
                "exp_wave2_battery.run_battery, so an ablation here is the same computation as in wave 2",
                f"battery_executed_for_{len([k for k in b if k in TD6.DESIGNS])}_topics__"
                f"e06_pairs_{len(e06)}__e17_arms_{len(e17.get('arms') or [])}__distinct_command_strings_"
                f"{e19.get('distinct_command_strings')}",
                "results_raw/EXP0180_wave6_battery_0180_*.json", str(TD6.SEED),
                "the E-step record for all six packages; the instrument pairs and the command-duplication audit are "
                "what license reading a switch rate or a repetition count as a property of the search rather than of "
                "a handful of boilerplate commands",
                "yes - the E-coverage table of every wave-6 package")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
