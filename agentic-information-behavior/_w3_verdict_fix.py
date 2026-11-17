"""Apply the round-2 verdict fix to wave 3 and rebuild the four packages it feeds.

The second pass found rows whose printed verdict contradicts the interval shipped beside them (EXP-0145 H3,
EXP-0147 H1): the design sentence asks only that two arms *differ*, while the hand-rolled expression tested
`ci[0] > 0`, so an interval entirely below zero - real evidence of a difference - fell through to `null`, the word
the freeze reserves for an interval that covers zero. The expression also read a missing bound as zero.

This script runs the step exactly as the packages' `reproduce.sh` freezes it (all four designs, seed 42), re-reads
the artefacts into the registry, and re-assembles only the four packages whose numbers can move. It snapshots each
package's model table first and prints the verdict changes, so a number that moved without an explanation is
visible rather than buried.

    python _w3_verdict_fix.py [--apply]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "02_shared_code" / "package_factory"))
PY = ["py", "-3.11"]
TOPICS = ["T113", "T119", "T120", "T122"]
PKGS = {}


def run(*args) -> int:
    print("+", " ".join(args[:3]) + " ...")
    r = subprocess.run(PY + list(args), cwd=str(ROOT), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    tail = [l for l in (r.stdout + r.stderr).splitlines() if l.strip()]
    for l in tail[-6:]:
        print("   ", l[:180])
    return r.returncode


def t3(pkg_name: str):
    """The package's own main-models table; wave 3 does not all call it `table3_main_models.csv`."""
    d = next((p for p in (ROOT / "papers").glob(f"{pkg_name}_*")), None)
    f = next(iter(sorted((d / "tables").glob("table3_*.csv"))), None) if d else None
    return f


def rows_of(pkg_name: str):
    f = t3(pkg_name)
    if not f or not f.is_file():
        return {}
    return {(r.get("hypothesis") or "", r.get("term") or "")[:40]: (r.get("verdict") or "").strip()
            for r in csv.DictReader(io.StringIO(f.read_text(encoding="utf-8-sig")))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    import topic_designs_wave3 as M3                                    # noqa: E402
    for tid in TOPICS:
        PKGS[tid] = M3.DESIGNS[tid]["pkg"][:4]
    before = {tid: rows_of(pk) for tid, pk in PKGS.items()}
    digests = {tid: hashlib.sha256(t3(pk).read_bytes()).hexdigest()[:12] for tid, pk in PKGS.items()}
    print("before:", {t: (PKGS[t], digests[t]) for t in TOPICS})
    if not a.apply:
        print("(dry run; pass --apply to run the step, re-record and re-assemble)")
        return 0

    rc = run("02_shared_code/package_factory/exp_wave3_designs.py")
    if rc:
        return rc
    rc = run("02_shared_code/registry/record_wave3.py")
    if rc:
        return rc
    for tid in TOPICS:
        rc = run("02_shared_code/package_factory/wave_package.py", "--designs", "topic_designs_wave3",
             "--topic", tid, "--assemble-only")
        if rc:
            return rc
    for tid in TOPICS:
        after = rows_of(PKGS[tid])
        new = hashlib.sha256(t3(PKGS[tid]).read_bytes()).hexdigest()[:12]
        moved = {k: (before[tid].get(k), v) for k, v in after.items() if before[tid].get(k) != v}
        print(f"{tid} {PKGS[tid]}: digest {digests[tid]} -> {new}; verdict rows changed: "
              + (str(sorted(moved.items()))[:400] if moved else "none"))
    return 0


def json_dumps(o):
    import json
    return json.dumps(o, ensure_ascii=False)[:400]


if __name__ == "__main__":
    raise SystemExit(main())
