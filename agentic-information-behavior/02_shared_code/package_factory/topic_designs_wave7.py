"""The wave-7 protocol freeze: the lexical ecosystem a tool catalogue is made of.

Six designs (T161 near-synonym decoys, T162 affordance language in descriptions, T164 namespaces and overload,
T165 the catalogue population as an ecosystem of sources, T166 irrelevant-information contamination of the ranking,
T169 which tools are needed together). The substrate is P001's routing release again, for one reason: it is the only
local corpus whose rows carry a *candidate set* - the names, descriptions and parameter lists an agent chooses
between - together with a frozen ranker's behaviour on it.

That boundary is stated in every design before any estimate: this release records no agent choice. Its outcome
columns are the shipped BM25 rank, margin and fail-at-k of the gold tool inside the candidate list, so a wave-7
coefficient is a statement about what a lexical ranker does with a catalogue's language, which is what these six
titles are actually about, and no design claims an agent's decision was measured.

Every threshold, band, direction and kill-gate sentence was written before the frame was built, and each gate cites
the value EXP-0181 measured for it. The census ran twice with identical output.
"""
from __future__ import annotations

EXP_OF = {"T161": "EXP-0183", "T162": "EXP-0184", "T164": "EXP-0185", "T165": "EXP-0186", "T166": "EXP-0187",
          "T169": "EXP-0188"}
RUNNABLE = tuple(EXP_OF)
FEATURE_EXP = "EXP-0182"
PREMISE_EXP = "EXP-0181"
BATTERY_EXP = "EXP-0189"
ENCODER_EXP = ""
SEED = 42
BANDS = {"small": 0.05, "medium": 0.15, "large": 0.30}
MATRIX = "results_raw/EXP0182_wave7_candidate_matrix_*.json"
PREMISE_GLOB = "results_raw/EXP0181_wave7_premise_census_*.json"
BATTERY = "results_raw/EXP0189_wave7_battery_0189_*.json"
MATRIX_GLOB = MATRIX
BATTERY_GLOB = BATTERY
ENCODER_GLOB = ""
MATRIX_SCRIPT = "exp_wave7_features.py"
BATTERY_SCRIPT = "exp_wave7_battery.py"
PROBE_SCRIPT = "probe_wave7_premises.py"
SCRIPT_OF = {t: "exp_wave7_designs.py" for t in RUNNABLE}
MAIN_SCRIPT_OF = {t: "exp_wave7_designs.py" for t in RUNNABLE}
DESIGNS_MODULE = "topic_designs_wave7"
STAGE_RX = "wave7_main"
CLEAN_ROOM_ONLY_FLAG = "--only"
CLEAN_ROOM_MODE = "full"
SUBSTRATE_LABEL = ("P001's routing release, dev split only, all three configs (OSS, Qwen3, Kimi-K2): 31,642 rows, "
                   "each an agent instruction with the candidate tool catalogue it was offered - the shipped "
                   "catalogue parser reads none of these rows because the release stores n/d/p rather than "
                   "name/description, so the wave brings its own reader (EXP-0181 reports both coverages); the "
                   "frozen BM25 rank, margin and fail-at-k of the gold tool are the only recorded outcome")
SAMPLE_FIELDS = ("corpus", "rows", "by_config", "median_candidates", "mean_candidates", "distinct_tools",
                 "distinct_servers", "catalogue_parse_share", "gold_index_recoverable_share",
                 "ranker_columns_present_share", "cluster_unit")
CONTRIBUTION_POPULATION = ("a corpus of agent instructions each paired with the tool catalogue it was offered and a "
                           "frozen lexical ranker's ordering of that catalogue - read with rule and lexical "
                           "instruments, with no model, no reranker and no recorded agent choice")

