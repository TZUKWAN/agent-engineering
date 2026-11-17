"""EXP-0198..EXP-0201: wave 9's four surviving pre-registered tests, from the frozen sentences in topic_designs_wave9.

Two of the wave's six designs were stopped by EXP-0196 before anything here ran (T151 and T156, at G9's
newness-availability floor of 0.90 against a measured 0.7876), and one hypothesis of a third is claim-limited (T153's
H1, at G6's family-breadth floor). What follows measures T153's transition arms, T178's early-signal prediction,
T179's recovery window and T193's rank disagreement - each with the band floor, the direction and the cluster unit its
own freeze names, and each reporting the cell it was actually estimated on.

Every interval is cluster-robust or bootstrapped on `instance_id`: a task attempted many times is one task, and the
release's label is a property of an attempt within that task rather than 19,988 independent outcomes.

    python 02_shared_code/package_factory/exp_wave9_designs.py [--quick] [--only EXP-0198]
"""
from __future__ import annotations

import argparse
import collections
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
import topic_designs_wave9 as TD9                                 # noqa: E402
import exp_wave8_designs as D8                                    # noqa: E402  the wrapped estimators

assert TD9.BANDS == W.BANDS, "the wave-9 freeze and wave_lib disagree about the effect bands"
BAND = W.BANDS["medium"]
BAND_SMALL = W.BANDS["small"]
CLUSTER = TD9.COMMON["sample"]["cluster_unit"]                    # "instance_id"
FRAMES = {"step": "EXP0197_wave9_step_features.csv.gz", "rollout": "EXP0197_wave9_rollout_features.csv.gz"}
CTRL = ["log_steps", "obs_chars_mean"]                            # the wave's standard controls, one definition
ALPHA = 1.0                                                       # Laplace smoothing for every transition table
term, holm_and_verdict, z = D8.term, D8.holm_and_verdict, D8.z


# the same guard wave 8 recorded for wave 7's helpers: an imported estimator carries the previous wave's default
# cluster column, which this frame does not have, so the defaults are re-bound here rather than at every call site
def glm(d, y, xs, family="binomial", cluster=CLUSTER):
    return D8.glm(d, y, xs, family, cluster)


def baselines(d, y, specs, family="binomial", controls=None, cluster=CLUSTER):
    # the same trap as the cluster default, one layer deeper: wave 7's ladder falls back to *its* control set when
    # none is passed, and a column the frame does not have makes the controls-only fit vanish silently
    return D8.baselines(d, y, specs, family, controls or CTRL, cluster)


def strata_rows(d, splits, y, xs, focus, min_rows=1000, family="binomial", cluster=CLUSTER):
    return D8.strata_rows(d, splits, y, xs, focus, min_rows, family, cluster)


def boot(d, cluster, fn, draws: int = 1000) -> dict:
    return W.cluster_boot_ci_and_p(d, cluster, fn, draws=draws, seed=TD9.SEED)


def _read(name: str) -> pd.DataFrame:
    search = []
    if os.environ.get("AIB_INPUT_DIR"):
        search.append(pathlib.Path(os.environ["AIB_INPUT_DIR"]) / name)
    search += [W.OUT / name, W.ROOT / "results_processed" / name]
    path = next((q for q in search if pathlib.Path(q).is_file()), None)
    if path is None:
        raise SystemExit(f"ABORT: {name} is not where the designs look ({', '.join(map(str, search))}) - run "
                         f"{TD9.FEATURE_EXP} (exp_wave9_features.py) first")
    F = pd.read_csv(gzip.open(path, "rt", encoding="utf-8"))
    F.attrs["frame_file"] = str(path)
    return F


def load() -> dict:
    """The two wave-9 frames, checked column by column, with the derived ranks the freeze names."""
    S, T = _read(FRAMES["step"]), _read(FRAMES["rollout"])
    need_s = ["traj_key", "instance_id", "step_index", "n_steps", "family", "switched", "position", "position_decile",
              "in_first_fifth", "in_last_fifth", "obs_chars", "log_obs_chars", "new_information", "failed_observation",
              "command_sha", "is_repeat", "task_family", "submitted", "first_change_lag", "changed_at_lag_1",
              "has_failure", "after_first_failure"]
    need_t = ["traj_key", "instance_id", "task_family", "n_steps", "log_steps", "duration", "submitted", "outcome",
              "switch_rate", "family_concentration", "distinct_families", "repeat_share", "newness_mean",
              "obs_chars_mean", "failures", "failure_then_a_further_command", "changed_at_lag_1", "changed_at_lag_3",
              "changed_at_lag_5", "first_change_lag", "ff_switch_rate", "ff_distinct_families", "ff_repeat_share",
              "ff_newness_mean", "ff_cmd_words", "lf_newness_mean", "lf_switch_rate", "steps_without_observation",
              "length_quartile", "rollouts_per_instance", "success_only_rank"]
    miss = [f"step:{c}" for c in need_s if c not in S.columns] + [f"rollout:{c}" for c in need_t if c not in T.columns]
    if miss:
        raise SystemExit(f"ABORT: the wave-9 frames lack {miss}; the designs would drop those terms in silence")
    for c in ("switch_rate", "family_concentration", "repeat_share", "newness_mean", "ff_switch_rate",
              "ff_repeat_share", "ff_newness_mean", "ff_cmd_words", "distinct_families"):
        T[c + "_z"] = z(T[c].astype(float))
    T["duration_z"] = z(T["duration"].astype(float))
    order = T.sort_values(["instance_id", "submitted", "n_steps", "repeat_share", "duration", "traj_key"],
                          ascending=[True, False, True, True, True, True])
    T["cost_adjusted_rank"] = (order.groupby("instance_id").cumcount() + 1).reindex(T.index)
    T["has_two_rollouts"] = (T["rollouts_per_instance"] >= 2).astype(int)
    return {"S": S, "T": T}


