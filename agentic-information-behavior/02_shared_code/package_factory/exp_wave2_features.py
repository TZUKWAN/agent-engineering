"""EXP-0136: the wave-2 metadata feature matrix, built once for the four designs whose premises held.

Wave 1 measured the instruction; wave 2 measures what the agent is *shown*. One row per query x candidate, carrying:

* the three agreement kinds T111 separates - entity (named spans of the instruction found in the candidate),
  action (verb lemmas found on both sides), constraint (per-family markers found on both sides);
* the description properties T115 and T116 need - tokens, clauses, named parameters, parameter-enumeration share,
  verb-lexicon coverage, entity specificity per 100 tokens;
* the distributional position T114 needs - `prototype_centrality`, the mean cosine from this candidate to the other
  candidates of the same catalogue, from the local encoder cache (EXP-0120), plus the lexical and semantic rank of
  the candidate inside its own catalogue;
* the same self-tests and parse guards as wave 1, because a metadata matrix whose catalogue silently failed to parse
  would make every agreement column look like zero evidence rather than zero measurement.

    python 02_shared_code/package_factory/exp_wave2_features.py [--rows 8000]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import random
import re
import sys
import time

import numpy as np
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import wave_lib as W                                              # noqa: E402
import encode_wave1_texts as ENC                                          # noqa: E402  (rendering + keying, single source)

OUTQ = W.OUT / "EXP0136_wave2_query_features.csv"
OUTC = W.OUT / "EXP0136_wave2_candidate_features.csv.gz"
CLAUSE_RE = re.compile(r"[.;,]| and ")
PARAM_RE = re.compile(r"\b[a-z][a-z0-9_]{2,}\b")


def instr_families(text: str) -> dict:
    """Which constraint families the instruction actually states, as booleans."""
    m = W.constraint_markers(text)
    return {k: int(m[k] > 0) for k in ("temporal", "entity", "numeric", "format", "scope", "negation")}


def desc_families(desc: str) -> dict:
    ql = " " + re.sub(r"\s+", " ", str(desc or "").lower()) + " "
    out = {"temporal": int(any(f" {w} " in ql for w in W.TEMPORAL) or bool(W.DATE_RE.search(desc or ""))),
           "entity": int(bool(W.PROPER_RE.findall(desc or ""))),
           "numeric": int(bool(W.NUM_RE.findall(ql)) or any(f" {w} " in ql for w in W.NUMWORD)),
           "format": int(any(f" {w} " in ql for w in W.FORMAT_WORDS)),
           "scope": int(any(f" {w} " in ql for w in W.SCOPE_WORDS)),
           "negation": int(any(f" {w.strip()} " in ql for w in W.NEG_WORDS))}
    return out


def build(rows_per_config: int = 8000, verbose: bool = True):
    d = W.load_routing(cfgs=W.CONFIGS, bucket="dev")
    d = d[d["subset_name"].astype(str).str.contains("single-turn-original", na=False)]
    keep = []
    for cfg, g in d.groupby("cfg"):
        idx = sorted(random.Random(W.SEED).sample(range(len(g)), min(rows_per_config, len(g))))
        keep.append(g.iloc[idx])
    d = pd.concat(keep, ignore_index=True)
    d = W.add_linguistic_frame(d)
    vi = W.load_encoder_vectors()
    if not vi:
        raise SystemExit("ABORT: EXP-0120's encoder cache is absent; prototype centrality cannot be measured, and a "
                         "lexical stand-in would not answer the design")
    guard = {"catalog_unparsed": 0, "gold_index_out_of_range": 0, "dense_missing": 0, "rows": int(len(d))}
    qrows, crows = [], []
    t0 = time.time()
    for r in d.itertuples(index=False):
        try:
            ent = W.read_catalog(r.catalog_json, r.n_candidates, r.query_id)
        except AssertionError:
            guard["catalog_unparsed"] += 1
            ent = []
        gold = set(W.as_int_list(r.gold_idx))
        if gold and max(gold) >= len(ent):
            guard["gold_index_out_of_range"] += 1
            gold = set()
        if not ent:
            continue
        q = str(r.question)
        qf = instr_families(q)
        qw = set(W.toks(q))
        qverbs = {lem for lem, forms in W.VERB_LEMMA.items() if qw & set(forms)}
        qobjs = {c for c, forms in W.OBJECT_NOUNS.items() if qw & set(forms)}
        qents = {e.lower() for e in W.PROPER_RE.findall(q)}
        docs = [f"{e['name']} {e['desc']} {' '.join(e['params'] or [])}" for e in ent]
        dv = []
        for i, t in enumerate(docs):
            key = W.text_sha(f"D|{r.query_id}|{i}|" + ENC.render_doc(ent[i]["name"], ent[i]["desc"],
                                                                      ent[i]["params"]))
            v = vi.vec_for("d", key)
            if v is None:
                guard["dense_missing"] += 1
            dv.append(v)
        M = np.vstack([v if v is not None else np.zeros(384, dtype=np.float32) for v in dv])
        present = [i for i, v in enumerate(dv) if v is not None]
        cent = {}
        if len(present) > 2:
            S = M[present] @ M[present].T
            for a, i in enumerate(present):
                row = np.delete(S[a], a)
                cent[i] = float(row.mean())
        for i, e in enumerate(ent):
            df_ = desc_families(f"{e['desc']} {' '.join(e['params'] or [])}")
            dw = set(W.toks(docs[i]))
            dverbs = {lem for lem, forms in W.VERB_LEMMA.items() if dw & set(forms)}
            dobjs = {c for c, forms in W.OBJECT_NOUNS.items() if dw & set(forms)}
            toks_i = W.toks(docs[i])
            params = [p for p in (e["params"] or [])]
            crows.append({
                "query_id": r.query_id, "cfg": r.cfg, "cand_idx": i, "gold": int(i in gold),
                "entity_agree": int(bool(qents) and any(x in docs[i].lower() for x in qents)),
                "action_agree": int(bool(qverbs & dverbs)),
                "object_agree": int(bool(qobjs & dobjs)),
                "constraint_agree": int(sum(qf[k] and df_[k] for k in qf)),
                **{f"agree_{k}": int(qf[k] and df_[k]) for k in qf},
                "q_family_n": int(sum(qf.values())), "d_family_n": int(sum(df_.values())),
                "desc_tokens": len(toks_i), "desc_chars": len(str(e["desc"])),
                "desc_clauses": int(len([x for x in CLAUSE_RE.split(str(e["desc"])) if x.strip()])),
                "param_n": len(params),
                "enum_share": round(float(np.mean([p.lower() in str(e["desc"]).lower() for p in params])), 4)
                if params else np.nan,
                "verb_coverage": round(float(len(dverbs) / max(1, len(W.VERB_LEMMA))), 4),
                "entity_specificity": round(float(100.0 * len(W.PROPER_RE.findall(docs[i])) /
                                                  max(1, len(docs[i]))), 4),
                "prototype_centrality": round(cent.get(i, np.nan), 5) if i in cent else np.nan,
                "has_dense": int(dv[i] is not None)})
        # query-level row: the released selection's own metadata properties, for the reachability designs
        gi = sorted(gold) or [0]
        gc = [c for c in crows[-len(ent):] if c["gold"] == 1] or crows[-len(ent):][:1]
        g0 = gc[0]
        qrows.append({"query_id": r.query_id, "cfg": r.cfg, "n_candidates": len(ent), "n_gold": len(gold),
                      "gold_action_agree": g0["action_agree"], "gold_entity_agree": g0["entity_agree"],
                      "gold_object_agree": g0["object_agree"], "gold_constraint_agree": g0["constraint_agree"],
                      "gold_desc_tokens": g0["desc_tokens"], "gold_param_n": g0["param_n"],
                      "gold_verb_coverage": g0["verb_coverage"], "gold_enum_share": g0["enum_share"],
                      "gold_entity_specificity": g0["entity_specificity"],
                      "gold_prototype_centrality": g0["prototype_centrality"],
                      "max_nongold_prototype": (max([c["prototype_centrality"] for c in crows[-len(ent):]
                                                     if not c["gold"] and np.isfinite(c["prototype_centrality"])],
                                                    default=np.nan)),
                      "q_family_n": g0["q_family_n"], "constraint_total": int(r.constraint_total),
                      "underspec_index": round(float(r.underspec_index), 5), "n_tokens": int(r.n_tokens),
                      "fail_at_1": int(r.fail_at_1), "fail_at_3": int(r.fail_at_3),
                      "bm25_best_rank": int(r.bm25_best_rank), "n_servers_in_row": int(r.n_servers_in_row)})
    Q = pd.DataFrame(qrows)
    C = pd.DataFrame(crows)
    if verbose:
        print(f"[exp0136] queries={len(Q)} candidate rows={len(C)} in {time.time() - t0:.1f}s guard={guard}")
    if len(C) < len(Q) or guard["catalog_unparsed"] > 0.01 * len(d) or guard["dense_missing"] > 0.02 * len(C):
        raise SystemExit(f"ABORT: wave-2 matrix incomplete (queries {len(Q)}, candidates {len(C)}, guard {guard})")
    return Q, C, guard


def premise_gates(Q: pd.DataFrame, C: pd.DataFrame) -> dict:
    """The gate each wave-2 design still owes before its outcomes are read."""
    coll = W.vif(C[["entity_agree", "action_agree", "constraint_agree"]].astype(float))
    out = {"T111_separable_components": dict(vif=coll, fires=bool(np.isfinite(coll.get("action_agree", np.nan))
                                                                  and coll["action_agree"] >= 10)),
            "T114_prototype_variance": dict(
                sd=round(float(C["prototype_centrality"].std()), 5),
                finite_share=round(float(C["prototype_centrality"].notna().mean()), 4),
                fires=bool(float(C["prototype_centrality"].std()) == 0)),
            "T115_block_coverage": dict(
                length=round(float((C["desc_tokens"] > 0).mean()), 4),
                specificity=round(float((C["entity_specificity"] > 0).mean()), 4),
                enumeration=round(float(C["enum_share"].notna().mean()), 4),
                verb=round(float((C["verb_coverage"] > 0).mean()), 4),
                # the frozen gate drops any block whose coverage is under half, so the list is computed from the
                # shares above rather than written out by hand
                below_50pct=None),
            "T116_spread": dict(desc_token_deciles=int(C["desc_tokens"].quantile(
                [0.1 * i for i in range(1, 10)]).nunique()),
                fires=bool(int(C["desc_tokens"].quantile([0.1 * i for i in range(1, 10)]).nunique()) < 3))}
    g = out["T115_block_coverage"]
    g["below_50pct"] = [k for k in ("length", "specificity", "enumeration", "verb") if g[k] < 0.50]
    g["fires"] = bool(g["below_50pct"])
    return out


def selftest() -> int:
    fails = []
    f = desc_families("Convert a CSV file to JSON. Does not support Excel or nested sheets.")
    if not f["negation"]:
        fails.append("desc_families missed a negation marker")
    if not f["format"]:
        fails.append("desc_families missed a format marker")
    q = instr_families("Convert all CSV files to JSON without changing the schema")
    if not (q["format"] and q["scope"] and q["negation"]):
        fails.append(f"instruction families wrong: {q}")
    if W.predicate_argument("Convert the CSV file", {"name": "csv_to_json", "desc": "convert csv to json",
                                                     "params": []})["predicate_fit"] != 1:
        fails.append("predicate agreement not detected on an obvious pair")
    for m in fails:
        print("  SELFTEST FAIL:", m)
    print(f"selftest: {len(fails)} failure(s)")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=8000)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    st = selftest()
    if a.selftest:
        return st
    if st:
        print("ABORT: the metadata extractor tests failed, so no matrix could be written")
        return st
    t0 = time.time()
    Q, C, guard = build(a.rows)
    gates = premise_gates(Q, C)
    W.PROCES.mkdir(parents=True, exist_ok=True)
    Q.to_csv(OUTQ, index=False)
    C.to_csv(OUTC, index=False, compression="gzip")
    art = {"exp_id": "EXP-0136", "seed": W.SEED, "rows_per_config": a.rows, "bucket": "dev",
           "guards": guard, "n_query_rows": int(len(Q)), "n_candidate_rows": int(len(C)),
           "agreement_prevalence": {c: round(float(C[c].mean()), 4) for c in
                                    ("entity_agree", "action_agree", "object_agree", "constraint_agree", "gold")},
           "prototype_centrality": {"mean": round(float(C["prototype_centrality"].mean()), 4),
                                    "sd": round(float(C["prototype_centrality"].std()), 4),
                                    "rows_with_dense": int(C["has_dense"].sum())},
           "premise_gates": gates,
           "outputs": [str(OUTQ.relative_to(W.ROOT)), str(OUTC.relative_to(W.ROOT))],
           "run_cost": W.run_cost_row("EXP-0136", t0, len(Q), Q.shape[1], "wave-2 metadata matrix"),
           "environment": W.environment_record(), "started_at": W.now(), "finished_at": W.now()}
    p = W.write_raw("EXP-0136", "wave2_metadata_matrix", art)
    (W.LOGS / f"EXP-0136_wave2_features_{time.strftime('%Y%m%dT%H%M%S')}.txt").write_text(
        json.dumps({k: v for k, v in art.items() if k != "environment"}, indent=1, ensure_ascii=False,
                   default=str), encoding="utf-8")
    print(json.dumps({k: art[k] for k in ("n_query_rows", "n_candidate_rows", "agreement_prevalence",
                                          "prototype_centrality", "premise_gates")}, indent=1, default=str)[:1600])
    print("wrote", p.name)
    return 0



if __name__ == "__main__":
    raise SystemExit(main())
