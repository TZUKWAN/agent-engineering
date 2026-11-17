"""Grade the wave packages' collision matrices with the programme's frozen four-family rule.

`grade_collisions.grade` is the rule the five earlier packages were graded with: a record's title plus abstract is
scored on four families (object, construct, measure, data) and the level is a fixed function of how many families
fire. This tool does not touch that function. It supplies the six *new* family lexicons - one per wave package,
written from the construct that package measures - and re-derives `overlap_level` for every row from the abstract
text already sitting in the matrix, recording which rule produced each level.

The columns a shipped matrix must carry (`overlap_level_rule_rederived`, `level_rederived_by`) exist because P001's
matrix once held levels the frozen rule could not reproduce on 17 of 19 rows: a level with no re-derived counterpart
is now a weakness the audit reports rather than a fact nobody checks.

    python 02_shared_code/literature/grade_wave_literature.py --paper P006 [--paper ...] | --all
"""
from __future__ import annotations

import argparse
import csv
import io
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
sys.path.insert(0, str(ROOT / "02_shared_code" / "package_factory"))
import grade_collisions as G                                        # noqa: E402
import topic_designs_wave1 as TD                                    # noqa: E402


def owner_of(pkg: str):
    """(topic id, design dict, module name) for a package id, found by reading every `topic_designs_wave*.DESIGNS`.

    This used to be a literal dict of the six wave-1 pairs, which raised KeyError on the first wave-2 package and
    would have to be edited by hand for every subsequent wave. The design modules are the record of who owns what.
    The design comes back with the id because the collision target is that design's frozen RQ, and reading it out
    of wave-1's module for a wave-4 package silently wrote an empty target instead. The module name comes back
    because the differentiation sentence names the corpus, and only the wave that owns the package knows which
    corpus that is.
    """
    import importlib
    for m in sorted(p.stem for p in (ROOT / "02_shared_code" / "package_factory").glob("topic_designs_wave*.py")):
        try:
            mod = importlib.import_module(m)
        except Exception:                                            # noqa: BLE001 - a broken wave module must not
            continue                                                 #                      hide the packages that grade
        for tid, d in getattr(mod, "DESIGNS", {}).items():
            if str(d.get("pkg", "")).startswith(pkg):
                return tid, d, m
    return "", {}, ""


def topic_of(pkg: str) -> str:
    return owner_of(pkg)[0]

