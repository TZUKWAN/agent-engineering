# Collision-level columns: what is reproducible, and what is legacy (EXP-0097)

Generated 2026-09-24 05:14 by `02_shared_code/literature/reconcile_collision_levels.py`. No number in this file is entered by hand.

**Why this exists.** EXP-0095 reported 26 collision grades moving under the frozen rule while recovering abstracts. Attributing them row by row: {"stored_level_not_reproducible_from_the_text_already_on_disk": 26}. None of the moves came from recovered text. They are values in `literature_graded.csv:overlap_level_current` - which `grade_collisions.py` describes as a retrieval note rather than a grade before EXP-0057 - copied into each paper's `literature_matrix.csv:overlap_level`. The rule's own output had been kept beside them in `level_rule`, and that is the column the shipped audits read.

## 1. What changed in the data files

- `literature_graded.csv` and all five `literature_matrix.csv` files now carry `overlap_level_rule_rederived` and `level_rederived_by`; the legacy column is left exactly as it was, so both levels remain on the record. Levels re-derived from text on disk: 250 of 289 graded records (the remainder hold no >= 25-word abstract and stay labelled `title_only`).

## 2. Legacy column vs frozen rule

Across the five curated matrices, **5 of 36** rows that carry a level in both columns agree with the frozen rule. Direction matters more than the count: a demotion means the shipped table overstated a collision, a promotion means it understated one.

| paper | matrix rows | comparable rows | legacy agrees | legacy disagrees | demoted | promoted | rows with a legacy level but no abstract on disk |
|---|---|---|---|---|---|---|---|
| P001 | 20 | 19 | 2 | 17 | 14 | 3 | 0 |
| P002 | 50 | 4 | 0 | 4 | 4 | 0 | 0 |
| P003 | 72 | 5 | 0 | 5 | 5 | 0 | 20 |
| P004 | 54 | 2 | 1 | 1 | 0 | 1 | 7 |
| P005 | 120 | 6 | 2 | 4 | 4 | 0 | 0 |
| P006 | 30 | 0 | 0 | 0 | 0 | 0 | 30 |
| P007 | 19 | 0 | 0 | 0 | 0 | 0 | 19 |
| P008 | 30 | 0 | 0 | 0 | 0 | 0 | 30 |
| P009 | 30 | 0 | 0 | 0 | 0 | 0 | 30 |

## 3. Do the shipped audits reproduce? (this decides whether any claim moves)

Each `novelty_grading.md` prints a level distribution. Recomputing it from `level_rule` plus the hand assignment dict in `record_novelty_grading.py`:

| paper | shipped | recomputed | reproduces |
|---|---|---|---|
| P001 | `{"L1": 14, "L0": 5, "L2": 1}` | `{"L0": 5, "L1": 14, "L2": 1}` | yes
| P002 | `{"L1": 10, "L0": 12, "L2": 24, "L3": 4}` | `{"L0": 12, "L1": 10, "L2": 24, "L3": 4}` | yes
| P003 | `{"L0": 37, "L2": 11, "L1": 4}` | `{"L0": 37, "L1": 4, "L2": 11}` | yes
| P004 | `{"L0": 8, "L3": 7, "L1": 18, "L2": 14}` | `{"L0": 8, "L1": 18, "L2": 14, "L3": 7}` | yes
| P005 | `{}` | `{}` | n/a - no novelty_grading.md - this package's audit is owned by its own generator and was excluded from EXP-0059 on purpose
| P006 | `{}` | `{}` | n/a - no novelty_grading.md - this package's audit is owned by its own generator and was excluded from EXP-0059 on purpose
| P007 | `{}` | `{}` | n/a - no novelty_grading.md - this package's audit is owned by its own generator and was excluded from EXP-0059 on purpose
| P008 | `{}` | `{}` | n/a - no novelty_grading.md - this package's audit is owned by its own generator and was excluded from EXP-0059 on purpose
| P009 | `{}` | `{}` | n/a - no novelty_grading.md - this package's audit is owned by its own generator and was excluded from EXP-0059 on purpose

## 4. Rows the rule places at L2 or above where the legacy column was lower

These could change a gap statement, because they are collisions the earlier column understated:
- `P001` TSDQPP: rule L2 vs legacy L1
- `P004` 2026.gem-main.19|An: rule L3 vs legacy L2

**Decision under the rule fixed before the run.** Every paper's shipped audit reproduces from the sources it names (P005 ships no generated grading file and is recorded as n/a), and no newly-promoted L2+ row is missing from an audited population, so no novelty claim in any of the five packages changes. What changed is verifiability: every level a reader now meets in a collision table can be re-derived by one command, and the level that could not be re-derived is labelled as legacy rather than being cited as a grade.

wallclock: 0.0 s
