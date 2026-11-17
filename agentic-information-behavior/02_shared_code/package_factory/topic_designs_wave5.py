"""Wave 5's frozen designs: what an agent *says* about evidence versus what it retrieved.

Six topics, one substrate (hermes-agent-reasoning-traces, the same 20,000-trajectory cap and the same seeded
trajectory sample as wave 4, now deduplicated per EXP-0162), one shared step frame (EXP-0164). Every construct here
is a relation between two things already in the release: the prose of an assistant turn, and the tool calls and
observations around it. Nothing is judged by a model, and no dependent variable is computed by reading text for
meaning - the markers are lexical, the evidence comparison is set overlap over content words, the outcomes are the
agent's own next action.

Prevalences and cell sizes below come from EXP-0161, the wave's premise census, which was run and is cited *before*
any of these hypotheses can be evaluated; a gate that had fired is recorded as limiting exactly the hypothesis its
sentence scopes. Two did: a conclusion marker appears in 0.75% of turns (floor 2%) and only 114 trajectories conclude
before their first inspection (floor 200), so **T132's H1 is not testable on this release as frozen**, and that is
its result, not an obstacle to route around.

    python 02_shared_code/package_factory/exp_wave5_designs.py            # the six designs, EXP-0165..EXP-0170
"""
from __future__ import annotations

SEED = 42
BANDS = {"small": 0.05, "medium": 0.15, "large": 0.30}

SAMPLE = {"traj_cap": 20000, "cluster_unit": "traj_id",
          "rule": "one seeded draw of trajectory ids over the whole release, duplicates dropped before sampling "
                  "(EXP-0162), reused by every step of the wave; no re-draw per hypothesis",
          "unit_of_analysis": "the assistant turn, clustered within its trajectory",
          "excluded": "rows of P001's test split - this release has none, and no routing row is read here"}

