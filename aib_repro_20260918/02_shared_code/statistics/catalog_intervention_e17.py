"""EXP-0016: controlled catalog interventions on the development split (E17 + E12).

Everything before this experiment is observational: the paper can say the pre-retrieval predictor
tracks lexical unreachability, but not that unreachability is *caused* by catalog competition, because
catalogs were never manipulated. The persisted question + full catalog (EXP-0013) make manipulation
possible without re-reading the source corpus, so this script rewrites each catalog under seven
deterministic conditions and re-runs the frozen ranker and the frozen predictor on the result.

  control            the published catalog (sanity anchor; must reproduce the published labels)
  distract_2/4/8     append k sibling decoys built from the GOLD tool's own vocabulary - more
                     competition at constant answer
  enrich_gold        append the instruction's top-IDF missing terms to the GOLD description, i.e. the
                     curator action the paper's implications section recommends
  enrich_sham        identical enrichment appended to a RANDOM NON-GOLD tool - the specificity control:
                     if this helps too, the effect is "the catalog changed", not "the gold got clearer"
  namespace_prefix   rename every tool as `srv-<id>-<name>` - tests whether the signal is an artifact of
                     name formatting rather than of lexical reachability
  order_shuffle      permute catalog order (a near-null control; BM25 is order-invariant modulo ties)

Because the decoys and the enrichment are generated from data already in the row, labels move by
design: each condition's fail@3 is a *different* quantity, so conditions are compared within-row and
against control, never pooled. The mechanism test is the per-row covariance between the intervention's
effect and the frozen predictor's own risk score, which never sees gold.

Development only. The test split was consumed once by EXP-0012 and is never opened here.

    python catalog_intervention_e17.py

Outputs results_raw/EXP0016_catalog_intervention_*.json and results_processed/EXP0016_*.csv.
"""

from __future__ import annotations

import json
import math
import random
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "trajectory_parser"))
from analyze_routing_failure import CONFIGS, PROC, SEEDS, oof_auc, scaled_pipeline  # noqa: E402
from build_toucan_routing_dataset import (BM25, collection_qpp_features, toks)  # noqa: E402
from run_p001_experiments import FROZEN_C, FROZEN_FEATURES, matrices  # noqa: E402

SEED = 42
K = 3
DV = "fail_at_3"
N_BOOT = 1000
OUT_RAW = HERE.parents[1] / "results_raw"
OUT_PROC = HERE.parents[1] / "results_processed"
QPP_PREFIX = "qpp_"
CONDITIONS = ["control", "distract_2", "distract_4", "distract_8",
              "enrich_gold", "enrich_sham", "namespace_prefix", "order_shuffle"]
STOP = set("a an the and or of to in on for with without you your our i my is are be can could will "
           "would should please them they it this that these those from at as by if then there here "
           "what which how when where who all any some one two three first also just need want me "
           "help make using use called call get provide".split())


def gold_rank(order: list[int], gold: set[int], n: int) -> int:
    return min((order.index(g) + 1 for g in gold), default=n)


def ranked_order(sc: list[float]) -> list[int]:
    return sorted(range(len(sc)), key=lambda i: (-sc[i], i))


def docs_of(cat: list[dict]) -> list[list[str]]:
    return [toks(d["n"].replace("-", " ").replace("_", " ")) + toks(d["d"]) + toks(" ".join(d["p"]))
            for d in cat]


def top_idf_missing(qtok: list[str], cat: list[dict], gold: set[int], m: int) -> list[str]:
    """Instruction terms absent from every catalog doc, ranked by rarity across the catalog."""
    df: dict[str, int] = {}
    for d in docs_of(cat):
        for t in set(d):
            df[t] = df.get(t, 0) + 1
    n = max(1, len(cat))
    missing = [t for t in dict.fromkeys(qtok) if df.get(t, 0) == 0 and t not in STOP]
    return sorted(missing, key=lambda t: -(math.log((1 + n) / 1.0) + 1.0))[:m]