# object = what is being measured; construct = the theoretical thing; measure = what is done to it;
# data = the population it is done on. A record has to fire on all four, with two construct hits, to be L4.
WAVE = {
 "P006": {"object": ["query", "instruction", "request", "utterance", "question"],
          "construct": ["underspecif", "ambigu", "missing information", "vague", "unresolved", "anaphor",
                        "ellipsis", "specificity", "information need"],
          "measure": ["search behaviour", "clarif", "retrieval performance", "task", "select", "ask",
                      "resolution rate", "effect on"],
          "data": ["conversational search", "agent", "language model", "llm", "dialogue", "tool", "search log"]},
 "P007": {"object": ["task", "query", "goal", "instruction"],
          "construct": ["complexit", "constraint", "difficulty", "cognitive load", "multi-facet", "compound",
                        "number of facets"],
          "measure": ["search behaviour", "exploration", "breadth", "depth", "performance", "time on task",
                      "interaction", "retrieval effectiveness"],
          "data": ["task", "agent", "language model", "llm", "search session", "conversational", "benchmark"]},
 "P008": {"object": ["query", "reformulation", "rewrite", "utterance", "instruction"],
          "construct": ["information loss", "fidelity", "semantic preservation", "meaning preservation",
                        "degradation", "faithful", "drift"],
          "measure": ["retrieval", "effectiveness", "recall", "nDCG", "hit rate", "overlap", "evaluation"],
          "data": ["conversational search", "agent", "language model", "llm", "dialogue", "tool call", "query log"]},
 "P009": {"object": ["document", "passage", "tool", "candidate", "answer"],
          "construct": ["lexical overlap", "word matching", "shortcut", "spurious", "surface cue",
                        "lexical bias", "question overlap"],
          "measure": ["ranking", "relevance", "selection", "judgment", "evaluation", "accuracy", "bias analysis"],
          "data": ["retrieval", "reading comprehension", "benchmark", "language model", "llm", "agent",
                   "ranking model"]},
 "P010": {"object": ["retriever", "ranker", "representation", "model", "document"],
          "construct": ["lexical", "semantic", "dense", "sparse", "embedding", "vocabulary mismatch",
                        "disagreement", "complementar"],
          "measure": ["retrieval", "ranking", "recall", "comparison", "analysis", "effectiveness", "case study"],
          "data": ["benchmark", "collection", "language model", "llm", "search", "passage", "tool"]},
 "P011": {"object": ["predicate", "relation", "argument", "semantic role", "verb", "structure"],
          "construct": ["semantic role", "predicate argument", "compositional", "relation matching",
                        "structure aware", "frame semantic"],
          "measure": ["retrieval", "ranking", "matching", "relevance", "prediction", "evaluation"],
          "data": ["language model", "llm", "benchmark", "passage", "tool", "knowledge graph", "dataset"]},
 # --- wave 2. Authored from each design's frozen construct, before those packages have any outcome to read. ---
 "P012": {"object": ["tool", "api", "document", "candidate", "passage", "query"],
          "construct": ["entity match", "semantic role", "predicate", "argument", "constraint match",
                        "structured query representation", "compositional match", "slot filling",
                        "functional matching"],
          "measure": ["ranking", "retrieval performance", "selection", "relevance", "prediction", "matching"],
          "data": ["tool", "api", "language model", "llm", "benchmark", "collection", "e-commerce"]},
 "P014": {"object": ["document", "candidate", "category", "item", "tool", "class"],
          "construct": ["prototype", "typicalit", "centrality", "centroid", "category structure",
                        "representativeness", "prototypical"],
          "measure": ["ranking", "selection", "judgment", "relevance", "classification", "scoring"],
          "data": ["retrieval", "ranking model", "language model", "llm", "benchmark", "annotation", "crowd"]},
 "P015": {"object": ["metadata", "description", "document", "dataset", "tool", "record"],
          "construct": ["metadata quality", "completeness", "richness", "documentation quality",
                        "description length", "quality score", "standard conformance"],
          "measure": ["discovery", "retrieval", "reuse", "findab", "ranking", "assessment"],
          "data": ["dataset", "repository", "catalogue", "tool", "linked data", "data paper", "registry"]},
 "P016": {"object": ["description", "abstract", "annotation", "metadata", "document", "query"],
          "construct": ["granularit", "verbosity", "detail", "specificity", "information density",
                        "over-specif", "length effect"],
          "measure": ["retrieval effectiveness", "ranking", "performance", "recall", "ndcg", "matching"],
          "data": ["collection", "retrieval", "language model", "llm", "benchmark", "catalogue", "tool"]},
 # --- wave 3. Same authoring rule: written from each design's frozen construct, before that package has a result.
 "P018": {"object": ["description", "document", "tool", "api", "resource"],
          "construct": ["use case", "procedural", "declarative", "framing", "purpose statement", "task oriented",
                        "intent oriented"],
          "measure": ["retrieval", "discovery", "ranking", "matching", "reachab"],
          "data": ["tool", "api", "catalogue", "documentation", "language model", "llm", "benchmark"]},
 "P020": {"object": ["metadata", "description", "title", "label", "name", "record"],
          "construct": ["congruence", "consistency", "coherence", "alignment", "term mismatch", "contradict",
                        "internal divergence"],
          "measure": ["discovery", "retrieval", "ranking", "quality assessment", "matching"],
          "data": ["catalogue", "repository", "dataset", "tool", "linked data", "metadata registry", "collection"]},
 "P021": {"object": ["term", "vocabulary", "synonym", "description", "query"],
          "construct": ["synonym control", "vocabulary normalis", "lexical ambiguity", "canonicalis",
                        "controlled vocabulary", "thesaurus"],
          "measure": ["retrieval effectiveness", "consistency", "ranking", "recall", "matching"],
          "data": ["language model", "llm", "catalogue", "collection", "benchmark", "knowledge graph", "web"]},
 "P022": {"object": ["description", "metadata", "document", "resource", "entry"],
          "construct": ["discriminative", "distinctiveness", "uniqueness", "contrastive",
                        "specificity", "completeness"],
          "measure": ["discoverability", "retrieval", "ranking", "reuse", "assessment"],
          "data": ["catalogue", "repository", "dataset", "collection", "metadata registry", "tool", "benchmark"]},
 # --- wave 4. Same authoring rule: each lexicon is the construct of that design's frozen RQ, written before the
 #     package had any outcome to read.
 "P023": {"object": ["assistant turn", "agent turn", "response", "utterance", "message", "tool call", "action"],
          "construct": ["epistemic modality", "hedg", "uncertaint", "epistemic", "confidence expression",
                        "hedge detection", "epistemic marker", "commitment"],
          "measure": ["followed by", "next action", "verification", "additional search", "inspection",
                      "predict", "association", "behaviour"],
          "data": ["language model", "llm", "agent", "conversational search", "dialogue", "search log",
                   "assistant"]},
 "P024": {"object": ["reasoning", "chain of thought", "response", "answer", "internal state", "plan", "trace"],
          "construct": ["diverg", "discrepanc", "disclos", "alignment", "private", "verbal report",
                        "inconsistent", "expressed uncertainty"],
          "measure": ["behaviour", "action", "comparison", "predict", "stopping", "inspection", "accuracy"],
          "data": ["language model", "llm", "agent", "reasoning trace", "dialogue", "benchmark", "chain of thought"]},
 "P025": {"object": ["observation", "evidence", "source", "document", "tool output", "retrieved result", "passage"],
          "construct": ["contradict", "conflict", "inconsisten", "disagreement", "diverg", "belief revision",
                        "ambiguity from"],
          "measure": ["uncertaint", "modality", "hedg", "confidence", "escalat", "ranking", "appraisal"],
          "data": ["retrieval", "search", "agent", "language model", "llm", "multi-source", "web", "query"]},
 "P026": {"object": ["search session", "turn", "query", "task", "trajectory", "episode"],
          "construct": ["satisfic", "sufficien", "stop", "terminat", "foraging", "threshold", "quit",
                        "enough information"],
          "measure": ["stopping", "search behaviour", "session length", "additional search", "information gain",
                      "inspection", "decision"],
          "data": ["information seeking", "search log", "agent", "language model", "llm", "interactive search",
                   "task"]},
 # --- wave 5. Same authoring rule: each lexicon is the construct of that design's frozen RQ, written before the
 #     package had any outcome to read.
 "P027": {"object": ["turn", "utterance", "assistant message", "reasoning", "dialogue act", "plan", "question"],
          "construct": ["speech act", "dialogue act", "discourse act", "illocutionar", "annotat acts",
                        "conversational move", "act type"],
          "measure": ["frequenc", "distribut", "sequence", "position", "predict", "association", "cod"],
          "data": ["language model", "llm", "agent", "dialogue", "conversation", "reasoning trace", "benchmark"]},
 "P028": {"object": ["claim", "conclusion", "answer", "assertion", "statement", "evidence", "observation"],
          "construct": ["premature closure", "order effect", "assertion before", "belief perseverance",
                        "evidence first", "sequenc", "timing of the answer", "distortion"],
          "measure": ["accuracy", "supported", "overconfidence", "insufficient search", "revis", "association"],
          "data": ["agent", "language model", "llm", "search", "reasoning", "human information seeking",
                   "diagnostic"]},
 "P029": {"object": ["error", "failure", "observation", "feedback", "tool output", "turn"],
          "construct": ["repair", "self-correct", "recovery", "backtrack", "revision after", "error response",
                        "acknowledg"],
          "measure": ["retry", "abandon", "give up", "next action", "language", "success", "behaviour"],
          "data": ["agent", "language model", "llm", "tool use", "interactive", "task", "benchmark"]},
 "P030": {"object": ["connective", "causal expression", "justification", "explanation", "clause", "argument"],
          "construct": ["causal connective", "discourse marker", "coherence relation", "rhetorical relation",
                        "explicit causation", "because", "therefore", "faithful"],
          "measure": ["support", "ground", "evidence", "entail", "verif", "align", "accuracy"],
          "data": ["language model", "llm", "agent", "chain of thought", "reasoning", "text", "evidence"]},
 "P031": {"object": ["explanation", "argument", "chain", "step", "narrative", "account"],
          "construct": ["explanatory coherence", "plausibility", "fluenc", "narrative fallac", "seductive detail",
                        "coherence", "chain length", "convincing"],
          "measure": ["judge", "rate", "persuad", "accuracy", "support", "overlook", "confusion of"],
          "data": ["language model", "llm", "human", "reasoning", "discourse", "evidence", "experiment"]},
 "P032": {"object": ["plan", "intention", "action", "tool call", "step", "instruction"],
          "construct": ["plan", "adherence", "alignment", "consistency between", "grounding of intention",
                        "intent-to-action", "decomposition"],
          "measure": ["match", "overlap", "execut", "follow", "compare", "predict", "deviat"],
          "data": ["agent", "language model", "llm", "tool use", "robot", "benchmark", "trajectory"]},
 # --- wave 6. Same authoring rule: each lexicon is the construct of that design's frozen RQ, written before the
 #     package had any outcome to read.
 "P033": {"object": ["search session", "rollout", "trajectory", "query", "task", "interaction"],
          "construct": ["depth", "effort", "session length", "number of queries", "task complexit",
                        "query difficult", "cognitive load", "budget"],
          "measure": ["associat", "predict", "match", "effect on", "model", "compare"],
          "data": ["agent", "language model", "llm", "search log", "interactive search", "benchmark",
                   "software engineering"]},
 "P034": {"object": ["step", "action", "query", "patch", "document", "observation", "result"],
          "construct": ["information scent", "forag", "cue valid", "expectation", "patch.leaving",
                        "prior knowledge", "estimate of relevance"],
          "measure": ["predict", "next", "choice", "select", "association", "model"],
          "data": ["human information seeking", "agent", "language model", "llm", "search", "web",
                   "interactive"]},
 "P035": {"object": ["observation", "result", "document", "step", "session", "evidence"],
          "construct": ["marginal gain", "diminishing return", "novelt", "redundanc", "new information",
                        "satisfic", "persist", "stop"],
          "measure": ["continue", "stopping", "length", "yield", "decision", "association"],
          "data": ["search session", "agent", "language model", "llm", "foraging", "interactive search"]},
 "P036": {"object": ["tool", "action", "interface", "source", "step", "command"],
          "construct": ["switching cost", "task set", "attention residue", "cognitive cost", "diversit",
                        "exploration", "overlap between sources"],
          "measure": ["cost", "performance", "quality", "effect", "rate", "association"],
          "data": ["human computer interaction", "agent", "language model", "llm", "multi-tool", "search"]},
 "P037": {"object": ["first action", "initial query", "step", "trajectory", "decision", "choice"],
          "construct": ["path depend", "primac", "anchor", "lock.in", "commitment", "mental set",
                        "sequenc of actions", "state dependency"],
          "measure": ["constrain", "predict", "determine", "downstream", "diverg", "associate"],
          "data": ["agent", "language model", "llm", "search", "decision making", "benchmark", "trajectory"]},
 "P038": {"object": ["query", "command", "action", "attempt", "session", "step"],
          "construct": ["repetit", "duplicate", "loop", "persever", "rumina", "revisit", "circular",
                        "stuck"],
          "measure": ["detect", "rate", "effect on", "outcome", "identify", "associat"],
          "data": ["search log", "agent", "language model", "llm", "interactive search", "conversation"]},
 "P039": {"object": ["tool", "function", "candidate", "api", "description", "retrieval"],
          "construct": ["near synonym", "distractor", "similar tool", "confus", "ambigu", "decoy",
                        "misselec", "disambiguat"],
          "measure": ["select", "accura", "rank", "hit", "error", "associate"],
          "data": ["agent", "language model", "llm", "tool use", "benchmark", "api"]},
 "P040": {"object": ["description", "documentation", "tool", "api", "parameter", "interface"],
          "construct": ["affordance", "action verb", "verb", "capability statement", "parameter list",
                        "wording", "phrasing"],
          "measure": ["select", "retriev", "accura", "effect on", "rank", "associat"],
          "data": ["agent", "language model", "llm", "api documentation", "tool use", "human computer interaction"]},
 "P041": {"object": ["tool", "namespace", "candidate", "list", "menu", "catalogue"],
          "construct": ["overload", "set size", "number of tools", "grouping", "hierarch", "choice",
                        "categoris", "prefix"],
          "measure": ["select", "accura", "performance", "rank", "effect", "associat"],
          "data": ["agent", "language model", "llm", "human computer interaction", "tool use", "api"]},
 "P042": {"object": ["server", "provider", "repository", "tool", "registry", "catalogue"],
          "construct": ["specialis", "ecosystem", "concentration", "redundanc", "duplicate", "coverage",
                        "diversity of sources", "naming convention"],
          "measure": ["describe", "count", "share", "overlap", "measure", "index"],
          "data": ["mcp", "software repository", "api ecosystem", "agent", "mining software", "registry"]},
 "P043": {"object": ["candidate", "document", "result", "context", "retrieval", "ranking"],
          "construct": ["irrelevant", "distractor", "contaminat", "noise", "unrelated", "zero overlap",
                        "precision"],
          "measure": ["rank", "degrade", "effect on", "accuracy", "associate", "margin"],
          "data": ["retrieval augmented", "language model", "llm", "agent", "interactive search", "benchmark"]},
 "P044": {"object": ["tool", "function", "call", "service", "step", "pair"],
          "construct": ["dependenc", "co.occur", "composition", "chain", "workflow", "graph",
                        "multi tool", "network"],
          "measure": ["select", "predict", "frequen", "overlap", "associate", "accuracy"],
          "data": ["agent", "language model", "llm", "service composition", "workflow", "benchmark"]},
 "P045": {"object": ["hypothesis", "evidence", "search", "query", "turn", "trajectory"],
          "construct": ["primac", "anchor", "confirmation bias", "premature closure", "consisten with belief",
                        "selective exposure", "persever", "lock.in", "belief", "expectation"],
          "measure": ["narrows", "concentrat", "restrict", "predict", "associate", "effect on"],
          "data": ["agent", "language model", "llm", "information search", "diagnostic reasoning", "human study"]},
 "P046": {"object": ["plan", "instruction", "task specification", "action", "constraint", "entity"],
          "construct": ["specificity", "granular", "detail", "ambigu", "vague", "constraint enumeration",
                        "explicit naming", "decomposition"],
          "measure": ["improve", "performance", "success", "redundan", "repea", "associate"],
          "data": ["agent", "language model", "llm", "robot planning", "prompt", "benchmark"]},
 "P047": {"object": ["error", "mistake", "critique", "action", "call", "turn", "response"],
          "construct": ["self.correct", "acknowledg", "apolog", "reflect", "repair", "revis", "recovery",
                        "stated versus observed", "superficial"],
          "measure": ["change", "recover", "repeat", "effect on", "associate", "detect"],
          "data": ["agent", "language model", "llm", "dialogue", "interactive system", "conversation"]},
 "P050": {"object": ["sequence", "transition", "step", "action", "search session", "trajectory"],
          "construct": ["grammar", "markov", "transition probabil", "n.gram", "regularit", "pattern",
                        "cross.task transfer", "domain generalis"],
          "measure": ["predict", "likelihood", "log.loss", "agre", "compare", "cluster"],
          "data": ["agent", "language model", "llm", "software repository", "search log", "process mining"]},
 "P051": {"object": ["trajectory", "episode", "step", "task", "attempt", "rollout"],
          "construct": ["early signal", "failure predict", "risk of failure", "abandon", "precursor",
                        "early warning", "outcome predict"],
          "measure": ["predict", "auc", "classif", "detect", "earl", "associate"],
          "data": ["agent", "language model", "llm", "software engineering", "benchmark", "interactive search"]},
 "P052": {"object": ["error", "failure", "action", "command", "step", "retry"],
          "construct": ["recovery", "repair", "replan", "correct", "window", "lag", "cascad",
                        "fault toleran", "rescue"],
          "measure": ["recover", "succeed", "predict", "decay", "associate", "effect on"],
          "data": ["agent", "language model", "llm", "robot", "software engineering", "dialogue"]},
 "P053": {"object": ["trajectory", "episode", "demonstration", "experience", "dataset", "rollout"],
          "construct": ["select", "curat", "reuse", "replay", "dedup", "filter", "value of an episode",
                        "efficien"],
          "measure": ["select", "rank", "improve", "agreement", "cost", "associate"],
          "data": ["agent", "language model", "llm", "imitation learning", "reinforcement learning", "benchmark"]},
 "P056": {"object": ["instruction", "task specification", "information need", "requirement", "query", "tool"],
          "construct": ["implicit", "underspecif", "unstated", "missing constraint", "ambigu", "vague",
                        "incomplete specification", "clarification"],
          "measure": ["cover", "recover", "completen", "predict", "retrieve", "associate"],
          "data": ["agent", "language model", "llm", "dialogue", "information retrieval", "benchmark"]},
 "P062": {"object": ["search session", "dialogue", "utterance", "trace", "protocol", "problem solving"],
          "construct": ["discourse structure", "move", "coherence", "successful", "failed", "marker of success",
                        "verbal protocol", "narrative"],
          "measure": ["differ", "characterise", "predict", "associate", "compare", "classify"],
          "data": ["information seeking", "agent", "language model", "llm", "human study", "dialogue"]},
 "P063": {"object": ["trace", "step", "demonstration", "procedure", "annotation", "rationale"],
          "construct": ["component", "carry forward", "reusab", "transfer", "procedural knowledge", "exception",
                        "observation", "context and condition"],
          "measure": ["carry", "reuse", "transfer", "predict", "improve", "associate"],
          "data": ["agent", "software agent", "language model", "llm", "workflow", "benchmark"]},
 "P064": {"object": ["instruction", "demonstration", "rule", "example", "procedure", "trace"],
          "construct": ["abstraction", "concreteness", "generality", "specificity", "verbatim", "hierarchical",
                        "level of description"],
          "measure": ["transfer", "generalise", "improve", "predict", "compare", "associate"],
          "data": ["agent", "language model", "llm", "learning", "problem solving", "human study"]},
 "P065": {"object": ["memory", "context", "summary", "trajectory", "history", "prompt"],
          "construct": ["compression", "summarisation", "information loss", "retention", "forgetting",
                        "provenance loss", "constraint retention", "budget"],
          "measure": ["retain", "lose", "compress", "predict", "compare", "measure"],
          "data": ["language model", "llm", "agent", "dialogue", "retrieval", "benchmark"]},
 "P066": {"object": ["attempt", "episode", "case", "memory", "response", "question"],
          "construct": ["relation", "restatement", "refinement", "contradiction", "entailment", "duplication",
                        "consolidation", "similarity"],
          "measure": ["classify", "relate", "consolidate", "predict", "detect", "associate"],
          "data": ["case based reasoning", "agent", "language model", "llm", "episodic memory", "dialogue"]},
 "P067": {"object": ["action", "code", "command", "turn", "tool call", "instruction"],
          "construct": ["code as action", "natural language action", "information density", "executable",
                        "representation", "action space", "interpreter"],
          "measure": ["compare", "densit", "length", "answer", "associate", "effect on"],
          "data": ["agent", "language model", "llm", "code", "benchmark", "interactive"]},
 "P068": {"object": ["reflection", "critique", "revision", "thought", "reasoning trace", "answer"],
          "construct": ["self-correction", "reconsideration", "ritual", "superficial", "verbal marker",
                        "without change", "monitoring"],
          "measure": ["change", "improve", "occur", "associate", "detect", "compare"],
          "data": ["language model", "llm", "agent", "multimodal", "reasoning", "dialogue"]},
 "P069": {"object": ["case", "episode", "trajectory", "task", "memory", "library"],
          "construct": ["reuse", "retrieval of prior work", "analogical transfer", "similarity of tasks",
                        "adaptation", "episodic memory"],
          "measure": ["reuse", "retrieve", "transfer", "predict", "associate", "improve"],
          "data": ["agent", "language model", "llm", "case based reasoning", "reinforcement learning",
                   "benchmark"]},
 "P070": {"object": ["corpus", "dataset", "benchmark", "trajectory", "log", "metadata"],
          "construct": ["availability", "coverage", "provenance", "reusability", "documentation",
                        "secondary analysis", "inventory"],
          "measure": ["describe", "count", "compare", "inventory", "aggregate", "characterise"],
          "data": ["agent", "language model", "llm", "survey", "dataset", "interaction log"]},
}
G.PAPERS.update({k: v for k, v in WAVE.items() if k not in G.PAPERS})

