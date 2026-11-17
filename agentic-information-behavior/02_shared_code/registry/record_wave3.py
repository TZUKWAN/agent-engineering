"""Register the wave-3 experiments, each status string taken from its own artefact.

The companion of `record_wave2.py` for this wave, and run the same way: after the designs and the battery, so a
re-run re-registers whatever the artefacts now say rather than whatever this file remembers.

    python 02_shared_code/registry/record_wave3.py [--only EXP-0143 ...]
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
PYEXE = sys.executable
REC = str(ROOT / "02_shared_code" / "registry" / "record_experiment.py")
sys.path.insert(0, str(ROOT / "02_shared_code" / "package_factory"))
import topic_designs_wave3 as TD3                                                 # noqa: E402


def latest(pat: str) -> pathlib.Path:
    f = sorted(glob.glob(str(ROOT / pat)), key=lambda x: pathlib.Path(x).stat().st_mtime)
    if not f:
        raise SystemExit(f"ABORT: no artefact matches {pat!r}; the experiment has not run")
    return pathlib.Path(f[-1])


def load(pat: str) -> dict:
    return json.loads(latest(pat).read_text(encoding="utf-8"))


def verdicts(a: dict) -> str:
    out = []
    for m in a.get("models") or []:
        if isinstance(m, dict) and m.get("verdict"):
            out.append(f"{m.get('hypothesis') or m.get('stratum') or m.get('term_name') or m.get('term')}:"
                       f"{m['verdict']}")
    return "_".join(out)


def call(exp, paper, topic, stage, script, config, status, artefact, seed, notes, enters):
    cmd = [PYEXE, REC, "--exp", exp, "--paper", paper, "--topic", topic, "--stage", stage, "--script", script,
           "--config", config[:300], "--status", status[:300], "--seed", seed, "--notes", notes[:300],
           "--enters-paper", enters[:200], "--artefact", artefact]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    tail = (r.stdout + r.stderr).strip().splitlines()
    print(f"{exp}: {tail[-1][:150] if tail else 'rc=' + str(r.returncode)}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", action="append", default=[], help="register just these experiment ids")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    want = set(a.only)

    if not want or "EXP-0143" in want:
        m = load("results_raw/EXP0143_wave3_description_matrix_*.json")
        call("EXP-0143", "P018;P020;P021;P022", "T113;T119;T120;T122", "wave3_feature_matrix",
             "02_shared_code/package_factory/exp_wave3_features.py",
             f"rows_per_config=8000; bucket=dev; seed=42; queries taken from the frozen wave-1 sample, not re-drawn; "
             f"four rule rewrites scored by the frozen BM25; n_queries={m.get('n_query_rows')} "
             f"n_candidate_rows={m.get('n_candidate_rows')}",
             f"matrix_built_{m.get('n_query_rows')}_queries_{m.get('n_candidate_rows')}_rows__dense_neighbour_"
             f"coverage_{m.get('dense_neighbour_coverage')}__contradiction_rows_"
             f"{m.get('contradiction_cell_rows')}",
             "results_raw/EXP0143_wave3_description_matrix_*.json", "42",
             "wave-3 substrate: name-description congruence against the description alone, neighbour "
             "discriminability (lexical and dense), and the rank of the released selection under baseline, "
             "use-case, length-matched and synonym-canonicalised catalogues",
             "yes - the sample, instruments and provenance tables of all four packages")

    for tid, exp in TD3.EXP_OF.items():
        if want and exp not in want:
            continue
        key = exp[-4:]
        art = load(f"results_raw/EXP{key}_wave3_design_{key}_*.json")
        call(exp, TD3.DESIGNS[tid]["pkg"][:4], tid, "wave3_main",
             "02_shared_code/package_factory/exp_wave3_designs.py",
             "seed=42; clustered on query_id; Holm over the design's three declared hypotheses; bands .05/.15/.30; "
             f"n={art.get('n_queries') or art.get('n_rows')}; the run's own argv is recorded in the artefact",
             verdicts(art) or "reported_as_thresholded_statistics",
             f"results_raw/EXP{key}_wave3_design_{key}_*.json", "42",
             "the pre-registered test for this topic; hypotheses whose own gate fired are labelled "
             "not_interpretable/not_testable in the artefact and stay that way in the package",
             "yes - the whole result set")

    if not want or "EXP-0149" in want:
        b = load("results_raw/EXP0149_wave3_battery_0149_*.json")
        sh = b.get("_shared") or {}
        e17 = sh.get("e17_counterfactual") or {}
        call("EXP-0149", "P018;P020;P021;P022", "T113;T119;T120;T122",
             "e04_ablation_e06_second_instrument_e08_external_e12_scaling_e15_16_errors_e17_counterfactual_"
             "e18_replication_e19_contamination",
             "02_shared_code/package_factory/exp_wave3_battery.py",
             "spec 9 E-step battery; the step loop imported from exp_wave2_battery.run_battery rather than copied, "
             "so an ablation or replication means the same thing in both waves",
             f"battery_executed_e17_rows_{e17.get('rows')}__arms_{len(e17.get('rank1_arms') or [])}",
             "results_raw/EXP0149_wave3_battery_0149_*.json", "42",
             "the E00-E19 package requirement is owed to every paper: ablation, scaling, replication under seed 7, "
             "error taxonomy and quoted cases, second instrument, external transfer, counterfactual arms, cost and "
             "contamination",
             "yes - E_COVERAGE.md and tables/table8..table17")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