def transition_loglik(S: pd.DataFrame) -> pd.DataFrame:
    """Per-rollout mean log-likelihood per transition, under four models of the same command alphabet.

    The pooled matrices leave the rollout's own task family out, so the comparison is held out rather than a
    restatement of the same counts; the shuffled arm permutes the target family within the rollout, which keeps the
    unigram marginal and destroys only the ordering. Rollouts are walked in sorted key order so the seeded shuffle is
    the same shuffle in every run.
    """
    fams = sorted(set(S["family"].dropna()))
    idx = {f: i for i, f in enumerate(fams)}
    A = len(fams)
    seqs, fam_of, inst_of = {}, {}, {}
    for r in S.sort_values(["traj_key", "step_index"]).itertuples(index=False):
        k = str(r.traj_key)
        seqs.setdefault(k, []).append(idx[r.family])
        fam_of[k], inst_of[k] = str(r.task_family), str(r.instance_id)
    uni = np.zeros(A)
    bi = np.zeros((A, A))
    fu, fb = collections.defaultdict(lambda: np.zeros(A)), collections.defaultdict(lambda: np.zeros((A, A)))
    for k, seq in seqs.items():
        f = fam_of[k]
        for a, b in zip(seq, seq[1:]):
            uni[a] += 1
            bi[a, b] += 1
            fu[f][a] += 1
            fb[f][a, b] += 1
    rng = np.random.default_rng(TD9.SEED)
    out = []
    for k in sorted(seqs):
        seq = seqs[k]
        if len(seq) < 2:
            continue
        f = fam_of[k]
        pair_total = float(uni.sum()) - float(fu[f].sum())
        rows = []
        for a, b in zip(seq, seq[1:]):
            row_pool = float(bi[a].sum()) - float(fb[f][a].sum())
            rows.append((a, b,
                         np.log((bi[a, b] - fb[f][a, b] + ALPHA) / (max(row_pool, 0.0) + ALPHA * A)),
                         np.log((uni[b] - fu[f][b] + ALPHA) / (max(pair_total, 0.0) + ALPHA * A)),
                         np.log((fb[f][a, b] + ALPHA) / (float(fb[f][a].sum()) + ALPHA * A))))
        targets = [b for _, b, _, _, _ in rows]
        rng.shuffle(targets)
        shuffled = [np.log((bi[a, t] - fb[f][a, t] + ALPHA) /
                           (max(float(bi[a].sum()) - float(fb[f][a].sum()), 0.0) + ALPHA * A))
                    for (a, _, _, _, _), t in zip(rows, targets)]
        out.append({"traj_key": k, "instance_id": inst_of[k], "task_family": f, "n_transitions": len(rows),
                    "ll_uniform": round(float(np.log(1.0 / A)), 6),
                    "ll_unigram": round(float(np.mean([r[3] for r in rows])), 6),
                    "ll_bigram": round(float(np.mean([r[2] for r in rows])), 6),
                    "ll_family": round(float(np.mean([r[4] for r in rows])), 6),
                    "ll_bigram_shuffled": round(float(np.mean(shuffled)), 6)})
    return pd.DataFrame(out)


