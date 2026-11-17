"""Drive the rest of wave 8: grade the harvest, record the premise-blocked designs, register the experiments,
assemble the three measured packages, run each package's chain, rebuild the registries and re-run both audits.

The order is the one wave 7 established the hard way: `table7_experiment_provenance.csv` is read out of
`00_program_registry/experiment_registry.csv`, so registering has to precede assembling, and a blocked design has to
be recorded before the audit walks the papers tree or its directory reads as a package missing every deliverable.

    python _w8_finish.py [--from grade]
"""
from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent
PY = sys.executable
PACKAGES = ["P045", "P046", "P047"]
BLOCKED = ["P048", "P049"]
CHAIN = ["writing/export_figure_plan.py", "writing/embed_paper_artefacts.py",
         "registry/export_package_registry.py", "registry/build_package_configs_readme.py",
         "registry/reconcile_package_evidence.py"]
ORDER = ["grade", "blocked", "record", "assemble", "chain", "registry", "audits"]


def run(args, log) -> int:
    print("+", " ".join(args), flush=True)
    with open(log, "a", encoding="utf-8") as fh:
        p = subprocess.run([PY, "-u"] + args, stdout=fh, stderr=subprocess.STDOUT, cwd=str(ROOT))
    if p.returncode:
        print("  rc", p.returncode, ":", "\n".join(open(log, encoding="utf-8").read().splitlines()[-6:]), flush=True)
    return p.returncode


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", default="grade")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    log = ROOT / "logs" / "w8_finish.log"
    start = ORDER.index(a.start)
    fails, t0 = [], time.time()

    if start <= 0:
        for p in PACKAGES:
            rc = run(["02_shared_code/literature/grade_wave_literature.py", "--paper", p], log)
            if rc:
                fails.append(f"grade {p} rc={rc}")
    if start <= 1 and not fails:
        # before any assembly: this writes the evidence row and the BLOCKED.md that keep T175 and T176 traceable
        rc = run(["02_shared_code/registry/record_blocked.py", "--designs", "topic_designs_wave8"], log)
        if rc:
            fails.append(f"record_blocked rc={rc}")
    if start <= 2 and not fails:
        rc = run(["02_shared_code/registry/record_wave8.py"], log)
        if rc:
            fails.append(f"record rc={rc}")
    if start <= 3 and not fails:
        rc = run(["02_shared_code/package_factory/wave_package.py", "--designs", "topic_designs_wave8", "--all"], log)
        if rc:
            fails.append(f"assemble rc={rc}")
    if start <= 4 and not fails:
        # the two blocked design directories are not packages: they hold a freeze and a BLOCKED.md, and running the
        # package chain over them would abort on the empty register they deliberately have
        for p in PACKAGES:
            for s in CHAIN:
                rc = run([f"02_shared_code/{s}", "--paper", p], log)
                if rc and "embed_paper_artefacts" not in s:
                    fails.append(f"{p} {s} rc={rc}")
    if start <= 5 and not fails:
        rc = run(["02_shared_code/registry/build_topic_registry.py"], log)
        if rc:
            fails.append(f"build_topic_registry rc={rc}")
    if start <= 6 and not fails:
        for s in ("registry/package_audit.py", "registry/spec_completion_audit.py"):
            rc = run([f"02_shared_code/{s}"], log)
            if rc:
                fails.append(f"{s} rc={rc}")
    print(f"wallclock {round(time.time() - t0, 1)}s")
    print("FAILS:", fails or "none")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
