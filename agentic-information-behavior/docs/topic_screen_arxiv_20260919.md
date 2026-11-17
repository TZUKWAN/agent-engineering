# arXiv-side novelty screen of the 12 live topics (EXP-0047)

Generated 2026-09-19 18:03 from `EXP0047_arxiv_topic_screen_20260919T180002.json`. Transport: curl against `https://export.arxiv.org/api/query` (python urllib is refused with 406 here for the same URL). Query form: `abs:"one phrase"` optionally narrowed by `cat:X` - never two phrases ANDed, which this API answers empty.

**Reading rule enforced by the screen**: `zero_records` is not evidence of a gap, and a topic whose every query came back empty is marked undecidable rather than novel. L-grades below are the author's judgement after reading the returned titles; the titles and arXiv ids they rest on are printed next to each grade so a reader can disagree with the grade without having to re-run the retrieval.

| topic | queries | informative | zero records | collision candidates | L | status after this screen |
|---|---|---|---|---|---|---|
| T004 | 4 | 1 | 3 | 6 | L2 | `w2_pilot_next_L2_adjacent` |
| T006 | 4 | 3 | 1 | 11 | L4 | `demoted_L4_taken_by_three_2026_papers` |
| T013 | 4 | 1 | 3 | 1 | L1 | `w2_pilot_next_L1_gap_p005_candidate` |
| T014 | 4 | 2 | 2 | 7 | L2 | `w2_merge_into_T013_p005` |
| T015 | 4 | 2 | 2 | 12 | L4 | `demoted_L4_crowded_and_data_blocked` |
| T021 | 4 | 4 | 0 | 15 | L4 | `demoted_L4_taken` |
| T027 | 4 | 2 | 2 | 7 | L3 | `w2_L3_crowded_needs_sharp_delta` |
| T028 | 4 | 3 | 1 | 12 | L3 | `demoted_L3_crowded_and_needs_human_gold` |
| T029 | 4 | 0 | 4 | 0 | undecidable | `w2_screen_incomplete_empty_feeds` |
| T030 | 4 | 1 | 3 | 6 | L3 | `killed_self_overlap_not_novelty` |
| T034 | 4 | 2 | 2 | 12 | L4 | `demoted_L4_crowded` |
| T036 | 4 | 0 | 4 | 0 | undecidable | `w2_screen_incomplete_empty_feeds` |

## Why each grade, and the records it rests on

### T004 — L2 → `w2_pilot_next_L2_adjacent`
adjacent: instruction-tuning generalisation from templates (2505.14425) is close, but the human-vs-synthetic contrast inside shipped agent corpora is not taken
- query `abs:"synthetic data instructions" AND cat:cs.CL` → **zero_records**, 0 returned, 0 keyword-relevant: —
- query `abs:"human written instructions" AND cat:cs.CL` → **informative**, 12 returned, 11 keyword-relevant: 2024 2407.12734v1 “A LLM Benchmark based on the Minecraft Builder Dialog Agent Task”, 2025 2505.14425v2 “From Templates to Natural Language: Generalization Challenges in Instruction-Tuned LLMs for Spatial Reasoning”, 2023 2311.15964v4 “Efficient Pre-training for Localized Instruction Generation of Videos”
- query `abs:"prompt distribution LLM" AND cat:cs.CL` → **zero_records**, 0 returned, 0 keyword-relevant: —
- query `abs:"instruction style transfer" AND cat:cs.CL` → **zero_records**, 0 returned, 0 keyword-relevant: —

### T006 — L4 → `demoted_L4_taken_by_three_2026_papers`
taken: 2602.14878 'MCP Tool Descriptions Are Smelly', 2602.18914 'From Docs to Descriptions', 2606.04769 'Description-Code Inconsistency in Real-world MCP Servers' - measurement AND benchmark AND improvement are all published in 2026
- query `abs:"tool description" AND cat:cs.SE` → **informative**, 12 returned, 8 keyword-relevant: 2026 2602.14878v3 “Model Context Protocol (MCP) Tool Descriptions Are Smelly! Towards Improving AI Agent Efficiency with Augmente”, 2026 2606.04769v1 “Description-Code Inconsistency in Real-world MCP Servers: Measurement, Detection, and Security Implications”, 2026 2602.18914v1 “From Docs to Descriptions: Smell-Aware Evaluation of MCP Server Descriptions”
- query `abs:"API documentation quality"` → **informative**, 1 returned, 1 keyword-relevant: 2019 1907.13260v1 “What should I document? A preliminary systematic mapping study into API documentation knowledge”
- query `abs:"tool documentation" AND cat:cs.SE` → **informative**, 8 returned, 5 keyword-relevant: 2025 2503.04479v3 “ToolFuzz -- Automated Agent Tool Testing”, 2025 2508.13774v1 “Agentic DraCor and the Art of Docstring Engineering: Evaluating MCP-empowered LLM Usage of the DraCor API”, 2026 2605.29561v1 “ParaTool: Shifting Tool Representations from Context to Parameters”
- query `abs:"metadata completeness retrieval" AND cat:cs.IR` → **zero_records**, 0 returned, 0 keyword-relevant: —

