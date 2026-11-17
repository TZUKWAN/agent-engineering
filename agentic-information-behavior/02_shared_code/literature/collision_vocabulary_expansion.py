"""EXP-0060: derive each paper's collision vocabulary from its own retrieved records, and query with it.

Why this exists: EXP-0047 screened T013 with five hand-picked phrase families and called it an L1 gap; EXP-0057/
EXP-0058 showed the colliding papers use different words ("license laundering", "permissive-washing"), which no
hand-picked family contained. The lesson is not "write better queries by hand" — it is that the vocabulary of a
field must be taken from the field's own text. So this script mines the bigrams that discriminate the records
already graded L2+ for a paper from those graded L0/L1, forms `abs:"bigram"` queries from them, and reports what
newly comes back. It closes the loop that P001–P004 have not yet had.

Statuses are the same three-way labels as the screen (informative / zero_records / transport_error), and
`zero_records` is never read as absence. Newly found records are written to a per-paper candidate file for
abstract retrieval and grading; nothing here changes a paper's claims by itself.

    python 02_shared_code/literature/collision_vocabulary_expansion.py
"""
from __future__ import annotations

import csv, json, pathlib, re, sys, time
from collections import Counter, defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[2]
REG = ROOT / "00_program_registry"
OUT = ROOT / "results_raw"
PROC = ROOT / "results_processed"
sys.path.insert(0, str(ROOT / "02_shared_code" / "literature"))
from arxiv_topic_screen import fetch, parse        # noqa: E402  (curl transport)
from grade_collisions import PAPERS                # noqa: E402  (construct families)

STOP = set(("a an the and or of to in for with on at is are be this that it its you your we our as by from into "
            "using used use based toward towards their there which when what how can could will would may might "
            "study paper propose present new large scale analysis learning model models data dataset datasets "
            "evaluation approach results result method show shows also more most between via about across").split())
MIN_DISK = 0.34        # a bigram must appear in this share of the paper's L2+ records and be rare in its L0/L1


def bigrams(text):
    w = [x for x in re.findall(r"[a-z][a-z\-']{2,}", (text or "").lower()) if x not in STOP]
    return [f"{a} {b}" for a, b in zip(w, w[1:])]


