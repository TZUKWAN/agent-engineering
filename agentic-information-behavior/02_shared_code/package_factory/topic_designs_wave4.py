"""Wave 4: does an agent's language about its own uncertainty track what it then *does*?

Four frozen designs plus one topic stopped by a gate measured before this file existed. The substrate is the
hermes-agent-reasoning-traces release: 4,000 sampled trajectories, 42,693 assistant turns, 50,760 parsed tool
calls with 50,760 parsed observations (EXP-0152). Every design here compares prose with behaviour, so the two are
kept in separate channels by construction:

* the language side is the marker lexicons below, applied to the assistant turn, reported **per face** - the
  reasoning block and the user-facing body are different registers and the census measured them apart
  (modality prevalence 0.1707 inside the reasoning block, 0.0488 in the body, 0.1595 over the whole turn);
* the behaviour side is the *name of the tool the agent called next* and whether the trajectory continued at all.
  Nothing on the behaviour side is derived from the text, which is the failure EXP-0076 measured on AgentNet
  (verification language scored at chance against a label taken from the same reflection).

| topic | package | question in one line |
|-------|---------|----------------------|
| T123  | P023    | does a hedged turn predict an inspection action next? |
| T124  | P024    | does an agent that hedges privately but asserts publicly still check? |
| T126  | P025    | does contradicting evidence raise the language of uncertainty? |
| T127  | P026    | does "I have enough" predict stopping, beyond what the evidence state predicts? |
| T191  | -       | blocked: the release carries no outcome field at all (EXP-0152, gate G7) |

Everything below - the seeds, the thresholds, the bands, the decision rules and what each gate scopes - was written
before any estimate in this wave existed. The prevalence numbers come from EXP-0152, which read structure only.
"""
from __future__ import annotations

SEED = 42
SAMPLE = dict(traj_cap=20000, bucket="all", cluster_unit="traj_id",
              rule="every trajectory in the release, read from the four parquet files in sorted order and capped at "
                   "20,000 by a seeded sample (seed 42); the same indices are used by the matrix, the designs and "
                   "the battery, so a difference between steps cannot be a difference in the sample",
              step_unit="one assistant turn and the behaviour that follows it")
BANDS = dict(small=0.05, medium=0.15, large=0.30)      # the same effect bands as waves 1-3

# ------------------------------------------------------------------ the lexicons (identical to EXP-0152's census)
MODAL = ["may ", "might ", "could ", "possibly", "probably", "perhaps", "unclear", "unsure", "not sure",
         "seems", "appears to", "likely", "unlikely", "assume", "assumption", "i think", "believe",
         "not certain", "could be", "should be able", "need to verify", "to confirm", "if i read"]
SUFFIC = ["enough", "sufficient", "that should do", "that will do", "we have what", "insufficient",
          "not enough", "more information", "need more", "missing", "all the information", "complete information"]
# A topical control lexicon of the same size and the same domain, built only to be *not* an uncertainty marker: the
# file/system vocabulary a coding agent uses while being entirely certain. Pre-registered for T123's H3.
TOPICAL_CONTROL = ["file", "directory", "path", "code", "script", "function", "line", "error", "output",
                   "command", "content", "result", "string", "value", "config", "folder", "repository",
                   "package", "module", "variable", "argument", "version", "branch", "commit", "terminal",
                   "session", "cache", "log", "test", "build", "install", "package.json", "readme", "python"]
FAILURE_MARKERS = ["error", "not found", "failed", "traceback", "permission denied", "no such", "exception"]

