"""The wave-10 protocol freeze: kinds of linguistic uncertainty, and whether a corpus can be asked about them.

Six designs were screened for this wave on P001's routing release - T102 (lexical vs referential vs
missing-constraint ambiguity under controlled difficulty), T104 (recovering the implicit information need), T107
(semantic coverage of a decomposed need), T128 (reliability cues in a source's own language), T129 (attribution
framing and credibility bias), T154 (how task ambiguity changes the search). EXP-0203 measured the release twice with
identical output, and one design-scope gate fired:

* G2 froze `>= 0.90 of rows offer at least two candidates, since every claim here is about which of several documents
  a lexical match reaches for`. The release measured **0.8376** - 5,137 of its 31,642 dev instructions are matched
  against a single candidate, and the median catalogue holds 4. That stops T102, T107, T128, T129 and T154 as whole
  designs, all five of which define their outcome as a comparison inside one candidate set.

The consequence is stated plainly rather than worked around (deviation W10-D01): the estimable cell - rows with two
or more candidates - is 26,505 instructions, far above any count floor this wave would have needed, and it was
*not* substituted, because the frozen sentence speaks about the share of rows in the substrate, not about the size of
the surviving cell. What the measurement establishes on its own account is a property of this corpus that earlier
waves used without naming: a sixth of the routing release's items cannot express a preference between documents at
all, so a prevalence computed over all rows silently mixes 'nothing else was offered' with 'this one was chosen'.

T104 stands: its outcome is not a comparison inside a candidate set but whether the requirement an instruction leaves
unstated is present in what the agent's own search returned, and its own floors were met - the underspecification
index splits the sample (13,874 rows above its median 0.0304, 17,768 below), 24,568 rows carry a referential marker,
6,859 distinct prompt groups exist for the repeat structure, and every row carries a gold index and a ranker column.
"""
from __future__ import annotations

EXP_OF = {"T104": "EXP-0204"}
RUNNABLE = tuple(EXP_OF)
BLOCKED_BY_GATE = ("T102", "T107", "T128", "T129", "T154")
FEATURE_EXP = "EXP-0205"
PREMISE_EXP = "EXP-0203"
BATTERY_EXP = "EXP-0206"
ENCODER_EXP = ""
SEED = 42
BANDS = {"small": 0.05, "medium": 0.15, "large": 0.30}
MATRIX = "results_raw/EXP0205_wave10_requirement_matrix_*.json"
PREMISE_GLOB = "results_raw/EXP0203_wave10_premise_census_*.json"
BATTERY = "results_raw/EXP0206_wave10_battery_0206_*.json"
MATRIX_GLOB = MATRIX
BATTERY_GLOB = BATTERY
ENCODER_GLOB = ""
MATRIX_SCRIPT = "exp_wave10_features.py"
BATTERY_SCRIPT = "exp_wave10_battery.py"
PROBE_SCRIPT = "probe_wave10_premises.py"
DESIGNS_MODULE = "topic_designs_wave10"
STAGE_RX = "wave10_main"
CLEAN_ROOM_ONLY_FLAG = "--only"
CLEAN_ROOM_MODE = "full"
SCRIPT_OF = {t: "exp_wave10_designs.py" for t in RUNNABLE}
MAIN_SCRIPT_OF = {t: "exp_wave10_designs.py" for t in RUNNABLE}
SUBSTRATE_LABEL = ("P001 routing release, dev split only, all three configs (OSS, Qwen3, Kimi-K2): 31,642 rows, each "
                   "an agent instruction with the candidate tool catalogue it was offered and the frozen lexical "
                   "ranker's behaviour on it; 26,505 rows offer two or more candidates and 5,137 offer exactly one, "
                   "and the release records no agent choice (the outcome boundary wave 7 fixed applies here too)")
SAMPLE_FIELDS = ("corpus", "rows", "by_config", "catalogue_parse_share", "gold_index_recoverable_share",
                 "ranker_columns_present_share", "mean_candidates", "queries_with_2plus_candidates_share",
                 "underspec_median", "cluster_unit")
CONTRIBUTION_POPULATION = ("a corpus of agent instructions each paired with the tool catalogue offered and a frozen "
                           "lexical ranker's ordering of it, read with rule and lexical instruments, with no model, "
                           "no reranker and no recorded agent choice")

