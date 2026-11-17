"""EXP-0053 (P005's own next action, named in its final_audit): do the payload VALUES carry rights text?

The main census (EXP-0049) decided L6/L7 from column and metadata-key NAMES. P005's limitation L2 says plainly that
a licence embedded inside a value, or a rights notice inside a nested document, would be missed by design. This
experiment is the threat test for that limitation: if rights text does appear inside the payload, the paper's
headline ("declared at the card, verifiable nowhere below it") has to be rewritten; if it does not, the headline
survives a test that could have refuted it.

Frozen rule, written before any value was read:
  CHANGE_HEADLINE iff at least one release yields >= 5 sampled rows whose value text contains a rights expression
  from RIGHTS_RE, in a column that is not itself the task instruction, AND those hits survive manual inspection of
  every distinct matching string (a hit inside a user's own question about licensing is NOT a rights notice about
  the corpus - that is the exact false-positive class this test must not fall for).
  CONFIRM_HEADLINE iff no release reaches that bar, with the sampled-cell count reported so the bound is visible.
  Anything in between (1-4 rows in one release) is reported as `sparse_unresolved` and the headline keeps its
  limitation, because a handful of incidental strings cannot establish verifiability.

Sampling (deterministic, seed 2026): per release, up to 40 parquet files chosen at random (coverage recorded per
release, because the largest release has 1,230 files and reading a whole row group of every one of them costs minutes
and gigabytes - the first attempt stalled on exactly that), one randomly chosen row group per file, and
<=2,000/40 ~= 50 rows per file; every string-valued column of a sampled row is searched, nested JSON decoded one
level deep, with a 300,000-character cap per cell. Nested JSON strings are decoded one level deep (the P003 interchange-vs-content
lesson: a JSON string column is not "absent"). Small non-parquet documents (< 2 MB) are searched whole, because
AgentBank's environments ship json/txt fixtures that a column scan never touches.

    python 02_shared_code/data_audit/governance_value_level_scan_p005.py
"""
from __future__ import annotations

import json, pathlib, random, re, sys, time
from collections import Counter, defaultdict

import pyarrow.parquet as pq

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "02_shared_code" / "data_audit"))
import governance_metadata_pilot_p005 as G      # noqa: E402  (CORPORA, DATA)

OUT, PROC = ROOT / "results_raw", ROOT / "results_processed"
SEED = 2026
ROWS_PER_RELEASE = 2000
FILES_PER_RELEASE = 40        # random files, coverage recorded; see the bounded-sampling note below
CELL_CHAR_CAP = 300_000
SMALL_DOC_BYTES = 2_000_000
JSONL_LINES_PER_RELEASE = 3000
INSTRUCTION_COLS = {"question", "instruction", "task", "prompt", "user_instruction", "conversations", "messages"}
RIGHTS_RE = re.compile(
    r"(copyright|all rights reserved|licensed under|license:\s*\S|licence:\s*\S|apache license|mit license|"
    r"cc-by|creative commons|gnu general public|redistribution and use in source and binary|terms of use|"
    r"attribution 4\.0|do not distribute|unlicensed)", re.I)
CONTEXT = re.compile(r"(dataset|corpus|code|repository|this (?:file|project|software)|data is|provided under)", re.I)


def texts_of(value, depth=0, out=None):
    """Every string reachable in a cell, decoding one level of nested JSON (never more)."""
    out = [] if out is None else out
    if value is None:
        return out
    if isinstance(value, str):
        s = value
        if depth == 0 and s[:1] in "[{" and len(s) < 4_000_000:
            try:
                return texts_of(json.loads(s), depth + 1, out)
            except Exception:
                pass
        out.append(s[:CELL_CHAR_CAP])
    elif isinstance(value, dict):
        for k, v in value.items():
            out.append(str(k)[:200])
            texts_of(v, depth + 1, out)
    elif isinstance(value, (list, tuple)):
        for v in value:
            texts_of(v, depth + 1, out)
    return out


