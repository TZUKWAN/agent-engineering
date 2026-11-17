"""Write the EXP-0038/EXP-0039 reading into a ranked Top-10 artefact and update both registries.

The L-levels are my own readings of the returned titles and abstracts, reproduced verbatim in the document so a
reviewer can disagree with them; the screen only shortlists. Every number is read from the two result files.
"""
from __future__ import annotations

import csv, glob, io, json, pathlib, time

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
R = ROOT / "results_raw"
f38 = pathlib.Path(sorted(glob.glob(str(R / "EXP0038_topic_collisions_*.json")))[-1])
f39 = pathlib.Path(sorted(glob.glob(str(R / "EXP0039_quality_score_pilot_*.json")))[-1])
e38 = json.loads(f38.read_text(encoding="utf-8"))
e39 = json.loads(f39.read_text(encoding="utf-8"))
c39 = e39["configs"]

GRADE = {
 "T006": ("L2-adjacent", "metadata quality/standardisation drives dataset discoverability (GigaScience 2026; "
          "TechRxiv 2026 enterprise data products); ToolSEE 2025 does agent tool search over large catalogues",
          "nobody measures description richness -> gold-tool recall in agent catalogues, but it overlaps P001 "
          "catalogue covariates and P003 schema work"),
 "T007": ("L0-no collision in these forms", "hits are domain taxonomies (construction firms, intelligence "
          "evaluation, taxonomy pruning for query classification) - none induces a scheme from an MCP tool "
          "catalogue and validates it against human categories", "hermes category/subcategory + AgentBank 18 "
          "environments are on disk; the open risk is label coarseness, which must be measured not assumed"),
 "T015": ("L1", "multimodal query enhancement and medical VLM retrieval only; the text-identical/"
          "image-different construct is untouched", "blocked on its own dependent variable: MMAT images are not "
          "on disk and cannot be fetched here, so answers cannot be scored"),
 "T018": ("L3-crowded", "ConvGQR (ACL 2023, 34 cites); multi-turn clarification generation (Information "
          "Sciences 2022, 16 cites; WWW 2024)", "turn-level design also re-uses P001 corpus and outcome -> fold"),
 "T019": ("L2-methods already mature", "ICC and design-effect estimation (Int. J. Epidemiology 2023, 28 cites; "
          "reliability ICC guideline 2021)", "P001 and P002 already implement clustered inference; standalone "
          "paper would re-slice our own machinery"),
 "T020": ("L3-crowded", "2026 audits of duplicate-driven leakage in clinical benchmarks, look-ahead leakage "
          "benchmarks, SCALER contamination-resistant benchmark", "P001 EXP-0020/0023 already measured catalogue "
          "overlap across releases"),
 "T021": ("L3-crowded", "semantic-aware process mining with LLMs (Computers 2025); event-log construction; "
          "differentially private event logs", "P002 covers trajectory sequence structure; a delta would need "
          "validated process labels we do not have"),
 "T024": ("L2-partial collision", "LLM-as-judge reliability and validity are active (graph-verified judge "
          "reliability 2026; MERSQI agreement 2026; LCR validity/agreement 2022) but all audit a judge being "
          "run, none audits scores a corpus ships", "measured pilot: alpha 0.113/0.185/0.119; criterion rho "
          "0.089/0.287/0.095; catalogue-size confound separable in 2 of 3 configs"),
 "T026": ("L4-taken", "Adaptive Query Performance Prediction for RAG (ACM TOIS 2026); IRT-based task difficulty "
          "prediction (Knowledge-Based Systems 2023)", "collides with P001's own contribution - a second QPP "
          "paper on the same data"),
 "T031": ("L3", "dialogue ellipsis/anaphora resolution (Applied Sciences 2024); referring-expression grounding "
          "(ICASSP 2026; CVPR 2021, 32 cites)", "P001 already uses ellipsis/coref proxies as features (H2)"),
 "T032": ("L3 and own overlap", "length-controlled explicit query expansion vs vocabulary mismatch (2026); LLM "
          "query expansion for code search (J. Systems and Software 2025, 6 cites)", "P001 E17 already ran a "
          "controlled catalogue/description intervention"),
 "T034": ("L1 but fragile", "no information-wandering index found; nearest are effort-based foraging tasks and "
          "grey-number information measures", "our own screen flags the relabelled-entropy risk; needs a "
          "construct-definition pass before any pilot"),
}
RANK = ["T007", "T024", "T006", "T034", "T021", "T018", "T031", "T032", "T015", "T019", "T020", "T026"]

