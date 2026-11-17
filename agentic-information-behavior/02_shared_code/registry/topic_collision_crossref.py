"""EXP-0038: literature-collision screening for the 12 topics stuck at `w1_audit_done`.

Those topics have a measured local-data feasibility verdict but NO literature pass: the earlier screen (EXP-0032)
used the arXiv export API, which returned HTTP 406 for every one of its 16 queries, and its output summarised that
as "query returned no records" - so nothing about their novelty has actually been tested. This closes that gap with
Crossref, which is reachable and covers the venues the spec names.

Method, fixed before running:
  * 3-4 hand-written query forms per topic (title-derived, not auto-mangled), restricted to publications from 2019;
  * a record is a `candidate_collision` iff its title+abstract shares >= 2 of the topic's key nouns AND it was
    published in 2021 or later;
  * every query is logged with `returned` and a `status` of hits_returned / zero_records / transport_error, so a
    refused request can never again be read as an empty literature;
  * the script only SHORTLISTS. Collision levels L0-L4 are assigned by reading the dumped abstracts, afterwards,
    and are written back by a separate step - an automated overlap score is not a novelty judgement.

    python 02_shared_code/registry/topic_collision_crossref.py
Writes results_raw/EXP0038_topic_collisions_*.json and results_processed/EXP0038_candidate_collisions.csv.
"""
from __future__ import annotations

import csv, json, re, sys, time, urllib.error, urllib.parse, urllib.request
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
API = "https://api.crossref.org/works?"
HDR = {"User-Agent": "aib-collision-screen/1.0 (mailto:research@example.org)"}
PACE = 2.0            # Crossref 429s at 0.6 s spacing (measured: 15 of 48 queries refused)
SELECT = "DOI,title,container-title,published,abstract,is-referenced-by-count"
SINCE = "2019-01-01"

TOPICS = {
 "T006": {"nouns": ["tool description", "metadata", "discoverab", "retrieval", "api documentation", "descriptive"], "queries": ["tool description quality retrieval", "API metadata discoverability mining", "tool description language model agent retrieval", "metadata richness resource recall"]},
 "T007": {"nouns": ["taxonomy", "classification scheme", "categor", "catalog", "knowledge organization", "unsupervised"], "queries": ["automatic taxonomy induction classification scheme", "tool categorisation mining api repositories", "unsupervised topic classification service catalogue", "taxonomy construction evaluation clusters"]},
 "T015": {"nouns": ["multimodal", "ambiguous", "underspecified", "image", "query", "visual question"], "queries": ["underspecified multimodal query ambiguity", "ambiguous visual question retrieval", "text image mismatch multimodal search", "query ambiguity multimodal information retrieval"]},
 "T018": {"nouns": ["conversational search", "multi-turn", "reformulation", "clarification", "turn", "session"], "queries": ["conversational search turn reformulation effectiveness", "multi-turn query clarification search", "follow-up question search session", "conversational dense retrieval turns"]},
 "T019": {"nouns": ["design effect", "intra-class", "cluster", "nested", "sampling", "standard errors"], "queries": ["cluster sampling design effect intra-class correlation", "nested data mixed models behavioural logs", "intra-class correlation retrieval evaluation", "clustering unit of analysis user experiments"]},
 "T020": {"nouns": ["contamination", "duplicate", "leakage", "benchmark", "deduplicat", "evaluation dataset"], "queries": ["benchmark contamination evaluation datasets language models", "near-duplicate detection web corpora", "training data leakage benchmark", "dataset overlap deduplication evaluation"]},
 "T021": {"nouns": ["process mining", "trace", "control flow", "sequence", "event log", "workflow"], "queries": ["process mining agent traces", "control flow discovery tool invocation sequences", "process mining large event logs accuracy", "LLM agent workflow discovery"]},
 "T024": {"nouns": ["llm-as-a-judge", "judge", "validity", "agreement", "self-assessment", "evaluation metric"], "queries": ["LLM as a judge validity construct", "automatic evaluation metric validity agreement", "language model self-assessment confidence calibration", "machine generated quality scores human agreement"]},
 "T026": {"nouns": ["difficulty", "complexity", "predict", "task", "metric", "estimate"], "queries": ["task difficulty prediction automatic", "computable complexity metrics programming tasks", "query difficulty prediction retrieval", "task complexity predicting human performance"]},
 "T031": {"nouns": ["ellipsis", "anaphora", "referring expression", "grounding", "dialogue", "omission"], "queries": ["ellipsis resolution dialogue failure", "referring expression grounding dialogue", "anaphora ambiguity instruction following agents", "underspecified references grounding failure"]},
 "T032": {"nouns": ["vocabulary mismatch", "query expansion", "rewriting", "translation", "description", "effectiveness"], "queries": ["vocabulary mismatch query translation retrieval", "document description rewriting retrieval effectiveness", "query expansion intervention effectiveness", "tool description rewriting retrieval agent"]},
 "T034": {"nouns": ["foraging", "wandering", "index", "measure", "browsing", "switching"], "queries": ["information foraging measure index", "browsing wandering metrics web behaviour", "attention switching information search measure", "cognitive load navigation metrics search"]},
}


