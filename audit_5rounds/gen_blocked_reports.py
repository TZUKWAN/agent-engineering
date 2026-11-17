# -*- coding: utf-8 -*-
"""为 12 个 blocked 包生成中文状态报告 paper_cn.md（状态报告，非论文）。"""
import io, os

BASE = r"G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers"

REPORTS = {
"P013_negative_boundary_metadata": {
 "topic": "T112", "wave": "wave-2", "gate": "T112_negation_identifiable",
 "rq": "目录描述中的负向边界表述（「不支持 X」「仅限 Y」式）作为元数据构念，能否在候选目录上测量其流行度与效应？",
 "status": "w2_blocked_premise_negation_prevalence_0p029_below_gate_0p05",
 "fired": "冻结门要求否定标记可识别且流行（候选中占比 ≥0.05）；实测否定标记仅占候选的 0.029（2.9%）。",
 "measured": "boundary_specific_share=0.0009；negation_marker_share=0.029；parameter_enumeration_share=1.0；description_tokens 均值 25.3（p50=16）；centring 主导格 0.8901。",
 "verdict": "构念在语料中几乎不存在（2.9% < 5% 地板），任何效应检验都没有对照臂可支撑。实验未运行，阈值未下调。",
 "unblock": "需要含丰富负向约束描述的目录语料（负向表述占比 ≥5%），或把研究问题改为「负向表述为何稀缺」的元问题。",
},
"P017_noun_verb_centring": {
 "topic": "T117", "wave": "wave-2", "gate": "T117_centring_contrast",
 "rq": "目录描述的名词中心化 vs 动词中心化是否与检索行为差异相关（中心化对比设计）？",
 "status": "w2_blocked_premise_centring_dominance_0p890_above_gate_0p80_kappa_0p414",
 "fired": "冻结门要求中心化分布有足够对比（主导格份额 ≤0.80）且双规则编码一致；实测主导格 0.8901、双规则 kappa 仅 0.414。",
 "measured": "centring.mean=1.401、sd=14.769、dominant_bin_share=0.8901、rule_b_agreement_kappa=0.4142、三等分层各 56,401；verb_lexicon_coverage_mean=0.0666。",
 "verdict": "对比的一侧几乎不存在（89% 挤在同一格）且量尺本身编码不可靠（kappa<0.5），对比设计不可估。实验未运行，阈值未下调。",
 "unblock": "需要名词/动词中心化分布更均衡的目录，或先解决中心化编码的双规则信度（kappa≥0.6）后重新冻结。",
},
"P019_hierarchy_facets_flat_lists": {
 "topic": "T118", "wave": "wave-3", "gate": "T118_hierarchy_exists",
 "rq": "目录名称的层级结构（多段名）是否影响切面（facets）式检索行为？",
 "status": "blocked_premise_no_hierarchy_to_expose",
 "fired": "冻结门要求 ≥20% 的条目名称多于一段（存在层级可暴露）；实测仅 16.94%，中位段数 1.0。",
 "measured": "T118_hierarchy_exists=false；T118_median_name_segments=1.0；T118_share_of_entries_with_more_than_one_segment=0.1694。",
 "verdict": "目录几乎是纯平铺列表，没有层级可供暴露——设计被判 not estimable。实验未运行，阈值未下调。",
 "unblock": "需要名称带层级段（如「分类/子类/条目」）的目录语料，或把研究问题改为「平铺目录的检索代价」。",
},
"P048_when_to_stop_a_recorded_search": {
 "topic": "T175", "wave": "wave-8", "gate": "G5_terminal_turn_identifiable",
 "rq": "智能体何时停止搜索——停止回合的特征与提前/延迟停止的代价？",
 "status": "blocked_premise_terminal_turn_0p4649_below_0p95",
 "fired": "G5 冻结 ≥0.95 的轨迹以助手回合收尾（STOP 是可测事件）；实测 0.4649——6,835 条以助手回合结束、5,485 条以无人应答的观察结束、2,381 条以用户消息结束。",
 "measured": "G5=0.4649；G1 解析率 1.0；G4 有后续回合的轨迹 13,695；G11 簇 14,701；G12 类别 8。",
 "verdict": "过半轨迹中途截断，「停止」这个事件对多数轨迹不存在。实验未运行，阈值未下调，也不允许只对存活的 46% 重新定义结局。",
 "unblock": "需要停止原因被显式记录的语料（stop_reason 列），或把研究问题改到「截断与完成的双分布」上重新注册。",
},
"P049_premature_termination_and_over_search": {
 "topic": "T176", "wave": "wave-8", "gate": "G13_outcome_label_available + G5",
 "rq": "过早终止与过度搜索——搜索时长相对任务需求的错配及其代价？",
 "status": "blocked_premise_no_outcome_column_and_mid_exchange_53p5",
 "fired": "双门齐触发：G13 要求任务结局列（「过早/过度」的参照系）——发布集只有 id/conversations/tools/category/subcategory/task，无结局列（实测 0）；G5 实测 53.5% 轨迹中途结束（两臂定义的人群大半不存在）。",
 "measured": "G13=0；G5=0.4649；G7 错误观察 0.5893；G10 重复调用轨迹 4,125；G11 簇 14,701。",
 "verdict": "「过早」与「过度」都需要「恰好」作参照，而参照系（结局标签）不存在。实验未运行，行为定义未被改写以迁就幸存子集。",
 "unblock": "需要带任务结局标签的语料（人工评分或自动验证），并解决截断问题——两者分别是 P051 复算清单与本包的共同缺口。",
},
"P054_an_induced_taxonomy_of_agent_information_behaviour": {
 "topic": "T151", "wave": "wave-9", "gate": "G9_newness_available + G3",
 "rq": "对智能体信息行为做诱导式分类（taxonomy）——以新词份额与命令家族两大特征块聚类？",
 "status": "blocked_premise_newness_0p7876_below_0p90_and_families_11_below_12",
 "fired": "G9 冻结 ≥0.90 的步有可计算新词份额的观察；实测 0.7876（21% 的命令步后面没有观察——轨迹就停在那）；G3 分类地板要求 ≥12 个命令家族、实测 11。",
 "measured": "G9=0.7876；G3=11 家族；G1 解析率 0.9994；G11 簇 1,784。",
 "verdict": "特征块之一（新词）在两成步上无值，聚类将在混合层上进行——同一名词测两种量。实验未运行，缺失记为发布集属性（W9-D01）。",
 "unblock": "需要观察覆盖 ≥90% 的语料，或把分类的特征块改为不依赖逐步观察的量（如纯命令序列特征）。",
},
"P055_the_exploration_exploitation_transition": {
 "topic": "T156", "wave": "wave-9", "gate": "G9_newness_available",
 "rq": "探索-利用转换——新词份额曲线随步数的形状与转换点？",
 "status": "blocked_premise_newness_0p7876_below_0p90",
 "fired": "G9 对本设计为 design-scope（H1 的结局就是新词份额本身）：实测 0.7876 < 0.90。G7 的切换地板顺利通过（19,964 条 rollout 有 ≥2 次切换）。",
 "measured": "G9=0.7876；G7=19,964；G2 结局标签在位 1.0；G11 簇 1,784。",
 "verdict": "只报告幸存的一半（切换曲线）而保留原标题即是被禁止的重新规格化——设计整体停止，覆盖率照档。实验未运行。",
 "unblock": "同 P054：观察覆盖 ≥90% 的语料；或把切换曲线作为独立设计重新注册（换标题换冻结句）。",
},
"P057_three_kinds_of_linguistic_uncertainty": {
 "topic": "T102", "wave": "wave-10", "gate": "G2_comparable_candidate_sets",
 "rq": "三类语言不确定性（词汇歧义、指代、欠明确）对候选比较行为的影响？",
 "status": "blocked_premise_comparable_sets_0p8376_below_0p90",
 "fired": "G2 冻结 ≥0.90 的行提供 ≥2 个候选（一切结局都是候选集内比较）；实测 0.8376——5,137 条指令只匹配到单一候选。",
 "measured": "G2=0.8376；G3 词汇歧义 15,264 行；G4 指代 24,568 行；G5 欠明确 13,874 行——三个仪表全部充足。",
 "verdict": "失败在比较基底而非构念（W10-D01）：仪器充足、底座缺角。实验未运行，阈值未下调。",
 "unblock": "需要候选集 ≥2 的行占 ≥90% 的语料，或把结局改注册到单候选行可定义的量上。",
},
"P058_need_decomposition_and_search_completeness": {
 "topic": "T107", "wave": "wave-10", "gate": "G2_comparable_candidate_sets",
 "rq": "需求分解（子任务标记）与搜索完备性的关系？",
 "status": "blocked_premise_comparable_sets_0p8376_below_0p90",
 "fired": "G2 同样辖本设计（完备性分母是候选集）：实测 0.8376 < 0.90。G8 分解地板通过（11,288 行有 ≥2 子任务标记，地板 1,000）。",
 "measured": "G2=0.8376；G8=11,288；G9 结局列在位 1.0。",
 "verdict": "停摆源于基底的单候选六分之一，而非需求不可分解（W10-D01）。实验未运行。",
 "unblock": "同 P057；或把完备性分母改注册为非候选集量（如需求清单覆盖率）。",
},
"P059_linguistic_cues_and_source_reliability": {
 "topic": "T128", "wave": "wave-10", "gate": "G2_comparable_candidate_sets",
 "rq": "可信度语言线索（权威/证据标记）是否使候选被更优先选择？",
 "status": "blocked_premise_comparable_sets_0p8376_below_0p90",
 "fired": "设计自身的地板全部通过（权威语言 10.65%、证据标记 25.55%，均过 5% 地板；描述均值 13.17 内容词），但 G2 的比较集规则辖全设计：实测 0.8376 < 0.90。",
 "measured": "G2=0.8376；G7 证据语言 0.2555；G11 描述 13.17 内容词。",
 "verdict": "「优于一个可比候选」是选择语句——单候选行上无意义。实验未运行（W10-D01）。",
 "unblock": "同 P057/P058。本包的线索测量值（10.65%/25.55%）已可作为未来设计的功率输入。",
},
"P060_attribution_framing_and_credibility_bias": {
 "topic": "T129", "wave": "wave-10", "gate": "G2_comparable_candidate_sets",
 "rq": "同一内容在不同提供方（server）名下的框架差异是否引起可信度偏见？",
 "status": "blocked_premise_comparable_sets_0p8376_below_0p90",
 "fired": "G6 实测充足且有富余——1,845 个跨 server 的同内容词集（覆盖 3,940 个候选槽，地板 200）；但 G2 对本设计同为 design-scope：实测 0.8376 < 0.90。",
 "measured": "G2=0.8376；G6=1,845 对（3,940 槽）；G1 解析 1.0。",
 "verdict": "天然的同内容异源材料被记为已测结构（measured structure）而非可信度检验（W10-D01）。实验未运行。",
 "unblock": "G2 修复后本包是最接近解锁的——同内容异源对已实测存在（1,845 对），只差可比基底。",
},
"P061_task_language_ambiguity_and_search_shape": {
 "topic": "T154", "wave": "wave-10", "gate": "G2_comparable_candidate_sets",
 "rq": "任务语言的歧义程度与搜索形状（位置、深度）的关系？",
 "status": "blocked_premise_comparable_sets_0p8376_below_0p90",
 "fired": "G2 同辖本设计（H2 的量是候选集内的位置，六分之一的行没有集合可供定位）：实测 0.8376 < 0.90。",
 "measured": "G2=0.8376；G3 词汇歧义 15,264；G4 指代 24,568。",
 "verdict": "停摆，仪器测量值照档（W10-D01）。实验未运行。",
 "unblock": "同 P057。",
},
}

