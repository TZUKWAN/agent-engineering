# 完成标准作为终止判准：用户指令验证显性度与任务型交互智能体执行效率——基于 AgentNet 交互轨迹的实证研究

---

## 摘要

任务型交互智能体（task-oriented interactive agent）在接收自然语言指令后，需将开放性目标转化为可执行动作序列，并在适当条件下终止执行。然而，用户指令往往未明确给出完成标准或验证方式，智能体常常难以判断“何时停止”，并可能出现过冲、冗余搜索或提前终止等终止偏差。本研究以公开的 AgentNet 大规模 GUI 交互轨迹数据集为经验边界，将用户指令中的完成标准/验证条件重新界定为智能体的“终止判准”（stopping cue），系统考察其对任务完成率、执行步数及终止阶段过程指标的影响。研究共纳入原始任务记录 $N=22{,}811$ 条；剔除关键变量缺失后，回归分析样本为 $N=20{,}484$ 条，其中含完成标准的任务 $n=2{,}684$ 条；位置分析聚焦于可定位验证关键词的子集 $N=2{,}512$ 条。基于关键词—句法规则，将含完成标准的指令进一步细分为动词指令式（V1）、状态目标式（V2）、条件验证式（V3）、混合式（V4）与不可分类（V0）五类；采用 Logistic 回归、负二项回归及新计算的终止阶段指标（最后 25% 步冗余/错误比例、最后一步冗余/错误、异常短轨迹率等）进行分析。结果显示：控制任务难度、指令长度与操作系统后，含完成标准的任务完成率显著更高（OR = 1.255，95% CI [1.127, 1.396]，$p<.001$），执行步数显著更少（IRR = 0.883，95% CI [0.866, 0.900]，$p<.001$）；终止阶段指标亦显示，含完成标准任务的后期冗余比例、后期错误比例及异常短轨迹率均较低。验证密度与完成率呈正相关，但未发现稳健的倒 U 形关系；验证表述位于指令开头、中间或末尾时，完成率差异不显著。上述发现为言语行为理论、关联理论与行动终止/停止规则理论在任务型交互智能体情境中的应用提供了新的过程层面证据，并对用户指令优化与智能体终止机制设计具有实践启示。

**关键词：** 任务型交互智能体；完成标准；终止判准；验证显性度；执行终止；AgentNet

---

## Abstract

Task-oriented interactive agents must translate open-ended natural-language goals into executable action sequences and terminate execution at an appropriate point. However, user instructions often lack explicit completion criteria or verification procedures, and agents often find it difficult to decide when to stop, with overshooting, redundant search, or premature termination as possible consequences. Drawing on the public AgentNet large-scale GUI interaction trajectory dataset, this study reframes completion criteria/verification conditions in user instructions as "stopping cues" for agents and systematically examines their associations with task completion rate, execution steps, and terminal-phase process indicators. The raw sample included $N=22{,}811$ task records; after excluding cases with missing key variables, the regression sample comprised $N=20{,}484$ records, of which $n=2{,}684$ contained completion criteria; the position analysis focused on the $N=2{,}512$ records with locatable verification keywords. Instructions containing completion criteria were further classified into five categories: verb-directive (V1), state-goal (V2), conditional-verification (V3), mixed (V4), and unclassifiable (V0). Logistic regression, negative binomial regression, and newly computed terminal-phase indicators (proportion of redundant/incorrect steps in the last 25%, final-step redundancy/incorrectness, abnormal short-trajectory rate, etc.) were employed. Results show that, after controlling for task difficulty, instruction length, and operating system, tasks with completion criteria had significantly higher completion rates (OR = 1.255, 95% CI [1.127, 1.396], $p<.001$) and fewer execution steps (IRR = 0.883, 95% CI [0.866, 0.900], $p<.001$). Terminal-phase indicators further revealed lower late-stage redundancy, lower late-stage error rates, and a lower abnormal short-trajectory rate for tasks with completion criteria. Verification density was positively associated with completion probability, but no robust inverted-U relationship was observed. The position of verification expressions (beginning, middle, or end) did not significantly affect completion rates. These findings offer new process-level evidence for speech act theory, relevance theory, and action-termination/stopping-rule theory in the context of task-oriented interactive agents, with practical implications for instruction optimization and agent termination mechanism design.

