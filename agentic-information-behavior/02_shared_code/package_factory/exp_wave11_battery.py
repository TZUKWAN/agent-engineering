"""EXP-0214: the E00-E19 battery for wave 11, on the same step loop as waves 2 and 4 through 10.

The shared steps (ablation, scaling, replication, error taxonomy, per-config headline) come from
`exp_wave1_battery` through `exp_wave2_battery.run_battery`; the estimators come down the wave 7 -> 9 -> 11 chain with
this wave's cluster and control defaults re-bound, which is the defect waves 8 and 9 each had to record once. What
wave 11 adds is the steps whose subject is a coded trace: a second reading of each coding instrument, the transfer of
the whole category set to text written by a different author, the within-stratum permutation as the counterfactual,
and the duplication audit that says how much of this draw is the same task prompt and the same opening command run
again.

    python 02_shared_code/package_factory/exp_wave11_battery.py [--quick]
"""
from __future__ import annotations

import collections
import hashlib
import pathlib
import re
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np                                                # noqa: E402
import pandas as pd                                               # noqa: E402
import wave_lib as W                                              # noqa: E402
import exp_wave2_battery as B2                                    # noqa: E402
import exp_wave5_features as EF5                                  # noqa: E402  one kappa, all waves
import exp_wave6_features as EF6                                  # noqa: E402  the reader, for the duplication pass
import exp_wave11_designs as D11                                  # noqa: E402
import probe_wave11_premises as P11                               # noqa: E402  the instruments, unchanged

EXP = "EXP-0214"
CTRL = D11.CTRL
CLUSTER = D11.CLUSTER
E06_DRAWS = 200


def frames() -> dict:
    fr = D11.load()
    R, P = fr["R"], fr["P"]
    return {"rollouts": R, "pairs": P, "long": R[R["n_turns"] >= 6].copy(),
            "repeated_instances": R[R["n_attempts"] >= 2].copy()}


def e06_second_instrument(fr: dict) -> dict:
    out = []
    R, P = fr["rollouts"], fr["pairs"]

    def rho(d, label, a, b, note, cluster=CLUSTER):
        dd = d[[a, b, cluster]].dropna()
        if dd.empty or dd[a].nunique() < 3 or dd[b].nunique() < 3:
            out.append({"construct": label, "status": "one instrument is near-degenerate on these rows",
                        "n": int(len(dd)), "note": note})
            return
        r = dict(W.rho_ci(dd, cluster, a, b))
        r.update(construct=label, n=int(len(dd)), clusters=int(dd[cluster].nunique()), note=note)
        out.append(r)

    def kappa(d, label, a, b, note, cluster=CLUSTER):
        dd = d[[a, b, cluster]].dropna()
        if dd.empty or dd[a].nunique() < 2 or dd[b].nunique() < 2:
            out.append({"construct": label, "status": "one instrument is constant on these rows", "n": int(len(dd)),
                        "note": note})
            return
        kb = W.cluster_boot_ci_and_p(dd, cluster, lambda x: EF5.kappa(x[a], x[b]), draws=E06_DRAWS, seed=P11.SEED)
        rec = {"construct": label, "kappa": EF5.kappa(dd[a], dd[b]),
               "agreement": round(float((dd[a] == dd[b]).mean()), 4), "n": int(len(dd)),
               "clusters": int(dd[cluster].nunique()), "note": note}
        rec["ci"] = ([round(float(v), 4) for v in kb["ci"]] if "ci" in kb else None)
        out.append(rec)

    R2 = R.copy()
    R2["comp_procedure_z"] = D11.z(R2["comp_procedure"].astype(float))
    R2["comp_rationale_z"] = D11.z(R2["comp_rationale"].astype(float))
    rho(R2, "procedure and rationale are coded as different categories (discriminant)", "comp_procedure",
        "comp_rationale", "T131 and T137 lean on the two being separable; near-perfect agreement would make the "
                          "category labels one signal")
    rho(R2, "presence of a result category against the exception it is balanced with (discriminant)", "comp_result",
        "comp_exception", "T131's manipulated term is the difference of these two, so their raw agreement is the "
                          "quantity its verdict depends on")
    kappa(R2.assign(has_uncert=(R2["uncert_n"] > 0).astype(int), has_exception=(R2["comp_exception"] > 0).astype(int)),
          "an uncertainty marker against an exception category", "has_uncert", "has_exception",
          "T140's H2 treats hedged language and failed observation as different classes; agreement near one would "
          "merge them")
    rho(P, "carry-forward of the procedure category against the text overlap of the pair (discriminant)",
        "earlier_procedure", "jaccard", "T137's H3 is exactly that the category is not the overlap; the pair-level "
                                         "correlation is where that can fail")
    rho(P, "concreteness of the earlier attempt against the later attempt's", "concreteness_earlier",
        "concreteness_later", "T138's H1 is this relation at the level of a regression; the rank form is reported "
                               "beside it")
    rho(R2, "survival at 25% against the number of turns a rollout had", "surv25_procedure", "n_turns",
          "a compression keeps a fraction of turns, so long rollouts keep more turns in absolute terms; this is the "
          "confound the survival ranking has to survive")
    kappa(P.assign(paired_success=((P["earlier_submitted"] == 1) & (P["later_submitted"] == 1)).astype(int),
                   any_success=((P["earlier_submitted"] == 1) | (P["later_submitted"] == 1)).astype(int)),
          "both attempts finishing against at least one finishing", "paired_success", "any_success",
          "T142's outcome is a per-attempt label while the claim reads like a per-task one; the agreement is the "
          "distance between the two readings")
    return {"pairs": out,
            "single_instrument_constructs": [
                "the eight component categories (one phrase list per category; a second independent coding would need "
                "a model, which the programme excludes)",
                "the relation class (one Jaccard banding of the pair's content words; the contradiction flag is the "
                "only second signal in the same family)",
                "finishing (the release's own exit_status, two values, 2.8% positive; there is no second outcome "
                "record anywhere in this draw)"],
            "note": "a construct with one operationalisation is listed, not silently dropped"}


