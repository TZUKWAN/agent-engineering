"""Ledger the generations the round-2 verification round superseded, with the reason read from the diff.

The re-run of every wave's design step wrote a new generation of each artefact. The estate's rule is that a retired
generation stays on disk as the audit trail but is named in `SUPERSEDED_ARTIFACTS.json` with a reason, and the
reason has to come from what actually differs between the discarded file and the kept one - not from a note written
before looking. This compares them with `compare_artefact_generations` and records the field counts, whether any
estimate moved (it must not: only the labelling and the direction field may), and whether any verdict word changed
(and if it did, which rows).

    python _round2_ledger.py [--apply]
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
import compare_artefact_generations as C                                    # noqa: E402

LEDGER = ROOT / "results_raw" / "SUPERSEDED_ARTIFACTS.json"
CUTOFF = datetime.datetime(2026, 9, 25, 22, 0).timestamp()      # first artefact of the round-2 label-rule re-run

REASONS = {
    "wave1_candidate_level": "re-run in the second round-2 sweep, which put the row's own proof on it: T108's "
                             "displacement row is now read by the frozen rule instead of a bespoke expression that "
                             "called a significant wrong-side estimate `null`; T108's decoy row prints the "
                             "relative-selection ratio its bootstrap interval actually belongs to (`ci_of`), with "
                             "the 1.0 its hypothesis measures against (`null_value`); T109's rank-agreement row "
                             "declares `verdict_rule=descriptive`, as its own frozen sentence ('characterised rather "
                             "than averaged away') says, so it carries the estate's non-inferential word instead of "
                             "`partial`.",
    "wave3_design": "re-run after the round-2 verdict fix: two bootstrap rows printed `null` although their "
                    "confidence interval excludes zero, because the expression tested only the positive side of an "
                    "any-sided hypothesis and read a missing bound as zero. The rows now go through "
                    "`wave_lib.magnitude_verdict`, which is the design's own frozen rule (deviation W3-D11).",
    "default": "re-run in the round-2 verification pass. Six changes, all of them about what a row can prove and "
               "none about the measurement: the four-way rules now reach every verdict row in the artefact instead "
               "of only a top-level `models` list (wave-1 summaries key by topic, and several designs file one "
               "hypothesis under its own name); an interval filed under the name of its resampling "
               "(`ci_clustered`) counts as the row's interval; a bootstrap row states where its interval and its p "
               "came from (`ci_kind`, `p_kind`, `draws_used`) instead of leaving a blank standard error to be "
               "guessed at; a recorded direction under `direction_predicted` or `direction` is read as well as one "
               "under `verdict_direction`; a row that says no direction was frozen is re-derived with the estate's "
               "direction-free rule `magnitude_verdict`, on its own interval, corrected p and the floor its design "
               "names; and a derived Holm value is withdrawn from a row whose declared rule is not inferential. An "
               "exact binomial or Fisher probability (`p_exact`) now counts as the row's test.",
}


def classify_moved(diffs, est, new_flat=None) -> str:
    """Say what a moved estimate field actually is, because two of them are not re-measurements.

    `p_holm` going from absent to a number is the derived-Holm step filling the corrected p the frozen family
    declared but the artefact never carried; a NaN becoming null is the writer's new non-finite rule; and a
    `p_holm` going from a number to absent is that same correction being withdrawn from a row whose declared rule
    is not inferential. Either way a reader of the ledger must be able to see that no coefficient, standard error
    or count was re-estimated - which is why the sibling fields are read from the kept artefact itself, since only
    fields that *changed* appear in the diff.
    """
    if not est:
        return ""
    by = {k: (a, b) for k, a, b in diffs}
    holm, nanish, other, withdrawn = [], [], [], []
    # a non-finite quantity reaches the JSON in three shapes: the float NaN, the strings "nan"/"NaN" an older
    # writer emitted, and None. All three mean "this row has no such number", and the current writer standardises
    # them on null - which is a formatting change, not a re-measurement.
    blank = (None, "nan", "NaN", "NA", "<NA>", "None")
    # the estate's own non-inferential words, and the rule names that earn them
    NON_INFERENTIAL = ("descriptive", "specificity", "coverage_only", "enumeration")

    def nonfinite(v):
        return v in blank or (isinstance(v, float) and v != v)

    for k in est:
        a, b = by.get(k, (None, None))
        if k.endswith(".p_holm") and nonfinite(a):
            holm.append(k)
        elif k.endswith(".p_holm") and nonfinite(b):
            # the correction was withdrawn, not the estimate re-run: a row whose declared rule is not inferential
            # no longer carries a Holm-corrected p, because that number belongs to an inferential claim it disclaims
            head = k[: -len(".p_holm")]
            flat = new_flat or {}
            rule = str(flat.get(head + ".verdict_rule") or (by.get(head + ".verdict_rule") or (None, None))[1]
                       or "").lower()
            word = str(flat.get(head + ".verdict") or (by.get(head + ".verdict") or (None, None))[1] or "")
            if rule in NON_INFERENTIAL or word.startswith(("measured_descriptively", "not_estimable", "not_",
                                                           "below_the", "descriptive")):
                withdrawn.append(k)
            else:
                other.append(k)
        elif nonfinite(a) or nonfinite(b):
            nanish.append(k)
        else:
            other.append(k)
    bits = []
    if holm:
        bits.append(f"{len(holm)} of them `p_holm`, absent in the retired generation and derived here from that "
                    "run's own `p_raw` values by the Holm rule its freeze declared (wave_lib.finalize_models) - a "
                    "correction computed on published numbers, not a re-estimation")
    if withdrawn:
        bits.append(f"{len(withdrawn)} of them `p_holm` withdrawn from a row that declares a non-inferential rule, "
                    "which makes no claim a corrected p could support (its own `p` is unchanged)")
    if nanish:
        bits.append(f"{len(nanish)} of them a non-finite value written as null rather than NaN")
    if other:
        bits.append(f"{len(other)} of them a genuinely different value: " + ", ".join(other[:6]))
    return ". Note: " + "; ".join(bits) + "."


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    led = json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.is_file() else {"superseded": []}
    have = {e["file"] for e in led["superseded"]}
    groups = {}
    for f in glob.glob(str(ROOT / "results_raw" / "EXP*.json")):
        base = os.path.basename(f)
        m = C.stem_of(base)
        groups.setdefault(m, []).append(f)
    entries, warnings = [], []
    for stem, fs in sorted(groups.items()):
        fs.sort(key=os.path.getmtime)
        keep = [f for f in fs if os.path.getmtime(f) >= CUTOFF]
        old = [f for f in fs if os.path.getmtime(f) < CUTOFF]
        if not keep or not old:
            continue
        diffs, _x, y = C.compare(C.load(old[-1]), C.load(keep[-1]))
        est = [k for k, _a, _b in diffs if k.endswith((".beta", ".se", ".ci_lo", ".ci_hi", ".p", ".p_holm", ".n",
                                                       ".clusters", ".mean_difference", ".delta"))]
        va, vb = C.verdicts(C.load(old[-1])), C.verdicts(C.load(keep[-1]))
        moved = {k: (va.get(k), vb.get(k)) for k in set(va) | set(vb) if va.get(k) != vb.get(k)}
        key = ("wave3_design" if "wave3_design" in stem else
               "wave1_candidate_level" if "wave1_candidate_level" in stem else "default")
        reason = (REASONS[key] + f" Diff against the kept generation {os.path.basename(keep[-1])}: "
                  f"{len(diffs)} field(s) changed, {len(est)} of them an estimate, {len(moved)} verdict word(s) moved"
                  + ("" if not moved else " [" + "; ".join(f"{k}: {v[0]} -> {v[1]}" for k, v in list(moved.items())[:6])
                     + "]"))
        if est:
            reason += classify_moved(diffs, est, y)
            # an explained move - a `p_holm` filled from the run's own p_raw values, a NaN written as null - is
            # recorded in the reason and does not stop the round; anything else is an unexplained re-measurement
            if "genuinely different value" in reason or "Note: " not in reason:
                warnings.append(f"{stem}: {len(est)} ESTIMATE FIELD(S) MOVED, unexplained: {est[:8]}")
        for f in old:
            b = os.path.basename(f)
            if b in have:
                continue
            entries.append({"file": b, "exp": "EXP-" + b[3:7], "reason": reason})
        print(f"{stem[:52]:52s} discarded {len(old):2d} kept {os.path.basename(keep[-1])[-16:]} "
              f"fields={len(diffs):5d} estimates={len(est)} verdicts_moved={len(moved)}")
    for w in warnings:
        print("  !!", w)
    print(f"\n{len(entries)} file(s) to supersede")
    if a.apply and entries:
        led["superseded"].extend({"file": e["file"], "exp_id": e["exp"],
                                  "at": datetime.datetime.now().isoformat(timespec="seconds"),
                                  "reason": e["reason"]} for e in entries)
        LEDGER.write_text(json.dumps(led, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"ledger now {len(led['superseded'])} entries")
    elif not a.apply:
        print("(dry run; --apply to write)")
    return 1 if warnings else 0


if __name__ == "__main__":
    raise SystemExit(main())
