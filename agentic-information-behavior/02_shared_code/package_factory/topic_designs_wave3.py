"""Wave 3: how tool descriptions are *organised*, and what that does to machine discovery.

Five frozen designs plus one topic that inherits a block already measured. Wave 3 stays on the description side of the
same encounter - the same 24,000 dev queries, the same 169,203 candidate rows, the same frozen BM25, the same
clustering unit (`query_id`) and the same effect bands - and adds the columns these designs need
(`exp_wave3_features.py`, EXP-0143). Two of the five are **intervention** designs: the catalogue is rewritten by a
rule, re-scored by the same ranker, and the change in the released selection's rank is the measurement. No model
generates any text in either arm; every rewrite is reversible by reading it.

The queue discipline in spec section 20 is what this file is: one bounded batch, frozen before any outcome of its
own is read, then run, then packaged one topic at a time.

| topic | package | question in one line |
|-------|---------|----------------------|
| T113  | P018    | does describing what a tool is *for* beat describing what it *does*? |
| T118  | P019    | does a hierarchical/faceted organisation of the catalogue help a machine find things? |
| T119  | P020    | does a name that matches its own description predict discoverability? |
| T120  | P021    | does rule-based synonym normalisation make retrieval more consistent? |
| T121  | -       | blocked: inherits EXP-0135's measured negation prevalence (2.9% < 5% gate) |
| T122  | P022    | does a description that *discriminates* its tool from its neighbours get found more? |
"""
from __future__ import annotations

SEED = 42
SAMPLE = dict(rows_per_config=8000, configs=("OSS", "Qwen3", "Kimi-K2"), bucket="dev",
              subset="single-turn-original", cluster_unit="query_id",
              rule="the same seeded dev sample EXP-0119 wrote and EXP-0136 re-read, so all three waves describe "
                   "byte-identical rows and a difference between waves cannot be a difference in the sample")
BANDS = dict(small=0.05, medium=0.15, large=0.30)      # effect-size bands used by every verdict here

