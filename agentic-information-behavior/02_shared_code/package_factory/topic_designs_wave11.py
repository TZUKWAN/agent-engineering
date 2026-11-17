"""The wave-11 protocol freeze: a recorded search as an organisation's memory.

Five designs (T131 successful-versus-failed discourse, T137 which components of a trace carry forward, T138 the level
of abstraction they carry forward at, T140 what a compression loses first, T142 what relation two attempts of one task
bear to each other) are measured on the estate's fixed 12-file SWE-ZERO rollout draw - 20,000 rollouts, 1,784 task
instances, 1,775 of them attempted more than once, an outcome label on every rollout and assistant prose averaging
4,901 characters. EXP-0207 measured all of it twice with identical output; two gates fired, both at strata scope only
(the draw has one scaffold agent, and 2 of 805 repository prefixes reach 200 rollouts), so the stratum these designs
report inside is the repository and never a claim of cross-scaffold breadth.

One boundary the whole wave inherits from wave 9: `exit_status` has two values, and the release's own completion
signal is rare - **560 of 20,000 rollouts (2.8%) are `Submitted`**, the rest `incomplete`. Every success-flavoured
claim below is therefore a comparison against that base rate, with the positive count printed beside every estimate,
and no floor was written or moved after seeing it.

    python 02_shared_code/package_factory/freeze_wave.py --designs topic_designs_wave11
"""
from __future__ import annotations

EXP_OF = {"T131": "EXP-0209", "T137": "EXP-0210", "T138": "EXP-0211", "T140": "EXP-0212", "T142": "EXP-0213"}
RUNNABLE = tuple(EXP_OF)
BLOCKED_BY_GATE = ()
FEATURE_EXP = "EXP-0208"
PREMISE_EXP = "EXP-0207"
BATTERY_EXP = "EXP-0214"
ENCODER_EXP = ""
SEED = 42
BANDS = {"small": 0.05, "medium": 0.15, "large": 0.30}
MATRIX = "results_raw/EXP0208_wave11_trace_matrix_*.json"
PREMISE_GLOB = "results_raw/EXP0207_wave11_premise_census_*.json"
BATTERY = "results_raw/EXP0214_wave11_battery_0214_*.json"
MATRIX_GLOB = MATRIX
BATTERY_GLOB = BATTERY
ENCODER_GLOB = ""
MATRIX_SCRIPT = "exp_wave11_features.py"
BATTERY_SCRIPT = "exp_wave11_battery.py"
PROBE_SCRIPT = "probe_wave11_premises.py"
DESIGNS_MODULE = "topic_designs_wave11"
STAGE_RX = "wave11_main"
CLEAN_ROOM_ONLY_FLAG = "--only"
CLEAN_ROOM_MODE = "full"
SCRIPT_OF = {t: "exp_wave11_designs.py" for t in RUNNABLE}
MAIN_SCRIPT_OF = {t: "exp_wave11_designs.py" for t in RUNNABLE}
SUBSTRATE_LABEL = ("the estate's fixed 12-file SWE-ZERO rollout draw (seed 42, content-deduplicated before sampling, "
                   "as in waves 6 and 9): 20,000 rollouts of 1,784 task instances, 1,775 instances with more than one "
                   "attempt, exit_status on every rollout (560 Submitted, 19,440 incomplete) and assistant prose "
                   "coded for eight component categories")
SAMPLE_FIELDS = ("corpus", "rollouts_drawn", "rollouts_parsed", "task_instances", "instances_with_2plus_rollouts",
                 "outcome_label_share", "submitted_share", "median_assistant_turns", "mean_chars_of_agent_text",
                 "cluster_unit")
CONTRIBUTION_POPULATION = ("recorded step-level agent searches with the release's own completion label and several "
                           "attempts of the same task, read with rule and lexical instruments only - no model, no "
                           "judge, no re-running of a rollout")