def make_condition(name: str, cat: list[dict], gold: set[int], qtok: list[str], rnd: random.Random):
    """Return a NEW catalog (list of name/desc/params dicts). Gold indices refer to the ORIGINAL
    entries, so callers must remap by identity for conditions that only append."""
    cat = [dict(d) for d in cat]
    if name == "control":
        return cat
    if name.startswith("distract_"):
        k = int(name.split("_")[1])
        gi = sorted(gold)[0] if gold else 0
        base = cat[gi]
        pool = list(dict.fromkeys(toks(base["n"].replace("-", " ").replace("_", " ")) + toks(base["d"])))
        pool = [t for t in pool if t not in STOP] or ["tool"]
        for j in range(k):
            # a decoy is the gold's vocabulary minus one token, so it is maximally confusable but
            # never identical; identical decoys would test tie-breaking, not competition
            keep = [t for t in pool if rnd.random() > 0.15] or pool[:1]
            cat.append({"n": f"{base['n']}-variant-{j}", "d": " ".join(keep), "p": list(base["p"])})
        return cat
    if name in ("enrich_gold", "enrich_sham"):
        add = top_idf_missing(qtok, cat, gold, 6)
        if not add:
            return cat
        if name == "enrich_gold":
            tgt = sorted(gold)[0] if gold else 0
        else:
            non = [i for i in range(len(cat)) if i not in gold]
            if not non:
                return cat
            tgt = non[rnd.randrange(len(non))]
        cat[tgt] = dict(cat[tgt], d=str(cat[tgt]["d"]) + " " + " ".join(add))
        return cat
    if name == "namespace_prefix":
        return [dict(d, n=f"srv-{rnd.randrange(10000):04d}-{d['n']}") for d in cat]
    if name == "order_shuffle":
        perm = list(range(len(cat)))
        rnd.shuffle(perm)
        return [cat[i] for i in perm]
    raise ValueError(name)


def remap_gold(cat_before: list[dict], cat_after: list[dict], gold: set[int]) -> set[int]:
    """Append-only conditions keep original indices; permutation/rewrite conditions are matched by identity."""
    if all(cat_after[i] == cat_before[i] for i in range(len(cat_before))):
        return set(gold)
    key = {(d["n"], d["d"]): i for i, d in enumerate(cat_after)}
    out = set()
    for g in gold:
        b = cat_before[g]
        j = key.get((b["n"], b["d"]))
        if j is None:  # gold entry was renamed (namespace_prefix) -> track by name suffix
            j = next((i for i, d in enumerate(cat_after) if d["n"].endswith(b["n"])), None)
        if j is not None:
            out.add(j)
    return out or set(gold)


def paired_boot(y_a, y_b, prob_a, prob_b, clusters):
    """Δ prevalence and Δ AUC with jointly resampled prompt_id clusters; also the risk-tracking test."""
    rng = np.random.default_rng(SEED)
    groups = np.unique(clusters)
    idx_of = {g: np.where(clusters == g)[0] for g in groups}
    d_prev, d_auc, d_risk, corr = [], [], [], []
    for _ in range(N_BOOT):
        take = np.concatenate([idx_of[g] for g in rng.choice(groups, len(groups), True)])
        if y_a[take].sum() == 0 or y_b[take].sum() == 0:
            continue
        d_prev.append(float(y_b[take].mean() - y_a[take].mean()))
        if len(set(y_a[take])) > 1 and len(set(y_b[take])) > 1:
            d_auc.append(roc_auc_score(y_b[take], prob_b[take]) - roc_auc_score(y_a[take], prob_a[take]))
        d_risk.append(float(prob_b[take].mean() - prob_a[take].mean()))
    ci = lambda v: [round(float(np.percentile(v, q)), 4) for q in (2.5, 97.5)] if len(v) else None
    # the control condition has zero variance in every delta, and corrcoef of a constant returns NaN,
    # which is invalid JSON; a non-informative correlation is reported as None instead
    finite = (np.isfinite(d_prev).all() and np.isfinite(d_risk).all()
              and float(np.std(d_prev)) > 0 and float(np.std(d_risk)) > 0) if len(d_prev) > 2 else False
    return (ci(d_prev), ci(d_auc) if d_auc else None, ci(d_risk) if d_risk else None,
            round(float(np.corrcoef(d_prev, d_risk)[0, 1]), 4) if finite else None)


