"""EXP-0221: the E00-E19 battery for wave 12, on the same step loop as waves 2 and 4 through 11.

Wave 12 spreads across three corpora and an inventory, so the battery's shared steps carry more of its evidence than
usual: a second reading of the reflection and correction instruments, the transfer of the marker sets to a corpus with
a different author, the within-stratum permutation as the counterfactual, and a duplication audit of the action text
itself - because a claim that code is dense only means something if the code is not one template repeated.

    python 02_shared_code/package_factory/exp_wave12_battery.py [--quick]
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
import exp_wave12_designs as D12                                  # noqa: E402
import exp_wave10_features as E10                                 # noqa: E402  requirement extraction, unchanged
import probe_wave11_premises as P11                               # noqa: E402
import probe_wave12_premises as P12                               # noqa: E402
import topic_designs_wave12 as TD12                               # noqa: E402

EXP = "EXP-0221"
CLUSTER = "conversation_id"
E06_DRAWS = 200


def frames() -> dict:
    fr = D12.load()
    g = fr["R"].merge(fr["NE"][["rollout_index", "best_neighbour_similarity"]], on="rollout_index", how="left")
    g["log_steps"] = np.log1p(g["n_steps"].astype(float))
    return {"codeact": fr["C"], "mmat": fr["M"], "swe": g, "siblings": fr["SI"], "inventory": fr["IV"]}


def e06_second_instrument(fr: dict) -> dict:
    C, M, g = fr["codeact"], fr["mmat"], fr["swe"]
    out = []

    def rho(d, label, a, b, note, cluster=CLUSTER):
        dd = d[[a, b, cluster]].dropna() if cluster in d.columns else d[[a, b]].dropna()
        if dd.empty or dd[a].nunique() < 3 or dd[b].nunique() < 3:
            out.append({"construct": label, "status": "one instrument is near-degenerate on these rows",
                        "n": int(len(dd)), "note": note})
            return
        r = dict(W.rho_ci(dd, cluster if cluster in dd.columns else dd.columns[0], a, b))
        r.update(construct=label, n=int(len(dd)), note=note)
        out.append(r)

    def kappa(d, label, a, b, note, cluster=CLUSTER):
        dd = d[[a, b, cluster]].dropna()
        if dd.empty or dd[a].nunique() < 2 or dd[b].nunique() < 2:
            out.append({"construct": label, "status": "one instrument is constant on these rows", "n": int(len(dd)),
                        "note": note})
            return
        kb = W.cluster_boot_ci_and_p(dd, cluster, lambda x: EF5.kappa(x[a], x[b]), draws=E06_DRAWS, seed=TD12.SEED)
        rec = {"construct": label, "kappa": EF5.kappa(dd[a], dd[b]),
               "agreement": round(float((dd[a] == dd[b]).mean()), 4), "n": int(len(dd)), "note": note}
        rec["ci"] = ([round(float(v), 4) for v in kb["ci"]] if "ci" in kb else None)
        out.append(rec)

    kappa(C.assign(is_code=(C["kind"] == "code").astype(int), has_block=(C["code_blocks"] > 0).astype(int)),
          "action kind from the classifier vs the raw presence of an execute block", "is_code", "has_block",
          "T184's independent variable is the kind; if the classifier and the literal block disagreed the "
          "comparison would be between labels, not between actions", cluster="conversation_id")
    rho(C, "turn length against its content-word count", "chars", "content_words",
        "density is a ratio of these two, so the pair is the denominator audit of T184's H1", cluster="conversation_id")
    rho(M, "a marker in the earlier thought against a marker in the later one", "marker_before", "marker_after",
        "T189's two readings of 'after a marker' (W12-D05) - how often a pair carries one, the other or both")
    rho(g, "neighbour similarity against the rollout's own step count", "best_neighbour_similarity", "log_steps",
        "T194's H3 would be meaningless if similarity were carried by task difficulty alone, and step count is its "
        "proxy in this corpus", cluster="instance_id")
    rho(fr["siblings"], "sibling issue similarity against sibling command similarity", "issue_similarity",
        "command_similarity", "the quantity H2 could not test because the issue side is constant; the pair is "
                              "reported here as measured", cluster="instance_id")
    return {"pairs": out,
            "single_instrument_constructs": [
                "correctness (absent from both the code-act and MMAT releases, which is why neither design claims it)",
                "the retrieval of a past case (no timestamp and no case column anywhere in the SWE draw - G10 fired)",
                "corpus labels in T036's inventory, which reads the column names a release spells and has no second "
                "source to check them against"],
            "note": "a construct with one operationalisation is listed, not silently dropped"}


def e08_external(fr: dict) -> dict:
    """The marker sets run on a different author: human instructions, agent turns, and the MMAT operator loop."""
    df = W.load_routing(cols=None)
    head = df["question"].astype(str).head(4000)
    human = {"reflection_marker": round(float(sum(1 for q in head if P12.REFLECT_RX.search(q)) / max(1, len(head))), 4),
             "error_string": round(float(sum(1 for q in head if P12.ERROR_RX.search(q)) / max(1, len(head))), 4),
             "mean_content_words": round(float(np.mean([len(P12.words(q)) for q in head])), 2)}
    M = fr["mmat"]
    C = fr["codeact"]
    return {"corpus": "P001 routing release dev instructions (4,000 rows), human-authored task text",
            "instruments": {"reflection": "probe_wave12_premises.REFLECT_RX, unchanged",
                            "error": "probe_wave12_premises.ERROR_RX, unchanged"},
            "prevalences_human_instructions": human,
            "prevalences_mmat_transitions": {"reflection_marker_share": round(float(M["marker_after"].mean()), 4),
                                             "mean_jaccard": round(float(M["jaccard"].mean()), 4)},
            "prevalences_codeact_turns": {"error_in_own_text_share": round(float(C["own_reports_error"].mean()), 4),
                                          "answered_turn_share": round(float(C["has_observation"].mean()), 4),
                                          "kinds": {str(k): int(v) for k, v in C["kind"].value_counts().items()}},
            "what_transfers": "both marker lists, unchanged, across three corpora with different authors",
            "what_does_not": "the unit. An instruction has no successor turn, so nothing about what a marker is "
                             "*followed by* can be measured in the human text - which is exactly why the reflection "
                             "claim needs a trace corpus and cannot be made from prompts",
            "arms": {}}


def e17_counterfactual(fr: dict) -> dict:
    rng = np.random.default_rng(TD12.SEED)
    spec = {"T184": dict(frame="codeact", y="density_per_1000", x="has_observation", family="gaussian",
                         covars=[], cluster="conversation_id", permute_within="kind"),
            "T189": dict(frame="mmat", y="jaccard", x="marker_before", family="gaussian", covars=[],
                         cluster="conversation_index", permute_within="operator_after"),
            "T194": dict(frame="swe", y="log_steps", x="best_neighbour_similarity", family="gaussian", covars=[],
                         cluster="instance_id", permute_within="repo")}

    def fit(d, sp):
        f = D12.glm(d, sp["y"], [sp["x"]] + sp["covars"], sp["family"], sp["cluster"])
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
            arms.append({"topic": topic, "term": sp["x"], "note": f"no column {w!r} to permute within"})
            continue
        perm = F.copy()
        perm[sp["x"]] = F.groupby(w, observed=True)[sp["x"]].transform(lambda s: rng.permutation(s.to_numpy()))
        arms.append({"topic": topic, "term": sp["x"], "on_outcome": sp["y"], "permuted_within": w,
                     "as_frozen": fit(F, sp), "marker_permuted_within_stratum": fit(perm, sp),
                     "rows": int(len(F)), "strata": int(F[w].nunique())})
    return {"instrument": "the same frozen specification on the same rows, with the manipulated term permuted inside "
                          "each stratum it is compared within",
            "arms": arms,
            "note": "no transcript can be re-acted against a different world without a model, so the counterfactual "
                    "is placement-only: it keeps the marginal amount of code, markers and neighbour similarity in each "
                    "kind, operator and repository and destroys which turn or rollout carries it"}


def e19_action_duplication(fr: dict) -> dict:
    C = fr["codeact"]
    dig = C[C["code_blocks"] > 0]["cmd"].value_counts()
    openings = collections.Counter()
    for cid, g in C.sort_values(["conversation_id", "turn_index"]).groupby("conversation_id", sort=True):
        text = " ".join(g[g["code_blocks"] == 0]["cmd"].astype(str))
        openings[hashlib.sha1(re.sub(r"\s+", " ", text).strip().lower().encode("utf-8")).hexdigest()[:16]] += 1
    prose = pd.Series(openings)
    conv = C["conversation_id"].nunique()
    return {"conversations": int(conv), "code_turns": int((C["code_blocks"] > 0).sum()),
            "distinct_executed_blocks": int(dig.size),
            "share_of_code_turns_repeating_a_block": round(float(1 - dig.size / max(1, (C["code_blocks"] > 0).sum())),
                                                           4),
            "most_repeated_block_turns": int(dig.max()) if dig.size else 0,
            "share_of_turns_in_the_twenty_most_repeated_blocks":
                round(float(C[C["cmd"].isin(set(dig.head(20).index))].shape[0] / max(1, len(C))), 4),
            "distinct_nl_openings": int(prose.nunique()) if len(prose) else 0,
            "rule": "one sha1 per whitespace-normalised executed block, and one per conversation's concatenated "
                    "non-code text: a density claim about code is worth little if the code is one template"}


def shared(fr: dict, quick: bool = False) -> dict:
    return {"e06_second_instrument": e06_second_instrument(fr),
            "e08_external": e08_external(fr),
            "e17_counterfactual": e17_counterfactual(fr),
            "e19_contamination": e19_action_duplication(fr)}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    B2.run_battery(EXP, "wave12_battery_0221", frames, {
        "T184": dict(frame="codeact", y="density_per_1000", x="has_observation", family="gaussian", covars=[],
                     cluster="conversation_id"),
        "T189": dict(frame="mmat", y="jaccard", x="marker_before", family="gaussian", covars=[],
                     cluster="conversation_index"),
        "T194": dict(frame="swe", y="log_steps", x="best_neighbour_similarity", family="gaussian", covars=[],
                     cluster="instance_id"),
        "T036": dict(frame="inventory", y="rows_in_first_four_files", x="files", family="gaussian", covars=[],
                     cluster="corpus")}, shared, quick="--quick" in sys.argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
