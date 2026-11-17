"""EXP-0226: put the error-category shares P001 quotes into a table it ships.

`paper.md`, `limitations.md`, `reviewer_attack.md` and deviation D33 all quote shares of the form "R1 accounts for
0.6491 of true positives but only 0.3885 of false negatives". They are true - every one of them recomputes from the
shipped census, `results_processed/EXP0093_error_census.csv` - but no file in the package states them, so a reader
can only take the prose's word for an aggregation over 1,596 rows. The round-2 number-provenance pass flagged
exactly that: a figure in a sentence with no artefact behind it.

This writes the aggregation itself: per `kind`, the count and share of each category, plus the rule-covered share
(1 - R6) the paper calls 0.7868. It also checks each value against the sentence it came from and refuses to write a
table whose numbers disagree with the text that motivated it.

    python 02_shared_code/data_audit/p001_census_shares.py [--selftest]
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
PKG = ROOT / "papers" / "P001_routing_failure_qpp"
RAW = ROOT / "results_raw"
PROC = ROOT / "results_processed"
CENSUS = PKG / "results_processed" / "EXP0093_error_census.csv"
EXP = "EXP-0226"
# the figures P001's prose states, so the table is checked against the sentences rather than beside them
QUOTED = {"R1 no_lexical_bridge": {"FN": 0.3885, "TP": 0.6491},
          "R2 crowded_catalogue": {"FN": 0.3507},
          "R6 other": {"FN": 0.2132}}
RULE_COVERED_OF_FN = 0.7868


def shares(rows: list) -> dict:
    out = {}
    kinds = {}
    for r in rows:
        kinds.setdefault(r["kind"], []).append(r["category"])
    for kind, cats in kinds.items():
        n = len(cats)
        out[kind] = {"n": n, "by_category": {c: round(cats.count(c) / n, 4) for c in sorted(set(cats))},
                     "rule_covered_share": round(1 - cats.count("R6 other") / n, 4)}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if a.selftest:
        rows = [{"kind": "FN", "category": "R6 other"}, {"kind": "FN", "category": "R1 no_lexical_bridge"},
                {"kind": "FN", "category": "R1 no_lexical_bridge"}, {"kind": "TP", "category": "R6 other"}]
        s = shares(rows)
        ok = s["FN"]["by_category"]["R1 no_lexical_bridge"] == 0.6667 and s["FN"]["n"] == 3 \
            and s["TP"]["rule_covered_share"] == 0.0
        print("selftest:", "PASS" if ok else json.dumps(s))
        return 0 if ok else 1
    rows = list(csv.DictReader(io.StringIO(CENSUS.read_text(encoding="utf-8-sig"))))
    s = shares(rows)
    bad = []
    for cat, per_kind in QUOTED.items():
        for kind, want in per_kind.items():
            got = s[kind]["by_category"].get(cat)
            if got is None or abs(got - want) > 0.0002:
                bad.append(f"{kind}/{cat}: paper says {want}, census gives {got}")
    if abs(s["FN"]["rule_covered_share"] - RULE_COVERED_OF_FN) > 0.0002:
        bad.append(f"FN rule-covered: paper says {RULE_COVERED_OF_FN}, census gives {s['FN']['rule_covered_share']}")
    if bad:
        raise SystemExit("ABORT: the prose and the census disagree, so neither may be shipped as is:\n  " +
                         "\n  ".join(bad))
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["kind", "n", "category", "share", "source_row_count"])
    for kind in sorted(s):
        for cat in sorted(s[kind]["by_category"]):
            w.writerow([kind, s[kind]["n"], cat, s[kind]["by_category"][cat],
                        round(s[kind]["by_category"][cat] * s[kind]["n"])])
        w.writerow([kind, s[kind]["n"], "rule_covered(R1..R5)", s[kind]["rule_covered_share"], ""])
    PROC.mkdir(exist_ok=True)
    stem = "EXP0093_category_shares.csv"
    (PKG / "results_processed" / stem).write_text(buf.getvalue(), encoding="utf-8")
    (PROC / stem).write_text(buf.getvalue(), encoding="utf-8")
    art = {"exp_id": EXP, "seed": 42, "census_rows": len(rows), "shares": s,
           "checked_against_prose": {"quoted": QUOTED, "rule_covered_of_FN": RULE_COVERED_OF_FN,
                                     "all_matched": True},
           "wrote": [str(PKG / "results_processed" / stem), str(PROC / stem)],
           "not_reproduced_from_this_census": ["the 0.4919 figure in D33/limitations is a share of no-bridge rows "
                                               "whose task succeeded, a different quantity from TP/FN kind here"],
           "invocation": " ".join([sys.executable] + sys.argv)}
    import time
    import datetime
    art["started_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    p = RAW / f"{EXP.replace('-', '')}_census_category_shares_{time.strftime('%Y%m%dT%H%M%S')}.json"
    p.write_text(json.dumps(art, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {p.name} and {stem}; every quoted share matched the census")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