COMMON = {
    "seed": SEED,
    "bands": BANDS,
    "module": "topic_designs_wave7",
    "sample": {"traj_cap": 31642, "cluster_unit": "query_id",
              "unit_of_analysis": "the query, with its candidate set measured per candidate",
              "rule": "every dev row of all three configs, no subsample: the release is small enough to read whole, "
                      "so the wave's clusters are the queries it has rather than a draw from them; the split filter "
                      "is an assertion in wave_lib.load_routing, which raises if any test row is present",
              "excluded": "P001's test split - load_routing keeps only rows whose split field is dev and reports the "
                          "counts it dropped"},
    "instruments": ("candidate names are split into a namespace prefix and a local name on `.`/`_`/`::`; a "
                    "description's content words are its lower-cased alphanumeric tokens minus the frozen stop list; "
                    "affordance language is the frozen 38-verb list; a decoy is a non-gold candidate whose "
                    "description shares >= 0.5 of its content words with some gold candidate's description; "
                    "contamination is a candidate with no content-word overlap with the question that the ranker "
                    "placed above every gold one"),
}

DESIGNS = {
 # ------------------------------------------------------------------ T161
 "T161": {
  "pkg": "P039_semantic_decoy_and_misselection",
  "title": "The Semantic Decoy Effect: Why Near-Synonym Tools Cause Misselection",
  "rq": "When a candidate list contains a non-gold tool whose description is lexically almost the same as the gold "
        "tool's, does the frozen ranker miss the gold tool more often, and by how much does the effect grow with the "
        "number of such look-alikes?",
  "hypotheses": [
   "H1 a query whose candidate set contains at least one near-synonym decoy is more likely to have its gold tool "
   "missed at rank 1 than a query with none, holding the catalogue size and the question's length fixed.",
   "H2 the effect is a dose-response in the number of decoys, not a threshold: the mean fail-at-1 rate is reported "
   "by decoy count with a cluster-robust interval per count, and it should rise monotonically.",
   "H3 the decoy contrast is not simply 'more candidates': with the candidate count and the gold description's length "
   "controlled, a decoy's presence still separates, and the same specification with the decoy measure replaced by a "
   "randomly chosen non-gold candidate's similarity to the question produces nothing."],
  "features": {
   "decoy_present": "1 if some non-gold candidate's description shares >= 0.5 of its content words with a gold "
                    "candidate's description",
   "decoy_count": "how many non-gold candidates meet that threshold, capped at 5 for the dose-response rows",
   "max_similarity": "the largest such similarity among non-gold candidates, the continuous form of the same measure",
   "control_similarity": "the same similarity computed against one non-gold candidate chosen by the query's own "
                         "digest, not by maximising it - the specificity arm"},
  "dvs": {"fail_at_1": "H1's and H3's outcome: the frozen ranker put no gold tool first",
          "bm25_best_rank": "H2's outcome, as the rank the decoy pressure has to move"},
  "models": [
   "logistic on fail_at_1 with the decoy indicator plus the standard controls, clustered on query_id",
   "the fail-at-1 rate by decoy count with a cluster bootstrap interval per count, reported as a measured profile",
   "logistic on fail_at_1 with the control similarity plus the standard controls, the specificity arm"],
  "thresholds": {"support": "|beta| >= 0.15 with CI excluding 0 and p_holm < 0.05",
                 "partial": "CI excludes 0 below the floor", "null": "CI includes 0"},
  "family": "three",
  "gate_scope": "design",
  "kill_gate": ("G1 (>= 0.95 of catalogues parseable), G2 (>= 0.95 of gold index lists recoverable) and G4 (>= 200 "
                "queries carrying a near-synonym decoy) froze this design's subject. EXP-0181 measured 1.0, 1.0 and "
                "13,698, so the design stands."),
  "strata": ["candidate-count quartile", "config"],
  "tables": ["table1_sample_and_structure.csv", "table2_decoy_census.csv", "table3_main_models.csv",
             "table4_strata_by_candidate_count.csv", "table5_robustness_inference.csv",
             "table6_baseline_comparison.csv", "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_decoy_examples.pdf", "fig2_main_effect.pdf", "fig3_mechanism_by_band.pdf",
              "fig4_robustness.pdf"],
 },
 # ------------------------------------------------------------------ T162
 "T162": {
  "pkg": "P040_affordance_language_and_selection",
  "title": "Affordance Language in Tool Descriptions and Its Effect on Selection",
  "rq": "Does a gold tool whose description states what it can do - and lists the parameters it takes - get found "
        "more easily by a lexical ranker than one whose description is terse or nominal?",
  "hypotheses": [
   "H1 a gold description with more affordance verbs per content word is less likely to be missed at rank 1, "
   "holding catalogue size and question length fixed.",
   "H2 parameter lists behave the same way: a gold candidate that names its inputs is easier to rank first, because "
   "the words an agent searches with are parameter names.",
   "H3 the two are not the same signal: with affordance density in the model, parameter presence still adds, and the "
   "description's length alone adds nothing once both are in."],
  "features": {
   "affordance_density": "affordance-verb occurrences per content word in the gold description",
   "gold_has_params": "1 if the gold candidate lists at least one parameter",
   "gold_param_words": "content words contributed by the gold candidate's parameter names",
   "desc_words": "content words in the gold description"},
  "dvs": {"fail_at_1": "H1's to H3's outcome: the frozen ranker put no gold tool first",
          "bm25_margin": "the ranker's own separation between its best and second-best candidate, reported beside "
                         "the rank so a margin effect is not read as a correctness effect"},
  "models": [
   "logistic on fail_at_1 with affordance density plus the standard controls, clustered on query_id",
   "logistic on fail_at_1 with the parameter indicators plus the standard controls, clustered on query_id",
   "logistic on fail_at_1 with density, parameters and description length together, so each is estimated with the "
   "others held"],
  "thresholds": {"support": "|beta| >= 0.15 with CI excluding 0 and p_holm < 0.05",
                 "partial": "CI excludes 0 below the floor", "null": "CI includes 0"},
  "family": "three",
  "gate_scope": "H3",
  "kill_gate": ("G5 froze >= 0.30 of descriptions carrying an affordance verb (measured 0.711) and G12 >= 0.30 "
                "carrying a parameter list (measured 0.8505), so both arms of the construct exist; H3 is additionally "
                "scoped to the collinearity of the two measures, which the artefact reports whether or not it bites."),
  "strata": ["catalogue-size quartile", "config"],
  "tables": ["table1_sample_and_structure.csv", "table2_affordance_census.csv", "table3_main_models.csv",
             "table4_strata_by_catalogue_size.csv", "table5_robustness_inference.csv",
             "table6_baseline_comparison.csv", "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_affordance_examples.pdf", "fig2_main_effect.pdf",
              "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"],
 },
 # ------------------------------------------------------------------ T164
 "T164": {
  "pkg": "P041_tool_namespace_and_candidate_overload",
  "title": "Does a Tool Namespace Reduce Information Overload?",
  "rq": "When the same number of tools is offered under a namespace that groups them, is the ranking easier - or "
        "does grouping only relabel the same competition while the candidate count does the work?",
  "hypotheses": [
   "H1 within a query of fixed candidate count, a higher share of namespaced candidate names is associated with "
   "fewer misses at rank 1.",
   "H2 the overload effect is the candidate count itself: moving from the first to the fourth quartile of catalogue "
   "size raises the miss rate, and that association is reported separately from the namespace share so one cannot be "
   "credited to the other.",
   "H3 namespace grouping concentrates the candidate set within fewer servers, and it is that concentration - fewer "
   "distinct sources at the same count - that carries whatever effect H1 finds; with distinct servers in the model, "
   "the namespace share falls to nothing."],
  "features": {
   "namespaced_share": "share of the query's candidates whose name carries a namespace separator",
   "candidate_count": "how many tools the query was offered",
   "distinct_servers": "how many namespace prefixes the candidate names resolve to",
   "server_concentration": "1 - distinct servers / candidates, the concentration the freeze's H3 names"},
  "dvs": {"fail_at_1": "H1's and H2's outcome", "bm25_margin": "H3's secondary reading of ranking difficulty"},
  "models": [
   "logistic on fail_at_1 with namespaced share, the log candidate count and the standard controls, clustered on "
   "query_id",
   "the same model with candidate count as a quartile factor instead of a log term",
   "the same model with distinct servers and server concentration added, so the grouping mechanism and the count "
   "mechanism compete inside one specification"],
  "thresholds": {"support": "|beta| >= 0.15 with CI excluding 0 and p_holm < 0.05",
                 "partial": "CI excludes 0 below the floor", "null": "CI includes 0"},
  "family": "three",
  "gate_scope": "H1",
  "kill_gate": ("G3 froze >= 0.05 of candidate names carrying a namespace separator, because without a grouped arm "
                "there is no namespace to evaluate. EXP-0181 measured 0.6248, so the contrast is well populated; "
                "H1's frozen floor is the separator share and nothing else, and this sentence states that the "
                "62% figure means most catalogues are already grouped, so the ungrouped arm is the minority."),
  "strata": ["candidate-count quartile", "server-count quartile"],
  "tables": ["table1_sample_and_structure.csv", "table2_namespace_census.csv", "table3_main_models.csv",
             "table4_strata_by_server_count.csv", "table5_robustness_inference.csv",
             "table6_baseline_comparison.csv", "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_namespace_examples.pdf", "fig2_main_effect.pdf",
              "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"],
 },
 # ------------------------------------------------------------------ T165
 "T165": {
  "pkg": "P042_the_catalogue_ecosystem",
  "title": "Have MCP Servers Become a Machine Information-Source Ecosystem?",
  "rq": "Across every candidate set the release offers, do tool names and descriptions cluster by their server the "
        "way sources specialise, or is each server a re-labelled copy of the others?",
  "hypotheses": [
   "H1 descriptions published by the same server share more content words with each other than descriptions from two "
   "randomly paired servers do: specialisation, measured as a within-versus-across overlap difference with a "
   "cluster bootstrap on the server.",
   "H2 the ecosystem is not concentrated: the Herfindahl index over servers, and the share of candidates contributed "
   "by the twelve largest, are reported as measured structure rather than as a hypothesis about a rank.",
   "H3 near-duplicate tool *names* recur across different servers (the same verb-object naming in more than one "
   "place), and the count of names published by >= 2 servers is reported next to the number of distinct names, so "
   "'many sources' and 'many distinct services' are not conflated."],
  "features": {
   "within_server_overlap": "mean content-word Jaccard between descriptions of candidates sharing a server, sampled "
                            "per server with a seeded draw of 40 pairs",
   "across_server_overlap": "the same measure for pairs drawn from different servers, same seed and pair count",
   "server_hhi": "sum of squared candidate shares over servers",
   "name_reuse": "how many local tool names (the part after the namespace) appear under >= 2 servers"},
  "dvs": {"overlap_difference": "H1's estimand: within minus across, bootstrapped on the server",
          "structure": "H2's and H3's estimands, which are counts and indices rather than modelled outcomes"},
  "models": [
   "cluster bootstrap of the within-minus-across description overlap, resampling servers, with the interval and the "
   "number of servers",
   "the measured concentration table: server shares, HHI, top-12 share, candidate and tool counts, without a "
   "coefficient",
   "the name-reuse counts by naming pattern, reported as a census"],
  "thresholds": {"support": "|difference| >= 0.15 with CI excluding 0 and p_holm < 0.05",
                 "partial": "CI excludes 0 below the floor", "null": "CI includes 0",
                 "h2_and_h3": "descriptive: the frozen sentence asks for a measured quantity, so no band applies and "
                              "none is invented"},
  "family": "three",
  "gate_scope": "design",
  "kill_gate": ("G9 froze >= 30 distinct namespace prefixes as the floor for calling this population an ecosystem. "
                "EXP-0181 measured 2,055 across 4,161 distinct tool names, so the design stands; the same census "
                "measured a server Herfindahl of 0.007, which is reported as the concentration fact H2 asks for."),
  "strata": ["server size decile"],
  "tables": ["table1_sample_and_structure.csv", "table2_ecosystem_census.csv", "table3_main_models.csv",
             "table4_strata_by_server_size.csv", "table5_robustness_inference.csv",
             "table6_baseline_comparison.csv", "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_ecosystem_structure.pdf", "fig2_main_effect.pdf",
              "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"],
 },
 # ------------------------------------------------------------------ T166
 "T166": {
  "pkg": "P043_irrelevant_candidate_contamination",
  "title": "How Irrelevant-Information Contamination Affects Agentic Decisions",
  "rq": "How often does a candidate with nothing in common with the request sit above everything the ground truth "
        "marks correct, and when it does, is the whole ranking flatter?",
  "hypotheses": [
   "H1 a query whose ranking places a zero-overlap candidate above every gold tool shows a smaller separation "
   "between its best and second-best scores than a query without one.",
   "H2 the share of such contaminated queries, and the share of candidates inside them that are zero-overlap, are "
   "reported per config rather than pooled, because the three configs share the candidate sets but not the "
   "instructions.",
   "H3 among the contaminated queries, the number of zero-overlap candidates ranked above the gold one rises with the "
   "catalogue size, so contamination is an overload phenomenon and not a property of the instruction."],
  "features": {
   "contaminated": "1 if some candidate with no content-word overlap with the question is ranked above every gold "
                   "candidate by the frozen ranker",
   "irrelevant_above_gold": "how many such candidates are ranked above the gold one",
   "bm25_margin": "the shipped separation between the top two scores",
   "irrelevant_share": "share of the query's candidates with no content-word overlap with the question"},
  "dvs": {"bm25_margin": "H1's outcome, standardised for the band test",
          "contaminated": "H3's outcome, modelled as a count of contaminating candidates"},
  "models": [
   "OLS on standardised margin with the contamination indicator plus the standard controls, clustered on query_id",
   "the contaminated share and the irrelevant-candidate share measured inside each config, with a cluster bootstrap",
   "a count model (Poisson) on irrelevant_above_gold with the log candidate count plus the standard controls, "
   "clustered on query_id"],
  "thresholds": {"support": "|beta| >= 0.15 with CI excluding 0 and p_holm < 0.05",
                 "partial": "CI excludes 0 below the floor", "null": "CI includes 0"},
  "family": "three",
  "gate_scope": "H1",
  "kill_gate": ("G8 froze >= 0.10 of queries having a zero-overlap candidate ranked above every gold one. EXP-0181 "
                "measured 0.0933 on all 31,642 dev rows - 2,953 queries, which is a large cell in absolute terms but "
                "below the share this sentence fixed - so H1 is reported as limited by its own rule and the measured "
                "share and count are printed beside that verdict. H2 and H3 stand on the same rows without a floor."),
  "strata": ["config", "candidate-count quartile"],
  "tables": ["table1_sample_and_structure.csv", "table2_contamination_census.csv", "table3_main_models.csv",
             "table4_strata_by_candidate_count.csv", "table5_robustness_inference.csv",
             "table6_baseline_comparison.csv", "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_contamination_examples.pdf", "fig2_main_effect.pdf",
              "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"],
 },
 # ------------------------------------------------------------------ T169
 "T169": {
  "pkg": "P044_tool_dependency_network",
  "title": "The Tool-Dependency Network in Multi-Tool Tasks",
  "rq": "When a task needs several tools, are the needed pairs arbitrary combinations or a structure - do the pairs "
        "that recur together also look alike, and does a frequent pair get found more easily?",
  "hypotheses": [
   "H1 a query whose gold tools form a pair that has been needed together often is less likely to be missed at rank "
   "1 than a query needing a pair that has rarely or never recurred, holding catalogue size fixed.",
   "H2 frequently co-needed tool pairs have more similar descriptions than random pairs of the same tools' neighbours, "
   "measured as a within-frequency minus random-pair overlap difference with a bootstrap on the pair.",
   "H3 the network is sparse and its degree is concentrated: the number of distinct gold pairs against the number of "
   "possible ones, and the share of queries carried by the most frequent pairs, are reported as structure."],
  "features": {
   "pair_frequency": "how many queries in the release need this exact unordered gold pair (computed over the whole "
                     "dev set, then averaged over the query's gold pairs)",
   "pair_frequent": "1 if the query's most frequent gold pair occurs in >= 10 queries",
   "pair_overlap": "content-word Jaccard between the two gold descriptions of the query's strongest pair",
   "random_pair_overlap": "the same Jaccard for a seeded random non-co-occurring pair drawn from the same two "
                          "servers' catalogues"},
  "dvs": {"fail_at_1": "H1's outcome",
          "overlap_difference": "H2's estimand: frequent-pair minus random-pair description overlap"},
  "models": [
   "logistic on fail_at_1 with the frequent-pair indicator plus the standard controls, clustered on query_id",
   "cluster bootstrap of the frequent-minus-random description overlap, resampling tool pairs",
   "the measured degree and sparsity table: pairs observed, pairs possible, degree distribution, top-pair share"],
  "thresholds": {"support": "|beta| >= 0.15 with CI excluding 0 and p_holm < 0.05",
                 "partial": "CI excludes 0 below the floor", "null": "CI includes 0",
                 "h3": "descriptive: a structure count, so no band applies"},
  "family": "three",
  "gate_scope": "H2",
  "kill_gate": ("G6 froze >= 200 queries needing >= 2 gold tools and G7 >= 200 distinct gold pairs, since a network "
                "needs edges. EXP-0181 measured 16,461 and 11,798, so H1 stands; H2 is scoped to the pair-level "
                "bootstrap, whose usable edge count is reported with the estimate."),
  "strata": ["pair-frequency band", "config"],
  "tables": ["table1_sample_and_structure.csv", "table2_dependency_census.csv", "table3_main_models.csv",
             "table4_strata_by_pair_frequency.csv", "table5_robustness_inference.csv",
             "table6_baseline_comparison.csv", "table7_experiment_provenance.csv", "table_run_cost.csv"],
  "figures": ["fig0_framework.pdf", "fig1_dependency_structure.pdf", "fig2_main_effect.pdf",
              "fig3_mechanism_by_band.pdf", "fig4_robustness.pdf"],
 },
}

