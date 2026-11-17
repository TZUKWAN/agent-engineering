"""EXP-0108 (spec E08 for P004): does the paper's instrument travel to a shipped score it was never built for?

P004 audits the automatic quality columns that arrive *inside* a released corpus - `question_quality_assessment` and
`response_quality_assessment` on Toucan-1.5M - and its E_COVERAGE row said E08 (跨数据集外部验证) was open: every
conclusion had been drawn on one release by one publisher. This run applies the same battery, with the same frozen
decision rules, to a shipped automatic label from a different corpus: SWE-ZERO-12M's `exit_status`, written by AlienKevin
over SWE-bench-style rollouts.

Decision rules, fixed in this docstring before the sample was read (they are P004's own criteria, not new ones):

  1. **presence** - the column's value census, per row, with `null`/empty counted separately. A shipped score that is
     empty for most rows cannot be the filter its publisher's documentation implies;
  2. **scale or label** - `NOT A SCALE` when the column takes <= 2 distinct non-empty values over the sampled rows
     (P004's Toucan arms had 5 and 11); otherwise `ORDINAL/CONTINUOUS`;
  3. **does it track anything** - association with an independent outcome signal derived from the trajectory text
     itself by a rule fixed here: a rollout counts as *self-declared complete* when its last assistant message contains
     one of `submit`, `all tests pass`, `resolved`, `fixed the issue`, `done` (case-insensitive), and *failed-looking*
     when it contains `traceback`, `error`, `failed`, `exception`. Report the 2x2 with a two-sided Fisher test and an
     instance-clustered bootstrap odds ratio (clustered by `instance_id`, because `exit_status` is a property of a
     rollout and rollouts of one instance are not independent draws - the same reason P001/P004 cluster);
  4. **gating consequence** - what filtering to the non-default value does to the population: share of rows kept,
     repositories remaining, and the reweighting of the largest repository;
  5. **verdict** - `TRAVELS` only if the shipped label is a scale (>= 3 values) AND its association CI excludes 1;
     otherwise `DOES NOT TRAVEL`, and the reason is reported in the same words the Toucan audit used.

A negative here is the point: P004's claim is that a shipped score's measurement properties have to be checked, not
assumed, so an external arm that finds a near-constant label is evidence for the paper, not against it.

    python 02_shared_code/statistics/p004_external_shipped_label_e08.py [--shards 24] [--rows 250]
"""
from __future__ import annotations
import argparse, collections, glob, json, pathlib, random, re, sys, time
from collections import Counter

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.stats import fisher_exact

ROOT = next(a for a in [pathlib.Path(__file__).resolve().parent,
                        *pathlib.Path(__file__).resolve().parents] if (a / "00_program_registry").is_dir())
DATA = ROOT.parent / "MATLABINTOKEN" / "datasets" / "AlienKevin/SWE-ZERO-12M-trajectories"
RAW, PROC = ROOT / "results_raw", ROOT / "results_processed"
SEED = 42
COMPLETE_RE = re.compile(r"\b(submit|all tests pass|resolved|fixed the issue|done)\b", re.I)
FAILED_RE = re.compile(r"\b(traceback|error|failed|exception)\b", re.I)
DRAWS = 2000


def last_assistant(msgs):
    for m in reversed(msgs or []):
        if (m.get("role") or m.get("from")) == "assistant":
            return str(m.get("content") or m.get("value") or "")
    return ""


