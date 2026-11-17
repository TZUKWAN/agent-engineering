"""The wave-12 protocol freeze: the closing batch of the 2026-09-23 intake.

Four designs, on three corpora and over all eight: T184 compares what a natural-language action, a tool call and an
executed code block each buy per character of agent output (xingyaoww/code-act); T189 asks whether an explicit
reflection changes the reasoning that follows it or is ritual (VIS-MPU-Agent/MMAT-1M); T194 asks whether a task
similar to one already attempted is searched differently (the estate's fixed SWE-ZERO draw); and T036 is the
descriptive aggregation of what the eight local corpora can and cannot say about agentic information behaviour.

EXP-0215 measured all four substrates twice with byte-identical output, and four arms came out limited by their own
sentences rather than blocked whole:

* **MMAT carries no correctness label** (G7 fired: 0 of 4,000 conversations), so T189 may claim that a reflection
  changes the next thought, and how often, but never that the change made the answer right;
* **the SWE-ZERO release records neither a timestamp nor a retrieved-case field** (G10 fired: 0 of 20,000 rollouts),
  so T194's third arm - that an agent drew on a past case - is not observable here at all and is reported as such;
* **only 200 of 20,000 rollouts have a neighbour instance at content similarity >= 0.3** (G9 fired against a floor of
  1,000), so T194's first arm is a measured prevalence with its floor stated, not a claim about a case library;
* **3 of the 8 corpora expose an outcome or quality column** (G12 fired against 4), which caps what T036's
  aggregation may say about labelled evidence across the estate.

No threshold was moved after a number was read, and nothing in this wave is estimated with a model.
"""
from __future__ import annotations

EXP_OF = {"T184": "EXP-0216", "T189": "EXP-0217", "T194": "EXP-0218", "T036": "EXP-0219"}
RUNNABLE = tuple(EXP_OF)
BLOCKED_BY_GATE = ()
CLAIM_LIMITED = {"T189": ("H3", "G7_mmat_no_correctness_label"), "T194": ("H1", "G9_swe_has_neighbours"),
                 "T036": ("H1", "G12_eight_corpus_label_coverage")}
FEATURE_EXP = "EXP-0220"
PREMISE_EXP = "EXP-0215"
BATTERY_EXP = "EXP-0221"
ENCODER_EXP = ""
SEED = 42
BANDS = {"small": 0.05, "medium": 0.15, "large": 0.30}
MATRIX = "results_raw/EXP0220_wave12_action_matrix_*.json"
PREMISE_GLOB = "results_raw/EXP0215_wave12_premise_census_*.json"
BATTERY = "results_raw/EXP0221_wave12_battery_0221_*.json"
MATRIX_GLOB = MATRIX
BATTERY_GLOB = BATTERY
ENCODER_GLOB = ""
MATRIX_SCRIPT = "exp_wave12_features.py"
BATTERY_SCRIPT = "exp_wave12_battery.py"
PROBE_SCRIPT = "probe_wave12_premises.py"
DESIGNS_MODULE = "topic_designs_wave12"
STAGE_RX = "wave12_main"
CLEAN_ROOM_ONLY_FLAG = "--only"
CLEAN_ROOM_MODE = "full"
SCRIPT_OF = {t: "exp_wave12_designs.py" for t in RUNNABLE}
MAIN_SCRIPT_OF = {t: "exp_wave12_designs.py" for t in RUNNABLE}
SUBSTRATE_LABEL = ("three corpora read at their frozen caps plus an inventory of all eight: xingyaoww/code-act "
                   "(4,000 of 78,385 conversations, each an assistant turn typed as natural language, a tool call or "
                   "an <execute> code block with the environment's reply); VIS-MPU-Agent/MMAT-1M (4,000 of 1,659,279 "
                   "lines of the validation file, a <THOUGHT>/<OPERATOR> loop whose operator results come back as user "
                   "turns); the estate's fixed SWE-ZERO draw (20,000 rollouts, 1,784 instances); and the eight-corporus "
                   "structure inventory EXP-0215 counted from the directories")
