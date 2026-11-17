"""EXP-0171: the E00-E19 battery for wave 5, run by the same step loop as waves 2 and 4.

The single-frame steps (ablation, scaling, replication, error taxonomy, contamination-by-row) come from
`exp_wave1_battery` through `exp_wave2_battery.run_battery`, so an ablation in wave 5 is the same computation as in
wave 2. What wave 5 supplies is its frames - one population per design's own subject - and the steps whose subject is
the turn's language: a second instrument for every marker, an external prevalence transfer to P001's routing
instructions, a within-trajectory permutation as the counterfactual this wave can actually run, and the
text-duplication audit.

    python 02_shared_code/package_factory/exp_wave5_battery.py [--quick]
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np                                              # noqa: E402
import pandas as pd                                             # noqa: E402
import wave_lib as W                                            # noqa: E402
import exp_wave2_battery as B2                                  # noqa: E402
import exp_wave5_designs as D5                                  # noqa: E402
import probe_wave5_premises as P5                               # noqa: E402
import topic_designs_wave5 as TD5                               # noqa: E402

EXP = "EXP-0171"
CTRL = D5.CTRL

SPEC = {
    "T130": dict(frame="turns", y="act_plan", x="last_third", family="binomial", covars=CTRL, cluster="traj_id"),
    "T132": dict(frame="conclusion_turns", y="ov_z", x="concl_after_inspect", family="gaussian", covars=CTRL,
                 cluster="traj_id"),
    "T133": dict(frame="turns", y="repair_diagnose", x="prev_obs_error", family="binomial", covars=CTRL,
                 cluster="traj_id"),
    "T134": dict(frame="evidence_turns", y="ov_z", x="has_causal", family="gaussian", covars=CTRL,
                 cluster="traj_id"),
    "T135": dict(frame="connective_turns", y="ov_z", x="chain", family="gaussian", covars=CTRL, cluster="traj_id"),
    "T136": dict(frame="align_turns", y="prev_obs_error_next", x="align_z", family="binomial", covars=CTRL,
                 cluster="traj_id"),
}


def frames() -> dict:
    F = D5.load()
    t = F[F["body_len"] >= 20]
    return {"turns": t,
            "conclusion_turns": t[t["act_conclusion"] == 1].dropna(subset=["ov_z"]),
            "evidence_turns": t[(t["has_prior_evidence"] == 1)].dropna(subset=["ov_z"]),
            "connective_turns": t[(t["has_causal"] == 1) & (t["has_prior_evidence"] == 1)].dropna(subset=["ov_z"]),
            "align_turns": t[(t["has_align"] == 1)].dropna(subset=["align_diff"])}


E06_DRAWS = 200                        # cluster-bootstrap draws for an agreement statistic, fixed before reading


def e06_second_instrument(fr: dict) -> dict:
    """Every wave-5 marker that has a second operationalisation, and the list of constructs that do not.

    Each pair is two ways of deciding the same thing on the same rows, so a marker that only tracks one rule set's
    vocabulary shows up here as a low statistic rather than as a coefficient six steps later. Intervals are clustered
    on the trajectory, which is the unit both labelings were computed within.
    """
    out = []

    def pair(F, label, a, b, note, kind="kappa"):
        d = F[[a, b, "traj_id"]].dropna().rename(columns={a: "a", b: "b"})
        if d.empty:
            out.append({"construct": label, "status": "no row carries both instruments", "n": 0, "note": note})
            return
        if kind == "rho":
            r = dict(W.rho_ci(d, "traj_id", "a", "b"))
            r.update(construct=label, n=int(len(d)), clusters=int(d["traj_id"].nunique()), note=note)
            out.append(r)
            return
        if d["a"].nunique() < 2 or d["b"].nunique() < 2:
            out.append({"construct": label, "status": "one instrument is constant on these rows, so no agreement "
                        "statistic exists", "share_a": round(float(d["a"].mean()), 4),
                        "share_b": round(float(d["b"].mean()), 4), "n": int(len(d)),
                        "clusters": int(d["traj_id"].nunique()), "note": note})
            return
        boot = W.cluster_boot_ci_and_p(d, "traj_id", lambda x: D5.EF.kappa(x["a"], x["b"]),
                                       draws=E06_DRAWS, seed=TD5.SEED)
        rec = {"construct": label, "kappa": D5.EF.kappa(d["a"], d["b"]),
               "agreement": round(float((d["a"] == d["b"]).mean()), 4), "n": int(len(d)),
               "clusters": int(d["traj_id"].nunique()), "note": note}
        if "error" in boot:
            rec["ci"], rec["boot_note"] = None, boot["error"]
        else:
            rec["ci"] = [round(float(v), 4) for v in boot["ci"]]
        out.append(rec)

    T = fr["turns"].assign(infer_only=lambda s: (s["n_inferential"] > 0).astype(int),
                           chain_infer=lambda s: (s["n_inferential"] >= 2).astype(int),
                           insp_ever=lambda s: (s["prior_inspections"] > 0).astype(int))
    for k in P5.ACT:
        pair(T, f"speech act {k}: lexicon A vs the independently worded lexicon B", f"act_{k}", f"act_{k}_b",
             "two rule sets over the same turn text, so agreement is an instrument property, not a human one")
    pair(T, "causal connective present: both families vs the inferential family only", "has_causal", "infer_only",
         "T134's indicator, re-based on the family whose markers carry the direction of support")
    pair(T, "connective chain: >= 2 markers of either family vs >= 2 inferential", "chain", "chain_infer",
         "T135's chain threshold, tested one step higher and one family narrower")
    pair(T, "an inspection already happened before this turn: wave 5's walk vs wave 4's spine counter",
         "concl_after_inspect", "insp_ever",
         "the same fact read by two independent walks of the same conversation; disagreement would mean one of the "
         "two name regexes is wrong, which would move T132's own rows")
    return {"pairs": out,
            "single_instrument_constructs": [
                "evidence support (only the content-word overlap against all observations returned before the turn; "
                "a last-observation form would need the observation tokens, which the frame does not store)",
                "plan execution (only the alignment of the turn's content words with the call that followed it)",
                "repair subtype (one lexicon per family, unlike the five acts, which carry two)",
                "stopping (only the absence of a following call)"],
            "note": "a construct with one operationalisation is listed, not silently dropped"}


def e08_external(fr: dict) -> dict:
    """Prevalence transfer to a corpus this wave never measured on: P001's routing instructions.

    The external set is human-written, single-utterance, and carries no observations and no tool call, so what can
    cross the boundary is the marker lexicon and how often it fires; what cannot is any association, because wave 5's
    dependent variables are the name of the call that followed and the absence of one. The dev split only: the audit
    of which buckets were dropped is kept in the row so the licence is visible, not asserted.
    """
    R = W.load_routing(bucket="dev", cols=["question"])
    audit = {k: {"rows_total": v["rows_total"], "rows_kept": v["rows_kept"], "splits": v["split_counts"]}
             for k, v in (R.attrs.get("load_routing_audit") or {}).items()}
    low = R["question"].astype(str).str.lower()

    def any_of(names):
        return float(low.apply(lambda s: any(m in s for m in names)).mean())

    def two_of(names):
        return float(low.apply(lambda s: sum(s.count(m) for m in names) >= 2).mean())

    ext = {"any_act_marker": any_of(sum(P5.ACT.values(), [])),
           **{f"act_{k}": any_of(v) for k, v in P5.ACT.items()},
           "causal_connective": any_of(P5.CAUSAL), "causal_chain": two_of(P5.CAUSAL),
           "inferential_connective": any_of(P5.INFERENTIAL), "explanatory_connective": any_of(P5.EXPLANATORY),
           "diagnostic_repair_language": any_of(P5.REPAIR["diagnose"]),
           "reissue_language": any_of(P5.REPAIR["reissue"]), "abandon_language": any_of(P5.REPAIR["abandon"]),
           "control_pseudo_connective": any_of(P5.CAUSAL_CONTROL)}
    T = fr["turns"]

    def internal(col):
        return round(float(T[col].mean()), 4) if col in T else None

    intn = {"any_act_marker": internal("act_any"),
            **{f"act_{k}": internal(f"act_{k}") for k in P5.ACT},
            "causal_connective": internal("has_causal"), "causal_chain": internal("chain"),
            "inferential_connective": round(float((T["n_inferential"] > 0).mean()), 4),
            "explanatory_connective": round(float((T["n_explanatory"] > 0).mean()), 4),
            "diagnostic_repair_language": internal("repair_diagnose"),
            "reissue_language": internal("repair_reissue"), "abandon_language": internal("repair_abandon"),
            "control_pseudo_connective": round(float((T["control_count"] > 0).mean()), 4)}
    return {"corpus": "P001's routing release, dev split only: human-written task instructions with a candidate "
                     "catalogue, no assistant turn and no observation",
            "rows_read": int(len(R)), "by_config": audit,
            "markers_compared": sorted(ext),
            "prevalence_external_instructions": {k: round(v, 4) for k, v in ext.items()},
            "prevalence_wave5_turns": intn,
            "ratio_turn_over_instruction": {k: round(intn[k] / v, 3) if v and intn.get(k) is not None else None
                                             for k, v in ext.items()},
            "what_transfers": "the lexicons themselves: each is a string list applied to lower-cased text, so the "
                              "external column is the same rule run on prose this wave did not write",
            "what_does_not": "no association is transferred. The external corpus has no observation, so "
                             "`evidence_overlap` has nothing to overlap with, and no call follows an instruction, so "
                             "`next_is_inspect`, `stops_here` and the plan-alignment term do not exist there. "
                             "EXP-0027/29/30 measured the same asymmetry at column level across all eight releases",
            "arms": {}}


def e17_counterfactual(fr: dict) -> dict:
    """The intervention this wave can run: destroy the marker's placement, keep its dose.

    Rewriting an agent's recorded words and re-observing its behaviour is impossible without a model, which the
    programme forbids, so the counterfactual arm is estimated on the same rows with the marker redistributed *within*
    each trajectory. A real association in a language-behaviour design survives that; a marker that merely tracks
    where in a trajectory the text sits does not.
    """
    rng = np.random.default_rng(42)

    def fit(d, x, y, family):
        f = D5.glm(d, y, [x] + D5.CTRL, family)
        if f is None or f.empty:
            return None
        r = f[f["term"] == x]
        return None if r.empty else [round(float(r.iloc[0]["beta"]), 4), round(float(r.iloc[0]["ci_lo"]), 4),
                                     round(float(r.iloc[0]["ci_hi"]), 4)]
    arms = []
    for topic, sp in SPEC.items():
        F = fr[sp["frame"]]
        perm = F.copy()
        perm[sp["x"]] = F.groupby("traj_id")[sp["x"]].transform(
            lambda s: rng.permutation(s.to_numpy()))
        arms.append({"topic": topic, "term": sp["x"], "on_outcome": sp["y"],
                     "as_frozen": fit(F, sp["x"], sp["y"], sp["family"]),
                     "marker_permitted_within_trajectory": fit(perm, sp["x"], sp["y"], sp["family"]),
                     "rows": int(len(F))})
    return {"instrument": "the same frozen model on the same rows, with the marker permuted inside each trajectory",
            "arms": arms,
            "note": "a rewrite arm is not offered because recorded behaviour cannot be re-simulated without a model"}


def e19_text_duplication(fr: dict) -> dict:
    """How many distinct turn texts stand behind a marker prevalence."""
    F = fr["turns"]
    d = F.dropna(subset=["turn_sha_body"])
    vc = d["turn_sha_body"].value_counts()
    rep = d["turn_sha_body"].map(vc)
    return {"rows_scanned": int(len(F)), "rows_with_a_digest": int(len(d)),
            "distinct_turn_texts": int(vc.size),
            "share_of_turns_that_are_a_repeat": round(float(1 - vc.size / max(1, len(d))), 4),
            "most_repeated_turn_text_rows": int(vc.iloc[0]) if len(vc) else 0,
            "causal_share_among_repeats": round(float(d[rep > 1]["has_causal"].mean()), 4) if len(vc) else None,
            "causal_share_among_unique_turns": round(float(d[rep == 1]["has_causal"].mean()), 4) if len(vc) else None,
            "rule": "one digest per turn body; a repeat is the same text in another trajectory"}


def shared(fr: dict, quick: bool = False) -> dict:
    return {"e06_second_instrument": e06_second_instrument(fr),
            "e08_external": e08_external(fr),
            "e17_counterfactual": e17_counterfactual(fr),
            "e19_contamination": e19_text_duplication(fr)}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    B2.run_battery(EXP, "wave5_battery_0171", frames, SPEC, shared, quick="--quick" in sys.argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
