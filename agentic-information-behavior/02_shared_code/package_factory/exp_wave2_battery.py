"""EXP-0141: the E00-E19 battery for wave 2, run per package rather than asserted.

Spec section 9 requires the twenty-step minimum experiment package of *every* paper, so a wave-2 package needs the
ablation, the learning curve, the replication under a new seed, the error taxonomy, the quoted cases, the second
instrument, the counterfactual rewrite, the external-transfer arm, the cost table and the contamination audit - not
only its pre-registered hypothesis test.

The single-frame steps (`fit`, `e12_scaling`, `e04_ablation`, `e18_replicate`, `e15_16_errors`, `e19_contamination`)
are imported from `exp_wave1_battery.py` unchanged: they take a frame and the frozen (y, x, covariates) triple, so
running them here is the same instrument on new data, not a rewritten statistic. Wave 2 supplies the frames and the
steps whose measurement is description-side:

* E06 - each construct measured a second way by a different rule, correlated within query clusters, and an explicit
  list of the constructs for which the matrix carries only one operationalisation;
* E17 - a mechanical rewrite of the *gold description*, re-scored by the frozen ranker (wave 1 rewrote the query);
* E08 - external transfer, which starts by asking whether the second corpus carries the field at all.

Nothing here re-tunes a model or moves a threshold: the covariate sets are the ones in `exp_wave2_designs.py`, the
cluster unit is `query_id`, and the bands are the frozen .05/.15/.30.

    python 02_shared_code/package_factory/exp_wave2_battery.py [--quick]
"""
from __future__ import annotations

import argparse
import random
import re
import sys
import time

import numpy as np
import pandas as pd

HERE = pathlib_dir = __import__("pathlib").Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import wave_lib as W                                              # noqa: E402
import exp_wave1_battery as B1                                    # noqa: E402
import exp_wave2_designs as D2                                    # noqa: E402

# topic -> (frame, outcome, predictor, covariates). The predictor is the construct whose frozen test the package
# carries; the battery asks of it: how much data the estimate needs (E12), what happens without the controls (E04),
# whether it survives a new seed (E18), and which rows drive it (E15/E16).
SPEC = {
    "T111": dict(frame="candidate", y="gold", x="constraint_agree", family="binomial",
                 covars=["bm25_z", "dense_z", "entity_agree", "action_agree"]),
    "T114": dict(frame="candidate", y="at_rank1", x="centr_z", family="binomial",
                 covars=["fit_z", "bm25_z", "n_candidates"]),
    "T115": dict(frame="query", y="reachable", x="composite_z", family="binomial",
                 covars=["len_tok_z", "n_candidates"]),
    "T116": dict(frame="query", y="reachable", x="len_tok_z", family="binomial",
                 covars=["gold_param_n", "n_candidates"]),
}

# Pairs of columns that measure the same thing by different rules. Each entry is
# (construct, column A, column B, how B differs from A); anything not listed here has one operationalisation only
# and is reported under `single_instrument_constructs` rather than being given a made-up partner.
SECOND_INSTRUMENTS = [
    ("description length (tokens vs characters)", "desc_tokens", "desc_chars",
     "character count is blind to the identifier-aware tokeniser"),
    ("description length (tokens vs clauses)", "desc_tokens", "desc_clauses",
     "clause count is a syntactic, not a lexical, size proxy"),
    ("description length (characters vs clauses)", "desc_chars", "desc_clauses",
     "neither count uses the tokeniser"),
    ("enumeration (share vs absolute parameter count)", "enum_share", "param_n",
     "share normalises by description length; the count does not"),
    ("specificity (entity share vs proper-noun density)", "entity_specificity", "verb_coverage",
     "NOT a second instrument for specificity: it measures the verb lexicon, reported to show the two are distinct"),
]


