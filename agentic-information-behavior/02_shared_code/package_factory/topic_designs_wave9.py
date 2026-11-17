"""The wave-9 protocol freeze: structure, transitions and value in recorded step-level searches.

Six designs were screened for this wave (T151 an induced taxonomy of agent information behaviour, T153 a cross-task
grammar, T156 the exploration-to-exploitation transition, T178 predicting the final outcome from the first fifth of a
rollout, T179 the recovery window after a failed observation, T193 which rollouts deserve to be reused). The substrate
is the same 12-file, seeded, content-deduplicated draw wave 6 measured: 19,988 rollouts, 292,992 commanded steps,
1,784 task instances, and - unlike hermes - a real per-rollout label (`exit_status`) and a real cost (`duration_sec`).

EXP-0190's successor EXP-0196 measured this release twice with identical output, and three of its gates changed what
this wave can claim:

* G9 froze `>= 0.90 of steps have an observation whose new-word share is computable` and measured **0.7876** - 21% of
  commanded steps are followed by nothing at all. Newness is one of the two feature blocks T151 clusters on and the
  outcome T156 curves against, and both sentences put that quantity at design scope, so T151 and T156 are stopped by
  their own gates here rather than re-specified on 79% of the steps under the same names;
* G6 froze `>= 10 task families with >= 200 rollouts each` for T153's cross-task claim and measured **2 of 805**:
  the release is organised by repository and the org-level grouping is concentrated in two names, so T153's H1 is
  claim-limited by its own sentence while its other arms, which need bigram support rather than family breadth, stand
  (G12 measured 77 bigrams occurring >= 100 times against a floor of 50);
* the outcome label, present on 1.0 of rollouts, turns out to be near-degenerate: **560 `Submitted` against 19,428
  `incomplete`** - 2.8% positive. That is a measured premise, not a result: T178 and T193 condition on it, so every
  their estimate reports the size of the positive cell next to the coefficient and the frozen floors stay where they
  were written (deviation W9-D03).

What remains measurable in this wave is T153 (H2 and H3), T178, T179 and T193, and every threshold below was fixed
before any of them was estimated.
"""
from __future__ import annotations

EXP_OF = {"T153": "EXP-0198", "T178": "EXP-0199", "T179": "EXP-0200", "T193": "EXP-0201"}
RUNNABLE = tuple(EXP_OF)
BLOCKED_BY_GATE = ("T151", "T156")
FEATURE_EXP = "EXP-0197"
PREMISE_EXP = "EXP-0196"
BATTERY_EXP = "EXP-0202"
ENCODER_EXP = ""
SEED = 42
BANDS = {"small": 0.05, "medium": 0.15, "large": 0.30}
MATRIX = "results_raw/EXP0197_wave9_step_matrix_*.json"
PREMISE_GLOB = "results_raw/EXP0196_wave9_premise_census_*.json"
BATTERY = "results_raw/EXP0202_wave9_battery_0202_*.json"
MATRIX_GLOB = MATRIX
BATTERY_GLOB = BATTERY
ENCODER_GLOB = ""
MATRIX_SCRIPT = "exp_wave9_features.py"
BATTERY_SCRIPT = "exp_wave9_battery.py"
PROBE_SCRIPT = "probe_wave9_premises.py"
DESIGNS_MODULE = "topic_designs_wave9"
STAGE_RX = "wave9_main"
CLEAN_ROOM_ONLY_FLAG = "--only"
CLEAN_ROOM_MODE = "full"
SCRIPT_OF = {t: "exp_wave9_designs.py" for t in RUNNABLE}
MAIN_SCRIPT_OF = {t: "exp_wave9_designs.py" for t in RUNNABLE}
SUBSTRATE_LABEL = ("the same 12 files of SWE-ZERO / AgentTrove commanded-step rollouts wave 6 drew (seed 42, content"
                   "-deduplicated): 19,988 rollouts over 1,784 task instances, 292,992 assistant steps each carrying "
                   "one shell command and the observation returned, with the release's own exit_status label "
                   "(560 Submitted, 19,428 incomplete) and duration_sec on 1.0 of rollouts")