COMMON = {
    "seed": SEED,
    "bands": BANDS,
    "module": "topic_designs_wave11",
    "sample": {"traj_cap": 20000, "cluster_unit": "instance_id",
              "unit_of_analysis": "the rollout, grouped within the task instance whose attempts it is",
              "rule": "the same seeded 12-file draw and the same 20,000-rollout cap waves 6 and 9 used, deduplicated "
                      "by exact content before sampling; no further subsample",
              "excluded": "rollouts with no commanded step and no assistant prose (21 of 20,000, EXP-0207 measured "
                          "0.9989 parse coverage), which cannot be coded for components"},
    "instruments": ("a component category is present in a rollout when one of its frozen phrases occurs in the "
                    "assistant's own prose with the command blocks removed; abstraction is the count of generic "
                    "references against the count of identifiers, paths and numbers; uncertainty and negative "
                    "constraint lists are wave 4's and the frozen list in EXP-0207; a compression keeps the first "
                    "k fraction of a rollout's assistant turns, k in 0.1/0.25/0.5, and re-codes the same text; a "
                    "relation between consecutive attempts of one instance is a content-word Jaccard band "
                    "(restatement >= 0.6, refinement 0.25-0.6, new < 0.25) with a contradiction flag where the "
                    "negative-constraint counts differ by two or more inside a non-new pair; attempt order inside an "
                    "instance is the draw's row order, which the frame records as an explicit index"),
}

