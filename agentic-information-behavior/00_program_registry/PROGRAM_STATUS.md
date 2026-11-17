# Programme status and handoff - Agentic Information Behavior series

Generated 2026-09-27 00:49 by `02_shared_code/registry/program_status.py`. Every number below is read from the files named under it; nothing here is recalled from a previous session. The hand-written document this replaces is at `docs/archived/PROGRAM_STATUS_handwritten_20260919.md`.

**Verification tools.** `02_shared_code/registry/package_audit.py` (deliverables + content checks per package), `02_shared_code/registry/gates18_complete.py` (the G18 matrix), `02_shared_code/registry/spec_completion_audit.py` (every requirement id in the spec), `results_raw/SUPERSEDED_ARTIFACTS.json` (failed and superseded runs, kept and labelled, never deleted).

## 1 The five packages

| paper | topic | claims (by status) | limitation sections | deviations D# | experiments | package audit | G18 verdicts |
|---|---|---|---|---|---|---|---|
| P001_routing_failure_qpp | T001, T001-T003, T024, T037 | 30 (supported:20, qualifies_claim:3, supported_as_null_result:1) | 25 | 33 | 53 | missing=none weak=none | A=PASS B=PASS C=PASS (seeds 42–46 everywhere, per- D=fail on split and metric for every E=PASS F=verdict not parsed |
| P002_isp_stage_measurement | T008, T012, T013, T014, T024 | 9 (supported:6, supported_mixed:1, supported_negative:1) | 8 | 10 | 10 | missing=none weak=none | A=PASS B=PARTIAL - two named items open C=PARTIAL (3/8 claims inferential) D=PASS (no SOTA claim) E=PASS (EXP-0079) F=PASS |
| P003_metadata_interoperability | T008, T012, T013, T014, T024 | 12 (supported:9, ?:2, supported_negative:1) | 8 | 8 | 14 | missing=none weak=none | A=PASS B=PASS (type C: instrument, not SOTA C=PASS D=PASS E=PASS F=PASS |
| P004_shipped_quality_score_validity | T008, T012, T013, T014, T024, T037 | 8 (supported:4, supported_negative:1, supported_mixed:1) | 8 | 7 | 15 | missing=none weak=none | A=PASS B=PARTIAL - one corpus ships the obj C=PASS D=PASS (no SOTA claim) E=PASS (EXP-0079) F=PASS |
| P005_governance_metadata_verifiability | T008, T012, T013, T014, T024 | 12 (supported:9, reported:1, binding:1) | 13 | 4 | 15 | missing=none weak=none | A=PASS B=PASS C=PASS D=PASS (no SOTA claim) E=PASS (EXP-0079) F=PASS |
| P006_underspecified_needs | T101, T103, T106, T108, T109, T110 | 6 (executed:3, null:2, opposite:1) | 8 | 6 | 11 | missing=none weak=none | A=pass B=pass C=pass D=pass E=pass F=pass |
| P007_constraint_density | T101, T103, T106, T108, T109, T110 | 6 (executed:3, null:1, opposite:1) | 9 | 6 | 11 | missing=none weak=none | A=pass B=pass C=pass D=pass E=pass F=pass |
| P008_query_reformulation_fidelity | T101, T103, T106, T108, T109, T110 | 6 (executed:3, partial:1, opposite:1) | 8 | 6 | 11 | missing=none weak=none | A=pass B=pass C=pass D=pass E=pass F=pass |
| P009_lexical_match_bias | T101, T103, T106, T108, T109, T110 | 6 (executed:3, opposite:1, supported:1) | 8 | 6 | 10 | missing=none weak=none | A=pass B=pass C=pass D=pass E=pass F=pass |
| P010_lexical_semantic_conflict | - | 6 (executed:3, supported:1, see:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P011_predicate_argument_relevance | - | 6 (executed:3, not_testable:2, partial:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P012_entity_action_constraint_fit | - | 6 (partial:3, executed:3) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P013_negative_boundary_metadata | - | 0 () | 0 | 0 | 0 | missing=not run weak=not run |  |
| P014_semantic_prototype_bias | - | 6 (executed:3, null:1, supported:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P015_metadata_quality_model | - | 6 (executed:3, not_estimable_no_interval_for_this_statistic:2, not_estimable_denominator_not_recorded:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P016_description_granularity | - | 6 (executed:3, supported:1, not_testable:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P017_noun_verb_centring | - | 0 () | 0 | 0 | 0 | missing=not run weak=not run |  |
| P018_function_vs_usecase_description | - | 6 (executed:3, not_interpretable_length_confound:1, null:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P019_hierarchy_facets_flat_lists | - | 0 () | 0 | 0 | 0 | missing=not run weak=not run |  |
| P020_name_description_congruence | - | 6 (executed:3, supported:1, partial:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P021_synonym_normalisation_consistency | - | 6 (executed:3, partial:1, null:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P022_discriminability_and_discoverability | - | 6 (executed:3, null:2, supported:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P023_modality_and_verification | - | 6 (executed:3, supported:1, null:1) | 8 | 15 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P024_epistemic_behavioural_gap | - | 6 (executed:3, supported:2, outside_the_frozen_rule_negative_contrast:1) | 8 | 15 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P025_contradiction_and_modality | - | 6 (executed:3, opposite:1, supported:1) | 8 | 15 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P026_sufficiency_language_and_stopping | - | 6 (executed:3, null:1, opposite:1) | 8 | 15 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P027_discourse_grammar_of_seeking | - | 6 (executed:3, supported:2, not_invariant_kappa_below_0p60_for_conclusion_evidence_request_hypothesis_plan_question:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P028_conclusion_before_evidence | - | 6 (executed:3, not_testable_premise_floor_with_114_trajectories:1, opposite:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P029_discourse_repair_after_failure | - | 6 (executed:3, supported:2, opposite:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P030_causal_connectives_and_evidence | - | 6 (executed:3, partial:1, null:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P031_explanatory_coherence_and_evidential_gaps | - | 6 (executed:3, null:2, not_reproduced_in_three_of_four_quartiles:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P032_plan_action_alignment | - | 6 (executed:3, null:1, opposite:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P033_search_depth_vs_need_complexity | - | 6 (executed:3, opposite:1, supported:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P034_information_scent_and_the_next_choice | - | 6 (executed:3, partial:2, not_specific_control_tracks_the_same_variance:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P035_marginal_gain_and_search_persistence | - | 6 (executed:3, opposite:1, not_testable_premise_floor_share_0p20_measured_0p1855:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P036_command_family_switching_cost | - | 6 (executed:3, opposite:2, not_reproduced_in_0_of_9_families_below_the_5_frozen_floor:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P037_first_action_path_dependence | - | 6 (executed:3, null:2, opposite:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P038_repetition_and_rumination | - | 6 (executed:3, supported:1, opposite:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P039_semantic_decoy_and_misselection | - | 6 (executed:3, supported:1, not_monotone_in_6_measured_levels:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P040_affordance_language_and_selection | - | 6 (executed:3, null:2, not_specific_length_carries_the_same_signal:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P041_tool_namespace_and_candidate_overload | - | 6 (executed:3, supported:2, not_specific_namespace_share_still_separates:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P042_the_catalogue_ecosystem | - | 6 (executed:3, measured_descriptively_no_band_was_frozen:2, supported:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P043_irrelevant_candidate_contamination | - | 6 (executed:3, not_testable_premise_floor_share_0p10_measured_0p0933:1, measured_per_config_no_band_was_frozen:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P044_tool_dependency_network | - | 6 (executed:3, supported:2, measured_descriptively_no_band_was_frozen:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P045_primacy_lock_in_and_later_search | - | 6 (executed:3, opposite:1, null:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P046_plan_specificity_and_search_quality | - | 6 (executed:3, opposite:2, not_specific_length_carries_the_same_signal:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P047_verbal_versus_behavioural_correction | - | 6 (executed:3, opposite:1, not_at_or_above_the_frozen_floor_measured_0p0155:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P048_when_to_stop_a_recorded_search | - | 0 () | 0 | 0 | 0 | missing=not run weak=not run |  |
| P049_premature_termination_and_over_search | - | 0 () | 0 | 0 | 0 | missing=not run weak=not run |  |
| P050_a_cross_task_grammar_of_agent_search | - | 6 (executed:3, not_testable_premise_family_breadth_frozen_10_measured_2:1, partial:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P051_early_signals_of_agent_search_failure | - | 6 (executed:3, supported:1, not_specific_the_later_phase_adds_nothing:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P052_the_recovery_window_after_a_failed_step | - | 6 (executed:3, null:1, not_monotone_in_3_measured_lags:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P053_which_rollouts_deserve_reuse | - | 6 (executed:3, supported:1, measured_descriptively_no_band_was_frozen:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P054_an_induced_taxonomy_of_agent_information_behaviour | - | 0 () | 0 | 0 | 0 | missing=not run weak=not run |  |
| P055_the_exploration_exploitation_transition | - | 0 () | 0 | 0 | 0 | missing=not run weak=not run |  |
| P056_the_implicit_information_need | - | 6 (executed:3, partial:1, measured_descriptively_rule_declared_non_inferential:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P057_three_kinds_of_linguistic_uncertainty | - | 0 () | 0 | 0 | 0 | missing=not run weak=not run |  |
| P058_need_decomposition_and_search_completeness | - | 0 () | 0 | 0 | 0 | missing=not run weak=not run |  |
| P059_linguistic_cues_and_source_reliability | - | 0 () | 0 | 0 | 0 | missing=not run weak=not run |  |
| P060_attribution_framing_and_credibility_bias | - | 0 () | 0 | 0 | 0 | missing=not run weak=not run |  |
| P061_task_language_ambiguity_and_search_shape | - | 0 () | 0 | 0 | 0 | missing=not run weak=not run |  |
| P062_discourse_structure_of_successful_and_failed_searches | - | 6 (executed:3, supported:1, null:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P063_which_components_of_a_trace_carry_forward | - | 6 (executed:3, supported:1, not_uniform_enough_to_claim:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P064_abstraction_level_of_a_trace_and_transfer | - | 6 (executed:3, supported:1, null:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P065_what_a_compression_loses_first | - | 6 (executed:3, not_the_predicted_ordering:1, measured_descriptively_rule_declared_non_inferential:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P066_relation_classes_between_attempts_of_one_task | - | 6 (executed:3, not_estimable_quasi_separation_in_this_cell:2, measured_descriptively_rule_declared_non_inferential:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P067_information_density_of_language_and_code_actions | - | 6 (executed:3, opposite:1, supported:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P068_corrective_and_ritual_reflection | - | 6 (executed:3, supported:2, below_the_frozen_floor_measured_0p0000:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P069_case_based_reuse_of_historical_trajectories | - | 6 (executed:3, measured_descriptively_gate_fired_claim_limited:1, not_testable:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |
| P070_agent_trajectory_corpora_as_intelligence_sources | - | 6 (executed:3, measured_descriptively_no_band_was_frozen:2, measured_descriptively_gate_fired_claim_limited:1) | 8 | 6 | 0 | missing=not run weak=not run | A=pass B=pass C=pass D=pass E=pass F=pass |

### What each package still owes, in its own words

- **P001_routing_failure_qpp** - Not submittable yet (this paragraph re-checked against the record on 2026-09-20: the dense-baseline sentence that stood here was stale after EXP-0024/EXP-0062 and has been replaced). The empirical core is sound, the H4 hole is closed, and what was D13's *bound…
- **P002_isp_stage_measurement** - NOT submittable, for two reasons. (a) RQ4 could not be run as written because there is no human coding pass here, and re-running codex A against itself gives kappa = 1 by construction, so it was re-instantiated as rubric invariance (registered as a deviation, …
- **P003_metadata_interoperability** - Verification steps this audit owed are all executed; the gate stays open on scope, not on work. The three items listed here until 2026-09-21 have each become a measurement: (1) the 30-cell hand re-derivation ran as EXP-0089, a blind second auditor over all 96 …
- **P004_shipped_quality_score_validity** - NOT submittable yet.
- **P005_governance_metadata_verifiability** - package complete; the gate stays open on scope, not on work.
- **P006_underspecified_needs** - not stated in final_audit.md
- **P007_constraint_density** - not stated in final_audit.md
- **P008_query_reformulation_fidelity** - not stated in final_audit.md
- **P009_lexical_match_bias** - not stated in final_audit.md
- **P010_lexical_semantic_conflict** - not stated in final_audit.md
- **P011_predicate_argument_relevance** - not stated in final_audit.md
- **P012_entity_action_constraint_fit** - not stated in final_audit.md
- **P013_negative_boundary_metadata** - not stated in final_audit.md
- **P014_semantic_prototype_bias** - not stated in final_audit.md
- **P015_metadata_quality_model** - not stated in final_audit.md
- **P016_description_granularity** - not stated in final_audit.md
- **P017_noun_verb_centring** - not stated in final_audit.md
- **P018_function_vs_usecase_description** - not stated in final_audit.md
- **P019_hierarchy_facets_flat_lists** - not stated in final_audit.md
- **P020_name_description_congruence** - not stated in final_audit.md
- **P021_synonym_normalisation_consistency** - not stated in final_audit.md
- **P022_discriminability_and_discoverability** - not stated in final_audit.md
- **P023_modality_and_verification** - not stated in final_audit.md
- **P024_epistemic_behavioural_gap** - not stated in final_audit.md
- **P025_contradiction_and_modality** - not stated in final_audit.md
- **P026_sufficiency_language_and_stopping** - not stated in final_audit.md
- **P027_discourse_grammar_of_seeking** - not stated in final_audit.md
- **P028_conclusion_before_evidence** - not stated in final_audit.md
- **P029_discourse_repair_after_failure** - not stated in final_audit.md
- **P030_causal_connectives_and_evidence** - not stated in final_audit.md
- **P031_explanatory_coherence_and_evidential_gaps** - not stated in final_audit.md
- **P032_plan_action_alignment** - not stated in final_audit.md
- **P033_search_depth_vs_need_complexity** - not stated in final_audit.md
- **P034_information_scent_and_the_next_choice** - not stated in final_audit.md
- **P035_marginal_gain_and_search_persistence** - not stated in final_audit.md
- **P036_command_family_switching_cost** - not stated in final_audit.md
- **P037_first_action_path_dependence** - not stated in final_audit.md
- **P038_repetition_and_rumination** - not stated in final_audit.md
- **P039_semantic_decoy_and_misselection** - not stated in final_audit.md
- **P040_affordance_language_and_selection** - not stated in final_audit.md
- **P041_tool_namespace_and_candidate_overload** - not stated in final_audit.md
- **P042_the_catalogue_ecosystem** - not stated in final_audit.md
- **P043_irrelevant_candidate_contamination** - not stated in final_audit.md
- **P044_tool_dependency_network** - not stated in final_audit.md
- **P045_primacy_lock_in_and_later_search** - not stated in final_audit.md
- **P046_plan_specificity_and_search_quality** - not stated in final_audit.md
- **P047_verbal_versus_behavioural_correction** - not stated in final_audit.md
- **P048_when_to_stop_a_recorded_search** - not stated in final_audit.md
- **P049_premature_termination_and_over_search** - not stated in final_audit.md
- **P050_a_cross_task_grammar_of_agent_search** - not stated in final_audit.md
- **P051_early_signals_of_agent_search_failure** - not stated in final_audit.md
- **P052_the_recovery_window_after_a_failed_step** - not stated in final_audit.md
- **P053_which_rollouts_deserve_reuse** - not stated in final_audit.md
- **P054_an_induced_taxonomy_of_agent_information_behaviour** - not stated in final_audit.md
- **P055_the_exploration_exploitation_transition** - not stated in final_audit.md
- **P056_the_implicit_information_need** - not stated in final_audit.md
- **P057_three_kinds_of_linguistic_uncertainty** - not stated in final_audit.md
- **P058_need_decomposition_and_search_completeness** - not stated in final_audit.md
- **P059_linguistic_cues_and_source_reliability** - not stated in final_audit.md
- **P060_attribution_framing_and_credibility_bias** - not stated in final_audit.md
- **P061_task_language_ambiguity_and_search_shape** - not stated in final_audit.md
- **P062_discourse_structure_of_successful_and_failed_searches** - not stated in final_audit.md
- **P063_which_components_of_a_trace_carry_forward** - not stated in final_audit.md
- **P064_abstraction_level_of_a_trace_and_transfer** - not stated in final_audit.md
- **P065_what_a_compression_loses_first** - not stated in final_audit.md
- **P066_relation_classes_between_attempts_of_one_task** - not stated in final_audit.md
- **P067_information_density_of_language_and_code_actions** - not stated in final_audit.md
- **P068_corrective_and_ritual_reflection** - not stated in final_audit.md
- **P069_case_based_reuse_of_historical_trajectories** - not stated in final_audit.md
- **P070_agent_trajectory_corpora_as_intelligence_sources** - not stated in final_audit.md

P001's test split has been evaluated **1 time(s)** (2026-09-18T18:58:02), which is the pre-registered limit; the ledger is `papers/P001_routing_failure_qpp/test_eval_ledger.json`.

## 2 Programme record

- `00_program_registry/experiment_registry.csv`: **234 experiments**, 234 distinct ids, no ragged rows (checked by `package_audit.py`).
- `results_raw/SUPERSEDED_ARTIFACTS.json`: **1673** failed or superseded artefacts, each with a reason and a `was_it_quoted` field; the files are moved to `results_raw/superseded/`, never deleted.
- `01_datasets/manifests`: 19 evidence entries.
- Status vocabulary in the registry: `success` x6, `battery_executed_across_six_` x6, `H1:supported_H2:supported_H3` x5, `matrix_built_147253_turns_in` x3, `H1:supported_H2:null_H3:not_` x3, `battery_executed_for_6_topic` x3

## 3 Spec compliance (EXP-0099)

Of the **74** requirement ids the spec states, **37** evidenced in package, **37** satisfied by content signature. Detail: `docs/SPEC_COMPLETION_AUDIT.md` (artefact `EXP-0099` scan of 12159 text files).

## 4 Literature position

- 54 abstracts recovered in the second round (openalex=46, semanticscholar=8); 1 screened records stay title-only and are labelled `undecidable_on_title`.
- The grade moves that round reported are **not** new collisions: attributed row by row, {"stored_level_not_reproducible_from_the_text_already_on_disk": 26}.
- Collision levels in the five curated matrices are now re-derivable by one command (`02_shared_code/literature/reconcile_collision_levels.py`); the legacy column is kept beside the re-derived one. See `docs/collision_level_consistency.md`.
- OpenAlex answers from this host (positive control 198 words); Crossref and Semantic Scholar too. arXiv export API reachable; the Hugging Face mirror reachable for dataset files.

## 5 The topic funnel

123 topics tracked. Status distribution: `demoted_L3_crowded` x15, `w3_fold_into_T037` x9, `demoted_L4_taken` x2, `w5_package_complete_pre_submission_checks_open` x2, `w3_fold_into_T012` x2, `not_promoted_single_corpus_and_p001_overlap_PREMISE_CORRECTED_EXP0073` x1, `demoted_L4_taken_by_three_2026_papers` x1, `killed_pilot_no_identifiability` x1, `w3_pilot_passed_main_experiment_next` x1, `w3_fold_into_T008` x1, `killed_L4_and_unidentifiable` x1, `w3_pilot_PROSE_ONLY_declaration_vs_verifiability_p005` x1, `w3_merged_into_T013_reference_structure_only` x1, `demoted_L4_crowded_and_data_blocked` x1, `killed_blocked` x1, `w3_fold_into_T001` x1, `demoted_L4_taken_and_own_overlap` x1, `w2_parked_after_feasibility_probe_EXP0096` x1, `demoted_L3_crowded_and_needs_human_gold` x1, `not_promoted_identifiability` x1, `killed_self_overlap_not_novelty` x1, `w3_fold_into_T002` x1, `demoted_L4_crowded` x1, `w12_packaged_corpora_exposing_an_outcome_or_quality_c:measured_descriptively_gate_fired_claim_limited_spread_in_unit_of_observation_across_the:measured_descriptively_no_band_was_frozen_construct_by_corpus_availability_matrix:measured_descriptively_no_band_was_frozen` x1, `w5_package_complete_as_P001_reconciled_EXP0098` x1, `w1_packaged_underspec_z:null_underspec_z:clarification:null_underspec_z:wrong_tool:opposite` x1, `w_blocked_premise_T102_cluster_count=31642_catalogues_and_rows_parseable=1.0_comparable_candidate_sets=0.8376_lexical_ambiguity_variation=15264_referential_ambiguity_variation=24568_underspecification_spread=13874_outcome_columns_present=1.` x1, `w1_packaged_density_z:inspected_pos:null_density_z:bm25_desc_rank:opposite_H3_nested_gain:below_the_frozen_floor_measured_0p0005` x1, `w10_packaged_underspecification_of_the_instruction_on:partial_the_share_of_requirements_surfaced_by_at:measured_descriptively_rule_declared_non_inferential_underspecification_against_constraint_co:not_specific_another_uncertainty_kind_carries_the_signal` x1, `w1_packaged_H1:partial_con_z:opposite_H3:verdict_not_recorded` x1, `w_blocked_premise_T107_cluster_count=31642_catalogues_and_rows_parseable=1.0_comparable_candidate_sets=0.8376_decomposable_needs=11288_outcome_columns_present=1.0` x1, `w1_packaged_underspec_z_on_displacement:null` x1, `w1_packaged_H1:supported_H2:non_vocabulary_verdict_word_see_ci_the_two_rates_and_their_interval_carry_th_H3:measured_descriptively_rule_declared_non_inferential` x1, `w1_packaged_unlabelled_row:verdict_not_recorded` x1, `w2_packaged_entity_agree:partial_action_agree:partial_constraint_agree:partial` x1, `w2_blocked_premise_negation_prevalence_0p029_below_gate_0p05` x1, `w3_packaged_usecase_minus_baseline_hit1:not_interpretable_length_confound_gain_by_description_length:null_usecase_matched_minus_baseline_hit1:partial` x1, `w2_packaged_centr_z:verdict_not_recorded_hi:supported_H3_disagreement_census:characterised` x1, `w2_packaged_unlabelled_row:verdict_not_recorded_binding_nested_step_enumeration->full:not_estimable_no_interval_for_this_statistic_composite_minus_length_only_auroc:not_estimable_denominator_not_recorded` x1, `w2_packaged_t:descriptive stratum slope, not a family member_txlarge:supported` x1, `w2_blocked_premise_centring_dominance_0p890_above_gate_0p80_kappa_0p414` x1, `w_blocked_premise_T118_median_name_segments=1.0_share_of_entries_with_more_than_one_segment=0.1694` x1, `w3_packaged_congruence_unconditional:supported_congruence_with_frozen_controls:partial_congruence_level_contrast:not_testable_empty_cell` x1, `w3_packaged_synonym_minus_baseline_hit1:partial_within_family_rank_spread_synonym_minus_:null_benefit_where_vocabulary_differs:opposite` x1, `w_blocked_premise_T121_marker_share_of_candidates=0.029_gate=0.05_source=EXP-0135 (wave-2 premise census), the same column on the same corpus` x1, `w3_packaged_discriminability_lexical:null_discriminability_over_completeness_auroc:null_discriminability_x_catalogue_size:supported` x1, `w4_packaged_modal_turn_on_next_inspection:supported_modal_x_error_interaction:null_topical_control_count_z_on_next_inspecti:not_specific_control_tracks_the_same_variance` x1, `w4_packaged_discordant_minus_body_only_on_next_inspe:supported_body_only_vs_no_hedge_on_next_inspection:outside_the_frozen_rule_negative_contrast_discordant_minus_body_only_on_stopping:supported` x1, `w4_packaged_same_tool_content_change_on_modality:opposite_changed_minus_different_tool_on_modality:supported_same_tool_content_change_on_sufficiency_:null` x1, `w4_packaged_sufficiency_claim_added_to_the_evidence_:null_prior_inspections_at_claim_stops_minus_o:opposite_category_strata_of_the_claim_effect:descriptive stratum slopes, not a family member` x1, `w_blocked_premise_T128_cluster_count=31642_descriptions_have_text=13.17_catalogues_and_rows_parseable=1.0_comparable_candidate_sets=0.8376_credibility_language_present=0.2555_outcome_columns_present=1.0` x1, `w_blocked_premise_T129_cluster_count=31642_catalogues_and_rows_parseable=1.0_comparable_candidate_sets=0.8376_cross_server_content_pairs=1845_outcome_columns_present=1.0` x1, `w5_packaged_last_third_on_act_plan:supported_last_third_on_act_conclusion:supported_tagger_a_vs_tagger_b_kappa_per_act:not_invariant_kappa_below_0p60_for_conclusion_evidence_request_hypothesis_plan_question` x1, `w11_packaged_result_minus_exception_balance_on_submit:supported_submitting_on_the_position_of_the_first_:null_the_balance_against_an_observation_count:not_specific_the_observation_count_alone_separates` x1, `w5_packaged_conclusion_before_first_inspection_vs_af:not_testable_premise_floor_with_114_trajectories_concluded_after_inspection_on_standardis:opposite_act_conclusion_on_stopping_here:supported` x1, `w5_packaged_failure_preceded_turn_on_diagnostic_lang:supported_reissue_language_on_calling_again_after_:supported_abandon_language_on_stopping_after_failu:opposite` x1, `w5_packaged_causal_connective_on_standardised_eviden:partial_inferential_minus_explanatory_on_evidenc:null_causal_control_lexicon_on_evidence_overl:measured_descriptively_rule_declared_non_inferential` x1, `w5_packaged_causal_chain_on_standardised_evidence_ov:null_causal_chain_on_stopping_here:null_sign_of_the_chain_contrast_within_body_l:not_reproduced_in_three_of_four_quartiles` x1, `w5_packaged_plan_alignment_minus_other_trajectory_nu:null_alignment_on_the_next_call_failing:opposite_sign_of_the_alignment_contrast_by_tool_f:not_testable_only_4_of_20_families_estimable` x1, `w11_packaged_carry_forward_lift_per_component_categor:supported_the_spread_of_carry_forward_across_categ:not_uniform_enough_to_claim_own_earlier_category_against_an_alien_on:not_specific_the_alien_category_carries_it_too` x1, `w11_packaged_the_earlier_attempt_s_concreteness_on_th:null_own_earlier_level_against_a_seeded_other:not_specific_the_alien_level_carries_it_too` x1, `w11_packaged_survival_of_each_component_category_unde:not_the_predicted_ordering_survival_within_a_stratum_of_first_menti:measured_descriptively_rule_declared_non_inferential_a_compression_that_removes_the_exception:null` x1, `w11_packaged_prevalence_of_each_relation_class_among_:measured_descriptively_rule_declared_non_inferential_refinement_versus_new_on_the_later_attem:not_estimable_quasi_separation_in_this_cell_the_relation_class_beyond_overlap_and_th:not_estimable_quasi_separation_in_this_cell` x1, `w_blocked_premise_T151_cluster_count=1784_rollouts_parseable=0.9994_command_families_for_a_taxonomy=11_newness_available=0.7876` x1, `w3_fold_into_P002` x1, `w9_packaged_pooled_transition_matrix_against_the_uni:not_testable_premise_family_breadth_frozen_10_measured_2_a_family_s_own_matrix_against_the_pooled:partial_ordering_beyond_the_unigram_against_a_wi:not_specific_the_shuffle_carries_the_same_gain` x1, `w_blocked_premise_T154_cluster_count=31642_catalogues_and_rows_parseable=1.0_comparable_candidate_sets=0.8376_lexical_ambiguity_variation=15264_referential_ambiguity_variation=24568_outcome_columns_present=1.0` x1, `w6_packaged_need_length_within_instance_on_log_steps:opposite_depth_on_submitting_rather_than_running_:supported_sign_of_the_depth_need_association_by_ta:not_reproduced_in_1_of_1_families_below_the_10_frozen_floor` x1, `w_blocked_premise_T156_cluster_count=1784_rollouts_parseable=0.9994_outcome_label_present=1.0_trajectories_with_switches=19964_newness_available=0.7876` x1, `w6_packaged_scent_on_new_information_returned:partial_same_model_under_the_asymmetric_scent_in:partial_verbosity_control_on_new_information:not_specific_control_tracks_the_same_variance` x1, `w6_packaged_newness_of_the_observation_just_returned:opposite_failed_observation_on_continuing_the_sea:not_testable_premise_floor_share_0p20_measured_0p1855_cumulative_newness_on_submitting_within_:not_reproduced_in_0_of_4_quartiles` x1, `w7_packaged_near_synonym_decoy_present_on_missing_th:supported_fail_at_1_profile_by_number_of_decoys_in:not_monotone_in_6_measured_levels_decoy_presence_against_a_random_candidat:measured_descriptively_rule_declared_non_inferential` x1, `w7_packaged_affordance_verb_density_in_the_gold_desc:null_gold_candidate_naming_its_parameters_on_:null_parameters_and_affordance_language_are_n:not_specific_length_carries_the_same_signal` x1, `w3_fold_into_T116` x1, `w7_packaged_namespace_separator_share_within_a_catal:supported_fourth_versus_first_candidate_count_quar:supported_the_namespace_share_after_server_concent:not_specific_namespace_share_still_separates` x1, `w7_packaged_within_server_minus_across_server_descri:supported_the_catalogue_population_is_not_concentr:measured_descriptively_no_band_was_frozen_local_tool_names_published_by_more_than_:measured_descriptively_no_band_was_frozen` x1, `w7_packaged_a_zero_overlap_candidate_ranked_above_th:not_testable_premise_floor_share_0p10_measured_0p0933_contamination_measured_inside_each_confi:measured_per_config_no_band_was_frozen_catalogue_size_on_the_number_of_contamin:supported` x1, `w3_fold_into_P001` x1, `w6_packaged_family_switch_on_new_information:opposite_switch_rate_on_rollout_depth:opposite_sign_of_the_switching_cost_by_command_fa:not_reproduced_in_0_of_9_families_below_the_5_frozen_floor` x1, `w7_packaged_a_frequently_co_needed_gold_pair_on_miss:supported_frequent_pair_minus_random_pair_descript:supported_the_network_is_sparse_and_its_degree_is_:measured_descriptively_no_band_was_frozen` x1, `w6_packaged_off_modal_first_action_on_family_concent:null_staying_in_the_first_family_on_submittin:opposite_search_first_opening_on_staying_in_famil:null` x1, `w8_packaged_turn_position_on_overlap_with_the_trajec:opposite_an_early_hypothesis_on_the_newness_of_wh:null_own_anchor_versus_a_seed_chosen_alien_an:not_specific_the_alien_anchor_tracks_the_same_variance` x1, `w6_packaged_repeated_command_on_new_information:supported_exact_repeat_present_on_submitting_with_:opposite_newness_profile_by_number_of_prior_runs:not_monotone_in_4_measured_levels` x1, `w_blocked_premise_T175_cluster_count=14701_category_breadth=8_trajectories_parseable=1.0_trajectories_with_later_turns=13695_terminal_turn_identifiable=0.4649_observations_parseable=1.0` x1, `w_blocked_premise_T176_repeated_call_trajectories=4125_cluster_count=14701_category_breadth=8_outcome_label_available=0_trajectories_parseable=1.0_terminal_turn_identifiable=0.4649_observations_parseable=1.0_error_marked_observations=0.5893` x1, `w3_fold_into_T131` x1, `w9_packaged_first_fifth_features_predict_the_release:supported_the_increment_from_adding_the_last_fifth:not_specific_the_later_phase_adds_nothing_the_early_signal_inside_each_of_the_five:not_reproduced_in_0_of_3_families_below_the_3_frozen_floor` x1, `w9_packaged_changing_the_command_at_the_first_step_a:null_the_completion_advantage_by_lag_after_th:not_monotone_in_3_measured_lags_the_lag_one_advantage_inside_each_length:not_estimable_no_interval_for_this_statistic` x1, `w8_packaged_first_turn_plan_specificity_on_the_repea:opposite_first_turn_plan_specificity_on_the_error:opposite_the_specificity_parts_against_opening_tu:not_specific_length_carries_the_same_signal` x1, `w12_packaged_content_word_density_per_1000_characters:opposite_share_of_turns_answered_by_an_observatio:supported_composition_and_block_level_correction_a:measured_descriptively_no_band_was_frozen` x1, `w3_fold_into_T123` x1, `w3_fold_into_T125` x1, `w3_fold_into_T127` x1, `w12_packaged_share_of_conversations_with_a_reflection:supported_content_word_overlap_with_the_previous_t:supported_share_of_marker_transitions_whose_conten:below_the_frozen_floor_measured_0p0000` x1, `w8_packaged_a_verbal_correction_after_an_error_marke:opposite_the_share_of_verbal_corrections_with_no_:not_at_or_above_the_frozen_floor_measured_0p0155_agreement_between_an_admission_and_a_pre:measured_descriptively_rule_declared_non_inferential` x1, `w_blocked_premise_T191_field_coverage_of_sampled_trajectories=0.0_gate=0.5_local_alternative=AgentTrove `result` 13.7% (EXP-0027), below the same gate` x1, `w9_packaged_within_instance_agreement_between_succes:supported_instances_where_a_cheaper_successful_rol:measured_descriptively_no_band_was_frozen_the_agreement_after_restricting_to_succe:measured_descriptively_rule_declared_non_inferential` x1, `w12_packaged_share_of_rollouts_with_another_instance_:measured_descriptively_gate_fired_claim_limited_sibling_issue_similarity_against_sibling:not_testable_neighbour_similarity_against_steps_and_f:not_testable_premise_no_order_or_case_library_recorded` x1

Rows still in the working part of the funnel, with what each one is waiting on:

| topic | status | waiting on |
|---|---|---|
| T008 12M 轨迹上的信息搜索过程阶段再检验 | w3_pilot_passed_main_experiment_next | EXP-0031 executed (EXP0031_p002_stage_main_20260919T002148.json). SWE-ZERO: codability 95.4%, RQ2 direction clears its CI null but misses both frozen  |


**How to read the funnel.** A parked or killed topic carries the measurement that ended it, not an opinion: T027 is parked because its outcome is censored on task completion (2x2 [[0,3238],[1137,625]], Fisher p 0), T029 because its predictor was not separable from its label, T036 because a 392-record screen found 1 L2+ and 0 L3+ with 199 records unread - a bounded negative, not proof of absence.

## 6 Reproducing any of this

Each package carries `reproduce.sh`, and the whole set was replicated in a clean environment (EXP-0079: fresh venv, no system site-packages, dataset reached by junction, whole-artefact leaf comparison). The commands are in the scripts; `package_audit.py` is what says whether a package is complete, and it is run by CI-of-one here rather than trusted from memory.

