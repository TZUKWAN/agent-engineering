"""Feasibility probe: can gold `target_tools` be resolved onto `available_tools`?

T001/T002/T003/T006/T024/T026/T032/T033 all stand on one unverified assumption:
that the comma-separated `target_tools` string refers to entries actually present
in the same row's tool catalog. If the join fails there is no retrieval ground
truth and every one of those topics dies.

First run (2026-09-18, this file's git history) measured resolution_rate 0.0 under
naive name matching. The cause is real and is itself a finding: gold items are
written as `"Movie Recommender::get_movies"` while the catalog flattens the same
tool into the slug `"movie-recommender-get_movies"`, so the two identifier
conventions never coincide. This version tests the deterministic slug mapping.

    python probe_gold_tool_grounding.py [--rows N] [--configs OSS Qwen3 Kimi-K2 SFT]

Writes results_raw/P000_gold_tool_grounding_<ts>.json. Exit 0 only when every
config grounds >=90% of gold items.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import time
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

SEED = 42
DATA = Path(r"G:/刘俊琦/AGENT ENGINEERING/MATLABINTOKEN/datasets/Agent-Ark/Toucan-1.5M")
CATALOG_COL = {"OSS": "available_tools", "Qwen3": "available_tools",
               "Kimi-K2": "available_tools", "SFT": "tools"}
MIN_GROUNDING = 0.90


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")


def catalog_entries(catalog_json: str):
    """-> list of (flat_name, function_name, description) from the row's catalog."""
    try:
        cat = json.loads(catalog_json)
    except Exception:
        return None
    if not isinstance(cat, list):
        return None
    out = []
    for e in cat:
        if not isinstance(e, dict):
            continue
        f = e.get("function") if isinstance(e.get("function"), dict) else e
        name = f.get("name") or f.get("tool_name") or f.get("id")
        if not name:
            continue
        out.append((str(name), str(f.get("name") or name), str(f.get("description") or "")))
    return out


def gold_items(target_tools: str):
    if not target_tools or not str(target_tools).strip():
        return []
    return [t.strip() for t in re.split(r",(?![^{]*\})", str(target_tools)) if t.strip()]


