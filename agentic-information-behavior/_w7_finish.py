"""Drive the rest of wave 7 end to end: grade the harvest, assemble the six packages, run each package's chain,
register the experiments, rebuild the registries and re-run both estate audits.

Every step is a subprocess of the shipped script, in the order the programme's own reproduce.sh uses, and a nonzero
rc stops the run with the step named - because a package assembled after a failed grading step would carry a
literature matrix from the previous generation and still look complete.

    python _w7_finish.py [--from grade]
"""
from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent
PY = sys.executable
PACKAGES = ["P039", "P040", "P041", "P042", "P043", "P044"]
CHAIN = ["writing/export_figure_plan.py", "writing/embed_paper_artefacts.py",
         "registry/export_package_registry.py", "registry/build_package_configs_readme.py",
         "registry/reconcile_package_evidence.py"]
ORDER = ["grade", "record", "assemble", "chain", "registry", "audits"]


def run(args, log) -> int:
    print("+", " ".join(args), flush=True)
    with open(log, "a", encoding="utf-8") as fh:
        p = subprocess.run([PY, "-u"] + args, stdout=fh, stderr=subprocess.STDOUT, cwd=str(ROOT))
    return p.returncode


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", default="grade")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    log = ROOT / "logs" / "w7_finish.log"
    start = ORDER.index(a.start)
    fails = []
    t0 = time.time()

    if start <= 0:
        for p in PACKAGES:
            rc = run([f"02_shared_code/literature/grade_wave_literature.py", "--paper", p], log)
            if rc:
                fails.append(f"grade {p} rc={rc}")
    if start <= 1 and not fails:
        # the recorder first: every package's `table7_experiment_provenance.csv` is read out of
        # 00_program_registry/experiment_registry.csv, so assembling before registering ships an empty register
        rc = run(["02_shared_code/registry/record_wave7.py"], log)
        if rc:
            fails.append(f"record rc={rc}")
    if start <= 2 and not fails:
        rc = run(["02_shared_code/package_factory/wave_package.py", "--designs", "topic_designs_wave7", "--all"], log)
        if rc:
            fails.append(f"assemble rc={rc}")
    if start <= 3 and not fails:
        for p in PACKAGES:
            for s in CHAIN:
                rc = run([f"02_shared_code/{s}", "--paper", p], log)
                if rc and "embed_paper_artefacts" not in s:
                    fails.append(f"{p} {s} rc={rc}")
    if start <= 4 and not fails:
        for s in ("registry/build_topic_registry.py", "registry/build_topic_evidence.py"):
            if (ROOT / "02_shared_code" / s).is_file():
                rc = run([f"02_shared_code/{s}"], log)
                if rc:
                    fails.append(f"{s} rc={rc}")
    if start <= 5 and not fails:
        for s in ("registry/package_audit.py", "registry/spec_completion_audit.py"):
            rc = run([f"02_shared_code/{s}"], log)
            if rc:
                fails.append(f"{s} rc={rc}")
    print(f"wallclock {round(time.time() - t0, 1)}s")
    print("FAILS:", fails or "none")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
