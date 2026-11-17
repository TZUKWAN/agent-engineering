"""Frozen designs for wave 1 (T101, T103, T106, T108, T109, T110) - written before any outcome was read.

This file is the protocol freeze for six of the topics registered on 2026-09-23. It is deliberately the *first* thing
written for them: every hypothesis, feature definition, sample rule, seed, threshold, decision rule and kill gate is
fixed here, in code, before a single row of `question`/`target_tools` is opened, so no number below can be chosen after
seeing a result (the discipline spec §7 asks for and the one this programme has been burned by before).

What is already known at freeze time is only what the dataset audit manifests record - row counts, column names and
per-column non-empty ratios. No distribution of any dependent variable is known.

Shared substrate for all six (so the six do not silently measure one thing six times):

* one corpus: Toucan-1.5M, the four teacher configs, dev bucket only (P001's test split is never touched);
* one frozen retriever: the BM25 implementation P001 already shipped, same tokeniser, same k1/b, no tuning;
* one outcome per design, named in the design: `hit@k`/rank against `target_tools`, or a trajectory behaviour count;
* one clustering rule: every interval clusters on the prompt/instance the feature is computed from, never on rows;
* one correction rule: Holm across the family declared per design, fixed here.

    python 02_shared_code/package_factory/freeze_wave1.py        # writes each package's protocol_freeze.md
"""
from __future__ import annotations

SEED = 42
SAMPLE = dict(rows_per_config=8000, configs=("OSS", "Qwen3", "Kimi-K2"), bucket="dev",
              rule="random.Random(42).sample over the rows the builder marks as dev, taken once per config; "
                   "shard ids are recorded in the raw artefact")
BANDS = dict(small=0.05, medium=0.15, large=0.30)     # effect-size bands used by every verdict here

