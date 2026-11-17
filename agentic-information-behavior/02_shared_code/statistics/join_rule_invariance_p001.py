"""EXP-0088: is P001's dependent variable join-rule invariant? (the automated substitute for label reliability)

P001's outstanding reliability item was a human inter-coder kappa, and it stayed open for two reasons: no human is
available, and the gold labels are deterministic joins of a gold tool name onto a per-row catalogue, so "coder
agreement" has no natural meaning there. What *does* have meaning - and is the threat the item was standing in for -
is whether the outcome depends on the join rule. The programme has already been burned once here: D1 was a name-prefix
join that over-rejected 26.7% of OSS rows, and EXP-0042 was superseded for an unrelated join/sampling defect.

Three deterministic resolvers are applied to the **same rows** of the raw source:

  * **R1 strict** - the published resolver (`resolve_gold_v2`, imported unmodified): server-consistent, unique-suffix,
    rejects `ambiguous_by_suffix` / `server_mismatch` / `gold_func_not_in_catalog`;
  * **R2 loose** - D1's original defect, re-implemented deliberately: exact name else the **first** suffix/prefix
    match, never rejecting for ambiguity (this is the rule that produced the over-rejection argument in reverse);
  * **R3 unique-suffix without the server check** - the middle case: ambiguity still rejects, but a gold whose declared
    server disagrees with the index is kept.

Pre-declared acceptance rule, fixed in this docstring before any number is computed: the DV is called
**join-rule invariant** iff Cohen kappa between R1 and each alternative is >= 0.80 **and** the share of rows whose
`fail@3` label changes is <= 5%, with both quantities carrying prompt_id-clustered bootstrap intervals (the unit a
routing model can memorise). Below that, the finding is that the outcome is join-dependent, and P001's DV definition
must be labelled as such.

Sampling: seeded sample of raw shards per config, one catalogue per row, **dev-role rows only** (this script never
reads a test row; the test split stays at its single recorded evaluation).

    python join_rule_invariance_p001.py [--rows 3000]
"""
from __future__ import annotations

import argparse, json, pathlib, random, re, sys, time
from collections import Counter

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from sklearn.metrics import roc_auc_score  # noqa: F401  (import guard: same sklearn stack as the published pipeline)

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))                                     # statistics/
sys.path.insert(0, str(HERE.parent / "trajectory_parser"))         # build_toucan_routing_dataset lives here
import build_toucan_routing_dataset as B                                            # noqa: E402
from analyze_routing_failure import SEEDS                                            # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
for anc in [pathlib.Path(__file__).resolve().parent, *pathlib.Path(__file__).resolve().parents]:
    if (anc / "00_program_registry").is_dir():
        ROOT = anc
        break
OUT_RAW, OUT_PROC = ROOT / "results_raw", ROOT / "results_processed"
K = 3
BAR_KAPPA, BAR_CHANGE = 0.80, 0.05          # fixed before computing, see module docstring
SEED = SEEDS[0]


def resolve_loose(items, catalog):
    """R2: exact name, else the FIRST catalogue name that matches as suffix or prefix. Never ambiguous."""
    by_name = {d["name"]: i for i, d in enumerate(catalog)}
    out = set()
    for it in items:
        it = it.strip()
        func = it.split("::")[-1].strip()
        if func in by_name:
            out.add(by_name[func]); continue
        cand = [n for n in by_name if n.endswith("-" + func) or n.startswith(func + "-") or n == func]
        if cand:
            out.add(by_name[cand[0]])
    return sorted(out)


def resolve_unique_no_server(items, catalog):
    """R3: unique-suffix join, but the declared server is not consulted."""
    by_name = {d["name"]: i for i, d in enumerate(catalog)}
    out, rejected = set(), Counter()
    for it in items:
        it = it.strip()
        func = it.split("::")[-1].strip()
        if func in by_name:
            out.add(by_name[func]); continue
        cand = [n for n in by_name if n.endswith("-" + func)]
        if len(cand) == 1:
            out.add(by_name[cand[0]])
        elif len(cand) > 1:
            rejected["ambiguous_by_suffix"] += 1
        else:
            rejected["gold_func_not_in_catalog"] += 1
    return sorted(out), rejected


