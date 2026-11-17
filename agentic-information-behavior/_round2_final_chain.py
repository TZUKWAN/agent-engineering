"""The round's closing chain, in the order the estate's own rules require.

Run this after the design re-pass has finished. Each step is a generator the estate already uses; the point of
chaining them is that no step depends on somebody remembering the next one:

1. `_round2_ledger.py --apply`   - retire the generations the re-pass replaced, with the measured diff as reason;
2. `fix_prewave_registry_rows_p001.py` - re-apply the register corrections the pre-wave packages need (EXP-0228),
                                   including the ledger entry that names the one table two runs of
                                   `analyze_routing_failure.py` both declare at one fixed path. It runs before the
                                   supersede step because that step is what strips a declaration the ledger has
                                   just retired: in the other order the register kept pointing at the retired file
                                   until the following pass, which is a pass in which the package mirror reports it
                                   as named-but-unresolved;
3. `supersede_undeclared_generations.py --apply` - recompute the register/ledger agreement against the final state;
4. `round2_register_windows.py --apply` (first of two) - label every register row's time claim with what its own
                                   artefacts support (`measured`, `instant_recorded`, `output_stamp`, or an honest
                                   not-recorded shape) and re-anchor the 12 rows whose stated window no generation
                                   of theirs falls inside, before any step copies the register into a package
                                   (EXP-0234);
5. `_reassemble_all_waves.py`    - rebuild every wave package from its artefacts and run its per-package chain, so
                                   the shipped evidence folders are the ones the register resolves to;
6. `export_package_registry.py`  - rewrite every package's copy of the register and its run index;
7. `prune_package_evidence.py --apply --all` - the same resolution for the five hand-assembled packages, which the
                                   factory does not build, and re-verification of the factory's own rule everywhere
                                   else, so a package that cites a programme census holds that census (EXP-0231);
8. `export_e_coverage.py`        - rewrite the five hand packages' E00-E19 statements against the registers that step
                                   6 just exported; the factory writes its own for the other 65;
9. `round2_cluster_unit_map.py`  - publish the unit behind every cluster-robust interval, read from the run records
                                   and from the code that produced them (EXP-0232);
10. `write_blocked_reproduce.py --apply` - give the twelve premise-gated packages the `reproduce.sh` they never had, so
                                   the gate that stopped a design can be re-derived and not only read (EXP-0233);
11. `build_topic_registry.py`    - regenerate the topic table with its three overlays and its integrity asserts;
12. `program_status.py`          - regenerate the programme's status document;
13. `round2_register_windows.py --apply` (second of two) - the steps above add rows to the register, and a row
                                   nobody labelled is a row whose time claim nobody tested, so the labeler runs
                                   once more after the last row-creating step and before the sweep reads them;
14. `_round2_record_resolutions.py` - write this round's resolutions into the status file the list reads;
15. `round2_run_all.py`          - run the six detectors and rebuild the problem list from what they find;
16. `package_audit.py`           - the deliverable audit every package must pass;
17. `spec_completion_audit.py`   - the spec-to-artefact completion audit;
18. `_estate_two_pass.py`        - snapshot, rebuild everything, and prove the second state is the first.

Everything is appended to one log so a single read shows where it stopped.

    python _round2_final_chain.py
"""
from __future__ import annotations

import datetime
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
LOG = ROOT / "logs" / "round2_final_chain.log"
STEPS = (
    ("_round2_ledger.py", "--apply"),
    ("02_shared_code/registry/fix_prewave_registry_rows_p001.py",),
    ("02_shared_code/registry/supersede_undeclared_generations.py", "--apply"),
    ("02_shared_code/registry/round2_register_windows.py", "--apply"),
    ("_reassemble_all_waves.py",),
    ("02_shared_code/registry/export_package_registry.py",),
    ("02_shared_code/registry/prune_package_evidence.py", "--apply", "--all"),
    ("02_shared_code/registry/export_e_coverage.py",),
    ("02_shared_code/registry/round2_cluster_unit_map.py",),
    ("02_shared_code/registry/write_blocked_reproduce.py", "--apply"),
    ("02_shared_code/registry/build_topic_registry.py",),
    ("02_shared_code/registry/program_status.py",),
    ("02_shared_code/registry/round2_register_windows.py", "--apply"),
    ("_round2_record_resolutions.py",),
    ("02_shared_code/registry/round2_run_all.py",),
    ("02_shared_code/registry/package_audit.py",),
    ("02_shared_code/registry/spec_completion_audit.py",),
    ("_estate_two_pass.py",),
)


def main() -> int:
    # the console this prints to is cp936 on the box the estate runs on, and the steps echo paths that carry the
    # author's own non-ASCII directory name - a print must never be what stops a verification chain
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    with open(LOG, "a", encoding="utf-8") as log:
        for i, step in enumerate(STEPS, 1):
            head = (f"\n=== [{i}/{len(STEPS)}] {' '.join(step)}  "
                    f"{datetime.datetime.now().isoformat(timespec='seconds')}\n")
            log.write(head)
            log.flush()
            print(head.strip(), flush=True)
            r = subprocess.run([sys.executable, "-u", *step], cwd=str(ROOT), stdout=log,
                               stderr=subprocess.STDOUT)
            tail = ""
            with open(LOG, encoding="utf-8", errors="replace") as f:
                lines = [l for l in f.read().splitlines() if l.strip()]
            tail = " | ".join(lines[-3:])
            print(f"    rc={r.returncode}  {tail[:260]}", flush=True)
            if r.returncode:
                log.write(f"!! step {i} failed rc={r.returncode}; chain stopped\n")
                print(f"CHAIN STOPPED at step {i} ({step[0]}) - see {LOG.name}", flush=True)
                return r.returncode
    print("chain complete; log:", LOG.name, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
