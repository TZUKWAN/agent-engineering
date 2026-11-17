"""Record EXP-0047 (arXiv-side novelty screen) into the programme: doc + topic statuses + registry row.

Every collision title quoted here is read from the result file; the L-grades and status changes are the author's
judgement after reading those titles, and are labelled as such in the generated document.

    python 02_shared_code/registry/record_exp0047_funnel.py
"""
from __future__ import annotations

import csv, glob, io, json, pathlib, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
REG = ROOT / "00_program_registry"
DOCS = ROOT / "docs"
NAME = sorted(glob.glob(str(ROOT / "results_raw" / "EXP0047_arxiv_topic_screen_*.json")))[-1]
D = json.loads(pathlib.Path(NAME).read_text(encoding="utf-8"))
ROLL, RECS = D["rollup"], D["records"]
BY = {}
for r in RECS:
    BY.setdefault(r["topic"], []).append(r)

# Judgement applied after reading the returned titles (not a script output). Kept as data so the doc, the topic
# registry and the registry note cannot drift apart.
GRADE = {
    "T013": ("L1", "gap: only 1 of 4 queries returned anything (model cards -> AI System Cards 2509.20394); the "
             "licence/provenance/attribution metadata OF AGENT TRAJECTORY CORPORA is not the object of any returned "
             "paper", "w2_pilot_next_L1_gap_p005_candidate"),
    "T014": ("L2", "adjacent: science-software linkage (2104.05891) and repository availability (2207.12879) exist, "
             "but no agent-corpus treatment; and link availability cannot be measured from this machine (HF/GitHub "
             "unreachable), so only the structural part is feasible", "w2_merge_into_T013_p005"),
    "T004": ("L2", "adjacent: instruction-tuning generalisation from templates (2505.14425) is close, but the "
             "human-vs-synthetic contrast inside shipped agent corpora is not taken", "w2_pilot_next_L2_adjacent"),
    "T006": ("L4", "taken: 2602.14878 'MCP Tool Descriptions Are Smelly', 2602.18914 'From Docs to Descriptions', "
             "2606.04769 'Description-Code Inconsistency in Real-world MCP Servers' - measurement AND benchmark AND "
             "improvement are all published in 2026", "demoted_L4_taken_by_three_2026_papers"),
    "T021": ("L4", "taken: agentic process mining agenda 2609.07984 plus a saturated conformance-checking literature "
             "(12/12 and 12/12 relevant on its two broad queries)", "demoted_L4_taken"),
    "T015": ("L4", "crowded: underspecified-query and multimodal-entity-linking benchmarks are active "
             "(8/9 and 12/12 relevant), and the corpus's images are still absent locally",
             "demoted_L4_crowded_and_data_blocked"),
    "T027": ("L3", "crowded: controlled instruction-complexity augmentation (2505.18557) and ill-defined-task "
             "evaluation (2603.17067) cover the construct; readability-vs-execution link not taken",
             "w2_L3_crowded_needs_sharp_delta"),
    "T028": ("L3", "crowded: entangled/contradictory instruction evaluation exists (2503.13222, 2608.22138, "
             "2502.14494); a detection method for shipped corpora would also need two human coders",
             "demoted_L3_crowded_and_needs_human_gold"),
    "T030": ("L3", "the 'constraint density' phrase returns CSP physics, not instruction work - so novelty is not "
             "the problem; the problem is that it re-slices P001's own covariates", "killed_self_overlap_not_novelty"),
    "T029": ("undecidable", "all four queries returned empty feeds; per this screen's own rule that is a query-form "
             "failure, not evidence of a gap", "w2_screen_incomplete_empty_feeds"),
    "T034": ("L4", "taken: exploratory search / information foraging is a dense, established area (12/12 relevant on "
             "both broad queries)", "demoted_L4_crowded"),
    "T036": ("undecidable", "all four queries returned empty feeds", "w2_screen_incomplete_empty_feeds"),
}
PAPER = {"T013": "P005 (candidate)", "T014": "P005 (merged in)"}

DOC = DOCS / "topic_screen_arxiv_20260919.md"
L = ["# arXiv-side novelty screen of the 12 live topics (EXP-0047)", "",
     f"Generated {time.strftime('%Y-%m-%d %H:%M')} from `{pathlib.Path(NAME).name}`. Transport: curl against "
     "`https://export.arxiv.org/api/query` (python urllib is refused with 406 here for the same URL). Query form: "
     '`abs:"one phrase"` optionally narrowed by `cat:X` - never two phrases ANDed, which this API answers empty.',
     "", "**Reading rule enforced by the screen**: `zero_records` is not evidence of a gap, and a topic whose every "
     "query came back empty is marked undecidable rather than novel. L-grades below are the author's judgement after "
     "reading the returned titles; the titles and arXiv ids they rest on are printed next to each grade so a reader "
     "can disagree with the grade without having to re-run the retrieval.", "",
     "| topic | queries | informative | zero records | collision candidates | L | status after this screen |",
     "|---|---|---|---|---|---|---|"]
for t in sorted(ROLL):
    v = ROLL[t]
    L.append(f"| {t} | {v['queries']} | {v['informative']} | {v['zero_records']} | "
             f"{v['collision_candidates']} | {GRADE[t][0]} | `{GRADE[t][2]}` |")
L += ["", "## Why each grade, and the records it rests on", ""]
for t in sorted(ROLL):
    g, why, st = GRADE[t]
    L.append(f"### {t} — {g} → `{st}`" + (f" → **{PAPER[t]}**" if t in PAPER else ""))
    L.append(why)
    for r in BY[t]:
        got = ", ".join(f"{c['year']} {c['id']} “{c['title']}”" for c in r["collision_candidates"][:3]) or "—"
        L.append(f"- query `{r['query_string']}` → **{r['status']}**, {r['n_returned']} returned, "
                 f"{r['n_keyword_relevant']} keyword-relevant: {got}")
    L.append("")
