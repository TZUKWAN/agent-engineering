"""Which rows carry blanks in the intake-descriptive columns, and are they intake topics?"""
from __future__ import annotations

import csv
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = pathlib.Path(__file__).resolve().parent
INTAKE = set(f"T{n:03d}" for n in list(range(101, 143)) + list(range(151, 195)))
rows = list(csv.DictReader((ROOT / "00_program_registry" / "topic_registry.csv").open(encoding="utf-8-sig")))
for col in ("primary_dv", "primary_iv", "differentiation_from_other_topics", "novelty_risk",
            "data_feasibility", "blocking_issue", "theory_basis", "main_method", "paper_type"):
    b = [r["topic_id"] for r in rows if not (r.get(col) or "").strip()]
    print(f"{col:34s} blank={len(b):3d} intake={sum(1 for t in b if t in INTAKE):3d} -> {b[:12]}")
