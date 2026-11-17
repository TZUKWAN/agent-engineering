"""Scratch: supersede every pre-fix generation of the artefacts the ranker fix regenerated.

The ledger entry has to carry a reason, and a reason has to come from the diff, so this compares the last pre-fix
generation with the kept one for each artefact family (via `compare_artefact_generations`) and writes one entry per
superseded file naming the changed-field count and whether any hypothesis verdict moved.

    python _supersede_prefix_generations.py [--apply]
"""
from __future__ import annotations

import argparse
import datetime
import glob
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "02_shared_code" / "registry"))
import compare_artefact_generations as C            # noqa: E402

FIX_START = datetime.datetime(2026, 9, 24, 9, 45).timestamp()      # first artefact the re-run chain wrote
LEDGER = ROOT / "results_raw" / "SUPERSEDED_ARTIFACTS.json"

SCAN = ("results_raw/EXP01*_wave*.json", "results_raw/EXP0119_*.json")

REASON_HEAD = ("produced by the ranker before EXP-0151's amendment: BM25 summed query-term contributions in "
               "`set` order, so PYTHONHASHSEED decided the last bits of a score and hit@1 on the exactly-tied rows "
               "(EXP-0151 measures 331 of the 7,476 sampled dev rows, 4.43%) could move between "
               "runs of identical code. Superseded by the generation rebuilt with `sorted(set(...))`, so this "
               "package's numbers all come from one deterministic instrument. ")


def already():
    led = json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.is_file() else {"superseded": []}
    return {e["file"] for e in led["superseded"]}, led


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    have, led = already()
    entries, notes, kept_families = [], [], 0
    files = sorted({f for pat in SCAN for f in glob.glob(str(ROOT / pat))}, key=os.path.getmtime)
    groups = {}
    for f in files:
        groups.setdefault(C.stem_of(os.path.basename(f)), []).append(f)
    for stem, fs in sorted(groups.items()):
        exp = "EXP-" + os.path.basename(fs[0])[3:7]
        keep = [f for f in fs if os.path.getmtime(f) >= FIX_START]
        old = [f for f in fs if os.path.getmtime(f) < FIX_START]
        if not keep or not old:
            continue
        kept_families += 1
        diffs, _, _ = C.compare(C.load(old[-1]), C.load(keep[-1]))
        va, vb = C.verdicts(C.load(old[-1])), C.verdicts(C.load(keep[-1]))
        moved = {k: (va.get(k), vb.get(k)) for k in set(va) | set(vb) if va.get(k) != vb.get(k)}
        reason = (REASON_HEAD + f"Diff against the kept generation {os.path.basename(keep[-1])}: "
                  f"{len(diffs)} field(s) changed; {len(va)} verdict(s) carried, {len(moved)} moved"
                  + ("" if not moved else " (PATHS: " + ", ".join(sorted(moved)) + ")"))
        for f in old:
            if os.path.basename(f) in have:
                continue
            entries.append({"file": os.path.basename(f), "exp": exp, "reason": reason})
        if moved:
            notes.append(f"{exp}: VERDICTS MOVED {json.dumps(moved, default=str)[:220]}")
    for e in entries:
        print(f"{e['exp']} {e['file']}\n    {e['reason'][:200]}")
    print(f"\n{len(entries)} file(s) to supersede; families whose regeneration moved a verdict: "
          f"{len(notes)}")
    for n in notes:
        print("  " + n)
    if a.apply and entries:
        led["superseded"].extend({"file": e["file"], "exp_id": e["exp"],
                                  "at": datetime.datetime.now().isoformat(timespec="seconds"),
                                  "reason": e["reason"]} for e in entries)
        LEDGER.write_text(json.dumps(led, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"ledger now {len(led['superseded'])} entries")
    elif not a.apply:
        print("(dry run; pass --apply to write)")
    return 1 if notes else 0


if __name__ == "__main__":
    raise SystemExit(main())
