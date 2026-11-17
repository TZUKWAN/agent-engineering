"""Scratch: supersede the discarded wave-4 generations, with a reason read out of the diff, not out of memory.

Wave 4 was re-run four times for instrument reasons that are each recorded as a deviation (D07-D10) or a failed run
in `topic_designs_wave4.FAILED_RUNS`. Every discarded generation stays on disk and has to be named in
`results_raw/SUPERSEDED_ARTIFACTS.json` with a reason, so this compares each discarded file with the kept one and
writes what actually differs - including whether any hypothesis verdict moved, which is the difference between a
cleaned-up instrument and a moved result.

    python _supersede_wave4_generations.py            # print
    python _supersede_wave4_generations.py --apply    # write the ledger
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

LEDGER = ROOT / "results_raw" / "SUPERSEDED_ARTIFACTS.json"
SCAN = ("results_raw/EXP015[2-8]_wave4_*.json",)

# Why each family was re-run. The kept generation is always the newest; these sentences explain the others.
HEAD = {   # why each family was re-run; the newest cause is named first, the earlier ones stay listed
    "0152": ("rebuilt after EXP-0162 measured that the release stores 7,646 of its 14,701 trajectories twice over "
             "(identical content in `train.parquet` and the sharded copy), so the census was sampling rows and "
             "calling them trajectories. Prevalences shift by up to 1.9 pp; the same gates pass and G7 still fires "
             "alone. Earlier generations of this family carried the instrument fixes recorded as D07-D11 in the "
             "wave's deviations."),
    "0153": ("rebuilt on the deduplicated frame per EXP-0162: 234,920 turn rows over 14,701 ids became 147,253 rows "
             "over the same 14,701 ids, so no trajectory contributes its turns twice. Feature definitions, marker "
             "lexicons and the cluster unit are unchanged; earlier generations carried D07 and the `turn_sha` "
             "identity hash the duplication audit needs."),
    "0154": "rebuilt on the deduplicated frame (EXP-0162) from the same frozen sentences, bands, seed and cluster unit; the interaction estimate moved with it and is reported as measured. Earlier generations carried D08-D09 and the D12/D13 strata and baseline work.",
    "0155": "rebuilt on the deduplicated frame (EXP-0162) from the same frozen sentences, bands, seed and cluster unit; no verdict moved. Earlier generations carried D08, D10 and the D12/D13 strata and baseline work.",
    "0156": "rebuilt on the deduplicated frame (EXP-0162) from the same frozen sentences, bands, seed and cluster unit; both contradiction hypotheses moved from null to opposite once duplicated trajectories stopped diluting the contrast. Earlier generations carried D07, D08 and the collinearity split.",
    "0157": "rebuilt on the deduplicated frame (EXP-0162) from the same frozen sentences, bands, seed and cluster unit; no verdict moved. Earlier generations carried D08 and D09.",
    "0158": "rebuilt on the deduplicated frame (EXP-0162); the E-step definitions are the same functions the earlier waves call, on the traj_id cluster unit. An earlier generation carried the cluster-threading and control_rank fixes.",

}


def already():
    led = json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.is_file() else {"purpose":
                                                                                   "artefacts kept but not citable",
                                                                                   "superseded": []}
    return {e["file"] for e in led["superseded"]}, led


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    have, led = already()
    files = sorted({f for pat in SCAN for f in glob.glob(str(ROOT / pat))}, key=os.path.getmtime)
    groups = {}
    for f in files:
        groups.setdefault(C.stem_of(os.path.basename(f)), []).append(f)
    entries, notes = [], []
    for stem, fs in sorted(groups.items()):
        key = os.path.basename(fs[0])[3:7]
        exp = "EXP-" + key
        keep, old = fs[-1], fs[:-1]
        if not old:
            print(f"{exp}: single generation, nothing to supersede")
            continue
        if key not in HEAD:
            raise SystemExit(f"ABORT: no reason written for family {stem} - refusing to file an unexplained exclusion")
        kv = C.verdicts(C.load(keep))
        head = HEAD[key]
        for f in old:
            name = os.path.basename(f)
            ov = C.verdicts(C.load(f))
            moved = {k: (ov.get(k), kv.get(k)) for k in set(ov) | set(kv) if ov.get(k) != kv.get(k)}
            if name in have:
                continue
            diffs, _, _ = C.compare(C.load(f), C.load(keep))
            reason = (f"discarded {exp} generation, superseded by {os.path.basename(keep)}: {head} "
                      f"Diff against the kept generation: {len(diffs)} field(s) changed; {len(ov)} verdict(s) "
                      f"present, verdicts moved relative to the kept file: "
                      + ("none" if not moved else json.dumps(moved, default=str)[:220]))
            entries.append({"file": name, "exp": exp, "reason": reason})
            if moved:
                notes.append(f"{exp} {name}: " + json.dumps(moved, default=str)[:260])
    for e in entries:
        print(f"{e['exp']} {e['file']}\n    {e['reason'][:230]}")
    print(f"\n{len(entries)} file(s) to supersede")
    for n in notes:
        print("  NOTE verdict moved - " + n)
    if a.apply and entries:
        led["superseded"].extend({"file": e["file"], "exp_id": e["exp"],
                                  "at": datetime.datetime.now().isoformat(timespec="seconds"),
                                  "reason": e["reason"]} for e in entries)
        LEDGER.write_text(json.dumps(led, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"ledger now {len(led['superseded'])} entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