def scan_release(name, rel, rng):
    d = G.DATA / rel
    res = {"corpus": name, "rows_sampled": 0, "cells_sampled": 0, "chars_scanned": 0,
           "rights_hits": 0, "hit_columns": {}, "hit_strings": {}, "instruction_hits": 0,
           "small_docs_scanned": 0, "small_doc_hits": 0, "errors": []}
    all_pq = sorted(d.rglob("*.parquet"))
    # Bounded and random over files: reading one whole row group per file for all 1,230 files of the largest release
    # costs minutes and gigabytes per file-set, and the first attempt hung on exactly that. Files are sampled
    # without replacement and the coverage is recorded, so the sample is visible rather than assumed.
    n_files = min(len(all_pq), FILES_PER_RELEASE)
    pqs = sorted(rng.sample(all_pq, n_files)) if all_pq else []
    res["parquet_files_present"] = len(all_pq)
    res["parquet_files_read"] = len(pqs)
    res["file_coverage"] = round(len(pqs) / len(all_pq), 4) if all_pq else None
    per_file = max(1, ROWS_PER_RELEASE // max(1, len(pqs)))
    for p in pqs:
        try:
            f = pq.ParquetFile(p)
        except Exception as e:
            res["errors"].append(f"{p.name}: {type(e).__name__}")
            continue
        if res["rows_sampled"] >= ROWS_PER_RELEASE:
            break
        n_rows = int(f.metadata.num_rows)
        if not n_rows:
            continue
        take = min(per_file, n_rows)
        # One randomly chosen row group per file, not the first: reading group 0 and striding would reproduce the
        # head-of-file bias this programme already had to measure in P001 (EXP-0034), and a rare rights notice is
        # exactly the kind of thing that would sit outside the first group.
        try:
            rg = rng.randrange(int(f.metadata.num_row_groups))
            tbl = f.read_row_group(rg)
            if tbl.num_rows > take:                     # slice in arrow before materialising python objects
                tbl = tbl.take(sorted(rng.sample(range(tbl.num_rows), take)))
            rows = tbl.to_pylist()
            del tbl
        except Exception as e:
            res["errors"].append(f"{p.name}: read {type(e).__name__}")
            continue
        for row in rows:
            res["rows_sampled"] += 1
            for col, val in row.items():
                for t in texts_of(val):
                    res["cells_sampled"] += 1
                    res["chars_scanned"] += len(t)
                    m = RIGHTS_RE.search(t)
                    if not m:
                        continue
                    if col.lower() in INSTRUCTION_COLS:
                        res["instruction_hits"] += 1
                        res.setdefault("instruction_examples", []).append(
                            {"col": col, "snippet": re.sub(r"\s+", " ", t[max(0, m.start() - 90):m.end() + 90])})
                        continue
                    res["rights_hits"] += 1
                    res["hit_columns"][col] = res["hit_columns"].get(col, 0) + 1
                    key = re.sub(r"\s+", " ", t[max(0, m.start() - 60):m.end() + 60]).strip()[:200]
                    res["hit_strings"][key] = res["hit_strings"].get(key, 0) + 1
    res["card_self_hits_excluded"] = 0
    for p in sorted(d.rglob("*.jsonl")):
        # jsonl rows are payload too; MMAT-1M had no value coverage at all before this branch (D-P9)
        if res["rows_sampled"] >= ROWS_PER_RELEASE:
            break
        try:
            fh = open(p, encoding="utf-8", errors="replace")
        except Exception as e:
            res["errors"].append(f"{p.name}: jsonl {type(e).__name__}")
            continue
        with fh:
            for line in fh:
                if res.get("jsonl_lines_scanned", 0) > JSONL_LINES_PER_RELEASE:
                    break
                res["jsonl_lines_scanned"] = res.get("jsonl_lines_scanned", 0) + 1
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                res["rows_sampled"] += 1
                for col, val in (row.items() if isinstance(row, dict) else [("-", row)]):
                    for t in texts_of(val):
                        res["cells_sampled"] += 1
                        res["chars_scanned"] += len(t)
                        m = RIGHTS_RE.search(t)
                        if not m:
                            continue
                        if col.lower() in INSTRUCTION_COLS:
                            res["instruction_hits"] += 1
                            continue
                        res["rights_hits"] += 1
                        key = col + ": " + re.sub(r"\s+", " ", t[max(0, m.start() - 60):m.end() + 90]).strip()[:180]
                        res["hit_strings"][key] = res["hit_strings"].get(key, 0) + 1
                        res["hit_columns"][col] = res["hit_columns"].get(col, 0) + 1
    for p in sorted(d.rglob("*")):
        if not p.is_file() or p.suffix.lower() in (".parquet", ".jsonl") or p.stat().st_size > SMALL_DOC_BYTES:
            continue
        if p.name.lower() == "readme.md":
            # the card is exactly the level EXP-0049 already counted (L2/L4). Scoring it as payload evidence would
            # make the threat test pass on the very thing it is meant to threaten (D-P8).
            try:
                t0 = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                t0 = ""
            res["card_self_hits_excluded"] = int(bool(RIGHTS_RE.search(t0)))
            continue
        try:
            t = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        res["small_docs_scanned"] += 1
        m = RIGHTS_RE.search(t)
        if m:
            res["small_doc_hits"] += 1
            key = f"{p.name}: " + re.sub(r"\s+", " ", t[max(0, m.start() - 60):m.end() + 90]).strip()[:180]
            res["hit_strings"][key] = res["hit_strings"].get(key, 0) + 1
            res["rights_hits"] += 1
    res["distinct_hit_strings"] = len(res["hit_strings"])
    res["verdict_for_release"] = ("candidate_for_headline_change" if res["rights_hits"] >= 5
                                  else ("sparse_unresolved" if res["rights_hits"] else "no_payload_rights_text"))
    return res


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    res = {"exp_id": "EXP-0053", "paper_id": "P005", "threatens": "P005 limitation L2 (names, not contents)",
           "rule": "see module docstring; CHANGE_HEADLINE needs >=5 non-instruction hits in one release that "
                   "survive inspection of every distinct string",
           "seed": SEED, "rows_per_release_cap": ROWS_PER_RELEASE,
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "releases": []}
    for name, rel in G.CORPORA.items():
        r = scan_release(name, rel, random.Random(SEED + sum(map(ord, name))))
        res["releases"].append(r)
        print(f"  {name:13s} rows={r['rows_sampled']:5d} cells={r['cells_sampled']:8d} "
              f"Mb={r['chars_scanned']/1e6:7.1f} rights_hits={r['rights_hits']:3d} "
              f"(in-instruction={r['instruction_hits']:3d}, small-doc={r['small_doc_hits']:2d}) "
              f"distinct={r['distinct_hit_strings']:3d} -> {r['verdict_for_release']}", flush=True)
    reach = [r for r in res["releases"] if r["rights_hits"] >= 5]
    res["verdict"] = ("CHANGE_HEADLINE" if reach else
                      "CONFIRM_HEADLINE" if not any(r["rights_hits"] for r in res["releases"]) else
                      "sparse_unresolved")
    res["total_rows"] = sum(r["rows_sampled"] for r in res["releases"])
    res["total_cells"] = sum(r["cells_sampled"] for r in res["releases"])
    res["total_chars_mb"] = round(sum(r["chars_scanned"] for r in res["releases"]) / 1e6, 1)
    res["instruction_snippets_kept"] = {r["corpus"]: r.get("instruction_examples", [])[:5]
                                        for r in res["releases"] if r.get("instruction_examples")}
    res["wallclock_sec"] = round(time.time() - t0, 1)
    res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    out = OUT / f"EXP0053_value_level_rights_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str), encoding="utf-8", newline="")
    with open(PROC / "EXP0053_value_hits.csv", "w", encoding="utf-8", newline="") as fh:
        fh.write("corpus,release,hits,distinct_strings,verdict\n")
        for r in res["releases"]:
            for s, c in sorted(r["hit_strings"].items(), key=lambda x: -x[1])[:40]:
                fh.write(f'{r["corpus"]},,{c},,see_json\n')
            fh.write(f'{r["corpus"]},TOTAL,{r["rights_hits"]},{r["distinct_hit_strings"]},{r["verdict_for_release"]}\n')
    print("VERDICT", res["verdict"], "| rows", res["total_rows"], "| cells", res["total_cells"],
          "| MB", res["total_chars_mb"])
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