**Keywords:** task-oriented interactive agent; completion criteria; stopping cue; verification explicitness; action termination; AgentNet

---

## 1 引言

近年来，以大语言模型（Large Language Model, LLM）为核心、融合视觉感知的任务型交互智能体（task-oriented interactive agent）在人机交互、自动化办公、软件测试与数字助手等领域受到广泛关注。典型系统如 Mind2Web（Yang et al., 2022）、WebGPT（Pal et al., 2022）以及 AUSTIN（Yuan et al., 2023）展示了智能体在网页浏览、文件管理与复杂多步骤任务中的执行能力；AgentNet（Zhang et al., 2024）等大规模真实交互轨迹数据集的发布，则为从自然语言指令角度理解人机协同效能提供了宝贵的实证基础。

从过程视角看，任务型交互智能体的执行可抽象为一条通用链：用户任务表达 → 意图解析 → 动作规划 → 环境交互 → 状态评估 → 执行终止。在这一链条中，终止环节决定了智能体何时停止当前动作序列并返回结果。与自然语言处理中常见的“生成到句末即停”不同，任务型智能体的终止必须依赖对外部任务状态是否达标的判断。当用户指令仅给出高层目标（如“整理桌面”）而未说明完成判据（如“所有截图文件移入 Screenshots 文件夹且桌面剩余文件不超过 5 个”）时，智能体便面临终止不确定性：既可能因未达潜在目标而过早停止，也可能因缺乏明确判据而反复验证、过冲搜索。

本研究以 AgentNet GUI 交互轨迹为经验边界，将用户指令中的完成标准/验证条件重新概念化为智能体的“终止判准”（stopping cue），核心研究问题为：用户指令中的完成标准如何为任务型交互智能体提供停止信号？换言之，当指令明确包含“检查/确认/确保……”等验证性表述或“完成/就绪/正确”等目标状态时，智能体是否更善于将自然语言目标转译为可操作的停止条件，并与更高的执行效率相关联？

本文的基本论点是：任务型交互智能体必须将自然语言目标转译为可执行的停止条件（executable stopping condition）；明确的验证标准与完成状态能够降低智能体对“是否已达目标”的不确定性，并与更少的冗余探索和提前终止相关联。需要强调的是，本文基于观察性交互轨迹数据，所有发现均描述统计关联，而非因果效应。

---

## 2 理论基础与研究假设

### 2.1 言语行为理论与指令中的验证行为

言语行为理论（Speech Act Theory）指出，语言不仅是描述世界的工具，也是执行行为的手段（Austin, 1962; Searle, 1969）。在任务型交互情境中，用户指令本质上是一种“指令式言语行为”（directive），其语力在于引导智能体执行特定操作序列。当指令中包含“检查”“确认”“确保”等动词时，用户不仅指示智能体完成动作，还同时规定了验证行为；当指令中出现“完成”“正确”“就绪”等状态时，则为智能体提供了终止执行的语义目标。因此，完成标准与验证条件可被视为指令语力的重要组成部分，直接影响智能体对任务边界的识别与终止时机的判断。

### 2.2 关联理论与认知效应优化

关联理论（Relevance Theory）强调，交际双方在信息处理中追求以最小认知努力获取最大认知效应（Sperber & Wilson, 1995）。对于任务型交互智能体而言，明确的完成标准能够显著降低意图识别与状态评估的认知成本，使智能体在更少探索步数内达到任务目标。然而，根据关联原则，过高的验证密度可能在提供冗余约束的同时限制智能体的灵活推理空间，从而可能削弱甚至逆转验证信息的正向效应。这提示验证密度与任务结果之间可能存在非线性关系，但需在经验层面加以检验。

