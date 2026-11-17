"""Two-pass rebuild check: run a package's own chain twice and say whether the second run reproduces the first.

`rebuild_determinism.py` compares a package against a snapshot; this driver produces the two states to compare by
executing the steps the package's `reproduce.sh` names. It reads the script rather than keeping its own list of steps,
so a step added to `reproduce.sh` is exercised here automatically and a step removed from it cannot be quietly skipped.

    python 02_shared_code/registry/rebuild_two_pass_check.py --paper P004 [--skip dataset_build --skip main]

Heavy acquisition/training steps are excluded by `--skip` patterns (the point of the check is whether the package's
*documents and tables* regenerate identically, and re-running a 40-minute dataset build to find out would be a different
experiment). Skipped steps are printed, never dropped silently: the report says which part of the chain the verdict
covers. A step that exits non-zero aborts the pass and is reported as a failure of the chain, not of the comparison.
"""
from __future__ import annotations
import argparse, json, pathlib, re, subprocess, sys, time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
STEP = re.compile(r'^"\$PY"\s+(\S+)(.*)$')


def steps(pkg_dir: pathlib.Path, skips):
    sh = (pkg_dir / "reproduce.sh")
    if not sh.is_file():
        raise SystemExit(f"ABORT: {sh} not found - the package has no chain to exercise")
    txt = sh.read_text(encoding="utf-8", errors="replace")
    run, skipped, in_heredoc = [], [], False
    for ln in txt.splitlines():
        if ln.startswith('<<"') or ln.startswith("<<'") or ln.startswith("<<-"):
            in_heredoc = True
            continue
        if in_heredoc:
            if ln.strip().upper() in ("PYEOF", "EOF", "PY"):
                in_heredoc = False
            continue
        m = STEP.match(ln.strip())
        if not m:
            continue
        script, rest = m.group(1), m.group(2).strip()
        if script.startswith("-"):
            # `"$PY" - <<'EOF'` and `"$PY" -c "..."` run code that is written into the script itself; a step cannot be
            # re-invoked as a file path, and treating `-c` as a script aborted the pass with a SyntaxError
            in_heredoc = rest.startswith("<<")
            skipped.append(("(inline block " + (rest or script)[:30] + ")", "", "inline-stdin"))
            continue
        rest = re.split(r"\s#|#", rest, 1)[0].strip()      # a trailing shell comment is not an argument
        cmd = [str(ROOT / script)] + ([a for a in re.split(r"\s+", rest) if a] if rest else [])
        hit = next((s for s in skips if s in script), "")
        (skipped if hit else run).append((script, rest, hit))
    if not run:
        raise SystemExit(f"ABORT: no steps parsed from {sh.name}")
    return run, skipped


def execute(cmd, tag):
    env = {"AIB_PYTHON": sys.executable, "PATH": str(pathlib.Path(sys.executable).parent) + ":"
                                                           + str(pathlib.Path(sys.executable).parent / "Scripts"),
           "SYSTEMROOT": str(pathlib.Path("C:/Windows")), "PYTHONIOENCODING": "utf-8",
           "HOME": str(pathlib.Path.home())}
    import os
    env = {**os.environ, **env}
    p = subprocess.run([sys.executable] + cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8",
                       env=env)
    tail = ((p.stdout or "") + (p.stderr or "")).strip().splitlines()[-2:]
    print(f"    {'' if p.returncode == 0 else 'FAILED '}{cmd[0].split('/')[-1]} {p.returncode and '| ' + ' / '.join(tail)}")
    return p.returncode


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", required=True)
    ap.add_argument("--skip", action="append", default=[], help="substring of a script path to leave out of the check")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    pkg = next(p for p in sorted((ROOT / "papers").glob("P0*")) if p.name.startswith(a.paper))
    run, skipped = steps(pkg, a.skip)
    print(f"  {a.paper}: {len(run)} steps to exercise"
          + (f"; skipped {len(skipped)}: " + ", ".join(s[0].split('/')[-1] + f"({s[2]})" for s in skipped)
             if skipped else ""))
    for passno in (1, 2):
        print(f"  pass {passno}")
        for script, rest, _hit in run:
            cmd = [script] + ([x for x in re.split(r"\s+", rest) if x] if rest else [])
            if execute(cmd, script):
                print(f"  ABORT: pass {passno} failed at {script} - the chain itself is broken, not just its output")
                return 1
        snap = ROOT / "results_raw" / "snapshots" / f"{a.paper}_two_pass_{passno}.json"
        subprocess.run([sys.executable, str(HERE / "rebuild_determinism.py"), "--dir", str(pkg),
                        "--save", str(snap)], cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8")
    out = subprocess.run([sys.executable, str(HERE / "rebuild_determinism.py"), "--dir", str(pkg),
                          "--against", str(ROOT / "results_raw" / "snapshots" / f"{a.paper}_two_pass_1.json")],
                         cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8")
    for ln in (out.stdout or "").splitlines():
        if not ln.strip().startswith("P0"):
            print("   ", ln)
    # Record the invocation next to the snapshots it produced. A "0 material" verdict is only evidence if someone can
    # run the same chain: which steps were exercised and which were skipped is part of the claim, not a detail of one
    # terminal session.
    (snap.parent / f"{a.paper}_two_pass_invocation.json").write_text(
        json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "argv": sys.argv, "interpreter": sys.executable,
                    "steps_exercised": [[s, r] for s, r, _ in run],
                    "steps_skipped": [[s, why] for s, _r, why in skipped],
                    "exit_code": out.returncode,
                    "verdict": [ln.strip() for ln in (out.stdout or "").splitlines() if "verdict" in ln]},
                   indent=1, ensure_ascii=False), encoding="utf-8")
    return out.returncode


if __name__ == "__main__":
    sys.exit(main())
