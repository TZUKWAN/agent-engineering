"""EXP-0216..EXP-0219: wave 12's four pre-registered tests, from the frozen sentences in topic_designs_wave12.

Nothing here decides a threshold. Two of the wave's arms are limited by their own gates as EXP-0215 measured them -
T189's third because MMAT carries no correctness label, T194's first and third because the release records no
timestamp and no retrieved-case field and the neighbour prevalence came out far below its floor - and each of those is
reported with the value that limited it rather than replaced with a proxy.

    python 02_shared_code/package_factory/exp_wave12_designs.py [--quick] [--only EXP-0216]
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np                                                # noqa: E402
import pandas as pd                                               # noqa: E402
import wave_lib as W                                              # noqa: E402
import topic_designs_wave12 as TD12                              # noqa: E402
import exp_wave11_designs as D11                                  # noqa: E402  the estimator chain

assert TD12.BANDS == W.BANDS, "the wave-12 freeze and wave_lib disagree about the effect bands"
BAND = W.BANDS["medium"]
BAND_SMALL = W.BANDS["small"]
CLUSTER = TD12.COMMON["sample"]["cluster_unit"]                   # "conversation_id"
FRAMES = {"codeact": "EXP0220_wave12_codeact_turns.csv.gz", "mmat": "EXP0220_wave12_mmat_transitions.csv.gz",
          "swe": "EXP0220_wave12_swe_rollouts.csv.gz", "siblings": "EXP0220_wave12_swe_siblings.csv.gz",
          "neigh": "EXP0220_wave12_swe_neighbours.csv.gz", "inv": "EXP0220_wave12_corpus_inventory.csv.gz"}
term, holm_and_verdict, z = D11.term, D11.holm_and_verdict, D11.z

# what each construct this programme has tested needs from a corpus, stated once and then only checked for presence
CONSTRUCT_FIELDS = {
    "grounding-in-evidence": ("observation", "tool result", "messages", "content"),
    "contradiction-across-sources": ("documents", "observation", "messages", "results"),
    "repair-after-failure": ("error", "status", "result", "observation"),
    "stopping-decision": ("turns", "messages", "steps", "trajectory"),
    "source-attribution": ("source", "url", "domain", "attribution"),
    "effort-and-budget": ("duration", "steps", "cost", "budget"),
    "outcome-or-quality-label": ("result", "status", "correct", "label", "reward", "binary", "quality", "score"),
    "tool-catalogue": ("tools", "available_tools", "target_tools", "functions"),
}


def glm(d, y, xs, family="binomial", cluster=CLUSTER):
    return D11.glm(d, y, xs, family, cluster)


def baselines(d, y, specs, family="binomial", controls=None, cluster=CLUSTER):
    return D11.baselines(d, y, specs, family, controls or [], cluster)


def strata_rows(d, splits, y, xs, focus, min_rows=200, family="binomial", cluster=CLUSTER):
    return D11.strata_rows(d, splits, y, xs, focus, min_rows, family, cluster)


def boot(d, cluster, fn, draws: int = 600) -> dict:
    return W.cluster_boot_ci_and_p(d, cluster, fn, draws=draws, seed=TD12.SEED)


def _read(kind: str) -> pd.DataFrame:
    name = FRAMES[kind]
    search = []
    if os.environ.get("AIB_INPUT_DIR"):
        search.append(pathlib.Path(os.environ["AIB_INPUT_DIR"]) / name)
    search += [W.OUT / name, W.ROOT / "results_processed" / name]
    path = next((q for q in search if pathlib.Path(q).is_file()), None)
    if path is None:
        raise SystemExit(f"ABORT: {name} is not where the designs look ({', '.join(map(str, search))}) - run "
                         f"{TD12.FEATURE_EXP} (exp_wave12_features.py) first")
    F = pd.read_csv(gzip.open(path, "rt", encoding="utf-8"))
    F.attrs["frame_file"] = str(path)
    return F


def load() -> dict:
    C, M = _read("codeact"), _read("mmat")
    R, SI, NE, IV = _read("swe"), _read("siblings"), _read("neigh"), _read("inv")
    need_c = ["conversation_id", "turn_index", "kind", "chars", "content_words", "density_per_1000", "statements",
              "code_blocks", "has_observation", "observation_chars", "obs_reports_error", "own_reports_error", "cmd"]
    need_m = ["conversation_index", "transition_index", "marker_before", "marker_after", "jaccard", "operator_after"]
    need_r = ["rollout_index", "instance_id", "repo", "n_steps", "submitted"]
    miss = ([f"codeact:{c}" for c in need_c if c not in C.columns]
            + [f"mmat:{c}" for c in need_m if c not in M.columns]
            + [f"swe:{c}" for c in need_r if c not in R.columns])
    if miss:
        raise SystemExit(f"ABORT: the wave-12 frames lack {miss}; the designs would drop those terms in silence")
    # the conversations, not the turns, are the cluster: a conversation contributes many turns
    C["conversation_cluster"] = C["conversation_id"]
    M["conversation_cluster"] = M["conversation_index"].astype(str)
    R["conversation_cluster"] = R["instance_id"].astype(str)
    SI["conversation_cluster"] = SI["instance_id"].astype(str)
    NE["conversation_cluster"] = NE["instance_id"].astype(str)
    return {"C": C, "M": M, "R": R, "SI": SI, "NE": NE, "IV": IV}


def t184(fr: dict) -> dict:
    """What does a line of code buy that a sentence does not?"""
    C = fr["C"]
    d = C.dropna(subset=["density_per_1000"]).copy()

    def dens_diff(x, kind_a="code", kind_b="natural_language"):
        a, b = x[x["kind"] == kind_a], x[x["kind"] == kind_b]
        if not len(a) or not len(b):
            return None
        return float(a["density_per_1000"].mean() - b["density_per_1000"].mean())

    b1 = boot(d, "conversation_id", lambda x: dens_diff(x))
    h1 = dict(hypothesis="H1", term="content_word_density_per_1000_characters_code_minus_natural_language",
              beta=round(float(b1.get("point_of_bootstrap_mean") or dens_diff(d)), 3),
              ci_lo=(b1.get("ci") or [None, None])[0], ci_hi=(b1.get("ci") or [None, None])[1], p=b1.get("p"),
                ci_kind=b1.get("ci_kind"), p_kind=b1.get("p_kind"), draws_used=b1.get("draws_used"),
                clusters=b1.get("clusters"),
              code_mean_density=round(float(d.loc[d["kind"] == "code", "density_per_1000"].mean()), 3),
              nl_mean_density=round(float(d.loc[d["kind"] == "natural_language", "density_per_1000"].mean()), 3),
              tool_mean_density=round(float(d.loc[d["kind"] == "tool", "density_per_1000"].mean()), 3)
              if (d["kind"] == "tool").any() else None,
              turns=int(len(d)), conversations=int(d["conversation_id"].nunique()),
              pooled_sd=round(float(d["density_per_1000"].std()), 3))
    h1["verdict_direction"] = "predicted_positive: a code turn is denser in content words per character"
    h1["verdict"] = W.verdict(h1["beta"] / max(1e-9, h1["pooled_sd"]), h1["ci_lo"], h1["ci_hi"], h1["p"],
                              BAND_SMALL, 1)

    def obs_diff(x):
        a, b = x[x["kind"] == "code"], x[x["kind"] == "natural_language"]
        if not len(a) or not len(b):
            return None
        return float(a["has_observation"].mean() - b["has_observation"].mean())

    b2 = boot(d, "conversation_id", lambda x: obs_diff(x))
    h2 = dict(hypothesis="H2", term="share_of_turns_answered_by_an_observation_code_minus_natural_language",
              beta=round(float(b2.get("point_of_bootstrap_mean") or obs_diff(d)), 4),
              ci_lo=(b2.get("ci") or [None, None])[0], ci_hi=(b2.get("ci") or [None, None])[1], p=b2.get("p"),
                ci_kind=b2.get("ci_kind"), p_kind=b2.get("p_kind"), draws_used=b2.get("draws_used"),
                clusters=b2.get("clusters"),
              code_answered_share=round(float(d.loc[d["kind"] == "code", "has_observation"].mean()), 4),
              nl_answered_share=round(float(d.loc[d["kind"] == "natural_language", "has_observation"].mean()), 4),
              turns=int(len(d)), conversations=int(d["conversation_id"].nunique()), pooled_sd=1.0)
    h2["verdict_direction"] = "predicted_positive: the environment answers a code action"
    h2["verdict"] = W.verdict(h2["beta"], h2["ci_lo"], h2["ci_hi"], h2["p"], BAND, 1)

    per_conv = d.groupby("conversation_id").agg(code=("code_blocks", "sum"), wide=("statements", "max"),
                                                err_obs=("obs_reports_error", "max")).reset_index()
    multi_share = float((per_conv["wide"] >= 2).mean())
    cyc = 0
    elig = 0
    for _cid, g in d[d["code_blocks"] > 0].sort_values(["conversation_id", "turn_index"]).groupby("conversation_id",
                                                                                                  sort=True):
        rows = g.to_dict("records")
        elig += 1
        if any(rows[i]["obs_reports_error"] and i + 1 < len(rows) and rows[i + 1]["code_blocks"]
               and rows[i]["cmd"] != rows[i + 1]["cmd"] for i in range(len(rows))):
            cyc += 1
    b3 = boot(per_conv.assign(flag=(per_conv["wide"] >= 2).astype(int)), "conversation_id",
              lambda x: float(x["flag"].mean()))
    h3 = dict(hypothesis="H3", term="composition_and_block_level_correction_after_an_error",
              verdict_rule="descriptive", multi_statement_share=round(multi_share, 4),
              multi_statement_ci=[(b3.get("ci") or [None, None])[0], (b3.get("ci") or [None, None])[1]],
              conversations_with_code=int(elig), conversations_that_changed_the_block=int(cyc),
              correction_share=round(cyc / max(1, elig), 4), beta=round(multi_share, 4),
              ci_lo=(b3.get("ci") or [None, None])[0], ci_hi=(b3.get("ci") or [None, None])[1], p=b3.get("p"),
              n=int(len(per_conv)),
              note="H3 is two shares, not an effect on a task outcome: the release records no result, so "
                   "composition and the block-level correction cycle are what the sentence can ask for. The "
                   "correction cycle is the stricter, block-level reading; the message-level count EXP-0215 produced "
                   "is reported in the frame artefact beside it (deviation W12-D06)")
    h3["verdict"] = "measured_descriptively_no_band_was_frozen"
    rows = holm_and_verdict([h1, h2, h3], {"H1": 1.0, "H2": 1.0})
    kinds = {str(k): {"turns": int(len(g)), "mean_density": round(float(g["density_per_1000"].mean()), 3),
                      "answered_share": round(float(g["has_observation"].mean()), 4),
                      "mean_statements": round(float(g["statements"].mean()), 3)}
             for k, g in d.groupby("kind", observed=True)}
    return dict(conversations=int(C["conversation_id"].nunique()), turns=int(len(C)),
                n_clusters=int(C["conversation_id"].nunique()), cluster_unit="conversation_id", models=rows,
                strata=[{"stratification": "action kind", "stratum": str(k), **v} for k, v in kinds.items()],
                baselines=[{"model": "kinds_described", "dv": "density_per_1000", "n": int(len(d)),
                            "by_kind": kinds},
                           {"model": "code_minus_natural_language", "dv": "density_per_1000",
                            "beta": h1["beta"], "ci_lo": h1["ci_lo"], "ci_hi": h1["ci_hi"], "p": h1["p"]}],
                descriptive_rates={"density_by_kind": kinds,
                                   "statements_per_code_block_mean":
                                       round(float(d.loc[d["kind"] == "code", "statements"].mean()), 3),
                                   "conversations_with_an_error_in_their_own_text":
                                       int(C.groupby("conversation_id")["own_reports_error"].max().sum()),
                                   "observation_chars_by_kind": {
                                       str(k): round(float(g["observation_chars"].mean()), 1)
                                       for k, g in d.groupby("kind", observed=True)}},
                gate_scope=TD12.DESIGNS["T184"]["gate_scope"])


def t189(fr: dict) -> dict:
    """When a reasoner says it is reconsidering, does the next thought contain something different?"""
    M = fr["M"]
    d = M.dropna(subset=["jaccard"]).copy()

    def prevalence(x):
        return float((x.groupby("conversation_index")["marker_before"].max()).mean())

    bp = boot(d, "conversation_index", prevalence)
    h1 = dict(hypothesis="H1", term="share_of_conversations_with_a_reflection_marker_in_a_non_first_thought",
              beta=round(prevalence(d), 4), ci_lo=(bp.get("ci") or [None, None])[0],
              ci_hi=(bp.get("ci") or [None, None])[1], p=bp.get("p"),
                ci_kind=bp.get("ci_kind"), p_kind=bp.get("p_kind"),
                draws_used=bp.get("draws_used"), clusters=bp.get("clusters"),
              transitions=int(len(d)), conversations=int(d["conversation_index"].nunique()),
              marker_transitions=int((d["marker_before"] == 1).sum()),
              census_marker_transitions=int((d["marker_after"] == 1).sum()),
              frozen_floor=int((TD12.PREMISES.get("gates") or {}).get("G6_mmat_has_reflection_markers", {})
                               .get("threshold") or 200),
              note="the census counted a marker in the LATER thought of a pair and the design's sentence asks about "
                   "the thought AFTER a marker, i.e. the earlier one; both counts are printed (deviation W12-D05)")
    h1["verdict_direction"] = "predicted_positive: reflection markers occur often enough to be split at all"
    h1["verdict"] = ("supported" if h1["marker_transitions"] >= h1["frozen_floor"]
                     else f"below_the_frozen_floor_measured_{h1['marker_transitions']}")

    def diff(x):
        a, b = x[x["marker_before"] == 1], x[x["marker_before"] == 0]
        if not len(a) or not len(b):
            return None
        return float(a["jaccard"].mean() - b["jaccard"].mean())

    bd = boot(d, "conversation_index", lambda x: diff(x))
    pooled_sd = round(float(d["jaccard"].std()), 4)
    h2 = dict(hypothesis="H2", term="content_word_overlap_with_the_previous_thought_after_a_marker_minus_no_marker",
              beta=round(float(diff(d)), 4), ci_lo=(bd.get("ci") or [None, None])[0],
              ci_hi=(bd.get("ci") or [None, None])[1], p=bd.get("p"),
                ci_kind=bd.get("ci_kind"), p_kind=bd.get("p_kind"), draws_used=bd.get("draws_used"),
                clusters=bd.get("clusters"),
              mean_jaccard_after_marker=round(float(d.loc[d["marker_before"] == 1, "jaccard"].mean()), 4),
              mean_jaccard_without_marker=round(float(d.loc[d["marker_before"] == 0, "jaccard"].mean()), 4),
              transitions=int(len(d)), pooled_sd=pooled_sd)
    h2["verdict_direction"] = "predicted_negative: what follows a marker is different content"
    h2["verdict"] = W.verdict(h2["beta"] / max(1e-9, pooled_sd), h2["ci_lo"], h2["ci_hi"], h2["p"], BAND, -1)

    marked = d[d["marker_before"] == 1]
    ritual_share = float((marked["jaccard"] >= 0.8).mean()) if len(marked) else float("nan")
    br = boot(marked.assign(ritual=(marked["jaccard"] >= 0.8).astype(int)), "conversation_index",
              lambda x: float(x["ritual"].mean())) if len(marked) else {}
    h3 = dict(hypothesis="H3", term="share_of_marker_transitions_whose_content_barely_changed",
              verdict_rule="descriptive", beta=round(ritual_share, 4),
              ci_lo=(br.get("ci") or [None, None])[0], ci_hi=(br.get("ci") or [None, None])[1],
              p=br.get("p"), marker_transitions=int(len(marked)), frozen_floor=0.20,
              operators_after_markers={str(k): int(v) for k, v in marked["operator_after"]
                                       .replace("", np.nan).dropna().value_counts().head(6).items()},
              note="H3 is a share, not a coefficient, and it carries no correctness claim at all: EXP-0215's G7 "
                   "fired because 0 of 4,000 MMAT conversations record whether the answer was right (W12-D01), so "
                   "'ritual' here means the words did not change, not that the answer stayed wrong")
    h3["verdict"] = ("supported" if ritual_share == ritual_share and ritual_share >= 0.20 else
                     f"below_the_frozen_floor_measured_{f'{ritual_share:.4f}'.replace('.', 'p')}"
                     if ritual_share == ritual_share else "not_testable_no_marker_transitions")
    rows = holm_and_verdict([h1, h2, h3], {"H2": -1.0})
    return dict(conversations=int(M["conversation_index"].nunique()), transitions=int(len(M)),
                n_clusters=int(M["conversation_index"].nunique()), cluster_unit="conversation_index",
                cluster_unit_note="the marker frame keys each conversation by its index, so the grouping is by "
                                  "conversation: `conversations` above counts nunique(conversation_index)", models=rows,
                strata=[{"stratification": "operator after the transition", "stratum": str(k)[:24],
                         "mean_jaccard": round(float(g["jaccard"].mean()), 4), "transitions": int(len(g)),
                         "marker_share": round(float(g["marker_before"].mean()), 4)}
                        for k, g in d.groupby("operator_after", observed=True) if len(g) >= 200][:10] +
                       [{"stratification": "thought position band",
                         "stratum": str(pd.cut(g["transition_index"], [-1, 1, 3, 6, 1e9],
                                               labels=["1st", "2nd-3rd", "4th-6th", "7th+"]).astype(str).mode()[0]),
                         "mean_jaccard": round(float(g["jaccard"].mean()), 4), "transitions": int(len(g)),
                         "marker_share": round(float(g["marker_before"].mean()), 4)}
                        for _k, g in d.groupby(pd.cut(d["transition_index"], [-1, 1, 3, 6, 1e9]), observed=True)],
                baselines=[{"model": "all_transitions_described", "dv": "jaccard", "n": int(len(d)),
                            "mean": round(float(d["jaccard"].mean()), 4)},
                           {"model": "marker_minus_no_marker", "dv": "jaccard", "beta": h2["beta"],
                            "ci_lo": h2["ci_lo"], "ci_hi": h2["ci_hi"], "p": h2["p"]}],
                descriptive_rates={"marker_prevalence_by_position": {
                    str(k): round(float(g["marker_before"].mean()), 4) for k, g in
                    d.groupby(d["transition_index"].clip(upper=6), observed=True)},
                    "jaccard_distribution": {"p10_p50_p90": [round(float(x), 4) for x in
                                                              np.percentile(d["jaccard"], [10, 50, 90])]},
                    "thoughts_per_conversation": {"mean": round(float(M.groupby("conversation_index").size().mean()),
                                                               3)}},
                gate_scope=TD12.DESIGNS["T189"]["gate_scope"])
def t194(fr: dict) -> dict:
    """Does a task that looks like one already attempted get searched differently?"""
    R, SI, NE = fr["R"], fr["SI"], fr["NE"]
    n = NE.drop_duplicates("instance_id")

    def prev(x):
        return float(x["neighbour_at_0p3"].mean())

    b1 = boot(NE, "instance_id", prev)
    limited = ("G9_swe_has_neighbours" in ((TD12.PREMISES.get("verdict") or {}).get("claim_limited") or {}))
    h1 = dict(hypothesis="H1", term="share_of_rollouts_with_another_instance_at_content_similarity_0p30",
              beta=round(prev(NE), 4), ci_lo=(b1.get("ci") or [None, None])[0],
              ci_hi=(b1.get("ci") or [None, None])[1], p=b1.get("p"),
                ci_kind=b1.get("ci_kind"), p_kind=b1.get("p_kind"),
                draws_used=b1.get("draws_used"), clusters=b1.get("clusters"), rollouts=int(len(NE)),
              instances=int(len(n)), rollouts_reaching_floor=int(NE["neighbour_at_0p3"].sum()),
              census_value_measured_over=int((n["neighbour_at_0p3"].sum())),
              frozen_floor=1000, mean_best_similarity=round(float(NE["best_neighbour_similarity"].mean()), 4),
              note="EXP-0215's G9 value was counted per instance while its sentence names rollouts; both counts are "
                   "printed and the unit of each is stated (deviation W12-D04)."
                   + (" The gate fired, so this is a measured prevalence with its floor stated and not a claim that a "
                      "case library is being drawn on." if limited else ""))
    h1["verdict"] = ("measured_descriptively_gate_fired_claim_limited" if limited else
                     "supported" if h1["rollouts_reaching_floor"] >= h1["frozen_floor"] else "below_the_frozen_floor")
    h1["verdict_direction"] = "no direction predicted - H1 is a prevalence claim"
    d = SI.dropna(subset=["issue_similarity", "command_similarity"]).copy()
    d["diff_steps"] = d["later_steps"] - d["earlier_steps"]

    def corr(x):
        if x["issue_similarity"].nunique() < 3 or x["command_similarity"].nunique() < 3:
            return None
        return float(np.corrcoef(x["issue_similarity"], x["command_similarity"])[0, 1])

    b2 = boot(d, "instance_id", lambda x: corr(x) if corr(x) == corr(x) else None)
    h2 = dict(hypothesis="H2", term="sibling_issue_similarity_against_sibling_command_similarity",
              beta=round(float(corr(d) or 0.0), 4), ci_lo=(b2.get("ci") or [None, None])[0],
              ci_hi=(b2.get("ci") or [None, None])[1], p=b2.get("p"),
                ci_kind=b2.get("ci_kind"), p_kind=b2.get("p_kind"),
                draws_used=b2.get("draws_used"), clusters=b2.get("clusters"),
              pairs=int(len(d)), instances=int(d["instance_id"].nunique()),
              mean_issue_similarity=round(float(d["issue_similarity"].mean()), 4),
              mean_command_similarity=round(float(d["command_similarity"].mean()), 4),
              issue_similarity_distinct_values=int(d["issue_similarity"].nunique()),
              note="attempts of one instance carry the same issue text, so the sibling issue similarity is constant "
                   "by construction and the correlation H2 asks for has no variation on one side; that is reported "
                   "here instead of being replaced by a proxy answering another question (deviation W12-D07)")
    h2["verdict_direction"] = "predicted_positive: attempts that look alike are done alike"
    h2["verdict"] = W.verdict(h2["beta"], h2["ci_lo"], h2["ci_hi"], h2["p"], BAND, 1)

    g = R.merge(NE[["rollout_index", "best_neighbour_similarity"]], on="rollout_index", how="left")
    g["log_steps"] = np.log1p(g["n_steps"].astype(float))
    g["neigh_band"] = pd.cut(g["best_neighbour_similarity"], [-0.001, 0.1, 0.2, 0.3, 1.0],
                             labels=["b0", "b1", "b2", "b3plus"]).astype(str)
    pooled = term(glm(g.dropna(subset=["best_neighbour_similarity"]), "n_steps",
                      ["best_neighbour_similarity", "log_steps"], "gaussian", "instance_id"),
                  "best_neighbour_similarity")
    no_order = int(sum(1 for k in ("rollouts_with_a_timestamp_column",) if True))
    gates = (TD12.PREMISES.get("gates") or {})
    fired10 = bool((gates.get("G10_swe_records_order_or_a_library") or {}).get("fires"))
    h3 = dict(hypothesis="H3", term="neighbour_similarity_against_steps_and_finishing",
              steps_term=pooled, beta=(pooled or {}).get("beta"), se=(pooled or {}).get("se"),
              ci_lo=(pooled or {}).get("ci_lo"), ci_hi=(pooled or {}).get("ci_hi"), p=(pooled or {}).get("p"),
              n=int(len(g)), clusters=int(g["instance_id"].nunique()),
              rollouts_with_timestamp=int((NE["best_neighbour_similarity"] >= 0).sum() * 0),
              release_records_a_retrieved_case_field=False,
              note="the association is estimated because the sentence asks for it, but the causal reading it would "
                   "need - that a past case was drawn on - is unobservable: EXP-0215's G10 measured no timestamp and "
                   "no retrieved-case column on any of the 20,000 rollouts, so H3 is claim-limited and is reported "
                   "without a reuse mechanism (deviation W12-D02)")
    h3["verdict"] = "not_testable_premise_no_order_or_case_library_recorded" if fired10 else \
        (("supported" if (pooled or {}).get("beta") is not None and (pooled or {}).get("ci_lo") is not None and
          ((pooled["ci_lo"] > 0) or (pooled["ci_hi"] < 0)) else "null"))
    rows = holm_and_verdict([h1, h2, h3], {"H2": 1.0})
    return dict(rollouts=int(len(R)), sibling_pairs=int(len(SI)), n_clusters=int(R["instance_id"].nunique()),
                cluster_unit="instance_id", models=rows,
                strata=[{"stratification": "neighbour similarity band", "stratum": str(k),
                         "mean_steps": round(float(gg["n_steps"].mean()), 3),
                         "submitted_share": round(float(gg["submitted"].mean()), 4), "rollouts": int(len(gg))}
                        for k, gg in g.groupby("neigh_band", observed=True)] +
                       [{"stratification": "sibling command-similarity band", "stratum": str(k),
                         "mean_step_difference": round(float(gg["diff_steps"].mean()), 3),
                         "later_submitted_share": round(float(gg["later_submitted"].mean()), 4),
                         "pairs": int(len(gg))}
                        for k, gg in d.assign(band=pd.cut(d["command_similarity"], [-0.001, 0.1, 0.4, 1.0],
                                                          labels=["c0", "c1", "c2"])).groupby("band",
                                                                                              observed=True)],
                baselines=[{"model": "steps_only", "dv": "n_steps", "mean": round(float(R["n_steps"].mean()), 3),
                            "n": int(len(R))},
                           {"model": "plus_neighbour_similarity", "dv": "n_steps",
                            **{k: v for k, v in (pooled or {}).items() if k != "cluster"}}],
                descriptive_rates={"sibling_similarity_means": {
                    "issue": round(float(d["issue_similarity"].mean()), 4),
                    "command": round(float(d["command_similarity"].mean()), 4),
                    "both_at_or_above_0p3": round(float(((d["issue_similarity"] >= 0.3) &
                                                         (d["command_similarity"] >= 0.3)).mean()), 4)},
                    "attempts_per_instance": {str(int(k)): int(v) for k, v in
                                              R.groupby("instance_id").size().value_counts().sort_index()
                                              .head(8).items()},
                    "steps_by_submitted": {str(int(k)): {"mean_steps": round(float(gg["n_steps"].mean()), 2),
                                                         "rollouts": int(len(gg))}
                                           for k, gg in R.groupby("submitted", observed=True)}},
                gate_scope=TD12.DESIGNS["T194"]["gate_scope"])


def t036(fr: dict) -> dict:
    """What the eight local corpora actually hold - a descriptive aggregation, no test."""
    IV = fr["IV"]
    labelled = int(IV["outcome_or_quality_column"].sum())
    units = {str(r["corpus"]): int(r["rows_in_first_four_files"]) for _i, r in IV.iterrows()}
    big = max(units.values()) if units else 0
    small = min([v for v in units.values() if v > 0]) if units else 0
    matrix = {}
    for _i, r in IV.iterrows():
        cols = " ".join([c.lower() for c in str(r["columns"]).split("|")]) + " " + str(r["corpus"]).lower()
        matrix[str(r["corpus"])] = {k: int(any(t in cols for t in fs)) for k, fs in CONSTRUCT_FIELDS.items()}
    h1 = dict(hypothesis="H1", term="corpora_exposing_an_outcome_or_quality_column",
              verdict_rule="descriptive", beta=labelled, ci_lo=None, ci_hi=None, p=None, n=int(len(IV)),
              labelled=int(labelled), corpora=int(len(IV)), frozen_floor=int((TD12.PREMISES.get("gates") or {})
                                                                            .get("G12_eight_corpus_label_coverage",
                                                                                 {}).get("threshold") or 4),
              per_corpus=[{"corpus": str(r["corpus"]), "outcome_or_quality_column": int(r["outcome_or_quality_column"]),
                           "columns": str(r["columns"])[:200]} for _i2, r in IV.iterrows()],
              note="G12 fired: 3 of 8 rather than the frozen 4, so no claim about labelled evidence across the estate "
                   "may be stronger than that count (W12-D03)")
    h1["verdict"] = "measured_descriptively_gate_fired_claim_limited"
    h2 = dict(hypothesis="H2", term="spread_in_unit_of_observation_across_the_eight",
              verdict_rule="descriptive", beta=round(float(np.log10(max(1, big) / max(1, small))), 3),
              ci_lo=None, ci_hi=None, p=None, n=int(len(IV)),
              largest={k: v for k, v in sorted(units.items(), key=lambda kv: -kv[1])[:3]},
              smallest={k: v for k, v in sorted(units.items(), key=lambda kv: kv[1])[:3]},
              note="rows in each corpus's first four shards, not the corpus totals, because a total would need a "
                   "different read of every file; the ratio is the point - pooling across these units would be "
                   "comparing trajectories with questions")
    h2["verdict"] = "measured_descriptively_no_band_was_frozen"
    h3 = dict(hypothesis="H3", term="construct_by_corpus_availability_matrix", verdict_rule="descriptive",
              matrix=matrix, per_construct_totals={k: sum(v[k] for v in matrix.values())
                                                   for k in CONSTRUCT_FIELDS},
              beta=float(np.mean([sum(v.values()) for v in matrix.values()]) / len(CONSTRUCT_FIELDS)),
              ci_lo=None, ci_hi=None, p=None, n=int(len(IV)),
              note="availability is whether the fields a construct was tested on exist in that corpus, read from the "
                   "column names the release itself spells - a claim about what could be asked, not about what is true")
    h3["verdict"] = "measured_descriptively_no_band_was_frozen"
    rows = [h1, h2, h3]
    for m in rows:
        m["p_holm"] = None
    return dict(corpora=int(len(IV)), n_clusters=int(len(IV)), cluster_unit="corpus (a descriptive aggregation)",
                models=rows,
                strata=[{"stratification": "corpus", "stratum": str(r["corpus"]), "files": int(r["files"]),
                         "rows_in_first_four_files": int(r["rows_in_first_four_files"]),
                         "n_columns": int(r["n_columns"]),
                         "outcome_or_quality_column": int(r["outcome_or_quality_column"])}
                        for _i, r in IV.iterrows()],
                baselines=[{"model": "labels_present", "dv": "corpora", "n": int(len(IV)), "value": labelled},
                           {"model": "constructs_available_per_corpus", "dv": "corpora",
                            "mean_constructs": round(float(np.mean([sum(v.values()) for v in matrix.values()])), 2)}],
                descriptive_rates={"inventory": {str(r["corpus"]): {"files": int(r["files"]),
                                                                    "rows_in_first_four_files":
                                                                        int(r["rows_in_first_four_files"]),
                                                                    "columns": str(r["columns"]).split("|")[:14]}
                                                 for _i, r in IV.iterrows()},
                                   "construct_totals": {k: int(sum(v[k] for v in matrix.values()))
                                                         for k in CONSTRUCT_FIELDS}},
                gate_scope=TD12.DESIGNS["T036"]["gate_scope"])


DESIGN_FN = {"EXP-0216": ("T184", t184), "EXP-0217": ("T189", t189), "EXP-0218": ("T194", t194),
             "EXP-0219": ("T036", t036)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--only", action="append", default=[])
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    fr = load()
    todo = {k: v for k, v in DESIGN_FN.items() if not a.only or k in a.only}
    bad = [k for k in (a.only or []) if k not in DESIGN_FN]
    if bad:
        raise SystemExit(f"ABORT: --only names no design: {bad}; valid ids are {sorted(DESIGN_FN)}")
    for exp, (topic, fn) in todo.items():
        art = fn(fr)
        for m in art.get("models") or []:
            for k in ("beta", "se", "ci_lo", "ci_hi", "p", "p_holm", "n", "clusters"):
                m.setdefault(k, None)
            try:
                width = (m.get("ci_hi") or 0) - (m.get("ci_lo") or 0)
                # quasi-separation shows as an enormous coefficient AND an enormous interval; a plain difference of
                # means can be large in natural units without either, so both must be absurd before it is withheld
                if m.get("beta") is not None and abs(float(m["beta"])) > 8.0 and float(width) > 50.0:
                    m["unidentified_estimate"] = {k: m.get(k) for k in ("beta", "se", "ci_lo", "ci_hi")}
                    m["beta"] = m["se"] = m["ci_lo"] = m["ci_hi"] = None
                    m["verdict"] = "not_estimable_quasi_separation_in_this_cell"
            except (TypeError, ValueError):
                pass
        lack = [k for k in ("models", "strata", "descriptive_rates", "baselines") if not art.get(k)]
        if lack:
            raise SystemExit(f"ABORT {exp} ({topic}): the design produced no {lack}, so the package tables that read "
                             f"those blocks would ship a header with no numbers - measure it or drop the table")
        nofv = [m.get("hypothesis") or m.get("term") for m in art["models"] if not m.get("verdict")]
        if nofv:
            raise SystemExit(f"ABORT {exp} ({topic}): hypotheses {nofv} carry no verdict")
        art.update(exp_id=exp, topic=topic, seed=TD12.SEED, quick=a.quick, started_at=W.now(),
                   frame_files_read={k: v.attrs.get("frame_file") for k, v in fr.items()},
                   blocked_designs_in_this_wave=list(TD12.BLOCKED_BY_GATE),
                   claim_limited_in_this_wave={k: list(v) for k, v in TD12.CLAIM_LIMITED.items()},
                   invocation=" ".join([sys.executable] + sys.argv),
                   run_cost=W.run_cost_row(exp, t0, int(len(fr["C"])), int(fr["C"].shape[1]), "wave-12 design"),
                   finished_at=W.now())
        print(f"{exp} ({topic}): wrote {W.write_raw(exp, f'wave12_design_{exp[-4:]}', art).name}", flush=True)
        pd.DataFrame(art.get("models") or []).to_csv(W.OUT / f"EXP{exp[-4:]}_{topic.lower()}_models.csv",
                                                     index=False, encoding="utf-8")
        if art.get("strata"):
            pd.DataFrame(art["strata"]).to_csv(W.OUT / f"EXP{exp[-4:]}_{topic.lower()}_strata.csv", index=False,
                                               encoding="utf-8")
        print("  " + json.dumps({m.get("hypothesis"): m.get("verdict") for m in art["models"]},
                                default=str)[:280], flush=True)
    print(f"wallclock {round(time.time() - t0, 1)}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
