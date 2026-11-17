"""The wave-6 protocol freeze: the economics of an agent's search on SWE-ZERO-12M's step-level trajectories.

Six designs (T155 depth against need complexity, T157 information scent and the next choice, T158 marginal gain and
persistence, T168 the cost of switching command families, T170 path dependence of the first action, T174 repetition
and rumination). What makes this wave different from waves 4 and 5 is the substrate: hermes carries one assistant
turn per step with its reasoning attached, while SWE-ZERO carries a whole rollout - an ordered sequence of a command,
the output that came back, and a termination label - so a step here is an action with a predecessor and a successor,
which is what a depth, a switch, a repeat and a path are made of.

Every threshold, band, direction and kill-gate sentence below was written before the frame was built, and the gate
each design carries cites the value EXP-0172 measured for it. Two readings of that census, twelve files apart in
nothing, are byte-identical apart from their timestamps, which is why the numbers quoted here can be quoted again.

The whole module is the protocol: `freeze_wave.py` renders it into `protocol_freeze.md`, `exp_wave6_features.py`
implements the features, and nothing in the analysis scripts is allowed to introduce a number that is not here.
"""
from __future__ import annotations

EXP_OF = {"T155": "EXP-0174", "T157": "EXP-0175", "T158": "EXP-0176", "T168": "EXP-0177", "T170": "EXP-0178",
          "T174": "EXP-0179"}
RUNNABLE = tuple(EXP_OF)
FEATURE_EXP = "EXP-0173"
PREMISE_EXP = "EXP-0172"
BATTERY_EXP = "EXP-0180"
ENCODER_EXP = ""
SEED = 42
BANDS = {"small": 0.05, "medium": 0.15, "large": 0.30}
MATRIX = "results_raw/EXP0173_wave6_step_matrix_*.json"
PREMISE_GLOB = "results_raw/EXP0172_wave6_premise_census_*.json"
BATTERY = "results_raw/EXP0180_wave6_battery_0180_*.json"
MATRIX_GLOB = MATRIX
BATTERY_GLOB = BATTERY
ENCODER_GLOB = ""
MATRIX_SCRIPT = "exp_wave6_features.py"
BATTERY_SCRIPT = "exp_wave6_battery.py"
PROBE_SCRIPT = "probe_wave6_premises.py"
SCRIPT_OF = {t: "exp_wave6_designs.py" for t in RUNNABLE}
MAIN_SCRIPT_OF = {t: "exp_wave6_designs.py" for t in RUNNABLE}
DESIGNS_MODULE = "topic_designs_wave6"
STAGE_RX = "wave6_main"
CLEAN_ROOM_ONLY_FLAG = "--only"
CLEAN_ROOM_MODE = "full"
SUBSTRATE_LABEL = ("SWE-ZERO-12M trajectory release (AlienKevin), 12 of its 1,230 parquet files drawn with seed 42 "
                   "and every row of each read: ordered rollouts in which an assistant message issues one fenced shell "
                   "command and the next message returns its output; the frozen sample holds 120,000 trajectories in "
                   "1,793 instances and 1,758,365 assistant steps, and P001's test split does not exist in this "
                   "corpus - 0 rows of it were read")
SAMPLE_FIELDS = ("corpus", "files_read", "sample_cap", "trajectories", "instances", "assistant_steps",
                 "parsed_steps", "unparsed_steps", "median_steps_per_trajectory", "commands_with_observation_share",
                 "cluster_unit")
CONTRIBUTION_POPULATION = ("a corpus of complete software-engineering rollouts, where every step is a shell command "
                           "the agent wrote and an output the machine returned, read with frozen rule and lexical "
                           "instruments and with no ranker, no model and no human label")

