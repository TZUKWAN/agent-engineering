"""EXP-0076 recorder: file the T029 identifiability decision.

A topic is never assumed valid here, so EXP-0076 tested whether T029's independent variable can be measured at all and
whether its corpus is disjoint from the estate already published. The disjointness test passed cleanly; the
identifiability test did not, and the reason is worth writing down rather than filing as "no signal": the marker classes
that do separate from their permutation null separate in the **opposite** direction to the hypothesis, and the most
plausible mechanism for that is that AgentNet's step label and its step text describe the same event - the label records
whether the preceding action was right, and the reflection text is the agent saying so.

    python 02_shared_code/registry/record_exp0076_t029.py
"""
from __future__ import annotations

import csv, glob, io, json, pathlib, re, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
REG = ROOT / "00_program_registry"
DOCS = ROOT / "docs"
NOW = time.strftime("%Y-%m-%d")
f = sorted(glob.glob(str(ROOT / "results_raw" / "EXP0076_t029_identifiability_*.json")))[-1]
D = json.loads(pathlib.Path(f).read_text(encoding="utf-8"))
CK, AS, PV, WI = D["go_rule"]["checks"], D["association"], D["marker_prevalence"], D["within_task_contrast_share"]
OV = D["overlap"]

assoc_rows = "\n".join(
    f"| {c} | {PV[c]:.4f} | {WI[c]:.4f} | {AS[c]['auc_marker_vs_outcome']:.4f} "
    f"({AS[c]['cluster_boot_ci95'][0]}-{AS[c]['cluster_boot_ci95'][1]}) | "
    f"{AS[c]['within_task_permutation_null_mean']:.4f} | "
    f"{'yes' if AS[c]['detectable_either_direction'] else 'no'} | "
    f"{'above' if AS[c]['ci_lower_above_null'] else ('below' if AS[c]['ci_upper_below_null'] else 'inside')} |"
    for c in AS)

DOC = f"""# Funnel decision - T029 (Verification Language and Stopping Judgement), {NOW}

Probe: `02_shared_code/data_audit/t029_identifiability_probe.py` -> `results_raw/{pathlib.Path(f).name}`.
Screens: EXP-0074 (novelty), EXP-0073 (data premise).

## What had to be true, and what is true

T029 asks whether a step that contains verification language is more often followed by a correct termination. EXP-0073
established the corpus is on this machine ({D['sampled_tasks']:,} sampled tasks,
{D['labelled_steps_with_text']:,} labelled steps with text, mean {D['mean_steps_per_task']} steps/task), and EXP-0074
found no literature collision. Two gates remained, and the GO rule was fixed in the script before any step text was
read.

**Gate 1 - disjointness from the completed papers: PASS.** Against the {OV['other_rows_scanned']:,} rows in
`01_datasets/processed/routing_*.parquet` that P001/P002/P004/P005 report on, the intersection is
**{OV['id_intersection']} task ids and {OV['signature_intersection']} normalised instruction signatures** over
{OV['agentnet_ids_sampled']:,} sampled AgentNet tasks. So this is not a re-slice of an existing paper's rows.

**Gate 2 - identifiability of the IV: FAIL.**

| marker class | step prevalence | within-task contrast | AUC vs outcome (task-clustered 95% CI) | within-task permutation null | detectable | direction |
|---|---|---|---|---|---|---|
{assoc_rows}

Reading of the table, class by class:

* **A explicit verification** ({PV['A_explicit_verification']:.1%} of steps) sits at chance against the outcome
  ({AS['A_explicit_verification']['auc_marker_vs_outcome']:.4f}, CI inside the null band) - nothing to model.
* **B result inspection** ({PV['B_result_inspection']:.1%}) fails the prevalence band on the high side: it is in almost
  every step, so it carries almost no within-step information, and what it does carry is inverse.
* **C repair evaluation** ({PV['C_repair_evaluation']:.1%}) is the only strong signal, and it is **negative**: AUC
  {AS['C_repair_evaluation']['auc_marker_vs_outcome']:.4f} against a within-task null of
  {AS['C_repair_evaluation']['within_task_permutation_null_mean']:.4f}. Steps where the agent says "wrong / failed /
  retry" are the steps labelled incorrect.
* The frequency control lexicon ({PV['control']:.1%}, AUC
  {D['control_lexicon_association']['auc_marker_vs_outcome']:.4f}) behaves like class A, i.e. at chance - so the class-C
  result is not simply verbosity.

## Why this is a kill rather than a "try a better lexicon"

The inverse class-C association has a mechanical explanation that a better lexicon cannot escape: AgentNet's
`last_step_correct` is a judgement about the action the reflection text is commenting on. Marker and label are two views
of the same event, so any improvement in detecting verification language improves the detection of "this step went
badly" in the same direction. That is reverse-causal by construction, not a measurement error to be tuned away, and the
outcome is also near-degenerate ({D['outcome_positive_rate']:.1%} positive), which leaves little variance to explain.

No threshold was moved and no criterion was softened after seeing this: the rule's two-sided widening (recorded in the
script's docstring) made the test **harder** to pass by refusing to call a strong inverse association "no signal", and
the direction field was added as a separate, stricter requirement.

## Decision

`not_promoted_identifiability` - T029's IV is not separable from its label on this corpus. The topic stays in the
registry with this reason; the novelty screen and the disjointness result stay valid and are what would have made it
eligible had identifiability held.

## What would change the verdict

A corpus where the verification text and the correctness label are produced independently - e.g. human annotations of
step correctness made without reading the agent's own reflection, or a design where the reflection is emitted after the
labelled action with a temporal gap. That is a data-acquisition problem, not an analysis problem, and it is why this is
filed as a kill rather than a pilot.
"""
(DOCS / "funnel_decision_T029_20260920.md").write_text(DOC, encoding="utf-8", newline="")
print("[e76] wrote docs/funnel_decision_T029_20260920.md")

