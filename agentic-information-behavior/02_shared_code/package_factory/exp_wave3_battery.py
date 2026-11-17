"""EXP-0149: the E00-E19 battery for wave 3.

The step loop is `exp_wave2_battery.run_battery`, not a copy of it: the ablation, the scaling curve, the replication
under seed 7 and the error profile all take a frame and the frozen (y, x, covariates) triple, so what changes between
waves is the frames, the spec and the three steps whose measurement is wave-specific. Two copies of that loop would
drift, and a drift in an E-step is invisible until someone re-reads a table.

Wave 3's own versions:

* **E06** - second instruments that already exist in the matrix: lexical versus distributional discriminability, and
  the two congruence rules, correlated within query clusters.
* **E08** - external transfer to the second corpus, on the two constructs that are computable there from the
  catalogue text alone (name-description congruence and neighbour discriminability). Prototype-style dense measures
  are reported as not transferred rather than proxied.
* **E17** - the counterfactual is the arm table itself: four rewrites of one catalogue scored by the frozen ranker,
  read from EXP-0143 rather than re-ranked a second time.

    python 02_shared_code/package_factory/exp_wave3_battery.py [--quick]
"""
from __future__ import annotations

import argparse
import random
import sys
import time

import numpy as np
import pandas as pd

HERE = pathlib_ = __import__("pathlib").Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import wave_lib as W                                              # noqa: E402
import exp_wave1_battery as B1                                    # noqa: E402
import exp_wave2_battery as B2                                    # noqa: E402
import exp_wave3_designs as D3                                    # noqa: E402
import exp_wave3_features as F3                                      # noqa: E402


def z(s):
    return D2z(s)


D2z = __import__("exp_wave2_designs").z


def frames() -> dict:
    Q, C = D3.load()
    c = C.dropna(subset=["name_desc_congruence", "gold"]).copy()
    c["congr_z"] = z(c["name_desc_congruence"])
    c["len_z"] = z(c["desc_tokens"].astype(float))
    c["param_z"] = z(c["param_n"].astype(float))
    c["centr_z"] = z(c["prototype_centrality"].astype(float))
    g = C[C["gold"] == 1].groupby("query_id")[["discrimin_lexical", "discrimin_dense"]].mean().reset_index()
    q = Q.merge(g, on="query_id", how="left")
    q["reachable"] = 1 - q["fail_at_1"]
    q["lex_z"] = z(q["discrimin_lexical"])
    # The battery's length covariate is z-scored here, from the column the matrix actually carries. Naming it once,
    # in the frame that owns it, is what keeps a spec typo from being read as a missing measurement.
    q["len_z"] = z(q["gold_desc_tokens"].astype(float))
    q["gain_usecase"] = q["usecase_hit1"].astype(float) - q["baseline_hit1"].astype(float)
    q["gain_matched"] = q["usecase_matched_hit1"].astype(float) - q["baseline_hit1"].astype(float)
    q["gain_synonym"] = q["synonym_hit1"].astype(float) - q["baseline_hit1"].astype(float)
    q["mismatch_flag"] = q["gold_synonym_changed"].astype(float)
    gain = q.dropna(subset=["gain_usecase", "gain_synonym", "len_z"]).copy()
    # EXP-0145's H2 moderation term, rebuilt here by its own frozen rule (median split of the gold description's
    # token count). Without it the leave-one-term-out ablation has no complement to drop and the step silently
    # produced zero rows, which a file-level audit read as a delivered ablation.
    gain["short"] = (gain["gold_desc_tokens"] <= gain["gold_desc_tokens"].median()).astype(float)
    return {"candidate": c, "query": q, "gain": gain}


SPEC = {
    "T113": dict(frame="gain", y="gain_usecase", x="len_z", family="gaussian", covars=["short"]),
    "T119": dict(frame="candidate", y="gold", x="congr_z", family="binomial",
                 covars=["len_z", "param_z", "centr_z"]),
    "T120": dict(frame="gain", y="gain_synonym", x="mismatch_flag", family="gaussian",
                 covars=["len_z"]),
    "T122": dict(frame="query", y="reachable", x="lex_z", family="binomial",
                 covars=["gold_param_n", "gold_enum_share"]),
}


def e06_second_instrument(fr: dict, quick: bool = False) -> dict:
    c = fr["candidate"]
    out = []
    pairs = [("neighbour discriminability", "discrimin_lexical", "discrimin_dense"),
             ("name-description congruence", "name_desc_congruence", "name_predicate_in_desc"),
             ("catalogue position", "facet_overlap", "hier_depth")]
    for label, a, b in pairs:
        if a not in c or b not in c:
            out.append({"construct": label, "status": f"NOT COMPUTABLE: {a if a not in c else b} absent"})
            continue
        d = c[[a, b, "query_id"]].dropna()
        if d[b].nunique() < 3:                     # a 0/1 companion cannot carry a rank correlation claim
            agree = float((d[a].gt(d[a].median()).astype(int) == d[b].astype(int)).mean())
            out.append({"construct": label, "status": "second instrument is binary: agreement share reported, "
                                                      "no rank correlation claimed",
                        "agreement_share": round(agree, 4), "n": int(len(d))})
            continue
        r = dict(W.rho_ci(d, "query_id", a, b))
        r.update(construct=label, n=int(len(d)), clusters=int(d["query_id"].nunique()))
        out.append(r)
    return {"pairs": out,
            "note": "the wave-3 constructs are the ones the designs already promised a second instrument for; where "
                    "the companion is binary the agreement share is reported instead of a correlation coefficient"}


