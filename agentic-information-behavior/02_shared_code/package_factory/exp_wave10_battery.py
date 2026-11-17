"""EXP-0206: the E00-E19 battery for wave 10, on the same step loop as waves 2 and 4 through 9.

One design survived EXP-0203's gates, so the wave's battery is not an appendix to six packages but the instrument
audit of one - and it carries a heavier share of the evidence because of that. The shared steps come from
`exp_wave1_battery` through `exp_wave2_battery.run_battery`; what wave 10 supplies is its frame plus four steps whose
subject is the requirement instrument itself: a second reading of coverage, the transfer of the whole extraction to a
corpus of different instructions, the within-stratum permutation as the counterfactual, and the duplication audit of
a release whose instructions repeat across configs.

    python 02_shared_code/package_factory/exp_wave10_battery.py [--quick]
"""
from __future__ import annotations

import collections
import gzip
import json
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np                                                # noqa: E402
import pandas as pd                                               # noqa: E402
import wave_lib as W                                              # noqa: E402
import exp_wave2_battery as B2                                    # noqa: E402
import exp_wave5_features as EF5                                  # noqa: E402  one kappa, all waves
import exp_wave10_designs as D10                                  # noqa: E402  estimators with this wave's defaults
import exp_wave10_features as E10                                 # noqa: E402  the requirement extractor, unchanged
import probe_wave7_premises as P7                                 # noqa: E402  catalogue reader and content words
import topic_designs_wave10 as TD10                               # noqa: E402

EXP = "EXP-0206"
CTRL = D10.CTRL
CLUSTER = D10.CLUSTER
HERMES_CORPUS = pathlib.Path(str(W.ROOT.parent) + "/MATLABINTOKEN/datasets/lambda/hermes-agent-reasoning-traces")
E06_DRAWS = 200


def frames() -> dict:
    F = D10.load()
    return {"rows": F, "with_requirements": F[F["has_requirements"] == 1].copy(),
            "comparable": F[F["has_2plus_candidates"] == 1].copy()}


def e06_second_instrument(fr: dict) -> dict:
    out = []
    E = fr["with_requirements"]

    def rho(d, label, a, b, note):
        dd = d[[a, b, CLUSTER]].dropna()
        if dd.empty or dd[a].nunique() < 3 or dd[b].nunique() < 3:
            out.append({"construct": label, "status": "one instrument is near-degenerate on these rows", "n": int(len(dd)),
                        "note": note})
            return
        r = dict(W.rho_ci(dd, CLUSTER, a, b))
        r.update(construct=label, n=int(len(dd)), clusters=int(dd[CLUSTER].nunique()), note=note)
        out.append(r)

    def kappa(d, label, a, b, note):
        dd = d[[a, b, CLUSTER]].dropna()
        if dd.empty or dd[a].nunique() < 2 or dd[b].nunique() < 2:
            out.append({"construct": label, "status": "one instrument is constant on these rows", "n": int(len(dd)),
                        "note": note})
            return
        kb = W.cluster_boot_ci_and_p(dd, CLUSTER, lambda x: EF5.kappa(x[a], x[b]), draws=E06_DRAWS, seed=TD10.SEED)
        rec = {"construct": label, "kappa": EF5.kappa(dd[a], dd[b]),
               "agreement": round(float((dd[a] == dd[b]).mean()), 4), "n": int(len(dd)),
               "clusters": int(dd[CLUSTER].nunique()), "note": note}
        rec["ci"] = ([round(float(v), 4) for v in kb["ci"]] if "ci" in kb else None)
        out.append(rec)

    rho(E, "requirement coverage: any-word reading against the half-of-words reading", "coverage_any",
        "coverage_half", "T104's outcome is defined by the loose reading and reported with the strict one beside it; "
                         "how far apart they sit is the width of that definitional choice")
    kappa(E.assign(cov_any_bin=(E["coverage_any"] >= 0.5).astype(int),
                   cov_half_bin=(E["coverage_half"] >= 0.5).astype(int)),
          "a requirement set at least half surfaced, by either reading", "cov_any_bin", "cov_half_bin",
          "the same dichotomy at the 0.5 point, because a share difference can hide a classification agreement")
    rho(E, "underspecification against constraint count (discriminant)", "underspec_index", "constraint_total",
        "T104's H3 is exactly the claim that these are not one quantity: the underspecification index is built from "
          "constraints negatively, so a large negative here is the definition working and a near-zero would be the "
          "index carrying no information beyond the count")
    rho(E, "referential markers against ellipsis (discriminant)", "referential_markers", "ellipsis_n",
        "one points back with no antecedent, the other omits words entirely; T104's H3 treats them as separate kinds")
    rho(E, "requirement count against instruction length", "requirement_n", "question_words",
        "coverage has a denominator, so the count and the length must not be the same axis for the estimate to mean "
        "anything")
    rho(E, "lexical ambiguity against the candidate count it is computed over", "lexical_ambiguity", "n_candidates",
        "a word can only be ambiguous across two servers if two servers are present: this is the confound G2's "
        "single-candidate sixth would have created")
    return {"pairs": out,
            "single_instrument_constructs": [
                "the requirement set of an instruction (one clause-extraction rule; a second would need a parse the "
                "programme's rule-based instruments do not have, and a model is excluded by the protocol)",
                "the gold requirement (the release marks which candidate answers the instruction, not which part of "
                "it); coverage is therefore measured against the whole surfaced catalogue, as the freeze says"],
            "note": "a construct with one operationalisation is listed, not silently dropped"}