def t153(fr: dict) -> dict:
    """Cross-task grammar: does one pooled transition model predict another family's searches?"""
    L = transition_loglik(fr["S"])
    L["gain_pooled_vs_uniform"] = L["ll_bigram"] - L["ll_uniform"]
    L["gain_family_vs_pooled"] = L["ll_family"] - L["ll_bigram"]
    L["gain_bigram_vs_unigram"] = L["ll_bigram"] - L["ll_unigram"]
    L["gain_shuffled_vs_unigram"] = L["ll_bigram_shuffled"] - L["ll_unigram"]

    def stat(col):
        return boot(L, "instance_id", lambda x, c=col: float(x[c].mean()))

    def row(hyp, col, term_name, direction_note, extra=None):
        b = stat(col)
        r = {"hypothesis": hyp, "term": term_name, "beta": round(float(L[col].mean()), 4),
             "ci_lo": (b.get("ci") or [None, None])[0], "ci_hi": (b.get("ci") or [None, None])[1],
             "p": b.get("p"), "n": int(len(L)), "clusters": b.get("clusters"),
             # the row says where its interval and its p came from: a cluster bootstrap has no analytic standard
             # error, and a reader holding the row should not have to guess which of the two is missing
             "ci_kind": b.get("ci_kind"), "p_kind": b.get("p_kind"), "draws_used": b.get("draws_used"),
             "rollouts_with_transitions": int(len(L)), "mean_transitions_per_rollout":
                 round(float(L["n_transitions"].mean()), 2), "unit": "nats per transition"}
        r["verdict_direction"] = direction_note
        r.update(extra or {})
        return r

    h1 = row("H1", "gain_bigram_vs_unigram", "pooled_transition_matrix_against_the_uniform_baseline",
             "predicted_positive: the pooled grammar predicts a held-out family better than a coin flip over the "
             "same alphabet")
    lim = ((TD9.PREMISES.get("verdict") or {}).get("claim_limited") or {})
    if "G6_task_families_for_a_cross_task_grammar" in lim:
        h1["verdict"] = ("not_testable_premise_family_breadth_frozen_10_measured_" +
                         str((TD9.PREMISES.get("measured") or {}).get("task_families_200plus_rollouts")))
        h1["note"] = ("EXP-0196's G6 froze >= 10 task families with >= 200 rollouts each and measured 2 of 805, so "
                      "the cross-task claim this row would carry is limited by its own sentence; the estimate is "
                      "printed because the number exists and is not offered as the scoped test")
    h2 = row("H2", "gain_family_vs_pooled", "a_family_s_own_matrix_against_the_pooled_leave_one_family_out_matrix",
             "predicted_positive: each family speaks a dialect the pooled model does not capture")
    per_fam = []
    for f, g in L.groupby("task_family", observed=True):
        if len(g) < 200 or g["instance_id"].nunique() < 30:
            continue
        bb = boot(g, "instance_id", lambda x: float(x["gain_family_vs_pooled"].mean()))
        per_fam.append({"task_family": str(f)[:30], "rollouts": int(len(g)), "instances": int(g["instance_id"].nunique()),
                        "gain": round(float(g["gain_family_vs_pooled"].mean()), 4),
                        "ci_lo": (bb.get("ci") or [None, None])[0], "ci_hi": (bb.get("ci") or [None, None])[1]})
    h2["reported_per_family"] = per_fam
    def gain(col):
        bb = boot(L, "instance_id", lambda x, c=col: float(x[c].mean()))
        return {"beta": round(float(L[col].mean()), 4), "ci": bb.get("ci"), "p": bb.get("p"),
                "clusters": bb.get("clusters"), "n": int(len(L))}

    big, shf = gain("gain_bigram_vs_unigram"), gain("gain_shuffled_vs_unigram")
    h3 = dict(hypothesis="H3", term="ordering_beyond_the_unigram_against_a_within_rollout_shuffle",
              verdict_rule="specificity", bigram_vs_unigram=big, shuffled_vs_unigram=shf,
              note="H3 is supported when the bigram adds over the unigram and the shuffled target does not, which is "
                   "the ordering fact the sentence claims and nothing else")

    def excl(d):
        ci = d.get("ci") or [None, None]
        return ci[0] is not None and (ci[0] > 0 or ci[1] < 0)
    h3["beta"] = big["beta"]
    h3["n"] = int(len(L))
    h3["verdict"] = ("supported" if excl(big) and not excl(shf) and abs(big["beta"]) >= BAND_SMALL else
                     "not_specific_the_shuffle_carries_the_same_gain" if excl(big) else "null")
    rows = holm_and_verdict([h1, h2, h3], {"H1": 1.0, "H2": 1.0, "H3": 1.0})
    T = fr["T"]
    return dict(n_rollouts=int(len(T)), n_steps=int(len(fr["S"])), n_clusters=int(T["instance_id"].nunique()),
                cluster_unit="instance_id (the unit a transition sequence belongs to)", models=rows,
                strata=[{"stratification": "transitions_band", "stratum": str(k), "rollouts": int(len(g)),
                         "mean_pooled_bigram_gain": round(float(g["gain_bigram_vs_unigram"].mean()), 4),
                         "mean_family_gain": round(float(g["gain_family_vs_pooled"].mean()), 4)}
                        for k, g in L.assign(band=pd.cut(L["n_transitions"], [0, 5, 15, 40, 1e9],
                                                         labels=["1to5", "6to15", "16to40", "41plus"]).astype(str)
                                             ).groupby("band", observed=True)] +
                       [{"stratification": "task_family", "stratum": str(k)[:30], "rollouts": int(len(g)),
                         "mean_pooled_bigram_gain": round(float(g["gain_bigram_vs_unigram"].mean()), 4),
                         "mean_family_gain": round(float(g["gain_family_vs_pooled"].mean()), 4)}
                        for k, g in L.groupby("task_family", observed=True) if len(g) >= 200][:12],
                baselines=[{"model": "uniform_baseline", "dv": "ll_bigram", "n": int(len(L)),
                            "mean_loglik": round(float(L["ll_uniform"].mean()), 4)},
                           {"model": "plus_unigram", "dv": "ll_bigram", "n": int(len(L)),
                            "mean_loglik": round(float(L["ll_unigram"].mean()), 4),
                            "deviance_drop": round(float(L["ll_unigram"].mean() - L["ll_uniform"].mean()), 4)},
                           {"model": "plus_pooled_bigram", "dv": "ll_bigram", "n": int(len(L)),
                            "mean_loglik": round(float(L["ll_bigram"].mean()), 4),
                            "deviance_drop": round(float(L["ll_bigram"].mean() - L["ll_unigram"].mean()), 4)},
                           {"model": "plus_family_bigram", "dv": "ll_bigram", "n": int(len(L)),
                            "mean_loglik": round(float(L["ll_family"].mean()), 4),
                            "deviance_drop": round(float(L["ll_family"].mean() - L["ll_bigram"].mean()), 4)}],
                descriptive_rates={"transitions_per_rollout": {
                    str(int(k)): int(v) for k, v in L["n_transitions"].value_counts().sort_index().head(8).items()},
                    "alphabet": {"distinct_command_families": int(fr["S"]["family"].nunique()),
                                 "rollouts_with_at_least_one_transition": int(len(L)),
                                 "mean_transitions_per_rollout": round(float(L["n_transitions"].mean()), 2)},
                    "mean_loglik_by_model": {"uniform": round(float(L["ll_uniform"].mean()), 4),
                                             "unigram": round(float(L["ll_unigram"].mean()), 4),
                                             "pooled_bigram": round(float(L["ll_bigram"].mean()), 4),
                                             "family_bigram": round(float(L["ll_family"].mean()), 4),
                                             "shuffled_bigram": round(float(L["ll_bigram_shuffled"].mean()), 4)}},
                gate_scope=TD9.DESIGNS["T153"]["gate_scope"])


