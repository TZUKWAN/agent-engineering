"""EXP-0204: T104's pre-registered test, run from the frozen sentences in topic_designs_wave10.

Wave 10 came in with six designs and EXP-0203's G2 stopped five of them before any association was estimated: 0.8376
of the release's instructions offer two or more candidates against the 0.90 the sentences that compare candidates
froze, and the surviving cell was not substituted under their names (deviation W10-D01). What runs here is T104,
whose outcome is a comparison between instructions rather than between candidates, and whose own floors the census
measured as met.

Estimators are the shared wave-7 ones with this wave's cluster and control defaults re-bound, the lesson wave 8 and
wave 9 each recorded once.

    python 02_shared_code/package_factory/exp_wave10_designs.py [--quick]
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
import topic_designs_wave10 as TD10                               # noqa: E402
import exp_wave9_designs as D9                                    # noqa: E402  the estimators, one chain of wrappers

assert TD10.BANDS == W.BANDS, "the wave-10 freeze and wave_lib disagree about the effect bands"
BAND = W.BANDS["medium"]
BAND_SMALL = W.BANDS["small"]
CLUSTER = TD10.COMMON["sample"]["cluster_unit"]                   # "query_id"
FRAME = "EXP0205_wave10_requirement_features.csv.gz"
CTRL = ["log_candidates", "question_words_log"]                   # the freeze's controls: catalogue size and length
term, holm_and_verdict, z = D9.term, D9.holm_and_verdict, D9.z


def glm(d, y, xs, family="binomial", cluster=CLUSTER):
    return D9.glm(d, y, xs, family, cluster)


def baselines(d, y, specs, family="binomial", controls=None, cluster=CLUSTER):
    return D9.baselines(d, y, specs, family, controls or CTRL, cluster)


def strata_rows(d, splits, y, xs, focus, min_rows=1000, family="binomial", cluster=CLUSTER):
    return D9.strata_rows(d, splits, y, xs, focus, min_rows, family, cluster)


def boot(d, cluster, fn, draws: int = 1000) -> dict:
    return W.cluster_boot_ci_and_p(d, cluster, fn, draws=draws, seed=TD10.SEED)


def load() -> pd.DataFrame:
    search = []
    if os.environ.get("AIB_INPUT_DIR"):
        search.append(pathlib.Path(os.environ["AIB_INPUT_DIR"]) / FRAME)
    search += [W.OUT / FRAME, W.ROOT / "results_processed" / FRAME]
    path = next((q for q in search if pathlib.Path(q).is_file()), None)
    if path is None:
        raise SystemExit(f"ABORT: {FRAME} is not where the designs look ({', '.join(map(str, search))}) - run "
                         f"{TD10.FEATURE_EXP} (exp_wave10_features.py) first")
    F = pd.read_csv(gzip.open(path, "rt", encoding="utf-8"))
    need = ["query_id", "cfg", "n_candidates", "fail_at_1", "bm25_best_rank", "candidates_before_gold",
            "requirement_n", "requirement_words", "coverage_any", "coverage_half", "underspec_index", "underspec_z",
            "constraint_total", "constraint_total_z", "unresolved_ref", "ellipsis_n", "entity_density",
            "question_words", "question_words_log", "log_candidates", "lexical_ambiguity", "lex_amb_z",
            "referential_markers", "ref_mark_z", "has_2plus_candidates", "cand_quartile", "req_band"]
    miss = [c for c in need if c not in F.columns]
    if miss:
        raise SystemExit(f"ABORT: the wave-10 frame lacks {miss}; the designs would drop those terms in silence")
    F.attrs["frame_file"] = str(path)
    F["has_requirements"] = (F["requirement_n"] >= 1).astype(int)
    return F


def t104(F: pd.DataFrame) -> dict:
    """Does the amount a instruction leaves unstated predict how little of it the catalogue surfaced?"""
    d = F.dropna(subset=["coverage_any"]).copy()
    est = d[d["has_requirements"] == 1]
    h1 = term(glm(est, "coverage_any_z", ["underspec_z"] + CTRL, "gaussian"), "underspec_z")
    h1.update(hypothesis="H1", term="underspecification_of_the_instruction_on_requirement_coverage",
              instructions_with_requirements=int(len(est)), mean_coverage=round(float(est["coverage_any"].mean()), 4),
              coverage_by_underspec_quartile={
                  str(k): {"mean_coverage_any": round(float(g["coverage_any"].mean()), 4), "rows": int(len(g))}
                  for k, g in est.assign(uq=pd.qcut(est["underspec_index"].rank(method="first"), 4,
                                                    labels=["u1_most_specified", "u2", "u3",
                                                           "u4_least"]).astype(str)).groupby("uq", observed=True)})
    h1["verdict_direction"] = "predicted_negative: less specified instructions surface less of what they need"
    floor = 0.30
    b = boot(est, CLUSTER, lambda x: float(x["coverage_any"].mean()), 1000)
    share = float(est["coverage_any"].mean())
    h2 = dict(hypothesis="H2", term="the_share_of_requirements_surfaced_by_at_least_one_candidate",
              verdict_rule="descriptive", beta=round(share, 4), ci_lo=(b.get("ci") or [None, None])[0],
              ci_hi=(b.get("ci") or [None, None])[1], p=b.get("p"), clusters=b.get("clusters"), n=int(len(est)),
              frozen_floor=floor, strict_reading_mean=round(float(est["coverage_half"].mean()), 4),
              requirements_total=int(est["requirement_n"].sum()),
              note="H2 is a prevalence claim with a floor on the share, so the bootstrap interval is read against the "
                   "floor directly; the strict content-word reading is reported beside it, not instead of it")
    h2["verdict"] = ("supported" if share >= floor and (h2["ci_lo"] or 0) >= floor else
                     f"not_at_or_above_the_frozen_floor_measured_{f'{share:.4f}'.replace('.', 'p')}"
                     if share == share else "not_testable_no_requirements_estimable")
    joint = glm(est, "coverage_any_z", ["underspec_z", "constraint_total_z", "ref_mark_z", "lex_amb_z"] + CTRL,
                "gaussian")
    with_constraints = term(joint, "underspec_z")
    referential = term(joint, "ref_mark_z")
    lexical = term(joint, "lex_amb_z")
    alone = term(glm(est, "coverage_any_z", ["constraint_total_z"] + CTRL, "gaussian"), "constraint_total_z")

    def separates(t):
        return t.get("beta") is not None and t.get("ci_lo") is not None and (t["ci_lo"] > 0 or t["ci_hi"] < 0)

    def nullish(t):
        return t.get("beta") is not None and t.get("ci_lo") is not None and t["ci_lo"] <= 0 <= t["ci_hi"]
    h3 = dict(hypothesis="H3", term="underspecification_against_constraint_count_and_the_two_other_uncertainty_kinds",
              verdict_rule="specificity", underspec_with_constraints=with_constraints,
              constraint_count_alone=alone, referential_term=referential, lexical_term=lexical,
              beta=with_constraints.get("beta"), se=with_constraints.get("se"), ci_lo=with_constraints.get("ci_lo"),
              ci_hi=with_constraints.get("ci_hi"), p=with_constraints.get("p"), n=with_constraints.get("n"),
              note="H3 claims the underspecification index is not the constraint count speaking twice and not the "
                   "other two uncertainty kinds in disguise, so all four enter one specification")
    h3["verdict"] = ("supported" if separates(with_constraints) and nullish(referential) and abs(
        with_constraints.get("beta") or 0) >= BAND_SMALL else
                     "not_specific_another_uncertainty_kind_carries_the_signal" if with_constraints else
                     "not_testable_no_coefficient_estimated")
    rows = holm_and_verdict([h1, h2, h3], {"H1": -1.0, "H2": 1.0, "H3": -1.0})
    return dict(n_rows=int(len(F)), n_clusters=int(F["query_id"].nunique()), cluster_unit=CLUSTER,
                rows_without_a_requirement=int((F["requirement_n"] == 0).sum()),
                single_candidate_rows=int((F["n_candidates"] < 2).sum()), models=rows,
                strata=strata_rows(est, ["cand_quartile", "cfg"], "coverage_any_z", ["underspec_z"] + CTRL,
                                   "underspec_z", family="gaussian", min_rows=1000),
                baselines=baselines(est, "coverage_any_z",
                                    [("controls_only", CTRL, "log_candidates"),
                                     ("controls_plus_underspecification", ["underspec_z"] + CTRL, "underspec_z"),
                                     ("controls_plus_referential_markers", ["ref_mark_z"] + CTRL, "ref_mark_z"),
                                     ("controls_plus_lexical_ambiguity", ["lex_amb_z"] + CTRL, "lex_amb_z")],
                                    family="gaussian"),
                descriptive_rates={"coverage_by_requirement_band": {
                    str(k): {"mean_coverage_any": round(float(g["coverage_any"].mean()), 4),
                             "mean_coverage_half": round(float(g["coverage_half"].mean()), 4), "rows": int(len(g))}
                    for k, g in est.groupby("req_band", observed=True)},
                    "coverage_by_candidate_quartile": {
                        str(k): {"mean_coverage_any": round(float(g["coverage_any"].mean()), 4),
                                 "rows": int(len(g))}
                        for k, g in est.groupby("cand_quartile", observed=True)},
                    "requirement_count_distribution": {str(int(k)): int(v) for k, v in
                                                       F["requirement_n"].value_counts().sort_index().head(12).items()},
                    "strict_and_loose_coverage": {"rho": dict(W.rho_ci(est[["coverage_any", "coverage_half", CLUSTER]]
                                                                       .dropna(), CLUSTER, "coverage_any",
                                                                       "coverage_half")) if est["coverage_half"]
                                                  .nunique() > 2 else None}},
                gate_scope=TD10.DESIGNS["T104"]["gate_scope"])


DESIGN_FN = {"EXP-0204": ("T104", t104)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--only", action="append", default=[])
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    F = load()
    if a.quick:
        F = F.sample(min(20000, len(F)), random_state=TD10.SEED)
    todo = {k: v for k, v in DESIGN_FN.items() if not a.only or k in a.only}
    bad = [k for k in (a.only or []) if k not in DESIGN_FN]
    if bad:
        raise SystemExit(f"ABORT: --only names no design: {bad}; valid ids are {sorted(DESIGN_FN)}")
    for exp, (topic, fn) in todo.items():
        art = fn(F)
        for m in art.get("models") or []:
            for k in ("beta", "se", "ci_lo", "ci_hi", "p", "p_holm", "n"):
                m.setdefault(k, None)
        lack = [k for k in ("models", "strata", "descriptive_rates", "baselines") if not art.get(k)]
        if lack:
            raise SystemExit(f"ABORT {exp} ({topic}): the design produced no {lack}, so the package tables that read "
                             f"those blocks would ship a header with no numbers - measure it or drop the table")
        nofv = [m.get("hypothesis") or m.get("term") for m in art["models"] if not m.get("verdict")]
        if nofv:
            raise SystemExit(f"ABORT {exp} ({topic}): hypotheses {nofv} carry no verdict")
        art.update(exp_id=exp, topic=topic, seed=TD10.SEED, quick=a.quick, started_at=W.now(),
                   frame_file_read=F.attrs.get("frame_file"),
                   blocked_designs_in_this_wave=list(TD10.BLOCKED_BY_GATE),
                   invocation=" ".join([sys.executable] + sys.argv),
                   run_cost=W.run_cost_row(exp, t0, int(len(F)), int(F.shape[1]), "wave-10 design"),
                   finished_at=W.now())
        print(f"{exp} ({topic}): wrote {W.write_raw(exp, f'wave10_design_{exp[-4:]}', art).name}", flush=True)
        pd.DataFrame(art.get("models") or []).to_csv(W.OUT / f"EXP{exp[-4:]}_{topic.lower()}_models.csv",
                                                     index=False, encoding="utf-8")
        if art.get("strata"):
            pd.DataFrame(art["strata"]).to_csv(W.OUT / f"EXP{exp[-4:]}_{topic.lower()}_strata.csv", index=False,
                                               encoding="utf-8")
        print("  " + json.dumps({m.get("hypothesis"): m.get("verdict") for m in art["models"]},
                                default=str)[:260], flush=True)
    print(f"wallclock {round(time.time() - t0, 1)}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
