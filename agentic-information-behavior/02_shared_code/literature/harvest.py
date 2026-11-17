"""Shared literature harvester for the AIB series (spec section 4: 20-30 directly relevant + 50+ background records).

One module used by every paper and every topic screen, so a later paper does not re-write the retrieval code.

What it does, and what it deliberately does NOT do:
  * queries `https://export.arxiv.org/api/query` (the only bibliographic host reachable from this environment)
    across the QUERY FAMILIES configured for the paper;
  * reads each returned abstract and scores it against that paper's own construct terms, keeping records above a
    threshold - so volume comes from real hits, not from padding;
  * deduplicates against rows already in the paper's `literature_matrix.csv` (by arXiv id and by normalised title);
  * logs every query it ran, INCLUDING zero-record queries. An empty result is reported as "no record found with
    this query form", never as "no prior work exists";
  * does not invent venues, DOIs or dates: an arXiv-only record carries `venue = arXiv preprint <id>` and a
    verify_status saying the venue could not be independently checked here. Non-arXiv classics are added by hand
    elsewhere because their publisher sites are unreachable from this machine.

    python 02_shared_code/literature/harvest.py --paper P002
    python 02_shared_code/literature/harvest.py --paper P003 --dry-run
"""
from __future__ import annotations

import argparse, csv, io, json, re, subprocess, time, urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ATOM = "{http://www.w3.org/2005/Atom}"
API = "https://export.arxiv.org/api/query?"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36",
      "Accept": "application/atom+xml, application/xml, text/xml, */*"}
# A browser-like UA is kept because it is what works when the service is healthy. It is NOT the cause of the
# 406s seen on 2026-09-19: a 2x2 test over {browser UA, default UA} x {simple, quoted, quoted+AND} queries gave
# 406 on all six cells minutes after the same simple+browser combination had returned 200, i.e. the endpoint
# begins refusing this client after roughly forty rapid queries. Treat 406 as RATE-LIMITED, back off, and never
# record it as "no such literature" - EXP-0032 did exactly that and reported 16 topics as unsearched.

