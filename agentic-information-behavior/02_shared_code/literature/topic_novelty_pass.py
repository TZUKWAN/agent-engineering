"""EXP-0074: the novelty screen that never ran, for the two topics parked as "screen incomplete: empty feeds".

T029 and T036 are still at `w2_screen_incomplete_empty_feeds`: when they were screened, the arXiv feed returned nothing
(urllib was being refused 406 from this host) and Crossref had only been queried per-work by DOI, so the collision
question was answered by an empty result rather than by a search. Both transports are now known to work - arXiv over
curl, Crossref `query.bibliographic`, and Semantic Scholar's batch endpoint for abstract text - so the screen can be
run for real.

Term families for each topic are authored from the topic's own registry fields (object = what it studies, construct =
the property asked, measure = operationalisation, data = corpus family) and injected into the grading module **at
runtime**, so `grade_collisions.py` stays byte-identical and every grade already recorded for P001-P005 still means the
same thing. The rule itself is the frozen one.

Decision rule, fixed before the first query:
  * a topic is `L4_COLLISION` if any record co-mentions object + construct + measure + data; `L3_CROWDED` if object +
    construct + one of measure/data; `L2_PARTIAL` if object + construct; below that the topic's neighbourhood is
    background, not a collision;
  * `not_promoted` requires either an L3/L4 hit or a measured data/self-overlap blocker; an empty feed is neither, so a
    zero-collision result must be reported with how much of the retrieved set was actually readable;
  * every query is logged with its per-source status, including zero-result ones.

    python topic_novelty_pass.py T029
    python topic_novelty_pass.py T036
"""
from __future__ import annotations

import csv, io, json, pathlib, sys, time
from collections import Counter

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import grade_collisions as GC                       # noqa: E402 - the frozen rule, injected not edited
from expand_paper_literature import (arxiv, build_queries, crossref, held_keys, key_of,  # noqa: E402
                                     norm, parse_arxiv, MIN_SHARED)
from fetch_abstracts_s2 import post, tokens          # noqa: E402

ROOT = HERE.parents[1]
REG = ROOT / "00_program_registry"
OUT_RAW = ROOT / "results_raw"
EXP_BY_TOPIC = {"T029": "EXP-0074", "T036": "EXP-0075"}

TOPICS = {
    "T029": {
        "object": ["agent trajectory", "computer use agent", "gui agent", "step level action", "task termination",
                   "early stopping"],
        "construct": ["verification language", "self-verification", "stopping judgement", "termination decision",
                      "step correctness", "redundant step"],
        "measure": ["survival analysis", "hazard model", "last step correct", "step-level accuracy",
                    "conditional probability"],
        "data": ["agentnet", "swe-bench", "gui dataset", "computer control trajectory", "winmac"],
    },
    "T036": {
        "object": ["agent trajectory corpus", "agent dataset", "llm agent benchmark", "tool use dataset",
                   "public agent corpus"],
        "construct": ["intelligence source", "knowledge source", "supply side view", "corpus landscape",
                      "research frontier signal", "technology foresight"],
        "measure": ["bibliometric", "aggregation of corpora", "coverage analysis", "topic distribution",
                    "metadata landscape"],
        "data": ["hugging face dataset", "agent trajectory release", "open dataset", "github"],
    },
}


