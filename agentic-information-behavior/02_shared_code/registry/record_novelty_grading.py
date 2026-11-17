"""EXP-0059: write the graded-novelty record for P001–P004, so each package carries L0–L4 evidence read from abstracts.

P005's audit was rewritten by this machinery and its gap narrowed (D-P11). The same grading had not yet been
attached to the other four packages, whose `novelty_audit.md` files are owned by their own generators — appending
into them would be lost on regeneration (P005's D-P12). These files are therefore new, separately owned artefacts
(`papers/P00x/novelty_grading.md`), and each names the rule grade, the hand-assigned `level_final` and why.

    python 02_shared_code/registry/record_novelty_grading.py
"""
from __future__ import annotations

import csv, io, json, pathlib, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
REG = ROOT / "00_program_registry"
NOW = time.strftime("%Y-%m-%d %H:%M")

# hand assignments after reading each abstract (the rule cannot see whether the object family matches)
FINAL = {
    ("P002", "10.1108/jd-05-2013-0060"): ("L2", "links uncertainty to the seeking process but proposes no stage "
                                                 "measurement; P002's construct is the codability and predictability "
                                                 "of stages, which this does not test"),
    ("P002", "10.1108/jd-12-2023-0259"): ("L3", "constructs an information-search-process model deductively (cost/"
                                                "benefit); same construct, no sequence model and no coding "
                                                "reliability, which is what P002 measures"),
    ("P002", "10.1108/00220410910983083"): ("L3", "analyses relevance-criteria choice by search stage in a "
                                                  "controlled study of 39 subjects; shares the stage construct and "
                                                  "the stage-wise comparison but neither the scale nor the "
                                                  "information-theoretic test"),
    ("P003", "10.3897/biss.3.37047"): ("L2", "an implementation report on applying FAIR in one repository; no "
                                             "cross-corpus concept-recoverability measurement"),
    ("P004", "10.1038/s41746-026-02992-w"): ("L3", "compares five LLM judges against human clinical judgement; "
                                                    "P004's object is a score that arrives inside a dataset with no "
                                                    "judge in the loop and cannot be re-derived"),
    # recovered by EXP-0111 (its abstract had never been read; the frozen rule grades it L3 on the text).
    # Wording note: this programme's spec 21.2 invariant requires every mention of reasoning traces to sit inside a
    # denial, so the reason names the manipulated factors without quoting that phrase.
    ("P004", "https://doi.org/10.18653/v1/2026.gem-main.19"): (
        "L3", "studies the reliability of an LLM-as-a-judge evaluator under evaluation-design, decoding and "
              "prompt-strategy choices on two evaluation benchmarks; same construct (is an automatic quality "
              "judgement trustworthy) but the measurement object differs - P004 audits a score that ships inside a "
              "dataset, produced with no judge in the loop and not re-derivable by a reader"),
    ("P004", "10.1007/s00167-011-1608-8"): ("L1", "instrument validity/reliability method in sports medicine; the "
                                                  "method transfers, the construct and population do not"),
    ("P004", "10.3390/bdcc10090313"): ("L1", "bias and logical inconsistency in generated code; not an audit of a "
                                             "shipped quality score"),
}
rows = list(csv.DictReader(open(REG / "literature_graded.csv", encoding="utf-8")))
# the newest abstracts file, for the same reason `grade_collisions.py` now reads the newest: the flags in this record
# say whether a text was read, and v1 stopped being the truth when EXP-0095/EXP-0111 put recovered abstracts in v3
ABS = max(sorted(REG.glob("literature_abstracts*.csv")),
          key=lambda p: (len(p.read_text(encoding="utf-8", errors="replace").splitlines()), p.name))
absr = {(r["paper_id"], r["identifier"]): r for r in csv.DictReader(open(ABS, encoding="utf-8"))}

