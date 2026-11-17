"""Crossref-backed literature harvester (spec section 2: named venues, not arXiv alone).

Why this exists: the export arXiv API is the only bibliographic host this project used so far, and the papers say
so in their limitations ("non-arXiv venue search could not be verified here"). Measured 2026-09-19, that is no
longer true: `api.crossref.org` answers 200 and returns DOIs, container titles, years and - for many records -
author-deposited abstracts, which covers ACL/EMNLP/SIGIR/CIKM/WWW/CHI/CHIIR/NeurIPS/JASIST/IP&M/Journal of
Documentation. `api.semanticscholar.org` answered 429 (retryable) and the arXiv hosts 406 (throttled).

Rules of this module, so that volume never becomes padding:
  * a record must carry a container title (a real venue) or be dropped - unhosted SSRN/preprint-registry hits are
    excluded by default, because the point of this host is peer-reviewed venue coverage;
  * relevance is scored against the paper's construct terms over title + abstract; a record needs a minimum score
    to be kept, and the score and the exact query are stored on the row;
  * every query is logged with `returned` and `error`, and an empty answer is recorded as `zero_records`, never as
    "no such literature";
  * DOIs are copied from the response - nothing is constructed from memory.

    python 02_shared_code/literature/crossref_harvest.py --paper P002
    python 02_shared_code/literature/crossref_harvest.py --paper P003 --cap 40 --dry-run
"""
from __future__ import annotations

import argparse, csv, io, json, re, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API = "https://api.crossref.org/works?"
HDR = {"User-Agent": "aib-literature-harvest/1.0 (https://example.org; research reproducibility)"}
SELECT = "DOI,title,container-title,published,abstract,author,type,is-referenced-by-count,URL"

VENUES = {  # spec section 2, spelled as Crossref spells them where known
    "JASIST": "Journal of the Association for Information Science and Technology",
    "IP&M": "Information Processing & Management",
    "JDoC": "Journal of Documentation",
    "CHIIR": "ACM Transactions on Computer-Human Interaction",
}

