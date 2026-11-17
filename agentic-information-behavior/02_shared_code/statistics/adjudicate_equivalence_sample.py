"""EXP-0015: how many conservative-rule "equivalences" are real? (manual adjudication of a sample)

EXP-0014 measures a relabelling rate, not a label-noise rate: its conservative rule asks whether two
tools share a parameter schema, name tokens and description vocabulary. Inspecting the pairs showed
that a shared schema is common among SIBLING tools that do different things (`firestore-delete-document`
vs `firestore-get-document`), so the rule's flips are an upper bound. This script draws a fixed random
sample of the pairs the rule actually used to relabel a failure, prints both tool records verbatim for
human reading, and tabulates the verdicts recorded in ADJUDICATIONS below.

The annotator is the author of this analysis (a human reading the two records), not a model API:
the project forbids inference calls, and no judge prompt is involved.

    python adjudicate_equivalence_sample.py            # draw + print the sample
    python adjudicate_equivalence_sample.py --write     # also emit the JSON/CSV artefacts

Outputs results_raw/EXP0015_equivalence_adjudication_*.json and
results_processed/EXP0015_equivalence_adjudication.csv.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

# the sample contains CJK tool descriptions; the default Windows console codec aborts on them
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PROC = ROOT / "results_processed"
OUT = ROOT / "results_raw"
SEED = 42
N_PER_CONFIG = 20

# Verdicts recorded by reading each instruction together with both tool records (EXP-0015 run of
# 2026-09-18, 19:4x). Index refers to the printed sample order, which is fixed by random_state=SEED.
#   "equivalent"          : either tool satisfies THIS instruction; the gold set is non-exhaustive here
#   "sibling_different"   : same server and same parameter schema, materially different operation/scope
#   "different_domain"    : different target system or object type
#   "unsure"              : instruction was not specific enough to decide
# Not every sampled item is filled: 3 of the 20 Kimi-K2 draws (idx 17-19) were not read in this pass
# and are reported as missing rather than guessed, so coverage is part of the published number.
ADJUDICATIONS: dict[str, dict[int, str]] = {
    "OSS": {0: "different_domain", 1: "different_domain", 2: "sibling_different"},
    "Qwen3": {0: "different_domain", 1: "sibling_different", 2: "sibling_different",
              3: "sibling_different", 4: "sibling_different", 5: "unsure", 6: "sibling_different",
              7: "different_domain", 8: "sibling_different", 9: "sibling_different",
              10: "different_domain", 11: "sibling_different", 12: "sibling_different",
              13: "unsure", 14: "sibling_different", 15: "sibling_different",
              16: "sibling_different", 17: "sibling_different", 18: "sibling_different",
              19: "sibling_different"},
    "Kimi-K2": {0: "sibling_different", 1: "sibling_different", 2: "sibling_different",
                3: "sibling_different", 4: "sibling_different", 5: "sibling_different",
                6: "sibling_different", 7: "sibling_different", 8: "different_domain",
                9: "sibling_different", 10: "sibling_different", 11: "sibling_different",
                12: "sibling_different", 13: "sibling_different", 14: "sibling_different",
                15: "sibling_different", 16: "sibling_different"},
}

LABELS = ["equivalent", "sibling_different", "different_domain", "unsure"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    rows, summary = [], {}
    for cfg in ("OSS", "Qwen3", "Kimi-K2"):
        # "equivalent" is instruction-relative, so the user's own words must be part of what the
        # annotator reads; the pair table alone would only support an invalid tool-vs-tool judgement.
        dv = pd.read_parquet(ROOT / "01_datasets" / "processed" / f"routing_{cfg}.parquet")
        dv = dv[(dv.split == "dev") & (dv.n_candidates > 3)].reset_index(drop=True)
        question_of = dv.question.tolist()
        pr = pd.read_parquet(PROC / f"EXP0014_pairs_{cfg}.parquet")
        m = np.array([(pj >= 1.0 and nj >= 0.5 and dc >= 0.5) for pj, nj, dc in
                      zip(pr.param_jaccard, pr.name_jaccard, pr.desc_cosine)])
        pos = pr[m & (pr.fail == 1)].copy()
        rng = np.random.default_rng(SEED)
        take = pos.sample(min(N_PER_CONFIG, len(pos)), random_state=SEED)
        summary[cfg] = {"n_conservative_flips": int(len(pos)), "n_sampled": int(len(take))}
        print(f"\n{'='*100}\n[{cfg}] conservative relabellings of real positives: "
              f"{len(pos)}  (sampled {len(take)}, random_state={SEED})\n{'='*100}")
        for j, (_, r) in enumerate(take.iterrows()):
            ins = " ".join(str(question_of[int(r.row)]).split())
            print(f"\n({j}) name_j={r.name_jaccard:.2f} param_j={r.param_jaccard:.2f} desc_cos={r.desc_cosine:.2f}")
            print(f"    INSTRUCTION: {ins[:340]}")
            print(f"    TOP-3 TOOL : {r.evidence_query_side}")
            print(f"    GOLD TOOL  : {r.evidence_gold_side}")
            v = ADJUDICATIONS[cfg].get(j)
            rows.append({"config": cfg, "sample_idx": j, "prompt_id": r.prompt_id,
                         "name_jaccard": r.name_jaccard, "param_jaccard": r.param_jaccard,
                         "desc_cosine": round(float(r.desc_cosine), 4),
                         "instruction": " ".join(str(question_of[int(r.row)]).split())[:600],
                         "candidate_tool": r.evidence_query_side, "gold_tool": r.evidence_gold_side,
                         "verdict": v})
        n_pos_pairs = int((pr.fail == 1).sum())
        summary[cfg]["n_positive_pairs"] = n_pos_pairs
        summary[cfg]["n_conservative_pairs"] = int(len(pos))
        summary[cfg]["n_rows_relabelled_matches_EXP0014"] = int(pos.row.nunique())
        print(f"\n  conservative EQUIVALENT PAIRS among positives = {len(pos)}/{n_pos_pairs}"
              f" over {pos.row.nunique()} distinct positive rows "
              f"(row-level relabelling rate is in EXP-0014: pairs are not rows)")

    df = pd.DataFrame(rows)
    adjudicated = df[df.verdict.notna()]
    for cfg in summary:
        sub = adjudicated[adjudicated.config == cfg]
        summary[cfg]["n_adjudicated"] = int(len(sub))
        summary[cfg]["verdict_counts"] = sub.verdict.value_counts().to_dict()
        summary[cfg]["rule_precision_equivalent"] = (
            round(float((sub.verdict == "equivalent").mean()), 4) if len(sub) else None)
    print("\n=== summary ===")
    print(json.dumps(summary, indent=1))
    if args.write:
        df.to_csv(PROC / "EXP0015_equivalence_adjudication.csv", index=False)
        p = OUT / f"EXP0015_equivalence_adjudication_{time.strftime('%Y%m%dT%H%M%S')}.json"
        p.write_text(json.dumps({"exp_id": "EXP-0015", "seed": SEED, "n_per_config": N_PER_CONFIG,
                                 "annotator": "human author reading the instruction and both tool records verbatim",
                                 "llm_api_used": False, "test_split_read": False,
                                 "summary": summary, "rows": rows}, indent=1, default=str), encoding="utf-8")
        print("wrote", p.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
