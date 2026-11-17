"""P004 shared loading and statistics layer (frozen by papers/P004_shipped_quality_score_validity/protocol_freeze.md).

Everything the main experiments need, in one place so E2/E3/E4/E5 cannot drift apart in sampling or naming:
  * the frozen sample rule (seed 42, 10 random shards per config, <= 2,000 rows read per shard, dev rows only);
  * score parsing from the two shipped JSON columns, with parse failures counted rather than dropped silently;
  * the rule-extracted executed-tool criterion (section 2 of the freeze), which is the only new ground truth this
    paper builds - it never asks a model anything;
  * prompt_id-clustered bootstrap CIs (a score computed from a catalogue is clustered by that catalogue's cue),
    Cronbach alpha with a clustered CI, and Holm correction.
"""
from __future__ import annotations

import json, random, re, sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(r"G:/刘俊琦/AGENT ENGINEERING/MATLABINTOKEN/datasets/Agent-Ark/Toucan-1.5M")
PROC = ROOT / "01_datasets" / "processed"
SEED, SHARDS, ROWS_PER_SHARD = 42, 10, 2000
CONFIGS = ["OSS", "Qwen3", "Kimi-K2"]
QD = ["tool_selection_difficulty", "tool_selection_uniqueness", "question_quality", "scenario_realism",
      "verifiable", "stability"]
RD = ["completeness", "conciseness", "desired_tools_used_percentage", "order_correctness"]
DEV_BUCKET = 700
NAME_SPLIT = re.compile(r"__|::|\.")


def local_name(s):
    """Toucan qualifies tool names with the server slug; gold lists use the same convention, so compare locals."""
    return NAME_SPLIT.split(str(s).strip())[-1].strip().lower()


def bucket(pid: str) -> int:
    import hashlib
    return int(hashlib.md5(str(pid).encode()).hexdigest()[:8], 16) % 1000


def parse_scores(blob):
    try:
        q = json.loads(blob) if isinstance(blob, str) else (blob or {})
    except Exception:                                        # noqa: BLE001 - a parse failure is a finding
        return None, None
    qd, rd = {}, {}
    for k, v in (q or {}).items():
        qd["q_" + k] = v.get("score") if isinstance(v, dict) else v
    return qd, rd


def extract_response_scores(blob):
    try:
        a = json.loads(blob) if isinstance(blob, str) else (blob or {})
    except Exception:                                        # noqa: BLE001
        return None
    return {"r_" + k: (v.get("score") if isinstance(v, dict) else v) for k, v in (a or {}).items()}


def called_tools(messages_blob):
    """Rule extraction of which tools the trajectory actually invoked. Handles the shapes seen in this corpus:
    function_call/name, tool_calls[].function.name, and ```tool_code``` blocks naming a function."""
    try:
        ms = json.loads(messages_blob) if isinstance(messages_blob, str) else (messages_blob or [])
    except Exception:                                        # noqa: BLE001
        return None
    names = set()
    for m in ms if isinstance(ms, list) else []:
        if not isinstance(m, dict):
            continue
        fc = m.get("function_call") or m.get("tool_call")
        if isinstance(fc, dict) and fc.get("name"):
            names.add(local_name(fc["name"]))
        for tc in (m.get("tool_calls") or []):
            if isinstance(tc, dict):
                nm = (tc.get("function") or {}).get("name") or tc.get("name")
                if nm:
                    names.add(local_name(nm))
        if m.get("name"):
            names.add(local_name(m["name"]))
        c = m.get("content")
        if isinstance(c, str):
            for mm in re.finditer(r"\b([a-zA-Z_][\w.]{2,})\s*\(", c):
                names.add(local_name(mm.group(1)))
    return names


