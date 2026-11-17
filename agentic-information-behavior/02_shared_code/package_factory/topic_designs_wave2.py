"""Frozen designs for wave 2 (T111, T112, T114, T115, T116, T117) - written before any outcome was read.

Wave 1 asked how the *instruction* language shapes the search. Wave 2 asks the same question of the other side of the
encounter: the language of the resource description the agent is shown. All six run on the metadata text the releases
already carry (tool/function name, description, parameter names), on the same dev-only rows, the same frozen BM25, the
same locally-run encoder, the same clustering unit (the query) and the same effect bands.

Nothing here has been computed yet. What is known at freeze time is the column inventory, EXP-0119's measured parse
guards and EXP-0135's premise census (which ran on structure only). If a census says a premise does not hold, the
affected design is amended in `PREMISES` below, with the measurement that forced it, before its first outcome.

    python 02_shared_code/package_factory/freeze_wave.py --designs topic_designs_wave2
"""
from __future__ import annotations

SEED = 42
SAMPLE = dict(rows_per_config=8000, configs=("OSS", "Qwen3", "Kimi-K2"), bucket="dev",
              rule="the same seeded dev sample EXP-0119 wrote, so wave 1 and wave 2 read byte-identical rows")
BANDS = dict(small=0.05, medium=0.15, large=0.30)