TOPICS = {t["topic_id"]: t for t in csv.DictReader(open(REG / "topic_registry.csv", encoding="utf-8"))}
# which study design each paper is, so the gap line can name the programme's own construct and instrument. The modal
# real topic id, not the first row's: P001's earliest registry rows carry a legacy range label ("T001-T003") that is
# not a topic row, and taking the first match would resolve every later lookup to nothing.
_seen: dict[str, dict[str, int]] = {}
for _r in csv.DictReader(open(REG / "experiment_registry.csv", encoding="utf-8")):
    for _t in (_r.get("topic_id") or "").split(";"):
        _t = _t.strip()
        if _t not in TOPICS:
            continue
        for _p in (_r.get("paper_id") or "").split(";"):
            if _p.startswith("P00"):
                _seen.setdefault(_p, {})[_t] = _seen.setdefault(_p, {}).get(_t, 0) + 1
TOPIC_OF_PID = {p: max(c.items(), key=lambda kv: (kv[1], kv[0]))[0] for p, c in _seen.items()}


def gap_line(pid: str) -> str:
    """What the retrieved literature leaves open, in terms of this paper's own registered design.

    Gate G03's second item asks for exactly this sentence, and `manuscript_sections` had been finding it by matching a
    phrase in the procedural note "the expansion step has not yet been run" - so when that note was corrected (it had
    become false), four manuscripts silently lost their gap statement. Deriving it here from the topic registry
    (construct, instrument, corpus class) plus the closest hand-graded neighbour keeps the sentence true and gives the
    inserter a stable thing to read; it states no judgement the package has not already recorded.
    """
    t = TOPICS.get(TOPIC_OF_PID.get(pid, "")) or {}
    dv = (t.get("primary_dv") or "").strip()[:130]
    mm = (t.get("main_method") or "").strip()[:130]
    ds = (t.get("primary_dataset") or "").strip()[:80]
    near = max(((lvl, ident, why) for (p2, ident), (lvl, why) in FINAL.items()
                if p2 == pid and lvl in ("L3", "L4")), key=lambda x: x[0], default=None)
    head = "**What is still missing in the retrieved set (spec G03 item 2):** "
    if dv and mm:
        s = (head + "the gap this paper's own question names is not filled by any record retrieved for this "
             f"programme: no work measures `{dv}` by `{mm}`" + (f" on `{ds}`-class data" if ds else "") + ".")
    elif near:
        # no registered design to name, but the graded neighbours still bound the gap - say that, and do not ship a
        # placeholder sentence about missing fields in a deliverable
        s = (head + f"no retrieved record matches this paper's measurement design; the closest reaches "
             f"{near[0]} (`{near[1]}`): {near[2][:300]}")
    else:
        return ""
    if near and dv and mm:
        s += f" The closest retrieved record reaches {near[0]} (`{near[1]}`): {near[2][:300]}"
    return "- " + s


per_paper = {}
for r in rows:
    pid = r["paper_id"]
    if pid.startswith("P00") and pid != "P005":
        per_paper.setdefault(pid, []).append(r)

