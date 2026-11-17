"""EXP-0032: push the w0_audit topics through the funnel with evidence, not opinion.

For every topic still sitting at w0_audit this records (a) data feasibility measured from the local audit
manifests that the shared dataset-audit module produced (rows, shards, schema, licence declaration, key-field
coverage), (b) a collision check against arXiv via the export API (title-derived keyword query, hit counts and
the nearest titles kept verbatim), and (c) a status assigned by a rule written down here before the run:

  * primary dataset is not among the eight local corpora and no reachable source  -> w2_blocked (no data here)
  * licence undeclared in the release metadata                                   -> w2_blocked (G04 rule)
  * the concept the topic's DV needs is absent from that corpus's measured schema -> killed_L4_and_unidentifiable
  * >= 3 arXiv hits whose titles share the topic's core nouns                     -> demoted_L3_crowded
  * otherwise                                                                    -> w1_recommended / w1_audit_done

Nothing here is a paper-quality judgement; it is the funnel's feasibility + collision screen that decides which
topics deserve a pilot at all.
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
REG = ROOT / "00_program_registry" / "topic_registry.csv"
MAN = ROOT / "01_datasets" / "manifests"
OUT_RAW = ROOT / "results_raw"
STOP = set("a an the of and for on in with from to using via toward towards study studies based public large scale".split())


def arxiv(query, n=5):
    url = ("https://export.arxiv.org/api/query?search_query=" + urllib.parse.quote(query)
           + f"&max_results={n}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                                                           "Chrome/124.0.0.0 Safari/537.36",
                                                "Accept": "application/atom+xml, text/xml, */*"})
    try:
        raw = urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "replace")
    except Exception as exc:
        # A refused/throttled request is NOT an empty literature. Callers must check `error` before
        # concluding anything about collision, and label the outcome "retrieval_failed".
        return {"error": f"{type(exc).__name__}: {exc}", "collision_status": "retrieval_failed",
                "query": query, "hits": []}
    titles = re.findall(r"<title>(.*?)</title>", raw, re.S)[1:]
    ids = re.findall(r"<id>(http://arxiv.org/abs/.*?)</id>", raw)
    return {"query": query, "collision_status": "zero_records" if not titles else "hits_returned",
            "n_returned": len(titles),
            "hits": [{"title": t.strip().replace("\n", " ")[:160], "id": i} for i, t in zip(ids, titles)]}


def key_nouns(title, k=4):
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z\-]+", str(title)) if w.lower() not in STOP]
    seen, out = set(), []
    for w in words:
        lw = w.lower()
        if lw not in seen:
            seen.add(lw)
            out.append(lw)
        if len(out) >= k:
            break
    return out


def manifest_for(name):
    """Locate the audit manifest whose dataset name best matches a topic's primary_dataset string."""
    if not name or (isinstance(name, float) and pd.isna(name)):
        return None
    cand = sorted(MAN.glob("*.audit.json"))
    toks = [t for t in re.split(r"[^A-Za-z0-9]+", str(name)) if len(t) > 2]
    best = None
    for f in cand:
        stem = f.name.replace(".audit.json", "")
        score = sum(1 for t in toks if t.lower() in stem.lower())
        if score and (best is None or score > best[1]):
            best = (f, score)
    return best[0] if best else None


def registry_row(name):
    """Licence and row counts are recorded in the program-level dataset_registry.csv, NOT in the per-dataset
    audit json - the first version of this screen read the wrong file and mis-blocked 13 topics (D23)."""
    if not name or (isinstance(name, float) and pd.isna(name)):
        return None
    reg = pd.read_csv(MAN / "dataset_registry.csv")
    toks = [t for t in re.split(r"[^A-Za-z0-9]+", str(name)) if len(t) > 2]
    best = None
    for _, r in reg.iterrows():
        hay = f"{r['dataset']} {r['hf_repo_id']}".lower()
        score = sum(1 for t in toks if t.lower() in hay)
        if score and (best is None or score > best[0]):
            best = (score, r)
    return None if best is None else best[1]


