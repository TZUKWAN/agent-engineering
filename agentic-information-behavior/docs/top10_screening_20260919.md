# Topic collision screen and Top-10 ranking (EXP-0038, EXP-0039)

Generated 2026-09-19 16:17 from `results_raw/EXP0038_topic_collisions_20260919T155842.json` and `results_raw/EXP0039_quality_score_pilot_20260919T161258.json`.

Source: `api.crossref.org/works`, 48 hand-written query forms (3-4 per topic), publications from 2019 onward. Query status totals: {'transport_error': 1, 'hits_returned': 47}. One T006 query was still refused with HTTP 429 and is recorded as `transport_error`, not as an empty literature.

The screen only shortlists (>=2 shared key nouns and year >= 2021). Every level below was assigned by reading the returned titles and abstracts; the reading is reproduced so a reviewer can dispute it.

| rank | topic | collision level | closest prior work actually read | our own overlap / blocker |
|---|---|---|---|---|
| 1 | T007 | L0-no collision in these forms | hits are domain taxonomies (construction firms, intelligence evaluation, taxonomy pruning for query classification) - none induces a scheme from an MCP tool catalogue and validates it against human categories | hermes category/subcategory + AgentBank 18 environments are on disk; the open risk is label coarseness, which must be measured not assumed |
| 2 | T024 | L2-partial collision | LLM-as-judge reliability and validity are active (graph-verified judge reliability 2026; MERSQI agreement 2026; LCR validity/agreement 2022) but all audit a judge being run, none audits scores a corpus ships | measured pilot: alpha 0.113/0.185/0.119; criterion rho 0.089/0.287/0.095; catalogue-size confound separable in 2 of 3 configs |
| 3 | T006 | L2-adjacent | metadata quality/standardisation drives dataset discoverability (GigaScience 2026; TechRxiv 2026 enterprise data products); ToolSEE 2025 does agent tool search over large catalogues | nobody measures description richness -> gold-tool recall in agent catalogues, but it overlaps P001 catalogue covariates and P003 schema work |
| 4 | T034 | L1 but fragile | no information-wandering index found; nearest are effort-based foraging tasks and grey-number information measures | our own screen flags the relabelled-entropy risk; needs a construct-definition pass before any pilot |
| 5 | T021 | L3-crowded | semantic-aware process mining with LLMs (Computers 2025); event-log construction; differentially private event logs | P002 covers trajectory sequence structure; a delta would need validated process labels we do not have |
| 6 | T018 | L3-crowded | ConvGQR (ACL 2023, 34 cites); multi-turn clarification generation (Information Sciences 2022, 16 cites; WWW 2024) | turn-level design also re-uses P001 corpus and outcome -> fold |
| 7 | T031 | L3 | dialogue ellipsis/anaphora resolution (Applied Sciences 2024); referring-expression grounding (ICASSP 2026; CVPR 2021, 32 cites) | P001 already uses ellipsis/coref proxies as features (H2) |
| 8 | T032 | L3 and own overlap | length-controlled explicit query expansion vs vocabulary mismatch (2026); LLM query expansion for code search (J. Systems and Software 2025, 6 cites) | P001 E17 already ran a controlled catalogue/description intervention |
| 9 | T015 | L1 | multimodal query enhancement and medical VLM retrieval only; the text-identical/image-different construct is untouched | blocked on its own dependent variable: MMAT images are not on disk and cannot be fetched here, so answers cannot be scored |
| 10 | T019 | L2-methods already mature | ICC and design-effect estimation (Int. J. Epidemiology 2023, 28 cites; reliability ICC guideline 2021) | P001 and P002 already implement clustered inference; standalone paper would re-slice our own machinery |
| 11 | T020 | L3-crowded | 2026 audits of duplicate-driven leakage in clinical benchmarks, look-ahead leakage benchmarks, SCALER contamination-resistant benchmark | P001 EXP-0020/0023 already measured catalogue overlap across releases |
| 12 | T026 | L4-taken | Adaptive Query Performance Prediction for RAG (ACM TOIS 2026); IRT-based task difficulty prediction (Knowledge-Based Systems 2023) | collides with P001's own contribution - a second QPP paper on the same data |

## T024 pilot, measured (EXP-0039)

| config | rows joined to objective outcomes | Cronbach alpha (6 question-side items) | rho(difficulty, fail@3) | rho inside catalogue-size strata |
|---|---|---|---|---|
| OSS | 6790 | 0.113 | 0.089 | [-0.006, -0.044, -0.019, 0.119] |
| Qwen3 | 8780 | 0.185 | 0.287 | [0.354, 0.121, 0.094, 0.578] |
| Kimi-K2 | 9190 | 0.119 | 0.095 | [0.029, 0.047, 0.062, 0.166] |

Internal consistency is uniformly poor, which is a result on its own. Criterion validity is not: Qwen3 reaches rho 0.287, so the pre-registered promotion rule (which required every config to be weak: {'variability_and_join': True, 'weak_criterion_validity': False, 'confound_separable': True}) returned `criteria not met on the pilot - do not promote`.

**That rule was mis-shaped and is recorded as a defect rather than widened after seeing the numbers.** It required the instrument to fail before the audit could continue, which is a confirmation-shaped gate: a validity study must be able to conclude either way. The pilot therefore licenses a T024 study only after a two-sided decision criterion is written into its protocol freeze.

## Consequences for the queue

1. **T007 leads** - no collision in any form searched, data on disk, and it is the knowledge-organisation paper the series does not yet have. Its risk (label coarseness) is measurable before any modelling.
2. **T024** proceeds only behind a criterion that can fail it either way: alpha, per-dimension criterion validity and the catalogue-size confound per config, on the full sample.
3. **T018, T031, T032, T019, T020, T026** fold into existing papers rather than becoming papers - they share P001/P002/P003 corpora, outcomes or machinery, and the anti-repetition rule forbids a further cut.
4. **T015** stays blocked on a real external dependency (MMAT-1M images absent, no reachable source here); **T034** needs a construct-definition pass before any experiment.

## Superseded by a pilot: T007 is killed by measurement (EXP-0040, 2026-09-19 16:22)

The ranking above put T007 first because nothing collided with it. Its real constraint is identifiability, and
EXP-0040 measured it: a scheme-induction study needs many items to cluster, a human category scheme to validate
against, and both on the SAME unit. In this corpus estate the three conditions never co-occur.

| corpus | what it offers | what it lacks |
|---|---|---|
| Toucan-1.5M | 2,168 distinct tool names, per-item catalogue on 100% of rows | any human category scheme - its only label column is `subset_name` (cardinality 1), i.e. provenance, not a taxonomy |
| hermes traces | human labels: category=9, subcategory=26 over 20,000 items | tool universe: only 26 distinct tool names, so a 26-way scheme over 26 tools is degenerate |
| AgentBank | a 19-way human task scheme (the environment directory split) over 53,205 items | a tool catalogue - the shards carry ['conversations', 'game_file', 'id', 'meta_information'] only, so there is nothing to induce a tool taxonomy from |

**Decision recorded by the pre-registered rule:** `NO-GO on label granularity/coverage - T007 folds into P003 or is killed`
(qualifying corpora = 1, needed 2).

T007 is therefore killed as a standalone paper rather than re-scoped into something smaller. The hermes finding
(26 distinct tool names across 20,000 items) is a second independent
measurement of the same catalogue-poverty that P001's EXP-0020/0023 reported, and is worth citing there.
The AgentBank 19-environment split remains usable as a *task-level* stratifier, which is how P001 already uses it.

