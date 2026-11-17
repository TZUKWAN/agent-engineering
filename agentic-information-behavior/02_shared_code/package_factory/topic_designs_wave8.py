"""The wave-8 protocol freeze: what a transcript can be asked about stopping, anchoring and correcting.

Five designs (T171 primacy lock-in, T175 when to stop, T176 premature termination and over-search, T182 plan
specificity, T190 verbal versus behavioural correction) on the hermes reasoning-trace release - the only local corpus
whose rows are *recorded searches*: 14,701 distinct trajectories, 147,253 assistant turns, 174,545 tool observations,
every emitted call answered.

Two boundaries are fixed here before any estimate, because both change what a coefficient can mean:

1. the release carries **no task outcome**. Its columns are `id`, `conversations`, `tools`, `category`,
   `subcategory` and `task`, and there is no success, reward, pass or exit-status field on any row - so every
   "quality" or "failure" quantity in this wave is defined on the trajectory's own observable behaviour, and no design
   claims a task was won or lost;
2. **more than half of the trajectories end mid-exchange**: 6,835 end on an assistant turn, 5,485 end on an
   observation the agent never answers and 2,381 end on a human message. A recorded turn is therefore not evidence of
   a decision to stop for 53.5% of the sample, and that is what EXP-0190's G5 was written to catch.

EXP-0190 measured both, twice, with identical output. Its design-scope gates fired on G5 and G13, so T175 and T176 are
stopped by their own sentences and are recorded as blocked with the values that stopped them; T171, T182 and T190 pass
every floor their sentences freeze and are measured.

    python 02_shared_code/package_factory/freeze_wave.py --designs topic_designs_wave8
"""
from __future__ import annotations

EXP_OF = {"T171": "EXP-0192", "T182": "EXP-0193", "T190": "EXP-0194"}
RUNNABLE = tuple(EXP_OF)
FEATURE_EXP = "EXP-0191"
PREMISE_EXP = "EXP-0190"
BATTERY_EXP = "EXP-0195"
ENCODER_EXP = ""
SEED = 42
BANDS = {"small": 0.05, "medium": 0.15, "large": 0.30}
MATRIX = "results_raw/EXP0191_wave8_turn_matrix_*.json"
PREMISE_GLOB = "results_raw/EXP0190_wave8_premise_census_*.json"
BATTERY = "results_raw/EXP0195_wave8_battery_0195_*.json"
MATRIX_GLOB = MATRIX
BATTERY_GLOB = BATTERY
ENCODER_GLOB = ""
MATRIX_SCRIPT = "exp_wave8_features.py"
BATTERY_SCRIPT = "exp_wave8_battery.py"
PROBE_SCRIPT = "probe_wave8_premises.py"
DESIGNS_MODULE = "topic_designs_wave8"
STAGE_RX = "wave8_main"
CLEAN_ROOM_ONLY_FLAG = "--only"
CLEAN_ROOM_MODE = "full"
SCRIPT_OF = {t: "exp_wave8_designs.py" for t in RUNNABLE}
MAIN_SCRIPT_OF = {t: "exp_wave8_designs.py" for t in RUNNABLE}
SUBSTRATE_LABEL = ("hermes-agent-reasoning-traces, the whole release after the duplicate-trajectory drop "
                   "(EXP-0162 measured 7,646 trajectories stored twice): 14,701 trajectories, 147,253 assistant "
                   "turns, 174,545 tool observations across 8 task categories - recorded searches with the agent's "
                   "own thinking, its emitted tool calls and the responses it received; the release carries no task "
                   "outcome of any kind")
SAMPLE_FIELDS = ("corpus", "trajectories", "assistant_turns_total", "observations_total",
                 "median_turns_per_trajectory", "trajectories_ending_on_an_assistant_turn_share",
                 "observations_with_a_failure_marker_share", "outcome_field_present", "cluster_unit")
CONTRIBUTION_POPULATION = ("a corpus of recorded agent trajectories - assistant turns with their thinking, their tool "
                           "calls and the observations returned - read with rule and lexical instruments, with no "
                           "model, no judge and no task-outcome label")