COMMON = {
    "seed": SEED,
    "bands": BANDS,
    "module": "topic_designs_wave6",
    "sample": {"traj_cap": 20000, "cluster_unit": "instance_id",
              "unit_of_analysis": "the assistant step inside a rollout, clustered within its instance",
              "rule": "the 12 parquet files the census drew with seed 42 are the wave's whole substrate; within them "
                      "the frame is one seeded draw of 20,000 trajectory rows (draw 42, no re-draw per hypothesis), "
                      "every step of each selected rollout kept; the file is the sampling unit and the instance the "
                      "cluster",
              "excluded": "rows of P001's test split - this release has none, and no routing row is read here"},
    "instruments": ("all constructs are rule or lexical: a command block is what sits between ``` fences, its family "
                    "is the first executable named by a frozen 12-family table, an observation is the message that "
                    "follows and starts with 'Observation', new information is the share of an observation's content "
                    "words not present in any earlier observation or in the issue text, and the termination label is "
                    "the release's own exit_status field"),
}

DESIGNS = {
 # ------------------------------------------------------------------ T155
 "T155": {
  "pkg": "P033_search_depth_vs_need_complexity",
  "title": "Does Search Depth Match Information-Need Complexity?",
  "rq": "When the same task is rolled out many times, does the number of information steps an agent takes track how "
        "complex the stated need is, or is depth a property of the rollout rather than of the task?",
  "hypotheses": [
   "H1 within an instance, a one-SD longer issue text goes with more assistant steps: the need's stated complexity "
   "has to be a property of the task for depth to answer to it, so the contrast is estimated across rollouts of the "
   "same instance, not across instances.",
   "H2 the step count at which a rollout terminates by submission rather than by running out is below the step count "
   "rollouts reach when they do not submit: depth is compared against the release's own termination label.",
   "H3 the sign of H1 reproduces inside each stratum of task family that carries >= 200 rollouts; a depth effect "
   "that exists only in the pooled data is an instance-mix effect."],
  "features": {
   "log_steps": "log1p of the number of assistant steps that issued a command in the rollout",
   "need_words": "content words in the issue text of the task, standardised within instance (the task is held fixed)",
   "submitted": "1 if exit_status is the submission label, 0 if the rollout is recorded as incomplete",
   "step_limit_reached": "the maximum step count any rollout of this instance reaches, the budget the agent ran out "
   "of - reported next to H2 so a ceiling cannot be read as a choice"},
  "dvs": {"log_steps": "H1's outcome, standardised for the band test",
          "submitted": "H2's outcome: the run ended by submitting rather than by running out"},
  "models": [
   "OLS on log_steps with the within-instance standardised need length plus the standard controls, clustered on "
   "instance_id",
   "logistic on submitted with log_steps plus the standard controls, clustered on instance_id",
   "the same H1 specification estimated inside each task-family stratum, reported as a sign-reproduction count"],
  "thresholds": {"support": "|beta| >= 0.15 with CI excluding 0 and p_holm < 0.05",
                 "partial": "CI excludes 0 below the floor", "null": "CI includes 0"},
  "family": "three",
  "gate_scope": "design",
  "kill_gate": ("G3 needs an outcome label with >= 2 values whose rarest carries >= 200 trajectories and G5 needs "
                ">= 200 instances with >= 2 rollouts. EXP-0172 measured 2 levels (Submitted 3,625; incomplete "
                "116,375) and 1,787 instances with 2+ rollouts, so both clear and the design stands."),
  "strata": ["task family (repository)", "issue-length quartile", "step-budget quartile"],
  "tables": ["table1_sample_and_structure.csv", "table2_depth_and_need_census.csv", "table3_main_models.csv",
             "table4_strata_by_repository.csv", "table5_robustness_inference.csv", "table6_baseline_comparison.csv",
             "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_depth_examples.pdf", "fig2_main_effect.pdf",
              "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"],
 },
 # ------------------------------------------------------------------ T157
 "T157": {
  "pkg": "P034_information_scent_and_the_next_choice",
  "title": "Can Information Scent Predict an Agent's Next Choice?",
  "rq": "Before an agent issues a command it has said what it expects to find. Does the overlap between that "
        "expectation and the command it actually types go with the step being rewarded with information it did not "
        "already have?",
  "hypotheses": [
   "H1 a step whose pre-command text overlaps its own command more (higher scent) is more likely to return "
   "observation content that was not present earlier in the rollout.",
   "H2 the effect is not a property of one similarity definition: the same association estimated with an asymmetric "
   "containment measure rather than a symmetric overlap has the same sign.",
   "H3 scent is not merely verbosity - a control count of the same step's words with no referential content leaves "
   "the association intact, and on its own produces nothing."],
  "features": {
   "scent_jaccard": "|content words of the text before the command INTERSECT content words of the command| / |their "
                    "union|, 0 when either side is empty",
   "scent_contain": "the same intersection divided by the number of content words in the pre-command text only - an "
                    "asymmetric reading of the same two strings",
   "new_information": "share of the returned observation's content words that appear in no earlier observation of "
                      "the rollout and not in the issue text",
   "step_words": "content words in the assistant's own text for the step, the verbosity control"},
  "dvs": {"new_information": "H1's and H3's outcome, standardised for the band test",
          "scent_contain": "H2's re-estimation of the same construct under a second instrument"},
  "models": [
   "OLS on standardised new_information with scent_jaccard plus the standard controls, clustered on instance_id",
   "the identical model with scent_contain in place of scent_jaccard - the instrument-sensitivity arm, compared by "
   "sign and interval rather than by a p-value race",
   "OLS on standardised new_information with the verbosity control alone, the specificity arm"],
  "thresholds": {"support": "|beta| >= 0.15 with CI excluding 0 and p_holm < 0.05",
                 "partial": "CI excludes 0 below the floor", "null": "CI includes 0"},
  "family": "three",
  "gate_scope": "H2",
  "kill_gate": ("G9 needs >= 0.80 of steps after the first to be followed by a non-empty observation and G2 >= 0.80 "
                "of fenced steps to yield a parsable command. EXP-0172 measured 0.9998 and 0.9998, so the frame can "
                "compute scent and newness on the whole sample; H2 is scoped to the instrument pair, which is "
                "reported whether or not the two readings agree."),
  "strata": ["position in the rollout (thirds)", "command family of the step"],
  "tables": ["table1_sample_and_structure.csv", "table2_scent_and_newness_census.csv", "table3_main_models.csv",
             "table4_strata_by_step_position.csv", "table5_robustness_inference.csv",
             "table6_baseline_comparison.csv", "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_scent_examples.pdf", "fig2_main_effect.pdf", "fig3_mechanism_by_band.pdf",
              "fig4_robustness.pdf"],
 },
 # ------------------------------------------------------------------ T158
 "T158": {
  "pkg": "P035_marginal_gain_and_search_persistence",
  "title": "Diminishing Marginal Information Gain and the Persistence of Search",
  "rq": "Does an agent keep searching when the next step is unlikely to tell it anything new, and does a failed "
        "step make it more or less likely to continue?",
  "hypotheses": [
   "H1 the probability of taking another step falls as the information the last step returned was new: search stops "
   "when the haul is good, which is the diminishing-gain reading of the step sequence.",
   "H2 after an observation carrying a failure marker, continuing is more likely than after one that carries none - "
   "persistence in the face of a step that produced nothing usable.",
   "H3 the cumulative new-information profile of a rollout predicts whether it ends by submission, with the sign "
   "reproduced in each quartile of rollout length."],
  "features": {
   "continues": "1 if the rollout contains another assistant step after this observation",
   "new_information": "as T157: the share of this observation's content words not seen earlier in the rollout",
   "failed_observation": "1 if this observation carries any marker of the frozen failure list (no such file, "
                         "permission denied, traceback, error:, exit code, ...)",
   "cumulative_newness": "the running mean of new_information up to and including this step"},
  "dvs": {"continues": "H1's and H2's outcome: whether the search continued past this observation",
          "submitted": "H3's outcome: the rollout ended by submitting rather than running out"},
  "models": [
   "logistic on continues with the previous observation's standardised newness plus the standard controls, clustered "
   "on instance_id",
   "logistic on continues with the failure indicator plus the standard controls, clustered on instance_id",
   "logistic on submitted with cumulative newness plus the standard controls inside each rollout-length quartile, "
   "reported as a sign-reproduction count"],
  "thresholds": {"support": "|beta| >= 0.15 with CI excluding 0 and p_holm < 0.05",
                 "partial": "CI excludes 0 below the floor", "null": "CI includes 0"},
  "family": "three",
  "gate_scope": "H2",
  "kill_gate": ("G11 froze >= 0.20 of observations carrying a failure marker for H2's conditioning cell. EXP-0172 "
                "measured 0.1855, so the gate fires and H2 is limited by its own sentence; the cell it describes is "
                "large in absolute terms and that size is reported beside the verdict. G4 (>= 0.80 of trajectories "
                "with >= 3 steps) measured 0.9993, so H1 and H3 stand."),
  "strata": ["rollout-length quartile", "command family of the failing step"],
  "tables": ["table1_sample_and_structure.csv", "table2_gain_and_persistence_census.csv", "table3_main_models.csv",
             "table4_strata_by_length_quartile.csv", "table5_robustness_inference.csv",
             "table6_baseline_comparison.csv", "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_gain_curve.pdf", "fig2_main_effect.pdf", "fig3_mechanism_by_band.pdf",
              "fig4_robustness.pdf"],
 },
 # ------------------------------------------------------------------ T168
 "T168": {
  "pkg": "P036_command_family_switching_cost",
  "title": "Tool Switching Cost and the Quality of Exploration",
  "rq": "When an agent changes the kind of information action it is performing - from reading to searching to "
        "editing - does the step right after the switch return less new information than one that stayed put?",
  "hypotheses": [
   "H1 a step whose command family differs from the previous step's returns less new information than a step that "
   "repeats the family - the switching cost, measured on the output rather than on the intention.",
   "H2 a rollout that switches more often reaches more steps before it terminates, so switching is not simply "
   "inefficiency: the two quantities are estimated together and reported apart.",
   "H3 the sign of H1 reproduces within each command family large enough to have a switching past, and not only in "
   "the pooled estimate."],
  "features": {
   "switched": "1 if this step's command family differs from the previous step's (0 for the first step, which is "
               "excluded from the contrast and counted separately)",
   "family": "the step's command family from the frozen 12-family table (search_name, search_content, read_file, "
             "list, edit, version_control, run_python, ...)",
   "new_information": "as T157", "switch_rate": "share of a rollout's steps after the first that changed family"},
  "dvs": {"new_information": "H1's and H3's outcome, standardised for the band test",
          "log_steps": "H2's outcome: how deep the rollout got before it terminated"},
  "models": [
   "OLS on standardised new_information with the switch indicator plus the standard controls, clustered on "
   "instance_id",
   "OLS on log_steps with the rollout's switch rate plus the standard controls, clustered on instance_id",
   "the H1 specification re-estimated within each family stratum with >= 200 switching steps, reported as a "
   "sign-reproduction count"],
  "thresholds": {"support": "|beta| >= 0.15 with CI excluding 0 and p_holm < 0.05",
                 "partial": "CI excludes 0 below the floor", "null": "CI includes 0"},
  "family": "three",
  "gate_scope": "H1",
  "kill_gate": ("G7 froze >= 200 trajectories using >= 3 distinct command families so that a switch exists to study. "
                "EXP-0172 measured 118,598 and a mean of 8.0 family changes per trajectory, so H1 and H2 stand; H3 "
                "is additionally scoped by the per-family cell size, which is reported rather than assumed."),
  "strata": ["command family of the step", "position in the rollout (thirds)"],
  "tables": ["table1_sample_and_structure.csv", "table2_switching_census.csv", "table3_main_models.csv",
             "table4_strata_by_command_family.csv", "table5_robustness_inference.csv",
             "table6_baseline_comparison.csv", "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_switch_examples.pdf", "fig2_main_effect.pdf",
              "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"],
 },
 # ------------------------------------------------------------------ T170
 "T170": {
  "pkg": "P037_first_action_path_dependence",
  "title": "Path Dependence of the First Action",
  "rq": "The same task is rolled out many times from the same instruction. Does the first information action an "
        "agent takes determine the shape of the rest of the search, or does each step answer to the task afresh?",
  "hypotheses": [
   "H1 within an instance, a rollout whose first command family differs from the instance's modal first family "
   "differs in the family mix of its remaining steps: the first action locks in a path rather than being a "
   "replaceable opening move.",
   "H2 continuing in the same family as the first step is associated with terminating by submission rather than "
   "running out, estimated with depth held in the model so a short path is not credited to the habit.",
   "H3 the concentration of family use after the first step is higher when the first step's family is a search "
   "family than when it is a reading or editing family, which is the mechanism the lock-in claim needs."],
  "features": {
   "first_family": "family of the rollout's first commanded step",
   "instance_modal_first_family": "the modal first family across rollouts of the same instance, computed on the "
                                  "other rollouts of that instance only (leave-one-out, so a rollout is never "
                                  "compared with itself)",
   "family_concentration": "share of the steps after the first that belong to the first step's family",
   "stays_in_family": "1 if this step's family equals the first step's family"},
  "dvs": {"family_concentration": "H1's outcome, standardised for the band test",
          "submitted": "H2's outcome", "stays_in_family": "H3's outcome at the step level"},
  "models": [
   "OLS on standardised family_concentration with the off-modal-first-family indicator plus the standard controls, "
   "clustered on instance_id",
   "logistic on submitted with stays_in_family, log_steps and the standard controls, clustered on instance_id",
   "logistic on stays_in_family with a search-family-first indicator plus the standard controls, clustered on "
   "instance_id"],
  "thresholds": {"support": "|beta| >= 0.15 with CI excluding 0 and p_holm < 0.05",
                 "partial": "CI excludes 0 below the floor", "null": "CI includes 0"},
  "family": "three",
  "gate_scope": "H1",
  "kill_gate": ("G8 froze >= 200 instances whose rollouts differ in first command family, because without that "
                "spread the first action is a property of the task and not a choice. EXP-0172 measured 771 such "
                "instances; it also measured that 97.99% of rollouts open with a name search, so the contrast is "
                "anchored on the 2% minority and this sentence states that limitation before any estimate is read."),
  "strata": ["first command family", "issue-length quartile"],
  "tables": ["table1_sample_and_structure.csv", "table2_first_action_census.csv", "table3_main_models.csv",
             "table4_strata_by_first_family.csv", "table5_robustness_inference.csv",
             "table6_baseline_comparison.csv", "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_path_examples.pdf", "fig2_main_effect.pdf", "fig3_mechanism_by_band.pdf",
              "fig4_robustness.pdf"],
 },
 # ------------------------------------------------------------------ T174
 "T174": {
  "pkg": "P038_repetition_and_rumination",
  "title": "Repetitive Search and Information Rumination",
  "rq": "Some agents re-run a command they already ran. Does repeating an information action buy anything, or is it "
        "the signature of a search that has stopped making progress?",
  "hypotheses": [
   "H1 a step that re-issues a command already issued earlier in the same rollout returns less new information than "
   "a step running that command for the first time, estimated within rollout so the comparison is like for like.",
   "H2 rollouts containing an exact repeated command are less likely to end by submission than rollouts that never "
   "repeat, with the number of steps in the model so repetition is not just a proxy for a long search.",
   "H3 the deficit in H1 grows with the number of times the command has already been run, reported as the "
   "measured repetition count profile rather than as a fitted slope."],
  "features": {
   "is_repeat": "1 if this step's whitespace-normalised command string is identical to an earlier step's in the "
                "same rollout",
   "repeat_index": "how many times this exact command has already been issued in this rollout (0 for the first)",
   "new_information": "as T157", "has_exact_repeat": "1 if the rollout contains at least one repeated command"},
  "dvs": {"new_information": "H1's and H3's outcome, standardised for the band test",
          "submitted": "H2's outcome"},
  "models": [
   "OLS on standardised new_information with the repeat indicator plus the standard controls, clustered on "
   "instance_id",
   "logistic on submitted with has_exact_repeat, log_steps and the standard controls, clustered on instance_id",
   "the mean newness by repetition count, with a cluster bootstrap interval per count"],
  "thresholds": {"support": "|beta| >= 0.15 with CI excluding 0 and p_holm < 0.05",
                 "partial": "CI excludes 0 below the floor", "null": "CI includes 0"},
  "family": "three",
  "gate_scope": "H1",
  "kill_gate": ("G6 froze >= 200 trajectories containing an exact repeated command. EXP-0172 measured 27,576 of "
                "120,000, so the contrast has its subject; G12 (>= 30 instances for a cluster interval) measured "
                "1,793."),
  "strata": ["repetition count", "command family of the repeated step"],
  "tables": ["table1_sample_and_structure.csv", "table2_repetition_census.csv", "table3_main_models.csv",
             "table4_strata_by_repeat_count.csv", "table5_robustness_inference.csv",
             "table6_baseline_comparison.csv", "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_repeat_examples.pdf", "fig2_main_effect.pdf",
              "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"],
 },
}