SAMPLE_FIELDS = ("corpus_set", "codeact", "mmat", "swe", "eight_corpora", "cluster_unit")
CONTRIBUTION_POPULATION = ("recorded agent traces from four corpora and a structural inventory of all eight local "
                           "corpora, read with rule and lexical instruments only; no model, no judge, and no claim "
                           "about correctness where the release does not record one")

COMMON = {
    "seed": SEED,
    "bands": BANDS,
    "module": "topic_designs_wave12",
    "sample": {"traj_cap": 4000, "cluster_unit": "conversation_id",
              "unit_of_analysis": "the conversation (code-act and MMAT) or the rollout and its instance (SWE-ZERO)",
              "rule": "each corpus is read to its frozen cap in file order from the seeded sample EXP-0215 names, and "
                      "the SWE-ZERO draw is the estate's fixed 12-file, content-deduplicated sample; no subsample "
                      "after that, and every claim states the cap it was measured on",
              "excluded": "conversations with no assistant turn (10 of 4,000 in code-act, 0 in MMAT) and, for T194, "
                          "instances with a single attempt when a comparison of attempts is what is being counted"},
    "instruments": ("an action kind is read from the assistant turn itself: an <execute> block is code, a tool-call or "
                    "python-fence marker is a tool action, otherwise natural language; density is content words per "
                    "1,000 characters of that turn; a returned observation is the following non-assistant turn; an "
                    "error string is wave 4's failure vocabulary; a reflection marker is the frozen phrase list in "
                    "EXP-0215, and the content shift it produces is the Jaccard of content words between consecutive "
                    "<THOUGHT> blocks; instance similarity is the Jaccard of the first 400 sorted content words of "
                    "each issue text"),
}