BY = "grade_collisions.grade(P00x PAPERS lexicons extended by grade_wave_literature.py; four-family rule unchanged)"
DEFAULT_POPULATION = "an agent-instruction corpus with a frozen lexical ranker"
DIFF = {
 "L4": "same construct, same population and same outcome as this package: the package's claim is narrowed to the "
       "mechanism, corpus and instrument named in its freeze, and the difference is stated in this column",
 "L2": "adjacent construct or adjacent measure: cited as background, not as a competitor",
 "L1": "shares an object or a measure but not the construct: cited only where a term needs a source",
 "L0": "no family overlap beyond shared vocabulary: retained in the screen record, not cited",
}


def differentiation(lvl: str, mod: str) -> str:
    """The per-row differentiation sentence, with the corpus clause taken from the wave that owns the package.

    L3 used to be one literal naming the routing-corpus waves, so every transcript-corpus package shipped a row
    stating that its contribution was measured on a corpus it does not use. The wave module now declares its own
    population, and a module that declares none is treated as the routing-corpus case it was written for.
    """
    if lvl != "L3":
        return DIFF[lvl]
    pop = DEFAULT_POPULATION
    if mod:
        try:
            import importlib
            pop = getattr(importlib.import_module(mod), "CONTRIBUTION_POPULATION", DEFAULT_POPULATION)
        except Exception:                                            # noqa: BLE001 - an unreadable module keeps the
            pass                                                     #                      sentence its wave was written for
    return ("same construct on an adjacent population or outcome: this package's contribution is the measured "
            f"mechanism on {pop}")


