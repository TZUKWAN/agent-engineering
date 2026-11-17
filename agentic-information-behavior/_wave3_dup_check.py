"""Scratch: compare the non-volatile content of the duplicated wave-3 design artefacts.

The four designs were re-run several times while instrument bugs were being fixed, so each
EXP-0145..0148 has 4-5 files. Registration must cite one generation per design, so this prints
which fields actually changed between consecutive generations - the reason text for superseding
has to come from that, not from a guess.
"""
import glob
import hashlib
import json
import os
import sys

VOLATILE = ("started_at", "finished_at", "run_cost", "invocation")


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


def main() -> int:
    for num in ("0145", "0146", "0147", "0148"):
        files = sorted(glob.glob(f"results_raw/EXP{num}_wave3_design_{num}_*.json"))
        print(f"== EXP-{num}: {len(files)} generations")
        prev = None
        for f in files:
            d = json.load(open(f, encoding="utf-8"))
            v = {k: d[k] for k in d if k not in VOLATILE}
            h = hashlib.sha256(json.dumps(v, sort_keys=True, default=str).encode()).hexdigest()[:10]
            diffs = []
            if prev is not None:
                a, b = flat(prev), flat(v)
                for k in sorted(set(a) | set(b)):
                    if a.get(k) != b.get(k):
                        diffs.append(f"{k}: {a.get(k)!r} -> {b.get(k)!r}")
            print(f"   {os.path.basename(f)} {h}")
            for line in diffs[:14]:
                print("        ~", line[:160])
            if len(diffs) > 14:
                print(f"        ~ ... {len(diffs) - 14} more changed fields")
            if prev is not None and not diffs:
                print("        = byte-equal apart from the volatile keys")
            prev = v
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