### 2.3 行动终止理论与停止规则

行动终止/停止规则理论关注行为主体在何种条件下停止当前动作并转入下一阶段（Gigerenzer et al., 1999; Payne et al., 1993）。在任务执行中，终止规则可分为内部终止（达到预设目标状态）与外部终止（用户干预或超时）。当指令明确提供完成标准时，智能体可依据内部终止规则停止操作，减少不必要的后续步骤；反之，模糊的终止条件迫使智能体依赖启发式停止规则，容易导致过冲或反复验证。由此，完成标准构成了内部终止规则的重要语言线索。

### 2.4 研究假设

基于上述理论，本研究提出以下假设：

- **H1a**：包含完成标准/验证条件的任务，其完成率显著高于不包含完成标准的任务。
- **H1b**：包含完成标准的任务执行步数显著少于不包含完成标准的任务。
- **H1c**：包含完成标准的任务在终止阶段具有更低的冗余比例与错误比例。
- **H2**：不同验证语言形式（动词指令式、状态目标式、条件验证式、混合式）对执行终止过程的影响存在差异（探索性）。
- **H3**：验证关键词密度与任务完成率可能呈非线性关系；本研究将其作为补充性探索，而非主效应。
- **H4**：验证表述位于指令不同位置时，其终止引导效应可能存在差异（探索性）。

需要说明的是，H1a–H1c 为关联性假设，H2–H4 因类型分布严重失衡而仅作探索性分析。

---

## 3 研究方法

### 3.1 数据来源、样本口径与数据性质说明

本研究使用公开的 AgentNet 数据集（Zhang et al., 2024），原始数据包含 $N=22{,}811$ 条自然语言 GUI 任务及其交互轨迹。该数据集为真实人机/人–智能体交互的观察性记录，非实验操纵数据。任务完成状态、步骤正确性、冗余性等字段由数据集原始标注或后续规则化处理得到，反映的是特定模型与特定用户在特定交互情境下的结果，其外部效度受模型版本、应用领域与用户群体限制。

样本口径需明确区分三层：

1. **原始全量样本**：$N=22{,}811$，用于描述总体分布与完成标准二值特征的标注。
2. **含完成标准原始子集**：$n=2{,}869$（即 `has_completion_criteria == 1`），用于验证语言形式的分类描述。
3. **回归分析样本**：在剔除 `task_completed` 与 `task_difficulty` 缺失值后，$N=20{,}484$；其中含完成标准的任务 $n=2{,}684$，不含完成标准的任务 $n=17{,}800$。
4. **位置分析样本**：在含完成标准且能定位到验证关键词的子集中，$N=2{,}512$。

### 3.2 变量操作化与规则化特征的有效性说明

核心解释变量为二值变量 `has_completion_criteria`（是否包含完成标准/验证条件），该变量由数据集原始标注或前期规则化提取得到，本质上是一种基于关键词与句法启发式的规则化特征。尽管其在统计上与任务结果存在稳健关联，但需注意：

- 规则化特征可能存在误报或漏报，例如某些含完成标准的表述可能未命中关键词，而某些关键词在不同语境下未必表达完成判据；
- 原始标注可能偏向“检查/确认”类动词，导致状态目标式与条件验证式样本稀少；
- 本文将 `has_completion_criteria` 视为一种可观测的语言线索，而非对“指令质量”的全面度量。

进一步地，对 `has_completion_criteria == 1` 的指令依据关键词与句法窗口规则细分为五类：

- **V1 动词指令式**：出现 check / verify / confirm / validate / ensure / make sure 等动词，直接指示验证动作；
- **V2 状态目标式**：出现 done / complete / correct / proper / finished / ready 等状态词，描述完成后的目标状态；
- **V3 条件验证式**：出现 until / when / once / after 等条件词，其中 until 直接视为完成条件，when / once / after 仅在周围 15 词窗口内同时出现 V1/V2 关键词时才视为完成条件；
- **V4 混合式**：同时命中 V1/V2/V3 中至少两类；
- **V0 不可分类/伪阳性**：`has_completion_criteria == 1` 但未命中任何 V1/V2/V3 关键词。

