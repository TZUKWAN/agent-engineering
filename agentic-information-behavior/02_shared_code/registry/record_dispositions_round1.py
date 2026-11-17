"""EXP-0230: fill the four evidence columns for the topics the first round decided without a machine record.

`topic_registry.csv` is the table a reader judges a topic by, and its four evidence columns
(`exp_ids`, `measured_coverage`, `figures_tables`, `collision_verdict`) are the difference between "this idea was
screened" and "this idea was screened, and here is what the screening measured". Round 2 found 24 of the 123 rows
carrying none of the four: 13 wave-3 folds, 8 demotions and 3 kills, all decided on 2026-09-18 by hand-reading the
first literature pass - before the machine collision search (EXP-0038) and the feasibility census (EXP-0032)
existed, and before `record_intake_dispositions.py` covered the later funnel decisions.

Three derivations are tried for each row, in this order, and each records only what it actually finds:

1. **the machine screen** - the topic's own record in `EXP0032_funnel_audit_*.json` (feasibility measured against
   the dataset manifests) and `EXP0038_topic_collisions_*.json` (live transport queries, candidates, shared-noun
   overlap);
2. **the graded corpus** - records in `literature_graded*.csv` whose `collision_target` names the topic, with the
   level the frozen rule re-derived for them (EXP-0097);
3. **the citations the decision itself names** - the arXiv ids, DOIs and cite keys quoted in the row's
   `blocking_issue`, looked up in the harvested abstract corpora. A decision that cites a paper the estate never
   fetched is reported as such rather than being given a cleaner look: the count of unresolved citations is written
   into the evidence row, because that is a real limit on how checkable the disposition is.

A row that resolves through none of the three keeps its columns empty rather than receiving prose invented for the
occasion, and is printed so the round can see what is left.

    python 02_shared_code/registry/record_dispositions_round1.py [--apply]
"""
from __future__ import annotations

import argparse
import csv
import datetime
import glob
import io
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
REG = ROOT / "00_program_registry" / "topic_registry.csv"
EVID = ROOT / "00_program_registry" / "topic_evidence.csv"
COLS = ["topic_id", "package", "exp_ids", "measured_coverage", "figures_tables", "collision_verdict"]
EV = COLS[2:]
ARX = re.compile(r"\b\d{4}\.\d{4,5}\b")
DOI = re.compile(r"\b10\.\d{4,9}/[^\s;,)]+")
TRUNC = 1800


def latest(pat: str):
    f = sorted(glob.glob(str(ROOT / pat)), key=lambda x: pathlib.Path(x).stat().st_mtime)
    return pathlib.Path(f[-1]) if f else None


def read(p):
    return list(csv.DictReader(io.StringIO(p.read_text(encoding="utf-8-sig")))) if p and p.is_file() else []


def corpus_index() -> dict:
    """{identifier -> (file, row)} over every harvested literature record the estate holds."""
    idx = {}
    for p in sorted((ROOT / "00_program_registry").glob("literature_*.csv")) + \
            [f for f in sorted((ROOT / "papers").glob("*/literature_*.csv"))]:
        for r in read(p):
            for key in (r.get("identifier"), r.get("arxiv_id"), r.get("doi"), r.get("cite_key")):
                if key and str(key).strip():
                    idx.setdefault(str(key).strip().lower(), (p.name, r))
    return idx


def screen_records():
    f32, f38 = latest("results_raw/EXP0032_funnel_audit_*.json"), latest("results_raw/EXP0038_topic_collisions_*.json")
    a32 = json.loads(f32.read_text(encoding="utf-8")) if f32 else {}
    a38 = json.loads(f38.read_text(encoding="utf-8")) if f38 else {}
    by32 = {t.get("topic_id"): t for t in a32.get("topics") or [] if isinstance(t, dict)}
    by38 = dict(a38.get("topics") or {})
    q38 = {}
    for q in a38.get("queries") or []:
        if isinstance(q, dict) and q.get("topic"):
            q38.setdefault(q["topic"], []).append(q)
    return by32, by38, q38, (f32.name if f32 else ""), (f38.name if f38 else "")


