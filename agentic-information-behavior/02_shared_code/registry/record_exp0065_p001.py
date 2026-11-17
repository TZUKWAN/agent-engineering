"""EXP-0065 recorder: fold P001's expanded literature pass into its package, honestly labelled.

The expansion retrieved ~550 records with readable abstracts across four communities. Two things are done separately
on purpose, because conflating them is how a literature count becomes fiction:

* the **curated** `literature_matrix.csv` gains only the records the frozen rule places at L2 or above, each with
  `verify_status=pending_hand_check` - a rule grade is a screen, and nothing here claims to have read and judged them;
* the full set is documented in `literature_background.md`, which reports per-community and per-venue counts, the
  exact query forms, and the queries that returned nothing, so the "50+ background works from 3+ communities"
  requirement is checkable against a file rather than asserted in prose.

    python 02_shared_code/registry/record_exp0065_p001.py
"""
from __future__ import annotations

import csv, glob, io, json, pathlib, re, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
PAP = ROOT / "papers" / "P001_routing_failure_qpp"
REG = ROOT / "00_program_registry"
NOW = time.strftime("%Y-%m-%dT%H:%M:%S")

hits = sorted(glob.glob(str(ROOT / "results_raw" / "EXP0065_p001_expansion_summary_*.json")))
if not hits:
    raise SystemExit("[e65] no EXP-0065 summary; writing nothing.")
S = json.loads(pathlib.Path(hits[-1]).read_text(encoding="utf-8"))
EXP = REG / "literature_p001_expansion_v2.csv"
EXP1 = REG / "literature_p001_expansion.csv"
if not EXP.exists():
    raise SystemExit("[e65] run EXP-0066 (fill_expansion_abstracts.py) first; the v1 file holds records "
                     "that were graded unreadable and must not be the basis of a literature claim.")
E66_FILES = sorted(glob.glob(str(ROOT / "results_raw" / "EXP0066_expansion_abstracts_*.json")))
if not E66_FILES:
    raise SystemExit("[e65] no EXP-0066 summary; run fill_expansion_abstracts.py first.")
E66 = json.loads(pathlib.Path(E66_FILES[-1]).read_text(encoding="utf-8"))
rows = list(csv.DictReader(io.StringIO(EXP.read_text(encoding="utf-8"))))
if not rows:
    raise SystemExit("[e65] the expansion file is empty; nothing to record.")

l2 = [r for r in rows if r["level_rule"] in ("L2", "L3", "L4")]
unread = sum(1 for r in rows if not int(r["abstract_chars"] or 0))
l2.sort(key=lambda r: ({"L4": 0, "L3": 1, "L2": 2}[r["level_rule"]], r["community"], r["title"]))
by_comm = {}
for r in rows:
    c = by_comm.setdefault(r["community"], {"n": 0, "L2": 0, "venues": {}, "queries": {}})
    c["n"] += 1
    c["L2"] += r["level_rule"] in ("L2", "L3", "L4")
    c["venues"][r["venue"]] = c["venues"].get(r["venue"], 0) + 1
    c["queries"][r["query"]] = c["queries"].get(r["query"], 0) + 1

# ---------------------------------------------------------------- 1. curated matrix gains the L2+ screen only
MTX = PAP / "literature_matrix.csv"
mrows = list(csv.reader(io.StringIO(MTX.read_text(encoding="utf-8"))))
hdr, body = mrows[0], [r for r in mrows[1:] if r]
have = {re.sub(r"\s+", " ", (r[3] or "").lower()).strip() for r in body}
have_ck = {(r[0] or "").strip() for r in body}
_seen_row, _dedup = set(), []
for r in body:
    k = tuple(r[:4])
    if k not in _seen_row:
        _seen_row.add(k)
        _dedup.append((list(r) + [""] * (len(hdr) - len(r))) if len(r) < len(hdr) else r)
if len(_dedup) != len(body):
    print(f"[e65] dropped {len(body) - len(_dedup)} duplicate matrix row(s)")
