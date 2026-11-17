"""Register wave 10 from its artefacts, so a status string is never typed by hand.

Wave 10 is the first wave where most of the screened designs never ran, so the census row carries the fired gate with
the value that fired it, `record_blocked.py` (run before this by `_w10_finish.py`) files the five blocked designs
with their measurements, and the two rows that were measured - the frame and T104 - are read from their artefacts.

    python 02_shared_code/registry/record_wave10.py [--only EXP-0204]
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
import topic_designs_wave10 as TD10                                # noqa: E402

MATRIX_PAPERS = "P056;P057;P058;P059;P060;P061"
TOPICS = ";".join(TD10.RUNNABLE)


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

    if not want or "EXP-0203" in want:
        c = R4.load("results_raw/EXP0203_wave10_premise_census_*.json")
        m = c.get("measured") or {}
        R4.call("EXP-0203", MATRIX_PAPERS, TOPICS, "wave10_premise_census",
                "02_shared_code/package_factory/probe_wave10_premises.py",
                f"dev rows read={m.get('rows')}; candidate slots={m.get('candidates_total')}; mean candidates="
                f"{m.get('mean_candidates')}; seed {c.get('seed')}; structure and prevalence only, no outcome is "
                f"associated with anything",
                gate_status(c),
                "results_raw/EXP0203_wave10_premise_census_*.json", str(c.get("seed") or "42"),
                "the census that sets this wave's twelve gates; G2's comparable-candidate-set rule fired at 0.8376 "
                "against 0.90 and stopped five of the six screened designs, which is recorded as a property of the "
                "substrate (deviation W10-D01), and the pass ran twice with byte-identical output",
                "yes - the premise section of each package")

    if not want or "EXP-0205" in want:
        m = R4.load("results_raw/EXP0205_wave10_requirement_matrix_*.json")
        xk = m.get("census_cross_check") or {}
        R4.call("EXP-0205", MATRIX_PAPERS, TOPICS, "wave10_requirement_matrix",
                "02_shared_code/package_factory/exp_wave10_features.py",
                f"seed={m.get('seed')}; one row per dev instruction: its extracted requirement clauses, both coverage "
                f"readings, wave 1's uncertainty indices and the frozen ranker's columns; instructions="
                f"{m.get('rows')}, with at least one requirement={m.get('rows_with_any_requirement')}",
                f"matrix_built_{m.get('rows')}_instructions__rows_with_requirements_{m.get('rows_with_any_requirement')}"
                f"__mean_requirements_{m.get('mean_requirements')}__mean_coverage_any_{m.get('mean_coverage_any')}"
                f"__mean_coverage_half_{m.get('mean_coverage_half')}__"
                + "__".join(f"census_agreement_{k}_{v[0]}_vs_{v[1]}" for k, v in sorted(xk.items())),
                "results_raw/EXP0205_wave10_requirement_matrix_*.json", str(m.get("seed") or "42"),
                "the shared substrate for the wave: what an instruction asks for as extracted clauses, how much of it "
                "the surfaced catalogue covers under a loose and a strict reading, and the ambiguity instruments the "
                "census measured - cross-checked aggregate by aggregate against EXP-0203 before anything was written",
                "yes - the sample, instrument and provenance tables of every wave-10 package")

    for tid, exp in TD10.EXP_OF.items():
        if want and exp not in want:
            continue
        key = exp[-4:]
        art = R4.load(f"results_raw/EXP{key}_wave10_design_{key}_*.json")
        R4.call(exp, TD10.DESIGNS[tid]["pkg"][:4], tid, "wave10_main",
                "02_shared_code/package_factory/exp_wave10_designs.py",
                f"seed={TD10.SEED}; clustered on {TD10.COMMON['sample']['cluster_unit']}; Holm over the design's "
                f"three declared hypotheses; bands .05/.15/.30; instructions={art.get('n_rows')}; clusters="
                f"{art.get('n_clusters')}; rows without a requirement={art.get('rows_without_a_requirement')}; "
                f"single-candidate rows={art.get('single_candidate_rows')}; the run's own argv is in the artefact",
                R4.verdicts(art) or "no_hypothesis_row_returned",
                f"results_raw/EXP{key}_wave10_design_{key}_*.json", str(TD10.SEED),
                "the pre-registered test for this topic; the outcome is a frozen lexical ranker's, not an agent's "
                "choice (W7-D02 applies to this substrate too), and both coverage readings are reported so the "
                "definitional choice is visible",
                "yes - the whole result set")

    if not want or "EXP-0206" in want:
        b = R4.load("results_raw/EXP0206_wave10_battery_0206_*.json")
        sh = b.get("_shared") or {}
        e06 = (sh.get("e06_second_instrument") or {}).get("pairs") or []
        e17 = sh.get("e17_counterfactual") or {}
        e19 = sh.get("e19_contamination") or {}
        R4.call("EXP-0206", MATRIX_PAPERS, TOPICS,
                "e04_ablation_e06_second_instrument_e08_external_e12_scaling_e15_16_errors_"
                "e17_counterfactual_e18_replication_e19_contamination_e_by_config",
                "02_shared_code/package_factory/exp_wave10_battery.py",
                "spec 9 E-step battery on the wave-10 requirement frame; the step loop is imported from "
                "exp_wave2_battery.run_battery and the estimators through waves 7 to 9 with this wave's defaults",
                f"battery_executed_for_{len([k for k in b if k in TD10.EXP_OF])}_topic_of_six_five_blocked_at_premise"
                f"__e06_pairs_{len(e06)}__e17_arms_{len(e17.get('arms') or [])}__distinct_instructions_"
                f"{e19.get('distinct_instruction_strings')}__prompt_groups_{e19.get('prompt_groups')}__"
                f"max_rows_per_prompt_group_{e19.get('max_rows_per_prompt_group')}__in_all_three_configs_"
                f"{e19.get('prompt_groups_seen_in_all_three_configs')}",
                "results_raw/EXP0206_wave10_battery_0206_*.json", str(TD10.SEED),
                "the E-step record for the wave's one measured package; the coverage-instrument invariance pair and "
                "the instruction-duplication audit are what license reading a coverage share as a property of the "
                "instruction and the catalogue rather than of the clause-extraction rule or the release's repeated "
                "prompt groups",
                "yes - the E-coverage table of every wave-10 package")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
