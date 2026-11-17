"""EXP-0063/0064 recorder: publish the abstract-recovery result, including the part that hurts.

Reading more abstracts made the collisions look **closer**, not thinner: of the 30 records that gained text, 12 were
re-graded and every one of the 12 moved UPWARDS (four of them to L3). That is the direction a literature pass should
move in when it was previously under-read, and it is the opposite of what a novelty audit wants, so it is written here
with the affected papers' positioning amended in the same pass. Generated from
`00_program_registry/EXP0063_s2_summary.json` and `EXP0064_regrade_delta.json`; the hand assignments below are the
only authored text, and each one names what the closer work does and what this paper's claim is therefore limited to.

    python 02_shared_code/registry/record_exp0063_0064_literature.py
"""
from __future__ import annotations

import csv, io, json, pathlib, re, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
REG = ROOT / "00_program_registry"
DOCS = ROOT / "docs"
NOW = time.strftime("%Y-%m-%dT%H:%M:%S")
S63 = json.loads((REG / "EXP0063_s2_summary.json").read_text(encoding="utf-8"))
S64 = json.loads((REG / "EXP0064_regrade_delta.json").read_text(encoding="utf-8"))
GRADED_V2 = REG / "literature_graded_v2.csv"
TOTAL_RECORDS = len(list(csv.DictReader(io.StringIO((REG / "literature_abstracts.csv").read_text(encoding="utf-8")))))
SUPERSEDED = "results_raw/superseded/EXP0063_literature_abstracts_s2_run1_collapsed_by_paper_id.csv"

# hand-verified after reading the recovered abstracts: (paper, cite_key) -> (level_final, what they do, our limit)
HAND = {
    ("P004", "Haldar2025r"): ("L3",
        "quantifies low intra-rater reliability of LLM judges across repeated runs on standard NLG benchmarks and asks "
        "whether judicious use is still possible",
        "studies scores the authors can re-run; P004 studies scores already shipped in published artefacts, where no "
        "re-run of the generating configuration is available, and tests criterion validity (does the score track "
        "anything), not only self-consistency"),
    ("P004", "Gu2026a"): ("L2",
        "survey that defines and classifies LLM-as-a-judge systems and proposes a reliability-oriented benchmark",
        "a forward-looking design framework; P004 is an audit of the measurement properties of scores that already "
        "ship, and cites this survey as the framing it argues against rather than builds on"),
    ("P004", "Enguehard2025l"): ("L2",
        "reference-free legal-domain judge (Legal Data Points) built because judge reliability differs in legal text",
        "domain-specific judge construction; P004 does not propose a judge and its object is the shipped score itself"),
    ("P004", "Amin2026m"): ("L2",
        "controlled 2,400-rating multi-language study of rubric-guided AI-assisted feedback to raise the "
        "reproducibility of human code-quality ratings",
        "reproducibility of in-study human ratings under two conditions; P004's population is third-party published "
        "scores with no condition contrast, and it adds the criterion-validity test they do not run"),
    ("P005", "Duan2024m"): ("L3",
        "ModelGo audits licence conflicts and legal risk across the software, database and model components of an ML "
        "project, and derives guidelines from five real-world use cases",
        "consumes licence declarations as given and reasons over conflicts; P005 measures the declarations themselves - "
        "whether rights/provenance metadata is present, attributable to an artefact, and verifiable - and reports the "
        "cases where it is not, which is the precondition ModelGo assumes"),
}


def read(p):
    return list(csv.DictReader(io.StringIO(pathlib.Path(p).read_text(encoding="utf-8"))))


def write_csv(p, rows, fields):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\r\n", extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    pathlib.Path(p).write_text(buf.getvalue(), encoding="utf-8", newline="")


