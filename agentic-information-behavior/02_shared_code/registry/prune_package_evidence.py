"""Round-2 maintenance: make every package's evidence folders hold exactly what the register resolves to.

The factory's `mirror_evidence` now copies in the kept generation of each run a package registers or cites, and
deletes the copies an earlier pass left behind. The five hand-built packages (P001-P005) are not assembled by the
factory, so they kept the older state: P001's `results_raw/` held 71 retired generations of EXP-0099 - the
programme's own completion audit, re-run each time the estate changed - while the generation its register names was
absent, and copies of runs it never cites sat beside them.

This runs the same resolution for those packages, through the same function the factory uses, and refuses to delete
a file whose only copy is inside the package: every deletion must still exist in the programme's own results folders,
so the history stays where the estate keeps history.

    python 02_shared_code/registry/prune_package_evidence.py [--paper P001 ...] [--apply]
"""
from __future__ import annotations

import argparse
import csv
import datetime
import io
import json
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
sys.path.insert(0, str(ROOT / "02_shared_code" / "package_factory"))
import wave_package as P                                                    # noqa: E402

REG = ROOT / "00_program_registry" / "experiment_registry.csv"
EXP = "EXP-0231"
ROW = {"paper_id": "programme",
       "stage": "round2_package_evidence_reconciliation",
       "script": "02_shared_code/registry/prune_package_evidence.py",
       "config": "every package under papers/ (`--all`), or the ones named with `--paper`; each run is resolved "
                 "against the master register and the supersession ledger, no measurement is taken, and no file is "
                 "deleted that the programme's own results folders do not still hold",
       "seed": "n/a (a read-and-copy maintenance pass)",
       "status": "evidence_reconciled",
       "outputs": "results_raw/EXP0231_package_evidence_remirror_*.json",
       "enters_paper": "no",
       "notes": "round-2: the packages' evidence folders were holding 13,097 copies that the register does not "
                "resolve to - retired generations and other papers' runs - because the mirror step copied by name "
                "and never removed what an earlier pass left. The factory's `package_evidence()` now both copies "
                "and prunes; this runs the same function over every package, which is the only path that "
                "reconciles the five hand-built ones, and it is a step of `_round2_final_chain.py`. Applying it "
                "estate-wide also copies in what a package cites and never held: the ten premise-gated packages "
                "name the censuses that stopped them while shipping no evidence folder at all."}


def ensure_row(started: str, finished: str) -> int:
    """Carry this run in the master register before it writes, so the artefact is never the only record of it."""
    rows = list(csv.DictReader(io.StringIO(REG.read_text(encoding="utf-8"))))
    cols = list(rows[0])
    hit = next((r for r in rows if r["exp_id"] == EXP), None)
    if hit is None:
        hit = {c: "" for c in cols}
        hit["exp_id"] = EXP
        rows.append(hit)
    n = 0
    for k, v in ROW.items():
        if hit.get(k) != v:
            hit[k] = v
            n += 1
    for k, v in (("started_at", started), ("finished_at", finished)):
        if hit.get(k) != v:
            hit[k] = v
            n += 1
    if not n:
        return 0
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator=chr(10))
    w.writeheader()
    for r in rows:
        w.writerow({c: str(r.get(c) or "") for c in cols})
    REG.write_text(buf.getvalue(), encoding="utf-8")
    print(f"registry: EXP-0231 row set ({n} field(s) written)")
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", action="append", default=[])
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--all", action="store_true", help="every package, to re-verify the factory's own rule")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    paps = sorted(p for p in (ROOT / "papers").glob("P0*") if p.is_dir())
    if a.paper and not a.all:
        paps = [p for p in paps if p.name[:4] in set(a.paper)]
    source = {p.name for sub in ("results_raw", "results_processed", "logs")
              for p in (ROOT / sub).rglob("*") if p.is_file()}
    started = datetime.datetime.now().isoformat(timespec="seconds")
    if a.apply:
        ensure_row(started, started)                    # the register carries the run before the run writes
    rows, unsourced = [], []
    for pap in paps:
        r = P.package_evidence(pap, copy=a.apply)
        r["package"] = pap.name
        for f in r["deleted"]:
            if pathlib.Path(f).name not in source:
                unsourced.append(f"{pap.name}/{f}")
        rows.append(r)
        print(f"{pap.name[:40]:40s} {'applied' if a.apply else 'dry-run '} "
              f"resolved={r['copied_in']:4d} selected={r['selected']:4d} prune={len(r['deleted']):4d} "
              f"named_by_a_doc={len(r['kept_by_name']):2d} "
              f"(register {r['runs_registered']}, cited {r['runs_cited']})")
        for x in r["kept_by_name"][:3]:
            print(f"    named but unresolved: {x}")
    payload = {"exp_id": "EXP-0231", "seed": "n/a (a read-and-copy maintenance pass)",
               "applied": bool(a.apply), "packages": len(rows),
               "deletions_without_a_programme_copy": unsourced,
               "started_at": datetime.datetime.now().isoformat(timespec="seconds"),
               "invocation": " ".join([sys.executable] + sys.argv), "detail": rows}
    if unsourced:
        payload["aborted"] = ("a file the resolution does not select has no copy in the programme's own results "
                              "folders, so deleting it would destroy the only record of a run")
        print(json.dumps(payload["aborted"]) + ": " + ", ".join(unsourced[:5]))
        return 2
    if a.apply:
        dest = ROOT / "results_raw" / f"EXP0231_package_evidence_remirror_{time.strftime('%Y%m%dT%H%M%S')}.json"
        dest.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
        print("wrote", dest.name)
    else:
        print(json.dumps({k: payload[k] for k in ("packages", "deletions_without_a_programme_copy")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