def e08_external(quick: bool = False) -> dict:
    """Congruence and discriminability on the second corpus, computed from its catalogue text by the same rules."""
    try:
        h = W.hermes_routing(bucket="external")
    except Exception as exc:                                       # noqa: BLE001 - an absent corpus is a result
        return {"status": "NOT RUN: the second corpus could not be opened", "error": str(exc)[:200]}
    rng = random.Random(W.SEED)
    h = h.iloc[sorted(rng.sample(range(len(h)), min(60 if quick else 2000, len(h))))]
    rows = []
    for r in h.itertuples(index=False):
        ent = W.read_catalog(r.catalog_json, getattr(r, "n_candidates", None), getattr(r, "uuid", ""))
        gold = set(W.as_int_list(r.gold_idx))
        if not ent or not gold:
            continue
        etoks = F3.entry_tokens(ent)
        lex, _ = F3.discrimin_all(etoks)
        uid = str(getattr(r, "uuid", "") or "")
        for i, e in enumerate(ent):
            con, pred, _contra = F3.congruence(str(e.get("name") or ""), e)
            rows.append(dict(query_id=uid, gold=int(i in gold), name_desc_congruence=con,
                             name_predicate_in_desc=pred, discrimin_lexical=lex[i]))
    if not rows:
        return {"status": "NOT MEASURED: no external-corpus row yielded a parseable catalogue and a gold index",
                "rows_attempted": int(len(h))}
    d = pd.DataFrame(rows)
    d["congr_z"] = z(d["name_desc_congruence"])
    d["lex_z"] = z(d["discrimin_lexical"])
    arms = {}
    for name, sp in (("T119_congruence_on_external", dict(y="gold", x="congr_z", family="binomial", covars=[])),
                     ("T122_discriminability_on_external", dict(y="gold", x="lex_z", family="binomial", covars=[]))):
        dd = d.dropna(subset=[sp["y"], sp["x"]] + ["query_id"])
        arms[name] = ({"status": "NOT MEASURED: fewer than 30 query clusters"} if dd["query_id"].nunique() < 30
                      else dict(B1.fit(dd, sp), rows=int(len(dd)), clusters=int(dd["query_id"].nunique())))
    return {"status": "RUN", "corpus": "HERMES (external)", "queries": int(d["query_id"].nunique()),
            "candidate_rows": int(len(d)), "arms": arms,
            "not_transferred": {"the rewrite arms (T113, T120)": "the four rule rewrites are defined on the Toucan "
                                                                 "catalogue fields this corpus does not carry in "
                                                                 "the same shape; transferring a paraphrase of a "
                                                                 "different text would not be the same intervention",
                                "prototype centrality": "defined on the encoder space; a lexical centroid substitute "
                                                        "would measure a different construct"}}


def e17_arms(fr: dict, quick: bool = False) -> dict:
    """The four catalogue rewrites, read from the frozen matrix rather than re-ranked here."""
    q = fr["query"]
    base = q["baseline_hit1"].astype(float)
    rows = []
    for arm in ("usecase", "usecase_matched", "synonym"):
        p = q[arm + "_hit1"].astype(float)
        dif = p - base
        rows.append(dict(arm=arm + "_vs_baseline", n=int(len(q)), hit_at_1_base=round(float(base.mean()), 4),
                         hit_at_1_arm=round(float(p.mean()), 4), vs_baseline=round(float(dif.mean()), 4),
                         paired_se=round(float(dif.std(ddof=0) / max(1, len(dif)) ** 0.5), 4),
                         changed_rows=int((dif != 0).sum())))
    rk = []
    for arm in ("usecase", "usecase_matched", "synonym"):
        dif = q[arm + "_rank"].astype(float) - q["baseline_rank"].astype(float)
        rk.append(dict(arm=arm + "_rank_minus_baseline", mean=round(float(dif.mean()), 4),
                       se=round(float(dif.std(ddof=0) / max(1, len(dif)) ** 0.5), 4),
                       improved=int((dif < 0).sum()), worsened=int((dif > 0).sum()), unchanged=int((dif == 0).sum())))
    return {"rows": int(len(q)), "rank1_arms": rows, "rank_arms": rk,
            "instrument": "the frozen BM25 over name+description+parameters, applied to the whole rewritten catalogue",
            "note": "every arm rewrites every entry of a catalogue, so a rank is comparable across arms within a "
                    "query and the paired difference is the quantity"}


def shared(fr: dict, quick: bool = False) -> dict:
    return {"e06_second_instrument": e06_second_instrument(fr, quick),
            "e08_external": e08_external(quick),
            "e17_counterfactual": e17_arms(fr, quick),
            "e19_contamination": B2.e19_description_duplication(30 if quick else 3000)}


def _columns_ok() -> None:
    """Fail at import-time use, not mid-run: every column the specs name must exist in the frame it names."""
    fr = frames()
    for tid, sp in SPEC.items():
        f = fr.get(sp["frame"])
        if f is None:
            raise SystemExit(f"ABORT {tid}: no frame {sp['frame']!r}")
        miss = [c for c in [sp["y"], sp["x"]] + list(sp.get("covars") or []) if c not in f.columns]
        if miss:
            raise SystemExit(f"ABORT {tid}: frame {sp['frame']!r} lacks {miss}; the spec names a column that was "
                             f"never built, and B1.fit would have dropped those covariates in silence")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    _columns_ok()
    B2.run_battery("EXP-0149", "wave3_battery_0149", frames, SPEC, shared, quick=a.quick)
    print(f"wallclock {round(time.time() - t0, 1)}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