DESIGNS = {
 # ------------------------------------------------------------------------------------------ T113 / P018
 "T113": dict(
    pkg="P018_function_vs_usecase_description",
    title="Function Descriptions versus Use-Case Descriptions in Machine Information Discovery",
    rq="RQ1 for a tool catalogue: does a description written as what the function *does* (its operation) or as what "
       "it is *for* (a use case) make the released selection easier for a machine to find?",
    hypotheses=[
        "H1 rewriting a description into a use-case frame (the task it serves, in the vocabulary of the request) "
        "changes the released selection's BM25 rank, and the direction is not known in advance",
        "H2 the effect of the use-case frame is larger where the original description is short, i.e. the frame adds "
        "what the text omitted rather than duplicating it",
        "H3 the function frame is not simply longer: at matched length, the two frames still differ"],
    features={
        "function_frame": "the description as released",
        "usecase_frame": "rule template: '<n> for <first clause of the description> given <parameter names>' with "
                         "the original text kept as the tail, so no content is invented and the arm is reversible",
        "matched_length_arm": "the shorter of the two texts padded by truncation of the longer to the same token count"},
    dvs={"rank_change": "gold item's BM25 rank under the frozen ranker, rewrite minus baseline",
         "reachable_at_1": "1 if the released selection is rank 1 after the rewrite"},
    models=["paired within-query contrast of rank and of rank-1 reachability, cluster bootstrap on query_id",
            "logistic on rank_change with a length-matched interaction, query-clustered SEs"],
    thresholds=dict(support="|beta| >= 0.15 or a paired rank shift >= 0.5 positions with CI excluding 0 and "
                            "p_holm < 0.05",
                    partial="CI excludes 0 below the floor", null="CI includes 0"),
    family=3,
    gate_scope="H1",   # what the frozen gate sentence below actually decides (transcribed, not chosen now)
    kill_gate="if a rewrite arm changes the token count by more than 40% on median, the length confound dominates "
              "and the frame contrast is reported as uninterpretable rather than as an effect",
    tables=["table1_sample_and_structure.csv", "table2_frame_rewrite_summary.csv", "table3_main_models.csv",
            "table4_strata_by_length.csv", "table5_robustness_inference.csv", "table6_baseline_comparison.csv",
            "table7_experiment_provenance.csv", "table_run_cost.csv"],
    figures=["fig0_framework.pdf", "fig1_underspec_examples.pdf", "fig2_main_effect.pdf",
             "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"]),

 # ------------------------------------------------------------------------------------------ T118 / P019
 "T118": dict(
    pkg="P019_hierarchy_facets_flat_lists",
    title="Hierarchy, Facets and Flat Lists in Machine Information Discovery",
    rq="RQ1: a tool catalogue is organised implicitly by server prefixes and name segments; does exposing that "
       "structure (hierarchical path, facet set) to the retriever change whether the released selection is found?",
    hypotheses=[
        "H1 a candidate's *hierarchical depth* (segments in its name path) is associated with being the released "
        "selection, independently of lexical match",
        "H2 adding the server path and the name segments as separate weighted fields changes reachability at rank 1 "
        "relative to the flat concatenation the baseline uses",
        "H3 facet overlap between the query and the candidate's path predicts which candidates a lexical ranker "
        "prefers, over and above whole-text overlap"],
    features={
        "hier_depth": "count of '-' separated segments in the entry name",
        "path_facets": "the set name segments plus the server slug the row carries",
        "facet_overlap": "share of the candidate's facets present in the query (identifier-aware tokeniser)"},
    dvs={"gold": "membership in the release's selection", "reachable_at_1": "rank 1 under the frozen BM25"},
    models=["candidate-level logistic, query-clustered SEs, controlling bm25_z and dense_z",
            "field-weighting intervention: score the same catalogue with path and segments as separate fields, and "
            "compare rank-1 reachability within query"],
    thresholds=dict(support="|beta| >= 0.15 with CI excluding 0 and p_holm < 0.05, or a paired reachability "
                            "difference with CI excluding 0 at or above 0.05",
                    partial="CI excludes 0 below the floor", null="CI includes 0"),
    family=3,
    gate_scope="design",   # what the frozen gate sentence below actually decides (transcribed, not chosen now)
    kill_gate="if fewer than 20% of entries have a name with more than one segment, there is no hierarchy to "
              "expose and the design is reported as not estimable on this catalogue",
    tables=["table1_sample_and_structure.csv", "table2_hierarchy_distribution.csv", "table3_main_models.csv",
            "table4_strata_by_depth.csv", "table5_robustness_inference.csv", "table6_baseline_comparison.csv",
            "table7_experiment_provenance.csv", "table_run_cost.csv"],
    figures=["fig0_framework.pdf", "fig1_underspec_examples.pdf", "fig2_main_effect.pdf",
             "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"]),

 # ------------------------------------------------------------------------------------------ T119 / P020
 "T119": dict(
    pkg="P020_name_description_congruence",
    title="Name-Description Congruence in Tool Metadata and Its Effect on Discovery",
    rq="RQ1: when a tool's name says what its description says, does a machine find it more reliably - and is "
       "congruence doing work of its own, or just re-measuring how much text there is?",
    hypotheses=[
        "H1 congruence between an entry name and its own description (shared identifier tokens, and the predicate "
        "the name asserts being present in the description) is positively associated with being the released "
        "selection",
        "H2 the association survives controls for description length, parameter count and whole-catalogue "
        "typicality, so it is not a size or prototypicality artefact",
        "H3 low congruence is *worse for discovery than a neutral name*: an entry whose name contradicts its "
        "description is less likely to be reached than one whose name is merely uninformative"],
    features={
        "name_desc_congruence": "1 - (unique name tokens not in the description) / (name tokens), identifier-aware",
        "name_predicate_in_desc": "the name's verb lemma and object noun both occur in the description",
        "contradiction": "name asserts a predicate family the description explicitly negates (frozen negation lexicon)"},
    dvs={"gold": "membership in the release's selection", "reachable_at_1": "rank 1 under the frozen BM25"},
    models=["candidate-level logistic with bm25_z, dense_z, desc_tokens, param_n and prototype centrality as "
            "controls, query-clustered SEs",
            "three-level congruence contrast (congruent / uninformative / contradictory) with within-query "
            "differences and a cluster bootstrap"],
    thresholds=dict(support="|beta| >= 0.15 with CI excluding 0 and p_holm < 0.05",
                    partial="CI excludes 0 below the floor", null="CI includes 0"),
    family=3,
    gate_scope="H3",   # what the frozen gate sentence below actually decides (transcribed, not chosen now)
    kill_gate="if the contradiction cell holds fewer than 200 candidate rows, H3 is reported as not testable rather "
              "than folded into the neutral cell",
    tables=["table1_sample_and_structure.csv", "table2_congruence_distribution.csv", "table3_main_models.csv",
            "table4_strata_by_length.csv", "table5_robustness_inference.csv", "table6_baseline_comparison.csv",
            "table7_experiment_provenance.csv", "table_run_cost.csv"],
    figures=["fig0_framework.pdf", "fig1_underspec_examples.pdf", "fig2_main_effect.pdf",
             "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"]),

 # ------------------------------------------------------------------------------------------ T120 / P021
 "T120": dict(
    pkg="P021_synonym_normalisation_consistency",
    title="Does Synonym Normalisation Improve the Consistency of Machine Retrieval?",
    rq="RQ1: vocabulary control is a classical answer to the synonym problem. Applied by rule to a tool catalogue, "
       "does mapping synonymous verbs and objects to one canonical form make which tool is found more consistent?",
    hypotheses=[
        "H1 canonicalising the catalogue's description text (rule-based synonym map, applied to the candidate side) "
        "changes the released selection's rank-1 reachability relative to the unnormalised baseline",
        "H2 normalisation reduces *within-family disagreement*: the spread of ranks across candidate rows that share "
        "a verb lemma and object noun falls",
        "H3 the benefit is concentrated where the query and the description use different vocabulary for the same "
        "act, and is absent where they already match"],
    features={
        "normalised_text": "description with the frozen SYN_MAP applied to verb and object lemmas (a checked-in "
                           "table, not a model); the arm is reversible by reading the map",
        "vocab_mismatch": "query contains a mapped synonym whose canonical form appears in the candidate, or the "
                          "converse"},
    dvs={"reachable_at_1": "rank 1 of the released selection under the frozen BM25, baseline vs normalised",
         "within_family_rank_spread": "interquartile range of ranks inside a (verb lemma, object noun) family"},
    models=["paired within-query contrast with a cluster bootstrap on query_id",
            "logistic on the rank-1 change with the mismatch indicator and its interaction with the arm"],
    thresholds=dict(support="a paired reachability change with CI excluding 0 and |change| >= 0.05, and a reduction "
                            "in within-family spread with CI excluding 0",
                    partial="CI excludes 0 below the floor", null="CI includes 0"),
    family=3,
    gate_scope="design",   # what the frozen gate sentence below actually decides (transcribed, not chosen now)
    kill_gate="if the synonym map covers under 10% of candidate rows on median, the intervention touches too little "
              "of the catalogue to carry a claim and the design is reported as a coverage measurement",
    tables=["table1_sample_and_structure.csv", "table2_synonym_coverage.csv", "table3_main_models.csv",
            "table4_strata_by_mismatch.csv", "table5_robustness_inference.csv", "table6_baseline_comparison.csv",
            "table7_experiment_provenance.csv", "table_run_cost.csv"],
    figures=["fig0_framework.pdf", "fig1_underspec_examples.pdf", "fig2_main_effect.pdf",
             "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"]),

 # ------------------------------------------------------------------------------------------ T122 / P022
 "T122": dict(
    pkg="P022_discriminability_and_discoverability",
    title="Description Discriminability and Discoverability of Information Resources",
    rq="RQ1: metadata quality is usually scored as completeness. The functional question is different - does this "
       "description tell its tool apart from *its own neighbours*? - and this design measures that directly.",
    hypotheses=[
        "H1 a description's *discriminability* (how far it sits from the other descriptions of its own catalogue, in "
        "lexical and distributional space) is positively associated with the released selection being reachable",
        "H2 discriminability beats the completeness-style predictors of the same corpus (parameter count, "
        "enumeration share, verb coverage) in incremental AUROC for reachability",
        "H3 the association is strongest in large catalogues, where many candidates share the query's words"],
    features={
        "discrim_lexical": "mean IDF-weighted dissimilarity of the description to the other descriptions of its "
                           "catalogue",
        "discrim_dense": "1 - mean cosine to the other descriptions of its catalogue (encoder cache, unchanged)",
        "completeness_set": "gold_param_n, gold_enum_share, gold_verb_coverage as the completeness-style comparators"},
    dvs={"reachable_at_1": "1 - fail_at_1 for the released selection, query level"},
    models=["query-level logistic with the controls the freeze keeps, plus a nested AUROC ladder (completeness set "
            "-> + discriminability) with a cluster bootstrap",
            "catalogue-size stratification at the median"],
    thresholds=dict(support="delta AUROC over the completeness set >= 0.02 with CI excluding 0 and p_holm < 0.05",
                    partial="CI excludes 0 below the floor", null="CI includes 0"),
    family=3,
    gate_scope="rows",   # what the frozen gate sentence below actually decides (transcribed, not chosen now)
    kill_gate="if a catalogue has fewer than 3 candidates for over half the queries, neighbour dissimilarity is not "
              "estimable for those rows and they are excluded and counted, not scored as zero dissimilarity",
    tables=["table1_sample_and_structure.csv", "table2_discriminability_distribution.csv", "table3_nested_models.csv",
            "table4_strata_by_catalogue_size.csv", "table5_robustness_inference.csv",
            "table6_baseline_comparison.csv", "table7_experiment_provenance.csv", "table_run_cost.csv"],
    figures=["fig0_framework.pdf", "fig1_underspec_examples.pdf", "fig2_main_effect.pdf",
             "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"])}

