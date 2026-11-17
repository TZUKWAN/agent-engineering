"""Round-5 topic pool: the 44 topics in the attached list (编号 1-41, 46-48), registered on 2026-09-23.

The user supplied two batches on this date: 42 numbered ideas in the message body (registered as T101-T142 by
`topic_pool_round4.py`) and a 44-item list in the attachment, whose own numbering runs 1-41 and 46-48 - the file skips
42-45 and its group 六 heading is absent, so 44 is what is actually there, not 48. Both batches go through the same
funnel as T001-T037: registered at `w0_audit`, data feasibility measured against `01_datasets/manifests/*.audit.json`,
collision checked against the literature transports, and a status assigned by a rule written down before the run.

`nearest_in_programme` is recorded rather than decided here: several of these ideas are close to topics the series has
already packaged (the information-act taxonomy, the ISP stage lifecycle, plan-action alignment, the epistemic-behavioural
gap), and the fold/demote verdict belongs to the screen, not to the author of the row.

    python build_topic_registry.py
"""
from __future__ import annotations

# (id, title_zh, title_en, primary_dataset, method as supplied, nearest in this programme)
RAW = [
 ("T151", "LLM 智能体信息行为分类体系的计算发现",
  "An Empirically Induced Taxonomy of LLM-Agent Information Behaviour",
  "AgentTrove;hermes;AgentBank",
  "encode trajectories into information acts (NEED/PLAN/SEARCH/INSPECT/FILTER/COMPARE/VERIFY/REFORMULATE/INTEGRATE/"
  "STOP), then sequence clustering / HMM / process mining for stable structure",
  "P002's ISP stage codex and the programme's information-act taxonomy"),
 ("T152", "智能体信息搜寻生命周期的计算识别",
  "Computational Identification of the Agentic Information-Seeking Lifecycle",
  "AgentTrove;hermes",
  "test whether Task interpretation -> Exploration -> Focusing -> Verification -> Integration -> Termination really "
  "exists, with change-point detection, HMM, sequence embedding, process mining",
  "P002 (ISP stages: exploration/extraction/verify/documentation)"),
 ("T153", "智能体信息行为是否存在跨任务普遍语法",
  "Is There a Cross-Task Universal Grammar of Agentic Information Behaviour?",
  "AgentTrove;AgentBank;AgentInstruct",
  "mine whether motifs such as QUERY->INSPECT->REFORMULATE hold across coding, browser, database, KG, WebShop, OS, "
  "math environments", "T151, T152"),
 ("T154", "任务语言模糊性如何改变 Agent 的信息搜寻行为",
  "How Task-Language Ambiguity Changes Agentic Information Seeking",
  "Toucan-1.5M",
  "compute lexical ambiguity, referential ambiguity, constraint density, underspecification, entity density, "
  "instruction complexity; test whether they raise query count, tool switching, trajectory length, reformulation",
  "T001 (pragmatic form of instructions), T101 (underspecification)"),
 ("T155", "信息需求复杂度与搜寻深度是否匹配",
  "Does Search Depth Match Information-Need Complexity?",
  "Toucan-1.5M;hermes;AgentTrove",
  "build an Information Need Complexity Index and compare with trajectory depth; study over-search on simple tasks "
  "and premature stopping on complex ones (Search Effort Miscalibration)", "T103 (constraint density)"),
 ("T156", "智能体的探索—利用转换机制",
  "The Exploration-Exploitation Transition in Agentic Search",
  "SWE-ZERO-12M",
  "define an exploration ratio and locate its turning point from broad find/browse to focused inspect/edit/synthesis",
  "P002's stage-transition analysis"),
 ("T157", "信息气味能否预测 Agent 的下一步选择",
  "Can Information Scent Predict an Agent's Next Choice?",
  "Toucan-1.5M",
  "operationalise foraging scent as similarity(task, source/tool/observation); test selection against it and whether "
  "failed tracks chase low-scent sources", "T108/T109 (lexical vs semantic relevance)"),
 ("T158", "边际信息收益递减是否支配搜寻持续",
  "Diminishing Marginal Information Gain and the Persistence of Search",
  "Toucan-1.5M;SWE-ZERO-12M",
  "estimate information gain per acquisition step and find where further search adds no effective information",
  "T127 (evidence sufficiency), T155"),
 ("T159", "信息过载还是语义过载：工具数量与语义密度的区分效应",
  "Information Overload or Semantic Overload? Separating Tool Count from Tool Semantic Density",
  "Toucan-1.5M",
  "separate number of tools from SemanticCrowding = mean pairwise description similarity; test each against selection "
  "quality", "T002 (catalogue semantic crowding, folded into T037)"),
 ("T160", "工具选择熵作为决策不确定性指标",
  "Tool Choice Entropy as an Indicator of Decision Uncertainty",
  "Toucan-1.5M",
  "define choice entropy; model how tool count, tool similarity and task ambiguity move it, and entropy against "
  "wrong tool / extra calls / failure", "T10, T124 (linguistic uncertainty)"),
 ("T161", "语义诱饵效应：近义工具为何导致错误选择",
  "The Semantic Decoy Effect: Why Near-Synonym Tools Cause Misselection",
  "Toucan-1.5M",
  "measure semantic distance from the chosen wrong tool to the gold tool; test whether errors concentrate on the "
  "nearest neighbour", "T114 (prototype bias), T122 (discriminability)"),
 ("T162", "工具描述中的可供性语言如何影响选择",
  "Affordance Language in Tool Descriptions and Its Effect on Selection",
  "Toucan-1.5M",
  "code action verbs, object descriptions, conditions, parameter constraints and negative constraints in tool "
  "descriptions against selection", "T113 (function vs use-case framing), T112 (negation)"),
 ("T163", "工具描述粒度与信息辨识能力",
  "Description Granularity and Machine Discriminability",
  "Toucan-1.5M",
  "counterfactual rewriting of one tool description at five granularities (minimal / function / function+boundary / "
  "function+scenario / function+counter-example) with offline replay", "T116 (granularity), T121 (negative metadata)"),
 ("T164", "工具命名空间能否降低信息过载",
  "Does a Tool Namespace Reduce Information Overload?",
  "Toucan-1.5M",
  "compare a flat tool space with a server-prefixed hierarchical one; treat the namespace as a classification scheme",
  "T118 (hierarchy/facet/flat), T117 (noun vs verb organisation)"),
 ("T165", "MCP Server 是否已形成机器信息源生态",
  "Have MCP Servers Become a Machine Information-Source Ecosystem?",
  "Toucan-1.5M",
  "build a server-tool-task network over the catalogue and analyse centrality, functional clusters, source overlap, "
  "specialisation and redundancy", "T015-era MCP audit; P005's component structure"),
 ("T166", "无关信息污染对决策的影响",
  "How Irrelevant-Information Contamination Affects Agentic Decisions",
  "Toucan-1.5M",
  "use the release's own irrelevant subset as a natural treatment; test count, semantic distance and server origin of "
  "irrelevant tools against selection, path, calls and answer", "T002's distractor injection (E17)"),
 ("T167", "正确信息存在为何仍找不到",
  "Why Is the Right Information Still Missed When It Is Present?",
  "Toucan-1.5M",
  "condition on the gold tool being in the candidate list and decompose the failure into retrieval, semantic "
  "discrimination, planning and parameter failure (availability != accessibility)", "P001's routing-failure analysis"),
 ("T168", "工具切换成本与探索质量",
  "Tool Switching Cost and the Quality of Exploration",
  "Toucan-1.5M;hermes;AgentTrove",
  "define switching rate and look for an inverted-U between switching and success", "P002's switching dimension"),
 ("T169", "多工具任务中的工具依赖网络",
  "The Tool-Dependency Network in Multi-Tool Tasks",
  "Toucan-1.5M;AgentBank",
  "learn A->B dependencies from trajectories and separate necessary order, swappable, parallel and redundant; test "
  "whether successful tracks obey the hidden structure", "T130 (discourse grammar), T142"),
 ("T170", "第一行动的路径依赖",
  "Path Dependence of the First Action",
  "SWE-ZERO-12M",
  "within one PR's many rollouts, group by the first action (ls/grep/find/cat/git/edit) and measure subsequent "
  "trajectory divergence", "P002's transition analysis"),
 ("T171", "首因锁定：初始假设是否收缩后续信息选择",
  "Primacy Lock-In: Does an Initial Hypothesis Narrow Later Search?",
  "hermes;SWE-ZERO-12M",
  "extract the first hypothesis statement and test whether later information selection concentrates on it "
  "(confirmation-seeking, not a bias claim)", "T132 (evidence order), T134"),
 ("T172", "搜寻宽度与搜寻深度哪个更重要",
  "Breadth versus Depth in Agentic Search",
  "SWE-ZERO-12M",
  "Breadth = unique files/directories/tools inspected; Depth = repeated inspection; compare their relation to "
  "outcome by task type", "T155, P002's breadth/depth dimensions"),
 ("T173", "智能体的信息迷航行为",
  "Machine Information Wandering",
  "SWE-ZERO-12M;hermes",
  "define wandering via graph distance, low semantic relevance, high action entropy and no convergence; test what "
  "predicts it", "T158, T168"),
 ("T174", "重复搜寻与信息反刍",
  "Repetitive Search and Information Rumination",
  "SWE-ZERO-12M;AgentTrove",
  "detect repeated grep / re-read / near-identical query / identical tool call and separate necessary re-check from "
  "unproductive repetition", "T142 (semantic dedup of memory)"),
 ("T175", "信息搜寻何时应该停止",
  "When Should Agentic Search Stop?",
  "hermes;AgentTrove",
  "predict STOP vs CONTINUE from marginal information, evidence consistency, uncertainty, repetition and length",
  "T127 (sufficiency language)"),
 ("T176", "过早停止与过度搜寻的双重失配",
  "Premature Termination and Over-Search as a Double Mismatch",
  "hermes;AgentTrove",
  "identify the linguistic and behavioural antecedents of each failure mode separately", "T155, T175"),
 ("T177", "成功与失败轨迹的过程 motif",
  "Process Motifs of Successful and Failed Trajectories",
  "AgentTrove",
  "PrefixSpan / sequential pattern mining / process mining against the reward label", "T131 (discourse structure by "
  "outcome)"),
 ("T178", "只看前 20% 轨迹能否预测最终失败",
  "Can the First 20% of a Trajectory Predict Final Failure?",
  "AgentTrove",
  "train on early turns only; report which early information behaviours carry the diagnostic signal rather than the "
  "classifier itself", "P001's early-warning predictor"),
 ("T179", "智能体什么时候还能被救回来",
  "The Recovery Window: How Late Can an Agent Still Be Saved?",
  "SWE-ZERO-12M;AgentTrove",
  "measure correction success by the step at which the error entered, defining a recovery window", "T133 (repair)"),
 ("T180", "错误级联：早期错误如何污染后续信息行为",
  "Information Error Cascades",
  "SWE-ZERO-12M;hermes",
  "trace wrong assumption -> wrong source -> wrong evidence -> reinforced hypothesis -> wrong action", "T134, T135"),
 ("T181", "语言计划与信息行动的一致性",
  "Do Agents Do What They Said? Plan-Action Alignment",
  "hermes",
  "extract intended actions from the reasoning text and align them with the actual tool calls (PlanActionAlignment)",
  "T136 (identical construct), T031-era work"),
 ("T182", "计划具体性是否改善搜寻质量",
  "Does Plan Specificity Improve Search Quality?",
  "hermes;AgentTrove",
  "score plan specificity by entity count, action count, ordering and constraints, and relate it to trajectory "
  "quality", "T136, T181"),
 ("T183", "信息需求在推理中的重新表述",
  "How the Information Need Is Reformulated Inside Reasoning",
  "hermes",
  "track initial task -> intermediate subquestion -> search query -> revised hypothesis (need evolution, not rewrite "
  "optimisation)", "T105 (multi-turn evolution), T106"),
 ("T184", "自然语言行动与代码行动的信息表达效率",
  "Information Density of Natural-Language versus Code Actions",
  "code-act;hermes",
  "compare natural-language actions, structured tool calls and executable code actions on information density, "
  "correctability, composition and trajectory length", "T014-era CodeAct audit"),
 ("T185", "表达不确定之后是否真的继续查证",
  "Does Expressed Uncertainty Lead to Actual Checking?",
  "hermes",
  "extract epistemic markers (maybe/probably/unclear/need to check/not sure) and test the marker -> verification link",
  "T123, T124 (same construct)"),
 ("T186", "不确定性语言随信息获取的动态变化",
  "The Dynamics of Linguistic Uncertainty as Evidence Arrives",
  "hermes;SWE-ZERO-12M",
  "estimate U_1..U_T per turn; test drops after tool results, rises after errors, and re-rises on conflicting "
  "evidence", "T125, T126"),
 ("T187", "什么信息触发验证行为",
  "What Kind of Information Triggers Verification?",
  "hermes",
  "compare error, empty result, unexpected result, contradiction, low semantic fit and partial answer as triggers",
  "T126, T123"),
 ("T188", "证据不足感的形成",
  "How a Sense of Insufficient Evidence Forms",
  "hermes;AgentTrove",
  "detect 'not enough' / 'need additional evidence' / 'can't conclude' and compare with objective source count, tool "
  "results and evidence coverage", "T127 (same construct)"),
 ("T189", "Reflection 是纠正还是仪式",
  "Corrective versus Ritual Reflection",
  "MMAT-1M",
  "compare reasoning, answer, tool use and source choice before and after each explicit reflection", "T133, T124"),
 ("T190", "语言纠错与行为纠错是否一致",
  "Verbal Correction versus Behavioural Correction",
  "hermes",
  "find 'I made a mistake' statements and test whether the following action actually differs", "T136, T181"),
 ("T191", "信息验证深度的最优区间",
  "Is There an Optimal Depth of Verification?",
  "Toucan-1.5M;hermes",
  "relate verification count to quality and cost and estimate a quality-verification-cost frontier", "T158, T175"),
 ("T192", "从大规模轨迹自动发现工作流程知识",
  "Discovering Workflow Knowledge from Large Trajectory Corpora",
  "SWE-ZERO-12M;AgentTrove",
  "cluster trajectories into Task -> workflow patterns and build an agent procedural knowledge base", "T137"),
 ("T193", "哪些轨迹值得沉淀为组织知识",
  "Which Trajectories Deserve to Become Organisational Knowledge?",
  "AgentTrove;SWE-ZERO-12M",
  "construct a Knowledge Reusability Score from success, efficiency, generality, novelty, coverage and redundancy",
  "T137, T140"),
 ("T194", "历史轨迹的案例化知识重用",
  "Case-Based Reuse of Historical Trajectories",
  "SWE-ZERO-12M;AgentTrove",
  "build a trajectory case base and compare no-memory, raw-trajectory retrieval and abstract-workflow retrieval on "
  "success, tool calls, tokens and search redundancy", "T141 (representation formats)"),
]

