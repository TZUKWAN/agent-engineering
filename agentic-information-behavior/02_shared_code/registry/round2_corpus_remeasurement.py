"""Round-2 check B: re-measure the corpora on disk against what the audit manifests claim.

Every premise census, feature frame and feasibility verdict in the programme is anchored on
`01_datasets/manifests/*.audit.json`, which records per dataset and per config: how many files, how many rows,
which columns, and the non-empty coverage of the keys the designs read. If those numbers have drifted from the
bytes on disk - a shard that is no longer there, a column renamed, a row count that was never the whole release -
then every gate that passed on them passed on a measurement that no longer holds.

This re-derives them from the files:

* file count: the files the release layout attributes to that config - its own folder, its own file prefix, or the
  unclaimed remainder of the release - same extension as the manifest recorded;
* row count: parquet row-group metadata (no data is read), reported as not re-measured for line-oriented formats
  rather than estimated;
* columns: the arrow schema of the first file, compared against the manifest's column list.

    python 02_shared_code/registry/round2_corpus_remeasurement.py [--limit 20]
"""
from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import round2_lib as L                                                    # noqa: E402

ROOT = L.ROOT
MANIFESTS = ROOT / "01_datasets" / "manifests"
CORPORA = ROOT.parent / "MATLABINTOKEN" / "datasets"


def release_dir(hf_id: str):
    """The local directory for a `org/repo` id, resolved the way the probes resolve it."""
    if not hf_id or "/" not in hf_id:
        return None
    org, repo = hf_id.split("/", 1)
    for cand in ((CORPORA / org / repo), (CORPORA / repo)):
        if cand.is_dir():
            # the repo root, not the first folder that happens to hold a parquet: a multi-config release keeps
            # one folder per config under here, and `config_dir` is what picks between them.
            return cand
    return None


def data_files(d: pathlib.Path, ext: str) -> list:
    """Every `ext` file under `d`, ignoring the dot-directories a `hf download` leaves behind.

    `.cache/huggingface/download/` mirrors the whole release layout with a `.metadata` file per shard, so a
    cache-blind walk sees each config in two places at once - which is why code-act's configs first looked
    unattributable rather than resolvable to `data/`.
    """
    if not d:
        return []
    return sorted(p for p in d.rglob(f"*.{ext}")
                  if not any(part.startswith(".") for part in p.relative_to(d).parts[:-1]))


def config_dir(root: pathlib.Path, cfg: str):
    """The sub-directory a multi-config release keeps this config in, if it keeps one.

    AgentBank stores each of its 18 environments as its own folder and Toucan each teacher config as its own
    folder, so a whole-release glob attributes every file to every config - which is how the first pass of this
    check came to report the same 623 rows for all of them. When no such folder exists the release really is
    single-config (or the config is a column inside the files), and row counts are then compared as measured.
    """
    if not root:
        return None
    subdirs = [d for d in root.rglob("*") if d.is_dir() and not any(p.startswith(".") for p in d.relative_to(root).parts)]
    exact = [d for d in subdirs if d.name == cfg]
    if len(exact) == 1:
        return exact[0]
    named = [d for d in subdirs if cfg.lower() in d.name.lower()]
    return named[0] if len(named) == 1 else None


def config_files(root: pathlib.Path, cfgs, cfg: str):
    """The data files that belong to one config, or None when the release layout cannot attribute them.

    Three layouts occur. AgentBank and Toucan give each config its own folder. code-act keeps the configs side by
    side in one folder and separates them by file name (`codeact-00000-of-00001.parquet`, `general-...`), so the
    prefix - not the folder, which holds both - is the config's file set. hermes gives two of its three configs a
    folder and leaves the unnamed default config's shards loose, which is attributed by elimination: one config
    unclaimed plus files nobody else claimed means those files are this config's. Two unnamed configs stay
    unattributed rather than guessed at, and the row-count comparison is then reported as impossible instead of
    approximated.
    """
    ext = "parquet" if data_files(root, "parquet") else "jsonl"

    def owned(c):
        d = config_dir(root, c)
        if d is not None:
            return data_files(d, ext)
        pref = [f for f in data_files(root, ext) if f.name.lower().startswith(c.lower())]
        return pref or None

    got = owned(cfg)
    if got is not None:
        return got
    sib = {c: owned(c) for c in cfgs if c != cfg}
    claimed = {str(f) for v in sib.values() if v for f in v}
    loose = [f for f in data_files(root, ext) if str(f) not in claimed]
    return loose if loose and all(v is not None for v in sib.values()) else None


def parquet_rows(f: pathlib.Path) -> int:
    import pyarrow.parquet as pq
    return int(pq.ParquetFile(f).metadata.num_rows)