def frames() -> dict:
    """The wave-2 frames, built by the same loader the pre-registered designs used."""
    Q, C = D2.load()
    c = C.dropna(subset=["prototype_centrality", "dense", "bm25"]).copy()
    c["centr_z"] = D2.z(c["prototype_centrality"])
    c["fit_z"] = D2.z(c["dense"])
    c["at_rank1"] = (c["rank_full"] == 1).astype(int)
    q = Q.copy()
    q["reachable"] = 1 - q["fail_at_1"]
    q["len_tok_z"] = D2.z(q["gold_desc_tokens"])
    blocks = {"length": ["gold_desc_tokens", "gold_param_n"], "enumeration": ["gold_enum_share"],
              "verb": ["gold_verb_coverage"],
              "agreement": ["gold_action_agree", "gold_entity_agree", "gold_constraint_agree"]}
    have = {b: [x for x in g if x in q] for b, g in blocks.items()}
    have = {b: g for b, g in have.items() if g}
    # This z-sum is a battery convenience for error profiling, NOT the pre-registered model of EXP-0139, which fits
    # the blocks separately. The artefact carries `composite_note` saying so, so no reader can mistake one for the
    # other.
    # z-score every column, then average within a block and across blocks: `z` takes a column, so passing it a
    # DataFrame raises pandas' ambiguous-truth-value error rather than doing nothing useful.
    std = pd.DataFrame({b: pd.concat([D2.z(q[c].astype(float)).rename(c) for c in g], axis=1).mean(axis=1)
                        for b, g in have.items()})
    q = pd.concat([q, std.mean(axis=1).rename("composite_z")], axis=1)
    return {"candidate": c, "query": q.dropna(subset=["composite_z"])}


def e06_second_instrument(fr: dict) -> dict:
    c = fr["candidate"]
    rows = []
    for label, a, b, why in SECOND_INSTRUMENTS:
        if a not in c or b not in c:
            rows.append({"construct": label, "status": f"NOT COMPUTABLE: {a if a not in c else b} is not a column"})
            continue
        d = c[[a, b, "query_id"]].dropna()
        r = dict(W.rho_ci(d, "query_id", a, b))
        r.update(construct=label, alternative=why, n=int(len(d)), clusters=int(d["query_id"].nunique()))
        rows.append(r)
    used = {x for _, a, b, _ in SECOND_INSTRUMENTS for x in (a, b)}
    all_c = [k for k in ("prototype_centrality", "entity_agree", "action_agree", "constraint_agree",
                         "verb_coverage") if k in c.columns]
    return {"pairs": rows,
            "single_instrument_constructs": [k for k in all_c if k not in used],
            "note": "a construct with one operationalisation is listed, not silently dropped: agreement between two "
                    "measurements that do not exist cannot be reported"}


ENUM = re.compile(r"\b(parameters?|args?|fields?|options?|takes?|accepts?|:)\b[^.]{0,200}", re.I)
PAREN = re.compile(r"\([^()]{3,80}\)")


