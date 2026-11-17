"""Register wave 4 from its artefacts, so a status string is never typed by hand.

`record_wave2.py` and `record_wave3.py` do the same job for their waves; this is the wave-4 counterpart. Every field
comes from the artefact it describes, and the verdict string is composed from the hypotheses inside it, so a re-run
that changes an estimate changes the registry line rather than leaving it to disagree with the file.

    python 02_shared_code/registry/record_wave4.py [--only EXP-0154]
"""
from __future__ import annotations

import argparse
import glob
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
sys.path.insert(0, str(ROOT / "02_shared_code" / "package_factory"))
import topic_designs_wave4 as TD4                                # noqa: E402

PYEXE = sys.executable
REC = str(HERE / "record_experiment.py")


def latest(pat: str):
    hits = sorted(glob.glob(str(ROOT / pat)), key=lambda f: pathlib.Path(f).stat().st_mtime)
    return hits[-1] if hits else None


def load(pat: str) -> dict:
    f = latest(pat)
    return json.loads(pathlib.Path(f).read_text(encoding="utf-8")) if f else {}


def verdicts(a: dict) -> str:
    out = []
    for m in (a.get("models") or []):
        if isinstance(m, dict) and m.get("hypothesis"):
            out.append(f"{m['hypothesis']}:{m.get('verdict')}")
    return "_".join(out)


def call(exp, paper, topic, stage, script, config, status, artefact, seed, notes, enters):
    cmd = [PYEXE, REC, "--exp", exp, "--paper", paper, "--topic", topic, "--stage", stage, "--script", script,
           "--config", config[:300], "--status", status[:300], "--seed", seed, "--notes", notes[:300],
           "--enters-paper", enters[:200], "--artefact", artefact]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    tail = (r.stdout + r.stderr).strip().splitlines()
    print(f"{exp}: {tail[-1][:170] if tail else 'rc=' + str(r.returncode)}")


MATRIX_PAPERS = "P023;P024;P025;P026"


def gate_status(c: dict) -> str:
    """`no_gate_fired`, or each fired gate with the scope its own frozen sentence carries.

    A fired gate is not a failure of the wave: G7 blocks the topic whose hypothesis needs an outcome label, and the
    rest of the wave stands. So the registry line names the gate and its scope rather than printing a bare list.
    """
    v = c.get("verdict") or {}
    fired = v.get("blocked_gates") or []
    if not fired:
        return "no_gate_fired"
    rules = c.get("gate_scopes") or c.get("gate_rules") or {}
    parts = []
    for g in fired:
        r = rules.get(g) if isinstance(rules.get(g), dict) else {}
        parts.append(f"{g}[scope={r.get('scope', '?')}]" if r else str(g))
    return ("gates_fired__" + "__".join(parts)
            + "__stopped_designs_" + "_".join(v.get("blocked_whole_design") or [])
            + f"__claim_limited_{len(v.get('claim_limited') or {})}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", action="append", default=[], help="register just these experiment ids")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    want = set(a.only)

    if not want or "EXP-0152" in want:
        c = load("results_raw/EXP0152_wave4_premise_census_*.json")
        call("EXP-0152", MATRIX_PAPERS, "T123;T124;T126;T127;T191", "wave4_premise_census",
             "02_shared_code/package_factory/probe_wave4_premises.py",
             f"trajectories sampled={c.get('sampled_rows')}; seed 42; structure, prevalence and joint turn-to-action "
             f"cells only, no outcome read",
             gate_status(c),
             "results_raw/EXP0152_wave4_premise_census_*.json", "42",
             "the census that sets this wave's gates; the parse-coverage counts inside it are what separate a thin "
             "cell from an instrument that could not read the field",
             "yes - the premise section of each package")

    if not want or "EXP-0153" in want:
        m = load("results_raw/EXP0153_wave4_step_matrix_*.json")
        call("EXP-0153", MATRIX_PAPERS, "T123;T124;T126;T127", "wave4_step_matrix",
             "02_shared_code/package_factory/exp_wave4_features.py",
             f"traj_cap={m.get('sample_cap')}; seed={m.get('seed')}; one row per assistant turn; calls and "
             f"observations parsed from the turn's own tag blocks; n_turns={m.get('assistant_turns')} "
             f"n_trajectories={m.get('trajectories')}",
             f"matrix_built_{m.get('assistant_turns')}_turns_in_{m.get('trajectories')}_trajectories__"
             f"calls_unparseable_{m.get('calls_unparseable')}__modal_share_{m.get('modal_turn_share')}",
             "results_raw/EXP0153_wave4_step_matrix_*.json", "42",
             "the shared substrate for all four designs: two prose faces per turn, the tool-name family of the call "
             "the turn emitted, and the evidence state before it",
             "yes - the sample, instrument and provenance tables of every wave-4 package")

    for tid, exp in TD4.EXP_OF.items():
        if want and exp not in want:
            continue
        key = exp[-4:]
        art = load(f"results_raw/EXP{key}_wave4_design_{key}_*.json")
        call(exp, TD4.DESIGNS[tid]["pkg"][:4], tid, "wave4_main",
             "02_shared_code/package_factory/exp_wave4_designs.py",
             f"seed=42; clustered on traj_id; Holm over the design's three declared hypotheses; bands "
             f".05/.15/.30; turns={art.get('n_turns')}; trajectories={art.get('n_trajectories')}; the run's own "
             f"argv is recorded in the artefact",
             verdicts(art) or "no_hypothesis_row_returned",
             f"results_raw/EXP{key}_wave4_design_{key}_*.json", "42",
             "the pre-registered test for this topic; a verdict of outside_the_frozen_rule_* is an outcome the "
             "frozen sentence did not enumerate and is reported as such",
             "yes - the whole result set")

    if not want or "EXP-0158" in want:
        b = load("results_raw/EXP0158_wave4_battery_0158_*.json")
        sh = b.get("_shared") or {}
        e17 = sh.get("e17_counterfactual") or {}
        e19 = sh.get("e19_contamination") or {}
        call("EXP-0158", MATRIX_PAPERS, "T123;T124;T126;T127",
             "e04_ablation_e06_second_instrument_e08_external_e12_scaling_e15_16_errors_e17_counterfactual_"
             "e18_replication_e19_contamination_e_by_config",
             "02_shared_code/package_factory/exp_wave4_battery.py",
             "spec 9 E-step battery on the wave-4 step frame; the step loop imported from "
             "exp_wave2_battery.run_battery rather than copied, so an ablation means the same thing in both waves",
             f"battery_executed_for_{len([k for k in b if k in TD4.DESIGNS])}_topics__"
             f"e17_arms_{len(e17.get('arms') or [])}__turn_text_repeat_share_{e19.get('share_of_turns_that_are_a_repeat')}",
             "results_raw/EXP0158_wave4_battery_0158_*.json", "42",
             "the E-step record for all four packages; the text-duplication audit is what licenses reading the "
             "marker prevalences as language rather than as boilerplate counts",
             "yes - the E-coverage table of every wave-4 package")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
