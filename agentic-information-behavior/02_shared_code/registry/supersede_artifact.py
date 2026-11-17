"""Register an artefact as superseded: move it to results_raw/superseded/ and append the reason to the programme
register. Failed and superseded runs are kept, never deleted (spec T01.03) - this is the step that keeps them out of
citation while leaving them on disk.

Refuses to invent a reason: `--reason` is required, and the script aborts if the file is neither in results_raw/ nor
already in the register, so a typo cannot silently "supersede" nothing.

    python supersede_artifact.py --file EXP0089_p003_second_auditor_20260921T014435.json \\
        --exp EXP-0089 --reason "..." --quoted "no - replaced before any paper text cited it"
"""
from __future__ import annotations

import argparse, json, pathlib, sys, time

ROOT = next(a for a in [pathlib.Path(__file__).resolve().parent, *pathlib.Path(__file__).resolve().parents]
            if (a / "00_program_registry").is_dir())
RAW = ROOT / "results_raw"
REG = RAW / "SUPERSEDED_ARTIFACTS.json"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, help="basename of the artefact in results_raw/")
    ap.add_argument("--exp", required=True)
    ap.add_argument("--reason", required=True)
    ap.add_argument("--quoted", required=True, help="was the value already used in paper text? say so either way")
    ap.add_argument("--superseded-by", default="", help="the file that replaces it, when one exists yet")
    a = ap.parse_args()

    reg = json.loads(REG.read_text(encoding="utf-8"))
    if not isinstance(reg.get("superseded"), list):
        raise SystemExit(f"ABORT: {REG.name} has no 'superseded' list - refusing to guess its schema")
    if any(e.get("file") == a.file for e in reg["superseded"]):
        print(f"already registered: {a.file} - nothing moved")
        return 0
    src, dst = RAW / a.file, RAW / "superseded" / a.file
    if not src.is_file() and not dst.is_file():
        raise SystemExit(f"ABORT: {a.file} is neither in results_raw/ nor in the register")
    if src.is_file():
        (RAW / "superseded").mkdir(exist_ok=True)
        src.rename(dst)
        print(f"  moved {a.file} -> results_raw/superseded/")
    reg["superseded"].append({"file": a.file, "exp_id": a.exp, "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                              "reason": a.reason, "was_it_quoted": a.quoted,
                              "superseded_by": a.superseded_by or "see experiment_registry.csv for this exp_id"})
    REG.write_text(json.dumps(reg, indent=1, ensure_ascii=False), encoding="utf-8", newline="")
    chk = json.loads(REG.read_text(encoding="utf-8"))
    print(f"  register now holds {len(chk['superseded'])} superseded artefacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
