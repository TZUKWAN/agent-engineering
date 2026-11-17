"""Do the 86 intake rows still carry intake placeholders ("pending ...") after their decision?

Placeholders are not blanks, so the blank census misses them. This counts, per column, how many intake rows
still hold the round-5 intake wording or an explicit "pending".
"""
from __future__ import annotations

import csv
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = pathlib.Path(__file__).resolve().parent
INTAKE = [f"T{n:03d}" for n in list(range(101, 143)) + list(range(151, 195))]
rows = {r["topic_id"]: r for r in
        csv.DictReader((ROOT / "00_program_registry" / "topic_registry.csv").open(encoding="utf-8-sig"))}
PEND = re.compile(r"pending|see the supplied design|w0_audit", re.I)
for col in ("core_rq_h", "data_feasibility", "novelty_risk", "theory_basis", "blocking_issue",
            "primary_dv", "primary_iv", "status", "compute_cost", "expected_venue"):
    hits = [t for t in INTAKE if PEND.search((rows[t].get(col) or "")) or not (rows[t].get(col) or "").strip()]
    print(f"{col:18s} placeholder_or_blank={len(hits):3d}  e.g. {hits[:8]}")
print("\nsample packaged row T155:")
for k, v in rows["T155"].items():
    print(f"  {k:32s} {(v or '')[:120]}")