COMMON = {
    "seed": SEED,
    "bands": BANDS,
    "module": "topic_designs_wave8",
    "sample": {"traj_cap": 14701, "cluster_unit": "traj_id",
              "unit_of_analysis": "the assistant turn, nested in the trajectory whose decisions it is part of",
              "rule": "every trajectory of the release, deduplicated by traj_id before sampling and never subsampled "
                      "afterwards, so the trajectory clusters are the ones the release has rather than a draw from "
                      "them; there is no dev/test split in this corpus and nothing outside these rows is read",
              "excluded": "the 7,646 duplicate trajectory rows the release stores twice over, dropped by "
                          "exp_wave4_features.load_trajectories before any counting"},
    "instruments": ("a hypothesis is a turn carrying one of wave 5's two independently worded hypothesis lexicons; a "
                    "plan marker is one of wave 5's two plan lexicons; specificity counts distinct file paths, quoted "
                    "or backticked spans, camel-case identifiers, action verbs, ordering markers and constraint "
                    "phrases in a turn; an observation carries a failure marker on wave 4's frozen list, unchanged "
                    "from waves 6 and 7; a verbal correction is one of the 24 phrases frozen in EXP-0190, which are "
                    "the agent's admissions about its own prior act and deliberately not the error vocabulary of an "
                    "observation; a call is a repeat of another when its name and its canonical arguments are equal"),
}