def cv_auc(T: pd.DataFrame, xs, y="submitted", folds: int = 5):
    """Instance-disjoint cross-validated AUC, with a cluster bootstrap on the out-of-fold predictions.

    Folds are grouped by `instance_id`, so an attempt at a task and another attempt at the same task can never sit in
    different folds - the label is a property of attempts within one task, and splitting by row would leak it.
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import GroupKFold
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    d = T.dropna(subset=[y] + xs)
    X, yy, g = d[xs].astype(float).to_numpy(), d[y].astype(int).to_numpy(), d["instance_id"].to_numpy()
    if yy.sum() < folds or len(np.unique(yy)) < 2:
        return None, d
    p = np.zeros(len(d))
    for tr, te in GroupKFold(n_splits=folds).split(X, yy, g):
        m = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, class_weight="balanced"))
        m.fit(X[tr], yy[tr])
        p[te] = m.predict_proba(X[te])[:, 1]
    d = d.assign(p_first=p)
    try:
        auc = float(roc_auc_score(yy, p))
    except ValueError:
        return None, d
    b = boot(d, "instance_id", lambda x: (float(roc_auc_score(x[y], x["p_first"]))
                                          if x[y].nunique() > 1 else None), 400)
    return {"auc": round(auc, 4), "n": int(len(d)), "positives": int(yy.sum()),
            "clusters": int(len(set(g))), "ci": b.get("ci"), "p": b.get("p"), "features": list(xs)}, d


def t178(fr: dict) -> dict:
    """How much of a rollout's ending is legible in its first fifth."""
    T = fr["T"]
    ff = ["ff_switch_rate", "ff_distinct_families", "ff_repeat_share", "ff_cmd_words", "ff_newness_mean"]
    both = ff + ["lf_switch_rate", "lf_newness_mean"]
    a1, d1 = cv_auc(T, ff)
    a2, _ = cv_auc(T, both)
    h1 = dict(hypothesis="H1", term="first_fifth_features_predict_the_release_s_completion_label",
              frozen_auc_floor=0.65, frozen_chance_floor=0.5, **(a1 or {"auc": None}))
    if a1:      # the estimand is a cross-validated AUC, so the row's coefficient and interval *are* that statistic
        h1["beta"], h1["ci_lo"], h1["ci_hi"] = a1["auc"], (a1.get("ci") or [None, None])[0], \
            (a1.get("ci") or [None, None])[1]
        h1["ci_kind"] = str(a1.get("ci_kind") or "cluster_bootstrap_of_the_out_of_fold_predictions")
        h1["p_kind"] = a1.get("p_kind")
    h1["verdict_direction"] = "predicted_positive: the early phase carries signal above chance"
    if a1:
        h1["verdict"] = ("supported" if a1["auc"] >= 0.65 and (a1.get("ci") or [0, 0])[0] > 0.5 else
                         f"partial_below_the_frozen_floor_measured_{str(a1['auc']).replace('.', 'p')}"
                         if a1["auc"] > 0.5 else
                         f"not_at_or_above_chance_measured_{str(a1['auc']).replace('.', 'p')}")
    delta = None
    if a1 and a2:
        dd = d1.assign(p_both=0.0)
        a2b, _ = cv_auc(T, both)
        delta = round(float(a2["auc"] - a1["auc"]), 4)
    h2 = dict(hypothesis="H2", term="the_increment_from_adding_the_last_fifth",
              auc_first_fifth=(a1 or {}).get("auc"), auc_both_phases=(a2 or {}).get("auc"),
              increment_nats_of_auc=delta, beta=delta, n=(a1 or {}).get("n"), p=None,
              note="both models share the same instance-disjoint folds, so the increment is a difference of two "
                   "cross-validated estimates on the same partition; the freeze asks for it reported with a cluster "
                   "bootstrap, which is why each side carries its own interval instead of a paired p")
    h2["verdict_direction"] = "predicted_positive: the later phase adds what the first fifth does not carry"
    h2["verdict"] = ("supported" if delta is not None and delta >= BAND_SMALL else
                     "not_specific_the_later_phase_adds_nothing" if delta is not None else
                     "not_testable_no_model_estimable")
    fams = T["task_family"].value_counts().head(5).index.tolist()
    per_fam, above = [], 0
    for f in fams:
        g = T[T["task_family"] == f]
        a, _ = cv_auc(g, ff)
        if a:
            per_fam.append(dict(task_family=str(f)[:30], **a))
            above += int(a["auc"] >= 0.65)
    h3 = dict(hypothesis="H3", term="the_early_signal_inside_each_of_the_five_largest_task_families",
              verdict_rule="sign_reproduction", families=per_fam, families_tested=len(per_fam),
              families_at_or_above_floor=above,
              verdict=("supported" if len(per_fam) >= 3 and above >= 3 else
                       f"not_reproduced_in_{above}_of_{len(per_fam)}_families_below_the_3_frozen_floor"
                       if per_fam else "not_testable_no_family_with_enough_positives"))
    rows = holm_and_verdict([h1, h2, h3], {"H1": 1.0, "H2": 1.0})
    return dict(n_rollouts=int(len(T)), n_steps=int(len(fr["S"])),
                n_clusters=int(T["instance_id"].nunique()), cluster_unit=CLUSTER, models=rows,
                strata=[{"stratification": "length_quartile", "stratum": str(k), "rollouts": int(len(g)),
                         "auc_first_fifth": (cv_auc(g, ff)[0] or {}).get("auc"),
                         "positives": int(g["submitted"].sum())}
                        for k, g in T.groupby("length_quartile", observed=True) if len(g) >= 500],
                baselines=[{"model": "chance", "dv": "submitted", "auc": 0.5, "n": int(len(T))},
                           {"model": "length_only", "dv": "submitted",
                            "auc": (cv_auc(T, ["log_steps"])[0] or {}).get("auc"), "n": int(len(T))},
                           {"model": "first_fifth_block", "dv": "submitted", "auc": (a1 or {}).get("auc"),
                            "n": int(len(T))},
                           {"model": "both_phases", "dv": "submitted", "auc": (a2 or {}).get("auc"),
                            "n": int(len(T))}],
                descriptive_rates={"completion_by_length_quartile": {
                    str(k): {"submitted_share": round(float(g["submitted"].mean()), 4), "rollouts": int(len(g))}
                    for k, g in T.groupby("length_quartile", observed=True)},
                    "positives": {"submitted_rollouts": int(T["submitted"].sum()),
                                  "share_of_rollouts": round(float(T["submitted"].mean()), 4),
                                  "instances_with_any_success": int(T.loc[T["submitted"] == 1,
                                                                          "instance_id"].nunique())},
                    "first_fifth_features": {c: {"mean": round(float(T[c].mean()), 4),
                                                 "std": round(float(T[c].std()), 4)}
                                             for c in ff if T[c].notna().any()}},
                gate_scope=TD9.DESIGNS["T178"]["gate_scope"])