SAMPLE_FIELDS = ("corpus", "trajectories", "trajectories_parsed", "steps_total", "mean_steps", "instances",
                 "instances_with_2plus_rollouts", "outcome_label_share", "newness_available_share", "cluster_unit")
CONTRIBUTION_POPULATION = ("a corpus of recorded step-level agent searches with the release's own completion label "
                           "and per-rollout cost, read with rule, lexical and classical-clustering instruments, with "
                           "no model API anywhere")

COMMON = {
    "seed": SEED,
    "bands": BANDS,
    "module": "topic_designs_wave9",
    "sample": {"traj_cap": 20000, "cluster_unit": "instance_id",
              "unit_of_analysis": "the commanded step, nested in its rollout, nested in the task instance",
              "rule": "the same seeded draw of 12 files and 20,000 rollout rows wave 6 used, deduplicated by exact "
                      "content before sampling; no subsample after it, so the instance clusters are the ones the "
                      "release has",
              "excluded": "rollouts with no commanded step at all (12 of 20,000 - EXP-0196 measured 0.9994 parse "
                          "coverage), which contribute no step and no transition"},
    "instruments": ("a family is wave 6's frozen classifier over the first executable token of the command, read left "
                    "to right across pipes; a switch is a step whose family differs from the previous step's; "
                    "newness is wave 6's content-word share of the observation not seen earlier in the rollout; a "
                    "failed observation carries wave 4's failure markers, unchanged since waves 6 and 7; the first "
                    "fifth of a rollout is its first ceil(n_steps / 5) commanded steps; a lag-k recovery is a command "
                    "whose name and arguments both differ from the failing one, k steps after a failed observation"),
}