### T013 — L1 → `w2_pilot_next_L1_gap_p005_candidate` → **P005 (candidate)**
gap: only 1 of 4 queries returned anything (model cards -> AI System Cards 2509.20394); the licence/provenance/attribution metadata OF AGENT TRAJECTORY CORPORA is not the object of any returned paper
- query `abs:"dataset license" AND cat:cs.DB` → **zero_records**, 0 returned, 0 keyword-relevant: —
- query `abs:"data provenance machine learning"` → **zero_records**, 0 returned, 0 keyword-relevant: —
- query `abs:"responsible release datasets" AND cat:cs.CY` → **zero_records**, 0 returned, 0 keyword-relevant: —
- query `abs:"model card" AND cat:cs.CL` → **informative**, 12 returned, 1 keyword-relevant: 2025 2509.20394v1 “Blueprints of Trust: AI System Cards for End to End Transparency and Governance”

### T014 — L2 → `w2_merge_into_T013_p005` → **P005 (merged in)**
adjacent: science-software linkage (2104.05891) and repository availability (2207.12879) exist, but no agent-corpus treatment; and link availability cannot be measured from this machine (HF/GitHub unreachable), so only the structural part is feasible
- query `abs:"link rot"` → **informative**, 8 returned, 7 keyword-relevant: 2021 2104.05891v1 “Science-Software Linkage: The Challenges of Traceability between Scientific Knowledge and Software Artifacts”, 2022 2207.12879v1 “"Knock knock! Who's there?" A study on scholarly repositories' availability”, 2025 2511.18382v1 “ViMix-14M: A Curated Multi-Source Video-Text Dataset with Long-Form, High-Quality Captions and Crawl-Free Acce”
- query `abs:"reproducibility software dependencies" AND cat:cs.SE` → **zero_records**, 0 returned, 0 keyword-relevant: —
- query `abs:"broken links"` → **informative**, 12 returned, 1 keyword-relevant: 2026 2603.00331v2 “Linting Style and Substance in READMEs”
- query `abs:"archival of research artifacts" AND cat:cs.DL` → **zero_records**, 0 returned, 0 keyword-relevant: —

### T015 — L4 → `demoted_L4_crowded_and_data_blocked`
crowded: underspecified-query and multimodal-entity-linking benchmarks are active (8/9 and 12/12 relevant), and the corpus's images are still absent locally
- query `abs:"underspecified queries" AND cat:cs.IR` → **informative**, 9 returned, 8 keyword-relevant: 2026 2608.20357v1 “Clarify-Then-Search: A Clarification Benchmark for Deep Search with End-to-End Nugget Restoration”, 2026 2605.16479v1 “Policy-Grounded Dynamic Facet Suggestions for Job Search”, 2026 2607.01530v1 “IntentTune: Using user demand and personalization to resolve "unknown" query intents for e-commerce search”
- query `abs:"visual question ambiguity" AND cat:cs.CV` → **zero_records**, 0 returned, 0 keyword-relevant: —
- query `abs:"multimodal entity linking" AND cat:cs.CL` → **informative**, 12 returned, 12 keyword-relevant: 2023 2305.14725v2 “AMELI: Enhancing Multimodal Entity Linking with Fine-Grained Attributes”, 2025 2510.02726v1 “PGMEL: Policy Gradient-based Generative Adversarial Network for Multimodal Entity Linking”, 2025 2510.14307v1 “MERLIN: A Testbed for Multilingual Multimodal Entity Recognition and Linking”
- query `abs:"query intent ambiguity" AND cat:cs.IR` → **zero_records**, 0 returned, 0 keyword-relevant: —