def resolve(gold: str, names: set, by_func: dict, by_suffix: dict):
    """Return (method, matched_name). method in M1..M6/FAIL."""
    if gold in names:
        return "M1_exact", gold
    if "::" in gold:
        server, func = gold.split("::", 1)
        server, func = server.strip(), func.strip()
        cand = slug(server) + "-" + slug(func)
        if cand in names:
            return "M2_slug_server_dash_func", cand
        cand2 = slug(server) + slug(func)
        if cand2 in names:
            return "M3_slug_concat", cand2
        hits = by_suffix.get(slug(func), [])
        if len(hits) == 1:
            return "M4_suffix_unique", hits[0]
        if len(hits) > 1:
            return "M5_suffix_ambiguous", hits[0]
    hits = by_suffix.get(slug(gold), [])
    if len(hits) == 1:
        return "M4_suffix_unique", hits[0]
    if len(hits) > 1:
        return "M5_suffix_ambiguous", hits[0]
    return "FAIL", None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=400)
    ap.add_argument("--configs", nargs="+", default=["OSS", "Qwen3", "Kimi-K2", "SFT"])
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    rng = random.Random(SEED)
    report: dict = {"probe": "gold target_tools -> catalog grounding under slug mapping",
                    "seed": SEED, "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "min_grounding_required": MIN_GROUNDING, "configs": {}}
    print(f"probe: gold-tool grounding | seed={SEED} | rows/config={args.rows}")
    ok_all = True

    for cfg in args.configs:
        col = CATALOG_COL.get(cfg, "available_tools")
        shards = sorted((DATA / cfg).glob("*.parquet"))
        if not shards:
            report["configs"][cfg] = {"error": "no shards"}
            ok_all = False
            continue
        shard = rng.choice(shards)
        tbl = pq.read_table(shard, columns=["uuid", "question", col, "target_tools", "subset_name"])
        n = min(args.rows, tbl.num_rows)
        rows = tbl.take(sorted(rng.sample(range(tbl.num_rows), n))).to_pylist()

        c: Counter = Counter()
        ex_fail, ex_ambig, ex_ok = [], [], []
        for r in rows:
            entries = catalog_entries(r[col])
            if entries is None:
                c["catalog_unparseable"] += 1
                continue
            names = {e[0] for e in entries}
            # suffix index: a gold bare function name refers to the catalog entry whose
            # flattened slug ends with it ("met-museum-server-search-museum-objects"
            # is reachable from "search-museum-objects").
            by_suffix: dict[str, list] = {}
            for e in entries:
                parts = slug(e[0]).split("-")
                seen = set()
                for i in range(len(parts)):
                    sfx = "-".join(parts[i:])
                    if sfx not in seen:
                        by_suffix.setdefault(sfx, []).append(e[0])
                        seen.add(sfx)
            items = gold_items(r["target_tools"])
            if not items:
                c["gold_empty"] += 1
                continue
            c["catalog_parseable"] += 1
            row_all_ok = True
            for it in items:
                c["gold_items"] += 1
                method, matched = resolve(it, names, {}, by_suffix)
                c[method] += 1
                if method == "FAIL":
                    row_all_ok = False
                    if len(ex_fail) < 3:
                        ex_fail.append({"uuid": r["uuid"], "gold": it, "catalog_names": sorted(names)[:6]})
                elif method == "M5_suffix_ambiguous":
                    row_all_ok = False
                    if len(ex_ambig) < 3:
                        func_part = it.split("::")[-1] if "::" in it else it
                        ex_ambig.append({"uuid": r["uuid"], "gold": it, "matched": matched,
                                         "n_candidates": len(by_suffix.get(slug(func_part), []))})
                elif len(ex_ok) < 2:
                    ex_ok.append({"gold": it, "resolved_to": matched})
            c["rows_fully_grounded"] += int(row_all_ok)
        rate = 1 - c["FAIL"] / (c["gold_items"] or 1)
        per = {"rows_read": n, "catalog_column": col, "shard": shard.name,
               "gold_items": c["gold_items"], "counts_by_method": dict(c),
               "resolution_rate": round(rate, 4),
               "row_level_grounded_rate": round(c["rows_fully_grounded"] / (c["catalog_parseable"] or 1), 4),
               "ambiguous_rate": round(c["M5_func_suffix_ambiguous"] / (c["gold_items"] or 1), 4),
               "examples_resolved": ex_ok, "examples_ambiguous": ex_ambig, "examples_failed": ex_fail}
        report["configs"][cfg] = per
        ok_all = ok_all and rate >= MIN_GROUNDING
        print(f"\n[{cfg}] col={col} shard={shard.name} rows={n} gold_items={c['gold_items']}")
        print(f"   resolution_rate={rate:.4f}  row_level={per['row_level_grounded_rate']:.4f}  "
              f"ambiguous={per['ambiguous_rate']:.4f}")
        print(f"   by method: {dict((k, v) for k, v in c.items() if k.startswith('M'))}")
        if ex_ok:
            print(f"   resolved e.g.: {json.dumps(ex_ok[0], ensure_ascii=False)[:160]}")
        if ex_ambig:
            print(f"   AMBIGUOUS e.g.: {json.dumps(ex_ambig[0], ensure_ascii=False)[:200]}")
        if ex_fail:
            print(f"   FAILED e.g.: {json.dumps(ex_fail[0], ensure_ascii=False)[:300]}")

    ts = time.strftime("%Y%m%dT%H%M%S")
    outdir = Path(args.out) if args.out else Path(__file__).resolve().parents[2] / "results_raw"
    outdir.mkdir(parents=True, exist_ok=True)
    report["verdict"] = "PASS" if ok_all else "FAIL"
    p = outdir / f"P000_gold_tool_grounding_{ts}.json"
    p.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {p}")
    print(f"VERDICT {report['verdict']}: "
          + ("slug mapping grounds the gold labels -> retrieval topics feasible"
             if ok_all else
             f"grounding below {MIN_GROUNDING} -> T001/T002/T003 not feasible as designed"))
    return 0 if ok_all else 2


if __name__ == "__main__":
    raise SystemExit(main())