def e17_counterfactual(rows: int = 2500) -> dict:
    """Mechanical rewrites of the *gold description*, re-scored by the frozen ranker.

    Five arms: the baseline, then strip the enumerated parameter list, strip parentheticals, truncate to eight
    tokens, and append the parameter names the catalogue already carries. All are reversible by reading them and none
    is generated by a model. The measured quantity is whether the released selection still occupies rank 1 under the
    same BM25, scored row by row so the comparison is paired within the query.
    """
    d = W.load_routing(cfgs=W.CONFIGS, bucket="dev")
    d = d[d["subset_name"].astype(str).str.contains("single-turn-original", na=False)]
    rng = random.Random(W.SEED)
    per = max(1, rows // max(1, d["cfg"].nunique()))
    keep = [g.iloc[sorted(rng.sample(range(len(g)), min(per, len(g))))] for _, g in d.groupby("cfg")]
    d = pd.concat(keep, ignore_index=True)
    arms = {k: [] for k in ("baseline", "strip_enumeration", "strip_parentheticals", "truncate8", "append_params")}
    n_done = 0
    for r in d.itertuples(index=False):
        ent = W.read_catalog(r.catalog_json, r.n_candidates, r.query_id)
        gold = W.as_int_list(r.gold_idx)
        if not ent or not gold:
            continue
        gi = min(gold)
        desc = str(ent[gi].get("desc") or "")

        def rank1_ok(edits):
            e2 = [dict(x) for x in ent]
            e2[gi].update(edits)
            return float(int(np.argmin(-W.bm25_matrix(str(r.question), e2, mode="full"))) == gi)
        try:
            arms["baseline"].append(rank1_ok({}))
            arms["strip_enumeration"].append(rank1_ok({"desc": ENUM.sub(" ", desc)}))
            arms["strip_parentheticals"].append(rank1_ok({"desc": PAREN.sub(" ", desc)}))
            arms["truncate8"].append(rank1_ok({"desc": " ".join(desc.split()[:8])}))
            arms["append_params"].append(rank1_ok({"desc": desc + " " + " ".join(map(str, ent[gi].get("params") or []))}))
            n_done += 1
        except Exception:                                          # noqa: BLE001 - one unreadable catalogue must not
            continue                                               #                        erase the other rows
    if n_done == 0:
        return {"status": "NOT MEASURED: no row yielded both a parseable catalogue and a gold index",
                "rows_attempted": int(len(d))}
    base = np.array(arms["baseline"], dtype=float)
    out = []
    for k, v in arms.items():
        p = np.array(v, dtype=float)
        dif = p - base
        out.append(dict(arm=k, n=int(len(p)), hit_at_1=round(float(p.mean()), 4),
                        vs_baseline=round(float(p.mean() - base.mean()), 4),
                        paired_se=round(float(dif.std(ddof=0) / max(1, len(dif)) ** 0.5), 4),
                        changed_rows=int((dif != 0).sum())))
    return {"rows": n_done, "arms": out, "instrument": "the frozen BM25 over name+description+parameters",
            "note": "the unit is the query and every arm is scored on the same rows, so the paired difference is the "
                    "quantity; the unpaired rates across arms are not comparable"}


def e19_description_duplication(sample_rows: int = 3000) -> dict:
    """Cross-config duplicate *descriptions*, which wave 1's uuid-level audit cannot see.

    A shared tool description in two configs is not a leaked row but is a shared measurement: the two configs'
    estimates are then not independent samples of catalogue text. Measured on a bounded sample with a digest, which
    the feature matrix does not carry.
    """
    base = B1.e19_contamination()
    d = W.load_routing(cfgs=W.CONFIGS, bucket="dev")
    d = d[d["subset_name"].astype(str).str.contains("single-turn-original", na=False)]
    rng = random.Random(W.SEED)
    idx = sorted(rng.sample(range(len(d)), min(sample_rows, len(d))))
    sha_by_cfg, counts = {}, {}
    for r in d.iloc[idx].itertuples(index=False):
        ent = W.read_catalog(r.catalog_json, r.n_candidates, r.query_id)
        for e in ent or []:
            h = W.text_sha(str(e.get("desc") or ""))
            sha_by_cfg.setdefault(h, set()).add(r.cfg)
            counts[h] = counts.get(h, 0) + 1
    n = max(1, len(sha_by_cfg))
    return {"wave1_row_level_audit": base,
            "distinct_descriptions_in_sample": len(sha_by_cfg),
            "descriptions_in_more_than_one_config": sum(1 for v in sha_by_cfg.values() if len(v) > 1),
            "share_of_descriptions_shared_across_configs": round(
                sum(1 for v in sha_by_cfg.values() if len(v) > 1) / n, 5),
            "most_reused_description_row_count": int(max(counts.values()) if counts else 0),
            "sample_rows": len(idx),
            "rule": "dev bucket only; no test-split row is opened by any wave-2 estimate"}


FAMILIES = ("temporal", "entity", "numeric", "format", "scope", "negation")


def e08_external(rows: int = 3000) -> dict:
    """Re-estimate the wave-2 effects on the second corpus, with the same rules and the same estimands.

    Only what can be computed *by the frozen rule* transfers. Constraint fit is the count of the six families
    present on both sides, predicate/argument fit come from `wave_lib.predicate_argument`, description length from
    the same tokeniser, and reachability is rank 1 of the same BM25 - so a matching coefficient means the same
    quantity moved corpus, not a look-alike proxy. Prototype centrality is reported as not transferable because it
    is defined on the encoder's vector space and this corpus is scored lexically here; substituting a bag-of-words
    centroid would be a different construct wearing the old name.
    """
    try:
        h = W.hermes_routing(bucket="external")
    except Exception as exc:                                       # noqa: BLE001 - an absent corpus is a result
        return {"status": "NOT RUN: the second corpus could not be opened", "error": str(exc)[:200]}
    rng = random.Random(W.SEED)
    h = h.iloc[sorted(rng.sample(range(len(h)), min(rows, len(h))))]
    out_rows, per_query = [], []
    for r in h.itertuples(index=False):
        ent = W.read_catalog(r.catalog_json, getattr(r, "n_candidates", None), getattr(r, "uuid", ""))
        gold = set(W.as_int_list(r.gold_idx))
        if not ent or not gold:
            continue
        q = str(getattr(r, "question", "") or "")
        qm = W.constraint_markers(q)
        uid = str(getattr(r, "uuid", "") or getattr(r, "query_id", len(per_query)))
        for i, e in enumerate(ent):
            text = " ".join(str(e.get(k) or "") for k in ("name", "desc", "params"))
            dm = W.constraint_markers(text)
            pa = W.predicate_argument(q, e)
            out_rows.append(dict(query_id=uid, gold=int(i in gold),
                                 constraint_agree=sum(1 for f in FAMILIES if qm[f] > 0 and dm[f] > 0),
                                 desc_tokens=len(W.toks(text)),
                                 **{k: pa[k] for k in ("predicate_fit", "argument_fit", "both_fit")}))
            if i == min(gold):
                # T116's estimand is query-level: is the *released selection* reachable at rank 1. Reading it off
                # candidate rows would copy one query-level fact onto every candidate and inflate n, so the gold
                # row contributes the query frame instead.
                per_query.append(dict(query_id=uid, reachable=int(int(getattr(r, "bm25_best_rank", 0) or 0) == 1),
                                      gold_desc_tokens=len(W.toks(text))))
    if not out_rows:
        return {"status": "NOT MEASURED: no external-corpus row yielded a parseable catalogue and a gold index",
                "rows_attempted": int(len(h))}
    d = pd.DataFrame(out_rows)
    qd = pd.DataFrame(per_query).drop_duplicates("query_id")
    qd["len_tok_z"] = (qd["gold_desc_tokens"] - qd["gold_desc_tokens"].mean()) / (
        qd["gold_desc_tokens"].std(ddof=0) or 1.0)
    arms = {
        "T111_constraint_fit_on_external": (d, dict(y="gold", x="constraint_agree", family="binomial",
                                                    covars=["predicate_fit", "argument_fit"])),
        "T111_predicate_and_argument_fit_on_external": (d, dict(y="gold", x="both_fit", family="binomial",
                                                                covars=[])),
        "T116_description_length_on_reachability": (qd, dict(y="reachable", x="len_tok_z", family="binomial",
                                                             covars=[])),
    }
    res = {}
    for name, (frame, sp) in arms.items():
        dd = frame.dropna(subset=[sp["y"], sp["x"]] + sp["covars"] + ["query_id"])
        if dd["query_id"].nunique() < 30:
            res[name] = {"status": "NOT MEASURED: fewer than 30 query clusters on the external corpus"}
            continue
        res[name] = dict(B1.fit(dd, sp), rows=int(len(dd)), clusters=int(dd["query_id"].nunique()),
                         unit=("query" if frame is qd else "candidate row"))
    return {"status": "RUN", "corpus": "HERMES (external)", "queries": int(d["query_id"].nunique()),
            "candidate_rows": int(len(d)), "query_rows": int(len(qd)), "arms": res,
            "not_transferred": {"prototype_centrality": "defined on the encoder vector space; a lexical centroid "
                                                        "substitute would measure a different construct",
                                "entity_specificity": "needs the catalogue-side proper-noun spans this corpus does "
                                                     "not carry in the same field"},
            "gold_rate": round(float(d["gold"].mean()), 5),
            "reachable_rate": round(float(qd["reachable"].mean()), 5)}


def run_battery(exp_id: str, tag: str, frames_fn, spec: dict, shared, quick: bool = False) -> dict:
    """The E-step loop, so a later wave supplies frames, a spec and its own shared steps - not a copy of this file.

    Every step function takes a frame and the frozen (y, x, covariate) triple, which is what a new wave changes;
    duplicating the loop would let two waves' ablations or replications drift apart without anyone noticing.
    """
    t0 = time.time()
    fr = frames_fn()
    steps = {}
    for topic, sp in spec.items():
        if sp["frame"] not in fr:
            steps[topic] = {"status": "frame_absent", "frame": sp["frame"]}
            continue
        df = fr[sp["frame"]]
        if quick:
            df = df.sample(min(20000, len(df)), random_state=W.SEED)
        clu = sp.get("cluster") or "query_id"
        if clu not in df.columns:
            raise SystemExit(f"ABORT {topic}: the spec clusters on {clu!r}, which the frame lacks")
        steps[topic] = dict(frame=sp["frame"], rows=int(len(df)), clusters=int(df[clu].nunique()),
                            primary=B1.fit(df, sp), e12_scaling=B1.e12_scaling(df, sp),
                            e04_ablation=B1.e04_ablation(df, sp), e18_replication=B1.e18_replicate(df, sp),
                            e_by_config=B1.e_by_config(df, sp),
                            e15_16=B1.e15_16_errors(df, sp, None), cluster_unit=clu)
    steps["_shared"] = dict(shared(fr, quick), **{"composite_note": "the battery's `composite_z` is the unweighted mean of the four block "
                                          "z-scores, used only to profile errors and scaling; EXP-0139's "
                                          "pre-registered model fits the blocks separately"})
    steps["_shared"]["run_cost"] = W.run_cost_row(exp_id, t0, sum(int(v.get("rows", 0)) for k, v in steps.items()
                                                                  if isinstance(v, dict)), 0)
    steps["invocation"] = " ".join([sys.executable] + sys.argv)
    steps["seed"] = W.SEED
    dest = W.write_raw(exp_id, tag, steps)
    print(f"{exp_id}: wrote {dest.name}  (wallclock {round(time.time() - t0, 1)}s)")
    for k, v in steps.items():
        if not isinstance(v, dict) or k.startswith("_") or k in ("invocation", "seed"):
            continue
        print(f"  {k}: rows={v.get('rows')} primary_beta={(v.get('primary') or {}).get('beta')} "
              f"verdict={(v.get('primary') or {}).get('verdict')}")
    e17 = steps["_shared"].get("e17_counterfactual") or {}
    # wave 1 and 2 store the arms under "arms", wave 3 under "rank1_arms"; reading only one key printed
    # "E17 arms: []" for a run whose artefact held three fully populated arms.
    arms = e17.get("arms") or e17.get("rank1_arms") or []
    print("  E17 arms:", [(r.get("arm"), r.get("hit_at_1", r.get("hit_at_1_arm"))) for r in arms][:6]
          or f"none under arms/rank1_arms (keys present: {sorted(e17)})")
    print("  E08:", (steps["_shared"].get("e08_external") or {}).get("status", "")[:90])
    return steps


def _wave2_shared(fr, quick):
    return {"e06_second_instrument": e06_second_instrument(fr),
            "e08_external": e08_external(),
            "e19_contamination": e19_description_duplication(30 if quick else 3000),
            "e17_counterfactual": e17_counterfactual(25 if quick else 2500)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    run_battery("EXP-0141", "wave2_battery_0141", frames, SPEC, _wave2_shared, quick=a.quick)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
