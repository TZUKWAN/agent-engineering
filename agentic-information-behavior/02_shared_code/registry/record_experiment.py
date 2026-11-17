"""Generic experiment recorder: one row per experiment in `00_program_registry/experiment_registry.csv`.

The programme carried ~60 one-off `record_expXXXX_*.py` scripts, one per experiment. That does not scale to the wave
packages and, worse, each new script was a new chance to write a row whose numbers did not come from the artefact.
This recorder reads the run's own JSON artefact and takes every field it can from it, so a row cannot claim a seed
or a timestamp the run did not use.

Rules it enforces:
* the artefact's `exp_id` must equal the row's - an artefact cannot be filed under a different experiment;
* `paper_id` must be `programme`, `P<digits>`, or a ';' join of those, which is what EXP-0078's vocabulary check
  (in `package_audit.registry_paper_id_vocabulary`) tests;
* re-running with the same `--exp` **replaces** the existing row instead of appending a duplicate, which is the
  failure mode EXP-0087 found in the log recorders;
* every non-derivable field must be passed explicitly, and `--notes` may not contain a phrase that defers the work
  to a person.

    python 02_shared_code/registry/record_experiment.py --exp EXP-0119 \
        --artefact 'results_raw/EXP0119_wave1_feature_matrix_*.json' \
        --paper P006;P007;P008;P009;P010;P011 --topic T101;T103;T108;T109;T110 \
        --stage wave1_feature_matrix --script 02_shared_code/package_factory/exp_wave1_features.py \
        --status-filed-by kill_gates_summary --status <value-in-artefact> \
        --config 'rows_per_config=8000; bucket=dev; seed=42' \
        --enters-paper 'no - shared instrument record' --notes 'why this run exists and what it settles'
"""
from __future__ import annotations

import argparse
import csv
import glob
import io
import json
import pathlib
import re
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
REG = ROOT / "00_program_registry" / "experiment_registry.csv"
COLS = ["exp_id", "paper_id", "stage", "script", "config", "seed", "started_at", "finished_at", "status",
        "outputs", "notes", "enters_paper", "topic_id"]
HUMAN_WORDS = ("pending human", "manual review", "to be checked by", "awaiting author", "需人工", "人工确认",
               "human check", "hand check pending")


def _dig(obj: dict, dotted: str):
    cur = obj
    for k in dotted.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def latest_artefact(pattern: str) -> pathlib.Path:
    p = pattern if pathlib.Path(pattern).is_absolute() else str(ROOT / pattern)
    hits = sorted(glob.glob(p.replace("\\", "/")))
    if not hits:
        raise SystemExit(f"ABORT: no artefact matches {pattern!r} - the experiment has not been run, "
                         f"so it cannot be registered")
    return pathlib.Path(max(hits, key=lambda f: pathlib.Path(f).stat().st_mtime)).resolve()


def validate(exp: str, paper: str, status: str, notes: str) -> None:
    if not re.fullmatch(r"EXP-\d{4}", exp):
        raise SystemExit(f"ABORT: --exp must look like EXP-0119, got {exp!r}")
    for tok in (t.strip() for t in paper.split(";")):
        if tok and not re.fullmatch(r"P\d{3}|programme", tok):
            raise SystemExit(f"ABORT: paper_id token {tok!r} is outside the registry vocabulary (EXP-0078)")
    if not status.strip():
        raise SystemExit("ABORT: an empty status would print as a green row in the audit")
    low = (notes + " " + status).lower()
    for w in HUMAN_WORDS:
        if w in low:
            raise SystemExit(f"ABORT: the row defers work to a person ({w!r}); the objective forbids "
                             f"human-dependent steps - run it or record the measured blocker")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", required=True)
    ap.add_argument("--artefact", action="append", required=True, help="glob, repeatable")
    ap.add_argument("--paper", required=True)
    ap.add_argument("--topic", default="programme")
    ap.add_argument("--stage", required=True)
    ap.add_argument("--script", required=True)
    ap.add_argument("--config", default="")
    ap.add_argument("--status", default=None)
    ap.add_argument("--status-filed-by", default=None, help="dotted artefact key holding the status string")
    ap.add_argument("--seed", default=None)
    ap.add_argument("--notes", default="")
    ap.add_argument("--enters-paper", default="yes - see the package documents")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    arts = [latest_artefact(p) for p in args.artefact]
    blob = [json.loads(a.read_text(encoding="utf-8")) for a in arts]
    for a, b in zip(arts, blob):
        if str(b.get("exp_id", "")).strip() and b["exp_id"] != args.exp:
            raise SystemExit(f"ABORT: {a.name} records exp_id={b['exp_id']!r}, not {args.exp!r}")
    status = args.status
    if args.status_filed_by:
        vals = [str(_dig(b, args.status_filed_by)) for b in blob if _dig(b, args.status_filed_by) is not None]
        if not vals:
            raise SystemExit(f"ABORT: key {args.status_filed_by!r} is not in the artefact, so the status "
                             f"would have been invented")
        status = vals[0]
    seed = args.seed
    if seed is None:
        s = {str(b.get("seed")) for b in blob if b.get("seed") is not None}
        seed = "; ".join(sorted(s)) if s else "n/a (deterministic)"
    started = [str(b.get("started_at")) for b in blob if b.get("started_at")]
    finished = [str(b.get("finished_at")) for b in blob if b.get("finished_at")]
    outputs = "; ".join(str(a.relative_to(ROOT)).replace("\\", "/") for a in arts)
    extra = []
    for b in blob:
        for o in (b.get("outputs") or []):
            if isinstance(o, str) and o not in outputs:
                extra.append(o.replace("\\", "/"))
    outputs = "; ".join([outputs] + sorted(set(extra)))
    validate(args.exp, args.paper, status or "", args.notes)

    row = {"exp_id": args.exp, "paper_id": args.paper, "stage": args.stage, "script": args.script,
           "config": args.config, "seed": seed,
           "started_at": min(started) if started else "", "finished_at": max(finished) if finished else "",
           "status": status, "outputs": outputs, "notes": args.notes,
           "enters_paper": args.enters_paper, "topic_id": args.topic}
    text = REG.read_text(encoding="utf-8")
    rows = list(csv.DictReader(io.StringIO(text)))
    hdr = list(rows[0].keys())
    if hdr != COLS:
        raise SystemExit(f"ABORT: registry columns changed shape: {hdr}")
    n_before = len(rows)
    rows = [r for r in rows if r["exp_id"] != args.exp]
    replaced = n_before - len(rows)
    rows.append({c: row[c] for c in COLS})
    rows.sort(key=lambda r: r["exp_id"])
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLS, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({c: str(r.get(c) or "") for c in COLS})
    REG.write_text(buf.getvalue(), encoding="utf-8", newline="")
    print(f"{args.exp}: {'replaced 1 row' if replaced else 'appended'} "
          f"(registry now {len(rows)} rows) | status={status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