COMMON = {
    "seed": SEED,
    "bands": BANDS,
    "module": "topic_designs_wave10",
    "sample": {"traj_cap": 31642, "cluster_unit": "query_id",
              "unit_of_analysis": "the instruction, with its requirement set and the catalogue it was matched against",
              "rule": "every dev row of all three configs, no subsample, as in wave 7; the split filter is an "
                      "assertion inside wave_lib.load_routing, which raises if any test row is present",
              "excluded": "P001's test split, which load_routing reports dropping and never reads"},
    "instruments": ("a requirement is an executable clause of the instruction: an imperative verb plus its object, "
                    "or a constraint phrase, on wave 1's frozen constraint marker table; requirement coverage is the "
                    "share of those clauses whose content words appear in what the ranker surfaced; "
                    "underspecification, unresolved-reference and ellipsis indices are wave 1's, unchanged; a "
                    "cross-server content signature is wave 7's sorted content-word set of a description, and it is "
                    "used here only as a measurement of how much of this corpus cannot support a comparison"),
}

DESIGNS = {
 # ------------------------------------------------------------------ T104
 "T104": {
  "pkg": "P056_the_implicit_information_need",
  "title": "Can Agents Recover the Implicit Information Need?",
  "rq": "When an instruction leaves a requirement unstated but execution needs it, does the search the frozen ranker "
        "surfaces still cover that requirement, and does the amount left unstated predict the miss?",
  "hypotheses": [
   "H1 an instruction whose underspecification index is higher - more missing specification relative to its own "
   "constraints, unresolved references and ellipsis - has lower requirement coverage in the surfaced catalogue, "
   "holding the candidate count and the instruction length fixed.",
   "H2 the requirement that a clause leaves implicit is recoverable from the catalogue at all: the measured share of "
   "requirements whose content words appear in at least one surfaced candidate description, with a cluster bootstrap "
   "on query_id, is reported against the 0.30 floor this sentence fixes.",
   "H3 the association is not the constraint count speaking twice: with `constraint_total` in the model the "
   "underspecification index still separates, and with it removed the same specification holds, and a referential "
   "marker count (unresolved references and demonstratives) produces nothing once underspecification is in."],
  "features": {
   "underspec_index": "wave 1's equal-weight z-scored index; higher means less specified",
   "requirement_n": "count of executable clauses in the instruction (imperative verb plus object, or constraint "
                    "phrase)",
   "requirement_coverage": "share of those clauses whose content words appear in at least one candidate description",
   "constraint_total": "wave 1's constraint marker count",
   "referential_markers": "unresolved references plus strong demonstratives in the instruction"},
  "dvs": {"requirement_coverage": "H1's and H3's outcome", "coverage_share_with_floor": "H2's outcome"},
  "models": [
   "OLS on standardised requirement coverage with the underspecification index, log candidate count and log "
   "instruction length, clustered on query_id",
   "the measured coverage share with a cluster bootstrap on query_id, read against the frozen 0.30 floor",
   "the same model with constraint_total entered, and the referential-marker model without underspecification, so "
   "the two uncertainty kinds are separated rather than pooled"],
  "thresholds": {"support": "|beta| >= 0.15 with CI excluding 0 and p_holm < 0.05",
                 "partial": "CI excludes 0 below the floor", "null": "CI includes 0",
                 "h2": "the floor is on the measured share (>= 0.30 of requirements recoverable), not on a "
                       "coefficient, and the interval is read against it"},
  "family": "three",
  "gate_scope": "design",
  "kill_gate": ("G1, G9 and G10 froze that the rows parse, that a gold index and the ranker columns are present, and "
                "that the sample is large enough to cluster: EXP-0203 measured 1.0, 1.0, 1.0 and 31,642. G5's "
                "underspecification spread, which is this design's manipulated quantity, measured 13,874 rows above "
                "the median 0.0304 and 17,768 below it against a floor of 1,000 each, so both ends of the contrast "
                "exist. G2 - the comparable-set rule that stopped the other five designs - does not scope any "
                "sentence here, because H1 and H3 compare instructions with instructions rather than candidates with "
                "candidates, and H2 counts coverage over the whole surfaced catalogue of a row."),
  "strata": ["candidate-count quartile", "config"],
  "tables": ["table1_sample_and_structure.csv", "table2_requirement_census.csv", "table3_main_models.csv",
             "table4_strata_by_candidate_count.csv", "table5_robustness_inference.csv",
             "table6_baseline_comparison.csv", "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_requirement_examples.pdf", "fig2_main_effect.pdf",
              "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"],
 },
 # ------------------------------------------------------------------ T102
 "T102": {
  "pkg": "P057_three_kinds_of_linguistic_uncertainty",
  "title": "Lexical Ambiguity, Referential Ambiguity and Missing Constraints Have Divergent Effects",
  "rq": "Do three kinds of linguistic uncertainty in one instruction push the search apart in different directions "
        "once task difficulty is held fixed?",
  "hypotheses": [
   "H1 each kind - a content word pointing into two servers' descriptions, an unresolved reference or demonstrative, "
   "and a below-median constraint set - raises the miss rate at rank 1 by its own amount, holding candidate count "
   "and instruction length fixed.",
   "H2 the three effects differ in sign or size, which is the divergence the title claims: reported per kind with a "
   "cluster bootstrap rather than as one pooled uncertainty index.",
   "H3 the divergence survives a controlled difficulty comparison inside candidate-count quartiles."],
  "features": {"lexical_ambiguity": "count of instruction content words appearing in >= 2 servers' descriptions",
               "referential_ambiguity": "unresolved references plus strong demonstratives",
               "missing_constraints": "1 if constraint_total is below the sample median"},
  "dvs": {"fail_at_1": "H1 to H3's outcome"},
  "models": ["logistic on fail-at-1 with the three uncertainty kinds, candidate count and length, clustered on "
             "query_id", "each kind alone with the same controls, reported side by side",
             "the same comparison inside each candidate-count quartile"],
  "thresholds": {"support": "|beta| >= 0.15 with CI excluding 0 and p_holm < 0.05",
                 "partial": "CI excludes 0 below the floor", "null": "CI includes 0"},
  "family": "three",
  "gate_scope": "design",
  "kill_gate": ("G2 froze >= 0.90 of rows offering at least two candidates, because every outcome this design "
                "measures is a comparison inside a candidate set, and EXP-0203 measured 0.8376: 5,137 instructions "
                "were matched against exactly one candidate. The design is stopped by that sentence. The three "
                "instruments themselves were measured and are ample - 15,264 rows carry a lexically ambiguous word, "
                "24,568 a referential marker, and the underspecification index splits the sample - so what fails is "
                "the comparison substrate, not the constructs (deviation W10-D01)."),
  "strata": ["candidate-count quartile", "config"],
  "tables": ["table1_sample_and_structure.csv", "table2_uncertainty_census.csv", "table3_main_models.csv",
             "table4_strata_by_candidate_count.csv", "table5_robustness_inference.csv",
             "table6_baseline_comparison.csv", "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_uncertainty_examples.pdf", "fig2_main_effect.pdf",
              "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"],
 },
 # ------------------------------------------------------------------ T107
 "T107": {
  "pkg": "P058_need_decomposition_and_search_completeness",
  "title": "Semantic Coverage of Need Decomposition and the Completeness of Information Seeking",
  "rq": "When a task decomposes into several atomic requirements, does the search cover them all, and do the "
        "omissions predict the miss?",
  "hypotheses": [
   "H1 coverage - the share of a task's atomic requirements whose content words appear among the surfaced "
   "candidates - falls as the requirement count rises.",
   "H2 an instruction whose requirements are less fully covered misses its gold tool more often, with candidate "
   "count and length fixed.",
   "H3 coverage is not the inverse of length: with both in the model, coverage still separates."],
  "features": {"requirement_n": "atomic requirement count", "coverage": "share of requirements surfaced",
               "omitted_requirements": "requirement_n minus the covered count"},
  "dvs": {"coverage": "H1's outcome", "fail_at_1": "H2's and H3's outcome"},
  "models": ["OLS on coverage with requirement count and controls, clustered on query_id",
             "logistic on fail-at-1 with coverage plus controls", "coverage and length entered together"],
  "thresholds": {"support": "|beta| >= 0.15 with CI excluding 0 and p_holm < 0.05",
                 "partial": "CI excludes 0 below the floor", "null": "CI includes 0"},
  "family": "three",
  "gate_scope": "design",
  "kill_gate": ("G2's comparable-set rule also scopes this design, whose coverage denominator is the candidate set a "
                "row was offered: measured 0.8376 against 0.90. G8's decomposition floor - 11,288 rows with two or "
                "more subtask markers against a floor of 1,000 - passed, so the stopping is about the substrate's "
                "single-candidate sixth rather than about decomposable needs (deviation W10-D01)."),
  "strata": ["requirement-count band", "config"],
  "tables": ["table1_sample_and_structure.csv", "table2_coverage_census.csv", "table3_main_models.csv",
             "table4_strata_by_requirement_count.csv", "table5_robustness_inference.csv",
             "table6_baseline_comparison.csv", "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_decomposition_examples.pdf", "fig2_main_effect.pdf",
              "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"],
 },
 # ------------------------------------------------------------------ T128
 "T128": {
  "pkg": "P059_linguistic_cues_and_source_reliability",
  "title": "Can Agents Judge Source Reliability from Linguistic Cues?",
  "rq": "Holding content words fixed, does authority or evidential language in a candidate's own description move "
        "where the ranker puts it?",
  "hypotheses": [
   "H1 a candidate description carrying an authority marker ranks better than an otherwise comparable one that does "
   "not, with content-word count and candidate count fixed.",
   "H2 evidential language (a cited source, a documented reference) behaves differently from authority language, "
   "reported as two coefficients rather than one credibility index.",
   "H3 the effect is not length or term frequency: with description length and the number of question-matching words "
   "controlled, the marker terms remain."],
  "features": {"authority_marker": "count of the frozen authority list in the candidate description",
               "evidential_marker": "count of the frozen evidential list",
               "bm25_rank": "the frozen ranker's own position for that candidate"},
  "dvs": {"bm25_rank": "H1 to H3's outcome, a rank the release records"},
  "models": ["OLS on log rank with marker counts and description controls, clustered on query_id",
             "authority and evidential entered together", "the same model with length and overlap controlled"],
  "thresholds": {"support": "|beta| >= 0.15 with CI excluding 0 and p_holm < 0.05",
                 "partial": "CI excludes 0 below the floor", "null": "CI includes 0"},
  "family": "three",
  "gate_scope": "design",
  "kill_gate": ("Two of this design's own floors passed - credibility-bearing language is present in 10.65% of rows "
                "for authority and 25.55% for evidential markers against a 5% floor, and descriptions average 13.17 "
                "content words - but G2's comparable-set rule scopes the design as a whole, because 'better than an "
                "otherwise comparable one' is a statement about a choice between candidates, and the release measured "
                "0.8376 of rows with two or more against a frozen 0.90. Stopped (deviation W10-D01)."),
  "strata": ["candidate-count quartile", "config"],
  "tables": ["table1_sample_and_structure.csv", "table2_cue_census.csv", "table3_main_models.csv",
             "table4_strata_by_candidate_count.csv", "table5_robustness_inference.csv",
             "table6_baseline_comparison.csv", "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_cue_examples.pdf", "fig2_main_effect.pdf", "fig3_mechanism_by_band.pdf",
              "fig4_robustness.pdf"],
 },
 # ------------------------------------------------------------------ T129
 "T129": {
  "pkg": "P060_attribution_framing_and_credibility_bias",
  "title": "Does Attribution Language Create Unwarranted Credibility Bias?",
  "rq": "Where the same content is offered under different provenance labels, does the label move the ranking?",
  "hypotheses": [
   "H1 among candidates whose descriptions share a content-word set but sit under different servers, the one whose "
   "name or framing carries an authority marker ranks better.",
   "H2 the framing effect is bounded: reported with a cluster bootstrap on query_id, its size is compared against "
   "the 0.15 band the freeze names.",
   "H3 the contrast disappears when the marker is permuted within a signature group, which is the falsification arm "
   "for a pure label effect."],
  "features": {"cross_server_signature": "a content-word set shared by candidates owned by different servers",
               "authority_framing": "authority or attribution-framing marker present in the name or description",
               "rank_within_signature": "the ranker's position of a candidate among the members of its signature"},
  "dvs": {"rank_within_signature": "H1 to H3's outcome"},
  "models": ["paired comparison inside each signature group with a cluster bootstrap on query_id",
             "the same comparison with the marker permuted within the group",
             "the association with the number of servers sharing the content set"],
  "thresholds": {"support": "|beta| >= 0.15 with CI excluding 0 and p_holm < 0.05",
                 "partial": "CI excludes 0 below the floor", "null": "CI includes 0"},
  "family": "three",
  "gate_scope": "design",
  "kill_gate": ("G6 measured what this design needs and it passed with room - 1,845 content-word sets are shared by "
                "candidates under at least two different servers, covering 3,940 candidate slots, against a floor of "
                "200 - but G2's rule that every row must offer a comparison set is design-scope for T129 as well, "
                "and it measured 0.8376. The natural same-content-different-source material in this corpus is "
                "therefore recorded as measured structure rather than as a credibility test (deviation W10-D01)."),
  "strata": ["signature size band", "config"],
  "tables": ["table1_sample_and_structure.csv", "table2_signature_census.csv", "table3_main_models.csv",
             "table4_strata_by_signature_size.csv", "table5_robustness_inference.csv",
             "table6_baseline_comparison.csv", "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_signature_pairs.pdf", "fig2_main_effect.pdf",
              "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"],
 },
 # ------------------------------------------------------------------ T154
 "T154": {
  "pkg": "P061_task_language_ambiguity_and_search_shape",
  "title": "How Task-Language Ambiguity Changes Agentic Information Seeking",
  "rq": "Do ambiguous, underspecified and referentially incomplete instructions produce longer, more switchy "
        "searches, or just less accurate ones?",
  "hypotheses": [
   "H1 each ambiguity kind raises the miss rate at rank 1.",
   "H2 each kind raises the number of candidates the ranker had to pass over before the gold one, which is the "
   "closest observable to a longer search in a corpus that records no agent behaviour.",
   "H3 the two outcomes separate: an instruction can be missed at rank 1 without a long search and the reverse, and "
   "the association of each ambiguity kind with each outcome is reported apart."],
  "features": {"lexical_ambiguity": "as T102", "referential_ambiguity": "as T102",
               "underspecification": "wave 1's index", "candidates_before_gold": "bm25_best_rank minus 1"},
  "dvs": {"fail_at_1": "H1's outcome", "candidates_before_gold": "H2's outcome"},
  "models": ["logistic on fail-at-1 with the three kinds plus controls, clustered on query_id",
             "OLS on log candidates-before-gold with the same specification",
             "the two outcomes compared per ambiguity kind, with no pooling of the two"],
  "thresholds": {"support": "|beta| >= 0.15 with CI excluding 0 and p_holm < 0.05",
                 "partial": "CI excludes 0 below the floor", "null": "CI includes 0"},
  "family": "three",
  "gate_scope": "design",
  "kill_gate": ("G2 scopes this design too: H2's quantity is a position within a candidate set, and a sixth of rows "
                "have no set to be positioned in (0.8376 against 0.90). Stopped, with the instrument measurements "
                "recorded (deviation W10-D01)."),
  "strata": ["candidate-count quartile", "config"],
  "tables": ["table1_sample_and_structure.csv", "table2_search_shape_census.csv", "table3_main_models.csv",
             "table4_strata_by_candidate_count.csv", "table5_robustness_inference.csv",
             "table6_baseline_comparison.csv", "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_shape_examples.pdf", "fig2_main_effect.pdf",
              "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"],
 },
}