DESIGNS = {
 # ------------------------------------------------------------------------------------------ T123 / P023
 "T123": dict(
    pkg="P023_modality_and_verification",
    title="Do Epistemic-Modality Cues Predict an Agent's Verification Behaviour?",
    rq="Does an assistant turn that carries epistemic-modality language get followed by an information-gathering "
       "action more often than a turn that does not, once the position in the trajectory and the state of the "
       "evidence are held fixed?",
    hypotheses=[
        "H1 a turn carrying a modality marker is followed by an inspection-family call more often than a turn "
        "without one, with the direction predicted positive",
        "H2 the association is stronger for a turn that immediately follows an observation carrying a failure "
        "marker, i.e. hedging is a response to a check that did not come off",
        "H3 the effect is specific to the uncertainty lexicon: a same-size topical control lexicon drawn from the "
        "same register shows no comparable association"],
    features={
        "modal_turn": "1 if any MODAL string occurs in the turn, case-insensitive (reasoning block and body)",
        "modal_body": "the same test applied to the user-facing body only",
        "modal_think": "the same test applied to the reasoning block only",
        "topical_control_turn": "1 if any TOPICAL_CONTROL string occurs in the turn",
        "prev_obs_error": "1 if the immediately preceding observation carries a FAILURE_MARKER"},
    dvs={"next_is_inspect": "1 if the next action is a call whose tool name is inspection-family",
         "next_is_call": "1 if the turn is followed by any call at all"},
    models=["logistic on next_is_inspect with the marker, turn index, log body length, prior inspection count, "
            "prior non-inspection count and prev_obs_error, cluster-robust SEs on traj_id",
            "the same model with a marker x prev_obs_error interaction for H2",
            "the same model with the topical control lexicon substituted for the marker, for H3"],
    thresholds=dict(support="|beta| >= 0.15 with CI excluding 0 and p_holm < 0.05",
                    partial="CI excludes 0 below the floor", null="CI includes 0",
                    h3="H3 is supported when the control lexicon's |beta| is below the small band and the marker's "
                        "is above it; it is reported as not-specific otherwise"),
    family=3,
    gate_scope="H1",
    kill_gate="if the hedged-then-inspection and plain-then-inspection arms do not each hold >= 200 turns, H1 is "
              "reported as a prevalence description rather than a test",
    strata="by task category and by turn position (first third / middle / last third)",
    tables=["table1_sample_and_structure.csv", "table2_modality_distribution.csv", "table3_main_models.csv",
            "table4_strata_by_position_and_category.csv", "table5_robustness_inference.csv", "table6_baseline_comparison.csv",
            "table7_experiment_provenance.csv", "table_run_cost.csv"],
    figures=["fig0_framework.pdf", "fig1_modality_examples.pdf", "fig2_main_effect.pdf",
             "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"]),

 # ------------------------------------------------------------------------------------------ T124 / P024
 "T124": dict(
    pkg="P024_epistemic_behavioural_gap",
    title="The Epistemic-Behavioural Gap: Saying 'Uncertain' versus Actually Checking",
    rq="When the two faces of one assistant turn disagree about being unsure - the reasoning block hedges and the "
       "user-facing body does not - is the behaviour like the hedge or like the assertion?",
    hypotheses=[
        "H1 turns that hedge privately while asserting publicly are followed by inspection at a rate closer to the "
        "hedge than to the assertion, i.e. the private face carries the epistemic signal",
        "H2 turns that hedge only in the user-facing body are not elevated over turns that hedge nowhere, which is "
        "the reading that treats a public hedge as conversational rather than epistemic",
        "H3 the discordant pattern is associated with a lower rate of stopping at that turn than a body-only hedge "
        "is, i.e. private uncertainty keeps the search going"],
    features={
        "face_pattern": "discordant (think=1, body=0) / concordant (1,1) / body_only (0,1) / neither (0,0), "
                        "computed only on turns whose body is >= 20 characters and which have a reasoning block",
        "body_hedge": "the user-facing face alone", "think_hedge": "the reasoning face alone"},
    dvs={"next_is_inspect": "1 if the next action is an inspection-family call",
         "stops_here": "1 if no further action follows the turn"},
    models=["logistic on next_is_inspect with two indicator contrasts (discordant vs neither, body_only vs neither) "
            "plus position, body length and prior inspection counts, cluster-robust SEs on traj_id",
            "the discordant vs concordant contrast, which asks whether agreement across faces changes anything",
            "logistic on stops_here with the same indicators for H3"],
    thresholds=dict(support="|beta| >= 0.15 with CI excluding 0 and p_holm < 0.05",
                    partial="CI excludes 0 below the floor", null="CI includes 0",
                    h2="H2 is supported only when the body-only contrast is null, so a positive there reads as "
                        "evidence against the conversational interpretation"),
    family=3,
    gate_scope="H1",
    kill_gate="if the discordant cell holds fewer than 200 turns, H1 is not testable and the pattern is reported "
              "as a prevalence census",
    strata="by task category and by whether the preceding observation carried a failure marker",
    tables=["table1_sample_and_structure.csv", "table2_face_pattern_distribution.csv", "table3_main_models.csv",
            "table4_strata_by_category_and_error.csv", "table5_robustness_inference.csv", "table6_baseline_comparison.csv",
            "table7_experiment_provenance.csv", "table_run_cost.csv"],
    figures=["fig0_framework.pdf", "fig1_face_examples.pdf", "fig2_main_effect.pdf",
             "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"]),

 # ------------------------------------------------------------------------------------------ T126 / P025
 "T126": dict(
    pkg="P025_contradiction_and_modality",
    title="Does Contradicting Evidence Escalate Epistemic Modality?",
    rq="After the same tool returns different content on two consecutive calls, does the next assistant turn carry "
       "more uncertainty language than after the same tool returns the same content?",
    hypotheses=[
        "H1 the modality rate rises after a same-tool content change relative to a same-tool identical observation, "
        "compared within trajectory",
        "H2 the rise is specific to contradiction: a new observation from a *different* tool does not raise modality "
        "as much as a changed observation from the same tool",
        "H3 sufficiency language moves in the same direction as modality in that condition, i.e. the agent states the "
        "information state as well as hedging about it"],
    features={
        "prev_state": "same_tool_changed / same_tool_same / different_tool / none, read off the observation stream",
        "modal_turn": "as in T123", "suffic_turn": "as in T123"},
    dvs={"modal_turn": "the marker on the turn that follows the observation",
         "modal_think": "the same marker restricted to the reasoning block"},
    models=["logistic on modal_turn with the prev_state indicators, position and body length, cluster-robust SEs on "
            "traj_id; the same-tool-changed term is H1",
            "the same-tool-changed vs different-tool contrast for H2, with a cluster bootstrap on the difference",
            "the same model with suffic_turn as the dependent variable for H3"],
    thresholds=dict(support="|beta| >= 0.15 with CI excluding 0 and p_holm < 0.05",
                    partial="CI excludes 0 below the floor", null="CI includes 0",
                    h2="H2 is supported when the changed-vs-different difference has CI excluding 0"),
    family=3,
    gate_scope="H3",
    kill_gate="if fewer than 200 trajectories contain a same-tool content change, the contradiction cell is not "
              "testable and H3 is reported as not testable while H1/H2 keep their own estimates",
    strata="by tool family (inspection / execution / production) of the contradicting call",
    tables=["table1_sample_and_structure.csv", "table2_contradiction_census.csv", "table3_main_models.csv",
            "table4_strata_by_tool_family.csv", "table5_robustness_inference.csv",
            "table6_baseline_comparison.csv", "table7_experiment_provenance.csv", "table_run_cost.csv"],
    figures=["fig0_framework.pdf", "fig1_contradiction_examples.pdf", "fig2_main_effect.pdf",
             "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"]),

 # ------------------------------------------------------------------------------------------ T127 / P026
 "T127": dict(
    pkg="P026_sufficiency_language_and_stopping",
    title="The Language of Perceived Information Sufficiency and When Agents Stop",
    rq="Does a turn that asserts the agent has enough information end the trajectory more often than the evidence "
       "state alone predicts?",
    hypotheses=[
        "H1 a sufficiency claim raises the probability that the trajectory stops at that turn beyond what the prior "
        "inspection count, the prior non-inspection count, position and the last observation's failure state predict "
        "(incremental validity over the evidence-state baseline)",
        "H2 stops that follow a sufficiency claim have gathered less information - fewer prior inspection calls - "
        "than stops that do not, which is the premature-termination reading",
        "H3 the association is not uniform across task categories, so the pooled coefficient is reported together "
        "with the category strata"],
    features={
        "suffic_turn": "1 if any SUFFIC string occurs in the turn (either face)",
        "prior_inspections": "count of inspection-family calls earlier in the trajectory",
        "prior_non_inspections": "count of all other calls earlier in the trajectory"},
    dvs={"stops_here": "1 if no further action follows the turn"},
    models=["logistic on stops_here with the evidence-state covariates alone (the baseline), then with the "
            "sufficiency claim added; the comparison is a likelihood-ratio test plus the added term's clustered "
            "coefficient",
            "cluster bootstrap of the difference in prior_inspections between claim-preceded and other stops",
            "category strata of the added term, reported descriptively"],
    thresholds=dict(support="added-term |beta| >= 0.15 with CI excluding 0 and p_holm < 0.05, or a difference in "
                            "prior inspections >= 0.5 calls with CI excluding 0",
                    partial="CI excludes 0 below the floor", null="CI includes 0",
                    h3="H3 is a heterogeneity description: no threshold, no Holm entry"),
    family=3,
    gate_scope="H1",
    kill_gate="if fewer than 200 trajectory endings are preceded by a sufficiency claim, H1 is reported as a "
              "prevalence measurement rather than a test of stopping",
    strata="by task category and by trajectory length quartile",
    tables=["table1_sample_and_structure.csv", "table2_sufficiency_distribution.csv", "table3_main_models.csv",
            "table4_strata_by_category_and_length.csv", "table5_robustness_inference.csv", "table6_baseline_comparison.csv",
            "table7_experiment_provenance.csv", "table_run_cost.csv"],
    figures=["fig0_framework.pdf", "fig1_sufficiency_examples.pdf", "fig2_main_effect.pdf",
             "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"]),
}