def grade_one(pkg: str) -> dict:
    topic, design, mod = owner_of(pkg)
    if not design:
        raise SystemExit(f"ABORT {pkg}: no topic_designs_wave*.DESIGNS entry owns it, so its collision target - the "
                         f"frozen research question this matrix grades against - is unknown")
    target = (design.get("rq") or "").strip()
    if not target:
        raise SystemExit(f"ABORT {pkg}/{topic}: the design carries no `rq`, so every row would get an empty "
                         f"collision_target column")
    pap = next(p for p in (ROOT / "papers").glob(pkg + "_*"))
    f = pap / "literature_matrix.csv"
    if not f.is_file():
        raise SystemExit(f"ABORT {pkg}: no literature_matrix.csv - the harvest has not run")
    rows = list(csv.DictReader(io.StringIO(f.read_text(encoding="utf-8"))))
    hdr = list(rows[0].keys())
    for c in ("overlap_level", "overlap_level_rule_rederived", "level_rederived_by", "differentiation",
              "verify_status", "paper_id", "collision_target"):
        if c not in hdr:
            hdr.append(c)
    dist, changed = {}, 0
    olds = [r.get("differentiation") for r in rows]      # so the count of rewritten sentences is measured, not meant
    for r in rows:
        text = " ".join(str(r.get(k) or "") for k in ("problem", "main_result", "method", "dataset_used"))
        lvl, hit, n = G.grade(pkg, str(r.get("title") or ""), text)
        if r.get("overlap_level") != lvl:
            changed += 1
        r["overlap_level"] = lvl
        r["overlap_level_rule_rederived"] = "yes"
        r["level_rederived_by"] = BY
        r["differentiation"] = differentiation(lvl, mod)
        r["paper_id"] = pkg
        # Written unconditionally: the harvester seeds this column with the placeholder "graded in novelty_audit",
        # and an `or` fallback therefore never fired, so the column that is supposed to say what a record collides
        # with carried a note about a later step instead of the frozen question.
        r["collision_target"] = target[:160]
        r["verify_status"] = (f"Crossref record; abstract text present in {len(text)} characters; "
                              f"graded by the four-family rule; {lvl}")
        dist[lvl] = dist.get(lvl, 0) + 1
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=hdr, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
    w.writeheader()
    for r in rows:
        w.writerow({c: str(r.get(c) or "") for c in hdr})
    f.write_text(buf.getvalue(), encoding="utf-8")
    return {"paper": pkg, "rows": len(rows), "levels": dist, "levels_changed": changed,
            "sentences_rewritten": sum(1 for r, o in zip(rows, olds) if r["differentiation"] != o),
            "strongest": [r["cite_key"] for r in rows if r["overlap_level"] == "L4"][:6]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", action="append", default=[])
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    pks = a.paper or (sorted(WAVE) if a.all else [])
    out = [grade_one(p) for p in pks]
    for o in out:
        print(o)
    (ROOT / "results_raw" / f"EXP0127_wave_literature_grading_{time.strftime('%Y%m%dT%H%M%S')}.json").write_text(
        __import__("json").dumps({"exp_id": "EXP-0127", "seed": "n/a (deterministic rule)",
                                  "rule": BY, "papers": out, "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                  "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S")},
                                 indent=1, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