# census key (a dotted path into its `measured` block) -> the name this freeze gives it, so EXP-0163 can rewrite the
# PREMISES literal below from the artefact rather than from a hand-kept copy.
PREMISE_MAP = {
 "rows": "dev_rows", "catalogue_parse_share": "catalogue_parse_share",
 "gold_index_recoverable_share": "gold_index_recoverable_share",
 "ranker_columns_present_share": "ranker_columns_present_share",
 "mean_candidates": "mean_candidates", "candidates_total": "candidate_slots",
 "queries_with_2plus_candidates_share": "comparable_candidate_share",
 "underspec_median": "underspec_median", "queries_above_underspec_median": "rows_above_underspec_median",
 "queries_below_underspec_median": "rows_below_underspec_median",
 "queries_with_any_lexical_ambiguity": "rows_with_lexical_ambiguity",
 "queries_with_any_referential_marker": "rows_with_referential_marker",
 "queries_with_two_plus_subtask_markers": "rows_with_2plus_subtasks",
 "authority_marker_share_of_rows": "authority_marker_share",
 "evidential_marker_share_of_rows": "evidential_marker_share",
 "attribution_framing_share_of_rows": "attribution_framing_share",
 "mean_words_per_candidate_description": "mean_words_per_description",
 "signatures_spanning_2plus_servers": "cross_server_content_signatures",
 "candidate_slots_under_a_cross_server_signature": "slots_under_cross_server_signature",
 "prompt_groups": "distinct_prompt_groups", "hedge_mean": "hedge_mean",
 "path_like_share_of_queries": "path_like_share",
}