def get(params, tries=4):
    """Retry 429/5xx with the server's own Retry-After when present; a 404/400 is not retried."""
    url = API + urllib.parse.urlencode(params)
    last = None
    for a in range(tries):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=45).read()), None
        except urllib.error.HTTPError as exc:
            last = f"HTTPError: {exc}"
            if exc.code not in (429, 500, 502, 503, 504):
                return None, last
            time.sleep(min(60, int(exc.headers.get("Retry-After") or 0) or (4 * (a + 1))))
        except Exception as exc:                               # noqa: BLE001
            last = f"{type(exc).__name__}: {exc}"
            time.sleep(2 * (a + 1))
    return None, last


def clean(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    res = {"exp_id": "EXP-0038", "paper_id": "program", "stage": "topic_collision_screen",
           "source": "api.crossref.org/works", "since": SINCE,
           "rule": "candidate_collision iff >=2 key nouns in title+abstract and year>=2021; L-levels assigned "
                   "afterwards by reading the dumped abstracts",
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "topics": {}, "queries": []}
    prev = None
    if "--resume" in sys.argv:
        pf = sorted((ROOT / "results_raw").glob("EXP0038_topic_collisions_*.json"))
        if not pf:
            sys.exit("[e38] --resume needs a previous EXP-0038 file")
        prev = json.loads(pf[-1].read_text(encoding="utf-8"))
        redo = {r["topic"] for r in prev["queries"] if r["status"] == "transport_error"}
        print(f"[e38] resume: re-running failed queries for {sorted(redo)}")
    for tid, spec in TOPICS.items():
        if prev is not None and tid not in redo:
            res["topics"][tid] = prev["topics"][tid]
            res["queries"].extend([x for x in prev["queries"] if x["topic"] == tid])
            continue
        seen, hits = set(), {}
        for q in spec["queries"]:
            if prev is not None:
                done = {x["query"] for x in prev["queries"] if x["topic"] == tid and x["status"] != "transport_error"}
                if q in done:
                    continue
            data, err = get({"query.bibliographic": q, "filter": f"from-pub-date:{SINCE}", "rows": 25,
                             "select": SELECT})
            items = (data or {}).get("message", {}).get("items", []) if data else []
            kept = 0
            for it in items:
                doi = (it.get("DOI") or "").lower()
                title = clean((it.get("title") or [""])[0])
                abst = clean(it.get("abstract") or "")
                blob = (title + " " + abst).lower()
                yr = int(((it.get("published") or {}).get("date-parts") or [["0"]])[0][0] or 0)
                if not doi or doi in seen:
                    continue
                shared = [n for n in spec["nouns"] if n in blob]
                if len(shared) >= 2 and yr >= 2021:
                    seen.add(doi)
                    kept += 1
                    hits[doi] = {"doi": doi, "year": yr, "title": title,
                                 "venue": clean((it.get("container-title") or [""])[0]),
                                 "cited": int(it.get("is-referenced-by-count") or 0),
                                 "shared_nouns": shared, "n_shared": len(shared),
                                 "abstract": abst[:700] or "not deposited"}
            res["queries"].append({"topic": tid, "query": q, "returned": len(items), "candidates": kept,
                                   "status": "transport_error" if err else ("zero_records" if not items else
                                                                            "hits_returned"),
                                   "error": err or ""})
            time.sleep(PACE)
        ranked = sorted(hits.values(), key=lambda x: (-x["n_shared"], -x["cited"]))
        res["topics"][tid] = {"n_candidates": len(ranked), "top": ranked[:6],
                              "queries_with_records": sum(1 for x in res["queries"] if x["topic"] == tid and
                                                          x["returned"]),
                              "queries_errored": sum(1 for x in res["queries"] if x["topic"] == tid and x["error"])}
        print(f"  {tid}: candidates={len(ranked):3d} "
              f"{'| top: ' + ranked[0]['title'][:60] if ranked else '| no candidate in this form'}")
    tot = Counter(v["status"] for v in res["queries"])
    res["query_status_totals"] = dict(tot)
    res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    res["wallclock_sec"] = round(time.time() - t0, 1)
    if tot.get("transport_error"):
        print(f"[e38] WARNING {tot['transport_error']} queries failed - those topics are NOT screened, "
              "and must not be read as gap-confirmed.")
    (ROOT / "results_raw").mkdir(exist_ok=True)
    out = ROOT / "results_raw" / f"EXP0038_topic_collisions_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    rows = [{"topic": tid, **{k: v for k, v in h.items() if k != "abstract"},
             "abstract_excerpt": h["abstract"][:300]}
            for tid, d in res["topics"].items() for h in d["top"]]
    (ROOT / "results_processed").mkdir(exist_ok=True)
    pd.DataFrame(rows).to_csv(ROOT / "results_processed" / "EXP0038_candidate_collisions.csv", index=False)
    print(json.dumps({"query_status_totals": dict(tot), "topics_with_candidates":
                      sum(1 for d in res["topics"].values() if d["n_candidates"])}))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