DESIGNS = {
 # ------------------------------------------------------------------ T131
 "T131": {
  "pkg": "P062_discourse_structure_of_successful_and_failed_searches",
  "title": "Do Successful and Failed Searches Have Different Discourse Structures?",
  "rq": "Holding how long a search was and how much it observed, does a rollout that ends by submitting differ in "
        "what its own prose carries - results, exceptions, procedure, rationale?",
  "hypotheses": [
   "H1 a rollout that ends Submitted carries the result category more often and the exception category less often "
   "than an incomplete rollout of the same length, with assistant-turn count and prose length controlled.",
   "H2 the ordering differs: a submitted rollout states its procedure earlier relative to its own length and its "
   "observations later than an incomplete one, reported as two positions with cluster-robust intervals.",
   "H3 the asymmetry is not the step count speaking twice: with the number of observations controlled, the "
   "result-minus-exception balance still separates, and the same model with only the observation count adds nothing "
   "above the controls."],
  "features": {"comp_result": "the result category present in the rollout prose",
               "comp_exception": "the exception category present",
               "balance": "comp_result minus comp_exception, and the same over the eight categories",
               "first_procedure_position": "index of the first assistant turn carrying the procedure category over the "
                                           "rollout's turn count",
               "first_observation_position": "the same for the observation category"},
  "dvs": {"submitted": "H1's and H3's outcome, the release's own label",
          "first_procedure_position": "H2's outcome", "first_observation_position": "H2's second arm"},
  "models": ["logistic on submitted with the result and exception indicators, the balance term, assistant-turn count "
             "and prose length, clustered on instance_id",
             "OLS on the two positions with the same controls",
             "the balance term entered with the observation count, then without it, so the two are separated"],
  "thresholds": {"support": "|beta| >= 0.15 with CI excluding 0 and p_holm < 0.05",
                 "partial": "CI excludes 0 below the floor", "null": "CI includes 0"},
  "family": "three",
  "gate_scope": "design",
  "kill_gate": ("G1 froze >= 1,000 readable rollouts and EXP-0207 measured 20,000; G2 froze >= 500 with a non-null "
                "outcome and measured 20,000; G8, which scopes H2 only, measured 19,995 rollouts with an observation "
                "after a command. The label's sparsity - 560 Submitted against 19,440 incomplete - is a measured "
                "property of this release, stated here and printed with every estimate, not a floor that was moved."),
  "strata": ["repository prefix", "rollout-length quartile"],
  "tables": ["table1_sample_and_structure.csv", "table2_discourse_census.csv", "table3_main_models.csv",
             "table4_strata_by_repository.csv", "table5_robustness_inference.csv", "table6_baseline_comparison.csv",
             "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_discourse_profile.pdf", "fig2_main_effect.pdf",
              "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"],
 },
 # ------------------------------------------------------------------ T137
 "T137": {
  "pkg": "P063_which_components_of_a_trace_carry_forward",
  "title": "Which Linguistic Components of a Trajectory Constitute Reusable Procedural Knowledge?",
  "rq": "When the same task is attempted twice, which kinds of thing the first attempt said make the second attempt "
        "more likely to say them too?",
  "hypotheses": [
   "H1 for at least one component category, a category present in an earlier attempt of an instance is present in "
   "the next attempt more often than when it was absent earlier, and the lift reaches the frozen 0.15 band with an "
   "interval excluding 0.",
   "H2 the lift is not uniform across categories: all eight are reported with cluster-robust intervals on the "
   "instance, and the claim is about their spread, not about an average.",
   "H3 the carry-forward is not generic text overlap: with a Jaccard band entered in the model the category term "
   "still separates, and a category taken from another instance's attempt in the same repository does not carry at "
   "all."],
  "features": {"earlier_has_category": "the category present in the preceding attempt of the same instance",
               "later_has_category": "the same category in the following attempt",
               "alien_has_category": "the category present in a seeded other instance's attempt in the same "
                                     "repository", "text_jaccard": "content-word overlap between the two attempts"},
  "dvs": {"later_has_category": "H1 to H3's outcome, a 0/1 event per category and per adjacent attempt pair"},
  "models": ["paired within-instance lift per category with a cluster bootstrap on instance_id",
             "the same lift with the text-overlap band entered, so carry-forward is not restatement",
             "the alien-category arm in place of the instance's own earlier attempt"],
  "thresholds": {"support": "lift >= 0.15 with CI excluding 0 and p_holm < 0.05",
                 "partial": "CI excludes 0 below the floor", "null": "CI includes 0"},
  "family": "three",
  "gate_scope": "design",
  "kill_gate": ("G3 froze >= 300 tasks with two or more recorded attempts and measured 1,775; G5 froze >= 1,000 "
                "rollouts carrying two or more component categories and measured 19,887, with a median of six of the "
                "eight per rollout. G10's scaffold-diversity condition fires (the draw has one agent) and is strata "
                "scope only, so the stratum actually reported is the repository - named in every stratum row."),
  "strata": ["repository prefix", "component category"],
  "tables": ["table1_sample_and_structure.csv", "table2_carry_forward_census.csv", "table3_main_models.csv",
             "table4_strata_by_repository.csv", "table5_robustness_inference.csv", "table6_baseline_comparison.csv",
             "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_carry_forward_matrix.pdf", "fig2_main_effect.pdf",
              "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"],
 },
 # ------------------------------------------------------------------ T138
 "T138": {
  "pkg": "P064_abstraction_level_of_a_trace_and_transfer",
  "title": "How the Level of Linguistic Abstraction Affects Knowledge Transfer",
  "rq": "When an attempt is written concretely - identifiers, paths, numbers - does the next attempt of the same "
        "task stay concrete, and does that level predict whether the task is eventually submitted?",
  "hypotheses": [
   "H1 consecutive attempts of one instance share a concreteness level: the within-pair correlation of the concreteness "
   "index is positive with an interval excluding 0.",
   "H2 a more concrete earlier attempt is followed by a higher chance that the later attempt ends Submitted, holding "
   "the pair's lengths and the repository fixed.",
   "H3 the transmission is not generic similarity: with the text-overlap band in the model the level still "
   "correlates, and pairing an attempt with a seeded attempt of a *different* instance in the same repository "
   "produces nothing."],
  "features": {"concreteness": "concrete marker count minus abstract marker count, z-scored over pairs",
               "earlier_concreteness": "the index in the preceding attempt of the instance",
               "later_concreteness": "the same in the following attempt",
               "alien_concreteness": "the index of a seeded other instance's attempt in the same repository"},
  "dvs": {"later_concreteness": "H1's and H3's outcome", "submitted": "H2's outcome"},
  "models": ["OLS on the later level with the earlier level, the overlap band and length controls, clustered on "
             "instance_id",
             "logistic on the later attempt's own submitted label with the earlier level and the same controls",
             "the same pair model with the alien earlier level substituted"],
  "thresholds": {"support": "|beta| >= 0.15 with CI excluding 0 and p_holm < 0.05",
                 "partial": "CI excludes 0 below the floor", "null": "CI includes 0"},
  "family": "three",
  "gate_scope": "design",
  "kill_gate": ("G6 froze >= 1,000 rollouts carrying a code identifier - the concrete end of this axis - and "
                "EXP-0207 measured 18,711, with a mean of 18.1 concrete markers per rollout against 2.1 abstract "
                "ones; G3's repeated-attempt floor (1,775 against 300) is what makes a consecutive pair exist at "
                "all, and G10's agent-diversity condition fired at strata scope only, so breadth across scaffolds is "
                "not claimed anywhere in this design."),
  "strata": ["repository prefix", "pair-overlap band"],
  "tables": ["table1_sample_and_structure.csv", "table2_abstraction_census.csv", "table3_main_models.csv",
             "table4_strata_by_repository.csv", "table5_robustness_inference.csv",
             "table6_baseline_comparison.csv", "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_abstraction_pairs.pdf", "fig2_main_effect.pdf",
              "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"],
 },
 # ------------------------------------------------------------------ T140
 "T140": {
  "pkg": "P065_what_a_compression_loses_first",
  "title": "Which Information Is Lost First in Agent Memory Compression?",
  "rq": "When only the opening fraction of a recorded search can be kept, which kinds of what it said survive, and do "
        "exceptions, negative constraints, provenance and uncertainty go first?",
  "hypotheses": [
   "H1 survival is unequal across the eight component categories at a 25% budget, and the exception, condition, "
   "provenance and uncertainty markers sit at the bottom of the ranking - the ordering this sentence freezes.",
   "H2 the ranking is not an artefact of where a category tends to appear: with each rollout's first-mention position "
   "for the category controlled, its survival still differs from the median.",
   "H3 losing a category is not the same as the rollout having one: the gap between an uncompressed and a compressed "
   "coding of the same rollout is reported per category with its interval, and the pairs where compression removes "
   "the exception category are the ones where the instance later fails, which is the claim H3 tests."],
  "features": {"survives_at_10": "the category still present when the first 10% of assistant turns are kept",
               "survives_at_25": "the same at a 25% budget", "survives_at_50": "the same at a 50% budget",
               "removal_by_compression": "present in the full text and absent in the compressed text",
               "first_mention_position": "the turn index of the category's first occurrence over turn count"},
  "dvs": {"survives_at_25": "H1's and H2's outcome", "removal_by_compression": "H3's outcome"},
  "models": ["per-category survival rate at each budget with a cluster bootstrap on instance_id, reported as a "
             "ranking",
             "the same rates with first-mention position controlled",
             "logistic on the instance's later failure with the removal indicator per category, clustered on "
             "instance_id"],
  "thresholds": {"support": "a survival gap of >= 0.15 between the best and worst category with intervals excluding "
                            "the median, or |beta| >= 0.15 for H3",
                 "partial": "the gap or coefficient excludes 0 below the floor", "null": "the intervals include it"},
  "family": "three",
  "gate_scope": "design",
  "kill_gate": ("G4 froze >= 500 rollouts with six or more assistant turns, below which a 10% budget is the whole "
                "text, and EXP-0207 measured 19,979; G11 froze >= 500 rollouts carrying a negative constraint and "
                "measured 8,715; G9, which scopes H2, froze >= 500 rollouts with uncertainty language and measured "
                "11,453. The compression is a deterministic re-coding of text the release already contains, not a "
                "re-running of the agent, which the programme forbids."),
  "strata": ["component category", "rollout-length quartile"],
  "tables": ["table1_sample_and_structure.csv", "table2_survival_census.csv", "table3_main_models.csv",
             "table4_strata_by_length.csv", "table5_robustness_inference.csv", "table6_baseline_comparison.csv",
             "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_survival_curves.pdf", "fig2_main_effect.pdf",
              "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"],
 },
 # ------------------------------------------------------------------ T142
 "T142": {
  "pkg": "P066_relation_classes_between_attempts_of_one_task",
  "title": "Semantic-Relation-Based Consolidation of Agent Organisational Memory",
  "rq": "Are the attempts of one task restatements, refinements or new approaches of each other, and does the "
        "relation predict which attempt finishes?",
  "hypotheses": [
   "H1 the three relation classes have measurable prevalence among consecutive attempts of an instance, reported with "
   "cluster bootstrap intervals on the instance, and no class is empty: the frozen floor is 5% of pairs in each of "
   "refinement and new.",
   "H2 a later attempt classified as a refinement ends Submitted more often than one classified as new, with length "
   "and the earlier attempt's own outcome controlled.",
   "H3 the relation adds beyond the pair's text overlap and beyond whether the earlier attempt succeeded: with both "
   "in the model the class term still separates, and removing it leaves a model that adds nothing."],
  "features": {"relation_class": "restatement, refinement or new by content-word Jaccard band",
               "contradiction_flag": "a negative-constraint count difference of at least two inside a non-new pair",
               "earlier_submitted": "the preceding attempt's own label", "pair_jaccard": "the overlap itself"},
  "dvs": {"submitted": "H2's and H3's outcome, on the later attempt of each pair"},
  "models": ["class prevalence with a cluster bootstrap on instance_id",
             "logistic on the later attempt's submitted label with class dummies, the earlier label, overlap and "
             "lengths, clustered on instance_id",
             "the same model without the class term, as the falsification arm"],
  "thresholds": {"support": "|beta| >= 0.15 with CI excluding 0 and p_holm < 0.05; H1's floor is a 0.05 share in "
                            "each of two named classes",
                 "partial": "CI excludes 0 below the floor", "null": "CI includes 0"},
  "family": "three",
  "gate_scope": "design",
  "kill_gate": ("G7 froze >= 200 task groups with two or more attempts for the classification to exist at all and "
                "EXP-0207 measured 1,775; G2's outcome coverage (20,000 of 20,000) is what scores each attempt. The "
                "submission rate is 2.8%, so the class contrast in H2 compares two thin cells against a large "
                "incomplete majority, and the counts are printed with the estimate rather than the comparison being "
                "softened."),
  "strata": ["repository prefix", "attempt-pair position"],
  "tables": ["table1_sample_and_structure.csv", "table2_relation_census.csv", "table3_main_models.csv",
             "table4_strata_by_repository.csv", "table5_robustness_inference.csv",
             "table6_baseline_comparison.csv", "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_relation_classes.pdf", "fig2_main_effect.pdf",
              "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"],
 },
}

