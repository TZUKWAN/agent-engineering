"""EXP-0041 (P004 E1): which of the eight local releases ship vendor-assigned quality fields at all?

RQ5 needs a count, not a narrative: a release counts as shipping an instrument iff a quality-shaped field exists
and is non-null in >= 5% of sampled rows (protocol_freeze.md section 3). "Quality-shaped" is a frozen name list plus
a structural test (a JSON object whose keys look like scores), because a field can be called
`question_quality_assessment` or hide inside `meta_information`.

Scanning is by parquet schema + a row sample, so it is cheap on the 79 GB estate; jsonl-only releases are probed on
the first records and labelled as such. Nothing here is a validity claim - it establishes where a validity claim
could even be tested.

    python 02_shared_code/data_audit/quality_presence_scan_p004.py
Writes results_raw/EXP0041_quality_presence_scan_*.json.
"""
from __future__ import annotations

import collections, glob, json, pathlib, re, sys, time

import pyarrow.parquet as pq

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA = pathlib.Path(r"G:/刘俊琦/AGENT ENGINEERING/MATLABINTOKEN/datasets")
RELEASES = {
    "Toucan-1.5M": "Agent-Ark/Toucan-1.5M", "AgentTrove": "open-thoughts/AgentTrove",
    "MMAT-1M": "VIS-MPU-Agent/MMAT-1M", "AgentBank": "Solaris99/AgentBank",
    "hermes": "lambda/hermes-agent-reasoning-traces", "SWE-ZERO-12M": "AlienKevin/SWE-ZERO-12M-trajectories",
    "code-act": "xingyaoww/code-act", "AgentInstruct": "zai-org/AgentInstruct",
}
NAME_HINT = re.compile(r"quality|score|rating|grade|assess|judge|verdict|metric", re.I)
SUB_HINT = re.compile(r"difficulty|useful|correct|complet|concise|quality|verifi|realis|realiz|stabilit|"
                      r"agreement|percent|overall", re.I)
ROWS = 2000


def numeric_scores(obj, out, prefix=""):
    """Collect leaf values that look like a score: a number, or {'score': number}."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, dict) and any(isinstance(x, (int, float)) for x in v.values()):
                nums = [x for x in v.values() if isinstance(x, (int, float))]
                out[prefix + k] = nums[0]
            elif isinstance(v, (int, float)) and not isinstance(v, bool):
                out[prefix + k] = v
            elif isinstance(v, (dict, list)):
                numeric_scores(v, out, prefix + k + ".")
            if prefix + k in out and not SUB_HINT.search(k):
                del out[prefix + k]
    elif isinstance(obj, list):
        for x in obj[:3]:
            numeric_scores(x, out, prefix)


def scan(parquet_files, jsonl_files):
    hit_cols = collections.Counter()
    rows_read = 0
    found = collections.defaultdict(list)
    nonnull = collections.Counter()
    if parquet_files:
        cols = list(pq.ParquetFile(parquet_files[0]).schema_arrow.names)
        suspect = [c for c in cols if NAME_HINT.search(c)]
        nested_cols = [c for c in cols if c.lower() in ("metadata", "meta_information", "extra", "info",
                                                        "quality_assessment")]
        want = [c for c in suspect + nested_cols if c in cols]
        if not want:                              # never fall back to reading a whole multi-GB shard
            return {"rows_read": 0, "columns_matching": {}, "score_fields": {},
                    "all_columns": cols, "scanned_without_candidates": True}
        for f in parquet_files[:3]:
            try:
                tbl = pq.read_table(f, columns=want)
            except Exception:                                   # noqa: BLE001 - empty/odd column sets
                continue
            for r in tbl.slice(0, max(1, ROWS - rows_read)).to_pylist():
                rows_read += 1
                for c in suspect:
                    v = r.get(c)
                    if v is None:
                        continue
                    hit_cols[c] += 1
                    if isinstance(v, str):
                        try:
                            v = json.loads(v)
                        except Exception:                       # noqa: BLE001
                            continue
                    acc = {}
                    numeric_scores(v, acc)
                    for k, val in acc.items():
                        found[c + "!" + k].append(val)
                for c in nested_cols:
                    v = r.get(c)
                    if isinstance(v, str):
                        try:
                            v = json.loads(v)
                        except Exception:                         # noqa: BLE001
                            continue
                    if isinstance(v, dict):
                        for k, val in v.items():
                            if not NAME_HINT.search(k):
                                continue
                            acc = {}
                            numeric_scores(val, acc, k + ".")
                            for kk, vv in acc.items():
                                found["nested:" + kk].append(vv)
                                hit_cols["nested:" + k] += 1
    elif jsonl_files:
        with open(jsonl_files[0], encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if rows_read >= ROWS:
                    break
                rows_read += 1
                try:
                    r = json.loads(line)
                except Exception:                                 # noqa: BLE001
                    continue
                for k, v in r.items():
                    if NAME_HINT.search(k):
                        hit_cols[k] += 1
                        acc = {}
                        numeric_scores(v, acc, k + ".")
                        for kk, vv in acc.items():
                            found[kk].append(vv)
    for k, vals in found.items():
        nonnull[k] = round(len(vals) / max(1, rows_read), 4)
    return {"rows_read": rows_read, "columns_matching": dict(hit_cols),
            "score_fields": {k: {"non_null_share": nonnull[k], "n_obs": len(v),
                                 "min": min(v), "max": max(v), "distinct": len(set(v))}
                             for k, v in sorted(found.items()) if len(v) >= 5}}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    res = {"exp_id": "EXP-0041", "paper_id": "P004", "stage": "E1_presence_scan", "rows_per_release": ROWS,
           "rule": "ships an instrument iff a quality-shaped field is non-null in >=5% of sampled rows",
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "releases": {}}
    for name, rel in RELEASES.items():
        base = DATA / rel
        if not base.exists():
            res["releases"][name] = {"error": "path not on disk", "path": str(base)}
            print(f"  {name:14s} NOT ON DISK")
            continue
        files = [f for f in sorted(glob.glob(str(base / "**/*.parquet"), recursive=True)) if ".cache" not in f]
        jl = [f for f in sorted(glob.glob(str(base / "**/*.jsonl"), recursive=True)) if ".cache" not in f]
        d = scan(files, jl)
        d["container"] = ("parquet" if files else ("jsonl" if jl else "none"))
        d["qualifies"] = any(x["non_null_share"] >= 0.05 for x in d["score_fields"].values())
        res["releases"][name] = d
        print(f"  {name:14s} container={d['container']:7s} rows={d['rows_read']:5d} "
              f"score_fields={len(d['score_fields'])} qualifies={d['qualifies']}")
    q = [k for k, v in res["releases"].items() if v.get("qualifies")]
    res["verdict"] = {"releases_shipping_quality_scores": q, "n": len(q),
                      "note": ("P004's criterion-validity audit is possible on " + ", ".join(q) +
                               ";" if q else "no release ships a usable score field; P004 has no object") +
                              " cross-corpus replication is only possible where two or more qualify."}
    res["wallclock_sec"] = round(time.time() - t0, 1)
    res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    (ROOT / "results_raw").mkdir(exist_ok=True)
    out = ROOT / "results_raw" / f"EXP0041_quality_presence_scan_{time.strftime('%Y%m%dT%H%M%S')}.json"

    def default(o):
        return str(o)

    out.write_text(json.dumps(res, indent=1, ensure_ascii=False, default=default), encoding="utf-8")
    print(json.dumps(res["verdict"], ensure_ascii=False)[:400])
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