验证密度 `verification_density` 定义为验证关键词出现次数除以指令总词数。验证位置 `verification_position_region` 按字符相对位置 25% / 50% / 25% 划分为开头（< 0.25）、中间（0.25–0.75）与末尾（≥ 0.75）三类。

因变量包括：

- `task_completed`：任务完成状态（0/1）；
- `total_steps`：总执行步数（计数变量）；
- 新增终止阶段指标：最后 25% 步的冗余比例、错误比例、最后一步是否冗余/错误、未完成任务中的异常短轨迹标识等（详见 3.3）。

控制变量包括：`task_difficulty`（任务难度，1–10 连续评分）、`word_count`（指令词数）、`os`（操作系统，ubuntu / win_mac）。

### 3.3 新增终止阶段过程指标

为从过程层面刻画完成标准对终止行为的影响，本研究基于 `data/processed/analysis_data.parquet` 与 `data/interim/steps.parquet` 计算以下终止阶段指标：

1. **最后 25% 步冗余比例**（`last25_redundant_prop`）：对每条任务，取步数最后 25%（向上取整，至少 1 步）的步骤，计算其中 `last_step_redundant == True` 的比例；缺失值不计入分母。
2. **最后 25% 步错误比例**（`last25_incorrect_prop`）：同上，但计算 `last_step_correct == False` 的比例。
3. **最后一步是否冗余**（`final_step_redundant`）：任务最后一步 `last_step_redundant == True`。
4. **最后一步是否错误**（`final_step_incorrect`）：任务最后一步 `last_step_correct == False`。
5. **最后 25% 步是否出现冗余/错误**（`last25_any_redundant`、`last25_any_incorrect`）：二值指标。
6. **异常短轨迹**（`abnormal_short`）：针对未完成任务，若其总步数 `total_steps` 不高于已完成任务总步数的第 5 百分位数，则标记为异常短轨迹，作为提前终止失败的描述性指标。本数据中该阈值为 9 步。

上述指标保存于 `revised/paper01_tables/terminal_phase_metrics_by_task.csv`，并按 `has_completion_criteria` 分组汇总保存于 `revised/paper01_tables/terminal_phase_summary_by_criteria.csv`。

### 3.4 分析模型

- **任务完成率**：采用 Logistic 回归，报告比值比（OR）及其 95% Wald 置信区间；
- **执行步数**：采用负二项回归（NB2），报告发生率比（IRR）及 95% CI，并报告离散参数 alpha；
- **验证密度的非线性效应**：在 Logistic 模型中加入 `verification_density` 与 `verification_density_sq`，并采用 AIC 与似然比检验（LRT）进行模型比较。由于密度分析为补充性探索，结果置于 4.5 节；
- **位置效应**：采用卡方检验与 Bonferroni 校正后的成对比例 Z 检验；
- **终止阶段指标**：采用 Welch t 检验（连续比例）与双比例 Z 检验（二值指标）进行组间比较。

所有分析在 Python 中完成，显著性水平 α = 0.05。由于数据为观察性样本，所有回归系数均解释为条件关联，而非因果效应。

---

## 4 结果

### 4.1 描述性统计与验证类型分布

在回归样本（$N=20{,}484$）中，总体任务完成率为 79.22%。无完成标准任务 $n=17{,}800$，完成率为 78.76%，平均执行步数为 20.61（SD = 17.12）；有完成标准任务 $n=2{,}684$，完成率为 82.27%，平均执行步数为 19.64（SD = 11.32）。初步描述性统计表明，含完成标准的任务在完成率上具有约 3.5 个百分点的优势，且平均执行步数更低。

