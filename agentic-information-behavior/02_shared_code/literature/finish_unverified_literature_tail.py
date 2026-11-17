"""EXP-0111: finish the literature rows whose shipped status says a human still has to look at them.

Two wordings survive in the matrices after every retrieval round: `pending_hand_check (...)` and
`UNVERIFIED - found by search ...`. Both state an action by a person, so they are outstanding manual steps inside a
package that is meant to be reproducible without one - and a reader cannot tell whether the work was never attempted
or attempted and failed. EXP-0095 established the distinction is measurable: it probed Crossref, OpenAlex and
Semantic Scholar with positive and negative controls and recorded 54 recoveries and 35 rows where no channel returned
text. What it did not try is the arXiv export API, because its loop worked on DOI-bearing rows (89 of 94 targets),
so an arXiv-only record stayed "UNVERIFIED" with the block having come from a *rendered web page* (HTTP 403 on
arxiv.org/html), not from the API that this environment has already validated.

Pre-declared decision rule, fixed before any request was sent:
  1. select every row in the five package matrices and the programme matrix whose verify_status matches
     /pending_hand_check|UNVERIFIED/i;
  2. for each, try the channels in the order arXiv export API (when an arXiv id is present), Crossref, OpenAlex,
     Semantic Scholar; keep the HTTP status per attempt, because a 200 with no abstract field, a 404, a 429 and a
     connection failure are four different findings;
  3. if an abstract of >= 120 characters comes back, append a row to `literature_abstracts_v3.csv` tagged with the
     channel and rewrite verify_status to say the text was recovered, and by which experiment. The rule grade is NOT
     copied here: `reconcile_collision_levels.py`, which every package chain already runs, owns levels;
  4. if no channel returns text, rewrite verify_status to a terminal statement naming the channels tried and the
     consequence - title-only, excluded from positive novelty evidence - so no human action is implied;
  5. never change an `overlap_level` value and never drop a row: an unrecoverable record stays visible as one.

Nothing here can rescue a claim: it only makes the shipped record say what was actually tried.

    python 02_shared_code/literature/finish_unverified_literature_tail.py
"""
from __future__ import annotations

import csv, io, json, pathlib, re, subprocess, sys, time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REG = ROOT / "00_program_registry"
ABS_V3 = REG / "literature_abstracts_v3.csv"
OUT = ROOT / "results_raw"
MIN_ABSTRACT = 120                       # shorter than this is a snippet or an abstract-less landing page
UA = "agentic-information-behavior-programme/1.0 (research use; contact via repository)"
TIMEOUT = 25
# The three wordings that say a person still has to look, plus UNRECOVERABLE_IN_ENVIRONMENT: that one is terminal, but
# a re-run must revisit it, because a channel can be briefly unreachable on a later run while the abstract recovered
# earlier is still on file - and a transient failure must not be republished as a permanent finding.
PENDING = re.compile(r"pending_hand_check|UNVERIFIED|UNRECOVERABLE_IN_ENVIRONMENT", re.I)

STATUSES: dict[str, str] = {}            # url -> last HTTP status or exception class, so failure modes stay distinct


def fetch(url: str, retries: int = 2):
    """GET with curl, returning the body or None; every attempt's status is recorded rather than collapsed.

    `-L` matters: this environment returns HTTP 301 with an empty body for the plain-HTTP arXiv export endpoint, and a
    fetcher that reads "not 200" as "unreachable" would keep a record labelled unverified that is one redirect away.
    """
    for _ in range(retries + 1):
        try:
            r = subprocess.run(["curl", "-sS", "-L", "-o", "-", "-w", "\n%{http_code}", "--max-time", str(TIMEOUT),
                                "-A", UA, url], capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=TIMEOUT + 10)
        except Exception as e:
            STATUSES[url] = f"exception:{type(e).__name__}"
            continue
        body, _, code = (r.stdout or "").rpartition("\n")
        STATUSES[url] = code.strip() or "no-status"
        if code.strip() == "200" and body.strip():
            return body
    return None


def _oa_text(doc: dict) -> str:
    """OpenAlex returns an abstract as an inverted index (word -> positions); rebuild the text by position."""
    pos = {i: w for w, idxs in ((doc or {}).get("abstract_inverted_index") or {}).items() for i in idxs}
    return " ".join(pos[i] for i in sorted(pos))


def _json_field(body: str, pick):
    try:
        return re.sub(r"\s+", " ", str(pick(json.loads(body)) or "")).strip()
    except Exception:
        return ""