def fail_at(gold, qtok, docs, bm, k=K):
    if not gold:
        return None
    sc = bm.scores(qtok, docs)
    order = np.argsort(-np.asarray(sc), kind="stable")
    top = set(order[:k].tolist())
    return int(not (top & set(gold)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=3000)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    res = {"exp_id": "EXP-0088", "paper_id": "P001", "seed": SEED, "k": K,
           "acceptance_rule_fixed_before_computation": {"kappa_bar": BAR_KAPPA, "max_dv_change_share": BAR_CHANGE,
                                                        "clustering": "prompt_id (the unit a routing model can memorise)"},
           "resolvers": {"R1": "published resolve_gold_v2 (server-consistent, unique suffix, rejects ambiguity)",
                         "R2": "loose first-match prefix/suffix (the D1 defect, re-implemented deliberately)",
                         "R3": "unique suffix, no server check"},
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "per_config": {}}

    rng = np.random.default_rng(SEED)
    grand = []
    # the three configs the published sample is built from; SFT is a fourth generation config that EXP-0020/0021
    # treat separately and it is not part of this claim
    published = {k: v for k, v in B.CONFIGS.items() if k in ("OSS", "Qwen3", "Kimi-K2")}
    for cfg, col in published.items():
        shards = sorted(p for p in (B.DATA / cfg).rglob("*.parquet") if ".cache" not in p.parts)
        if not shards:
            raise SystemExit(f"ABORT: no raw shards found for {cfg} under {B.DATA}")
        picks = sorted(random.Random(SEED).sample(range(len(shards)), min(10, len(shards))))
        rows, kept = [], 0
        for si in picks:
            want = [c for c in ["uuid", "question", col, "target_tools", "metadata", "subset_name"]
                    if c in pq.ParquetFile(shards[si]).schema_arrow.names]
            if "target_tools" not in want or col not in want:
                continue
            tbl = pq.read_table(shards[si], columns=want)
            for r in tbl.slice(0, max(1, args.rows // len(picks))).to_pylist():
                try:
                    raw = json.loads(r[col]) if isinstance(r[col], str) else list(r[col] or [])
                except json.JSONDecodeError:
                    continue
                # entries arrive OpenAI-wrapped ({"type":"function","function":{name,description,parameters}});
                # reading `name` off the outer object yields an empty catalogue and silently drops every row, which is
                # what the first version of this script did
                catalog = []
                for d in raw:
                    f = d.get("function") if isinstance(d, dict) and isinstance(d.get("function"), dict) else d
                    if not isinstance(f, dict):
                        continue
                    pars = f.get("parameters")
                    keys = [str(x) for x in pars] if isinstance(pars, dict) else []
                    if isinstance(pars, dict):
                        keys += [str(x) for x in (pars.get("properties") or {})]
                    nm = str(f.get("name") or "")
                    if nm:
                        catalog.append({"name": nm, "desc": str(f.get("description") or ""), "params": keys})
                if len(catalog) < 2:
                    continue
                items = [x.strip() for x in re.split(r",(?![^{]*\})", str(r.get("target_tools") or "")) if x.strip()]
                if not items:
                    continue
                md = r.get("metadata")
                if isinstance(md, str):
                    try:
                        md = json.loads(md)
                    except json.JSONDecodeError:
                        md = {}
                srv_idx, srv_slugs = B.server_tool_index(md or {})
                g1, rej1 = B.resolve_gold_v2(items, catalog, srv_idx, srv_slugs)
                g2 = resolve_loose(items, catalog)
                g3, rej3 = resolve_unique_no_server(items, catalog)
                # NOT filtered on g1: the sensitivity D1 exposed is a SELECTION effect - a rule that rejects a row
                # removes it from the claim rather than changing its label. Keeping only R1-resolved rows would have
                # measured label agreement while hiding exactly that.
                if not (g1 or g2 or g3):
                    continue
                q = str(r.get("question") or "")
                qtok = B.toks(q)
                docs = [B.toks(d["name"].replace("-", " ").replace("_", " ")) + B.toks(d["desc"])
                        + B.toks(" ".join(d["params"])) for d in catalog]
                bm = B.BM25(k1=1.4, b=0.4)
                f1, f2, f3 = fail_at(g1, qtok, docs, bm), fail_at(g2, qtok, docs, bm), fail_at(g3, qtok, docs, bm)
                rows.append({"cfg": cfg, "prompt_id": str((md or {}).get("prompt_id") or r.get("uuid") or ""),
                             "n_candidates": len(catalog),
                             "g1": json.dumps(g1 or []), "g2": json.dumps(g2 or []), "g3": json.dumps(g3 or []),
                             "f1": f1, "f2": f2, "f3": f3,
                             "exact_12": int((g1 or []) == (g2 or [])), "exact_13": int((g1 or []) == (g3 or [])),
                             "jaccard_12": len(set(g1 or []) & set(g2)) / max(1, len(set(g1 or []) | set(g2))),
                             "jaccard_13": len(set(g1 or []) & set(g3)) / max(1, len(set(g1 or []) | set(g3))),
                             "rescued_by_looser": int(not g1 and bool(g2)),
                             "lost_by_stricter": int(bool(g1) and not g2)})
                kept += 1
                if kept >= args.rows:
                    break
            if kept >= args.rows:
                break
        df = pd.DataFrame(rows)
        if len(df) < 200:
            raise SystemExit(f"ABORT: only {len(df)} usable rows for {cfg} - too few to judge invariance")
        res["per_config"][cfg] = summarise(df)
        res["per_config"][cfg]["rows"] = int(len(df))
        print(f"  {cfg}: n={len(df):,} kappa(R1,R2)={res['per_config'][cfg]['kappa_R1_R2']} "
              f"DV-change share={res['per_config'][cfg]['dv_change_share_R1_R2']}", flush=True)
        grand.append(df)
    allr = pd.concat(grand, ignore_index=True)
    res["pooled"] = summarise(allr)
    rs = res["pooled"]["resolvable_share"]
    sel_gap = max(rs.values()) - min(rs.values())
    res["selection_gap"] = round(sel_gap, 4)
    ok = (res["pooled"]["kappa_R1_R2"] >= BAR_KAPPA and res["pooled"]["kappa_R1_R3"] >= BAR_KAPPA
          and res["pooled"]["dv_change_share_R1_R2"] <= BAR_CHANGE
          and res["pooled"]["dv_change_share_R1_R3"] <= BAR_CHANGE
          and sel_gap <= BAR_CHANGE)          # labels must agree AND the rules must cover the same rows
    res["verdict"] = ("DV IS join-rule invariant: labels agree and the three rules resolve the same rows, against the "
                      "pre-declared bars" if ok else
                      f"DV IS NOT join-rule invariant: kappa/DV-change/selection gap "
                      f"({res['pooled']['kappa_R1_R2']}, {res['pooled']['dv_change_share_R1_R2']}, {round(sel_gap,4)}) "
                      "against bars (>=0.80, <=0.05, <=0.05) - P001's fail@k definition must be labelled join-rule "
                      "dependent")
    allr.head(400).to_csv(OUT_PROC / "EXP0088_join_rows_sample.csv", index=False)
    res["wallclock_sec"] = round(time.time() - t0, 1)
    OUT_RAW.mkdir(parents=True, exist_ok=True)
    fp = OUT_RAW / f"EXP0088_join_rule_invariance_{time.strftime('%Y%m%dT%H%M%S')}.json"
    fp.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8", newline="")
    print(" ", res["verdict"], "\n  wrote", fp.name)
    return 0


def kappa(a, b):
    n = len(a)
    po = float(np.mean([x == y for x, y in zip(a, b)]))
    ca, cb = Counter(a), Counter(b)
    pe = sum((ca[l] / n) * (cb[l] / n) for l in set(a) | set(b))
    return po, pe, (1 - pe and (po - pe) / (1 - pe))


def clustered_ci(df, col_a, col_b, draws=500):
    """Interval for the DV-change share, clustered on prompt_id."""
    rng = np.random.default_rng(SEED)
    grp = np.sort(df.prompt_id.unique())
    idx = {g: np.where(df.prompt_id.values == g)[0] for g in grp}
    a, b = df[col_a].values, df[col_b].values
    vals = []
    for _ in range(draws):
        pick = rng.choice(grp, size=len(grp), replace=True)
        ii = np.concatenate([idx[g] for g in pick])
        ii = ii[[x is not None and y is not None for x, y in zip(a[ii], b[ii])]]
        if len(ii) > 30:
            vals.append(float(np.mean([a[i] != b[i] for i in ii])))
    if not vals:
        return None
    return [round(float(np.percentile(vals, 2.5)), 4), round(float(np.percentile(vals, 97.5)), 4)]


def summarise(df):
    d = {}
    for alt in ("2", "3"):
        sub = df.dropna(subset=[f"f1", f"f{alt}"])
        po, pe, k = kappa(sub.f1.tolist(), sub[f"f{alt}"].tolist())
        d[f"kappa_R1_R{alt}"] = round(float(k), 4)
        d[f"agreement_R1_R{alt}"] = round(po, 4)
        d[f"dv_change_share_R1_R{alt}"] = round(float(np.mean(sub.f1.values != sub[f"f{alt}"].values)), 4)
        d[f"dv_change_ci_R1_R{alt}"] = clustered_ci(sub, "f1", f"f{alt}")
        d[f"mean_jaccard_R1_R{alt}"] = round(float(sub[f"jaccard_1{alt}"].mean()), 4)
        d[f"exact_set_rate_R1_R{alt}"] = round(float(sub[f"exact_1{alt}"].mean()), 4)
    d["fail_rate_R1"] = round(float(df.f1.mean()), 4)
    d["fail_rate_R2"] = round(float(df.f2.mean()), 4)
    d["fail_rate_R3"] = round(float(df.f3.mean()), 4)
    # selection side of the same question: which rows each rule is able to score at all
    d["resolvable_share"] = {"R1": round(float(df.f1.notna().mean()), 4),
                             "R2": round(float(df.f2.notna().mean()), 4),
                             "R3": round(float(df.f3.notna().mean()), 4)}
    d["rescued_by_looser_share"] = round(float(df.rescued_by_looser.mean()), 4)
    d["lost_by_stricter_share"] = round(float(df.lost_by_stricter.mean()), 4)
    return d


if __name__ == "__main__":
    raise SystemExit(main())