COMMON = dict(
    seed=SEED, sample=SAMPLE, bands=BANDS,
    substrate="Toucan-1.5M dev split, 24,000 single-turn-original queries and their released selections, joined to "
              "the tool catalogue by the frozen M2/M4 rule",
    instruments="the frozen BM25 and identifier-aware tokeniser from P001, the local all-MiniLM-L6-v2 cache from "
                "EXP-0120 as the only pretrained component, and rule-based extractors; no judge and no API",
    notes="wave 3 asks about the *organisation of the catalogue text*, so two of its designs are interventions on "
          "that text and are evaluated by the same ranker the release itself was scored with")

# Premise census results are filled in by `probe_wave3_premises.py` (EXP-0142) *before* any outcome is read, and the
# numbers below are what that run measured - not what the designs hoped for.
# The premise census results, written in after EXP-0142 ran and before any wave-3 outcome existed. A design
# whose own gate fired is recorded with the scope its frozen sentence gives that gate.
PREMISES = {'census': 'EXP-0142 (EXP0142_wave3_premise_census_20260924T072417.json)', 'measured': {'T113_median_abs_token_change_of_usecase_rewrite_pct': 0.6667, 'T118_median_name_segments': 1.0, 'T118_share_of_entries_with_more_than_one_segment': 0.1694, 'T119_candidate_rows_with_name_asserting_a_family_the_description_negates': 0, 'T120_share_of_queries_with_any_description_the_synonym_map_touches': 0.776, 'T121_negation_share_of_candidate_descriptions': 0.029, 'T122_median_catalogue_size': 3.0, 'T122_share_of_queries_with_fewer_than_three_candidates': 0.4507, 'rows_census_actual': 4000}, 'gates': {'T113_rewrite_length_within_tolerance': False, 'T118_hierarchy_exists': False, 'T119_contradiction_cell_testable': False, 'T120_synonym_map_coverage_enough': True, 'T122_neighbours_estimable': True}, 'verdict': {'blocked_gates': ['T118_hierarchy_exists'], 'blocked_whole_design': ['T118'], 'claim_limited': {'T113_rewrite_length_within_tolerance': 'H1', 'T119_contradiction_cell_testable': 'H3'}, 'note': 'a fired gate is a result, not an obstacle: it stops exactly what its frozen sentence says it stops (the whole design, one named hypothesis, or a set of rows to exclude and count) and nothing is renegotiated after an estimate exists', 'runnable': ['T113', 'T119', 'T120', 'T122']}}