# census key (a dotted path into its `measured` block) -> the name this freeze gives it, so EXP-0163 can rewrite the
# PREMISES literal below from the artefact rather than from a hand-kept copy.
PREMISE_MAP = {
 "rows": "dev_rows", "catalogue_parse_share": "catalogue_parse_share",
 "gold_index_recoverable_share": "gold_index_recoverable_share",
 "ranker_columns_present_share": "ranker_columns_present_share",
 "median_candidates": "median_candidates", "mean_candidates": "mean_candidates",
 "distinct_tools": "distinct_tools", "distinct_servers": "distinct_servers",
 "server_hhi": "server_hhi", "names_with_separator_share": "names_with_separator_share",
 "descriptions_with_affordance_verb_share": "affordance_verb_share",
 "candidates_with_parameters_share": "parameter_list_share",
 "queries_with_near_synonym_decoy": "near_synonym_queries",
 "queries_needing_2plus_gold": "multi_gold_queries", "distinct_gold_pairs": "distinct_gold_pairs",
 "queries_with_irrelevant_candidate_above_gold": "contaminated_queries",
 "fail_at_1_share": "fail_at_1_share", "min_config_rows": "min_config_rows",
 "shipped_parser_entries_recovered": "entries_recovered_by_the_shipped_parser",
}

