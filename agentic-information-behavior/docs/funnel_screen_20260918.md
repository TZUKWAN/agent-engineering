# Funnel screen of the w0_audit topics (2026-09-18)

Rule-based, evidence-backed triage of the 16 topics still at w0_audit; result: {'w1_audit_done': 12, 'w2_blocked': 4}.

| topic | assigned | local rows | files | collision evaluated | reason |
|---|---|---|---|---|---|
| T004 | w2_blocked | None | None | no records returned | primary dataset is not among the eight releases on local disk and has no reachable source here |
| T006 | w1_audit_done | 457130 | 47 | no records returned | local data present (457130 rows, 47 files, 9 columns); collision: query returned no records, so NOT evaluated |
| T007 | w1_audit_done | 457130 | 47 | no records returned | local data present (457130 rows, 47 files, 9 columns); collision: query returned no records, so NOT evaluated |
| T013 | w2_blocked | None | None | no records returned | primary dataset is not among the eight releases on local disk and has no reachable source here |
| T015 | w1_audit_done | 1659279 | 4 | no records returned | local data present (1659279 rows, 4 files, 2 columns); collision: query returned no records, so NOT evaluated |
| T018 | w1_audit_done | 457130 | 47 | no records returned | local data present (457130 rows, 47 files, 9 columns); collision: query returned no records, so NOT evaluated |
| T019 | w1_audit_done | 12290800 | 1230 | no records returned | local data present (12290800 rows, 1230 files, 6 columns); collision: query returned no records, so NOT evalua |
| T020 | w1_audit_done | 12290800 | 1230 | no records returned | local data present (12290800 rows, 1230 files, 6 columns); collision: query returned no records, so NOT evalua |
| T021 | w1_audit_done | 457130 | 47 | no records returned | local data present (457130 rows, 47 files, 9 columns); collision: query returned no records, so NOT evaluated |
| T024 | w1_audit_done | 457130 | 47 | no records returned | local data present (457130 rows, 47 files, 9 columns); collision: query returned no records, so NOT evaluated |
| T026 | w1_audit_done | 12290800 | 1230 | no records returned | local data present (12290800 rows, 1230 files, 6 columns); collision: query returned no records, so NOT evalua |
| T027 | w2_blocked | None | None | no records returned | primary dataset is not among the eight releases on local disk and has no reachable source here |
| T031 | w1_audit_done | 457130 | 47 | no records returned | local data present (457130 rows, 47 files, 9 columns); collision: query returned no records, so NOT evaluated |
| T032 | w1_audit_done | 457130 | 47 | no records returned | local data present (457130 rows, 47 files, 9 columns); collision: query returned no records, so NOT evaluated |
| T034 | w1_audit_done | 12290800 | 1230 | no records returned | local data present (12290800 rows, 1230 files, 6 columns); collision: query returned no records, so NOT evalua |
| T036 | w2_blocked | None | None | no records returned | primary dataset is not among the eight releases on local disk and has no reachable source here |

## Corrections during this screen

- D23: licence was read from `*.audit.json` (which has no licence key) instead of `dataset_registry.csv`; the first run therefore blocked 13 topics spuriously. Statuses were restored and the screen re-run.
- D24: the first collision step used an OR of loose title keywords, which returned zero records; treating that as 'no collision' would have been a false negative. It now uses an AND of the two most specific nouns and marks each topic informative/non-informative explicitly, so untested novelty is not reported as clear.

## What this does NOT do

It does not certify that the 12 w1_audit_done topics are novel, nor that they are worth a pilot; it only establishes that the data they need exists locally and is measurable, and that arXiv collision was *not* evaluated for most of them. The 4 w2_blocked topics are blocked on access, not on quality.
