"""Register wave 7 from its artefacts, so a status string is never typed by hand.

Like the wave-6 recorder this reads only measured JSON: the census, the frame, the six designs and the battery. Two
things are wave-7 specific and are said where they occur: the frame cross-checks five of its own aggregates against
EXP-0181 and prints the pairs, so the recorder carries that verdict rather than a prose claim; and one premise gate
(G8) fired, which is a result the status line has to name with the scope and the count its own sentence fixed.

    python 02_shared_code/registry/record_wave7.py [--only EXP-0183]
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
import topic_designs_wave7 as TD7                                  # noqa: E402

MATRIX_PAPERS = "P039;P040;P041;P042;P043;P044"
TOPICS = ";".join(TD7.RUNNABLE)


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

    if not want or "EXP-0181" in want:
        c = R4.load("results_raw/EXP0181_wave7_premise_census_*.json")
        m = c.get("measured") or {}
        R4.call("EXP-0181", MATRIX_PAPERS, TOPICS, "wave7_premise_census",
                "02_shared_code/package_factory/probe_wave7_premises.py",
                f"dev rows read={m.get('rows')}; by config={m.get('by_config')}; seed {c.get('seed')}; structure and "
                f"prevalence only, no outcome is associated with anything. The shipped catalogue parser recovered "
                f"{m.get('shipped_parser_entries_recovered')} entries from the first 500 rows, so the wave reads the "
                f"release's own n/d/p schema (deviation W7-D01)",
                gate_status(c),
                "results_raw/EXP0181_wave7_premise_census_*.json", str(c.get("seed") or "42"),
                "the census that sets this wave's twelve gates; every one of them names the topic it scopes and the "
                "value it fired on, and the pass was run twice over all 31,642 dev rows with identical output",
                "yes - the premise section of each package")

    if not want or "EXP-0182" in want:
        m = R4.load("results_raw/EXP0182_wave7_candidate_matrix_*.json")
        xk = m.get("census_cross_check") or {}
        R4.call("EXP-0182", MATRIX_PAPERS, TOPICS, "wave7_candidate_matrix",
                "02_shared_code/package_factory/exp_wave7_features.py",
                f"seed={m.get('seed')}; one row per dev query plus three auxiliary frames (server, gold pair, tool "
                f"roster) and a drawn-pair frame; queries={m.get('queries_measured')} of {m.get('rows_offered')} "
                f"offered, dropped={m.get('queries_dropped')}; median candidates={m.get('median_candidates')}; "
                f"distinct gold pairs={m.get('distinct_gold_pairs')}",
                f"matrix_built_{m.get('queries_measured')}_queries_in_{m.get('by_config')}__"
                f"queries_dropped_{m.get('queries_dropped')}__"
                + "__".join(f"census_agreement_{k}_{v[0]}_vs_{v[1]}" for k, v in sorted(xk.items())) +
                f"__fail_at_1_share_{m.get('fail_at_1_share')}__decoy_present_share_{m.get('decoy_present_share')}"
                f"__contaminated_share_{m.get('contaminated_share')}",
                "results_raw/EXP0182_wave7_candidate_matrix_*.json", str(m.get("seed") or "42"),
                "the shared substrate for all six designs: every quantity the freezes name, measured once, beside the "
                "frozen ranker's own columns; the five aggregates the census also computes are cross-checked and the "
                "build aborts if any two readings of one rule diverge",
                "yes - the sample, instrument and provenance tables of every wave-7 package")

    for tid, exp in TD7.EXP_OF.items():
        if want and exp not in want:
            continue
        key = exp[-4:]
        art = R4.load(f"results_raw/EXP{key}_wave7_design_{key}_*.json")
        R4.call(exp, TD7.DESIGNS[tid]["pkg"][:4], tid, "wave7_main",
                "02_shared_code/package_factory/exp_wave7_designs.py",
                f"seed={TD7.SEED}; clustered as each hypothesis names (query, server or tool pair); Holm over the "
                f"design's declared hypotheses; bands .05/.15/.30; queries={art.get('n_queries')}; clusters="
                f"{art.get('n_clusters')}; candidate slots={art.get('n_candidates_offered')}; the run's own argv is "
                f"recorded in the artefact",
                R4.verdicts(art) or "no_hypothesis_row_returned",
                f"results_raw/EXP{key}_wave7_design_{key}_*.json", str(TD7.SEED),
                "the pre-registered test for this topic; a cell a premise gate scoped out is reported as "
                "not_testable_* with its measured count, a quantity the freeze asks to be reported rather than tested "
                "keeps its own verdict label, and the outcome throughout is a frozen lexical ranker's, not an agent's "
                "choice (deviation W7-D02)",
                "yes - the whole result set")

    if not want or "EXP-0189" in want:
        b = R4.load("results_raw/EXP0189_wave7_battery_0189_*.json")
        sh = b.get("_shared") or {}
        e06 = (sh.get("e06_second_instrument") or {}).get("pairs") or []
        ri = (sh.get("e06_second_instrument") or {}).get("ranker_invariance") or {}
        e17 = sh.get("e17_counterfactual") or {}
        e19 = sh.get("e19_contamination") or {}
        ranker_arms = "__".join(f"ranker_{k}_fail_at_1_{(v or {}).get('fail_at_1_share')}"
                                for k, v in sorted((ri.get("modes") or {}).items())) or "ranker_arms_absent"
        R4.call("EXP-0189", MATRIX_PAPERS, TOPICS,
                "e04_ablation_e06_second_instrument_e08_external_e12_scaling_e15_16_errors_"
                "e17_counterfactual_e18_replication_e19_contamination_e_by_config",
                "02_shared_code/package_factory/exp_wave7_battery.py",
                "spec 9 E-step battery on the wave-7 candidate frame; the step loop is imported from "
                "exp_wave2_battery.run_battery, so an ablation here is the same computation as in wave 2",
                f"battery_executed_for_{len([k for k in b if k in TD7.DESIGNS])}_topics__"
                f"e06_pairs_{len(e06)}__e17_arms_{len(e17.get('arms') or [])}__{ranker_arms}__"
                f"description_signatures_{e19.get('distinct_description_signatures')}",
                "results_raw/EXP0189_wave7_battery_0189_*.json", str(TD7.SEED),
                "the E-step record for all six packages; the ranker-invariance arm and the description-duplication "
                "census are what license reading a miss rate as a property of the catalogue's language rather than of "
                "the scorer's document definition or of a handful of repeated descriptions",
                "yes - the E-coverage table of every wave-7 package")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
