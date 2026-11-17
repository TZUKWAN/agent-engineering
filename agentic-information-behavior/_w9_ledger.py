"""Append the wave-9 superseded generations to results_raw/SUPERSEDED_ARTIFACTS.json through the shipped tool.

Arguments are passed as a list so no shell quoting can lose a word of the reason - the failure mode that once put a
backtick phrase into a ledger entry by eating it.
"""
import glob
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
PY = sys.executable
TOOL = "02_shared_code/registry/supersede_artefacts.py"

CENSUS = ("EXP-0196 first launch was a 400-rollout smoke run - 5,908 commanded steps over 360 task instances - used "
          "to prove the step reader, the derived switch and lag definitions and the gate wiring. Nine of its twelve "
          "gates fired there against three on the whole sample, because the draw was 50 times smaller: G3 counted 5 "
          "families with >= 500 steps where the release holds 11, G6 counted 0 task families with >= 200 rollouts "
          "where it holds 2, and G8 counted 37 instances with repeated rollouts where it holds 1,775. The two "
          "measurements that decide the wave are near-identical across the two scales - newness available on 0.7737 "
          "of steps in the smoke run and 0.7876 on the whole sample - so that generation is superseded and every "
          "value the freeze cites is a whole-sample one, produced twice with byte-identical output.")

DESIGN = ("EXP-0198 to EXP-0201 generations run before three fixes, none of which relaxes a threshold: the imported "
          "baseline ladder defaulted to wave 7's control set and returned a single 'not fitted on these rows' line "
          "for T179 (deviation W9-D07); T153's stratum block binned rollouts by a rank decile of their transition "
          "count and produced 14,273 rows where the table promises bands, and now reports four transition bands plus "
          "the task families with at least 200 rollouts; and T193's H2 denominator was taken from the first row of "
          "each instance, which found 49 instances with a success where the full frame has 235, so the share is "
          "recomputed on an any-success flag. T179's row also now carries the arm sizes and the step-cap counts that "
          "deviations W9-D05 and W9-D06 describe.")


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


groups = [("EXP0196_wave9_premise_census_*.json", CENSUS, 2),
          ("EXP0197_wave9_step_matrix_*.json", DESIGN, 1),
          ("EXP0198_wave9_design_0198_*.json", DESIGN, 1), ("EXP0199_wave9_design_0199_*.json", DESIGN, 1),
          ("EXP0200_wave9_design_0200_*.json", DESIGN, 1), ("EXP0201_wave9_design_0201_*.json", DESIGN, 1),
          ("EXP0202_wave9_battery_0202_*.json", DESIGN, 1)]
rc = 0
for pat, reason, keep in groups:
    rc |= call(pat, reason, keep)
print("rc", rc)
sys.exit(rc)
