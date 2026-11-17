"""EXP-0070: read the appended collision rows and write what they actually are, including the one that is not.

EXP-0067/0068/0069 appended 29 rows to the curated matrices with `verify_status=pending_hand_check` and an empty
`differentiation` cell, because a term-frequency screen cannot say what a paper does. This pass reads every one of
those abstracts and fills `problem / dataset_used / method / metric / main_result / differentiation` from the reading,
and it is where the screen's own error surfaces: one of P003's 20 appended rows is a pedestrian-safety study that
matched on the word "crosswalk". It is relabelled `rejected_on_read` and kept in the file with its reason, not deleted,
so the precision of the screen (19/20 for P003, 7/9 readable-and-relevant for P004) is on the record.

Two of P004's nine anchored survivors still have no abstract anywhere reachable; their titles are on-topic but they
stay `pending_hand_check`, because a title is not a read.

    python 02_shared_code/registry/fill_matrix_hand_reads_p003_p004.py
"""
from __future__ import annotations

import csv, io, json, pathlib, re, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
REG = ROOT / "00_program_registry"
PAP = ROOT / "papers"
NOW = time.strftime("%Y-%m-%d")

# key -> (problem, dataset, method, metric, main_result, code, differentiation, verdict)
# verdict: "read" = adjudicated and kept as prior work; "reject" = false positive of the screen, kept and labelled.
P003 = {
 "A Novel Solution for Manufacturing Interoperability": (
  "cloud-manufacturing service architectures cannot talk to each other across distributed clouds",
  "conceptual; no dataset named", "reference-architecture proposal with an interoperability service provider layer",
  "none reported", "a proposed ISP-mediated fulfilment scheme; no quantitative evaluation reported",
  "no", "domain-specific (manufacturing) interoperability architecture; P003 measures whether agent-trajectory "
  "releases' own metadata supports conversion, and reports coverage rather than proposing a target architecture", "read"),
 "A Study on Harmonizing Multi-Format EDI": (
  "heterogeneous EDI formats (ANSI X12, EDIFACT, XML) block supply-chain integration",
  "retail/logistics EDI transaction sets in a case study plus controlled simulations",
  "design-science: a data-native harmonisation framework with prototype workflows",
  "mapping complexity, processing throughput, data consistency, operational efficiency",
  "a single harmonised internal representation reduces mapping effort versus pairwise converters",
  "no", "same convert-and-harmonise logic as P003 but on a standardised, vendor-governed format family; P003's "
  "inputs have no governing schema, which is why its failure modes are coverage and attribution rather than mapping cost", "read"),
 "An LLM-Driven Semantic Control Plane": (
  "the O(N x M) adapter space across lakehouse table formats loses semantic fidelity ('interoperability tax')",
  "multiple storage/table formats over a lakehouse; workshop-scale evaluation",
  "generative, versioned mapping manifest with a 3-tier dialect decomposition",
  "reported behavioural-type-drift and signal-loss diagnostics",
  "a manifest replaces per-engine adapters while preserving query semantics in the case evaluated",
  "no", "closest prior work to P003's mechanism: it also treats a machine-generated crosswalk as the interoperability "
  "artefact. Difference: it targets table formats with a known schema registry, while P003 targets trajectory releases "
  "whose source schemas are self-declared and often absent, and P003 quantifies what cannot be recovered", "read"),
 "An integrated heterogeneous web service retrieval": (
  "instance-only matching misses metadata semantics when retrieving heterogeneous web services",
  "web-service repositories with multi-version services",
  "combined instance-based + metadata-based schema matching",
  "matching precision/recall against a ground truth",
  "the combination outperforms either family used alone",
  "no", "matching-quality work on curated services; P003 does not build a matcher - it measures whether the metadata "
  "needed by any matcher is present in released corpora", "read"),
 "Analyzing Data Format Interoperability in API Ecosystems": (
  "variety of structured payloads in API request/response exchange",
  "API ecosystem data under a big-data architecture (poorly specified)",
  "conceptual discussion centred on XML's dynamic typing",
  "none reported", "no measurable result reported; the paper is largely descriptive",
  "no", "kept as evidence that format-interoperability claims are often made without measurement; P003's contribution "
  "is the measurement, so this row supports the gap rather than competing with the method", "read"),
 "Automated Interoperability based on Decision Tree": (
  "schema matching is done manually and resists automation",
  "two heterogeneous source schemas (domains named in the paper)",
  "decision-tree classifier over matching patterns",
  "matching accuracy/F-measure",
  "a learned matcher reaches usable accuracy on the evaluated pair",
  "no", "matcher construction; P003 is upstream of it (input-metadata availability)", "read"),
 "Biomedical heterogeneous data categorization": (
  "clinical text/audio/video heterogeneity plus privacy constraints block integration",
  "clinical corpora from multiple institutions",
  "categorisation into semantic groups then schema mapping toward a canonical model",
  "integration coverage reported qualitatively", "a staged pipeline from unstructured records to mapped schemas",
  "no", "clinical-domain integration with expert-in-the-loop; P003's population is public ML releases where no "
  "institutional custodian can be asked, so unverifiable metadata cannot be resolved by consultation", "read"),
 "CONCEPTUAL FRAMEWORK FOR XML SCHEMA MAPPING": (
  "source-to-target mapping for XML needs declared semantics and access paths",
  "XML schemas (illustrative)", "mapping-generation framework over element similarities",
  "mapping expressiveness, not accuracy against a benchmark", "a framework that emits both correspondences and load paths",
  "no", "format-specific (XML) mapping theory; P003's corpora are JSONL/Parquet with no governing schema to map from", "read"),
 "Enhancing Big Data Interoperability: Automating Schema Expansion": (
  "Parquet columns absent from the destination BigQuery schema block migration",
  "Parquet files loaded into BigQuery tables", "an open-source Python migrator that expands the target schema",
  "successful migration / schema-evolution handling", "a working library used in data-engineering practice",
  "yes (stated as an open-source library)", "engineering of schema evolution for one well-typed pair of formats; "
  "P003 measures recoverability across releases whose types are undocumented", "read"),
 "Impact of FHIR Data Format in Healthcare Interoperability": (
  "non-standard clinical datasets prevent querying and continuity of care",
  "healthcare settings adopting FHIR resources", "descriptive study of FHIR resource adoption",
  "none reported", "standardisation improves interchange; adoption is limited by legacy architecture",
  "no", "a standards-adoption argument; P003's finding is the absence of any comparable standard for agent trajectories", "read"),
 "Joint Word Segmentation Based Substring Matching": (
  "naming heterogeneity degrades schema matching during legacy-to-SaaS migration",
  "heterogeneous data stores in migration projects", "word-segmentation-based substring similarity for element names",
  "matching accuracy", "improved name-similarity matching over plain substring measures",
  "no", "lexical matcher component; orthogonal to P003's metadata-coverage question", "read"),
 "Mapping the Metadata Landscape of Energy Data Repositories": (
  "energy repositories may not supply the dataset- and column-level metadata OEMetadata requires",
  "records from ten energy data catalogues",
  "harvest, crosswalk to OEMetadata v2, normalise, compute dataset- and resource-level coverage",
  "field-level coverage percentages per portal",
  "coverage is weak and uneven: licences absent in half the portals, provenance concentrated in two, column-level "
  "data dictionaries largely absent",
  "yes (crosswalks and a reproducible harvesting workflow released)",
  "STRUCTURALLY THE CLOSEST PRIOR WORK FOUND: same census-plus-coverage design, applied to energy catalogues against "
  "an existing standard. P003 differs in object (agent-trajectory releases), in having no governing standard to "
  "crosswalk against - which is itself a finding - and in testing round-trip recoverability rather than declared-field "
  "coverage alone", "read"),
 "Metadata Interoperability and Standardization - A Study of Methodology Part I": (
  "proliferation of metadata schemas blocks exchange across digital libraries",
  "survey of published interoperability efforts",
  "methodological analysis at the schema level",
  "none (qualitative taxonomy of methods)",
  "a schema-level taxonomy of interoperability methods", "no",
  "canonical background for P003's level distinction; it is a methodology survey, not a measurement of a corpus family", "read"),
 "Metadata Interoperability and Standardization - A Study of Methodology Part II": (
  "same problem at record and repository level",
  "survey of published efforts", "methodological analysis at record and repository level",
  "none (qualitative)", "element-based vs value-based perspectives on achieved interoperability", "no",
  "as Part I; P003 operationalises the record-level view as a measurable coverage statistic", "read"),
 "Overview on Data Ingestion and Schema Matching": (
  "ingestion and alignment of heterogeneous sources in the big-data era",
  "literature", "narrative overview", "none", "identifies ML-based matching as the current direction",
  "no", "survey; background for the mechanism vocabulary P003's constructs use", "read"),
 "Schema Mapping and Data Exchange Tools": (
  "schema-mapping tooling needs declarative semantics and modular deployment",
  "literature and the authors' own tools", "position/evolution paper over three 'ages' of exchange systems",
  "none", "a research agenda for mapping management", "no",
  "theory of mappings between declared schemas; P003's inputs frequently declare nothing", "read"),
 "Schema mapping discovery from data instances": (
  "infer a mapping from two database instances with unknown schemata",
  "synthetic/derived database instance pairs", "minimum-repair formalisation, complexity analysis",
  "formal optimality, decision-problem complexity", "a theoretical framework with complexity results",
  "no", "the strongest formal result in this set; assumes both instances exist and are comparable, whereas P003 "
  "measures how often the metadata needed to even attempt that is missing", "read"),
 "USING LINGUISTIC TECHNIQUES FOR SCHEMA MATCHING": (
  "syntactic/semantic similarity of element names drives matching quality",
  "SASMINT system over collaborative-network schemas", "NLP-based linguistic matching",
  "matching precision/recall", "linguistic techniques outperform limited similarity-metric baselines",
  "no", "matcher internals; P003 is about the availability of the inputs those internals need", "read"),
 "Where the Crosswalk Ends": (
  "spatial distribution of marked pedestrian crosswalks in San Francisco",
  "satellite imagery of San Francisco intersections", "manual image review to detect crosswalk markings",
  "share of intersections with marked crosswalks", "crosswalks present at 58% of roughly 31,000 intersections",
  "no",
  "NOT PRIOR WORK FOR THIS PAPER. Screen false positive: it matched P003's construct family on the word 'crosswalk', "
  "used here in the street-crossing sense. Retained and labelled rather than deleted so the screen's error rate is "
  "auditable.", "reject"),
 "raddec: Elevating IoT Interoperability": (
  "no common digital representation for radio decodings above the hardware layer",
  "RFID/BLE decoding streams", "an open-source common data structure plus middleware",
  "adoption in industry and research deployments", "a vendor- and technology-agnostic decoding representation",
  "yes (open-source library)", "proposes a format where none exists; P003 documents what happens in a domain where "
  "nobody has done that, i.e. heterogeneous self-declared releases", "read"),
}

