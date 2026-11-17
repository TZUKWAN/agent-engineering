"""Run every round-2 detector and rebuild the problem list from what they find.

The second verification pass asked three questions of the whole estate - is the data real, is the method
re-checkable, is each registered run an experiment that actually happened - and each question has a detector:

| detector | asks |
|---|---|
| `round2_number_provenance.py` | is every number the package prints carried by one of its own runs? |
| `round2_statistical_consistency.py` | does each printed verdict follow from the numbers beside it? |
| `round2_corpus_remeasurement.py` | do the row counts and coverage the censuses claim still hold on disk? |
| `round2_run_reality.py` | does each registry row resolve to a script, an artefact and a package copy? |
| `round2_claim_support.py` | does each claim's wording match the support its package can show? |
| `round2_derivation_precision.py` | is each published figure computed from measurements, or from values already rounded? |

This driver runs them in order and then calls `round2_problem_list.py`, which merges their reports into
`docs/ROUND2_PROBLEM_LIST.md` with a status per item. Item statuses live in
`results_raw/ROUND2_PROBLEM_STATUS.json`, so re-running the detectors refreshes the evidence without forgetting
what has already been resolved and why.

    python 02_shared_code/registry/round2_run_all.py
"""
from __future__ import annotations

import datetime
import json
import pathlib
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
DETECTORS = ("round2_number_provenance.py", "round2_statistical_consistency.py",
             "round2_corpus_remeasurement.py", "round2_run_reality.py", "round2_claim_support.py",
             "round2_interval_audit.py",
             # not a reading of the shipped artefacts but of the code that writes them: a published figure computed
             # from values that were already rounded is reproducible only by repeating the writer's rounding, which
             # is how P002's 1.367 bits/trajectory and P001/P003's 88.1% came to be published at all
             "round2_derivation_precision.py")


def run(script: str, *args: str) -> dict:
    r = subprocess.run([sys.executable, str(HERE / script), *args], cwd=str(ROOT), capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    tail = [l for l in (r.stdout + r.stderr).splitlines() if l.strip()]
    print(f"--- {script} (rc={r.returncode})")
    for l in tail[-4:]:
        print("   ", l[:170])
    return {"script": script, "rc": r.returncode, "summary": tail[-1][:300] if tail else ""}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    present = [d for d in DETECTORS if (HERE / d).is_file()]
    missing = [d for d in DETECTORS if d not in present]
    if missing:
        raise SystemExit(f"ABORT: {missing} is listed as a round-2 detector but does not exist")
    # Label the register first, then read it. The round-2 detectors register their own run as they go
    # (`round2_derivation_precision.py`, `prune_package_evidence.py`), so a sweep that runs before the labeller
    # always finds its own newest rows unlabelled - two such rows sat open across three full closing chains.
    # Labelling at the head of the sweep makes the verification self-consistent: whatever this pass adds, the next
    # pass sees already labelled.
    run("round2_register_windows.py", "--apply")
    out = [run(d) for d in present]
    out.append(run("round2_problem_list.py"))
    payload = {"exp_id": "EXP-0224", "seed": "n/a (a read-only verification pass)",
               "detectors": out, "wallclock_sec": round(time.time() - t0, 1),
               "started_at": datetime.datetime.now().isoformat(timespec="seconds")}
    dest = ROOT / "results_raw" / f"EXP0224_round2_verification_sweep_{time.strftime('%Y%m%dT%H%M%S')}.json"
    dest.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote", dest.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