body = _dedup
have = {re.sub(r"\s+", " ", (r[3] or "").lower()).strip() for r in body}
added = 0
for r in l2:
    t = re.sub(r"\s+", " ", r["title"].lower()).strip()
    # the stored title is truncated to 160 characters, so comparing the full one let long titles re-append on every
    # run; cite_key is the stable identity, and duplicates already in the file are removed above
    ck = (r["doi"] or r["url"]).split("/")[-1][:34] + "|" + re.sub(r"[^A-Za-z]", "", r["title"].split()[0])[:12]
    if t in have or ck in have_ck:
        continue
    matched = json.loads(r["matched"])
    hit_txt = "; ".join(f"{k}:{','.join(v[:3])}" for k, v in matched.items() if v)
    # emitted by column name, so a header that grows another column cannot shift a positional row's fields
    vals = {"cite_key": ck, "year": r["year"], "venue": r["venue"][:60], "title": r["title"][:160],
            "problem": f"retrieved by the EXP-0065 battery (community {r['community']}); not yet read for this paper",
            "collision_target": hit_txt, "overlap_level": r["level_rule"] + " (rule grade, unverified)",
            "url": r["url"], "retrieved_on": time.strftime("%Y-%m-%d"),
            "verify_status": "pending_hand_check", "paper_id": "P001"}
    body.append([vals.get(c, "") for c in hdr])
    added += 1
buf = io.StringIO()
w = csv.writer(buf, lineterminator="\r\n")
w.writerow(hdr)
w.writerows(body)
MTX.write_text(buf.getvalue(), encoding="utf-8", newline="")
print(f"[e65] matrix: {len(body)} rows now ({added} L2+ screen records appended, all marked pending_hand_check)")

# ---------------------------------------------------------------- 2. search log gains every query
LOG = PAP / "lit_search_log.csv"
lrows = list(csv.reader(io.StringIO(LOG.read_text(encoding="utf-8"))))
lhdr, lbody = lrows[0], [r for r in lrows[1:] if r]
# The header is paper,query_form,params,... and this recorder's rows hold the *kind* in query_form and the query text
# in params, so keying the "already logged?" test on r[1] compared a constant against a query string: every run
# re-appended all 25 of its queries, and the shipped log carried 280 rows for 55 queries (225 exact duplicates,
# dropped below). Identify a logged query by (kind, text), and de-duplicate on the whole row while preserving order.
_seen_q = {(r[1], r[2]) for r in lbody if len(r) > 2}
_before = len(lbody)
_dedup, _keep = [], set()
for r in lbody:
    k = tuple(r)
    if k in _keep:
        continue
    _keep.add(k)
    _dedup.append(r)
lbody = _dedup
if len(lbody) != _before:
    print(f"[e65] lit_search_log.csv: dropped {_before - len(lbody)} duplicate row(s) left by the mis-keyed guard")
n_log = 0
for q in S["query_log"]:
    form = q["query_form"]
    if ("query.bibliographic+arxiv_all", form) in _seen_q:
        continue
    lbody.append(["P001", "query.bibliographic+arxiv_all", form, str(q["returned_kept"]), str(q["returned_kept"]),
                  f"crossref={q['crossref_status']}; arxiv={q['arxiv_status']}", q["error"], q["ran_at"],
                  "crossref+arxiv"])
    n_log += 1
buf = io.StringIO()
w = csv.writer(buf, lineterminator="\r\n")
w.writerow(lhdr)
w.writerows(lbody)
LOG.write_text(buf.getvalue(), encoding="utf-8", newline="")
zero = [q for q in S["query_log"] if q["crossref_status"] == "zero_records" or q["arxiv_status"] == "zero_records"]
print(f"[e65] lit_search_log: {n_log} query rows appended; {len(zero)} queries returned zero records on at least "
      "one source (kept in the log, not deleted)")

# ---------------------------------------------------------------- 3. the background note
comm_tbl = "\n".join(
    f"| {c} | {v['n']} | {v['L2']} | {len(v['venues'])} | {len(v['queries'])} |" for c, v in sorted(by_comm.items()))
# counted into a dict and ordered by (-count, name): iterating a set gave ties a per-process order (string hashing is
# randomised), so every run permuted the equal-count venues in the shipped table
_vc: dict[str, int] = {}
for r in rows:
    _vc[r["venue"]] = _vc.get(r["venue"], 0) + 1
venue_tbl = "\n".join(f"| {k} | {n} |" for k, n in sorted(_vc.items(), key=lambda x: (-x[1], x[0]))[:25])
q_tbl = "\n".join(f"| {q['community']} | `{q['query_form']}` | {q['returned_kept']} | crossref={q['crossref_status']}; "
                  f"arxiv={q['arxiv_status']} |" for q in S["query_log"])
