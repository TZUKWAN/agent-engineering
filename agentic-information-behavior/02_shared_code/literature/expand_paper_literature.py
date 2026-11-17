"""EXP-0067/0068: family-driven collision hunting for the papers whose directly-relevant count is below the minimum.

The task list asks for 20-30 directly relevant works per candidate paper. Measured against the frozen EXP-0057 screen,
P003 holds 9 and P004 holds 17. EXP-0065 showed why a hand-written phrase battery does not fix that: broad
relevance-sorted queries return background, not collisions, and 80% of Crossref rows arrive without abstract text, so
they are graded from a title and can never clear L2. This script does the two things that pass needs:

  1. queries are **derived from the paper's own term families** (the same `PAPERS[pid]` dictionaries the grading rule
     uses), so the battery hunts for the object/construct combination the rule rewards instead of for topics that
     merely sound adjacent;
  2. every candidate is filled with abstract text **before** it is graded - Crossref's deposited abstract first, then
     the Semantic Scholar batch index - and a candidate that still has no readable text is kept but flagged, never
     silently counted as screened.

Fixed before the first query:
  * the query list is generated deterministically from the families and printed in full before any request, so the
    battery can be audited against the result;
  * arXiv is queried over curl (urllib is refused 406 from this host - measured in EXP-0047);
  * a Semantic Scholar fill is accepted only when its title agrees with ours on at least 6 content tokens;
  * grading uses `grade_collisions.grade()` imported unchanged;
  * deduplication is against every record already held for this programme, by DOI (version suffix stripped) and by
    normalised title, and records are addressed by a per-record key - `paper_id` names the paper, not the record.

    python expand_paper_literature.py P003
    python expand_paper_literature.py P004

Writes 00_program_registry/literature_<pid>_expansion.csv and
results_raw/EXP006x_<pid>_family_expansion_summary_*.json.
"""

from __future__ import annotations

import csv
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
from fetch_abstracts_s2 import post, tokens                       # noqa: E402
from grade_collisions import PAPERS, grade                        # noqa: E402

ROOT = HERE.parents[1]
REG = ROOT / "00_program_registry"
UA = {"User-Agent": "aib-series-literature-audit/1.0 (research metadata retrieval)",
      "Content-Type": "application/json"}
ROWS_PER_QUERY = 25
SELECT = "DOI,title,abstract,container-title,issued,type,is-referenced-by-count,URL"
MIN_SHARED = 6
MAX_PAIR_QUERIES = 18
EXP_BY_PID = {"P001": "EXP-0065", "P002": "EXP-0069", "P003": "EXP-0067", "P004": "EXP-0068", "P005": "EXP-0070"}


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", (s or "").lower()).strip()


def key_of(doi: str, title: str):
    d = re.sub(r"\.v\d+$", "", (doi or "").lower().strip())
    return ("doi:" + d) if d else ("title:" + norm(title)[:80])


def build_queries(pid: str) -> list:
    """Deterministic: every construct phrase on its own, then object x construct pairs."""
    fam = PAPERS[pid]
    qs = [c for c in fam["construct"]]
    objs = fam["object"][:6]
    pairs = [f"{o} {c}" for c in fam["construct"] for o in objs]
    return qs + pairs[:MAX_PAIR_QUERIES]


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
    """(blob, None) with entries, ("", None) for a genuine zero-result, (None, err) when nothing was learned."""
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
            return "", None
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
                    "year": pub[:4] if pub[:4].isdigit() else "", "url": link})
    return out


def held_keys() -> set:
    seen = set()
    for pat in ("literature_abstracts.csv", "literature_p001_expansion_v2.csv", "literature_p003_expansion.csv",
                "literature_p004_expansion.csv"):
        p = REG / pat
        if p.exists():
            for r in csv.DictReader(io.StringIO(p.read_text(encoding="utf-8"))):
                seen.add(key_of(r.get("identifier") or r.get("doi") or r.get("DOI") or "", r.get("title", "")))
                seen.add("title:" + norm(r.get("title", ""))[:80])
    return seen


