"""EXP-0076: is T029 identifiable at all, and is its corpus disjoint from the papers already finished?

EXP-0073 removed T029's data blocker (AgentNet is on this disk with step-level labels) and EXP-0074 found no literature
collision. Two things still have to be measured before a topic may be promoted, and the programme's own rules say a
topic is never assumed valid:

1. **identifiability of the independent variable.** T029's IV is "verification act markers" in the step text. If those
   markers are absent, universal, or perfectly collinear with step position or text length, no hazard model can be
   fitted and the topic dies regardless of its novelty;
2. **disjointness from the estate already published.** The series forbids re-cutting one result set into several
   papers, so T029 must not consume the same task rows P001/P002/P004/P005 already report on. Identifiers are not
   enough for that - the same instruction text can carry different ids across corpora - so the test is on normalised
   text signatures as well as on ids.

GO rule, fixed before any text was read (all four conjuncts required; a failure names itself). The (d) test was
widened to two tails before the first run, because a one-sided "above the null" reading would have labelled a strong
inverse association as "nothing detected" - a reporting error, not a change of threshold:
  (a) each marker class has step prevalence in [0.02, 0.80];
  (b) >= 0.30 of tasks contain both marked and unmarked steps (within-task contrast exists);
  (c) zero overlap with the completed papers' rows, on task ids AND on normalised instruction signatures;
  (d) the marker-outcome association's task-clustered bootstrap interval excludes a step-label permutation null **in
      either direction**; a separate field records whether the direction is the one T029 hypothesises.
A pass is a feasibility signal only: it licenses writing a protocol, not reporting an effect.

    python t029_identifiability_probe.py
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import random
import re
import sys
import time
from collections import Counter

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
RAW = ROOT.parent / "MATLABINTOKEN" / "data" / "raw"
PROC = ROOT / "01_datasets" / "processed"
OUT_RAW = ROOT / "results_raw"
FILES = ["agentnet_ubuntu_5k.jsonl", "agentnet_win_mac_18k.jsonl"]
SAMPLE_PER_FILE = 2000
SEED = 20260920
BOOT, PERM = 1000, 300

# three verification-act classes, declared before reading any step text
CLASSES = {
    "A_explicit_verification": [r"\bverif(y|ies|ication|ing)\b", r"\bcheck (whether|if|that)\b",
                                r"\bconfirm (that|the|it)\b", r"\bmake sure\b", r"\bensure\b", r"\bvalidat(e|ion|ing)\b"],
    "B_result_inspection": [r"\bi see\b", r"\bthe screen shows\b", r"\bit appears\b", r"\blooks like\b",
                            r"\bthe result is\b", r"\bcurrent state\b", r"\bnow shows\b", r"\b(i|we) can see\b"],
    "C_repair_evaluation": [r"\bwrong\b", r"\bfailed\b", r"\bnot working\b", r"\bdid not\b", r"\bretry\b",
                            r"\btry again\b", r"\binstead of\b", r"\bincorrect\b", r"\berror\b"],
}
# a frequency control: topically about GUI work but not an evaluation act. If this behaves like the marker classes,
# the "effect" is really about verbose steps, not about verification.
CONTROL = [r"\bfile\b", r"\bwindow\b", r"\bclick\b", r"\bopen\b", r"\btext\b", r"\bicon\b", r"\bapplication\b"]
PREVALENCE_BAND = (0.02, 0.80)
WITHIN_TASK_MIN = 0.30


def norm_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower().strip())


def sig(s: str) -> str:
    return hashlib.sha1(norm_text(s)[:240].encode("utf-8")).hexdigest()


def hits(patterns, text):
    return any(re.search(p, text) for p in patterns)


def line_offsets(path):
    offs, pos = [], 0
    with path.open("rb") as fh:
        for raw in fh:
            offs.append(pos)
            pos += len(raw)
    return offs


def read_sample(path, rng):
    offs = line_offsets(path)
    pick = sorted(rng.sample(range(len(offs)), min(SAMPLE_PER_FILE, len(offs))))
    out = []
    with path.open("rb") as fh:
        for i in pick:
            fh.seek(offs[i])
            line = fh.readline()
            if not line.strip() or line[:1] != b"{":
                continue
            try:
                d = json.loads(line)
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            out.append(d)
    if not out:
        raise SystemExit(f"[e76] ABORT: parsed 0 sampled lines from {path.name}; that is a broken read.")
    return out


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    rng = random.Random(SEED)
    steps = []
    tasks_seen = 0
    agent_sigs, agent_ids = set(), set()
    for name in FILES:
        for d in read_sample(RAW / name, rng):
            traj = d.get("traj") or []
            tasks_seen += 1
            tid = str(d.get("task_id"))
            agent_ids.add(tid)
            agent_sigs.add(sig(d.get("instruction") or d.get("natural_language_task") or ""))
            for j, s in enumerate(traj):
                v = s.get("value") if isinstance(s.get("value"), dict) else {}
                if "last_step_correct" not in v:
                    continue
                txt = norm_text(" ".join(str(v.get(k, "")) for k in ("thought", "reflection")))
                row = {"task": tid, "file": name, "step": j, "n_steps": len(traj),
                       "y": int(bool(v.get("last_step_correct"))), "chars": len(txt),
                       "control": int(hits(CONTROL, txt))}
                for cname, pats in CLASSES.items():
                    row[cname] = int(hits(pats, txt))
                if txt:
                    steps.append(row)
    S = pd.DataFrame(steps)
    print(f"[e76] {tasks_seen} sampled tasks, {len(S):,} labelled steps with non-empty text "
          f"({round(time.time() - t0, 1)}s)", flush=True)

    # ---- overlap with the rows the completed papers already consume
    other_ids, other_sigs = set(), set()
    for f in sorted(PROC.glob("routing_*.parquet")):
        d = pd.read_parquet(f, columns=["prompt_id", "uuid", "question"])
        other_ids |= set(d["prompt_id"].astype(str)) | set(d["uuid"].astype(str))
        other_sigs |= {sig(q) for q in d["question"].astype(str)}
    ov_ids = agent_ids & other_ids
    ov_sigs = agent_sigs & other_sigs

    prev = {c: round(float(S[c].mean()), 4) for c in list(CLASSES) + ["control"]}
    grp = S.groupby("task")
    within = {c: round(float(((grp[c].sum() > 0) & (grp[c].sum() < grp[c].size())).mean()), 4) for c in CLASSES}
    conf_len = {c: round(float(np.corrcoef(S[c], np.log1p(S["chars"]))[0, 1]), 4) for c in list(CLASSES) + ["control"]}
    rel_pos = S["step"] / S["n_steps"].clip(lower=1)
    conf_pos = {c: round(float(np.corrcoef(S[c], rel_pos)[0, 1]), 4) for c in list(CLASSES) + ["control"]}

    y = S["y"].values
    tasks = S["task"].values
    uniq = pd.unique(tasks)
    idx_of = {t: np.where(tasks == t)[0] for t in uniq}

    def boot_auc(marker):
        m = S[marker].values
        from sklearn.metrics import roc_auc_score
        obs = roc_auc_score(y, m)
        rngb = np.random.default_rng(SEED)
        vals = []
        for _ in range(BOOT):
            take = np.concatenate([idx_of[t] for t in rngb.choice(uniq, size=len(uniq), replace=True)])
            yy = y[take]
            if yy.min() == yy.max():
                continue
            vals.append(roc_auc_score(yy, m[take]))
        lo, hi = np.percentile(vals, [2.5, 97.5])
        # within-task permutation, vectorised: a uniform random order inside each task block keeps the task
        # structure fixed without a python loop over thousands of groups
        blocks = pd.factorize(tasks)[0]
        null = []
        for _ in range(PERM):
            order = np.lexsort((rngb.random(len(y)), blocks))
            null.append(roc_auc_score(y[order], m))
        null_mean, null_p95, null_p05 = (float(np.mean(null)), float(np.percentile(null, 95)),
                                         float(np.percentile(null, 5)))
        if len(null) < PERM:
            raise SystemExit(f"[e76] ABORT: only {len(null)}/{PERM} permutation replicates were usable")
        # two directional tests, because "does not clear the null" would otherwise hide a strong NEGATIVE association:
        # detectable = the interval sits outside the null on either side; hypothesis-direction = above it, which is
        # what T029's H actually claims
        return {"auc_marker_vs_outcome": round(float(obs), 4),
                "cluster_boot_ci95": [round(float(lo), 4), round(float(hi), 4)],
                "within_task_permutation_null_mean": round(null_mean, 4),
                "null_p05": round(null_p05, 4), "null_p95": round(null_p95, 4),
                "ci_lower_above_null": bool(lo > null_p95),
                "ci_upper_below_null": bool(hi < null_p05),
                "detectable_either_direction": bool(lo > null_p95 or hi < null_p05),
                "direction_matches_hypothesis": bool(lo > null_p95),
                "resamples": len(vals)}

    assoc = {c: boot_auc(c) for c in CLASSES}
    assoc_len = boot_auc("control")

    checks = {
        "a_prevalence_in_band": {c: bool(PREVALENCE_BAND[0] <= prev[c] <= PREVALENCE_BAND[1]) for c in CLASSES},
        "b_within_task_contrast": {c: bool(within[c] >= WITHIN_TASK_MIN) for c in CLASSES},
        "c_disjoint_from_completed_papers": {"task_ids": len(ov_ids), "instruction_signatures": len(ov_sigs),
                                             "pass": not ov_ids and not ov_sigs},
        "d_association_detectable_vs_null": {c: assoc[c]["detectable_either_direction"] for c in CLASSES},
        "e_direction_matches_hypothesis": {c: assoc[c]["direction_matches_hypothesis"] for c in CLASSES},
    }
    go = (all(checks["a_prevalence_in_band"].values()) and all(checks["b_within_task_contrast"].values())
          and checks["c_disjoint_from_completed_papers"]["pass"]
          and any(checks["d_association_detectable_vs_null"].values()))
    res = {"exp_id": "EXP-0076", "topic": "T029", "seed": SEED, "sampled_tasks": tasks_seen,
           "labelled_steps_with_text": int(len(S)), "mean_steps_per_task": round(float(S.groupby("task")["n_steps"].first().mean()), 2),
           "outcome_positive_rate": round(float(y.mean()), 4),
           "marker_prevalence": prev, "within_task_contrast_share": within,
           "confound_corr_with_log_text_length": conf_len, "confound_corr_with_relative_step_position": conf_pos,
           "association": assoc, "control_lexicon_association": assoc_len,
           "overlap": {"agentnet_ids_sampled": len(agent_ids), "other_ids": len(other_ids),
                       "id_intersection": len(ov_ids),
                       "agentnet_sigs_sampled": len(agent_sigs), "other_sigs": len(other_sigs),
                       "signature_intersection": len(ov_sigs),
                       "other_rows_scanned": int(sum(len(pd.read_parquet(f, columns=['question']))
                                                     for f in sorted(PROC.glob('routing_*.parquet'))))},
           "go_rule": {"prevalence_band": PREVALENCE_BAND, "within_task_min": WITHIN_TASK_MIN,
                       "checks": checks, "GO": bool(go)},
           "what_a_pass_licenses": "writing a protocol and freezing it - not reporting an effect. The marker lexicon is "
                                   "crude, the association is unadjusted, and step text is model-authored, so "
                                   "verification language and verification-adjacent verbosity are not separated here",
           "wallclock_sec": round(time.time() - t0, 1), "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    OUT_RAW.mkdir(parents=True, exist_ok=True)
    out = OUT_RAW / f"EXP0076_t029_identifiability_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8", newline="")
    print(json.dumps({k: res[k] for k in ("marker_prevalence", "within_task_contrast_share", "outcome_positive_rate",
                                          "overlap", "go_rule")}, indent=1, ensure_ascii=False), flush=True)
    print("wrote", out.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
