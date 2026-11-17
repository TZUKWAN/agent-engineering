"""Append entries to results_raw/SUPERSEDED_ARTIFACTS.json.

Kept-but-not-citable is the programme's convention: an artefact produced by a run that was later superseded stays on
disk (so a reviewer can see it happened) and is named here with the reason, while the package builders exclude it.
This tool refuses to supersede a file that does not exist and refuses to write a reason that is empty, because an
unexplained exclusion is how a quiet sample swap once survived three audits.

    python 02_shared_code/registry/supersede_artefacts.py --reason '...' --file A.json --file B.json
"""
from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
LEDGER = ROOT / "results_raw" / "SUPERSEDED_ARTIFACTS.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", action="append", required=True)
    ap.add_argument("--reason", required=True)
    ap.add_argument("--exp", default="")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    led = json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.is_file() else {"purpose":
                                                                                   "artefacts kept but not citable",
                                                                                   "superseded": []}
    have = {e["file"] for e in led["superseded"]}
    added = 0
    for f in args.file:
        p = pathlib.Path(f) if pathlib.Path(f).is_absolute() else ROOT / f
        if not p.is_file():
            raise SystemExit(f"ABORT: {f} is not on disk, so it cannot be superseded")
        name = p.name
        if name in have:
            print(f"  {name}: already superseded")
            continue
        led["superseded"].append({"file": name, "exp_id": args.exp or f"EXP-{name[3:7]}",
                                  "at": datetime.datetime.now().isoformat(timespec="seconds"),
                                  "reason": args.reason})
        added += 1
    if not added:
        print("nothing added")
        return 0
    LEDGER.write_text(json.dumps(led, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"appended {added} entries (ledger now {len(led['superseded'])})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