# census key (a dotted path into its `measured` block) -> the name this freeze gives it. EXP-0163 regenerates the
# PREMISES literal below from the census artefact through this map, so the freeze cannot keep quoting numbers a
# rebuilt census no longer produces.
PREMISE_MAP = {
 "trajectories": "trajectories", "instances": "instances", "assistant_steps": "assistant_steps",
 "parsed_steps": "parsed_command_steps", "unparsed_steps": "unparsed_command_steps",
 "command_parse_share": "command_parse_share", "share_ge3_steps": "share_of_trajectories_ge3_steps",
 "median_steps_per_trajectory": "median_steps_per_trajectory",
 "obs_after_first_step_share_of_multi_step_rows": "observation_text_computable_share",
 "failure_marker_share_of_observation_bearing_steps": "failure_marker_share_of_observations",
 "instances_with_2plus_rollouts": "instances_with_2plus_rollouts",
 "instances_with_differing_first_family": "instances_with_differing_first_family",
 "trajectories_with_exact_repeat": "trajectories_with_exact_repeat",
 "trajectories_with_3plus_families": "trajectories_with_3plus_families",
 "mean_switches_per_trajectory": "mean_family_switches_per_trajectory",
 "rarest_outcome_trajectories": "rarest_outcome_label_trajectories",
 "outcome_levels": "outcome_label_levels",
 "issue_ge40_words_instances": "issue_ge40_word_instances",
 "repo_field_present_share": "repository_field_present_share",
}

