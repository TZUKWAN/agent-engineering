"""Scratch driver: re-assemble every wave package from its shipped artefacts, then re-run the per-package chain.

Nothing here measures anything: `wave_package.py` reads the artefacts in `results_raw/` and rewrites the 20
deliverables, and the chain scripts re-export the figure plan, the embedded artefacts, the package registry view, the
configs README and the evidence reconciliation. It exists because the registry columns a reader judges a topic by
(`measured_coverage`, `collision_verdict`) are generated inside the assembly step, so fixing them estate-wide means
running the assembly estate-wide - and because a factory change is only trustworthy once every package has been
rebuilt with it and audited again.

    python _reassemble_all_waves.py [--only wave4] [--packages P023 ...]
"""
from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent
PY = sys.executable
FACTORY = "02_shared_code/package_factory"
# Derived, not listed: the constant stopped at wave 7 while waves 8-12 existed, so the estate rebuild the
# determinism check is supposed to prove silently skipped 25 packages. A list that has to be extended by hand
# always ends up one wave behind.
WAVES = [f"topic_designs_wave{n}" for n in
         sorted(int(p.stem.replace("topic_designs_wave", ""))
                for p in (ROOT / FACTORY).glob("topic_designs_wave*.py")
                if p.stem.replace("topic_designs_wave", "").isdigit())]
CHAIN = ["writing/export_figure_plan.py", "writing/embed_paper_artefacts.py",
         "registry/export_package_registry.py", "registry/build_package_configs_readme.py",
         "registry/reconcile_package_evidence.py"]


def run(args: list, log) -> int:
    t0 = time.time()
    p = subprocess.run([PY, "-u"] + args, stdout=log, stderr=subprocess.STDOUT, cwd=str(ROOT))
    log.flush()
    return p.returncode


def figures(mod: str, log) -> int:
    """Re-render each package's figures from the artefacts the register now keeps, before anything reads them.

    A figure is drawn once and afterwards only *copied* around: the assembly below rewrites documents, tables and the
    evidence folders, but no step re-drew the PDFs. So after a design re-pass retires generations, a package can ship
    a plot of a run the register no longer keeps. For waves 1-12 this round proved no plotted quantity moved (only
    words beside them), so nothing was mis-drawn - but the estate should not have to lean on that proof to know its
    figures are current. Blocked packages are skipped: they owe no figures, and `wave_figures.py` would fail on them.
    """
    import importlib
    importlib.invalidate_caches()
    sys.path.insert(0, str(ROOT / FACTORY))
    try:
        TD = importlib.import_module(mod)
    except Exception as e:                                        # noqa: BLE001 - reported by the assembly right after
        print(f"  figures skipped for {mod}: module will not import ({type(e).__name__})", file=log)
        return 0
    bad = 0
    for t in list(getattr(TD, "RUNNABLE", getattr(TD, "DESIGNS", {}))):
        d = (getattr(TD, "DESIGNS", {}) or {}).get(t) or {}
        pkg = d.get("pkg") or ""
        if not pkg or (ROOT / "papers" / pkg / "BLOCKED.md").is_file():
            continue
        if not (ROOT / "papers" / pkg / "figures").is_dir():
            continue
        rc = run([f"{FACTORY}/wave_figures.py", "--pkg", pkg, "--topic", t, "--design-module", mod], log)
        if rc:
            print(f"  !! wave_figures rc={rc} for {pkg}", file=log)
            bad += 1
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--packages", action="append", default=[])
    a = ap.parse_args()
    mods = [a.only] if a.only else WAVES
    fails = []
    for mod in mods:
        with open(ROOT / "logs" / f"reassemble_{mod}.log", "w", encoding="utf-8") as fh:
            nf = figures(mod, fh)
            rc = run([f"{FACTORY}/wave_package.py", "--designs", mod, "--all"], fh)
        print(f"{mod}: figures_failed={nf} assemble rc={rc}", flush=True)
        if rc:
            fails.append(mod)
            continue
    pkgs = a.packages or sorted(p.name[:4] for p in (ROOT / "papers").glob("P0*")
                                if p.name[:4] not in ("P001", "P002", "P003", "P004", "P005"))
    for p in pkgs:
        with open(ROOT / "logs" / f"chain_{p}_reassemble.log", "w", encoding="utf-8") as fh:
            for s in CHAIN:
                rc = run([f"02_shared_code/{s}", "--paper", p], fh)
                if rc and "embed_paper_artefacts" not in s:      # embed tolerates a paper without markers
                    print(f"{p} {s}: rc={rc}", flush=True)
                    fails.append(f"{p}/{s}")
        print(f"{p}: chain done", flush=True)
    print("FAILURES:", fails or "none", flush=True)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
