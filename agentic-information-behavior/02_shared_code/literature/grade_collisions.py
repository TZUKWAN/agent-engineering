"""EXP-0057: grade every screened record L0–L4 against the construct of the paper it was retrieved for.

The spec requires the literature matrix to carry a collision level per record and the novelty audit to be written
from it. Until now `overlap_level` held a retrieval note, not a grade, and grading needs the abstract - which
EXP-0056 fetched into `00_program_registry/literature_abstracts.csv`.

Levels (the programme's convention, L4 most severe):
  L4  same object AND same construct AND same measurement on comparable data  -> the gap is taken
  L3  same construct and same object family, different measurement or data
  L2  same construct, different object family (method or population differs)
  L1  overlapping method/technique only, different construct
  L0  background, vocabulary or venue overlap only

The grading is rule-based over title + abstract with each paper's own term families, and every record keeps the
matched terms as its evidence. Two honesty rules are enforced in the output:
  * a record graded from the title alone is marked `title_only` — 94 of the 247 Crossref records have no deposited
    abstract, and they are not silently treated as read;
  * every L3/L4 grade is listed for hand verification in `docs/literature_grading_review_20260920.md`. A rule that
    can over-grade a record because two phrase families co-occur must be checked, not trusted.

    python 02_shared_code/literature/grade_collisions.py
"""
from __future__ import annotations

import csv, json, pathlib, re, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
REG = ROOT / "00_program_registry"
# the newest abstracts file, not literally v1: EXP-0095 and EXP-0111 wrote recovered text into v2/v3, and grading from
# v1 silently ignored 57 records' worth of abstracts that had been recovered after this script's first run (v3 is a
# superset of v1 by cite key, so nothing is lost by following the chain)
SRC = max(sorted(REG.glob("literature_abstracts*.csv")),
          key=lambda p: (len(p.read_text(encoding="utf-8", errors="replace").splitlines()), p.name))
OUTCSV = REG / "literature_graded.csv"
REVIEW = ROOT / "docs" / "literature_grading_review_20260920.md"

# object = what is studied; construct = the question/property asked about it; measure = the operationalisation;
# data = the corpus family it is done on.
PAPERS = {
    "P001": {"object": ["tool retrieval", "tool search", "function calling", "tool selection", "mcp", "api retrieval"],
             "construct": ["query performance prediction", "query difficulty", "pre-retrieval", "failure prediction",
                           "predicting retrieval quality", "query quality"],
             "measure": ["auc", "auroc", "hit rate", "recall@", "precision@", "correlation with", "regression on"],
             "data": ["toucan", "toolbench", "api bank", "agent trajectory", "function call logs"]},
    "P002": {"object": ["search session", "information seeking", "search process", "interaction trace", "dialogue",
                        "agent trajectory", "log data"],
             "construct": ["search stage", "information search process", "uncertainty", "problem behaviour",
                           "exploration stage", "phase model", "step classification"],
             "measure": ["markov", "transition probability", "bits per", "entropy", "codab", "coding scheme",
                         "inter-rater", "kappa"],
             "data": ["search log", "conversation dataset", "agent trajectory", "session logs"]},
    "P003": {"object": ["dataset schema", "trajectory data", "corpus metadata", "data format", "jsonl", "parquet",
                        "benchmark dataset"],
             "construct": ["interoperability", "schema mapping", "schema matching", "metadata conformance",
                           "canonical schema", "crosswalk", "harmoniz", "portability"],
             "measure": ["field coverage", "recoverab", "mapping", "conversion", "round-trip", "conformance check"],
             "data": ["language model dataset", "agent dataset", "benchmark corpus", "hugging face dataset"]},
    "P004": {"object": ["quality score", "llm-as-a-judge", "judge", "rating", "label", "score"],
             "construct": ["construct validity", "criterion validity", "reliability", "agreement", "consistency",
                           "internal structure", "cronbach"],
             "measure": ["correlation with", "ground truth", "krippendorff", "cohens kappa", "cronbach alpha",
                         "roc", "agreement rate"],
             "data": ["agent trajectory", "synthetic data", "instruction dataset", "preference dataset"]},
    "P005": {"object": ["dataset card", "datacard", "model card", "datasheet", "ai system card", "dataset release",
                        "corpus", "benchmark"],
             "construct": ["licens", "copyright", "provenance", "attribution", "redistribut", "terms of use",
                           "governance", "compliance", "documentation completeness", "metadata quality"],
             "measure": ["audit", "census", "presence", "completeness assessment", "we measure", "study of"],
             "data": ["hugging face", "model repository", "open dataset", "agent trajectory", "llm dataset",
                      "research software", "github"]},
}


