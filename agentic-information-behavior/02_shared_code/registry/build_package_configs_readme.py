"""EXP-0077: build the two package items the audit was not checking - `configs/` and `README.md`.

Spec deliverable 13 requires a `configs/` directory for every paper and gate G18-E requires a README. All five packages
reported "missing=none" while both were absent, because `package_audit.py` never looked for them; the gap is now visible
in that tool's own output. This step generates the artefacts rather than hand-writing them, so a reviewer can check
them against the sources they summarise:

* `configs/experiment_configs.csv` - every registry row belonging to the paper (script, config, seed, timings, status,
  outputs), which is what "all experiment configurations" means in practice;
* `configs/frozen_parameters.json` - module-level UPPER_CASE constants read out of the paper's own scripts by **AST
  parsing, never by importing them**, because importing an analysis script can execute its pipeline; plus the study
  design fields held in the topic registry;
* `configs/dataset_config.json` - the processed inputs with real row counts, and the sample-identity digest where one
  was recorded;
* `README.md` - an inventory computed from the files on disk (counts, claim tally, deviation count), the reproduce entry
  point with the environment variables it reads, the single-use test ledger status where the paper has one, and the
  recorded headline claims. It deliberately does **not** list open items: an earlier version lifted every line of
  `final_audit.md` matching `OPEN|FAILED|not run` verbatim, and because that file keeps the prose of closed items ("what
  keeps G18-B open now is X", later resolved) the README published a stale to-do list that contradicted the package -
  and nothing caught it, since no chain re-ran this step. The README now points at the three files that own status.

Nothing here asserts a scientific conclusion; every number is a file count or a copied value, and the README names its
sources so a stale copy is detectable. It carries no generation timestamp and is wired into every package's
`reproduce.sh`, so it cannot fall out of step with the artefacts it summarises.

    python 02_shared_code/registry/build_package_configs_readme.py [--paper P004]
"""
from __future__ import annotations

import ast, csv, io, json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parents[2]
PAPERS = ROOT / "papers"
REG = ROOT / "00_program_registry"
MAX_REPR = 220
TOPIC_OF = {"P001": "T037", "P002": "T008", "P003": "T012", "P004": "T024", "P005": "T014"}
DESIGN_COLS = ("title_en", "paper_type", "primary_dataset", "external_validation_dataset", "theory_basis",
               "core_rq_h", "primary_dv", "primary_iv", "main_method", "expected_venue", "status")
CONFIG_ITEMS = ("figures", "tables", "logs", "results_raw", "results_processed", "scripts", "configs")


def read_csv(p):
    return list(csv.DictReader(io.StringIO(pathlib.Path(p).read_text(encoding="utf-8"))))


def module_constants(script):
    """Literal UPPER_CASE module constants, read with ast so nothing is executed."""
    try:
        tree = ast.parse(script.read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, OSError):
        return {}
    out = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for tgt in node.targets:
            if isinstance(tgt, ast.Name) and re.fullmatch(r"[A-Z][A-Z0-9_]{1,}", tgt.id):
                try:
                    val = ast.literal_eval(node.value)
                except (ValueError, SyntaxError):
                    continue
                out[tgt.id] = _canon(val)
    return out


def _canon(val, depth=0):
    """A repr whose output is stable across processes: `repr()` of a set follows hash order, which is randomised.

    A cue table held as a set of synonyms therefore re-serialised differently on every rebuild, which made
    `configs/frozen_parameters.json` - the file that is supposed to pin the frozen constants - a per-run artefact.
    """
    if isinstance(val, (set, frozenset)):
        return "{" + ", ".join(sorted(_canon(v, depth + 1) for v in val)) + "}"
    if isinstance(val, dict):
        return ("{" + ", ".join(f"{_canon(k, depth + 1)}: {_canon(v, depth + 1)}"
                                for k, v in sorted(val.items(), key=lambda kv: str(kv[0]))) + "}")
    if isinstance(val, (list, tuple)):
        inner = ", ".join(_canon(v, depth + 1) for v in val)
        return inner + "," if isinstance(val, tuple) else f"[{inner}]"
    r = repr(val)
    return r[:MAX_REPR] + (" …" if len(r) > MAX_REPR else "") if depth == 0 else r