# --------------------------------------------------------------------------------------------- designs
DESIGNS = {
 "T101": dict(
   pkg="P006_underspecified_needs",
   title="How Underspecified Information Needs Shape Agentic Information Seeking",
   rq="RQ1 does linguistic underspecification in the instruction change how much an agent searches, whether it asks, "
       "and how often it selects a wrong tool?",
   hypotheses=[
     "H1 instructions with more unresolved references and fewer stated constraints produce deeper search "
     "(more turns before the terminal action) - positive on the depth DV",
     "H2 underspecification raises the rate of clarification turns before any tool call",
     "H3 underspecification raises the wrong-tool rate against target_tools under the frozen retriever",
   ],
   features={
     "constraint_count": "count of explicit constraint markers: temporal, entity, numeric, format, scope, negation "
                         "(rule lexicons listed in the freeze)",
     "unresolved_reference": "third-person/anaphoric object nouns ('it', 'they', 'the file', 'that one') with no "
                             "instructive antecedent in the same sentence, by rule",
     "ellipsis": "imperative with an omitted object, detected by verb-transitivity lexicon",
     "entity_density": "distinct proper-noun-like tokens per 100 chars (regex, no NER model)",
     "underspec_index": "z-scored mean of the four above, sign-fixed here: higher = less specified",
   },
   dvs={"search_depth": "turns from the start of the trajectory to the terminal action",
        "clarification_rate": "share of trajectories with a clarification turn before any tool call",
        "wrong_tool_rate": "share of selected tools not in target_tools"},
   models=["mixed-effects logistic (wrong tool) and Poisson (depth) with query nested in catalogue, per P001's "
           "dependence correction"],
   thresholds=dict(support="|beta| >= 0.15 (medium band) AND the prompt-clustered 95% CI excludes 0 AND p_holm < 0.05",
                   partial="direction correct and CI excludes 0 but |beta| < 0.15",
                   null="CI includes 0"),
   family=3,   # H1..H3, Holm across them
   kill_gate="if the underspec index correlates with instruction length at |rho| >= 0.8, the construct is a length "
             "proxy and the topic is reported as unidentifiable rather than as a finding",
   tables=["table1_sample_and_structure.csv", "table2_underspec_distribution.csv",
           "table3_main_models.csv", "table4_strata_by_length.csv", "table5_robustness_inference.csv",
           "table6_baseline_comparison.csv", "table7_experiment_provenance.csv", "table_run_cost.csv"],
   figures=["fig0_framework.pdf", "fig1_underspec_examples.pdf", "fig2_main_effect.pdf",
            "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"]),

 "T103": dict(
   pkg="P007_constraint_density",
   title="Constraint Density in Task Language as a Determinant of Information-Search Complexity",
   rq="RQ1 does the number of independent semantic constraints in a task statement predict the structure of the "
      "search that follows, beyond task difficulty as shipped?",
   hypotheses=[
     "H1 constraint density predicts search breadth (distinct tools/sources touched) monotonically",
     "H2 constraint density predicts search depth, and the relation is steeper than for breadth",
     "H3 constraint density adds explanatory power over the release's own difficulty field (nested-model comparison)",
   ],
   features={
     "constraint_density": "count of constraint clauses by type (temporal, entity, conditional, relational, "
                           "operational), extracted by rule from the question text",
     "difficulty_control": "the release's own q_* fields, used only as a covariate, never as the IV",
   },
   dvs={"breadth": "distinct tools or files touched per trajectory", "depth": "turns to terminal action",
        "reformulation": "count of near-duplicate self-queries (cosine >= 0.85 on the frozen tokeniser)"},
   models=["mixed-effects ordinal/linear per DV with query nested in catalogue; nested-model likelihood-ratio for H3"],
   thresholds=dict(support="partial R^2 gain >= 0.01 for H3 and CI excludes 0 for H1/H2 with |beta| >= 0.15",
                   partial="CI excludes 0 but the gain is < 0.01", null="CI includes 0"),
   family=3,
   kill_gate="if constraint density is collinear with token count (VIF >= 10) the construct is redefined once, on "
             "record, to the count of constraint *types* rather than clauses, and the change is logged as a deviation",
   tables=["table1_sample_and_structure.csv", "table2_density_by_type.csv", "table3_main_models.csv",
           "table4_nested_model_comparison.csv", "table5_robustness_inference.csv",
           "table6_baseline_comparison.csv", "table7_experiment_provenance.csv", "table_run_cost.csv"],
   figures=["fig0_framework.pdf", "fig1_density_examples.pdf", "fig2_dose_response.pdf",
            "fig3_breadth_vs_depth.pdf", "fig4_robustness.pdf"]),

 "T106": dict(
   pkg="P008_query_reformulation_fidelity",
   title="Information Loss from User Question to Machine Query: Semantic Fidelity in Agent Reformulation",
   rq="RQ1 which linguistic material survives the transformation from the user's question to the query the agent "
      "actually issues, and does loss predict failure?",
   hypotheses=[
     "H1 entity retention is high and constraint retention is materially lower (paired comparison within trajectory)",
     "H2 lower constraint retention raises the wrong-tool rate",
     "H3 coreference introduced by the reformulation ('it', 'this') predicts retrieval failure more than length does",
   ],
   features={
     "entity_retention": "share of distinct entities in the question that appear in any issued query (string + "
                         "normalised surface forms)",
     "constraint_retention": "share of question constraint clauses with a matching element in an issued query",
     "relation_retention": "share of question predicate-argument pairs preserved in a query",
     "introduced_coreference": "count of anaphora in issued queries whose antecedent is not in the query itself",
   },
   dvs={"wrong_tool_rate": "as T101", "outcome": "exit/label available in the release for the trajectory"},
   models=["paired bootstrap within trajectory for H1; mixed-effects logistic for H2/H3, prompt-clustered CIs"],
   thresholds=dict(support="H1 paired difference >= 0.10 with CI excluding 0; H2/H3 |beta| >= 0.15 with CI excluding "
                           "0 and p_holm < 0.05", partial="CI excludes 0 below the magnitude floor",
                   null="CI includes 0"),
   family=3,
   kill_gate="if no issued query can be recovered for >= 20% of trajectories, the fidelity construct is not "
             "measurable on this release and the paper reports the measurement limit instead of a result",
   tables=["table1_sample_and_structure.csv", "table2_retention_summary.csv", "table3_paired_losses.csv",
           "table4_main_models.csv", "table5_robustness_inference.csv", "table6_baseline_comparison.csv",
           "table7_experiment_provenance.csv", "table_run_cost.csv"],
   figures=["fig0_framework.pdf", "fig1_reformulation_examples.pdf", "fig2_retention_ladder.pdf",
            "fig3_loss_vs_failure.pdf", "fig4_robustness.pdf"]),

 "T108": dict(
   pkg="P009_lexical_match_bias",
   title="Lexical-Match Bias in Machine Relevance Judgment",
   rq="RQ1 does the agent (and the frozen retriever) judge a tool relevant because its description shares words with "
      "the instruction rather than because it does the job?",
   hypotheses=[
     "H1 selection probability rises with lexical overlap even holding gold relevance fixed (bias term)",
     "H2 high-overlap non-gold tools are chosen more often than low-overlap non-gold tools (decoy asymmetry)",
     "H3 the bias is larger for instructions with more underspecification (interaction with T101's index, tested as "
     "a covariate here, not as a duplicate)",
   ],
   features={
     "lexical_overlap": "BM25(query, tool description) on the frozen retriever",
     "gold_relevance": "membership in target_tools (the release's own label)",
     "decoy_class": "non-gold tools split into high/low overlap by the median computed on the sample",
   },
   dvs={"selected": "whether the tool was the one acted on / retrieved at rank 1"},
   models=["conditional logistic within query; two-way overlap x gold table with Fisher exact per stratum"],
   thresholds=dict(support="bias coefficient |beta| >= 0.15 with prompt-clustered CI excluding 0 and p_holm < 0.05",
                   partial="CI excludes 0 below the floor", null="CI includes 0"),
   family=3,
   kill_gate="if overlap and gold relevance are so entangled that no high-overlap non-gold pair exists in >= 300 "
             "queries, the bias is not identifiable here and the design is reported as infeasible",
   tables=["table1_sample_and_structure.csv", "table2_overlap_gold_contingency.csv", "table3_main_models.csv",
           "table4_decoy_asymmetry.csv", "table5_robustness_inference.csv", "table6_baseline_comparison.csv",
           "table7_experiment_provenance.csv", "table_run_cost.csv"],
   figures=["fig0_framework.pdf", "fig1_contingency.pdf", "fig2_bias_by_overlap.pdf",
            "fig3_decoy_asymmetry.pdf", "fig4_robustness.pdf"]),

 "T109": dict(
   pkg="P010_lexical_semantic_conflict",
   title="When Semantic and Lexical Relevance Conflict",
   rq="RQ1 when the lexical and the distributional account of relevance disagree, which one does the agent follow, "
      "and does the answer depend on the tool's description length?",
   hypotheses=[
     "H1 on conflict cases (high lexical / low semantic or the reverse) the agent follows lexical more often than "
     "chance",
     "H2 the split is moderated by catalogue size (more candidates, more lexical defaulting)",
     "H3 the retriever's own rank and the agent's choice disagree systematically on the conflict set, and the "
     "disagreement is characterised rather than averaged away",
   ],
   features={
     "lexical_relevance": "BM25 as in T108",
     "semantic_relevance": "cosine on the locally run pretrained encoder (the P001 E03c recipe), never an API call",
     "conflict_set": "queries where the two rankings put different tools first",
   },
   dvs={"agent_follows": "which of the two candidate tools the trajectory acted on"},
   models=["exact binomial against chance for H1; mixed-effects logistic with catalogue size for H2; agreement "
           "statistics (kappa, disagreement census) for H3"],
   thresholds=dict(support="H1 proportion >= 0.6 with CI excluding chance; H2 |beta| >= 0.15 with CI excluding 0; "
                           "H3 kappa <= 0.6 on the conflict set with a characterised pattern",
                   partial="CI excludes the null below the magnitude floor", null="CI includes the null"),
   family=3,
   kill_gate="if the conflict set is smaller than 200 queries the design is reported as underpowered and no "
             "directional claim is made",
   tables=["table1_sample_and_structure.csv", "table2_conflict_census.csv", "table3_main_models.csv",
           "table4_catalogue_size_strata.csv", "table5_robustness_inference.csv", "table6_baseline_comparison.csv",
           "table7_experiment_provenance.csv", "table_run_cost.csv"],
   figures=["fig0_framework.pdf", "fig1_conflict_map.pdf", "fig2_follow_rates.pdf",
            "fig3_by_catalogue_size.pdf", "fig4_robustness.pdf"]),

 "T110": dict(
   pkg="P011_predicate_argument_relevance",
   title="Predicate-Argument Structure as a Predictor of Tool Relevance Beyond Text Similarity",
   rq="RQ1 does matching the task's predicate and its arguments to the ability structure in a tool description "
      "predict relevance better than bag-of-words similarity?",
   hypotheses=[
     "H1 predicate-argument fit predicts gold relevance after controlling for BM25 and encoder similarity",
     "H2 predicate fit and argument fit have separable effects (argument fit dominates when the catalogue is dense)",
     "H3 the gain over text similarity is largest on instructions with high constraint density (cross-reference to "
     "T103, tested as an interaction here)",
   ],
   features={
     "predicate_fit": "overlap between the task's main verb lemma set and the verb set in the tool description "
                      "(WordNet-style lemma groups held as a rule lexicon in the freeze)",
     "argument_fit": "compatibility between the task's direct-object head nouns and the description's object nouns",
     "controls": "BM25 and encoder cosine, both computed as in T108/T109",
   },
   dvs={"gold_relevance": "membership in target_tools"},
   models=["nested logistic models (similarity only, + predicate, + argument) with prompt-clustered CIs and "
           "likelihood-ratio tests; AUROC comparison"],
   thresholds=dict(support="delta AUROC >= 0.02 with CI excluding 0 for the added structure, and LR test p_holm < "
                           "0.05", partial="significant but below the AUROC floor", null="CI includes 0"),
   family=3,
   kill_gate="if the verb/object lexicons cover < 50% of the sampled descriptions, the construct is a coverage "
             "artefact; the coverage number is reported and the claim is capped accordingly",
   tables=["table1_sample_and_structure.csv", "table2_lexicon_coverage.csv", "table3_nested_models.csv",
           "table4_auroc_comparison.csv", "table5_robustness_inference.csv", "table6_baseline_comparison.csv",
           "table7_experiment_provenance.csv", "table_run_cost.csv"],
   figures=["fig0_framework.pdf", "fig1_examples.pdf", "fig2_nested_gain.pdf", "fig3_coverage_vs_effect.pdf",
            "fig4_robustness.pdf"]),
}

