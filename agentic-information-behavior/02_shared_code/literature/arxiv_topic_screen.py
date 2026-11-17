"""EXP-0047: arXiv-side novelty screen for the 12 live funnel topics, using the query form that actually works here.

Why this exists: the funnel's earlier arXiv passes (inside EXP-0032/EXP-0038) never returned records - first because
`export.arxiv.org` answered HTTP 406 for the whole session, and second because the queries chained several quoted
phrases with AND, which this API answers with an empty feed even when the literature is large. Both failure modes
look identical from the outside, so every query here records its own status:
  informative        - the feed carried entries
  zero_records       - the request succeeded and the feed was genuinely empty  (may still mean "no collision" only
                       for THIS phrase; never generalised on its own)
  transport_error    - HTTP != 200 or the feed could not be parsed (no evidence either way).
                     Transport is curl, not urllib: urllib is refused with 406 here for every header
                     variant, for the same URL that curl fetches successfully (see fetch()).

The rule enforced at the end: a topic may only be called collision-weak if at least one of its queries came back
`informative` for the topic's own phrase family. `zero_records` alone can never establish a gap.

Query form: one quoted phrase, optionally narrowed by `cat:` - never two phrases ANDed.

    python 02_shared_code/literature/arxiv_topic_screen.py            # full run
    python 02_shared_code/literature/arxiv_topic_screen.py --resume    # continue from the checkpoint
"""
from __future__ import annotations

import json, pathlib, re, subprocess, sys, time
import urllib.parse
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "results_raw"
CKPT = OUT_DIR / "EXP0047_arxiv_screen_checkpoint.json"
NS = {"a": "http://www.w3.org/2005/Atom"}
API = "https://export.arxiv.org/api/query"
PACE = 3.0
MAX_RESULTS = 12

# topic -> (phrase, category) pairs. Categories are arXiv's own; a phrase without a category is left broad.
SCREEN = {
    "T004": [("synthetic data instructions", "cs.CL"), ("human written instructions", "cs.CL"),
             ("prompt distribution LLM", "cs.CL"), ("instruction style transfer", "cs.CL")],
    "T006": [("tool description", "cs.SE"), ("API documentation quality", None),
             ("tool documentation", "cs.SE"), ("metadata completeness retrieval", "cs.IR")],
    "T013": [("dataset license", "cs.DB"), ("data provenance machine learning", None),
             ("responsible release datasets", "cs.CY"), ("model card", "cs.CL")],
    "T014": [("link rot", None), ("reproducibility software dependencies", "cs.SE"),
             ("broken links", None), ("archival of research artifacts", "cs.DL")],
    "T015": [("underspecified queries", "cs.IR"), ("visual question ambiguity", "cs.CV"),
             ("multimodal entity linking", "cs.CL"), ("query intent ambiguity", "cs.IR")],
    "T021": [("process mining", "cs.AI"), ("tool call sequences", "cs.SE"),
             ("agent trajectory analysis", "cs.AI"), ("conformance checking", "cs.SE")],
    "T027": [("readability metrics source code", "cs.SE"), ("instruction complexity", "cs.CL"),
             ("cognitive load programming", "cs.HC"), ("execution time prediction", "cs.PF")],
    "T028": [("conflicting instructions", "cs.CL"), ("constraint satisfaction instructions", "cs.CL"),
             ("contradictory requirements", "cs.SE"), ("instruction following evaluation", "cs.CL")],
    "T029": [("termination criteria agents", "cs.AI"), ("self verification language models", "cs.CL"),
             ("stopping policy reinforcement", None), ("answer completeness judgement", "cs.IR")],
    "T030": [("constraint density", None), ("task complexity agents", "cs.AI"),
             ("instruction length effects", "cs.CL"), ("cognitive load language models", "cs.HC")],
    "T034": [("information wandering", "cs.IR"), ("exploratory search", "cs.IR"),
             ("information foraging", "cs.IR"), ("attention lapse search", "cs.HC")],
    "T036": [("corpus as data source", "cs.DL"), ("secondary analysis agent traces", None),
             ("dataset reuse", "cs.DB"), ("research compendium", "cs.DL")],
}
KEYWORDS = {  # per topic, words that make a returned abstract count as a real collision rather than a keyword match
    "T004": ["synthetic", "human-written", "prompt style", "instruction distribution"],
    "T006": ["description", "documentation", "metadata", "discoverab", "register"],
    "T013": ["licen", "provenance", "compliance", "release", "governance"],
    "T014": ["link rot", "reproducib", "artifact", "archiv", "dependency"],
    "T015": ["underspecif", "ambigu", "visual", "multimodal", "clarif"],
    "T021": ["process mining", "trace", "trajectory", "conformance", "sequence"],
    "T027": ["readab", "complexity", "cognitive load", "execution time", "efficiency"],
    "T028": ["conflict", "contradict", "constraint", "infeasible", "instruction"],
    "T029": ["terminat", "stopping", "self-verif", "completion", "refuse"],
    "T030": ["densit", "complexity", "length", "cognitive", "constraint"],
    "T034": ["wander", "explorator", "foraging", "browse", "session"],
    "T036": ["secondary analysis", "reuse", "corpus", "reposit", "repurpos"],
}


