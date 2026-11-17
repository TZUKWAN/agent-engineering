# Program Status and Handoff — Agentic Information Behavior series

Generated 2026-09-19 (session pause at 17/20 goal turns). Verification tool: `02_shared_code/registry/package_audit.py`
writes `00_program_registry/package_audit.{csv,json}`; experiment record: `00_program_registry/experiment_registry.csv`
(37 rows). This document states what exists on disk, what is in flight, and what remains — it does not restate
claims that lack a result file.

## 1b A fourth paper is now in flight, and the topic queue has been screened for real

**P004 — "are the quality scores that agent corpora ship with themselves valid instruments?" (topic T024).**
`research_plan.md` and `protocol_freeze.md` exist; the main run **EXP-0043** is complete on 42,092 dev rows across
three teacher configs, with the objective criteria computed inside P004 (frozen BM25, imported gold resolution)
after D31 corrected a first attempt that had inherited P001's routing table. Measured: Cronbach alpha
0.179/0.184/0.191 (pooled 0.185) → **NOT_COHERENT in every config**; 7 of 12 dimensions `NOT_VALID` against their
named objective criterion, 1 `VALID` (completeness vs rule-extracted executed-tool agreement), 4 inconclusive; the
difficulty score's apparent criterion validity is catalogue size (pooled rho 0.103 → 0.003 partial); and the
customary `overall_score >= 4` gate keeps ~55% of rows while **distorting measured failure prevalence in all three
configs** (`GATING_DISTORTS`). `papers/P004_shipped_quality_score_validity/literature_matrix.csv` holds 45
Crossref-sourced records with DOIs (EMNLP 2025, NeurIPS 38, ACL 2025, Journal of Documentation), which also fixes
the novelty framing: the judge-bias literature audits a judge in use, not scores that arrive as data and cannot be
re-derived. **Package now complete** (EXP-0041 presence scan, EXP-0043 main, EXP-0044 criterion sensitivity;
paper/appendix/claims K1–K6/novelty/SOTA audit/dataset card/limitations/reviewer attack 11 rows/final audit/
reproduce.sh/5 tables/4 PDF figures), `package_audit.py` reports 0 missing and 0 weak, and its own gate reads
**NOT submittable yet** because three pre-declared checks are still open (§4).

**The fifth paper exists now: P005 (T013 + T014), package complete.** EXP-0047 finished the arXiv side of the
12-topic screen (48 queries, all reachable via curl) and called T013 the only L1 — **a judgement later withdrawn**
by EXP-0057/EXP-0058 (the screen's five phrase families never contained the words the colliding records use;
licence verifiability had already been measured for AI artefacts generally by 2310.16787, 2602.08816 and
2607.20300, all graded L4); the paper survives on a narrower claim, recorded as D-P11; T006 was **demoted to L4** by
three 2026 MCP-tool-description papers (2602.14878, 2602.18914, 2606.04769), T021/T015/T034 are crowded, T027/T028
crowded and short of human gold, T030 dies on self-overlap with P001, and T029/T036 are recorded as *undecidable*
because all four of their queries returned empty feeds. The decision record with the quoted titles is
`docs/topic_screen_arxiv_20260919.md`. P005 then ran pilot → freeze → census → sensitivity → hand check
(EXP-0048/0049/0050/0051) with its literature matrix built from Crossref *and* arXiv (EXP-0052). Its headline is the
weaker one its own pilot rule produced: **rights are declared at the release card in 7/8 and verifiable nowhere below
it in 8/8, while the same cards' numeric claims are exact in 27/27 testable comparisons.**

Earlier in the same funnel work (EXP-0038 Crossref + EXP-0040 pilot): **T007 was killed by measurement, not by
novelty** — no collision was found, but the three conditions a taxonomy paper needs never co-occur (Toucan: 2,168
tools, no human categories; hermes: a 9/26-way human scheme over 26 tool names; AgentBank: 19 human environments, no
tool catalogue). T024 became P004; T018/T019/T020/T026/T031/T032 were folded into existing papers to respect the
anti-repetition rule.

