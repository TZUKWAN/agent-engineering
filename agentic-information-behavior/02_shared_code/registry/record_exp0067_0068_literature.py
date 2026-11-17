"""EXP-0067/0068 recorder: fold the family-driven collision hunt in, and report where the screen failed.

The two papers came out differently and the recorder treats them differently, which is the point:

* **P003** - the screen's L2 hits are on-construct: metadata interoperability, schema mapping and matching, data-format
  interoperability in health informatics, library science and data engineering. Its readable L2 rows are appended to the
  curated matrix as adjacent-domain prior work, marked `pending_hand_check`.
* **P004** - the screen is **not trustworthy for this paper**, and nothing is appended. Its term families contain the
  generic words `rating`, `score`, `label` and `judge`, so any clinical or psychometric scale-validation study matches
  object + construct + measure and is graded L2/L3. Twelve sampled L2+ hits are listed with what they actually are; not
  one concerns an automatic score attached to generated text. Appending them would have raised P004's
  "directly relevant" count from 17 to 184 while making the matrix false.

The precision judgement below is a read of a random sample (seed 7) by this agent, not a validated coding scheme, and
the sample size is stated everywhere it is used.

    python 02_shared_code/registry/record_exp0067_0068_literature.py
"""
from __future__ import annotations

import csv, glob, io, json, pathlib, random, re, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
REG = ROOT / "00_program_registry"
BASELINE = {"P003": 9, "P004": 17}
RUNS = {"P003": "EXP-0067", "P004": "EXP-0068"}
# what the screen rewards, and what the paper is actually about, per record read in the sample
VERDICT = {
    "P003": {"in_domain": True,
             "why": "the sampled L2 hits are about metadata/schema/data-format interoperability itself - the construct "
                    "this paper measures - coming from adjacent domains (health informatics, library and information "
                    "science, data engineering) rather than from this paper's corpus family"},
    "P004": {"in_domain": False,
             "why": "the sampled L2/L3 hits are clinical, psychometric, educational and engineering scale-validation "
                    "studies (rating scales, severity indices, network reliability, credit ratings). They match because "
                    "P004's object family contains the bare words rating/score/label/judge, not because they concern an "
                    "automatic score attached to generated text"},
}
SAMPLE_N = 12


def read(p):
    return list(csv.reader(io.StringIO(pathlib.Path(p).read_text(encoding="utf-8"))))


def write_rows(p, hdr, body):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    w.writerow(hdr)
    w.writerows(body)
    pathlib.Path(p).write_text(buf.getvalue(), encoding="utf-8", newline="")