EXP_OF = {"T123": "EXP-0154", "T124": "EXP-0155", "T126": "EXP-0156", "T127": "EXP-0157"}
RUNNABLE = ("T123", "T124", "T126", "T127")     # T191 stopped by gate G7 at EXP-0152
MATRIX = "results_raw/EXP0153_wave4_step_matrix_*.json"
BATTERY = "results_raw/EXP0158_wave4_battery_0158_*.json"

# ------------------------------------------------------------------ wave-level constants for the package builder
FEATURE_EXP = "EXP-0153"
PREMISE_EXP = "EXP-0152"
BATTERY_EXP = "EXP-0158"
ENCODER_EXP = "not used in this wave"
MATRIX_GLOB = MATRIX
BATTERY_GLOB = "results_raw/EXP0158_wave4_battery_0158_*.json"
PREMISE_GLOB = "results_raw/EXP0152_wave4_premise_census_*.json"
ENCODER_GLOB = ""
# This wave's package table 1 is about trajectories, not query/candidate frames, so the substrate sentence and the
# sample fields the matrix artefact actually carries are named here rather than inherited from wave 1's text.
SUBSTRATE_LABEL = ("hermes-agent-reasoning-traces release: assistant turns with the tool calls inside them and the "
                   "observations returned, sampled at the frozen trajectory cap; P001's test split does not exist in "
                   "this corpus and 0 rows of it were read")
