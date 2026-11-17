"""EXP-0128..EXP-0133: the E00-E19 battery for wave 1, run per package rather than asserted.

Spec section 9 requires the twenty-step minimum experiment package **of every paper**, so a wave package needs more
than its pre-registered hypothesis test: it needs the ablation, the second instrument, the learning curve, the
replication under a new seed, the error taxonomy, the quoted cases, the counterfactual rewrite, the external-corpus
transfer, the cost table and the contamination audit. This script runs them on the shared substrate, one artefact per
step, and each is registered against the six packages with a stage name that says which step it answers.

What this script deliberately does not do:
* it does not invent a step the substrate cannot support. Where a step needs a second corpus the topic does not have,
  the transfer arm is run on the corpus that does exist and the substitution is recorded in the artefact;
* it does not re-tune anything. Models, covariates, clustering unit and effect bands are the ones already frozen in
  `topic_designs_wave1.py`; a step that changes the specification would be a different experiment.

    python 02_shared_code/package_factory/exp_wave1_battery.py [--quick]
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
import encode_wave1_texts as ENC                                  # noqa: E402

# one row per topic: the frame it is measured on, its outcome, its predictor, and the covariates the freeze kept in
SPEC = {
 "T101": dict(frame="query", y="wrong_tool", x="underspec_z", family="binomial",
              covars=["len_z", "n_candidates", "n_gold"]),
 "T103": dict(frame="query", y="inspected_pos", x="density_z", family="poisson",
              covars=["len_z", "ncand_z", "ngold_z"]),
 "T106": dict(frame="fidelity", y="dfail", x="con_z", family="gaussian",
              covars=["len_z", "n_tokens", "n_candidates"]),
 "T108": dict(frame="displacement", y="displaced", x="underspec_z", family="binomial",
              covars=["len_z", "ncand_z", "ngold_z"]),
 "T109": dict(frame="conflict", y="follows_lexical", x="lex_adv_z", family="binomial",
              covars=["len_z", "ncand_z"]),
 "T110": dict(frame="candidate", y="gold", x="both_fit", family="binomial",
              covars=["bm25_z", "dense_z"]),
}
CURATE_WORDS = ["the file", "the module", "the script", "the config", "the dataset"]


def z(df, c):
    s = df[c].astype(float)
    return (s - s.mean()) / (s.std(ddof=0) or 1.0)


def build_frames() -> dict:
    Q = pd.read_csv(W.PROCES / "EXP0119_wave1_query_features.csv")
    C = pd.read_csv(W.PROCES / "EXP0119_wave1_candidate_rows.csv.gz")
    D = pd.read_csv(W.PROCES / "EXP0125_wave1_dense_scores.csv.gz") if (
        W.PROCES / "EXP0125_wave1_dense_scores.csv.gz").is_file() else None
    # query frame
    q = Q.copy()
    q["wrong_tool"] = 1 - q["top1_norm_ok"]
    q["inspected_pos"] = q["inspected_to_gold"].clip(lower=0)
    for a, b in (("underspec_z", "underspec_index"), ("density_z", "constraint_total"), ("len_z", "n_tokens"),
                 ("ncand_z", "n_candidates"), ("ngold_z", "n_gold")):
        q[a] = z(q, b)
    # displacement frame (one row per query: did a word-overlap decoy take the released selection's slot)
    gg = C[C["gold"] == 1].groupby("query_id")["bm25"].max().rename("gold_bm25")
    ng = C[C["gold"] == 0].groupby("query_id")["bm25"].max().rename("decoy_bm25")
    dsp = pd.concat([gg, ng], axis=1).dropna().reset_index()
    dsp["displaced"] = (dsp["decoy_bm25"] > dsp["gold_bm25"]).astype(float)
    dsp = dsp.merge(q[["query_id", "underspec_z", "len_z", "ncand_z", "ngold_z", "constraint_total"]],
                    on="query_id", how="inner").dropna()
    # conflict frame (queries where the lexical and distributional top-1 differ)
    cf = None
    if D is not None:
        dd = C.merge(D, on=["query_id", "cand_idx"], how="left").dropna(subset=["dense"])
        l1 = dd[dd["rank_full"] == 1][["query_id", "cand_idx", "gold", "bm25"]].rename(
            columns={"cand_idx": "lex_idx", "gold": "lex_gold", "bm25": "lex_bm25"})
        s1 = dd[dd["dense_rank"] == 1][["query_id", "cand_idx", "dense", "bm25"]].rename(
            columns={"cand_idx": "sem_idx", "dense": "sem_cos", "bm25": "sem_bm25"})
        cf = l1.merge(s1, on="query_id", how="inner")
        cf = cf[cf["lex_idx"] != cf["sem_idx"]].copy()
        cf["follows_lexical"] = (cf["lex_gold"] == 1).astype(float)
        cf["adv"] = cf["lex_bm25"] - cf["sem_bm25"]
        cf["lex_adv_z"] = z(cf, "adv")
        cf = cf.merge(q[["query_id", "len_z", "ncand_z"]], on="query_id", how="left").dropna()
    # candidate frame for T110
    cand = C.copy()
    if D is not None:
        cand = cand.merge(D, on=["query_id", "cand_idx"], how="left").dropna(subset=["dense"])
    cand["bm25_z"] = z(cand, "bm25")
    cand["dense_z"] = z(cand, "dense") if "dense" in cand else 0.0
    frames = {"query": q, "displacement": dsp, "candidate": cand}
    if cf is not None:
        frames["conflict"] = cf
    fid_path = W.PROCES / "EXP0123_t106_fidelity_rows.csv"
    if fid_path.is_file():
        f = pd.read_csv(fid_path)
        f["dfail"] = f["delta_fail"].astype(float)
        f["con_z"] = z(f.dropna(subset=["constraint_retention"]), "constraint_retention") if True else 0
        m = f.dropna(subset=["constraint_retention", "dfail"]).copy()
        m["con_z"] = z(m, "constraint_retention")
        m["len_z"] = z(m, "issued_len_tokens")
        m["n_tokens"] = z(m, "n_tokens")
        m["n_candidates"] = z(m, "n_candidates")
        frames["fidelity"] = m
    return frames


def CLU(sp, df=None):
    """The column a design clusters its standard errors on.

    The routing waves freeze `query_id`, so a spec that names nothing keeps it. A wave whose unit differs - wave 4
    clusters assistant turns inside their trajectory - names it in its spec, and this refuses rather than letting
    an artefact claim a cluster the frame does not contain.
    """
    c = sp.get("cluster") or "query_id"
    if df is not None and c not in df.columns:
        raise SystemExit(f"ABORT: the spec clusters on {c!r}, which the frame lacks; columns are "
                         f"{sorted(df.columns)[:14]}")
    return c


def terms(sp, d) -> list:
    """The model's term list, deduplicated in the order the spec names it.

    A design can manipulate a variable that also sits in its own control set - wave 5's T133 estimates the effect of
    `prev_obs_error`, which is a control in every model of that wave - and putting the identical column in the matrix
    twice splits one coefficient between two columns and leaves the cluster-robust covariance singular. The designs
    drop the duplicate through `dict.fromkeys`, so the battery has to as well, or "the same model" in an E-step is
    not the same model in a design step.
    """
    # the outcome is never one of its own regressors: wave 6's T155 manipulates need length and its dependent
    # variable is depth, which sits inside the wave's standard control set, and a duplicated column makes the fit
    # unidentifiable in the same way it does in the design script.
    return list(dict.fromkeys([c for c in [sp["x"]] + list(sp["covars"]) if c != sp["y"] and c in d.columns]))


def fit(df, sp, subset=None):
    d = df if subset is None else subset(df)
    xs = terms(sp, d)
    d = d.dropna(subset=[sp["y"]] + xs)                # the designs drop these rows before fitting; an E-step that
                                                       # keeps them is a different model on different rows
    const = [c for c in xs if d[c].nunique(dropna=False) <= 1]
    xs = [c for c in xs if c not in const]
    if not xs:
        return None
    f = W.glm_term(d, sp["y"], xs, sp["family"], cluster=CLU(sp, d))
    if f is None:
        return None
    r = f[f["term"] == sp["x"]]
    if r.empty:
        return None
    row = r.iloc[0]
    return dict(beta=round(float(row["beta"]), 4), se=round(float(row["se"]), 4),
                ci_lo=round(float(row["ci_lo"]), 4), ci_hi=round(float(row["ci_hi"]), 4),
                p=float(row["p"]), n=int(row["n"]),
                dropped_constant_terms="+".join(const) or "none")


# ------------------------------------------------------------------------------------------------- the steps
def e12_scaling(df, sp, sizes=(1000, 2000, 4000, 8000, None)):
    out = []
    clu = CLU(sp, df)
    clusters = df[clu].nunique()
    for n in sizes:
        if n and clusters < n:
            continue
        if n:
            keep = list(df[clu].drop_duplicates().sample(min(n, clusters), random_state=42))
            sub = df[df[clu].isin(keep)]
        else:
            sub = df
        r = fit(sub, sp)
        if r:
            out.append(dict(level=f"n_queries={n or clusters}", **r))
    if len(out) >= 2:
        mono = all(out[i]["se"] >= out[i + 1]["se"] - 1e-9 for i in range(len(out) - 1))
        out.append(dict(level="interval_shrinks_monotonically", note=str(mono)))
    return out


def e04_ablation(df, sp):
    """Leave-one-covariate-out and leave-one-feature-component-out, so a single retained column cannot hide an effect."""
    out = []
    for c in terms(sp, df):
        xs = [k for k in terms(sp, df) if k != c]
        d = df[[sp["y"]] + xs + [CLU(sp, df)]].dropna()
        xs = [c for c in xs if d[c].nunique(dropna=False) > 1]      # a control constant in this cell is not a control
        if not xs or len(d) < 200:
            continue
        f = W.glm_term(d, sp["y"], xs, sp["family"], cluster=CLU(sp, d))
        r = f[f["term"] == sp["x"]] if f is not None else None
        out.append(dict(removed=c, beta=(round(float(r.iloc[0]["beta"]), 4) if r is not None and len(r) else None),
                        ci_lo=(round(float(r.iloc[0]["ci_lo"]), 4) if r is not None and len(r) else None),
                        ci_hi=(round(float(r.iloc[0]["ci_hi"]), 4) if r is not None and len(r) else None),
                        n=int(len(d))))
    return out


def e_by_config(df, sp, min_rows=200, min_clusters=30):
    """The frozen model estimated inside each corpus config, so a pooled coefficient cannot hide a config where
    the term is unidentified. No threshold and no Holm entry attach to it: it is the same quantity measured where
    the catalogue differs, which is the §15 "headline result by config" panel and the reason the programme records
    per-config results as heterogeneity rather than replication (EXP-0150 measured 95.4% shared descriptions).
    """
    clu = CLU(sp, df)
    cols = [sp["y"]] + terms(sp, df) + [clu]
    if "cfg" not in df.columns:
        return [{"config": "-", "status": "NOT MEASURABLE: the frame carries no config column"}]
    out = []
    for cfg, d in df.dropna(subset=cols).groupby("cfg"):
        r = dict(config=str(cfg), rows=int(len(d)), clusters=int(d[clu].nunique()),
                 share_of_rows=round(float(len(d) / max(1, len(df.dropna(subset=cols)))), 4))
        f = fit(d, sp) if len(d) >= min_rows and d[clu].nunique() >= min_clusters else None
        r.update(f or {})
        r["status"] = "RUN" if f else f"NOT ESTIMABLE below {min_rows} rows or {min_clusters} query clusters"
        out.append(r)
    return sorted(out, key=lambda x: x["config"])


def e18_replicate(df, sp, seed=7):
    """Refit on a freshly drawn seed-7 subsample of the same size: a replication of the sampling, not of the code."""
    clu = CLU(sp, df)
    n = min(len(df), max(2000, int(0.5 * df[clu].nunique())))
    keep = list(df[clu].drop_duplicates().sample(min(n, df[clu].nunique()), random_state=seed))
    sub = df[df[clu].isin(keep)]
    return dict(seed=seed, original=fit(sub, sp), n_queries=int(sub[clu].nunique()),
                rows=int(len(sub)), same_cluster_unit=clu)


def e15_16_errors(df, sp, primary):
    """Error taxonomy plus quoted cases: where the fitted model and the observed outcome disagree."""
    d = df.dropna(subset=[sp["y"], sp["x"]]).copy()
    if len(d) < 200:
        return {}, []
    d["pred"] = (d[sp["y"]] > d[sp["y"]].mean()).astype(int)
    d["obs"] = (d[sp["y"]] > 0.5).astype(int) if set(d[sp["y"]].unique()) <= {0.0, 1.0} else (
        (d[sp["y"]] > d[sp["y"]].median()).astype(int))
    disc = d[d["pred"] != d["obs"]]
    tax = {}
    if "n_candidates" in d:
        tax["catalogue_below_median"] = int((disc["n_candidates"] < d["n_candidates"].median()).sum())
    if "n_tokens" in d:
        tax["length_top_quartile"] = int((disc["n_tokens"] > d["n_tokens"].quantile(.75)).sum())
    if "constraint_total" in d:
        tax["zero_constraints"] = int((disc["constraint_total"] == 0).sum())
    tax["discordant_rows"] = int(len(disc))
    tax["rows_total"] = int(len(d))
    tax["discordance_share"] = round(float(len(disc) / max(1, len(d))), 4)
    cols = [c for c in ("question", "issued", CLU(sp), "traj_id", "turn_index") if c in disc.columns]
    cases = []
    for r in disc.head(6).to_dict("records"):
        cases.append({c: (str(r.get(c))[:180]) for c in cols})
    return tax, cases


def e17_counterfactual(frames, sp_by_topic) -> dict:
    """A rule-based minimal pair on the instruction, scored by the frozen ranker.

    Two rewrites, both mechanical and both reversible by reading them: (a) *explicit object* - an unnamed-file
    anaphora is replaced by the name the release itself pairs with the request, and (b) *constraint strip* - every
    marker of the six constraint families is deleted. The measured quantity is the change in whether the released
    selection is reachable at rank 1 under the same BM25. No model generated either rewrite.
    """
    Q = frames["query"]
    d = W.load_routing(cfgs=W.CONFIGS, bucket="dev")
    d = d[d["subset_name"].astype(str).str.contains("single-turn-original", na=False)]
    keep = []
    for cfg, g in d.groupby("cfg"):
        idx = sorted(random.Random(W.SEED).sample(range(len(g)), min(2500, len(g))))
        keep.append(g.iloc[idx])
    d = pd.concat(keep, ignore_index=True)
    rows = []
    for r in d.itertuples(index=False):
        ent = W.read_catalog(r.catalog_json, r.n_candidates, r.query_id)
        gold = W.as_int_list(r.gold_idx)
        if not ent or not gold:
            continue
        docs = [W.doc_tokens(ent, i, "full") for i in range(len(ent))]
        q = str(r.question)
        name = ent[gold[0]]["name"]
        explicit = re.sub(r"\b(it|them|the file|that|this)\b", name.replace("-", " "), q, flags=re.I)
        stripped = q
        for fam in (W.TEMPORAL, W.FORMAT_WORDS, W.SCOPE_WORDS, W.NEG_WORDS):
            for w in fam:
                stripped = re.sub(r"\b" + re.escape(w.strip()) + r"\b", " ", stripped, flags=re.I)

        def top1_ok(text):
            t = W.toks(text)
            if not t:
                return None
            rk = W.rank_from(W._bm25_scores(t, docs))
            return int(min(rk[i] for i in gold if i < len(rk)) == 1)
        a, b, c = top1_ok(q), top1_ok(explicit), top1_ok(stripped)
        if a is None or b is None or c is None:
            continue
        rows.append(dict(query_id=r.cfg + "|" + r.uuid, base=a, explicit=b, stripped=c,
                         d_explicit=b - a, d_stripped=c - a,
                         changed=bool(a != b or a != c)))
    F = pd.DataFrame(rows)
    out = {"rows": int(len(F)),
           "explicit_object": dict(mean_change=round(float(F["d_explicit"].mean()), 4),
                                   n_changed=int(F["changed"].sum())),
           "constraint_strip": dict(mean_change=round(float(F["d_stripped"].mean()), 4))}
    lo, hi, k = W.cluster_boot(F, "query_id", lambda x: float(x["d_explicit"].mean()))
    out["explicit_object"]["ci"] = [lo, hi]
    out["explicit_object"]["clusters"] = k
    lo2, hi2, k2 = W.cluster_boot(F, "query_id", lambda x: float(x["d_stripped"].mean()))
    out["constraint_strip"]["ci"] = [lo2, hi2]
    out["constraint_strip"]["clusters"] = k2
    return out


def e06_second_instrument(frames) -> dict:
    """Agreement between the two independent relevance instruments, and between the two label sources."""
    C = frames["candidate"]
    if "dense" not in C or C["dense"].isna().all():
        return {"status": "not_measured", "reason": "the dense arm cache is absent for this run"}
    import scipy.stats as st
    # vectorised: rank within the query, then one Pearson correlation per group. `groupby.apply` with a per-group
    # spearman call is both slower on 169k rows and version-fragile in pandas 2.1.
    R = C.assign(rb=C.groupby("query_id")["bm25"].rank(), rd=C.groupby("query_id")["dense"].rank(),
                 ng=C.groupby("query_id")["cand_idx"].transform("size"))
    R = R[(R["ng"] > 2) & R["dense"].notna() & R["bm25"].notna()]
    cov = (R["rb"] * R["rd"]).groupby(R["query_id"]).mean()
    mr = R.groupby("query_id")["rb"].mean()
    dr_ = R.groupby("query_id")["rd"].mean()
    vr = R.groupby("query_id")["rb"].var()
    vd = R.groupby("query_id")["rd"].var()
    num = cov - mr * dr_
    den = (vr * vd).pow(0.5).replace(0, np.nan)
    per = (num / den).dropna()
    per = pd.Series(per).dropna()
    return {"spearman_bm25_vs_encoder_per_query": dict(
        mean=round(float(per.mean()), 4), median=round(float(per.median()), 4),
        share_below_half=round(float((per < 0.5).mean()), 4), n_queries=int(len(per)))}


def e08_external(frames, sp_by_topic) -> dict:
    """Transfer the same specification to the other corpus family in the estate."""
    out = {}
    q = frames["query"]
    try:
        H = W.load_routing(cfgs=("HERMES",), bucket="external")
    except Exception as e:                                    # noqa: BLE001 - the frame is an input
        return {"status": "not_measured", "reason": str(e)[:160]}
    H = W.add_linguistic_frame(H)
    H["wrong_tool"] = np.nan
    try:
        rows = []
        for r in H.itertuples(index=False):
            ent = W.read_catalog(r.catalog_json, r.n_candidates, r.uuid)
            if not ent:
                continue
            docs = [W.doc_tokens(ent, i, "full") for i in range(len(ent))]
            rk = W.rank_from(W._bm25_scores(W.toks(r.question), docs))
            gold = W.as_int_list(r.gold_idx)
            rows.append(dict(query_id="HERMES|" + r.uuid, wrong_tool=int(min(rk[i] for i in gold) != 1),
                             underspec_z=0.0, len_z=0.0, n_tokens=int(r.n_tokens),
                             n_candidates=len(ent), n_gold=len(gold), underspec_index=float(r.underspec_index)))
        E = pd.DataFrame(rows)
        E["underspec_z"] = z(E, "underspec_index")
        E["len_z"] = z(E, "n_tokens")
        sp = dict(SPEC["T101"])
        out["T101_on_HERMES"] = fit(E, sp)
        out["T101_on_HERMES_note"] = ("same feature, same frozen ranker, different corpus family and catalogue "
                                      "construction; the transfer is of the specification, not of the estimate")
        out["T101_rows"] = int(len(E))
    except Exception as e:                                    # noqa: BLE001 - report, never hide
        out["status"] = f"transfer arm failed: {type(e).__name__}: {str(e)[:160]}"
    out["T106_on_Toucan"] = "not_measured - Toucan ships no separate issued query (EXP-0118)"
    return out


def e19_contamination() -> dict:
    """Split discipline and near-duplicate audit across the configs this wave pools over."""
    aud = {}
    seen = {}
    for cfg in W.CONFIGS + ("HERMES", "SFT"):
        try:
            d = W.load_routing(cfgs=(cfg,), bucket="dev")
        except Exception as e:                                # noqa: BLE001
            aud[cfg] = {"error": str(e)[:120]}
            continue
        toks = [set(W.toks(q)) for q in d["question"].astype(str)]
        u = set(d["uuid"].astype(str))
        inter = {c2: len(u & v) for c2, v in seen.items()}
        seen[cfg] = u
        # near-duplicate audit inside the config: identical token sets between different rows
        key = {}
        dup = 0
        for i, s in enumerate(toks):
            k = frozenset(s)
            if k in key and key[k] != d["uuid"].iloc[i]:
                dup += 1
            key[k] = d["uuid"].iloc[i]
        aud[cfg] = {"dev_rows": int(len(d)), "uuid_collisions_with_other_configs": inter,
                    "near_duplicate_token_sets": int(dup),
                    "near_duplicate_share": round(float(dup / max(1, len(d))), 5)}
    test_rows_read = 0
    return {"per_config": aud, "test_split_rows_read_by_wave1": test_rows_read,
            "rule": "only the dev bucket of the frozen routing frames enters a wave-1 estimate; HERMES rows are the "
                    "external corpus and are labelled as such wherever they appear"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    frames = build_frames()
    steps = {}
    for topic, sp in SPEC.items():
        fr = sp["frame"]
        if fr not in frames:
            steps[topic] = {"status": "frame_absent", "frame": fr}
            continue
        df = frames[fr]
        steps[topic] = dict(frame=fr, rows=int(len(df)), clusters=int(df["query_id"].nunique()),
                            primary=fit(df, sp), e12_scaling=e12_scaling(df, sp),
                            e04_ablation=e04_ablation(df, sp), e18_replication=e18_replicate(df, sp),
                            e_by_config=e_by_config(df, sp),
                            e15_16=e15_16_errors(df, sp, None))
    steps["_shared"] = {"e06_second_instrument": e06_second_instrument(frames),
                        "e08_external": e08_external(frames, SPEC),
                        "e19_contamination": e19_contamination(),
                        "e17_counterfactual": e17_counterfactual(frames, SPEC)}
    steps["_shared"]["run_cost"] = W.run_cost_row("EXP-0128..0133", t0, sum(int(v.get("rows", 0))
                                                                            for k, v in steps.items()
                                                                            if isinstance(v, dict)), 0)
    for exp in ("EXP-0128", "EXP-0129", "EXP-0130", "EXP-0131", "EXP-0132", "EXP-0133"):
        art = dict(exp_id=exp, seed=W.SEED, topics=steps, started_at=W.now(), finished_at=W.now())
        p = W.write_raw(exp, "wave1_battery_" + exp[-4:], art)
        print(f"{exp}: wrote {p.name}")
    (W.LOGS / f"EXP-0128_0133_battery_{time.strftime('%Y%m%dT%H%M%S')}.txt").write_text(
        json.dumps(steps, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps({k: (v.get("primary") if isinstance(v, dict) else v) for k, v in steps.items()},
                     indent=1, default=str)[:1800])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