DESIGNS = {
 # ------------------------------------------------------------------ T171
 "T171": {
  "pkg": "P045_primacy_lock_in_and_later_search",
  "title": "Primacy Lock-In: Does an Initial Hypothesis Narrow Later Search?",
  "rq": "When an agent states a hypothesis early, does its later language keep returning to that hypothesis's own "
        "vocabulary more than the task instruction alone would explain, and does the information it receives become "
        "correspondingly less new?",
  "hypotheses": [
   "H1 within a trajectory that states a hypothesis in its first two turns, the share of a later turn's content words "
   "already present in that hypothesis statement rises with the turn's position in the trajectory, holding "
   "trajectory length and instruction length fixed.",
   "H2 the later turns of such a trajectory receive less new information - a smaller share of words in the following "
   "observation that the trajectory had not seen - than the later turns of trajectories that stated no early "
   "hypothesis, with length and category held fixed.",
   "H3 the concentration is on the hypothesis rather than on early text in general: with the overlap against a "
   "seed-chosen hypothesis statement from another trajectory of the same category in the model, the trajectory's own "
   "anchor still separates and the alien anchor does not."],
  "features": {
   "hypo_anchor_overlap": "share of the turn's content words that appear in the trajectory's own first hypothesis "
                          "statement",
   "alien_anchor_overlap": "the same share against a hypothesis statement drawn by a seeded, digest-keyed choice from "
                           "another trajectory of the same category and comparable length",
   "obs_new_word_share": "share of the following observation's content words not present anywhere earlier in the "
                         "trajectory",
   "position": "turn index divided by the trajectory's turn count"},
  "dvs": {"hypo_anchor_overlap": "H1's and H3's outcome", "obs_new_word_share": "H2's outcome"},
  "models": [
   "OLS on the anchor-overlap z-score with position, log turn count and log instruction length, clustered on traj_id",
   "OLS on the new-word share with an early-hypothesis indicator plus the same controls, clustered on traj_id",
   "the same overlap model carrying both the own-anchor and the alien-anchor terms, so each is estimated with the "
   "other held"],
  "thresholds": {"support": "|beta| >= 0.15 with CI excluding 0 and p_holm < 0.05",
                 "partial": "CI excludes 0 below the floor", "null": "CI includes 0"},
  "family": "three",
  "gate_scope": "design",
  "kill_gate": ("G1, G2, G4 and G11 froze that the trajectories are readable, carry an instruction, run long enough "
                "to have a later half, and are numerous enough to cluster. EXP-0190 measured 1.0, 1.0, 13,695 and "
                "14,701, and G3's own floor of 200 early-hypothesis trajectories was met at 570, so the design "
                "stands; H1's arm is that 570-trajectory cell and its size is printed with every estimate."),
  "strata": ["trajectory-length quartile", "task category"],
  "tables": ["table1_sample_and_structure.csv", "table2_anchor_census.csv", "table3_main_models.csv",
             "table4_strata_by_length.csv", "table5_robustness_inference.csv", "table6_baseline_comparison.csv",
             "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_anchor_examples.pdf", "fig2_main_effect.pdf", "fig3_mechanism_by_band.pdf",
              "fig4_robustness.pdf"],
 },
 # ------------------------------------------------------------------ T175
 "T175": {
  "pkg": "P048_when_to_stop_a_recorded_search",
  "title": "When Should Agentic Search Stop?",
  "rq": "Given a turn, do marginal information, evidence consistency, uncertainty, repetition and length predict "
        "whether the recorded search ends there?",
  "hypotheses": [
   "H1 a turn whose preceding observation returned little new information is more likely to be the trajectory's last "
   "assistant turn, holding position and length fixed.",
   "H2 repetition and uncertainty rise at the end: a final turn is more likely to repeat an earlier call and to carry "
   "an uncertainty marker than a matched interior turn.",
   "H3 sufficiency language marks the stop: a turn stating that it has enough is more likely to end the trajectory "
   "than a turn that does not, with the same controls."],
  "features": {"stops_here": "1 if this is the trajectory's last assistant turn and the trajectory ends on an "
                             "assistant turn", "marginal_information": "new-word share of the preceding observation",
               "repeated_call": "this call equals an earlier call of the same trajectory", "uncertainty_markers":
               "count of the frozen uncertainty list in the turn", "sufficiency": "count of wave 4's sufficiency "
               "markers in the turn"},
  "dvs": {"stops_here": "H1 to H3's outcome, a binomial event"},
  "models": ["logistic on stops_here with marginal information plus position, log turn count, category and the "
             "standard controls, clustered on traj_id", "the same model with repetition and uncertainty in place of "
             "marginal information", "the same model with the sufficiency count in place of repetition"],
  "thresholds": {"support": "|beta| >= 0.15 with CI excluding 0 and p_holm < 0.05",
                 "partial": "CI excludes 0 below the floor", "null": "CI includes 0"},
  "family": "three",
  "gate_scope": "design",
  "kill_gate": ("G5 froze '>= 0.95 of trajectories end on an assistant turn, so STOP is a measurable event rather "
                "than a guess about a truncated log'. EXP-0190 measured 0.4649 - 6,835 trajectories end on an "
                "assistant turn, 5,485 on an observation the agent never answers and 2,381 on a human message - so "
                "the event this design's sentence defines does not exist for over half the release, and the design is "
                "stopped by its own gate. The threshold is not moved and no estimate is offered on the surviving "
                "half, because the frozen outcome is the trajectory's end, not a subsample's."),
  "strata": ["task category", "trajectory-length quartile"],
  "tables": ["table1_sample_and_structure.csv", "table2_stop_census.csv", "table3_main_models.csv",
             "table4_strata_by_length.csv", "table5_robustness_inference.csv", "table6_baseline_comparison.csv",
             "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_stop_examples.pdf", "fig2_main_effect.pdf",
              "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"],
 },
 # ------------------------------------------------------------------ T176
 "T176": {
  "pkg": "P049_premature_termination_and_over_search",
  "title": "Premature Termination and Over-Search as a Double Mismatch",
  "rq": "Are the antecedents of stopping too early and of searching too long the same linguistic and behavioural "
        "state, or two different ones?",
  "hypotheses": [
   "H1 a search that ends within one turn of an error-marked observation is preceded by more uncertainty language "
   "than a search of the same length that continues past the same kind of error.",
   "H2 a search that repeats an already-issued call after its tenth turn is preceded by more sufficiency language "
   "and less new information than a search that does not.",
   "H3 the two arms are distinguishable from each other, not one tail: a model of the premature arm's antecedents "
   "does not carry the over-search arm and vice versa."],
  "features": {"premature": "trajectory ends on an assistant turn within one turn of an error-marked observation",
               "over_search": "trajectory re-issues an identical call at or after its tenth assistant turn",
               "uncertainty_markers": "count in the turn", "sufficiency": "count in the turn",
               "marginal_information": "new-word share of the preceding observation"},
  "dvs": {"premature": "H1's outcome", "over_search": "H2's outcome"},
  "models": ["logistic on the premature arm with uncertainty plus length and category controls, clustered on traj_id",
             "logistic on the over-search arm with sufficiency and marginal information plus the same controls",
             "each arm's antecedents entered into the other arm's model, so one cannot be borrowed as the other's"],
  "thresholds": {"support": "|beta| >= 0.15 with CI excluding 0 and p_holm < 0.05",
                 "partial": "CI excludes 0 below the floor", "null": "CI includes 0"},
  "family": "three",
  "gate_scope": "design",
  "kill_gate": ("Two gates scope this design and both fired as measured. G13 froze that the release carries a "
                "task-outcome column a mismatch could be scored against; the release ships id, conversations, tools, "
                "category, subcategory and task only, so 'premature' and 'over' have no reference - a search cannot "
                "be too short or too long for a task whose completion was never recorded. G5 separately measured that "
                "53.5% of trajectories end mid-exchange, which is the population both arms define themselves against. "
                "The design is stopped by its own sentences; the behavioural definitions were not rescued by "
                "retargeting them onto whatever subset survived."),
  "strata": ["task category", "trajectory-length quartile"],
  "tables": ["table1_sample_and_structure.csv", "table2_failure_mode_census.csv", "table3_main_models.csv",
             "table4_strata_by_length.csv", "table5_robustness_inference.csv", "table6_baseline_comparison.csv",
             "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_failure_modes.pdf", "fig2_main_effect.pdf",
              "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"],
 },
 # ------------------------------------------------------------------ T182
 "T182": {
  "pkg": "P046_plan_specificity_and_search_quality",
  "title": "Does Plan Specificity Improve Search Quality?",
  "rq": "When the opening turn names more entities, actions, order and constraints, does the rest of the recorded "
        "search behave more productively - fewer repeated calls, fewer error-marked observations, a cleaner final "
        "observation?",
  "hypotheses": [
   "H1 a more specific opening plan is associated with a lower share of the trajectory's calls repeating an "
   "identical earlier call, holding task category and instruction length fixed.",
   "H2 a more specific opening plan is associated with a lower share of error-marked observations in the trajectory.",
   "H3 specificity is not verbosity: with the opening turn's character count in the model the specificity terms "
   "still add, and with specificity in the model length adds nothing."],
  "features": {"plan_specificity": "the z-scored sum of distinct entities, action verbs, ordering markers and "
                                   "constraint phrases counted in the first assistant turn",
               "specificity_parts": "the same four counts as separate terms, so the composite cannot hide which part "
                                    "of it carries the association",
               "repeat_share": "share of the trajectory's calls that duplicate an earlier call of the same trajectory",
               "error_share": "share of the trajectory's observations carrying a failure marker",
               "final_obs_clean": "1 if the trajectory's last observation carries no failure marker"},
  "dvs": {"repeat_share": "H1's outcome", "error_share": "H2's outcome",
          "final_obs_clean": "H3's secondary reading, reported beside the two rates"},
  "models": ["OLS on the repeated-call share with plan specificity plus category and length controls, clustered on "
             "traj_id", "OLS on the error share with the same specification",
             "the four specificity parts entered together with the opening turn's length, so each part is estimated "
             "against the others and against verbosity"],
  "thresholds": {"support": "|beta| >= 0.15 with CI excluding 0 and p_holm < 0.05",
                 "partial": "CI excludes 0 below the floor", "null": "CI includes 0"},
  "family": "three",
  "gate_scope": "design",
  "kill_gate": ("G9 froze >= 200 trajectories whose first turn carries at least two ordering markers and two action "
                "verbs, the floor below which 'a plan whose specificity can be counted' would describe too thin a cell "
                "to compare. EXP-0190 measured 6,975, and G2's instruction floor was met at 1.0, so the design "
                "stands. What the gate cannot give this design is a task outcome: G13 measured that the release "
                "carries none, so 'quality' here means the observable productivity quantities named in the features, "
                "and no sentence below or in the package claims a task was completed (deviation W8-D01)."),
  "strata": ["task category", "instruction-length quartile"],
  "tables": ["table1_sample_and_structure.csv", "table2_specificity_census.csv", "table3_main_models.csv",
             "table4_strata_by_category.csv", "table5_robustness_inference.csv", "table6_baseline_comparison.csv",
             "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_specificity_examples.pdf", "fig2_main_effect.pdf",
              "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"],
 },
 # ------------------------------------------------------------------ T190
 "T190": {
  "pkg": "P047_verbal_versus_behavioural_correction",
  "title": "Verbal Correction versus Behavioural Correction",
  "rq": "When an agent says it was wrong, does the next thing it actually do differ from what it was doing - and how "
        "often does an admission stand alone?",
  "hypotheses": [
   "H1 after an error-marked observation, a turn that states a verbal correction is more likely to be followed by a "
   "call that differs in name or arguments from the previous call than a turn that states none, holding position, "
   "length and category fixed.",
   "H2 a substantial share of verbal corrections are not followed by any behavioural change: the measured rate, with "
   "a cluster bootstrap interval on the trajectory, is at or above the frozen 0.20 floor this sentence names.",
   "H3 the admission instrument is not the error instrument: agreement between a turn carrying a verbal correction "
   "and the observation before it carrying a failure marker is low, so one cannot be read as the other."],
  "features": {"verbal_correction": "1 if the turn carries at least one of the 24 frozen correction phrases",
               "call_changed": "1 if the turn's first call differs in name or arguments from the trajectory's "
                               "previous call",
               "prior_error": "1 if the most recent preceding observation carries a failure marker",
               "ritual": "1 if verbal_correction and not call_changed"},
  "dvs": {"call_changed": "H1's outcome", "ritual_rate": "H2's outcome, a rate with a bootstrap interval"},
  "models": ["logistic on call changed with the verbal-correction indicator, prior error, position, log turn count "
             "and category, clustered on traj_id",
             "the measured ritual share among corrections with a cluster bootstrap on traj_id, read against the "
             "frozen floor",
             "Cohen's kappa between the correction marker and the preceding error marker, with a cluster bootstrap"],
  "thresholds": {"support": "|beta| >= 0.15 with CI excluding 0 and p_holm < 0.05",
                 "partial": "CI excludes 0 below the floor", "null": "CI includes 0",
                 "h2": "the floor is on the measured rate (>= 0.20 of corrections with no behavioural change), not on "
                       "a coefficient",
                 "h3": "kappa < 0.50 on these rows means the two instruments are separable, which is what H3 claims"},
  "family": "three",
  "gate_scope": "design",
  "kill_gate": ("G8 froze >= 200 trajectories containing an explicit self-correction, because a construct that "
                "appears in a handful of transcripts cannot carry a prevalence claim; EXP-0190 measured 825, which is "
                "5.6% of the release - enough to measure, still a minority, and the design's own sentences say so. "
                "G6's 1.0 (every emitted call is answered) and G10's 4,125 trajectories with a repeated identical "
                "call are what make 'the next thing it does' a computable quantity."),
  "strata": ["task category", "position in the trajectory"],
  "tables": ["table1_sample_and_structure.csv", "table2_correction_census.csv", "table3_main_models.csv",
             "table4_strata_by_category.csv", "table5_robustness_inference.csv", "table6_baseline_comparison.csv",
             "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_correction_examples.pdf", "fig2_main_effect.pdf",
              "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"],
 },
}