def main() -> int:
    s2rows = read(REG / "literature_abstracts_s2.csv")
    st = {"known_no_text": sum(1 for r in s2rows if r["status"] == "informative" and not r["abstract"].strip()),
          "unknown_to_index": sum(1 for r in s2rows if r["status"] == "all_null"),
          "transport_error": sum(1 for r in s2rows if r["status"] == "transport_error"),
          "with_text": sum(1 for r in s2rows if r["abstract"].strip())}
    rows = read(GRADED_V2)
    if "hand_note" not in rows[0]:
        for r in rows:
            r["hand_note"] = ""
    fields = list(rows[0].keys())
    bykey = {(r["paper_id"], r["cite_key"]): r for r in rows}
    missing = [k for k in HAND if k not in bykey]
    if missing:
        raise SystemExit(f"[e63/64] ABORT: hand-assigned records not in {GRADED_V2.name}: {missing}")
    for (pid, ck), (lvl, what, limit) in HAND.items():
        r = bykey[(pid, ck)]
        if r["level_rule"] != "L3":
            raise SystemExit(f"[e63/64] ABORT: {pid}/{ck} is rule-graded {r['level_rule']}, not L3; the assignment "
                             "list no longer matches the re-grade and must be re-read rather than applied.")
        r["level_final"] = lvl
        r["hand_note"] = f"they do: {what} | our claim is limited to: {limit}"
    write_csv(GRADED_V2, rows, fields)
    print(f"[e63/64] level_final + hand_note written for {len(HAND)} re-graded records")

    # ---------------------------------------------------------------- the programme-level note
    ch = S64["changed"]
    up = S64["n_changed_upwards"]
    tbl = "\n".join(f"| {m['paper_id']} | `{m['cite_key']}` | {m['rule_before']} -> {m['rule_after']} | "
                    f"{m['graded_on_before']} -> {m['graded_on_after']} | {m['abstract_source']} | "
                    f"{m['title'][:88]} |" for m in ch)
    assigned = "\n".join(f"- **{pid} `{ck}`** -> `level_final={lvl}` (rule said L3). {what}. "
                         f"This paper's claim is limited to: {limit}."
                         for (pid, ck), (lvl, what, limit) in sorted(HAND.items()))
    NOTE = f"""# Literature abstract recovery and re-grade (EXP-0063 + EXP-0064), {time.strftime('%Y-%m-%d')}

Generated by `02_shared_code/registry/record_exp0063_0064_literature.py` from
`00_program_registry/EXP0063_s2_summary.json` and `00_program_registry/EXP0064_regrade_delta.json`.

## Why

EXP-0056 could not retrieve an abstract for **{S63['records_without_abstract']} of {TOTAL_RECORDS}**
retrieved records, and EXP-0057's grading rule cannot honestly read an overlap level from a title alone: those records
were marked `graded_on=title_only` and left undecidable. That is a hole in the literature pass of all five papers, so
the premise "no other abstract source is reachable" was measured instead of assumed:
`api.openalex.org` does not connect from this host, while `api.semanticscholar.org` answers and its batch endpoint
returns stored abstract text. No inference API is involved - this is a bibliographic metadata service.

## What was done

* `02_shared_code/literature/fetch_abstracts_s2.py` (EXP-0063): DOI/arXiv batch lookup in groups of 50, three tries per
  batch, three-way per-batch status (`informative` / `all_null` / `transport_error`), checkpointed per batch. The
  frozen `literature_abstracts.csv` is never modified; results land in `literature_abstracts_s2.csv`.
* `02_shared_code/literature/regrade_with_recovered_abstracts.py` (EXP-0064): merges the recovered text into
  `literature_abstracts_v2.csv` and re-runs **the imported, unmodified EXP-0057 rule** (not a copy) to
  `literature_graded_v2.csv`, then aligns the two graded tables by position with the alignment asserted.

## Result

| quantity | before | after |
|---|---|---|
| records graded from title only | {S64['records']['graded_on_title_only_before']} | {S64['records']['graded_on_title_only_after']} |
| abstracts recovered by EXP-0063 | - | {S64['records']['abstracts_recovered_by_e63']} |
| rule grades L0/L1/L2/L3/L4 | {' / '.join(str(S64['grade_dist_before'][k]) for k in ('L0','L1','L2','L3','L4'))} | {' / '.join(str(S64['grade_dist_after'][k]) for k in ('L0','L1','L2','L3','L4'))} |
| records needing hand verification | {S64['hand_check_before']} | {S64['hand_check_after']} |

**{S64['n_rule_changed']} records changed rule grade, and all {up} moved upwards.** Reading more of the literature made the
collisions look closer, not thinner - which is the direction a previously under-read pass should move in, and the
opposite of what a novelty audit hopes for. The remaining
{S64['records']['graded_on_title_only_after']} title-only records break down as {st['known_no_text']} records whose
identifier the index knows but where it stores no abstract text, {st['unknown_to_index']} the index does not know at
all, and {st['transport_error']} where the title-search endpoint returned a transport error (it is rate-limited without
a key, and no key was used); they stay undecidable and are reported as such rather than graded from titles.

| paper | cite_key | rule | graded on | abstract source | title |
|---|---|---|---|---|---|
{tbl}

## Hand verification of the records that became L3

{assigned}

## Two bugs this pass caught about itself

1. `paper_id` in the literature tables names the **paper** (five distinct values across {TOTAL_RECORDS}
   records) and no column is unique, so the first run of EXP-0063 keyed its per-record state on `paper_id` and
   silently collapsed 89 lookup results into 3 rows. Fixed by addressing records as `{{index}}|{{cite_key}}`; the
   collapsed output is archived at `{SUPERSEDED}`.
2. The first version of the EXP-0064 delta made the same mistake on the graded tables and reported 5 records. The
   re-run asserts positional alignment on `(paper_id, cite_key, title)` for all {S64['records']['v1']} rows before
   comparing anything.

## What this does not claim

It does not mean the literature pass is now complete: {S64['records']['graded_on_title_only_after']} records are still
title-only, the recovered set covers only what one secondary index holds, and a rule grade is a screen, not a verdict -
`level_final` is authoritative and is filled only for the records read above.
"""
    (DOCS / "literature_abstract_recovery_20260920.md").write_text(NOTE, encoding="utf-8", newline="")
    print("[e63/64] wrote docs/literature_abstract_recovery_20260920.md")

    # ---------------------------------------------------------------- per-paper positioning + deviation rows
    for pid, keys in (("P004", [k for k in HAND if k[0] == "P004"]), ("P005", [k for k in HAND if k[0] == "P005"])):
        pap = ROOT / "papers" / next(p for p in (ROOT / "papers").glob(f"{pid}_*"))
        na = pap / "novelty_audit.md"
        txt = na.read_text(encoding="utf-8")
        if "EXP-0064" not in txt:
            body = "\n".join(f"- `{ck}` ({bykey[(pid, ck)]['title'][:90]}, {bykey[(pid, ck)]['venue'][:46]} "
                             f"{bykey[(pid, ck)]['year']}): rule L3, hand-assigned **{HAND[(pid, ck)][0]}**. "
                             f"They do: {HAND[(pid, ck)][1]}. Our claim is limited to: {HAND[(pid, ck)][2]}."
                             for ck in [k[1] for k in keys])
            na.write_text(txt.rstrip() + f"""

## Post-recovery positioning (EXP-0063/0064, {time.strftime('%Y-%m-%d')})

These records were previously graded from a title alone. Their abstracts were recovered from Semantic Scholar and the
frozen EXP-0057 rule re-run, which moved each of them **up** to L3. They are reported here rather than quietly
re-labelled, and `level_final` in `00_program_registry/literature_graded_v2.csv` carries the reading:

{body}

The novelty statement above this section is unchanged in direction but narrower than it would have looked had these
abstracts never been read: the closest prior work is closer than the title-only pass showed.
""", encoding="utf-8", newline="")
            print(f"[e63/64] {pid} novelty_audit positioning appended")
        dv = pap / "deviations.md"
        dt = dv.read_text(encoding="utf-8")
        alld = [int(x) for f in sorted((ROOT / "papers").glob("*/deviations.md"))
                for x in re.findall(r"(?m)^\| D(\d+) \|", f.read_text(encoding="utf-8"))]
        dn = max(alld or [0])
        subject = "文献摘要缺口回填后重叠等级全部上移，本文档的最近邻比原判定更近"
        if subject not in dt:
            dv.write_text(dt.rstrip() + f"""
| D{dn+1} | {NOW} | {subject} | EXP-0063 从 Semantic Scholar 批量取回 {S64['records']['abstracts_recovered_by_e63']} 条摘要；EXP-0064 用**未改动的** EXP-0057 规则重评，{S64['n_rule_changed']} 条等级变化且 {S64['n_changed_upwards']} 条全部上移（本纸 {len(keys)} 条升至 L3），逐条读摘要后给出 level_final 与差异声明 | 否 | 未移动门槛也未下调判据：把更近的先前工作写进 novelty_audit 并收窄声明；标题不可判记录仍有 {S64['records']['graded_on_title_only_after']} 条如实保留 |""",
                          encoding="utf-8", newline="")
            print(f"[e63/64] {pid} D{dn+1} appended")

    # ---------------------------------------------------------------- registry
    p = REG / "experiment_registry.csv"
    txt = p.read_text(encoding="utf-8")
    have = {r[0] for r in csv.reader(io.StringIO(txt)) if r}
    new = []
    if "EXP-0063" not in have:
        new.append(["EXP-0063", "programme", "success_abstracts_recovered_from_semanticscholar",
                    "02_shared_code/literature/fetch_abstracts_s2.py",
                    f"batch DOI/arXiv lookup of the {S63['records_without_abstract']} retrieved records that EXP-0056 "
                    "could not supply an abstract for; 50-id batches, 3 tries, three-way per-batch status, checkpointed; "
                    "title-search fallback accepted only above a 6-shared-token title match; frozen source file untouched",
                    "none (deterministic given the checkpoint)", S63["started_at"], S63["finished_at"],
                    f"recovered={S63['batches']['recovered']} with_abstract_now={S63['with_abstract_now']} "
                    f"still_title_only={S63['still_title_only']} transport_error={S63['batches']['transport_error']}",
                    "00_program_registry/literature_abstracts_s2.csv; 00_program_registry/EXP0063_s2_summary.json; " + SUPERSEDED,
                    "OpenAlex does not connect from this host; Semantic Scholar does and holds abstract text. First run "
                    "keyed state on paper_id (which names the paper, not the record) and collapsed 89 results into 3 "
                    "rows - archived as superseded.", "yes - closes part of the EXP-0057 undecidable set"])
    if "EXP-0064" not in have:
        new.append(["EXP-0064", "programme", "success_REGRADE_ALL_CHANGES_UPWARDS",
                    "02_shared_code/literature/regrade_with_recovered_abstracts.py",
                    "merge recovered abstracts into literature_abstracts_v2.csv and re-run the imported EXP-0057 "
                    "grading rule unchanged; graded tables aligned by position with (paper_id, cite_key, title) "
                    "asserted row by row before any comparison", "none",
                    S64["at"], S64["at"],
                    f"title_only {S64['records']['graded_on_title_only_before']}->{S64['records']['graded_on_title_only_after']}; "
                    f"rule changes {S64['n_rule_changed']} (upwards {S64['n_changed_upwards']}); hand_check "
                    f"{S64['hand_check_before']}->{S64['hand_check_after']}",
                    "00_program_registry/literature_graded_v2.csv; 00_program_registry/EXP0064_regrade_delta.json; "
                    "docs/literature_abstract_recovery_20260920.md",
                    "reading more abstracts made the collisions closer, not thinner; the five new L3 records were read "
                    "and given level_final plus a narrowed positioning statement in P004/P005 novelty audits, and the "
                    "threshold was not moved", "yes - P004/P005 novelty audits, two deviation rows"])
    if new:
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\r\n")
        for r in new:
            w.writerow(r)
        p.write_text(txt.rstrip("\r\n") + "\r\n" + buf.getvalue().rstrip("\r\n") + "\r\n", encoding="utf-8", newline="")
        print(f"[e63/64] registered {', '.join(r[0] for r in new)}")
    import pandas as pd
    d = pd.read_csv(p)
    assert not d.exp_id.duplicated().any()
    print(f"[e63/64] registry rows={len(d)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