DESIGNS = {
 # ------------------------------------------------------------------ T130: is there a grammar, and is it the tagger's?
 "T130": {
  "pkg": "P027_discourse_grammar_of_seeking",
  "title": "A Discourse Grammar of Agentic Information Seeking",
  "rq": "Do the five speech acts of information seeking - hypothesising, questioning, planning, requesting "
        "evidence, concluding - fall on an assistant turn with a stable, position-dependent structure, and does "
        "that structure survive an independently worded second tagger?",
  "hypotheses": [
   "H1 the plan act is more frequent in the first third of a trajectory than in the last third, with the difference "
   "in the predicted direction and at least the medium band on the logit scale",
   "H2 the conclusion act is more frequent in the last third than in the first third, same rule",
   "H3 the instrument is not the finding: the A and B taggers reach Cohen kappa >= 0.60 per act over the same turns; "
   "below the bar the grammar is reported as tagger-dependent for that act and no H1/H2 claim rests on it"],
  "features": {
   "act_hypothesis / act_question / act_plan / act_evidence_request / act_conclusion":
       "1 if any marker of that act's lexicon occurs in the turn (reasoning block and body together); the five "
       "lexicons are listed in exp_wave5_features and were written before any row was opened",
   "act_*_b": "the same five acts under a second, independently worded lexicon, for H3 only",
   "position_third": "first / middle / last third of the trajectory by turn index"},
  "dvs": {"act_plan": "H1's outcome", "act_conclusion": "H2's outcome",
          "cohen_kappa_by_act": "H3's statistic, computed on the trajectory clusters with a bootstrap interval"},
  "models": [
   "logistic on act_plan with a last-third indicator plus log turn index, log body length, prior inspections, "
   "prior non-inspections and prev_obs_error, cluster-robust SEs on traj_id",
   "the same specification for act_conclusion",
   "per-act Cohen kappa between the A and B taggers, bootstrapped over trajectories"],
  "thresholds": {
   "support": "|beta| >= 0.15 with CI excluding 0 and p_holm < 0.05",
   "partial": "CI excludes 0 below the floor",
   "null": "CI includes 0",
   "h3": "supported at kappa >= 0.60 for the act; otherwise tagger_dependent_for_that_act, reported as such"},
  "family": 3, "gate_scope": "H3",
  "kill_gate": "G2 >= 0.05 of turns carry at least one act marker under the A tagger and G3 >= 0.02 under the B "
               "tagger, else there is no grammar to describe and no second instrument to check it with. Measured "
               "0.6694 and 0.2677, so both cleared before any outcome existed.",
  "strata": "by act, by trajectory position third, and by task category",
  "tables": ["table1_sample_and_structure.csv", "table2_act_prevalence.csv", "table3_main_models.csv",
             "table4_strata_by_position_and_category.csv", "table5_robustness_inference.csv",
             "table6_baseline_comparison.csv", "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_modality_examples.pdf", "fig2_main_effect.pdf",
              "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"]},

 # ------------------------------------------------------------------ T132: concluding before checking
 "T132": {
  "pkg": "P028_conclusion_before_evidence",
  "title": "Conclusion Before Evidence: Order Effects in Agentic Reasoning",
  "rq": "When an agent states a conclusion, has it inspected anything yet, and does the relation between the "
        "conclusion and the evidence already in hand depend on that order?",
  "hypotheses": [
   "H1 a conclusion that precedes the trajectory's first inspection-family call is a distinct phenomenon from one "
   "that follows it: the two cells are compared, and the frozen floor is >= 200 trajectories in the earlier cell. "
   "EXP-0161 measured 114, so this hypothesis is reported as not_testable_premise_floor_with_114_trajectories",
   "H2 among turns carrying a conclusion marker, the lexical overlap with the observations already returned is "
   "higher for conclusions that follow an inspection than for those that precede one",
   "H3 a conclusion act raises the probability that the trajectory stops at that turn, beyond what the prior "
   "inspection and non-inspection counts predict"],
  "features": {
   "act_conclusion": "1 if any conclusion marker occurs in the turn",
   "concl_after_inspect": "1 if the trajectory had already produced an inspection-family call when the turn was "
                          "written, else 0",
   "evidence_overlap": "|content words of the turn INTERSECT content words of every observation returned so far| / "
                       "|content words of the turn|, computed on the turn's own body"},
  "dvs": {"evidence_overlap": "H2's outcome, standardised for the band test",
          "stops_here": "H3's outcome: no further call in the trajectory"},
  "models": [
   "cell counts and per-cell rates for H1, with the frozen floor stated next to the measured value",
   "OLS on standardised evidence_overlap with the order indicator plus the standard controls, clustered on traj_id",
   "logistic on stops_here with act_conclusion plus the standard controls, clustered on traj_id"],
  "thresholds": {
   "support": "|beta| >= 0.15 with CI excluding 0 and p_holm < 0.05",
   "partial": "CI excludes 0 below the floor",
   "null": "CI includes 0",
   "h1": "testable only with >= 200 trajectories in the earlier cell; below that the cell is described, not tested"},
  "family": 3, "gate_scope": "H1",
  "kill_gate": "G4 >= 0.02 of turns carry a conclusion marker and G5 >= 200 trajectories conclude before their first "
               "inspection. Measured 0.0075 and 114: both fired, so H1 stops at its own sentence while H2 and H3 "
               "stand on cells that cleared (3,694 and 1,845 respectively).",
  "strata": "by trajectory position third, by task category, and by whether the prior observation carried a failure",
  "tables": ["table1_sample_and_structure.csv", "table2_conclusion_order_census.csv", "table3_main_models.csv",
             "table4_strata_by_position_and_category.csv", "table5_robustness_inference.csv",
             "table6_baseline_comparison.csv", "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_modality_examples.pdf", "fig2_main_effect.pdf",
              "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"]},

 # ------------------------------------------------------------------ T133: what the prose does after a failure
 "T133": {
  "pkg": "P029_discourse_repair_after_failure",
  "title": "Discourse Repair after Failed Information Seeking",
  "rq": "Immediately after an observation that says the retrieval or the command did not work, what does the agent's "
        "next turn do in language, and does that language go with trying again or with giving up?",
  "hypotheses": [
   "H1 diagnostic language is more frequent on the turn after a failure-marked observation than on other turns",
   "H2 among failure-preceded turns, re-issue language is followed by another call more often than re-issue-free "
   "turns are",
   "H3 among failure-preceded turns, abandon language predicts stopping the trajectory there"],
  "features": {
   "prev_obs_error": "1 if the immediately preceding observation carries a failure marker (the wave-4 lexicon, "
                     "unchanged: error/failed/not found/traceback/permission denied/...)",
   "repair_diagnose / repair_reissue / repair_abandon": "1 if any marker of that repair family occurs in the turn; "
                                                        "the acknowledge family is the conditioning event, not a "
                                                        "predictor, so it is reported as a prevalence only"},
  "dvs": {"next_is_call": "H2's outcome", "stops_here": "H3's outcome",
          "repair_diagnose": "H1's outcome"},
  "models": [
   "logistic on repair_diagnose with prev_obs_error plus the standard controls, clustered on traj_id",
   "logistic on next_is_call with repair_reissue plus the standard controls, restricted to failure-preceded turns",
   "logistic on stops_here with repair_abandon plus the standard controls, restricted to failure-preceded turns"],
  "thresholds": {
   "support": "|beta| >= 0.15 with CI excluding 0 and p_holm < 0.05",
   "partial": "CI excludes 0 below the floor",
   "null": "CI includes 0"},
  "family": 3, "gate_scope": "H1",
  "kill_gate": "G6 >= 200 turns immediately preceded by a failure-marked observation. Measured 22,209, so the "
               "design's subject exists before any estimate.",
  "strata": "by repair family, by task category, and by the tool family of the failing observation",
  "tables": ["table1_sample_and_structure.csv", "table2_repair_prevalence.csv", "table3_main_models.csv",
             "table4_strata_by_category_and_tool_family.csv", "table5_robustness_inference.csv",
             "table6_baseline_comparison.csv", "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_modality_examples.pdf", "fig2_main_effect.pdf",
              "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"]},

 # ------------------------------------------------------------------ T134: do connectives track evidence?
 "T134": {
  "pkg": "P030_causal_connectives_and_evidence",
  "title": "Do Causal Connectives Reflect the Actual Evidence-Conclusion Relation?",
  "rq": "When an agent writes 'because' or 'therefore', is the content it connects actually present in the "
        "observations it has been given?",
  "hypotheses": [
   "H1 turns carrying a causal connective overlap lexically with the observations already returned more than turns "
   "without one, at least the medium band on the standardised overlap",
   "H2 the inferential family (therefore/thus/hence/so that/as a result) overlaps less with prior evidence than the "
   "explanatory family (because/since/given that/due to), which is the direction a connective used to bridge a gap "
   "would predict",
   "H3 the association is specific to connectives: a same-size control lexicon of function words that carry no "
   "inferential meaning shows no comparable association"],
  "features": {
   "has_causal": "1 if any CAUSAL marker occurs in the turn",
   "causal_inferential / causal_explanatory": "counts of markers in each family, standardised",
   "causal_control_z": "standardised count of a 12-item control lexicon of high-frequency function words with no "
                       "inferential content ('the', 'with', 'into', ...), chosen before the census ran",
   "evidence_overlap": "as in T132, computed on the turn's own body against every observation returned so far"},
  "dvs": {"evidence_overlap": "the outcome for H1-H3, standardised"},
  "models": [
   "OLS on standardised evidence_overlap with has_causal plus the standard controls, clustered on traj_id",
   "the same model with the two connective families entered separately, the contrast being H2",
   "the same model with the control lexicon substituted for has_causal"],
  "thresholds": {
   "support": "|beta| >= 0.15 with CI excluding 0 and p_holm < 0.05",
   "partial": "CI excludes 0 below the floor",
   "null": "CI includes 0",
   "h3": "supported (specific) when the control's |beta| < 0.05 and its CI includes 0 while H1's estimate clears the "
         "medium band; otherwise not_specific_control_tracks_the_same_variance"},
  "family": 3, "gate_scope": "H1",
  "kill_gate": "G7 >= 0.05 of turns carry a causal connective and G8 >= 0.50 of those turns have >= 50 characters of "
               "prior observation text to compare against. Measured 0.0601 and 0.8322.",
  "strata": "by connective family, by body-length quartile, and by task category",
  "tables": ["table1_sample_and_structure.csv", "table2_connective_prevalence.csv", "table3_main_models.csv",
             "table4_strata_by_family_and_length.csv", "table5_robustness_inference.csv",
             "table6_baseline_comparison.csv", "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_modality_examples.pdf", "fig2_main_effect.pdf",
              "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"]},

 # ------------------------------------------------------------------ T135: chains and the gaps they hide
 "T135": {
  "pkg": "P031_explanatory_coherence_and_evidential_gaps",
  "title": "Does Explanatory Coherence Conceal Evidential Gaps?",
  "rq": "Is a turn that strings several causal steps together better or worse supported by the evidence already in "
        "hand than a turn with a single step?",
  "hypotheses": [
   "H1 turns carrying at least two causal connectives overlap *less* with the prior observations than "
   "single-connective turns, the concealment direction, at least the medium band",
   "H2 chain turns are more likely than single-connective turns to end the trajectory at that turn, which is what a "
   "self-supporting explanation buys the agent",
   "H3 the association is not an artefact of length: within body-length quartiles the H1 contrast keeps its sign"],
  "features": {
   "chain": "1 if the turn carries >= 2 causal markers",
   "n_causal": "count of causal markers in the turn",
   "evidence_overlap": "as above", "body_len": "characters of the turn's body"},
  "dvs": {"evidence_overlap": "H1 and H3's outcome", "stops_here": "H2's outcome"},
  "models": [
   "OLS on standardised evidence_overlap with chain plus the standard controls, clustered on traj_id",
   "logistic on stops_here with chain plus the standard controls",
   "the H1 specification within each body-length quartile, reported as strata"],
  "thresholds": {
   "support": "|beta| >= 0.15 with CI excluding 0 and p_holm < 0.05",
   "partial": "CI excludes 0 below the floor",
   "null": "CI includes 0",
   "h3": "supported when the sign of H1's estimate is reproduced in >= 3 of 4 quartiles"},
  "family": 3, "gate_scope": "H1",
  "kill_gate": "G9 >= 200 turns carrying at least two causal connectives. Measured 490.",
  "strata": "by body-length quartile, by number of connectives, and by task category",
  "tables": ["table1_sample_and_structure.csv", "table2_chain_length_distribution.csv", "table3_main_models.csv",
             "table4_strata_by_length_quartile.csv", "table5_robustness_inference.csv",
             "table6_baseline_comparison.csv", "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_modality_examples.pdf", "fig2_main_effect.pdf",
              "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"]},

 # ------------------------------------------------------------------ T136: plans versus the next call
 "T136": {
  "pkg": "P032_plan_action_alignment",
  "title": "Alignment Between Linguistic Plans and Actual Information Actions",
  "rq": "When an agent says what it is about to look up, is that what the next call asks for?",
  "hypotheses": [
   "H1 the words of a plan-marked turn overlap with the next call's tool name and arguments more than they overlap "
   "with a call drawn from another trajectory of the same length, the permutation null, at least the medium band",
   "H2 lower alignment is followed by a failure-marked observation more often than higher alignment is, which is "
   "the reading under which a plan that is not executed is a plan that will not work",
   "H3 the association is not the tool-name vocabulary alone: restricting to the 20 most frequent tool families, "
   "the H1 contrast keeps its sign in at least 14 of them"],
  "features": {
   "plan_flag": "1 if any plan marker occurs in the turn",
   "align_next": "|content words of the turn INTERSECT content words of the next call's name and argument JSON| / "
                 "|content words of the turn|",
   "align_perm": "the same statistic against a call from a different trajectory, drawn by seeded permutation "
                 "(100 draws) within the same trajectory-length bin",
   "prev_obs_error_next": "1 if the observation returned by that next call carries a failure marker"},
  "dvs": {"align_diff_perm": "H1's outcome: the per-turn difference between align_next and its permutation mean, "
                             "clustered on traj_id",
          "prev_obs_error_next": "H2's outcome", "sign_by_tool_family": "H3's stratum counts"},
  "models": [
   "cluster bootstrap of the mean within-turn difference against the permutation null, with the band test",
   "logistic on prev_obs_error_next with the alignment residual plus the standard controls, on plan-marked turns",
   "the H1 contrast recomputed inside each of the 20 largest tool families"],
  "thresholds": {
   "support": "|beta| >= 0.15 with CI excluding 0 and p_holm < 0.05",
   "partial": "CI excludes 0 below the floor",
   "null": "CI includes 0",
   "h3": "supported when >= 14 of the 20 largest tool families reproduce the sign"},
  "family": 3, "gate_scope": "H1",
  "kill_gate": "G10 >= 200 plan-marked turns followed by at least one call. Measured 24,500.",
  "strata": "by tool family of the next call, by task category, and by trajectory position third",
  "tables": ["table1_sample_and_structure.csv", "table2_alignment_distribution.csv", "table3_main_models.csv",
             "table4_strata_by_tool_family.csv", "table5_robustness_inference.csv",
             "table6_baseline_comparison.csv", "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_modality_examples.pdf", "fig2_main_effect.pdf",
              "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"]},
}