# census key (a dotted path into its `measured` block) -> the name this freeze gives it, so EXP-0163 can rewrite the
# PREMISES literal below from the artefact rather than from a hand-kept copy.
PREMISE_MAP = {
 "trajectories": "trajectories_read", "trajectories_parsed": "trajectories_parsed",
 "assistant_turns_total": "assistant_turns", "observations_total": "observations",
 "median_turns_per_trajectory": "median_turns_per_trajectory",
 "task_instruction_share": "task_instruction_share",
 "trajectories_stating_a_hypothesis_in_the_first_two_turns": "early_hypothesis_trajectories",
 "trajectories_with_4plus_turns": "trajectories_with_4plus_turns",
 "trajectories_ending_on_an_assistant_turn_share": "terminal_turn_share",
 "trajectories_answering_every_call_share": "every_call_answered_share",
 "observations_with_a_failure_marker_share": "failure_marker_share_of_observations",
 "trajectories_with_an_explicit_self_correction": "self_correcting_trajectories",
 "trajectories_with_a_countable_first_turn_plan": "countable_plan_trajectories",
 "trajectories_with_a_repeated_identical_call": "repeated_call_trajectories",
 "categories_with_100plus_trajectories": "categories_100plus",
 "median_entities_in_the_first_turn": "median_first_turn_entities",
 "median_action_verbs_in_the_first_turn": "median_first_turn_verbs",
 "calls_unparsed_share": "unparsed_call_share", "outcome_field_present": "task_outcome_field_present",
}

