"""Run the two-pass rebuild check for every package, exercising every step except the declared measurements.

`rebuild_two_pass_check.py` exercises one package's chain and takes heavy-step exclusions as `--skip` flags. Choosing
those flags by hand each round is how a re-verification quietly stops covering the newest generator, so the exclusions
live in `rebuild_heavy_steps.txt`: one script path per line, grouped under a `# P00x` header, with the reason stated in
that file. The rule is deliberately one-sided -

* a step is skipped only when this package's chain declares it and the list names it;
* every other step runs, including any step a future chain adds, so coverage cannot shrink by omission;
* a listed path that no chain declares any more is printed as stale rather than dropped, because that means the
  measurement it excludes has moved and the list has not followed.

    python 02_shared_code/registry/rebuild_all_rounds.py [--paper P004]
"""
from __future__ import annotations

import argparse, pathlib, re, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
PAPERS = sorted(p for p in (ROOT / "papers").glob("P0*") if p.is_dir())
LIST = HERE / "rebuild_heavy_steps.txt"
STEP = re.compile(r'^"\$PY"\s+(\S+)')


def heavy_by_package():
    out: dict[str, set] = {}
    group = "*"
    for ln in LIST.read_text(encoding="utf-8").splitlines():
        s = ln.strip()
        if not s:
            continue
        m = re.match(r"^#\s*(P\d\d\d)\s*$", s)
        if m:
            group = m.group(1)
            out.setdefault(group, set())
            continue
        if s.startswith("#"):
            continue
        out.setdefault(group, set()).add(s)
    return out


def declared(pkg: pathlib.Path):
    return [STEP.match(l.strip()).group(1) for l in (pkg / "reproduce.sh").read_text(encoding="utf-8").splitlines()
            if STEP.match(l.strip())]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", default="")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    heavy, bad, stale_total = heavy_by_package(), [], []
    for pkg in PAPERS:
        pid = pkg.name[:4]
        if a.paper and pid != a.paper:
            continue
        rounds = 0
        while True:
            steps = declared(pkg)
            skip = heavy.get(pid, set()) | heavy.get("*", set())
            hit = [s for s in steps if s in skip]
            stale_total += sorted(skip - set(steps) - heavy.get("*", set()))
            print(f"######## {pid}  ({len(steps) - len(hit)} of {len(steps)} chain steps exercised"
                  + (f", re-run {rounds} of 1" if rounds else "") + ")", flush=True)
            for s in hit:
                print(f"  skip (declared measurement): {s}", flush=True)
            cmd = [sys.executable, str(HERE / "rebuild_two_pass_check.py"), "--paper", pid]
            for s in hit:
                cmd += ["--skip", s]
            r = subprocess.run(cmd, cwd=ROOT)
            print(f"{pid} EXIT={r.returncode}", flush=True)
            # `reproduce.sh` is itself generated in three packages, so a round can exercise a list the chain has
            # already replaced: a step added to the builder is absent from the list read at the start of the round,
            # and "0 material differences" would then certify fewer steps than the package actually runs. Re-read the
            # chain and, if it moved, run the round again so the verdict covers the chain as it now stands.
            after = declared(pkg)
            if after != steps and rounds == 0:
                rounds += 1
                print(f"  {pid}: reproduce.sh changed during the round ({len(steps)} -> {len(after)} steps); "
                      f"re-running so the new steps are exercised", flush=True)
                continue
            if after != steps:
                print(f"  {pid}: reproduce.sh still moving after the re-run - the chain is not a fixed point",
                      flush=True)
                bad.append(pid + "(non-converging-chain)")
            elif r.returncode:
                bad.append(pid)
            break
    if stale_total:
        print(f"[rounds] STALE list entries (no chain declares them): {stale_total}")
    print(f"[rounds] packages with a non-zero exit: {bad or 'none'}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