COLUMNS = ["topic_id", "title_zh", "title_en", "paper_type", "primary_dataset",
           "external_validation_dataset", "theory_basis", "core_rq_h", "primary_dv", "primary_iv",
           "main_method", "novelty_risk", "data_feasibility", "compute_cost", "expected_venue",
           "status", "blocking_issue", "differentiation_from_other_topics"]


def rows():
    out = []
    for tid, zh, en, ds, method, near in RAW:
        primary = ds.split(";")[0].strip()
        out.append(dict(
            topic_id=tid, title_zh=zh, title_en=en,
            paper_type="C_new_metric" if "index" in method.lower() or "score" in method.lower()
                       else ("D_system" if tid in ("T194", "T165") else "A_mechanism"),
            primary_dataset=primary,
            external_validation_dataset="; ".join(x.strip() for x in ds.split(";")[1:]) or "pending_funnel_screen",
            theory_basis="see the supplied design; the screen records the collision result before the theory is frozen",
            core_rq_h="pending - fixed in the protocol freeze before any local row is read",
            primary_dv="", primary_iv="",
            main_method=method,
            novelty_risk="pending_lit_audit",
            data_feasibility="pending_funnel_screen",
            compute_cost="low_cpu_offline_replay",
            expected_venue="IP&M / JASIST / CHIIR / ACL-CBR / TOIS (per group)",
            status="w0_audit", blocking_issue="",
            differentiation_from_other_topics=f"nearest already in this programme: {near}"))
    return out