DESIGNS = {
 # ------------------------------------------------------------------ T153
 "T153": {
  "pkg": "P050_a_cross_task_grammar_of_agent_search",
  "title": "Is There a Cross-Task Universal Grammar of Agentic Information Behaviour?",
  "rq": "Do the transition statistics of one task family predict another, or does every family speak its own dialect "
        "of the same command alphabet?",
  "hypotheses": [
   "H1 a transition matrix pooled over all task families predicts a held-out family's step sequence better than a "
   "uniform model over the same alphabet. [claim-limited by G6: the release offers 2 org-level families with >= 200 "
   "rollouts, not the 10 the sentence froze.]",
   "H2 a family-specific matrix beats the pooled one on that family's own held-out steps, and the gain is reported "
   "per family rather than pooled, so a single large family cannot carry the average.",
   "H3 the ordering facts are not just the step-count and family-mixture: with the unigram family distribution "
   "controlled, the bigram term still adds, and the same comparison with the bigram shuffled produces nothing."],
  "features": {
   "bigram_loglik": "mean log-likelihood per transition of a held-out rollout under the pooled leave-one-family-out "
                    "matrix, against the uniform and unigram baselines",
   "family_specific_gain": "bigram log-likelihood under the family's own matrix minus the pooled leave-one-out matrix",
   "bigram_shuffle": "the same likelihood with the target family of each transition permuted within the rollout"},
  "dvs": {"bigram_loglik": "H1's and H3's outcome", "family_specific_gain": "H2's outcome"},
  "models": [
   "leave-one-family-out likelihood comparison on held-out rollouts, with a cluster bootstrap on instance_id",
   "the same comparison for a family's own matrix against the pooled one, reported per family with >= 200 rollouts",
   "a three-way likelihood ladder - uniform, unigram, bigram - on the same held-out steps"],
  "thresholds": {"support": "|beta| >= 0.15 with CI excluding 0 and p_holm < 0.05",
                 "partial": "CI excludes 0 below the floor", "null": "CI includes 0",
                 "note": "the estimand is a mean log-likelihood difference per transition, so the band is applied in "
                         "nats and the unit it is compared against is named in the artefact"},
  "family": "three",
  "gate_scope": "H1",
  "kill_gate": ("G6 froze >= 10 task families with >= 200 rollouts each as the floor for calling anything cross-task, "
                "and EXP-0196 measured 2 of 805 org-level families - the release is organised by repository, and its "
                "org grouping is concentrated in two names - so H1 is reported as limited by its own sentence, with "
                "both counts printed. G12's support floor for the transition table itself passed (77 bigrams "
                "occurring >= 100 times), which is why H2 and H3 are estimated."),
  "strata": ["task family", "rollout-length quartile"],
  "tables": ["table1_sample_and_structure.csv", "table2_grammar_census.csv", "table3_main_models.csv",
             "table4_strata_by_family.csv", "table5_robustness_inference.csv", "table6_baseline_comparison.csv",
             "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_transition_structure.pdf", "fig2_main_effect.pdf",
              "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"],
 },
 # ------------------------------------------------------------------ T151
 "T151": {
  "pkg": "P054_an_induced_taxonomy_of_agent_information_behaviour",
  "title": "An Empirically Induced Taxonomy of LLM-Agent Information Behaviour",
  "rq": "Do recorded searches fall into a small number of behavioural types, and does each type end differently?",
  "hypotheses": [
   "H1 a k-way partition of rollouts on the frozen step-feature block separates with silhouette >= 0.15 at some "
   "k in 4..8.",
   "H2 the clusters differ in their completion rate, reported per cluster with a cluster bootstrap on instance_id.",
   "H3 the partition is stable: two halves of the instances, clustered separately, agree with an adjusted Rand index "
   ">= 0.50."],
  "features": {"silhouette": "the mean silhouette of the k-way solution on z-scored step features",
               "cluster_membership": "the k-way label assigned to each rollout",
               "split_half_ari": "adjusted Rand index between the two half-sample assignments on shared instances"},
  "dvs": {"silhouette": "H1's outcome", "completion_rate_by_cluster": "H2's outcome",
          "split_half_ari": "H3's outcome"},
  "models": ["k-means over the frozen feature block at k in 4..8 with silhouette reported at each k",
             "completion rate per cluster with a cluster bootstrap on instance_id",
             "the same clustering on two disjoint halves of the instances, compared by adjusted Rand index"],
  "thresholds": {"support": "silhouette >= 0.15 for H1, ARI >= 0.50 for H3, and a bootstrap interval excluding the "
                            "pooled rate for H2", "partial": "the floor met in one arm only",
                 "null": "no floor met"},
  "family": "three",
  "gate_scope": "design",
  "kill_gate": ("G9 froze `>= 0.90 of steps have an observation whose new-word share is computable` at design scope, "
                "because newness is one of the two feature blocks this taxonomy is built on and one of the two "
                "quantities its clusters are compared on. EXP-0196 measured 0.7876: 21% of commanded steps are "
                "followed by no observation at all. The design is stopped by its own sentence rather than re-cut on "
                "the surviving 79% under the same feature names, and the missingness is recorded as a property of "
                "the release (deviation W9-D01). G3's taxonomy floor fired too - 11 families with >= 500 steps "
                "against a frozen 12 - and is recorded with it."),
  "strata": ["task family", "rollout-length quartile"],
  "tables": ["table1_sample_and_structure.csv", "table2_taxonomy_census.csv", "table3_main_models.csv",
             "table4_strata_by_family.csv", "table5_robustness_inference.csv", "table6_baseline_comparison.csv",
             "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_cluster_structure.pdf", "fig2_main_effect.pdf",
              "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"],
 },
 # ------------------------------------------------------------------ T156
 "T156": {
  "pkg": "P055_the_exploration_exploitation_transition",
  "title": "The Exploration-Exploitation Transition in Agentic Search",
  "rq": "Does a recorded search start broad and narrow, and where does the narrowing happen?",
  "hypotheses": [
   "H1 the newness of what an agent learns declines with position in the rollout.",
   "H2 the family-switch rate declines with position too, and the two declines are reported separately so neither "
   "can be borrowed as the other's evidence.",
   "H3 the decline is not a length artifact: inside each rollout-length quartile the first-decile-versus-last-decile "
   "contrast has the same sign in at least three of the four quartiles."],
  "features": {"position_decile": "step index divided by the rollout's step count, binned in tenths",
               "new_information": "wave 6's new-word share of the observation",
               "switched": "this step's family differs from the previous step's"},
  "dvs": {"new_information": "H1's outcome", "switched": "H2's outcome"},
  "models": ["OLS on the newness z-score with position plus log step count, clustered on instance_id",
             "OLS on switching with position plus the same controls",
             "the same two fits inside each length quartile, with the sign reproduced across quartiles"],
  "thresholds": {"support": "|beta| >= 0.15 with CI excluding 0 and p_holm < 0.05",
                 "partial": "CI excludes 0 below the floor", "null": "CI includes 0",
                 "h3": "sign reproduction in >= 3 of 4 quartiles"},
  "family": "three",
  "gate_scope": "design",
  "kill_gate": ("G9's newness availability rule is design-scope for this design as well, because H1's outcome is the "
                "newness share itself and the curve is drawn over steps that have an observation: measured 0.7876 "
                "against a frozen 0.90. G7's switch floor passed comfortably (19,964 rollouts with >= 2 switches), so "
                "the part of the design that survives is the switch curve - and reporting only that half under this "
                "title would be the re-specification the sentence forbids, so the design is stopped and the measured "
                "coverage is recorded with the block."),
  "strata": ["rollout-length quartile", "task family"],
  "tables": ["table1_sample_and_structure.csv", "table2_transition_census.csv", "table3_main_models.csv",
             "table4_strata_by_length.csv", "table5_robustness_inference.csv", "table6_baseline_comparison.csv",
             "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_transition_curve.pdf", "fig2_main_effect.pdf",
              "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"],
 },
 # ------------------------------------------------------------------ T178
 "T178": {
  "pkg": "P051_early_signals_of_agent_search_failure",
  "title": "Can the First 20% of a Trajectory Predict Final Failure?",
  "rq": "How much of a rollout's ending is already legible in its first fifth, and what does the rest add?",
  "hypotheses": [
   "H1 a model restricted to first-fifth features separates completed from incomplete rollouts above chance, with a "
   "cross-validated AUC >= 0.65 against the frozen 0.5 floor.",
   "H2 the last fifth adds information the first fifth does not carry: the same model with end-phase features "
   "reaches a higher AUC, and the increment is reported with a cluster bootstrap on instance_id.",
   "H3 the early signal is not one big family: the AUC is reported inside each of the five largest task families, "
   "and the frozen claim needs >= 0.65 in at least three of them."],
  "features": {"first_fifth_features": "step count, family mixture, switch rate, repetition, command length and "
                                       "observation size, all computed over the first ceil(n_steps / 5) steps",
               "end_fifth_features": "the same block over the last fifth",
               "cv_auc": "5-fold stratified cross-validated AUC over instances, so no two folds share an instance"},
  "dvs": {"cv_auc": "H1's to H3's outcome"},
  "models": ["logistic regression on the first-fifth block with instance-disjoint folds, AUC with a cluster bootstrap",
             "the same model on the last-fifth block, and on both, with the increment bootstrapped",
             "the first-fifth model refit inside each of the five largest task families"],
  "thresholds": {"support": "AUC >= 0.65 with a bootstrap interval excluding 0.5",
                 "partial": "above 0.5, below 0.65", "null": "the interval includes 0.5",
                 "h3": ">= 3 of the 5 largest families at or above 0.65"},
  "family": "three",
  "gate_scope": "design",
  "kill_gate": ("G2 froze that >= 0.95 of rollouts carry a non-empty outcome label and measured 1.0, and G4 that "
                ">= 1,000 rollouts have >= 10 steps (measured 19,713), so a first fifth exists to read. What the "
                "census also measured, and what the design cannot escape, is the label's distribution: 560 Submitted "
                "against 19,428 incomplete. The positive class is 2.8% of rollouts, so every AUC here is estimated "
                "against that base rate, folds are disjoint by instance to stop a 1775-instance repeated-attempt "
                "structure leaking the label, and the counts are printed beside every estimate (deviation W9-D03)."),
  "strata": ["task family", "rollout-length quartile"],
  "tables": ["table1_sample_and_structure.csv", "table2_early_signal_census.csv", "table3_main_models.csv",
             "table4_strata_by_family.csv", "table5_robustness_inference.csv", "table6_baseline_comparison.csv",
             "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_early_feature_importance.pdf", "fig2_main_effect.pdf",
              "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"],
 },
 # ------------------------------------------------------------------ T179
 "T179": {
  "pkg": "P052_the_recovery_window_after_a_failed_step",
  "title": "The Recovery Window: How Late Can an Agent Still Be Saved?",
  "rq": "After an observation comes back failed, how much does a fast change of command buy, and does the value of "
        "changing decay with the delay?",
  "hypotheses": [
   "H1 a rollout whose command changes at the first step after a failed observation is more likely to end Submitted "
   "than one that does not change, holding length and family mixture fixed.",
   "H2 the advantage decays with the lag: the change-at-lag-k contrasts are reported for k = 1..5 and should fall "
   "monotonically toward zero.",
   "H3 the window is not the same as having more steps left: within each length quartile the lag-1 contrast keeps "
   "its sign in at least three of the four."],
  "features": {"changed_at_lag_k": "1 if the command k steps after a failed observation differs in name and arguments "
                                   "from the failing one",
               "first_change_lag": "the smallest k at which any change occurs, censored at 5",
               "remaining_steps": "steps left in the rollout at the failure"},
  "dvs": {"submitted": "H1's to H3's outcome, the release's own completion label"},
  "models": ["logistic on Submitted with the lag-1 change indicator, length, family mixture and repetition, "
             "clustered on instance_id",
             "the same specification at each lag from 1 to 5, reported as a profile rather than pooled",
             "the lag-1 specification inside each rollout-length quartile"],
  "thresholds": {"support": "|beta| >= 0.15 with CI excluding 0 and p_holm < 0.05",
                 "partial": "CI excludes 0 below the floor", "null": "CI includes 0",
                 "h2": "a monotone decline across the five measured lags",
                 "h3": "sign reproduction in >= 3 of 4 quartiles"},
  "family": "three",
  "gate_scope": "design",
  "kill_gate": ("G5 froze >= 500 rollouts containing a failed observation followed by a further command and measured "
                "17,229, and G10 measured duration on 1.0 of rollouts, so the window has both an event and a cost "
                "axis. The label sparsity that qualifies T178 applies here too and is stated with the estimates "
                "rather than in a footnote."),
  "strata": ["task family", "rollout-length quartile"],
  "tables": ["table1_sample_and_structure.csv", "table2_recovery_census.csv", "table3_main_models.csv",
             "table4_strata_by_length.csv", "table5_robustness_inference.csv", "table6_baseline_comparison.csv",
             "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_recovery_window.pdf", "fig2_main_effect.pdf",
              "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"],
 },
 # ------------------------------------------------------------------ T193
 "T193": {
  "pkg": "P053_which_rollouts_deserve_reuse",
  "title": "Which Trajectories Deserve to Become Organisational Knowledge?",
  "rq": "When a task has been attempted several times, does the rollout that succeeded also deserve to be kept, or "
        "is a cheaper, less repetitive attempt usually the better teacher?",
  "hypotheses": [
   "H1 ranking repeated instances by success alone and by a cost-adjusted value (success, then fewer steps, then "
   "less repetition) agree only partially: Kendall's tau between the two rankings, bootstrapped on the instance, is "
   "below the frozen 0.80.",
   "H2 in most multi-rollout instances a cheaper successful rollout than the longest one exists - the measured share "
   "with its bootstrap interval is the quantity the sentence asks for, and it is reported rather than tested.",
   "H3 the disagreement is not driven by the rare successes: restricted to instances with at least two "
   "observations-bearing rollouts the tau keeps its sign, and removing the single most expensive rollout per "
   "instance leaves the ordering still disagreeing."],
  "features": {"cost_adjusted_value": "a rank score: Submitted first, then fewer commanded steps, then a lower "
                                      "exact-repeat share, then shorter duration",
               "success_only_rank": "the ranking by the release's label alone",
               "tau": "Kendall's tau between the two rankings within instances with >= 2 rollouts",
               "cheaper_success_exists": "1 for an instance where a successful rollout uses fewer steps than the "
                                         "longest rollout of that instance"},
  "dvs": {"tau": "H1's and H3's outcome", "cheaper_success_share": "H2's outcome"},
  "models": ["within-instance rank agreement with a cluster bootstrap over instances",
             "the measured share of instances with a cheaper successful rollout, with its interval",
             "the same agreement after the stated restrictions, reported as robustness rather than as a new test"],
  "thresholds": {"support": "tau <= 0.80 with a bootstrap interval excluding 0.80",
                 "partial": "the point estimate below the floor with the interval covering it",
                 "null": "an interval above the floor",
                 "h2": "descriptive: the sentence asks for a share and an interval, so no band applies"},
  "family": "three",
  "gate_scope": "design",
  "kill_gate": ("G8 froze >= 300 instances attempted more than once, because a selection rule needs a comparison "
                "within one task, and EXP-0196 measured 1,775 of 1,784 - the release is almost entirely repeated "
                "attempts. G10's cost column and G2's label both measured 1.0. The success arm is thin for the reason "
                "T178 states: 560 Submitted rollouts in 19,988, so H2's share is computed on what successes exist and "
                "the denominator is printed with it."),
  "strata": ["rollouts per instance band", "task family"],
  "tables": ["table1_sample_and_structure.csv", "table2_selection_census.csv", "table3_main_models.csv",
             "table4_strata_by_repetitions.csv", "table5_robustness_inference.csv",
             "table6_baseline_comparison.csv", "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_rank_disagreement.pdf", "fig2_main_effect.pdf",
              "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"],
 },
}

