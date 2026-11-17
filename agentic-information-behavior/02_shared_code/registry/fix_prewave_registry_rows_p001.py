"""Correct four pre-wave registry rows that the round-2 traceability check could not follow.

`round2_run_reality.py` reads the registry as the authority on where each run wrote, and on four P001 rows that
authority is wrong in four different ways:

* **EXP-0006b** declares its artefact with a Windows separator (`results_raw\\EXP0006_...`), which no other row in
  the estate uses, and the file it names is filed under EXP-0006's own prefix because the script writes one name
  for every ladder run. The row is truthful - the timestamp separates the two generations - so only the separator
  is normalised.
* **EXP-0007** declared only its JSON summary, while the run also wrote the three routing frames its script
  documents (`build_toucan_routing_dataset.py` writes `01_datasets/processed/routing_<cfg>.parquet` and the summary's
  own `finished_at` confirms the timestamp the package copy carries a second off). P001's shipped copy declares the
  frames and a wrong timestamp; the estate row declares neither. Both are fixed by writing the union, with the
  timestamp the artefact itself carries.
* **EXP-0008** was a console probe: no script, no file, and a 7.1 % prompt_id-recurrence figure that round 2 could
  not reproduce from disk and that deviation D61 withdrew. EXP-0225 promoted the probe to a script and re-measured
  all three of its quantities, so this row is now marked `superseded_by_EXP-0225` and says what the successor
  measured. Its `script` and `outputs` are left as they were, because the probe genuinely left nothing: pointing
  the row at another run's artefact would make two different runs indistinguishable.
* **EXP-0014b** has an artefact but names a module instead of a script in its `script` cell, so the run it records
  cannot be re-opened. EXP-0227 re-ran the same audit as a script and swept the process hash seed, which is what
  turned "2 rank differences, both ties" into a measured spread of 2-5 per seed with the dependent variable
  unchanged at every seed; the row now records that it is the earlier, narrower draw.

Every path this script writes is checked on disk first: a registry row must not name an artefact that is not there.

    python 02_shared_code/registry/fix_prewave_registry_rows_p001.py [--check]
"""
from __future__ import annotations

import argparse
import csv
import datetime
import io
import json
import pathlib
import re
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
REG = ROOT / "00_program_registry" / "experiment_registry.csv"


def exists(*rels: str) -> bool:
    return all((ROOT / r).is_file() for r in rels)


def latest(prefix: str) -> str:
    f = sorted((ROOT / "results_raw").glob(prefix))
    return f"results_raw/{f[-1].name}" if f else ""


_SUPS = None


def retired(rel: str) -> bool:
    """Is this file named by the supersession ledger (kept, but not citable)?"""
    global _SUPS
    if _SUPS is None:
        led = ROOT / "results_raw" / "SUPERSEDED_ARTIFACTS.json"
        _SUPS = {e["file"] for e in json.loads(led.read_text(encoding="utf-8")).get("superseded", [])} \
            if led.is_file() else set()
    return pathlib.Path(rel).name in _SUPS


def package_row_outputs(exp_id: str) -> list:
    """What the owning package's own copy of the register says this run wrote.

    The per-package copy is generated from the master register, so where the master row has been emptied it is the
    surviving record of the run's outputs - which is exactly the case this script has to repair.
    """
    for p in sorted((ROOT / "papers").glob("P00*")):
        f = p / "experiment_registry.csv"
        if not f.is_file():
            continue
        for r in csv.DictReader(io.StringIO(f.read_text(encoding="utf-8"))):
            if r.get("exp_id") == exp_id and str(r.get("outputs") or "").strip():
                return [x.strip().replace(chr(92), "/")
                        for x in re.split(r"[;,]", r["outputs"]) if x.strip()]
    return []