# census key (a dotted path into its `measured` block) -> the name this freeze gives it, so EXP-0163 can rewrite the
# PREMISES literal below from the artefact rather than from a hand-kept copy.
PREMISE_MAP = {
 "rollouts_drawn": "rollouts_drawn", "rollouts_parsed": "rollouts_parsed",
 "median_assistant_turns": "median_assistant_turns", "mean_assistant_turns": "mean_assistant_turns",
 "mean_chars_of_agent_text": "mean_chars_of_agent_text", "outcome_label_share": "outcome_label_share",
 "submitted_share": "submitted_share", "task_instances": "task_instances",
 "instances_with_2plus_rollouts": "instances_with_2plus_rollouts",
 "instances_with_3plus_rollouts": "instances_with_3plus_rollouts",
 "max_rollouts_per_instance": "max_rollouts_per_instance", "repos_200plus_rollouts": "repos_200plus_rollouts",
 "distinct_repos": "distinct_repos", "rollouts_with_6plus_assistant_turns": "rollouts_with_6plus_turns",
 "rollouts_with_an_observation_after_a_command": "rollouts_with_an_observation",
 "median_component_kinds_per_rollout": "median_component_kinds",
 "rollouts_with_2plus_component_kinds": "rollouts_with_2plus_component_kinds",
 "rollouts_with_uncertainty_language": "rollouts_with_uncertainty",
 "rollouts_with_negative_constraints": "rollouts_with_negative_constraints",
 "rollouts_with_code_identifiers": "rollouts_with_identifiers",
 "mean_abstract_markers": "mean_abstract_markers", "mean_concrete_markers": "mean_concrete_markers"}