PAPERS = {
    "P002": {
        "dir": "papers/P002_isp_stage_measurement",
        "queries": ["information search process stages", "uncertainty human information behavior",
                    "problem behaviour graph information seeking", "search session logging stages",
                    "annotation coding reliability interaction", "conversation coding scheme reliability",
                    "Markov model user behaviour sequence", "search action sequence analysis",
                    "information foraging patch", "stopping behaviour search",
                    "task complexity search behaviour", "exploration exploitation information seeking",
                    "dialogue act annotation agreement", "process discovery event logs",
                    "trace data agent language model", "censoring truncation behavioural sequence"],
        "venue_queries": ["information search process", "stage model information seeking",
                          "coding reliability annotation", "agent trajectory evaluation"],
        "terms": ["information search", "search stage", "search process", "seeking", "uncertainty",
                  "coding scheme", "annotation", "reliability", "agreement", "sequence", "markov",
                  "foraging", "stopping", "session log", "process mining", "trace"],
    },
    "P003": {
        "dir": "papers/P003_metadata_interoperability",
        "queries": ["metadata interoperability schema mapping", "schema matching survey",
                    "ontology alignment evaluation", "FAIR principles metadata compliance",
                    "dataset documentation data cards", "metadata quality assessment",
                    "provenance machine learning reproducibility", "knowledge organization schemes digital",
                    "vocabulary mapping linked data", "crosswalk metadata standards",
                    "benchmark contamination evaluation", "reproducibility data archives",
                    "agentic workflow tool schema", "function calling interface description"],
        "venue_queries": ["metadata interoperability", "schema matching", "FAIR data", "dataset documentation"],
        "terms": ["metadata", "interoperab", "schema", "ontology align", "crosswalk", "FAIR", "provenance",
                  "dataset doc", "knowledge organization", "vocabulary", "mapping", "reproducib", "conformance"],
    },
    "P004": {
        "dir": "papers/P004_shipped_quality_score_validity",
        "queries": ["LLM as a judge validity agreement human", "automatic evaluation metric construct validity",
                    "dataset quality filtering language model training", "data quality annotation agreement",
                    "synthetic corpus quality assessment reliability", "reward model score validity benchmark",
                    "preference label noise model evaluation", "metadata quality data discovery information",
                    "Cronbach alpha information behaviour scale", "uncertainty confidence calibration evaluation",
                    "trajectory dataset annotation quality", "LLM generated labels bias agreement study",
                    "data curation filtering effect downstream performance", "instrument validation information science",
                    "benchmark score inflation automatic evaluation"],
        "venue_queries": ["LLM as a judge validity", "dataset quality filtering", "annotation agreement validity",
                          "automatic evaluation construct validity"],
        "terms": ["llm-as-a-judge", "judge", "validity", "agreement", "reliability", "quality score",
                  "filter", "annotation", "evaluation metric", "construct", "calibration", "bias",
                  "dataset quality", "synthetic data", "trajectory", "cronbach", "scale"],
    },
    "P005": {
        "dir": "papers/P005_governance_metadata_verifiability",
        "queries": ["dataset license compliance machine learning", "datasheets for datasets adoption",
                    "data provenance documentation reproducibility", "AI system cards governance transparency",
                    "dataset documentation metadata quality discovery", "research software link rot citation",
                    "data license compatibility reuse derivative", "corpus documentation annotation provenance",
                    "FAIR principles assessment dataset releases", "model card dataset card completeness",
                    "training data attribution licensing", "reproducibility data availability statement",
                    "agent trajectory dataset sharing terms", "synthetic data licensing open dataset",
                    "metadata completeness data repositories", "secondary use dataset reuse governance"],
        "venue_queries": ["dataset documentation", "data licensing", "provenance metadata", "research compendium",
                          "FAIR data assessment"],
        "terms": ["license", "licensing", "provenance", "attribution", "dataset card", "datasheet", "model card",
                  "documentation", "metadata quality", "FAIR", "reuse", "redistribution", "link rot",
                  "reproducibility", "data availability", "repository", "agent trajectory", "corpus",
                  "governance", "compliance"],
    },
    "P001": {
        "dir": "papers/P001_routing_failure_qpp",
        "queries": ["query performance prediction survey", "query difficulty prediction retrieval",
                    "pre-retrieval features query quality", "vocabulary mismatch query translation",
                    "tool retrieval benchmark agents", "function calling evaluation language model",
                    "tool selection large language model", "agentic information seeking retrieval",
                    "conversational query reformulation", "learning to rank domain adaptation",
                    "dense retrieval versus lexical", "calibration ranking scores",
                    "clustered standard errors information retrieval", "synthetic data evaluation bias"],
        "venue_queries": ["query performance prediction", "tool retrieval", "vocabulary mismatch",
                          "query difficulty"],
        "terms": ["query performance", "prediction", "difficulty", "pre-retrieval", "query quality",
                  "vocabulary mismatch", "tool retrieval", "tool selection", "function calling", "agent",
                  "reformulation", "ranking", "calibration", "clustered", "benchmark"],
    },
    # ------------------------------------------------------------------------------------------- wave 1 (T101+)
    "P006": {
        "dir": "papers/P006_underspecified_needs",
        "queries": ["underspecified information needs search", "ambiguous queries clarification search",
                    "query specificity retrieval performance", "clarifying questions conversational search",
                    "instruction specificity agent task completion", "anaphora resolution search query",
                    "elliptical queries information retrieval", "task ambiguity search behaviour",
                    "entity specificity query formulation", "user instructions ambiguity dialogue"],
        "venue_queries": ["underspecified queries", "clarifying questions search", "query ambiguity",
                          "conversational search"],
        "terms": ["underspecif", "ambigu", "clarif", "specificity", "anaphor", "ellipsis", "vague",
                  "information need", "query formulation", "conversational search", "agent", "instruction",
                  "retrieval performance", "uncertainty"],
    },
    "P007": {
        "dir": "papers/P007_constraint_density",
        "queries": ["task complexity search behaviour", "constraint queries retrieval",
                    "query length retrieval performance", "multi-facet task search",
                    "composed information retrieval", "complex goal decomposition search",
                    "search breadth depth foraging", "number of constraints user task",
                    "task difficulty ranking performance", "query complexity measures"],
        "venue_queries": ["task complexity", "query complexity", "search as task", "information foraging"],
        "terms": ["task complexity", "constraint", "query complex", "facet", "compound", "decomposition",
                  "breadth", "depth", "foraging", "difficulty", "length", "search behaviour", "retrieval"],
    },
    "P008": {
        "dir": "papers/P008_query_reformulation_fidelity",
        "queries": ["query reformulation information loss", "query rewriting conversational search",
                    "context dependent query rewriting", "query transformation retrieval effectiveness",
                    "semantic fidelity paraphrase retrieval", "agent tool invocation formulation",
                    "instruction decomposition query", "rewrite degradation dense retrieval",
                    "coreference query rewriting dialogue", "query performance reformulation"],
        "venue_queries": ["query reformulation", "query rewriting", "conversational query"],
        "terms": ["reformulat", "rewrit", "information loss", "fidelity", "paraphrase", "degrad",
                  "context dependent", "coreference", "transformation", "query", "retrieval", "agent"],
    },
    "P009": {
        "dir": "papers/P009_lexical_match_bias",
        "queries": ["lexical bias retrieval ranking", "shortcut learning text matching",
                    "question overlap answer selection bias", "adversarial lexical overlap reading",
                    "BM25 bias relevance judgment", "spurious features neural ranking",
                    "distractor selection retrieval evaluation", "word overlap relevance assessment",
                    "decoy candidates benchmark design", "training data leakage ranking metrics"],
        "venue_queries": ["lexical bias", "neural ranking bias", "text matching shortcuts", "relevance judgment"],
        "terms": ["lexical", "overlap", "bias", "shortcut", "spurious", "distractor", "decoy", "relevance",
                  "ranking", "adversarial", "bm25", "matching"],
    },
    "P010": {
        "dir": "papers/P010_lexical_semantic_conflict",
        "queries": ["lexical semantic mismatch retrieval", "dense sparse retrieval disagreement",
                    "vocabulary mismatch semantic retrieval", "hybrid retrieval complementarity analysis",
                    "embedding versus bm25 cases", "query-document representation conflict",
                    "disagreement ranking systems retrieval", "semantic similarity lexical overlap ranking"],
        "venue_queries": ["dense retrieval", "lexical retrieval", "hybrid search", "vocabulary mismatch"],
        "terms": ["lexical", "semantic", "dense", "sparse", "hybrid", "mismatch", "disagree", "complement",
                  "embedding", "vocabulary", "ranking", "retrieval"],
    },
    "P011": {
        "dir": "papers/P011_predicate_argument_relevance",
        "queries": ["semantic role labeling information retrieval", "predicate argument structure matching",
                    "relation extraction query understanding", "verb semantics document ranking",
                    "structured query understanding retrieval", "entity relation relevance ranking",
                    "frame semantics text grounding", "compositional matching retrieval",
                    "tool capability description matching", "argument structure query formulation"],
        "venue_queries": ["semantic role labeling", "query understanding", "structured retrieval",
                          "compositional generalization retrieval"],
        "terms": ["predicate", "argument", "semantic role", "relation", "structure", "compositional",
                  "matching", "query understanding", "frame", "role labeling", "relevance", "ranking"],
    },
    # ------------------------------------------------------------------------------------------- wave 2 (T111+)
    # P013 (T112) and P017 (T117) are absent on purpose: EXP-0135 blocked both on their measurement premise, so
    # neither becomes a package and there is no manuscript for a collision screen to protect.
    "P012": {
        "dir": "papers/P012_entity_action_constraint_fit",
        "queries": ["entity matching semantic retrieval", "action verb matching tool selection",
                    "constraint satisfaction query retrieval", "semantic role matching document ranking",
                    "structured query representation retrieval", "argument structure relevance ranking",
                    "predicate lexical overlap ranking", "compositional matching neural ranking",
                    "entity linking retrieval ranking", "relation matching knowledge retrieval"],
        "venue_queries": ["query understanding", "semantic retrieval", "relevance ranking", "structured retrieval"],
        "terms": ["entity", "predicate", "argument", "action", "constraint", "matching", "compositional",
                  "semantic role", "relevance", "ranking", "retrieval", "query understanding"],
    },
    "P014": {
        "dir": "papers/P014_semantic_prototype_bias",
        "queries": ["prototype typicality ranking retrieval", "semantic centrality document selection",
                    "typicality bias machine ranking", "centroid representation retrieval ranking",
                    "distributional typicality relevance", "category typicality information retrieval",
                    "representation bias ranking models", "prototype theory retrieval",
                    "semantic space structure ranking", "catalogue composition bias retrieval"],
        "venue_queries": ["neural ranking", "semantic retrieval", "bias in retrieval", "relevance"],
        "terms": ["prototype", "typical", "centrality", "centroid", "bias", "ranking", "relevance",
                  "distributional", "embedding", "retrieval", "catalogue"],
    },
    "P015": {
        "dir": "papers/P015_metadata_quality_model",
        "queries": ["metadata quality scoring model", "description quality resource discovery",
                    "tool description documentation quality", "metadata completeness measurement retrieval",
                    "dataset documentation quality assessment", "card quality scoring discoverability",
                    "metadata attributes ranking performance", "documentation richness search effectiveness",
                    "quality index metadata standard", "composite metadata quality score"],
        "venue_queries": ["metadata quality", "information retrieval", "knowledge organization", "data papers"],
        "terms": ["metadata quality", "completeness", "description", "score", "index", "discoverab",
                  "documentation", "assessment", "retrieval", "richness", "standard"],
    },
    "P016": {
        "dir": "papers/P016_description_granularity",
        "queries": ["description length retrieval performance", "detail granularity metadata search",
                    "verbosity document ranking", "description specificity retrieval",
                    "long short document descriptions ranking", "information density metadata",
                    "text length bias ranking", "document length effects retrieval effectiveness",
                    "over specification retrieval", "annotation granularity information retrieval"],
        "venue_queries": ["retrieval effectiveness", "document ranking", "metadata", "query length"],
        "terms": ["granularity", "length", "verbosity", "detail", "density", "specificity", "description",
                  "retrieval", "ranking", "metadata", "effects"],
    },
    # ------------------------------------------------------------------------------------------- wave 3 (T113+)
    # P019 (T118, hierarchy and facets) is absent on purpose: EXP-0142 measured that only 16.94% of entry names carry
    # more than one segment against the design's own 20% gate, so the catalogue has no hierarchy to expose and there
    # is no manuscript for a collision screen to protect.
    "P018": {
        "dir": "papers/P018_function_vs_usecase_description",
        "queries": ["use case documentation retrieval", "procedural versus declarative description search",
                    "task oriented metadata description", "function description phrasing discovery",
                    "intent oriented document description ranking", "scenario based documentation search",
                    "purpose statement metadata discovery", "description framing effect ranking",
                    "operational versus applicability description", "tool description wording retrieval"],
        "venue_queries": ["information retrieval", "documentation studies", "metadata", "human computer interaction"],
        "terms": ["use case", "function", "procedure", "description", "framing", "documentation", "purpose",
                  "intent", "task", "retrieval", "discoverab"],
    },
    "P020": {
        "dir": "papers/P020_name_description_congruence",
        "queries": ["name description consistency metadata", "label content alignment retrieval",
                    "title abstract consistency", "naming convention documentation quality",
                    "term mismatch metadata description", "self consistency of resource descriptions",
                    "identifier semantics discovery", "metadata internal coherence",
                    "congruent metadata retrieval", "title body divergence search"],
        "venue_queries": ["metadata quality", "knowledge organization", "information retrieval", "documentation"],
        "terms": ["congruence", "consistency", "name", "label", "title", "description", "coherence", "alignment",
                  "metadata", "retrieval", "discoverab"],
    },
    "P021": {
        "dir": "papers/P021_synonym_normalisation_consistency",
        "queries": ["synonym control retrieval", "vocabulary normalization search",
                    "lexical ambiguity resolution ranking", "synonym ring information retrieval",
                    "controlled vocabulary metadata mapping", "term normalization document retrieval",
                    "word sense disambiguation search", "thesaurus mapping discovery",
                    "morphological normalization ranking", "lexical variation retrieval effectiveness"],
        "venue_queries": ["information retrieval", "knowledge organization", "semantic web", "computational linguistics"],
        "terms": ["synonym", "normali", "vocabulary", "lexical", "ambigu", "mapping", "thesaurus",
                  "disambiguation", "retrieval", "term"],
    },
    "P022": {
        "dir": "papers/P022_discriminability_and_discoverability",
        "queries": ["distinctive document description retrieval", "discriminative features metadata ranking",
                    "uniqueness description discovery", "differentiation catalog entries search",
                    "specificity metadata quality", "completeness versus usefulness metadata",
                    "local distinctiveness term weighting", "contrastive document representation",
                    "informativeness metadata assessment", "neighbour contrast ranking"],
        "venue_queries": ["metadata quality", "information retrieval", "ranking", "knowledge organization"],
        "terms": ["discriminat", "distinctive", "uniqueness", "contrast", "specificity", "completeness",
                  "metadata", "quality", "ranking", "retrieval"],
    },
    # --- wave 4. Queries and construct terms written from each design's frozen RQ, before that package has a result.
    "P023": {
        "dir": "papers/P023_modality_and_verification",
        "queries": ["epistemic modality markers text", "hedging detection uncertainty language",
                    "uncertainty expression followed by verification", "agent additional search after uncertainty",
                    "confidence expression behaviour prediction", "epistemic markers dialogue acts",
                    "uncertainty triggers clarification question", "hedge detection reliability annotation",
                    "language model expresses uncertainty", "modality cue information seeking behaviour"],
        "venue_queries": ["uncertainty expression and search behaviour", "epistemic modality in dialogue"],
        "terms": ["modality", "hedge", "uncertaint", "epistemic", "marker", "verification", "confidence",
                  "behaviour", "behavior", "next action", "assistant turn"],
    },
    "P024": {
        "dir": "papers/P024_epistemic_behavioural_gap",
        "queries": ["reasoning trace versus final answer divergence", "chain of thought disclosure",
                    "private public behaviour discrepancy", "verbal report versus observed behaviour",
                    "internal state expression alignment", "uncertainty disclosure agent response",
                    "saying doing alignment cognition", "metacognitive report and control",
                    "confidence expression versus accuracy", "covert cognition self report"],
        "venue_queries": ["reasoning traces and behaviour", "self report versus observed behaviour"],
        "terms": ["reasoning", "chain of thought", "discrepanc", "diverg", "disclos", "private", "public",
                  "verbal report", "alignment", "behaviour", "behavior"],
    },
    "P025": {
        "dir": "papers/P025_contradiction_and_modality",
        "queries": ["conflicting evidence information seeking", "contradictory search results user response",
                    "inconsistent information sources retrieval", "contradiction detection across documents",
                    "belief revision conflicting evidence", "uncertainty increase contradictory information",
                    "source disagreement ranking", "repeated query differing results",
                    "ambiguity from inconsistent evidence", "conflict appraisals multiple sources"],
        "venue_queries": ["contradiction and uncertainty", "conflicting evidence and confidence"],
        "terms": ["contradict", "conflict", "inconsisten", "discrepan", "disagreement", "belief revision",
                  "uncertaint", "evidence", "retrieval", "source"],
    },
    "P026": {
        "dir": "papers/P026_sufficiency_language_and_stopping",
        "queries": ["satisfaction threshold information seeking", "search session stopping rules",
                    "perceived information sufficiency", "optimal foraging patch leaving",
                    "enough information judgment search", "premature search termination",
                    "aspiration level search behaviour", "sufficiency criteria relevance assessment",
                    "uncertainty of understanding stopping", "termination decision interactive search"],
        "venue_queries": ["stopping and satisfaction in search", "information foraging and sufficiency"],
        "terms": ["satisfic", "sufficien", "stop", "terminat", "foraging", "threshold", "quit",
                  "enough information", "search session", "premature"],
    },
    "P027": {
        "dir": "papers/P027_discourse_grammar_of_seeking",
        "queries": ["speech act annotation dialogue", "dialogue act sequence conversational",
                    "discourse structure agent reasoning", "hypothesising questioning planning turns",
                    "illocutionary force language model output", "utterance function classification dialogue",
                    "act labelling information seeking turns", "turn position dialogue act frequency",
                    "planning speech act task dialogue", "conclusion act discourse annotation"],
        "venue_queries": ["dialogue acts and information seeking", "speech act annotation of agent language"],
        "terms": ["speech act", "dialogue act", "discourse", "annotat", "turn", "utterance", "plan",
                  "question", "conclusion", "sequence"],
    },
    "P028": {
        "dir": "papers/P028_conclusion_before_evidence",
        "queries": ["premature closure diagnostic reasoning", "hypothesis evaluation order evidence",
                    "answer stated before retrieval", "belief perseverance information search",
                    "assertion and evidence order effect", "overconfidence insufficient search",
                    "conclusion confidence before data", "revising a claim after evidence",
                    "order of information acquisition judgement", "cherry picking evidence sequence"],
        "venue_queries": ["premature closure and evidence order", "confidence and information acquisition"],
        "terms": ["premature", "closure", "order", "conclusion", "assertion", "evidence", "revis",
                  "overconfidence", "belief", "sequence"],
    },
    "P029": {
        "dir": "papers/P029_discourse_repair_after_failure",
        "queries": ["self correction language model agent", "error recovery tool use failure",
                    "repair after failed action dialogue", "backtracking in agent trajectories",
                    "feedback and retry behaviour", "acknowledging errors generated text",
                    "conversational repair other initiation", "failure observation next turn",
                    "abandoning a task after error", "replan after unsuccessful retrieval"],
        "venue_queries": ["repair and self-correction in dialogue", "agent error recovery behaviour"],
        "terms": ["repair", "self-correct", "error", "failure", "recovery", "retry", "backtrack",
                  "feedback", "abandon", "next turn"],
    },
    "P030": {
        "dir": "papers/P030_causal_connectives_and_evidence",
        "queries": ["causal connectives text analysis", "discourse markers causal reasoning",
                    "because justification grounding", "rhetorical relation evidence support",
                    "coherence markers factual accuracy", "causal expression entailment premise",
                    "connective detection in generated text", "explanation faithfulness to source",
                    "therefore inference validity text", "unsupported causal claims language model"],
        "venue_queries": ["causal discourse markers and evidence", "justification and grounding"],
        "terms": ["causal", "connective", "discourse marker", "because", "therefore", "coherence",
                  "justification", "evidence", "support", "faithful"],
    },
    "P031": {
        "dir": "papers/P031_explanatory_coherence_and_evidential_gaps",
        "queries": ["explanatory coherence judgement", "fluency plausibility bias",
                    "narrative coherence and belief", "seductive details memory",
                    "chain length and accuracy", "coherence as a cue to truth",
                    "plausible explanation missing evidence", "explanation quality rating bias",
                    "discourse fluency credibility", "argument structure persuasiveness"],
        "venue_queries": ["coherence and plausibility", "fluency and judgement accuracy"],
        "terms": ["coherence", "explanator", "plausib", "fluenc", "credibilit", "persuas", "gap",
                  "evidence", "judgement", "accuracy"],
    },
    "P032": {
        "dir": "papers/P032_plan_action_alignment",
        "queries": ["plan adherence language model agent", "stated intention and executed action",
                    "plan representation tool call", "intention action consistency agent",
                    "plan decomposition execution match", "declared plan versus behaviour",
                    "plan following benchmark agents", "alignment between plan and action",
                    "prose plan and structured action", "deviation from a stated plan"],
        "venue_queries": ["plan adherence in language agents", "intention and action alignment"],
        "terms": ["plan", "intention", "action", "adherence", "alignment", "deviation", "tool call",
                  "execut", "consistency", "step"],
    },
    "P045": {
        "dir": "papers/P045_primacy_lock_in_and_later_search",
        "queries": ["primacy effect hypothesis testing search", "confirmation bias information search",
                    "initial hypothesis constrains later evidence", "anchoring and adjustment in diagnosis",
                    "hypothesis consistent information seeking", "selective exposure to evidence agent",
                    "premature closure diagnostic reasoning", "belief perseverance search behaviour",
                    "agent trajectory anchoring", "confirmation seeking large language model agent"],
        "venue_queries": ["confirmation bias in reasoning", "hypothesis testing and diagnostic accuracy"],
        "terms": ["primac", "anchor", "confirmation bias", "premature closure", "hypothesis", "consisten",
                  "persever", "selective exposure", "belief", "constrain"],
    },
    "P046": {
        "dir": "papers/P046_plan_specificity_and_search_quality",
        "queries": ["plan specificity agent task performance", "detailed instruction following language model",
                    "task specification ambiguity agent", "planning granularity robot task",
                    "prompt specificity and agent success", "constraint specification information seeking",
                    "entity naming in task instructions", "redundant action agent plans",
                    "plan quality measurement trajectory", "action ordering and performance"],
        "venue_queries": ["plan quality in automated agents", "instruction specificity and task performance"],
        "terms": ["specific", "granular", "plan", "instruction", "constraint", "specification", "ambigu",
                  "detail", "quality", "entity"],
    },
    "P047": {
        "dir": "papers/P047_verbal_versus_behavioural_correction",
        "queries": ["self-correction language model agent", "verbal acknowledgement of error",
                    "error recovery interactive agent", "apology and behaviour change", "self-reflection efficacy",
                    "critique and revision dialogue", "mistake acknowledgement dialogue systems",
                    "repeated action after failure agent", "superficial self-correction",
                    "alignment between stated and observed behaviour"],
        "venue_queries": ["self-correction in language models", "repair in dialogue and interactive systems"],
        "terms": ["self.correct", "apolog", "admission", "recovery", "revis", "reflect", "mistake", "error",
                  "stuck", "repea"],
    },
    "P050": {
        "dir": "papers/P050_a_cross_task_grammar_of_agent_search",
        "queries": ["sequence mining agent trajectories", "Markov model of search behaviour",
                    "transition probabilities information seeking", "grammar of interaction sequences",
                    "n-gram model of tool use", "task transfer across software repositories",
                    "domain generalisation of agent policies", "process mining of agent logs",
                    "pattern discovery in search sessions", "cross-domain behavioural regularity"],
        "venue_queries": ["process mining of interaction logs", "sequential models of search behaviour"],
        "terms": ["transition", "sequence", "grammar", "markov", "n.gram", "pattern", "cross.task",
                  "domain", "regularit", "process min"],
    },
    "P051": {
        "dir": "papers/P051_early_signals_of_agent_search_failure",
        "queries": ["predicting agent task failure early", "run time failure prediction agent",
                    "early warning of dialogue failure", "trajectory outcome prediction",
                    "process quality prediction in interactive search", "agent failure taxonomy",
                    "predict task success from initial behaviour", "run length and agent outcome",
                    "error prediction software agent", "abandonment detection interactive search"],
        "venue_queries": ["predicting search task failure", "agent reliability and failure analysis"],
        "terms": ["predict", "early", "failure", "outcome", "success", "abando", "risk", "warn",
                  "trajectory", "runtime"],
    },
    "P052": {
        "dir": "papers/P052_the_recovery_window_after_a_failed_step",
        "queries": ["error recovery in interactive agents", "self repair after a failed action",
                    "retry behaviour software agent", "replanning after execution failure",
                    "lag between error and correction", "fault tolerance agent behaviour",
                    "recovery from tool call failure", "dialogue repair after misunderstanding",
                    "cost of delayed correction", "error cascade in multi step tasks"],
        "venue_queries": ["error recovery in human computer interaction", "agent self-correction after failure"],
        "terms": ["recovery", "repair", "retry", "replan", "correction", "failed", "error", "lag",
                  "window", "cascad"],
    },
    "P053": {
        "dir": "papers/P053_which_rollouts_deserve_reuse",
        "queries": ["trajectory selection for agent learning", "experience replay selection agent",
                    "demonstration selection imitation", "data curation for agent fine tuning",
                    "case based reasoning trajectory reuse", "reward filtered behaviour cloning",
                    "which episodes to keep", "redundancy in agent datasets",
                    "cost efficiency of successful trajectories", "deduplication of experience banks"],
        "venue_queries": ["data selection in machine learning", "experience replay and reuse"],
        "terms": ["select", "reuse", "curat", "replay", "demonstration", "episode", "trajectory",
                  "dedup", "efficien", "filter"],
    },
    "P067": {
        "dir": "papers/P067_information_density_of_language_and_code_actions",
        "queries": ["code as action versus natural language action", "program synthesis agent tool use",
                    "code interpreter agent reasoning", "information density of code versus prose",
                    "executable actions in dialogue agents", "code execution feedback loop",
                    "structured action representation agent", "programming by example agent tasks",
                    "action space code commands", "tool call versus code generation"],
        "venue_queries": ["code generation for interactive agents", "action representations in agents"],
        "terms": ["code", "action", "natural language", "densit", "execut", "interpreter", "command",
                  "program", "representation", "feedback"],
    },
    "P068": {
        "dir": "papers/P068_corrective_and_ritual_reflection",
        "queries": ["self-reflection without behaviour change", "ritualistic correction dialogue",
                    "verbal self-correction reasoning", "reconsideration markers in chain of thought",
                    "reflection tuning language models", "superficial self-critique",
                    "does self-reflection change the answer", "revision markers in reasoning traces",
                    "multimodal reasoning operators", "monitoring and correction in agent loops"],
        "venue_queries": ["self-reflection in language models", "revision and repair in reasoning"],
        "terms": ["reflect", "reconsider", "ritual", "superficial", "self-correct", "revision", "critique",
                  "monitor", "change", "marker"],
    },
    "P069": {
        "dir": "papers/P069_case_based_reuse_of_historical_trajectories",
        "queries": ["case-based reasoning for agents", "retrieval of past trajectories",
                    "similar task reuse in agent learning", "analogical problem solving agents",
                    "experience replay across tasks", "transfer from prior episodes",
                    "nearest neighbour task similarity", "episodic memory retrieval agent",
                    "case adaptation in problem solving", "library of solved tasks"],
        "venue_queries": ["case-based reasoning", "episodic memory in artificial agents"],
        "terms": ["case", "reuse", "retriev", "analog", "prior", "episode", "similar", "library",
                  "transfer", "recall"],
    },
    "P070": {
        "dir": "papers/P070_agent_trajectory_corpora_as_intelligence_sources",
        "queries": ["agent trajectory dataset survey", "corpora for agentic behaviour analysis",
                    "benchmark inventory of language model agents", "secondary analysis of interaction logs",
                    "data commons for agent research", "metadata of agent datasets",
                    "reusability of agent traces", "comparative analysis of agent corpora",
                    "information behaviour datasets", "provenance of training traces"],
        "venue_queries": ["surveys of LLM agent benchmarks", "dataset documentation and reuse"],
        "terms": ["corpora", "dataset", "trajectory", "survey", "inventory", "benchmark", "metadata",
                  "reus", "provenance", "secondary analysis"],
    },
    "P062": {
        "dir": "papers/P062_discourse_structure_of_successful_and_failed_searches",
        "queries": ["discourse structure of search sessions", "successful versus failed search dialogue",
                    "verbal protocols of information seeking", "move structure in information search",
                    "linguistic markers of task success", "coherence in problem solving dialogue",
                    "utterance functions in interactive search", "language of expert versus novice searchers",
                    "failed search session analysis", "narrative structure of agent traces"],
        "venue_queries": ["discourse analysis of information search", "verbal protocols in problem solving"],
        "terms": ["discourse", "structure", "successful", "failed", "move", "utterance", "coherence",
                  "verbal protocol", "narrative", "marker"],
    },
    "P063": {
        "dir": "papers/P063_which_components_of_a_trace_carry_forward",
        "queries": ["reusable procedural knowledge from agent traces", "trajectory component transfer",
                    "rationale in agent logs reuse", "exception handling knowledge reuse",
                    "observation versus procedure in skill libraries", "workflow knowledge extraction",
                    "what makes a demonstration useful", "step types in agent trajectories",
                    "context condition and result in instructions", "carry over of annotations"],
        "venue_queries": ["procedural knowledge acquisition", "experience reuse in software agents"],
        "terms": ["component", "carry", "transfer", "procedure", "rationale", "exception", "observation",
                  "reusab", "annotation", "knowledge"],
    },
    "P064": {
        "dir": "papers/P064_abstraction_level_of_a_trace_and_transfer",
        "queries": ["level of abstraction and transfer learning", "concrete versus abstract instructions",
                    "generality of demonstrations", "specificity and generalisation in prompts",
                    "concrete examples versus rules", "abstraction in procedural text",
                    "transfer between similar tasks", "verbatim versus generalised memory",
                    "language exactness and instruction following", "hierarchical instruction representations"],
        "venue_queries": ["concreteness effects on learning and transfer", "abstraction in human problem solving"],
        "terms": ["abstraction", "concrete", "generali", "specific", "transfer", "verbatim", "general",
                  "hierarch", "example", "rule"],
    },
    "P065": {
        "dir": "papers/P065_what_a_compression_loses_first",
        "queries": ["context compression for language agents", "memory summarisation of agent trajectories",
                    "information loss in prompt compression", "summarising long dialogue history",
                    "which details survive summarisation", "negative constraint retention",
                    "provenance loss in compression", "uncertainty preservation in summaries",
                    "compaction of agent memory", "context window budget allocation"],
        "venue_queries": ["text summarisation and information retention", "agent memory management"],
        "terms": ["compress", "summar", "loss", "retain", "forget", "memory", "context window", "budget",
                  "provenance", "compaction"],
    },
    "P066": {
        "dir": "papers/P066_relation_classes_between_attempts_of_one_task",
        "queries": ["relation between repeated problem solving attempts", "restatement and refinement in dialogue",
                    "contradiction detection between responses", "case based reasoning adaptation",
                    "semantic relation classification of texts", "duplicate and related question detection",
                    "consolidation of episodic memories", "contradictory evidence integration",
                    "multiple attempts task learning", "organizational memory of agent experience"],
        "venue_queries": ["textual entailment and contradiction", "episodic memory consolidation"],
        "terms": ["relation", "restat", "refine", "contradict", "entail", "consolidat", "duplicate", "similar",
                  "attempt", "episode"],
    },
    "P056": {
        "dir": "papers/P056_the_implicit_information_need",
        "queries": ["implicit information need in instructions", "underspecified task specification agent",
                    "missing requirements in user instructions", "clarification questions ambiguous tasks",
                    "requirement extraction from task text", "information need completeness measurement",
                    "implicit constraints in natural language instructions", "instruction following and unstated "
                    "requirements", "tool retrieval from vague queries", "task ambiguity and retrieval coverage"],
        "venue_queries": ["ambiguous instructions and clarification in dialogue", "retrieval for underspecified needs"],
        "terms": ["implicit", "underspec", "unspecified", "missing constraint", "requirement", "ambigu",
                  "clarif", "coverage", "completeness", "instruction"],
    },
    "P039": {
        "dir": "papers/P039_semantic_decoy_and_misselection",
        "queries": ["tool selection large language model agent", "function calling retrieval ambiguity",
                    "near duplicate tool description disambiguation", "tool retrieval benchmark MCP",
                    "semantic similarity and tool choice", "misselection API retrieval",
                    "candidate list length tool selection accuracy", "similar tools confusion agent",
                    "tool documentation quality agent performance", "API naming and retrieval error",
                    "multiple choice retrieval distractor effect"],
        "venue_queries": ["tool use in language model agents", "API retrieval and selection"],
        "terms": ["tool select", "function call", "tool retriev", "distractor", "near duplicate", "ambigu",
                  "confusion", "candidate", "description", "misselec"],
    },
    "P040": {
        "dir": "papers/P040_affordance_language_and_selection",
        "queries": ["affordance language tool description", "verb semantics interface description",
                    "documentation phrasing and retrieval", "action terms API description",
                    "parameter documentation discovery", "affordance presentation user performance",
                    "natural language interface description quality", "tool schema description usefulness",
                    "keyword richness documentation search", "parameter naming agent tool use"],
        "venue_queries": ["affordances in human computer interaction", "API documentation quality"],
        "terms": ["affordance", "description", "documentat", "verb", "parameter", "schema", "phrasing",
                  "action term", "wording", "interface"],
    },
    "P041": {
        "dir": "papers/P041_tool_namespace_and_candidate_overload",
        "queries": ["tool namespace naming convention agent", "many tools candidate overload",
                    "information overload tool list", "grouping and categorisation of interfaces",
                    "menu size and selection performance", "hierarchical naming API catalogue",
                    "too many options agent tool selection", "choice overload human performance",
                    "namespace prefix collision tools", "catalogue size retrieval accuracy"],
        "venue_queries": ["choice overload and set size", "API naming conventions and tooling"],
        "terms": ["namespace", "overload", "catalogue", "size", "grouping", "hierarch", "prefix",
                  "number of tools", "list length", "menu"],
    },
    "P042": {
        "dir": "papers/P042_the_catalogue_ecosystem",
        "queries": ["MCP server ecosystem analysis", "repository of tools measurement study",
                    "specialisation of API providers", "duplicate tools across servers",
                    "software ecosystem evolution", "herfindahl concentration APIs",
                    "naming conventions across repositories", "tool catalogue coverage redundancy",
                    "public API registry study", "server supply of agent tools"],
        "venue_queries": ["mining software repositories", "API ecosystem empirical study"],
        "terms": ["ecosystem", "server", "registry", "repository", "specialis", "concentration", "provider",
                  "duplicate", "catalogue", "naming"],
    },
    "P043": {
        "dir": "papers/P043_irrelevant_candidate_contamination",
        "queries": ["irrelevant documents in retrieval context", "distractors degrade retrieval performance",
                    "noise in candidate list ranking", "context contamination language model",
                    "irrelevant information effect on decisions", "zero relevance results above the answer",
                    "retrieval precision distractor", "long context irrelevant content harm",
                    "corpus contamination ranking quality", "distraction in search result lists"],
        "venue_queries": ["distractors in reading and search", "retrieval noise and answer quality"],
        "terms": ["irrelevant", "distract", "contaminat", "noise", "precision", "above", "zero overlap",
                  "unrelated", "ranking", "context"],
    },
    "P044": {
        "dir": "papers/P044_tool_dependency_network",
        "queries": ["multi-tool composition agent", "tool dependency graph", "co-occurrence of API calls",
                    "workflow mining service composition", "sequence of tool calls patterns",
                    "toolchain discovery", "graph of function calls language model agent",
                    "service composition co-usage", "plan structure multi step tasks",
                    "network of tool interactions"],
        "venue_queries": ["web service composition mining", "workflow graphs in software ecosystems"],
        "terms": ["dependenc", "co.occur", "composition", "graph", "network", "chain", "multi tool",
                  "pair", "workflow", "sequence"],
    },
    "P033": {
        "dir": "papers/P033_search_depth_vs_need_complexity",
        "queries": ["search depth information need complexity", "query difficulty and interaction length",
                    "search session length task complexity", "effort after meaning model",
                    "cognitive load and search behaviour", "number of queries task difficulty",
                    "search as browsing effort accounting", "step budget agent task",
                    "multi rollout variation search depth", "information need formulation complexity"],
        "venue_queries": ["search process and task complexity", "query difficulty and interaction"],
        "terms": ["depth", "complexit", "difficulty", "session length", "number of queries", "effort",
                  "information need", "search process", "step", "budget"],
    },
    "P034": {
        "dir": "papers/P034_information_scent_and_the_next_choice",
        "queries": ["information scent foraging model", "patch leaving decision foraging",
                    "scent estimate relevance judgement", "prior knowledge and next query",
                    "predicting the next search action", "expectation and evidence encounter",
                    "query reformulation from results", "foraging theory human information search",
                    "cue validity in interactive search", "semantic scent retrieval"],
        "venue_queries": ["information scent and foraging", "predicting search actions"],
        "terms": ["scent", "forag", "patch", "cue", "expectation", "next query", "reformulat",
                  "prediction", "relevance", "search step"],
    },
    "P035": {
        "dir": "papers/P035_marginal_gain_and_search_persistence",
        "queries": ["marginal information gain search", "diminishing returns information seeking",
                    "when to stop searching foraging", "persistence after failure search",
                    "novelty of retrieved documents over a session", "redundancy in search results",
                    "satisfaction threshold and stopping", "continued search despite low yield",
                    "exploration budget search agent", "new information rate interaction"],
        "venue_queries": ["stopping and marginal gain", "persistence in information search"],
        "terms": ["marginal", "gain", "diminishing", "novelt", "redundan", "persist", "stop",
                 "yield", "budget", "continued search"],
    },
    "P036": {
        "dir": "papers/P036_command_family_switching_cost",
        "queries": ["task switching cost human computer", "attention residue interface switching",
                    "cognitive cost of switching tools", "exploration exploitation search behaviour",
                    "tool switching in multi-tool agents", "diversity of search actions quality",
                    "switching between information sources", "interaction cost model search",
                    "switch rate and performance", "cognitive tunneling search"],
        "venue_queries": ["switching cost and interaction", "exploration and switching in search"],
        "terms": ["switch", "cost", "task set", "attention", "tool use", "diversit", "exploration",
                  "overlap", "source", "performance"],
    },
    "P037": {
        "dir": "papers/P037_first_action_path_dependence",
        "queries": ["path dependence decision sequence", "primacy effect information search",
                    "initial choice constrains later search", "commitment and search trajectory",
                    "first query quality downstream", "anchor and adjustment in retrieval",
                    "lock-in exploration agent", "sequential dependence of actions",
                    "trajectory diversity same task", "starting point effect search"],
        "venue_queries": ["primacy and path dependence", "initial action and later choice"],
        "terms": ["path depend", "primac", "anchor", "lock", "commitment", "first", "initial",
                  "sequence", "trajectory", "constraint"],
    },
    "P038": {
        "dir": "papers/P038_repetition_and_rumination",
        "queries": ["repetitive querying search behaviour", "query repetition and redundancy",
                    "rumination problem solving", "loop detection agent behaviour",
                    "perseveration in interactive search", "repeated action futility",
                    "search revisit rate", "circular search behaviour", "mental set and fixing",
                    "duplicate query detection logs", "query reformulation repetition session",
                    "unproductive search loops problem solving", "redundant queries conversational search",
                    "stuck in a loop automated agent behaviour"],
        "venue_queries": ["repetition and perseveration in search", "loops in agent behaviour"],
        "terms": ["repetit", "revisit", "duplicate", "loop", "persever", "rumina", "redundanc",
                  "retry", "stuck", "circular"],
    },
}