## 1 Paper packages

| paper | topic | package state (from `package_audit.csv`) | headline result files |
|---|---|---|---|
| **P001** routing-failure QPP | T037 | **complete: 0 missing, 0 weak** (paper, appendix, plan, freeze, 20-row literature matrix, SOTA audit, dataset card, 21 claims C1–C21, limitations L1–L17, deviations D1–D17 + D33/D34, 27-row reviewer attack, final audit, reproduce.sh with a claim-driven evidence gate, 21 tables, 6 figures, env record) | `results_raw/EXP0012_FINAL_TEST_*` (one evaluation), `EXP0023_*` (cross-corpus AUROC 0.6939), `EXP0024_*` (dense comparator; cross-ranker 0.6451 < 0.65), `EXP0025_*` (clean-room replication, tolerance declared), `EXP0028_*` (learning curve), `EXP0033_*` (second-coder agreement), `EXP0034_*`/`EXP0035_*` (sample is one query subset; transfer fails on single-turn-diversify), `EXP0046_*` (§7.8 error analysis: recall at 0.5 is 0.095/0.171/0.021 and the misses are reachable-but-missed, not lexically unreachable) |
| **P003** metadata interoperability | T012 | **complete: 0 missing, 0 weak** (incl. `fig0_framework`, `fig1_coverage_heatmap`, `fig2_concept_recoverability`, `fig3_containers_and_loss`, 5 tables, 8 claims, novelty audit with failed queries listed) | `results_raw/EXP0027_*` (pilot), `EXP0029_*` (frozen main), `EXP0030_*` (corrected probes), `EXP0036_*` (randomised row resample → matrix STABLE), `EXP0045_*` (independently derived concept inventory). Headline: only **2 of 12** concepts recoverable in all 8 corpora; outcome 1/8, observation 2/8; 5 corpora have no dependence key; MMAT-1M is jsonl-only with 300/300 sampled media references unresolvable. **Under a presence-only inventory the headline becomes 1 of 12**, which is reported rather than suppressed (K8) |
| **P002** ISP stage measurement | T008 | **complete: 0 missing, 0 weak** (paper, appendix, plan, freeze, literature matrix (5 records), novelty audit, pilot report, dataset card, deviations D22/D25/D26/D27/D28, 6-claim evidence matrix, limitations (7 items), reviewer attack (11), final audit, reproduce.sh, 3 vector figures, 5 tables, env record, result+log copies) | `results_raw/EXP0026_*` pilot; **`EXP0031_p002_stage_main_20260919T002148.json`** main: 240,000 SWE-ZERO trajectories / 3,566,324 turns / 3,764 instances vs 20,524 AgentTrove trajectories / 116,581 turns / 15 instances. Headline: RQ2 clears its CI null (B2-B4 = 0.0957 bits/turn, CI 0.0845-0.1086) but **misses both frozen magnitude floors** (4.593 vs 5.0 and 1.422 vs 2.0 bits/trajectory), the **previous-command model outranks the stage-history model**, and AgentTrove is only 9.9% codable so the replication is **untestable, not negative**. Gate: NOT submittable - the frozen RQ4 agreement step needs a human coder this environment does not have |
| **P004** shipped quality-score validity | T024 | **complete: 0 missing, 0 weak** (paper, appendix, plan, freeze, 45-record Crossref literature matrix, novelty audit, SOTA audit, dataset card, 6 claims K1–K6, limitations, reviewer attack (11), final audit, reproduce.sh, 5 tables, 4 PDF figures, env record) | `EXP0041_*` (presence scan: which corpora ship scores at all), `EXP0043_*` (main, 42,092 dev rows, criteria recomputed in-pipeline after D31/D32), `EXP0044_*` (three executed-tool extraction rules). Headline: Cronbach α 0.179/0.184/0.191 → **NOT_COHERENT in every config**; 7 of 12 dimensions NOT_VALID against their named objective criterion, 1 VALID, 4 inconclusive; difficulty's criterion validity is catalogue size (ρ 0.103 → 0.003 partial); the customary `overall_score ≥ 4` gate keeps ~55% of rows and **distorts measured failure prevalence in all three configs**. Gate: NOT submittable (3 open checks) |
| **P005** declared-but-not-verifiable rights metadata | T013 (+T014) | **complete: 0 missing, 0 weak** (paper, appendix, plan, freeze written before the scan, 80-record literature matrix from Crossref *and* arXiv, query log incl. empty queries, novelty audit, SOTA audit, dataset card, 7 claims K1–K7, 9 limitations, reviewer attack (11), final audit, reproduce.sh with a claims-driven evidence gate, 7 tables, 4 PDF figures, env record, pilot report) | `EXP0048_*` pilot (verdict `PROSE_ONLY`, binding); `EXP0049_*` census — 2,916 files, 1,433 parquet footers, 15,789,996 exact rows, **L1/L5/L6/L7 all 0/8 vs L2 7/8 (6 of them the same `apache-2.0`)**, 27/27 size comparisons at ratio 1.000, 1 disagreement (code-act's `size_categories` band vs its own splits), 3 multi-component releases with 0 per-component rights; `EXP0050_*` lexicon sensitivity (licence 0/8 under both lexicons, provenance 0/8 → **4/8** broad, so H1 is established for rights and partially refuted for provenance); `EXP0051` hand check (single coder, caught a false negative → D-P6). H3 and H4 **refuted** by their pre-declared patterns. Gate: package complete, NOT submittable (second coder + value-level rights scan) |



## 2 In flight (parked, resumable)

**Nothing is parked mid-run.** EXP-0047 (the arXiv side of the 12-topic screen) finished and is recorded with its
decisions in `docs/topic_screen_arxiv_20260919.md`; P005's experiments (EXP-0048…EXP-0053) all have result files, and
the funnel probe EXP-0054 closed T004. The next topic to act on: none is at `w1_audit_done`; the live queue is
T021/T027/T028/T029/T030/T034/T036 (all crowded, undecidable or self-overlapping — see
`docs/topic_screen_arxiv_20260919.md`), so the productive next steps are the **per-paper open items in §4**, not a new
topic. Two candidate directions that survive the anti-repetition rule are named at the end of §4.

**Closed since the last pause:** EXP-0034/0035 (P001's sample is one query subset, and the predictor does not
transfer to `single-turn-diversify`), EXP-0036 (P003's matrix is stable under randomised row resampling),
EXP-0045 (P003's headline becomes 1-of-12 under an independently derived, presence-only concept inventory),
EXP-0041/0043/0044 (P004's whole evidence base), and EXP-0046 (P001 §7.8 error analysis). Two harness lessons from
EXP-0046 are recorded as deviations instead of being quietly fixed: **D33** — the first version read
`catalog_json` with the builder's non-persisted key names, every catalogue tokenised to nothing, and the taxonomy
therefore reported "1,323 of 1,323 misses have no lexical bridge", i.e. a restatement of the ranker's definition;
the corrected run reverses that conclusion, and the script now aborts when a schema tokenises to empty. **D34** —
P001's `reproduce.sh` evidence loop contained literal `\ \n` sequences from a one-shot heredoc, so it could only
ever misreport MISSING; it now derives its path list from `claims_evidence_matrix.csv` (21 claims / 51 paths / 0
missing, verified by running the block), which immediately exposed six claims whose evidence cells held prose or a
bare experiment id — those pointers were moved, not deleted. The same audit found and removed 39 result/log copies
belonging to sibling papers from P001's package mirror (`package_p001.py: owns()`).


## 3 Environment facts that constrain the design (measured, not assumed)

- Interpreter `D:/Environment/anaconda3/python.exe` (3.11.7); `python` on PATH is a WindowsApps stub.
- GPU present (RTX 3060 12 GB) but installed torch is a **CPU-only build**; no `sentence_transformers`/
  `transformers`/`faiss`; a clean venv was built from PyPI with the pinned versions used in P001's replication.
- Network: `export.arxiv.org` and PyPI reachable; **huggingface.co, github.com, w3.org, schema.org,
  dublincore.org unreachable**, so no new external corpus and no non-arXiv venue search could be verified.
  Two transport facts, both measured here rather than recalled: (i) the arXiv export API refuses **python
  `urllib` with HTTP 406 for every header variant** (no headers, curl's UA, `Accept: */*`, `Accept:
  application/atom+xml`) while `curl` returns 200 with entries for the *same* URL — so literature code shells out to
  curl; (ii) `api.crossref.org` and `api.openreview.net` work, `api.semanticscholar.org` returns 429. An earlier
  "arXiv is throttled / 406 after ~40 queries" note in this file was a mixture of that client block and genuine
  bursts; queries spaced ≥3 s over curl have been returning records all session.
- Policy: no model inference API during analysis, so dense encoders are limited to models trained from scratch
  on our own data (done, EXP-0024) and LLM judges are not used anywhere.

## 4 What remains for the objective as written

1. ~~**P002**: main result → package~~ **DONE** — EXP-0031 executed, package generated and audit-clean; what
   remains there is a human coder for the frozen RQ4 step and a second corpus the codex can reach (§1 table).
2. **Funnel — both literature channels now actually run, and the screen has been spent once.** EXP-0038 gave all 12
   live topics a real Crossref pass (`docs/top10_screening_20260919.md`), T007 was killed by measurement and T024 became
   P004. EXP-0047 then ran the arXiv side (48 single-phrase × `cat:` queries with per-query status) and its decision
   record is `docs/topic_screen_arxiv_20260919.md`: T006 demoted to L4 by three 2026 MCP-description papers,
   T021/T015/T034 crowded, T027/T028 crowded and short of human gold, T030 killed on self-overlap, T029/T036
   undecidable (all queries empty). Its one apparent L1 became **P005** (T013+T014), package complete, positioned against the graded nearest neighbours. Remaining live
   candidates, in rough order of measured feasibility: **T004 (next pilot), T013's follow-up value-level rights scan,
   T021, T027, T028, T029, T030, T034, T036**; 8 topics stay at `w2_blocked`, of which T015 (MMAT images) is blocked
   by data access, not by design. Nothing may be promoted because the queue is long — the spec's rule is that a topic
   without a gap dies.
   `02_shared_code/literature/harvest.py` (arXiv, curl transport) and `crossref_harvest.py` are the shared, paced,
   status-labelling entry points; `api.semanticscholar.org` is not usable (429) and non-arXiv venues are reachable only
   through Crossref/OpenReview, which is what the matrices say.
3. **P001 pre-submission.** ~~larger manual error review~~ **DONE (EXP-0046 → §7.8, tables 17–19, C20/C21, L17)**:
   the misses are reachable-but-missed queries, not the lexically unreachable ones, and the 0.5 cut-off is reported
   as unusable rather than quietly re-thresholded. ~~sample-scope~~ **DONE (EXP-0034/0035, L15/L16, C19)**. Still
   open: (a) a **human** second coder — EXP-0033's mechanical coder agrees 97.5% but is never more permissive, and
   κ is inestimable because the human pass is single-category, so human inter-coder reliability is still owed;
   (b) a randomised resample of P001's own 15k-row sample, which needs a snapshot + digest check against
   `01_datasets/manifests/routing_sample_identity.json` before any rebuild (rebuild-discipline rule); (c) the
   pretrained-encoder feasibility note (weights are unreachable; only from-scratch models are admissible).
4. **P003 pre-submission.** ~~randomised sampling~~ **DONE (EXP-0036: the 12×8 matrix is STABLE under uniform
   random row positions, so the headline is not a head-of-file artefact)**; ~~independently derived concept list~~
   **DONE (EXP-0045: a mechanical, presence-only inventory derived from the 8 releases moves the headline from 2 to
   1 of 12, and the synonym-resolution order that produced a spurious LIST_DEPENDENT first is recorded in the
   script)**. Still open: a **second human** re-derivation of the 30 self-audit cells — the deterministic
   re-derivation exists, the human one does not.
5. **P004 pre-submission — its own gate names three substantive gaps** (`final_audit.md`): (a) the executed-tool
   criterion needs human coding that this environment cannot supply; (b) only one corpus ships the object, so
   external validity is a stated limit rather than a tested one; (c) the pilot's promotion rule was confirmation-
   shaped (logged as D30) and the main run therefore stands on the frozen bands in `protocol_freeze.md` alone.
   What would change the conclusion: a second release shipping comparable scores, or human-coded call ground truth
   that rescues the strict-name extraction variant.
6. **P005 pre-submission.** ~~value-level rights scan~~ **DONE (EXP-0053 → claim K8, appendix A7)**: 15,751 rows /
   384.9 MB of cell text searched, 3 payload hits in one release and 0 in the other seven, every hit inspected and
   rejected as model-written prose *about* licences rather than a notice *of* one — the headline survived a test that
   could have refuted it, and building that test exposed three of our own defects (D-P8 the card counted as payload,
   D-P9 no jsonl coverage, D-P10 unbounded file reads). Still open: (a) a **second coder** for the artefact and
   disagreement decisions (limitations L6, A9) — the hand check is one person's; (b) the unread-file residue: the scan
   covers ≤40 random files per release (coverage recorded in `table8`), so a rights notice confined to unread files
   would still be missed.
7. **Literature depth — graded, and the expansion step is now done for all five.** Abstracts were fetched for
   every screened identifier (EXP-0056: 189 of 287 carry one; 94 Crossref records deposit none and stay
   `title_only`), all 287 were rule-graded L0-L4 against each paper's own construct families with the matched
   terms kept as evidence (EXP-0057; hand-check list `docs/literature_grading_review_20260920.md`), P005's
   audit was rewritten and its gap narrowed (D-P11), P001-P004 carry `novelty_grading.md` (EXP-0059: no L4
   among them, two P004 records hand-downgraded to L1), and EXP-0060 mined each paper's collision vocabulary
   from its own retrieved records and re-queried with it (32 informative queries, ~450 previously-unseen
   records examined): **no new construct-level collision for P001-P004**, and P005's two extra records are
   positive controls, not competitors. Each package carries `novelty_expansion_exp0060.md`. Remaining
   literature work is per-paper: P001's expansion used the all-abstracts fallback because only one of its 20
   records graded L2+, so a construct-poor phrase cannot produce a hit; a hand-written family for QPP-on-
   agents is still worth running before submission.
8. Cross-cutting: no paper currently claims a SOTA result, and each `sota_audit.md` documents why the five
   fair-comparison conditions fail against ToolRet/Tool-DE/AgentSearchBench numbers.

**Two directions that would survive the anti-repetition rule** (if more papers are wanted, these are the honest
candidates, not further cuts of the existing four units): (i) a **re-user behaviour study** — how information
professionals actually read a dataset card and what they conclude (P005 §10 names this as the unanswered
information-behaviour question; it needs participants, not a corpus); (ii) a **longitudinal re-audit** of the same
eight releases, which would turn P005's cross-sectional census into a change measurement and would need no new data
access beyond re-fetching the snapshots (blocked here by the same unreachable hosts).

## 5 Anti-repetition rule for the next session

P001's 20-item package and its 21 claims are **done** — extending it means new experiments (the three items in §4.3),
not re-narrating the existing tables. The five papers must not re-cut each other's data: P003's unit is the
corpus/schema level (what a converter can carry), P002's is the turn/sequence level (what a process claim needs),
P001's is the per-query failure prediction on Toucan only, P004's is the **instrument** level (whether a score a
corpus ships about itself measures what its name claims), and P005's is the **release as a rights object** (what a
re-user can verify below the card). Note the adjacency P005 must keep outgrowing: its §10 re-user-question is a
behaviour study, and its A7 threat test is about payload text — neither is a P003 concept-portability claim, and the
two matrices must stay separate. The shared auditors
(`canonical_conformance_audit_p003.py`, `isp_stage_coder.py`, `analyze_routing_failure.py`,
`p004_common.py`, `governance_metadata_pilot_p005.py`) are the reuse points; `p004_common.load_config` is the
canonical way to recompute a frozen-BM25 criterion inside a new script, `governance_metadata_pilot_p005.py` supplies
the corpus registry (`CORPORA`), artefact sets and licence classifier that EXP-0049/0053 import rather than re-type,
and `error_analysis_p001.py: cat_tokens/tool_field` is the canonical way to read `catalog_json`'s persisted `n/d/p`
keys — copying the naive `name`/`desc` access is what produced D33.

## In flight at the 2026-09-20 handoff

*Final update of this session:* the transfer job is running under the agent background runner (one worker seen at ~299 MB resident, i.e. past the 44k-document catalogue load); its log is still empty because the first print follows that load. The EXP-0081 channel finding was also re-worded to name the **call** rather than the endpoint family - on hf-mirror, dataset_info() is uniform-answer while list_repo_files discriminates - in limitations L6, external_benchmark_probe.md and the EXP-0081 recorder template, so a rebuild cannot restore the imprecise sentence.

**EXP-0085 RECORDED - and it withdraws EXP-0084's verdict.** A 6-row probe across all three catalogue partitions found 6/6 (arm A) and 6/6 (arm B) rows with a frozen feature outside the Toucan dev min/max range, and both arms emit a constant p=1.0 with no NaN/inf. A saturating logistic cannot rank, so the below-chance AUROC measured extrapolation, not absent signal - and EXP-0082's 0.6536 is demoted on the same grounds. Registered: EXP-0085, claim C25, limitations L21, a gate row reading OPEN, a deviation, and a correction banner atop `external_toolret_eval_transfer.md`. Open next: a support-respecting external test (matched-pool calibration, or restricting external rows to catalogues inside the dev feature range, or a rank statistic that does not depend on a saturating probability), then the standing human second-coder gaps.

When it lands, the closing sequence is fixed and nothing else should be inferred from the number:
1. register it as **EXP-0084** (the EXP-0083 id is already taken by the ingestion audit - `external_toolret_eval_ingestion.md`),
   writing the registry row by column name, never by position;
2. add claim **C24** to P001's `claims_evidence_matrix.csv` with `direction` set from the measured AUROC and the
   subset-clustered interval, and status worded to the band result only;
3. add a limitations entry next to L19 stating the sample size, the union-catalogue construct, and that this is not a
   leaderboard reproduction;
4. move the final-audit row from "EXECUTED on an external corpus - borderline (EXP-0082)" to name both external arms
   only if EXP-0084's number is reported with its interval;
5. guard every recorder edit on a content marker (not a next-free id) and re-run it twice against an md5 snapshot.

Already finished this session and citable: EXP-0081 (channel probe - arXiv and GitHub raw reachable, HF *dataset file
download* discriminative, `toolret` not on the reachable PyPI index), EXP-0082 (training-partition transfer, AUROC
0.6536, row CI 0.6349-0.6733 against a band frozen at 0.65 - point estimate passes, interval straddles it, and arm B
came out below arm A against the pre-specified leakage direction), EXP-0083 (eval release ingested and censused:
7,961 queries, 44,453 tools, 100% gold resolution on the union partition).

Still owed at the 2026-09-20 handoff, and what replaced it: human second coders (P001 kappa, P002 60-turn retest,
P003 30 self-audit cells, P005 artefact/disagreement decisions), P001's larger manual review of main predictions,
T027's sharp-delta decision, 64 literature records still graded from titles alone, and the 18 live w1/w3 funnel
candidates.

## The programme went fully automated on 2026-09-21: no human step remains in any package

The instruction now in force is that nothing may wait on a person. Every owed item that was written as "needs a human
coder" has been either executed as a machine measurement or restated as a limit of scope. The rule applied each time:
an automated substitute may replace a human step **only** where it measures something real, it is registered as a
substitution rather than passed off as the original, and it is not allowed a weaker bar than the test it replaces.

* **P002 / RQ4 - EXP-0087, executed and failed.** The 60-turn hand retest became rubric invariance: a second codex
  written from the protocol's own definitions, different decision procedure and cue table, 900 turns from 844
  instances. Percent agreement 0.6467, **kappa 0.5019** (instance-clustered 0.4659-0.5406), alpha 0.4985, 0.5612 on
  the protocol's 60-turn subsample, against the bar of 0.75 frozen before any of it was run. The bar was not moved.
  P002's submission gate stays open *on a measured result*, its distribution claims are labelled rubric-sensitive
  (K7), and `final_audit.md`/`paper.md` now say "executed, failed" rather than "needs a human" - generated from the
  artefact so a rebuild cannot restore the old sentence.
* **P001 / DV - EXP-0088.** Three join rules for the gold index agree at kappa 0.9956 and 0.9927 with DV changing on
  0.0004/0.0006 of rows, so the failure label is join-rule invariant (C26).
* **P003 / the audit itself - EXP-0089 and EXP-0090, and the audit lost.** A second auditor with no access to the
  per-corpus mapping re-derived all 96 cells: usable agreement 0.9062, kappa 0.7236, **9 boundary crossings**, both
  pre-declared tolerance triggers firing. Three crossings were confirmed real - Toucan-1.5M stores `messages` as a
  JSON string and the frozen accessor did `list(m or [])`, which iterates characters, so two message-derived concepts
  were scored `absent` at coverage 0.0; AgentBank's `Observation:` text was carried by a parser that existed but was
  never hypothesised for it. EXP-0090 corrected the probes (appended after the frozen list, same rows, same
  thresholds): the all-corpus concept count moves **two to three**, observation recoverability 2/8 to 4/8, Toucan loss
  0.4167 to 0.25, and §5.4's claim that "verdicts are robust to a probe fix" is withdrawn as an n=1
  over-generalisation. The corrected matrix is what the paper now cites; `paper.md`'s headline count and concept names
  are read from the matrix, so no prose edit was needed to change it.
* **P005 / the hand check - EXP-0091** re-decides every RQ4 disagreement instance with a matcher that shares no code
  with EXP-0049 (indentation scan instead of a YAML loader, directory-scope attribution instead of path substring,
  token presence instead of substring). H3's refutation rests on a single instance, so the pre-declared rule is about
  the per-release boolean, not a count. Registered when it lands.
* **P001 / kappa on single-category labels** stays a declared limit rather than a fake measurement: the routing DV is
  one label per query, so an agreement statistic between two rules is meaningful (EXP-0088) while a "second human
  coder" substitute for a coding *task* that does not exist would not be.

Two verifier classes were added on the way, each from a defect this session actually produced: duplicate log rows
(a recorder's idempotency guard tested for an English phrase inside a row it writes in Chinese, so a rebuild appended
D51 alongside D50), and empty interpolation in generated prose (P003's `Concept-wise recoverability (of 8):` printed
nothing after the colon in every build since the file existed, which no pointer or file-existence check could see).
`final_audit.md` may no longer assert a claim or deviation count that differs from the file it describes.