RUNNABLE = ("T130", "T132", "T133", "T134", "T135", "T136")
EXP_OF = {"T130": "EXP-0165", "T132": "EXP-0166", "T133": "EXP-0167", "T134": "EXP-0168",
          "T135": "EXP-0169", "T136": "EXP-0170"}

MATRIX = "results_raw/EXP0164_wave5_step_matrix_*.json"
BATTERY = "results_raw/EXP0171_wave5_battery_0171_*.json"

FEATURE_EXP = "EXP-0164"
PREMISE_EXP = "EXP-0161"
BATTERY_EXP = "EXP-0171"
ENCODER_EXP = "not used in this wave"
MATRIX_GLOB = MATRIX
BATTERY_GLOB = "results_raw/EXP0171_wave5_battery_0171_*.json"
PREMISE_GLOB = "results_raw/EXP0161_wave5_premise_census_*.json"
ENCODER_GLOB = ""
SUBSTRATE_LABEL = ("hermes-agent-reasoning-traces release, deduplicated to one row per trajectory id (EXP-0162): "
                   "assistant turns, the calls inside them and the observations returned; P001's test split does not "
                   "exist in this corpus and 0 rows of it were read")
# What a literature row that shares the construct but not the population is differentiated from, in this wave's own
# words. The grader's L3 sentence used to name the routing corpus every earlier wave measured on, which a transcript
# package does not use, so the clause now comes from the module that owns the package.
CONTRIBUTION_POPULATION = ("a corpus of agent transcripts whose assistant turns carry their own reasoning, tool calls "
                           "and returned observations, read with frozen rule and lexical instruments and with no "
                           "ranker, no model and no human label")