### T021 — L4 → `demoted_L4_taken`
taken: agentic process mining agenda 2609.07984 plus a saturated conformance-checking literature (12/12 and 12/12 relevant on its two broad queries)
- query `abs:"process mining" AND cat:cs.AI` → **informative**, 12 returned, 12 keyword-relevant: 2021 2103.07184v1 “Process Comparison Using Object-Centric Process Cubes”, 2026 2609.07984v2 “From Event Logs to Governed Action: A BlueSky Agenda for Agentic Process Mining”, 2022 2205.04827v2 “Probabilistic and Non-Deterministic Event Data in Process Mining: Embedding Uncertainty in Process Analysis Te”
- query `abs:"tool call sequences" AND cat:cs.SE` → **informative**, 1 returned, 1 keyword-relevant: 2026 2602.19218v2 “Gecko: A Simulation Environment with Stateful Feedback for Refining Agent Tool Calls”
- query `abs:"agent trajectory analysis" AND cat:cs.AI` → **informative**, 2 returned, 2 keyword-relevant: 2026 2608.30391v1 “Using Grounded Theory for Agent Behavior Analysis at Scale”, 2026 2605.13625v1 “How to Interpret Agent Behavior”
- query `abs:"conformance checking" AND cat:cs.SE` → **informative**, 12 returned, 12 keyword-relevant: 2022 2209.09712v1 “Process Mining Meets Visual Analytics: The Case of Conformance Checking”, 2026 2605.00283v1 “A Privacy-Preserving Approach to Conformance Checking”, 2020 2101.00958v1 “Scalable Online Conformance Checking Using Incremental Prefix-Alignment Computation”

### T027 — L3 → `w2_L3_crowded_needs_sharp_delta`
crowded: controlled instruction-complexity augmentation (2505.18557) and ill-defined-task evaluation (2603.17067) cover the construct; readability-vs-execution link not taken
- query `abs:"readability metrics source code" AND cat:cs.SE` → **zero_records**, 0 returned, 0 keyword-relevant: —
- query `abs:"instruction complexity" AND cat:cs.CL` → **informative**, 12 returned, 7 keyword-relevant: 2025 2505.18557v2 “TAG-INSTRUCT: Controlled Instruction Complexity Enhancement through Structure-based Augmentation”, 2026 2603.17067v1 “Evaluating Ill-Defined Tasks in Large Language Models”, 2023 2311.01487v2 “What Makes for Good Visual Instructions? Synthesizing Complex Visual Reasoning Instructions for Visual Instruc”
- query `abs:"cognitive load programming" AND cat:cs.HC` → **zero_records**, 0 returned, 0 keyword-relevant: —
- query `abs:"execution time prediction" AND cat:cs.PF` → **informative**, 1 returned, 1 keyword-relevant: 2021 2102.00527v2 “A Runtime-Based Computational Performance Predictor for Deep Neural Network Training”

### T028 — L3 → `demoted_L3_crowded_and_needs_human_gold`
crowded: entangled/contradictory instruction evaluation exists (2503.13222, 2608.22138, 2502.14494); a detection method for shipped corpora would also need two human coders
- query `abs:"conflicting instructions" AND cat:cs.CL` → **informative**, 8 returned, 8 keyword-relevant: 2026 2608.22138v1 “Measuring Stability and Failure Behavior in Language Models Under Structured Perturbations”, 2025 2503.13222v3 “Can Language Models Follow Multiple Turns of Entangled Instructions?”, 2026 2601.06403v1 “Steer Model beyond Assistant: Controlling System Prompt Strength via Contrastive Decoding”
- query `abs:"constraint satisfaction instructions" AND cat:cs.CL` → **zero_records**, 0 returned, 0 keyword-relevant: —
- query `abs:"contradictory requirements" AND cat:cs.SE` → **informative**, 1 returned, 0 keyword-relevant: —
- query `abs:"instruction following evaluation" AND cat:cs.CL` → **informative**, 12 returned, 10 keyword-relevant: 2025 2502.04688v1 “M-IFEval: Multilingual Instruction-Following Evaluation”, 2025 2506.01776v2 “MaXIFE: Multilingual and Cross-lingual Instruction Following Evaluation”, 2024 2407.03942v1 “Diverse and Fine-Grained Instruction-Following Ability Exploration with Synthetic Data”