EXP_OF = {"T113": "EXP-0145", "T119": "EXP-0146", "T120": "EXP-0147", "T122": "EXP-0148"}
MATRIX = "results_raw/EXP0143_wave3_description_matrix_*.json"
BATTERY = "results_raw/EXP0149_wave3_battery_0149_*.json"
RUNNABLE = ("T113", "T119", "T120", "T122")     # T118 stopped by its own gate at EXP-0142

# ------------------------------------------------------------------ wave-level constants for the package builder
FEATURE_EXP = "EXP-0143"
PREMISE_EXP = "EXP-0142"
BATTERY_EXP = "EXP-0149"
ENCODER_EXP = "EXP-0120/EXP-0125"
MATRIX_GLOB = MATRIX
BATTERY_GLOB = "results_raw/EXP0149_wave3_battery_0149_*.json"
PREMISE_GLOB = "results_raw/EXP0142_wave3_premise_census_*.json"
ENCODER_GLOB = "results_raw/EXP0120_wave1_encoder_run_*.json"
DESIGNS_MODULE = "topic_designs_wave3"
CLEAN_ROOM_ONLY_FLAG = "--only"
STAGE_RX = "wave3_main"
PROBE_SCRIPT = "probe_wave3_premises.py"
MATRIX_SCRIPT = "exp_wave3_features.py"
BATTERY_SCRIPT = "exp_wave3_battery.py"
ENCODE_SCRIPT = "encode_wave1_texts.py"
SCRIPT_OF = {t: "exp_wave3_designs.py" for t in RUNNABLE}
MAIN_SCRIPT_OF = {t: ("exp_wave3_designs.py", e) for t, e in EXP_OF.items()}
DENSE_SUPERSESSION_NOTE = "(EXP-0120/EXP-0125, the cache this wave re-reads)"
FAILED_RUNS = [
    "EXP0142_run_console.log / results_raw/EXP0142_wave3_premise_census_20260924T071121.json and "
    "...T072342.json (two superseded census generations): the first treated every unmet gate as a whole-design "
    "block, although each gate's own frozen sentence scopes it, and the second still listed T118 as runnable "
    "because the blocked set held gate labels while the runnable test compared topic ids.",
    "EXP0143_run_console.log / results_raw/EXP0143_wave3_description_matrix_20260924T075351.json: the "
    "name/description congruence column was computed against text that already contains the name, so it printed a "
    "tautological mean of 1.000, and the dense encoder cache was never loaded, so every dense column reported "
    "non_null=0 and coverage 0.0. The kept generation measures 0.4571 congruence on description tokens and 0.8755 "
    "dense neighbour coverage over 148143 rows.",
    "EXP0145_run_console.log (three crashed design processes, 08:11-08:15): the merges that built the query and "
    "candidate frames renamed colliding columns with pandas suffixes, so the designs raised KeyError on "
    "'gold_desc_tokens', 'desc_tokens', 'fail_at_1' and 'len_tok_z' after their bootstraps had already run. Each "
    "crash left a partial generation of artefacts on disk; every one of them is in the programme ledger.",
    "EXP0145_run_console.log (a run whose argv said `--only EXP-0148` but executed all four designs): the flag was "
    "declared and not honoured, which is why the kept EXP-0145/0146/0147 artefacts carry an invocation naming a "
    "different design. The filter now aborts on an unknown id and restricts the loop.",
    "EXP0148_wave3_design_0148_20260924T081554.json: the Holm family carried p=1.0 for H1 and H3 and p=0.54 for H2 "
    "because the cluster-bootstrap p for the interaction contrast had not been wired in, and the pre-registered "
    "reachability strata were absent. With the real clustered p the frozen H3 conjunct evaluates supported rather "
    "than partial, so this generation is superseded as an instrument defect, not a re-cut of the same result.",
    "EXP0149_run_console.log (first battery launch): died at import with a SyntaxError because a blind string "
    "replace rewrote a `def` line as `def F3.entry_tokens`. Its console log was overwritten by the relaunch that "
    "reused the filename, so this entry is recorded without a log artefact - the log-per-run-name rule in "
    "reproduce.sh is the correction.",
    "EXP0149 (second launch, kept artefact 20260924T090032.json): T113's E04 ablation returned zero rows because "
    "the battery's frame for that design carried only the single frozen regressor, so leave-one-covariate-out had "
    "no complement to drop. The design's own H2 moderation term is now rebuilt in the frame and the step "
    "re-executed; the printed summary also read `E17 arms: []` for a block stored under a different key, which is "
    "a log-reader defect fixed in the same commit.",
    "Package build (this wave, first assembly): figures fig4_robustness, fig5_headline_result_by_config and "
    "fig6_corpus_data_structure shipped as byte-identical copies of the robustness panel in every wave package "
    "built so far, because the figure dispatcher fell through to its default branch for any name it did not "
    "recognise. fig5 is now drawn from the battery's measured per-config block and fig6 from the package's "
    "structure table, and an unrecognised role aborts the build.",
]


