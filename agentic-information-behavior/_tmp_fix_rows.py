"""Move the new reviewer-attack rows into the reviewer-attack block of each builder.

The previous patch inserted them after the last `| ` line of the whole generator file, which for P002 and P004 sits in
the final_audit block, so the rows were written into the wrong shipped document (and P005's into no shipped document at
all). This removes those rows from wherever they landed and re-inserts them inside the reviewer-attack string only.
"""
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
P = pathlib.Path("papers")
GEN = {"P002": ("P002_isp_stage_measurement/scripts/build_package.py", 14),
       "P004": ("P004_shipped_quality_score_validity/scripts/build_package.py", 11),
       "P005": ("P005_governance_metadata_verifiability/scripts/build_package_partb.py", "A14")}

ROWS = {
 "P002": [
  '| 14 | "Is `exploration` an information-search stage or just a word your cue table happens to fire on?" '
  '(construct validity) | The construct is the published ISP stage vocabulary and the operationalisation is tested '
  'against it three ways: the cue table is frozen in `protocol_freeze.md` before the pilot; the truncation curve '
  '(EXP-0031) shows the stage mix responding to a manipulation of available context rather than to surface tokens; '
  'and an independent implementation of the same definitions reproduces the distribution only partly (EXP-0088, '
  "EXP-0112, kappa 0.5679 against a pre-registered 0.75), which is reported as the instrument's measured boundary "
  "| `agenttrove_rubric_invariance_exp0112.md`, `ABLATION_CASES_INTERVENTION_EXP0107.md`, limitations 7 |"],
 "P004": [
  '| 11 | "You read the teacher model\'s output as evidence about cognition" | No claim of that kind is made or '
  'needed: the objects audited are the numeric score fields a release ships, and the criterion side is an '
  'executed-tool comparison. Reasoning text is never opened as a measure of the model, and the programme-level rule '
  'against treating `<think>` as cognition is recorded for this package in `docs/section21_special_risks.md` (21.2) '
  '| `protocol_freeze.md`, `dataset_card.md`, docs/section21_special_risks.md |',
  '| 12 | "Your unit is a row, but rows cluster by prompt" | Every interval in the package is prompt-clustered: '
  '`ci95_prompt_clustered` is a bootstrap over prompt clusters rather than over rows, the 12 criterion tests are '
  'Holm-corrected as a family, and the per-configuration alphas use the same clustering (`draws: 500`) '
  '| `tables/table9_full_score_comparison.csv`, `results_raw/EXP0043_*.json` |',
  '| 13 | "Is the criterion contaminated by the score it validates?" | The criterion is computed from the executed '
  'tool calls and the gold tool set of the same row, never from the shipped score; the remaining channel is the '
  'shared release, and that is measured rather than assumed - EXP-0104 reports duplication per source column and '
  'per configuration, with a `rows with a value` column so a null field is never read as independence '
  '| `CONTAMINATION_AND_COST.md` (EXP-0104), `tables/table_presence_scan.csv` |'],
 "P005": [
  '| A14 | "Your ladder is an invented construct, so a high level only means your lexicon fired." | Partly fair, and '
  'answered on construct validity: the construct is the declared-then-verifiable distinction, so the paper asserts '
  'nothing about whether a licence is good, only that a declaration exists at a named read site under a named key or '
  'filename. The four read sites and their filename/key sets are frozen in `protocol_freeze.md` §2, both lexicons are '
  'reported side by side (`tables/table3_record_level_lexicon_sensitivity.csv`), and a level the caps could not scan '
  'is printed as `unscanned`, never as absent | `tables/table2_level_census.csv`, limitations |',
  '| A15 | "You are reading agent reasoning traces as evidence about a model\'s mind" | No reasoning content is '
  'interpreted anywhere in this package: the scan reads filenames, YAML front matter, column names and parquet '
  'footer keys. The corpus whose name mentions reasoning (`hermes-agent-reasoning-traces`) is treated exactly like '
  'the others, and the programme-level prohibition on treating `<think>` as cognition is recorded in '
  '`docs/section21_special_risks.md` (21.2) | `dataset_card.md`, `tables/table1_release_inventory.csv` |'],
}
# where each builder's reviewer-attack text starts, and how it ends
BLOCK = {"P002": ('(PAP / "reviewer_attack.md").write_text(f"""', '""")'),
         "P004": ('(PAP / "reviewer_attack.md").write_text(f"""', '""")'),
         "P005": ("REV = f\"\"\"", '(PAP / "reviewer_attack.md").write_text(REV')}


def block_span(lines, pid):
    start_pat, end_pat = BLOCK[pid]
    si = next(i for i, l in enumerate(lines) if start_pat in l)
    ei = next(i for i, l in enumerate(lines) if i > si and end_pat in l)
    return si, ei


for pid, (rel, key) in GEN.items():
    f = P / rel
    lines = f.read_text(encoding="utf-8").splitlines()
    rows = ROWS[pid]
    # 1. drop any of these rows wherever they currently sit in the generator
    lines = [l for l in lines if not any(l.strip().startswith(r[:60]) for r in rows)]
    si, ei = block_span(lines, pid)
    inside = [i for i in range(si, ei) if lines[i].startswith("| ") and "---" not in lines[i]]
    if not inside:
        print(f"  {pid}: NO table rows inside the reviewer-attack block - aborting this package")
        continue
    at = inside[-1] + 1
    lines[at:at] = rows
    f.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="")
    print(f"  {pid}: {len(rows)} rows placed inside the reviewer-attack block (after line {at}), "
          f"block spans {si + 1}-{ei + 1}")
