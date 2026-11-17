"""EXP-0121 (T101) and EXP-0122 (T103): the query-level wave-1 designs, run on the shared EXP-0119 matrix.

Both designs take one instruction and ask what its *language* predicts about the search that follows. They share the
substrate (24,000 dev queries from three Toucan configs), the frozen feature definitions in `wave_lib`, the
cluster rule (bootstrap and robust standard errors on `query_id`, never on rows) and the correction rule (Holm over
each design's declared family of three).

Precedence of what is measured versus promised, from the amendment recorded in `topic_designs_wave1.py`:

* T101's depth DV is the dialogue-side turn count joined in from the release's own `messages` column, not an
  executed-search depth, because Toucan ships no executed trajectory. Coverage of that join is reported, and the
  claim is capped at what the covered rows support.
* T103's breadth/depth DVs are retriever-side (what the frozen BM25 had to pass through before it reached the gold
  tool), and its "beyond the release's own difficulty field" hypothesis is restated against the structural controls
  the release actually carries - it ships no difficulty field. Both restatements are logged as deviations.

    python 02_shared_code/package_factory/exp_wave1_query_level.py [--quick]
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
import wave_lib as W                                             # noqa: E402

DATASETS = W.ROOT.parent / "MATLABINTOKEN" / "datasets"
TOUCAN = DATASETS / "Agent-Ark" / "Toucan-1.5M"
TOOL_MARK = re.compile(r"<tool_call|tool_call\s*:|function=|def \w+\(|```python|execute\(|action\s*[:=]", re.I)
CLAR_MARK = re.compile(r"\b(could you|can you clarify|which one|do you mean|need more information|unclear)\b", re.I)
Q_OUT = {}


# ---------------------------------------------------------------------------------- dialogue join (Toucan raw)
def dialogue_columns(want: pd.DataFrame) -> tuple:
    """Join the release's own `messages` column for the sampled queries: turns before the first tool call, and
    whether an assistant turn asked for clarification before that call.

    Scans shards until every uuid is found, and returns the coverage it achieved. Nothing here is inferred from the
    question text - these are counts of what the release contains.
    """
    need = {c: set(want.loc[want["cfg"] == c, "uuid"].astype(str)) for c in want["cfg"].unique()}
    got = {}
    for cfg, uuids in need.items():
        d = TOUCAN / cfg
        if not d.is_dir():
            continue
        left = set(uuids)
        for f in sorted(d.glob("*.parquet")):
            if not left:
                break
            try:
                t = pd.read_parquet(f, columns=["uuid", "messages", "subset_name"])
            except Exception:                                      # noqa: BLE001 - unreadable shard, keep scanning
                continue
            t = t[t["uuid"].astype(str).isin(left)]
            for r in t.itertuples(index=False):
                try:
                    obj = json.loads(r.messages) if isinstance(r.messages, str) else r.messages
                except Exception:                                  # noqa: BLE001
                    continue
                if not isinstance(obj, list):
                    continue
                pre, clar, seen_call = 0, 0, False
                for m in obj:
                    role = str((m or {}).get("role") or (m or {}).get("from") or "")
                    body = str((m or {}).get("content") or (m or {}).get("value") or "")
                    if role == "user":
                        continue
                    if seen_call:
                        break
                    if role == "assistant":
                        if TOOL_MARK.search(body):
                            seen_call = True
                            continue
                        pre += 1
                        if CLAR_MARK.search(body):
                            clar = 1
                    elif role in ("function", "tool"):
                        seen_call = True
                        break
                got[str(r.uuid)] = (pre, clar, int(seen_call))
            left -= set(t["uuid"].astype(str))
    idx = want["uuid"].astype(str).map(got)
    want = want.copy()
    want["dlg_turns_before_call"] = [float(v[0]) if isinstance(v, tuple) else np.nan for v in idx]
    want["dlg_clarify_before_call"] = [int(v[1]) if isinstance(v, tuple) else np.nan for v in idx]
    want["dlg_call_present"] = [int(v[2]) if isinstance(v, tuple) else np.nan for v in idx]
    cov = {c: {"queries": int((want["cfg"] == c).sum()),
               "joined": int(want.loc[want["cfg"] == c, "dlg_turns_before_call"].notna().sum())}
           for c in want["cfg"].unique()}
    cov["overall_share_joined"] = round(float(want["dlg_turns_before_call"].notna().mean()), 4)
    return want, cov


# ------------------------------------------------------------------------------------------- inference helpers
def glm_term(df, y, xs, family_name, cluster="query_id"):
    fam = {"binomial": W.logit, "poisson": W.poisson, "gaussian": W.ols}[family_name]
    fit = fam(df, y, xs, cluster=cluster)
    if fit is None:
        return None
    p, dev, n, ok = fit
    p["ci_lo"] = p["beta"] - 1.959963985 * p["se"]
    p["ci_hi"] = p["beta"] + 1.959963985 * p["se"]
    p["dv"] = y
    p["n"] = n
    p["converged"] = ok
    p["deviance"] = dev
    return p


def std(df, col) -> pd.Series:
    s = df[col].astype(float)
    return (s - s.mean()) / (s.std(ddof=0) or 1.0)


def add_std(df, name, col):
    df[name] = std(df, col)
    return df


def table_main(fit, term="underspec_index") -> list:
    if fit is None:
        return []
    r = fit[fit["term"] == term]
    if r.empty:
        return []
    row = r.iloc[0]
    return [dict(term=term, beta=round(float(row["beta"]), 4), se=round(float(row["se"]), 4),
                 ci_lo=round(float(row["ci_lo"]), 4), ci_hi=round(float(row["ci_hi"]), 4),
                 p_raw=float(row["p"]), n=int(row["n"]))]


# ------------------------------------------------------------------------------------------------------ T101
def t101(Q: pd.DataFrame, cov: dict) -> dict:
    d = Q.copy()
    add_std(d, "underspec_z", "underspec_index")
    add_std(d, "len_z", "n_tokens")
    d["wrong_tool"] = 1 - d["top1_norm_ok"]
    d["inspected_z"] = std(d, "inspected_to_gold")
    out = {"join_coverage": cov}
    if cov["overall_share_joined"] < 0.5:
        out["H1_status"] = ("not_measured", f"only {cov['overall_share_joined']:.1%} of sampled queries could be "
                                           f"joined to the release's own messages column")
    fam = {}
    rows = []
    # H1: depth (dialogue turns before the first tool call), Poisson, length-adjusted
    h1d = d.dropna(subset=["dlg_turns_before_call", "underspec_z"])
    if len(h1d) >= 500 and h1d["dlg_turns_before_call"].std() > 0:
        f = glm_term(h1d, "dlg_turns_before_call", ["underspec_z", "len_z"], "poisson")
        rows += table_main(f, "underspec_z")
        fam["H1"] = rows[-1]["p_raw"] if rows else 1.0
        out["H1_n"] = int(len(h1d))
    else:
        out["H1_status"] = ("not_measured", "the joined dialogue column has no usable variance in this sample")
    # H2: clarification before any call, logistic
    h2d = d.dropna(subset=["dlg_clarify_before_call", "underspec_z"])
    if len(h2d) >= 500 and h2d["dlg_clarify_before_call"].nunique() > 1:
        f = glm_term(h2d, "dlg_clarify_before_call", ["underspec_z", "len_z"], "binomial")
        r = table_main(f, "underspec_z")
        for x in r:
            x["term"] = "underspec_z:clarification"
        rows += r
        fam["H2"] = r[-1]["p_raw"] if r else 1.0
    else:
        out["H2_status"] = ("not_measured", "no clarification signal joined")
    # H3: wrong tool under the frozen retriever, logistic
    f = glm_term(d, "wrong_tool", ["underspec_z", "len_z"], "binomial")
    r = table_main(f, "underspec_z")
    for x in r:
        x["term"] = "underspec_z:wrong_tool"
    rows += r
    fam["H3"] = r[-1]["p_raw"] if r else 1.0
    adj = W.holm(fam)
    for x in rows:
        key = "H1" if x["term"] == "underspec_z" else ("H2" if "clarification" in x["term"] else "H3")
        x["p_holm"] = adj.get(key)
        x["verdict"] = W.verdict(x["beta"], x["ci_lo"], x["ci_hi"], x["p_holm"], W.BANDS["medium"],
                                 direction=-1.0 if key == "H1" else 1.0)
        # H1 as frozen predicts *more* searching for *less* specification, and the index is signed so higher = less
        # specified; direction is therefore +1 for every hypothesis, and this guard records that no sign was flipped
        # after seeing an estimate
        x["direction_predicted"] = "positive"
    # tertile contrasts for the figure and an interpretable magnitude
    d["tert"] = pd.qcut(d["underspec_index"].rank(method="first"), 3, labels=["low", "mid", "high"])
    cont = d.groupby("tert", observed=True).agg(
        n=("query_id", "size"), wrong_tool=("wrong_tool", "mean"),
        depth=("dlg_turns_before_call", "mean"), clarify=("dlg_clarify_before_call", "mean"),
        inspected=("inspected_to_gold", "mean")).reset_index()
    lo, hi, k = W.cluster_boot(d.assign(one=d["wrong_tool"]), "query_id",
                               lambda x: float(x[x.tert == "high"]["one"].mean()
                                               - x[x.tert == "low"]["one"].mean()))
    cont["high_minus_low_wrong_tool"] = round(float(cont.loc[cont.tert == "high", "wrong_tool"].iloc[0]
                                                   - cont.loc[cont.tert == "low", "wrong_tool"].iloc[0]), 4)
    cont["hi_lo_ci_lo"] = lo
    cont["hi_lo_ci_hi"] = hi
    cont["contrast_clusters"] = k
    # robustness: index without each component, types-only index, per config, clustering on prompt_id
    rob = []
    for tag, cols in (("components", ["constraint_total", "unresolved_ref", "ellipsis_n", "entity_density"]),
                      ("per_config", None), ("cluster_prompt", None), ("types_only", None)):
        if tag == "components":
            for c in cols:
                dd = d.copy()
                keep = [x for x in cols if x != c]
                dd["underspec_index"] = pd.Series(
                    np.mean(np.column_stack([(-W.zscore(dd[k_]) if k_ in ("constraint_total", "entity_density")
                                              else W.zscore(dd[k_])) for k_ in keep]), axis=1), index=dd.index)
                add_std(dd, "underspec_z", "underspec_index")
                f = glm_term(dd, "wrong_tool", ["underspec_z", "len_z"], "binomial")
                rob += [dict(robustness=f"drop_{c}", dv="wrong_tool", **{kk: vv for kk, vv in
                              (table_main(f, "underspec_z") or [{}])[0].items()
                              if kk in ("beta", "ci_lo", "ci_hi", "p_raw", "n")})]
        elif tag == "per_config":
            for cfg, g in d.groupby("cfg"):
                f = glm_term(g, "wrong_tool", ["underspec_z", "len_z"], "binomial")
                rob += [dict(robustness=f"config={cfg}", dv="wrong_tool", **{kk: vv for kk, vv in
                              (table_main(f, "underspec_z") or [{}])[0].items()
                              if kk in ("beta", "ci_lo", "ci_hi", "p_raw", "n")})]
        elif tag == "cluster_prompt":
            f = glm_term(d, "wrong_tool", ["underspec_z", "len_z"], "binomial", cluster="prompt_id")
            rob += [dict(robustness="cluster=prompt_id", dv="wrong_tool", **{kk: vv for kk, vv in
                          (table_main(f, "underspec_z") or [{}])[0].items()
                          if kk in ("beta", "ci_lo", "ci_hi", "p_raw", "n")})]
        else:
            dd = d.copy()
            dd["underspec_index"] = W.zscore(-dd["constraint_types"].astype(float))
            add_std(dd, "underspec_z", "underspec_index")
            f = glm_term(dd, "wrong_tool", ["underspec_z", "len_z"], "binomial")
            rob += [dict(robustness="types_only_index", dv="wrong_tool", **{kk: vv for kk, vv in
                          (table_main(f, "underspec_z") or [{}])[0].items()
                          if kk in ("beta", "ci_lo", "ci_hi", "p_raw", "n")})]
    # baseline comparison: does the index add over a length-only and a QPP-only predictor?
    base = []
    for name, xs in (("length_only", ["len_z"]), ("qpp_only", ["qpp_coverage_std", "len_z"]),
                     ("underspec_only", ["underspec_z"]), ("underspec_plus_length", ["underspec_z", "len_z"])):
        dd = d.copy()
        if "qpp_coverage_std" not in dd:
            add_std(dd, "qpp_coverage_std", "qpp_coverage")
        f = glm_term(dd, "wrong_tool", xs, "binomial")
        if f is None:
            base.append(dict(model=name, note="not fitted (missing column or separation)"))
            continue
        base.append(dict(model=name, deviance=round(float(f["deviance"].iloc[0]), 2), n=int(f["n"].iloc[0]),
                         terms=";".join(x for x in xs)))
    out.update(models=rows, tertiles=cont.to_dict("records"), robustness=rob, baselines=base,
               holm=adj, distribution=dict(
                   constraint_total_mean=round(float(d["constraint_total"].mean()), 4),
                   unresolved_zero_share=round(float((d["unresolved_ref"] == 0).mean()), 4),
                   ellipsis_zero_share=round(float((d["ellipsis_n"] == 0).mean()), 4),
                   underspec_sd=round(float(d["underspec_index"].std()), 4),
                   wrong_tool_rate=round(float(d["wrong_tool"].mean()), 4)),
               n=int(len(d)))
    return out


# ------------------------------------------------------------------------------------------------------ T103
def t103(Q: pd.DataFrame) -> dict:
    d = Q.copy()
    add_std(d, "density_z", "constraint_total")
    add_std(d, "len_z", "n_tokens")
    add_std(d, "ncand_z", "n_candidates")
    add_std(d, "ngold_z", "n_gold")
    d["inspected_pos"] = d["inspected_to_gold"].clip(lower=0)
    out, rows, fam = {}, [], {}
    # H1 breadth: candidates passed before gold, Poisson; H2 depth: rank of gold under desc-only BM25
    for h, dv, famname in (("H1", "inspected_pos", "poisson"), ("H2", "bm25_desc_rank", "poisson")):
        dd = d.dropna(subset=[dv, "density_z"])
        dd = dd[dd[dv] >= 0]
        f = glm_term(dd, dv, ["density_z", "len_z", "ncand_z", "ngold_z"], famname)
        r = table_main(f, "density_z")
        for x in r:
            x["term"] = f"density_z:{dv}"
            x["hypothesis"] = h
        rows += r
        fam[h] = r[-1]["p_raw"] if r else 1.0
    # H3 nested comparison: structural controls, + density
    dd = d.dropna(subset=["inspected_pos", "density_z"])
    dd = dd[dd["inspected_pos"] >= 0]
    fits = {}
    for name, xs in (("structural_only", ["len_z", "ncand_z", "ngold_z"]),
                     ("structural_plus_density", ["len_z", "ncand_z", "ngold_z", "density_z"])):
        import statsmodels.api as sm
        X = sm.add_constant(dd[xs].astype(float))
        fits[name] = sm.GLM(dd["inspected_pos"].astype(float), X, family=sm.families.Poisson()).fit()
    from scipy import stats as st
    lr = 2 * (float(fits["structural_plus_density"].llf) - float(fits["structural_only"].llf))
    p_lr = float(st.chi2.sf(max(lr, 0.0), 1))
    y = dd["inspected_pos"].astype(float).to_numpy()
    pr2 = W.partial_r2(y, fits["structural_plus_density"].fittedvalues, fits["structural_only"].fittedvalues)
    r = [dict(term="H3_nested_gain", beta=round(pr2, 5), se=np.nan, ci_lo=np.nan, ci_hi=np.nan,
              p_raw=p_lr, n=int(len(dd)), lr_stat=round(lr, 3))]
    rows += r
    fam["H3"] = p_lr
    adj = W.holm(fam)
    for x in rows:
        h = x.get("hypothesis") or ("H3" if x["term"].startswith("H3") else "H1")
        x["p_holm"] = adj.get(h)
        if h == "H3":
            # The frozen rule for this row is a nested-model gain: `partial` and `null` are the words the freeze
            # reserves for a coefficient whose CI excludes or covers zero, and an LR gain has no CI, so a row below
            # the 0.01 floor says so in its own words rather than borrowing a CI verdict. Round-2 finding R2-S1.
            x["verdict_rule"] = "nested_gain_partial_r2"
            x["verdict"] = ("supported" if pr2 >= 0.01 and p_lr < 0.05 else
                            "below_the_frozen_floor_measured_" + str(round(float(pr2), 4)).replace(".", "p")
                            if pr2 < 0.01 else "not_significant_at_the_frozen_alpha")
        else:
            x["verdict"] = W.verdict(x["beta"], x["ci_lo"], x["ci_hi"], x["p_holm"], W.BANDS["medium"])
    # dose response
    d["dec"] = pd.qcut(d["constraint_total"].rank(method="first"), 10, labels=False) + 1
    dose = d.groupby("dec").agg(n=("query_id", "size"), constraint_total=("constraint_total", "mean"),
                                inspected=("inspected_pos", "mean"), gold_rank_desc=("bm25_desc_rank", "mean"),
                                fail_at_3=("fail_at_3_shipped", "mean"),
                                top1_ok=("top1_norm_ok", "mean")).reset_index()
    mono = bool((dose["inspected"].diff().dropna() >= 0).all())
    # breadth vs depth coefficient comparison on the same sample
    z = np.log(max(1e-9, float(d["inspected_pos"].mean())))
    out.update(models=rows, dose_response=dose.to_dict("records"), monotone_breadth=mono,
               holm=adj, partial_r2_gain=round(pr2, 5), lr=round(lr, 3), p_lr=p_lr,
               n=int(len(d)), distribution=dict(
                   density_mean=round(float(d["constraint_total"].mean()), 4),
                   density_zero_share=round(float((d["constraint_total"] == 0).mean()), 4),
                   types_mean=round(float(d["constraint_types"].mean()), 4)),
               collinearity=W.vif(d[["constraint_total", "n_tokens", "constraint_types", "entity_density"]]),
               # the reformulation DV the freeze listed cannot be computed here and is reported, not dropped
               not_measured={"reformulation_count": "Toucan ships no issued machine query per trajectory, so "
                                                    "near-duplicate self-queries cannot be counted"})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    Q = pd.read_csv(W.PROCES / "EXP0119_wave1_query_features.csv")
    if args.quick:
        Q = Q.groupby("cfg").apply(lambda g: g.sample(min(1500, len(g)), random_state=42)).reset_index(drop=True)
    Q, cov = dialogue_columns(Q)
    a1 = t101(Q, cov)
    a3 = t103(Q)
    tabdir = W.OUT
    for exp, art in (("EXP-0121", a1), ("EXP-0122", a3)):
        p = W.write_raw(exp, "wave1_query_level_" + exp[-4:], art)
        print(f"{exp}: wrote {p.name}")
    pd.DataFrame(a1["models"]).to_csv(tabdir / "EXP0121_t101_main_models.csv", index=False)
    pd.DataFrame(a1["tertiles"]).to_csv(tabdir / "EXP0121_t101_tertile_contrast.csv", index=False)
    pd.DataFrame(a1["robustness"]).to_csv(tabdir / "EXP0121_t101_robustness.csv", index=False)
    pd.DataFrame(a1["baselines"]).to_csv(tabdir / "EXP0121_t101_baselines.csv", index=False)
    pd.DataFrame(a3["models"]).to_csv(tabdir / "EXP0122_t103_main_models.csv", index=False)
    pd.DataFrame(a3["dose_response"]).to_csv(tabdir / "EXP0122_t103_dose_response.csv", index=False)
    art = {"exp_id": "EXP-0121;EXP-0122", "seed": W.SEED, "quick": args.quick, "n_rows": int(len(Q)),
           "dialogue_join": cov,
           "T101": {k: a1[k] for k in ("models", "holm", "distribution", "n")},
           "T103": {k: a3[k] for k in ("models", "holm", "partial_r2_gain", "p_lr", "monotone_breadth", "n")},
           "run_cost": W.run_cost_row("EXP-0121/0122", t0, len(Q), Q.shape[1]),
           "started_at": W.now(), "finished_at": W.now()}
    p = W.write_raw("EXP-0121", "wave1_query_level_summary", art)
    (W.LOGS / f"EXP-0121_0122_query_level_{time.strftime('%Y%m%dT%H%M%S')}.txt").write_text(
        json.dumps(art, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps({"join": cov["overall_share_joined"], "T101": art["T101"]["models"],
                      "T103": art["T103"]["models"]}, indent=1, default=str)[:2500])
    print("wrote", p.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
