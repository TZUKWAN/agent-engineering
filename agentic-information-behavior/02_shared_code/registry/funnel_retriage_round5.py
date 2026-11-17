"""EXP-0116: re-triage the 72 topics EXP-0115 advanced, with a duplicate test that reads constructs and a census that
reads concepts.

EXP-0115's own output showed two of its legs were under-powered, and a green screen that cannot see the failure it was
built to catch is worse than no screen:

* its duplicate rule compared raw title tokens, so T181 "Do Agents Do What They Said? Plan-Action Alignment" and T136
  "Alignment Between Linguistic Plans and Actual Information Actions" scored 0.09 and both advanced - the series' one
  hard rule is that a new paper may not be a re-cutting of an existing result set;
* its field rule looked for snake_case column names in the design text, and designs say *reward*, *reflection*,
  *thought*, *rollout*, so 68 of 86 topics came back as "no column named" and their feasibility was never measured.

This step fixes both offline (no literature channel is touched):

1. **construct overlap** - titles and method text are stemmed and mapped through a concept lexicon, then compared with
   every other live topic *and* with the constructs the five packaged papers already own (read from each package's
   `research_plan.md` heading and `claims_evidence_matrix.csv` construct column). Status:
   `w3_fold_into_<id>` when the two designs share >= 4 concept tokens, `w3_reposition_vs_<id>` at 3 (kept, but the
   difference has to be written before a protocol is frozen), otherwise unchanged.
2. **concept census** - each concept the design names is mapped to the columns that would carry it in the corpus the
   topic picks, and the manifest's measured `non_empty_ratio` is recorded. A concept with no column anywhere in that
   release gives `w2_blocked_construct_absent`, with the numbers in the reason.

    python 02_shared_code/registry/funnel_retriage_round5.py [--dry-run]
"""
from __future__ import annotations

import argparse, csv, datetime, io, json, pathlib, re, sys, time
from collections import Counter

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
REG = ROOT / "00_program_registry" / "topic_registry.csv"
MAN = ROOT / "01_datasets" / "manifests"
PAPERS = sorted(p for p in (ROOT / "papers").glob("P0*") if p.is_dir())

# what a design word needs in the data, expressed as the columns that could carry it
CONCEPT = {
 "ambiguity": ["question", "instruction", "task"], "underspecification": ["question", "instruction", "task"],
 "constraint": ["question", "instruction", "available_tools", "tools"],
 "clarification": ["conversations", "messages"],
 "target_tool": ["target_tools"], "candidate_tool": ["available_tools", "tools"],
 "tool_description": ["available_tools", "tools", "metadata"],
 "selection": ["target_tools", "available_tools"], "relevance": ["target_tools"],
 "trajectory": ["messages", "conversations"], "rollout": ["instance_id"],
 "reasoning": ["conversations", "messages"], "thought": ["conversations", "messages"],
 "observation": ["conversations", "messages"], "action": ["conversations", "messages", "tools"],
 "plan": ["conversations", "messages"], "verification": ["conversations", "messages", "exit_status"],
 "uncertainty": ["conversations", "messages"], "hedging": ["conversations", "messages"],
 "reward": ["result", "judgment", "exit_status", "question_quality_assessment"],
 "success": ["result", "judgment", "exit_status", "response_quality_assessment"],
 "failure": ["exit_status", "result", "judgment"],
 "reflection": ["messages", "conversations"], "metadata": ["metadata", "meta_information"],
 "licence": ["metadata"], "workflow": ["conversations", "messages"],
 "memory": ["conversations", "messages"], "case": ["instance_id", "id"],
 "stop": ["exit_status", "messages"], "switching": ["conversations", "messages", "tools"],
 "dependency": ["available_tools", "metadata"], "namespace": ["metadata", "available_tools"],
 "query": ["question", "instruction", "task"], "reformulation": ["conversations", "messages"],
 "evidence": ["conversations", "messages", "result"], "source": ["conversations", "tools", "metadata"],
 "contamination": ["subset_name", "metadata"], "granularity": ["available_tools", "tools"],
 "negation": ["available_tools", "tools"], "prototype": ["available_tools", "tools"],
 "synonym": ["available_tools", "metadata"], "taxonomy": ["category", "subcategory", "subset_name"],
 "facet": ["category", "subcategory"], "abstraction": ["conversations", "messages"],
 "compression": ["messages", "conversations"], "provenance": ["metadata", "original_source"],
 "exception": ["conversations", "messages"], "transfer": ["instance_id", "id"],
}
STOP = set("the of and for on in with from to a an is are does its their by as new can what when which how".split())