P004 = {
 "Benchmarking Next-Generation Frontier Models for Document-Level Arabic-Thai": (
  "whether an LLM-as-a-judge jury is reliable enough to score low-resource medical translation",
  "OpenWHO Arabic/Thai medical documents (293), web-crawl shielded",
  "AI jury of three efficient reasoning models scoring fidelity, fluency, cultural appropriateness; 3,516 evaluations",
  "judge-model agreement/reliability against NMT baselines",
  "frontier models compared against Google Translate under a multi-judge reliability protocol",
  "no", "reliability of a judge the authors control and re-run; P004 studies scores already shipped with published "
  "artefacts, where the generating run cannot be re-executed, and asks whether the score tracks anything at all", "read"),
 "Effect of evaluation prompt strategies": (
  "does the evaluation prompt change LLM-judge scores and their concordance with clinical raters",
  "90 structured ICU reports from a prior XGBoost/MIMIC-IV study, GPT-4o as judge",
  "post-hoc comparison of evaluation prompt strategies against human clinical raters",
  "scoring patterns and concordance/agreement with expert raters",
  "prompt strategy shifts scoring patterns and expert concordance",
  "no", "reliability under controlled re-runs with a known configuration; P004's population has no configuration to "
  "vary and no experts to re-recruit", "read"),
 "Multimodal Quiz Generation via RAG": (
  "generate and evaluate pedagogically meaningful MCQs from lecture videos",
  "first lecture of an introductory CS course (15 MCQs)",
  "RAG generation (LLaVA + LLaMA 3.1) with a two-stage evaluation including an LLM judge",
  "two-stage evaluation scores of generated quizzes", "a working multimodal quiz generator with an LLM-judged rubric",
  "no", "uses a judge as one stage of its own pipeline; it does not test whether published automatic scores are valid "
  "measurements, which is P004's question", "read"),
 "Evaluating LLM-as-a-Judge for Medical Term Simplification": (
  "is LaaJ reliable and robust for specialised medical knowledge",
  "LLM-simplified medical terms with human expert annotations",
  "six LLMs judged under Vanilla, Epistemic and Bias setups against experts",
  "correctness, readability, completeness; agreement with experts under each setup",
  "judge reliability and robustness vary substantially across setups and models",
  "no", "one of the closest works: it also probes judge robustness against a human criterion. It still generates the "
  "scores under its own control; P004's target is scores a downstream reader cannot regenerate", "read"),
 "LLM Evaluations for Emotional Expressiveness and Factual Consistency": (
  "evaluate small open models on dialogue dimensions beyond factual correctness",
  "curated medical QnA dataset; Qwen and Gemma variants (2B-4B)",
  "G-Eval factual alignment plus DeepEval metrics for sentiment, tone, readability",
  "standardised tool-computed scores and their comparison across models",
  "small models are competitive on domain-specific dimensions under standardised scoring",
  "no", "adopts shipped metric tools (DeepEval/G-Eval) as the scoring instrument - the very class of artefact P004 "
  "audits - but does not test those scores' measurement properties", "read"),
 "LLM-as-a-Judge Approaches as Proxies for Mathematical Coherence": (
  "can LLM judges replace expensive embedding-based coherence metrics",
  "news articles on Cuban protests; scientific papers from visualisation conferences",
  "LLM judge scores compared against mathematical coherence metrics",
  "Pearson correlation with the objective metric (up to 0.65)",
  "LLM judgments correlate moderately with an independent coherence measure",
  "no", "criterion-validity logic (correlate a score with an independent criterion), which P004 also uses; the "
  "difference is direction - it validates a judge the authors built, P004 audits scores it did not", "read"),
 "Who Judges the Judge?": (
  "can LLMs judge semantic equivalence in French medical open-ended QA",
  "French medical OEQA answers from multiple generators",
  "closed-access, general-purpose and biomedical-adapted judges vs expert annotations; SFT/GRPO adaptation",
  "agreement with experts, stratified by answer generator",
  "judgments are strongly influenced by which model generated the answer; adaptation improves alignment",
  "no", "identifies generator-dependent judge bias, a mechanism adjacent to P004's instability findings; it measures "
  "judges, not third-party published scores, and has re-run access to every component", "read"),
 "An Empirical Study of LLM-as-a-Judge: How Design Choices": (
  "", "", "", "", "", "", "", "pending"),
 "The Impact of Likert Scale Design on Judgment Reliability": (
  "", "", "", "", "", "", "", "pending"),
}