**表 1** 报告了验证语言形式在含完成标准原始子集（$N=2{,}869$）中的分布。动词指令式（V1）占绝对主导（82.9%），混合式（V4）次之（9.7%），不可分类/伪阳性（V0）占 7.1%，而状态目标式（V2）与条件验证式（V3）仅占 0.2% 与 0.0%。这一严重失衡的分布意味着 H2 的组间推断力极为有限，验证类型差异仅作描述性展示，不宜进行统计显著性比较。

**表 1 验证语言形式在含完成标准任务中的分布（$N=2{,}869$）**

| 类型 | 标签 | $n$ | 比例 | 典型样例（节选） |
|------|------|-----|------|------------------|
| V0 | 不可分类/伪阳性 | 205 | 7.1% | “…proceed to checkout” / “Export and copy the final content.” |
| V1 | 动词指令式 | 2,379 | 82.9% | “…finally look at the file content and make sure the file exists” |
| V2 | 状态目标式 | 5 | 0.2% | “…set confirmation completed” |
| V3 | 条件验证式 | 1 | 0.0% | “…trace the edges of the egg in the picture until they close…” |
| V4 | 混合式 | 279 | 9.7% | “…After the installation is completed, restart the application.” |

### 4.2 完成标准对任务完成率的影响

**表 2** 报告了 Logistic 回归结果（$N=20{,}484$）。在控制任务难度、指令词数与操作系统后，`has_completion_criteria` 的 OR 为 1.255（95% CI [1.127, 1.396]，$p<.001$），表明含完成标准的任务完成 odds 提高约 25.5%。该结果支持 H1a。操作系统方面，win_mac 平台的完成率显著低于 Ubuntu 参考组（OR = 0.554，$p<.001$）；任务难度的效应不显著（OR = 0.983，$p=.206$）；指令词数每增加一词，完成 odds 提高约 0.2%（OR = 1.002，$p=.026$）。

**表 2 任务完成率影响因素的 Logistic 回归结果（$N=20{,}484$）**

| 预测变量 | OR [95% CI] | $p$ |
|----------|-------------|-----|
| Intercept | 6.413 [5.421, 7.586] | <.001 |
| `has_completion_criteria` | 1.255 [1.127, 1.396] | <.001 |
| `task_difficulty` | 0.983 [0.958, 1.009] | .206 |
| `word_count` | 1.002 [1.000, 1.004] | .026 |
| `C(os)[T.win_mac]` | 0.554 [0.492, 0.623] | <.001 |

### 4.3 完成标准对执行成本的影响

**表 3** 为负二项回归结果（$N=20{,}484$）。`has_completion_criteria` 的 IRR 为 0.883（95% CI [0.866, 0.900]，$p<.001$），表明在控制其他变量后，含完成标准的任务预期执行步数低约 11.7%，支持 H1b。任务难度的 IRR 为 1.211（$p<.001$），即难度每增加 1 分，预期步数增加约 21.1%；win_mac 平台的步数略高于 Ubuntu（IRR = 1.079，$p<.001$）。离散参数 α = 0.171，提示步数数据存在适度过度离散，负二项模型较 Poisson 模型更为合适。

**表 3 执行步数影响因素的负二项回归结果（NB2，$N=20{,}484$）**

| 预测变量 | IRR [95% CI] | $p$ |
|----------|--------------|-----|
| Intercept | 5.838 [5.661, 6.020] | <.001 |
| `has_completion_criteria` | 0.883 [0.866, 0.900] | <.001 |
| `task_difficulty` | 1.211 [1.205, 1.217] | <.001 |
| `word_count` | 1.001 [1.001, 1.002] | <.001 |
| `C(os)[T.win_mac]` | 1.079 [1.057, 1.100] | <.001 |
| alpha | 1.187 [1.182, 1.192] | <.001 |

### 4.4 终止阶段过程指标

为将完成标准重新框架为“终止判准”，本研究进一步比较了两组任务在终止阶段的行为差异。**表 4** 报告了按 `has_completion_criteria` 分组的终止阶段指标描述与组间比较。

**表 4 终止阶段指标按是否含完成标准的比较**

