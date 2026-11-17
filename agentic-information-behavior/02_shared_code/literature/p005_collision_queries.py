"""EXP-0058: targeted collision queries against the records EXP-0057 surfaced for P005.

The funnel screen (EXP-0047) called T013 the only L1 in its set, and P005 was written on that basis. Rule-based
grading of the harvested abstracts then surfaced three 2026 papers this programme never queried for:
`Permissive-Washing in the Open AI Supply Chain` (2602.08816), `Don't Trust the Label: License Laundering in AI
Supply Chains` (2607.20300) and `Open but Incompatible` (2606.28867). The screen's four phrase families were
`dataset license`, `licensing+cs.DB`, `data provenance`, `responsible release datasets`, `model card` — none of
which contains the words those papers use. So the L1 call was a query-coverage failure, not a gap.

This script queries the phrase families the collided records actually use, and reports per-query status in the same
three-way form (informative / zero_records / transport_error) so the result is auditable either way.

    python 02_shared_code/literature/p005_collision_queries.py
"""
from __future__ import annotations

import json, pathlib, sys, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "02_shared_code" / "literature"))
from arxiv_topic_screen import fetch, parse          # noqa: E402  (curl transport, same as the screen)

OUT = ROOT / "results_raw"
PROC = ROOT / "results_processed"
PHRASES = [
    ("P005", "license laundering", None), ("P005", "permissive-washing", None), ("P005", "permissive washing", None),
    ("P005", "license integrity", None), ("P005", "license compatibility", None),
    ("P005", "license compliance", "cs.DB"), ("P005", "license provenance", None),
    ("P005", "open-weight governance", None), ("P005", "model card", "cs.CL"),
    ("P005", "datasheet for datasets", None), ("P005", "data provenance", "cs.AI"),
    ("P005", "AI supply chain", None), ("P005", "dataset licensing", None),
    ("P005", "training data license", None), ("P005", "repository metadata audit", None),
    ("P005", "agent trajectory dataset", None), ("P005", "trajectory corpus", None),
    ("P005", "dataset card", "cs.IR"),
]
# the constructs P005 claims as its delta; a collision must match more than the topic words
DELTA = ["agent trajectory", "tool-calling", "llm agent", "function calling", "release card", "dataset card",
         "hugging face", "corpus release", "verifiab", "audit", "census"]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    res = {"exp_id": "EXP-0058", "paper_id": "P005", "why": "EXP-0047's phrase families missed the records "
           "EXP-0057 surfaced; this queries the words the collided papers actually use",
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "records": []}
    for pid, phrase, cat in PHRASES:
        q = f'all:"{phrase}"' + (f" AND cat:{cat}" if cat else "")
        body, err = fetch({"search_query": q, "max_results": 20, "sortBy": "relevance"})
        hits = [] if err else parse(body)
        rel = [h for h in hits if any(d in (h["title"] + " " + h["abstract"]).lower() for d in DELTA)]
        res["records"].append({"paper_id": pid, "phrase": phrase, "category": cat, "query_string": q,
                               "status": "transport_error" if err else ("informative" if hits else "zero_records"),
                               "error": err, "n_returned": len(hits), "n_delta_relevant": len(rel),
                               "titles": [h["title"][:120] for h in hits[:8]],
                               "relevant": [{"id": h["arxiv_id"], "year": h["published"][:4],
                                             "title": h["title"][:130],
                                             "abstract": h["abstract"][:600]} for h in rel[:6]]})
        print(f"  {phrase!r:34} {cat or '-':7} {res['records'][-1]['status']:15} "
              f"returned={len(hits):2d} delta-relevant={len(rel):2d}", flush=True)
        time.sleep(3.0)
    seen = {}
    for r in res["records"]:
        for c in r["relevant"]:
            seen.setdefault(c["id"], c)
    res["distinct_relevant_records"] = list(seen.values())
    res["verdict"] = ("COLLISION_CONFIRMED" if len(seen) >= 3 else
                      "PARTIAL" if seen else "NO_COLLISION_WITH_THESE_QUERIES")
    res["note"] = ("a `zero_records` answer is a property of this phrase, not of the literature; only the "
                   "`informative` queries carry weight here")
    res["wallclock_sec"] = round(time.time() - t0, 1)
    res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    out = OUT / f"EXP0058_p005_collision_queries_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8", newline="")
    with open(PROC / "EXP0058_collision_queries.csv", "w", encoding="utf-8", newline="") as fh:
        fh.write("phrase,category,status,returned,delta_relevant,query_string\n")
        for r in res["records"]:
            fh.write(f'"{r["phrase"]}",{r["category"] or ""},{r["status"]},{r["n_returned"]},'
                     f'{r["n_delta_relevant"]},"{r["query_string"]}"\n')
    print("verdict", res["verdict"], "| distinct relevant records:", len(seen))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
