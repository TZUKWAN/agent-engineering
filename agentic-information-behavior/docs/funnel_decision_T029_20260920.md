# Funnel decision - T029 (Verification Language and Stopping Judgement), 2026-09-20

Probe: `02_shared_code/data_audit/t029_identifiability_probe.py` -> `results_raw/EXP0076_t029_identifiability_20260920T052114.json`.
Screens: EXP-0074 (novelty), EXP-0073 (data premise).

## What had to be true, and what is true

T029 asks whether a step that contains verification language is more often followed by a correct termination. EXP-0073
established the corpus is on this machine (4,000 sampled tasks,
67,840 labelled steps with text, mean 18.54 steps/task), and EXP-0074
found no literature collision. Two gates remained, and the GO rule was fixed in the script before any step text was
read.

**Gate 1 - disjointness from the completed papers: PASS.** Against the 66,000 rows in
`01_datasets/processed/routing_*.parquet` that P001/P002/P004/P005 report on, the intersection is
**0 task ids and 0 normalised instruction signatures** over
4,000 sampled AgentNet tasks. So this is not a re-slice of an existing paper's rows.

**Gate 2 - identifiability of the IV: FAIL.**

| marker class | step prevalence | within-task contrast | AUC vs outcome (task-clustered 95% CI) | within-task permutation null | detectable | direction |
|---|---|---|---|---|---|---|
| A_explicit_verification | 0.1692 | 0.8267 | 0.4891 (0.4834-0.4939) | 0.4949 | no | inside |
| B_result_inspection | 0.9185 | 0.6671 | 0.4818 (0.4789-0.4847) | 0.4871 | yes | below |
| C_repair_evaluation | 0.2414 | 0.8762 | 0.1651 (0.1599-0.1697) | 0.4422 | yes | below |

Reading of the table, class by class:

* **A explicit verification** (16.9% of steps) sits at chance against the outcome
  (0.4891, CI inside the null band) - nothing to model.
* **B result inspection** (91.8%) fails the prevalence band on the high side: it is in almost
  every step, so it carries almost no within-step information, and what it does carry is inverse.
* **C repair evaluation** (24.1%) is the only strong signal, and it is **negative**: AUC
  0.1651 against a within-task null of
  0.4422. Steps where the agent says "wrong / failed /
  retry" are the steps labelled incorrect.
* The frequency control lexicon (93.3%, AUC
  0.4945) behaves like class A, i.e. at chance - so the class-C
  result is not simply verbosity.

## Why this is a kill rather than a "try a better lexicon"

The inverse class-C association has a mechanical explanation that a better lexicon cannot escape: AgentNet's
`last_step_correct` is a judgement about the action the reflection text is commenting on. Marker and label are two views
of the same event, so any improvement in detecting verification language improves the detection of "this step went
badly" in the same direction. That is reverse-causal by construction, not a measurement error to be tuned away, and the
outcome is also near-degenerate (89.8% positive), which leaves little variance to explain.

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
