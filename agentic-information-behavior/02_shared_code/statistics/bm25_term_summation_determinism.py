"""EXP-0151: is the frozen ranker's hit@1 label invariant to PYTHONHASHSEED?

Found while checking whether a battery re-run reproduced its own numbers: two runs of identical code on identical
rows disagreed on which side of an exact tie won, because `BM25.rank` and `wave_lib._bm25_scores` summed the query
terms in `set` iteration order and float addition is not associative. This script measures how much of the dev
sample is exposed to that (rows where the gold ties exactly with the best rival), and proves that the old
accumulation moves hit@1 between hash seeds while the fixed one does not.

    python 02_shared_code/statistics/bm25_term_summation_determinism.py [--seeds 0 1 7]

No model, no API: rule scoring on the frozen dev rows only.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
sys.path.insert(0, str(ROOT / "02_shared_code" / "package_factory"))
import wave_lib as W                                              # noqa: E402

CHILD = r'''
import json, math, random, sys
from collections import Counter
sys.path.insert(0, "02_shared_code/package_factory")
import pandas as pd
import wave_lib as W


def old_scores(q_tokens, docs_tokens, k1=1.4, b=0.4):
    """The accumulation as it stood before EXP-0151: query terms in `set` order."""
    n = len(docs_tokens)
    df, tf, dl = Counter(), [], []
    for dd in docs_tokens:
        c = Counter(dd); tf.append(c); dl.append(len(dd)); df.update(c.keys())
    avgdl = sum(dl) / n if n else 1.0
    out = []
    for i in range(n):
        s = 0.0
        for t in set(q_tokens):
            f = tf[i].get(t, 0)
            if not f:
                continue
            idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
            s += idf * f * (k1 + 1) / (f + k1 * (1 - b + b * dl[i] / avgdl))
        out.append(s)
    return out


d = W.load_routing(cfgs=W.CONFIGS, bucket="dev")
d = d[d["subset_name"].astype(str).str.contains("single-turn-original", na=False)]
keep = []
for cfg, g in d.groupby("cfg"):
    keep.append(g.iloc[sorted(random.Random(W.SEED).sample(range(len(g)), min(2500, len(g))))])
d = pd.concat(keep, ignore_index=True)
hits_old, hits_new, ties, n = {}, {}, 0, 0
for r in d.itertuples(index=False):
    ent = W.read_catalog(r.catalog_json, r.n_candidates, r.query_id)
    gold = [i for i in W.as_int_list(r.gold_idx) if ent and i < len(ent)]
    t = W.toks(str(r.question))
    if not ent or not gold or not t:
        continue
    docs = [W.doc_tokens(ent, i, "full") for i in range(len(ent))]
    n += 1
    s = W._bm25_scores(t, docs)
    rival = [s[i] for i in range(len(s)) if i not in gold]
    if rival and any(abs(s[g] - max(rival)) < 1e-12 for g in gold):
        ties += 1
    hits_old[r.query_id] = int(min(W.rank_from(old_scores(t, docs))[i] for i in gold) == 1)
    hits_new[r.query_id] = int(min(W.rank_from(s)[i] for i in gold) == 1)
print(json.dumps({"n": n, "exact_ties": ties, "old": hits_old, "new": hits_new}))
'''


def run(seed: int) -> dict:
    p = subprocess.run([sys.executable, "-c", CHILD], capture_output=True, text=True, cwd=str(ROOT),
                       env={**os.environ, "PYTHONHASHSEED": str(seed), "PYTHONIOENCODING": "utf-8"})
    if p.returncode:
        raise SystemExit(f"ABORT: child with PYTHONHASHSEED={seed} failed:\n{p.stderr[-1200:]}")
    return json.loads(p.stdout.strip().splitlines()[-1])


def disagree(base: dict, other: dict) -> int:
    return sum(1 for k in base if base[k] != other[k])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 7])
    ap.add_argument("--exp", default="EXP-0151")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    res = [run(s) for s in a.seeds]
    n, ties = res[0]["n"], res[0]["exact_ties"]
    if any(r["n"] != n or r["exact_ties"] != ties for r in res):
        raise SystemExit("ABORT: the sampled row count moved between hash seeds, so the sample itself is not frozen")
    old_moves = {str(s): disagree(res[0]["old"], r["old"]) for s, r in zip(a.seeds[1:], res[1:])}
    new_moves = {str(s): disagree(res[0]["new"], r["new"]) for s, r in zip(a.seeds[1:], res[1:])}
    verdict = ("deterministic" if not any(new_moves.values()) and any(v for v in old_moves.values())
               else "deterministic_before_and_after" if not any(new_moves.values())
               else "NOT_DETERMINISTIC")
    out = {"verdict": verdict, "dev_rows_scored": n,
           "rows_with_gold_exactly_tied_with_best_rival": ties,
           "tie_share": round(ties / n, 5), "hash_seeds_probed": a.seeds,
           "hit1_rows_moved_between_seeds_old_accumulation": old_moves,
           "hit1_rows_moved_between_seeds_sorted_terms": new_moves,
           "rule": "the fixed scorer must move 0 rows across every seed probed; a nonzero old count is the "
                   "diagnosis, and an all-zero old count would mean these particular seeds did not expose it",
           "instrument": "wave_lib._bm25_scores / BM25.rank with k1=1.4, b=0.4, ties broken by candidate index"}
    dest = W.write_raw(a.exp, "bm25_summation_determinism", out)
    print(json.dumps(out, indent=1, ensure_ascii=False)[:1200])
    print(f"wrote {dest.name}")
    if verdict == "NOT_DETERMINISTIC":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