PREMISES = {
    "census": "EXP-0172 (EXP0172_wave6_premise_census_20260924T154332.json)",
    "transcribed_by": "02_shared_code/registry/refresh_wave_premises.py (EXP-0163); no number in this block is typed by hand",
    "measured": {
        "trajectories": 120000,
        "instances": 1793,
        "assistant_steps": 1758365,
        "parsed_command_steps": 1757969,
        "unparsed_command_steps": 396,
        "command_parse_share": 0.9998,
        "share_of_trajectories_ge3_steps": 0.9993,
        "median_steps_per_trajectory": 15.0,
        "observation_text_computable_share": 0.9998,
        "failure_marker_share_of_observations": 0.1855,
        "instances_with_2plus_rollouts": 1787,
        "instances_with_differing_first_family": 771,
        "trajectories_with_exact_repeat": 27576,
        "trajectories_with_3plus_families": 118598,
        "mean_family_switches_per_trajectory": 8.0025,
        "rarest_outcome_label_trajectories": 3625,
        "outcome_label_levels": {'Submitted': 3625, 'incomplete': 116375},
        "issue_ge40_word_instances": 1793,
        "repository_field_present_share": 1.0,
    },
    "gates": {
          "G10_need_complexity_proxy": {'blocks': ['T155'], 'fires': False, 'measured': 1793.0, 'scope': 'H1'},
          "G11_failure_marker_present": {'blocks': ['T158'], 'fires': True, 'measured': 0.1855, 'scope': 'H2'},
          "G12_cluster_count": {'blocks': ['T155', 'T157', 'T158', 'T168', 'T170', 'T174'], 'fires': False, 'measured': 1793.0, 'scope': 'design'},
          "G1_trajectory_rows_recoverable": {'blocks': ['T155', 'T157', 'T158', 'T168', 'T170', 'T174'], 'fires': False, 'measured': 1.0, 'scope': 'design'},
          "G2_command_block_parseable": {'blocks': ['T155', 'T157', 'T158', 'T168', 'T170', 'T174'], 'fires': False, 'measured': 0.9998, 'scope': 'design'},
          "G3_outcome_label_multilevel": {'blocks': ['T155', 'T170'], 'fires': False, 'measured': 3625.0, 'scope': 'design'},
          "G4_steps_per_trajectory": {'blocks': ['T157', 'T158', 'T168', 'T174'], 'fires': False, 'measured': 0.9993, 'scope': 'design'},
          "G5_rollouts_per_instance": {'blocks': ['T155'], 'fires': False, 'measured': 1787.0, 'scope': 'H1'},
          "G6_repeated_command_trajectories": {'blocks': ['T174'], 'fires': False, 'measured': 27576.0, 'scope': 'H1'},
          "G7_multi_family_trajectories": {'blocks': ['T168'], 'fires': False, 'measured': 118598.0, 'scope': 'H1'},
          "G8_first_family_varies_across_instances": {'blocks': ['T170'], 'fires': False, 'measured': 771.0, 'scope': 'H1'},
          "G9_observation_text_computable": {'blocks': ['T157', 'T158'], 'fires': False, 'measured': 0.9998, 'scope': 'design'},
      },
    "verdict": {
          "blocked_gates": ['G11_failure_marker_present'],
          "blocked_whole_design": [],
          "claim_limited": {'G11_failure_marker_present': 'H2'},
      },
    "note": "a fired gate is a result, not an obstacle: it stops exactly what its frozen sentence scopes",
    "runnable": list(RUNNABLE),
}