def feasibility(path):
    if not path:
        return {"manifest": None, "on_local_disk": False}
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    cfgs = d.get("configs", {})
    first = next(iter(cfgs.values()), {})
    cols = {c: v for c, v in (first.get("columns") or {}).items()}
    reg = registry_row(d.get("dataset") or d.get("hf_repo_id"))
    lic = (str(reg["license_declared"]) if reg is not None else None)
    declared = bool(reg is not None) and str(lic).strip().lower() not in ("false", "none", "nan", "")
    return {"manifest": Path(path).name, "on_local_disk": True, "hf_repo_id": d.get("hf_repo_id"),
            "license_declared": declared, "license_field": lic,
            "rows_registered": (None if reg is None else reg.get("total_rows_measured")),
            "n_files": first.get("n_files"), "rows_total": first.get("total_rows_all_files"),
            "unreadable_shards": first.get("unreadable_shards"), "columns": list(cols),
            "key_coverage": {c: {"null_ratio": v.get("null_ratio"), "non_empty_ratio": v.get("non_empty_ratio")}
                             for c, v in list(cols.items())[:10]}}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    topics = pd.read_csv(REG)
    todo = topics[topics.status == "w0_audit"]
    res = {"exp_id": "EXP-0032", "stage": "funnel_audit_w0_topics", "seed": "n/a (deterministic screen)",
           "rule": "see module docstring; statuses are assigned by the rule, not by hand",
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "n_topics": int(len(todo)), "topics": []}
    new_status = {}
    for _, row in todo.iterrows():
        tid = row.topic_id
        man = manifest_for(row.get("primary_dataset"))
        fe = feasibility(man)
        nouns = key_nouns(row.get("title_en"))
        # AND of the two most specific nouns: an OR of loose keywords returns nothing useful and was
        # previously read as "no collision", which it is not (D24).
        phrase = " AND ".join(f'all:"{n}"' for n in nouns[:2])
        coll = arxiv(phrase) if len(nouns) >= 2 else {"query": None, "hits": [], "n_returned": 0}
        strong = 0
        if nouns:
            for h in coll.get("hits", []):
                t = h["title"].lower()
                if sum(1 for n in nouns if n in t) >= max(2, len(nouns) - 1):
                    strong += 1
        if not fe["on_local_disk"]:
            status = "w2_blocked"
            reason = "primary dataset is not among the eight releases on local disk and has no reachable source here"
        elif not fe.get("license_declared", True):
            status = "w2_blocked"
            reason = "release declares no licence (G04 rule)"
        elif strong >= 3:
            status = "demoted_L3_crowded"
            reason = f"{strong} arXiv records share the topic's core nouns: {nouns}"
        else:
            status = "w1_audit_done"
            reason = (f"local data present ({fe.get('rows_total')} rows, {fe.get('n_files')} files, "
                      f"{len(fe.get('columns') or [])} columns); collision: "
                      + (f"{strong} strong match(es) of {coll.get('n_returned')} returned"
                         if coll.get("n_returned") else "query returned no records, so NOT evaluated"))
        new_status[tid] = (status, reason, fe, coll)
        res["topics"].append({"topic_id": tid, "title_en": str(row.get("title_en"))[:180],
                              "primary_dataset": str(row.get("primary_dataset")), "feasibility": fe,
                              "collision_query": coll.get("query"), "collision_n_returned": coll.get("n_returned"),
                              "collision_informative": bool(coll.get("n_returned")),
                              "collision_strong_matches": strong,
                              "collision_top_titles": [h["title"] for h in coll.get("hits", [])[:3]],
                              "assigned_status": status, "reason": reason})
        print(f"  {tid}: {status} ({reason[:80]})")

    topics["status"] = topics.apply(lambda r: new_status[r.topic_id][0] if r.topic_id in new_status else r.status, axis=1)
    topics["data_feasibility"] = topics.apply(
        lambda r: (new_status[r.topic_id][2].get("manifest") or "no manifest") + " | " + new_status[r.topic_id][1]
        if r.topic_id in new_status else r.data_feasibility, axis=1)
    topics.to_csv(REG, index=False)
    res["wallclock_sec"] = round(time.time() - t0, 1)
    res["status_counts"] = topics.status.value_counts().to_dict()
    res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    OUT_RAW.mkdir(exist_ok=True)
    out = OUT_RAW / f"EXP0032_funnel_audit_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    pd.DataFrame([{"topic_id": t["topic_id"], "assigned_status": t["assigned_status"],
                   "collision_strong": t["collision_strong_matches"], "local_rows": t["feasibility"].get("rows_total"),
                   "license_declared": t["feasibility"].get("license_declared"), "reason": t["reason"]}
                  for t in res["topics"]]).to_csv(ROOT / "results_processed" / "EXP0032_funnel_screen.csv", index=False)
    print(json.dumps(res["status_counts"], ensure_ascii=False))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
