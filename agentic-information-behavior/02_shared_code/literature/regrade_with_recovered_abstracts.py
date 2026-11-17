"""EXP-0064: merge the recovered abstracts back in and re-run the FROZEN grading rule on the fuller corpus.

EXP-0057's rule is not rewritten here - it is imported and executed with its input/output paths redirected, so the
only thing that can change a grade is the newly available abstract text. The v1 artefacts stay on disk untouched:
this writes `literature_abstracts_v2.csv`, `literature_graded_v2.csv` and a v2 hand-check list, plus a delta file
that states which records moved and which did not, because "we recovered more abstracts" is only a contribution if
the grade distribution is reported before and after.

    python regrade_with_recovered_abstracts.py
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
import grade_collisions as GC  # noqa: E402  - the frozen rule, imported not copied

ROOT = HERE.parents[1]
REG = ROOT / "00_program_registry"
V1 = REG / "literature_abstracts.csv"
S2 = REG / "literature_abstracts_s2.csv"
V2 = REG / "literature_abstracts_v2.csv"
GRADED_V1 = REG / "literature_graded.csv"
GRADED_V2 = REG / "literature_graded_v2.csv"
REVIEW_V2 = ROOT / "docs" / f"literature_grading_review_v2_{time.strftime('%Y%m%d')}.md"
OUT_JSON = REG / "EXP0064_regrade_delta.json"


def read(p):
    return list(csv.DictReader(io.StringIO(pathlib.Path(p).read_text(encoding="utf-8"))))


def write_csv(path, rows, fields):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\r\n", extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    pathlib.Path(path).write_text(buf.getvalue(), encoding="utf-8", newline="")


def main() -> int:
    for p in (V1, S2, GRADED_V1):
        if not p.exists():
            raise SystemExit(f"[e64] ABORT: {p.name} missing; run EXP-0056/0057/0063 first.")
    v1 = read(V1)
    for i, r in enumerate(v1):                       # same record key as EXP-0063: position + cite_key
        r["row_key"] = f"{i:04d}|{r['cite_key']}"
    s2 = {r["row_key"]: r for r in read(S2)}
    fields = list(v1[0].keys()) + ["abstract_source"]
    merged, n_filled = [], 0
    assert all(r["row_key"].count("|") == 1 for r in v1)
    for r in v1:
        rec = dict(r)
        rec["abstract_source"] = "crossref_or_arxiv" if r["abstract"].strip() else "none"
        got = s2.get(r["row_key"])
        if not r["abstract"].strip() and got and (got.get("abstract") or "").strip():
            if got.get("attempted_via") == "title_search" and got.get("status") != "informative":
                pass                                   # a fuzzy match never supplies text a grade is based on
            else:
                rec["abstract"] = got["abstract"].strip()
                rec["abstract_present"] = "1"
                rec["abstract_source"] = "semanticscholar_" + got.get("attempted_via", "?")
                n_filled += 1
        merged.append(rec)
    write_csv(V2, merged, fields)          # V2 keeps row_key and abstract_source alongside the frozen columns
    print(f"[e64] merged: {n_filled} previously title-only records now carry abstract text", flush=True)

    before_rows = read(GRADED_V1)
    GC.SRC, GC.OUTCSV, GC.REVIEW = V2, GRADED_V2, REVIEW_V2
    GC.main()
    after_rows = read(GRADED_V2)
    # No column of these tables is unique (paper_id names the PAPER; cite_key repeats for 8 records), so the two
    # graded tables are aligned by position and that alignment is asserted, not assumed: the grader walks the
    # abstracts file in order and emits one row per record. Keying on paper_id collapsed 287 records into 5 and
    # made the first version of this delta meaningless.
    if len(before_rows) != len(after_rows):
        raise SystemExit(f"[e64] ABORT: graded v1 has {len(before_rows)} rows, v2 has {len(after_rows)}; the grader "
                         "did not emit one row per record, so the delta cannot be keyed by position.")
    for b, a in zip(before_rows, after_rows):
        if (b["paper_id"], b["cite_key"], b["title"]) != (a["paper_id"], a["cite_key"], a["title"]):
            raise SystemExit(f"[e64] ABORT: positional alignment broken at {b['cite_key']!r} vs {a['cite_key']!r}")
    print(f"[e64] {len(before_rows)} graded records aligned positionally and asserted", flush=True)
    before, after = dict(enumerate(before_rows)), dict(enumerate(after_rows))

    moved = [{"row_index": k, "paper_id": after[k]["paper_id"], "cite_key": after[k]["cite_key"],
              "title": after[k]["title"][:120], "collision_target": after[k]["collision_target"],
              "rule_before": before[k]["level_rule"], "rule_after": after[k]["level_rule"],
              "graded_on_before": before[k]["graded_on"], "graded_on_after": after[k]["graded_on"],
              "abstract_source": merged[k]["abstract_source"]}
             for k in after if before[k]["level_rule"] != after[k]["level_rule"]]
    up = [m for m in moved if int(m["rule_after"][1]) > int(m["rule_before"][1])]
    res = {"exp_id": "EXP-0064", "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "records": {"v1": len(before), "v2": len(after), "abstracts_recovered_by_e63": n_filled,
                       "graded_on_title_only_before": sum(r["graded_on"] == "title_only" for r in before.values()),
                       "graded_on_title_only_after": sum(r["graded_on"] == "title_only" for r in after.values())},
           "grade_dist_before": {lvl: sum(1 for r in before.values() if r["level_rule"] == lvl)
                                 for lvl in ("L0", "L1", "L2", "L3", "L4")},
           "grade_dist_after": {lvl: sum(1 for r in after.values() if r["level_rule"] == lvl)
                                for lvl in ("L0", "L1", "L2", "L3", "L4")},
           "hand_check_before": sum(int(r["needs_hand_check"]) for r in before.values()),
           "hand_check_after": sum(int(r["needs_hand_check"]) for r in after.values()),
           "n_rule_changed": len(moved), "n_changed_upwards": len(up), "changed": moved,
           "rule_reused_verbatim": "grade_collisions.grade() imported, not copied",
           "v1_artefacts_left_untouched": [V1.name, GRADED_V1.name]}
    OUT_JSON.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8", newline="")
    print(json.dumps({k: v for k, v in res.items() if k != "changed"}, indent=1), flush=True)
    for m in moved[:25]:
        print(f"  {m['paper_id']} {m['rule_before']}->{m['rule_after']} "
              f"{m['graded_on_before']}->{m['graded_on_after']} via {m['abstract_source']} | {m['title'][:70]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
