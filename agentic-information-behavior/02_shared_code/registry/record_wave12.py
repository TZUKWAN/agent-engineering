"""Register wave 12 from its artefacts, so a status string is never typed by hand.

Wave 11's census stopped no design but did fire two strata-scope gates, and the wave's own history includes a
substrate change made before any outcome was estimated (W11-D02) and two designs' worth of hypotheses that turned out
not to be estimable in the cell the release offers (W11-D05). All of that is read here from the artefacts, so the
registry states what was measured rather than what was intended.

    python 02_shared_code/registry/record_wave12.py [--only EXP-0216]
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
import topic_designs_wave12 as TD12                                # noqa: E402

MATRIX_PAPERS = "P067;P068;P069;P070"
TOPICS = ";".join(TD12.RUNNABLE)


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

    if not want or "EXP-0215" in want:
        c = R4.load("results_raw/EXP0215_wave12_premise_census_*.json")
        m = c.get("measured") or {}
        R4.call("EXP-0215", MATRIX_PAPERS, TOPICS, "wave12_premise_census",
                "02_shared_code/package_factory/probe_wave12_premises.py",
                f"rollouts read={m.get('rollouts_drawn')} (duplicate rows dropped before sampling: "
                f"{c.get('duplicate_rollout_rows_dropped_before_sampling')} of {c.get('rows_in_files')}); "
                f"task instances={m.get('task_instances')}; instances with a second attempt="
                f"{m.get('instances_with_2plus_rollouts')}; seed {c.get('seed')}; the same 12-file draw as waves 6 "
                f"and 9, chosen over AgentTrove before any outcome estimate (deviation W11-D02)",
                gate_status(c),
                "results_raw/EXP0215_wave12_premise_census_*.json", str(c.get("seed") or "42"),
                "the census that sets this wave's twelve gates, run twice with byte-identical output; two fired at "
                "strata scope only (one scaffold agent, 2 of 805 repository prefixes with >= 200 rollouts), so the "
                "wave claims no cross-scaffold breadth, and the AgentTrove structure scan it superseded is kept as a "
                "separate artefact of the same experiment",
                "yes - the premise section of each package")

    if not want or "EXP-0220" in want:
        m = R4.load("results_raw/EXP0220_wave12_action_matrix_*.json")
        xk = m.get("census_cross_check") or {}
        R4.call("EXP-0220", MATRIX_PAPERS, TOPICS, "wave12_action_matrix",
                "02_shared_code/package_factory/exp_wave12_features.py",
                f"seed={m.get('seed')}; one row per code-act turn ({m.get('codeact_turns')} turns in "
                f"{m.get('codeact_conversations')} conversations), one per MMAT thought transition "
                f"({m.get('mmat_transitions')} in {m.get('mmat_conversations')} conversations), one per SWE rollout "
                f"({m.get('swe_rollouts')}) with {m.get('swe_sibling_pairs')} sibling pairs, and the eight-corporus "
                f"inventory ({m.get('corpora_inventoried')} corpora)",
                f"matrix_built_{m.get('codeact_conversations')}_codeact_conversations_and_{m.get('mmat_transitions')}"
                f"_mmat_transitions_and_{m.get('swe_rollouts')}_swe_rollouts__"
                + "__".join(f"census_agreement_{k}_{v[0]}_vs_{v[1]}" for k, v in sorted(xk.items())) +
                f"__correction_cycles_block_level_{m.get('codeact_conversations_changed_after_error_block_level')}"
                f"_message_level_{m.get('codeact_conversations_changed_after_error_message_level')}",
                "results_raw/EXP0220_wave12_action_matrix_*.json", str(m.get("seed") or "42"),
                "the shared substrate for all four designs: each code-act turn typed as code, tool or natural language "
                "with its character count, content words and returned observation; each MMAT thought transition with "
                "its reflection markers, content-word overlap and operator; each SWE rollout with its step count, "
                "label, sibling pair and best neighbour similarity; and the corpus inventory - every aggregate the "
                "census shares reproduced, or the build refuses to write",
                "yes - the sample, instrument and provenance tables of every wave-12 package")

    for tid, exp in TD12.EXP_OF.items():
        if want and exp not in want:
            continue
        key = exp[-4:]
        art = R4.load(f"results_raw/EXP{key}_wave12_design_{key}_*.json")
        R4.call(exp, TD12.DESIGNS[tid]["pkg"][:4], tid, "wave12_main",
                "02_shared_code/package_factory/exp_wave12_designs.py",
                f"seed={TD12.SEED}; clustered on {TD12.COMMON['sample']['cluster_unit']}; Holm over the design's "
                f"three declared hypotheses; bands .05/.15/.30; rollouts={art.get('n_rollouts')}; pairs="
                f"{art.get('n_pairs')}; clusters={art.get('n_clusters')}; the run's own argv is in the artefact",
                R4.verdicts(art) or "no_hypothesis_row_returned",
                f"results_raw/EXP{key}_wave12_design_{key}_*.json", str(TD12.SEED),
                "the pre-registered test for this topic; a term the cell cannot identify is reported as "
                "not_estimable_quasi_separation_in_this_cell with the raw fit withheld (W11-D05), and intervals are "
                "given only for the quantity they belong to (W11-D06)",
                "yes - the whole result set")

    if not want or "EXP-0221" in want:
        b = R4.load("results_raw/EXP0221_wave12_battery_0221_*.json")
        sh = b.get("_shared") or {}
        e06 = (sh.get("e06_second_instrument") or {}).get("pairs") or []
        e17 = sh.get("e17_counterfactual") or {}
        e19 = sh.get("e19_contamination") or {}
        R4.call("EXP-0221", MATRIX_PAPERS, TOPICS,
                "e04_ablation_e06_second_instrument_e08_external_e12_scaling_e15_16_errors_"
                "e17_counterfactual_e18_replication_e19_contamination_e_by_config",
                "02_shared_code/package_factory/exp_wave12_battery.py",
                "spec 9 E-step battery on the wave-12 rollout and pair frames; the step loop is imported from "
                "exp_wave2_battery.run_battery and the estimators down the wave 7 -> 9 -> 11 chain with this wave's "
                "cluster and control defaults re-bound",
                f"battery_executed_for_{len([k for k in b if k in TD12.EXP_OF])}_topics__e06_pairs_{len(e06)}__"
                f"e17_arms_{len(e17.get('arms') or [])}__distinct_executed_blocks_"
                f"{e19.get('distinct_executed_blocks')}__share_repeating_a_block_"
                f"{e19.get('share_of_code_turns_repeating_a_block')}__distinct_opening_texts_"
                f"{e19.get('distinct_nl_openings')}",
                "results_raw/EXP0221_wave12_battery_0221_*.json", str(TD12.SEED),
                "the E-step record for all four packages; the author-transfer and the executed-block duplication "
                "audit are what license reading a density difference as a property of code versus prose rather than "
                "of one template block repeated across a corpus",
                "yes - the E-coverage table of every wave-12 package")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
