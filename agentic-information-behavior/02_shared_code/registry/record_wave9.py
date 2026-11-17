"""Register wave 9 from its artefacts, so a status string is never typed by hand.

The wave-7 and wave-8 recorder pattern, with the one thing wave 9 adds: two of its designs never ran, so the census
row carries the gates that stopped them and `record_blocked.py` (run before this, by `_w9_finish.py`) has already
written the blocked rows and their BLOCKED.md files.

    python 02_shared_code/registry/record_wave9.py [--only EXP-0198]
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
import topic_designs_wave9 as TD9                                  # noqa: E402

MATRIX_PAPERS = "P050;P051;P052;P053;P054;P055"
TOPICS = ";".join(TD9.RUNNABLE)


def gate_status(c: dict) -> str:
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

    if not want or "EXP-0196" in want:
        c = R4.load("results_raw/EXP0196_wave9_premise_census_*.json")
        m = c.get("measured") or {}
        R4.call("EXP-0196", MATRIX_PAPERS, TOPICS, "wave9_premise_census",
                "02_shared_code/package_factory/probe_wave9_premises.py",
                f"rollouts read={m.get('trajectories')} after dropping "
                f"{c.get('duplicate_rollout_rows_dropped_before_sampling')} duplicate rows from "
                f"{c.get('rows_in_files')} rows in {len(c.get('files_read') or [])} files; commanded steps="
                f"{m.get('steps_total')}; instances={m.get('instances')}; seed {c.get('seed')}; structure and "
                f"prevalence only, no outcome is associated with anything",
                gate_status(c),
                "results_raw/EXP0196_wave9_premise_census_*.json", str(c.get("seed") or "42"),
                "the census that sets this wave's twelve gates and the outcome sparsity (560 Submitted of 19,988); "
                "G9's newness-availability rule stopped T151 and T156 as whole designs and G6's family-breadth rule "
                "limits T153's H1, each with its measured value cited, and the pass ran twice with identical output",
                "yes - the premise section of each package")

    if not want or "EXP-0197" in want:
        m = R4.load("results_raw/EXP0197_wave9_step_matrix_*.json")
        xk = m.get("census_cross_check") or {}
        R4.call("EXP-0197", MATRIX_PAPERS, TOPICS, "wave9_step_matrix",
                "02_shared_code/package_factory/exp_wave9_features.py",
                f"seed={m.get('seed')}; one row per commanded assistant step plus one row per rollout; "
                f"steps={m.get('steps_measured')} in {m.get('rollouts_measured')} rollouts over "
                f"{m.get('instances')} instances; median steps={m.get('median_steps')}",
                f"matrix_built_{m.get('steps_measured')}_steps_in_{m.get('rollouts_measured')}_rollouts_in_"
                f"{m.get('instances')}_instances__" + "__".join(f"census_agreement_{k}_{v[0]}_vs_{v[1]}"
                                                                for k, v in sorted(xk.items())) +
                f"__submitted_share_{m.get('submitted_share')}__mean_switch_rate_{m.get('mean_switch_rate')}"
                f"__mean_newness_{m.get('mean_newness')}__steps_without_observation_share_"
                f"{m.get('steps_without_observation_share')}",
                "results_raw/EXP0197_wave9_step_matrix_*.json", str(m.get("seed") or "42"),
                "the shared substrate for all four measured designs: each step's family, switch, newness and failure "
                "state, its phase (first or last fifth), its relation to the command that preceded it and to the "
                "first failure's lag, and the rollout's own outcome and cost - cross-checked aggregate by aggregate "
                "against EXP-0196 before anything is written",
                "yes - the sample, instrument and provenance tables of every wave-9 package")

    for tid, exp in TD9.EXP_OF.items():
        if want and exp not in want:
            continue
        key = exp[-4:]
        art = R4.load(f"results_raw/EXP{key}_wave9_design_{key}_*.json")
        R4.call(exp, TD9.DESIGNS[tid]["pkg"][:4], tid, "wave9_main",
                "02_shared_code/package_factory/exp_wave9_designs.py",
                f"seed={TD9.SEED}; clustered on {TD9.COMMON['sample']['cluster_unit']}; Holm over the design's three "
                f"declared hypotheses; bands .05/.15/.30; rollouts={art.get('n_rollouts')}; steps="
                f"{art.get('n_steps')}; clusters={art.get('n_clusters')}; the run's own argv is recorded in the "
                f"artefact",
                R4.verdicts(art) or "no_hypothesis_row_returned",
                f"results_raw/EXP{key}_wave9_design_{key}_*.json", str(TD9.SEED),
                "the pre-registered test for this topic; a hypothesis its own premise gate limited is reported as "
                "not_testable_* with the measured value, a quantity the freeze asks to be reported rather than tested "
                "keeps its own verdict label, and the release's 15-step truncation and 2.8% completion rate are "
                "printed inside the affected rows (deviations W9-D03, W9-D05 and W9-D06)",
                "yes - the whole result set")

    if not want or "EXP-0202" in want:
        b = R4.load("results_raw/EXP0202_wave9_battery_0202_*.json")
        sh = b.get("_shared") or {}
        e06 = (sh.get("e06_second_instrument") or {}).get("pairs") or []
        e17 = sh.get("e17_counterfactual") or {}
        e19 = sh.get("e19_contamination") or {}
        R4.call("EXP-0202", MATRIX_PAPERS, TOPICS,
                "e04_ablation_e06_second_instrument_e08_external_e12_scaling_e15_16_errors_"
                "e17_counterfactual_e18_replication_e19_contamination_e_by_config",
                "02_shared_code/package_factory/exp_wave9_battery.py",
                "spec 9 E-step battery on the wave-9 step and rollout frames; the step loop is imported from "
                "exp_wave2_battery.run_battery and the estimators from waves 7 and 8 with this wave's defaults "
                "re-bound, so an ablation here is the same computation as in wave 2",
                f"battery_executed_for_{len([k for k in b if k in TD9.EXP_OF])}_topics_of_six_two_blocked_at_premise__"
                f"e06_pairs_{len(e06)}__e17_arms_{len(e17.get('arms') or [])}__distinct_command_strings_"
                f"{e19.get('distinct_command_strings')}__most_repeated_command_rows_"
                f"{e19.get('most_repeated_command_rows')}__share_in_the_twenty_most_repeated_"
                f"{e19.get('share_of_steps_in_the_twenty_most_repeated_commands')}",
                "results_raw/EXP0202_wave9_battery_0202_*.json", str(TD9.SEED),
                "the E-step record for all four measured packages; the command-duplication audit and the "
                "tool-call-corpus transfer are what license reading a transition grammar as a property of this "
                "release's shell alphabet rather than of agent behaviour in general",
                "yes - the E-coverage table of every wave-9 package")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
