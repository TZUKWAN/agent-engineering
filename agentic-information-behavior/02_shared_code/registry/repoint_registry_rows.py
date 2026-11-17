"""Re-point registry rows at the artefact generation that survived a re-run, and prove the status still holds.

A wave re-run writes a new timestamped JSON, so `experiment_registry.csv` would otherwise cite a file that the
programme ledger has marked not-citable. `record_wave2.py` / `record_wave3.py` recompose their own rows from the
artefacts, but wave 1 was registered by one-off calls, so this closes the gap for every row generically: it finds
the newest kept generation for each `results_raw/*.json` the row cites, and before rewriting anything it checks that
the row's own status string still agrees with the verdicts inside the new file. A disagreement is a finding about the
measurement, not a bookkeeping detail, so the tool aborts rather than quietly republishing a stale claim.

    python 02_shared_code/registry/repoint_registry_rows.py [--exp EXP-0121 ...] [--apply]
"""
from __future__ import annotations

import argparse
import csv
import glob
import io
import json
import os
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
REG = ROOT / "00_program_registry" / "experiment_registry.csv"
LEDGER = ROOT / "results_raw" / "SUPERSEDED_ARTIFACTS.json"


def superseded() -> set:
    if not LEDGER.is_file():
        return set()
    return {e["file"] for e in json.loads(LEDGER.read_text(encoding="utf-8")).get("superseded", [])}


def verdict_tokens(status: str):
    """`H1_null_H3_opposite` -> {H1: null, H3: opposite}; a status without this shape yields nothing."""
    return dict(re.findall(r"(H\d)_(supported|null|opposite|partial)\b", status or ""))


def artefact_verdicts(d: dict) -> dict:
    out = {}
    for m in (d.get("models") or []):
        if isinstance(m, dict) and re.fullmatch(r"H\d", str(m.get("hypothesis") or "")):
            out[m["hypothesis"]] = str(m.get("verdict"))
    return out


def newest_kept(pattern: str, sup: set):
    hits = [f for f in glob.glob(str(ROOT / pattern)) if os.path.basename(f) not in sup]
    hits.sort(key=os.path.getmtime)
    return hits[-1] if hits else None


WAVE1 = tuple(f"EXP-01{n:02d}" for n in range(18, 34))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", action="append", default=[], help="restrict to these experiment ids "
                                                                "(default: the wave-1 rows, which no recorder owns)")
    ap.add_argument("--all-rows", action="store_true", help="scan every row instead of just the wave-1 ones")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    scope = set(a.exp) if a.exp else (None if a.all_rows else set(WAVE1))
    sup = superseded()
    rows = list(csv.DictReader(io.StringIO(REG.read_text(encoding="utf-8"))))
    hdr = list(rows[0].keys())
    changed, problems = 0, []
    for r in rows:
        if scope is not None and r["exp_id"] not in scope:
            continue
        outs = [o.strip() for o in (r.get("outputs") or "").split(";") if o.strip()]
        new_outs, touched, pointed = [], False, None
        for o in outs:
            if not (o.startswith("results_raw/") and o.endswith(".json")):
                new_outs.append(o)
                continue
            stem = re.sub(r"_?\d{8}T\d{6}", "", os.path.basename(o))
            # the stripped stem still ends in `.json`, so the wildcard has to go before the suffix
            cand = newest_kept("results_raw/" + stem.replace(".json", "*.json"), sup)
            if cand is None:
                problems.append(f"{r['exp_id']}: no kept generation for {stem}")
                new_outs.append(o)
                continue
            if os.path.basename(cand) != os.path.basename(o):
                d = json.loads(pathlib.Path(cand).read_text(encoding="utf-8"))
                want, have = verdict_tokens(r.get("status") or ""), artefact_verdicts(d)
                bad = {k: (v, have.get(k)) for k, v in want.items() if have.get(k) != v}
                if bad:
                    problems.append(f"{r['exp_id']}: kept generation {os.path.basename(cand)} says "
                                    f"{json.dumps(bad)} but the row's status claims the old verdicts")
                    new_outs.append(o)
                    continue
                new_outs.append("results_raw/" + os.path.basename(cand))
                pointed = pointed or d
                touched = True
            else:
                new_outs.append(o)
        if touched:
            changed += 1
            print(f"{r['exp_id']}: re-pointed -> {'; '.join(new_outs)[:110]}")
            r["outputs"] = "; ".join(new_outs)
            for k in ("started_at", "finished_at"):
                if pointed and pointed.get(k):
                    r[k] = str(pointed[k])
    print(f"\n{changed} row(s) re-pointed; problems: {len(problems)}")
    for p in problems:
        print("  ! " + p)
    if a.apply and changed:
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=hdr, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
        REG.write_text(buf.getvalue(), encoding="utf-8")
        print("registry written")
    elif not a.apply:
        print("(dry run; pass --apply to write)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