# failures of the tooling itself, kept visible rather than edited out.
FAILED_RUNS = [
 "EXP0172 first launch was a 2-file smoke run (results_raw/EXP0172_wave6_premise_census_20260924T152508.json), used "
 "to prove the instruments and measure the per-file cost; it is superseded because the frozen sampling rule is 12 "
 "files, so that draw is not the record any gate fires on.",
]

EXTRA_DEVIATIONS = [
 ("W6-D01", "The outcome label in this release is a termination label, not a correctness label",
            "exit_status takes exactly two values in the frozen sample - Submitted (3,625 trajectories) and "
            "incomplete (116,375) - and neither says whether the patch passed tests. Every dependent variable in "
            "this wave that uses the label therefore means 'the rollout ended by submitting' rather than 'the task "
            "was solved', and the sentence of each affected hypothesis names it. No design in this wave claims a "
            "correctness effect, and no label was recoded to make one available."),
 ("W6-D02", "The first action is near-invariant, which narrows T170 before its data was read",
            "G8 passed (771 instances have rollouts differing in first command family, above the frozen 200), but "
            "the census also measured that 97.99% of rollouts open with a name search. T170's H1 is therefore "
            "estimated on a 2% minority of openings, and the kill-gate sentence says so in advance rather than the "
            "discussion explaining it afterwards."),
 ("W6-D03", "G11 fired on a cell that is large in rows and thin in share",
            "H2 of T158 froze a floor of 0.20 of observations carrying a failure marker; the census measured "
            "0.1855. The floor is not moved and the hypothesis is reported as limited by its own sentence, while "
            "the absolute size of the cell it describes is printed next to the verdict so a reader can see that the "
            "gate fired on a proportion, not on emptiness."),
 ("W6-D04", "The census read every row of the drawn files; the frame draws 20,000 trajectories from them",
  "EXP-0172 measured the premises on all 120,000 trajectories of the 12 drawn files, because a prevalence "
            "gate should not be estimated on a subsample. The frame is a seeded draw of 20,000 of the same rows - the "
            "wave-4 and wave-5 rule, so a cell in this wave means the same size-of-cell thing it means in those "
            "waves - and every design prints the count its own rows carry next to the census number it was gated "
            "against. No floor named in a freeze was re-scaled to the smaller frame. The release was also checked for "
            "the duplicate-record defect EXP-0162 found in hermes: 0 of the 120,000 drawn rollout rows are exact "
            "repeats, so no trajectory is counted twice here."),
 ("W6-D05", "The premise refresher wrote JSON booleans into the frozen module, which made it unimportable",
            "`refresh_wave_premises._lit` rendered values with `json.dumps` except for a top-level bool, so a gate "
            "block carrying `\"fires\": false` was transcribed into `topic_designs_wave6.py` as the name `false`, "
            "and the module no longer imported - which is also how the refresher itself failed to run a second time "
            "to undo it. Structured values now go through `repr`, the frozen block was re-transcribed from the same "
            "census artefact, and the 12 gate measurements, the fired set and the scoped claim are identical to what "
            "the first transcription recorded. No threshold, band, seed, hypothesis or decision sentence changed."),
 ("W6-D06", "The standard control set contains depth, which is T155's own dependent variable",
            "`glm()` now removes the outcome from its own regressor list before fitting. The wave's standard controls "
            "include `log_steps` because every other design needs depth held fixed, and T155's H1 estimates depth, "
            "so the naive term list put the dependent variable in its own design matrix: the fit is not identified, "
            "and in the first wave-6 run it raised inside the degenerate-cell test rather than returning a number. "
            "H1 is therefore the association between stated need length and depth among rollouts of the same task, "
            "with the remaining controls (position, complexity, observation size, previous failure) held; no "
            "coefficient, band or floor was changed to obtain that, and the nested-model degrees of freedom count "
            "the same removal."),
 ("W6-D07", "Three implementation defects found by reading the fits, not the verdicts",
            "First, `single_rollout_instance` was computed with a lambda over a defaultdict and disagreed with the "
            "recomputed count on 16,247 of 19,988 rollouts; it is now a map over the grouped count, and the frame's "
            "self-test asserts the flag and the leave-one-out modal family on three hand-built rollouts. Second, a "
            "control that is constant on the rows a design estimates on made the trajectory-level fits singular - "
            "`prev_failed` is identically 0 at a rollout's first step - so `glm()` now drops zero-variance terms "
            "and names them in the reported row. Third, T158's H1 was fitted on the subset of steps that are not "
            "last, which makes its dependent variable constant; the frozen unit is a step whose observation came "
            "back, with the last step of a rollout contributing the zero that says the search stopped. Its "
            "predictor is that observation's own newness, which is what 'the information the last step returned' "
            "means for the decision to take another step. No threshold, band, seed, hypothesis direction or "
            "decision sentence changed, and the first wave-6 generation is superseded with this reason."),
 ("W6-D08", "T158's outcome is determined by one of the wave's standard controls",
            "A step continues exactly when it is not the rollout's last, which is the statement `step_position < 1`, "
            "so holding position fixed in a model of continuation makes the outcome a function of its own regressor: "
            "the likelihood separates and the first wave-6 attempt returned a coefficient with a NaN interval. The "
            "two continuation hypotheses are estimated against the rest of the control set - depth, need complexity, "
            "observation size, previous failure - and `baselines()` takes the same set so the nested comparison is "
            "built on the terms the hypothesis model uses. `step_position` is still in the wave's control set "
            "everywhere it is not the outcome, and no threshold, band, seed, direction or decision sentence changed."),
 ("W6-D09", "The shared battery step needed the same two guards the design scripts got",
            "`exp_wave1_battery.fit()` kept the manipulated column twice where it is also a control (T155 "
            "manipulates need length, which sits in the wave control set) and kept a control that is constant on the "
            "cell it estimated - `prev_failed`, identically zero at a first step - so T170's E-step reported no "
            "coefficient at all. `terms()` now excludes the outcome, `fit()` drops zero-variance controls and names "
            "what it dropped (T170 reports `dropped_constant_terms: prev_failed`), and every primary in the battery "
            "matches its design: T155 -0.0042, T157 0.0273, T158 0.6314, T168 0.2234, T170 0.0121, T174 -1.3441. "
            "The change is shared, so EXP-0171 (the wave-5 battery) was re-run under it and is numerically identical "
            "to the generation its packages cite; waves 1 to 4 name no control that is also their outcome, and the "
            "estate scan over every live battery artefact found no non-finite statistic."),
]