# census key (a dotted path into its `measured` block) -> the name this freeze gives it, so EXP-0163 can rewrite the
# PREMISES literal below from the artefact rather than from a hand-kept copy.
PREMISE_MAP = {
 "trajectories": "rollouts_drawn", "trajectories_parsed": "rollouts_parsed",
 "trajectory_parse_share": "rollout_parse_share", "steps_total": "commanded_steps",
 "mean_steps": "mean_steps_per_rollout", "median_steps": "median_steps_per_rollout",
 "instances": "task_instances", "instances_with_2plus_rollouts": "instances_with_repeated_rollouts",
 "outcome_label_share": "outcome_label_share", "newness_available_share": "newness_available_share",
 "duration_present_share": "duration_available_share", "distinct_command_families": "distinct_command_families",
 "families_with_500plus_steps": "families_500plus_steps", "distinct_task_prefixes": "distinct_task_prefixes",
 "task_prefixes_with_200plus_trajectories": "task_families_200plus_rollouts",
 "distinct_family_bigrams": "distinct_family_bigrams",
 "bigrams_with_100plus_occurrences": "bigrams_100plus",
 "trajectories_with_10plus_steps": "rollouts_with_10plus_steps",
 "trajectories_with_2plus_switches": "rollouts_with_2plus_switches",
 "trajectories_with_a_failure_then_a_further_command": "rollouts_with_a_failure_then_a_command",
 "mean_switches_per_trajectory": "mean_switches_per_rollout",
}