SAMPLE_FIELDS = ("corpus", "files_read", "sample_cap", "trajectories", "assistant_turns",
                 "turns_emitting_a_call", "turns_followed_by_inspection", "calls_total", "calls_unparseable",
                 "cluster_unit", "act_any_share", "causal_share", "plan_share", "evidence_overlap_mean",
                 "evidence_computable_share")
DESIGNS_MODULE = "topic_designs_wave5"
CLEAN_ROOM_ONLY_FLAG = "--only"
# This wave's designs subsample on `--quick`, and T132's strata need 500 rows a cell, which a 2,000-trajectory draw
# cannot supply - the quick path therefore aborts on its own deliverable guard instead of shipping an empty table.
# The clean-environment re-run runs the design in full, on the same rows the shipped artefact read, so the headline
# comparison is exact rather than a smoke test.
CLEAN_ROOM_MODE = "full"
STAGE_RX = "wave5_main"
PROBE_SCRIPT = "probe_wave5_premises.py"
MATRIX_SCRIPT = "exp_wave5_features.py"
BATTERY_SCRIPT = "exp_wave5_battery.py"
ENCODE_SCRIPT = "encode_wave1_texts.py"
SCRIPT_OF = {t: "exp_wave5_designs.py" for t in RUNNABLE}
MAIN_SCRIPT_OF = {t: ("exp_wave5_designs.py", e) for t, e in EXP_OF.items()}

