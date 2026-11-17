"""EXP-0044 (P004 E6): does the one positive finding survive a stricter executed-tool criterion?

P004's single `VALID` verdict (completeness against executed-tool agreement) rests on a criterion this paper built
by rule, and that rule is generous: it counts any `name(` token in assistant text as a call, and it compares
*local* tool names after stripping the server prefix. Mean agreement is 0.315 with 28.9% at unity, so the
distribution is not obviously "did the declared tools get used". A positive result must not depend on the loosest
plausible extraction, so this re-computes the criterion three ways, pre-declared:

  loose  - any identifier followed by a parenthesis anywhere in assistant content, local names (the E3 rule);
  strict - only structured calls: `function_call`/`tool_calls`/a `name` field, local names;
  exact  - structured calls only, compared on the FULL qualified name without prefix stripping.

Reported per variant: how many rows have any extracted call at all, mean agreement, share at unity, and Spearman
rho of each response-side score against it with a prompt_id-clustered CI. `VALID_STABLE` iff the completeness rho
keeps |rho| >= 0.30 with the CI above 0.15 under BOTH strict variants; otherwise the finding is
`RULE_DEPENDENT` and must be reported as such.
"""
from __future__ import annotations

import json, re, sys, time
from math import erfc, sqrt
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p004_common as C

ROOT = Path(__file__).resolve().parents[2]
DATA = C.DATA


def calls_from_messages(blob, strict=False, full=False):
    try:
        ms = json.loads(blob) if isinstance(blob, str) else (blob or [])
    except Exception:                                          # noqa: BLE001
        return None
    names = set()
    for m in ms if isinstance(ms, list) else []:
        if not isinstance(m, dict):
            continue
        for fc in [m.get("function_call"), m.get("tool_call")] + list(m.get("tool_calls") or []):
            if isinstance(fc, dict):
                nm = fc.get("name") or (fc.get("function") or {}).get("name")
                if nm:
                    names.add(str(nm) if full else C.local_name(nm))
        if m.get("name"):
            names.add(str(m["name"]) if full else C.local_name(m["name"]))
        if not strict:
            c = m.get("content")
            if isinstance(c, str):
                for mm in re.finditer(r"\b([a-zA-Z_][\w.]{2,})\s*\(", c):
                    names.add(mm.group(1) if full else C.local_name(mm.group(1)))
    return names


def load_variant(cfg, strict, full):
    files = sorted((DATA / cfg).glob("*.parquet"))
    picks = sorted(random_sample(files))
    rows = []
    for f in picks:
        have = set(pq.ParquetFile(f).schema_arrow.names)
        cols = [c for c in ("uuid", "metadata", "target_tools", "messages", "response_quality_assessment")
                if c in have]
        for r in pq.read_table(f, columns=cols).slice(0, C.ROWS_PER_SHARD).to_pylist():
            try:
                pid = str(json.loads(r["metadata"]).get("prompt_id") or r["uuid"])
            except Exception:                                  # noqa: BLE001
                pid = str(r["uuid"])
            items = [x.strip() for x in re.split(r",(?![^{]*\})", str(r.get("target_tools") or "")) if x.strip()]
            gold = {(x if full else C.local_name(x)) for x in items}
            called = calls_from_messages(r.get("messages"), strict=strict, full=full)
            rd = C.extract_response_scores(r.get("response_quality_assessment")) or {}
            rows.append({"uuid": r["uuid"], "prompt_id": pid, "cfg": cfg, **rd,
                         "agreement": (len(gold & (called or set())) / len(gold)) if gold else np.nan,
                         "n_called": len(called or set()), "n_gold": len(gold)})
    df = pd.DataFrame(rows)
    return df[df.prompt_id.map(C.bucket) < C.DEV_BUCKET]