def try_channels(row: dict) -> tuple[str, str, str]:
    """Return (channel, abstract, attempt-log). Channels are tried in the order fixed in the docstring."""
    tried = []

    def attempt(name: str, url: str, pick):
        body = fetch(url)
        ab = _json_field(body, pick) if body else ""
        tried.append(f"{name}={STATUSES.get(url, '?')}/{len(ab)}ch")
        return ab

    text = f"{row.get('identifier') or ''} {row.get('url') or ''}"
    m = re.search(r"(\d{4}\.\d{4,5})(?:v\d+)?(?:\W|$)", text)
    if m:
        # the export API answers Atom, so this channel is parsed from the body rather than through `attempt`
        url = f"https://export.arxiv.org/api/query?id_list={m.group(1)}&max_results=1"
        body = fetch(url) or ""
        mm = re.search(r"<summary>(.*?)</summary>", body, re.S)
        ab = re.sub(r"\s+", " ", mm.group(1)).strip() if mm else ""
        tried.append(f"arxiv-export-api={STATUSES.get(url, '?')}/{len(ab)}ch")
        if len(ab) >= MIN_ABSTRACT:
            return "arxiv-export-api", ab, "; ".join(tried)

    doi = ""
    for k in ("url", "identifier", "code_or_data_public"):
        d = re.search(r"10\.\d{4,9}/[-+./;()_:A-Za-z0-9]+", str(row.get(k) or ""))
        if d:
            doi = d.group(0).rstrip(".,;)")
            break
    if doi:
        for name, url, pick in (
            ("crossref", f"https://api.crossref.org/works/{doi}", lambda j: (j.get("message") or {}).get("abstract")),
            ("openalex", f"https://api.openalex.org/works/https://doi.org/{doi}", _oa_text),
            ("semanticscholar", f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=abstract",
             lambda j: j.get("abstract"))):
            ab = attempt(name, url, pick)
            if len(ab) >= MIN_ABSTRACT:
                return name, ab, "; ".join(tried)
    return "", "", "; ".join(tried) or "no arXiv id and no DOI: no channel applicable"


def register_self(res: dict, started: str) -> str:
    """Add (or refresh) this run's row in the experiment registry, so the numbers above stay traceable."""
    p = REG / "experiment_registry.csv"
    rows = list(csv.reader(io.StringIO(p.read_text(encoding="utf-8", errors="replace"))))
    hdr, body = rows[0], rows[1:]
    row = {"exp_id": "EXP-0111", "paper_id": "P001;P004",
           "stage": "e77_finish_pending_literature_tail",
           "script": "02_shared_code/literature/finish_unverified_literature_tail.py",
           "config": f"min_abstract_chars={MIN_ABSTRACT}; channels=arxiv-export-api,crossref,openalex,semanticscholar",
           "seed": "n/a", "started_at": started, "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "status": f"{res['recovered_n']} recovered, {res['terminal_n']} terminal of {res['targets']}",
           "outputs": "; ".join(res["raw_files"]),
           "notes": ("clears the two wordings that implied an outstanding human check. The arXiv export endpoint "
                     "answered HTTP 301 to plain-HTTP requests, so a record EXP-0095 logged as unreachable proved to "
                     "be one redirect away - recorded rather than quietly reclassified."),
           "enters_paper": "no - it changes a verification status, not a number in the paper",
           "topic_id": "T037;T024"}
    out = [row.get(c, "") for c in hdr]
    idx = next((i for i, r in enumerate(body) if r and r[0] == "EXP-0111"), None)
    if idx is None:
        body.append(out)
        action = "registered EXP-0111"
    else:
        body[idx] = out
        action = "refreshed EXP-0111's row"
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\r\n").writerows([hdr] + body)
    p.write_text(buf.getvalue(), encoding="utf-8", newline="")
    return action


def hand_assignments():
    """The (paper, identifier) -> (level, reason) judgements, read from the recorder's source by ast.

    `reconcile_collision_levels.py` extracts the same dict the same way: importing the recorder would re-run a
    programme step, and re-typing the reasons here would put one judgement in two places that can disagree.
    """
    src = (ROOT / "02_shared_code" / "registry" / "record_novelty_grading.py").read_text(encoding="utf-8")
    m = re.search(r"^FINAL = (\{.*?^\})", src, re.M | re.S)
    if not m:
        raise SystemExit("ABORT: the hand-assignment dict is not where record_novelty_grading.py keeps it")
    import ast
    return ast.literal_eval(m.group(1))


def _set_cells(path: pathlib.Path, cite_key: str, cells: dict, pred=None) -> int:
    """Rewrite named columns of one record's row, keeping CRLF and column order; returns rows touched."""
    pred = pred or PENDING.search
    txt = path.read_text(encoding="utf-8", errors="replace")
    rows = list(csv.reader(io.StringIO(txt)))
    if not rows:
        return 0
    hdr, idx = rows[0], {c: i for i, c in enumerate(rows[0])}
    if "cite_key" not in hdr:
        return 0
    n = 0
    for r in rows[1:]:
        if len(r) <= idx["cite_key"] or r[idx["cite_key"]] != cite_key:
            continue
        for col, fn in cells.items():
            i = idx.get(col)
            if i is None or i >= len(r):
                continue
            cur = r[i] or ""
            if col == "verify_status" and not pred(cur):
                continue
            if col == "differentiation" and not re.search(r"no abstract|not cited|until read|empty on purpose",
                                                           cur, re.I):
                continue                      # a real differentiation already exists; never overwrite analysis
            r[i] = fn(cur)
        n += 1
    if n:
        buf = io.StringIO()
        csv.writer(buf, lineterminator="\r\n").writerows(rows)
        path.write_text(buf.getvalue(), encoding="utf-8", newline="")
    return n