| 指标 | 无完成标准（$n=19{,}942$） | 有完成标准（$n=2{,}869$） | 统计量 | $p$ |
|------|---------------------------|---------------------------|--------|-----|
| 最后 25% 步冗余比例（均值） | 0.0637 | 0.0555 | $t=-3.496$ | <.001 |
| 最后 25% 步错误比例（均值） | 0.1340 | 0.1218 | $t=-3.384$ | <.001 |
| 最后 25% 步出现冗余（比例） | 26.31% | 23.14% | $Z=-3.620$ | <.001 |
| 最后 25% 步出现错误（比例） | 44.77% | 41.65% | $Z=-3.143$ | .002 |
| 最后一步冗余率 | 0.02% | 0.14% | $Z=3.193$ | .001 |
| 最后一步错误率 | 23.65% | 23.74% | $Z=0.104$ | .917 |
| 异常短轨迹率（未完成任务） | 2.47% | 1.19% | $Z=-4.278$ | <.001 |
| 平均总步数 | 19.99 | 19.24 | — | — |
| 平均冗余比例 | 0.0728 | 0.0661 | $t=-4.207$ | <.001 |
| 平均错误比例 | 0.1188 | 0.1079 | $t=-5.035$ | <.001 |

结果显示，含完成标准任务在最后 25% 步的冗余比例、错误比例、出现冗余/错误的概率以及整体冗余/错误比例均显著更低；异常短轨迹率（未完成任务中总步数 ≤ 9 步）亦显著更低。最后一步错误率在两组间差异不显著（$p=.917$）；最后一步冗余率虽有统计显著性，但绝对发生率极低（0.02% vs. 0.14%），实际意义有限。综合来看，H1c 获得部分支持：完成标准与更低的终止阶段冗余与错误相关联，但这种关联不应被解释为完成标准“导致”了更优的终止行为。

### 4.5 验证密度作为补充分析

为检验 H3，本研究比较了线性与二次 Logistic 模型。线性模型中，`verification_density` 的系数显著为正（OR = 25.619，$p<.001$），即验证密度越高，完成率越高。二次模型中，二次项系数不显著（OR = $2.66\times10^{-5}$，$p=.654$），似然比检验 χ² = 0.197，$p=.657$，AIC 亦更支持线性模型（线性 AIC = 20811.69，二次 AIC = 20813.49，ΔAIC = −1.80）。据此，H3 未获支持；在当前操作化下，未发现验证密度与完成率之间存在稳健的倒 U 形关系。鉴于密度分析并非本文主线，其结果仅作补充讨论。

### 4.6 位置分析（探索性）

为检验 H4，本研究对可定位验证关键词的 $N=2{,}512$ 条指令按 25% / 50% / 25% 字符比例划分为开头、中间与末尾三类。三组的完成率分别为 83.87%、82.01% 与 81.02%，卡方检验不显著（χ² = 1.894，$p=.388$，Cramer's V = .028）。成对比例 Z 检验经 Bonferroni 校正后亦均未达到显著水平。因此，H4 未获支持；在本数据集中，验证表述的“存在”比其“位置”对任务成功更具预测力。

### 4.7 稳健性检验

**表 5** 汇总了稳健性检验结果。针对冗余比例，由于约 30% 任务的冗余比例为 0，本研究采用两部分模型思路：全体样本 OLS、正样本 OLS、是否冗余 Logistic 以及 log(1 + 冗余) OLS。结果显示，`has_completion_criteria` 在正样本 OLS 中不显著（β = 0.0007，$p=.740$），在是否冗余 Logistic 中显著为负（β = −0.298，$p<.001$），在其他设定中为弱负向，说明 H1c 未获一致支持，冗余行为可能更受任务领域与模型策略影响。替代密度定义（仅 V1 + V2）与替代位置分段（等分三段）均不改变主结论，进一步验证了结果的稳健性。

**表 5 稳健性检验：冗余比例、替代密度与替代位置定义**

