"""EXP-0189: the E00-E19 battery for wave 7, run by the same step loop as waves 2, 4, 5 and 6.

The single-frame steps (ablation, scaling, replication, error taxonomy, per-config headline) come from
`exp_wave1_battery` through `exp_wave2_battery.run_battery`, so an ablation in wave 7 is the computation it is in wave
2. What wave 7 supplies is its frames and the steps whose subject is a catalogue: the ranker-invariance arm, which
re-ranks every dev catalogue with the estate's own BM25 under three document definitions and asks whether the wave's
dependent variable survives the instrument that produced it; a second instrument for each lexical construct; the
transfer of those instruments to the other local release that carries tool names; the within-stratum permutation as
the counterfactual this corpus can run; and the description-duplication census.

    python 02_shared_code/package_factory/exp_wave7_battery.py [--quick]
"""
from __future__ import annotations

import gzip
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np                                                # noqa: E402
import pandas as pd                                               # noqa: E402
import wave_lib as W                                              # noqa: E402
import exp_wave2_battery as B2                                    # noqa: E402
import exp_wave5_designs as D5                                    # noqa: E402  (kappa: one statistic, all waves)
import exp_wave7_designs as D7                                    # noqa: E402
import probe_wave7_premises as P7                                 # noqa: E402
import topic_designs_wave7 as TD7                                 # noqa: E402

EXP = "EXP-0189"
CTRL = D7.CTRL
CTRL_PAIR = D7.CTRL_PAIR
CLUSTER = D7.CLUSTER
HERMES_FRAME = "EXP0164_wave5_step_features.csv.gz"
RANKER_MODES = ("full", "desc", "name")           # three document definitions of the same catalogue, fixed before
E06_DRAWS = 200                                   # cluster-bootstrap draws for an agreement statistic

SPEC = {
    "T161": dict(frame="queries", y="fail_at_1", x="decoy_present", family="binomial", covars=CTRL,
                 cluster=CLUSTER, permute_within="cand_quartile"),
    "T162": dict(frame="queries", y="fail_at_1", x="afford_density_z", family="binomial", covars=CTRL,
                 cluster=CLUSTER, permute_within="cand_quartile"),
    "T164": dict(frame="queries", y="fail_at_1", x="namespaced_z", family="binomial", covars=CTRL,
                 cluster=CLUSTER, permute_within="cand_quartile"),
    "T165": dict(frame="opairs", y="jaccard", x="same_server", family="gaussian", covars=CTRL_PAIR, cluster="tool",
                 permute_within="server"),
    "T166": dict(frame="queries", y="margin_z", x="contaminated", family="gaussian", covars=CTRL,
                 cluster=CLUSTER, permute_within="cand_quartile"),
    "T169": dict(frame="paired_queries", y="fail_at_1", x="pair_frequent", family="binomial", covars=CTRL,
                 cluster=CLUSTER, permute_within="cand_quartile"),
}


def frames() -> dict:
    fr = D7.load()
    F = fr["F"]
    return {"queries": F, "opairs": fr["O"],
            "paired_queries": F[F["top_pair"].fillna("") != ""],
            "servers": fr["S"], "pairs": fr["P"], "roster": fr["R"]}


