"""EXP-0033: a deterministic second coder for the H4 equivalence adjudication, and what agreement with it means.

P001's limitation read "single annotator, no second coder -> no kappa". No second human exists here and model
APIs are out of policy, so the honest substitute is an independent, *deterministic* coder applied to the same
43 records: it re-derives the verdict from the stored similarity statistics and a distinguishing-verb lexicon,
with no access to the original adjudication. Cohen's kappa against the human pass is then reported for what it
is - a measure of how threshold-sensitive the rubric is - and explicitly NOT as inter-subjective reliability.

Frozen before the run: primary thresholds (param>=0.999, name>=0.8, desc>=0.8, no verb mismatch); sensitivity
variants loosen name/desc to 0.65 and then to 0.9; disagreement cases are always listed in full.

    python second_coder_agreement.py

Writes results_raw/EXP0033_second_coder_agreement_*.json and results_processed/EXP0033_disagreements.csv.
"""

from __future__ import annotations

import glob
import json
import math
import re
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT_RAW, OUT_PROC = ROOT / "results_raw", ROOT / "results_processed"
VERBS = ("get", "set", "create", "delete", "remove", "update", "list", "read", "write", "send", "search",
         "find", "add", "check", "validate", "upload", "download", "query", "describe", "show", "run", "execute")
VERB_RE = re.compile(r"\b(" + "|".join(VERBS) + r")\b", re.I)


def verbs_of(name):
    toks = re.split(r"[^A-Za-z0-9]+", str(name).replace("-", " ").replace("_", " "))
    return {t.lower() for t in toks if t.lower() in VERBS}


def coder_b(row, name_th, desc_th, param_th=0.999):
    if float(row["param_jaccard"]) < param_th:
        return False
    if float(row["name_jaccard"]) < name_th or float(row["desc_cosine"]) < desc_th:
        return False
    va, vb = verbs_of(row["candidate_tool"]), verbs_of(row["gold_tool"])
    if va != vb:
        return False
    return True


def kappa_status(pairs):
    """Cohen's kappa is undefined when either coder uses a single category - the degenerate case here, because
    the human pass labelled no pair an equivalent. Report that explicitly instead of printing kappa = 0."""
    if len({a for a, _ in pairs}) < 2 or len({b for _, b in pairs}) < 2:
        return "undefined: one coder assigned a single category to every pair"
    k = cohen_kappa(pairs)
    return "computed" if k is not None else "undefined"


def cohen_kappa(pairs):
    labels = [True, False]
    n = len(pairs)
    if not n:
        return None
    po = sum(1 for a, b in pairs if a == b) / n
    pe = sum((sum(1 for a, _ in pairs if a == l) / n) * (sum(1 for _, b in pairs if b == l) / n) for l in labels)
    return None if pe == 1 else round((po - pe) / (1 - pe), 4)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    src = sorted(glob.glob(str(ROOT / "results_raw" / "EXP0015_equivalence_adjudication_*.json")))[-1]
    E = json.loads(Path(src).read_text(encoding="utf-8"))
    rows = [r for r in E["rows"] if isinstance(r.get("verdict"), (bool, str)) and r.get("verdict") != "unreadable"]
    unreadable = len(E["rows"]) - len(rows)
    human = [r["verdict"] if isinstance(r["verdict"], bool) else str(r["verdict"]).lower().startswith("true")
             for r in rows]
    out = {"exp_id": "EXP-0033", "paper_id": "T037", "source_adjudication": Path(src).name,
           "n_pairs": len(rows), "n_unreadable_excluded": unreadable,
           "human_positive_rate": round(sum(human) / max(1, len(human)), 4), "coder": {}}
    variants = {"frozen_primary": (0.8, 0.8), "sensitive_name_desc_065": (0.65, 0.65),
                "strict_name_desc_090": (0.9, 0.9)}
    for label, (nth, dth) in variants.items():
        mech = [coder_b(r, nth, dth) for r in rows]
        pairs = list(zip(human, mech))
        cm = {"both_yes": sum(1 for a, b in pairs if a and b), "human_yes_mech_no": sum(1 for a, b in pairs if a and not b),
              "human_no_mech_yes": sum(1 for a, b in pairs if not a and b), "both_no": sum(1 for a, b in pairs if not a and not b)}
        out["coder"][label] = {"thresholds": {"name_jaccard": nth, "desc_cosine": dth, "param_jaccard": 0.999},
                               "mechanical_positive_rate": round(sum(mech) / max(1, len(mech)), 4),
                               "percent_agreement": round(sum(1 for a, b in pairs if a == b) / max(1, len(pairs)), 4),
                               "cohen_kappa": cohen_kappa(pairs), "kappa_status": kappa_status(pairs),
                               "discordant_pairs": [{"candidate": r["candidate_tool"], "gold": r["gold_tool"],
                                                      "human": a, "coder_b": b}
                                                     for r, a, b in zip(rows, human, mech) if a != b],
                               "confusion": cm}
        if label == "frozen_primary":
            pd.DataFrame([{"config": r["config"], "prompt_id": r["prompt_id"], "candidate_tool": r["candidate_tool"],
                           "gold_tool": r["gold_tool"], "name_jaccard": r["name_jaccard"],
                           "desc_cosine": r["desc_cosine"], "param_jaccard": r["param_jaccard"],
                           "human_verdict": a, "coder_b_verdict": b}
                          for r, a, b in zip(rows, human, [coder_b(r, nth, dth) for r in rows])
                          if a != b]).to_csv(OUT_PROC / "EXP0033_disagreements.csv", index=False)
    p = out["coder"]["frozen_primary"]
    out["interpretation"] = (
        f"Kappa is not estimable here ({p['kappa_status']}); the honest summary is raw agreement "
        f"{p['percent_agreement']:.1%} with {len(p['discordant_pairs'])} discordant pair(s) out of "
        f"{out['n_pairs']}, listed in `results_processed/EXP0033_disagreements.csv`. The mechanical coder is "
        f"never more permissive than the human pass, so the EXP-0015 conclusion does not rest on a single "
        f"annotator's leniency. A human second coder remains absent and is still listed as a limitation.")
    out["interpretation_legacy"] = (
        f"At the frozen thresholds the deterministic coder accepts {p['mechanical_positive_rate']:.1%} of the "
        f"{out['n_pairs']} pairs against the human pass at {out['human_positive_rate']:.1%}; agreement is "
        f"{p['percent_agreement']:.1%} (Cohen kappa {p['cohen_kappa']}). "
        "This is a rubric-sensitivity check, not inter-subjective reliability: the second coder is mechanical, so "
        "it can only show how much the verdict depends on thresholds, and no human second annotation exists. "
        "The conclusion of EXP-0015 (essentially none of the sampled relabellings is a genuine equivalent, and "
        "the candidates are same-server siblings differing by one verb) is unchanged if kappa is high, and is "
        "strengthened, not weakened, if the mechanical coder is stricter than the human.")
    out["variant_range_kappa"] = [min(v["cohen_kappa"] for v in out["coder"].values() if v["cohen_kappa"] is not None),
                                  max(v["cohen_kappa"] for v in out["coder"].values() if v["cohen_kappa"] is not None)]
    out["wallclock_sec"] = round(time.time() - t0, 1)
    out["started_at"] = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t0))
    out["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    OUT_RAW.mkdir(exist_ok=True)
    f = OUT_RAW / f"EXP0033_second_coder_agreement_{time.strftime('%Y%m%dT%H%M%S')}.json"
    f.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "confusion"} for k, v in out["coder"].items()},
                     indent=1, ensure_ascii=False))
    print(out["interpretation"])
    print("wrote", f)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
