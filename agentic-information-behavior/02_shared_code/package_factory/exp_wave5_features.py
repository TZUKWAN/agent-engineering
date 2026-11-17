"""EXP-0164: wave 5's step frame - wave 4's turn spine plus the language-about-evidence columns wave 5 needs.

One row per assistant turn of >= 20 characters, on the same seeded, deduplicated trajectory sample the wave-4 matrix
used, joined to that matrix's own columns (`traj_id`, `turn_index`, `prior_inspections`, `prev_obs_error`,
`next_is_inspect`, `next_action_kind`, `category`, `turn_sha`) so a control or an outcome means the same thing in
both waves. What is added here is computed from the turn's own text and the observations that preceded it:

* five speech-act flags under two independently worded lexicons (T130's instrument-invariance pair);
* causal-connective counts, split into the inferential and explanatory families, a chain flag, and a
  no-inferential-content control lexicon (T134/T135);
* `evidence_overlap`, the share of the turn's content words that appear anywhere in the observations returned
  before it - the only mechanical reading of "the evidence says so" available without a model (T132/T134/T135);
* repair-family flags on the turn after a failure-marked observation (T133);
* plan-action alignment: the turn's content words against the next call's name and arguments, plus a seeded
  permutation of that statistic within trajectory-length bins (T136).

Every lexicon is in this file or in `topic_designs_wave5`, written before the frame was built; the self-test below
reads a hand-built trajectory and asserts the flags, so a marker that stopped matching is caught here rather than
showing up as a null coefficient six steps later.

    python 02_shared_code/package_factory/exp_wave5_features.py [--cap 20000]
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import pathlib
import re
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np                                              # noqa: E402
import pandas as pd                                             # noqa: E402
import wave_lib as W                                            # noqa: E402
import exp_wave4_features as EF                                 # noqa: E402
import probe_wave5_premises as P5                               # noqa: E402  (same lexicons as the census)

EXP = "EXP-0164"
TD5 = __import__("topic_designs_wave5")
PERM_DRAWS = 100                       # permutations per turn for T136's null, fixed here before any row was read
STOP = P5.STOP
BAD = collections.Counter()
CROSSCHECK = {}                        # shared column -> {rows_compared, agree, disagree}, filled at the join


def cwords(s: str) -> set:
    return P5.words(s)


def family_counts(low: str) -> dict:
    infer = sum(low.count(m) for m in P5.INFERENTIAL)
    expl = sum(low.count(m) for m in P5.EXPLANATORY)
    causal = sum(low.count(m) for m in P5.CAUSAL)
    return {"n_causal": causal, "n_inferential": infer, "n_explanatory": expl,
            "n_contrast": sum(low.count(m) for m in P5.CONTRAST),
            "control_count": sum(low.count(m) for m in P5.CAUSAL_CONTROL)}


def build_extra(df) -> list:
    """One dict per assistant turn, keyed by (traj_id, turn_index), carrying only the wave-5 columns."""
    rows = []
    for i, r in enumerate(df.itertuples(index=False)):
        pos = {}                              # (traj, turn_index) -> index in `rows`, so marking the turn whose call
                                              #         failed is one lookup, not a scan of every row so far. Local
        msgs = [dict(m) for m in (list(r.conversations) if r.conversations is not None else [])]
        traj = str(r.traj_id)
        evidence = []                       # observation texts handed to the agent so far, in order
        ev_words = set()                    # their content words, accumulated once per observation instead of
        ev_chars = 0                        # re-tokenising the whole evidence history on every turn
        seen_inspect = False
        turn_i = 0                          # assistant turns only, 1-based: the wave-4 spine's index, exactly
        pending = None                      # (traj, turn_index) of a turn whose call's response has not arrived
        for m in msgs:
            role, v = str(m.get("from")), str(m.get("value"))
            if role in ("tool", "function", "observation"):
                for nm, content in EF.parse_obs(v):
                    evidence.append(content or "")
                    ev_words |= cwords(content)
                    ev_chars += len(content or "")
                    if pending is not None and any(x in str(content).lower() for x in P5.REPAIR["acknowledge"]):
                        rows[pos[pending]]["prev_obs_error_next"] = 1

                pending = None
                continue
            if role not in ("gpt", "assistant"):
                continue
            body = EF.THINK.sub("", v).strip()
            think = " ".join(EF.THINK.findall(v)).strip()
            names = [nm for nm in EF.parse_calls(v)]
            calls_json = " ".join(json.dumps(c, ensure_ascii=False) for c in _call_args(v))
            key = (traj, turn_i + 1)
            turn_i += 1
            low = v.lower()
            tw = cwords(body)
            emits = int(bool([n for n in names if n]))
            rec = {
                "key": key, "traj_id": traj, "turn_index": turn_i, "emits_call": emits,
                "first_call_name": (names[0] if names else ""),
                **{f"act_{k}": int(any(x in low for x in lex)) for k, lex in P5.ACT.items()},
                **{f"act_{k}_b": int(any(x in low for x in lex)) for k, lex in P5.ACT_B.items()},
                "act_any": int(any(any(x in low for x in lex) for lex in P5.ACT.values())),
                **family_counts(low),
                "has_prior_evidence": int(ev_chars > 0),
                "evidence_chars": ev_chars,
                "evidence_overlap": (round(len(tw & ev_words) / max(1, len(tw)), 4) if tw else np.nan),
                "concl_after_inspect": int(seen_inspect),
                **{f"repair_{k}": int(any(x in low for x in lex))
                   for k, lex in P5.REPAIR.items() if k != "acknowledge"},
                "align_next": (round(len(tw & cwords(calls_json)) / max(1, len(tw)), 4)
                               if (tw and calls_json) else np.nan),
                "prev_obs_error_next": 0,
                "turn_sha_body": hashlib.sha256(body.encode("utf-8")).hexdigest()[:16],
            }
            if any(n and EF.INSPECT.search(str(n)) for n in names if n):
                seen_inspect = True
            if emits:
                pending = key
            pos[key] = len(rows)
            rows.append(rec)
        if (i + 1) % 2000 == 0:
            print(f"  extra features: {i + 1}/{len(df)} trajectories walked, {len(rows)} turns", flush=True)
    return rows


def _call_args(value: str):
    """The full call objects (name and arguments), so alignment sees the parameters, not just the tool name."""
    out = []
    for b in EF.CALL.findall(value):
        try:
            out.append(json.loads(b.strip()))
        except Exception:                                        # noqa: BLE001 - unparseable calls are counted
            BAD["calls_unparseable"] += 1
    return out


def permutation_null(F: pd.DataFrame) -> pd.Series:
    """T136's null: the alignment the same turn would get from a call in *another* trajectory of its length bin.

    The freeze names this as a 100-draw seeded permutation. Drawing it is a Monte-Carlo estimate of a quantity that
    has an exact value - the mean of the bin's alignments, leaving the turn's own trajectory out - and the exact form
    costs one groupby instead of 64 million draws and carries no seed sensitivity. The expectation is therefore what
    is computed, and the substitution is recorded as W5-D03 in the wave's deviations.
    """
    pool = F[(F["emits_call"] == 1) & F["align_next"].notna()].copy()
    if pool.empty:
        return pd.Series(np.nan, index=F.index, name="align_perm_mean")
    g = pool.groupby("len_bin", observed=True)["align_next"]
    pool["bin_sum"], pool["bin_n"] = g.transform("sum"), g.transform("count")
    t = pool.groupby(["len_bin", "traj_id"], observed=True)["align_next"]
    pool["own_sum"], pool["own_n"] = t.transform("sum"), t.transform("count")
    den = pool["bin_n"] - pool["own_n"]
    pool["perm"] = np.where(den > 0, (pool["bin_sum"] - pool["own_sum"]) / den.where(den > 0), np.nan)
    out = pd.Series(np.nan, index=F.index, name="align_perm_mean")
    out.loc[pool.index] = pool["perm"].to_numpy()
    return out


def kappa(a: pd.Series, b: pd.Series) -> float:
    """Cohen's kappa between two 0/1 labelings - T130's H3 statistic, on the frame's own rows."""
    d = pd.DataFrame({"a": a, "b": b}).dropna()
    if d.empty:
        return float("nan")
    po = float((d["a"] == d["b"]).mean())
    pa, pb = float(d["a"].mean()), float(d["b"].mean())
    pe = pa * pb + (1 - pa) * (1 - pb)
    return float("nan") if pe == 1.0 else round((po - pe) / (1 - pe), 4)