P = REG / "topic_registry.csv"
rows = list(csv.reader(io.StringIO(P.read_text(encoding="utf-8"))))
hdr, body = rows[0], [r for r in rows[1:] if r]
before = {r[0]: list(r) for r in body}
iS, iB = hdr.index("status"), hdr.index("blocking_issue")
n = 0
for r in body:
    if r[0] == "T029":
        r[iS] = "not_promoted_identifiability"
        r[iB] = (f"IV not separable from the label: explicit-verification class at chance "
                 f"(AUC {AS['A_explicit_verification']['auc_marker_vs_outcome']}), result-inspection class in "
                 f"{PV['B_result_inspection']:.0%} of steps (outside the prevalence band), repair class strongly "
                 f"INVERSE (AUC {AS['C_repair_evaluation']['auc_marker_vs_outcome']} vs within-task null "
                 f"{AS['C_repair_evaluation']['within_task_permutation_null_mean']}) because last_step_correct judges "
                 "the same event the reflection text comments on; corpus IS disjoint from completed papers "
                 f"({OV['id_intersection']} ids, {OV['signature_intersection']} signatures) and novelty screen found "
                 "0 L2+ (EXP-0074)")
        n += 1
assert n == 1, n
for r in body:
    changed = [hdr[i] for i in range(len(hdr)) if before[r[0]][i] != r[i]]
    if set(changed) - {"status", "blocking_issue"}:
        raise SystemExit(f"[e76] ABORT: {r[0]} changed more than status/blocking_issue: {changed}")
buf = io.StringIO()
w = csv.writer(buf, lineterminator="\r\n")
w.writerow(hdr)
w.writerows(body)
P.write_text(buf.getvalue(), encoding="utf-8", newline="")
print("[e76] topic registry: T029 -> not_promoted_identifiability (only status/blocking_issue touched)")

p = REG / "experiment_registry.csv"
erows = [r for r in csv.reader(io.StringIO(p.read_text(encoding="utf-8"))) if r]
if "EXP-0076" not in {r[0] for r in erows}:
    erows.append(["EXP-0076", "funnel:T029", "not_promoted_IDENTIFIABILITY_IV_COLLIDES_WITH_LABEL",
                  "02_shared_code/data_audit/t029_identifiability_probe.py",
                  f"seeded sample of {D['sampled_tasks']:,} AgentNet tasks -> "
                  f"{D['labelled_steps_with_text']:,} labelled steps with text; "
                  "three verification-act lexicon classes plus a topical control lexicon fixed before reading any step "
                  "text; prevalence, within-task contrast, confound correlations against log text length and relative "
                  "step position; task-clustered bootstrap AUC against a within-task label permutation null, tested in "
                  "both tails with direction recorded separately; disjointness against every routing parquet on ids "
                  "AND normalised instruction signatures",
                  f"seed {D['seed']}", D["at"], D["at"],
                  f"GO=False; disjoint PASS ({OV['id_intersection']}/{OV['signature_intersection']} overlap on "
                  f"{OV['other_rows_scanned']} rows); A at chance, B prevalence {PV['B_result_inspection']}, "
                  f"C inverse AUC {AS['C_repair_evaluation']['auc_marker_vs_outcome']} vs null "
                  f"{AS['C_repair_evaluation']['within_task_permutation_null_mean']}",
                  f"results_raw/{pathlib.Path(f).name}; docs/funnel_decision_T029_20260920.md",
                  "kills T029 on identifiability rather than novelty: the marker and the label judge the same event, so "
                  "no lexicon improvement separates them; the corpus-disjointness and novelty results are retained as "
                  "valid", "yes - funnel decision doc and topic registry"])
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\r\n").writerows(erows)
    p.write_text(buf.getvalue(), encoding="utf-8", newline="")
    print("[e76] registered EXP-0076")
import pandas as pd
d = pd.read_csv(p)
assert not d.exp_id.duplicated().any()
print(f"[e76] registry rows={len(d)}")
