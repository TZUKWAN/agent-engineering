# Canonical intermediate representation: the unit tests behind it (EXP-0109)

Spec 21.4 allows a cross-schema study to map different original formats onto one canonical representation,
but requires **each transformation to have a unit test** and the original schema to be kept. This is the
record that the second half of that sentence is now true, and what each group of cases pins.

| case | what it pins |
|---|---|
| `message_key_vocabularies_map_onto_one_reader` | message_key_vocabularies_map_onto_one_reader |
| `json_string_message_column_is_only_counted_as_presence` | json_string_message_column_is_only_counted_as_presence |
| `model_id_is_read_from_the_nested_generation_configs` | model_id_is_read_from_the_nested_generation_configs |
| `metadata_cell_types_never_raise` | metadata_cell_types_never_raise |
| `non_empty_separates_absent_blank_null_and_a_real_zero` | non_empty_separates_absent_blank_null_and_a_real_zero |
| `catalogue_parsing_rejects_instead_of_truncating` | catalogue_parsing_rejects_instead_of_truncating |
| `split_is_a_pure_function_of_prompt_id_with_disjoint_buckets` | split_is_a_pure_function_of_prompt_id_with_disjoint_buckets |
| `turn_splitting_extracts_the_first_command_line_only` | turn_splitting_extracts_the_first_command_line_only |
| `coder_priority_is_first_match_wins_and_thought_only_needs_a_command` | coder_priority_is_first_match_wins_and_thought_only_needs_a_command |
| `observation_kind_keeps_three_states_apart` | observation_kind_keeps_three_states_apart |
| `tool_call_spellings_are_extracted_per_shape` | tool_call_spellings_are_extracted_per_shape |
| `lexical_tokenisation_is_lowercase_stopword_free_and_empty_safe` | lexical_tokenisation_is_lowercase_stopword_free_and_empty_safe |

Suite status: **ALL_TESTS_PASS**, 12 cases, 0.02 s, run by `python 02_shared_code/trajectory_parser/test_canonical_ir.py`. The module imports the production functions (`build_toucan_routing_dataset`, `isp_stage_coder`, `canonical_conformance_audit_p003`) rather than copies, so a change to a transformation fails a test instead of moving a published number.

Two behaviours became explicit while writing these tests:
* the stage coder's *thought* is only the prose **before** the first fenced command - text after a command
  is not part of the input to the label, which is why `clarification` keys on opening prose;
* a turn with no command can only be `clarification` or `uncodable`: a thought that merely contains the
  word `done` cannot mark an episode finished, so the `end` share is not inflated by wishful phrasing.

Neither behaviour was documented before; both are now asserted on every run of the chain.
