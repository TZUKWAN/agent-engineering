"""Append the wave-10 superseded generations to results_raw/SUPERSEDED_ARTIFACTS.json through the shipped tool.

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

CENSUS = ("EXP-0203 first launch was a 300-row smoke run, used to prove the lexical-ambiguity, referential, "
          "marker-list and cross-server-signature instruments and the gate wiring. Eight of its twelve gates fired "
          "there against one on the whole release, because the draw was 300 rows: G3 found 151 rows with a lexically "
          "ambiguous word where the release holds 15,264, and G12 found 295 prompt groups where it holds 6,859. The "
          "measurement that decided the wave is unchanged in kind across the two scales - 0.8376 of rows offer two or "
          "more candidates in both - so that generation is superseded and every cited value is a whole-release one, "
          "produced twice with byte-identical output.")

DESIGN = ("EXP-0204 generation, none of which relaxes a threshold: the imported "
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


groups = [("EXP0203_wave10_premise_census_*.json", CENSUS, 2),
          ("EXP0204_wave10_design_0204_*.json", DESIGN, 1),
          ("EXP0205_wave10_requirement_matrix_*.json", DESIGN, 1)]
rc = 0
for pat, reason, keep in groups:
    rc |= call(pat, reason, keep)
print("rc", rc)
sys.exit(rc)