def main() -> int:
    reg_rows = read(REG / "experiment_registry.csv")
    reg_hdr, reg_body = reg_rows[0], [r for r in reg_rows[1:] if r]
    have_ids = {r[0] for r in reg_body}

    for pid, exp in RUNS.items():
        hits = sorted(glob.glob(str(ROOT / "results_raw" / f"{exp.replace('-', '')}_{pid.lower()}_family_expansion_summary_*.json")))
        if not hits:
            print(f"[{exp}] no summary for {pid}; skipped")
            continue
        S = json.loads(pathlib.Path(hits[-1]).read_text(encoding="utf-8"))
        EXPF = REG / S["out_file"]
        rows = list(csv.DictReader(io.StringIO(EXPF.read_text(encoding="utf-8"))))
        pap = ROOT / "papers" / next(p for p in (ROOT / "papers").glob(f"{pid}_*"))
        l2 = [r for r in rows if r["level_rule"] in ("L2", "L3", "L4")]
        readable = [r for r in l2 if int(r["abstract_chars"] or 0)]
        sample = random.Random(7).sample(readable, min(SAMPLE_N, len(readable)))
        smp_tbl = "\n".join(f"| {r['level_rule']} | {r['title'][:96]} | {r['venue'][:38]} | "
                            f"{r['abstract'][:150].replace('|', '/')} |" for r in sample)

        # ---- matrix append happens only where the sampled precision supports it
        MTX = pap / "literature_matrix.csv"
        m = read(MTX)
        hdr, body = m[0], [r for r in m[1:] if r]
        # Keys on cite_key as well as title: the stored title is truncated to 160 characters while the comparison used
        # the full one, so any record with a longer title failed the guard and was appended again on every run (P003's
        # matrix gained one row per rebuild). Duplicate rows already in the file are dropped, first occurrence kept.
        have = {re.sub(r"\s+", " ", (r[3] or "").lower()).strip() for r in body}
        have_ck = {(r[0] or "").strip() for r in body}
        _seen_row, _dedup = set(), []
        for r in body:
            k = tuple(r[:4])
            if k in _seen_row:
                continue
            _seen_row.add(k)
            # rows written by the older positional append are two fields short of this header, and the missing ones are
            # exactly the trailing re-derivation columns, so padding at the end is the correct repair
            _dedup.append((list(r) + [""] * (len(hdr) - len(r))) if len(r) < len(hdr) else r)
        if len(_dedup) != len(body):
            print(f"[{exp}] {pid}: dropped {len(body) - len(_dedup)} duplicate matrix row(s) left by the truncated-title "
                  "guard")
        body = _dedup
        have = {re.sub(r"\s+", " ", (r[3] or "").lower()).strip() for r in body}
        added = 0
        if VERDICT[pid]["in_domain"]:
            for r in readable:
                t = re.sub(r"\s+", " ", r["title"].lower()).strip()
                ck = (r["doi"] or r["url"]).split("/")[-1][:34] + "|" + re.sub(r"[^A-Za-z]", "", r["title"].split()[0])[:12]
                if t in have or ck in have_ck:
                    continue
                matched = json.loads(r["matched"])
                hit_txt = "; ".join(f"{k}:{','.join(v[:3])}" for k, v in matched.items() if v)
                # one dict per column, emitted in header order: a positional row is 17 fields long while this package's
                # header is 19 (it gained `differentiation` and the two re-derivation columns at different times), and
                # appending by position shipped nine ragged rows in P003's matrix
                vals = {"cite_key": ck, "year": r["year"], "venue": r["venue"][:60], "title": r["title"][:160],
                        "problem": f"adjacent-domain prior work surfaced by the {exp} family battery; not yet read "
                                   f"for this paper",
                        "collision_target": hit_txt,
                        "overlap_level": r["level_rule"] + " (rule grade, unverified)",
                        "url": r["url"], "retrieved_on": time.strftime("%Y-%m-%d"),
                        "verify_status": "pending_hand_check", "paper_id": pid,
                        "differentiation": "empty on purpose: differentiation is written after the abstract is read, "
                                           "not from a screen"}
                body.append([vals.get(c, "") for c in hdr])
                added += 1
            write_rows(MTX, hdr, body)
        print(f"[{exp}] {pid}: L2+ {len(l2)} ({len(readable)} readable); matrix rows appended = {added}")

        LOG = pap / "lit_search_log.csv"
        lg = read(LOG)
        lhdr, lbody = lg[0], [r for r in lg[1:] if r]
        seen_q = {r[2] for r in lbody}
        n = 0
        for q in S["query_log"]:
            form = f'query.bibliographic="{q["query"]}" + arXiv all:"{q["query"]}"'
            if form in seen_q:
                continue
            lbody.append([pid, "family_derived_query.bibliographic+arxiv_all", form, str(q["kept"]), str(q["kept"]),
                          f"crossref={q['crossref']}; arxiv={q['arxiv']}", q["error"], q["at"], "crossref+arxiv"])
            n += 1
        write_rows(LOG, lhdr, lbody)
        zero = [q for q in S["query_log"] if "zero_records" in (q["crossref"], q["arxiv"])]

        (pap / "literature_background.md").write_text(f"""# {pid} background and collision literature ({exp})

Generated by `02_shared_code/registry/record_exp0067_0068_literature.py` from `{pathlib.Path(hits[-1]).name}` and
`{EXPF.name}`. Before this pass the shared graded set held **{BASELINE[pid]}** records at L2 or above for {pid}.

## How the queries were chosen

{len(S['queries'])} query forms **derived from the same term families the frozen EXP-0057 rule scores on** - each
construct phrase alone, then this paper's object terms paired with each construct phrase. The battery is therefore a
collision hunt reproducible from `PAPERS["{pid}"]` in `02_shared_code/literature/grade_collisions.py`, not a topic
browse, and the queries were printed before any request was made.

## What came back

* {S['new_records']} new records after deduplication against everything this programme already holds, from
  {S['distinct_venues']} distinct venues.
* Abstract text was filled **before** grading: {S['filled_by_semanticscholar']} gained text from the Semantic Scholar
  batch index, {S['rejected_on_title_mismatch']} candidate fills were refused for title disagreement below 6 shared
  content tokens. {S['unread']} of the {S['new_records']} records are still unread.
* Rule grades: {json.dumps(S['grade_distribution'], ensure_ascii=False)}; at L2 or above **{S['L2plus']}**, of which
  {len(readable)} carry text.

## Screen precision, measured by reading a sample - and what it decided

A random sample of {len(sample)} of the {len(readable)} readable L2+ records was read (seed 7). Verdict:
**{VERDICT[pid]['why']}**

| rule | title | venue | abstract opening |
|---|---|---|---|
{smp_tbl}

Consequence, decided on that reading and not on the count:
**{"the readable L2+ rows were appended to `literature_matrix.csv` as adjacent-domain prior work (" + str(added) + " rows), each marked `pending_hand_check` with an empty `differentiation` cell." if added else "nothing was appended to `literature_matrix.csv`. The screen's " + str(len(l2)) + " L2+ hits are an artifact of this paper's term families containing the bare words `rating`, `score`, `label` and `judge`; appending them would have inflated the directly-relevant count from " + str(BASELINE[pid]) + " to " + str(BASELINE[pid] + len(l2)) + " while making the matrix false."}**
{"The count of directly relevant works for this paper therefore stays at the curated set plus the records recovered by EXP-0064, and the spec's 20-30 target is reported as NOT met by a screen that cannot distinguish an LLM-judge paper from a menopause rating scale." if not added else ""}

## Query battery and per-source outcome

{chr(10).join(f"- `{q['query']}` -> kept={q['kept']} crossref={q['crossref']} arxiv={q['arxiv']}"
              + (f" error={q['error']}" if q['error'] else "") for q in S['query_log'])}

{len(zero)} queries returned zero records on at least one source; they are listed above with that status rather than
removed.

## What this does not claim

* The precision judgement is one agent's read of {len(sample)} sampled records, not a validated coding scheme with an
  agreement statistic; it is the basis for the append/no-append decision and nothing else.
* {S['unread']} records were graded from a title alone, so the L2+ count is bounded by coverage in both directions.
* Discovery is limited to Crossref and arXiv, with Semantic Scholar used only to fill abstract text; OpenAlex does not
  connect from this host (measured in EXP-0063).
""", encoding="utf-8", newline="")
        print(f"[{exp}] wrote {pap.name}/literature_background.md; lit_search_log +{n} rows, {len(zero)} zero-result queries kept")

        if exp not in have_ids:
            reg_body.append([exp, pid, f"success_FAMILY_SCREEN_PRECISION_{'OK' if VERDICT[pid]['in_domain'] else 'ZERO'}",
                             "02_shared_code/literature/expand_paper_literature.py",
                             f"{len(S['queries'])} query forms generated from PAPERS['{pid}'] term families over "
                             "Crossref query.bibliographic and the arXiv export API (curl); Semantic Scholar batch fill "
                             "applied BEFORE grading with a 6-shared-token title agreement requirement; graded with the "
                             "imported, unmodified EXP-0057 rule; screen precision measured on a seed-7 sample of 12 "
                             "readable L2+ records", "seed 7 (precision sample)", S["started_at"], S["finished_at"],
                             f"{S['new_records']} new records, {S['readable']} readable, {S['unread']} unread, L2+ "
                             f"{S['L2plus']}; {added} rows appended to the curated matrix",
                             f"{EXPF.name}; {pathlib.Path(hits[-1]).name}; papers/{pap.name}/literature_background.md",
                             ("adjacent-domain prior work added to the matrix as pending_hand_check" if added else
                              "screen shown to be uninformative for this paper's generic term families; nothing "
                              "appended, and the 20-30 directly-relevant minimum is reported as unmet rather than "
                              "reached by inflating the matrix"), "yes - literature_background.md"])
            have_ids.add(exp)
            print(f"[{exp}] registered")
    write_rows(REG / "experiment_registry.csv", reg_hdr, reg_body)
    import pandas as pd
    d = pd.read_csv(REG / "experiment_registry.csv")
    assert not d.exp_id.duplicated().any()
    print(f"registry rows={len(d)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