# What a literature row that shares the construct but not the population is differentiated from, in this wave's own
# words. The grader's L3 sentence used to name the routing corpus every earlier wave measured on, which a transcript
# package does not use, so the clause now comes from the module that owns the package (deviation D15).
CONTRIBUTION_POPULATION = ("a corpus of agent transcripts whose assistant turns carry their own reasoning, tool calls "
                           "and returned observations, read with frozen rule and lexical instruments and with no "
                           "ranker, no model and no human label")
SAMPLE_FIELDS = ("corpus", "files_read", "sample_cap", "trajectories", "assistant_turns", "turns_emitting_a_call",
                 "turns_followed_by_inspection", "calls_total", "calls_unparseable", "cluster_unit",
                 "modal_turn_share", "suffic_turn_share", "topical_control_share", "topical_count_sd")
DESIGNS_MODULE = "topic_designs_wave4"
CLEAN_ROOM_ONLY_FLAG = "--only"
STAGE_RX = "wave4_main"
PROBE_SCRIPT = "probe_wave4_premises.py"
MATRIX_SCRIPT = "exp_wave4_features.py"
BATTERY_SCRIPT = "exp_wave4_battery.py"
ENCODE_SCRIPT = "encode_wave1_texts.py"
SCRIPT_OF = {t: "exp_wave4_designs.py" for t in RUNNABLE}
MAIN_SCRIPT_OF = {t: ("exp_wave4_designs.py", e) for t, e in EXP_OF.items()}
DENSE_SUPERSESSION_NOTE = "(no wave-4 design uses the dense arm; the encoder cache is not read here)"
FAILED_RUNS = [
    "EXP0152_run_console.log / results_raw/EXP0152_wave4_premise_census_20260924T111506.json: the census read tool "
    "calls from a role named 'function_call' that this release does not use, counted zero calls and reported "
    "inspection prevalence 0.000. Had this generation stood, four designs would have been blocked by the "
    "instrument rather than by the data.",
    "EXP0152 generation 20260924T112454.json: a per-trajectory flag was summed inside the message loop, so a share "
    "printed as 10.67, and terminal/execute_code were classed as production calls, putting 68% of calls in the "
    "write family. The kept generation counts each unit once and reports the execution family separately (0.4775).",
    "EXP0152 generation 20260924T112631.json: complete but without the joint turn-to-action cells that the wave-4 "
    "gates need, so G8-G11 could not be evaluated.",
    "EXP0152_run_console.log (two aborted launches at 11:33): TypeError on a turn with no following step, and a "
    "KeyError where a gate name did not match its measured key. Both are instrument fixes; the thresholds and gate "
    "sentences were not touched, and no outcome had been read at either point.",
    "environment/clean_room_run_*.json of all four wave-4 packages (first build): the gate G18-E re-run exited 1 "
    "because the design script looked for its own input frame inside the redirected scratch directory, so the "
    "clean-room record showed a failure and the package audit still printed weak=none. The designs now search the "
    "repository's results_processed for the matrix, record which file they read, and the audit reads the exit code "
    "out of the record instead of only checking that a record exists.",
]