PREMISES = {
    "census": "EXP-0181 (EXP0181_wave7_premise_census_20260924T170600.json)",
    "transcribed_by": "02_shared_code/registry/refresh_wave_premises.py (EXP-0163); no number in this block is typed by hand",
    "measured": {
        "dev_rows": 31642,
        "catalogue_parse_share": 1.0,
        "gold_index_recoverable_share": 1.0,
        "ranker_columns_present_share": 1.0,
        "median_candidates": 4.0,
        "mean_candidates": 7.04,
        "distinct_tools": 4161,
        "distinct_servers": 2055,
        "server_hhi": 0.007,
        "names_with_separator_share": 0.6248,
        "affordance_verb_share": 0.711,
        "parameter_list_share": 0.8505,
        "near_synonym_queries": 13698,
        "multi_gold_queries": 16461,
        "distinct_gold_pairs": 11798,
        "contaminated_queries": 2953,
        "fail_at_1_share": 0.1788,
        "min_config_rows": 10492,
        "entries_recovered_by_the_shipped_parser": 0,
    },
    "gates": {
          "G10_cluster_count_per_config": {'blocks': ['T161', 'T162', 'T164', 'T165', 'T166', 'T169'], 'fires': False, 'measured': 10492.0, 'scope': 'design'},
          "G11_ranker_columns_present": {'blocks': ['T161', 'T162', 'T164', 'T165', 'T166', 'T169'], 'fires': False, 'measured': 1.0, 'scope': 'design'},
          "G12_parameter_lists_present": {'blocks': ['T162'], 'fires': False, 'measured': 0.8505, 'scope': 'H3'},
          "G1_catalogues_parseable": {'blocks': ['T161', 'T162', 'T164', 'T165', 'T166', 'T169'], 'fires': False, 'measured': 1.0, 'scope': 'design'},
          "G2_gold_indices_recoverable": {'blocks': ['T161', 'T162', 'T164', 'T165', 'T166', 'T169'], 'fires': False, 'measured': 1.0, 'scope': 'design'},
          "G3_namespace_separators_present": {'blocks': ['T164'], 'fires': False, 'measured': 0.6248, 'scope': 'H1'},
          "G4_near_synonym_queries": {'blocks': ['T161'], 'fires': False, 'measured': 13698.0, 'scope': 'H1'},
          "G5_affordance_language_present": {'blocks': ['T162'], 'fires': False, 'measured': 0.711, 'scope': 'design'},
          "G6_multi_gold_queries": {'blocks': ['T169'], 'fires': False, 'measured': 16461.0, 'scope': 'H1'},
          "G7_distinct_gold_pairs": {'blocks': ['T169'], 'fires': False, 'measured': 11798.0, 'scope': 'H2'},
          "G8_contaminated_rankings": {'blocks': ['T166'], 'fires': True, 'measured': 0.0933, 'scope': 'H1'},
          "G9_distinct_servers": {'blocks': ['T165'], 'fires': False, 'measured': 2055.0, 'scope': 'design'},
      },
    "verdict": {
          "blocked_gates": ['G8_contaminated_rankings'],
          "blocked_whole_design": [],
          "claim_limited": {'G8_contaminated_rankings': 'H1'},
      },
    "note": "a fired gate is a result, not an obstacle: it stops exactly what its frozen sentence scopes",
    "runnable": list(RUNNABLE),
}

