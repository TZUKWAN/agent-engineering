"""Register wave 11 from its artefacts, so a status string is never typed by hand.

Wave 11's census stopped no design but did fire two strata-scope gates, and the wave's own history includes a
substrate change made before any outcome was estimated (W11-D02) and two designs' worth of hypotheses that turned out
not to be estimable in the cell the release offers (W11-D05). All of that is read here from the artefacts, so the
registry states what was measured rather than what was intended.

    python 02_shared_code/registry/record_wave11.py [--only EXP-0209]
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
import topic_designs_wave11 as TD11                                # noqa: E402

MATRIX_PAPERS = "P062;P063;P064;P065;P066"
TOPICS = ";".join(TD11.RUNNABLE)


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

    if not want or "EXP-0207" in want:
        c = R4.load("results_raw/EXP0207_wave11_premise_census_*.json")
        m = c.get("measured") or {}
        R4.call("EXP-0207", MATRIX_PAPERS, TOPICS, "wave11_premise_census",
                "02_shared_code/package_factory/probe_wave11_premises.py",
                f"rollouts read={m.get('rollouts_drawn')} (duplicate rows dropped before sampling: "
                f"{c.get('duplicate_rollout_rows_dropped_before_sampling')} of {c.get('rows_in_files')}); "
                f"task instances={m.get('task_instances')}; instances with a second attempt="
                f"{m.get('instances_with_2plus_rollouts')}; seed {c.get('seed')}; the same 12-file draw as waves 6 "
                f"and 9, chosen over AgentTrove before any outcome estimate (deviation W11-D02)",
                gate_status(c),
                "results_raw/EXP0207_wave11_premise_census_*.json", str(c.get("seed") or "42"),
                "the census that sets this wave's twelve gates, run twice with byte-identical output; two fired at "
                "strata scope only (one scaffold agent, 2 of 805 repository prefixes with >= 200 rollouts), so the "
                "wave claims no cross-scaffold breadth, and the AgentTrove structure scan it superseded is kept as a "
                "separate artefact of the same experiment",
                "yes - the premise section of each package")

    if not want or "EXP-0208" in want:
        m = R4.load("results_raw/EXP0208_wave11_trace_matrix_*.json")
        xk = m.get("census_cross_check") or {}
        R4.call("EXP-0208", MATRIX_PAPERS, TOPICS, "wave11_trace_matrix",
                "02_shared_code/package_factory/exp_wave11_features.py",
                f"seed={m.get('seed')}; one row per rollout with assistant prose plus one row per consecutive "
                f"attempt pair of an instance; rollouts={m.get('rollouts_measured')}, pairs={m.get('attempt_pairs')},"
                f" instances with a second attempt={m.get('instances_with_2plus')}",
                f"matrix_built_{m.get('rollouts_measured')}_rollouts_and_{m.get('attempt_pairs')}_pairs__"
                + "__".join(f"census_agreement_{k}_{v[0]}_vs_{v[1]}" for k, v in sorted(xk.items())[:8]) +
                f"__submitted_share_{m.get('submitted_share')}__pairs_refinement_"
                f"{(m.get('pairs_by_class') or {}).get('refinement')}",
                "results_raw/EXP0208_wave11_trace_matrix_*.json", str(m.get("seed") or "42"),
                "the shared substrate for all five designs: each rollout's component categories, first-mention "
                "positions and survival under three compression budgets, each consecutive-attempt pair's carry-forward "
                "and relation class with a seeded alien arm, and the release's own labels - every aggregate the census "
                "shares reproduced or the build refuses to write",
                "yes - the sample, instrument and provenance tables of every wave-11 package")

    for tid, exp in TD11.EXP_OF.items():
        if want and exp not in want:
            continue
        key = exp[-4:]
        art = R4.load(f"results_raw/EXP{key}_wave11_design_{key}_*.json")
        R4.call(exp, TD11.DESIGNS[tid]["pkg"][:4], tid, "wave11_main",
                "02_shared_code/package_factory/exp_wave11_designs.py",
                f"seed={TD11.SEED}; clustered on {TD11.COMMON['sample']['cluster_unit']}; Holm over the design's "
                f"three declared hypotheses; bands .05/.15/.30; rollouts={art.get('n_rollouts')}; pairs="
                f"{art.get('n_pairs')}; clusters={art.get('n_clusters')}; the run's own argv is in the artefact",
                R4.verdicts(art) or "no_hypothesis_row_returned",
                f"results_raw/EXP{key}_wave11_design_{key}_*.json", str(TD11.SEED),
                "the pre-registered test for this topic; a term the cell cannot identify is reported as "
                "not_estimable_quasi_separation_in_this_cell with the raw fit withheld (W11-D05), and intervals are "
                "given only for the quantity they belong to (W11-D06)",
                "yes - the whole result set")

    if not want or "EXP-0214" in want:
        b = R4.load("results_raw/EXP0214_wave11_battery_0214_*.json")
        sh = b.get("_shared") or {}
        e06 = (sh.get("e06_second_instrument") or {}).get("pairs") or []
        e17 = sh.get("e17_counterfactual") or {}
        e19 = sh.get("e19_contamination") or {}
        R4.call("EXP-0214", MATRIX_PAPERS, TOPICS,
                "e04_ablation_e06_second_instrument_e08_external_e12_scaling_e15_16_errors_"
                "e17_counterfactual_e18_replication_e19_contamination_e_by_config",
                "02_shared_code/package_factory/exp_wave11_battery.py",
                "spec 9 E-step battery on the wave-11 rollout and pair frames; the step loop is imported from "
                "exp_wave2_battery.run_battery and the estimators down the wave 7 -> 9 -> 11 chain with this wave's "
                "cluster and control defaults re-bound",
                f"battery_executed_for_{len([k for k in b if k in TD11.EXP_OF])}_topics__e06_pairs_{len(e06)}__"
                f"e17_arms_{len(e17.get('arms') or [])}__distinct_prompts_{e19.get('distinct_task_prompts')}__"
                f"share_repeating_a_prompt_{e19.get('share_of_rollouts_sharing_a_prompt')}__"
                f"distinct_opening_prose_{e19.get('distinct_opening_assistant_messages')}",
                "results_raw/EXP0214_wave11_battery_0214_*.json", str(TD11.SEED),
                "the E-step record for all five packages; the author-transfer and the template-duplication audit are "
                "what license reading a component category as a property of agent prose rather than of the phrase "
                "list or of a handful of repeated task prompts and opening messages",
                "yes - the E-coverage table of every wave-11 package")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
