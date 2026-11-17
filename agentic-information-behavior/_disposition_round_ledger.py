"""Ledger the generations this registry round superseded, with the reason taken from the diff.

Three scripts ran twice or three times while their bugs were found, and an artefact family whose earlier generation
is still on disk needs to say which one a reader should trust and why. The reason is composed from what actually
changed between the last discarded generation and the kept one (`compare_artefact_generations`), not from a note
written before looking.

    python _disposition_round_ledger.py [--apply]
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
import compare_artefact_generations as C                                            # noqa: E402

LEDGER = ROOT / "results_raw" / "SUPERSEDED_ARTIFACTS.json"

WHY = {
    "EXP0222_intake_dispositions": (
        "resolved a fold only onto a topic, so its two folds onto the pre-wave packages (P001, P002) were written as "
        "'a fold with no host', and it let any row with a registered run claim the package its probes fed - which put "
        "three topics in P001 and two in P005. Kept generation reads a package only for the row whose own status owns "
        "it and resolves a package host from papers/ on disk."),
    "EXP0223_intake_facts": (
        "tested an intake value against a placeholder tuple that contained the empty string, and `str.startswith('')` "
        "is true for every string - so it overwrote the round-4 batch's CL/IM theory anchors and its supplied DV/IV "
        "with derived text. Kept generation matches placeholders by prefix only and preserves what the intake supplied."),
    "EXP0160_sibling_differentiation": (
        "compared the outcome and what-is-manipulated axes on cells the attachment batch had left empty, so 44 of its "
        "statements were written on title and method alone, and the generations before waves 9-12 were assembled also "
        "had no literature matrix of theirs to grade against. Kept generation runs after EXP-0223 filled those "
        "columns from the frozen designs and every wave package had been built."),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    led = json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.is_file() else {"superseded": []}
    have = {e["file"] for e in led["superseded"]}
    groups = {}
    for stem in WHY:
        groups[stem] = sorted(glob.glob(str(ROOT / "results_raw" / f"{stem}_*.json")), key=os.path.getmtime)
    entries, notes = [], []
    for stem, fs in sorted(groups.items()):
        keep, old = fs[-1:], fs[:-1]        # the last generation of each family is the one the corrected script wrote
        if not keep or not old:
            notes.append(f"{stem}: nothing to supersede (kept {len(keep)}, old {len(old)})")
            continue
        diffs, _, _ = C.compare(C.load(old[-1]), C.load(keep[-1]))
        va, vb = C.verdicts(C.load(old[-1])), C.verdicts(C.load(keep[-1]))
        moved = {k: (va.get(k), vb.get(k)) for k in set(va) | set(vb) if va.get(k) != vb.get(k)}
        reason = (WHY[stem] + f" Diff of the last discarded generation against the kept "
                  f"{os.path.basename(keep[-1])}: {len(diffs)} field(s) changed; {len(va)} verdict(s) carried, "
                  f"{len(moved)} moved" + ("" if not moved else " (PATHS: " + ", ".join(sorted(moved)) + ")"))
        for f in old:
            if os.path.basename(f) in have:
                continue
            entries.append({"file": os.path.basename(f), "exp": "EXP-" + os.path.basename(f)[3:7],
                            "reason": reason})
        print(f"{stem}: {len(old)} discarded, kept {os.path.basename(keep[-1])}, {len(diffs)} field(s) differ")
    for e in entries:
        print(f"  {e['exp']} {e['file']}\n      {e['reason'][:180]}")
    print(f"\n{len(entries)} file(s) to supersede")
    if a.apply and entries:
        led["superseded"].extend({"file": e["file"], "exp_id": e["exp"],
                                  "at": datetime.datetime.now().isoformat(timespec="seconds"),
                                  "reason": e["reason"]} for e in entries)
        LEDGER.write_text(json.dumps(led, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"ledger now {len(led['superseded'])} entries")
    elif not a.apply:
        print("(dry run; pass --apply to write)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