def _diff_text(pid: str, row: dict, graded: dict, final: dict) -> str:
    """The differentiation cell for a record whose abstract has just become readable.

    These cells asserted "no abstract at any source; not cited as prior work until read" - after recovery that is false,
    and the sentence is load-bearing because the manuscript's related-work section is assembled from this column. The
    reason comes from the recorded hand assignment where one exists, so the judgement lives in exactly one place.
    """
    g = graded.get((pid, row.get("cite_key"))) or {}
    lvl = (re.match(r"L[0-4]", str(g.get("level_rule") or row.get("overlap_level") or "")) or [None, ""])[0]
    hand = final.get((pid, row.get("identifier") or row.get("url") or ""))
    if hand:
        return f"hand-graded {hand[0]} (EXP-0059): {hand[1]}"
    # Below L3 the cell stays empty on purpose: `manuscript_sections.related_work` emits one bullet per *non-empty*
    # differentiation, so writing "this is background, not differentiated" there would put the record in the paper's
    # list of curated neighbours - the opposite of what the sentence says.
    return "" if lvl in ("L0", "L1", "L2", "") else (
        f"abstract recovered (EXP-0111) and rule-graded {lvl} (EXP-0097 on the recovered text); no hand assignment "
        "recorded, so the level is the rule's and is flagged for review")