DESIGNS = {
 # ------------------------------------------------------------------ T184
 "T184": {
  "pkg": "P067_information_density_of_language_and_code_actions",
  "title": "Information Density of Natural-Language versus Code Actions",
  "rq": "Per character the agent has to produce, what does a line of code buy that a sentence does not - and does the "
        "environment answer a code action at all?",
  "hypotheses": [
   "H1 an executed code block carries a higher content-word density per 1,000 characters of agent text than a "
   "natural-language assistant turn, reported as a difference of means with a bootstrap interval on the conversation.",
   "H2 a code action is followed by a returned observation far more often than a natural-language action is, which is "
   "the sense in which code is a cheaper way of asking the world something.",
   "H3 code actions compose and self-correct: a multi-statement block is the norm rather than the exception, and after "
   "an observation reporting a problem the next executed block differs from the previous one - both reported as shares "
   "with intervals, not as effects on a task outcome the release does not record."],
  "features": {"kind": "code / tool / natural language, read from the turn itself",
               "density": "content words per 1,000 characters of that turn",
               "has_observation": "a following non-assistant turn exists",
               "statements": "semicolon- or newline-separated statements in the block",
               "changed_after_error": "the next executed block differs from the one whose reply reported a problem"},
  "dvs": {"density": "H1's outcome", "has_observation": "H2's outcome",
          "multi_statement_and_changed_after_error": "H3's outcomes"},
  "models": ["difference of mean density between action kinds, bootstrapped on conversation_id",
             "difference of the share of turns answered by an observation, bootstrapped on conversation_id",
             "shares with intervals for composition and for post-error change, plus the density difference within "
             "multi-statement blocks only"],
  "thresholds": {"support": "|difference| >= 0.15 of the pooled standard deviation, or a share gap >= 0.15, with CI "
                            "excluding 0 and p_holm < 0.05",
                 "partial": "CI excludes 0 below the floor", "null": "CI includes 0"},
  "family": "three",
  "gate_scope": "design",
  "kill_gate": ("G1 froze >= 200 readable code-act conversations and EXP-0215 measured 4,000; G2 froze >= 200 with "
                "an executed block and measured 3,990; G3, which scopes H3, froze >= 100 conversations reporting an "
                "error and measured 567, with 797 showing a changed block after one; G4 froze >= 100 multi-statement "
                "blocks and measured 3,171. What this corpus does not carry is an outcome label, so every arm is a "
                "share or a density, never a success claim."),
  "strata": ["source (codeact or general split)", "block statement-count band"],
  "tables": ["table1_sample_and_structure.csv", "table2_action_density_census.csv", "table3_main_models.csv",
             "table4_strata_by_source.csv", "table5_robustness_inference.csv", "table6_baseline_comparison.csv",
             "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_action_kinds.pdf", "fig2_main_effect.pdf",
              "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"],
 },
 # ------------------------------------------------------------------ T189
 "T189": {
  "pkg": "P068_corrective_and_ritual_reflection",
  "title": "Corrective versus Ritual Reflection",
  "rq": "When a multimodal reasoner says it is reconsidering, does the next thought actually contain something "
        "different, and how often does it not?",
  "hypotheses": [
   "H1 reflection markers occur in a measurable share of <THOUGHT> transitions, reported with a cluster bootstrap on "
   "the conversation; the frozen floor is 200 scoreable marker transitions and EXP-0215 measured 267.",
   "H2 a thought following a reflection marker shares less of its content words with the previous thought than a "
   "thought following no marker does, reported as a difference of mean Jaccard with an interval.",
   "H3 the ritual share - marker transitions whose content barely changed (Jaccard >= 0.80) - is measured with an "
   "interval. [claim-limited by G7: the release records no correctness label, so nothing in this design may be read as "
   "the reflection having improved the answer.]"],
  "features": {"marker": "a reflection phrase in the <THOUGHT> block",
               "jaccard_before_after": "content-word overlap between consecutive thoughts",
               "ritual": "a marker transition with Jaccard >= 0.80",
               "operator": "the <OPERATOR> invoked after the thought"},
  "dvs": {"jaccard_before_after": "H2's outcome", "ritual_share": "H3's outcome"},
  "models": ["marker prevalence per conversation with a cluster bootstrap",
             "difference of mean Jaccard between marker and non-marker transitions, bootstrapped on conversation_id",
             "the ritual share with its interval, reported per operator"],
  "thresholds": {"support": "|difference of mean Jaccard| >= 0.15 with CI excluding 0; H3 is a share, so its floor is "
                            "read directly against 0.20",
                 "partial": "CI excludes 0 below the floor", "null": "CI includes 0"},
  "family": "three",
  "gate_scope": "design",
  "kill_gate": ("G5 froze >= 200 conversations with a <THOUGHT> block and measured 4,000; G6, which scopes H1, froze "
                ">= 200 scoreable marker transitions and measured 267. G7 fired: not one of the 4,000 conversations "
                "carries a correctness label, so H3 is reported as a measured share with its interval and the "
                "was-it-right question is left unanswered on the record (deviation W12-D01)."),
  "strata": ["operator invoked after the marker", "thought position in the conversation"],
  "tables": ["table1_sample_and_structure.csv", "table2_reflection_census.csv", "table3_main_models.csv",
             "table4_strata_by_operator.csv", "table5_robustness_inference.csv", "table6_baseline_comparison.csv",
             "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_reflection_examples.pdf", "fig2_main_effect.pdf",
              "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"],
 },
 # ------------------------------------------------------------------ T194
 "T194": {
  "pkg": "P069_case_based_reuse_of_historical_trajectories",
  "title": "Case-Based Reuse of Historical Trajectories",
  "rq": "When a task is similar to another task already attempted in the same repository, does the search differ - "
        "shorter, less repetitive, more often finished?",
  "hypotheses": [
   "H1 a measurable share of rollouts has another instance in the draw whose issue text reaches content-word Jaccard "
   "0.30. [claim-limited by G9: 200 of 20,000 reached that floor against a frozen 1,000, so this is reported as a "
   "prevalence with its floor stated, not as a case library.]",
   "H2 within instances attempted more than once, the similarity of two attempts' issue text is associated with the "
   "similarity of their command sequences, reported as a correlation with a cluster bootstrap on instance_id.",
   "H3 an attempt whose earlier sibling in the same repository was closer in text uses fewer steps and finishes more "
   "often. [claim-limited by G10: the release records no timestamp and no retrieved-case field, so whether a past "
   "case was actually drawn on is unobservable here.]"],
  "features": {"neighbour_similarity": "best content-word Jaccard to any other instance's issue text",
               "sibling_similarity": "Jaccard to the other attempt of the same instance",
               "command_sequence_similarity": "Jaccard over the ordered command digests of two attempts",
               "n_steps": "commanded steps in the rollout", "submitted": "the release's own label"},
  "dvs": {"neighbour_prevalence": "H1's outcome", "command_sequence_similarity": "H2's outcome",
          "n_steps": "H3's first outcome", "submitted": "H3's second outcome"},
  "models": ["prevalence of a neighbour at >= 0.30 with a cluster bootstrap on instance_id",
             "correlation of sibling text similarity with sibling command similarity, clustered on instance_id",
             "OLS on step count and logistic on finishing with the neighbour similarity, length and repository "
             "controls, clustered on instance_id"],
  "thresholds": {"support": "|beta| >= 0.15 or |r| >= 0.15 with CI excluding 0 and p_holm < 0.05",
                 "partial": "CI excludes 0 below the floor", "null": "CI includes 0",
                 "h1": "the floor is on the share itself (>= 5% of rollouts with a neighbour at 0.30)"},
  "family": "three",
  "gate_scope": "design",
  "kill_gate": ("G8 froze >= 300 instances attempted more than once and measured 1,775, so H2 has its pairs. G9 "
                "measured 200 rollouts of 20,000 with a neighbour instance at >= 0.30 against a frozen 1,000 and G10 "
                "measured no timestamp and no retrieved-case column on any of the 20,000 - both fire at H-scope, so "
                "H1 is a stated prevalence and H3's retrieval question is reported as unobservable rather than "
                "answered by proxy (deviation W12-D02)."),
  "strata": ["similarity band", "repository prefix"],
  "tables": ["table1_sample_and_structure.csv", "table2_neighbour_census.csv", "table3_main_models.csv",
             "table4_strata_by_similarity.csv", "table5_robustness_inference.csv", "table6_baseline_comparison.csv",
             "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_neighbour_pairs.pdf", "fig2_main_effect.pdf",
              "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"],
 },
 # ------------------------------------------------------------------ T036
 "T036": {
  "pkg": "P070_agent_trajectory_corpora_as_intelligence_sources",
  "title": "Agent Trajectory Corpora as Intelligence Sources: a Structural Aggregation",
  "rq": "Across the eight local corpora, what is actually recorded - units, sizes, labels, language - and which "
        "agentic information behaviour constructs can any of them support?",
  "hypotheses": [
   "H1 a countable share of the eight corpora expose an outcome or quality column, and that share - not a metaphor "
   "about data richness - is the ceiling on labelled evidence in this estate. [claim-limited by G12 to 3 of 8 "
   "against a frozen 4.]",
   "H2 the unit of observation differs across the eight by more than an order of magnitude, which is what makes any "
   "pooled statistic a described object rather than an estimated one.",
   "H3 the constructs this programme has tested - grounding, contradiction, repair, stopping, sourcing, budget - map "
   "onto the corpora unevenly, and the mapping is reported as measured availability, cell by cell."],
  "features": {"files": "parquet and jsonl shards found", "rows": "row counts in the first four files of each",
               "columns": "column names as the release spells them", "label_present": "an outcome or quality column",
               "construct_availability": "whether the fields a construct needs are present"},
  "dvs": {"no dependent variable": "T036 is a descriptive aggregation; nothing here is tested against a band"},
  "models": ["structure counts and label presence per corpus, with the estate's own experiment and package registries "
             "as the source of what has been tested where",
             "a construct-by-corpus availability matrix built from the frozen instruments of waves 1 to 12",
             "unit-of-observation comparison across the eight"],
  "thresholds": {"support": "not applicable - a descriptive aggregation carries no inferential threshold",
                 "partial": "not applicable", "null": "not applicable"},
  "family": "descriptive only",
  "gate_scope": "design",
  "kill_gate": ("G11 froze >= 6 of the eight corpora yielding a file count, a row count and a column list and measured "
                "8, so the aggregation stands. G12, which scopes H1, measured 3 labelled corpora against a floor of 4: "
                "the availability count is reported, and no claim about labelled evidence across the estate is "
                "strengthened beyond what the directories show."),
  "strata": ["corpus", "unit of observation"],
  "tables": ["table1_sample_and_structure.csv", "table2_inventory_census.csv", "table3_main_models.csv",
             "table4_strata_by_corpus.csv", "table5_robustness_inference.csv", "table6_baseline_comparison.csv",
             "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_corpus_inventory.pdf", "fig2_main_effect.pdf",
              "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"],
 },
}

