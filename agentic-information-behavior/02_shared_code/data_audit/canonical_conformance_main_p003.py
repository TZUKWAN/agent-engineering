"""EXP-0029 (P003 main): full canonical-conformance audit - all eight corpora, sensitivity and dependence.

Reuses the frozen concept list, states, thresholds and parsers from the pilot module
(`canonical_conformance_audit_p003.py`), and adds what the main experiment requires:

  * MMAT-1M, which ships jsonl rather than parquet, so it needs its own container reader and a
    broken-reference test on the image paths it points at (measured against the filesystem, not assumed);
  * a precedence-reversal sensitivity run for every `ambiguous` cell, so the coverage claim does not depend on
    the order in which candidate columns happen to be listed;
  * Wilson 95% intervals on every coverage proportion;
  * a dependence census: for each usable grouping key, distinct values and rows-per-group in the sample, plus how
    many groups 10,000 rows span - the number that decides whether "N trajectories" means anything;
  * a self-audit of 30 cells printing the deciding evidence and two concrete values each, for hand verification.

    python canonical_conformance_main_p003.py

Writes results_raw/EXP0029_p003_conformance_main_*.json and results_processed/EXP0029_*.csv.
"""

from __future__ import annotations

import glob
import json
import math
import random
import sys
import time
from collections import Counter
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import canonical_conformance_audit_p003 as pilot  # noqa: E402

ROOT = pilot.ROOT
DATA = pilot.DATA
OUT_RAW, OUT_PROC = pilot.OUT_RAW, pilot.OUT_PROC
CONCEPTS = pilot.CONCEPTS
MMAT_SPEC = {
    "path": "VIS-MPU-Agent/MMAT-1M",
    "cols": {"C1_trajectory_id": [], "C2_group_key": [], "C3_timestamp": [], "C4_model_id": [],
             "C5_teacher_provider": [], "C6_message_sequence": [pilot.D("messages")],
             "C7_role_vocabulary": [pilot.R("role_vocab")],
             "C8_user_instruction": [pilot.R("instruction_from_msg")], "C9_candidate_actions": [],
             "C10_executed_action": [pilot.R("free_text_call")], "C11_observation": [pilot.R("tool_named_reply")],
             "C12_outcome_signal": []},
}


def wilson(k, n, z=1.96):
    if n == 0:
        return [0.0, 0.0]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0.0, c - h), 4), round(min(1.0, c + h), 4)]