COMMON = dict(
    seed=SEED, sample=SAMPLE, bands=BANDS,
    instruments="rule-based act, connective and repair lexicons over the two prose faces of a turn; set overlap "
                "over content words for every evidence comparison; classical OLS and logistic models with "
                "cluster-robust standard errors; seeded permutation for the plan-alignment null. No judge, no API, "
                "no model reading or generating any text",
    notes="the evidence a connective or a conclusion is compared against is only what the agent had been given "
          "before that turn, so an overlap is a claim about the record, not about what the model 'meant'")

FAILED_RUNS = [
    "EXP0161_run_console.log (first launch): TypeError in the wave-5 census because `files` had become an int after "
    "the shared loader returned a count, and the measured block then had no G1 entry at all, so a declared gate had "
    "nothing to be compared against. The census now aborts when a gate has no measurement instead of letting the gate "
    "silently fail to fire.",
    "EXP0161 generation 20260924T131257.json: the census denominators were row counts, and EXP-0162 showed the "
    "release repeats 7,646 of its 14,701 trajectory ids. Kept-but-not-citable; the deduplicated census replaced it.",
]

# Deviations recorded against this wave as it was built, each naming what changed and what it changed.
EXTRA_DEVIATIONS = [
    ("W5-D01", "The premise census is reported as structure and prevalence only, and two gates fired",
               "T132's H1 froze a floor of 200 trajectories concluding before their first inspection and a floor of "
               "2% of turns carrying a conclusion marker. EXP-0161 measured 114 and 0.0075 against them, so H1 is "
               "recorded as not_testable at its own sentence while H2 and H3 stand on cells that cleared. No floor "
               "was lowered and no floor was moved after the number arrived."),
    ("W5-D02", "T134's H2 rests on a thin arm, and the thinness is stated rather than made a gate",
             "The census splits the causal family: an explanatory connective occurs in 5.88% of turns and an "
             "inferential one in 0.38% (about 153 of 40,340 turns). The family split was declared after the floors "
             "were fixed, so no new threshold is imposed on it and H2 is not withdrawn; its estimate is reported "
             "with the cell count next to it, and a family too thin to identify is recorded as not_testable on the "
             "count, which is the same rule the other waves apply."),
    ("W5-D03", "T136's permutation null is computed exactly instead of drawn",
             "The freeze named a 100-draw seeded permutation as the comparison for plan-action alignment. Drawing it "
             "costs one random choice per turn per draw over 640,000 turns and returns a Monte-Carlo estimate of a "
             "quantity that has a closed form: the mean alignment in the same trajectory-length bin, leaving the "
             "turn's own trajectory out. That exact expectation is what the frame computes, the 100-draw figure is "
             "recorded beside it in the artefact, and the statistical claim - a call from another trajectory of a "
             "comparable length - is unchanged."),
    ("W5-D04", "The literature grader's L3 sentence named a corpus this wave does not measure on",
             "The sentence that distinguishes an adjacent-population record stated that the package's contribution "
             "was measured on 'an agent-instruction corpus with a frozen lexical ranker', which is what the routing "
             "waves measure. This wave measures agent transcripts with lexical instruments and no ranker, so "
             "`CONTRIBUTION_POPULATION` is declared here and the grader composes the sentence from it; the count of "
             "rewritten sentences is measured in the EXP-0127 re-grade artefact. No overlap_level moved and no "
             "statistical verdict in this wave is affected (the same fix is recorded as D15 for wave 4)."),
    ("W5-D05", "Two build defects in the frame step, both found before any dependent variable was read",
             "The first frame build hung: marking the turn whose call produced a failure-marked observation scanned "
             "every row appended so far, which is quadratic in the size of the release. It is now one dict lookup per "
             "marked turn, and the step prints progress per 2,000 trajectories so a stall is visible rather than "
             "inferred. The second: the wave-5 columns and the wave-4 spine both carry `emits_call` and "
             "`first_call_name`, so the merge renamed them silently and the designs asked for a column the frame no "
             "longer had. The join now compares the two walks, drops a duplicate only where it is identical, keeps "
             "both readings under `_w5` where it is not, and aborts if a needed column disappears; the measured "
             "agreement is in the matrix artefact under `join_crosscheck_vs_wave4_spine` "
             "(emits_call 147,253/147,253; first_call_name 147,251/147,253). Neither change touches a threshold, "
             "band, seed, hypothesis or decision sentence."),
    ("W5-D06", "T132's H2 was fitted with a logit link on a continuous outcome, which moved two verdicts",
             "`glm()` defaults to the binomial family and T132's H2 - standardised evidence overlap - was passed "
             "without a family, so a logistic model was fitted to a continuous dependent variable. It returned a "
             "coefficient of -3.0e15 with a NaN cluster-robust interval, and the four-way rule read that interval as "
             "a null. The call now names `gaussian`, as the frozen model line for H2 says (OLS on standardised "
             "evidence_overlap), and `glm()` refuses a binomial link on an outcome that is not 0/1 so the mistake "
             "cannot recur silently. Re-running the wave moved T132's H2 from null to opposite (-0.2498, "
             "[-0.4141, -0.0855], p_holm 0.0058) and H3 from partial to supported, because Holm now has a real p to "
             "order. No threshold, band, seed, hypothesis direction or decision sentence was changed."),
    ("W5-D07", "T132's H1 floor was measured on the census sample, which is smaller than the design frame",
               "EXP-0161's census samples 4,000 trajectories and measured 114 of them concluding before their first "
               "inspection, below the frozen floor of 200, and the H1 sentence names that measurement as the thing "
               "the floor is tested against. The design frame is the full 20,000-trajectory draw (14,701 available) "
               "and carries 472 trajectories in the same cell, above the floor. H1 keeps the verdict its own frozen "
               "sentence gives it - not testable - and reports both numbers beside it, so the larger sample is "
               "visible without being used to reopen a test the pre-registration closed."),
    ("W5-D08", "The battery's external set first named a corpus that is not on this host",
               "E08 was written against an AgentNet export path, and the step's own guard reported `not attempted: "
               "the file is absent` rather than inventing a number. No transcript corpus other than this release "
               "exists locally (EXP-0027/29/30 measured what the eight routing releases carry), so the external set "
               "is now P001's routing instructions, dev split only, and what crosses is the marker lexicon's "
               "prevalence on human-written single-utterance prose. No association is transferred, because an "
               "instruction has no observation to overlap with and no call after it. The change alters no design, "
               "threshold or verdict in this wave."),
    ("W5-D09", "The shared battery step put a manipulated column into its model twice",
               "`exp_wave1_battery.fit()` built its term list as [x] + covariates without deduplicating, and T133 "
               "manipulates `prev_obs_error`, which is a control in every model of this wave. The duplicated column "
               "split the coefficient (0.073 against the design's 0.2921) and made the cluster-robust covariance "
               "singular, so the interval came back NaN, and the same was true of that topic's scaling and "
               "ablation rows. `terms()` now deduplicates in the order the spec names and `fit()` drops the rows the "
               "designs drop, so the battery estimates the design's model. The audit over every live battery "
               "artefact found the pattern in wave 5 only (0 non-finite statistics in the nine shipped wave-1 to "
               "wave-4 battery artefacts), and EXP-0158 was re-run under the change: its artefact is identical to "
               "the shipped one apart from timestamps and the recorded argv, so the fix is inert where no spec "
               "manipulates one of its own controls."),
]