def e06_second_instrument(fr: dict) -> dict:
    """Each wave-7 construct measured a second way, and the list of constructs that have only one form.

    Two of the pairs below are deliberately *discriminant* rather than convergent: a construct and the thing it must
    not be confused with, whose agreement is exactly what a design's control assumes.
    """
    out = []

    def rho(d, label, a, b, note, cluster=CLUSTER):
        dd = d[[a, b, cluster]].dropna()
        if dd.empty or dd[a].nunique() < 3 or dd[b].nunique() < 3:
            out.append({"construct": label, "status": "one instrument is near-degenerate on these rows, so no rank "
                        "correlation is claimed", "n": int(len(dd)), "note": note})
            return
        r = dict(W.rho_ci(dd, cluster, a, b))
        r.update(construct=label, n=int(len(dd)), clusters=int(dd[cluster].nunique()), note=note)
        out.append(r)

    def kappa(d, label, a, b, note, cluster=CLUSTER):
        dd = d[[a, b, cluster]].dropna()
        if dd.empty or dd[a].nunique() < 2 or dd[b].nunique() < 2:
            out.append({"construct": label, "status": "one instrument is constant on these rows, so no agreement "
                        "statistic exists", "n": int(len(dd)), "note": note})
            return
        boot = W.cluster_boot_ci_and_p(dd, cluster, lambda x: D5.EF.kappa(x[a], x[b]), draws=E06_DRAWS,
                                       seed=TD7.SEED)
        rec = {"construct": label, "kappa": D5.EF.kappa(dd[a], dd[b]),
               "agreement": round(float((dd[a] == dd[b]).mean()), 4), "n": int(len(dd)),
               "clusters": int(dd[cluster].nunique()), "note": note}
        rec["ci"] = ([round(float(v), 4) for v in boot["ci"]] if "ci" in boot else None)
        if "error" in boot:
            rec["boot_note"] = boot["error"]
        out.append(rec)

    F = fr["queries"]
    F = F.assign(params_by_word_count=(F["gold_param_words"] > 0).astype(int))
    O = fr["opairs"]
    kappa(F, "parameterisation: the release's parameter list vs a count of its content words", "gold_has_params",
          "params_by_word_count", "a parameter named with a stop word or shorter than three characters is present to "
                                   "the indicator and invisible to the counter, so the two can disagree")
    rho(F, "affordance language: density vs raw verb count", "affordance_density", "affordance_verbs",
        "the density is the count per content word, so this is the normalisation check T162's H1 rests on")
    rho(F, "affordance language against description length (discriminant)", "afford_density_z", "desc_words_log",
        "T162's H3 asks whether density is nothing but length: a strong association here is the negative result for "
        "the construct, not for the pair")
    rho(F, "decoy pressure: maximised similarity vs a randomly chosen candidate's", "max_sim_z", "ctrl_sim_z",
        "T161's specificity arm is this pair; the two differ only in how the non-gold candidate was picked")
    rho(F, "grouping: separator share vs the number of servers it implies", "namespaced_z", "servers_z",
        "T164's H3 claims the second of these carries the first, so the size of this correlation is part of what "
        "that hypothesis means")
    rho(F, "contamination: ranked above the gold vs present anywhere", "contaminated", "irrelevant_share_z",
        "T166's H1 is about the ranking; the share is about the catalogue, and only one of them is a ranker's act")
    rho(F, "the wave's two standard controls against each other", "log_candidates", "question_words_log",
        "if the size of a catalogue tracked the length of the instruction, every model holding both fixed would be "
        "reading nearly the same variance twice")
    rho(O, "overlap against the smaller side's word count", "jaccard", "partner_words",
        "a Jaccard over content-word sets is bounded by how much text each side has, and the regression controls it",
        cluster="tool")
    return {"pairs": out,
            "single_instrument_constructs": [
                "the ranker's outcome (fail-at-1, best rank, margin): the release ships one frozen scorer, so the "
                "second instrument is a re-run of that scorer under different document definitions, which is what "
                "ranker_invariance below reports rather than a different model",
                "goldness (the release's own index list; no second annotation of any catalogue exists locally)",
                "namespace (one separator rule over the tool name; a second reading would need a server registry the "
                "release does not carry)"],
            "ranker_invariance": e06b_ranker_invariance(),
            "note": "a construct with one operationalisation is listed, not silently dropped"}