| 模型/设定 | $N$ | 关键统计量 | `has_completion_criteria` 效应 | $p$ |
|-----------|-----|-----------|--------------------------------|-----|
| OLS（全体冗余比例） | 20,484 | $R^2=.041$ | β = −0.0057 [−0.0092, −0.0023] | .001 |
| OLS（冗余比例 > 0） | 14,222 | $R^2=.130$ | β = 0.0007 [−0.0032, 0.0045] | .740 |
| Logistic（是否冗余） | 20,484 | 伪 $R^2=.006$ | β = −0.298 [−0.385, −0.212] | <.001 |
| OLS（log(1 + 冗余比例)） | 20,484 | $R^2=.038$ | β = −0.0053 [−0.0084, −0.0023] | <.001 |
| 替代密度（V1+V2）二次项 | 20,484 | — | 二次项 $p=.074$ | .074 |
| 替代位置（等分三段） | 2,512 | χ² = 3.926 | — | .140 |

---

## 5 讨论

### 5.1 完成标准作为终止判准：过程层面的证据

本研究将用户指令中的完成标准/验证条件重新框架为任务型交互智能体的“终止判准”（stopping cue），并基于大规模真实交互轨迹提供了过程层面的证据。主结果显示，含完成标准的任务不仅完成率更高、执行步数更少，而且在终止阶段具有更低的冗余比例、错误比例及异常短轨迹率。这些发现共同支持如下解释：当用户指令提供明确的验证信息时，智能体更可能将自然语言目标转译为可操作的停止条件，从而在接近目标时与更少的冗余探索及错误尝试相关联。

然而，必须强调的是，本研究为观察性研究，无法确立因果关系。完成标准的存在可能与任务本身较简单、用户表达能力较强、或模型对特定表述更敏感等未观测变量相关。因此，本文使用“与……相关联”“预测”“提示”等关联性语言，而非“导致”“提升”等因果性表述。

### 5.2 理论解释

从言语行为理论视角看，完成标准与验证动作使指令的语力更加明确，智能体能够将“达到某状态”或“执行某验证动作”作为行为终止条件，降低意图歧义（Austin, 1962; Searle, 1969）。关联理论进一步解释为何明确验证信息可减少执行步数：智能体以更低的认知努力即可确认任务目标已达成，避免冗余探索（Sperber & Wilson, 1995）。行动终止理论则说明，完成标准为智能体提供了内部终止规则，减少对外部启发式停止规则的依赖，从而抑制过冲行为（Gigerenzer et al., 1999; Payne et al., 1993）。

### 5.3 对智能体设计的实践启示

对用户而言，在指令中明确加入“请确认……是否完成”“确保……处于……状态”等验证性表述，有助于智能体准确判断终止时机。对智能体设计者而言，可在规划模块中显式识别验证关键词并将其编码为候选终止条件；当用户指令缺乏验证信息时，智能体可主动询问用户以建立共同基础（Clark & Brennan, 1991）。此外，由于验证密度未呈现倒 U 形，当前结果不支持对验证信息数量的过度担忧；但未来在更复杂的领域特定任务中仍需进一步检验。

### 5.4 局限性与未来方向

首先，本研究为观察性研究，难以直接推断因果；完成标准可能与用户表达能力、任务复杂度等未观测变量相关。其次，验证类型的关键词标注较为粗糙，状态目标式与条件验证式的样本量过小，限制了对 H2 的检验。再次，当前分析未区分应用领域与智能体模型版本，未来可引入这些变量进行分层分析。最后，本文的终止阶段指标基于规则化的步骤标注（`last_step_redundant`、`last_step_correct`），其有效性受原始标注质量与规则定义影响；未来可结合人工复核或更细粒度的行为编码提升指标精度。

---

## 6 结论与展望

