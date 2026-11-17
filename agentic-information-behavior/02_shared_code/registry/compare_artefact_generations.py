"""Tool: what actually changed between two generations of the same artefact?

Kept-but-not-citable entries have to say why, and "I re-ran it" is not a reason. This compares consecutive
generations field by field, ignoring the keys every run rewrites (timestamps, wallclock, the argv it recorded),
and prints the changed-field count plus any hypothesis-level verdict or estimate that moved. The output is what
`supersede_artefacts.py --reason` should be written from.

    python 02_shared_code/registry/compare_artefact_generations.py --glob 'results_raw/EXP0119_*.json'
    python 02_shared_code/registry/compare_artefact_generations.py --glob '...' --all-pairs
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import math
import os
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
VOLATILE = {"started_at", "finished_at", "run_cost", "invocation", "wallclock_sec", "generated_at", "at"}


def flat(obj, prefix=""):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(flat(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(flat(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = obj
    return out


def norm(o):
    """NaN and inf compared unequal to themselves (IEEE), so a table of identical NaNs read as drift once before."""
    if isinstance(o, float) and not math.isfinite(o):
        return "NaN"
    if isinstance(o, dict):
        return {k: norm(v) for k, v in o.items()}
    if isinstance(o, list):
        return [norm(v) for v in o]
    return o


def load(f):
    d = json.load(open(f, encoding="utf-8"))
    return norm({k: v for k, v in d.items() if k not in VOLATILE})


def verdicts(d):
    """Every hypothesis-level verdict in the artefact, wherever it is nested, as {path: verdict}."""
    out = {}

    def walk(o, p):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "verdict" and isinstance(v, (str, type(None))):
                    out[p] = v
                walk(v, f"{p}.{k}" if p else str(k))
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{p}[{i}]")
    walk(d, "")
    return out


def digest(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()[:10]


def compare(a, b):
    x, y = flat(a), flat(b)
    return [(k, x.get(k), y.get(k)) for k in sorted(set(x) | set(y)) if x.get(k) != y.get(k)], x, y


def interesting(diffs):
    """Changed fields that a reader of the paper would notice: verdicts, estimates, p-values, gates, row counts."""
    hits = []
    for k, u, v in diffs:
        if any(t in k for t in ("verdict", "beta", "p_holm", "p_boot", "_p", "ci_lo", "ci_hi", "auroc",
                                "hit", "n_queries", "rows", "gate", "share", "status", "n_changed",
                                "mean_change", "clusters", "coverage", "rho")):
            hits.append((k, u, v))
    return hits


def stem_of(name: str) -> str:
    """The file name without its run timestamp, so a `..._summary_<ts>.json` is not compared with `..._<ts>.json`.

    The first version globbed `EXP0121_*.json` and paired a design artefact with the summary file the same run
    wrote beside it, which printed 243 "changed fields" that were really two different documents.
    """
    return re.sub(r"_?\d{8}T\d{6}", "", name)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", required=True)
    ap.add_argument("--all-pairs", action="store_true", help="compare every consecutive pair, not just the last")
    ap.add_argument("--max-show", type=int, default=12)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    files = sorted(glob.glob(str(ROOT / a.glob)), key=os.path.getmtime)
    groups = {}
    for f in files:
        groups.setdefault(stem_of(os.path.basename(f)), []).append(f)
    if len(groups) > 1:
        print(f"(this glob matched {len(groups)} distinct artefacts: "
              f"{', '.join(sorted(groups))}; comparisons are within each)")
    multi = {k: v for k, v in groups.items() if len(v) > 1}
    if not multi:
        print(f"{len(files)} file(s) for {a.glob}, each a single generation: nothing to compare")
        return 0
    for stem, fs in sorted(multi.items()):
        pairs = list(zip(fs, fs[1:])) if a.all_pairs else [tuple(fs[-2:])]
        for old, new in pairs:
            do, dn = load(old), load(new)
            diffs, _, _ = compare(do, dn)
            va, vb = verdicts(do), verdicts(dn)
            moved = {k: (va.get(k), vb.get(k)) for k in set(va) | set(vb) if va.get(k) != vb.get(k)}
            print(f"{os.path.basename(old)}  ->  {os.path.basename(new)}")
            print(f"   changed fields: {len(diffs)}"
                  + ("  (identical apart from timestamps/wallclock/argv)" if not diffs else ""))
            print(f"   verdicts carried: {len(va)}, moved: {len(moved)}"
                  + ("" if not moved else "  " + json.dumps(moved, default=str)[:260]))
            for k, u, v in interesting(diffs)[:a.max_show]:
                print(f"   ~ {k[:70]}: {str(u)[:34]} -> {str(v)[:34]}")
            rest = len(diffs) - len(interesting(diffs))
            if rest > 0:
                print(f"   + {rest} other changed fields that carry no paper-facing quantity")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
