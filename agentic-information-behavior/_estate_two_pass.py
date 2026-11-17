"""The estate's closing check: rebuild every wave package a second time and prove the second state is the first.

Three passes in one command:

1. snapshot each `papers/P0*` directory with `rebuild_determinism.py --save`, which stores two hashes per file - the
   plain one and a second that strips dates, times and PDF creation stamps;
2. run `_reassemble_all_waves.py`, which re-assembles every package from the artefacts already in `results_raw/` and
   then re-runs each package's own chain (figure plan, embedded artefacts, registry extract, configs README, evidence
   reconciliation) - the steps a reader of `reproduce.sh` would exercise, driven from the shipped scripts rather than
   from a list kept here;
3. compare each directory against its snapshot and report per package how many files differ at all and how many differ
   in substance once every stamp is normalised away.

A removed file or an un-stamped added file is MATERIAL by the tool's own rule, so a section a generator stopped writing
cannot pass as a timestamp - with the one exception the tool states: a removed generation that the rebuild replaced
with a newer one of the same family carrying the same content apart from stamps is a rolling artefact, not a loss.
The heavy acquisition and fitting steps are deliberately not re-run: this checks that the
deliverables regenerate identically from the measurements that exist, which is the claim a rebuild makes.

    python _estate_two_pass.py
"""
from __future__ import annotations

import collections
import json
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent
PY = sys.executable
SNAPS = ROOT / "results_raw" / "snapshots_estate"
LOG = ROOT / "logs" / "estate_two_pass.log"


def run(args, log, label) -> int:
    log.write(f"+ {' '.join(str(a) for a in args)}\n")
    log.flush()
    p = subprocess.run([PY, "-u"] + list(args), cwd=str(ROOT), stdout=log, stderr=subprocess.STDOUT)
    if p.returncode:
        log.write(f"  !! {label} exited {p.returncode}\n")
        log.flush()
    return p.returncode


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    SNAPS.mkdir(parents=True, exist_ok=True)
    pkgs = sorted(p for p in (ROOT / "papers").glob("P0*") if p.is_dir())
    t0 = time.time()
    with open(LOG, "w", encoding="utf-8") as log:
        print(f"snapshotting {len(pkgs)} package directories", flush=True)
        for p in pkgs:
            rc = run(["02_shared_code/registry/rebuild_determinism.py", "--dir", f"papers/{p.name}",
                      "--save", f"results_raw/snapshots_estate/{p.name}.json"], log, f"snapshot {p.name}")
            if rc:
                print(f"  snapshot failed for {p.name}: rc={rc}", flush=True)
                return rc
        print("reassembling every wave and re-running every package chain (this is the slow part)", flush=True)
        rc = run(["_reassemble_all_waves.py"], log, "reassemble all waves")
        print(f"reassemble rc={rc}", flush=True)
        print("comparing the second state against the snapshot", flush=True)
        bad, changed = [], []
        summary = {}
        kinds = collections.Counter()
        for p in pkgs:
            out = log.name
            cp = subprocess.run([PY, "-u", "02_shared_code/registry/rebuild_determinism.py",
                                 "--dir", f"papers/{p.name}",
                                 "--against", f"results_raw/snapshots_estate/{p.name}.json"],
                                cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
            log.write(f"\n=== {p.name} rc={cp.returncode} ===\n{cp.stdout}\n{cp.stderr[-1500:]}\n")
            log.flush()
            text = cp.stdout or ""
            material = "MATERIAL" in text
            # Named per package, not just a count: a run that reports "62 packages differ" tells the next reader
            # nothing about *why*, and the snapshot is gone by the time they ask. Each verdict line is kept, up to a
            # dozen per package, and tallied by the folder the file lives in.
            mats = [ln.split("MATERIAL", 1)[1].strip() for ln in text.splitlines() if ln.strip().startswith("MATERIAL")]
            ephem = [ln.split(None, 2)[2].strip() for ln in text.splitlines()
                     if ln.strip().startswith(("EPHEMERAL", "ENVIRONMENT"))]
            for m in mats:
                kinds[m.split("/")[0] if "/" in m else (m.split("_")[0] if m.startswith("EXP") else m)] += 1
            any_diff = bool([ln for ln in text.splitlines() if ln.strip().startswith(("+", "-"))])
            summary[p.name] = {"rc": cp.returncode, "material": material, "any_difference_line": any_diff,
                               "material_files": mats[:12], "n_material": len(mats),
                               "ephemeral_files": ephem[:12], "n_ephemeral": len(ephem),
                               "verdict_line": next((ln.strip() for ln in text.splitlines()
                                                    if "IDENTICAL" in ln or "DIFFERS" in ln or "MATERIAL" in ln), "")}
            if material or cp.returncode not in (0, 1):
                bad.append(p.name)
            elif any_diff:
                changed.append(p.name)
        report = {"packages": len(pkgs), "material_diffs": bad, "ephemeral_only_diffs": changed,
                  "material_kind_tally": dict(kinds.most_common()),
                  "wallclock_sec": round(time.time() - t0, 1), "per_package": summary}
        (ROOT / "results_raw" / "ESTATE_TWO_PASS_REBUILD.json").write_text(
            json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"packages compared: {len(pkgs)}", flush=True)
        print(f"material differences: {len(bad)} {bad[:8]}", flush=True)
        print(f"ephemeral-only differences: {len(changed)} {changed[:8]}", flush=True)
        if kinds:
            print("what kind of file differs, estate-wide: " + ", ".join(
                  f"{k} x{v}" for k, v in kinds.most_common(8)), flush=True)
        print(f"report: results_raw/ESTATE_TWO_PASS_REBUILD.json  (wallclock {report['wallclock_sec']}s)", flush=True)
        rc2 = run(["02_shared_code/registry/package_audit.py"], log, "package_audit")
        rc3 = run(["02_shared_code/registry/spec_completion_audit.py"], log, "spec_completion_audit")
        print(f"audits after the rebuild: package_audit rc={rc2}, spec_completion_audit rc={rc3}", flush=True)
        return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