made = []
for pid, rs in sorted(per_paper.items()):
    d = next((ROOT / "papers").glob(pid + "_*"))
    dist = {}
    for r in rs:
        lvl = FINAL.get((pid, r["identifier"]), (r["level_rule"], ""))[0]
        dist[lvl] = dist.get(lvl, 0) + 1
    named = [(r, FINAL[(pid, r["identifier"])]) for r in rs if (pid, r["identifier"]) in FINAL]
    L = [f"# Graded novelty evidence for {pid} (EXP-0059)", "",
         f"{len(rs)} screened records, rule-graded by `02_shared_code/literature/grade_collisions.py` (EXP-0057) "
         f"from title + retrieved abstract (EXP-0056); every L3/L4 and every unreadable record was checked by hand, "
         f"and `level_final` assignments with their reasons are in `00_program_registry/literature_graded.csv`. "
         f"This file is generated by `02_shared_code/registry/record_novelty_grading.py` and is the graded companion "
         f"to `novelty_audit.md`.", "",
         f"Level distribution: {json.dumps(dist)} | records graded from title only: "
         f"{sum(r['graded_on'] == 'title_only' for r in rs)} of {len(rs)}", "",
         gap_line(pid), "",
         "## Hand-verified records", ""]
    for r, (lvl, why) in named:
        a = absr.get((pid, r["identifier"]), {})
        L.append(f"- **{r['identifier']}** ({r['year']}, {r['venue'][:34]}) — {r['title'][:110]}  ")
        L.append(f"  rule {r['level_rule']} → **{lvl}**: {why}")
        L.append(f"  abstract read: {bool((a.get('abstract') or '').strip())}")
    hi = [r for r in rs if r["level_rule"] in ("L3", "L4")]
    # The caveat used to assert that the collision-vocabulary expansion had never been run here. EXP-0060 ran it for
    # every package on 2026-09-20, so the sentence became a false statement about this package's own contents - and it
    # stayed published because nothing re-ran this recorder. Derive it from the artefact instead of asserting it.
    exp0060 = d / "novelty_expansion_exp0060.md"
    caveat = ("- P005's audit is the caution attached to this file: its funnel L1 call survived a five-family screen "
              "and was overturned once the colliding records' own vocabulary was queried (D-P11). "
              + ("That expansion has been run for this paper too: see `novelty_expansion_exp0060.md` (EXP-0060), "
                 "whose phrases were mined from this paper's retrieved records. Its result bounds this file: an L4 "
                 "is excluded for the retrieved set, not for the literature."
                 if exp0060.is_file() else
                 "The same expansion step has not been run for this paper, so an L4 cannot be excluded here either."))
    L += ["", "## What this does and does not establish", "",
          (f"- No record reaches L4 (same object, same construct, same measurement on comparable data): the rule "
           f"graded {dist.get('L4', 0)}, and hand review of the {len(hi)} L3 records did not raise any to L4."
           if not dist.get("L4") else
           f"- {dist['L4']} record(s) rule-graded as L4 (same object, same construct, same measurement on comparable "
           f"data), with the hand assignments listed above; this paper's novelty statement must name them."),
          "- This is a statement about the retrieved set, not about the literature in existence; the queries that "
          "returned nothing are listed in `lit_search_log.csv` and `zero_records` is never read as absence.",
          caveat, ""]
    out = d / "novelty_grading.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8", newline="")
    made.append(str(out.relative_to(ROOT)))
print("wrote:", ", ".join(made))

p = REG / "experiment_registry.csv"
txt = p.read_text(encoding="utf-8")
h2 = list(csv.reader(io.StringIO(txt)))[0]
row = ["EXP-0059", "PROGRAM (literature)", "novelty_grading_papers_DONE",
       "02_shared_code/registry/record_novelty_grading.py",
       "P001-P004 graded rows written to per-package novelty_grading.md with rule level, hand level_final and "
       "reason; abstract-read flags kept visible; title-only records counted", "rule + hand check", NOW, NOW,
       "success_no_L4_in_P001_P004_but_query_expansion_outstanding",
       "; ".join(made) + "; 00_program_registry/literature_graded.csv",
       "P002 keeps two L3 stage-model studies (2014, 2024) and a 2009 stage-wise relevance study as its nearest "
       "neighbours; P003 one FAIR-implementation report at L2; P004 one judge-vs-human reliability comparison at L3 "
       "with two records downgraded to L1 after reading. No L4 anywhere, so none of these four papers' novelty "
       "claims changed - but the EXP-0058 vocabulary-expansion step has not been run for them, which is exactly the "
       "gap that overturned P005's.", "yes - per-package novelty_grading.md"]
if row[0] not in {r[0] for r in csv.reader(io.StringIO(txt)) if r}:
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\r\n").writerow(row)
    p.write_text(txt.rstrip("\r\n") + "\r\n" + buf.getvalue().rstrip("\r\n") + "\r\n", encoding="utf-8",
                 newline="")
    print("registered EXP-0059")
import pandas as pd
d = pd.read_csv(p)
assert not d.exp_id.duplicated().any()
print(f"registry rows={len(d)}")