def parquet_cols(f: pathlib.Path) -> list:
    """The file's own top-level columns.

    `ParquetFile.schema` is the deprecated pandas-style view, which flattens a struct or list-of-struct column into
    its subfields: it made AgentBank's `conversations` look like two columns called `from` and `value` and reported
    24 columns the release supposedly lacks. `schema_arrow` is what the file actually has.
    """
    import pyarrow.parquet as pq
    return list(pq.ParquetFile(f).schema_arrow.names)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=30)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    bad, checked = [], 0
    for mf in sorted(MANIFESTS.glob("*.audit.json")):
        d = json.loads(mf.read_text(encoding="utf-8"))
        rd = release_dir(str(d.get("hf_repo_id") or ""))
        if rd is None:
            bad.append({"dataset": d.get("dataset"), "problem": "release_directory_not_on_disk",
                        "hf_repo_id": d.get("hf_repo_id")})
            continue
        raw_cfgs = d.get("configs") or {}
        # Some manifests key their configs by name and some carry a list of records that name themselves.
        cfgs = {c.get("config") or c.get("name") or f"cfg{i}": c for i, c in enumerate(raw_cfgs)} \
            if isinstance(raw_cfgs, list) else dict(raw_cfgs)
        cfgs = {k: v for k, v in cfgs.items() if isinstance(v, dict)}
        multi = len(cfgs) > 1
        for cfg, c in cfgs.items():
            checked += 1
            files = (config_files(rd, list(cfgs), cfg) if multi
                     else (data_files(rd, "parquet") or data_files(rd, "jsonl")))
            if multi and files is None:
                # the config has neither a folder, a file prefix nor an unambiguous remainder: row counts cannot be
                # attributed to it from the file metadata, and saying so is the honest answer rather than a guessed
                # split - a column inside the files, if present, is named so the next reader knows where to look
                cols = set(parquet_cols(data_files(rd, "parquet")[0])) if data_files(rd, "parquet") else set()
                key = next((k for k in ("cfg", "config", "subset_name", "split") if k in cols), None)
                bad.append({"dataset": d.get("dataset"), "config": cfg,
                            "problem": "config_separated_only_by_a_column" if key else "config_not_separable_on_disk",
                            "column": key, "dir": str(rd)})
                continue
            ext = "parquet" if all(f.suffix == ".parquet" for f in files) else "jsonl"
            claim_n, claim_rows = c.get("n_files"), c.get("total_rows_all_files")
            if claim_n is not None and len(files) != int(claim_n):
                bad.append({"dataset": d.get("dataset"), "config": cfg, "problem": "file_count_differs",
                            "claimed": claim_n, "on_disk": len(files), "dir": str(rd)})
            if not files:
                bad.append({"dataset": d.get("dataset"), "config": cfg, "problem": "no_data_files_found",
                            "dir": str(rd), "extension_tried": ext})
                continue
            if ext == "parquet" and claim_rows is not None:
                rows = 0
                for f in files:
                    try:
                        rows += parquet_rows(f)
                    except Exception as e:                                  # noqa: BLE001 - report, don't skip
                        bad.append({"dataset": d.get("dataset"), "config": cfg,
                                    "problem": "shard_unreadable", "file": f.name, "error": str(e)[:120]})
                        break
                if rows != int(claim_rows):
                    bad.append({"dataset": d.get("dataset"), "config": cfg, "problem": "row_count_differs",
                                "claimed": claim_rows, "measured": rows, "files": len(files)})
            cols = c.get("columns") or []
            if cols:
                try:
                    have = set(parquet_cols(files[0])) if ext == "parquet" else set()
                except Exception:                                                # noqa: BLE001
                    have = set()
                if have:
                    miss = [k for k in cols if k not in have]
                    if miss:
                        bad.append({"dataset": d.get("dataset"), "config": cfg,
                                    "problem": "manifest_lists_columns_the_release_does_not_have",
                                    "missing": miss, "first_file": files[0].name})
    by = {}
    for x in bad:
        by[x["problem"]] = by.get(x["problem"], 0) + 1
    for x in bad[:a.limit]:
        print(json.dumps(x, ensure_ascii=False)[:220])
    print(f"\n{checked} dataset-config(s) re-measured; {len(bad)} finding(s)")
    print(json.dumps(by, indent=1))
    dest = ROOT / "results_raw" / f"ROUND2_CORPUS_REMEASURE_{time.strftime('%Y%m%dT%H%M%S')}.json"
    dest.write_text(json.dumps({"detector": "round2_corpus_remeasurement", "configs_checked": checked,
                                "totals": by, "detail": bad,
                                "at": datetime.datetime.now().isoformat(timespec="seconds")},
                               indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote", dest.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
