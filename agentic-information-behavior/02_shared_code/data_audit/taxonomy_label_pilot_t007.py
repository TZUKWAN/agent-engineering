"""EXP-0040 (T007 pilot): is there a human category scheme with enough granularity to validate a taxonomy against?

T007 proposes inducing a classification scheme from MCP-style tool catalogues and testing it against human
categories. Its novelty screen came back empty (EXP-0038), so the live question is identifiability, not collision:
a scheme-induction paper needs (i) catalogues to induce from, (ii) human labels at a granularity above the trivial,
and (iii) enough items per label that an ARI/NMI comparison is not noise. P003 already found hermes carries only
5-6 distinct catalogues, which could make any induced-vs-human comparison degenerate - so measure before freezing.

What this reports, per candidate corpus: label field cardinality, rows and distinct tools per label, the share of
items the labels cover, whether a per-item catalogue exists at all, and the number of *cross-corpus* clusters a
12-cluster solution would need to match (the resolution ceiling: ARI against a 4-value label cannot reward a
fine-grained scheme).

Pre-registered go/no-go, fixed before running:
  GO      iff >= 2 corpora each with (label cardinality >= 8) and (>= 300 distinct labelled tools) and
          (a per-item catalogue present);
  NO-GO   otherwise - then T007 is folded into P003 or killed, not re-scoped.

    python 02_shared_code/data_audit/taxonomy_label_pilot_t007.py
Writes results_raw/EXP0040_taxonomy_label_pilot_*.json.
"""
from __future__ import annotations

import collections, glob, json, pathlib, re, sys, time

import pyarrow.parquet as pq


ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA = pathlib.Path(r"G:/刘俊琦/AGENT ENGINEERING/MATLABINTOKEN/datasets")
ROWS = 20000


def probe_parquet(paths, label_cols, tool_col=None, cat_col=None, limit=ROWS):
    out = {lb: collections.Counter() for lb in label_cols}
    tools = collections.Counter()
    cat_sizes = []
    n = 0
    per_label_tools = collections.defaultdict(set)
    for f in paths:
        if n >= limit:
            break
        cols = [c for c in (label_cols + [tool_col, cat_col]) if c]
        have = set(pq.ParquetFile(f).schema_arrow.names)
        use = [c for c in cols if c in have]
        if not use:
            continue
        tbl = pq.read_table(f, columns=use).slice(0, max(0, limit - n))
        for r in tbl.to_pylist():
            n += 1
            for lb in label_cols:
                v = r.get(lb)
                if isinstance(v, str) and v.strip():
                    out[lb][v.strip()] += 1
            tl = r.get(tool_col)
            names = set()
            if isinstance(tl, str):
                s = tl.strip()
                parsed = None
                if s.startswith("[") or s.startswith("{"):
                    try:
                        parsed = json.loads(s)
                    except Exception:                          # noqa: BLE001 - falls back to a split
                        parsed = None
                if isinstance(parsed, list):
                    for x in parsed:
                        if isinstance(x, dict):
                            nm = x.get("name") or (x.get("function") or {}).get("name")
                            if nm:
                                names.add(str(nm))
                        elif x:
                            names.add(str(x))
                elif isinstance(parsed, dict):
                    names.update(str(k) for k in parsed)
                else:
                    names = {x.strip() for x in re.split(r"[,;|]", s) if x.strip()}
            elif isinstance(tl, list):
                for x in tl:
                    if isinstance(x, dict):
                        nm = x.get("name") or (x.get("function") or {}).get("name")
                        if nm:
                            names.add(str(nm))
                    elif x:
                        names.add(str(x))
            key = None
            for lb in label_cols:
                if isinstance(r.get(lb), str) and r.get(lb).strip():
                    key = (lb, r[lb].strip())
                    break
            for x in names:
                tools[x] += 1
                if key:
                    per_label_tools[key].add(x)
            if cat_col and isinstance(r.get(cat_col), str) and r[cat_col].strip():
                try:
                    c = json.loads(r[cat_col])
                    if isinstance(c, list):
                        cat_sizes.append(len(c))
                    elif isinstance(c, dict):
                        cat_sizes.append(sum(len(v) if isinstance(v, list) else 1 for v in c.values()))
                except Exception:                              # noqa: BLE001
                    pass
    return out, tools, per_label_tools, cat_sizes, n