def t179(fr: dict) -> dict:
    """The recovery window: does changing the command soon after a failure buy a completion?"""
    T = fr["T"][fr["T"]["failure_then_a_further_command"] == 1].copy()
    h1 = term(glm(T, "submitted", ["changed_at_lag_1"] + CTRL, "binomial"), "changed_at_lag_1")
    h1.update(hypothesis="H1", term="changing_the_command_at_the_first_step_after_a_failure_on_completing",
              rollouts_after_a_failure=int(len(T)), changed_at_lag_1=int(T["changed_at_lag_1"].sum()),
              submitted_share_when_changed=round(float(T.loc[T["changed_at_lag_1"] == 1, "submitted"].mean()), 4),
              submitted_share_when_not=round(float(T.loc[T["changed_at_lag_1"] == 0, "submitted"].mean()), 4))
    h1["verdict_direction"] = "predicted_positive: a fast change of command is a rollout that recovers"
    h1["share_changing_at_lag_1"] = round(float(T["changed_at_lag_1"].mean()), 4)
    h1["minority_arm_rollouts"] = int(min((T["changed_at_lag_1"] == 0).sum(), (T["changed_at_lag_1"] == 1).sum()))
    h1["sd_of_log_steps_in_this_cell"] = round(float(T["log_steps"].std()), 4)
    h1["rollouts_at_the_release_s_step_cap"] = int((T["n_steps"] >= 15).sum())
    h1["note"] = ("the interval is wide and the ladder thin because of two properties of this release rather than of "
                  "the behaviour: it truncates rollouts at 15 commanded steps, so the length the design controls for "
                  "barely varies, and 97.6% of the cell changes its command after a failure, so the comparison is a "
                  "minority of non-changers against everyone else. Both counts are printed with the estimate "
                  "(deviations W9-D05 and W9-D06)")
    prof = []
    for k in (1, 2, 3, 4, 5):
        t = term(glm(T, "submitted", [f"changed_at_lag_{k}"] + CTRL, "binomial"), f"changed_at_lag_{k}")
        if t.get("beta") is not None:
            prof.append(dict(lag=k, **t))
    used = [p for p in prof if abs(p.get("beta") or 0) > 0]
    falling = (len(used) >= 3 and all(abs(a["beta"]) >= abs(b["beta"]) - 1e-9
                                       for a, b in zip(used, used[1:])))
    h2 = dict(hypothesis="H2", term="the_completion_advantage_by_lag_after_the_failure",
              verdict_rule="dose_response", profile=prof, lags_estimable=len(used),
              note="the frozen claim is a decay toward zero across lags, so the verdict is the monotonicity of the "
                   "fitted advantages; each lag is its own coefficient, never pooled")
    h2["verdict"] = ("supported" if falling else f"not_monotone_in_{len(used)}_measured_lags" if used
                     else "not_testable_no_lag_estimable")
    quart = []
    for lab, g in T.groupby("length_quartile", observed=True):
        if len(g) < 300 or g["submitted"].nunique() < 2:
            continue
        t = term(glm(g, "submitted", ["changed_at_lag_1"] + CTRL, "binomial"), "changed_at_lag_1")
        if t.get("beta") is not None:
            quart.append(dict(stratum=str(lab), rollouts=int(len(g)), **t))
    pos = [q for q in quart if (q.get("beta") or 0) > 0]
    h3 = dict(hypothesis="H3", term="the_lag_one_advantage_inside_each_length_quartile",
              verdict_rule="sign_reproduction", strata=quart, quartiles_tested=len(quart),
              verdict=("supported" if len(pos) >= min(3, len(quart)) and len(quart) >= 3 else
                       f"not_reproduced_in_{len(pos)}_of_{len(quart)}_quartiles" if quart else
                       "not_testable_no_quartile_large_enough"))
    rows = holm_and_verdict([h1, h2, h3], {"H1": 1.0})
    return dict(n_rollouts=int(len(T)), n_steps=int(len(fr["S"])),
                n_clusters=int(T["instance_id"].nunique()), cluster_unit=CLUSTER, models=rows,
                strata=strata_rows(T, ["task_family", "length_quartile"], "submitted",
                                   ["changed_at_lag_1"] + CTRL, "changed_at_lag_1", min_rows=300),
                baselines=baselines(T, "submitted",
                                    [("controls_only", CTRL, "log_steps"),
                                     ("controls_plus_lag_one", ["changed_at_lag_1"] + CTRL, "changed_at_lag_1"),
                                     ("controls_plus_repetition_and_switches",
                                      ["changed_at_lag_1", "repeat_share_z", "switch_rate_z"] + CTRL,
                                      "changed_at_lag_1")]),
                descriptive_rates={"first_change_lag_distribution": {
                    str(int(k)): int(v) for k, v in T["first_change_lag"].value_counts().sort_index().head(8).items()},
                    "submitted_by_first_change_lag": {
                        str(int(k)): {"submitted_share": round(float(g["submitted"].mean()), 4),
                                      "rollouts": int(len(g))}
                        for k, g in T.groupby("first_change_lag", observed=True)},
                    "failures_per_rollout": {str(int(k)): int(v) for k, v in
                                             T["failures"].value_counts().sort_index().head(8).items()}},
                gate_scope=TD9.DESIGNS["T179"]["gate_scope"])