def selftest() -> int:
    """Read a hand-built trajectory and assert every wave-5 flag lands where its definition says it must."""
    def tc(c):
        return EF.t("tool_call") + c + EF.t("tool_call", True)

    call = json.dumps({"name": "read_file", "arguments": {"path": "/etc/app/config.yaml"}})
    call2 = json.dumps({"name": "terminal", "arguments": {"command": "cat /etc/app/config.yaml"}})
    obs_fail = json.dumps({"name": "read_file", "content": "Traceback: file not found /etc/app/config.yaml"})
    obs_ok = json.dumps({"name": "terminal", "content": "port = 8080\\nhost = localhost\\n"})
    t1 = "I will read the config file, because the port matters. " + tc(call)
    t2 = "That failed because the path was wrong; let me try again. " + tc(call2)
    t3 = "Therefore the service listens on 8080, thus the host is localhost, hence the answer is clear."
    df = pd.DataFrame({"traj_id": ["s1"], "category": ["config"], "subcategory": [""],
                       "conversations": [[{"from": "human", "value": "which port?"},
                                          {"from": "gpt", "value": t1},
                                          {"from": "tool", "value": EF.t("tool_response") + obs_fail
                                           + EF.t("tool_response", True)},
                                          {"from": "gpt", "value": t2},
                                          {"from": "tool", "value": EF.t("tool_response") + obs_ok
                                           + EF.t("tool_response", True)},
                                          {"from": "gpt", "value": t3}]]})
    x = pd.DataFrame(build_extra(df)).set_index("turn_index")
    assert x.loc[1, "act_plan"] == 1 and x.loc[1, "act_conclusion"] == 0, "the first turn is a plan, not a claim"
    assert x.loc[1, "n_causal"] >= 1 and x.loc[1, "emits_call"] == 1, "the because-clause and the call must land"
    assert x.loc[1, "prev_obs_error_next"] == 1, "the failure belongs to the turn whose call produced it"
    assert x.loc[1, "align_next"] > 0, "a plan naming config.yaml aligns with the call that asks for it"
    assert x.loc[1, "has_prior_evidence"] == 0, "nothing had been returned before the first call"
    assert x.loc[2, "repair_diagnose"] == 1 and x.loc[2, "repair_reissue"] == 1, "the repair families must split"
    assert x.loc[2, "concl_after_inspect"] == 1, "read_file is inspection-family, so turn 2 follows an inspection"
    assert x.loc[3, "act_conclusion"] == 1 and x.loc[3, "n_causal"] >= 2, "three inferential connectives are a chain"
    assert x.loc[3, "evidence_overlap"] >= 0.2, f"8080/localhost are in the evidence: {x.loc[3].to_dict()}"
    assert x.loc[3, "has_prior_evidence"] == 1 and x.loc[3, "prev_obs_error_next"] == 0
    assert np.isnan(x.loc[3, "align_next"]), "a turn with no call leaves alignment NaN, not 0"
    print("SELFTEST OK: acts, connective families, evidence overlap, order, failure and repair all land correctly")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap", type=int, default=int(TD5.SAMPLE["traj_cap"]))
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if a.selftest:
        return selftest()
    t0 = time.time()
    selftest()                                   # the instrument is proved on every real run, not only when asked
    W.OUT.mkdir(parents=True, exist_ok=True)
    take, files = EF.load_trajectories(a.cap)
    base = pd.DataFrame(EF.build_rows(take))     # wave 4's spine: same sample, same turn unit, same controls
    if base.empty:
        raise SystemExit("ABORT: the release yielded no assistant turns - the frame has no subject")
    extra = pd.DataFrame(build_extra(take))
    if extra.empty:
        raise SystemExit("ABORT: no turn text was read, so wave 5 has no features to join")
    base["turn_index"] = base["turn_index"].astype(int)
    extra["turn_index"] = extra["turn_index"].astype(int)
    # The spine already carries `emits_call` and `first_call_name`, read by wave 4's walk over the same text. A merge
    # would rename both silently and the frame would ship `emits_call_x` while the designs asked for `emits_call`, so
    # each shared column is compared between the walks first: identical -> the duplicate is dropped, otherwise both
    # readings are kept side by side under `_w5`, because a disagreement between two walks is a finding to record.
    for c in [x for x in extra.columns if x in set(base.columns) - {"traj_id", "turn_index"}]:
        chk = base[["traj_id", "turn_index", c]].merge(extra[["traj_id", "turn_index", c]],
                                                       on=["traj_id", "turn_index"], how="inner",
                                                       suffixes=("", "_w5"))
        n = int(len(chk))
        agree = int((chk[c].astype(str) == chk[f"{c}_w5"].astype(str)).sum())
        CROSSCHECK[c] = {"rows_compared": n, "agree": agree, "disagree": n - agree}
        if n and agree == n:
            extra = extra.drop(columns=[c])
        else:
            extra = extra.rename(columns={c: f"{c}_w5"})
    F = base.merge(extra.drop(columns=["key"]), on=["traj_id", "turn_index"], how="left", validate="one_to_one")
    lost = int(F["act_any"].isna().sum())
    if lost:
        raise SystemExit(f"ABORT: {lost} spine rows found no wave-5 feature row; the two walks disagree about the "
                         f"turn index, so a join this lossy cannot be shipped")
    gone = [c for c in ("emits_call", "first_call_name", "align_next", "prev_obs_error_next", "turn_sha")
            if c not in F.columns]
    if gone:
        raise SystemExit(f"ABORT: the joined frame lost {gone} to a rename at the merge, so the designs would read a "
                         f"column that is not there")
    F["len_bin"] = pd.qcut(F["n_turns_traj"].rank(method="first"), 5,
                           labels=["b1", "b2", "b3", "b4", "b5"]).astype(str)
    F["align_perm_mean"] = permutation_null(F)
    F["chain"] = (F["n_causal"] >= 2).astype(int)
    F["has_causal"] = (F["n_causal"] >= 1).astype(int)
    F["align_diff_perm"] = F["align_next"] - F["align_perm_mean"]
    F["stops_here"] = (F["next_action_kind"] != "call").astype(int)
    dest_csv = W.OUT / "EXP0164_wave5_step_features.csv.gz"
    F.to_csv(dest_csv, compression="gzip", index=False)

    def share(col):
        return round(float(F[col].mean()), 4) if col in F else None

    out = {"exp_id": EXP, "corpus": str(EF.CORPUS.name), "files_read": files,
           "trajectories": int(F["traj_id"].nunique()), "assistant_turns": int(len(F)),
           "sample_cap": int(a.cap), "cluster_unit": TD5.SAMPLE["cluster_unit"],
           "duplicate_traj_ids_dropped_before_sampling": int(take.attrs.get("duplicate_traj_ids_dropped", 0)),
           "act_any_share": share("act_any"), "plan_share": share("act_plan"),
           "conclusion_share": share("act_conclusion"), "causal_share": share("has_causal"),
           "chain_share": share("chain"), "repair_after_failure_turns": int(F["prev_obs_error_next"].sum()),
           "evidence_computable_share": share("has_prior_evidence"),
           "evidence_overlap_mean": round(float(F["evidence_overlap"].mean()), 4),
           "align_next_mean": round(float(F["align_next"].mean()), 4),
           "align_diff_perm_mean": round(float(F["align_diff_perm"].mean()), 4),
           "perm_draws_named_in_the_freeze": PERM_DRAWS,
           "perm_null_form": "exact leave-one-trajectory-out bin mean, the expectation of the drawn permutation "
                             "(W5-D03)",
           "kappa_act_a_vs_b": {k: kappa(F[f"act_{k}"], F[f"act_{k}_b"]) for k in P5.ACT},
           "join_crosscheck_vs_wave4_spine": CROSSCHECK,
           "calls_unparseable": int(BAD["calls_unparseable"]) + int(EF.BAD.get("calls_unparseable", 0)),
           "frame_file": str(dest_csv.relative_to(W.ROOT)), "seed": TD5.SEED, "started_at": W.now(),
           "wallclock_sec": round(time.time() - t0, 1), "invocation": " ".join([sys.executable] + sys.argv)}
    dest = W.write_raw(EXP, "wave5_step_matrix", out)
    print(json.dumps(out, indent=1, ensure_ascii=False, default=str)[:1800])
    print(f"\n{EXP}: wrote {dest_csv.name} ({len(F)} turns) and {dest.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