def grade(pid, title, abstract):
    fam = PAPERS[pid]
    txt = (title + " " + abstract).lower()
    hit = {k: [t for t in v if t in txt] for k, v in fam.items()}
    n = {k: len(v) for k, v in hit.items()}
    if n["construct"] >= 2 and n["measure"] >= 1 and n["object"] >= 1 and n["data"] >= 1:
        lvl = "L4"
    elif n["construct"] >= 2 and (n["object"] >= 1 or n["data"] >= 1):
        lvl = "L3"
    elif n["construct"] >= 1 and (n["measure"] >= 1 or n["object"] >= 1):
        lvl = "L2"
    elif n["object"] >= 1 or n["measure"] >= 1:
        lvl = "L1"
    else:
        lvl = "L0"
    return lvl, hit, n


def main() -> int:
    sys_stdout = __import__("sys").stdout
    try:
        sys_stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if not SRC.exists():
        raise SystemExit("[grade] run fetch_abstracts.py first; nothing to grade.")
    rows = list(csv.DictReader(open(SRC, encoding="utf-8")))
    out, dist = [], {p: {} for p in PAPERS}
    for r in rows:
        pid = (r["paper_id"] or "").strip()
        if pid not in PAPERS:
            continue
        lvl, hit, n = grade(pid, r["title"], r["abstract"])
        dist[pid][lvl] = dist[pid].get(lvl, 0) + 1
        out.append({**{k: r[k] for k in ("paper_id", "cite_key", "source", "identifier", "year", "venue", "title",
                                         "url", "collision_target", "overlap_level_current")},
                    "level_rule": lvl,
                    "graded_on": "title+abstract" if r["abstract"].strip() else "title_only",
                    "n_object": n["object"], "n_construct": n["construct"], "n_measure": n["measure"],
                    "n_data": n["data"],
                    "matched": json.dumps(hit, ensure_ascii=False),
                    "needs_hand_check": int(lvl in ("L3", "L4") or (lvl == "L2" and r["abstract"].strip() == "")),
                    "level_final": ""})
    fields = list(out[0].keys())
    with open(OUTCSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(out)
    print(json.dumps({"rows": len(out), "per_paper": dist,
                      "hand_check": sum(r["needs_hand_check"] for r in out),
                      "title_only": sum(r["graded_on"] == "title_only" for r in out)}, ensure_ascii=False, indent=1))

    need = [r for r in out if r["needs_hand_check"]]
    L = ["# L3/L4 hand-verification list (EXP-0057)", "",
         f"Generated {time.strftime('%Y-%m-%d %H:%M')} from `00_program_registry/literature_graded.csv`. "
         f"{len(need)} of {len(out)} records were rule-graded L3/L4 (or L2 with no abstract to read) and must be "
         "confirmed by reading the abstract before any novelty audit cites them; `level_final` in the CSV is the "
         "authoritative field once filled.", "",
         "| paper | rule | graded on | year | title | what matched |", "|---|---|---|---|---|---|"]
    for r in sorted(need, key=lambda x: (x["paper_id"], x["level_rule"] != "L4", x["level_rule"])):
        m = json.loads(r["matched"])
        matched = "; ".join(f"{k}={','.join(v)}" for k, v in m.items() if v)[:190]
        L.append(f"| {r['paper_id']} | {r['level_rule']} | {r['graded_on']} | {r['year']} | "
                 f"{r['title'][:110]} | {matched} |")
    REVIEW.write_text("\n".join(L) + "\n", encoding="utf-8", newline="")
    print("wrote", OUTCSV.name, "and", REVIEW.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