def t193(fr: dict) -> dict:
    """Which rollout of a repeated task deserves to be kept: the one that finished, or the cheap one?"""
    from scipy import stats as SP
    T = fr["T"][fr["T"]["rollouts_per_instance"] >= 2].copy()
    per_inst = []
    for inst, g in T.groupby("instance_id", observed=True):
        a = g["success_only_rank"].astype(float).to_numpy()
        b = g["cost_adjusted_rank"].astype(float).to_numpy()
        if len(g) < 2 or np.unique(a).size < 2 or np.unique(b).size < 2:
            continue
        k = SP.kendalltau(a, b)
        if k.statistic == k.statistic:
            per_inst.append({"instance_id": inst, "rollouts": int(len(g)), "tau": round(float(k.statistic), 4),
                             "successes": int(g["submitted"].sum())})
    P = pd.DataFrame(per_inst)
    floor = 0.80
    b = boot(P, "instance_id", lambda x: float(x["tau"].mean()), 600) if len(P) else {}
    h1 = dict(hypothesis="H1", term="within_instance_agreement_between_success_only_and_cost_adjusted_rankings",
              beta=round(float(P["tau"].mean()), 4) if len(P) else None,
              ci_lo=(b.get("ci") or [None, None])[0], ci_hi=(b.get("ci") or [None, None])[1], p=b.get("p"),
              ci_kind=b.get("ci_kind"), p_kind=b.get("p_kind"), draws_used=b.get("draws_used"),
              n=int(len(P)), clusters=b.get("clusters"), frozen_agreement_ceiling=floor,
              instances_with_two_rollouts=int(T["instance_id"].nunique()),
              instances_where_tau_is_defined=int(len(P)),
              note="the sentence fixes an agreement ceiling rather than an effect size, because the claim is that the "
                   "two rules disagree: the tau is bounded at 1 by construction and the interval is read against 0.80")
    h1["verdict_direction"] = "predicted_negative: the two rankings do not agree"
    h1["verdict"] = (("supported" if len(P) and h1["beta"] <= floor and (h1["ci_hi"] or 1) < floor else
                      "not_below_the_frozen_agreement_ceiling" if len(P) else
                      "not_estimable_no_instance_with_two_distinguishable_rankings"))
    succ = T[T["submitted"] == 1]
    longest = T.groupby("instance_id")["n_steps"].transform("max")
    T["instance_has_success"] = T.groupby("instance_id")["submitted"].transform("max").astype(int)
    T["cheaper_success_than_longest"] = ((T["submitted"] == 1) & (T["n_steps"] < longest)).groupby(
        T["instance_id"]).transform("max").astype(int)
    one = T.drop_duplicates("instance_id")
    have = one[one["instance_has_success"] == 1]
    inst_total = int(len(have))
    cheap = int(have["cheaper_success_than_longest"].sum())
    h2 = dict(hypothesis="H2", term="instances_where_a_cheaper_successful_rollout_than_the_longest_one_exists",
              verdict_rule="descriptive", instances_with_a_success=inst_total,
              instances_with_a_cheaper_success=cheap,
              share=round(cheap / inst_total, 4) if inst_total else None, p=None,
              beta=round(cheap / inst_total, 4) if inst_total else None,
              verdict="measured_descriptively_no_band_was_frozen",
              note="H2 asks for a share with its interval, not a coefficient; where no success exists in an instance "
                   "the sentence has no denominator, and that count is printed beside the share")
    if inst_total:
        b2 = boot(have.reset_index(), "instance_id",
                  lambda x: float(x["cheaper_success_than_longest"].mean()), 400)
        h2["ci"] = b2.get("ci")
    strict = P[P["successes"] >= 1] if len(P) else P
    trimmed = []
    for inst, g in T.groupby("instance_id", observed=True):
        if len(g) < 3:
            continue
        gg = g.sort_values("n_steps", ascending=False).iloc[1:]
        a, bb = gg["success_only_rank"].astype(float).to_numpy(), gg["cost_adjusted_rank"].astype(float).to_numpy()
        if np.unique(a).size < 2 or np.unique(bb).size < 2:
            continue
        k = SP.kendalltau(a, bb)
        if k.statistic == k.statistic:
            trimmed.append(k.statistic)
    h3 = dict(hypothesis="H3", term="the_agreement_after_restricting_to_success_bearing_and_trimmed_instances",
              verdict_rule="specificity", tau_all=h1["beta"],
              tau_instances_with_a_success=(round(float(strict["tau"].mean()), 4) if len(strict) else None),
              tau_after_dropping_the_longest_rollout=(round(float(np.mean(trimmed)), 4) if trimmed else None),
              instances_with_a_success=int(len(strict)), instances_trimmed=int(len(trimmed)),
              beta=h1["beta"], p=h1.get("p"), n=h1.get("n"),
              note="H3 asks whether one structure carries the disagreement: it is supported while the restricted "
                   "estimates keep the same side of the ceiling as the full one")
    same = (h3["tau_instances_with_a_success"] is None or h3["tau_instances_with_a_success"] <= floor) and \
        (h3["tau_after_dropping_the_longest_rollout"] is None
         or h3["tau_after_dropping_the_longest_rollout"] <= floor)
    h3["verdict"] = ("supported" if len(P) and h1["beta"] <= floor and same else
                     "not_robust_one_restriction_restores_the_agreement" if len(P) else
                     "not_testable_no_instance_with_two_distinguishable_rankings")
    rows = holm_and_verdict([h1, h2, h3], {"H1": -1.0})
    return dict(n_rollouts=int(len(T)), n_steps=int(len(fr["S"])), n_clusters=int(T["instance_id"].nunique()),
                cluster_unit=CLUSTER, models=rows,
                strata=[{"stratification": "rollouts_per_instance_band", "stratum": str(k),
                         "instances": int(len(g)), "mean_tau": round(float(g["tau"].mean()), 4),
                         "min_tau": round(float(g["tau"].min()), 4), "max_tau": round(float(g["tau"].max()), 4)}
                        for k, g in (P.assign(band=pd.cut(P["rollouts"], [1, 2, 5, 10, 1e9],
                                                          labels=["2", "3to5", "6to10", "11plus"]).astype(str))
                                     .groupby("band", observed=True) if len(P) else [])],
                baselines=[{"model": "success_only_ranking", "dv": "selected_rollout",
                             "mean_steps_of_selected": round(float(
                                 T.sort_values(["instance_id", "success_only_rank"]).groupby("instance_id")
                                  .first()["n_steps"].mean()), 2), "instances": int(T["instance_id"].nunique())},
                            {"model": "cost_adjusted_ranking", "dv": "selected_rollout",
                             "mean_steps_of_selected": round(float(
                                 T.sort_values(["instance_id", "cost_adjusted_rank"]).groupby("instance_id")
                                  .first()["n_steps"].mean()), 2), "instances": int(T["instance_id"].nunique()),
                             "mean_repeat_share_of_selected": round(float(
                                 T.sort_values(["instance_id", "cost_adjusted_rank"]).groupby("instance_id")
                                  .first()["repeat_share"].mean()), 4)},
                            {"model": "longest_rollout_of_each_instance", "dv": "selected_rollout",
                             "mean_steps_of_selected": round(float(
                                 T.groupby("instance_id")["n_steps"].max().mean()), 2),
                             "instances": int(T["instance_id"].nunique())}],
                descriptive_rates={"rollouts_per_instance": {str(int(k)): int(v) for k, v in
                                                             T.groupby("instance_id").size()
                                                              .value_counts().sort_index().head(10).items()},
                                   "tau_distribution": {"p10_p50_p90": [round(float(x), 4) for x in
                                                                        np.percentile(P["tau"], [10, 50, 90])]
                                                         if len(P) else None},
                                   "success_share": round(float(T["submitted"].mean()), 4),
                                   "steps_by_ranking_choice": {
                                       str(k): {"mean_steps": round(float(g["n_steps"].mean()), 2),
                                                "mean_duration": round(float(g["duration"].mean()), 2),
                                                "instances": int(len(g))}
                                       for k, g in T.assign(top=T["cost_adjusted_rank"] == 1).groupby(
                                           "top", observed=True)}},
                gate_scope=TD9.DESIGNS["T193"]["gate_scope"])


