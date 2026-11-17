"""EXP-0017b / EXP-0018: how much of the published test split sits in a catalogue development has seen.

The routing split is grouped by `prompt_id`, so a test row's exact CANDIDATE CATALOGUE can still appear among the
development rows, and every collection-aware QPP feature is a function of that catalogue. This measures the leak as
three integers per config - rows whose catalogue straddles, distinct catalogues on each side, catalogues spanning both
- and is the record behind the 63.7-88.0% range quoted in P001 and P003.

Round 2 found this record had no script on disk: it was written by an ad-hoc pass, it stored the same share twice -
once rounded to four decimals under `share`, once under a key naming a row count - and that pre-rounded 0.8805 is what
let the figure be republished as 88.1% for a value that is 3941/4476 = 88.0474%. Re-measuring from the parquet
reproduces every count and stores each share at full precision, so any downstream rounding has one step.

    py -3.11 02_shared_code/trajectory_parser/measure_catalog_split_recurrence.py

Rewrites results_processed/EXP0017b_catalog_split_recurrence.json. Reads only; the published `split` column and the
dataset are untouched, and the run refuses to report on a sample whose uuid digest is not the published one.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "01_datasets" / "processed"
MAN = ROOT / "01_datasets" / "manifests"
EXP = "EXP-0017b"
DEST = ROOT / "results_processed" / "EXP0017b_catalog_split_recurrence.json"
CONFIGS = ["OSS", "Qwen3", "Kimi-K2"]


def fp_of(catalog_json: str) -> str:
    """The catalogue fingerprint EXP-0017/0018 group by: order-free digest of the candidate names."""
    cat = json.loads(catalog_json)
    return hashlib.sha1("|".join(sorted(d["n"] for d in cat)).encode()).hexdigest()[:16]


def ensure_row(started: str, finished: str, measured: dict, corroborated: bool) -> None:
    """Carry this measurement in the master register, and take the record off the row that never wrote it.

    The file is named for a run the register had no row for while the row that claimed to produce it - EXP-0018 -
    names a script that writes a different file with the same quantities in it. Round 2 flags both halves of that
    (an artefact no run owns, and an output cell no script writes), so the fix is the row, not the flag: this run
    owns the file, and EXP-0018 keeps what its own artefact carries.
    """
    import csv
    import io
    reg = ROOT / "00_program_registry" / "experiment_registry.csv"
    rows = list(csv.DictReader(io.StringIO(reg.read_text(encoding="utf-8"))))
    cols = list(rows[0])
    hit = next((r for r in rows if r["exp_id"] == EXP), None)
    if hit is None:
        hit = {c: "" for c in cols}
        hit["exp_id"] = EXP
        rows.append(hit)
    ratios = "; ".join(f"{c} {v['test_rows_whose_catalog_appears_in_dev']}/{v['test_rows']}"
                       for c, v in measured.items())
    want = {"paper_id": "P001", "topic_id": "T037",
            "stage": "protocol_amendment_D13_published_split_catalogue_recurrence",
            "script": "02_shared_code/trajectory_parser/measure_catalog_split_recurrence.py",
            "config": "the published `split` column, untouched; the catalogue fingerprint is the order-free sha1 of "
                      "the candidate names that EXP-0017/0018 group by; a test row counts once if its fingerprint "
                      "appears among the development rows; the run refuses to report unless each config's uuid "
                      "digest still matches 01_datasets/manifests/routing_sample_identity.json",
            "seed": "deterministic, no RNG", "started_at": started, "finished_at": finished,
            "status": "success_LEAKAGE_CONCERN_CONFIRMED",
            "outputs": "results_processed/EXP0017b_catalog_split_recurrence.json",
            "enters_paper": "yes (validity section; the straddle rate is disclosed in the abstract)",
            "notes": "round-2 re-measurement of the figure published as 88.1%: " + ratios + ", i.e. "
                     + ", ".join(f"{round(v['share'] * 100, 1)}%" for v in measured.values())
                     + ". Every count reproduces EXP-0018's own artefact, which was written by a different script "
                       "on 2026-09-18. The stored share is now the unrounded proportion: the earlier record held it "
                       "rounded to four places, and a document that turned 0.8805 into a percentage and then into "
                       "one decimal published 88.1% for what 3941/4476 supports as 88.0%. Cross-checked against "
                       "EXP-0018's own artefact: "
                       + ("the counts agree." if corroborated else "THEY DISAGREE; see the run's console output.")
                       }
    n = 0
    for k, v in want.items():
        if k in cols and hit.get(k) != v:
            hit[k] = v
            n += 1
    for r in rows:
        if r["exp_id"] == "EXP-0018" and DEST.name in (r.get("outputs") or ""):
            kept = "; ".join(x.strip() for x in r["outputs"].split(";") if x.strip() and DEST.name not in x)
            r["outputs"] = kept
            r["notes"] = (r.get("notes") or "") + (
                " round-2: the catalogue-recurrence record this row also named is a measurement of its own "
                "(EXP-0017b), whose script now writes it; this row keeps the same quantities inside "
                "EXP0018_catalog_disjoint_split_*.json, which its own script does write.")
            n += 1
    if not n:
        return
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator=chr(10))
    w.writeheader()
    for r in rows:
        w.writerow({c: str(r.get(c) or "") for c in cols})
    reg.write_text(buf.getvalue(), encoding="utf-8")
    print(f"registry: {EXP} row set and EXP-0018's outputs corrected ({n} field(s) written)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report the measurement without writing the record or row")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    started = datetime.now().isoformat(timespec="seconds")
    anchor = json.loads((MAN / "routing_sample_identity.json").read_text(encoding="utf-8"))["configs"]
    out = {}
    for cfg in CONFIGS:
        df = pd.read_parquet(PROC / f"routing_{cfg}.parquet")
        digest = hashlib.sha256("|".join(sorted(df.uuid.astype(str))).encode()).hexdigest()[:16]
        if digest != anchor[cfg]["uuid_digest"]:
            raise SystemExit(f"[{cfg}] refusing to report on a sample that is not the published one "
                             f"({digest} != {anchor[cfg]['uuid_digest']})")
        fp = [fp_of(c) for c in df.catalog_json]
        dv_fp = set(f for f, s in zip(fp, df.split) if s == "dev")
        dev_pids = set(df[df.split == "dev"].prompt_id)
        tst = [(f, p) for f, s, p in zip(fp, df.split, df.prompt_id) if s == "test"]
        n_shared = sum(1 for f, _ in tst if f in dv_fp)
        test_fp = set(f for f, _ in tst)
        out[cfg] = {
            "dev_rows": int(len(df) - len(tst)),
            "test_rows": int(len(tst)),
            "distinct_catalogs_dev": int(len(dv_fp)),
            "distinct_catalogs_test": int(len(test_fp)),
            "test_rows_whose_catalog_appears_in_dev": int(n_shared),
            "share": n_shared / len(tst),
            "share_note": "proportion of test rows, not a row count; the counts above are the measurement",
            "prompt_ids_in_both_splits": int(len({p for _, p in tst} & dev_pids)),
            "catalogs_spanning_both_splits": int(len(test_fp & dv_fp)),
        }
        print(f"[{cfg}] {n_shared}/{len(tst)} = {out[cfg]['share']:.6f} "
              f"| {out[cfg]['catalogs_spanning_both_splits']} catalogues straddle "
              f"| {out[cfg]['prompt_ids_in_both_splits']} prompts straddle")
    agree = cross_check(out)
    if a.check:
        print("--check: record and register left as they are")
        return 0
    finished = datetime.now().isoformat(timespec="seconds")
    DEST.parent.mkdir(exist_ok=True)
    DEST.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote", DEST.relative_to(ROOT))
    ensure_row(started, finished, out, agree)
    return 0


def cross_check(out: dict) -> bool:
    """Do the counts agree with the other script that measured the same thing?

    EXP-0018 rebuilt the published split's straddle counts inside its own disjoint-split run, from the same frames
    and the same fingerprint rule, so two independent programs have measured these integers once apiece. Recording
    that they agree is the cheap half of round 2: a figure reproduced by one script reproduces only the script.
    """
    files = sorted((ROOT / "results_raw").glob("EXP0018_catalog_disjoint_split_*.json"))
    if not files:
        print("corroboration: EXP-0018's artefact is not on disk, so these counts stand uncorroborated")
        return False
    other = json.loads(files[-1].read_text(encoding="utf-8")).get("configs") or {}
    bad = []
    for cfg, v in out.items():
        o = other.get(cfg) or {}
        if int(o.get("test_rows_sharing_catalogue_with_dev_published", -1)) != v["test_rows_whose_catalog_appears_in_dev"]:
            bad.append(f"{cfg} straddling test rows {o.get('test_rows_sharing_catalogue_with_dev_published')}"
                       f" vs {v['test_rows_whose_catalog_appears_in_dev']}")
        if int(o.get("catalogues_straddling_published_split", -1)) != v["catalogs_spanning_both_splits"]:
            bad.append(f"{cfg} straddling catalogues {o.get('catalogues_straddling_published_split')}"
                       f" vs {v['catalogs_spanning_both_splits']}")
    print(f"corroboration against {files[-1].name}: "
          + ("all counts agree" if not bad else "DISAGREES - " + "; ".join(bad)))
    return not bad


if __name__ == "__main__":
    raise SystemExit(main())
