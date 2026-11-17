"""Report the fill state of topic_registry.csv for the 86 intake topics and estate-wide.

The six disposition columns are the ones the objective requires: status, package, exp_ids,
measured_coverage, figures_tables, collision_verdict. A blank is only acceptable when the row's
status says no experiment was run for it (a literature demotion or a fold), which this script
checks rather than assumes.
"""
from __future__ import annotations

import csv
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = pathlib.Path(__file__).resolve().parent
COLS = ["status", "package", "exp_ids", "measured_coverage", "figures_tables", "collision_verdict"]
RUN = re.compile(r"packaged|package_complete|_main_done|blocked_premise|premise|pilot|prose_only")

rows = list(csv.DictReader((ROOT / "00_program_registry" / "topic_registry.csv").open(encoding="utf-8-sig")))
by_id = {r["topic_id"]: r for r in rows}
intake = [f"T{n:03d}" for n in list(range(101, 143)) + list(range(151, 195))]

missing = {c: [] for c in COLS}
bad = []
for t in intake:
    r = by_id.get(t)
    if r is None:
        bad.append(t + ":ABSENT_FROM_REGISTRY")
        continue
    for c in COLS:
        if not (r.get(c) or "").strip():
            missing[c].append(t)
    # a row that claims a measurement must carry its experiment ids
    if RUN.search(r["status"]) and not (r["exp_ids"] or "").strip():
        bad.append(t + ":status_claims_a_run_but_exp_ids_blank")

print(f"intake topics covered: {len(intake)}  rows found: {sum(1 for t in intake if t in by_id)}")
for c in COLS:
    print(f"  blank {c:18s}: {len(missing[c])}" + (f"  {sorted(missing[c])}" if missing[c] else ""))
print("inconsistent:", bad or "none")

# estate-wide: the 37 non-intake rows, grouped by whether they ever ran anything
other = [r for r in rows if r["topic_id"] not in intake]
ran = [r for r in other if RUN.search(r["status"] or "")]
never = [r for r in other if not RUN.search(r["status"] or "")]
print(f"other rows: {len(other)} (of which status says something was run: {len(ran)}; "
      f"decision-only rows: {len(never)})")
for label, group in (("ran", ran), ("decision-only", never)):
    gaps = {c: sum(1 for r in group if not (r.get(c) or "").strip()) for c in COLS}
    print(f"  {label}: blank counts {gaps}")
print("\nblank exp_ids among decision-only rows:",
      sorted(r["topic_id"] for r in never if not (r.get("exp_ids") or "").strip()) or "none")
print("blank package among decision-only rows:",
      sorted(r["topic_id"] for r in never if not (r.get("package") or "").strip()) or "none")