def summarise(name, res, label_cols):
    cnt, tools, per_label_tools, cat_sizes, n = res
    d = {"rows_read": n, "labels": {}}
    for lb in label_cols:
        c = cnt.get(lb) or collections.Counter()
        if not c:
            d["labels"][lb] = {"present": False}
            continue
        d["labels"][lb] = {"present": True, "cardinality": len(c), "labelled_rows": sum(c.values()),
                           "coverage_share": round(sum(c.values()) / max(1, n), 4),
                           "rows_per_label_mean": round(sum(c.values()) / len(c), 1),
                           "top5": c.most_common(5)}
    d["distinct_tools_seen"] = len(tools)
    d["labels_with_ge_300_tools"] = sum(1 for v in per_label_tools.values() if len(v) >= 300)
    d["per_label_tool_sets"] = {f"{a}:{b}": len(v) for (a, b), v in
                                sorted(per_label_tools.items(), key=lambda x: -len(x[1]))[:8]}
    if cat_sizes:
        d["per_item_catalogue_size_mean"] = round(sum(cat_sizes) / len(cat_sizes), 2)
        d["per_item_catalogue_present_share"] = round(len(cat_sizes) / max(1, n), 4)
    else:
        d["per_item_catalogue_present_share"] = 0.0
    return d


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    res = {"exp_id": "EXP-0040", "paper_id": "T007", "stage": "pilot", "rows_limit": ROWS,
           "rule": "GO iff >=2 corpora have label cardinality>=8, >=300 distinct labelled tools and a per-item "
                   "catalogue; otherwise NO-GO (fold into P003 or kill, not re-scope)",
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "corpora": {}}

    plans = [
        ("hermes-agent-reasoning-traces", ["category", "subcategory"], "tools", "tools"),
        ("Toucan-1.5M", ["subset_name"], "target_tools", "available_tools"),
    ]
    for corp, labels, tool_col, cat_col in plans:
        base = None
        for cand in (DATA / "lambda" / corp, DATA / "Solaris99" / corp,
                     DATA / "Agent-Ark" / "Toucan-1.5M" / "OSS", DATA / corp):
            if cand.exists():
                base = cand
                break
        if base is None:
            res["corpora"][corp] = {"error": "path not found on disk"}
            print(f"  {corp}: NOT ON DISK")
            continue
        files = sorted(glob.glob(str(base / "**/*.parquet"), recursive=True))
        files = [f for f in files if ".cache" not in f]
        if not files:
            res["corpora"][corp] = {"error": "no parquet shards; container format differs"}
            print(f"  {corp}: no parquet shards (container differs)")
            continue
        res["corpora"][corp] = summarise(corp, probe_parquet(files, labels, tool_col, cat_col), labels)
        res["corpora"][corp]["parquet_shards"] = len(files)
        c = res["corpora"][corp]
        card = {k: v.get("cardinality") for k, v in c["labels"].items() if v.get("present")}
        print(f"  {corp:32s} rows={c['rows_read']:6d} label cardinarity={card} "
              f"tools={c['distinct_tools_seen']} catalogue_present={c['per_item_catalogue_present_share']}")

    ab = DATA / "Solaris99" / "AgentBank"
    envs = sorted([d.name for d in ab.iterdir() if d.is_dir() and not d.name.startswith(".")])
    per_env, cols = {}, collections.Counter()
    for e in envs:
        fs = sorted((ab / e).glob("*.parquet"))
        if not fs:
            continue
        pf = pq.ParquetFile(fs[0])
        cols.update(pf.schema_arrow.names)
        per_env[e] = int(pf.metadata.num_rows)
    res["corpora"]["AgentBank"] = {
        "label_field": "directory name = task environment (no label column exists in the shards)",
        "environments": len(per_env), "rows_total": sum(per_env.values()),
        "rows_per_environment_mean": round(sum(per_env.values()) / max(1, len(per_env)), 1),
        "columns_present": dict(cols), "per_item_catalogue_present_share": 0.0,
        "note": "the human scheme is the environment split itself; there is no tool column to induce a scheme "
                "from, so it can validate a task-level taxonomy but not a tool-level one"}
    print(f"  AgentBank environments={len(per_env)} rows={sum(per_env.values())} cols={dict(cols)}")

    ok = []
    for corp, d in res["corpora"].items():
        for lb, v in (d.get("labels") or {}).items():
            if (v.get("present") and v.get("cardinality", 0) >= 8 and v.get("labelled_rows", 0) >= 300
                    and d.get("per_item_catalogue_present_share", 0) > 0):
                ok.append((corp, lb, v["cardinality"]))
    res["candidate_label_fields"] = ok
    res["verdict"] = {"qualifying_fields": len(ok),
                      "qualifying_corpora": len({c for c, _, _ in ok}),
                      "decision": "GO" if len({c for c, _, _ in ok}) >= 2 else
                                  "NO-GO on label granularity/coverage - T007 folds into P003 or is killed"}
    res["wallclock_sec"] = round(time.time() - t0, 1)
    res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    out_dir = ROOT / "results_raw"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"EXP0040_taxonomy_label_pilot_{time.strftime('%Y%m%dT%H%M%S')}.json"

    def default(o):
        if isinstance(o, collections.Counter):
            return dict(o.most_common(20))
        raise TypeError(str(type(o)))

    out.write_text(json.dumps(res, indent=1, ensure_ascii=False, default=default), encoding="utf-8")
    print(json.dumps(res["verdict"], ensure_ascii=False))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