DESIGNS = {
 "T111": dict(
   pkg="P012_entity_action_constraint_fit",
   title="Entity, Action and Constraint Fit: Which Linguistic Component Drives Machine Source Selection",
   rq="RQ1 when an instruction and a candidate description can agree on an entity, on an action, or on a constraint, "
      "which kind of agreement actually moves the machine's selection?",
   hypotheses=[
     "H1 entity agreement raises the probability the candidate is selected at rank 1 more than token overlap does",
     "H2 action (predicate) agreement adds on top of entity agreement, and the two are separable",
     "H3 constraint agreement (numeric/format/scope/negation matched on both sides) has the smallest effect of the "
     "three and may be null",
   ],
   features={
     "entity_agree": "1 if any proper-noun-like or file-name span of the instruction occurs in the candidate's "
                     "name+description+parameters (case-folded)",
     "action_agree": "1 if any verb lemma of the frozen VERB_LEMMA groups occurs on both sides",
     "constraint_agree": "count of the six constraint families present on both sides (0-6)",
     "controls": "BM25 score, encoder cosine, catalogue size, description length, parameter count",
   },
   dvs={"selected_at_1": "the candidate occupies rank 1 under the frozen BM25 for that query",
        "gold": "membership in the release's selection"},
   models=["nested logistic models (overlap only, +entity, +action, +constraint) with query-clustered standard "
           "errors, likelihood-ratio tests and an AUROC ladder"],
   thresholds=dict(support="each component's incremental delta AUROC >= 0.02 with CI excluding 0 and p_holm < 0.05",
                   partial="CI excludes 0 below the AUROC floor", null="CI includes 0"),
   family=3,
   kill_gate="if entity, action and constraint agreement are mutually collinear (any VIF >= 10) the three components "
             "are not separable on this corpus and the design is reported as a single composite instead of three",
   tables=["table1_sample_and_structure.csv", "table2_agreement_prevalence.csv", "table3_nested_models.csv",
           "table4_auroc_ladder.csv", "table5_robustness_inference.csv", "table6_baseline_comparison.csv",
           "table7_experiment_provenance.csv", "table_run_cost.csv"],
   figures=["fig0_framework.pdf", "fig1_agreement_examples.pdf", "fig2_nested_gain.pdf",
            "fig3_separability_by_component.pdf", "fig4_robustness.pdf"]),

 "T112": dict(
   pkg="P013_negative_boundary_metadata",
   title="Does Negative Boundary Language in Resource Metadata Improve Machine Relevance Judgment",
   rq="RQ1 do descriptions that say what a tool does NOT do help a machine rank it correctly?",
   hypotheses=[
     "H1 candidates whose description carries negation or exclusion language are less often wrongly selected at "
     "rank 1 (a displacement-reducing effect)",
     "H2 the effect is larger for non-gold decoys than for gold items, because the boundary language is what keeps "
     "them out",
     "H3 the effect survives controlling for description length, which is the obvious confound",
   ],
   features={
     "negation_markers": "count of the NEG_WORDS family plus explicit exclusion phrases ('not for', 'cannot', "
                         "'does not', 'excludes', 'instead of') in the candidate description",
     "boundary_specificity": "1 if a negation marker is followed within six tokens by a named entity or file type",
     "length_control": "description tokens and parameter count",
   },
   dvs={"wrongly_first": "the candidate occupies rank 1 for a query whose released selection is a different tool",
        "displaced": "the query's released selection is displaced from rank 1 by any candidate"},
   models=["query-clustered logistic at candidate level with a gold x negation interaction; exact Fisher tests "
           "within strata; Holm over the declared family"],
   thresholds=dict(support="interaction or main effect |beta| >= 0.15 with CI excluding 0 and p_holm < 0.05",
                   partial="CI excludes 0 below the floor", null="CI includes 0"),
   family=3,
   kill_gate="if fewer than 5% of candidate descriptions carry any negation marker, boundary language is not "
             "identifiable on this corpus and the design is reported as unmeasurable rather than run thin",
   tables=["table1_sample_and_structure.csv", "table2_negation_prevalence.csv", "table3_main_models.csv",
           "table4_gold_by_negation_strata.csv", "table5_robustness_inference.csv",
           "table6_baseline_comparison.csv", "table7_experiment_provenance.csv", "table_run_cost.csv"],
   figures=["fig0_framework.pdf", "fig1_negation_examples.pdf", "fig2_displacement_by_negation.pdf",
            "fig3_gold_x_negation.pdf", "fig4_robustness.pdf"]),

 "T114": dict(
   pkg="P014_semantic_prototype_bias",
   title="Semantic Prototype Bias in Machine Relevance Assessment",
   rq="RQ1 does a candidate that resembles the catalogue's prototype get judged relevant even when the released "
      "selection is another tool?",
   hypotheses=[
     "H1 a candidate's prototype centrality (mean cosine to the other candidates of its catalogue) raises its chance "
     "of occupying rank 1 independently of its match to the query",
     "H2 low-prototype non-gold candidates are displaced downward relative to high-prototype ones",
     "H3 prototype centrality and query-specific relevance disagree on an identifiable set, and the disagreement is "
     "characterised rather than averaged",
   ],
   features={
     "prototype_centrality": "mean encoder cosine between this candidate and the other candidates of the same query",
     "query_fit": "encoder cosine to the query, and BM25",
     "disagreement_set": "candidates where prototype centrality and query fit rank them in opposite directions",
   },
   dvs={"rank1": "occupies rank 1 under the frozen BM25", "gold": "membership in the released selection"},
   models=["candidate-level logistic with query-clustered SEs; a paired within-query comparison on the disagreement "
           "set; a characterisation table of the disagreement pattern"],
   thresholds=dict(support="|beta| >= 0.15 with CI excluding 0 and p_holm < 0.05",
                   partial="CI excludes 0 below the floor", null="CI includes 0"),
   family=3,
   kill_gate="if the disagreement set holds fewer than 200 queries the pattern is reported descriptively and no "
             "directional claim is made",
   tables=["table1_sample_and_structure.csv", "table2_prototype_distribution.csv", "table3_main_models.csv",
           "table4_disagreement_census.csv", "table5_robustness_inference.csv", "table6_baseline_comparison.csv",
           "table7_experiment_provenance.csv", "table_run_cost.csv"],
   figures=["fig0_framework.pdf", "fig1_prototype_examples.pdf", "fig2_centricity_effect.pdf",
            "fig3_disagreement_map.pdf", "fig4_robustness.pdf"]),

 "T115": dict(
   pkg="P015_metadata_quality_model",
   title="A Description-Quality Model for AI-Agent Resources",
   rq="RQ1 which measurable properties of a tool description predict whether an agent can find the tool it needs, and "
      "do they compose into a usable quality score?",
   hypotheses=[
     "H1 length, entity specificity, parameter enumeration, verb coverage and boundary language each carry "
     "incremental information about whether a released selection is reachable by the frozen ranker",
     "H2 a composite of them beats description length alone on AUROC for reachability",
     "H3 the composite's weights are stable across the three configs, i.e. it is not one model's artefact",
   ],
   features={
     "length": "description tokens; parameter count",
     "specificity": "proper-noun-like and file-name spans per 100 tokens",
     "enumeration": "share of parameter names appearing in the description text",
     "verb_coverage": "share of VERB_LEMMA groups the description names",
     "boundary": "negation marker count (T112's feature, reused not redefined)",
   },
   dvs={"reachable": "the released selection is retrieved at rank 1 (and at rank 3) by the frozen BM25"},
   models=["logistic with the five blocks entered hierarchically; stratified ten-fold AUROC by query cluster; "
           "per-config refits for weight stability (Spearman of coefficient vectors)"],
   thresholds=dict(support="delta AUROC over length-only >= 0.02 with CI excluding 0, and per-config weight "
                           "correlation >= 0.6", partial="significant but below the floor", null="CI includes 0"),
   family=3,
   kill_gate="if any block has under 50% non-zero coverage across candidates it is dropped from the composite and "
             "the drop is recorded, so the score is not built on a column that is mostly empty",
   tables=["table1_sample_and_structure.csv", "table2_feature_coverage.csv", "table3_hierarchical_models.csv",
           "table4_auroc_comparison.csv", "table5_weight_stability.csv", "table6_baseline_comparison.csv",
           "table7_experiment_provenance.csv", "table_run_cost.csv"],
   figures=["fig0_framework.pdf", "fig1_feature_coverage.pdf", "fig2_auroc_ladder.pdf",
            "fig3_weight_stability.pdf", "fig4_robustness.pdf"]),

 "T116": dict(
   pkg="P016_description_granularity",
   title="Metadata Description Granularity and Machine Resource Discovery",
   rq="RQ1 is there an optimal granularity for a tool description, or does more detail monotonically help a machine "
      "find the tool?",
   hypotheses=[
     "H1 reachability improves with granularity up to a point and flattens, i.e. a concave dose-response",
     "H2 the turning point differs between short-list and long-list catalogues",
     "H3 over-granular descriptions help the wrong queries: the non-gold displacement rate rises with description "
     "length, which is the cost side of the same knob",
   ],
   features={
     "granularity": "description token count, clause count, and named-parameter count, entered separately as well "
                    "as their sum",
     "catalogue_size": "candidates in the query's list (short vs long by the median)",
   },
   dvs={"reachable_at_1": "released selection at rank 1", "displaces_others": "the candidate displaces a gold item "
        "from rank 1 for a query it is not the answer to"},
   models=["segmented/linear-by-decile models with query-clustered SEs; a per-catalogue-size stratum; a paired "
           "within-query contrast for the cost side"],
   thresholds=dict(support="a monotone-then-flat pattern with the low-vs-high decile contrast CI excluding 0 and "
                           "|beta| >= 0.15, and H3 in the opposite direction with the same requirements",
                   partial="CI excludes 0 below the floor", null="CI includes 0"),
   family=3,
   kill_gate="if the description-length distribution has under 3 distinct deciles of spread (i.e. descriptions are "
             "near-uniform) the dose-response is not estimable and is reported as such",
   tables=["table1_sample_and_structure.csv", "table2_granularity_distribution.csv", "table3_dose_response.csv",
           "table4_by_catalogue_size.csv", "table5_robustness_inference.csv", "table6_baseline_comparison.csv",
           "table7_experiment_provenance.csv", "table_run_cost.csv"],
   figures=["fig0_framework.pdf", "fig1_granularity_examples.pdf", "fig2_dose_response.pdf",
            "fig3_cost_side.pdf", "fig4_robustness.pdf"]),

 "T117": dict(
   pkg="P017_noun_verb_centring",
   title="Noun-Centred or Verb-Centred: An Agent-Oriented Classification of Tool Descriptions",
   rq="RQ1 do descriptions organised around what a tool acts on (noun-centred) or around what it does (verb-centred) "
      "fit different kinds of instructions, and does the mismatch cost retrieval?",
   hypotheses=[
     "H1 instruction centring and description centring interact: a verb-centred instruction finds a verb-centred "
     "description better than a noun-centred one, and symmetrically",
     "H2 the interaction survives total token overlap, so it is a structural effect and not a vocabulary effect",
     "H3 the classification is stable under a second, independently written centring rule (agreement reported)",
   ],
   features={
     "centring": "ratio of action-lemma tokens to entity/object tokens in a text, binned into noun-centred, balanced "
                 "and verb-centred by the frozen terciles",
     "second_rule": "an independently written second rule (position-weighted: lemma in the first clause counts, "
                    "object nouns only in the second) computed for the agreement check",
   },
   dvs={"reachable_at_1": "released selection at rank 1 under the frozen BM25"},
   models=["logistic with instruction centring x description centring and an overlap control; a second-rule "
           "agreement table (Cohen kappa) and a re-fit under the second coding"],
   thresholds=dict(support="interaction |beta| >= 0.15 with CI excluding 0 and p_holm < 0.05, plus kappa >= 0.6 for "
                           "H3", partial="CI excludes 0 below the floor, or kappa in [0.4, 0.6)",
                   null="CI includes 0 or kappa < 0.4"),
   family=3,
   kill_gate="if either centring rule puts >= 80% of texts in one bin, the classification has no contrast to work "
             "with and the topic is reported as unidentifiable on this corpus",
   tables=["table1_sample_and_structure.csv", "table2_centring_distribution.csv", "table3_interaction.csv",
           "table4_second_rule_agreement.csv", "table5_robustness_inference.csv",
           "table6_baseline_comparison.csv", "table7_experiment_provenance.csv", "table_run_cost.csv"],
   figures=["fig0_framework.pdf", "fig1_centring_examples.pdf", "fig2_interaction.pdf",
            "fig3_second_rule_agreement.pdf", "fig4_robustness.pdf"]),
}

