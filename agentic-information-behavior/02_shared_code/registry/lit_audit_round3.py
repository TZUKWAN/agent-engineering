"""Round-3 literature audit: two 2026 agentic-search studies found via the arXiv API and recorded against
P001 (novelty/near-neighbour) and against the topic registry (T008's survival test).

Fetched with `https://export.arxiv.org/api/query`, abstracts read in full; nothing here is quoted from memory.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PAP = ROOT / "papers" / "P001_routing_failure_qpp"
TODAY = "2026-09-18"

ROWS = [
    dict(cite_key="arxiv2601.17617", year=2026, venue="arXiv preprint 2601.17617v3 (2026-01-24)",
         title="Agentic Search in the Wild: Intents and Trajectory Dynamics from 14M+ Real Search Requests",
         problem="how agentic search sessions unfold at scale, and whether later queries reuse retrieved evidence",
         dataset_used="14.44M search requests / 3.97M sessions from DeepResearchGym (open API, external agentic clients)",
         method="sessionisation; LLM-based session-intent and step-wise query-reformulation labelling; "
                "Context-driven Term Adoption Rate (CTAR) measuring whether new query terms are lexically "
                "traceable to accumulated evidence",
         metric="CTAR; session-step and inter-request interval distributions; repetition by intent",
         main_result=">90% of multi-turn sessions have <=10 steps and 89% of inter-step intervals <1 min; "
                     "fact-seeking repeats more and grows more repetitive over time while reasoning sessions "
                     "explore wider; on average 54% of newly introduced query terms appear in the accumulated "
                     "evidence context",
         collision_target="T037 (P001) novelty boundary; T008 (P002) headline",
         overlap_level="L3 for P001 / L4 for T008",
         code_or_data_public="unknown from abstract; DeepResearchGym described as an open-source search API",
         url="https://arxiv.org/abs/2601.17617", retrieved_on=TODAY,
         verify_status="abstract read from arXiv API on 2026-09-18", paper_id="P001",
         differentiation="they analyse behaviour AFTER retrieval and describe sessions; they never ask whether a "
                         "retriever will miss the required tool BEFORE retrieval, use no QPP signal, and their "
                         "labels come from an LLM annotator. CTAR is a *backward-looking* lexical-traceability "
                         "measure over accumulated evidence, whereas our coverage/CLARITY/ECLE family is "
                         "*forward-looking* over the candidate catalogue only. Must be cited: it is the closest "
                         "neighbour for the 'lexical overlap between query and evidence' component of our features."),
    dict(cite_key="arxiv2604.22436", year=2026, venue="arXiv preprint 2604.22436v1 (2026-04-24)",
         title="AgentSearchBench: A Benchmark for AI Agent Search in the Wild",
         problem="retrieval and reranking of *agents* (not tools) for task queries under real provider diversity",
         dataset_used="~10,000 real-world agents across multiple providers",
         method="formalise agent search as retrieval + reranking with executable task queries and high-level task "
                "descriptions; relevance judged by execution-grounded performance signals; execution-aware probing",
         metric="retrieval/reranking quality against execution-grounded relevance",
         main_result="consistent gap between semantic similarity and actual agent performance; lightweight "
                     "behavioural/execution signals improve ranking",
         collision_target="T037 (P001) and T008; also the series' 'predict failure' framing",
         overlap_level="L3",
         code_or_data_public="yes github.com/Bingo-W/AgentSearchBench",
         url="https://arxiv.org/abs/2604.22436", retrieved_on=TODAY,
         verify_status="abstract read from arXiv API on 2026-09-18", paper_id="P001",
         differentiation="they improve ranking using execution signals, i.e. they act after the retrieval decision "
                         "and need runs; our predictor acts before retrieval with no execution and no model. Their "
                         "semantic-similarity/performance gap is independent support for our motivation, not a "
                         "competing method."),
]


def main():
    lm = PAP / "literature_matrix.csv"
    df = pd.read_csv(lm)
    before = len(df)
    df = pd.concat([df, pd.DataFrame([r for r in ROWS if r["cite_key"] not in set(df.cite_key)])],
                   ignore_index=True)
    df.to_csv(lm, index=False)
    print("literature_matrix rows", before, "->", len(df))

    rw = PAP / "paper.md"
    t = rw.read_text(encoding="utf-8")
    key = "Agentic Search in the Wild"
    if key not in t:
        anchor = "**Where the LIS question sits.**"
        assert anchor in t, "no related-work paragraph to extend"
        add = ("- **Agentic search behaviour at scale.** `Agentic Search in the Wild` (arXiv:2601.17617) sessionises "
               "14.44M real agentic search requests, labels intents and reformulations with an LLM annotator, and "
               "introduces Context-driven Term Adoption Rate to ask whether new query terms are traceable back to "
               "*already retrieved* evidence; `AgentSearchBench` (arXiv:2604.22436) shows semantic similarity "
               "disagrees with executed agent performance. Both look backwards at behaviour after retrieval or need "
               "executions; neither predicts, before retrieval, whether a catalogue will miss the required item - "
               "which is our question, and the reason our lexical-overlap features are computed forward over the "
               "candidate set only.\n")
        t = t.replace(anchor, add.strip() + "\n\n" + anchor, 1)
        rw.write_text(t, encoding="utf-8")
        print("related work extended")

    sa = PAP / "sota_audit.md"
    tx = sa.read_text(encoding="utf-8")
    if "2601.17617" not in tx:
        tx += ("\n## Round-3 additions (2026-09-18, arXiv API)\n\n"
               "| work | what it does | comparable to P001? | why |\n|---|---|---|---|\n"
               "| arXiv:2601.17617 Agentic Search in the Wild | 14.44M-request log analysis; LLM-labelled intents "
               "and reformulations; CTAR term-adoption measure | **not directly comparable** | no failure prediction, "
               "no pre-retrieval metric, different unit (sessions of queries, not per-catalogue routing), labels "
               "from an LLM; but it is the nearest neighbour for query-evidence lexical overlap, so it is cited in "
               "§2 and its 54% term-adoption figure is the natural external anchor for our coverage features |\n"
               "| arXiv:2604.22436 AgentSearchBench | agent (not tool) retrieval+reranking benchmark with "
               "execution-grounded relevance | not directly comparable | ranks agents, needs executions, reports "
               "ranking quality not failure risk; supports our motivation (similarity != performance) |\n")
        sa.write_text(tx, encoding="utf-8")
        print("sota_audit updated")

    reg = ROOT / "00_program_registry" / "topic_registry.csv"
    tr = pd.read_csv(reg)
    m = tr.topic_id == "T008"
    tr.loc[m, "blocking_issue"] = (
        "LIT AUDIT ROUND 3 (2026-09-18, arXiv API): arXiv:2601.17617 'Agentic Search in the Wild' already occupies "
        "large-scale agentic-search session/trajectory dynamics (14.44M requests, 3.97M sessions) including "
        "step-length and repetition distributions and reformulation traceability, so a *descriptive* ISP-stage "
        "measurement at scale is no longer a publishable gap on its own. Surviving angle must be methodological and "
        "auditable rather than descriptive: replicable RULE-BASED stage coding (no LLM annotator) + explicit "
        "right-censoring handling (SWE-ZERO is capped at 32 turns, p50=32) + a first-order Markov null + "
        "human-agreement statistics, and it must be positioned against arXiv:2601.17617 as the LLM-annotated "
        "counterpart. Decide at the pilot: if rule-based markers cannot reach an interpretable coverage/precision "
        "level, T008 is killed rather than re-scoped again.")
    tr.loc[m, "status"] = "w2_pilot_required_lit_round3_blocked"
    tr.to_csv(reg, index=False)
    print("topic registry: T008 updated")
    log = ROOT / "docs" / "lit_audit_round3_20260918.md"
    log.write_text("# Literature audit round 3 (2026-09-18)\n\n"
                   "Queries run against `https://export.arxiv.org/api/query` (abstracts read in full):\n"
                   "- `ti:\"Agentic Search in the Wild\"` -> arXiv:2601.17617v3, arXiv:2604.22436v1 (AgentSearchBench)\n"
                   "- `abs:\"information search process\" AND abs:agent` -> no hits\n"
                   "- `abs:\"tool use\" AND abs:\"behavioral analysis\" AND cat:cs.HC` -> no hits\n\n"
                   "Consequences recorded in P001 (literature matrix, related work, SOTA audit) and in the topic "
                   "registry (T008 blocked pending pilot; T012 unaffected).\n", encoding="utf-8")
    print("audit log written")


main()