def mine_phrases(pid, recs):
    """Discriminative bigrams among this paper's higher-graded records.

    Two deliberate choices. First, rank by discrimination and take the top N rather than cutting at an absolute
    threshold: a fixed cut-off silently produced *no* phrases for four of the five papers, which is a null result of
    the instrument, not of the literature. Second, when a paper has fewer than three records graded L2+ (P001 has
    one, P004 eight of which six carry abstracts), the "L2+ versus L0/L1" contrast is meaningless, so the fallback
    mines from every record that carries an abstract and says so in the output.
    """
    hi = [r for r in recs if r["level_rule"] in ("L2", "L3", "L4") and r["abstract"].strip()]
    fell_back = False
    if len(hi) < 3:
        hi = [r for r in recs if r["abstract"].strip()]
        fell_back = True
    lo = [r for r in recs if r not in hi]
    hc = Counter(bg for r in hi for bg in set(bigrams(r["title"] + " " + r["abstract"])))
    lc = Counter(bg for r in lo for bg in set(bigrams(r["title"] + " " + r["abstract"])))
    n_hi, n_lo = max(1, len(hi)), max(1, len(lo))
    scored = sorted(((c / n_hi - lc.get(bg, 0) / n_lo, c, bg)
                     for bg, c in hc.items() if c >= 2), reverse=True)
    fam = PAPERS[pid]["construct"]
    on_topic = [bg for d, c, bg in scored if any(f in bg for f in fam)]
    rest = [bg for _, _, bg in scored if bg not in on_topic]
    return (on_topic + rest)[:8], {"n_hi_pool": len(hi), "fell_back_to_all_abstracts": fell_back,
                                   "bigrams_scored": len(scored), "on_topic_first": len(on_topic)}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    graded = defaultdict(list)
    for r in csv.DictReader(open(REG / "literature_graded.csv", encoding="utf-8")):
        graded[r["paper_id"]].append(r)
    abso = {(r["paper_id"], r["identifier"]): r for r in csv.DictReader(open(REG / "literature_abstracts.csv", encoding="utf-8"))}
    for pid in sorted(graded):
        for r in graded[pid]:
            a = abso.get((pid, r["identifier"]), {})
            r["abstract"] = a.get("abstract", "")

    res = {"exp_id": "EXP-0060", "kind": "vocabulary-derived collision expansion",
           "why": "EXP-0057/0058 showed a hand-picked phrase family can hide an L4; phrases here are mined from the "
                  "papers' own retrieved records",
           "rule": "informative queries only; zero_records is never read as absence; new ids go to "
                   "results_processed/EXP0060_new_records.csv for retrieval + grading",
           "min_discrimination": MIN_DISK, "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "papers": {}}
    new_all = []
    t0 = time.time()
    for pid in sorted(graded):
        if pid not in PAPERS:
            continue
        phrases, meta = mine_phrases(pid, graded[pid])
        known = {re.sub(r"v\d+$", "", (r["identifier"] or "").split("/")[-1]).lower() for r in graded[pid]}
        per = {"phrases": phrases, "miner": meta, "queries": []}
        for ph in phrases:
            q = f'all:"{ph}"'
            body, err = fetch({"search_query": q, "max_results": 20, "sortBy": "relevance"})
            hits = [] if err else parse(body)
            fresh = [h for h in hits if re.sub(r"v\d+$", "", h["arxiv_id"].split("/")[-1]).lower() not in known]
            fam = PAPERS[pid]
            txt_all = [(h, (h["title"] + " " + h["abstract"]).lower()) for h in fresh]
            rel = [h for h, t in txt_all
                   if sum(k in t for k in fam["construct"]) >= 2 and sum(k in t for k in fam["object"] + fam["data"]) >= 1]
            per["queries"].append({"phrase": ph, "query_string": q,
                                   "status": "transport_error" if err else ("informative" if hits else "zero_records"),
                                   "error": err, "n_returned": len(hits), "n_new": len(fresh),
                                   "n_construct_relevant": len(rel),
                                   "relevant": [{"id": h["arxiv_id"], "year": h["published"][:4],
                                                 "title": h["title"][:140], "abstract": h["abstract"][:700]}
                                                for h in rel[:6]]})
            for h in rel:
                known.add(re.sub(r"v\d+$", "", h["arxiv_id"].split("/")[-1]).lower())
                new_all.append({"paper_id": pid, "identifier": h["arxiv_id"], "year": h["published"][:4],
                                "title": h["title"][:200], "abstract": h["abstract"][:3000],
                                "found_via": ph})
            print(f"  {pid} {ph!r:38} {per['queries'][-1]['status']:15} new={len(fresh):2d} "
                  f"construct-relevant={len(rel):2d}", flush=True)
            time.sleep(3.0)
        per["n_informative"] = sum(q["status"] == "informative" for q in per["queries"])
        per["n_new_relevant"] = sum(q["n_construct_relevant"] for q in per["queries"])
        res["papers"][pid] = per
    res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    res["wallclock_sec"] = round(time.time() - t0, 1)
    stamp = time.strftime("%Y%m%dT%H%M%S")
    (OUT / f"EXP0060_vocabulary_expansion_{stamp}.json").write_text(
        json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8", newline="")
    seen, uniq = set(), []
    for n in new_all:
        k = (n["paper_id"], re.sub(r"v\d+$", "", n["identifier"].split("/")[-1]).lower())
        if k not in seen:
            seen.add(k)
            uniq.append(n)
    with open(PROC / "EXP0060_new_records.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["paper_id", "identifier", "year", "title", "abstract", "found_via"])
        w.writeheader()
        w.writerows(uniq)
    print(json.dumps({p: {"phrases": len(v["phrases"]), "informative": v["n_informative"],
                          "new_relevant": v["n_new_relevant"]} for p, v in res["papers"].items()}, ensure_ascii=False))
    print("new unique construct-relevant records:", len(uniq), "| wrote", f"EXP0060_vocabulary_expansion_{stamp}.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