def clustered_or(rows, rng):
    """Odds ratio for the 2x2 between `exit_status` and the text-derived signal, with an instance-clustered bootstrap CI."""
    def or_of(sub):
        a = sum(1 for r in sub if r["kept"] and r["complete"])
        b = sum(1 for r in sub if r["kept"] and not r["complete"])
        c = sum(1 for r in sub if not r["kept"] and r["complete"])
        d = sum(1 for r in sub if not r["kept"] and not r["complete"])
        if min(a, b, c, d) == 0:
            a, b, c, d = a + 0.5, b + 0.5, c + 0.5, d + 0.5      # Haldane correction, declared here
        return (a * d) / (b * c)
    groups = collections.defaultdict(list)
    for r in rows:
        groups[r["instance_id"]].append(r)
    keys = list(groups)
    obs = or_of(rows)
    draws = []
    for _ in range(DRAWS):
        pick = [keys[i] for i in rng.integers(0, len(keys), len(keys))]
        samp = [r for k in pick for r in groups[k]]
        if samp:
            draws.append(or_of(samp))
    lo, hi = (np.percentile(draws, [2.5, 97.5]).tolist() if draws else [None, None])
    return obs, [round(float(lo), 3), round(float(hi), 3)] if draws else None, len(keys)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shards", type=int, default=24)
    ap.add_argument("--rows", type=int, default=250)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    files = [f for f in sorted(glob.glob(str(DATA / "**/*.parquet"), recursive=True)) if ".cache" not in f]
    if not files:
        raise SystemExit(f"ABORT: {DATA} is not on disk - the external arm would measure nothing")
    rng = np.random.default_rng(SEED)
    picks = sorted(rng.permutation(len(files))[:min(a.shards, len(files))])
    rows, empties, read = [], 0, 0
    for i in picks:
        t = pq.read_table(files[i], columns=["instance_id", "repo", "messages", "exit_status"])
        for r in t.slice(0, a.rows).to_pylist():
            read += 1
            raw = r.get("exit_status")
            txt = last_assistant(r["messages"])
            if raw is None or not str(raw).strip():
                empties += 1
                continue
            rows.append({"instance_id": str(r["instance_id"]), "repo": str(r["repo"]),
                         "exit_status": str(raw).strip(), "kept": str(raw).strip().lower() != "incomplete",
                         "complete": bool(COMPLETE_RE.search(txt[-2000:])), "failed_looking": bool(FAILED_RE.search(txt))})
    if not rows:
        raise SystemExit("ABORT: no row carried a non-empty exit_status - the external arm is not measurable here")
    vals = Counter(r["exit_status"] for r in rows)
    kept_rows = [r for r in rows if r["kept"]]
    tab = pd.crosstab(pd.Series([r["kept"] for r in rows], name="exit_status_is_non_default"),
                      pd.Series([r["complete"] for r in rows], name="text_says_complete"))
    odds, p = fisher_exact(tab.values, alternative="two-sided")
    or_obs, ci, n_groups = clustered_or(rows, np.random.default_rng(SEED + 1))
    repos_all = Counter(r["repo"] for r in rows)
    repos_kept = Counter(r["repo"] for r in kept_rows)
    top_all, top_kept = (repos_all.most_common(1)[0], repos_kept.most_common(1)[0] if repos_kept else ("-", 0))
    scale = len(vals) >= 3
    travels = scale and ci and (ci[0] > 1.0 or ci[1] < 1.0)
    out = {"exp_id": "EXP-0108", "at": time.strftime("%Y-%m-%dT%H:%M:%S"), "seed": SEED,
           "corpus": "AlienKevin/SWE-ZERO-12M-trajectories (different publisher and pipeline from Toucan-1.5M)",
           "sample": {"shards": len(picks), "rows_read": read, "rows_with_a_value": len(rows),
                      "rows_empty_or_null": empties, "distinct_instances": len({r['instance_id'] for r in rows})},
           "value_census": dict(vals.most_common()),
           "scale_or_label": ("ORDINAL/CONTINUOUS" if scale else "NOT A SCALE") + f" ({len(vals)} distinct values)",
           "association_with_text_signal": {"table_2x2": tab.to_dict(), "fisher_odds": round(float(odds), 3),
                                            "fisher_p_two_sided": round(float(p), 6),
                                            "instance_clustered_or": round(float(or_obs), 3),
                                            "bootstrap_ci95": ci, "clusters": n_groups, "draws": DRAWS,
                                            "rule": "self-declared completion in the last assistant message vs the "
                                                    "shipped label; two-sided because a zero cell is a finding"},
           "gating_consequence": {"rows_kept_by_filtering": len(kept_rows),
                                  "share_kept": round(len(kept_rows) / len(rows), 5),
                                  "repositories_before": len(repos_all), "repositories_after": len(repos_kept),
                                  "largest_repository_before": top_all,
                                  "largest_repository_after": top_kept if repos_kept else None},
           "verdict": "TRAVELS" if travels else "DOES NOT TRAVEL",
           "verdict_reason": (f"the shipped label takes {len(vals)} distinct value(s) and the instance-clustered "
                              f"odds ratio {or_obs} has CI {ci}; "
                              + ("the label behaves as a scale and the association is not explained by clustering"
                                 if travels else
                                 "P004's instrument presupposes a score that varies; this one is "
                                 + ("a two-value flag, so a rank correlation is undefined and the audit reports the "
                                    "2x2 instead" if not scale else "a scale whose association CI covers 1"))),
           "p004_headline_comparison": {
               "toucan_question_quality_assessment": "5 distinct values, monotone against the derived proxies "
                                                     "(P004 EXP-0042/0043)",
               "toucan_response_quality_assessment": "11 distinct values, confounded by length and catalogue size",
               "swzero_exit_status": f"{len(vals)} distinct values, {round(len(kept_rows) / len(rows), 4)} of rows "
                                     f"in the non-default value"},
           "wallclock_sec": round(time.time() - t0, 1)}
    (RAW / f"EXP0108_p004_external_shipped_label_{time.strftime('%Y%m%dT%H%M%S')}.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    pd.DataFrame([{"measure": k, "value": json.dumps(v, ensure_ascii=False, default=str)}
                  for k, v in out.items() if k not in ("exp_id", "at", "seed")]).to_csv(
        PROC / "EXP0108_external_shipped_label.csv", index=False)
    print(f"  read {read} rows; {len(rows)} carry a value, {empties} empty/null")
    print(f"  value census: {dict(vals.most_common(4))}")
    print(f"  2x2 {tab.to_dict()}  Fisher p={p:.3g} odds={odds:.3g}")
    print(f"  instance-clustered OR={or_obs} CI95={ci} over {n_groups} clusters")
    print(f"  filtering keeps {out['gating_consequence']['share_kept']} of rows "
          f"({out['gating_consequence']['repositories_after']}/{out['gating_consequence']['repositories_before']} repos)")
    print(f"  verdict: {out['verdict']} - {out['verdict_reason']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
