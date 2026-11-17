"""Append the wave-7 superseded generations to results_raw/SUPERSEDED_ARTIFACTS.json through the shipped tool.

Arguments are passed as a list, so no shell quoting can eat a word of the reason: an earlier round lost a backtick
phrase from a ledger reason that way, and an unexplained exclusion is exactly what the ledger exists to prevent.
"""
import glob
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
PY = sys.executable
TOOL = "02_shared_code/registry/supersede_artefacts.py"

FRAME = ("EXP-0182 generations before the current one. Two of them measured a rule the freeze does not state: the "
         "decoy column took the minimum containment over a query gold candidates where both the frozen instrument "
         "sentence and EXP-0181 use an any(), which scored decoy_present_share 0.1914 against the census value "
         "0.4329 on the same 31,642 rows; and the server pool was a set of (name, word-set) tuples handed to sorted(), "
         "which compares word sets through the partial subset order and so let PYTHONHASHSEED choose which 196 servers "
         "were usable and in what order they were drawn. The current generation keys the pool by tool name, reproduces "
         "all five cross-checked aggregates exactly (fail_at_1 0.1788, decoy 0.4329, contamination 0.0933, multi-gold "
         "16,461 queries, gold pairs 11,798), and adds the roster, the drawn-pair frame and the description-signature "
         "column that T165 needed. Recorded as deviations W7-D05 to W7-D09.")

DESIGN = ("EXP-0183 to EXP-0188 generations run against the superseded EXP-0182 frames listed in the entry above, "
          "and in the two earliest cases before the frame carried the columns these designs read. The shipped "
          "generation was run on the current frame, and its verdicts are the ones the packages report: T161 "
          "supported / not_monotone_in_6_measured_levels / supported, T162 null / null / "
          "not_specific_length_carries_the_same_signal, T164 supported / supported / "
          "not_specific_namespace_share_still_separates, T165 supported plus two measured-descriptively rows, T166 "
          "the G8-limited H1 plus per-config shares plus a supported H3, T169 supported / supported plus a measured "
          "structure row. Holm families also changed once the specificity rows carried their decisive arm p-value, "
          "which is why those rows are adjusted over three hypotheses rather than one or two.")


def files(pat):
    return sorted(glob.glob(str(ROOT / "results_raw" / pat)))


def call(pat, reason, keep_newest=1):
    fs = files(pat)
    drop = fs[: max(0, len(fs) - keep_newest)]
    if not drop:
        print(f"{pat}: nothing to supersede ({len(fs)} generations)")
        return 0
    args = [PY, "-u", TOOL, "--reason", reason]
    for f in drop:
        args += ["--file", str(pathlib.Path(f).relative_to(ROOT))]
    p = subprocess.run(args, cwd=str(ROOT))
    print(f"{pat}: superseded {len(drop)} of {len(fs)} generations, rc={p.returncode}")
    return p.returncode


rc = 0
for pat, keep in (("EXP0181_wave7_premise_census_*.json", 2), ("EXP0182_wave7_candidate_matrix_*.json", 1),
                  ("EXP0183_wave7_design_0183_*.json", 1), ("EXP0184_wave7_design_0184_*.json", 1),
                  ("EXP0185_wave7_design_0185_*.json", 1), ("EXP0186_wave7_design_0186_*.json", 1),
                  ("EXP0187_wave7_design_0187_*.json", 1), ("EXP0188_wave7_design_0188_*.json", 1)):
    rc |= call(pat, FRAME if pat.startswith(("EXP0181", "EXP0182")) else DESIGN, keep)
print("rc", rc)
sys.exit(rc)
