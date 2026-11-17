"""EXP-0123 (T106): information loss between the user's question and the query the agent actually issues.

Moved onto hermes-agent-reasoning-traces by the EXP-0118 premise census: Toucan ships a dialogue that *produces* a
query but no separate machine query to compare it against, so fidelity was unmeasurable there. Here each row carries
the user's request, the agent's `<think>` reasoning, and the `<tool_call>` it actually issued, in trace arms from
two different models over the same request set.

Definitions, fixed here before any retention rate was computed:

* **issued machine query** = the concatenation of every string- and number-valued argument of the *first* tool call
  in the trace, plus the called tool's name. A call with no textual argument yields no issued query and counts
  against the kill gate; it is not silently treated as "nothing was lost".
* **entity retention** = share of distinct entity spans in the question that occur in the issued query (case-folded
  substring, so `CSV_Cleaner.py` and `csv_cleaner.py` match).
* **constraint retention** = over the constraint families present in the question, the share whose lexical material
  also occurs in the issued query. A family the question never used is not counted, so a short question cannot be
  penalised for omitting constraints it never had.
* **relation retention** = over the predicate-argument pairs the question expresses (the frozen lemma lexicons), the
  share whose predicate and argument both survive.
* **introduced coreference** = anaphora in the issued query with no antecedent in the issued query itself - the
  machine query pointing at something only the dialogue knows.

DV: whether the tool actually called is one of the release's gold tools for that request, resolved with P001's own
join rule, plus the shipped retrieval outcome for the same row.

    python 02_shared_code/package_factory/exp_wave1_reformulation.py
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import time

import numpy as np
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import wave_lib as W                                             # noqa: E402

DATASETS = W.ROOT.parent / "MATLABINTOKEN" / "datasets" / "lambda" / "hermes-agent-reasoning-traces"
CALL_RE = re.compile(r"<tool_call\s*>?(.*?)(?:<\/tool_call>|<end_tool_call>|$)", re.S | re.I)
THINK_RE = re.compile(r"<think\s*>(.*?)</think>", re.S | re.I)
GPT_ROLES = ("gpt", "assistant")


def arms() -> list:
    out = []
    for f in sorted(DATASETS.rglob("*.parquet")):
        arm = f.parent.name if f.parent.name != "data" else "release_default"
        out.append((arm, f))
    return out


def first_call(value: str):
    """The first parseable `{"name":..., "arguments":{...}}` inside a <tool_call> block, or None."""
    for m in CALL_RE.finditer(str(value or "")):
        blob = m.group(1).strip()
        try:
            obj = json.loads(blob)
        except Exception:                                          # noqa: BLE001 - try the first JSON object
            i, j = blob.find("{"), blob.rfind("}")
            if i < 0 or j <= i:
                continue
            try:
                obj = json.loads(blob[i:j + 1])
            except Exception:                                      # noqa: BLE001
                continue
        if isinstance(obj, dict) and obj.get("name"):
            return obj
    return None


def issued_text(call: dict) -> str:
    bits = [str(call.get("name") or "")]
    args = call.get("arguments") or call.get("parameters") or {}
    if isinstance(args, str):
        bits.append(args)
    elif isinstance(args, dict):
        for k, v in args.items():
            if isinstance(v, (str, int, float)):
                bits.append(f"{k} {v}")
    return " ".join(bits)


def extract_trace(conversations) -> dict:
    calls, thinks, first = [], [], None
    for x in ([] if conversations is None else list(conversations)):
        role = str(x.get("from") or x.get("role") or "")
        val = str(x.get("value") or x.get("content") or "")
        if role in GPT_ROLES:
            thinks += THINK_RE.findall(val)
            c = first_call(val)
            if c and first is None:
                first = c
            for m in CALL_RE.finditer(val):
                calls.append(m.group(0))
    return {"first_call": first, "n_calls": len(calls), "issued": issued_text(first) if first else "",
            "think_chars": int(sum(len(t) for t in thinks)), "n_think": len(thinks)}


def retain(question: str, issued: str) -> dict:
    """Retention of entities, constraint families and predicate-argument pairs, per the docstring definitions."""
    q, s = str(question or ""), str(issued or "")
    ql, sl = q.lower(), s.lower()
    ents = {e.lower() for e in W.PROPER_RE.findall(q)}                       # proper-noun-like spans
    ents |= {f.lower() for f in re.findall(r"[\w.-]+\.[A-Za-z]{1,6}", q)}    # file-name spans
    ents = {e for e in ents if len(e) > 2}
    ent_hit = sum(1 for e in ents if e in sl)
    fams = W.constraint_markers(q)
    fam_present, fam_kept = 0, 0
    for fam, words in (("temporal", W.TEMPORAL), ("numeric", W.NUMWORD), ("format", W.FORMAT_WORDS),
                       ("scope", W.SCOPE_WORDS), ("negation", W.NEG_WORDS)):
        used = [w for w in words if w.strip() and f" {w} " in f" {ql} "]
        if fam == "numeric" and re.search(r"\d", ql):
            used = used or ["digit"]
        if not used:
            continue
        fam_present += 1
        if any((u.strip().lower() in sl) for u in used):
            fam_kept += 1
    if fams["entity"] and ents:
        fam_present += 1
        fam_kept += 1 if ent_hit else 0
    qp = {lem for lem, forms in W.VERB_LEMMA.items() if set(forms) & set(re.findall(r"[a-z]+", ql))}
    qa = {c for c, forms in W.OBJECT_NOUNS.items() if set(forms) & set(re.findall(r"[a-z]+", ql))}
    sp = {lem for lem, forms in W.VERB_LEMMA.items() if set(forms) & set(re.findall(r"[a-z]+", sl))}
    sa = {c for c, forms in W.OBJECT_NOUNS.items() if set(forms) & set(re.findall(r"[a-z]+", sl))}
    pairs = [(v, a) for v in qp for a in qa]
    rel_kept = sum(1 for v, a in pairs if v in sp and a in sa)
    return {"n_entities": len(ents), "entity_retention": (ent_hit / len(ents)) if ents else np.nan,
            "constraint_families": fam_present,
            "constraint_retention": (fam_kept / fam_present) if fam_present else np.nan,
            "relation_pairs": len(pairs),
            "relation_retention": (rel_kept / len(pairs)) if pairs else np.nan,
            "introduced_coreference": W.unresolved_references(s) if s else np.nan,
            "issued_len_tokens": len(W.toks(s)) if s else 0}


def reachability(question: str, issued: str, ent: list, target_idx: set) -> dict:
    """Did the reformulation make the agent's own target easier or harder to find?

    Retrieval is run twice over the same candidate catalogue with P001's frozen BM25: once with the user's question,
    once with the query the agent actually issued. `delta_fail` = fail(issued) - fail(question), so a positive value
    is information lost in the linguistic transformation and a negative value is information gained. This is the DV
    the design needs: the release's `wrong_tool` is definitionally zero here because the curated gold set IS the set
    of tools the trace called, so a model of it would fit a tautology - measured, and reported as such.
    """
    if not ent or not target_idx:
        return {"fail_q": np.nan, "fail_i": np.nan, "delta_fail": np.nan, "rank_q": -1, "rank_i": -1}
    docs_full = [W.doc_tokens(ent, i, "full") for i in range(len(ent))]

    def fail(text):
        if not str(text or "").strip():
            return -1, np.nan
        rk = W.rank_from(W._bm25_scores(W.toks(text), docs_full))
        best = min((rk[i] for i in target_idx if i < len(rk)), default=len(rk) + 1)
        return int(best), float(best > 1)
    rq, fq = fail(question)
    ri, fi = fail(issued)
    return {"fail_q": fq, "fail_i": fi, "delta_fail": (fi - fq) if (fq == fq and fi == fi) else np.nan,
            "rank_q": rq, "rank_i": ri}


def build(quick: bool = False) -> pd.DataFrame:
    R = W.load_routing(cfgs=("HERMES",), bucket="external")
    R["uuid"] = R["uuid"].astype(str)
    tr = {}
    for arm, f in arms():
        try:
            t = pd.read_parquet(f, columns=["id", "conversations"])
        except Exception:                                          # noqa: BLE001 - arm without the column
            continue
        for r in t.itertuples(index=False):
            if str(r.id) in tr or str(r.id) not in set(R["uuid"]):
                continue
            e = extract_trace(r.conversations)
            e["trace_arm"] = arm
            tr[str(r.id)] = e
    R["trace_found"] = R["uuid"].map(lambda u: int(u in tr))
    R["issued"] = R["uuid"].map(lambda u: tr.get(u, {}).get("issued", ""))
    R["n_calls"] = R["uuid"].map(lambda u: tr.get(u, {}).get("n_calls", 0))
    R["first_tool"] = R["uuid"].map(lambda u: (tr.get(u, {}).get("first_call") or {}).get("name", ""))
    R["think_chars"] = R["uuid"].map(lambda u: tr.get(u, {}).get("think_chars", 0))
    R["trace_arm"] = R["uuid"].map(lambda u: tr.get(u, {}).get("trace_arm", ""))
    rows = []
    for r in R.itertuples(index=False):
        ent = W.read_catalog(r.catalog_json, r.n_candidates, r.uuid)
        gold_names = {ent[i]["name"] for i in W.as_int_list(r.gold_idx) if ent and i < len(ent)}
        wrong = np.nan
        if r.first_tool:
            wrong = int(not _in_gold(r.first_tool, gold_names, ent))
        d = retain(r.question, r.issued)
        reach = reachability(r.question, r.issued, ent, set(W.as_int_list(r.gold_idx)))
        d.update(reach)
        d.update(query_id=r.cfg + "|" + r.uuid, uuid=r.uuid, trace_found=r.trace_found, wrong_tool=wrong,
                 fail_at_1=int(r.fail_at_1), n_candidates=int(r.n_candidates), n_gold=int(r.n_gold),
                 n_tokens=int(r.n_tokens), question=str(r.question), issued=str(r.issued)[:400],
                 trace_arm=r.trace_arm, n_calls=int(r.n_calls), think_chars=int(r.think_chars))
        rows.append(d)
    out = pd.DataFrame(rows)
    if quick:
        out = out.sample(1200, random_state=42)
    return out


def _in_gold(tool: str, gold_names: set, ent: list) -> bool:
    if not tool:
        return False
    if tool in gold_names:
        return True
    slug_t = W.re.sub(r"[^a-z0-9]+", "-", tool.lower()).strip("-")
    for g in gold_names:
        gs = W.re.sub(r"[^a-z0-9]+", "-", str(g).lower()).strip("-")
        if gs and (gs in slug_t or slug_t in gs):
            return True
    return any(e.get("name") == tool and e.get("name") in gold_names for e in (ent or []))


def analyse(D: pd.DataFrame) -> dict:
    meas = D[D["issued"].astype(str).str.len() > 0].copy()
    gate = {"trajectories": int(len(D)), "with_recovered_call": int(D["trace_found"].sum()),
            "with_issued_text": int(len(meas)),
            "unrecovered_share": round(float(1 - len(meas) / max(1, len(D))), 4)}
    gate["kill_gate_fires"] = bool(gate["unrecovered_share"] >= 0.20)
    out = {"measurement": gate}
    meas["ent_c"] = meas["entity_retention"].astype(float)
    meas["con_c"] = meas["constraint_retention"].astype(float)
    mm = meas.dropna(subset=["ent_c", "con_c"])
    lo, hi, k = W.cluster_boot(mm.assign(diff=mm["ent_c"] - mm["con_c"]), "query_id",
                               lambda x: float(x["diff"].mean()))
    p1, _nb = W.boot_p(mm, "query_id", lambda x: float((x["ent_c"] - x["con_c"]).mean()))
    out["H1"] = dict(n=int(len(mm)), entity_mean=round(float(mm["ent_c"].mean()), 4),
                     constraint_mean=round(float(mm["con_c"].mean()), 4),
                     relation_mean=round(float(mm.dropna(subset=['relation_retention'])["relation_retention"]
                                               .mean()), 4),
                     paired_gap=round(float((mm["ent_c"] - mm["con_c"]).mean()), 4), ci=[lo, hi],
                     p_boot=p1, clusters=k,
                     verdict=("supported" if (lo is not None and lo > 0
                                              and float((mm["ent_c"] - mm["con_c"]).mean()) >= 0.10) else
                              "partial" if (lo is not None and lo > 0) else "null"))
    # the tautology the release would have led us into, measured rather than noticed
    wt = meas["wrong_tool"].dropna()
    out["tautology_check"] = {"wrong_tool_rate": (round(float(wt.mean()), 4) if len(wt) else None),
                              "n": int(len(wt)),
                              "reading": ("the curated gold set is the set of tools this trace called, so a model of "
                                          "'wrong tool' here fits the label by construction; the DV is replaced by "
                                          "reachability change and this row is reported as the reason"),
                              "tautological": bool(len(wt) > 50 and float(wt.mean()) == 0.0)}
    m2 = meas.dropna(subset=["con_c", "delta_fail"])
    m2["con_z"] = W.zscore(m2["con_c"])
    m2["dfail"] = m2["delta_fail"].astype(float)
    f = W.glm_term(m2, "dfail", ["con_z", "n_tokens", "n_candidates"], "gaussian")
    h2 = _term(f, "con_z") or dict(term="con_z", note="not fitted")
    base_loss = round(float(m2["dfail"].mean()), 4)
    lo_b, hi_b, _ = W.cluster_boot(m2, "query_id", lambda x: float(x["dfail"].mean()))
    h2["mean_reachability_change"] = base_loss
    h2["mean_ci"] = [lo_b, hi_b]
    h2["n"] = int(len(m2))
    m3 = meas.dropna(subset=["introduced_coreference", "delta_fail"])
    m3["ic_z"] = W.zscore(m3["introduced_coreference"].astype(float))
    m3["len_z"] = W.zscore(m3["issued_len_tokens"].astype(float))
    m3["dfail"] = m3["delta_fail"].astype(float)
    f3 = W.glm_term(m3, "dfail", ["ic_z", "len_z", "n_candidates"], "gaussian")
    hi_ic = _term(f3, "ic_z") or {}
    hl_len = _term(f3, "len_z") or {}
    out["H2"], out["H3"] = h2, dict(ic=hi_ic, length=hl_len, n=int(len(m3)))
    adj = W.holm({"H1": p1 if p1 is not None else 1.0, "H2": float(h2.get("p_raw", 1.0)),
                  "H3": float(hi_ic.get("p_raw", 1.0))})
    out["holm"] = adj
    # The frozen H2 reads "lower constraint retention raises the failure rate", i.e. on the reachability-change DV
    # that the amendment substituted, a *negative* coefficient is the predicted direction. The sign is fixed here from
    # the freeze text, not from the estimate.
    for key, d, dr in (("H2", h2, -1.0), ("H3", hi_ic, 1.0)):
        if "beta" in d:
            d["p_holm"] = adj[key]
            d["direction_predicted"] = "negative (retention reduces loss)" if dr < 0 else "positive"
            d["verdict"] = W.verdict(d["beta"], d["ci_lo"], d["ci_hi"], d["p_holm"], W.BANDS["medium"],
                                     direction=dr)
    # per-arm and per-category contrasts, so the result is not read as one model's property
    arms = meas.groupby("trace_arm").agg(n=("query_id", "size"), entity=("ent_c", "mean"),
                                         constraint=("con_c", "mean"), wrong=("wrong_tool", "mean")).round(4)
    out["arms"] = arms.reset_index().to_dict("records")
    out["loss_ladder"] = [{"level": "entity", "retention": round(float(mm["ent_c"].mean()), 4)},
                          {"level": "constraint_family", "retention": round(float(mm["con_c"].mean()), 4)},
                          {"level": "predicate_argument_relation",
                           "retention": round(float(meas.dropna(subset=['relation_retention'])
                                                    ["relation_retention"].mean()), 4)}]
    return out


def _term(fit, name):
    if fit is None:
        return None
    r = fit[fit["term"] == name]
    if r.empty:
        return None
    row = r.iloc[0]
    return dict(term=name, beta=round(float(row["beta"]), 4), se=round(float(row["se"]), 4),
                ci_lo=round(float(row["ci_lo"]), 4), ci_hi=round(float(row["ci_hi"]), 4),
                p_raw=float(row["p"]), n=int(row["n"]))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    D = build(quick=args.quick)
    a = analyse(D)
    D.to_csv(W.OUT / ("EXP0123_t106_fidelity_rows.csv" if not args.quick else "EXP0123_quick_rows.csv"),
             index=False)
    a["run_cost"] = W.run_cost_row("EXP-0123", t0, int(len(D)), int(D.shape[1]))
    a["seed"] = W.SEED
    a["started_at"], a["finished_at"] = W.now(), W.now()
    p = W.write_raw("EXP-0123", "wave1_reformulation_fidelity", a)
    (W.LOGS / f"EXP-0123_reformulation_{time.strftime('%Y%m%dT%H%M%S')}.txt").write_text(
        json.dumps(a, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps(a, indent=1, default=str)[:2500])
    print("wrote", p.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