# census key -> the name this freeze gives it, so EXP-0163 rewrites PREMISES from the artefact, not from a copy
PREMISE_MAP = {
 "codeact.rows_read": "codeact_rows_read", "codeact.rows_with_assistant_turns": "codeact_readable",
 "codeact.conversations_with_code": "codeact_with_code",
 "codeact.conversations_with_multi_statement_code": "codeact_multi_statement",
 "codeact.conversations_with_an_error_string": "codeact_with_error",
 "codeact.conversations_with_a_correction_cycle": "codeact_correction_cycles",
 "codeact.mean_statements_per_code_block": "codeact_statements_per_block",
 "codeact.mean_content_words_per_nl_character_x1000": "codeact_nl_density_per_1000",
 "codeact.distinct_sources": "codeact_sources",
 "mmat.lines_read": "mmat_lines_read", "mmat.conversations_with_thoughts": "mmat_with_thoughts",
 "mmat.mean_thought_turns": "mmat_mean_thought_turns", "mmat.reflection_markers_total": "mmat_markers",
 "mmat.marker_pairs_scored": "mmat_marker_pairs", "mmat.pairs_that_shifted_content": "mmat_pairs_shifted",
 "mmat.mean_jaccard_after_marker": "mmat_mean_jaccard_after_marker",
 "mmat.correctness_label_present": "mmat_correctness_label", "mmat.distinct_operators": "mmat_operators",
 "swe.rollouts": "swe_rollouts", "swe.instances": "swe_instances",
 "swe.instances_with_2plus_rollouts": "swe_instances_with_repeats",
 "swe.mean_best_neighbour_similarity": "swe_mean_best_neighbour_similarity",
 "swe.rollouts_with_a_neighbour_at_0p3": "swe_rollouts_with_neighbour",
 "swe.rollouts_with_a_timestamp_column": "swe_rollouts_with_timestamp",
 "swe.rollouts_with_a_case_library_column": "swe_rollouts_with_case_library",
}