def e08_external(fr: dict) -> dict:
    """The category instruments run on text with a different author: the routing release's human instructions."""
    df = W.load_routing(cols=None)
    agent = fr["rollouts"]
    present = collections.Counter()
    for q in df["question"].astype(str).head(4000):
        c = P11.components_of(q)
        present.update(c)
    n = min(4000, len(df))
    return {"corpus": "P001 routing release dev instructions: human-authored task text, no agent prose",
            "rows_read": int(n),
            "instruments": {"category_lists": "probe_wave11_premises.COMPONENT, unchanged",
                            "marker_lists": "the abstraction, uncertainty and negative-constraint lists, unchanged"},
            "prevalences_human_instructions": {str(k): round(float(v / max(1, n)), 4) for k, v in present.items()},
            "prevalences_agent_prose": {k: round(float(agent[f"comp_{k}"].mean()), 4) for k in P11.COMPONENT},
            "marker_means_human": {"abstract": round(float(np.mean([P11.marker_counts(str(q))["abstract_n"]
                                                                   for q in df["question"].head(2000)])), 3),
                                   "uncertainty": round(float(np.mean([P11.marker_counts(str(q))["uncert_n"]
                                                                      for q in df["question"].head(2000)])), 3)},
            "marker_means_agent": {"abstract": round(float(agent["abstract_n"].mean()), 3),
                                   "uncertainty": round(float(agent["uncert_n"].mean()), 3)},
            "what_transfers": "the eight category lists and the marker lists, unchanged, applied to prose with a "
                              "different author",
            "what_does_not": "nothing outcome-shaped: the routing release records a lexical ranker's ordering, not a "
                             "task completion, and it has no attempt sequence, so no wave-11 coefficient can be "
                             "reproduced there",
            "arms": {}}


def e17_counterfactual(fr: dict) -> dict:
    rng = np.random.default_rng(P11.SEED)
    spec = {"T131": dict(frame="rollouts", y="submitted", x="balance", family="binomial", covars=CTRL,
                         cluster=CLUSTER, permute_within="length_quartile"),
            "T137": dict(frame="pairs", y="later_procedure", x="earlier_procedure", family="gaussian",
                         covars=["jaccard_z", "later_turns_log"], cluster=CLUSTER, permute_within="repo_prefix"),
            "T138": dict(frame="pairs", y="concreteness_later", x="concreteness_earlier", family="gaussian",
                         covars=["jaccard_z", "later_turns_log"], cluster=CLUSTER, permute_within="overlap_band"),
            "T140": dict(frame="rollouts", y="surv25_procedure", x="first_pos_procedure", family="gaussian",
                         covars=["n_turns"], cluster=CLUSTER, permute_within="length_quartile"),
            "T142": dict(frame="pairs", y="later_submitted", x="is_refinement", family="binomial",
                         covars=["earlier_submitted", "jaccard_z"], cluster=CLUSTER,
                         permute_within="relation_class")}

    def fit(d, sp):
        f = D11.glm(d, sp["y"], [sp["x"]] + sp["covars"], sp["family"], cluster=sp["cluster"])
        if f is None or f.empty:
            return None
        r = f[f["term"] == sp["x"]]
        return None if r.empty else [round(float(r.iloc[0]["beta"]), 4), round(float(r.iloc[0]["ci_lo"]), 4),
                                     round(float(r.iloc[0]["ci_hi"]), 4)]
    arms = []
    for topic, sp in spec.items():
        F = fr[sp["frame"]]
        w = sp["permute_within"]
        if w not in F.columns:
            arms.append({"topic": topic, "term": sp["x"],
                         "note": f"the permutation stratum {w!r} is not a column of this frame, so no arm is offered"})
            continue
        perm = F.copy()
        perm[sp["x"]] = F.groupby(w, observed=True)[sp["x"]].transform(lambda s: rng.permutation(s.to_numpy()))
        arms.append({"topic": topic, "term": sp["x"], "on_outcome": sp["y"], "permuted_within": w,
                     "as_frozen": fit(F, sp), "marker_permuted_within_stratum": fit(perm, sp),
                     "rows": int(len(F)), "strata": int(F[w].nunique())})
    return {"instrument": "the same frozen model on the same rows, with the manipulated marker permuted inside each "
                          "stratum the model already conditions on",
            "arms": arms,
            "note": "a rollout cannot be re-recorded against a different world without a model, which the programme "
                    "forbids; permuting within the stratum keeps the marginal distribution of the marker and destroys "
                    "only which rollout or which attempt carries it"}