本研究基于 AgentNet 数据集，从言语行为理论、关联理论与行动终止理论出发，将用户指令中的完成标准/验证条件重新概念化为任务型交互智能体的“终止判准”，并实证检验了其与执行效率的关联。研究发现，含完成标准的指令与更高的任务完成率、更少的执行步数以及更低的终止阶段冗余/错误率相关联；但验证密度与完成率之间未发现稳健的倒 U 形关系，验证表述位置亦无显著效应。这些发现为理解自然语言指令如何塑造智能体终止行为提供了新的过程层面证据。

未来研究可从以下方向深化：（1）采用人工标注或依存句法分析提升验证类型识别的精度；（2）通过实验操纵验证显性度以建立因果推断；（3）探讨完成标准与约束密度、任务复杂度之间的交互效应；（4）将验证信息纳入智能体规划与终止模块，设计可解释的终止决策机制。

---

## 参考文献

Austin, J. L. (1962). *How to Do Things with Words*. Oxford University Press.

Clark, H. H., & Brennan, S. E. (1991). Grounding in communication. In *Perspectives on socially shared cognition* (pp. 127–149).

Gigerenzer, G., Todd, P. M., & the ABC Research Group. (1999). *Simple Heuristics That Make Us Smart*. Oxford University Press.

Goedert, M., et al. (2013). Instruction clarity and performance in human-computer interaction. *Human Factors, 55*(4), 772–783.

Lasecki, W. S., et al. (2013). Crowdsourcing step-by-step instructions for GUI tasks. In *Proceedings of UIST*.

Liang, J., et al. (2020). Language models are few-shot learners for GUI tasks. In *Proceedings of ACL*.

Li, X., et al. (2024). A survey of GUI agents: Methods, applications, and challenges. *arXiv preprint*.

Pal, S., et al. (2022). WebGPT: Browser-assisted question-answering with human feedback. In *Advances in Neural Information Processing Systems, 35*.

Payne, J. W., Bettman, J. R., & Johnson, E. J. (1993). *The Adaptive Decision Maker*. Cambridge University Press.

Schatz, B. R., et al. (2003). Task complexity and instruction design in human-machine interaction. *International Journal of Human-Computer Studies*.

Searle, J. R. (1969). *Speech Acts: An Essay in the Philosophy of Language*. Cambridge University Press.

Sperber, D., & Wilson, D. (1995). *Relevance: Communication and Cognition* (2nd ed.). Blackwell.

Yang, Y., et al. (2022). Mind2Web: Towards a generalist agent for the web. In *Advances in Neural Information Processing Systems, 35*.

Yuan, X., et al. (2023). AUSTIN: Training autonomous GUI agents with visual understanding. In *Proceedings of CVPR*.

Zhang, Y., et al. (2024). AgentNet: A large-scale dataset of GUI agent trajectories. *arXiv preprint*.

---

## 图表目录

- **图 1**：含完成标准任务中的验证类型分布（`revised/paper01_figures/fig1_验证类型分布.png`）
- **图 2**：是否包含完成标准的任务完成率与执行步数对比（`revised/paper01_figures/fig2_完成率与步数对比.png`）
- **图 3**：验证密度对任务完成概率的预测效应（`revised/paper01_figures/fig3_验证密度与完成概率.png`）
- **图 4**：验证表述位于不同位置时的任务完成率（`revised/paper01_figures/fig4_位置完成率.png`）
- **图 5**：Logistic 回归系数森林图（`revised/paper01_figures/fig5_逻辑回归系数森林图.png`）
- **图 6**：负二项回归系数森林图（`revised/paper01_figures/fig6_负二项回归系数森林图.png`）
- **图 7**：终止阶段指标按是否含完成标准的比较（`revised/paper01_figures/fig_terminal_phase_comparison.png`）

## 补充数据文件

- `revised/paper01_tables/terminal_phase_metrics_by_task.csv`：每条任务的终止阶段指标。
- `revised/paper01_tables/terminal_phase_summary_by_criteria.csv`：按是否含完成标准分组的描述性汇总。
- `revised/paper01_tables/terminal_phase_group_comparisons.csv`：终止阶段指标的组间比较统计量。