def e06b_ranker_invariance(limit: int = 0) -> dict:
    """Re-rank every dev catalogue with the estate's own BM25 under three document definitions.

    The wave's dependent variable is a ranker's act, so the instrument that decides it is the one claim in this
    programme that can be re-run rather than re-annotated: same rows, same scorer, three different answers to
    "what is a candidate's document" - name plus description plus parameters, description alone, name alone. The
    agreement with the release's own fail-at-1 is the measurement, and the tie count beside it says how much of any
    disagreement the frozen tie-break could have produced on its own.
    """
    t0 = time.time()
    df = W.load_routing(cols=None)
    if limit:
        df = df.sample(min(limit, len(df)), random_state=TD7.SEED)
    arms = {m: [] for m in RANKER_MODES}
    rel = []
    ties = 0
    mismatches = 0
    for r in df.itertuples(index=False):
        try:
            ent = W.read_catalog(r.catalog_json, None, str(r.uuid))
        except AssertionError:                                     # a catalogue whose own count disagrees is counted
            mismatches += 1
            continue
        if not ent:
            continue
        gold = sorted({int(i) for i in (r.gold_idx or []) if str(i).lstrip("-").isdigit()} & set(range(len(ent))))
        if not gold:
            continue
        rel.append(int(r.fail_at_1))
        for m in RANKER_MODES:
            s = W.bm25_matrix(str(r.question), ent, mode=m)
            rk = W.rank_from(s)
            best = int(min(rk[i] for i in gold))
            arms[m].append(int(best != 1))
            if m == "full":
                top = max(s[i] for i in gold)
                ties += int(sum(1 for v in s if v == top and top > 0) > 1)
    a_rel = np.array(rel)
    out = {"modes": {m: {"rows": len(arms[m]),
                         "fail_at_1_share": round(float(np.mean(arms[m])), 4),
                         "agreement_with_the_release": round(float(np.mean(np.array(arms[m]) == a_rel)), 4),
                         "kappa_with_the_release": D5.EF.kappa(pd.Series(arms[m]), pd.Series(a_rel))}
                   for m in RANKER_MODES},
           "release_fail_at_1_share": round(float(a_rel.mean()), 4),
           "gold_tied_at_the_top_rows": int(ties),
           "catalogue_count_mismatches_skipped": int(mismatches),
           "rows_read": int(len(df)), "rows_scored": int(len(rel)),
           "wallclock_sec": round(time.time() - t0, 1),
           "reading": "the three arms are the same scorer on the same rows and differ only in what counts as a "
                      "candidate's document, so how far the miss rate moves between them is the part of every "
                      "wave-7 coefficient that belongs to the instrument rather than to the catalogue"}
    return out


def e08_external(fr: dict) -> dict:
    """The wave's lexical instruments run on the other local release that carries tool names at all.

    hermes logs a named tool call per assistant turn and no candidate catalogue, so the separator rule and the
    affordance-verb list transfer as definitions and their prevalences are measurable - but there is nothing to rank,
    so no outcome and no association transfers.
    """
    path = next((p for p in (W.OUT / HERMES_FRAME, W.ROOT / "results_processed" / HERMES_FRAME) if p.is_file()), None)
    if path is None:
        return {"status": "not attempted: the wave-5 frame is not on disk, so the other release was not read",
                "looked_for": [str(W.OUT / HERMES_FRAME)], "arms": {}}
    H = pd.read_csv(gzip.open(path, "rt", encoding="utf-8"))
    names = H["first_call_name"].dropna().astype(str)
    inst = fr["queries"]
    cat = []
    for r in W.load_routing(cols=["catalog_json", "n_candidates", "uuid"]).head(2000).itertuples(index=False):
        cat.extend(n for n in (c["name"] for c in P7.entries(r.catalog_json)))
    return {"corpus": "hermes-agent-reasoning-traces as measured for waves 4-5 (EXP-0164 frame): one named tool call "
                      "per assistant turn, no candidate catalogue and no ranker",
            "named_actions": int(len(names)),
            "instruments": {"namespace_separator_rule": "P7.NS_SEP over the name: dot, underscore or ::",
                            "affordance_verb_list": "the frozen 38-verb list, word-boundary form"},
            "prevalences_external": {
                "names_carrying_a_namespace_separator": round(float(sum(1 for n in names if P7.NS_SEP.search(n))
                                                                    / max(1, len(names))), 4),
                "names_containing_an_affordance_verb": round(float(sum(1 for n in names if P7.AFFORD_RX.search(
                    n.lower())) / max(1, len(names))), 4),
                "distinct_servers_among_the_names": int(len({P7.server_of(n) for n in names}))},
            "prevalences_wave7_candidate_names": {
                "names_carrying_a_namespace_separator": round(float(sum(1 for n in cat if P7.NS_SEP.search(n))
                                                                    / max(1, len(cat))), 4),
                "names_containing_an_affordance_verb": round(float(sum(1 for n in cat if P7.AFFORD_RX.search(
                    n.lower())) / max(1, len(cat))), 4),
                "distinct_servers_among_the_names": int(len({P7.server_of(n) for n in cat}))},
            "candidate_names_sampled": int(len(cat)),
            "mean_content_words_per_name": round(float(np.mean([len(P7.words(n)) for n in names[:5000]])), 3),
            "what_transfers": "the lexical instruments themselves, unchanged, applied to a different release's "
                              "naming practice",
            "what_does_not": "no outcome transfers. The other release offers no candidate set, so there is no rank, "
                             "no margin and no gold-against-rival comparison to compute - a wave-7 coefficient cannot "
                             "be reproduced there in principle, which is why this step reports prevalences only",
            "arms": {}}


