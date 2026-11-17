"""Two-pass determinism check for the wave packages: re-run the generating layer and compare digests.

The programme's existing rebuild rounds skip the measured experiments (they are checked in, and re-running the encoder
would take longer than the round is worth), so this check covers the layer that *turns* measurements into deliverables:
tables, figures, the claims matrix, the package registry copy, the configs table, and every generated document. It runs
the chain twice over each package and compares SHA-256 per file, and it separately confirms that the analysis layer is
reproducible by re-running one topic's design on the frozen sample and comparing the printed coefficients.

    python 02_shared_code/package_factory/wave_determinism_check.py [--skip-analysis]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import wave_lib as W                                              # noqa: E402

ROOT = W.ROOT
PY = sys.executable
SKIP_DIRS = {"environment", "logs", "results_raw", "results_processed", "__pycache__"}
TOPICS = [("T101", "P006_underspecified_needs"), ("T103", "P007_constraint_density"),
          ("T106", "P008_query_reformulation_fidelity"), ("T108", "P009_lexical_match_bias"),
          ("T109", "P010_lexical_semantic_conflict"), ("T110", "P011_predicate_argument_relevance")]


def digests(pkg: pathlib.Path) -> dict:
    out = {}
    for f in sorted(pkg.rglob("*")):
        if not f.is_file() or any(part in SKIP_DIRS for part in f.relative_to(pkg).parts):
            continue
        if f.suffix.lower() not in {".md", ".csv", ".pdf", ".svg", ".txt", ".json", ".sh"}:
            continue
        out[str(f.relative_to(pkg)).replace("\\", "/")] = hashlib.sha256(f.read_bytes()).hexdigest()[:16]
    return out


def generate(topic: str) -> None:
    subprocess.run([PY, str(HERE / "wave_package.py"), "--topic", topic], check=True,
                   capture_output=True, cwd=str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-analysis", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    report = {"exp_id": "EXP-0134", "seed": W.SEED, "packages": {}, "started_at": W.now()}
    bad = 0
    for topic, pkgname in TOPICS:
        pkg = ROOT / "papers" / pkgname
        generate(topic)
        a = digests(pkg)
        (HERE.parent.parent / "_wave_snap" / topic).mkdir(parents=True, exist_ok=True)
        (ROOT / "_wave_snap" / f"{topic}_pass1.json").write_text(json.dumps(a, indent=1, sort_keys=True),
                                                                 encoding="utf-8")
        generate(topic)
        b = digests(pkg)
        diff = sorted([k for k in set(a) | set(b) if a.get(k) != b.get(k)])
        report["packages"][pkgname] = {"files": len(a), "second_pass_identical": not diff, "changed": diff[:12]}
        if diff:
            bad += 1
            print(f"  {pkgname}: {len(diff)} file(s) changed between passes: {diff[:6]}")
        else:
            print(f"  {pkgname}: {len(a)} files, second pass identical")
    if not args.skip_analysis:
        # the analysis layer: re-run one design on the frozen sample and compare the coefficients it prints
        import pandas as pd
        before = pd.read_csv(ROOT / "results_processed" / "EXP0121_t101_main_models.csv")
        env = dict(__import__("os").environ, AIB_ARTEFACT_DIR=str(ROOT / "_wave_snap" / "raw"),
                   AIB_PROCESSED_DIR=str(ROOT / "_wave_snap" / "proc"))
        (ROOT / "_wave_snap" / "raw").mkdir(parents=True, exist_ok=True)
        (ROOT / "_wave_snap" / "proc").mkdir(parents=True, exist_ok=True)
        subprocess.run([PY, str(HERE / "exp_wave1_query_level.py")], check=True, capture_output=True,
                       cwd=str(ROOT), env=env, timeout=5400)
        after = pd.read_csv(ROOT / "_wave_snap" / "proc" / "EXP0121_t101_main_models.csv")
        same = (before.shape == after.shape
                and all(abs(float(before.iloc[i][c]) - float(after.iloc[i][c])) < 1e-9
                        for i in range(len(before)) for c in ("beta", "se", "ci_lo", "ci_hi")))
        report["analysis_layer"] = {"design": "T101 full 24,000-row run re-executed into a scratch directory",
                                    "rows": int(len(before)), "coefficients_identical": bool(same)}
        print(f"  analysis layer re-run identical: {same}")
        if not same:
            bad += 1
    report["verdict"] = "DETERMINISTIC" if bad == 0 else f"{bad} package(s) or the analysis layer differ between passes"
    report["run_cost"] = W.run_cost_row("EXP-0134", t0, 0, 0, "two-pass generation check over the six wave packages")
    report["finished_at"] = W.now()
    p = W.write_raw("EXP-0134", "wave_determinism_two_pass", report)
    print(json.dumps(report["packages"], indent=1)[:600])
    print("wrote", p.name)
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