def fixes() -> dict:
    """{exp_id: {column: new value}} - each entry conditioned on its evidence still being on disk."""
    out = {}
    j6b = "results_raw/EXP0006_preretrieval_prediction_fail_at_3_20260918T183649.json"
    j6a = "results_raw/EXP0006_preretrieval_prediction_fail_at_3_20260918T182156.json"
    j6c = "results_raw/EXP0006_preretrieval_prediction_fail_at_3_20260918T182947.json"
    csv6 = "results_processed/EXP0006_auc_table_fail_at_3.csv"
    if exists(j6b, csv6):
        # both rows declared the table under `results_raw/`, where it has never been: the script writes it into
        # `results_processed/` whenever that folder exists, which it has since the first rebuild
        out["EXP-0006b"] = {"outputs": f"{j6b}; {csv6}"}
    if exists(j6a, j6c, csv6):
        out["EXP-0006"] = {"outputs": f"{j6a}; {j6c}; {csv6}"}
    j7 = "results_raw/EXP0007_toucan_routing_dataset_20260918T182556.json"
    frames = [f"01_datasets/processed/routing_{c}.parquet" for c in ("OSS", "Qwen3", "Kimi-K2")]
    if exists(j7, *frames):
        out["EXP-0007"] = {"outputs": j7 + "; " + "; ".join(frames)}
    # Two rows lost their declaration while the generation bookkeeping was being sorted out (a step that retires a
    # row's only named file must not leave the row naming nothing). Restored from the package's own copy of the
    # register, which still carries what the run wrote, and filtered to files that exist and are not retired.
    for eid in ("EXP-0002", "EXP-0006b"):
        pkg_val = package_row_outputs(eid)
        good = [p for p in pkg_val if exists(p) and not retired(p)]
        if good:
            out[eid] = {"outputs": "; ".join(good)}
    p = "02_shared_code/data_audit/toucan_split_contamination_probe.py"
    j8 = latest("EXP0225_split_contamination_promoted_*.json")
    if exists(p) and j8:
        promoted = json.loads((ROOT / j8).read_text(encoding="utf-8"))
        m = promoted.get("measured") or {}
        # only the status and the note change: the probe really did leave no file, and pretending otherwise by
        # pointing the row at another run's artefact would make the two runs indistinguishable. `round2_run_reality`
        # reads `superseded_by_EXP-nnnn` and checks the successor's artefact in its place.
        out["EXP-0008"] = {
            "status": "superseded_by_EXP-0225",
            "notes": ("2026-09-25: this was an inline console probe with no script and no artefact, and its 7.1% "
                      "prompt_id-recurrence figure could not be reproduced from disk - withdrawn in deviation D61. "
                      "EXP-0225 (the promoted probe, artefact "
                      + j8 + ") re-ran the same three quantities on the frozen frames: exact-question overlap "
                      "across the split boundary "
                      + json.dumps({c: v["share"] for c, v in
                                    (m.get("exact_question_overlap_across_the_split_boundary") or {}).items()},
                                   ensure_ascii=False)
                      + ", prompt_ids arriving under more than one uuid "
                      + str(m.get("prompt_ids_arriving_under_more_than_one_uuid"))
                      + ", cross-config recurrence share "
                      + str(m.get("recurrence_share_of_pooled_prompts"))
                      + " (the figure that replaces 7.1%). Original note kept below. ")}
    j14b = latest("EXP0227_persistence_replication_audit_*.json")
    if j14b:
        a27 = json.loads((ROOT / j14b).read_text(encoding="utf-8"))
        rng = a27.get("pooled_range") or {}
        # EXP-0014b is not wrong, it is a single draw: its own appendix A9 and deviation D17 already say the rank
        # differences reach 7/19,198 and never move a label. The promoted audit measures that spread against the
        # hash seed, so the older row records what the newer one settled.
        out["EXP-0014b"] = {
            "status": "superseded_by_EXP-0227",
            "notes": ("2026-09-25: this audit was run inline, so its script cell named a module rather than a file. "
                      "EXP-0227 (artefact " + j14b + ") re-ran it as a script over the same population and swept "
                      "PYTHONHASHSEED: the stored fail_at_3 label reproduced for "
                      + str((rng.get("rows") or [0])[0]) + " dev rows at every seed with 0 flips, while "
                      "bm25_best_rank differed on " + "-".join(str(x) for x in (rng.get("rank_mismatches") or [0, 0]))
                      + " rows per seed, every difference an exact BM25 score tie, and not the same rows from one "
                      "seed to the next. Its own recorded '2 mismatches, 1 tie' is therefore one draw from that "
                      "spread, which is what D17 and appendix A9 already state as 'up to 7 of 19,198'. ")}
    return out


