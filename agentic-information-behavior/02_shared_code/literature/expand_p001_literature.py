"""EXP-0065: bring P001's literature pass up to the series' own minimum, and grade it with the frozen rule.

The task list requires, per candidate paper, 20-30 directly relevant works, 50+ background/method works and coverage
of at least three research communities. Measured against that, P001's shared graded set holds **20 records from 2
venues with 1 at L2 or above** - the thinnest literature base in the series, on the paper that carries the flagship
claim. Its own `literature_matrix.csv` has the same 20 rows. This is a retrieval gap, not an analysis gap, so it is
closed by retrieving.

Fixed before the first query:
  * the query battery below is written first and run as written; every query is logged with its exact form and its
    outcome, including the ones that return nothing, because a novelty audit that only lists successful queries is not
    an audit;
  * four communities, so the "only NLP" objection cannot be made: IR/NLP, HCI & information behaviour, ML/agents,
    and software & data engineering;
  * Crossref `query.bibliographic` (measured reachable, and it deposits abstract text) plus the arXiv export API over
    curl (urllib is refused 406 from this host - measured in EXP-0047);
  * a candidate is kept only with a container title and either an abstract or an arXiv summary, so nothing enters the
    matrix unread;
  * deduplication against everything already retrieved in this programme, by DOI (version suffix stripped) and by
    normalised title;
  * grading uses `grade_collisions.grade()` imported unchanged - the same rule that produced EXP-0057's grades, so an
    expansion cannot quietly invent a friendlier overlap criterion.

    python expand_p001_literature.py

Writes 00_program_registry/literature_p001_expansion.csv, its checkpoint, and
results_raw/EXP0065_p001_expansion_summary.json.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import pathlib
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from grade_collisions import grade  # noqa: E402  - the frozen rule, imported not copied

ROOT = HERE.parents[1]
REG = ROOT / "00_program_registry"
OUT = REG / "literature_p001_expansion.csv"
CKPT = REG / "literature_p001_expansion_checkpoint.json"
SUM = ROOT / "results_raw" / f"EXP0065_p001_expansion_summary_{time.strftime('%Y%m%dT%H%M%S')}.json"
UA = {"User-Agent": "aib-series-literature-audit/1.0 (research metadata retrieval)"}
ROWS_PER_QUERY = 25
SELECT = "DOI,title,abstract,container-title,issued,type,is-referenced-by-count,URL"

QUERIES = {
    "IR/NLP": ["query performance prediction",
               "pre-retrieval query performance prediction",
               "query difficulty estimation retrieval",
               "zero result query retrieval failure",
               "bad query detection information retrieval",
               "tool retrieval large language model agents",
               "tool selection LLM agent benchmark",
               "function calling reliability language model",
               "retrieval confidence estimation dense passage",
               "query performance prediction without relevance feedback"],
    "HCI/information behaviour": ["uncertainty in information seeking",
                                  "search problem detection interactive retrieval",
                                  "sensemaking support human agents",
                                  "trust in automated search results",
                                  "cognitive load search interface evaluation",
                                  "information foraging task interruption"],
    "ML/agents": ["LLM agent tool routing failure",
                  "agent trajectory evaluation benchmark",
                  "tool augmented language model planning",
                  "model context protocol tool server",
                  "reliability of LLM agent tool use"],
    "software/data engineering": ["API recommendation machine learning",
                                  "schema matching evaluation",
                                  "metadata quality assessment datasets",
                                  "data catalogue discoverability study"],
}


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", (s or "").lower()).strip()


def key_of(doi: str, title: str):
    d = re.sub(r"\.v\d+$", "", (doi or "").lower().strip())
    return ("doi:" + d) if d else ("title:" + norm(title)[:80])


def crossref(q: str):
    url = "https://api.crossref.org/works?" + urllib.parse.urlencode(
        {"query.bibliographic": q, "rows": ROWS_PER_QUERY, "select": SELECT,
         "filter": "type:journal-article,type:proceedings-article", "sort": "relevance"})
    last = None
    for a in range(3):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())["message"]["items"], None
        except Exception as exc:                                    # network is the boundary here
            last = f"{type(exc).__name__}: {exc}"
            time.sleep(2 + 2 * a)
    return None, last


def arxiv(q: str):
    """Return (blob, None) with entries, ("", None) for a genuine zero-result, or (None, error) if we learned nothing."""
    url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(
        {"search_query": f'all:"{q}"', "start": 0, "max_results": ROWS_PER_QUERY,
         "sortBy": "relevance", "sortOrder": "relevance"})
    last = "no entries returned by curl"
    for a in range(3):
        p = subprocess.run(["curl", "-s", "--max-time", "60", url], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        body = p.stdout or ""
        if "<entry" in body:
            return body, None
        if re.search(r"<opensearch:totalResults[^>]*>0</opensearch:totalResults>", body):
            return "", None                          # the API answered; this phrase genuinely has no records
        last = f"empty or malformed response ({len(body)} bytes, rc={p.returncode})"
        time.sleep(3 + 3 * a)
    return None, last


def parse_arxiv(blob: str):
    out = []
    for blk in blob.split("<entry>")[1:]:
        def tag(t):
            m = re.search(rf"<{t}[^>]*>(.*?)</{t}>", blk, re.S)
            return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
        link = tag("id")
        pub = tag("published")
        out.append({"doi": link.replace("https://doi.org/", "") if link.startswith("https://doi.org/") else "",
                    "title": tag("title"), "abstract": tag("summary"), "venue": "arXiv",
                    "year": pub[:4] if pub[:4].isdigit() else "", "url": link, "cited_by": ""})
    return out


def year(rec):
    parts = ((rec.get("issued") or {}).get("date-parts") or [[]])[0]
    return parts[0] if parts else ""


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    seen = set()
    for pat in ("literature_abstracts.csv", "literature_p001_expansion.csv"):
        p = REG / pat
        if p.exists():
            for r in csv.DictReader(io.StringIO(p.read_text(encoding="utf-8"))):
                seen.add(key_of(r.get("identifier") or r.get("DOI") or "", r.get("title", "")))
                seen.add("title:" + norm(r.get("title", ""))[:80])
    print(f"[e65] {len(seen)} existing keys to deduplicate against", flush=True)

    records, log = {}, []
    for community, qs in QUERIES.items():
        for q in qs:
            got = 0
            items, err = crossref(q)
            cr_status = "hits_returned" if items else ("zero_records" if items == [] else "transport_error")
            for rec in (items or []):
                t = (rec.get("title") or [""])[0]
                ct = (rec.get("container-title") or [""])[0]
                ab = re.sub(r"<[^>]+>", " ", rec.get("abstract") or "")
                if not t or not ct:
                    continue
                k = key_of(rec.get("DOI", ""), t)
                if k in seen or "title:" + norm(t)[:80] in seen:
                    continue
                seen.add(k); seen.add("title:" + norm(t)[:80])
                lvl, hit, n = grade("P001", t, ab)
                records[k] = {"key": k, "doi": rec.get("DOI", ""), "year": year(rec), "venue": ct,
                              "title": t, "abstract": ab.strip(), "abstract_chars": len(ab.strip()),
                              "source": "crossref", "community": community, "query": q,
                              "cited_by": rec.get("is-referenced-by-count", ""), "url": rec.get("URL", ""),
                              "level_rule": lvl, "matched": json.dumps(hit, ensure_ascii=False)}
                got += 1
            aitems, aerr = arxiv(q)
            ax = parse_arxiv(aitems) if aitems else []
            ax_status = "hits_returned" if ax else ("zero_records" if aitems == "" and not aerr else "transport_error")
            for rec in ax:
                k = key_of(rec.get("doi", ""), rec["title"])
                if k in seen or "title:" + norm(rec["title"])[:80] in seen:
                    continue
                seen.add(k); seen.add("title:" + norm(rec["title"])[:80])
                lvl, hit, n = grade("P001", rec["title"], rec["abstract"])
                records[k] = {"key": k, "doi": rec.get("doi", ""), "year": rec["year"], "venue": "arXiv",
                              "title": rec["title"], "abstract": rec["abstract"],
                              "abstract_chars": len(rec["abstract"]), "source": "arxiv",
                              "community": community, "query": q, "cited_by": "", "url": rec.get("url", ""),
                              "level_rule": lvl, "matched": json.dumps(hit, ensure_ascii=False)}
                got += 1
            log.append({"community": community, "query_form": f'query.bibliographic="{q}" + arXiv all:"{q}"',
                        "crossref_status": cr_status, "arxiv_status": ax_status, "returned_kept": got,
                        "error": f"{err or ''} {aerr or ''}".strip(),
                        "ran_at": time.strftime("%Y-%m-%dT%H:%M:%S")})
            print(f"  [{community[:14]:14s}] {q[:46]:46s} kept={got:3d} crossref={cr_status} arxiv={ax_status}",
                  flush=True)
            time.sleep(0.7)

    fields = ["key", "doi", "year", "venue", "title", "abstract_chars", "abstract", "source", "community", "query",
              "cited_by", "url", "level_rule", "matched"]
    rows = sorted(records.values(), key=lambda r: (r["community"], r["level_rule"], r["title"]))
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\r\n", extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    OUT.write_text(buf.getvalue(), encoding="utf-8", newline="")
    CKPT.write_text(json.dumps({"n": len(rows), "at": time.strftime("%Y-%m-%dT%H:%M:%S")}, indent=1),
                    encoding="utf-8", newline="")
    dist = {}
    for r in rows:
        dist[r["level_rule"]] = dist.get(r["level_rule"], 0) + 1
    per_comm = {}
    for r in rows:
        c = per_comm.setdefault(r["community"], {"n": 0, "L2plus": 0, "venues": set()})
        c["n"] += 1
        c["L2plus"] += int(r["level_rule"] in ("L2", "L3", "L4"))
        c["venues"].add(r["venue"])
    res = {"exp_id": "EXP-0065", "paper": "P001", "out_file": OUT.name,
           "queries_run": sum(len(v) for v in QUERIES.values()),
           "query_log": log,
           "new_records": len(rows), "grade_distribution": dist,
           "with_abstract": sum(1 for r in rows if r["abstract_chars"] > 0),
           "per_community": {k: {"n": v["n"], "L2plus": v["L2plus"], "distinct_venues": len(v["venues"])}
                             for k, v in per_comm.items()},
           "distinct_venues_all": len({r["venue"] for r in rows}),
           "rule_reused_verbatim": "grade_collisions.grade('P001', ...) imported, not copied",
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    SUM.parent.mkdir(exist_ok=True)
    SUM.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8", newline="")
    print(json.dumps({k: v for k, v in res.items() if k != "query_log"}, indent=1), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
