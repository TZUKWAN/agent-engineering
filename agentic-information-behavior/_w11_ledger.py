"""Append the wave-11 superseded generations to results_raw/SUPERSEDED_ARTIFACTS.json through the shipped tool.

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

CENSUS = ("EXP-0207 ran four generations before the one cited by the freeze. The first three measured open-thoughts/AgentTrove, the dataset these five topics were screened with: a 400-row smoke and then the first 12,000 rows of six shards, where every outcome column was null and no task prefix appeared twice - a property of the slice, as the whole-release scan later showed (1,696,847 rows, 128,435 non-null task_binary, 218,706 non-null result, 200,825 task prefixes attempted more than once). The fourth generation measured 400 rollouts of the new substrate to prove the reader. All four are superseded by the whole-draw run the freeze cites, which was produced twice with byte-identical output, and the AgentTrove scan that documents the abandoned substrate is kept as its own artefact (deviations W11-D01 and W11-D02).")

FRAME = ("EXP-0208 generations before the current one coded the abstraction and uncertainty markers as a sum over turns while EXP-0207 counted the presence of each marker over the whole text, so the frame and the census disagreed on mean abstract markers (3.569 against 2.071) and the build refused to write. The counting is now shared, and the frame reproduces all fifteen aggregates EXP-0207 measures, including the per-category rollout counts.")



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


DESIGN = ("EXP-0209 to EXP-0213 generations run before three fixes, none of which relaxes a threshold: T138's stratum block asked for repositories with 500 pairs and produced no rows at all, so it now reports overlap bands and repositories with 250; T137's H2 and T142's H1 carried ci_lo and ci_hi assembled from two different quantities, which is now null with the per-category intervals kept beside them (W11-D06); and T142's H2 and H3 fitted a class term that the outcome cell determines perfectly (beta 18.89, interval -283 to +321), which is now reported as not_estimable_quasi_separation_in_this_cell with the raw numbers held in an unidentified_estimate field (W11-D05).")

groups = [("EXP0207_wave11_premise_census_*.json", CENSUS, 1),
          ("EXP0208_wave11_trace_matrix_*.json", FRAME, 1),
          ("EXP0209_wave11_design_0209_*.json", DESIGN, 1),
          ("EXP0210_wave11_design_0210_*.json", DESIGN, 1),
          ("EXP0211_wave11_design_0211_*.json", DESIGN, 1),
          ("EXP0212_wave11_design_0212_*.json", DESIGN, 1),
          ("EXP0213_wave11_design_0213_*.json", DESIGN, 1),
          ("EXP0214_wave11_battery_0214_*.json", DESIGN, 1)]
rc = 0
for pat, reason, keep in groups:
    rc |= call(pat, reason, keep)
print("rc", rc)
sys.exit(rc)
