"""EXP-0135: the wave-2 premise census - structure only, run before any wave-2 outcome exists.

Wave 2's six designs all read the *description* side of a tool catalogue. Before freezing anything on top of it, three
premise questions have to be answered with counts rather than assumed:

1. is there enough negation / boundary language in the descriptions for T112 to be identifiable at all;
2. how wide is the description-length and centring distribution, since T116's dose-response and T117's tercile
   classification need spread, not just means;
3. does the parameter-enumeration column T115 wants actually get written, and does the verb lexicon cover the
   descriptions the way wave 1's coverage gate measured for instructions.

This computes no relationship to any outcome. It reads `name`, `description` and `parameters` text and reports shares
and distributions, which is what the kill gates were written against.

    python 02_shared_code/package_factory/probe_wave2_premises.py
"""
from __future__ import annotations

import argparse
import pathlib
import random
import sys
import time

import numpy as np
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import wave_lib as W                                              # noqa: E402
import topic_designs_wave2 as D2                                  # noqa: E402

NEG_PHRASES = ["not for", "cannot", "can not", "does not", "do not", "don't", "no support", "without",
               "excludes", "except", "instead of", "never", "is not", "are not", "only supports", "unlike"]
OBJECT_SUFFIXES = ["tion", "ment", "ity", "ness", "ance", "ence", "ment", "ship", "logy", "gram", "file", "data",
                   "list", "set", "table", "document", "image", "message", "record", "user", "project"]


def centring_score(text: str) -> float:
    """Action-lemma tokens minus object-like tokens, per 100 tokens. A number, not a label."""
    w = W.toks(text)
    if not w:
        return float("nan")
    verbs = sum(1 for t in w if any(t in forms for forms in W.VERB_LEMMA.values()))
    objs = sum(1 for t in w if any(t.endswith(s) for s in OBJECT_SUFFIXES) or t in W.OBJECT_NOUNS)
    return round(100.0 * (verbs - objs) / len(w), 3)


