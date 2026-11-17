"""EXP-0066: read what EXP-0065 retrieved. 439 of its 552 records arrived without abstract text.

The expansion pass kept candidates on a title plus a container title, so most rows entered the frozen grading rule as
title-only - which the rule scores L0/L1 by construction, never L2+. That is a property of the input, not a finding
about the literature, and it must not be reported as "no collision found". This step fills the missing abstracts from
the Semantic Scholar batch endpoint (proven to hold text for Crossref DOIs by EXP-0063, which recovered 30 of 94) and
then re-runs the same imported rule, so the grade distribution is read from records that were actually readable.

Fixed before the first request:
  * only rows with `abstract_chars == 0` and a DOI are queried; nothing already read is re-graded from a different
    text;
  * a filled abstract is accepted only when the index's title agrees with ours on at least 6 content tokens, so a
    wrong record can never supply the text a collision grade is based on;
  * the output is a new file; EXP-0065's artefact stays on disk as the record of what was retrieved;
  * per-row status is kept (`informative` / `all_null` / `transport_error`), because the residue is the honest part
    of the result.

    python fill_expansion_abstracts.py
"""
from __future__ import annotations

import csv
import io
import json
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from fetch_abstracts_s2 import post, tokens          # noqa: E402 - the transport EXP-0063 was validated with
from grade_collisions import grade                    # noqa: E402 - the frozen rule, imported not copied

ROOT = HERE.parents[1]
REG = ROOT / "00_program_registry"
SRC = REG / "literature_p001_expansion.csv"
OUT = REG / "literature_p001_expansion_v2.csv"
SUM = ROOT / "results_raw" / f"EXP0066_expansion_abstracts_{time.strftime('%Y%m%dT%H%M%S')}.json"
BATCH = 50
MIN_SHARED = 6


def norm_title(s: str) -> str:
    return " ".join(s.lower().split())


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    rows = list(csv.DictReader(io.StringIO(SRC.read_text(encoding="utf-8"))))
    need = [r for r in rows if not int(r["abstract_chars"] or 0) and r["doi"]]
    print(f"EXP-0066 | {len(rows)} expanded records, {len(need)} lack abstract text and carry a DOI", flush=True)

    t0 = time.time()
    text, status = {}, {}
    sids = sorted({"DOI:" + r["doi"] for r in need})
    for bi in range(0, len(sids), BATCH):
        chunk = sids[bi:bi + BATCH]
        res, err = post(chunk)
        if res is None:
            print(f"  batch {bi // BATCH + 1}: transport_error {err}", flush=True)
            for s in chunk:
                status[s] = "transport_error"
            continue
        got = 0
        for sid, rec in zip(chunk, res):
            if not rec:
                status[sid] = "all_null"
                continue
            ab = (rec.get("abstract") or "").strip()
            if not ab:
                status[sid] = "known_without_abstract"
                continue
            got += 1
            status[sid] = "informative"
            text[sid] = (ab, rec.get("title") or "")
        print(f"  batch {bi // BATCH + 1}: {got}/{len(chunk)} ids returned abstract text "
              f"({round(time.time() - t0)}s)", flush=True)
        time.sleep(1.2)

    filled = rejected = 0
    for r in rows:
        sid = "DOI:" + r["doi"] if r["doi"] else ""
        r["abstract_source"] = "retrieved" if int(r["abstract_chars"] or 0) else "none"
        r["s2_status"] = status.get(sid, "not_queried")
        if sid in text:
            ab, s2t = text[sid]
            if len(tokens(s2t) & tokens(r["title"])) < MIN_SHARED:
                r["s2_status"] = "title_mismatch_rejected"
                rejected += 1
            else:
                r["abstract"] = ab
                r["abstract_chars"] = str(len(ab))
                r["abstract_source"] = "semanticscholar"
                lvl, hit, n = grade("P001", r["title"], ab)
                r["level_before_fill"] = r["level_rule"]
                r["level_rule"] = lvl
                r["matched"] = json.dumps(hit, ensure_ascii=False)
                filled += 1
        if int(r["abstract_chars"] or 0):
            lvl, hit, n = grade("P001", r["title"], r["abstract"])
            r["level_rule"] = lvl
            r["matched"] = json.dumps(hit, ensure_ascii=False)

    fields = list(rows[0].keys())
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\r\n", extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    OUT.write_text(buf.getvalue(), encoding="utf-8", newline="")

    dist = {}
    for r in rows:
        dist[r["level_rule"]] = dist.get(r["level_rule"], 0) + 1
    moved = [{"title": r["title"][:120], "venue": r["venue"][:50], "year": r["year"], "community": r["community"],
              "before": r.get("level_before_fill", ""), "after": r["level_rule"]}
             for r in rows if r.get("level_before_fill") and r["level_before_fill"] != r["level_rule"]]
    res = {"exp_id": "EXP-0066", "src": SRC.name, "out": OUT.name, "records": len(rows),
           "needed_text": len(need), "ids_queried": len(sids), "filled": filled,
           "rejected_on_title_mismatch": rejected,
           "status_counts": {k: sum(1 for v in status.values() if v == k)
                             for k in ("informative", "all_null", "known_without_abstract", "transport_error")},
           "with_abstract_now": sum(1 for r in rows if int(r["abstract_chars"] or 0)),
           "grade_distribution_after": dist,
           "L2plus_after": sum(1 for r in rows if r["level_rule"] in ("L2", "L3", "L4")),
           "grade_changes": moved, "wallclock_sec": round(time.time() - t0, 1),
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t0)),
           "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    SUM.parent.mkdir(exist_ok=True)
    SUM.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8", newline="")
    print(json.dumps({k: v for k, v in res.items() if k != "grade_changes"}, indent=1), flush=True)
    for m in moved[:20]:
        print(f"  {m['before']}->{m['after']} [{m['community'][:12]}] {m['title'][:70]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
