"""Register wave 5 from its artefacts, so a status string is never typed by hand.

The wave-4 recorder already composes verdict strings, gate scopes and the registry call; this module reuses those
functions rather than restating them, and supplies only what is wave-5 specific: the artefact names, the paper ids the
wave owns and the sentences that say what each step measured.

    python 02_shared_code/registry/record_wave5.py [--only EXP-0165]
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
import topic_designs_wave5 as TD5                                        # noqa: E402

MATRIX_PAPERS = "P027;P028;P029;P030;P031;P032"
TOPICS = ";".join(TD5.RUNNABLE)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", action="append", default=[], help="register just these experiment ids")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    want = set(a.only)

    if not want or "EXP-0161" in want:
        c = R4.load("results_raw/EXP0161_wave5_premise_census_*.json")
        R4.call("EXP-0161", MATRIX_PAPERS, TOPICS + ";" + ";".join(sorted(set(
            sum([(g.get("blocks") or []) for g in (c.get("gate_scopes") or {}).values()], [])))),
            "wave5_premise_census",
            "02_shared_code/package_factory/probe_wave5_premises.py",
            f"trajectories sampled={c.get('sampled_rows')}; seed {c.get('seed')}; structure, marker prevalence and "
            f"joint turn-to-action cells only, no outcome read",
            R4.gate_status(c),
            "results_raw/EXP0161_wave5_premise_census_*.json", str(c.get("seed") or "42"),
            "the census that sets this wave's eleven gates; each fired gate is recorded with the scope its own "
            "frozen sentence gives it, so a limited claim is not read as a stopped design",
            "yes - the premise section of each package")

    if not want or "EXP-0164" in want:
        m = R4.load("results_raw/EXP0164_wave5_step_matrix_*.json")
        R4.call("EXP-0164", MATRIX_PAPERS, TOPICS, "wave5_step_matrix",
                "02_shared_code/package_factory/exp_wave5_features.py",
                f"traj_cap={m.get('sample_cap')}; seed={m.get('seed')}; wave 4's spine joined to the language "
                f"columns, one row per assistant turn; n_turns={m.get('assistant_turns')} "
                f"n_trajectories={m.get('trajectories')}",
                f"matrix_built_{m.get('assistant_turns')}_turns_in_{m.get('trajectories')}_trajectories__"
                f"calls_unparseable_{m.get('calls_unparseable')}__act_any_share_{m.get('act_any_share')}__"
                f"duplicate_traj_ids_dropped_before_sampling_"
                f"{m.get('duplicate_traj_ids_dropped_before_sampling')}",
                "results_raw/EXP0164_wave5_step_matrix_*.json", str(m.get("seed") or "42"),
                "the shared substrate for all six designs: two lexicons per act, connective families, the "
                "content-word overlap with prior observations, the repair families and the plan-to-call alignment "
                "with its leave-one-trajectory-out null",
                "yes - the sample, instrument and provenance tables of every wave-5 package")

    for tid, exp in TD5.EXP_OF.items():
        if want and exp not in want:
            continue
        key = exp[-4:]
        art = R4.load(f"results_raw/EXP{key}_wave5_design_{key}_*.json")
        R4.call(exp, TD5.DESIGNS[tid]["pkg"][:4], tid, "wave5_main",
                "02_shared_code/package_factory/exp_wave5_designs.py",
                f"seed={TD5.SEED}; clustered on {TD5.SAMPLE['cluster_unit']}; Holm over the design's three declared "
                f"hypotheses; bands .05/.15/.30; turns={art.get('n_turns')}; trajectories="
                f"{art.get('n_trajectories')}; the run's own argv is recorded in the artefact",
                R4.verdicts(art) or "no_hypothesis_row_returned",
                f"results_raw/EXP{key}_wave5_design_{key}_*.json", str(TD5.SEED),
                "the pre-registered test for this topic; a cell a premise gate scoped out is reported as "
                "not_testable_* with its measured count rather than by moving the floor",
                "yes - the whole result set")

    if not want or "EXP-0171" in want:
        b = R4.load("results_raw/EXP0171_wave5_battery_0171_*.json")
        sh = b.get("_shared") or {}
        e06 = (sh.get("e06_second_instrument") or {}).get("pairs") or []
        e17 = sh.get("e17_counterfactual") or {}
        e19 = sh.get("e19_contamination") or {}
        R4.call("EXP-0171", MATRIX_PAPERS, TOPICS,
                "e04_ablation_e06_second_instrument_e08_external_e12_scaling_e15_16_errors_"
                "e17_counterfactual_e18_replication_e19_contamination_e_by_config",
                "02_shared_code/package_factory/exp_wave5_battery.py",
                "spec 9 E-step battery on the wave-5 step frame; the step loop is imported from "
                "exp_wave2_battery.run_battery, so an ablation here is the same computation as in wave 2",
                f"battery_executed_for_{len([k for k in b if k in TD5.DESIGNS])}_topics__"
                f"e06_pairs_{len(e06)}__e17_arms_{len(e17.get('arms') or [])}__"
                f"turn_text_repeat_share_{e19.get('share_of_turns_that_are_a_repeat')}",
                "results_raw/EXP0171_wave5_battery_0171_*.json", str(TD5.SEED),
                "the E-step record for all six packages; the instrument-agreement pairs and the text-duplication "
                "audit are what license reading a marker prevalence as language rather than as one rule set's "
                "vocabulary counted back",
                "yes - the E-coverage table of every wave-5 package")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