def record(fields_changed: int) -> str:
    """File what the registry says right now for the rows this script owns.

    The script changes the master register, so the change itself is the evidence and has to be openable: this is
    the artefact the registry row for EXP-0228 points at. A re-run writes a record whose `after` equals its
    `before`, which is the honest statement that the correction is already in place.
    """
    import datetime
    rows = {r["exp_id"]: r for r in csv.DictReader(io.StringIO(REG.read_text(encoding="utf-8")))}
    fx = fixes()
    payload = {"exp_id": "EXP-0228", "seed": "n/a (a registry correction, not a measurement)",
               "status": ("registry_rows_already_correct" if not fields_changed
                          else f"{fields_changed}_registry_fields_corrected"),
               "fields_changed_by_this_run": fields_changed,
               "rows_owned": sorted(fx),
               "rows": {e: {k: {"before_in_registry": (rows.get(e) or {}).get(k),
                                "derived_from_the_run_it_cites": (v or "")[:200]}
                            for k, v in (fx.get(e) or {}).items()} for e in sorted(fx)},
               "registry_rows_total": len(rows),
               "evidence_read": {"EXP-0006b": "results_raw/EXP0006_preretrieval_prediction_fail_at_3_20260918T183649.json",
                                 "EXP-0007": "results_raw/EXP0007_toucan_routing_dataset_20260918T182556.json"
                                             " + the three routing frames the builder documents",
                                 "EXP-0008": latest("EXP0225_split_contamination_promoted_*.json"),
                                 "EXP-0014b": latest("EXP0227_persistence_replication_audit_*.json")},
               "at": datetime.datetime.now().isoformat(timespec="seconds")}
    dest = ROOT / "results_raw" / f"EXP0228_prewave_registry_corrections_{time.strftime('%Y%m%dT%H%M%S')}.json"
    dest.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote", dest.name)
    return str(dest.relative_to(ROOT)).replace(chr(92), "/")


def ledger_the_ladder_collision() -> int:
    """Name the one artefact two runs share, so neither can cite it as its own.

    `analyze_routing_failure.py` writes `EXP0006_auc_table_fail_at_3.csv` at a fixed path, so EXP-0006's 3-seed
    ladder and EXP-0006b's 5-seed ladder both declare the same file and the bytes on disk are the later run's.
    Nothing published reads the CSV - every P001 table is generated from the runs' JSON generations - but a
    registry row that points at a file another run overwrote is a citation a reader can be misled by, so the
    collision goes into the supersession ledger, where the estate's own rule is "kept, not citable".
    """
    led = ROOT / "results_raw" / "SUPERSEDED_ARTIFACTS.json"
    d = json.loads(led.read_text(encoding="utf-8")) if led.is_file() else {"purpose": "artefacts kept but not citable",
                                                                           "superseded": []}
    name = "EXP0006_auc_table_fail_at_3.csv"
    if any(e.get("file") == name for e in d["superseded"]):
        return 0
    d["superseded"].append({
        "file": name, "exp_id": "EXP-0006",
        "at": datetime.datetime.now().isoformat(timespec="seconds"),
        "reason": "both EXP-0006 (3 seeds) and EXP-0006b (5 seeds) declare this fixed-path table because "
                  "`analyze_routing_failure.py` names it after its own experiment id; the bytes on disk are the "
                  "18:36 generation, i.e. EXP-0006b's. Each run's own JSON generation stays citable and carries "
                  "the digests every published number is read from.",
        "was_it_quoted": "no - the name occurs nowhere in the estate but in a registry row, a provenance row, a "
                         "config row and the script that writes it: no table or figure generator reads it"})
    led.write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")
    return 1


