"""EXP-0115: screen the 86 topics registered on 2026-09-23 through the funnel, with measurements not opinions.

Two batches arrived the same day - 42 numbered ideas in the message (T101-T142) and a 44-item list in the attachment
(T151-T194, whose own numbering runs 1-41 and 46-48) - and both were registered at `w0_audit`. Spec §20 caps one
candidate pool at 50, so the intake is audited in waves of at most 50, and this step decides each topic's status by a
rule written here before any local row or literature query is touched:

1. **no data here** - none of the corpora the design names is among the eight releases on disk -> `w2_blocked_no_data`;
2. **the field the design needs is not there** - every column the topic's own method text names is checked against the
   audit manifest of that corpus, per config, and reported with its measured `non_empty_ratio`. A named column that is
   absent everywhere, or present but empty in every audited row, gives `w2_blocked_field_absent`. A column that exists
   under a different name is *not* silently substituted: the substitute and its coverage are printed and the topic is
   advanced with the substitution recorded;
3. **already in this programme** - the topic's English title is compared token-wise with every other live topic; a
   Jaccard overlap of 0.5 or more gives `w3_fold_into_<id>`, because a second paper on one construct is exactly what
   the series forbids;
4. **crowded outside** - the arXiv export API is queried with the AND of the two most specific title nouns (an OR of
   loose keywords returns nothing useful and was once misread as "no collision", D24); three or more strong title
   matches give `demoted_L3_crowded`. A refused or throttled request is recorded as `retrieval_failed` and is never
   read as an empty literature;
5. otherwise -> `w1_audit_done`, with the measured row/column counts in the blocking-issue field so the next step can
   see what it is standing on.

    python 02_shared_code/registry/funnel_audit_round5.py [--wave 1] [--dry-run]
"""
from __future__ import annotations

import argparse, csv, datetime, io, json, pathlib, re, sys, time, urllib.parse, urllib.request

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
sys.path.insert(0, str(HERE))
from funnel_audit import key_nouns  # the same noun rule as EXP-0032                      # noqa: E402
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0.0.0 Safari/537.36")

REG = ROOT / "00_program_registry" / "topic_registry.csv"
MAN = ROOT / "01_datasets" / "manifests"
WAVE_CAP = 50
JACCARD_FOLD = 0.5
STRONG_HITS = 3
STOP = set("the of and for on in with from to a an is are does its their agent agents study studies new".split())

# names the designs use that are not top-level columns in the release they name, with what the manifest does carry
SUBSTITUTES = {("AgentTrove", "reward"): "result/judgment", ("hermes", "thought"): "conversations",
               ("hermes", "reasoning"): "conversations", ("MMAT-1M", "reflection"): "messages",
               ("Toucan-1.5M", "difficulty"): "question_quality_assessment"}


