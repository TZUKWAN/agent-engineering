"""EXP-0063: recover the abstracts Crossref and arXiv did not serve, from the one bibliographic API that answers.

`fetch_abstracts.py` (EXP-0056) left 94 of 287 retrieved records with no abstract, and `grade_collisions.py`
(EXP-0057) cannot honestly grade an overlap level from a title alone - those records are marked `graded_on=title_only`
and stay undecidable, which is a hole in the literature pass of every paper in the series. The premise that no other
abstract source is reachable was measured, not assumed: OpenAlex fails to connect from this host, while
`api.semanticscholar.org` answers and its batch endpoint returns real abstract text (verified on three probe ids
before this script was written).

Fixed before the first request:
  * read-only: the frozen `literature_abstracts.csv` is never modified; results go to
    `literature_abstracts_s2.csv` next to it, one row per attempted record, with the HTTP outcome recorded;
  * id preference DOI: -> ARXIV: -> title search, and the id kind actually used is stored per row, so a later reader
    can tell a matched record from a fuzzy one;
  * batches of 50 (the documented batch size), 3 tries with linear backoff, and a three-way per-batch status -
    `informative` (at least one row came back with text or an explicit null), `all_null` (the API answered and knows
    none of them), `transport_error` (we learned nothing). Only the third is retried by `--resume`;
  * a title-search match is accepted only when the normalised titles share at least 6 content tokens, so a wrong
    paper can never supply the abstract that a collision grade is based on;
  * no inference API is called: this is a metadata/bibliographic service returning stored text.

    python fetch_abstracts_s2.py [--resume]

Writes 00_program_registry/literature_abstracts_s2.csv and literature_abstracts_s2_checkpoint.json.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]
REG = ROOT / "00_program_registry"
SRC = REG / "literature_abstracts.csv"
OUT = REG / "literature_abstracts_s2.csv"
CKPT = REG / "literature_abstracts_s2_checkpoint.json"
BATCH_URL = "https://api.semanticscholar.org/graph/v1/paper/batch"
SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
FIELDS = "title,abstract,externalIds,venue,year,paperId"
BATCH = 50
UA = {"User-Agent": "aib-series-literature-audit/1.0 (research metadata retrieval)",
      "Content-Type": "application/json"}
MIN_SHARED_TOKENS = 6


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())


def tokens(s: str) -> set:
    return {w for w in norm(s).split() if len(w) > 2}


def s2_id(row: dict):
    """Return (kind, id) in DOI -> arXiv order, or (None, None) when no stable identifier is stored."""
    ident = (row.get("identifier") or "").strip()
    if not ident:
        return None, None
    if re.match(r"^10\.\d{4,9}/", ident):
        return "DOI", "DOI:" + ident
    m = re.search(r"(?:arxiv[:/]\s*)?((?:\d{4}\.\d{4,5})|(?:\d{6}/\d{5})(?:v\d+)?)", ident, re.I)
    if m and (row.get("source") == "arxiv" or "arxiv" in ident.lower()):
        return "ARXIV", "ARXIV:" + m.group(1)
    return None, None


def post(ids):
    body = json.dumps({"ids": ids}).encode()
    last = None
    for a in range(3):
        try:
            req = urllib.request.Request(BATCH_URL + "?fields=" + FIELDS, data=body, headers=UA, method="POST")
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode()), None
        except Exception as exc:                                    # network is the boundary here
            last = f"{type(exc).__name__}: {exc}"
            time.sleep(2 + 2 * a)
    return None, last


def search(title: str):
    q = urllib.parse.urlencode({"query": title, "fields": FIELDS, "limit": 5})
    last = None
    for a in range(3):
        try:
            req = urllib.request.Request(SEARCH_URL + "?" + q, headers=UA)
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode()).get("data", []), None
        except Exception as exc:
            last = f"{type(exc).__name__}: {exc}"
            time.sleep(3 + 3 * a)
    return None, last


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()

    rows = list(csv.DictReader(io.StringIO(SRC.read_text(encoding="utf-8"))))
    # `paper_id` names the PAPER (five distinct values across 287 records) and no single column is unique, so a record
    # is addressed by its position in the frozen file plus its cite_key. The first run of this script keyed on
    # paper_id and collapsed 89 attempts into 3 rows, which is why the key is built here and nowhere else.
    for i, r in enumerate(rows):
        r["row_key"] = f"{i:04d}|{r['cite_key']}"
    todo = [r for r in rows if r.get("abstract_present") == "0"]
    n_missing_total = len(todo)
    print(f"EXP-0063 | {len(rows)} retrieved records, {len(todo)} without an abstract", flush=True)

    state = {}
    if args.resume and CKPT.exists():
        state = json.loads(CKPT.read_text(encoding="utf-8"))
        print(f"  resuming with {len(state)} already-attempted row_keys", flush=True)
    todo = [r for r in todo if r["row_key"] not in state]
    print(f"  {len(todo)} to attempt now", flush=True)

    sid_kind, by_sid, no_id = {}, {}, []
    for r in todo:
        kind, sid = s2_id(r)
        if sid:
            by_sid.setdefault(sid, []).append(r["row_key"])
            sid_kind[sid] = kind
        else:
            no_id.append(r)
    sids = sorted(by_sid)
    print(f"  {len(sids)} distinct stable ids covering {sum(len(v) for v in by_sid.values())} records; "
          f"{len(no_id)} records have no id and will be title-searched", flush=True)

    t0 = time.time()
    stats = {"informative": 0, "all_null": 0, "transport_error": 0, "recovered": 0, "title_match_rejected": 0}
    for bi in range(0, len(sids), BATCH):
        chunk = sids[bi:bi + BATCH]
        res, err = post(chunk)
        if res is None:
            stats["transport_error"] += 1
            print(f"  batch {bi // BATCH + 1}: transport_error {err}", flush=True)
            continue
        got_text = 0
        for sid, rec in zip(chunk, res):
            ab = (rec or {}).get("abstract") or ""
            if ab:
                got_text += 1
                stats["recovered"] += 1
            entry = {"attempted_via": sid_kind[sid], "queried": sid, "s2_paper_id": (rec or {}).get("paperId"),
                     "s2_title": (rec or {}).get("title"), "abstract": ab or None,
                     "abstract_chars": len(ab), "status": "informative" if rec else "all_null",
                     "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
            for rk in by_sid[sid]:
                state[rk] = dict(entry)
        stats["informative" if got_text else "all_null"] += 1
        print(f"  batch {bi // BATCH + 1}: {got_text}/{len(chunk)} ids returned abstract text "
              f"({round(time.time() - t0)}s)", flush=True)
        CKPT.write_text(json.dumps(state, indent=1, ensure_ascii=False), encoding="utf-8", newline="")
        time.sleep(1.2)

    for r in no_id:
        pid = r["row_key"]
        data, err = search(r["title"])
        if data is None:
            state[pid] = {"attempted_via": "title_search", "queried": r["title"], "abstract": None,
                          "abstract_chars": 0, "status": "transport_error", "error": err,
                          "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
            stats["transport_error"] += 1
            continue
        best = None
        for rec in data:
            if len(tokens(rec.get("title", "")) & tokens(r["title"])) >= MIN_SHARED_TOKENS:
                best = rec
                break
        if best is None:
            stats["title_match_rejected"] += 1
            state[pid] = {"attempted_via": "title_search", "queried": r["title"], "abstract": None,
                          "abstract_chars": 0, "status": "no_title_match",
                          "candidates_returned": len(data), "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
        else:
            ab = best.get("abstract") or ""
            if ab:
                stats["recovered"] += 1
            state[pid] = {"attempted_via": "title_search", "queried": r["title"],
                          "s2_paper_id": best.get("paperId"), "s2_title": best.get("title"),
                          "abstract": ab or None, "abstract_chars": len(ab),
                          "status": "informative" if ab else "all_null",
                          "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
        CKPT.write_text(json.dumps(state, indent=1, ensure_ascii=False), encoding="utf-8", newline="")
        time.sleep(1.2)

    hdr = ["row_key", "paper_id", "cite_key", "source", "identifier", "title", "attempted_via", "queried",
           "s2_paper_id", "s2_title", "abstract_chars", "status", "error", "abstract", "fetched_at"]
    by = {r["row_key"]: r for r in rows}
    out = []
    for rk, v in state.items():
        r = by.get(rk, {})
        out.append({"row_key": rk, "paper_id": r.get("paper_id", ""), "cite_key": r.get("cite_key", ""),
                    "source": r.get("source", ""), "identifier": r.get("identifier", ""),
                    "title": r.get("title", ""), **{k: v.get(k) for k in hdr[6:]}})
    out.sort(key=lambda d: d["row_key"])
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=hdr, lineterminator="\r\n", extrasaction="ignore")
    w.writeheader()
    w.writerows(out)
    OUT.write_text(buf.getvalue(), encoding="utf-8", newline="")
    CKPT.write_text(json.dumps(state, indent=1, ensure_ascii=False), encoding="utf-8", newline="")
    res = {"exp_id": "EXP-0063", "source_file": SRC.name, "out_file": OUT.name,
           "records_without_abstract": n_missing_total,
           "attempted": len(state), "batches": stats,
           "with_abstract_now": sum(1 for v in state.values() if v.get("abstract")),
           "still_title_only": sum(1 for v in state.values() if not v.get("abstract")),
           "wallclock_sec": round(time.time() - t0, 1),
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t0)),
           "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    print(json.dumps(res, indent=1), flush=True)
    (REG / "EXP0063_s2_summary.json").write_text(json.dumps(res, indent=1, ensure_ascii=False),
                                                 encoding="utf-8", newline="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
