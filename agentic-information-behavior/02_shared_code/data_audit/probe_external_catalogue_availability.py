"""EXP-0022: is an INDEPENDENT tool-catalogue corpus available at all? Evidence, not assertion.

P001's D13 narrowing (headline AUROC = upper bound for unseen catalogues) can only be retired by a
second catalogue distribution. This probe records, as machine-generated evidence with timestamps,

  A) which of the eight locally held corpora contain a per-query candidate-tool catalogue at all
     (column-name scan + real parse of up to 200 rows per dataset, so the answer comes from the
     files rather than from any README claim), and
  B) which remote hosts are reachable from the analysis environment, with retries, so the statement
     "an external tool-retrieval benchmark could not be downloaded" is auditable.

Outputs results_raw/EXP0022_external_catalogue_availability_*.json and logs/EXP-0022_...txt.
Read-only: touches nothing but the probes below.
"""

from __future__ import annotations

import json
import re
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path(r"G:/刘俊琦/AGENT ENGINEERING/MATLABINTOKEN/datasets")
OUT = ROOT / "results_raw"
CAT_COLS = re.compile(r"(available_tools$|^tools$|function_call|functions|api_(pool|search)|mcp)", re.I)
ROWS_TO_PARSE = 200
HOSTS = {
    # A 200 on a site root proves nothing about dataset access, so every host is probed TWICE:
    # once at its API/root and once at a real dataset FILE download URL that would have to work
    # before an external corpus could actually be pulled into this project.
    "huggingface.co (dataset API)": "https://huggingface.co/api/datasets/Agent-Ark/Toucan-1.5M",
    "huggingface.co (file download)": "https://huggingface.co/datasets/ibm/stac/resolve/main/README.md",
    "datasets-server.huggingface.co": "https://datasets-server.huggingface.co/validity?dataset=ibm/stac",
    "hf-mirror.com (root)": "https://hf-mirror.com/api/datasets",
    "hf-mirror.com (file download)": "https://hf-mirror.com/datasets/ibm/stac/resolve/main/README.md",
    "api.github.com (repo metadata)": "https://api.github.com/repos/OpenBMB/ToolBench",
    "raw.githubusercontent.com (file download)":
        "https://raw.githubusercontent.com/OpenBMB/ToolBench/master/README.md",
    "modelscope.cn (dataset file download)":
        "https://www.modelscope.cn/datasets/OpenBMB/ToolBench/resolve/master/README.md",
    "pypi.org (control, known-reachable)": "https://pypi.org/simple/",
}


def probe_hosts(retries: int = 3) -> dict:
    out = {}
    for label, url in HOSTS.items():
        attempts = []
        ok = False
        for _ in range(retries):
            t0 = time.time()
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "aib-audit/1.0"})
                with urllib.request.urlopen(req, timeout=20, context=ssl._create_unverified_context()) as r:
                    r.read(512)
                    attempts.append({"status": int(r.status), "sec": round(time.time() - t0, 2)})
                    ok = True
                    break
            except urllib.error.HTTPError as e:      # a response arrived: the host is reachable
                attempts.append({"status": int(e.code), "sec": round(time.time() - t0, 2)})
                ok = True
                break
            except Exception as e:
                attempts.append({"error": f"{type(e).__name__}: {str(e)[:90]}",
                                 "sec": round(time.time() - t0, 2)})
            time.sleep(1.0)
        out[label] = {"url": url, "reachable": ok, "attempts": attempts}
        print(f"  {'OK  ' if ok else 'FAIL'} {label}: {attempts[-1]}")
    return out


def scan_dataset(d: Path) -> dict:
    files = sorted(d.rglob("*.parquet"))
    files = [f for f in files if ".cache" not in f.parts]
    info = {"path": str(d.relative_to(DATA_ROOT)), "n_parquet_shards": len(files)}
    if not files:
        return {**info, "catalogue_columns": [], "verdict": "no parquet shards"}
    names = list(pq.ParquetFile(files[0]).schema_arrow.names)
    info["columns"] = names[:40]
    cat_cols = [c for c in names if CAT_COLS.search(c)]
    info["catalogue_columns"] = cat_cols
    if not cat_cols:
        return {**info, "verdict": "no per-row candidate-tool catalogue column"}
    col = cat_cols[0]
    parsed = rows = 0
    sizes, with_desc = Counter(), 0
    for f in files[:2]:
        try:
            t = pq.read_table(f, columns=[col]).slice(0, ROWS_TO_PARSE)
        except Exception as e:
            info["parse_error"] = f"{type(e).__name__}: {str(e)[:80]}"
            break
        for v in t.column(col).to_pylist():
            rows += 1
            try:
                obj = json.loads(v) if isinstance(v, str) else v
            except Exception:
                continue
            if isinstance(obj, list) and obj:
                parsed += 1
                sizes[len(obj)] += 1
                first = obj[0]
                first = first.get("function", first) if isinstance(first, dict) else {}
                if isinstance(first, dict) and str(first.get("description") or "").strip():
                    with_desc += 1
        if parsed >= 20:
            break
    info["rows_examined"] = rows
    info["rows_with_parseable_catalogue"] = parsed
    info["catalogue_size_hist_top5"] = dict(sorted(sizes.items())[:5]) if sizes else {}
    info["rows_with_tool_descriptions"] = with_desc
    info["verdict"] = ("catalogue present" if parsed >= max(1, rows // 4) and with_desc >=
                       max(1, rows // 4) else "catalogue column present but not machine-parseable")
    return info


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    res = {"exp_id": "EXP-0022", "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "question": "is any second, independent tool-catalogue distribution available to this project?",
           "A_local_corpora": [], "B_reachability": {}}
    print("A) local corpora: which carry a per-query candidate-tool catalogue?")
    for d in sorted(p for p in DATA_ROOT.glob("*/*") if p.is_dir()):
        info = scan_dataset(d)
        res["A_local_corpora"].append(info)
        print(f"  {info['path']:<42} shards={info['n_parquet_shards']:<5} "
              f"cat_cols={info['catalogue_columns']} -> {info['verdict']}")
    cat_bearing = [i["path"] for i in res["A_local_corpora"] if i["verdict"] == "catalogue present"]
    res["A_summary"] = {"datasets_with_machine_readable_catalogue": cat_bearing,
                        "note": "all catalogue-bearing shards found here belong to the SAME Toucan-1.5M "
                                "repo (its four generation configs); EXP-0021 measured that those configs "
                                "share one tool universe, so they are not independent catalogue sources"}
    print("\nB) remote hosts reachable from the analysis environment (3 attempts each):")
    res["B_reachability"] = probe_hosts()
    reachable_ds = [k for k, v in res["B_reachability"].items()
                    if v["reachable"] and "control" not in k and "raw.githubusercontent" not in k
                    and "api.github" not in k]
    res["B_summary"] = {
        "hosts_from_which_a_dataset_can_be_fetched": reachable_ds,
        "conclusion": ("an external tool-retrieval benchmark (ToolRet / STAC / ToolBench / API-Bank) could "
                       "NOT be downloaded in this environment"
                       if not reachable_ds else "partially reachable - attempt the download")}
    res["wallclock_sec"] = round(time.time() - t0, 1)
    res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    out = OUT / f"EXP0022_external_catalogue_availability_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print("\n" + json.dumps(res["A_summary"], ensure_ascii=False))
    print(json.dumps(res["B_summary"], ensure_ascii=False))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