# census key (dotted paths into its `measured` block are allowed) -> the name this freeze gives it. EXP-0163
# regenerates the PREMISES literal below from the census artefact through this map, so the freeze cannot keep quoting
# numbers a rebuilt census no longer produces.
PREMISE_MAP = {
    "trajectories_sampled": "trajectories", "assistant_turns_ge20": "turns_ge20",
    "G2_discourse_act_prevalence": "act_any_share", "G3_second_act_tagger_prevalence": "act_any_share_tagger_b",
    "act_share_by_act.plan": "act_share_plan", "act_share_by_act.conclusion": "act_share_conclusion",
    "G5_conclusion_before_first_inspection": "conclusion_before_first_inspection_trajectories",
    "G6_failure_marked_observation_units": "turns_after_failure_marked_observation",
    "G7_causal_connective_prevalence": "causal_connective_turn_share",
    "G8_evidence_text_computable": "causal_turns_with_evidence_computable",
    "G9_multi_connective_chains": "multi_connective_chain_turns",
    "G10_plan_marker_with_call_units": "plan_turns_followed_by_a_call",
    "G11_outcome_label_available": "outcome_label_coverage",
    "causal_inferential_turn_share": "causal_inferential_share",
    "causal_explanatory_turn_share": "causal_explanatory_share",
}