def main() -> int:
    pid = (sys.argv[1] if len(sys.argv) > 1 else "").strip()
    if pid not in PAPERS:
        raise SystemExit(f"usage: expand_paper_literature.py <P00x>; known: {sorted(PAPERS)}")
    EXP_ID = EXP_BY_PID[pid]
    sys.stdout.reconfigure(encoding="utf-8")
    qs = build_queries(pid)
    print(f"{EXP_ID} | {pid} | {len(qs)} queries derived from the paper's own term families:", flush=True)
    for q in qs:
        print("   ", q, flush=True)

    seen = held_keys()
    print(f"[{pid}] {len(seen)} existing keys to deduplicate against", flush=True)
    records, log = {}, []
    t0 = time.time()
    for q in qs:
        kept = 0
        items, err = crossref(q)
        cr = "hits_returned" if items else ("zero_records" if items == [] else "transport_error")
        cands = []
        for rec in (items or []):
            cands.append({"doi": rec.get("DOI", ""), "title": (rec.get("title") or [""])[0],
                          "venue": (rec.get("container-title") or [""])[0],
                          "abstract": re.sub(r"<[^>]+>", " ", rec.get("abstract") or "").strip(),
                          "year": (((rec.get("issued") or {}).get("date-parts") or [[]])[0] or [""])[0],
                          "url": rec.get("URL", ""), "src": "crossref"})
        ablob, aerr = arxiv(q)
        ax = parse_arxiv(ablob) if ablob else []
        axst = "hits_returned" if ax else ("zero_records" if ablob == "" and not aerr else "transport_error")
        for rec in ax:
            cands.append({"doi": rec["doi"], "title": rec["title"], "venue": "arXiv",
                          "abstract": rec["abstract"], "year": rec["year"], "url": rec["url"], "src": "arxiv"})
        for c in cands:
            if not c["title"] or not c["venue"]:
                continue
            k = key_of(c["doi"], c["title"])
            tk = "title:" + norm(c["title"])[:80]
            if k in seen or tk in seen:
                continue
            seen.add(k)
            seen.add(tk)
            records[k] = {"key": k, "doi": c["doi"], "year": c["year"], "venue": c["venue"], "title": c["title"],
                          "abstract": c["abstract"], "abstract_chars": len(c["abstract"]), "source": c["src"],
                          "query": q, "url": c["url"], "abstract_filled_by": "as_retrieved" if c["abstract"] else "none"}
            kept += 1
        log.append({"query": q, "crossref": cr, "arxiv": axst, "kept": kept,
                    "error": f"{err or ''} {aerr or ''}".strip(), "at": time.strftime("%Y-%m-%dT%H:%M:%S")})
        print(f"  {q[:52]:52s} kept={kept:3d} crossref={cr} arxiv={axst}", flush=True)
        time.sleep(0.7)

    # ---- fill the missing abstracts from the batch index BEFORE grading, so nothing is graded from a title silently
    need = sorted({"DOI:" + r["doi"] for r in records.values() if not r["abstract_chars"] and r["doi"]})
    text, status = {}, {}
    for bi in range(0, len(need), 50):
        chunk = need[bi:bi + 50]
        res, err = post(chunk)
        if res is None:
            for s in chunk:
                status[s] = "transport_error"
            continue
        for sid, rec in zip(chunk, res):
            a = ((rec or {}).get("abstract") or "").strip()
            status[sid] = "informative" if a else (((rec or {}).get("title") and "known_without_abstract") or "all_null")
            if a:
                text[sid] = (a, (rec or {}).get("title") or "")
        print(f"  fill batch {bi // 50 + 1}: {sum(1 for s in chunk if s in text)}/{len(chunk)} with text "
              f"({round(time.time() - t0)}s)", flush=True)
        time.sleep(1.2)

    filled = rejected = 0
    for r in records.values():
        sid = "DOI:" + r["doi"] if r["doi"] else ""
        r["s2_status"] = status.get(sid, "not_queried")
        if sid in text:
            a, s2t = text[sid]
            if len(tokens(s2t) & tokens(r["title"])) < MIN_SHARED:
                r["s2_status"] = "title_mismatch_rejected"
                rejected += 1
            else:
                r["abstract"], r["abstract_chars"] = a, len(a)
                r["abstract_filled_by"] = "semanticscholar"
                filled += 1
        lvl, hit, n = grade(pid, r["title"], r["abstract"])
        r["level_rule"] = lvl
        r["matched"] = json.dumps(hit, ensure_ascii=False)
        r["readable"] = int(r["abstract_chars"] > 0)

    rows = sorted(records.values(), key=lambda r: ({"L4": 0, "L3": 1, "L2": 2, "L1": 3, "L0": 4}[r["level_rule"]],
                                                   r["title"]))
    out = REG / f"literature_{pid.lower()}_expansion.csv"
    fields = ["key", "doi", "year", "venue", "title", "abstract_chars", "readable", "abstract", "source",
              "abstract_filled_by", "s2_status", "query", "url", "level_rule", "matched"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\r\n", extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    out.write_text(buf.getvalue(), encoding="utf-8", newline="")

    dist = {}
    for r in rows:
        dist[r["level_rule"]] = dist.get(r["level_rule"], 0) + 1
    l2 = [r for r in rows if r["level_rule"] in ("L2", "L3", "L4")]
    res = {"exp_id": EXP_ID, "paper": pid, "out_file": out.name, "queries": qs, "query_log": log,
           "new_records": len(rows), "grade_distribution": dist, "L2plus": len(l2),
           "readable": sum(r["readable"] for r in rows), "unread": sum(1 - r["readable"] for r in rows),
           "filled_by_semanticscholar": filled, "rejected_on_title_mismatch": rejected,
           "ids_queried_for_fill": len(need),
           "distinct_venues": len({r["venue"] for r in rows}),
           "L2plus_titles": [{"title": r["title"][:130], "venue": r["venue"][:50], "year": r["year"],
                              "level": r["level_rule"], "matched": r["matched"][:220]} for r in l2],
           "rule_reused_verbatim": "grade_collisions.grade() imported, not copied",
           "wallclock_sec": round(time.time() - t0, 1),
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t0)),
           "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    sp = ROOT / "results_raw" / f"{EXP_ID.replace('-', '')}_{pid.lower()}_family_expansion_summary_{time.strftime('%Y%m%dT%H%M%S')}.json"
    sp.parent.mkdir(exist_ok=True)
    sp.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8", newline="")
    print(json.dumps({k: v for k, v in res.items() if k not in ("query_log", "queries", "L2plus_titles")}, indent=1),
          flush=True)
    for r in l2[:25]:
        print(f"  {r['level_rule']} {r['title'][:82]} ({r['venue'][:30]}, {r['year']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