### T029 — undecidable → `w2_screen_incomplete_empty_feeds`
all four queries returned empty feeds; per this screen's own rule that is a query-form failure, not evidence of a gap
- query `abs:"termination criteria agents" AND cat:cs.AI` → **zero_records**, 0 returned, 0 keyword-relevant: —
- query `abs:"self verification language models" AND cat:cs.CL` → **zero_records**, 0 returned, 0 keyword-relevant: —
- query `abs:"stopping policy reinforcement"` → **zero_records**, 0 returned, 0 keyword-relevant: —
- query `abs:"answer completeness judgement" AND cat:cs.IR` → **zero_records**, 0 returned, 0 keyword-relevant: —

### T030 — L3 → `killed_self_overlap_not_novelty`
the 'constraint density' phrase returns CSP physics, not instruction work - so novelty is not the problem; the problem is that it re-slices P001's own covariates
- query `abs:"constraint density"` → **informative**, 12 returned, 10 keyword-relevant: 2009 0911.4328v3 “Criticality and Heterogeneity in the Solution Space of Random Constraint Satisfaction Problems”, 2025 2511.01037v1 “Binary perceptron computational gap -- a parametric fl RDT view”, 2021 2105.03831v1 “Super Solutions of the Model RB”
- query `abs:"task complexity agents" AND cat:cs.AI` → **zero_records**, 0 returned, 0 keyword-relevant: —
- query `abs:"instruction length effects" AND cat:cs.CL` → **zero_records**, 0 returned, 0 keyword-relevant: —
- query `abs:"cognitive load language models" AND cat:cs.HC` → **zero_records**, 0 returned, 0 keyword-relevant: —

### T034 — L4 → `demoted_L4_crowded`
taken: exploratory search / information foraging is a dense, established area (12/12 relevant on both broad queries)
- query `abs:"information wandering" AND cat:cs.IR` → **zero_records**, 0 returned, 0 keyword-relevant: —
- query `abs:"exploratory search" AND cat:cs.IR` → **informative**, 12 returned, 12 keyword-relevant: 2020 2007.11198v1 “Exploratory Search with Sentence Embeddings”, 2020 2005.01716v1 “Hierarchical Knowledge Graphs: A Novel Information Representation for Exploratory Search Tasks”, 2023 2310.05150v1 “From Data to Dialogue: Leveraging the Structure of Knowledge Graphs for Conversational Exploratory Search”
- query `abs:"information foraging" AND cat:cs.IR` → **informative**, 12 returned, 12 keyword-relevant: 2020 2008.02372v1 “Reinforcement Learning-driven Information Seeking: A Quantum Probabilistic Approach”, 2020 2001.06765v1 “Information Foraging for Enhancing Implicit Feedback in Content-based Image Recommendation”, 2016 1606.08157v1 “Risk and Ambiguity in Information Seeking: Eye Gaze Patterns Reveal Contextual Behaviour in Dealing with Uncer”
- query `abs:"attention lapse search" AND cat:cs.HC` → **zero_records**, 0 returned, 0 keyword-relevant: —

### T036 — undecidable → `w2_screen_incomplete_empty_feeds`
all four queries returned empty feeds
- query `abs:"corpus as data source" AND cat:cs.DL` → **zero_records**, 0 returned, 0 keyword-relevant: —
- query `abs:"secondary analysis agent traces"` → **zero_records**, 0 returned, 0 keyword-relevant: —
- query `abs:"dataset reuse" AND cat:cs.DB` → **zero_records**, 0 returned, 0 keyword-relevant: —
- query `abs:"research compendium" AND cat:cs.DL` → **zero_records**, 0 returned, 0 keyword-relevant: —

## Consequences for the queue

1. **T006 dies by literature, not by feasibility.** Its instrument exists locally and the audit would have been easy to run; three 2026 papers already measure MCP/tool-description quality, benchmark it and attack description-code inconsistency. Running it anyway would have produced a fourth cut of someone else's result.
2. **T021, T015, T034 are crowded**, and T028/T027 are crowded in their construct while also needing human gold this environment cannot supply. T030 dies on the anti-repetition rule (its own covariates are P001's), not on novelty.
3. **T013 is the only L1** - one relevant record in four queries - so it is the fifth paper's candidate. Its unit (dataset-level governance metadata: licence declarations, provenance, attribution, redistribution permission) is none of the four existing papers' units, which is the anti-repetition test it has to pass. T014 merges in as its reproducibility/reference component, because link *availability* cannot be measured from this machine (the unreachable-host list is in `PROGRAM_STATUS.md` §3) while reference *structure* can.
4. **T004 stays alive at L2** as the next candidate after T013, and T029/T036 must be re-screened with different phrase families before anything is claimed about them.