def random_sample(files):
    import random
    return sorted(random.Random(C.SEED).sample(files, min(C.SHARDS, len(files))))


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    E44V = []
    variants = {"loose_structured_plus_text": (False, False), "structured_only_local": (True, False),
                "structured_only_full_name": (True, True)}
    res = {"exp_id": "EXP-0044", "paper_id": "P004", "e_id": "E6_criterion_sensitivity", "seed": C.SEED,
           "rule": "VALID_STABLE iff rho(completeness, agreement) keeps |rho|>=0.30 with CI above 0.15 under both "
                   "strict variants", "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "variants": {}}
    for name, (strict, full) in variants.items():
        frames = [load_variant(cfg, strict, full) for cfg in C.CONFIGS]
        A = pd.concat(frames, ignore_index=True)
        ent = {"rows": int(len(A)), "share_with_any_call": round(float((A.n_called > 0).mean()), 4),
               "agreement_mean": round(float(A.agreement.mean()), 4),
               "agreement_share_unity": round(float((A.agreement == 1).mean()), 4),
               "per_config": {cfg: round(float(m.agreement.mean()), 4) for cfg, m in zip(C.CONFIGS, frames)},
               "dimensions": {}}
        for dim in [d for d in ("r_completeness", "r_conciseness", "r_desired_tools_used_percentage",
                                "r_order_correctness", "r_overall_score") if d in A.columns]:
            sub = A[[dim, "agreement", "prompt_id"]].dropna()
            if len(sub) < 50 or sub[dim].std() == 0 or sub["agreement"].std() == 0:
                continue
            r = float(spearmanr(sub[dim], sub.agreement).statistic)
            lo, hi, nd = C.clustered_ci(A, [dim, "agreement"],
                                        lambda s: float(spearmanr(s[dim], s.agreement).statistic), draws=1000)
            z = 0.5 * np.log((1 + r) / (1 - r)) * sqrt(max(1, len(sub) - 3))
            p = float(erfc(abs(z) / sqrt(2)))
            ent["dimensions"][dim] = {"n": int(len(sub)), "rho": round(r, 4), "ci95_prompt_clustered": [lo, hi],
                                      "p": p}
        res["variants"][name] = ent
        E44V.append((name, ent))
        print(f"  {name:32s} rows={ent['rows']:6d} any_call={ent['share_with_any_call']:.3f} "
              f"mean_agree={ent['agreement_mean']:.3f} rho(completeness)="
              f"{ent['dimensions'].get('r_completeness', {}).get('rho')}")
    st = [res["variants"][v]["dimensions"].get("r_completeness") for v in variants if "r_completeness" in
          res["variants"][v]["dimensions"]]
    stable = len(st) == 3 and all(abs(x["rho"]) >= 0.30 and min(abs(x["ci95_prompt_clustered"][0]),
                                                                abs(x["ci95_prompt_clustered"][1])) > 0.15
                                  for x in st[1:])
    res["verdict"] = {"n_variants_with_completeness": len(st),
                      "rho_by_variant": [x["rho"] for x in st],
                      "agreement_mean_by_variant": [res["variants"][v]["agreement_mean"] for v in variants],
                      "decision": "VALID_STABLE" if stable else
                                  "RULE_DEPENDENT - the only positive P004 finding depends on the loosest extraction "
                                  "rule and must be reported as provisional"}
    res["wallclock_sec"] = round(time.time() - t0, 1)
    res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")

    def default(o):
        return o.item() if isinstance(o, (np.floating, np.integer)) else str(o)

    (ROOT / "results_raw").mkdir(exist_ok=True)
    out = ROOT / "results_raw" / f"EXP0044_criterion_sensitivity_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False, default=default), encoding="utf-8")
    (ROOT / "results_processed").mkdir(exist_ok=True)
    pd.DataFrame([{"extraction_variant": k, "rows": v["rows"], "share_with_any_call": v["share_with_any_call"],
                   "agreement_mean": v["agreement_mean"], "agreement_share_unity": v["agreement_share_unity"],
                   "agreement_mean_by_config": str(v["per_config"]),
                   **{f"rho_{d}": e.get("rho") for d, e in v["dimensions"].items()},
                   **{f"ci_{d}": str(e.get("ci95_prompt_clustered")) for d, e in v["dimensions"].items()}}
                  for k, v in E44V]).to_csv(ROOT / "results_processed" / "EXP0044_criterion_sensitivity.csv",
                                            index=False)
    print(json.dumps(res["verdict"], ensure_ascii=False)[:400])
    print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