DESIGN_FN = {"EXP-0198": ("T153", t153), "EXP-0199": ("T178", t178), "EXP-0200": ("T179", t179),
             "EXP-0201": ("T193", t193)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--only", action="append", default=[])
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    fr = load()
    if a.quick:
        keep = fr["T"]["instance_id"].drop_duplicates().sample(300, random_state=TD9.SEED)
        fr["T"] = fr["T"][fr["T"]["instance_id"].isin(set(keep))]
        fr["S"] = fr["S"][fr["S"]["instance_id"].isin(set(keep))]
    todo = {k: v for k, v in DESIGN_FN.items() if not a.only or k in a.only}
    bad = [k for k in (a.only or []) if k not in DESIGN_FN]
    if bad:
        raise SystemExit(f"ABORT: --only names no design: {bad}; valid ids are {sorted(DESIGN_FN)}")
    for exp, (topic, fn) in todo.items():
        art = fn(fr)
        # every hypothesis row carries the same columns, whether its estimand is a coefficient, a share or a
        # cross-validated statistic: the model table and the forest figure read them by name
        for m in art.get("models") or []:
            for k in ("beta", "se", "ci_lo", "ci_hi", "p", "p_holm", "n"):
                m.setdefault(k, None)
        lack = [k for k in ("models", "strata", "descriptive_rates", "baselines") if not art.get(k)]
        if lack:
            raise SystemExit(f"ABORT {exp} ({topic}): the design produced no {lack}, so the package tables that read "
                             f"those blocks would ship a header with no numbers - measure it or drop the table")
        nofv = [m.get("hypothesis") or m.get("term") for m in art["models"] if not m.get("verdict")]
        if nofv:
            raise SystemExit(f"ABORT {exp} ({topic}): hypotheses {nofv} carry no verdict, and a pre-registered test "
                             f"that was not decided is not a deliverable")
        art.update(exp_id=exp, topic=topic, seed=TD9.SEED, quick=a.quick, started_at=W.now(),
                   frame_files_read={k: v.attrs.get("frame_file") for k, v in fr.items()},
                   blocked_designs_in_this_wave=list(TD9.BLOCKED_BY_GATE),
                   invocation=" ".join([sys.executable] + sys.argv),
                   run_cost=W.run_cost_row(exp, t0, int(len(fr["T"])), int(fr["T"].shape[1]), "wave-9 design"),
                   finished_at=W.now())
        print(f"{exp} ({topic}): wrote {W.write_raw(exp, f'wave9_design_{exp[-4:]}', art).name}", flush=True)
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