PREMISES = {
    "census": "EXP-0196 (EXP0196_wave9_premise_census_20260924T200504.json)",
    "transcribed_by": "02_shared_code/registry/refresh_wave_premises.py (EXP-0163); no number in this block is typed by hand",
    "measured": {
        "rollouts_drawn": 20000,
        "rollouts_parsed": 19988,
        "rollout_parse_share": 0.9994,
        "commanded_steps": 292992,
        "mean_steps_per_rollout": 14.66,
        "median_steps_per_rollout": 15.0,
        "task_instances": 1784,
        "instances_with_repeated_rollouts": 1775,
        "outcome_label_share": 1.0,
        "newness_available_share": 0.7876,
        "duration_available_share": 1.0,
        "distinct_command_families": 13,
        "families_500plus_steps": 11,
        "distinct_task_prefixes": 805,
        "task_families_200plus_rollouts": 2,
        "distinct_family_bigrams": 138,
        "bigrams_100plus": 77,
        "rollouts_with_10plus_steps": 19713,
        "rollouts_with_2plus_switches": 19964,
        "rollouts_with_a_failure_then_a_command": 17229,
        "mean_switches_per_rollout": 8.0,
    },
    "gates": {
          "G10_duration_available": {'blocks': ['T193'], 'fires': False, 'measured': 1.0, 'rule': ">= 0.90 of rollouts carry a duration, the cost axis of T179's window and T193's value trade-off", 'scope': 'H2', 'threshold': 0.9},
          "G11_cluster_count": {'blocks': ['T151', 'T153', 'T156', 'T178', 'T179', 'T193'], 'fires': False, 'measured': 1784, 'rule': '>= 500 task instances, so an instance-clustered interval exists for every design in the wave', 'scope': 'design', 'threshold': 500},
          "G12_bigram_support": {'blocks': ['T153'], 'fires': False, 'measured': 77, 'rule': '>= 50 family bigrams occurring >= 100 times, the support a transition matrix has to be estimated on', 'scope': 'H2', 'threshold': 50},
          "G1_rollouts_parseable": {'blocks': ['T151', 'T153', 'T156', 'T178', 'T179', 'T193'], 'fires': False, 'measured': 0.9994, 'rule': '>= 0.95 of drawn rollouts yield at least one commanded step', 'scope': 'design', 'threshold': 0.95},
          "G2_outcome_label_present": {'blocks': ['T156', 'T178', 'T193'], 'fires': False, 'measured': 1.0, 'rule': '>= 0.95 of rollouts carry a non-empty exit_status, which is the only final-outcome label this release has and three designs condition on it', 'scope': 'design', 'threshold': 0.95},
          "G3_command_families_for_a_taxonomy": {'blocks': ['T151'], 'fires': True, 'measured': 11, 'rule': '>= 12 command families with >= 500 steps each, below which a taxonomy of agent information behaviour would be a split of two bins', 'scope': 'H1', 'threshold': 12},
          "G4_rollouts_long_enough_for_a_first_fifth": {'blocks': ['T178'], 'fires': False, 'measured': 19713, 'rule': '>= 1,000 rollouts have >= 10 commanded steps, so a first-fifth feature is more than one step', 'scope': 'H1', 'threshold': 1000},
          "G5_failure_then_a_further_command": {'blocks': ['T179'], 'fires': False, 'measured': 17229, 'rule': '>= 500 rollouts contain a failed observation followed by another command - the window T179 measures', 'scope': 'H1', 'threshold': 500},
          "G6_task_families_for_a_cross_task_grammar": {'blocks': ['T153'], 'fires': True, 'measured': 2, 'rule': '>= 10 task families with >= 200 rollouts each, which is the minimum for comparing a grammar across tasks rather than within one', 'scope': 'H1', 'threshold': 10},
          "G7_trajectories_with_switches": {'blocks': ['T156'], 'fires': False, 'measured': 19964, 'rule': '>= 1,000 rollouts make >= 2 family switches, so a transition curve has variation to fit', 'scope': 'H1', 'threshold': 1000},
          "G8_instances_with_repeated_rollouts": {'blocks': ['T193'], 'fires': False, 'measured': 1775, 'rule': '>= 300 task instances attempted more than once, the comparison T193 needs to ask which rollout deserved reuse', 'scope': 'H1', 'threshold': 300},
          "G9_newness_available": {'blocks': ['T151', 'T156'], 'fires': True, 'measured': 0.7876, 'rule': '>= 0.90 of steps have an observation whose new-word share is computable', 'scope': 'design', 'threshold': 0.9},
      },
    "verdict": {
          "blocked_gates": ['G3_command_families_for_a_taxonomy', 'G6_task_families_for_a_cross_task_grammar', 'G9_newness_available'],
          "blocked_whole_design": ['T151', 'T156'],
          "claim_limited": {'G3_command_families_for_a_taxonomy': 'H1', 'G6_task_families_for_a_cross_task_grammar': 'H1'},
      },
    "note": "a fired gate is a result, not an obstacle: it stops exactly what its frozen sentence scopes",
    "runnable": list(RUNNABLE),
}    # filled verbatim from the census artefact - never edit these blocks by hand