PREMISES = {
    "census": "EXP-0152 (EXP0161_wave5_premise_census_20260924T133555.json)",
    "transcribed_by": "02_shared_code/registry/refresh_wave_premises.py (EXP-0163); no number in this block is typed by hand",
    "measured": {
        "trajectories": 4000,
        "turns_ge20": 40340,
        "act_any_share": 0.6694,
        "act_any_share_tagger_b": 0.2677,
        "act_share_plan": 0.6352,
        "act_share_conclusion": 0.0075,
        "conclusion_before_first_inspection_trajectories": 114,
        "turns_after_failure_marked_observation": 22209,
        "causal_connective_turn_share": 0.0601,
        "causal_turns_with_evidence_computable": 0.8322,
        "multi_connective_chain_turns": 490,
        "plan_turns_followed_by_a_call": 24500,
        "outcome_label_coverage": 0.0,
        "causal_inferential_share": 0.0038,
        "causal_explanatory_share": 0.0588,
    },
    "gates": {
          "G10_plan_marker_with_call_units": True,
          "G11_outcome_label_available": False,
          "G1_assistant_text_available": True,
          "G2_discourse_act_prevalence": True,
          "G3_second_act_tagger_prevalence": True,
          "G4_conclusion_marker_prevalence": False,
          "G5_conclusion_before_first_inspection": False,
          "G6_failure_marked_observation_units": True,
          "G7_causal_connective_prevalence": True,
          "G8_evidence_text_computable": True,
          "G9_multi_connective_chains": True,
      },
    "verdict": {
          "blocked_gates": ["G4_conclusion_marker_prevalence", "G5_conclusion_before_first_inspection", "G11_outcome_label_available"],
          "blocked_whole_design": [],
          "claim_limited": {"G4_conclusion_marker_prevalence": "H1", "G5_conclusion_before_first_inspection": "H1"},
      },
    "note": "a fired gate is a result, not an obstacle: it stops exactly what its frozen sentence scopes",
    "runnable": list(RUNNABLE),
}