COMMON = dict(seed=SEED, sample=SAMPLE, bands=BANDS,
              notes="Wave 2 reads the description side of the same encounter on the same rows. No inference API is "
                    "called; the encoder is the locally-run one already used in wave 1; nothing is labelled by a "
                    "judge; every DV is computed from columns the release ships.")

# Filled in by EXP-0135 (the wave-2 premise census) as soon as it runs, before any outcome is computed.
PREMISES = dict(
  census="results_raw/EXP0135_wave2_premise_census_*.json",
  measured={"negation_marker_share_of_candidates": 0.029,
          "boundary_specific_share": 0.0009,
          "verb_lexicon_coverage_mean": 0.0666,
          "parameter_enumeration_share": 1.0,
          "description_tokens": {"deciles_distinct": 10, "mean": 25.3, "p10": 7.0, "p50": 16.0, "p90": 46.0},
          "centring": {"dominant_bin_share": 0.8901, "mean": 1.401, "rule_b_agreement_kappa": 0.4142, "rule_b_observed_agreement": 0.6095, "sd": 14.769, "tercile_sizes": [56401, 56401, 56401]}},
  verdict="T112 and T117 are NOT identifiable on this corpus (their kill gates fired); T111, T114, T115 and "
          "T116 have their premises confirmed. The blocked topics are recorded with their numbers rather than "
          "run thin, which is what the spec's kill-gate rule asks for.",
  gates={"T111_component_collinearity": "measured in the run itself (VIF on the three agreement columns)", "T112_negation_identifiable": False, "T114_prototype_computable": True, "T115_enumeration_coverage": True, "T116_granularity_spread": True, "T117_centring_contrast": False},
  amendments={
    "T112": "not run: negation markers occur in 0.029 of candidate descriptions against the frozen 5 percent "
            "identifiability gate, so boundary language cannot carry a contrast here; the design is reported "
            "as a measurement limit",
    "T117": "not run: the frozen centring rule puts 0.8901 of texts in a single bin against the 80 percent gate, "
            "and the independently written second rule agrees only at kappa 0.4142, so neither the classification "
            "nor its reliability is established on this corpus",
    "T111": "runs as frozen", "T114": "runs as frozen", "T115": "runs as frozen", "T116": "runs as frozen"},
  deviation_note="premise census EXP-0135 ran on description structure only; no relationship to any outcome "
                 "had been computed when the gates above were evaluated")