FAILED_RUNS = [
 "EXP0196 first launch was a 400-rollout smoke run (results_raw/EXP0196_wave9_premise_census_20260924T200110.json), "
 "used to prove the step spine, the derived switch and lag definitions and the gate wiring; several gates fired there "
 "only because the draw was 400 rollouts, so that generation is superseded and the values cited are the whole-sample "
 "ones, which were produced twice with identical output.",
]

EXTRA_DEVIATIONS = [
 ("W9-D01", "A fifth of commanded steps have no observation at all, which stopped two designs",
            "G9 froze '>= 0.90 of steps have an observation whose new-word share is computable' at design scope "
            "before the census ran, and EXP-0196 measured 0.7876 on all 292,992 commanded steps: 21% of the steps "
            "this release records are a command with nothing after it - the rollout simply ends there. T151 clusters "
            "on a newness block and T156's H1 outcome is newness itself, so continuing on the surviving 79% would "
            "mean measuring a different quantity under the same names. Both are recorded as stopped by their own "
            "gates with the value cited, and no threshold was lowered."),
 ("W9-D02", "The release's org-level grouping is two names, not ten families",
            "G6 froze >= 10 task families with >= 200 rollouts each for T153's cross-task claim. The census found 805 "
            "distinct org prefixes and only 2 with >= 200 rollouts, because the corpus is organised by repository and "
            "the prefix is the organisation. T153's H1 is therefore claim-limited by its own sentence; its bigram "
            "arms, which need transition support rather than family breadth, stand on the 77 bigrams occurring "
            ">= 100 times, and both counts are printed in every affected row."),
 ("W9-D03", "The outcome label exists and is almost one-valued",
            "G2 measured 1.0 coverage of exit_status, which is why T178 and T193 were not blocked, but the label's "
            "distribution is 560 Submitted against 19,428 incomplete - 2.8% positive. Neither design's frozen floor "
            "was written against the base rate, so neither is moved: T178 keeps its AUC >= 0.65 rule and reports the "
            "positive count and the instance-disjoint folds beside every estimate, and T193's H2 is reported as a "
            "measured share with the denominator of successes it was computed on."),
 ("W9-D04", "Two step-level quantities the census names are derived, not stored",
            "`switched` and the notion of a step continuing are not fields of the release: a switch is this step's "
            "family differing from the previous step's and a continuation is any later commanded step in the same "
            "rollout. Both are derived identically in the census and in the frame, and the census's self-test asserts "
            "the derivations on a hand-built rollout so the definition cannot drift between the two layers that "
            "claim to share one reader."),
 ("W9-D05", "The release truncates every rollout at 15 commanded steps, so 'length' is almost not a variable",
            "86.8% of the 19,988 rollouts sit at exactly 15 commanded steps and the standard deviation of log steps "
            "inside T179's cell is 0.083. That is a property of how the corpus was collected, not of agent behaviour, "
            "and it means the length control the designs promise does little work: the fact is printed inside the "
            "affected rows (`rollouts_at_the_release_s_step_cap`, `sd_of_log_steps_in_this_cell`) rather than being "
            "hidden behind a non-significant coefficient, and no design's threshold was relaxed because of it."),
 ("W9-D06", "Almost every rollout changes its command after a failure, so the recovery contrast is a minority cell",
            "97.6% of the rollouts that have a failed observation followed by a further command do change the command "
            "at lag 1, which leaves 43 non-changers as the comparison arm against 16,763 changers. T179's H1 is "
            "reported as null with a wide cluster-robust interval (0.40, CI -1.85 to 2.66) precisely because of that "
            "shape, and the arm sizes are printed with the estimate; the alternative - a smaller model without the "
            "near-degenerate indicator - would answer a question no sentence in this freeze asks."),
 ("W9-D07", "The imported baseline ladder defaulted to the previous wave's control set and silently fitted nothing",
            "Wave 7's `baselines` helper supplies its own controls when a caller passes none, so wave 9's nested "
            "comparison came back as a single row reading 'not fitted on these rows' - a column name wave 9's frame "
            "does not have. The helper is now re-bound inside wave 9 to default to this wave's controls, and the "
            "ladder is fitted again; the earlier generation is superseded. Recorded next to the same class of defect "
            "as W8-D05: reusing an estimator across waves means reusing its defaults unless they are overridden."),
]