# T191 asks when verification is worth it, which needs an outcome. EXP-0152 measured that this release has no
# outcome column at all, and the programme's own conformance census (EXP-0027/0029/0030) measured outcome coverage
# of 1/8 corpora; the local release with the best outcome coverage is AgentTrove's `result` at 13.7%, below the 50%
# gate, so the block is a corpus-family fact rather than one file's gap.
# Deviations recorded against this wave as it was built, each naming what changed and what it changed.
EXTRA_DEVIATIONS = [
    ("D07", "The pre-registered specificity control was degenerate and is reported in its count form",
             "T123's H3 froze the topical control as an indicator (does this turn mention any of 34 file/system "
             "words). EXP-0153 measured its prevalence at 0.9998 of 234,920 turns: an indicator that is almost "
             "always 1 has no variance and no identifiable coefficient, so the same lexicon enters as its "
             "standardised occurrence count (sd 53.5). The indicator's prevalence is printed in the artefact and in "
             "the main-models table rather than being replaced in silence."),
    ("D08", "A falsy-zero bug in the Holm family inflated every corrected p in the first wave-4 run",
             "`float(r.get('p') or 1.0)` reads a genuine p = 0.0 as false and substitutes 1.0, so the first "
             "generation reported p_holm = 1.0 for a coefficient a dozen standard errors from zero and printed "
             "`partial` where the frozen rule gives `supported`. The family now tests for None explicitly. The "
             "superseded generations are in the programme ledger; no threshold or decision rule changed between "
             "them."),
    ("D09", "A duplicated covariate made an interaction model singular and it reported itself as untestable",
             "prev_obs_error is both a control and part of T123's H2 interaction, so the design matrix carried it "
             "twice; the cluster-robust covariance raised Singular matrix and the fit helper returns None for that, "
             "which the design read as not_testable. Covariate lists are de-duplicated before fitting, and a "
             "singular fit is now distinguishable from a genuinely thin cell."),
    ("D10", "T124's H2 has an outcome the frozen sentence did not name",
             "The rule froze two possibilities - the body-only contrast is null, or it is positive - and the "
             "estimate is neither: negative, with an interval excluding zero. It is recorded as "
             "`outside_the_frozen_rule_negative_contrast` with its number instead of being relabelled as the null "
             "the rule would have called a support."),
    ("D11", "A fired design-scope gate is recorded against the topic it stops, not against its own name",
            "EXP-0152's first four generations put the gate key in `blocked_whole_design`, so `record_blocked.py` "
            "filed an evidence row whose topic_id was `G7_outcome_label_available` - a real block, recorded under a "
            "name that is not a topic, while T191's own row only survived because this module re-listed it as an "
            "inherited block. Each gate now carries a pre-registered `blocks` list (the scope sentence in "
            "machine-readable form) and the census emits topics. The measured values are bit-identical across the "
            "change: no threshold, rule sentence or scope was altered, and the diff against the superseded "
            "generation is schema plus the timestamp."),
    ("D12", "Two strata tables were renamed to say what the freeze's own stratification measures",
             "T123's freeze stratifies by turn position *and* task category and T124's by task category *and* "
             "whether the preceding observation carried a failure marker; the first build fitted only the first "
             "dimension each, and T126's tool-family stratification was computed on tool names. The design runs now "
             "fit every named dimension (with a term that is constant inside its own stratum dropped and named in "
             "the row), and the files are `table4_strata_by_position_and_category.csv`, "
             "`table4_strata_by_category_and_error.csv` and `table4_strata_by_category_and_length.csv`. No "
             "hypothesis, threshold or primary model changed; the strata rows are descriptive."),
    ("D13", "The baseline-comparison table is a fitted reduced model, not a sentence about one",
             "`table6_baseline_comparison.csv` was the one package table that could be produced by a fallback: a "
             "wave with no `baselines` block shipped a two-cell note describing another wave's BM25 columns, which "
             "in a trajectory wave would simply have been false. Each wave-4 design now fits the evidence-state "
             "model on its own and with its construct term added, and reports the deviance drop with its "
             "likelihood-ratio statistic on the degrees of freedom actually added. The packager's unknown-source "
             "fall-through now stops the build instead of writing a note into a deliverable."),
    ("D14", "The release stores 7,646 of its trajectories twice, and the first wave-4 estate counted them twice",
            "EXP-0162 measures it: 22,347 parquet rows carry 14,701 distinct `traj_id`s, the repeats being the same "
            "trajectory in `train.parquet` and in the sharded copy, byte-identical in 300/300 inspected cases. The "
            "loaders sampled rows, so 74.6% of the shipped step frame's 234,920 turn rows were duplicated content, "
            "and on a seeded 4,000-trajectory sample the marker prevalences move when the duplicates are dropped "
            "(modality 0.1569 -> 0.1379, sufficiency 0.0470 -> 0.0431, plan language 0.6934 -> 0.6068). Both loaders "
            "now drop the repeated ids before sampling and record how many they dropped. The whole wave was rebuilt "
            "from the deduplicated frame; no threshold, band, seed, hypothesis or decision sentence changed, and "
            "the superseded generations are named in the programme ledger with this measurement as the reason."),
    ("D15", "The literature grader's L3 sentence named a corpus this wave does not measure on",
             "`grade_wave_literature.DIFF` was authored while every graded package was a routing-corpus paper, so its "
             "L3 sentence stated that the package's contribution was the measured mechanism on 'an agent-instruction "
             "corpus with a frozen lexical ranker'. P023-P026 measure an agent-transcript release with lexical "
             "instruments and no ranker, so the sentence in 5 shipped rows described a population their package does "
             "not use. The sentence is now composed from a `CONTRIBUTION_POPULATION` the owning wave module declares "
             "and the four matrices were re-graded; the measured count is in the artefact of that re-grade. No "
             "overlap_level moved: the four-family rule, the lexicons, the collision targets and every statistical "
             "verdict in this wave are untouched."),
]