def e08_external(fr: dict) -> dict:
    """The extraction and coverage instruments run on a different corpus of instructions.

    hermes carries a task statement and the tool schema that was offered with it, so the same requirement extractor and
    the same coverage rule can be applied with no re-aiming: what transfers is the definition, and the comparison is
    between two corpora's instruction language rather than between two models of it.
    """
    files = sorted(HERMES_CORPUS.glob("data/**/*.parquet"))
    if not files:
        return {"status": "not attempted: no hermes parquet on disk", "looked_for": str(HERMES_CORPUS), "arms": {}}
    import pyarrow.parquet as pq
    rows = []
    for f in files[:2]:
        for b in pq.ParquetFile(f).iter_batches(batch_size=2000, columns=["id", "task", "tools"]):
            rows.extend(b.to_pylist())
    reqs, cov, n = [], [], 0
    for r in rows:
        task = str(r.get("task") or "")
        try:
            tools = json.loads(r.get("tools") or "[]")
        except Exception:                                        # noqa: BLE001 - an unparseable schema is counted
            tools = []
        rr = E10.requirements(task)
        if not rr:
            continue
        cw = [P7.words(str(t.get("description") or "")) for t in tools if isinstance(t, dict)]
        a, _b = E10.coverage(rr, cw)
        if a == a:
            reqs.append(len(rr))
            cov.append(a)
            n += 1
    F = fr["rows"]
    return {"corpus": "hermes-agent-reasoning-traces: a task statement plus the tool schema offered with it",
            "instructions_read": len(rows), "instructions_with_requirements": n,
            "mean_requirements": round(float(np.mean(reqs)), 3) if reqs else None,
            "mean_coverage_any": round(float(np.mean(cov)), 4) if cov else None,
            "coverage_at_least_half_share": round(float(np.mean([c >= 0.5 for c in cov])), 4) if cov else None,
            "routing_release_for_comparison": {
                "instructions_with_requirements": int(F["has_requirements"].sum()),
                "mean_requirements": round(float(F.loc[F["has_requirements"] == 1, "requirement_n"].mean()), 3),
                "mean_coverage_any": round(float(F.loc[F["has_requirements"] == 1, "coverage_any"].mean()), 4)},
            "what_transfers": "the clause extraction, the content-word rule and the coverage test, unchanged",
            "what_does_not": "the candidate catalogue: hermes offers a tool schema per task and no ranked candidate "
                             "set, so no outcome of this wave - coverage, miss at rank 1 - exists to compare there",
            "arms": {}}


def e17_counterfactual(fr: dict) -> dict:
    rng = np.random.default_rng(TD10.SEED)
    spec = {"T104": dict(frame="with_requirements", y="coverage_any_z", x="underspec_z", family="gaussian",
                         covars=CTRL, cluster=CLUSTER, permute_within="cand_quartile")}

    def fit(d, sp):
        f = D10.glm(d, sp["y"], [sp["x"]] + sp["covars"], sp["family"], cluster=sp["cluster"])
        if f is None or f.empty:
            return None
        r = f[f["term"] == sp["x"]]
        return None if r.empty else [round(float(r.iloc[0]["beta"]), 4), round(float(r.iloc[0]["ci_lo"]), 4),
                                     round(float(r.iloc[0]["ci_hi"]), 4)]
    arms = []
    for topic, sp in spec.items():
        F = fr[sp["frame"]]
        perm = F.copy()
        perm[sp["x"]] = F.groupby(sp["permute_within"], observed=True)[sp["x"]].transform(
            lambda s: rng.permutation(s.to_numpy()))
        arms.append({"topic": topic, "term": sp["x"], "on_outcome": sp["y"], "permuted_within": sp["permute_within"],
                     "as_frozen": fit(F, sp), "marker_permuted_within_stratum": fit(perm, sp),
                     "rows": int(len(F)), "strata": int(F[sp["permute_within"]].nunique())})
    return {"instrument": "the same frozen model on the same rows, with the underspecification index permuted inside "
                          "each candidate-count quartile",
            "arms": arms,
            "note": "an instruction cannot be re-written without a model, which the programme forbids; permuting "
                    "within the quartile the model conditions on keeps the catalogue size and the distribution of "
                    "uncertainty and destroys only which instruction carries how much of it"}


def e19_duplication(fr: dict) -> dict:
    F = fr["rows"]
    q = F["question"].astype(str).str.lower().str.strip().value_counts() if "question" in F.columns else None
    ins = F["prompt_id"].value_counts()
    cfg_per_prompt = F.groupby("prompt_id")["cfg"].nunique()
    return {"instructions_scanned": int(len(F)), "distinct_instruction_strings": int(q.size) if q is not None else None,
            "share_of_rows_that_repeat_an_instruction_seen_elsewhere":
                round(float(1 - q.size / max(1, len(F))), 4) if q is not None else None,
            "most_repeated_instruction_rows": int(q.max()) if q is not None and q.size else 0,
            "prompt_groups": int(ins.size), "mean_rows_per_prompt_group": round(float(ins.mean()), 2) if ins.size else None,
            "max_rows_per_prompt_group": int(ins.max()) if ins.size else 0,
            "prompt_groups_seen_in_all_three_configs": int((cfg_per_prompt == 3).sum()),
            "rule": "the release re-offers one instruction under several model configs, so a row count is not an "
                    "instruction count: the intervals cluster on query_id as the freeze fixes, and this is where the "
                    "difference is recorded rather than assumed away"}


def shared(fr: dict, quick: bool = False) -> dict:
    return {"e06_second_instrument": e06_second_instrument(fr),
            "e08_external": e08_external(fr),
            "e17_counterfactual": e17_counterfactual(fr),
            "e19_contamination": e19_duplication(fr)}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    B2.run_battery(EXP, "wave10_battery_0206", frames, {
        "T104": dict(frame="with_requirements", y="coverage_any_z", x="underspec_z", family="gaussian",
                     covars=CTRL, cluster=CLUSTER)}, shared, quick="--quick" in sys.argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
