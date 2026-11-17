"""Append the measured catalogue-sharing limitation to the five papers whose strata are the Toucan configs.

EXP-0150 measured that 95.4% of the distinct tool descriptions in the dev sample occur in more than one config, with
one description recurring in 1,590 of 12,000 rows. That does not invalidate any of these papers - the numbers are what
they are - but it changes what a "consistent across OSS, Qwen3 and Kimi-K2" sentence can mean: three configs reading
the same catalogue text are one text three times, so the config split is a heterogeneity check on the same material,
not a replication on independent material.

The papers' own `limitations.md` files are hand-authored (no generator rewrites them), so this recorder is the safe
way to put a measured fact into them: it is idempotent - a file that already carries the marker is left untouched -
and it takes both numbers from the artefact rather than from this sentence.

    python 02_shared_code/registry/record_catalogue_sharing_limitation.py [--check]
"""
from __future__ import annotations

import argparse
import glob
import json
import pathlib
import re
import sys

ROOT = next(a for a in [pathlib.Path(__file__).resolve().parent,
                        *pathlib.Path(__file__).resolve().parents] if (a / "00_program_registry").is_dir())
MARK = "EXP-0150"
TOUCH = ("P001_routing_failure_qpp", "P002_isp_stage_measurement", "P003_metadata_interoperability",
         "P004_shipped_quality_score_validity", "P005_governance_metadata_verifiability")


def paragraph(m):
    sh = m.get("share_of_descriptions_shared_across_configs")
    reuse = m.get("most_reused_description_row_count")
    n = m.get("sample_rows")
    return (f"\n## L99 Configs are not independent samples of catalogue text ({MARK}, measured)\n\n"
            f"{sh:.4f} of the distinct tool descriptions in a seeded sample of {n:,} dev rows occur in more than one "
            f"config, and the single most reused description appears in {reuse:,} rows "
            f"(`results_raw/`{MARK}_catalogue_sharing*, `02_shared_code/registry/measure_catalogue_sharing.py`). "
            "The consequence is stated once and applies to every per-config table in this package: the config split "
            "is a heterogeneity check on the same catalogue material, not a replication on independent material, and "
            "no conclusion in this paper rests on treating it as the latter.\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report what would be written and change nothing")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    f = sorted(glob.glob(str(ROOT / "results_raw" / "EXP0150_catalogue_sharing_*.json")))
    if not f:
        raise SystemExit(f"ABORT: {MARK} has not run, so there is no measured share to record. Run "
                         f"02_shared_code/registry/measure_catalogue_sharing.py first.")
    art = json.loads(pathlib.Path(f[-1]).read_text(encoding="utf-8"))
    m = art.get("measurement") or {}
    for k in ("share_of_descriptions_shared_across_configs", "most_reused_description_row_count", "sample_rows"):
        if m.get(k) is None:
            raise SystemExit(f"ABORT: the {MARK} artefact has no {k!r}; refusing to write a limitation with a blank")
    text = paragraph(m)
    changed = 0
    for pkg in TOUCH:
        p = ROOT / "papers" / pkg / "limitations.md"
        if not p.is_file():
            print(f"  {pkg}: no limitations.md - skipped, not created")
            continue
        t = p.read_text(encoding="utf-8")
        if MARK in t:
            print(f"  {pkg}: already carries the {MARK} limitation")
            continue
        if not a.check:
            p.write_text(t.rstrip() + "\n" + text, encoding="utf-8")
        changed += 1
        print(f"  {pkg}: {'would append' if a.check else 'appended'} the measured limitation")
    if a.check:
        print("--check: nothing written")
        return 0
    print(f"{MARK}: share={m['share_of_descriptions_shared_across_configs']} reuse={m['most_reused_description_row_count']}"
          f" | {changed} file(s) updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