def load_config(cfg):
    """Frozen sample + P004's own objective criteria, computed on the rows it reads.

    The first implementation joined the published routing dataset to get fail@3, which collapsed the sample to a
    few thousand rows AND inherited P001's 2-of-10-shard coverage defect (deviation D31). The criteria are
    therefore recomputed here with the same frozen BM25 (k1=1.4, b=0.4) and the same gold-resolution code path the
    published pipeline uses, imported rather than re-implemented; EXP-0034 showed that path reproduces the
    published dev fail@3 to within sampling noise.
    """
    sys.path.insert(0, str(ROOT / "02_shared_code" / "trajectory_parser"))
    import build_toucan_routing_dataset as B
    files = sorted((DATA / cfg).glob("*.parquet"))
    picks = sorted(random.Random(SEED).sample(files, min(SHARDS, len(files))))
    rows, n_parse_fail, n_reject = 0, 0, 0
    out = []
    for f in picks:
        have = set(pq.ParquetFile(f).schema_arrow.names)
        cols = [c for c in ("uuid", "metadata", "question", "question_quality_assessment",
                            "response_quality_assessment", "target_tools", "messages",
                            "available_tools", "tools") if c in have]
        for r in pq.read_table(f, columns=cols).slice(0, ROWS_PER_SHARD).to_pylist():
            rows += 1
            qd, _ = parse_scores(r.get("question_quality_assessment"))
            rd = extract_response_scores(r.get("response_quality_assessment"))
            if qd is None or rd is None:
                n_parse_fail += 1
                qd, rd = {}, {}
            try:
                pid = str(json.loads(r["metadata"]).get("prompt_id") or r["uuid"])
            except Exception:                                # noqa: BLE001
                pid = str(r["uuid"])
            cat = B.parse_catalog(r.get("available_tools") or r.get("tools"))
            if not cat:
                n_reject += 1
                continue
            items = [x.strip() for x in re.split(r",(?![^{]*\})", str(r.get("target_tools") or "")) if x.strip()]
            srv_idx, srv_slugs = B.server_tool_index(r.get("metadata"))
            matched, _why = B.resolve_gold_v2(items, cat, srv_idx, srv_slugs) if items else (None, "no_gold")
            qtok = B.toks(str(r.get("question") or ""))
            docs = [B.toks(d["name"].replace("-", " ").replace("_", " ")) + B.toks(d["desc"])
                    + B.toks(" ".join(d["params"])) for d in cat]
            sc = B.BM25().scores(qtok, docs)
            ranked = sorted(range(len(sc)), key=lambda i: -sc[i])
            rb = min((ranked.index(i) + 1 for i in matched), default=len(cat)) if matched else len(cat)
            gold = {local_name(x) for x in items}
            called = called_tools(r.get("messages"))
            out.append({"uuid": r["uuid"], "prompt_id": pid, "cfg": cfg, **qd, **rd,
                        "fail_at_3": int(rb > 3), "bm25_best_rank": rb, "n_candidates": len(cat),
                        "n_gold": len(gold), "n_called": len(called or set()),
                        "executed_tool_agreement": (len(gold & (called or set())) / len(gold)) if gold else np.nan,
                        "q_chars": len(str(r.get("question") or "")), "gold_resolved": matched is not None})
    df = pd.DataFrame(out)
    return df, {"shards_picked": len(picks), "source_rows_read": rows,
                "score_json_parse_failures": n_parse_fail, "catalogue_unparseable": n_reject,
                "rows_with_criteria": int(len(df))}


def frame(cfg):
    df, meta = load_config(cfg)
    n_before = len(df)
    df = df[df.prompt_id.map(bucket) < DEV_BUCKET].copy()      # the published dev bucket; P004 never touches the
    meta["rows_dropped_outside_dev_bucket"] = int(n_before - len(df))  # single-use test split of any paper
    meta["parse_failure_rate"] = round(meta["score_json_parse_failures"] / max(1, meta["source_rows_read"]), 5)
    meta["gold_resolution_rate"] = round(float(df.gold_resolved.mean()), 4) if len(df) else None
    meta["dev_rows"] = int(len(df))
    return df, meta


def clustered_ci(df, cols, fn, draws=2000, seed=SEED):
    """Bootstrap CIs resampling whole prompt_id groups - never individual rows.

    `cols` are the columns the statistic needs, so the dropna happens on exactly those and the same frame is
    handed back to `fn` on each resample.
    """
    if "prompt_id" not in df.columns:
        raise ValueError("clustered_ci needs prompt_id in the frame; a row-level bootstrap would understate "
                         "the interval and the caller must pass the full frame")
    need = [c for c in cols if c in df.columns]
    d = df[need + (["prompt_id"] if "prompt_id" in df.columns else [])].dropna(subset=need)
    groups = [g.index.values for _, g in d.groupby("prompt_id")]
    if not groups:
        return None, None, 0
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(draws):
        take = np.concatenate([groups[i] for i in rng.choice(len(groups), len(groups), True)])
        try:
            v = fn(d.loc[take])
        except Exception:                                     # noqa: BLE001 - degenerate resamples happen
            continue
        if v is not None and np.isfinite(v):
            out.append(float(v))
    if not out:
        return None, None, 0
    a = np.array(out)
    return round(float(np.percentile(a, 2.5)), 4), round(float(np.percentile(a, 97.5)), 4), len(a)


def rho(df, x, y):
    from scipy.stats import spearmanr
    sub = df[[x, y]].dropna()
    if len(sub) < 50 or sub[x].std() == 0 or sub[y].std() == 0:
        return np.nan
    return float(spearmanr(sub[x], sub[y]).statistic)


def alpha(df, items):
    X = df[items].dropna()
    k = X.shape[1]
    if k < 2 or len(X) < 50:
        return np.nan
    v = X.sum(axis=1).var(ddof=1)
    if v == 0:
        return np.nan
    return float(k / (k - 1) * (1 - X.var(axis=0, ddof=1).sum() / v))


def holm(pvals):
    """Holm step-down on a dict of {name: p}; returns {name: adjusted}."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    n = len(items)
    out, prev = {}, 0.0
    for i, (k, p) in enumerate(items):
        adj = min(1.0, (n - i) * p)
        prev = max(prev, adj)
        out[k] = round(prev, 6)
    return out


def residual(df, target, controls):
    """Rank-residualise `target` on `controls` (Spearman-friendly: z-scored ranks)."""
    import numpy as np
    sub = df[[target] + controls].dropna()
    if len(sub) < 50:
        return pd.Series(np.nan, index=df.index)
    def z(s):
        r = s.rank(pct=True)
        sd = r.std(ddof=0)
        return (r - r.mean()) / (sd if sd and sd > 0 else 1)
    X = np.column_stack([np.ones(len(sub))] + [z(sub[c]).values for c in controls])
    y = z(sub[target]).values
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ beta
    out = pd.Series(np.nan, index=df.index)
    out.loc[sub.index] = res
    return out