COMMON = dict(seed=SEED, sample=SAMPLE, bands=BANDS,
              notes="No model inference API is called anywhere in wave 1. The only pretrained component is the "
                    "encoder P001 already runs locally (EXP-0061 recipe). Every dependent variable is computed from "
                    "columns the release ships; nothing is labelled by a judge.")

# --------------------------------------------------------------------------------- premise census and amendment
# EXP-0118 read the structure of the columns these designs depend on before any dependent variable was computed.
# It found that Toucan's `messages` is a synthetic user/assistant/`function` dialogue that *produces* the query, not an
# agent execution trajectory, and that the tool-call marker is present in 1.000/1.000 of OSS/Qwen3 rows but only
# 0.055 of Kimi-K2 rows. Three designs assumed agent-side trajectory DVs, so they are re-scoped here - before any
# outcome distribution was seen - and the change is logged as a deviation in each package.
PREMISES = dict(
  census="results_raw/EXP0118_wave1_premise_census_*.json",
  measured={"tool_call_marker_share": {"OSS": 1.0, "Qwen3": 1.0, "Kimi-K2": 0.055},
            "observation_marker_share": {"OSS": 0.0025, "Qwen3": 0.0085, "Kimi-K2": 0.0125},
            "clarification_marker_share": {"OSS": 0.4343, "Qwen3": 0.2375, "Kimi-K2": 0.1835},
            "roles": ["assistant", "function", "system", "user"], "turns_gt_2_share": 1.0},
  verdict_trajectory_dvs="NOT measurable as agent-search behaviour on Toucan; the `function` role carries tool "
                         "responses, so dialogue-side turns are measurable but executed-search depth is not",
  amendments={
    "T101": "H1's depth DV becomes dialogue turns before the query is issued (measurable), and the executed-search "
            "depth claim is dropped rather than proxied; wrong-tool and clarification DVs stand as frozen",
    "T103": "breadth/depth DVs become retriever-side - candidates inspected to reach gold and gold rank under the "
            "frozen BM25 - because the release has no executed search to measure",
    "T106": "moved to hermes-agent-reasoning-traces, whose conversations carry the issued tool calls; Toucan ships "
            "no distinct machine query to compare against the question, so fidelity is unmeasurable there",
  },
  deviation_note="logged per package as a protocol amendment made after a structure census and before any outcome "
                 "was read; the thresholds, seeds, family sizes and kill gates were not touched by it")



# topic -> the experiment that carries its pre-registered test (see the wave docstrings for what each ran)
EXP_OF = {"T101": "EXP-0121", "T103": "EXP-0122", "T106": "EXP-0123",
          "T108": "EXP-0124", "T109": "EXP-0125", "T110": "EXP-0126"}
MATRIX = "results_raw/EXP0119_wave1_feature_matrix_*.json"
BATTERY = "results_raw/EXP0128_wave1_battery_0128_*.json"
RUNNABLE = ("T101", "T103", "T106", "T108", "T109", "T110")