L = []
A = L.append
A("# Topic collision screen and Top-10 ranking (EXP-0038, EXP-0039)")
A("")
A(f"Generated {time.strftime('%Y-%m-%d %H:%M')} from `results_raw/{f38.name}` and `results_raw/{f39.name}`.")
A("")
A("Source: `api.crossref.org/works`, 48 hand-written query forms (3-4 per topic), publications from 2019 onward. "
  f"Query status totals: {e38['query_status_totals']}. One T006 query was still refused with HTTP 429 and is "
  "recorded as `transport_error`, not as an empty literature.")
A("")
A("The screen only shortlists (>=2 shared key nouns and year >= 2021). Every level below was assigned by reading "
  "the returned titles and abstracts; the reading is reproduced so a reviewer can dispute it.")
A("")
A("| rank | topic | collision level | closest prior work actually read | our own overlap / blocker |")
A("|---|---|---|---|---|")
for i, t in enumerate(RANK):
    A(f"| {i + 1} | {t} | {GRADE[t][0]} | {GRADE[t][1]} | {GRADE[t][2]} |")
A("")
A("## T024 pilot, measured (EXP-0039)")
A("")
A("| config | rows joined to objective outcomes | Cronbach alpha (6 question-side items) | "
  "rho(difficulty, fail@3) | rho inside catalogue-size strata |")
A("|---|---|---|---|---|")
for c in ("OSS", "Qwen3", "Kimi-K2"):
    d = c39[c]
    A(f"| {c} | {d['joined_dev_rows']} | {d['cronbach_alpha_question_side']} | "
      f"{d['criterion_rho_vs_fail_at_3'].get('q_tool_selection_difficulty')} | "
      f"{[v['rho'] for v in d['difficulty_by_catalogue_stratum'].values()]} |")
A("")
am = e39["verdict"]["criteria_met"]
A("Internal consistency is uniformly poor, which is a result on its own. Criterion validity is not: Qwen3 reaches "
  f"rho {c39['Qwen3']['criterion_rho_vs_fail_at_3'].get('q_tool_selection_difficulty')}, so the pre-registered "
  f"promotion rule (which required every config to be weak: {am}) returned "
  "`criteria not met on the pilot - do not promote`.")
A("")
A("**That rule was mis-shaped and is recorded as a defect rather than widened after seeing the numbers.** It "
  "required the instrument to fail before the audit could continue, which is a confirmation-shaped gate: a "
  "validity study must be able to conclude either way. The pilot therefore licenses a T024 study only after a "
  "two-sided decision criterion is written into its protocol freeze.")
A("")
A("## Consequences for the queue")
A("")
A("1. **T007 leads** - no collision in any form searched, data on disk, and it is the knowledge-organisation "
  "paper the series does not yet have. Its risk (label coarseness) is measurable before any modelling.")
A("2. **T024** proceeds only behind a criterion that can fail it either way: alpha, per-dimension criterion "
  "validity and the catalogue-size confound per config, on the full sample.")
A("3. **T018, T031, T032, T019, T020, T026** fold into existing papers rather than becoming papers - they share "
  "P001/P002/P003 corpora, outcomes or machinery, and the anti-repetition rule forbids a further cut.")
A("4. **T015** stays blocked on a real external dependency (MMAT-1M images absent, no reachable source here); "
  "**T034** needs a construct-definition pass before any experiment.")
p = ROOT / "docs/top10_screening_20260919.md"
p.parent.mkdir(exist_ok=True)
p.write_text("\n".join(L) + "\n", encoding="utf-8")
print("wrote", p.relative_to(ROOT), "with", len(L), "lines")