# topic -> the experiment that carries its pre-registered test, so the package builder can be pointed at a wave
EXP_OF = {"T111": "EXP-0137", "T114": "EXP-0138", "T115": "EXP-0139", "T116": "EXP-0140"}
MATRIX = "results_raw/EXP0136_wave2_metadata_matrix_*.json"
BATTERY = "results_raw/EXP0141_wave2_battery_*.json"
RUNNABLE = ("T111", "T114", "T115", "T116")

# --------------------------------------------------------------------------------- wave-level constants for the builder
# `wave_package.py` reads these instead of carrying wave-1's experiment ids, script names and failure narratives in
# its own prose. Anything absent here falls back to the wave-1 value, which is correct for shared substrate (the
# encoder cache below) and wrong to invent, so each entry names the artefact that actually exists.
FEATURE_EXP = "EXP-0136"                  # this wave's shared feature matrix
PREMISE_EXP = "EXP-0135"                  # this wave's premise census
BATTERY_EXP = "EXP-0141"                  # this wave's E00-E19 battery
ENCODER_EXP = "EXP-0120/EXP-0125"         # the dense arm is wave 1's cache, re-read rather than re-encoded
MATRIX_GLOB = MATRIX
BATTERY_GLOB = "results_raw/EXP0141_wave2_battery_0141_*.json"
PREMISE_GLOB = "results_raw/EXP0135_wave2_premise_census_*.json"
ENCODER_GLOB = "results_raw/EXP0120_wave1_encoder_run_*.json"
DESIGNS_MODULE = "topic_designs_wave2"
CLEAN_ROOM_ONLY_FLAG = "--only"
STAGE_RX = "wave2_main"
PROBE_SCRIPT = "probe_wave2_premises.py"
MATRIX_SCRIPT = "exp_wave2_features.py"
BATTERY_SCRIPT = "exp_wave2_battery.py"
ENCODE_SCRIPT = "encode_wave1_texts.py"
SCRIPT_OF = {t: "exp_wave2_designs.py" for t in RUNNABLE}
MAIN_SCRIPT_OF = {t: ("exp_wave2_designs.py", e) for t, e in EXP_OF.items()}
DENSE_SUPERSESSION_NOTE = "(EXP-0120/EXP-0125, the cache this wave re-reads)"
FAILED_RUNS = [
    "EXP0137_run_console.log / results_raw/EXP013[7-9]_wave2_design_*_20260924T061301.json and ...T061534.json "
    "(two pre-fix runs alive at once, each writing its own timestamped set): T111's verdict rule could not express a "
    "sign reversal, T114's H2 tested the gold outcome instead of the frozen non-gold displacement claim, T115 took "
    "min(step p) as its family entry and passed an invented p for H3, and T116's monotone predicate was true by "
    "construction. All eight files are in the programme ledger with these reasons.",
    "EXP0137_run_console.log (the first corrected run: crashed on the VIF kill gate after computing every bootstrap, "
    "because all four designs were written only at the end of main(); each design now writes its own artefact the "
    "moment it finishes, and the artefact records the argv that produced it)",
    "results_raw/EXP0136_wave2_metadata_matrix_*T052622.json (the matrix build's first pass, superseded when the "
    "T115 coverage gate was recomputed from the shares rather than asserted)",
]


EXTRA_DEVIATIONS = [
 ("W2-D09", "table4_disagreement_census.csv is filled from the Fisher 2x2 the run produced, not from a separately "
            "named census",
  "The freeze named a 'disagreement census' table for T114 and the design measured exactly that quantity, but it "
  "wrote it into the artefact as `fisher_decoy_table` - the 2x2 of whether a semantically closer decoy sits at rank 1 "
  "crossed with whether the released selection was a prototype. The round-2 pass found the shipped file holding a "
  "single line, `unknown table source disagreement_census`, because no table-to-source mapping was ever written for "
  "it, so the package was carrying an empty deliverable while the numbers sat unused in the artefact. The mapping "
  "now points the declared table at that block; no measurement, threshold or seed changed."),
]
