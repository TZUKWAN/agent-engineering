"""Re-run every wave's design step and prove that only the round-2 fixes moved.

Three round-2 changes alter artefacts rather than prose: a model row now carries the `verdict_direction` its design
froze (so `supported` can be re-derived from the artefact alone), non-finite floats are written as null instead of
`NaN`/`nan`, and wave 1's nested-gain row is labelled in the words its own threshold sentence uses. The honest way
to land that is to re-run each design from its frozen frame and diff the new artefact against the kept one: every
estimate - coefficient, standard error, interval, p-value, row count - must be identical, and the only permitted
differences are those three. If an estimate moves, that is a new finding to chase, not something to rebuild past.

Each step is run exactly as the packages' `reproduce.sh` states it (same script, seed 42, no `--only`), then the
wave's recorder re-reads the artefacts, then the packages are re-assembled.

    python _round2_rerun_designs.py [--waves 2 3] [--apply]
"""
from __future__ import annotations

import argparse
import datetime
import glob
import json
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "02_shared_code" / "registry"))
import compare_artefact_generations as C                                # noqa: E402

# fields whose movement would mean the measurement changed, not the labelling of it
ESTIMATE = re.compile(r"\.(beta|se|ci_lo|ci_hi|p|p_raw|p_holm|p_boot|n|clusters|mean_difference|delta|"
                      r"deviance|lr_chi2|lr_stat|rate|share|count)$")
LABEL_OK = re.compile(r"\.(verdict|verdict_direction|verdict_rule|note)$")


def run(args: list) -> tuple:
    r = subprocess.run([sys.executable] + args, cwd=str(ROOT), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    tail = [l for l in (r.stdout + r.stderr).splitlines() if l.strip()]
    return r.returncode, tail


def generations(stem: str) -> list:
    """Every generation of one artefact family, oldest first.

    A file can vanish between the snapshot and this listing - another pass, or the ledger's own housekeeping, is
    working on the same folder - so a generation that no longer exists is skipped rather than raised over.
    """
    out = []
    for f in sorted(glob.glob(str(ROOT / "results_raw" / f"{stem}_*.json")), key=os.path.getmtime):
        try:
            out.append((f, os.path.getmtime(f)))
        except OSError:
            continue
    return out


def kept_at(path: str) -> float:
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--waves", nargs="*", default=[])
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--no-assemble", action="store_true",
                    help="re-run and record each wave's designs, but leave the packages for one later sweep")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    waves = [int(w) for w in a.waves] or list(range(1, 13))
    ledger = json.loads((ROOT / "results_raw" / "SUPERSEDED_ARTIFACTS.json").read_text(encoding="utf-8"))
    retired = {str(ROOT / e["file"]).replace("\\", "/") for e in ledger["superseded"]}
    report = []
    for w in waves:
        steps = []
        if w == 1:
            # all three wave-1 design steps, not the two that happened to be listed: EXP-0123 comes from
            # exp_wave1_reformulation.py, and leaving it out kept a stale generation as the kept one through two
            # full re-passes
            steps = [["02_shared_code/package_factory/exp_wave1_query_level.py"],
                     ["02_shared_code/package_factory/exp_wave1_reformulation.py"],
                     ["02_shared_code/package_factory/exp_wave1_candidate_level.py"]]
        else:
            d = f"02_shared_code/package_factory/exp_wave{w}_designs.py"
            if not (ROOT / d).is_file():
                print(f"wave {w}: no design step to re-run")
                continue
            steps = [[d]]
        steps += [[f"02_shared_code/registry/record_wave{w}.py"]]
        if not a.no_assemble:
            # assembly is left out when the factory itself is about to change: rebuilding packages with code that is
            # being edited mid-run is how a mixed estate gets built, and the re-assembly can follow in one sweep
            steps.append(["02_shared_code/package_factory/wave_package.py", "--designs",
                          f"topic_designs_wave{w}", "--all"])
        if not a.apply:
            for s in steps:
                print("would run:", " ".join(s))
            continue
        # snapshot which artefact was kept before this wave ran, so the comparison is against what shipped
        before = {}
        for f in glob.glob(str(ROOT / "results_raw" / "EXP*.json")):
            m = re.match(r"(EXP\d{4})_", os.path.basename(f))
            if m and f not in retired:
                k = m.group(1)
                if k not in before or kept_at(f) > kept_at(before[k]):
                    before[k] = f
        aborted = False
        for s in steps:
            rc, tail = run(s)
            print(f"[{'ok ' if rc == 0 else 'ERR'}] {' '.join(s)}  ::  {(tail[-1] if tail else '')[:150]}",
                  flush=True)
            report.append({"cmd": " ".join(s), "rc": rc, "tail": (tail[-1] if tail else "")[:200]})
            if rc:
                aborted = True
                break
        if aborted:
            break
        for k, old_path in sorted(before.items()):
            if not pathlib.Path(old_path).is_file():
                continue                                  # retired and removed by another pass while we ran
            news = [f for f, mt in generations(os.path.basename(old_path).rsplit("_", 1)[0])
                    if f != old_path and mt > kept_at(old_path)]
            if not news:
                continue
            diffs, _, _ = C.compare(C.load(pathlib.Path(old_path)), C.load(pathlib.Path(news[-1])))
            est = [d[0] for d in diffs if ESTIMATE.search(d[0])]
            lab = sorted({d[0].split(".")[-1] for d in diffs if LABEL_OK.search(d[0])})
            other = [d[0] for d in diffs if d[0] not in est and d[0] not in lab]
            print(f"   {os.path.basename(old_path)[:44]} -> {os.path.basename(news[-1])[:44]}: "
                  f"{len(diffs)} field(s) changed, estimates moved {len(est)}, labels {lab[:6]}, other {len(other)}")
            report.append({"compare": os.path.basename(old_path), "against": os.path.basename(news[-1]),
                           "fields_changed": len(diffs), "estimates_moved": est[:30],
                           "labels_changed": lab, "other_changed": other[:30]})
    dest = ROOT / "results_raw" / "ROUND2_DESIGN_RERUN_REPORT.json"
    prev = json.loads(dest.read_text(encoding="utf-8")) if dest.is_file() else {"runs": []}
    prev["runs"].append({"applied": bool(a.apply), "waves": waves, "steps": report,
                         "at": datetime.datetime.now().isoformat(timespec="seconds")})
    dest.write_text(json.dumps(prev, indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote", dest.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