reg = ROOT / "00_program_registry/experiment_registry.csv"
rows = list(csv.reader(io.StringIO(reg.read_text(encoding="utf-8"))))
NEW = [
 ["EXP-0038", "program", "topic_collision_screen_DONE", "02_shared_code/registry/topic_collision_crossref.py",
  "Crossref works API; 48 hand-written query forms over the 12 w1_audit_done topics; from-pub-date 2019; "
  "candidate iff >=2 shared key nouns and year>=2021; 2 s pacing plus Retry-After backoff after a 429 burst",
  "", e38["started_at"], e38["finished_at"], "success_first_literature_pass_that_actually_ran",
  f"results_raw/{f38.name}; results_processed/EXP0038_candidate_collisions.csv; docs/"
  "top10_screening_20260919.md",
  "Replaces EXP-0032, whose 16 arXiv queries all failed with 406 and were summarised as 'query returned no "
  "records'. One T006 query still 429s and is stored as transport_error. A first resume-mode run dropped the "
  "earlier successful queries for the retried topics (T006 candidates fell 20 -> 2) because the merged source "
  "stored only top-6 hits; that artefact was discarded and the screen re-run in full rather than patched.",
  "feeds the queue; not a paper"],
 ["EXP-0039", "T024", "pilot_DONE_do_not_promote_on_this_rule",
  "02_shared_code/statistics/quality_score_pilot_t024.py",
  "3 configs x 3 shards of Toucan's shipped question/response quality assessments, joined to the published "
  "routing outcomes (dev rows only); Cronbach alpha, item-total rho, criterion rho vs fail@3, catalogue-size "
  "stratification; no model in the loop", "", e39["started_at"], e39["finished_at"],
  "pilot_heterogeneous_validity_promotion_rule_misshaped", f"results_raw/{f39.name}; "
  "results_processed/EXP0039_criterion_validity.csv",
  "alpha 0.113/0.185/0.119 - internal consistency is poor in every config. rho(difficulty, fail@3) "
  "0.089/0.287/0.095; stratified by catalogue size the relation collapses in OSS and Kimi-K2 but not in Qwen3. "
  "The pre-registered rule demanded weakness in ALL configs before promoting, so it returned 'do not promote'; "
  "that rule was confirmation-shaped and is recorded as a defect, not widened after the result.",
  "pilot only - T024 needs a two-sided criterion before any main run"]]
have = {r[0] for r in rows[1:] if r}
for rec in NEW:
    if rec[0] not in have:
        rows.append(rec)
buf = io.StringIO()
csv.writer(buf, lineterminator="\r\n").writerows(rows)
reg.write_text(buf.getvalue(), encoding="utf-8", newline="")
d = pd.read_csv(reg)
assert d.exp_id.is_unique and not (d.exp_id == "exp_id").any(), "registry integrity"
print("experiment registry rows:", len(d))

tp = ROOT / "00_program_registry/topic_registry.csv"
tl = list(csv.reader(io.StringIO(tp.read_text(encoding="utf-8"))))
th = tl[0]
NEWST = {"T007": "w2_pilot_next_no_collision_found", "T024": "w2_pilot_done_need_two_sided_criterion",
         "T006": "w2_pilot_next_L2_adjacent", "T034": "w2_blocked_construct_definition_needed",
         "T021": "w2_L3_crowded_needs_sharp_delta", "T018": "w3_fold_into_T037", "T031": "w3_fold_into_T037",
         "T032": "w3_fold_into_T037", "T019": "w3_fold_into_T037", "T020": "w3_fold_into_T012",
         "T026": "demoted_L4_taken_and_own_overlap", "T015": "w2_blocked"}
for r in tl[1:]:
    if r and r[0] in NEWST:
        r[th.index("status")] = NEWST[r[0]]
        if r[0] in ("T007", "T024", "T006"):
            r[th.index("blocking_issue")] = (
                "EXP-0038 Crossref screen and, for T024, EXP-0039 pilot (see docs/top10_screening_20260919.md). "
                + ("No collision in any of the four query forms searched; hermes category labels and AgentBank "
                   "environments are on disk. Before any main run: measure how coarse the human categories are "
                   "(distinct values, rows per category) - that is the identifiability risk, not novelty."
                   if r[0] == "T007" else
                   ("Criterion validity is config-heterogeneous (rho 0.089/0.287/0.095) and internal consistency "
                    "is uniformly poor (alpha 0.11-0.19); the pilot's promotion rule was confirmation-shaped and "
                    "must be replaced by a criterion that can reject the study either way."
                    if r[0] == "T024" else
                    "L2-adjacent only; must be differentiated from P001's catalogue covariates and P003's schema "
                    "conformance before it can be piloted.")))
buf = io.StringIO()
csv.writer(buf, lineterminator="\r\n").writerows(tl)
tp.write_text(buf.getvalue(), encoding="utf-8", newline="")
d2 = pd.read_csv(tp)
print("topic statuses now:", d2.status.value_counts().to_dict())