top_l2 = "\n".join(f"- **{r['level_rule']}** (rule, unverified) — {r['title'][:120]} ({r['venue'][:44]}, {r['year']}), "
                   f"{r['community']}; matched {r['matched'][:150]}"
                   for r in l2[:40])
_mr = [r.get("verify_status", "") for r in csv.DictReader(io.StringIO(
    (PAP / "literature_matrix.csv").read_text(encoding="utf-8", errors="replace")))]
_pend = sum(1 for s in _mr if "pending_hand_check" in s or "UNVERIFIED" in s.upper())
PEND = (f"{_pend} of {len(_mr)} rows in `literature_matrix.csv` still carry that status as this file is "
        "rewritten; the chain runs EXP-0111 to resolve the rest by recovering the abstract from an index")
PAP.joinpath("literature_background.md").write_text(f"""# P001 background and method literature (EXP-0065)

Generated by `02_shared_code/registry/record_exp0065_p001.py` from
`{pathlib.Path(hits[-1]).name}` and `{EXP.name}`. It exists because the series' own minimum is 20-30 directly
relevant works plus 50+ background/method works from at least three research communities, and P001's shared graded
set held 20 records from 2 venues before this pass. Nothing below is a claim of having read a paper: `level_rule` is
the frozen EXP-0057 screen applied to title+abstract. Every row this screen appends is written with `verify_status=pending_hand_check`, and the chain then runs EXP-0111 to resolve it: {PEND}.

## What was retrieved

{S['new_records']} new records from {S['queries_run']} query forms across four communities, deduplicated against every
record already held for this programme, and {E66['records']} carried forward into the graded file
`{EXP.name}`. Distinct venues: {S['distinct_venues_all']}.

EXP-0066 then filled in the abstracts Crossref had not deposited: {E66['needed_text']} of the {E66['records']} records
arrived without text, {E66['filled']} gained one from the Semantic Scholar batch index, and
{E66['rejected_on_title_mismatch']} were **refused** because the index's title did not agree with ours on at least
{6} content tokens - a wrong record is not allowed to supply the text a collision grade is based on.
{E66['status_counts']['known_without_abstract']} ids are known to that index but hold no abstract there and
{E66['status_counts']['all_null']} are unknown to it, so **{unread} of the {E66['records']} records are still unread**
and were graded from a title alone.

Grade distribution after the fill: {json.dumps(E66['grade_distribution_after'], ensure_ascii=False)};
records at L2 or above: **{E66['L2plus_after']}**.

| community | records | at L2+ | distinct venues | queries that contributed |
|---|---|---|---|---|
{comm_tbl}

Most frequent venues (first 25):

| venue | records |
|---|---|
{venue_tbl}

## Query battery, run as written

| community | query form | kept | per-source status |
|---|---|---|---|
{q_tbl}

Queries that returned zero records on a source are listed above with that status rather than removed; the count of
such cases is {len(zero)}.

## The L2+ screen (top 40 by rule grade)

{top_l2 if l2 else "None. The frozen EXP-0057 screen placed **no** record from this battery at L2 or above, so no row "
                   "was appended to `literature_matrix.csv` by this pass and nothing here is cited as prior work. "
                   "What that does and does not mean is stated in the next section, not left for a reader to infer."}

## What "zero at L2+" does and does not mean

It means: within {E66['records']} records surfaced by these {S['queries_run']} query forms, the frozen rule found no
work whose title and abstract co-mention P001's object family (tool/function retrieval, selection, MCP, API retrieval)
**and** its construct family (query performance prediction, query difficulty, pre-retrieval, failure prediction).
It does **not** mean no such work exists, for three measured reasons:

1. {unread} of the {E66['records']} records were graded from a title alone because no reachable source holds their
   abstract; the rule cannot fire on text that was never read.
2. The battery is phrase-based and fixed in advance; a construct described with different words ("bad query",
   "query hardness", "retrieval failure diagnosis") sits outside these particular forms.
3. The rule is strict by design and was not loosened for this pass - the same thresholds that produced EXP-0057's
   grades were imported unchanged.

The paper's collision basis therefore remains the {len(body) - added} curated rows already in
`literature_matrix.csv`, which include the L2/L3 works found by the earlier targeted passes; this expansion adds
background breadth and one negative screen result, and is reported as such.

## Limits of this pass

* It is a **screen**, not a review: {added} records were appended to `literature_matrix.csv`, each written as
  `pending_hand_check` and resolved afterwards where a source could be reached. {PEND}. A rule grade counts term-family co-occurrence in title and abstract; it cannot tell a
  genuine collision from a paper that merely uses the same words.
* Coverage is bounded by two indexes (Crossref for discovery, Semantic Scholar for missing abstract text). Anything
  indexed only elsewhere is absent, and OpenAlex does not connect from this host (measured in EXP-0063).
* The query battery was fixed before running and is not exhaustive; a different phrasing can surface different work.
""", encoding="utf-8", newline="")
print("[e65] wrote literature_background.md")

