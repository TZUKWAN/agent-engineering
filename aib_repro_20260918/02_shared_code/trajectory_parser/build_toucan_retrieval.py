"""Build the Toucan tool-retrieval corpus and run the W0 pilot baselines (EXP-0004).

Frozen join rule (docs/W0_data_feasibility_audit.md S7): a gold item resolves to a
catalog entry only if (M2) the server-slug + function slug equals the entry name,
or (M4) the entry is the unique name-suffix match AND, when the gold carries a
server prefix, that prefix agrees with the server the entry belongs to. Anything
else is excluded and the exclusion rate is reported, because silently accepting a
cross-server match would manufacture labels.

Metrics are computed for a purely lexical ranker, so they measure how reachable a
gold tool is from the user's own wording - not how well any agent routed.

    python build_toucan_retrieval.py --rows-per-config 5000

Outputs:
  01_datasets/processed/toucan_retrieval_<cfg>.parquet
  results_raw/EXP0004_toucan_retrieval_pilot_<ts>.json
  00_program_registry/experiment_registry.append.csv   (paste into the registry)
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

SEED = 42
DATA = Path(r"G:/刘俊琦/AGENT ENGINEERING/MATLABINTOKEN/datasets/Agent-Ark/Toucan-1.5M")
ROOT = Path(__file__).resolve().parents[2]
CONFIGS = {"OSS": "available_tools", "Qwen3": "available_tools", "Kimi-K2": "available_tools"}
STOP = set("""a an the and or of to in on for with without you your our i my is are be can could
will would should please them they it this that these those from at as by if then there here
what which how when where who all any some one two three first also just need want me help make
""".split())


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")


def toks(s: str) -> list[str]:
    """Identifier-aware tokenisation: splits snake_case, kebab-case and camelCase."""
    parts = re.split(r"[^A-Za-z0-9]+", str(s or ""))
    out: list[str] = []
    for p in parts:
        if not p:
            continue
        for sub in re.findall(r"[A-Z]+(?![a-z])|[A-Z][a-z]*|[a-z]+|\d+", p):
            out.append(sub.lower())
    return [t for t in out if t not in STOP and len(t) > 1 or (t.isdigit() and len(t) > 1)]


def parse_catalog(js: str):
    try:
        cat = json.loads(js)
    except Exception:
        return None
    if not isinstance(cat, list):
        return None
    entries = []
    for e in cat:
        if not isinstance(e, dict):
            continue
        f = e.get("function") if isinstance(e.get("function"), dict) else e
        name = f.get("name") or f.get("tool_name") or f.get("id")
        if not name:
            continue
        entries.append({"name": str(name),
                        "desc": str(f.get("description") or ""),
                        "params": list((f.get("parameters") or {}).get("properties", {}).keys())
                                   if isinstance(f.get("parameters"), dict) else []})
    return entries or None


def gold_items(target_tools: str) -> list[str]:
    if not target_tools or not str(target_tools).strip():
        return []
    return [t.strip() for t in re.split(r",(?![^{]*\})", str(target_tools)) if t.strip()]


def resolve_gold(items: list[str], entries: list[dict]):
    """-> (matched_index list, status counts). Raises ValueError if any item unresolved."""
    names = {e["name"] for e in entries}
    suffix_idx: dict[str, list[int]] = defaultdict(list)
    for i, e in enumerate(entries):
        parts = slug(e["name"]).split("-")
        for k in range(len(parts)):
            suffix_idx["-".join(parts[k:])].append(i)
    matched, stat = [], Counter()
    for it in items:
        if "::" in it:
            server, func = (x.strip() for x in it.split("::", 1))
            s_slug, f_slug = slug(server), slug(func)
            if f"{s_slug}-{f_slug}" in names:
                matched.append(next(i for i, e in enumerate(entries) if e["name"] == f"{s_slug}-{f_slug}"))
                stat["M2"] += 1
                continue
            cands = sorted({i for i in suffix_idx.get(f_slug, []) if slug(entries[i]["name"]).startswith(s_slug + "-")})
            if len(cands) == 1:
                matched.append(cands[0]); stat["M4_server_consistent"] += 1
            elif len(cands) > 1:
                stat["excluded_ambiguous"] += 1; raise ValueError("ambiguous")
            else:
                stat["excluded_unresolved"] += 1; raise ValueError("unresolved")
        else:
            f_slug = slug(it)
            if it in names:
                matched.append(next(i for i, e in enumerate(entries) if e["name"] == it)); stat["M1"] += 1
                continue
            cands = sorted(set(suffix_idx.get(f_slug, [])))
            if len(cands) == 1:
                matched.append(cands[0]); stat["M4_unique_suffix"] += 1
            elif len(cands) > 1:
                stat["excluded_ambiguous"] += 1; raise ValueError("ambiguous")
            else:
                stat["excluded_unresolved"] += 1; raise ValueError("unresolved")
    return sorted(set(matched)), stat


# ---------------- rankers ----------------

class BM25:
    """Okapi BM25 over the candidate documents of a single query."""
    def __init__(self, k1=1.4, b=0.4):
        self.k1, self.b = k1, b

    def rank(self, q_tokens, docs_tokens):
        n = len(docs_tokens)
        if n == 0:
            return []
        df, tf, dl = Counter(), [], []
        for d in docs_tokens:
            c = Counter(d)
            tf.append(c)
            dl.append(len(d))
            df.update(c.keys())
        avgdl = sum(dl) / n
        scores = []
        for i in range(n):
            s = 0.0
            for t in set(q_tokens):
                f = tf[i].get(t, 0)
                if not f:
                    continue
                idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                s += idf * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl[i] / avgdl))
            scores.append(s)
        return [i for i in range(n) if scores[i] > 0] + [i for i in range(n) if scores[i] <= 0] if False else \
               sorted(range(n), key=lambda i: -scores[i])


def doc_tokens(entries, i, mode):
    e = entries[i]
    name = toks(e["name"].replace("-", " ").replace("_", " "))
    if mode == "name":
        return name
    if mode == "desc":
        return toks(e["desc"])
    if mode == "desc_params":
        return toks(e["desc"]) + toks(" ".join(e["params"]))
    return name + toks(e["desc"]) + toks(" ".join(e["params"]))


def hit_at_k(ranked, gold, k):
    return float(any(g in ranked[:k] for g in gold))


def rr(ranked, gold):
    for r, i in enumerate(ranked, 1):
        if i in gold:
            return 1.0 / r
    return 0.0


def ndcg_at_k(ranked, gold, k=5):
    gains = [1.0 if i in gold else 0.0 for i in ranked[:k]]
    dcg = sum(g / math.log2(r + 2) for r, g in enumerate(gains))
    ideal = sorted([1.0] * min(len(gold), k) + [0.0] * max(0, k - len(gold)), reverse=True)
    idcg = sum(g / math.log2(r + 2) for r, g in enumerate(ideal))
    return dcg / idcg if idcg > 0 else 0.0


def mean_ci(vals, rng, boot=1000):
    m = sum(vals) / len(vals)
    bs = []
    n = len(vals)
    for _ in range(boot):
        s = sum(vals[rng.randrange(n)] for _ in range(n)) / n
        bs.append(s)
    bs.sort()
    return m, bs[int(0.025 * boot)], bs[int(0.975 * boot)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows-per-config", type=int, default=5000)
    ap.add_argument("--dev-frac", type=float, default=0.7)
    args = ap.parse_args()

    ts0 = time.time()
    rng = random.Random(SEED)
    report: dict = {"exp_id": "EXP-0004", "seed": SEED, "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "rows_requested_per_config": args.rows_per_config, "configs": {}}
    print(f"EXP-0004 Toucan retrieval pilot | seed={SEED} | rows/config={args.rows_per_config}")

    for cfg, col in CONFIGS.items():
        shards = sorted((DATA / cfg).glob("*.parquet"))
        pick = sorted(random.Random(SEED).sample(shards, min(4, len(shards))))
        rows_needed = args.rows_per_config
        got: list[dict] = []
        stat = Counter()
        for sp in pick:
            if len(got) >= rows_needed:
                break
            t = pq.read_table(sp, columns=["uuid", "question", col, "target_tools", "subset_name"])
            idx = sorted(random.Random(SEED).sample(range(t.num_rows), min(rows_needed - len(got), t.num_rows)))
            for r in t.take(idx).to_pylist():
                stat["rows_seen"] += 1
                entries = parse_catalog(r[col])
                if not entries:
                    stat["excluded_catalog"] += 1
                    continue
                items = gold_items(r["target_tools"])
                if not items:
                    stat["excluded_no_gold"] += 1
                    continue
                try:
                    matched, m_stat = resolve_gold(items, entries)
                except ValueError:
                    stat.update(m_stat if False else {})
                    stat["excluded_join_failed"] += 1
                    continue
                stat.update({f"join_{k}": v for k, v in m_stat.items()})
                got.append({"uuid": r["uuid"], "cfg": cfg, "question": r["question"],
                            "entries": entries, "gold": matched, "subset_name": r["subset_name"]})
            stat["rows_seen"] = stat["rows_seen"]

        by_uuid_split = [g for g in got if int(hashlib_md5(g["uuid"])) % 1000 < args.dev_frac * 1000]
        test = [g for g in got if g not in set(id(x) for x in by_uuid_split)] if False else \
               [g for g in got if int(hashlib_md5(g["uuid"])) % 1000 >= args.dev_frac * 1000]
        dev = by_uuid_split

        # corpus parquet
        schema = pa.schema([("uuid", pa.string()), ("split", pa.string()), ("question", pa.string()),
                            ("catalog_json", pa.string()), ("gold_idx", pa.list_(pa.int32())),
                            ("n_candidates", pa.int32()), ("n_gold", pa.int32()), ("subset_name", pa.string())])
        tbl = pa.table({
            "uuid": [g["uuid"] for g in got],
            "split": ["dev" if int(hashlib_md5(g["uuid"])) % 1000 < args.dev_frac * 1000 else "test" for g in got],
            "question": [g["question"] for g in got],
            "catalog_json": [json.dumps(g["entries"], ensure_ascii=False) for g in got],
            "gold_idx": [g["gold"] for g in got],
            "n_candidates": [len(g["entries"]) for g in got],
            "n_gold": [len(g["gold"]) for g in got],
            "subset_name": [g["subset_name"] for g in got]}, schema=schema)
        outp = ROOT / "01_datasets" / "processed" / f"toucan_retrieval_{cfg}.parquet"
        outp.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(tbl, outp)

        # pilot baselines on DEV only
        metrics: dict[str, list[float]] = defaultdict(list)
        cand_counts, gold_counts = [], []
        for g in dev:
            q = toks(g["question"])
            n = len(g["entries"])
            cand_counts.append(n)
            gold_counts.append(len(g["gold"]))
            docs_full = [doc_tokens(g["entries"], i, "full") for i in range(n)]
            docs_desc = [doc_tokens(g["entries"], i, "desc") for i in range(n)]
            docs_name = [doc_tokens(g["entries"], i, "name") for i in range(n)]
            metrics["B0_random"].append(hit_at_k(rng.sample(range(n), n), g["gold"], 1))
            metrics["B0_random_mrr"].append(rr(rng.sample(range(n), n), g["gold"]))
            names_sorted = sorted(range(n), key=lambda i: g["entries"][i]["name"])
            metrics["B0_alphabetical_hit1"].append(hit_at_k(names_sorted, g["gold"], 1))
            metrics["B1_bm25_name_hit1"].append(hit_at_k(BM25().rank(q, docs_name), g["gold"], 1))
            metrics["B1_bm25_desc_hit1"].append(hit_at_k(BM25().rank(q, docs_desc), g["gold"], 1))
            ranked = BM25().rank(q, docs_full)
            metrics["B1_bm25_full_hit1"].append(hit_at_k(ranked, g["gold"], 1))
            metrics["B1_bm25_full_hit3"].append(hit_at_k(ranked, g["gold"], 3))
            metrics["B1_bm25_full_hit5"].append(hit_at_k(ranked, g["gold"], 5))
            metrics["B1_bm25_full_mrr"].append(rr(ranked, g["gold"]))
            metrics["B1_bm25_full_ndcg5"].append(ndcg_at_k(ranked, g["gold"], 5))

        r2 = random.Random(SEED)
        summ = {}
        for k, v in metrics.items():
            m, lo, hi = mean_ci(v, r2)
            summ[k] = {"mean": round(m, 4), "ci95": [round(lo, 4), round(hi, 4)], "n": len(v)}
        report["configs"][cfg] = {
            "exclusion_accounting": dict(stat),
            "rows_kept": len(got), "dev_rows": len(dev), "test_rows": len(test),
            "corpus_parquet": str(outp),
            "candidates_per_query": {"mean": round(sum(cand_counts) / len(cand_counts), 2),
                                     "min": min(cand_counts), "max": max(cand_counts)},
            "gold_per_query": {"mean": round(sum(gold_counts) / len(gold_counts), 3),
                               "max": max(gold_counts)},
            "dev_baselines": summ}
        print(f"\n[{cfg}] kept={len(got)} dev={len(dev)} test={len(test)}  exclusions={dict(stat)}")
        for k in sorted(summ):
            print(f"   {k:26s} {summ[k]['mean']:.4f}  CI95 {summ[k]['ci95']}")

    report["wallclock_sec"] = round(time.time() - ts0, 1)
    report["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    out = ROOT / "results_raw" / f"EXP0004_toucan_retrieval_pilot_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {out}  (wallclock {report['wallclock_sec']}s)")
    return 0


def hashlib_md5(s: str) -> str:
    """Stable 0-999 bucket from a uuid, independent of python hash randomisation."""
    import hashlib
    return int(hashlib.md5(str(s).encode()).hexdigest()[:8], 16)


if __name__ == "__main__":
    raise SystemExit(main())
