"""Append the wave-8 superseded generations to results_raw/SUPERSEDED_ARTIFACTS.json through the shipped tool.

Arguments go in as a list so no shell quoting can swallow a word of a reason, and each call keeps the newest
generation citable while naming, with measured values, why the earlier ones are not.
"""
import glob
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
PY = sys.executable
TOOL = "02_shared_code/registry/supersede_artefacts.py"

CENSUS = ("EXP-0190 first launch was a 400-trajectory smoke run, used to prove the call parser, the anchor and "
          "correction instruments and the gate wiring. G3, G4, G9, G10 and G12 fired there only because the draw was "
          "400 trajectories - it found 9 early-hypothesis trajectories where the whole release holds 570 - so that "
          "generation is superseded and the gate verdicts the freeze cites are the whole-release ones, which were "
          "produced twice with identical output.")

FRAME = ("EXP-0191 generations before the current one. The trajectory summary and the turn rows both carried "
         "`category`, so the join would have renamed it to category_x/category_y and the designs' column check "
         "aborted on a missing column before any estimate existed (deviation W8-D04); the current generation supplies "
         "only the columns the turn rows lack, keeps the many-to-one row-count guard, and still reproduces every one "
         "of the fifteen aggregates EXP-0190 measured (trajectories 14,701, turns 147,253, observations 174,545, "
         "terminal-turn share 0.4649, failure-marker share 0.5893, early-hypothesis trajectories 570, self-correcting "
         "trajectories 825, countable plans 6,975, repeated-call trajectories 4,125).")

DESIGN = ("EXP-0192 to EXP-0194 generations run before two fixes that changed nothing in the arithmetic: wave 7's "
          "imported estimators defaulted to wave 7's cluster column, which made the first wave-8 run die on a missing "
          "`query_id` rather than fit anything (deviation W8-D05), and an earlier run carried an int-cast descriptive "
          "field that printed 0 where the measured mean newness share is 0.5423. The shipped generation reads "
          "trajectory clusters as its sentences promise and reports the corrected descriptives: T171 opposite / null "
          "/ not_specific, T182 opposite / opposite / not_specific, T190 opposite / below its frozen 0.20 floor at "
          "0.0155 / supported.")


def call(pat, reason, keep_newest=1):
    fs = sorted(glob.glob(str(ROOT / "results_raw" / pat)))
    drop = fs[: max(0, len(fs) - keep_newest)]
    if not drop:
        print(f"{pat}: nothing to supersede ({len(fs)} generations)")
        return 0
    args = [PY, "-u", TOOL, "--reason", reason]
    for f in drop:
        args += ["--file", str(pathlib.Path(f).relative_to(ROOT))]
    rc = subprocess.run(args, cwd=str(ROOT)).returncode
    print(f"{pat}: superseded {len(drop)} of {len(fs)} generations, rc={rc}")
    return rc


groups = [("EXP0190_wave8_premise_census_*.json", CENSUS, 2), ("EXP0191_wave8_turn_matrix_*.json", FRAME, 1),
          ("EXP0192_wave8_design_0192_*.json", DESIGN, 1), ("EXP0193_wave8_design_0193_*.json", DESIGN, 1),
          ("EXP0194_wave8_design_0194_*.json", DESIGN, 1), ("EXP0195_wave8_battery_0195_*.json", DESIGN, 1)]
rc = 0
for pat, reason, keep in groups:
    rc |= call(pat, reason, keep)
print("rc", rc)
sys.exit(rc)