def get(params: dict):
    url = API + urllib.parse.urlencode(params)
    try:
        return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=45).read()), None
    except Exception as exc:                                   # noqa: BLE001 - network is a boundary
        return None, f"{type(exc).__name__}: {exc}"


def clean(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


DOMAIN_ANCHORS = ["information seek", "information search", "information behav", "human information",
                  "search stage", "search session", "search interaction", "question asking", "retrieval",
                  "conversational search", "dialogue", "agent", "language model", "llm", "tool",
                  "browse", "web search", "library", "bibliometric", "knowledge organization", "metadata",
                  "annotation agreement", "coding reliability", "user study", "task performance"]


def score(item, terms):
    """(total, domain_anchored). Generic method words alone must never qualify a record - that is how a paper on
    protein sequence annotation scored 4 on 'annotation' + 'sequence'."""
    title = clean((item.get("title") or [""])[0])
    abst = clean(item.get("abstract") or "")
    t = (title + " " + abst).lower()
    total = sum(2 if term.lower() in title.lower() else 1 for term in terms if term.lower() in t)
    anchored = any(term in t for term in DOMAIN_ANCHORS)
    return total, anchored


def existing(path: Path):
    if not path.exists():
        return set(), set()
    rows = list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8"))))
    dois = {re.sub(r"^https?://(dx\.)?doi\.org/", "", (r.get("url") or ""), flags=re.I).lower() for r in rows}
    titles = {re.sub(r"[^a-z0-9 ]", "", (r.get("title") or "").lower())[:48] for r in rows}
    return {d for d in dois if "/" in d}, titles


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", required=True, choices=sorted(PAPERS))
    ap.add_argument("--rows", type=int, default=40)
    ap.add_argument("--min-score", type=int, default=2)
    ap.add_argument("--cap", type=int, default=45)
    ap.add_argument("--require-venue", action="store_true", default=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    cfg = PAPERS[a.paper]
    pap = ROOT / cfg["dir"]
    out_csv = pap / "literature_matrix.csv"
    have_dois, have_titles = existing(out_csv)
    rows0 = list(csv.DictReader(io.StringIO(out_csv.read_text(encoding="utf-8")))) if out_csv.exists() else []
    hdr = list(rows0[0].keys()) if rows0 else ["cite_key", "year", "venue", "title", "problem", "dataset_used",
                                               "method", "metric", "main_result", "collision_target",
                                               "overlap_level", "code_or_data_public", "url", "retrieved_on",
                                               "verify_status", "paper_id", "differentiation"]
    cand, log = {}, []
    plans = ([("title", {"query.title": q, "rows": a.rows, "select": SELECT}) for q in cfg["queries"]]
             + [(f"venue:{v}", {"query.bibliographic": q, "query.container-title": VENUES[v], "rows": 20,
                                "select": SELECT})
                for v, q in ((v, q) for v in VENUES for q in cfg["venue_queries"])])
    for label, params in plans:
        data, err = get(params)
        items = (data or {}).get("message", {}).get("items", []) if data else []
        kept = 0
        for it in items:
            doi = (it.get("DOI") or "").lower()
            venue = clean((it.get("container-title") or [""])[0])
            title = clean((it.get("title") or [""])[0])
            nt = re.sub(r"[^a-z0-9 ]", "", title.lower())[:48]
            s, anchored = score(it, cfg["terms"])
            if (not doi) or doi in have_dois or nt in have_titles or s < a.min_score or not anchored:
                continue
            if a.require_venue and not venue:
                continue
            kept += 1
            have_dois.add(doi)
            have_titles.add(nt)
            cand[doi] = (s, it, label)
        log.append({"paper": a.paper, "query_form": label, "params": json.dumps(params)[:220],
                    "returned": len(items), "kept": kept,
                    "status": ("transport_error" if err else ("zero_records" if not items else "hits_returned")),
                    "error": err or "", "ran_at": time.strftime("%Y-%m-%dT%H:%M:%S")})
        print(f"  {a.paper} | {label:34s} returned={len(items):3d} kept={kept:3d}{'  ' + (err or '')[:60] if err else ''}")
        time.sleep(1.2)                                        # Crossref is polite-pool tolerant but be well-behaved
    top = sorted(cand.values(), key=lambda x: (-x[0], -int(x[1].get("is-referenced-by-count") or 0)))[:a.cap]
    new = []
    for s, it, label in top:
        title = clean((it.get("title") or [""])[0])
        abst = clean(it.get("abstract") or "")
        auth = ((it.get("author") or [{}])[0].get("family") or "anon")
        d = {"cite_key": f"{auth}{(it.get('published') or {}).get('date-parts', [['']])[0][0]}{re.sub(r'[^a-z]', '', title.lower())[:1]}",
             "year": str(((it.get("published") or {}).get("date-parts") or [[""]])[0][0]),
             "venue": clean((it.get("container-title") or [""])[0]) or it.get("type", ""),
             "title": title,
             "problem": (abst[:300] or "abstract not deposited with Crossref"),
             "dataset_used": "", "method": (abst[300:560] or ""), "metric": "",
             "main_result": (abst[:300] or ""), "collision_target": "graded in novelty_audit",
             "overlap_level": "candidate - abstract read, not yet graded",
             "code_or_data_public": "not checked", "url": f"https://doi.org/{it['DOI']}",
             "retrieved_on": time.strftime("%Y-%m-%d"),
             "verify_status": f"Crossref record; relevance {s}; has_abstract={bool(abst)}; query={label}",
             "paper_id": a.paper, "differentiation": ""}
        new.append({k: d.get(k, "") for k in hdr})
    print(f"[crossref] {a.paper}: existing={len(rows0)} new={len(new)} zero_record_queries="
          f"{sum(1 for l in log if l['status'] == 'zero_records')} errors={sum(1 for l in log if l['error'])}")
    if not a.dry_run and new:
        with open(out_csv, "a", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=hdr)
            if not out_csv.exists() or out_csv.stat().st_size == 0:
                w.writeheader()
            w.writerows(new)
    ql = pap / "lit_search_log.csv"
    old = list(csv.DictReader(io.StringIO(ql.read_text(encoding="utf-8")))) if ql.exists() else []
    for r in old:
        r.setdefault("source", "arxiv_export_api")
    for r in log:
        r["source"] = "crossref"
    # Union the columns and build the whole text in memory first: an earlier version opened the file with "w"
    # before a crash-prone writerow, which truncated the previous source's log. Never destroy query history.
    keys = list(dict.fromkeys([k for r in old + log for k in r]))
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=keys, extrasaction="ignore")
    w.writeheader()
    w.writerows(old + log)
    ql.write_text(buf.getvalue(), encoding="utf-8", newline="")
    print(f"[crossref] {'NOT written (dry run), would add' if a.dry_run else 'wrote'} "
          f"{len(new)} rows -> {out_csv.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