def main() -> int:
    # --paper keeps each package's chain independent: without it a run of P004's chain would also rewrite the other
    # four packages' configs, so a per-package rebuild would no longer be a per-package operation
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", default="", help="P00x prefix; empty builds every package")
    a = ap.parse_args()
    reg = read_csv(REG / "experiment_registry.csv")
    topics = {t["topic_id"]: t for t in read_csv(REG / "topic_registry.csv")}
    for tdir in sorted(p for p in PAPERS.iterdir() if p.is_dir()):
        pid = tdir.name.split("_")[0]
        if a.paper and pid != a.paper:
            continue
        rows = [r for r in reg if pid in (r.get("paper_id") or "")]
        cdir = tdir / "configs"
        cdir.mkdir(exist_ok=True)

        cols = ["exp_id", "stage", "script", "config", "seed", "started_at", "finished_at", "status", "outputs"]
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\r\n")
        w.writerow(cols)
        for r in rows:
            w.writerow([(r.get(c) or "").replace("\n", " ") for c in cols])
        (cdir / "experiment_configs.csv").write_text(buf.getvalue(), encoding="utf-8", newline="")

        scripts = sorted({(r.get("script") or "").strip() for r in rows if (r.get("script") or "").strip()})
        consts = {rel: c for rel in scripts
                  for c in [module_constants(ROOT / rel)] if c}
        t = topics.get(TOPIC_OF.get(pid, ""))
        design = {TOPIC_OF[pid]: {k: (t.get(k) or "") for k in DESIGN_COLS}} if (t and pid in TOPIC_OF) else {}
        (cdir / "frozen_parameters.json").write_text(json.dumps(
            {"note": "generated by AST read of the scripts under scripts_probed; no module was imported or executed, "
                     "because importing an analysis script can run its pipeline",
             "scripts_probed": scripts, "n_scripts_with_module_constants": len(consts),
             "design_fields_from_topic_registry": design, "constants_by_script": consts},
            indent=1, ensure_ascii=False), encoding="utf-8", newline="")

        dcfg = {"processed_files": {}, "sample_identity_digest": None}
        for f in sorted((ROOT / "01_datasets" / "processed").glob("*.parquet")):
            try:
                import pyarrow.parquet as pq
                md = pq.ParquetFile(f).metadata
                dcfg["processed_files"][f.name] = {"rows": int(md.num_rows),
                                                   "columns": len(pq.ParquetFile(f).schema_arrow.names)}
            except Exception as exc:                                  # unreadable input is a finding, not a blank
                dcfg["processed_files"][f.name] = {"error": f"{type(exc).__name__}: {exc}"}
        sid = ROOT / "01_datasets" / "manifests" / "routing_sample_identity.json"
        if sid.exists():
            dcfg["sample_identity_digest"] = json.loads(sid.read_text(encoding="utf-8"))
        (cdir / "dataset_config.json").write_text(json.dumps(dcfg, indent=1, ensure_ascii=False),
                                                  encoding="utf-8", newline="")

        claims = read_csv(tdir / "claims_evidence_matrix.csv") if (tdir / "claims_evidence_matrix.csv").exists() else []
        n_sup = sum(1 for c in claims if (c.get("status") or "").startswith("supported"))
        n_neg = sum(1 for c in claims if "negative" in (c.get("status") or "")
                    or "not_established" in (c.get("status") or ""))
        dev = (tdir / "deviations.md").read_text(encoding="utf-8") if (tdir / "deviations.md").exists() else ""
        n_dev = len(set(re.findall(r"(?m)^\| D(\d+) \|", dev)))
        repro = (tdir / "reproduce.sh").read_text(encoding="utf-8") if (tdir / "reproduce.sh").exists() else ""
        # only variables the caller can set: a name assigned inside the script (ROOT=, PY=) is internal, not an input
        internal = {m for m in re.findall(r"(?m)^([A-Z][A-Z0-9_]{2,})=", repro)}
        envs = sorted(set(re.findall(r"\$\{?([A-Z][A-Z0-9_]{2,})", repro)) - internal)
        ledger_note = ""
        lp = tdir / "test_eval_ledger.json"
        if lp.exists():
            ldata = json.loads(lp.read_text(encoding="utf-8"))
            ev = ldata.get("evaluations") or ldata.get("entries") or []
            ledger_note = (f"\nTest-split ledger: **{len(ev)} recorded evaluation entr"
                           f"{'y' if len(ev) == 1 else 'ies'}**. The protocol allows exactly one, and `reproduce.sh` "
                           "deliberately excludes the final test stage; re-running it needs an override reason and a "
                           "deviations entry.")
        counts = {k: len(list((tdir / k).rglob("*"))) for k in CONFIG_ITEMS if (tdir / k).is_dir()}
        headline = "\n".join(f"- `{c.get('claim_id', '')}` {c.get('claim', '')[:150]} — "
                             f"{(c.get('digits_reported') or '')[:170]}" for c in claims[:6])
        (tdir / "README.md").write_text(f"""# {tdir.name} — package README

Generated by `02_shared_code/registry/build_package_configs_readme.py`, as part of this package's own
`reproduce.sh` chain. It states no conclusion of its own: every
number below is a file count, a registry row, or a value copied from another artefact, so a stale copy is detectable by
comparing it with its sources (`00_program_registry/experiment_registry.csv`, `topic_registry.csv`,
`claims_evidence_matrix.csv`, `final_audit.md`, `reproduce.sh`, and the directories counted here).

## What this package contains

| item | on disk |
|---|---|
{chr(10).join(f"| {k}/ | {v} files |" for k, v in sorted(counts.items()) if k != "logs")}
| `logs/` | run logs, one more written by every build, so their count is deliberately not stated here |
| claims in `claims_evidence_matrix.csv` | {len(claims)} ({n_sup} supported, {n_neg} reported as negative or not established) |
| experiments registered to this paper | {len(rows)} |
| entries in `deviations.md` | {n_dev} |
| scripts whose module constants were captured | {len(consts)} of {len(scripts)} probed |

## How to reproduce

```bash
bash papers/{tdir.name}/reproduce.sh
```

The interpreter resolves itself: `$AIB_PYTHON` if set and runnable, else the first candidate that actually executes
(each is tested by running it, because a Windows `python` on PATH may be the Store stub that exits 49 without
importing anything), else the script aborts and tells you to export `AIB_PYTHON`. Environment variables this
script reads: {', '.join('${' + e + '}' for e in envs) if envs else 'none'}.{ledger_note}

`configs/` holds the experiment configurations as registered, the frozen module constants read from the scripts by AST
(never by importing them), and the processed-input inventory with row counts.

## Recorded headline claims

{headline or '- see `claims_evidence_matrix.csv`'}

## Where open items are recorded

This README does not list them. `final_audit.md` keeps the prose of items that were once open and have since been
resolved, so a keyword scan of it publishes a to-do list the package has already finished - which is exactly what an
earlier version of this section did. Status belongs to three files, and this one copies no numbers from them:

- `final_audit.md` - the six G18 sub-gates and the evidence each verdict rests on;
- `../../docs/SPEC_COMPLETION_AUDIT.md` - the programme-wide requirement audit (EXP-0099), re-derived from the registry
  and the packages themselves rather than from any summary;
- `logs/RUN_INDEX.md` - every run registered to this package, including the failed, aborted and superseded ones.

## Limits of this README

It is generated, not maintained, so it cannot contain anything the artefacts do not already hold. It does not judge
whether the study was worth doing, whether a claim is over-stated, or whether an open item matters - those judgements
live in `paper.md`, `limitations.md`, `reviewer_attack.md` and `final_audit.md`.
""", encoding="utf-8", newline="")
        print(f"[e77] {tdir.name}: configs/ 3 files + README.md | {len(rows)} registry rows | "
              f"{len(consts)}/{len(scripts)} scripts with constants")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