def matrices():
    for p in sorted((ROOT / "papers").glob("*/literature_matrix.csv")):
        yield p
    yield REG / "shared_literature" / "literature_matrix.csv"


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report the selected rows without contacting any channel")
    ap.add_argument("--refill", action="store_true",
                    help="also revisit rows a previous EXP-0111 run marked recovered, to make sure the text really "
                         "reached the abstracts file (the first run skipped rows that already existed with no text)")
    a = ap.parse_args()
    pred = (lambda s: bool(PENDING.search(s)) or (a.refill and s.startswith("abstract recovered")))
    graded = {}
    if (REG / "literature_graded.csv").is_file():
        for r in csv.DictReader(io.StringIO((REG / "literature_graded.csv").read_text(encoding="utf-8",
                                                                                       errors="replace"))):
            graded[(r.get("paper_id"), r.get("cite_key"))] = r
    final = hand_assignments()
    sys.stdout.reconfigure(encoding="utf-8")

    targets = []
    for f in matrices():
        txt = f.read_text(encoding="utf-8", errors="replace")
        rdr = csv.DictReader(io.StringIO(txt))
        for i, row in enumerate(rdr or []):
            if row and pred(str(row.get("verify_status") or "")):
                targets.append((f, i, row))
    print(f"  rows whose shipped status implies a pending human check: {len(targets)}")
    for f, _i, r in targets:
        print(f"    {f.parent.name}/{f.name}: {r.get('cite_key','?')[:34]} | {(r.get('title') or '')[:60]}")
    if a.check:
        # a non-zero exit here is the chain's own guard: a shipped matrix must not carry a row whose status reads as
        # a person owing a check. Recovery is this script's ordinary (network) mode, so the guard is only reached
        # after that mode has run in the same chain.
        if targets:
            print(f"  CHECK FAILED: {len(targets)} row(s) still carry a pending status after recovery was attempted")
            return 1
        return 0

    if not targets:
        # a run with no subject must not log a result: this step is wired into every package chain, and writing an
        # EXP-0111 record each time would manufacture five experiment rows per rebuild and register a measurement
        # that measured nothing.
        print("  nothing to resolve: every shipped row already carries a terminal status, so no run is logged")
        return 0

    t0 = time.time()
    started = time.strftime("%Y-%m-%dT%H:%M:%S")
    recovered, terminal = [], []
    # one record can appear in a package matrix and in the programme matrix; ask the channels once per cite_key
    cache: dict[str, tuple[str, str, str]] = {}
    ab_rows = list(csv.DictReader(io.StringIO(ABS_V3.read_text(encoding="utf-8", errors="replace")))) if \
        ABS_V3.is_file() else []
    # the file keys rows positionally (`0007|cite_key`), so dedupe on (paper_id, cite_key) and number new rows next
    seen_abs = {(r.get("paper_id"), r.get("cite_key")) for r in ab_rows}
    for f, _i, row in targets:
        pid = (row.get("paper_id") or "").strip() or (f.parent.name.split("_")[0] if f.parent.parent.name == "papers"
                                                      else "")
        ck = row.get("cite_key") or ""
        if ck not in cache:
            cache[ck] = try_channels(row)
        chan, ab, log = cache[ck]
        rec = {"cite_key": row.get("cite_key"), "paper_id": pid, "channel_log": log, "outcome": "unrecoverable"}
        if ab:
            rec["outcome"] = "already stored"        # overwritten below when the row actually changes
            here = next((r for r in ab_rows if (r.get("paper_id"), r.get("cite_key")) == (pid, row.get("cite_key"))),
                        None)
            if here is not None:
                # the record already had a row with no abstract text on it - the state all four of these were in - so
                # fill that row rather than skipping it and leaving the recovered text unsaved
                if len(here.get("abstract") or "") < len(ab):
                    here.update(abstract=ab, abstract_present="1", abstract_source=f"EXP-0111 {chan}",
                                source="EXP-0111")
                    rec.update(outcome="filled an existing abstract row", channel=chan)
            elif pid:
                ab_rows.append({"paper_id": pid, "cite_key": row.get("cite_key"), "source": "EXP-0111",
                                "identifier": row.get("identifier") or row.get("url") or "", "year": row.get("year"),
                                "venue": row.get("venue"), "title": row.get("title"), "abstract": ab,
                                "abstract_present": "1", "collision_target": row.get("collision_target"),
                                "overlap_level_current": row.get("overlap_level"), "url": row.get("url"),
                                "row_key": f"{len(ab_rows):04d}|{row.get('cite_key')}",
                                "abstract_source": f"EXP-0111 {chan}"})
                seen_abs.add((pid, row.get("cite_key")))
                rec.update(outcome="appended an abstract row", channel=chan)
            rec["abstract_words"] = len(ab.split())
            new = (f"abstract recovered via {chan} on {time.strftime('%Y-%m-%d')} (EXP-0111; {log}); "
                   "rule re-grade left to reconcile_collision_levels.py, which every package chain runs")
            recovered.append(rec)
        else:
            on_file = next((r for r in ab_rows
                            if (r.get("paper_id"), r.get("cite_key")) == (pid, row.get("cite_key"))
                            and len(r.get("abstract") or "") >= MIN_ABSTRACT), None)
            if on_file is not None:
                # the text is already in the store from an earlier successful probe, so this run's failure is about the
                # channel right now, not about the record
                new = (f"abstract on file via {on_file.get('abstract_source') or 'EXP-0111'} "
                       f"({len(on_file['abstract'])} chars); this run's re-probe did not reach a channel ({log}, "
                       f"{time.strftime('%Y-%m-%d')})")
                rec.update(outcome="recovered from the on-file abstract", channel=on_file.get("abstract_source"))
                recovered.append(rec)
            else:
                new = (f"UNRECOVERABLE_IN_ENVIRONMENT: no abstract returned by any tried channel ({log}, "
                       f"{time.strftime('%Y-%m-%d')}, EXP-0111). Title-only evidence, excluded from positive novelty "
                       "claims; the record stays listed rather than being dropped.")
                terminal.append(rec)
        _set_cells(f, row.get("cite_key"), {"verify_status": lambda _c: new,
                                            "differentiation": lambda _c: _diff_text(pid, row, graded, final)}, pred)
        print(f"    {row.get('cite_key','?')[:30]}: {rec['outcome']} ({log})")

    hdr = list(ab_rows[0].keys()) if ab_rows else []
    if hdr:
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=hdr, lineterminator="\r\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(ab_rows)
        ABS_V3.write_text(buf.getvalue(), encoding="utf-8", newline="")

    res = {"exp_id": "EXP-0111", "at": time.strftime("%Y-%m-%dT%H:%M:%S"), "wallclock_sec": round(time.time() - t0, 1),
           "targets": len(targets), "recovered": recovered, "unrecoverable": terminal,
           "recovered_n": len(recovered), "terminal_n": len(terminal),
           "http_status_by_url": STATUSES, "min_abstract_chars": MIN_ABSTRACT,
           "levels_touched": 0,
           "rule": "no overlap_level value is written here; a recovered abstract is re-graded by the chain's own "
                   "reconciler, and an unrecoverable one is labelled terminal with the channels tried"}
    OUT.mkdir(exist_ok=True)
    o = OUT / f"EXP0111_literature_tail_{time.strftime('%Y%m%dT%H%M%S')}.json"
    res["raw_files"] = [f"results_raw/{o.name}", ABS_V3.relative_to(ROOT).as_posix()]
    o.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"  {len(recovered)} recovered, {len(terminal)} terminal | wrote {o.relative_to(ROOT)} | "
          f"{register_self(res, started)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