PREMISES = {
    "census": "EXP-0207 (EXP0207_wave11_premise_census_20260924T221408.json)",
    "transcribed_by": "02_shared_code/registry/refresh_wave_premises.py (EXP-0163); no number in this block is typed by hand",
    "measured": {
        "rollouts_drawn": 20000,
        "rollouts_parsed": 20000,
        "median_assistant_turns": 15.0,
        "mean_assistant_turns": 14.88,
        "mean_chars_of_agent_text": 4901.0,
        "outcome_label_share": 1.0,
        "submitted_share": 0.028,
        "task_instances": 1784,
        "instances_with_2plus_rollouts": 1775,
        "instances_with_3plus_rollouts": 1765,
        "max_rollouts_per_instance": 27,
        "repos_200plus_rollouts": 2,
        "distinct_repos": 805,
        "rollouts_with_6plus_turns": 19979,
        "rollouts_with_an_observation": 19995,
        "median_component_kinds": 6.0,
        "rollouts_with_2plus_component_kinds": 19887,
        "rollouts_with_uncertainty": 11453,
        "rollouts_with_negative_constraints": 8715,
        "rollouts_with_identifiers": 18711,
        "mean_abstract_markers": 2.071,
        "mean_concrete_markers": 18.095,
    },
    "gates": {
          "G10_agent_diversity_for_strata": {'blocks': ['T137', 'T138'], 'fires': True, 'measured': 1, 'note': "the estate's fixed 12-file draw is a single-scaffold corpus, so this gate is measured as one and is expected to fire; it scopes only the strata, and the stratum actually reported is the repository, which is named in every stratum row", 'rule': '>= 3 scaffold agents with >= 200 rollouts each, the stratum the carry-forward models report inside', 'scope': 'strata', 'threshold': 3},
          "G11_negative_constraints_present": {'blocks': ['T140'], 'fires': False, 'measured': 8715, 'rule': ">= 500 rollouts carrying a negative constraint, the class T140's hypothesis expects to be lost first", 'scope': 'H1', 'threshold': 500},
          "G12_source_diversity": {'blocks': ['T131', 'T137', 'T138', 'T140', 'T142'], 'fires': True, 'measured': 2, 'rule': ">= 3 sources with >= 200 rollouts each, so a pooled trajectory statistic is not one collection's artefact", 'scope': 'strata', 'threshold': 3},
          "G1_trajectories_readable": {'blocks': ['T131', 'T137', 'T138', 'T140', 'T142'], 'fires': False, 'measured': 20000, 'rule': '>= 1,000 parsed rollouts with at least one assistant turn', 'scope': 'design', 'threshold': 1000},
          "G2_outcome_label_populated": {'blocks': ['T131', 'T142'], 'fires': False, 'measured': 20000, 'rule': '>= 500 rollouts carry a non-null outcome label, which is what separates a successful from a failed discourse in T131 and scores an attempt in T142', 'scope': 'design', 'threshold': 500},
          "G3_repeated_attempts_of_one_task": {'blocks': ['T137', 'T138', 'T140', 'T142'], 'fires': False, 'measured': 1775, 'rule': '>= 300 tasks with two or more recorded attempts - the organisational memory the carry-forward designs read', 'scope': 'design', 'threshold': 300},
          "G4_trajectories_long_enough_to_compress": {'blocks': ['T140'], 'fires': False, 'measured': 19979, 'rule': '>= 500 rollouts with six or more assistant turns, below which a compression schedule has nothing to drop', 'scope': 'H1', 'threshold': 500},
          "G5_two_plus_component_kinds": {'blocks': ['T137'], 'fires': False, 'measured': 19887, 'rule': '>= 1,000 rollouts whose agent prose carries at least two of the eight frozen component categories, since T137 asks which kind carries forward', 'scope': 'H1', 'threshold': 1000},
          "G6_abstraction_contrast_computable": {'blocks': ['T138'], 'fires': False, 'measured': 18711, 'rule': '>= 1,000 rollouts containing at least one code identifier, the concrete end of the abstraction axis', 'scope': 'H1', 'threshold': 1000},
          "G7_relation_classes_computable": {'blocks': ['T142'], 'fires': False, 'measured': 1775, 'rule': '>= 200 task groups with two or more attempts, at which a relation between two attempts (restatement, refinement, distant) can be classified at all', 'scope': 'H1', 'threshold': 200},
          "G8_observation_pairs_present": {'blocks': ['T131'], 'fires': False, 'measured': 19995, 'rule': '>= 1,000 rollouts contain a user turn after an assistant command, i.e. a real observation the discourse responds to', 'scope': 'H2', 'threshold': 1000},
          "G9_provenance_and_uncertainty_language": {'blocks': ['T140'], 'fires': False, 'measured': 11453, 'rule': ">= 500 rollouts each carrying uncertainty language, which with the provenance and exception categories is what T140's H2 asks survives a compression", 'scope': 'H2', 'threshold': 500},
      },
    "verdict": {
          "blocked_gates": ['G10_agent_diversity_for_strata', 'G12_source_diversity'],
          "blocked_whole_design": [],
          "claim_limited": {'G10_agent_diversity_for_strata': 'strata', 'G12_source_diversity': 'strata'},
      },
    "note": "a fired gate is a result, not an obstacle: it stops exactly what its frozen sentence scopes",
    "runnable": list(RUNNABLE),
}    # filled verbatim from the census artefact - never edit these blocks by hand