def e19_template_duplication(fr: dict) -> dict:
    """How much of this draw is the same task prompt, the same opening command and the same first words again?"""
    t0 = time.time()
    drawn, picks, rows_in_files, dupes = EF6.load_trajectories(int(D11.TD9.__dict__.get("x", 0) or 20000)) \
        if hasattr(D11, "TD9") else EF6.load_trajectories(20000)
    issue, first_cmd, first_assist = collections.Counter(), collections.Counter(), collections.Counter()
    n = 0
    for t in drawn:
        msgs = [dict(x) for x in (t.get("messages") or [])]
        iss = next((str(m.get("content") or "") for m in msgs if str(m.get("role")) == "user"), "")
        cmds = [str(m.get("content") or "") for m in msgs if str(m.get("role")) == "assistant"]
        if not cmds:
            continue
        n += 1
        issue[hashlib.sha1(re.sub(r"\s+", " ", iss).strip().lower().encode("utf-8")).hexdigest()[:16]] += 1
        first_cmd[hashlib.sha1(re.sub(r"\s+", " ", cmds[0]).strip().lower().encode("utf-8")).hexdigest()[:16]] += 1
        first_assist[hashlib.sha1(re.sub(r"\s+", " ", P11.assistant_text({"messages": msgs}))[:400]
                                  .strip().lower().encode("utf-8")).hexdigest()[:16]] += 1
    return {"rollouts_scanned": n, "files_read": picks,
            "distinct_task_prompts": int(len(issue)),
            "share_of_rollouts_sharing_a_prompt": round(float(1 - len(issue) / max(1, n)), 4),
            "most_repeated_prompt_rows": int(max(issue.values())) if issue else 0,
            "distinct_opening_assistant_messages": int(len(first_cmd)),
            "share_repeating_an_opening_message": round(float(1 - len(first_cmd) / max(1, n)), 4),
            "distinct_opening_prose_400_chars": int(len(first_assist)),
            "share_repeating_opening_prose": round(float(1 - len(first_assist) / max(1, n)), 4),
            "wallclock_sec": round(time.time() - t0, 1),
            "rule": "whitespace-normalised, lower-cased sha1 of the text; the opening prose is the first 400 "
                    "characters of the agent's own words, so a template that only differs later is not counted as "
                    "evidence of a shared plan"}


def shared(fr: dict, quick: bool = False) -> dict:
    return {"e06_second_instrument": e06_second_instrument(fr),
            "e08_external": e08_external(fr),
            "e17_counterfactual": e17_counterfactual(fr),
            "e19_contamination": e19_template_duplication(fr)}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    B2.run_battery(EXP, "wave11_battery_0214", frames, {
        "T131": dict(frame="rollouts", y="submitted", x="balance", family="binomial", covars=CTRL, cluster=CLUSTER),
        "T137": dict(frame="pairs", y="later_procedure", x="earlier_procedure", family="gaussian",
                     covars=["jaccard_z", "later_turns_log"], cluster=CLUSTER),
        "T138": dict(frame="pairs", y="concreteness_later", x="concreteness_earlier", family="gaussian",
                     covars=["jaccard_z", "later_turns_log"], cluster=CLUSTER),
        "T140": dict(frame="rollouts", y="surv25_procedure", x="first_pos_procedure", family="gaussian",
                     covars=["n_turns"], cluster=CLUSTER),
        "T142": dict(frame="pairs", y="later_submitted", x="is_refinement", family="binomial",
                     covars=["earlier_submitted", "jaccard_z"], cluster=CLUSTER)}, shared,
        quick="--quick" in sys.argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