PREMISES = {
    "census": "EXP-0203 (EXP0203_wave10_premise_census_20260924T205722.json)",
    "transcribed_by": "02_shared_code/registry/refresh_wave_premises.py (EXP-0163); no number in this block is typed by hand",
    "measured": {
        "dev_rows": 31642,
        "catalogue_parse_share": 1.0,
        "gold_index_recoverable_share": 1.0,
        "ranker_columns_present_share": 1.0,
        "mean_candidates": 7.04,
        "candidate_slots": 222770,
        "comparable_candidate_share": 0.8376,
        "underspec_median": 0.0304,
        "rows_above_underspec_median": 13874,
        "rows_below_underspec_median": 17768,
        "rows_with_lexical_ambiguity": 15264,
        "rows_with_referential_marker": 24568,
        "rows_with_2plus_subtasks": 11288,
        "authority_marker_share": 0.1065,
        "evidential_marker_share": 0.2555,
        "attribution_framing_share": 0.1507,
        "mean_words_per_description": 13.17,
        "cross_server_content_signatures": 1845,
        "slots_under_cross_server_signature": 3940,
        "distinct_prompt_groups": 6859,
        "hedge_mean": 0.418,
        "path_like_share": 0.1694,
    },
    "gates": {
          "G10_cluster_count": {'blocks': ['T102', 'T104', 'T107', 'T128', 'T129', 'T154'], 'fires': False, 'measured': 31642, 'rule': '>= 5,000 dev rows in each config pooled and >= 10,000 overall, so a query-clustered interval exists', 'scope': 'design', 'threshold': 10000},
          "G11_descriptions_have_text": {'blocks': ['T128'], 'fires': False, 'measured': 13.17, 'rule': '>= 8 content words per candidate description on average, below which a marker prevalence or a content-word signature is measuring a label rather than a document', 'scope': 'H1', 'threshold': 8.0},
          "G12_prompt_groups_available": {'blocks': ['T104'], 'fires': False, 'measured': 6859, 'rule': '>= 500 distinct prompt_id groups, the repeat structure T104 needs to ask whether the same need is answered consistently across configs', 'scope': 'H2', 'threshold': 500},
          "G1_catalogues_and_rows_parseable": {'blocks': ['T102', 'T104', 'T107', 'T128', 'T129', 'T154'], 'fires': False, 'measured': 1.0, 'rule': '>= 0.95 of dev rows yield a readable catalogue and a gold index inside it', 'scope': 'design', 'threshold': 0.95},
          "G2_comparable_candidate_sets": {'blocks': ['T102', 'T107', 'T128', 'T129', 'T154'], 'fires': True, 'measured': 0.8376, 'rule': '>= 0.90 of rows offer at least two candidates, since every claim here is about which of several documents a lexical match reaches for', 'scope': 'design', 'threshold': 0.9},
          "G3_lexical_ambiguity_variation": {'blocks': ['T102', 'T154'], 'fires': False, 'measured': 15264, 'rule': ">= 1,000 queries contain at least one content word that points into two servers' descriptions, the lexical arm of T102 and T154", 'scope': 'H1', 'threshold': 1000},
          "G4_referential_ambiguity_variation": {'blocks': ['T102', 'T154'], 'fires': False, 'measured': 24568, 'rule': '>= 1,000 queries carry an unresolved reference or demonstrative, the referential arm', 'scope': 'H1', 'threshold': 1000},
          "G5_underspecification_spread": {'blocks': ['T102', 'T104'], 'fires': False, 'measured': 13874, 'rule': '>= 1,000 queries above and >= 1,000 below the median underspecification index, so the missing-constraint arm has both ends', 'scope': 'H1', 'threshold': 1000},
          "G6_cross_server_content_pairs": {'blocks': ['T129'], 'fires': False, 'measured': 1845, 'rule': '>= 200 candidate descriptions that share their content-word set with a description owned by a different server - the only same-content-different-source contrast this release offers (T129)', 'scope': 'design', 'threshold': 200},
          "G7_credibility_language_present": {'blocks': ['T128'], 'fires': False, 'measured': 0.2555, 'rule': ">= 0.05 of rows have a catalogue whose descriptions carry an authority or evidential marker, else T128's construct is absent from the corpus rather than uninformative", 'scope': 'H1', 'threshold': 0.05},
          "G8_decomposable_needs": {'blocks': ['T107'], 'fires': False, 'measured': 11288, 'rule': '>= 1,000 queries show two or more subtask markers (punctuation, bullets, multi-line), which is the decomposition T107 counts coverage of', 'scope': 'H1', 'threshold': 1000},
          "G9_outcome_columns_present": {'blocks': ['T102', 'T104', 'T107', 'T128', 'T129', 'T154'], 'fires': False, 'measured': 1.0, 'rule': ">= 0.95 of rows carry the frozen BM25 rank and margin - this corpus records a ranker's behaviour and no agent choice, as in wave 7", 'scope': 'design', 'threshold': 0.95},
      },
    "verdict": {
          "blocked_gates": ['G2_comparable_candidate_sets'],
          "blocked_whole_design": ['T102', 'T107', 'T128', 'T129', 'T154'],
          "claim_limited": {},
      },
    "note": "a fired gate is a result, not an obstacle: it stops exactly what its frozen sentence scopes",
    "runnable": list(RUNNABLE),
}    # filled verbatim from the census artefact - never edit these blocks by hand