PREMISES = {
    "census": "EXP-0190 (EXP0190_wave8_premise_census_20260924T190909.json)",
    "transcribed_by": "02_shared_code/registry/refresh_wave_premises.py (EXP-0163); no number in this block is typed by hand",
    "measured": {
        "trajectories_read": 14701,
        "trajectories_parsed": 14701,
        "assistant_turns": 147253,
        "observations": 174545,
        "median_turns_per_trajectory": 9.0,
        "task_instruction_share": 1.0,
        "early_hypothesis_trajectories": 570,
        "trajectories_with_4plus_turns": 13695,
        "terminal_turn_share": 0.4649,
        "every_call_answered_share": 1.0,
        "failure_marker_share_of_observations": 0.5893,
        "self_correcting_trajectories": 825,
        "countable_plan_trajectories": 6975,
        "repeated_call_trajectories": 4125,
        "categories_100plus": 8,
        "median_first_turn_entities": 10.0,
        "median_first_turn_verbs": 2.0,
        "unparsed_call_share": 0.0,
        "task_outcome_field_present": False,
    },
    "gates": {
          "G10_repeated_call_trajectories": {'blocks': ['T176', 'T190'], 'fires': False, 'measured': 4125, 'rule': '>= 200 trajectories re-issue an identical (name, arguments) call - the observable over-search arm T176 and the behavioural-change baseline T190 both need', 'scope': 'H1', 'threshold': 200},
          "G11_cluster_count": {'blocks': ['T171', 'T175', 'T176', 'T182', 'T190'], 'fires': False, 'measured': 14701, 'rule': '>= 1,000 trajectories readable at all, so a traj_id-clustered interval exists for every design', 'scope': 'design', 'threshold': 1000},
          "G12_category_breadth": {'blocks': ['T175', 'T176'], 'fires': False, 'measured': 8, 'rule': '>= 5 task categories with >= 100 trajectories each, which is the stratum T175 and T176 report inside', 'scope': 'strata', 'threshold': 5},
          "G13_outcome_label_available": {'blocks': ['T176'], 'fires': True, 'measured': 0, 'rule': "the release carries a per-trajectory task outcome (success, reward, pass, exit status) that a premature-versus-over-search mismatch could be scored against. This gate is reported as measured either way, because the sentence it scopes - T176's - can be narrowed to behaviour without moving any threshold, and a fired gate here is a statement about what the release does not record", 'scope': 'design', 'threshold': 1},
          "G1_trajectories_parseable": {'blocks': ['T171', 'T175', 'T176', 'T182', 'T190'], 'fires': False, 'measured': 1.0, 'rule': '>= 0.95 of drawn trajectories yield at least one readable assistant turn', 'scope': 'design', 'threshold': 0.95},
          "G2_task_instruction_present": {'blocks': ['T171', 'T182'], 'fires': False, 'measured': 1.0, 'rule': ">= 0.90 of trajectories carry a non-empty task instruction, which is what 'later search' is later than and what an entity count counts against", 'scope': 'design', 'threshold': 0.9},
          "G3_early_hypothesis_trajectories": {'blocks': ['T171'], 'fires': False, 'measured': 570, 'rule': '>= 200 trajectories state a hypothesis within their first two assistant turns - the arm T171 compares against', 'scope': 'H1', 'threshold': 200},
          "G4_trajectories_with_later_turns": {'blocks': ['T171', 'T175', 'T182'], 'fires': False, 'measured': 13695, 'rule': '>= 500 trajectories have >= 4 assistant turns, so a turn-by-turn concentration profile has a later half', 'scope': 'design', 'threshold': 500},
          "G5_terminal_turn_identifiable": {'blocks': ['T175', 'T176'], 'fires': True, 'measured': 0.4649, 'rule': '>= 0.95 of trajectories end on an assistant turn, so STOP is a measurable event rather than a guess about a truncated log', 'scope': 'design', 'threshold': 0.95},
          "G6_observations_parseable": {'blocks': ['T175', 'T176', 'T190'], 'fires': False, 'measured': 1.0, 'rule': '>= 0.80 of trajectories return at least one observation for every call they emitted - marginal information is computed from that content', 'scope': 'design', 'threshold': 0.8},
          "G7_error_marked_observations": {'blocks': ['T176'], 'fires': False, 'measured': 0.5893, 'rule': ">= 0.05 of observations carry a failure marker, the conditioning event T176's premature arm and T190's correction arm both stand on", 'scope': 'H1', 'threshold': 0.05},
          "G8_verbal_corrections": {'blocks': ['T190'], 'fires': False, 'measured': 825, 'rule': '>= 200 trajectories contain at least one explicit self-correction from the frozen list; below this the construct T190 names is rare in this corpus rather than uninformative', 'scope': 'design', 'threshold': 200},
          "G9_plan_specificity_computable": {'blocks': ['T182'], 'fires': False, 'measured': 6975, 'rule': ">= 200 trajectories have a first assistant turn carrying at least two ordering markers and at least two action verbs, the low end of 'a plan whose specificity can be counted'", 'scope': 'H1', 'threshold': 200},
      },
    "verdict": {
          "blocked_gates": ['G5_terminal_turn_identifiable', 'G13_outcome_label_available'],
          "blocked_whole_design": ['T175', 'T176'],
          "claim_limited": {},
      },
    "note": "a fired gate is a result, not an obstacle: it stops exactly what its frozen sentence scopes",
    "runnable": list(RUNNABLE),
}    # the blocks above are filled verbatim from the census artefact - never edit them by hand