INHERITED_BLOCKS = {
    "T191": {"package": "", "exp": "EXP-0152",
             "measured": {"outcome_field_coverage_of_sampled_trajectories": 0.0,
                          "gate": 0.50,
                          "best_local_alternative": "AgentTrove `result` 13.7% (EXP-0027), below the same gate"},
             "why": "a quality-verification trade-off cannot be estimated without a measured quality; every "
                    "quantity the design needs on the cost side exists, and the benefit side does not"}}

COMMON = dict(
    seed=SEED, sample=SAMPLE, bands=BANDS,
    substrate="hermes-agent-reasoning-traces: sampled trajectories with their assistant turns, the tool calls "
              "embedded in those turns, and the observations returned - 50,760 parsed calls against 50,761 "
              "call-shaped blocks (EXP-0152)",
    instruments="rule-based marker lexicons over two registers of the same turn, tool-name families read off the "
                "call record, and classical logistic models with cluster-robust SEs; no judge, no API, no model "
                "reading or generating any text",
    notes="the behaviour channel is never derived from the text channel, which is the specific defect EXP-0076 "
          "measured on AgentNet where the step label judged the reflection that was being used as the predictor")

# The premise census results. Written as a hand transcription before any wave-4 outcome existed, and
# regenerated from the cited census artefact by EXP-0163 whenever that census is rebuilt, so the block names
# the artefact it matches rather than remembering numbers. The measured values are structure and prevalence
# only: no dependent variable of any design in this wave is computed by the census.
PREMISES = {
    "census": "EXP-0152 (EXP0152_wave4_premise_census_20260924T131828.json)",
    "transcribed_by": "02_shared_code/registry/refresh_wave_premises.py (EXP-0163); no number in this block is typed by hand",
    "measured": {
        "T123_hedged_turns_followed_by_inspection": 965,
        "T123_plain_turns_followed_by_inspection": 4502,
        "T123_turns_after_failure_marked_observation": 19313,
        "T123_modality_rate_after_failure_observation": 0.1535,
        "T124_discordant_hedge_turns": 3694,
        "T124_concordant_hedge_turns": 332,
        "T124_body_only_hedge_turns": 1653,
        "T126_trajectories_with_same_tool_content_change": 1373,
        "T127_stops_preceded_by_sufficiency_claim": 267,
        "T127_stops_total": 1845,
        "T127_mean_prior_inspections_at_stop": 3.01,
        "T127_mean_prior_non_inspections_at_stop": 10.83,
        "modality_prevalence_whole_turn": 0.1408,
        "modality_prevalence_body_only": 0.0492,
        "modality_prevalence_reasoning_block": 0.1677,
        "sufficiency_marker_turn_share": 0.0444,
        "inspection_call_share": 0.1803,
        "execution_call_share": 0.4847,
        "write_only_call_share": 0.2051,
        "outcome_label_coverage": 0.0,
        "rows_census_actual": 4000,
    },
    "gates": {
          "G10_turns_after_error_observation": True,
          "G11_stops_preceded_by_sufficiency_claim": True,
          "G1_assistant_text_available": True,
          "G2_modality_prevalence": True,
          "G3_inspection_action_prevalence": True,
          "G4_trajectories_with_three_assistant_turns": True,
          "G5_contradiction_cell": True,
          "G6_sufficiency_cell": True,
          "G7_outcome_label_available": False,
          "G8_T123_contrast_smallest_arm": True,
          "G9_discordant_hedge_turns": True,
      },
    "verdict": {
          "blocked_gates": ["G7_outcome_label_available"],
          "blocked_whole_design": ["T191"],
          "claim_limited": {},
      },
    "note": "a fired gate is a result, not an obstacle: it stops exactly what its frozen sentence scopes",
    "runnable": list(RUNNABLE),
}