# Per-paper query families + the terms an abstract must touch to count as relevant. Kept here rather than in the
# paper folders so a reviewer can see exactly which searches produced which rows.
PAPERS = {
    "P001": {
        "dir": "papers/P001_routing_failure_qpp",
        "families": [
            'all:"tool retrieval" AND all:"agent"', 'all:"tool use" AND all:"benchmark"',
            'all:"query performance prediction"', 'all:"query difficulty" AND all:"retrieval"',
            'all:"vocabulary mismatch" AND all:"retrieval"', 'all:"tool selection" AND all:"LLM"',
            'all:"agentic search"', 'all:"function calling" AND all:"evaluation"',
            'all:"tool" AND all:"retrieval" AND all:"failure"', 'all:"MCP" AND all:"server"',
            'all:"pre-retrieval"', 'all:"query reformulation" AND all:"conversational"',
            'all:"ToolBench"', 'all:"API-Bank"', 'all:"tool-augmented" AND all:"language model"',
            'all:"learning to rank" AND all:"agents"', 'all:"zero-shot" AND all:"tool retrieval"',
            'all:"instruction following" AND all:"retrieval"',
        ],
        "terms": ["tool retriev", "tool selection", "query performance", "query difficulty", "pre-retrieval",
                  "vocabulary mismatch", "function call", "agentic search", "agent benchmark", "mcp",
                  "reformulat", "api retrieval", "tool-use", "failure predict", "instruction"],
    },
    "P002": {
        "dir": "papers/P002_isp_stage_measurement",
        "families": [
            'all:"information search process"', 'all:"stage" AND all:"search behaviour"',
            'all:"trajectory" AND all:"agent" AND all:"sequence analysis"', 'all:"process mining" AND all:"agent"',
            'all:"search session" AND all:"log"', 'all:"conversation" AND all:"search stages"',
            'all:"Ellis" AND all:"information search"', 'all:"Kuhlthau" AND all:"uncertainty"',
            'all:"coding scheme" AND all:"interaction"', 'all:"Markov" AND all:"behaviour model"',
            'all:"turn-taking" AND all:"dialogue"', 'all:"annotation agreement" AND all:"coding reliability"',
            'all:"LLM annotator" AND all:"agreement"', 'all:"search as learning"',
            'all:"exploration" AND all:"exploitation" AND all:"search"', 'all:"foraging" AND all:"information"',
            'all:"censoring" AND all:"sequence"', 'all:"templated" AND all:"generation"',
            'all:"agent trace" OR all:"trajectory dataset"', 'all:"problem behaviour graph"',
        ],
        "terms": ["information search process", "search stage", "search behaviour", "trajectory", "agent session",
                  "process mining", "sequence model", "markov", "coding scheme", "annotation", "agreement",
                  "krippendorff", "censoring", "foraging", "exploration", "stage model", "problem behaviour"],
    },
    "P003": {
        "dir": "papers/P003_metadata_interoperability",
        "families": [
            'all:"metadata interoperability"', 'all:"schema matching"', 'all:"ontology alignment"',
            'all:"FAIR" AND all:"metadata"', 'all:"dataset" AND all:"card"', 'all:"trajectory dataset"',
            'all:"agent" AND all:"benchmark" AND all:"dataset"', 'all:"provenance" AND all:"machine learning"',
            'all:"knowledge organization"', 'all:"crosswalk" AND all:"metadata"',
            'all:"harmonization" AND all:"schema"', 'all:"LLM" AND all:"schema matching"',
            'all:"interoperability" AND all:"agent"', 'all:"reproducibility" AND all:"dataset"',
            'all:"resource description framework"', 'all:"openai function" OR all:"tool schema"',
            'all:"metadata quality"', 'all:"linked data" AND all:"vocabulary mapping"',
        ],
        "terms": ["metadata", "interoperab", "schema match", "ontology align", "crosswalk", "fair",
                  "provenance", "dataset card", "knowledge organization", "harmoniz", "reproducib",
                  "trajectory", "tool schema", "vocabulary mapping", "metadata quality"],
    },
    "P005": {
        "dir": "papers/P005_governance_metadata_verifiability",
        "families": [
            'abs:"dataset license"', 'abs:"licensing" AND cat:cs.DB', 'abs:"data provenance"',
            'abs:"datasheet" AND abs:"datasets"', 'abs:"model card"', 'abs:"dataset card"',
            'abs:"redistribution" AND abs:"dataset"', 'abs:"terms of use"', 'abs:"copyright" AND cat:cs.CY',
            'abs:"link rot"', 'abs:"software citation" AND abs:"availability"', 'abs:"reproducible research" AND abs:"data"',
            'abs:"agent trajectory" AND abs:"dataset"', 'abs:"synthetic data" AND abs:"license"',
            'abs:"FAIR principles" AND abs:"assessment"', 'abs:"metadata completeness" AND abs:"dataset"',
            'abs:"data governance" AND cat:cs.AI', 'abs:"secondary use" AND abs:"dataset"',
            # added 2026-09-20 after EXP-0057/0058: these are the words the collided records actually use.
            # The original eight families never contained any of them, which is why T013 looked like an L1 gap.
            'abs:"license laundering"', 'abs:"permissive-washing"', 'abs:"permissive washing"',
            'abs:"license integrity"', 'abs:"license compatibility"', 'abs:"license provenance"',
            'abs:"dataset licensing"', 'abs:"data provenance initiative"', 'abs:"LLMware"',
            'abs:"agent trajectory" AND cat:cs.CL', 'abs:"hidden licensing"',
        ],
        "terms": ["license", "licens", "provenance", "attribution", "dataset card", "datasheet", "model card",
                  "redistribut", "terms of use", "copyright", "link rot", "reproducib", "fair principle",
                  "metadata completeness", "data governance", "secondary use", "corpus reuse", "agent trajectory",
                  "license laundering", "permissive-washing", "license integrity", "license compatibility",
                  "dataset licensing", "supply chain", "attribution", "copyright", "hidden licensing"],
    },
}


def fetch(query: str, n: int = 60, tries: int = 3):
    """Retrieve through curl. Measured 2026-09-19: python's urllib is refused with HTTP 406 by export.arxiv.org
    for every header variant (none, curl's UA, Accept:*/*, Accept:application/atom+xml), while curl returns 200
    with entries for the *same* URL. So the block is on the client, not on the request or the query syntax, and the
    transport here has to be curl for the harvest to return anything at all.
    """
    url = API + urllib.parse.urlencode({"search_query": query, "start": 0, "max_results": n})
    last = None
    for a in range(tries):
        p = subprocess.run(["curl", "-sS", "-f", "--max-time", "60", url], capture_output=True)
        if p.returncode == 0 and p.stdout:
            return p.stdout, None
        last = f"curl exit {p.returncode}: {p.stderr.decode('utf-8', 'replace').strip()[:160]}"
        time.sleep(3 + 3 * a)
    return None, last


def parse(blob: bytes):
    out = []
    try:
        root = ET.fromstring(blob)
    except ET.ParseError:
        return out
    for e in root.findall(f"{ATOM}entry"):
        def txt(tag):
            node = e.find(f"{ATOM}{tag}")
            return re.sub(r"\s+", " ", node.text or "").strip() if node is not None and node.text else ""
        aid = txt("id")
        m = re.search(r"abs/([^v]+)v?(\d*)", aid)
        out.append({"arxiv_id": m.group(1) if m else aid, "rev": m.group(2) if m else "",
                    "title": txt("title"), "abstract": txt("summary"), "published": txt("published")[:10],
                    "updated": txt("updated")[:10], "url": aid.replace("http://", "https://"),
                    "authors": " & ".join((p.find(f"{ATOM}name").text or "").strip()
                                          for p in e.findall(f"{ATOM}author")[:2])})
    return out