def e17_counterfactual(fr: dict) -> dict:
    """The intervention this wave can run: destroy the construct's placement, keep its dose.

    A recorded ranking cannot be re-run against a different catalogue without a model, which the programme forbids, so
    each design's manipulated term is redistributed *within* the stratum that its own model holds fixed. A candidate
    set's decoy count, namespace share or contamination is a property of the catalogue-question pair, so permuting it
    inside a same-size catalogue stratum keeps the marginal dose and breaks the pairing.
    """
    rng = np.random.default_rng(TD7.SEED)

    def fit(d, sp):
        f = D7.glm(d, sp["y"], [sp["x"]] + sp["covars"], sp["family"], cluster=sp["cluster"])
        if f is None or f.empty:
            return None
        r = f[f["term"] == sp["x"]]
        return None if r.empty else [round(float(r.iloc[0]["beta"]), 4), round(float(r.iloc[0]["ci_lo"]), 4),
                                     round(float(r.iloc[0]["ci_hi"]), 4)]
    arms = []
    for topic, sp in SPEC.items():
        F = fr[sp["frame"]]
        w = sp.get("permute_within")
        if w not in F.columns:
            arms.append({"topic": topic, "term": sp["x"],
                         "note": f"the permutation stratum {w!r} is not a column of this frame, so no arm is offered"})
            continue
        perm = F.copy()
        perm[sp["x"]] = F.groupby(w, observed=True)[sp["x"]].transform(lambda s: rng.permutation(s.to_numpy()))
        arms.append({"topic": topic, "term": sp["x"], "on_outcome": sp["y"],
                     "permuted_within": w, "as_frozen": fit(F, sp),
                     "construct_permuted_within_stratum": fit(perm, sp), "rows": int(len(F)),
                     "strata": int(F[w].nunique())})
    return {"instrument": "the same frozen model on the same rows, with the construct permuted inside each "
                          "same-size-catalogue stratum",
            "arms": arms,
            "note": "a rewrite arm is not offered because a catalogue cannot be re-ranked against a rewritten "
                    "description without a model; permuting within the stratum the model already holds fixed keeps "
                    "the dose and the composition and destroys only which question the construct belongs to, so a "
                    "coefficient that survives is not a property of the stratum"}


def e19_description_duplication(fr: dict) -> dict:
    """How many distinct descriptions stand behind the 222,770 candidate slots, across how many servers."""
    R = fr["roster"]
    g = R.groupby("desc_sha")
    sizes, nsrv = g.size(), g["server"].nunique()
    F = fr["queries"]
    return {"tools": int(len(R)), "candidate_slots": int(R["times_offered"].sum()),
            "distinct_description_signatures": int(g.ngroups),
            "signatures_carried_by_2plus_tools": int((sizes >= 2).sum()),
            "signatures_spanning_2plus_servers": int((nsrv >= 2).sum()),
            "largest_signature_group": int(sizes.max()),
            "share_of_tools_that_share_their_description_with_another_tool":
                round(float((R["desc_sha"].map(sizes) >= 2).mean()), 4),
            "queries_whose_catalogue_holds_a_near_synonym_decoy": round(float(F["decoy_present"].mean()), 4),
            "mean_decoys_per_query": round(float(F["decoy_count"].mean()), 3),
            "rule": "a signature is the sorted set of a description's content words, so two tools that permute the "
                    "same words collide by construction - which is the copy-detection a catalogue claim has to "
                    "survive before 'specialisation' can be claimed about it"}


def shared(fr: dict, quick: bool = False) -> dict:
    return {"e06_second_instrument": e06_second_instrument(fr),
            "e08_external": e08_external(fr),
            "e17_counterfactual": e17_counterfactual(fr),
            "e19_contamination": e19_description_duplication(fr)}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    B2.run_battery(EXP, "wave7_battery_0189", frames, SPEC, shared, quick="--quick" in sys.argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