# ---------------------------------------------------------------- 4. registry
p = REG / "experiment_registry.csv"
txt = p.read_text(encoding="utf-8")
have_ids = {r[0] for r in csv.reader(io.StringIO(txt)) if r}
if "EXP-0065" not in have_ids:
    row = ["EXP-0065", "P001", "success_LITERATURE_EXPANDED_TO_4_COMMUNITIES",
           "02_shared_code/literature/expand_p001_literature.py",
           f"{S['queries_run']} fixed query forms over Crossref query.bibliographic (journal-article + "
           "proceedings-article, sorted by relevance) and the arXiv export API via curl, 25 rows each; candidates kept "
           "only with a container title and abstract text; deduplicated against all programme-held records by DOI and "
           "normalised title; graded with the imported, unmodified EXP-0057 rule", "none",
           S["started_at"], S["finished_at"],
           f"{S['new_records']} new records with abstracts; grades {json.dumps(S['grade_distribution'])}; "
           f"{S['distinct_venues_all']} distinct venues; {len(l2)} at L2+",
           f"{EXP.name}; {pathlib.Path(hits[-1]).name}; papers/P001_routing_failure_qpp/literature_background.md",
           f"brings P001's literature pass to the series minimum ({added} L2+ screen rows appended to the curated "
           "matrix, all pending_hand_check, plus the documented background set); it does not by itself change any "
           "novelty claim - the appended rows must be read before they are cited", "yes - literature matrix + background note"]
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\r\n").writerow(row)
    p.write_text(txt.rstrip("\r\n") + "\r\n" + buf.getvalue().rstrip("\r\n") + "\r\n", encoding="utf-8", newline="")
    print("[e65] registered EXP-0065")
if "EXP-0066" not in {r[0] for r in csv.reader(io.StringIO(p.read_text(encoding="utf-8"))) if r}:
    row = ["EXP-0066", "P001", "success_ABSTRACT_FILLED_L2PLUS_STILL_ZERO",
           "02_shared_code/literature/fill_expansion_abstracts.py",
           f"Semantic Scholar batch lookup of the {E66['needed_text']} expanded records that arrived without abstract "
           "text; a fill accepted only above a 6-shared-token title agreement; the imported EXP-0057 rule re-run on "
           "the fuller text; EXP-0065's artefact left in place and a v2 file written", "none",
           E66["started_at"], E66["finished_at"],
           f"filled={E66['filled']} rejected_on_title_mismatch={E66['rejected_on_title_mismatch']} "
           f"with_abstract={E66['with_abstract_now']}/{E66['records']} L2plus={E66['L2plus_after']}",
           f"{EXP.name}; {E66['out']}; "
           f"{[pathlib.Path(x).name for x in glob.glob(str(ROOT / 'results_raw' / 'EXP0066_expansion_abstracts_*.json'))][0]}; "
           "papers/P001_routing_failure_qpp/literature_background.md",
           "makes the expansion readable for most records and still finds nothing at L2+, which is reported as a "
           f"bounded negative: {unread} records remain unread and the battery is phrase-based; the novelty basis stays "
           "the curated matrix", "yes - literature_background.md"]
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\r\n").writerow(row)
    p.write_text(p.read_text(encoding="utf-8").rstrip("\r\n") + "\r\n" + buf.getvalue().rstrip("\r\n") + "\r\n",
                 encoding="utf-8", newline="")
    print("[e65] registered EXP-0066")
import pandas as pd
d = pd.read_csv(p)
assert not d.exp_id.duplicated().any()
print(f"[e65] registry rows={len(d)}; matrix rows={len(body)}; L2+ appended={added}")