def score(rec, terms):
    """How many of the paper's construct terms the title/abstract actually contains (title counted twice)."""
    t = (rec["title"] + " " + rec["abstract"]).lower()
    return sum(2 if term in rec["title"].lower() else 1 for term in terms if term in t)


def norm(s):
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


def existing(path: Path):
    if not path.exists():
        return set(), set(), []
    rows = list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8"))))
    ids = {re.sub(r"\D", "", (r.get("url") or ""))[:10] for r in rows}
    titles = {norm(r.get("title", ""))[:48] for r in rows}
    return {i for i in ids if i}, titles, rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", required=True, choices=sorted(PAPERS))
    ap.add_argument("--max", type=int, default=60)
    ap.add_argument("--min-score", type=int, default=2)
    ap.add_argument("--cap", type=int, default=45, help="max new rows per run, ranked by relevance score")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    cfg = PAPERS[a.paper]
    pap = ROOT / cfg["dir"]
    out_csv = pap / "literature_matrix.csv"
    ids, titles, rows = existing(out_csv)
    hdr = list(rows[0].keys()) if rows else ["cite_key", "year", "venue", "title", "problem", "dataset_used",
                                             "method", "metric", "main_result", "collision_target",
                                             "overlap_level", "code_or_data_public", "url", "retrieved_on",
                                             "verify_status", "paper_id", "differentiation"]
    seen, cand, log = dict.fromkeys(ids), {}, []
    for q in cfg["families"]:
        blob, err = fetch(q, a.max)
        recs = parse(blob) if blob else []
        hits = 0
        for r in recs:
            s = score(r, cfg["terms"])
            if s < a.min_score or r["arxiv_id"] in seen or norm(r["title"])[:48] in titles:
                continue
            hits += 1
            cand[r["arxiv_id"]] = (s, r, q)
            seen[r["arxiv_id"]] = True
        log.append({"paper": a.paper, "query": q, "returned": len(recs), "kept_above_threshold": hits,
                    "error": err or "", "ran_at": time.strftime("%Y-%m-%dT%H:%M:%S")})
        print(f"  {a.paper} | {q[:62]:62s} returned={len(recs):3d} kept={hits:3d}{'' if not err else ' ' + err}")
        time.sleep(3)                                      # arXiv API courtesy delay
    top = sorted(cand.values(), key=lambda x: -x[0])[:a.cap]
    new_rows = []
    for s, r, q in top:
        d = {"cite_key": f"arxiv{r['arxiv_id']}", "year": (r["published"] or r["updated"])[:4],
             "venue": f"arXiv preprint {r['arxiv_id']}v{r['rev'] or '1'}", "title": r["title"],
             "problem": r["abstract"][:300], "dataset_used": "", "method": r["abstract"][300:520],
             "metric": "", "main_result": r["abstract"][:300], "collision_target": "see novelty_audit",
             "overlap_level": "candidate - not yet graded", "code_or_data_public": "unknown from this host",
             "url": r["url"], "retrieved_on": time.strftime("%Y-%m-%d"),
             "verify_status": f"abstract read in full; relevance score {s}; query form: {q}",
             "paper_id": a.paper, "differentiation": ""}
        new_rows.append({k: d.get(k, "") for k in hdr})
    print(f"[harvest] {a.paper}: existing={len(rows)} new_candidates={len(new_rows)} "
          f"zero_hit_queries={sum(1 for l in log if l['returned'] == 0)} errors={sum(1 for l in log if l['error'])}")
    if a.dry_run:
        print("[harvest] --dry-run: nothing written")
        return 0
    if new_rows:
        p = out_csv.exists()
        with open(out_csv, "a", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=hdr)
            if not p:
                w.writeheader()
            w.writerows(new_rows)
    ql = pap / "lit_search_log.csv"
    old = list(csv.DictReader(io.StringIO(ql.read_text(encoding="utf-8")))) if ql.exists() else []
    for r in old:
        r.setdefault("source", "crossref")
    for r in log:
        r["source"] = "arxiv_export_api"
    # Build in memory and write once: `open(..., "w")` truncates before a failing write, which destroyed the
    # other source's query history once already.
    keys = list(dict.fromkeys([k for r in old + log for k in r]))
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=keys, extrasaction="ignore")
    w.writeheader()
    w.writerows(old + log)
    ql.write_text(buf.getvalue(), encoding="utf-8", newline="")
    print(f"[harvest] wrote {len(new_rows)} rows -> {out_csv.relative_to(ROOT)}; query log -> {ql.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