# T121 asks whether machine-oriented organisation needs *negative applicability* metadata. That is the same
# construct T112 was stopped on, and the measurement already exists: EXP-0135 found negation markers in 2.9% of
# candidate descriptions against a 5% identifiability gate. Re-measuring the same column to reach the same verdict
# would spend a census for a sentence already evidenced, so the block is inherited and the prior artefact is cited.
INHERITED_BLOCKS = {
    "T121": {"package": "", "exp": "EXP-0135",
             "measured": {"negation_marker_share_of_candidates": 0.029, "gate": 0.05,
                          "source": "EXP-0135 (wave-2 premise census), the same column on the same corpus"},
             "why": "negative applicability metadata is by definition language about where a tool does not apply; "
                    "with negation in 2.9% of descriptions the construct has no identifiable variation to measure"}}


EXTRA_DEVIATIONS = [
 ("W3-D11", "Two bootstrap rows were printed `null` when their interval excludes zero; the rule is now applied as frozen",
  "The round-2 verification pass re-derived every verdict from the numbers shipped beside it and found EXP-0145 H3 "
  "(`usecase_matched_minus_baseline_hit1`, difference -0.0226, CI [-0.0272, -0.0181]) and EXP-0147 H1 "
  "(`synonym_minus_baseline_hit1`, difference -0.0031, CI [-0.005, -0.0013]) labelled `null`, which this programme's "
  "frozen vocabulary reserves for an interval that covers zero. Both hypotheses are written as \"the two arms "
  "differ\" / \"changes the reachability\" with no predicted side, so the interval's exclusion of zero is the "
  "evidence; the expression that assigned the verdict tested `ci[0] > 0`, which reads an any-sided claim as a "
  "positive-sided one and also turns a missing bound into zero. The three affected rows (T120 H2 as well) now go "
  "through `wave_lib.magnitude_verdict`, which implements the frozen three-way rule for a direction-free "
  "hypothesis: supported needs the design's own floor (0.05 for T120 H1, 0.02 for T122 H2) with the corrected p "
  "under 0.05, partial is an interval that excludes zero below the floor, null is an interval that covers it, and a "
  "row whose interval was never computed is reported `not_estimable_*` rather than `null`. No floor, band, seed or "
  "sample was changed; T113 H3 is now capped at `partial` because its frozen threshold sentence names a floor for a "
  "coefficient and a rank shift but not for a matched-length proportion difference, and a support claim cannot borrow "
  "a floor that was never frozen."),
]