def fetch(params, tries=3):
    """GET through curl. Measured here: python's urllib gets HTTP 406 for every header variant tried
    (none / curl UA / Accept:*/* / Accept:atom+xml / Accept only) while curl returns 200 with entries for the
    same URL, so the block is on the client, not the request. Curl is on PATH and needs no credentials.
    """
    url = API + "?" + urllib.parse.urlencode(params)
    last = None
    for k in range(tries):
        try:
            p = subprocess.run(["curl", "-sS", "--max-time", "60", "-w", "\n%{http_code}", url],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            body, _, code = p.stdout.rpartition("\n")
            if code.strip() != "200":
                last = f"HTTP {code.strip() or 'no-code'} {p.stderr.strip()[:120]}"
                time.sleep(PACE * (k + 1))
                continue
            return body, None
        except Exception as e:                                       # timeout/DNS all land here
            last = f"{type(e).__name__}: {e}"
            time.sleep(PACE * (k + 2))
    return None, last


def parse(body):
    root = ET.fromstring(body)
    out = []
    for e in root.findall("a:entry", NS):
        t = re.sub(r"\s+", " ", (e.findtext("a:title", "", NS) or "")).strip()
        s = re.sub(r"\s+", " ", (e.findtext("a:summary", "", NS) or "")).strip()
        cats = [c.get("term") for c in e.findall("a:category", NS)]
        out.append({"title": t, "abstract": s[:700], "published": (e.findtext("a:published", "", NS) or "")[:10],
                    "categories": cats, "arxiv_id": (e.findtext("a:id", "", NS) or "").rsplit("/", 1)[-1]})
    return out


def load_ckpt():
    return json.loads(CKPT.read_text(encoding="utf-8")) if CKPT.exists() else {"records": []}


def save_ckpt(state):
    tmp = CKPT.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=1, ensure_ascii=False), encoding="utf-8", newline="")
    tmp.replace(CKPT)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    resume = "--resume" in sys.argv
    state = load_ckpt() if resume else {"records": [], "started_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    done = {(r["topic"], r["phrase"], r["category"]) for r in state["records"]}
    t0 = time.time()
    for topic, pairs in SCREEN.items():
        for phrase, cat in pairs:
            key = (topic, phrase, cat)
            if key in done:
                continue
            q = f'abs:"{phrase}"' + (f" AND cat:{cat}" if cat else "")
            body, err = fetch({"search_query": q, "max_results": MAX_RESULTS, "sortBy": "relevance"})
            if err:
                status, hits = "transport_error", []
            else:
                try:
                    hits = parse(body)
                except Exception as e:
                    status, hits = "transport_error", []
                    err = f"parse {type(e).__name__}"
                else:
                    status = "informative" if hits else "zero_records"
            kw = KEYWORDS[topic]
            coll = [h for h in hits if any(w in (h["title"] + " " + h["abstract"]).lower() for w in kw)]
            rec = {"topic": topic, "phrase": phrase, "category": cat, "query_string": q, "status": status,
                   "error": err, "n_returned": len(hits), "n_keyword_relevant": len(coll),
                   "top": [{"title": h["title"][:110], "id": h["arxiv_id"], "year": h["published"][:4],
                            "cats": h["categories"]} for h in hits[:MAX_RESULTS]],
                   "collision_candidates": [{"title": h["title"][:110], "id": h["arxiv_id"],
                                             "year": h["published"][:4]} for h in coll[:6]]}
            state["records"].append(rec)
            save_ckpt(state)
            print(f"  {topic} {phrase!r:42s} {cat or '-':8s} {status:15s} returned={rec['n_returned']:2d} "
                  f"relevant={rec['n_keyword_relevant']:2d}", flush=True)
            time.sleep(PACE)

    by = {}
    for r in state["records"]:
        by.setdefault(r["topic"], []).append(r)
    rollup = {}
    for topic, rs in by.items():
        inf = [r for r in rs if r["status"] == "informative"]
        err = [r for r in rs if r["status"] == "transport_error"]
        cands = {c["id"] for r in rs for c in r["collision_candidates"]}
        rollup[topic] = {"queries": len(rs), "informative": len(inf), "zero_records": len(rs) - len(inf) - len(err),
                         "transport_error": len(err), "collision_candidates": len(cands),
                         "max_relevant_per_query": max([r["n_keyword_relevant"] for r in rs] or [0]),
                         "verdict": ("screen_incomplete_all_queries_empty" if len(inf) == 0
                                     else "collision_present" if cands else "informative_but_not_keyword_relevant"),
                         "decidable": len(inf) > 0 and len(err) == 0}
    out = {"exp_id": "EXP-0047", "kind": "arxiv_novelty_screen", "endpoint": API, "query_form": 'abs:"phrase" [AND cat:X]',
           "rule": "a gap may not be inferred from zero_records alone; see the module docstring",
           "started_at": state.get("started_at"), "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "wallclock_sec": round(time.time() - t0, 1), "rollup": rollup, "records": state["records"]}
    stamp = time.strftime("%Y%m%dT%H%M%S")
    (OUT_DIR / f"EXP0047_arxiv_topic_screen_{stamp}.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8", newline="")
    pdir = ROOT / "results_processed"
    pdir.mkdir(exist_ok=True)
    lines = ["topic,queries,informative,zero_records,transport_error,collision_candidates,verdict,decidable"]
    for t, v in sorted(rollup.items()):
        lines.append(f'{t},{v["queries"]},{v["informative"]},{v["zero_records"]},{v["transport_error"]},'
                     f'{v["collision_candidates"]},{v["verdict"]},{v["decidable"]}')
    (pdir / "EXP0047_topic_screen_rollup.csv").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="")
    print(json.dumps(rollup, ensure_ascii=False, indent=0)[:1200])
    print("wrote", f"EXP0047_arxiv_topic_screen_{stamp}.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
