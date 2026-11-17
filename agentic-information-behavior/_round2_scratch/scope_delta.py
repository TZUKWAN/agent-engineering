"""Scratch measurement: what does each scope-widening of the provenance checker actually surface?

The widened checker reads more documents (`round2_lib.package_docs`, which adds whatever a package ships outside the
fixed `DOCS` list) and more tables (every shipped summary CSV of 1-25 rows, not only its wide model tables). A
widening is only worth keeping if it finds something, so this runs both scopes over a slice of packages and reports
the findings that exist **only** because of the widening.

    py -3.11 _round2_scratch/scope_delta.py FIRST LAST
"""
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "02_shared_code" / "registry"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import round2_lib as L                                                     # noqa: E402
import round2_number_provenance as N                                       # noqa: E402

L.FROZEN = L.frozen_constants()
pkgs = L.packages()
lo, hi = int(sys.argv[1]), int(sys.argv[2])
tot = {"prose": 0, "prose_only_from_new_docs": 0, "cells": 0, "cells_only_from_summary_tables": 0,
       "docs_added": 0, "summary_tables_added": 0, "packages": 0}
t0 = time.time()


def nrows(f: pathlib.Path) -> int:
    try:
        return max(0, len(f.read_text(encoding="utf-8", errors="replace").splitlines()) - 1)
    except OSError:
        return 0


for i, pkg in enumerate(pkgs):
    if not (lo <= i < hi) or not (pkg / "paper.md").is_file():
        continue
    art, tbl, _src, groups, colsums, sibs = L.value_pool(pkg)
    pools = L.Pools(art, tbl, groups, colsums, sibs)
    prose = N.prose_numbers(pkg, pools)
    cells = N.table_numbers(pkg, pools)
    old_docs = set(L.DOCS)
    shipped = {str(f.relative_to(pkg)).replace(chr(92), "/") for f in pkg.rglob("*.md")}
    wide_tables = {f.name for f in sorted((pkg / "tables").glob("table*.csv"))
                   + sorted((pkg / "results_processed").glob("*.csv")) if nrows(f) > N.SUMMARY_ROW_CAP}
    added_docs = sorted(set(N.L.package_docs(pkg)) - old_docs)
    tot["prose"] += len(prose)
    tot["cells"] += len(cells)
    tot["prose_only_from_new_docs"] += sum(1 for x in prose if x["doc"] not in old_docs)
    tot["cells_only_from_summary_tables"] += sum(1 for x in cells if x["table"] not in wide_tables)
    tot["docs_added"] += len([d for d in added_docs if d in shipped or (pkg / d).is_file()])
    tot["summary_tables_added"] += len([f for f in N.printed_tables(pkg) if f.name not in wide_tables])
    tot["packages"] += 1
    for x in prose:
        print(f"[{i:2d}] {pkg.name[:38]:38s} PROSE {'NEW-DOC ' if x['doc'] not in old_docs else '        '}"
              f"{x['doc']}: {x['value']} :: {x['context'][:80]}", flush=True)
    for x in cells:
        print(f"[{i:2d}] {pkg.name[:38]:38s} CELL  {'SUMMARY ' if x['table'] not in wide_tables else '        '}"
              f"{x['table']}[{x['column']}] = {x['value']}", flush=True)
print(f"slice {lo}:{hi} ({tot['packages']} packages) in {time.time() - t0:.0f}s -> " + str(tot), flush=True)