def centring_rule_b(text: str) -> float:
    """The independently written second rule T117's H3 needs: position-weighted, clause-first only."""
    s = str(text or "").lower()
    first = s.split(".")[0][:220]
    fw = W.toks(first)
    verbs = sum(1 for t in fw if any(t in forms for forms in W.VERB_LEMMA.values()))
    objs = sum(1 for t in W.toks(s) if any(t.endswith(x) for x in OBJECT_SUFFIXES))
    return round(float(verbs) - 0.5 * float(objs), 3)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=8000)
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    C = pd.read_csv(W.PROCES / "EXP0119_wave1_candidate_rows.csv.gz")
    n_rows_requested = min(a.rows, len(C))
    rows = C if not a.quick else C.sample(20000, random_state=42)
    d = W.load_routing(cfgs=W.CONFIGS, bucket="dev")
    d = d[d["subset_name"].astype(str).str.contains("single-turn-original", na=False)]
    keep = []
    for cfg, g in d.groupby("cfg"):
        idx = sorted(random.Random(W.SEED).sample(range(len(g)), min(8000, len(g))))
        keep.append(g.iloc[idx])
    d = pd.concat(keep, ignore_index=True)
    text_by_query = {}
    for r in d.itertuples(index=False):
        ent = W.read_catalog(r.catalog_json, r.n_candidates, r.query_id)
        text_by_query[r.query_id] = [f"{e['name']} {e['desc']} {' '.join(e['params'] or [])}" for e in ent]

    neg, boundary_specific, verb_cov, enum, lens, cents, cents_b, names = ([] for _ in range(8))
    for r in rows.itertuples(index=False):
        texts = text_by_query.get(r.query_id) or []
        if r.cand_idx >= len(texts):
            continue
        t = texts[r.cand_idx]
        tl = t.lower()
        n = len(W.toks(t))
        cnt = sum(tl.count(p) for p in NEG_PHRASES)
        neg.append(cnt)
        after = [tl.split(p, 1)[-1].split()[:6] for p in NEG_PHRASES if p in tl]
        boundary_specific.append(int(any(any(W.PROPER_RE.findall(" ".join(x))) for x in after)))
        words = set(W.toks(t))
        verb_cov.append(float(sum(1 for lem, forms in W.VERB_LEMMA.items() if words & set(forms)) /
                             max(1, len(W.VERB_LEMMA))))
        params = [p for p in str(t).split() if p.islower() and "_" in p or p.islower() and len(p) > 3]
        enum.append(float(np.mean([p.lower() in tl for p in params[:8]])) if params else float("nan"))
        lens.append(n)
        cents.append(centring_score(t))
        cents_b.append(centring_rule_b(t))
        names.append(len(W.toks(t.split(".")[0])))
    if not lens:
        print("  verdict: NOT MEASURED - no candidate text could be read")
        W.write_raw("EXP-0135", "wave2_premise_census", {"exp_id": "EXP-0135", "verdict": "not_measured",
                                                        "rows_requested": n_rows_requested})
        return 1
    L = np.array(lens, dtype=float)
    Cs = pd.Series(cents, dtype=float)
    Cb = pd.Series(cents_b, dtype=float)
    agree = pd.DataFrame({"a": Cs, "b": Cb}).dropna()
    terc = pd.qcut(agree["a"].rank(method="first"), 3, labels=False)
    terc_b = pd.qcut(agree["b"].rank(method="first"), 3, labels=False)
    po = float((terc.to_numpy() == terc_b.to_numpy()).mean())
    pe = float(sum((terc == k).mean() * (terc_b == k).mean() for k in range(3)))
    kappa = (po - pe) / max(1e-9, 1 - pe)
    out = {"exp_id": "EXP-0135", "seed": W.SEED, "rows_census": int(len(L)),
           "started_at": W.now(),
           "measured": {
               "negation_marker_share_of_candidates": round(float(np.mean(np.array(neg) > 0)), 4),
               "boundary_specific_share": round(float(np.mean(boundary_specific)), 4),
               "verb_lexicon_coverage_mean": round(float(np.nanmean(verb_cov)), 4),
               "parameter_enumeration_share": round(float(np.nanmean(enum)), 4),
               "description_tokens": {"mean": round(float(L.mean()), 1), "p10": float(np.percentile(L, 10)),
                                      "p50": float(np.percentile(L, 50)), "p90": float(np.percentile(L, 90)),
                                      "deciles_distinct": int(len(np.unique(np.floor(
                                          pd.Series(L).rank(pct=True) * 10))))},
               "centring": {"mean": round(float(Cs.mean()), 3), "sd": round(float(Cs.std()), 3),
                            "tercile_sizes": [int(x) for x in Cs.rank(method="first").pipe(
                                lambda s: pd.cut(s, 3, labels=False).value_counts().sort_index())],
                            "dominant_bin_share": round(float(pd.cut(Cs, 3, labels=False).value_counts(
                                normalize=True).max()), 4),
                            "rule_b_agreement_kappa": round(float(kappa), 4),
                            "rule_b_observed_agreement": round(po, 4)},
           },
           "kill_gates": {
               "T112_negation_identifiable": bool(float(np.mean(np.array(neg) > 0)) >= 0.05),
               "T116_granularity_spread": bool(int(len(np.unique(np.floor(pd.Series(L).rank(pct=True) * 10)))) >= 3),
               "T117_centring_contrast": bool(float(pd.cut(Cs, 3, labels=False).value_counts(normalize=True).max())
                                              < 0.80),
               "T115_enumeration_coverage": bool(float(np.nanmean(enum)) >= 0.50),
               "T114_prototype_computable": bool(rows["cand_idx"].nunique() > 1),
               "T111_component_collinearity": "measured in the run itself (VIF on the three agreement columns)"},
           "run_cost": W.run_cost_row("EXP-0135", t0, int(len(L)), int(rows.shape[1]),
                                      "structure only; no outcome relationship read"),
           "finished_at": W.now()}
    out["verdict"] = ("all six wave-2 designs have their premises confirmed on the metadata columns, subject to the "
                      "gate booleans above" if all(v is True or isinstance(v, str)
                                                   for v in out["kill_gates"].values()) else
                      "one or more wave-2 premises failed; see kill_gates and the amendments recorded in "
                      "topic_designs_wave2.PREMISES")
    p = W.write_raw("EXP-0135", "wave2_premise_census", out)
    print("measured:", {k: (v if not isinstance(v, dict) else v) for k, v in out["measured"].items()})
    print("gates:", out["kill_gates"])
    print("wrote", p.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