L += ["## Consequences for the queue", "",
      "1. **T006 dies by literature, not by feasibility.** Its instrument exists locally and the audit would have "
      "been easy to run; three 2026 papers already measure MCP/tool-description quality, benchmark it and attack "
      "description-code inconsistency. Running it anyway would have produced a fourth cut of someone else's result.",
      "2. **T021, T015, T034 are crowded**, and T028/T027 are crowded in their construct while also needing human "
      "gold this environment cannot supply. T030 dies on the anti-repetition rule (its own covariates are P001's), "
      "not on novelty.",
      "3. **T013 is the only L1** - one relevant record in four queries - so it is the fifth paper's candidate. Its "
      "unit (dataset-level governance metadata: licence declarations, provenance, attribution, redistribution "
      "permission) is none of the four existing papers' units, which is the anti-repetition test it has to pass. "
      "T014 merges in as its reproducibility/reference component, because link *availability* cannot be measured "
      "from this machine (the unreachable-host list is in `PROGRAM_STATUS.md` §3) while reference *structure* can.",
      "4. **T004 stays alive at L2** as the next candidate after T013, and T029/T036 must be re-screened with "
      "different phrase families before anything is claimed about them.", ""]
DOC.write_text("\n".join(L) + "\n", encoding="utf-8", newline="")
print(f"[e47] wrote {DOC.relative_to(ROOT)}")

# ---------------------------------------------------------------- topic statuses
TP = REG / "topic_registry.csv"
hdr = list(csv.reader(io.StringIO(TP.read_text(encoding="utf-8"))))[0]
rows = list(csv.DictReader(open(TP, encoding="utf-8")))
before = {r["topic_id"]: dict(r) for r in rows}
changed = {}
for t, (_, _, st) in GRADE.items():
    for r in rows:
        if r["topic_id"] == t and r["status"] != st:
            changed[t] = (r["status"], st)
            r["status"] = st
with open(TP, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=hdr)
    w.writeheader()
    w.writerows(rows)
after = {r["topic_id"]: dict(r) for r in csv.DictReader(open(TP, encoding="utf-8"))}
assert set(after) == set(before)
for tid, a in after.items():
    for k in hdr:
        if k != "status" or tid not in changed:
            assert a[k] == before[tid][k], f"{tid}.{k} changed unintentionally"
print(f"[e47] topic statuses updated: {len(changed)} rows; only the status column moved")

# ---------------------------------------------------------------- registry row
buf = io.StringIO()
csv.writer(buf, lineterminator="\r\n").writerow([
    "EXP-0047", "PROGRAM (funnel)", "arxiv_novelty_screen_DONE",
    "02_shared_code/literature/arxiv_topic_screen.py",
    "12 live topics x 4 single-phrase queries, each optionally narrowed by cat:; https export API via curl; 3s pace; "
    "per-query status informative/zero_records/transport_error; keyword-relevance filter per topic; checkpoint after "
    "every query so an interruption cannot lose evidence", "none (retrieval, not estimation)",
    D["started_at"], D["finished_at"], "success_10_topics_have_collisions_2_undecidable",
    f"{pathlib.Path(NAME).name}; results_processed/EXP0047_topic_screen_rollup.csv; "
    f"docs/topic_screen_arxiv_20260919.md; results_raw/superseded/(first rollup, verdict-rule bug)",
    "T006 demoted to L4 by three 2026 MCP-description papers (2602.14878, 2602.18914, 2606.04769); T021/T015/T034 "
    "L4 crowded; T027/T028 L3 crowded and short human gold; T030 killed on self-overlap not novelty; T029/T036 "
    "undecidable (all queries returned empty feeds - the trap this screen was written to refuse to interpret as a "
    "gap). Only T013 is L1 (1 relevant record in 4 queries) and becomes P005's candidate, with T014 merged in as its "
    "reference-structure component because link availability is not measurable from this machine.",
    "yes - as the funnel decision record in docs/topic_screen_arxiv_20260919.md"])
txt = TP.parent.joinpath("experiment_registry.csv").read_text(encoding="utf-8")
if "EXP-0047" not in txt:
    p = REG / "experiment_registry.csv"
    p.write_text(txt.rstrip("\r\n") + "\r\n" + buf.getvalue().rstrip("\r\n") + "\r\n", encoding="utf-8", newline="")
    print("[e47] registered EXP-0047")
import pandas as pd
d = pd.read_csv(REG / "experiment_registry.csv")
assert not d.exp_id.duplicated().any()
print(f"[e47] registry rows={len(d)}")

SR = ROOT / "results_raw" / "SUPERSEDED_ARTIFACTS.json"
sj = json.loads(SR.read_text(encoding="utf-8"))
if not any(e["file"].startswith("EXP0047") for e in sj["superseded"]):
    sj["superseded"].append({
        "file": "EXP0047_arxiv_topic_screen_20260919T175813.json", "exp_id": "EXP-0047",
        "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "reason": "rollup verdict used `if inf == 0` on a list, so a topic whose queries ALL returned empty feeds was "
                  "labelled 'no_keyword_relevant_hit' instead of 'undecidable'; the retrieval records themselves were "
                  "correct and are reused unchanged",
        "was_it_quoted": "no - caught while reading the rollup, before any topic status was written"})
    SR.write_text(json.dumps(sj, indent=1, ensure_ascii=False), encoding="utf-8", newline="")
    print("[e47] superseded-register entry added")
print("[e47] OK")