def apply(path, table, unread_note):
    rows = list(csv.reader(io.StringIO(path.read_text(encoding="utf-8"))))
    hdr, body = rows[0], rows[1:]
    idx = {c: i for i, c in enumerate(hdr)}
    used = set()
    n_read = n_rej = 0

    def key_for(title):
        # \xa0 appears verbatim in some Crossref titles, so both sides are whitespace-normalised before comparing
        t = re.sub(r"\s+", " ", (title or "").replace("\xa0", " ")).lower().strip()
        cands = [k for k in table if t.startswith(re.sub(r"\s+", " ", k).lower().strip())]
        return max(cands, key=len) if cands else None

    for r in body:
        key = key_for(r[idx["title"]])
        if key is None:
            continue
        used.add(key)                      # matched at all, even if a previous run already adjudicated it
        if not r[idx["verify_status"]].startswith("pending_hand_check"):
            continue
        prob, ds, me, mt, mr, code, diff, verdict = table[key]
        if verdict == "pending":
            r[idx["verify_status"]] = "pending_hand_check (no abstract at any reachable source; title is on-topic)"
            r[idx["differentiation"]] = unread_note
            continue
        r[idx["problem"]] = prob
        r[idx["dataset_used"]] = ds
        r[idx["method"]] = me
        r[idx["metric"]] = mt
        r[idx["main_result"]] = mr
        r[idx["code_or_data_public"]] = code
        r[idx["differentiation"]] = diff
        if verdict == "reject":
            r[idx["verify_status"]] = "rejected_on_read (screen false positive; retained for audit)"
            n_rej += 1
        else:
            r[idx["verify_status"]] = "read_and_adjudicated"
            n_read += 1
    missing = [k for k in table if k not in used and table[k][7] != "pending"]
    if missing:
        raise SystemExit(f"[e70] ABORT: these read records were not found in {path.name}: {missing}")
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    w.writerow(hdr)
    w.writerows(body)
    path.write_text(buf.getvalue(), encoding="utf-8", newline="")
    print(f"[e70] {path.parent.name}/literature_matrix.csv: {n_read} newly adjudicated, {n_rej} rejected_on_read, "
          f"{len([k for k in table if table[k][7] == 'pending'])} still unread, "
          f"{len([k for k in used if table[k][7] != 'pending']) - n_read - n_rej} already done in a previous run")
    return n_read, n_rej