FAILED_RUNS = [
 "EXP0203 first launch was a 300-row smoke run (results_raw/EXP0203_wave10_premise_census_20260924T205616.json), "
 "used to prove the lexical-ambiguity, referential, marker-list and cross-server-signature instruments and the gate "
 "wiring; the count floors fired there only because the draw was 300 rows, so that generation is superseded and the "
 "values cited are the whole-release ones, produced twice with byte-identical output.",
]

EXTRA_DEVIATIONS = [
 ("W10-D01", "A design-scope gate that conflated a share of rows with the size of the estimable cell stopped five "
             "designs",
             "G2 was written as `>= 0.90 of rows offer at least two candidates` and measured 0.8376, which stops "
             "T102, T107, T128, T129 and T154 - the five designs whose outcomes are comparisons inside a candidate "
             "set. The honest accounting is recorded here rather than hidden: 26,505 rows do offer a comparison, "
             "every construct the five designs measure is amply present (15,264 rows with a lexically ambiguous word, "
             "24,568 with a referential marker, 1,845 cross-server content signatures over 3,940 slots), and what the "
             "gate found missing is a sixth of the substrate. No threshold was lowered and no subset was substituted "
             "under the same sentence. What changes for later waves is the drafting rule the estate follows from "
             "this: a feasibility gate is written as an absolute floor on the cell the estimate will actually use, "
             "because a share-of-rows rule can stop a research programme over a property of the corpus that is itself "
             "the finding."),
 ("W10-D02", "One sixth of the routing release cannot express a preference between documents",
             "5,137 of 31,642 dev instructions are matched against exactly one candidate, and the median catalogue "
             "holds 4. This is a measured property of the substrate, reported in every wave-10 table so a reader can "
             "see what any share computed over all rows mixes: 'nothing else was offered' and 'this one was chosen' "
             "are the same row count in a prevalence but not the same fact."),
 ("W10-D03", "The outcome remains the frozen ranker's, not an agent's",
             "As wave 7 recorded (W7-D02), this release stores no agent selection: every dependent variable in this "
             "wave is BM25's rank, margin or fail-at-1 over the catalogue the row was offered. T104's title asks what "
             "an agent recovers; the freeze fixes the gap between that phrasing and the measurable quantity, and the "
             "package keeps the phrasing only where the sentence next to it says what was measured."),
]