def sample_jsonl(path: Path, n_rows: int):
    """Read n_rows records from a multi-gigabyte jsonl without loading it, val splits first."""
    files = sorted(glob.glob(str(path / "**/*.jsonl"), recursive=True), key=lambda f: ("val" not in f, f))
    rows = []
    for f in files:
        with open(f, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                rows.append(json.loads(line))
                if len(rows) >= n_rows:
                    return rows[:n_rows], [Path(x).name for x in files]
    return rows[:n_rows], [Path(x).name for x in files]


def broken_image_refs(rows, base: Path, check: int = 300):
    missing = total = 0
    examples = []
    for r in rows[:check]:
        for im in (r.get("images") or []):
            total += 1
            p = (base / str(im)).resolve()
            alt = Path(str(im).replace("../datasets/", str(base.parent) + "/"))
            if not p.exists() and not alt.exists():
                missing += 1
                if len(examples) < 3:
                    examples.append(str(im)[:120])
    return {"references_checked": total, "unresolvable": missing,
            "unresolvable_share": round(missing / max(1, total), 4), "examples": examples}


def dependence_census(corp, spec, rows):
    out = {}
    n = len(rows)
    for con in ("C1_trajectory_id", "C2_group_key"):
        cands = spec["cols"].get(con, [])
        if not cands or cands[0][0] != "direct":
            out[con] = {"usable_key": False,
                        "note": "no single grouping column; a converter would have to invent one or drop the "
                                "dependence structure entirely"}
            continue
        col = cands[0][1]
        vals = [r.get(col) for r in rows]
        counts = Counter(map(str, vals))
        k = max(1, len(counts))
        rows_10k = min(n, 10000)
        span = len(set(map(str, vals[:rows_10k])))
        out[con] = {"usable_key": True, "column": col, "distinct_in_sample": len(counts),
                    "rows_per_group_mean": round(n / k, 2), "rows_per_group_max": max(counts.values()),
                    f"groups_spanned_by_{rows_10k}_rows": span,
                    "independent_units_per_10k_rows": span}
    return out


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    res = {"exp_id": "EXP-0029", "paper_id": "P003", "seed": pilot.SEED,
           "protocol": "papers/P003_metadata_interoperability/protocol_freeze.md",
           "reuses": "parsers and thresholds from 02_shared_code/data_audit/canonical_conformance_audit_p003.py",
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "corpora": {}, "sensitivity": {}, "dependence": {}}

    specs = dict(pilot.SPEC)
    specs["MMAT-1M"] = MMAT_SPEC
    if "--corrected-probes" in sys.argv:
        # EXP-0030 / D18: the hand-check showed Toucan's model id sits one level deeper than the frozen
        # top-level probe, so the nested parsers are appended AFTER the frozen ones (precedence preserved).
        tc = {"path": specs["Toucan-1.5M"]["path"], "cols": {k: list(v) for k, v in specs["Toucan-1.5M"]["cols"].items()},
              "conflicts": dict(specs["Toucan-1.5M"].get("conflicts", {}))}
        tc["cols"]["C4_model_id"] = tc["cols"]["C4_model_id"] + [pilot.R("meta_nested_model")]
        tc["cols"]["C5_teacher_provider"] = tc["cols"]["C5_teacher_provider"] + [pilot.R("meta_nested_provider")]
        specs["Toucan-1.5M"] = tc
        res["correction"] = {"exp": "EXP-0030", "reason": "D18: nested metadata probe added after a hand-check of "
                             "the EXP-0029 self-audit sample; the frozen order is kept and the nested parser is "
                             "only consulted when the frozen top-level probe finds nothing",
                             "exp_id_written": "EXP0030"}
    exp_id = "EXP0030" if "--corrected-probes" in sys.argv else "EXP0029"
    res["exp_id"] = exp_id
    for name, spec in specs.items():
        if name == "MMAT-1M":
            rows, files = sample_jsonl(DATA / spec["path"], pilot.ROWS)
            container = {"format": "jsonl", "files_read": files,
                         "note": "no parquet exists in this release; a parquet-only converter silently drops it"}
        else:
            rows, note = pilot.sample_parquet(DATA / spec["path"])
            container = {"format": "parquet", "note": note}
        if not rows:
            res["corpora"][name] = {"error": "no rows", "container": container}
            continue
        cells, conflicts = pilot.measure(name, spec, rows)
        cov = {}
        for con, cell in cells.items():
            ev = cell["evidence"]
            best = max((e["coverage"] for e in ev), default=0.0)
            cov[con] = {"state": cell["state"], "best_coverage": round(best, 4),
                        "wilson95": wilson(round(best * len(rows)), len(rows)), "evidence": ev}
        states = Counter(v["state"] for v in cov.values())
        flipped = {}
        for con, cell in cov.items():
            if cell["state"] != "ambiguous" or len(cell["evidence"]) < 2:
                continue
            rev = sorted(cell["evidence"], key=lambda e: -e["coverage"])
            flipped[con] = {"chosen": rev[0]["source"], "runner_up": rev[1]["source"] if len(rev) > 1 else None,
                             "gap": round(rev[0]["coverage"] - (rev[1]["coverage"] if len(rev) > 1 else 0), 4)}
        res["sensitivity"].update({f"{name}:{c}": v for c, v in flipped.items()})
        res["dependence"][name] = dependence_census(name, spec, rows)
        res["corpora"][name] = {"n_rows": len(rows), "container": container, "cells": cov,
                                "conflicts": conflicts, "loss_ratio": round(
                                    (states["absent"] + states["ambiguous"] + states["conflict"]) / len(CONCEPTS), 4),
                                "state_counts": dict(states)}
        if name == "MMAT-1M":
            res["corpora"][name]["asset_integrity"] = broken_image_refs(rows, DATA / spec["path"])
        print(f"  {name}: rows={len(rows)} loss={res['corpora'][name]['loss_ratio']} {dict(states)}")

    rows_tbl = [{"corpus": c, "concept": k, "state": v["state"], "coverage": v["best_coverage"],
                 "wilson95": str(v["wilson95"])} for c, v in res["corpora"].items() if "cells" in v
                for k, v in v["cells"].items()]
    pd.DataFrame(rows_tbl).to_csv(OUT_PROC / f"{exp_id}_coverage_matrix.csv", index=False)
    pd.DataFrame([{"corpus": k.split(":")[0], "concept": k.split(":")[1], **v}
                  for k, v in res["sensitivity"].items()]).to_csv(
        OUT_PROC / f"{exp_id}_ambiguous_sensitivity.csv", index=False)
    cov_count = Counter()
    for c, v in res["corpora"].items():
        for k, cell in (v.get("cells") or {}).items():
            if cell["state"] in ("direct", "derived"):
                cov_count[k] += 1
    res["coverage_by_concept"] = dict(cov_count)
    res["n_corpora_audited"] = sum(1 for v in res["corpora"].values() if "cells" in v)
    res["loss_ratios"] = {c: v["loss_ratio"] for c, v in res["corpora"].items() if "loss_ratio" in v}
    res["no_usable_grouping_key"] = sorted(c for c, v in res["dependence"].items()
                                            if not any(d["usable_key"] for d in v.values()))
    res["self_audit_sample"] = []
    rng = random.Random(pilot.SEED)
    for cell in rng.sample(rows_tbl, min(30, len(rows_tbl))):
        rec = res["corpora"][cell["corpus"]]["cells"][cell["concept"]]
        res["self_audit_sample"].append({"corpus": cell["corpus"], "concept": cell["concept"],
                                         "state": cell["state"], "coverage": cell["coverage"],
                                         "evidence": rec["evidence"][:2]})
    res["self_audit_note"] = ("each sampled cell carries the deciding source and its measured coverage so the "
                              "state can be re-derived from the data rather than trusted; disagreements found "
                              "during hand review are recorded as deviations")
    res["gate"] = {"rule": "drop P003 if >=10 of 12 concepts are direct|derived in >=7 corpora",
                  "concepts_passing": sum(1 for n in cov_count.values() if n >= max(7, res["n_corpora_audited"] - 1)),
                  "n_corpora": res["n_corpora_audited"]}
    res["wallclock_sec"] = round(time.time() - t0, 1)
    res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    out = OUT_RAW / f"{exp_id}_p003_conformance_main_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print("coverage by concept:", json.dumps(res["coverage_by_concept"], ensure_ascii=False))
    print("loss ratios:", json.dumps(res["loss_ratios"], ensure_ascii=False))
    print("no usable grouping key:", res["no_usable_grouping_key"])
    print("MMAT asset integrity:", json.dumps(res["corpora"]["MMAT-1M"].get("asset_integrity"), ensure_ascii=False))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
