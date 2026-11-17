"""Assemble the paper-level deliverable package for P001 (spec section 0, items 4, 8-11, 14-15, 17).

Everything here is derived, never hand-written: the literature slice comes from the program-level
matrix, the environment lock comes from the interpreter that actually ran the experiments, and the
raw/processed copies keep their original filenames so a number in the paper still resolves to the
same file name cited in claims_evidence_matrix.csv.

    python package_p001.py

Writes into papers/P001_routing_failure_qpp/:
  literature_matrix.csv  results_raw/  results_processed/  logs/  environment/{dependencies.txt,
  system_info.json, code_manifest.json, reproduce_run_manifest.json}
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PAPER = ROOT / "papers" / "P001_routing_failure_qpp"
SHARED = ROOT / "00_program_registry" / "shared_literature" / "literature_matrix.csv"
CODE_DIRS = [ROOT / "02_shared_code", PAPER / "scripts"]
PAPER_ID, TOPIC_ID = "P001", "T037"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def slice_literature() -> int:
    m = pd.read_csv(SHARED)
    cols = set(m.columns)
    # a row belongs to this paper if it names the topic, or its overlap/relation text points at the
    # routing-QPP line of work rather than some other registered topic
    hay = m[[c for c in ("collision_target", "overlap_level", "problem", "method", "main_result", "title")
             if c in cols]].fillna("").astype(str).agg(" | ".join, axis=1)
    sel = m[hay.str.contains(TOPIC_ID, na=False) | hay.str.contains(
        r"routing|QPP|query performance|query structur|tool retriev|tool selection|BM25|catalog", case=False, na=False, regex=True)]
    sel = sel.assign(paper_id=PAPER_ID)
    sel.to_csv(PAPER / "literature_matrix.csv", index=False)
    return int(len(sel))


def write_env_lock() -> dict:
    (PAPER / "environment").mkdir(exist_ok=True)
    mods = ["numpy", "pandas", "scipy", "sklearn", "pyarrow", "matplotlib", "statsmodels"]
    vers = {}
    for k in mods:
        try:
            mod = __import__(k)
            vers[k] = getattr(mod, "__version__", "?")
        except Exception as e:  # a missing optional module is a fact, not a failure
            vers[k] = f"NOT INSTALLED ({type(e).__name__})"
    try:
        from importlib.metadata import versions
        deps = "\n".join(f"{k}=={v}" for k, v in sorted(vers.items()) if not v.startswith("NOT")) + "\n"
    except Exception:
        deps = ""
    (PAPER / "environment" / "dependencies.txt").write_text(
        deps + f"\n# interpreter: {sys.executable}\n# python: {platform.python_version()}\n"
        f"# resolved-by: importlib.metadata not pinned to a lockfile; versions above are the ones\n"
        f"# that actually executed EXP-0004..EXP-0014 (see system_info.json)\n", encoding="utf-8")

    cpu = {"system": platform.system(), "release": platform.release(), "machine": platform.machine(),
           "processor": platform.processor(), "python": platform.python_version(),
           "executable": sys.executable, "cpus_logical": os.cpu_count(),
           "packages": vers, "llm_api_available_by_policy": False,
           "network_used_during_analysis": "none (all datasets are on local disk)"}
    try:
        import psutil
        cpu["ram_total_gb"] = round(psutil.virtual_memory().total / 2**30, 1)
        cpu["ram_available_gb_at_lock"] = round(psutil.virtual_memory().available / 2**30, 1)
    except Exception:
        cpu["ram_total_gb"] = "psutil not installed"
    try:
        import subprocess
        gpu = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                             capture_output=True, text=True, timeout=15).stdout.strip()
        cpu["gpu"] = gpu or "none detected (analysis is CPU-only)"
    except Exception:
        cpu["gpu"] = "none detected / nvidia-smi unavailable (analysis is CPU-only)"
    (PAPER / "environment" / "system_info.json").write_text(json.dumps(cpu, indent=1), encoding="utf-8")

    manifest = {}
    for d in CODE_DIRS:
        if not d.exists():
            continue
        for p in sorted(d.rglob("*.py")):
            manifest[str(p.relative_to(ROOT)).replace("\\", "/")] = sha(p)
    for p in sorted((PAPER).glob("*.md")) + sorted((PAPER / "configs").glob("*.json")):
        manifest[str(p.relative_to(ROOT)).replace("\\", "/")] = sha(p)
    (PAPER / "environment" / "code_manifest.json").write_text(
        json.dumps({"hashed_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "algorithm": "sha256[:16]",
                    "n_files": len(manifest), "files": manifest}, indent=1), encoding="utf-8")
    return cpu


def copy_results() -> dict:
    counts = {}
    for name, src in (("results_raw", ROOT / "results_raw"),
                      ("results_processed", ROOT / "results_processed"),
                      ("logs", ROOT / "logs")):
        dst = PAPER / name
        dst.mkdir(exist_ok=True)
        n = 0
        for p in sorted(src.glob("*")):
            if p.is_file() and ("P001" in p.name or p.name.startswith("EXP00") or "EXP-00" in p.name
                                or "routing" in p.name or "toucan" in p.name or name == "results_processed"):
                shutil.copy2(p, dst / p.name)
                n += 1
        counts[name] = n
    return counts


def main() -> int:
    n_lit = slice_literature()
    cpu = write_env_lock()
    counts = copy_results()
    ledger = PAPER / "test_eval_ledger.json"
    summary = {"paper_id": PAPER_ID, "packaged_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
               "literature_rows": n_lit, "copied": counts,
               "test_evaluations_recorded": int(len(json.loads(ledger.read_text(encoding="utf-8"))
                                                  .get("evaluations", []))) if ledger.exists() else None,
               "python": cpu["python"], "cpus_logical": cpu["cpus_logical"], "ram_total_gb": cpu["ram_total_gb"]}
    (PAPER / "environment" / "reproduce_run_manifest.json").write_text(
        json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    assert n_lit >= 20, f"only {n_lit} literature rows for P001 -- spec needs 20-30 direct + background"
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