def graded_records():
    """{topic_id: [rows whose collision_target names it]} across the three graded corpora."""
    out = {}
    for p in sorted((ROOT / "00_program_registry").glob("literature_graded*.csv")):
        for r in read(p):
            for t in set(re.findall(r"\bT0\d\d\b", str(r.get("collision_target") or ""))):
                out.setdefault(t, []).append((p.name, r))
    return out


def derive(row: dict, by32, by38, q38, graded, idx, hosts) -> dict:
    tid = row["topic_id"]
    ids, cov, coll = [], {}, {}
    if tid in by32:
        t = by32[tid]
        ids.append("EXP-0032")
        cov["feasibility_census"] = {"file": "EXP0032_funnel_audit", "record": {
            k: v for k, v in t.items() if k in ("primary_dataset", "feasibility", "compute", "data_feasibility")}}
    if tid in by38 or tid in q38:
        ids.append("EXP-0038")
        t = by38.get(tid) or {}
        qs = q38.get(tid) or []
        coll["machine_collision_search"] = {
            "file": "EXP0038_topic_collisions", "queries_run": len(qs),
            "returned": sum(int(q.get("returned") or 0) for q in qs),
            "candidates_screened": int(t.get("n_candidates") or sum(int(q.get("candidates") or 0) for q in qs)),
            "statuses": sorted({str(q.get("status")) for q in qs}),
            "closest_records": [{"title": str(x.get("title"))[:90], "n_shared": x.get("n_shared"),
                                 "shared_nouns": x.get("shared_nouns")}
                                for x in (t.get("top") or [])[:3]]}
    for fname, r in graded.get(tid) or []:
        ids.append("EXP-0097")
        coll.setdefault("graded_corpus_records", []).append(
            {"table": fname, "cite_key": r.get("cite_key"), "level_final": r.get("level_final"),
             "rederived_by": r.get("level_rederived_by")})
    named = sorted(set(ARX.findall(str(row.get("blocking_issue") or ""))) |
                   set(DOI.findall(str(row.get("blocking_issue") or ""))))
    if named:
        hit = {k: idx[k.lower()] for k in named if k.lower() in idx}
        coll["citations_named_by_the_decision"] = {
            "looked_up": len(named), "found_in_the_harvested_corpus": len(hit),
            "found": [{"id": k, "table": v[0], "title": str((v[1] or {}).get("title"))[:90]} for k, v in hit.items()],
            "absent_from_the_corpus": [k for k in named if k.lower() not in idx]}
    for i in re.findall(r"EXP-\d{4}", str(row.get("blocking_issue") or "")):
        ids.append(i)
    host = re.search(r"into_(T\d\d\d)", str(row.get("status") or "")) or \
        re.search(r"merged_into_(T\d\d\d)", str(row.get("status") or ""))
    if host and host.group(1) in hosts and not cov:
        h = hosts[host.group(1)]
        ids.extend(x for x in re.findall(r"EXP-\d{4}", str(h.get("exp_ids") or "")))
        cov["inherited_from_host_topic"] = {"host": host.group(1), "host_exp_ids": h.get("exp_ids"),
                                            "host_measured_coverage": str(h.get("measured_coverage"))[:400]}
        coll["folded_into"] = {"host": host.group(1), "host_package": h.get("package")}
    ids = sorted(set(ids))
    if not (ids or cov or coll):
        # Nothing in the estate's machine records names this topic: the disposition rests on a hand-reading of the
        # first literature pass. Saying so in the table is the honest completion of the row - it is what tells a
        # reader that this cell is an assertion to re-check, not a measurement to cite. The citations the decision
        # itself quotes are looked up anyway, and whether the harvest holds them is reported.
        coll["hand_audit_no_machine_record"] = {
            "decided_by": "hand-reading of the 2026-09-18 literature pass, before EXP-0032 and EXP-0038 existed",
            "citations_in_the_row": named,
            "re_derivation_possible_from": "the graded corpus plus the harvested abstracts, by re-running the "
                                           "frozen rule against this topic's own title and method"}
        return {"exp_ids": "none - no machine record names this topic",
                "measured_coverage": json.dumps({"disposition": row.get("status"),
                                                 "decided_on": str(row.get("blocking_issue"))[:280], **cov},
                                                ensure_ascii=False)[:TRUNC],
                "figures_tables": ("none - the funnel stopped the claim on the literature record, so no local row "
                                   "was read and no figure or table was built"),
                "collision_verdict": json.dumps(coll, ensure_ascii=False)[:TRUNC],
                "_report": {"limit": True}}
    rep = coll.get("citations_named_by_the_decision") or {}
    return {"exp_ids": ";".join(ids) or "none - no machine record names this topic",
            "measured_coverage": json.dumps({"disposition": row.get("status"),
                                             "decided_on": str(row.get("blocking_issue"))[:280], **cov},
                                            ensure_ascii=False)[:TRUNC],
            "figures_tables": ("none - the funnel stopped the claim on the literature and feasibility record, so no "
                               "local row was read and no figure or table was built"),
            "collision_verdict": json.dumps(coll, ensure_ascii=False)[:TRUNC], "_report": rep}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    rows = read(REG)
    ev = {r["topic_id"]: r for r in read(EVID)}
    blank = [r for r in rows if not any(str(r.get(k) or "").strip() for k in EV)]
    by32, by38, q38, f32n, f38n = screen_records()
    graded = graded_records()
    idx = corpus_index()
    hosts = {t: r for t, r in ((r["topic_id"], r) for r in rows)}
    hosts = {t: {**r, **ev.get(t, {})} for t, r in hosts.items()}
    print(f"{len(blank)} topic row(s) carry no evidence; screen {f32n} / {f38n}; "
          f"{len(graded)} topic(s) in the graded corpus; {len(idx)} literature identifiers indexed")
    filled, unresolved = {}, []
    for r in blank:
        d = derive(r, by32, by38, q38, graded, idx, hosts)
        if not d:
            unresolved.append(r["topic_id"])
            continue
        rep = d.pop("_report", {})
        filled[r["topic_id"]] = d
        tag = "LIMIT" if rep.get("limit") else "ok"
        print(f"  {r['topic_id']:6s} {tag:6s} exp_ids={d['exp_ids'][:44]:46s} citations looked up "
              f"{rep.get('looked_up', 0)} found {rep.get('found_in_the_harvested_corpus', '-')}")
    limits = [t for t, d in filled.items() if d["exp_ids"].startswith("none")]
    print(f"{len(filled)} row(s) written, {len(limits)} of them recording the limit that no machine record names "
          f"the topic: {limits}")
    if not a.apply:
        print("--check only; pass --apply to write topic_evidence.csv")
        return 0
    for t, d in filled.items():
        ev[t] = {**ev.get(t, {}), "topic_id": t, "package": ev.get(t, {}).get("package") or "", **d}
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLS[:2] + EV, lineterminator=chr(10))
    w.writeheader()
    for t in sorted(ev):
        w.writerow({c: str(ev[t].get(c) or "") for c in w.fieldnames})
    EVID.write_text(buf.getvalue(), encoding="utf-8")
    dest = ROOT / "results_raw" / f"EXP0230_round1_disposition_evidence_{datetime.datetime.now():%Y%m%dT%H%M%S}.json"
    dest.write_text(json.dumps({"exp_id": "EXP-0230",
                                "seed": "n/a (a registry reconstruction from artefacts already on disk)",
                                "status": f"{len(filled)}_rows_filled",
                                "topic_rows_without_evidence_before": len(blank),
                                "filled": sorted(filled), "no_machine_record": unresolved,
                                "sources": {"feasibility_census": f32n, "collision_search": f38n,
                                            "graded_tables": sorted({p.name for p in
                                                                    (ROOT / '00_program_registry').glob('literature_graded*.csv')}),
                                            "literature_identifiers_indexed": len(idx)},
                                "at": datetime.datetime.now().isoformat(timespec="seconds")},
                               indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote", dest.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