FAILED_RUNS = [
 "EXP0181 first launch was a 400-row smoke run (results_raw/EXP0181_wave7_premise_census_20260924T170456.json), used "
 "to prove the catalogue reader and the per-query rules; G10 and the two count floors fired there only because the "
 "draw was 400 rows, so that generation is superseded and the gate verdicts cited are the full-dev ones.",
]

EXTRA_DEVIATIONS = [
 ("W7-D01", "The shipped catalogue parser reads none of these rows, so the wave brought its own",
            "`wave_lib.catalog_entries` is P001's parser and expects `name`/`description` keys; the dev frames store "
            "`n`/`d`/`p`. The census measured 0 entries recovered from the first 500 rows through that parser and "
            "1.0 through `entries()`, which reads both spellings. No earlier wave depended on the shipped parser for "
            "these frames, so nothing else is affected, but every wave-7 count of candidates, descriptions and "
            "parameters is computed from the reader named here rather than from the parser that returned nothing."),
 ("W7-D02", "This release records a ranker's ordering, not an agent's choice",
            "The outcome columns available in the dev frames are the frozen BM25 rank, score margin and fail-at-k of "
            "the gold tool inside the candidate list. There is no logged selection by an agent, so each of the six "
            "frozen RQs above states that its dependent variable is what the lexical ranker did, and no design in "
            "this wave reports an effect on an agent's decision. T166's title asks about agentic decisions and its "
            "freeze text is the place where that gap between the title and the measurable quantity is fixed."),
 ("W7-D03", "G8 fired on a share and the cell it describes is large",
            "T166's H1 froze a floor of 0.10 of queries with a zero-overlap candidate ranked above every gold one; "
            "the census measured 0.0933 on all 31,642 dev rows, which is 2,953 queries. The floor is not moved, the "
            "hypothesis is reported as limited by its own sentence, and the absolute count is printed next to the "
            "verdict so the reader sees that the gate fired on a proportion."),
 ("W7-D04", "The namespace and density contrasts are majority-side, not balanced",
            "Two of the wave's own floors were cleared by a wide margin in a way that narrows what the comparison is: "
            "62.48% of candidate names carry a namespace separator, so T164's ungrouped arm is the minority, and "
            "71.1% of descriptions carry an affordance verb while 85.05% carry parameters, so T162's contrasts are "
            "within a mostly-positive distribution. Both facts are measured premises rather than results, and each "
            "affected kill-gate sentence names its own figure."),
 ("W7-D05", "The affordance gate counts a substring; the per-query column counts a word",
            "G5 froze '>= 0.30 of candidate descriptions contain at least one affordance verb from the frozen list' "
            "and the census measured that with a substring test, which is how 0.711 was obtained and reported. The "
            "same test is a poor counter: it scores 'get' inside 'target' as a verb, and the leading-space variant "
            "that avoids that misses a verb at position 0, which is where a description usually starts ('Read the "
            "contents of...'). EXP-0182 therefore reports both readings on the identical 204,998 descriptions: "
            "0.711 under the gate's substring test, 0.697 under `AFFORD_RX`, a word-boundary form of the same frozen "
            "list, and the per-query density is computed with the boundary form. G5's verdict is unchanged because "
            "both figures clear the 0.30 floor, and no design's threshold moved."),
 ("W7-D06", "T165's difference is bootstrapped, as frozen, and given a second reading on drawn pairs",
            "The freeze names three models for T165 - a cluster bootstrap over servers, a concentration table and a "
            "name-reuse census - and the frame delivers 184 servers with at least three described tools and a "
            "different-server comparison. wave_lib refuses any cluster-robust regression below 200 rows, the guard "
            "every earlier wave's fit also had to clear, so no regression is offered at the server's own scale and "
            "none was invented. Instead EXP-0182 draws 20 same-server and 20 different-server description pairs "
            "around each of the 4,161 named tools (123,720 pairs) and the same comparison is estimated there, "
            "clustered on the tool the pair was drawn around, with each side's word count controlled. That "
            "regression is reported beside the bootstrap as a second reading; the frozen H1 remains the bootstrap "
            "and the frozen band is applied to it."),
 ("W7-D07", "T161's specificity sentence names the question; the frozen instrument is the gold description",
            "H3's third clause asks for 'a randomly chosen non-gold candidate's similarity to the question', while "
            "the design's own feature table defines `control_similarity` as the same similarity as the decoy "
            "measure's - a random non-gold candidate against the gold description - and the instrument section fixes "
            "the decoy rule in terms of candidate descriptions. Both readings are measured: the random-candidate "
            "against-gold arm is the specificity decision, and the question-overlap arm (`irrelevant_share_z`, the "
            "share of candidates with no content word in common with the instruction) is reported in the same row. "
            "The verdict follows the instrument table, which is the definition the frame computes."),
 ("W7-D08", "Two server-pool bugs the census cross-check caught before any coefficient existed",
            "EXP-0182 cross-checks five aggregates against EXP-0181 and aborts if a pair diverges, and on the first "
            "build three things surfaced. The decoy column took the *minimum* containment over a query's gold "
            "candidates where the frozen rule and the census take an any(), so multi-gold queries lost their "
            "look-alikes (0.1914 against the census's 0.4329); the server pool was keyed as a set of "
            "(name, word-set) tuples and sorted, which compares word sets through the partial subset order and "
            "let the process hash seed choose which 196 servers were usable and in what order; and a name "
            "published with two different descriptions was counted twice. Each is fixed - max over golds, a dict "
            "keyed by tool name sorted by name - and the frame now reproduces the census exactly on all five "
            "quantities, with those pairs written into the artefact as `census_cross_check`."),
 ("W7-D09", "1,546 of the release's 11,798 gold pairs carry no description on one side",
            "G7 froze '>= 200 distinct unordered gold-tool pairs' and the census measured 11,798, so the network "
            "exists. T169's H2 needs a description on both ends to compare an overlap, and 1,546 pairs have a tool "
            "whose description carries no content word at all, leaving 10,252 pairs with a computable overlap and "
            "304 of those recurring in >= 10 queries - the edges the frequent-pair bootstrap actually resamples. "
            "Both counts are printed with the estimate, which is what the gate sentence asked for, and the frozen "
            "floor is not moved to the smaller number."),
]