FAILED_RUNS = [
 "EXP0207 was first written against open-thoughts/AgentTrove, the dataset the five topics were screened with, and ran "
 "three generations on that substrate "
 "(results_raw/EXP0207_wave11_premise_census_20260924T212549.json and its two successors): its first was a 300-row "
 "smoke and its later passes drew the first 12,000 rows of six shards, where every outcome column was null and no "
 "task appeared twice. Those generations are superseded by deviation W11-D02's substrate change; the whole-release "
 "AgentTrove scan that documents it is kept as "
 "results_raw/EXP0207_wave11_agenttrove_structure_scan_20260924T220813.json.",
]

EXTRA_DEVIATIONS = [
 ("W11-D01", "The census's first sampling rule for this wave was unrepresentative, and the fix was to measure the "
             "whole release before choosing",
             "The first three generations drew the first rows of six AgentTrove shards and reported no populated "
             "outcome column and no task attempted twice. A structure scan of all 38 shards - 1,696,847 rows, read "
             "without the conversation column - found 128,435 non-null task_binary, 218,706 non-null result and "
             "200,825 task prefixes attempted more than once, so the earlier reading was a property of the slice, not "
             "of the corpus. No gate threshold was touched; the sample rule was corrected, and the scan is kept as an "
             "artefact of EXP-0207 so the correction is checkable."),
 ("W11-D02", "The wave's substrate was changed before any outcome was estimated, and every threshold came with it",
             "AgentTrove carries the language these designs need, but a task-complete sample of it - both attempts of "
             "one task, read together - costs more to read than its information is worth: trajectories average 81,013 "
             "characters, and 1.7M rows are spread over 38 shards. The estate's fixed 12-file SWE-ZERO draw (seed 42, "
             "content-deduplicated, 20,000 rollouts, the same sample waves 6 and 9 used) carries an outcome on every "
             "rollout, 1,775 instances attempted more than once and 4,901 characters of agent prose per rollout. The "
             "gate rules and thresholds are the ones written for AgentTrove, re-measured here; what differs is only "
             "the corpus they are measured on, and the change was made after EXP-0207's structure work and before "
             "any design's dependent variable had been estimated. The abandoned substrate is documented by the scan "
             "named above rather than dropped."),
 ("W11-D03", "Two strata-scope gates fire, so this wave claims no cross-scaffold or cross-collection breadth",
             "G10 (>= 3 scaffold agents with 200 rollouts each) measured 1 and G12 (>= 3 sources with 200 rollouts "
             "each) measured 2 of 805 repository prefixes: the draw is one scaffold's rollouts over a few large "
             "repositories. Both gates are strata scope, so nothing here is blocked, but no sentence in this wave may "
             "be read as showing that these patterns hold across agents or across collections, and every stratum row "
             "names the repository prefix it was computed in."),
 ("W11-D04", "The release's own attempt order inside an instance is not recorded, so the frame fixes one",
             "Consecutive-attempt claims (T137, T138, T142) need an order among rollouts of one instance, and the "
             "release gives no sequence. The frame therefore records attempt_index as the draw's row order within the "
             "instance, established before any estimate and re-derived identically in every layer; a pair is only "
             "compared when both attempts exist, and the count of usable pairs is printed with each estimate."),
 ("W11-D05", "Two of T142's three hypotheses are not estimable, and the reason is reported as such",
             "T142's H2 and H3 ask whether a refinement of the earlier attempt finishes more often than a new "
             "approach. With 560 Submitted of 20,000 rollouts and 86% of pairs classified as refinement, the "
             "class term is perfectly predicted inside the outcome cell: the raw fit came back at beta = 18.89 with "
             "an interval from -283 to +321, which is quasi-separation and not an effect size. The fit now keeps the "
             "raw numbers in an `unidentified_estimate` field, sets the coefficient to null and the verdict to "
             "not_estimable_quasi_separation_in_this_cell, and no threshold was moved to make the term look "
             "estimable."),
 ("W11-D06", "Interval fields are per quantity only, never a range across quantities",
             "T137's H2 (the spread across categories) and T142's H1 (a floor on two classes) first carried ci_lo and "
             "ci_hi assembled from different rows' intervals, which reads as an interval of the reported quantity "
             "when it is a range across two of them. Both are now null, with the underlying per-category intervals kept "
             "in their own fields, because a claim has to be checkable against the interval that actually belongs to "
             "it."),
]