def main() -> int:
    t0 = time.time()
    per_cfg, long_rows = {}, []
    for cfg in CONFIGS:
        df = pd.read_parquet(PROC / f"routing_{cfg}.parquet")
        dev = df[(df.split == "dev") & (df.n_candidates > K)].reset_index(drop=True)
        base = matrices(dev, FROZEN_FEATURES)["all"]
        y0 = dev[DV].values.astype(int)
        prob0 = oof_auc(base, y0, scaled_pipeline(FROZEN_C), SEEDS[0])[1]
        res = {}
        for cond in CONDITIONS:
            rnd = random.Random(f"{SEED}-{cfg}-{cond}")
            rows, feats = [], []
            for i, r in dev.iterrows():
                cat0 = json.loads(r.catalog_json)
                gold = set(json.loads(r.gold_idx))
                cat = make_condition(cond, cat0, gold, toks(r.question), rnd)
                gold = remap_gold(cat0, cat, gold)
                docs = docs_of(cat)
                qtok = toks(r.question)
                sc = BM25().scores(qtok, docs)
                order = ranked_order(sc)
                rb = gold_rank(order, gold, len(sc))
                rows.append({"n_candidates": len(cat), "best_rank": rb,
                             "fail_at_3": int(rb > 3), "norm_rank": (rb - 1) / max(1, len(cat) - 1),
                             "chance_hit_3": (1.0 - math.comb(len(cat) - len(gold), 3) / math.comb(len(cat), 3))
                             if len(cat) >= 3 and len(cat) - len(gold) >= 0 else 1.0})
                f = dict(collection_qpp_features(qtok, docs))
                feats.append(f)
            cond_df = dev.copy()
            for c in ("n_candidates", "best_rank", "fail_at_3", "norm_rank", "chance_hit_3"):
                cond_df[c] = [x[c] for x in rows]
            # union of keys, not feats[0]: collection_qpp_features returns a SHORTER dict on its
            # empty-query/empty-catalog early-return branch, so the first row is not a schema.
            for k in sorted({kk for f in feats for kk in f}):
                cond_df[k] = [x.get(k, np.nan) for x in feats]
            X = matrices(cond_df, FROZEN_FEATURES)["all"]
            y = cond_df[DV].values.astype(int)
            oof = oof_auc(X, y, scaled_pipeline(FROZEN_C), SEEDS[0])[1]
            n_pos = int(y.sum())
            aucs = [oof_auc(X, y, scaled_pipeline(FROZEN_C), s)[0] for s in SEEDS]
            # transfer: the model fitted on the UNPERTURBED catalogue is applied to the perturbed one
            trans_auc = roc_auc_score(y, prob0)
            dp, da, dr, cor = paired_boot(y0, y, prob0, oof, dev.prompt_id.values)
            res[cond] = {
                "n": int(len(dev)), "positives": n_pos,
                # A refit AUROC on a catalogue where enrichment has engineered the answer in is not a
                # model result: with prevalence <=0.002 there are too few positives for AUROC to mean
                # anything, so the column is labelled rather than quietly reported.
                "auc_is_informative": bool(n_pos >= 50),
                "mean_catalog": round(float(cond_df.n_candidates.mean()), 2),
                "prevalence": round(float(y.mean()), 4), "auc_refit_mean": round(float(np.mean(aucs)), 4),
                "auc_refit_sd": round(float(np.std(aucs, ddof=1)), 4) if len(aucs) > 1 else None,
                "auc_transfer_control": round(float(trans_auc), 4),
                "mean_predicted_risk": round(float(oof.mean()), 4),
                "mean_idf_coverage": round(float(np.mean([f.get("qpp_idf_weighted_coverage", np.nan)
                                                          for f in feats])), 4),
                "delta_prevalence_ci95": dp, "delta_auc_ci95": da,
                "delta_predicted_risk_ci95": dr, "corr_delta_prevalence_delta_risk": cor}
            if cond == "control":
                drift = int((y != y0).sum())
                res[cond]["label_drift_vs_published"] = drift
                if drift:
                    raise SystemExit(f"[{cfg}] control condition changes {drift} published labels; "
                                     "the intervention harness does not reproduce the dataset")
            for key, v in res[cond].items():
                long_rows.append({"config": cfg, "condition": cond, "stat": key, "value": v})
            print(f"[{cfg}] {cond:18s} cat={res[cond]['mean_catalog']:5.2f} "
                  f"prev={res[cond]['prevalence']:.4f} AUCrefit={res[cond]['auc_refit_mean']:.4f} "
                  f"AUCtrans={res[cond]['auc_transfer_control']:.4f} "
                  f"Δrisk={res[cond]['mean_predicted_risk']:.4f}")
        # dose-response slope over the distractor ladder
        dpts = [(res[f"distract_{k}"]["mean_catalog"], res[f"distract_{k}"]["prevalence"])
                for k in (2, 4, 8)]
        slope = float(np.polyfit([p[0] for p in dpts], [p[1] for p in dpts], 1)[0]) if len(dpts) == 3 else None
        res["dose_response"] = {"distractor_points": dpts,
                                "prevalence_per_extra_candidate": None if slope is None else round(slope, 5),
                                # None = mathematically undefined (zero-variance delta), not zero
                                "risk_tracking_mean_corr": (lambda vals: round(float(np.mean(vals)), 4)
                                                            if vals else None)(
                                    [v for v in (res[c]["corr_delta_prevalence_delta_risk"]
                                                 for c in CONDITIONS if c != "control") if v is not None]),
                                "enrich_gold_minus_sham_prevalence": round(
                                    res["enrich_gold"]["prevalence"] - res["enrich_sham"]["prevalence"], 4)}
        per_cfg[cfg] = res

    verdict = {
        "auc_caveat": "enrich_gold/enrich_sham refit AUROC values are NOT model-improvement evidence: "
                      "gold enrichment drives prevalence to ~0.001-0.002, where AUROC is degenerate. "
                      "Read those arms for their prevalence effect, which is the curated-metadata "
                      "result, and read distract_* for the predictor-tracking result.",
        "informative_auc_arms_per_config": {c: [k for k, v in per_cfg[c].items()
                                                if isinstance(v, dict) and v.get("auc_is_informative")]
                                            for c in CONFIGS},
        "mechanism_supported_by_intervention": bool(
            all(per_cfg[c]["enrich_gold"]["prevalence"] < per_cfg[c]["control"]["prevalence"]
                and per_cfg[c]["enrich_gold"]["prevalence"] <= per_cfg[c]["enrich_sham"]["prevalence"]
                for c in CONFIGS)),
        "competition_monotone_in_distractors": bool(
            all(per_cfg[c]["dose_response"]["prevalence_per_extra_candidate"] is None
                or per_cfg[c]["dose_response"]["prevalence_per_extra_candidate"] >= 0 for c in CONFIGS)),
        "predictor_tracks_the_informative_interventions": {
            c: round(float(np.mean([per_cfg[c][k]["mean_predicted_risk"] - per_cfg[c]["control"]["mean_predicted_risk"]
                                    for k in ("distract_2", "distract_4", "distract_8")])), 4)
            for c in CONFIGS},
        "risk_increase_on_crowding_distract8": {
            c: round(per_cfg[c]["distract_8"]["mean_predicted_risk"]
                     - per_cfg[c]["control"]["mean_predicted_risk"], 4) for c in CONFIGS},
        "failure_increase_on_crowding_distract8": {
            c: round(per_cfg[c]["distract_8"]["prevalence"]
                     - per_cfg[c]["control"]["prevalence"], 4) for c in CONFIGS},
        "predictor_tracks_the_intervention": bool(all(
            (per_cfg[c]["distract_8"]["mean_predicted_risk"] - per_cfg[c]["control"]["mean_predicted_risk"])
            > 0 and (per_cfg[c]["distract_8"]["prevalence"] - per_cfg[c]["control"]["prevalence"]) > 0
            for c in CONFIGS)),
        "per_config_key_numbers": {c: {
            "control_prev": per_cfg[c]["control"]["prevalence"],
            "enrich_gold_prev": per_cfg[c]["enrich_gold"]["prevalence"],
            "enrich_sham_prev": per_cfg[c]["enrich_sham"]["prevalence"],
            "distract8_prev": per_cfg[c]["distract_8"]["prevalence"],
            "transfer_auc_on_distract8": per_cfg[c]["distract_8"]["auc_transfer_control"],
            "risk_corr_distract8": per_cfg[c]["distract_8"]["corr_delta_prevalence_delta_risk"]}
            for c in CONFIGS},
        "caveat": "enrichment injects words taken from the instruction into a description, which is what "
                  "log-driven catalog curation does in practice, but it is NOT a free lunch: the sham arm "
                  "is the control that keeps this from being read as a universal win.",
        "test_split_read": False, "llm_api_used": False}
    out = {"exp_id": "EXP-0016", "stage": "e17_catalog_intervention_dev_only", "seed": SEED,
           "seeds_used": SEEDS, "k": K, "dv": DV, "conditions": CONDITIONS,
           "condition_definitions": {
               "control": "published catalog, unchanged",
               "distract_2/4/8": "append k decoys sampled from the gold tool's own non-stopword vocabulary",
               "enrich_gold": "append the instruction's top-IDF catalog-absent terms to the gold description",
               "enrich_sham": "same enrichment on a random non-gold tool (specificity control)",
               "namespace_prefix": "rename every tool as srv-<rand>-<name>",
               "order_shuffle": "permute catalog order (near-null control)"},
           "configs": per_cfg, "verdict": verdict, "n_bootstrap": N_BOOT,
           "runtime_sec": round(time.time() - t0, 1), "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    p = OUT_RAW / f"EXP0016_catalog_intervention_{time.strftime('%Y%m%dT%H%M%S')}.json"
    p.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    pd.DataFrame(long_rows).to_csv(OUT_PROC / "EXP0016_intervention_table.csv", index=False)
    (OUT_PROC / "EXP0016_intervention_verdict.json").write_text(json.dumps(verdict, indent=1), encoding="utf-8")
    print("\nverdict:", json.dumps(verdict, indent=1))
    print("wrote", p.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