TPL = """# {title}——前提门封锁状态报告（中文版）

**包**：`{pkg}`　**主题**：{topic}　**数据波**：{wave}　**状态**：BLOCKED（前提门触发，未运行实验）

> 本文是状态报告，不是论文：该包的设计在前提门处被其自己的冻结句拦截，没有实验运行、没有效应估计、没有阈值下调。本文记录研究问题、触发的门、实测值与解锁条件，使封锁成为可核查、可解除的档案。

## 一、研究问题（冻结设计原文的意图）

{rq}

## 二、触发的门与实测值

**触发门**：{gate}

**实测**：{fired}

**前提普查关键值**：{measured}

## 三、处置与理由

{verdict}

封锁的纪律要点复述：没有在构念无法承载的语料上运行实验；没有在读数后下调任何阈值；协议冻结文件先于普查存在并作为"当初想做什么"的档案保留在本目录。封锁不是设计的失败——它阻止的是一次注定被无变异量尺或缺失基底吞没的分析，并让该构念的缺口第一次有了精确坐标。

## 四、解锁条件

{unblock}

## 五、与本系列的关联

本包的前提普查（同波 census 工件）同时为其他已运行包提供了前提数值。本包的封锁记录与系列全部封锁包共享同一格式：状态行、门名、实测 JSON、"未跑实验、未动阈值"声明。十二个封锁包的三类封锁原因——量尺无变异（本类构造性退化）、基底缺角（可比集/观察覆盖不足）、参照系缺失（结局标签/停止事件不存在）——在系列结构报告（P070 的构念矩阵）中均有空间定位。

## 六、复算与仲裁

本文全部数字来自目录内 BLOCKED.md 与其引用的 premise census 工件 JSON；BLOCKED.md 由记录脚本自动生成、声明不得手改；协议冻结文件的时间戳先于普查工件。对本文任何数字的怀疑可重跑 `reproduce.sh` 与对应 census 工件比对仲裁。
"""

count = 0
for pkg, info in REPORTS.items():
    d = os.path.join(BASE, pkg)
    title = pkg.split("_", 1)[1].replace("_", " ").title() if "_" in pkg else pkg
    md = TPL.format(pkg=pkg, title=title, **info)
    path = os.path.join(d, "paper_cn.md")
    io.open(path, "w", encoding="utf-8").write(md)
    count += 1
    print(pkg, "written")
print("total:", count)
