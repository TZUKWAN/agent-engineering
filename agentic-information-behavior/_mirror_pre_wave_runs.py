"""Mirror each pre-wave package's declared runs into that package (P001-P005).

`_reassemble_all_waves.py` rebuilds the wave packages, and `wave_package.mirror_evidence` now copies every run a
package's own register declares; the five hand-assembled packages predate both, so they keep the defect the round-2
pass counted - a row in `papers/P001_.../experiment_registry.csv` for a run whose artefact nobody can open inside
the package. This does for them what the factory does for the rest: byte-for-byte copies of the kept generation of
each declared run, nothing renamed, nothing rewritten, and no file removed.

    python _mirror_pre_wave_runs.py [--apply]
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "02_shared_code" / "package_factory"))
import wave_package as WP                                               # noqa: E402

PRE = ("P001_", "P002_", "P003_", "P004_", "P005_")
PROGRAM = ROOT / "00_program_registry"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    reg = list(csv.DictReader(io.StringIO((PROGRAM / "experiment_registry.csv").read_text(encoding="utf-8"))))
    total = 0
    for pkg in sorted(p for p in (ROOT / "papers").iterdir() if p.is_dir() and p.name.startswith(PRE)):
        pid = pfx = pkg.name[:4]
        declared = [r for r in reg if pid in [x.strip() for x in (r.get("paper_id") or "").split(";")]]
        have = {f.name for f in (pkg / "results_raw").iterdir()} | \
               {f.name for f in (pkg / "results_processed").iterdir() if (pkg / "results_processed").is_dir()}
        added = []
        for r in declared:
            for f in WP._run_artefacts(r.get("exp_id") or "", r.get("outputs") or ""):
                if f.name in have:
                    continue
                if not a.apply:
                    added.append(f"{r['exp_id']}:{f.name}")
                    continue
                dest = pkg / ("results_processed" if "results_processed" in f.parts else "results_raw") / f.name
                dest.parent.mkdir(exist_ok=True)
                dest.write_bytes(f.read_bytes())
                have.add(f.name)
                added.append(f"{r['exp_id']}:{f.name}")
        total += len(added)
        print(f"{pkg.name[:42]:42s} declared={len(declared):3d} mirrored_now={len(added):3d} "
              f"{'(dry run)' if not a.apply else ''}")
        for x in added[:6]:
            print("    +", x[:130])
    print(f"\n{total} artefact copies {'to make' if not a.apply else 'made'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