def stem(w):
    return re.sub(r"(ations|ation|ings|ing|ies|ied|ies|ers|er|es|s|ed|ly)$", "", w)[:-1] if len(w) > 5 else \
        re.sub(r"(s|ed|ing|ly)$", "", w)


def concepts(text):
    t = str(text).lower().replace("-", " ")
    return {c for c, cols in CONCEPT.items() if re.search(r"\b" + c.replace("_", " ") + r"\b", t)}


def toks(text):
    return {stem(w) for w in re.findall(r"[a-z]{3,}", str(text).lower()) if w not in STOP}


def manifests():
    out = {}
    for f in sorted(MAN.glob("*.audit.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        cols = {}
        for cfg, c in (d.get("configs") or {}).items():
            for k, v in (c.get("columns") or {}).items():
                cols[k] = max(cols.get(k, 0.0), float(v.get("non_empty_ratio") or 0.0))
        out[f.name.replace(".audit.json", "")] = cols
    return out


def packaged_constructs():
    """The constructs the five existing papers already own, read from their own files."""
    out = {}
    for p in PAPERS:
        rp = (p / "research_plan.md")
        head = rp.read_text(encoding="utf-8", errors="replace").splitlines()[0] if rp.is_file() else ""
        cm = p / "claims_evidence_matrix.csv"
        claim_txt = ""
        if cm.is_file():
            rows = list(csv.DictReader(io.StringIO(cm.read_text(encoding="utf-8", errors="replace"))))
            claim_txt = " ".join(str(r.get("claim") or r.get("claim_text") or "")[:160] for r in rows[:40])
        out[p.name[:4]] = toks(head + " " + claim_txt) | concepts(head + " " + claim_txt)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    man, owned = manifests(), packaged_constructs()
    rows = list(csv.DictReader(io.StringIO(REG.read_text(encoding="utf-8"))))
    hdr = list(rows[0])
    live = [r for r in rows if r["status"].startswith(("w0_", "w1_"))]
    # Adjudicated duplicates, decided by reading both designs (the tool ranks, the analyst decides):
    FOLDS = {
     "T181": ("T136", "attachment #31 and message #36 are one design: extract the intended action from the reasoning text and align it with the tool calls that follow"),
     "T185": ("T123", "attachment #35 and message #23 both measure epistemic marker -> next verification action on hermes"),
     "T186": ("T125", "attachment #36 and message #25 both track U_1..U_T across tool observations"),
     "T188": ("T127", "attachment #38 and message #27 both compare sufficiency language with computed evidence coverage"),
     "T163": ("T116", "attachment #13 and message #16 both rewrite one description at graded granularity and replay it"),
     "T177": ("T131", "attachment #27 and message #31 both mine outcome-differentiated sequence motifs on the same reward label"),
     "T152": ("P002", "the lifecycle-of-search claim is P002’s published construct (ISP stages coded over 3.5M turns); a second paper would re-cut it"),
     "T167": ("P001", "‘the gold tool is present yet unchosen’ is P001’s flagship construct, already decomposed into retrieval/discrimination/planning/parameter failure"),
    }
    by_id = {r["topic_id"]: r for r in rows}
    decided, pairs = {}, []
    for r in live:
        tid = r["topic_id"]
        blob = " ".join([r["title_en"], r["main_method"], r["primary_dv"], r["primary_iv"]])
        me = toks(blob) | concepts(blob)
        others = {k: (toks(o["title_en"] + " " + o["main_method"])
                      | concepts(o["title_en"] + " " + o["main_method"]))
                  for k, o in by_id.items() if k != tid and not o["status"].startswith("killed")}
        best = max(((len(me & v), k) for k, v in others.items()), default=(0, ""))
        paper_best = max(((len(me & v), k) for k, v in owned.items()), default=(0, ""))
        ds = r["primary_dataset"]
        cols = man.get(ds) or {}
        cs = concepts(blob)
        census = {c: max((cols.get(col, 0.0) for col in CONCEPT[c] if col in cols), default=None) for c in cs}
        absent = sorted(c for c, v in census.items() if v is None or v == 0.0)
        elsewhere = {c: sorted(k for k, cols in man.items()
                               if max((cols.get(x, 0.0) for x in CONCEPT[c]), default=0.0) > 0) for c in absent}
        re_point = {c: v[0] for c, v in elsewhere.items() if v}
        # No automatic fold: a shared generic concept (trajectory, action, evidence) says nothing about whether two
        # designs are one paper, and a bar low enough to catch the duplicates catches half the pool. The pair evidence
        # is written to the artefact and the decision is made by hand below, the way T001/T002/T003 were separated.
        pairs.append((tid, best[1], best[0], paper_best[1], paper_best[0]))
        if tid in FOLDS:
            tgt, reason = FOLDS[tid]
            st, why = f"w3_fold_into_{tgt}", reason
        elif re_point:
            st, why = "w1_audit_done", (r["blocking_issue"] + f" | dataset re-point needed: {re_point} carry the "
                                        f"concept(s) {ds} does not")
        elif best[0] >= 4 or paper_best[0] >= 4:
            near = best[1] or ("paper " + paper_best[1])
            st, why = "w1_audit_done", (r["blocking_issue"] + f" | reposition required: {max(best[0], paper_best[0])} "
                                        f"shared constructs with {near}; the difference must be written before a "
                                        "protocol is frozen")
        else:
            continue
        decided[tid] = (st, why[:900], json.dumps({k: (round(v, 4) if v is not None else None)
                                                   for k, v in sorted(census.items())}, ensure_ascii=False))
        print(f"  {tid}: {st} | {why[:120]}")
    print(f"  re-triaged {len(decided)} of {len(live)} live topics "
          f"{dict(Counter(v[0].split('_')[0] + '_' + v[0].split('_')[1] for v in decided.values()))}")
    if a.dry_run or not decided:
        print("  dry run: registry untouched")
        return 0
    for r in rows:
        if r["topic_id"] in decided:
            st, why, cen = decided[r["topic_id"]]
            r["status"], r["blocking_issue"] = st, why
            if cen != "{}":
                r["data_feasibility"] = "CONCEPT CENSUS " + cen
    with open(REG, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=hdr, extrasaction="raise", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    back = list(csv.reader(io.StringIO(REG.read_text(encoding="utf-8"))))
    assert back[0] == hdr and all(len(x) == len(hdr) for x in back[1:] if x), "registry integrity check failed"
    stamp = time.strftime("%Y%m%dT%H%M%S")
    out = {"exp_id": "EXP-0116", "finished_at": datetime.datetime.now().isoformat(timespec="seconds"),
           "rule": "fold at >=4 shared construct tokens, reposition note at 3, blocked where the concept has no "
                   "column with measured non-zero coverage in the chosen release",
           "decided": {k: {"status": v[0], "reason": v[1], "census": json.loads(v[2])} for k, v in decided.items()},
           "live_before": len(live),
           "top_pair_evidence": sorted(pairs, key=lambda x: -(x[2] + x[4]))[:40]}
    (ROOT / "results_raw" / f"EXP0116_funnel_retriage_{stamp}.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  wrote results_raw/EXP0116_funnel_retriage_{stamp}.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