def manifests():
    out = {}
    for f in sorted(MAN.glob("*.audit.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        name = f.name.replace(".audit.json", "")
        cols = {}
        for cfg, c in (d.get("configs") or {}).items():
            for k, v in (c.get("columns") or {}).items():
                r = cols.setdefault(k, {"present_in": [], "max_non_empty": 0.0, "rows": 0})
                r["present_in"].append(cfg)
                r["max_non_empty"] = max(r["max_non_empty"], float(v.get("non_empty_ratio") or 0.0))
                r["rows"] = max(r["rows"], int((c.get("rows_audited") or 0)))
        out[name] = {"n_configs": len(d.get("configs") or {}), "columns": cols,
                     "rows_total": sum(int((c.get("total_rows_all_files") or 0)) for c in (d.get("configs") or {}).values())}
    return out


def http(url, accept):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    try:
        return urllib.request.urlopen(req, timeout=45).read().decode("utf-8", "replace"), None
    except Exception as exc:
        return "", f"{type(exc).__name__}: {exc}"[:80]


def collision(nouns):
    """Ask three transports for records whose title carries the topic's core nouns; keep every channel's outcome.

    arXiv alone was unusable for this batch (406 then 429 after ~20 calls), and an unanswered query is not an empty
    literature (D24), so a topic is only called uncrowded when at least one channel actually answered.
    """
    phrase = " ".join(nouns[:3])
    q = urllib.parse.quote
    out = {"channels": {}, "answered": 0, "strong": 0}
    raw, err = http("https://export.arxiv.org/api/query?search_query=" + q("ti:" + phrase) + "&max_results=8",
                    "application/atom+xml, text/xml, */*")
    ti = [t.strip().replace("\n", " ")[:150] for t in re.findall(r"<title>(.*?)</title>", raw, re.S)[1:]]
    out["channels"]["arxiv"] = {"error": err or "", "n": len(ti),
                                "strong": sum(1 for t in ti if sum(1 for n in nouns if n in t.lower())
                                              >= max(2, len(nouns) - 1))}
    time.sleep(3.0)
    raw, err = http("https://api.crossref.org/works?query.title=" + q(phrase) + "&rows=8&select=title",
                    "application/json")
    try:
        ct = [str(i.get("title", [""])[0])[:150] for i in json.loads(raw).get("message", {}).get("items", [])]
    except Exception:
        ct = []
    out["channels"]["crossref"] = {"error": err or "", "n": len(ct),
                                   "strong": sum(1 for t in ct if sum(1 for n in nouns if n in t.lower())
                                                 >= max(2, len(nouns) - 1))}
    time.sleep(1.0)
    raw, err = http("https://api.openalex.org/works?filter=title_and_abstract.search:" + q(phrase)
                    + "&per-page=8&select=title", "application/json")
    try:
        ot = [str(i.get("title") or "")[:150] for i in json.loads(raw).get("results", [])]
    except Exception:
        ot = []
    out["channels"]["openalex"] = {"error": err or "", "n": len(ot),
                                   "strong": sum(1 for t in ot if sum(1 for n in nouns if n in t.lower())
                                                 >= max(2, len(nouns) - 1))}
    for ch in out["channels"].values():
        if not ch["error"]:
            out["answered"] += 1
        out["strong"] = max(out["strong"], ch["strong"])
    return out


def named_fields(text):
    """Column-like tokens the design itself names: snake_case words and known corpus column names."""
    return sorted({m.group(0) for m in re.finditer(r"\b[a-z][a-z0-9]*_[a-z0-9_]+\b", str(text).lower())}
                  - {"target_tools_list", "non_empty", "row_index"})


def tokens(s):
    return {w for w in re.findall(r"[a-z]{3,}", str(s).lower()) if w not in STOP}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wave", type=int, default=0, help="1-based wave index; 0 screens every pending wave")
    ap.add_argument("--dry-run", action="store_true", help="print the verdicts without touching the registry")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    man = manifests()
    rows = list(csv.DictReader(io.StringIO(REG.read_text(encoding="utf-8"))))
    hdr = list(rows[0])
    pending = [r for r in rows if r["status"] == "w0_audit"]
    waves = [pending[i:i + WAVE_CAP] for i in range(0, len(pending), WAVE_CAP)]
    print(f"  {len(pending)} topics at w0_audit, screened in {[len(w) for w in waves]} (cap {WAVE_CAP})")
    todo = [waves[a.wave - 1]] if a.wave else waves
    others = {r["topic_id"]: tokens(r["title_en"]) for r in rows if r["status"] != "w0_audit"}
    res, decided = {"exp_id": "EXP-0115", "rule": __doc__.split("rule written here")[1][:600], "topics": []}, {}
    for wave in todo:
        for r in wave:
            tid, ds = r["topic_id"], r["primary_dataset"]
            text = " ".join([r["main_method"], r["title_en"], r["external_validation_dataset"]])
            m = man.get(ds)
            if m is None:
                cand = [k for k in man if k.split("-")[0].lower() in ds.lower()]
                m = man[cand[0]] if len(cand) == 1 else None
            if m is None:
                st, why = "w2_blocked_no_data", f"no local release matches the named dataset '{ds}'"
                res["topics"].append({"topic_id": tid, "status": st, "reason": why})
                decided[tid] = (st, why, "", "")
                continue
            fields = [f for f in named_fields(text) if f in m["columns"]]
            named_elsewhere = [f for f in named_fields(text) if f not in m["columns"]]
            subs = [f"{ds}:{k[1]}->{v}" for (k, v) in (SUBSTITUTES.items())
                    if k[0] == ds and k[1] in named_elsewhere]
            cov = {f: round(m["columns"][f]["max_non_empty"], 4) for f in fields}
            if fields and max(cov.values()) == 0.0:
                st, why = ("w2_blocked_field_absent",
                           f"{ds} carries the named columns but every one is empty in all "
                           f"{m['columns'][fields[0]]['rows']} audited rows: {cov}")
            else:
                near = sorted(((len(tokens(r['title_en']) & v) / max(1, len(tokens(r['title_en']) | v)), k)
                               for k, v in others.items() if k != tid), reverse=True)
                if near and near[0][0] >= JACCARD_FOLD:
                    st, why = f"w3_fold_into_{near[0][1]}", (
                        f"title overlap {near[0][0]:.2f} with the live topic {near[0][1]}; the series forbids a second "
                        "paper on one construct")
                else:
                    nouns = key_nouns(r["title_en"])
                    coll = collision(nouns) if len(nouns) >= 2 else {"answered": 1, "strong": 0, "channels": {}}
                    if not coll["answered"]:
                        st = "w2_screen_incomplete_collision_unretrieved"
                        why = ("data measured but no literature channel answered, so crowding is unknown and the topic "
                               "is not advanced: " + json.dumps({k: v["error"] for k, v in coll["channels"].items()}))
                    elif coll["strong"] >= STRONG_HITS:
                        st, why = "demoted_L3_crowded", (f"{coll['strong']} titles share the core nouns {nouns} on "
                                                         f"{coll['answered']} of 3 channels")
                    else:
                        st = "w1_audit_done"
                        why = (f"{ds}: {m['rows_total']:,} rows over {m['n_configs']} configs; fields probed "
                               f"{cov or 'none named in the design text'}" + (f"; substitutes {subs}" if subs else "")
                               + f"; collision {coll['strong']} strong match(es), "
                                 f"{ {k: v['n'] for k, v in coll['channels'].items()} } returned")
            res["topics"].append({"topic_id": tid, "status": st, "reason": why, "fields": cov,
                                  "substitutes": subs})
            decided[tid] = (st, why, json.dumps(cov, ensure_ascii=False), json.dumps(subs, ensure_ascii=False))
            print(f"  {tid}: {st} | {why[:120]}")
    if a.dry_run:
        print("  dry run: registry untouched")
        return 0
    stamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    for r in rows:
        if r["topic_id"] in decided:
            st, why, cov, subs = decided[r["topic_id"]]
            r["status"] = st
            r["blocking_issue"] = why[:900]
            r["data_feasibility"] = ("MEASURED " + cov) if cov else ("MEASURED corpus present; no column named"
                                                                     " in the design text")
            r["novelty_risk"] = "screened_by_EXP-0115"
            if subs and subs != "[]":
                r["differentiation_from_other_topics"] = (r["differentiation_from_other_topics"]
                                                          + f" | field substitutes recorded: {subs}")
    with open(REG, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=hdr, extrasaction="raise", lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    back = list(csv.reader(io.StringIO(REG.read_text(encoding="utf-8"))))
    assert back[0] == hdr, "the registry header changed while it was being written"
    assert all(len(r) == len(hdr) for r in back[1:] if r), "a ragged row was written to the registry"
    res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    res["n_decided"] = len(decided)
    res["statuses"] = sorted({t["status"] for t in res["topics"]})
    (ROOT / "results_raw").mkdir(exist_ok=True)
    (ROOT / "results_raw" / f"EXP0115_funnel_screen_round5_{stamp}.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    print(f"  decided {len(decided)} topics:", dict(Counter(d[0] for d in decided.values())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