PREMISES = {
    "census": "EXP-0215 (EXP0215_wave12_premise_census_20260924T230739.json)",
    "transcribed_by": "02_shared_code/registry/refresh_wave_premises.py (EXP-0163); no number in this block is typed by hand",
    "measured": {
        "codeact_rows_read": 4000,
        "codeact_readable": 4000,
        "codeact_with_code": 3990,
        "codeact_multi_statement": 3171,
        "codeact_with_error": 567,
        "codeact_correction_cycles": 797,
        "codeact_statements_per_block": 6.31,
        "codeact_nl_density_per_1000": 110.809,
        "codeact_sources": 2,
        "mmat_lines_read": 4000,
        "mmat_with_thoughts": 4000,
        "mmat_mean_thought_turns": 2.93,
        "mmat_markers": 275,
        "mmat_marker_pairs": 267,
        "mmat_pairs_shifted": 267,
        "mmat_mean_jaccard_after_marker": 0.0324,
        "mmat_correctness_label": False,
        "mmat_operators": 4,
        "swe_rollouts": 20000,
        "swe_instances": 1784,
        "swe_instances_with_repeats": 1775,
        "swe_mean_best_neighbour_similarity": 0.2483,
        "swe_rollouts_with_neighbour": 200,
        "swe_rollouts_with_timestamp": 0,
        "swe_rollouts_with_case_library": 0,
    },
    "gates": {
          "G10_swe_records_order_or_a_library": {'blocks': ['T194'], 'fires': True, 'measured': 0, 'rule': ">= 1 rollout carrying a timestamp or an explicit retrieved-case field, without which 'reuse of historical trajectories' cannot be observed as retrieval", 'scope': 'H3', 'threshold': 1},
          "G11_eight_corpora_inventoried": {'blocks': ['T036'], 'fires': False, 'measured': 8, 'rule': ">= 6 of the eight local corpora yield a file count, a row count and a column list, which is all T036's aggregation can be built from", 'scope': 'design', 'threshold': 6},
          "G12_eight_corpus_label_coverage": {'blocks': ['T036'], 'fires': True, 'measured': 3, 'rule': '>= 4 corpora expose an outcome or quality column among their first columns, the ceiling on how many of the eight can carry a labelled claim', 'scope': 'H1', 'threshold': 4},
          "G1_codeact_readable": {'blocks': ['T184'], 'fires': False, 'measured': 4000, 'rule': '>= 200 code-act conversations with at least one assistant turn, the units T184 types', 'scope': 'design', 'threshold': 200},
          "G2_codeact_has_code_actions": {'blocks': ['T184'], 'fires': False, 'measured': 3990, 'rule': '>= 200 conversations containing an executed code block, without which there is no code action to compare with a natural-language one', 'scope': 'design', 'threshold': 200},
          "G3_codeact_has_errors_to_recover_from": {'blocks': ['T184'], 'fires': False, 'measured': 567, 'rule': '>= 100 conversations whose text reports an error, the correctability arm', 'scope': 'H3', 'threshold': 100},
          "G4_codeact_has_composition": {'blocks': ['T184'], 'fires': False, 'measured': 3171, 'rule': ">= 100 conversations with a multi-statement code block, T184's composition arm", 'scope': 'H3', 'threshold': 100},
          "G5_mmat_readable": {'blocks': ['T189'], 'fires': False, 'measured': 4000, 'rule': '>= 200 MMAT conversations with at least one <THOUGHT> block', 'scope': 'design', 'threshold': 200},
          "G6_mmat_has_reflection_markers": {'blocks': ['T189'], 'fires': False, 'measured': 267, 'rule': ">= 200 reflection markers followed by a scoreable content pair, below which 'ritual versus corrective' has no events to split", 'scope': 'H1', 'threshold': 200},
          "G7_mmat_no_correctness_label": {'blocks': ['T189'], 'fires': True, 'measured': 0, 'rule': 'a correctness label must be present for any claim about a reflection making the answer right; the release carries none, so this gate fires by design and the wave reports change instead of correctness', 'scope': 'H3', 'threshold': 1},
          "G8_swe_has_prior_attempts": {'blocks': ['T194'], 'fires': False, 'measured': 1775, 'rule': ">= 300 instances attempted more than once in the draw, which is T194's reuse material", 'scope': 'design', 'threshold': 300},
          "G9_swe_has_neighbours": {'blocks': ['T194'], 'fires': True, 'measured': 200, 'rule': '>= 1,000 rollouts whose issue text has a neighbour instance at Jaccard >= 0.3, the similar-past-case premise', 'scope': 'H1', 'threshold': 1000},
      },
    "verdict": {
          "blocked_gates": ['G7_mmat_no_correctness_label', 'G9_swe_has_neighbours', 'G10_swe_records_order_or_a_library', 'G12_eight_corpus_label_coverage'],
          "blocked_whole_design": [],
          "claim_limited": {'G10_swe_records_order_or_a_library': 'H3', 'G12_eight_corpus_label_coverage': 'H1', 'G7_mmat_no_correctness_label': 'H3', 'G9_swe_has_neighbours': 'H1'},
      },
    "note": "a fired gate is a result, not an obstacle: it stops exactly what its frozen sentence scopes",
    "runnable": list(RUNNABLE),
}    # filled verbatim from the census artefact - never edit these blocks by hand