FAILED_RUNS = [
 "EXP0190 first launch was a 400-trajectory smoke run "
 "(results_raw/EXP0190_wave8_premise_census_20260924T190715.json), used to prove the call parser, the anchor "
 "instruments and the gate wiring; G3, G4, G9, G10 and G12 fired there only because 400 trajectories is a small draw, "
 "so that generation is superseded and the gate verdicts cited are the whole-release ones.",
]

EXTRA_DEVIATIONS = [
 ("W8-D01", "This release records no task outcome, so 'quality' and 'failure' are defined on behaviour alone",
            "hermes ships id, conversations, tools, category, subcategory and task - EXP-0190 searched every column "
            "for a success, reward, pass, exit-status or score field and found none (G13 measured 0). Every "
            "productive-versus-unproductive quantity in this wave is therefore an observable of the trajectory: "
            "whether a call duplicates an earlier one, whether the observation before a turn carries a failure "
            "marker, whether the last observation is error-free. T176's title asks about a mismatch against the task, "
            "which is precisely the quantity that cannot be computed here, and that is one of the two reasons its own "
            "gate stopped it rather than a proxy being substituted."),
 ("W8-D02", "53.5% of recorded trajectories end mid-exchange, and that stopped two designs",
            "G5 froze a 0.95 floor for 'the trajectory ends on an assistant turn' before any row was opened, because "
            "a stop is only a stop if the agent chose it. The release measured 0.4649: 6,835 of 14,701 trajectories "
            "end on an assistant turn, 5,485 end on an observation nobody answers and 2,381 end on a human message. "
            "T175 and T176 define their outcomes on that event, so both are recorded as blocked at their own premise "
            "gate with these values cited, and no model was run on the surviving half under the other half's "
            "sentence."),
 ("W8-D03", "The hypothesis anchor is rare in the first two turns, so T171's cell is named wherever it is used",
            "G3's floor is 200 trajectories and the release measured 570 - 3.9% of them. The design stands on its "
            "frozen floor, but every H1 and H3 estimate is inside that 570-trajectory cell and every H2 contrast is "
            "between it and the rest, so the counts are printed beside the coefficients rather than only in the "
            "provenance table. The cell that H1 actually fits is smaller again - 3,764 turns in 515 of those "
            "trajectories - because a trajectory contributes only turns after its second, and 55 of the 570 end "
            "before then; that count is carried in the H1 row itself."),
 ("W8-D04", "The trajectory summary re-supplied a turn column, and the merge would have renamed it",
            "The frame joins the per-turn rows to the per-trajectory summary on traj_id with a many-to-one guard on "
            "the row count, but `category` was carried by both, so pandas would have produced `category_x` and "
            "`category_y` and left no `category` at all - which the designs' column check caught the moment they read "
            "the frame, before any estimate existed. The summary now supplies only the columns the turn rows do not "
            "have, and the build refuses outright if a joined column shadows one already present."),
 ("W8-D05", "The imported estimators carried wave 7's cluster column as their default",
            "Wave 8 reuses wave 7's fit, term, Holm, baseline and stratum helpers rather than restating them, and "
            "those helpers default to the column wave 7 clusters on. The first wave-8 run therefore died inside a "
            "fit with `query_id is not in index`. The helpers are now wrapped so that every wave-8 interval is "
            "cluster-robust on traj_id unless a call says otherwise; no arithmetic changed, only the default."),
]