def main() -> int:
    p3 = PAP / "P003_metadata_interoperability" / "literature_matrix.csv"
    p4 = PAP / "P004_shipped_quality_score_validity" / "literature_matrix.csv"
    n3, r3 = apply(p3, P003, "")
    n4, r4 = apply(p4, P004, "title on-topic but no abstract at Crossref, arXiv or Semantic Scholar; not cited as "
                             "prior work until read")
    def annotate(path, text):
        cur = path.read_text(encoding="utf-8")
        if "EXP-0070" in cur:
            print(f"[e70] {path.parent.name}/{path.name} already annotated; left alone")
            return
        path.write_text(cur.rstrip() + text, encoding="utf-8", newline="")

    def counts(f):
        rr = list(csv.DictReader(io.StringIO(f.read_text(encoding="utf-8"))))
        return (sum(1 for x in rr if x["verify_status"] == "read_and_adjudicated"),
                sum(1 for x in rr if x["verify_status"].startswith("rejected_on_read")),
                sum(1 for x in rr if x["verify_status"].startswith("pending_hand_check")))

    # totals, not this-run deltas: a re-run adjudicates nothing new, and prose must not then claim zero records read
    c3 = counts(p3)
    c4 = counts(p4)
    n3, r3 = c3[0], c3[1]
    n4 = c4[0]
    annotate(PAP / "P003_metadata_interoperability" / "literature_background.md", f"""

## Hand read completed (EXP-0070)

All {n3 + r3} rows EXP-0067 appended were read. {n3} are genuine adjacent-domain prior work and now carry a written
differentiation; **{r3} is a screen false positive** - "Where the Crosswalk Ends" is a pedestrian-safety study of
marked crosswalks in San Francisco that matched P003's construct family on the word "crosswalk". It is relabelled
`rejected_on_read` and left in the matrix so the screen's measured precision, {n3}/{n3 + r3}, is auditable rather
than quietly corrected.

The read set also surfaced one structurally close neighbour that the earlier curated pass had missed: *Mapping the
Metadata Landscape of Energy Data Repositories* runs the same harvest-crosswalk-coverage census on ten energy
catalogues against an existing standard (OEMetadata v2) and reports weak, uneven coverage including licences absent in
half the portals. P003's differentiation from it is recorded in the matrix row: an agent-trajectory population with no
governing standard to crosswalk against, and a round-trip recoverability test in addition to declared-field coverage.
""")
    annotate(PAP / "P004_shipped_quality_score_validity" / "literature_background.md", f"""

## Hand read completed (EXP-0070)

{n4} of the {n4 + 2} anchored survivors were read and adjudicated, with {r4} rejected on reading; every read record is
an LLM-as-a-judge evaluation study, so the anchor's precision holds on the full read set and not only on the seed-11
sample. {2} remain `pending_hand_check` because no reachable source holds their abstract text - their titles are
on-topic, and they are therefore listed but **not** cited as prior work. Each adjudicated row now carries the shared
differentiator plus its own specifics: all {n4} generate and re-run their judges under a configuration they control,
whereas P004's object is scores already shipped with published artefacts, where neither the run nor the rubric can be
recovered.
""")
    print("[e70] both literature_background.md files annotated")

    # ---- the read also produced a novelty consequence for P003, and one for P004: name the closest work found
    NB3 = PAP / "P003_metadata_interoperability" / "novelty_audit.md"
    if "EXP-0070" not in NB3.read_text(encoding="utf-8"):
        NB3.write_text(NB3.read_text(encoding="utf-8").rstrip() + f"""

## Closest structural prior work found by the read pass (EXP-0067 + EXP-0070)

*Mapping the Metadata Landscape of Energy Data Repositories* (Open Conference Proceedings, 2026) does what this paper
does, on a different population: it harvests ten catalogues, crosswalks them onto an existing standard (OEMetadata v2),
and reports dataset- and column-level coverage, finding licences absent in half the portals and column-level data
dictionaries largely absent. That is the same census-plus-coverage design, so this paper can no longer be positioned as
"nobody measures metadata coverage in repositories".

What survives the comparison, and what the paper now claims instead:

1. **No governing standard to crosswalk against.** The energy study can score records against OEMetadata v2. The
   agent-trajectory releases P003 audits have no equivalent, so the crosswalk itself is an artefact this paper must
   build and defend, and its absence is a finding about the field rather than an inconvenience.
2. **Declared coverage is not recoverability.** P003 additionally tests round-trip recoverability - whether a
   conversion preserves what the record claimed - which a coverage census cannot see.
3. **Different failure modes.** Their weak fields are provenance/licence/column dictionaries; P003's headline failures
   are schema-absent, self-declared and unattributable structures across formats.

The read pass also measured the screen that produced this row: {n3 + r3} appended records were read, {r3} was a false
positive (a pedestrian-crosswalk study matched on the word "crosswalk"), so precision on the read set is
{n3}/{n3 + r3}. Both numbers are recorded in `literature_background.md`, and the rejected row is retained in the
matrix labelled `rejected_on_read` rather than deleted.
""", encoding="utf-8", newline="")
        print("[e70] P003 novelty_audit closest-prior-work section appended")

    alld = [int(x) for f in sorted((ROOT / "papers").glob("*/deviations.md"))
            for x in re.findall(r"(?m)^\| D(\d+) \|", f.read_text(encoding="utf-8"))]
    dn = max(alld or [0])
    DV3 = PAP / "P003_metadata_interoperability" / "deviations.md"
    SUBJ = "读后新增最近邻先前工作（能源仓储元数据普查）并收窄本文新颖性声明"
    dt3 = DV3.read_text(encoding="utf-8")
    if SUBJ not in dt3:
        DV3.write_text(dt3.rstrip() + f"""
| D{dn+1} | {NOW} | {SUBJ} | EXP-0067 追加的 20 行全部读毕（{n3} 真相关、{r3} 为筛选假阳性），其中 *Mapping the Metadata Landscape of Energy Data Repositories* 与本文同为「采集-交叉映射-覆盖率普查」设计 | 否 | novelty_audit 新增「最近结构相似先前工作」一节：本文不再声称「无人普查元数据覆盖率」，改以（无统一标准可依、声明覆盖≠可恢复性、失效模式不同）三点立足；被拒行保留并标注 rejected_on_read |""",
                       encoding="utf-8", newline="")
        print(f"[e70] P003 D{dn+1} appended")

    tot_read = tot_rej = tot_pend = 0
    for f in (p3, p4):
        rr = [x for x in csv.DictReader(io.StringIO(f.read_text(encoding="utf-8")))]
        tot_read += sum(1 for x in rr if x["verify_status"] == "read_and_adjudicated")
        tot_rej += sum(1 for x in rr if x["verify_status"].startswith("rejected_on_read"))
        tot_pend += sum(1 for x in rr if x["verify_status"].startswith("pending_hand_check"))
    print(f"[e70] totals across both matrices: {tot_read} adjudicated, {tot_rej} rejected_on_read, {tot_pend} pending")

    reg = REG / "experiment_registry.csv"
    rows = [r for r in csv.reader(io.StringIO(reg.read_text(encoding="utf-8"))) if r]
    if "EXP-0070" not in {r[0] for r in rows if r}:
        rows.append(["EXP-0070", "P003;P004", f"success_HAND_READ_{tot_read}_ADJUDICATED_{tot_rej}_SCREEN_FALSE_POSITIVE",
                     "02_shared_code/registry/fill_matrix_hand_reads_p003_p004.py",
                     "every row appended by EXP-0067/0068/0069 read in full and given problem/dataset/method/metric/"
                     "main_result/differentiation; the two records with no abstract at any reachable source left "
                     "pending_hand_check and excluded from citation; the screen's false positive relabelled "
                     "rejected_on_read and retained", "none (reading, not sampling)",
                     NOW, NOW, f"totals: {tot_read} adjudicated, {tot_rej} rejected_on_read, {tot_pend} still pending (P003 {n3}+{r3} this run, P004 {n4}+{r4} this run)",
                     "papers/P003_metadata_interoperability/literature_matrix.csv; "
                     "papers/P004_shipped_quality_score_validity/literature_matrix.csv",
                     "the directly-relevant tallies for P003 and P004 are now read-and-differentiated rather than "
                     "screen-generated, and the screen's measured precision is on record", "yes - both matrices"])
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\r\n")
        for r in rows:
            w.writerow(r)
        reg.write_text(buf.getvalue(), encoding="utf-8", newline="")
        print("[e70] registered EXP-0070")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