FAILED_RUNS = [
 "EXP0215 first launch was a smoke run (200 code-act conversations, 120 MMAT lines, 400 SWE rollouts, "
 "results_raw/EXP0215_wave12_premise_census_20260924T230101.json) used to prove the action-kind, error, reflection and "
 "neighbour instruments and the gate wiring. Three gates fired there only because the draw was small - MMAT yielded 11 "
 "scoreable marker transitions against 267 at the frozen cap - so that generation is superseded and every cited value "
 "comes from the capped run, produced twice with byte-identical output.",
]

EXTRA_DEVIATIONS = [
 ("W12-D01", "MMAT-1M records no correctness label, so T189 answers change rather than improvement",
             "G7 was written to fire when no conversation carries a correctness field, and it fired: 0 of 4,000. The "
             "consequence is stated instead of worked around - H1 and H2 measure how often a reflection appears and "
             "whether the next thought contains something different (mean content-word Jaccard 0.032 after a marker), "
             "and H3's ritual share is reported as a share. No proxy for correctness was substituted: the final "
             "assistant turn is an answer, not a graded one, and calling it otherwise would be the model judgement "
             "the protocol excludes."),
 ("W12-D02", "The SWE-ZERO release records no timestamp and no retrieved-case field, so 'reuse' is measured as "
             "similarity and never as retrieval",
             "G10 measured 0 of 20,000 rollouts with any ordering or case-library column, and G9 measured 200 "
             "rollouts whose issue text reaches 0.30 similarity to another instance against a floor of 1,000. Both "
             "fire at H-scope, so T194's H1 is a stated prevalence with its floor and H3 is reported as unobservable: "
             "what remains estimable is whether attempts of the same instance resemble each other in text and in "
             "command sequence at once, which is a relation between records rather than a claim that an agent looked "
             "something up."),
 ("W12-D03", "The eight-corporus inventory counts labels, not richness",
             "G12 found 3 of the 8 corpora exposing an outcome or quality column, against a frozen 4, and T036's H1 "
             "therefore reports the count rather than a general claim about labelled agent data. The inventory is "
             "built from the directories and the releases' own column names - file counts, row counts of the first "
             "four shards each, and the columns as spelled - because a stronger statement would need a metadata "
             "source the estate does not have; the rights and provenance metadata question is P005's own subject and "
             "is not re-litigated here."),
 ("W12-D04", "One census gate value counted instances while its sentence named rollouts",
             "G9's key reads rollouts_with_a_neighbour_at_0p3 and the census filled it from a per-instance loop, so "
             "the cited 200 is instances, not rollouts. The frame recomputes the quantity both ways - rollouts whose "
             "instance has a neighbour at 0.30, and the instance count itself - prints both, and states the unit of "
             "each; the gate's outcome is unchanged because the floor it compares against (1,000) is exceeded by "
             "neither count. Nothing was re-graded after the unit was clarified."),
 ("W12-D05", "Two readings of 'a reflection was followed by' differ, and both are printed",
             "The census counted a marker in the later thought of a pair (267 scoreable transitions, mean Jaccard "
             "0.0324) and T189's H2 sentence asks about the thought after a marker, i.e. a marker in the earlier one "
             "(208 transitions). The design uses the definition its sentence states and reports the other count and "
             "the other mean beside it, so a reader can see the size of the definitional choice instead of having it "
             "made for them."),
 ("W12-D06", "The correction-cycle count differs between the census and the frame by design",
             "EXP-0215 asked whether the whole next message differed (797 conversations); T184's H3 sentence asks "
             "whether the executed block differed, which is the stricter question and gives 182. Both numbers are in "
             "the frame artefact with their definitions stated, and the cross-check no longer compares them as if "
             "they were one quantity."),
 ("W12-D07", "T194's H2 is untestable in the corpus, and no proxy was substituted",
             "Sibling attempts of one instance carry the same issue text, so the issue-similarity side of the "
             "correlation the sentence asks for has a single distinct value and the correlation is undefined. The "
             "row reports the distinct-value count and leaves the verdict at not_testable; comparing siblings' "
             "command sequences against each other without the text axis - or against other instances - would answer "
             "a different question than the one frozen."),
 ("W12-D08", "T036's table list was corrected to names the assembly can map, after its estimates existed",
             "The first table list named table2_corpus_inventory.csv and table3_construct_availability.csv, and the "
             "factory refused the package because no measured block feeds a name it does not know - the refusal that "
             "keeps a table from shipping as a header with no numbers. The two names became "
             "table2_inventory_census.csv (the descriptive-rates block, which is where the inventory is) and "
             "table3_main_models.csv (the three hypothesis rows). No hypothesis, threshold or estimand changed, and "
             "the freeze document on disk still shows the first pair of names because "
             "freeze_wave.py refuses to rewrite a freeze whose experiment is already registered; this entry is the "
             "record of the difference rather than a silent edit of the document."),
]