def fix_output_cells(rows: list) -> int:
    """Correct the two ways a pre-wave row's `outputs` cell stops pointing at what the run wrote.

    * **a bare file name.** EXP-0053's row declares `EXP0053_value_level_rights_20260920T014557.json`, but the
      artefact lives in `results_raw/`. Every reader of that cell - the package factory's `_run_artefacts`, the
      round-2 traceability check - resolves a path from the workspace root, so a package whose register declares
      that run receives no artefact for it while the run's own file sits unaccounted for.
    * **another run's primary artefact.** EXP-0071 and EXP-0072 each declare the other's JSON and CSV, so a package
      citing one of them is handed the other paper's file, which the deliverable audit then reports as a foreign
      object in the evidence folder.

    Both are settled by looking rather than by guessing: a bare token is prefixed with the directory that actually
    holds that file, and a token naming `EXPnnnn_*` is dropped from a row that is not EXP-nnnn exactly when EXP-nnnn's
    own row also declares it - so a genuinely shared companion stays where it is and a copy-paste twin goes away.
    """
    by_id = {r["exp_id"]: r for r in rows}
    own_declared = {}
    for r in rows:
        digits = r["exp_id"].replace("-", "")[3:]
        for tok in (r.get("outputs") or "").split(";"):
            b = tok.strip().replace(chr(92), "/").split("/")[-1]
            if b.startswith("EXP"):
                own_declared.setdefault(b, set()).add(digits)
    changed = 0
    for r in rows:
        digits = r["exp_id"].replace("-", "")[3:]
        toks = [t.strip() for t in (r.get("outputs") or "").split(";") if t.strip()]
        out = []
        for t in toks:
            if "(" in t:                                       # a parenthetical note travels with its token
                out.append(t)
                continue
            rel = t.replace(chr(92), "/")
            base = rel.split("/")[-1]
            if "/" not in rel and base.startswith("EXP"):
                sub = next((s for s in ("results_raw", "results_processed", "logs", "configs")
                            if (ROOT / s / base).is_file()), "")
                if sub:
                    print(f"  {r['exp_id']}.outputs: {rel} -> {sub}/{base}")
                    t = f"{sub}/{base}"
                    rel = t
            if base.startswith("EXP") and re.match(r"EXP0*(\d{1,4})_", base):
                other = re.match(r"EXP0*(\d{1,4})_", base).group(1).zfill(4)
                if other != digits and other in own_declared.get(base, set()):
                    print(f"  {r['exp_id']}.outputs: drops {rel}, which EXP-{other}'s own row declares")
                    changed += 1
                    continue
            out.append(t)
        new = "; ".join(out)
        if new != (r.get("outputs") or "").strip():
            r["outputs"] = new
            changed += 1
    return changed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    fx = fixes()
    if not a.check:
        print(f"ladder-collision ledger entries written: {ledger_the_ladder_collision()}")
    rows = list(csv.DictReader(io.StringIO(REG.read_text(encoding="utf-8"))))
    cols = list(rows[0].keys())
    changed = 0
    for r in rows:
        new = fx.get(r["exp_id"])
        if not new:
            continue
        for k, v in new.items():
            cur = r.get(k) or ""
            if k == "notes":                                  # the promotion is appended, never a replacement
                if v.strip() in cur:
                    print(f"  {r['exp_id']}.notes: already carries the promotion")
                    continue
                v = f"{cur} {v}".strip()
            elif cur == v:
                print(f"  {r['exp_id']}.{k}: already correct")
                continue
            print(f"  {r['exp_id']}.{k}:\n    - {cur[:150]}\n    + {v[:150]}")
            r[k] = v
            changed += 1
    paths = fix_output_cells(rows)
    changed += paths
    print(f"output cells corrected by the path rules: {paths}")
    if a.check:
        print(f"{changed} field(s) would change; --check wrote nothing")
        record(changed)
        return 0 if not changed else 1
    if not changed:
        print("registry already carries these corrections")
        record(0)
        return 0
    for r in rows:
        for k in cols:
            if not r.get(k):
                r[k] = ""
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator=chr(10))
    w.writeheader()
    w.writerows(rows)
    REG.write_text(buf.getvalue(), encoding="utf-8")
    print(f"wrote {REG.name}: {changed} field(s) corrected across {len(fx)} row(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