def main() -> int:
    tid = (sys.argv[1] if len(sys.argv) > 1 else "").strip()
    if tid not in TOPICS:
        raise SystemExit(f"usage: topic_novelty_pass.py {{{'|'.join(TOPICS)}}}")
    exp = EXP_BY_TOPIC[tid]
    sys.stdout.reconfigure(encoding="utf-8")
    GC.PAPERS[tid] = TOPICS[tid]                    # runtime injection only; the module file is not edited
    qs = build_queries(tid)
    print(f"{exp} | {tid} | {len(qs)} family-derived queries", flush=True)
    for q in qs:
        print("   ", q, flush=True)

    seen = held_keys()
    records, log = {}, []
    t0 = time.time()
    for q in qs:
        items, err = crossref(q)
        cr = "hits_returned" if items else ("zero_records" if items == [] else "transport_error")
        cands = [{"doi": r.get("DOI", ""), "title": (r.get("title") or [""])[0],
                  "venue": (r.get("container-title") or [""])[0],
                  "abstract": __import__("re").sub(r"<[^>]+>", " ", r.get("abstract") or "").strip(),
                  "year": (((r.get("issued") or {}).get("date-parts") or [[]])[0] or [""])[0],
                  "url": r.get("URL", ""), "src": "crossref"} for r in (items or [])]
        ab, ae = arxiv(q)
        ax = parse_arxiv(ab) if ab else []
        axst = "hits_returned" if ax else ("zero_records" if ab == "" and not ae else "transport_error")
        kept = 0
        for c in cands + [{"doi": r["doi"], "title": r["title"], "venue": "arXiv", "abstract": r["abstract"],
                           "year": r["year"], "url": r["url"], "src": "arxiv"} for r in ax]:
            if not c["title"] or not c["venue"]:
                continue
            k = key_of(c["doi"], c["title"]); tk = "title:" + norm(c["title"])[:80]
            if k in seen or tk in seen:
                continue
            seen.add(k); seen.add(tk)
            records[k] = {"key": k, **c, "abstract_chars": len(c["abstract"]), "query": q,
                          "abstract_filled_by": "as_retrieved" if c["abstract"] else "none"}
            kept += 1
        log.append({"query": q, "crossref": cr, "arxiv": axst, "kept": kept,
                    "error": f"{err or ''} {ae or ''}".strip()})
        print(f"  {q[:52]:52s} kept={kept:3d} crossref={cr} arxiv={axst}", flush=True)
        time.sleep(0.7)

    need = sorted({"DOI:" + r["doi"] for r in records.values() if not r["abstract_chars"] and r["doi"]})
    text = {}
    for bi in range(0, len(need), 50):
        chunk = need[bi:bi + 50]
        res, err = post(chunk)
        if res is None:
            continue
        for sid, rec in zip(chunk, res):
            a = ((rec or {}).get("abstract") or "").strip()
            if a:
                text[sid] = (a, (rec or {}).get("title") or "")
        time.sleep(1.0)
    filled = rejected = 0
    for r in records.values():
        sid = "DOI:" + r["doi"] if r["doi"] else ""
        if sid in text:
            a, s2t = text[sid]
            if len(tokens(s2t) & tokens(r["title"])) >= MIN_SHARED:
                r["abstract"], r["abstract_chars"] = a, len(a)
                r["abstract_filled_by"] = "semanticscholar"
                filled += 1
            else:
                rejected += 1
        lvl, hit, n = GC.grade(tid, r["title"], r["abstract"])
        r["level_rule"] = lvl
        r["readable"] = int(r["abstract_chars"] > 0)
        r["matched"] = json.dumps(hit, ensure_ascii=False)

    rows = sorted(records.values(), key=lambda r: ({"L4": 0, "L3": 1, "L2": 2, "L1": 3, "L0": 4}[r["level_rule"]],
                                                   r["title"]))
    out = REG / f"literature_{tid.lower()}_novelty_screen.csv"
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["key", "doi", "year", "venue", "title", "abstract_chars", "readable",
                                        "abstract", "src", "abstract_filled_by", "query", "url", "level_rule",
                                        "matched"], lineterminator="\r\n", extrasaction="ignore")
    w.writeheader(); w.writerows(rows)
    out.write_text(buf.getvalue(), encoding="utf-8", newline="")

    dist = Counter(r["level_rule"] for r in rows)
    l34 = [r for r in rows if r["level_rule"] in ("L3", "L4")]
    res = {"exp_id": exp, "topic": tid, "out_file": out.name, "queries": qs, "query_log": log,
           "records": len(rows), "readable": sum(r["readable"] for r in rows),
           "unread": sum(1 - r["readable"] for r in rows), "filled_by_semanticscholar": filled,
           "rejected_on_title_mismatch": rejected, "grade_distribution": dict(dist),
           "L2plus": dist.get("L2", 0) + dist.get("L3", 0) + dist.get("L4", 0),
           "L3plus": dist.get("L3", 0) + dist.get("L4", 0),
           "closest": [{"level": r["level_rule"], "title": r["title"][:140], "venue": r["venue"][:44],
                        "year": r["year"], "matched": r["matched"][:260]} for r in rows[:25]],
           "decision_rule": "L4 = object+construct+measure+data co-mentioned; L3 = object+construct+one of "
                            "measure/data; L2 = object+construct. not_promoted needs an L3/L4 hit or a measured "
                            "data/self-overlap blocker - an empty feed is neither",
           "term_families_injected_at_runtime": True, "grade_collisions_py_unmodified": True,
           "wallclock_sec": round(time.time() - t0, 1), "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    sp = OUT_RAW / f"{exp.replace('-', '')}_{tid.lower()}_novelty_screen_{time.strftime('%Y%m%dT%H%M%S')}.json"
    sp.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8", newline="")
    print(json.dumps({k: v for k, v in res.items() if k not in ("queries", "query_log", "closest")}, indent=1), flush=True)
    for r in res["closest"][:12]:
        print(f"  {r['level']} {r['title'][:80]} ({r['venue'][:26]}, {r['year']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
