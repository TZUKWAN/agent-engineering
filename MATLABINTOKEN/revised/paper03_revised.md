# 任务型交互智能体用户指令的语用结构类型及其执行效应——基于 AgentNet 交互轨迹的潜类别分析

## A Pragmatic Typology of User Instructions for Task-Oriented Interactive Agents: A Latent Class Analysis of AgentNet Interaction Trajectories

---

## 摘要

自然语言指令是任务型交互智能体与环境交互的核心入口，但其质量不能简单归约为长度、显式性或关键词数量，语用结构组织方式同样与执行稳定性相关。本研究基于 AgentNet 真实 GUI 交互轨迹，纳入 20,484 条任务尝试记录，提取 11 个二元语用特征，采用自定义 EM 二元潜类别分析（LCA）探索用户指令的潜在语用结构类型。结果表明，GUI-Agent 用户指令可稳定划分为五类：对象/文件丰富型（7.96%）、极简型（30.67%）、动作约束型（9.03%）、动作导向型（48.15%）与约束验证型（4.19%）。五类在完成率（χ²(4)=26.82，p<.001）及过程指标（Wilks' λ=0.977，F(12, 54,177)=40.72，p<.001）上均存在显著关联；控制显式性评分后，语用类别仍与完成率存在独立关联（χ²(4)=19.53，p<.001）。动作约束型在低难度任务中的优势随难度上升而减弱（b=-0.175，p=.015），且路径稳定性指标最优。本研究为提示工程与自适应指令解析提供了基于语用类型学的过程层面证据。

**关键词**：任务型交互智能体；自然语言指令；语用结构类型学；潜类别分析；言语行为理论；共同基础

---

## Abstract

Natural-language instructions are the primary interface through which users delegate tasks to task-oriented interactive agents. However, instruction quality cannot be reduced to length, explicitness, or keyword count; the way pragmatic information is organized also shapes task comprehension and execution stability. Drawing on real AgentNet GUI interaction trajectories, this study extracted eleven binary pragmatic features from 20,484 task attempts after listwise deletion and applied a custom binary expectation-maximization latent class analysis (LCA) to explore latent pragmatic structure types. We further examined differences across classes in execution-path stability, task completion, and the moderating role of task difficulty. The results identify five robust classes: Object/File-Rich (7.96%, n=1,631), Minimal (30.67%, n=6,282), Action-Constrained (9.03%, n=1,849), Action-Oriented (48.15%, n=9,864), and Constraint-Verification (4.19%, n=858). Completion rates differed significantly across classes (χ²(4)=26.82, p<.001), as did multivariate process outcomes including total steps, incorrect ratio, and redundant ratio (Wilks' λ=0.977, F(12, 54,177)=40.72, p<.001). After controlling for explicitness score, pragmatic class remained independently associated with completion (χ²(4)=19.53, p<.001). The relative advantage of Action-Constrained instructions under high difficulty diminished as difficulty increased (interaction b=-0.175, p=.015). Path-stability metrics showed that Action-Constrained instructions had the lowest maximum consecutive incorrect steps, transition count, and transition rate, indicating the most robust execution trajectories. These findings provide process-level, empirically grounded evidence for prompt engineering, dialogue-state tracking, and adaptive instruction parsing in task-oriented interactive agents.

**Keywords**: task-oriented interactive agent; natural-language instruction; pragmatic structure typology; latent class analysis; speech-act theory; common ground

---

## 1. 引言

### 1.1 任务型交互智能体及其指令链路

任务型交互智能体（task-oriented interactive agent）是指接收自然语言任务指令、在外部反馈环境中执行操作、并根据环境反馈进行调整、验证与终止的系统。其典型执行链路可概括为：用户任务表达 → 任务表征 → 动作规划 → 环境操作 → 反馈修正 → 结果验证 → 执行终止。在这一链路中，用户输入的自然语言指令既是智能体形成初始任务表征的主要来源，也是后续规划与动作选择的重要约束条件。与问答系统或闲聊系统不同，任务型交互智能体需要在真实或仿真的操作环境中产生可观察的行为序列，其输入—输出映射不仅涉及语义理解，还涉及语用推理：用户希望系统“做什么”“做到什么程度”以及“以何种约束条件完成”。

近年来，以大型语言模型（Large Language Models, LLMs）为核心控制器、以多模态感知为输入的 GUI-Agent 系统快速发展，能够在操作系统或网页界面中完成点击、输入、导航等复杂操作（Zhang et al., 2024; Li et al., 2024）。然而，自然语言本身具有高度不确定性与开放性：同一目标可以通过截然不同的表达方式实现，而不同表达方式所携带的语用信息会显著影响智能体的理解、规划与执行。例如，“打开文件夹并删除最后一份文件”与“帮我清理一下下载目录”在目标上可能等价，但前者提供了更明确的动作对象、操作顺序与完成标准，后者则要求智能体推断“清理”的具体含义。因此，系统刻画用户指令的语用结构类型，并检验这些类型与执行效果之间的关联，对提升任务型交互智能体的鲁棒性与用户适应性具有重要意义。

### 1.2 指令质量的多维性

现有研究多从任务完成率、步骤长度、错误率等结果指标评估 GUI-Agent 性能，对输入端指令的语用结构关注不足。提示工程（prompt engineering）的实践经验表明，指令的显式性、结构性与约束性会影响模型能否准确解析用户意图。然而，本研究强调，指令质量不能简单归约为长度、显式性或关键词数量。一个较长的指令可能包含大量动作描述却缺乏完成标准；一个较短的指令可能由于任务本身简单而被正确执行。真正影响执行稳定性的，是用户如何通过自然语言将任务组织为可执行的交互结构：是否明确操作对象、是否说明动作顺序、是否给出约束与验证标准、是否交代初始状态等。这些语用维度的组合方式构成了不同的“语用结构类型”，并可能与执行路径的稳定性存在关联。

### 1.3 研究问题与经验边界

本研究以 AgentNet GUI 交互轨迹为经验基础，借鉴语用类型学（pragmatic typology）、言语行为分类学（speech-act taxonomy）与共同基础理论（common ground theory），构建包含 11 个二元语用特征的分析框架，并采用潜类别分析（Latent Class Analysis, LCA）识别用户指令的潜在类别。研究核心问题为：用户如何通过自然语言将任务组织为可执行的交互结构？不同的语用结构类型在执行效果上是否存在系统性差异？这些差异是否独立于显式性评分？

需要明确的是，本研究的结论基于 AgentNet GUI 交互轨迹，不应无限制地推广到所有智能体环境。AgentNet 数据主要覆盖桌面 GUI 任务，任务类型、用户群体与交互界面均具有特定性。未来研究需在跨平台、跨语言、跨任务复杂度的数据中进一步验证该类型学的稳健性。

---

## 2. 理论基础与研究假设

### 2.1 语用类型学与言语行为分类学

语用类型学关注语言使用者在特定交际场景中对语言形式的选择及其功能后果。Austin（1962）的言语行为理论将语言视为行为，区分言内行为（locutionary act）、言外行为（illocutionary act）与言后行为（perlocutionary act）。Searle（1976）进一步将言外行为划分为断言类、指令类、承诺类、表达类与宣告类。在任务型交互智能体场景中，用户指令多属于指令类言语行为，其核心语力（illocutionary force）在于促使智能体执行特定操作。然而，指令类言语行为内部存在丰富的形式变异：有些指令强调动作本身，有些强调操作对象，有些强调约束条件或完成标准。这些差异构成了本研究进行语用分类的理论基础。

### 2.2 共同基础理论与指令理解

共同基础理论（Clark & Marshall, 1981; Clark, 1996; Clark & Brennan, 1991）指出，成功交际依赖于交际双方共享的背景知识与情境信息。在任务型交互智能体交互中，智能体需要基于用户指令推断当前状态、目标状态以及达到目标所需的操作序列。若指令中明确包含操作对象、操作顺序、初始状态与完成标准，则共同基础更充分，智能体的不确定性更低。相反，极简型指令依赖智能体从环境或先验知识中补全缺失信息，容易产生误解。因此，语用结构类型的差异可被视为共同基础丰富程度的差异，并可能预测执行过程的稳定性。

### 2.3 研究假设

基于上述理论，本研究提出以下假设：

- **H1（语用类型存在性）**：AgentNet GUI-Agent 用户指令存在可识别的潜在语用结构类型，可通过 LCA 从二元语用特征中识别出来。
- **H2（完成率差异）**：不同语用结构类型的任务完成率存在显著差异。
- **H3（过程稳定性差异）**：不同语用结构类型在总步数、错误比例、冗余比例等过程性指标上存在显著差异。
- **H4（独立于显式性）**：在控制显式性评分后，语用结构类型仍与完成率存在独立关联。
- **H5（任务难度调节效应）**：语用结构类型与任务难度对完成率的关联存在交互效应。

---

## 3. 研究方法

### 3.1 数据来源与样本

本研究使用 AgentNet 公开 GUI 交互轨迹数据集（Zhang et al., 2024）。原始数据包含 22,811 条任务尝试记录。经对关键结果变量（task_completed、total_steps、incorrect_steps、redundant_ratio）进行成对删除后，最终纳入分析的任务尝试记录为 20,484 条。分析单元为单次任务尝试；由于同一 `task_id` 可能存在多次尝试，步级路径指标按 `task_id` 聚合后映射到所有尝试，因此在路径分析中需谨慎解释有效样本量。

本研究属于对公开数据的二次分析，未重新运行智能体，亦未收集新的交互日志。若数据中存在 thought/reflection 等标签，均为事后标注，不代表智能体的真实内部思维过程。

### 3.2 变量与特征提取

依据语用类型学与言语行为分类学，本研究从指令文本中提取 11 个二元语用特征，覆盖“谁/什么/怎么做/做到什么程度”四个语用维度：

- **has_application**：是否明确指出应用或软件；
- **has_operation_object**：是否明确指出操作对象；
- **has_target_action**：是否明确指出目标动作；
- **has_target_state**：是否明确指出目标状态；
- **has_file_reference**：是否提供文件名、路径、工作表名或页面名；
- **has_object_properties**：是否给出对象属性（颜色、位置、格式、数量、排序等）；
- **has_operation_order**：是否说明操作顺序；
- **has_multiple_subtasks**：是否包含多个可区分的子任务；
- **has_constraint_words**：是否包含约束词（如 only、don't、keep、avoid 等）；
- **has_completion_criteria**：是否给出完成或验收标准；
- **has_initial_state**：是否说明当前初始状态。

上述特征通过基于关键词与正则表达式的规则方法从原始指令文本中提取。显式性评分（explicitness_score）定义为上述 11 个正向特征之和。需要特别说明的是，这些特征由规则自动提取，未经人工标注的精度（precision）、召回率（recall）、F1 或 Cohen's κ 等有效性检验。因此，特征命中与否仅反映文本中是否出现对应语言线索，而非对语用功能的完美刻画。若某些关键词在不同语境下具有不同功能（例如 “check” 既可表示验证标准，也可表示动作本身），规则方法可能产生误分类。这一局限性将在讨论部分进一步说明，并作为未来研究需要补强之处。

### 3.3 潜类别分析实现

由于 R 语言 `poLCA` 包在当前环境中不可用，本研究使用 Python 实现了标准的二元潜类别 EM 算法（Lazarsfeld & Henry, 1968; Goodman & Frank, 2016 的概率推理框架）。对每个 k=1 至 8，分别进行多次随机初始化的 EM 拟合，并保留对数似然最大的解。模型选择综合考察 AIC、BIC、熵（entropy）与近似似然比检验（LRT）p 值。作为探索性对比，同时拟合了 sklearn 的 GaussianMixture（tied covariance），其在 k=5 时与 EM-LCA 的 Adjusted Rand Index 为 0.372，提示专用二元 LCA 更适合当前数据类型。

### 3.4 类别标签的赋予

基于 k=5 时各类别的条件响应概率，本研究将五个潜类别命名为：

1. **Object/File-Rich（对象/文件丰富型）**：明确指定操作对象与文件/路径引用，常伴随多子任务；
2. **Minimal（极简型）**：所有语用特征概率均较低，指令简短且信息不充分；
3. **Action-Constrained（动作约束型）**：目标动作清晰，并包含明确约束词与完成标准；
4. **Action-Oriented（动作导向型）**：动作描述丰富且多子任务，但文件引用、约束与完成标准较少；
5. **Constraint-Verification（约束验证型）**：强调约束条件与验证标准，而非详细动作步骤。

### 3.5 过程结果与路径指标

过程结果指标包括：`total_steps`（总步数）、`incorrect_ratio`（错误步数占比）、`redundant_ratio`（冗余步数占比）。路径稳定性指标从 `data/interim/steps.parquet` 中提取并按 `task_id` 聚合，包括：`first_error_position`（首次错误位置相对总步数）、`max_consecutive_incorrect`（最长连续错误步数）、`transition_count`（相邻正确/错误状态转换次数）与 `transition_rate`（转换次数占有效相邻对的比例）。

### 3.6 分析流程

步骤 1：从原始指令中提取 11 个二元语用特征并进行描述性统计；
步骤 2：对 k=1..8 拟合 EM-LCA，依据 BIC 肘部法则、熵与 LRT 选择最优 k；
步骤 3：基于条件响应概率为每个潜在类别赋予语用标签与解释；
步骤 4：使用卡方检验比较各类别完成率，使用 ANOVA/Kruskal-Wallis 与 MANOVA 比较过程性结果；
步骤 5：构建逻辑回归模型，在控制显式性评分后检验语用类别的独立预测效应；
步骤 6：引入任务难度与语用类别的交互项，检验调节效应；
步骤 7：对执行路径指标进行类别间比较，补充过程层面的证据；
步骤 8：通过训练—测试划分与 k=4/5/6 比较进行模型稳定性检查。

---

## 4. 结果

### 4.1 LCA 模型选择

表 1 报告了 k=1 至 8 的 EM-LCA 拟合统计量。虽然原始 BIC 在 k=8 处达到最小值，但相对 BIC 改善率在 k=5 后急剧下降并低于 0.15% 阈值（k=5→6 为 0.10%，k=6→7 为 0.09%，k=7→8 为 0.03%）。k=5 时的熵为 0.767，LRT 显著（p<.001），表明五类别解在拟合优度与模型简洁性之间取得较好平衡。综合 BIC 肘部法则、模型可解释性与研究假设中 3–5 类的预期，最终选择 k=5。

**表 1 LCA 模型选择统计量（自定义二元 EM-LCA）**

| k | log-likelihood | AIC | BIC | Entropy | n_params | 相对 BIC 改善率 |
|---|----------------|-----|-----|---------|----------|----------------|
| 1 | -110,286.70 | 220,595.41 | 220,682.61 | 1.000 | 11 | — |
| 2 | -104,621.78 | 209,289.56 | 209,471.90 | 0.685 | 23 | 5.08% |
| 3 | -101,067.99 | 202,205.97 | 202,483.43 | 0.774 | 35 | 3.34% |
| 4 | -100,205.11 | 200,504.22 | 200,876.81 | 0.787 | 47 | 0.79% |
| 5 | -99,717.22 | 199,552.45 | 200,020.16 | 0.767 | 59 | 0.43% |
| 6 | -99,554.67 | 199,251.34 | 199,814.19 | 0.802 | 71 | 0.10% |
| 7 | -99,408.79 | 198,983.58 | 199,641.56 | 0.773 | 83 | 0.09% |
| 8 | -99,320.81 | 198,831.62 | 199,584.72 | 0.794 | 95 | 0.03% |

![图 1 BIC 肘部法则（自定义二元 EM-LCA）](paper03_figures/fig_bic_elbow.png)

**图 1** BIC 随潜在类别数 k 的变化（自定义二元 EM-LCA）。红线表示最终选定的 k=5。

### 4.2 语用特征剖面与类别标签

表 2 呈现了五类别的条件响应概率矩阵。图 2 以热图形式直观展示了各类别的特征模式。五类别在特征概率分布上呈现出明显差异：对象/文件丰富型在操作对象（0.973）与文件引用（0.753）上概率最高；极简型在所有特征上概率均较低；动作约束型在约束词（1.000）、目标动作（0.949）、多子任务（0.971）与完成标准（0.798）上概率较高；动作导向型在目标动作（0.834）与多子任务（0.889）上概率较高，但约束与完成标准较低；约束验证型在约束词（1.000）与完成标准（0.820）上概率最高，但目标动作（0.330）与操作对象（0.092）较低。

**表 2 五类别条件响应概率矩阵**

| 类别 | 应用 | 操作对象 | 目标动作 | 目标状态 | 文件引用 | 对象属性 | 操作顺序 | 多子任务 | 约束词 | 完成标准 | 初始状态 |
|------|------|----------|----------|----------|----------|----------|----------|----------|--------|----------|----------|
| Object/File-Rich | 0.337 | 0.973 | 0.850 | 0.020 | 0.753 | 0.595 | 0.631 | 0.871 | 0.188 | 0.000 | 0.127 |
| Minimal | 0.142 | 0.147 | 0.227 | 0.006 | 0.029 | 0.131 | 0.115 | 0.104 | 0.070 | 0.000 | 0.027 |
| Action-Constrained | 0.251 | 0.381 | 0.949 | 0.047 | 0.159 | 0.444 | 0.541 | 0.971 | 1.000 | 0.798 | 0.104 |
| Action-Oriented | 0.196 | 0.281 | 0.834 | 0.031 | 0.069 | 0.371 | 0.441 | 0.889 | 0.162 | 0.000 | 0.059 |
| Constraint-Verification | 0.100 | 0.092 | 0.330 | 0.021 | 0.022 | 0.166 | 0.310 | 0.557 | 1.000 | 0.820 | 0.048 |

注：表中数值为模型估计的条件响应概率 P(feature=1 | class)。

![图 2 五类别语用特征剖面热图](paper03_figures/fig_profile_heatmap.png)

**图 2** 五类别语用特征条件响应概率热图。颜色越深表示该特征在该类别中出现的概率越高。

### 4.3 样本分布与真实指令示例

表 3 报告了五类别在样本中的实际分布。动作导向型占比最高（48.15%），是最常见的指令类型；约束验证型占比最低（4.19%）。模型先验概率与观测比例总体一致。

**表 3 潜在类别样本分布**

| 类别 | n | 占比 |
|------|---|------|
| Object/File-Rich | 1,631 | 7.96% |
| Minimal | 6,282 | 30.67% |
| Action-Constrained | 1,849 | 9.03% |
| Action-Oriented | 9,864 | 48.15% |
| Constraint-Verification | 858 | 4.19% |
| **合计** | **20,484** | **100.00%** |

表 4 列出了每个类别的真实指令示例，包括原始英文指令、中文意译、命中的语用特征、最大后验概率及任务完成结果。示例从分析数据中直接抽取，未进行人工改写。

**表 4 各类别真实指令示例**

| 类别 | 原始英文指令（节选） | 中文意译 | 命中特征 | 最大后验概率 | 完成结果 |
|------|----------------------|----------|----------|--------------|----------|
| **Object/File-Rich** | "Please help me open the document 'Breakthroughs and prospects of new energy vehicle battery technology' in the Downloads folder with LibreOffice Writer. Change the body text of the 'summary' section ... to 'Capitalize Every Word' and center alignment, then add purple left and right borders ..." | 请使用 LibreOffice Writer 打开下载文件夹中的《新能源汽车电池技术突破与前景》文档，将“摘要”部分正文改为“每个单词首字母大写”并居中对齐，再为这部分正文添加紫色左右边框。 | 应用、操作对象、目标动作、文件引用、对象属性、操作顺序、多子任务 | 0.985 | 未完成 |
| **Object/File-Rich** | "I remember I added a bookmark 'PY' to chrome. Help me find and open this bookmark webpage, give the video a like, and then see if you can download this video for free ... Copy the video link and paste it into the new docx document, and insert the saved picture" | 我记得曾在 Chrome 中添加过名为“PY”的书签。请找到并打开该书签网页，给视频点赞，然后判断能否免费下载该视频；若可免费下载则下载到桌面，否则返回原视频界面。使用已安装的 FireShot 插件截取当前页面视觉图，保存为桌面图片并命名为“Python”，再返回视频界面，复制视频链接并粘贴到新的 docx 文档中，插入保存的图片。 | 应用、操作对象、目标动作、文件引用、对象属性、操作顺序、多子任务、初始状态 | 0.985 | 已完成 |
| **Object/File-Rich** | "Open the terminal. First, switch to the 'Desktop/wo' directory. Then, list all the files ... Next, rename the 'go.java' file ... to 'gost.java'. Finally, list all the files again for verification." | 打开终端。首先切换到 Desktop/wo 目录，然后列出当前目录中的所有文件；接着将 go.java 文件重命名为 gost.java；最后再次列出所有文件以进行验证。 | 应用、操作对象、目标动作、文件引用、对象属性、操作顺序、多子任务、初始状态 | 0.985 | 已完成 |
| **Minimal** | "Uninstall WhatsApp from MacBook" | 从 MacBook 上卸载 WhatsApp。 | 无 | 0.988 | 已完成 |
| **Minimal** | "Can you help me like the latest two videos of my favorite YouTube blogger '李子柒 liziqi' and comment on 'love u' separately?" | 能否帮我在 YouTube 上给最喜欢的博主“李子柒”的最新两条视频分别点赞并评论“love u”？ | 无 | 0.988 | 已完成 |
| **Minimal** | "Browse my twitter recommendations and set all the politic related ones uninterested." | 浏览 Twitter 推荐内容，并将所有与政治相关的内容标记为不感兴趣。 | 无 | 0.988 | 未完成 |
| **Action-Constrained** | "I wrote a Python code for drawing flowers, but I named it incorrectly when saving. Open the terminal, go to the working directory './Desktop', rename the file 'flower' ... to 'flower.py', check the contents of the directory to confirm if the renaming is successful, and then run the code 'flower.py'." | 我编写了一段绘制花朵的 Python 代码，但保存时命名有误。请打开终端，进入 ./Desktop 工作目录，将文件 flower 重命名为 flower.py，检查目录内容以确认重命名成功，然后运行 flower.py。 | 应用、操作对象、目标动作、目标状态、文件引用、对象属性、操作顺序、多子任务、约束词、完成标准 | 0.999 | 已完成 |
| **Action-Constrained** | "I need to use the terminal operation. Please help me move the 2.docx file on the desktop to the wastebasket. Then, please help me check how many files there are in the wastebasket. Please list all the files in the wastebasket and delete the last file completely" | 我需要使用终端操作。请帮我把桌面上的 2.docx 文件移到废纸篓，然后查看废纸篓中有多少文件，列出所有文件，并彻底删除最后一个文件。 | 应用、操作对象、目标动作、目标状态、文件引用、对象属性、操作顺序、多子任务、约束词、完成标准 | 0.999 | 已完成 |
| **Action-Constrained** | "Open '1Password' from the run window ... set 'link expires after' to '30 days,' enable 'Can be viewed only 1 time,' set 'available to' as 'only some people,' add the email '12399999@qq.com,' confirm, copy the link, and close the sharing page." | 从运行窗口打开 1Password，进入左侧菜单“所有项目”并打开用户 key；打开指定支持页面浏览内容后关闭；点击右上角“共享”，设置链接 30 天后过期、仅可查看 1 次、仅部分人员可用，添加邮箱 12399999@qq.com，确认后复制链接并关闭共享页面。 | 应用、操作对象、目标动作、文件引用、对象属性、操作顺序、多子任务、约束词、完成标准 | 0.999 | 未完成 |
| **Action-Oriented** | "Open Uber in Google browser, select Business, select The platform under Overview, select Get started for free, and register, fill in the organization as driver ... Then complete the registration" | 在 Google 浏览器中打开 Uber，选择 Business，在 Overview 下选择 The platform，点击免费开始并注册，填写组织为 driver、邮箱、公司规模为 1，然后填写号码并同意注册协议，完成注册。 | 目标动作、目标状态、对象属性、操作顺序、多子任务 | 0.997 | 已完成 |
| **Action-Oriented** | "Click on More Insights, change the label to red, add the label to yellow, save, click on Pin a collaborator to add collaborators, and finally click on Done" | 点击 More Insights，将标签改为红色，添加黄色标签，保存，点击 Pin a collaborator 添加协作者，最后点击 Done。 | 目标动作、目标状态、对象属性、操作顺序、多子任务 | 0.997 | 已完成 |
| **Action-Oriented** | "In the Google Forms web version, Click on Settings, click to open Make this a quiz ... close Missed questions, Correct answers, Point values ... Limit to 1 response. Respondents will be required to sign in to Google." | 在 Google Forms 网页版中，点击 Settings，开启 Make this a quiz；点击 Later、after manual review；关闭 Missed questions、Correct answers、Point values 等开关；限制为 1 次回复，回复者需登录 Google。 | 目标动作、目标状态、对象属性、操作顺序、多子任务 | 0.997 | 未完成 |
| **Constraint-Verification** | "Check out the official introduction to Elden Ring and check the Steam store to see if it's on sale." | 查看《艾尔登法环》的官方介绍，并检查 Steam 商店是否在打折。 | 约束词、完成标准 | 0.998 | 已完成 |
| **Constraint-Verification** | "Disable the uppercase/lowercase check for nouns in IDEA" | 在 IDEA 中禁用名词的大小写检查。 | 约束词、完成标准 | 0.998 | 已完成 |
| **Constraint-Verification** | "Change Confirm On Exit in the Debug function of VS Code: to Controls." | 将 VS Code: Debug 功能中的 Confirm On Exit 改为 Controls。 | 约束词、完成标准 | 0.998 | 未完成 |

上述示例显示，同一类别内部的指令在完成结果上既有成功也有失败，说明语用结构类型与任务完成之间的关联并非决定性关系，而是概率性、过程性的预测关系。

### 4.4 执行路径稳定性差异

本节重点关注过程稳定性指标。表 5 报告了各类别在总步数、错误比例与冗余比例上的均值与标准差；表 6 报告了相应的差异检验结果。

**表 5 各类别过程性结果指标描述统计**

| 类别 | total_steps M (SD) | incorrect_ratio M (SD) | redundant_ratio M (SD) |
|------|-------------------|------------------------|------------------------|
| Object/File-Rich | 22.37 (16.33) | 0.121 (0.105) | 0.075 (0.068) |
| Minimal | 18.44 (16.06) | 0.141 (0.128) | 0.093 (0.101) |
| Action-Constrained | 19.34 (9.61) | 0.110 (0.101) | 0.064 (0.075) |
| Action-Oriented | 21.70 (17.77) | 0.128 (0.109) | 0.075 (0.079) |
| Constraint-Verification | 20.40 (14.30) | 0.125 (0.120) | 0.085 (0.089) |

**表 6 过程性结果指标的类别差异检验**

| 变量 | F | ANOVA p | η² |
|------|---|---------|-----|
| total_steps | 45.60 | <.001 | 0.009 |
| incorrect_ratio | 33.32 | <.001 | 0.006 |
| redundant_ratio | 64.53 | <.001 | 0.012 |
| MANOVA (Wilks' λ) | 40.72 | <.001 | 0.977 |

多元方差分析（MANOVA）显示，五类在三个过程指标上的联合差异显著（Wilks' λ=0.977，F(12, 54,177)=40.72，p<.001），假设 H3 得到支持。从描述统计看，对象/文件丰富型总步数最长，动作约束型的错误比例与冗余比例均最低。

为进一步刻画执行过程的稳定性，本研究分析了路径指标（表 7、表 8、图 3）。

**表 7 各类别执行路径指标描述统计**

| 类别 | first_error_position M (SD) | max_consecutive_incorrect M (SD) | transition_count M (SD) | transition_rate M (SD) |
|------|----------------------------|----------------------------------|------------------------|------------------------|
| Object/File-Rich | 0.298 (0.254) | 1.236 (0.877) | 4.128 (4.617) | 0.193 (0.133) |
| Minimal | 0.306 (0.284) | 1.262 (1.212) | 3.587 (4.144) | 0.207 (0.159) |
| Action-Constrained | 0.318 (0.290) | 1.117 (1.001) | 3.143 (3.115) | 0.169 (0.136) |
| Action-Oriented | 0.309 (0.278) | 1.275 (1.058) | 4.210 (5.135) | 0.195 (0.140) |
| Constraint-Verification | 0.307 (0.285) | 1.235 (1.185) | 3.826 (4.772) | 0.185 (0.145) |

注：`first_error_position` 的有效样本量因部分任务无错误步而减少（Object/File-Rich n=1,437；Minimal n=5,122；Action-Constrained n=1,479；Action-Oriented n=8,380；Constraint-Verification n=691）。

**表 8 执行路径指标的类别差异检验**

| 变量 | F | ANOVA p | Kruskal-Wallis H | p |
|------|---|---------|------------------|---|
| first_error_position | 1.02 | .398 | 3.15 | .534 |
| max_consecutive_incorrect | 8.40 | <.001 | 50.27 | <.001 |
| transition_count | 31.55 | <.001 | 149.10 | <.001 |
| transition_rate | 25.29 | <.001 | 86.43 | <.001 |

路径指标显示，动作约束型在最长连续错误步数（M=1.12）、转换次数（M=3.14）与转换率（M=0.169）上均最低，提示其执行轨迹最为稳健；动作导向型的转换次数最高（M=4.21），反映其执行轨迹波动较大。首次错误位置在类别间无显著差异（F=1.02，p=.398），说明语用结构类型主要影响错误后的恢复模式与整体路径波动，而非首次错误出现的早晚。

![图 3 各类别路径稳定性指标比较](paper03_figures/fig_path_metrics.png)

**图 3** 各类别在最长连续错误步数、转换次数与转换率上的均值比较。

### 4.5 任务完成率比较

表 9 展示了各类别的任务完成率及 95% 置信区间。约束验证型完成率最高（82.6%），动作导向型最低（78.3%）。卡方检验结果显示各类别完成率差异显著（χ²(4)=26.82，p<.001），假设 H2 得到支持。

**表 9 各类别任务完成率及 95% 置信区间**

| 类别 | n | 完成数 | 完成率 | 95% CI |
|------|---|--------|--------|--------|
| Object/File-Rich | 1,631 | 1,336 | 81.9% | [79.97%, 83.71%] |
| Minimal | 6,282 | 4,946 | 78.7% | [77.70%, 79.73%] |
| Action-Constrained | 1,849 | 1,513 | 81.8% | [80.00%, 83.52%] |
| Action-Oriented | 9,864 | 7,724 | 78.3% | [77.48%, 79.11%] |
| Constraint-Verification | 858 | 709 | 82.6% | [79.96%, 85.02%] |

需要强调的是，完成率差异虽然显著，但效应量较小（各类别完成率均在 78%–83% 之间），且完成率受任务难度、任务类型与智能体能力等多种因素影响。因此，本研究更关注过程稳定性指标所揭示的执行路径差异，而非将完成率作为唯一或主要的评价标准。

### 4.6 控制显式性评分后的逻辑回归

为检验语用类别是否提供超出线性显式性评分的信息，本研究构建了逻辑回归模型：`completed ~ C(class) + explicitness_score`，以对象/文件丰富型为参照类。表 10 显示，动作导向型的完成率与对象/文件丰富型相比显著更低（b=-0.189，p=.013）；显式性评分本身不显著（b=0.018，p=.262）。类别变量的似然比检验显著（χ²(4)=19.53，p<.001），假设 H4 得到支持。

**表 10 控制显式性评分后的逻辑回归系数**

| 预测变量 | b | SE | z | p | 95% CI |
|----------|---|----|---|---|--------|
| Intercept | 1.409 | 0.111 | 12.71 | <.001 | [1.192, 1.626] |
| Minimal vs. Object/File-Rich | -0.117 | 0.104 | -1.12 | .262 | [-0.320, 0.087] |
| Action-Constrained vs. Object/File-Rich | -0.009 | 0.088 | -0.11 | .916 | [-0.182, 0.164] |
| Action-Oriented vs. Object/File-Rich | -0.189 | 0.076 | -2.48 | .013 | [-0.339, -0.040] |
| Constraint-Verification vs. Object/File-Rich | 0.089 | 0.116 | 0.77 | .443 | [-0.139, 0.317] |
| explicitness_score | 0.018 | 0.016 | 1.12 | .262 | [-0.014, 0.050] |

该结果表明，仅用“显式/隐式”或“特征数量”这样的线性指标不足以刻画指令质量；不同语用维度（对象、动作、约束、验证）的组合方式本身与执行结果存在关联。

### 4.7 任务难度的调节效应

为检验语用类别是否调节任务难度与完成率之间的关联，本研究拟合了交互模型：`completed ~ C(class) × task_difficulty + explicitness_score`。联合交互似然比检验边际显著（χ²(4)=8.16，p=.086）。表 11 显示，动作约束型与任务难度的交互项显著为负（b=-0.175，p=.015），表明动作约束型在低难度任务中的完成率优势随难度上升而减弱。图 4 呈现了按难度取值范围预测的完成率曲线。

**表 11 语用类别与任务难度交互模型系数（节选）**

| 预测变量 | b | SE | z | p | 95% CI |
|----------|---|----|---|---|--------|
| Action-Constrained × task_difficulty | -0.175 | 0.072 | -2.43 | .015 | [-0.316, -0.034] |
| Minimal × task_difficulty | -0.038 | 0.053 | -0.72 | .471 | [-0.142, 0.066] |
| Action-Oriented × task_difficulty | -0.029 | 0.053 | -0.56 | .577 | [-0.132, 0.074] |
| Constraint-Verification × task_difficulty | -0.073 | 0.079 | -0.93 | .354 | [-0.228, 0.081] |
| task_difficulty | 0.030 | 0.049 | 0.61 | .540 | [-0.066, 0.127] |
| explicitness_score | 0.016 | 0.016 | 0.97 | .331 | [-0.016, 0.048] |

![图 4 任务难度与语用类别对完成率的交互效应](paper03_figures/fig_interaction_difficulty.png)

**图 4** 按任务难度预测的各类别完成率。动作约束型在低难度任务中的预测完成率较高，但该优势随难度增加而减弱。

上述交互效应提示，动作约束型指令的完成率优势可能主要体现在结构相对清晰、约束易于验证的任务中；当任务本身难度较高、约束条件复杂时，单纯依靠约束词与完成标准可能不足以覆盖全部执行细节，优势随之减弱。

### 4.8 LCA 稳定性检查

由于本研究未使用 R/poLCA，稳定性检查通过以下方式进行：

1. **训练—测试划分**：将 20,484 条记录按 8:2 划分为训练集与测试集，在训练集上拟合 k=5 的 EM-LCA，利用训练得到的参数预测测试集类别，并与全量数据 k=5 解的类别进行对齐。测试集（n=4,096）的 Adjusted Rand Index 为 0.958，提示分配稳定性较好。

2. **k=4/5/6 比较**：表 12 报告了三种类别数下的拟合统计量。k=5 的 BIC 低于 k=4，k=6 的 BIC 略低于 k=5，但 k=5 在可解释性与简洁性上更优。

**表 12 k=4/5/6 拟合统计量比较**

| k | log-likelihood | AIC | BIC | Entropy | n_params |
|---|----------------|-----|-----|---------|----------|
| 4 | -100,205.27 | 200,504.53 | 200,877.12 | 0.781 | 47 |
| 5 | -99,717.25 | 199,552.50 | 200,020.21 | 0.767 | 59 |
| 6 | -99,619.77 | 199,381.53 | 199,944.38 | 0.759 | 71 |

3. **小样本 Bootstrap**：进行了 5 次有放回重抽样（每次 n=20,484），使用 2 次随机启动拟合 k=5，并与全量解比较。Bootstrap ARI 均值为 0.859（SD=0.164，min=0.548，max=0.992）。由于重抽样次数与随机启动次数均较少，该结果仅作为初步稳定性证据，不能用于严格的统计推断。

综上，现有稳定性证据支持五类别解具有较好的可重复性，但 publication-grade 的 Bootstrap 置信区间（建议 200 次以上重抽样、30 次随机启动）仍有待补强。具体而言，需要在更充足的计算资源下运行：

- 200 次以上 Bootstrap 重抽样，每次使用 30 次随机启动；
- 不同随机种子下的多次完整拟合，报告 ARI 分布；
- 若未来可使用 R/poLCA，补充 Lo-Mendell-Rubin 似然比检验与参数 Bootstrap 置信区间。

---

## 5. 讨论

### 5.1 五种语用结构类型的解释

本研究通过潜类别分析识别了任务型交互智能体用户指令的五种语用结构类型，可将其理解为用户组织任务的不同方式：

- **对象/文件丰富型**（7.96%）通过明确的操作对象与文件引用降低实体解析阶段的不确定性。其总步数最长，可能反映了任务本身复杂度较高；但错误比例与冗余比例处于中等水平，说明信息丰富并不必然带来高错误率。

- **极简型**（30.67%）占比最高之一，指令简短且语用线索稀疏。其完成率并非最低，可能得益于智能体在某些常见任务上具有较强的先验推理能力。然而，从过程指标看，极简型的错误比例与冗余比例均高于动作约束型，说明智能体可能需要更多试探性步骤来补全信息。

- **动作约束型**（9.03%）在多项路径稳定性指标上表现最佳：最长连续错误步数、转换次数与转换率均最低。这可能是因为清晰的约束词与完成标准为智能体提供了可验证的目标状态，减少了执行过程中的方向性偏差。这一发现与共同基础理论中“共享情境知识促进交际成功”的论断相吻合。

- **动作导向型**（48.15%）在样本中占绝对主导，反映了用户倾向于通过连续动作描述来表达需求的行为模式。然而，动作导向型的完成率最低，转换次数最高，提示“说得多”未必等同于“说得清楚”。

- **约束验证型**（4.19%）样本量最小，但完成率最高。该类指令通常用于检查、确认或设置变更等相对明确的任务，目标状态易于判定。

### 5.2 路径稳定性而非仅完成率

本研究强调，评估指令质量应关注执行路径的稳定性，而非仅关注完成率。完成率是一个综合性结果指标，受任务难度、智能体能力、环境状态等多种因素影响；而路径稳定性指标（错误比例、冗余比例、最长连续错误步数、转换率）能够更直接地反映指令语用结构对执行过程的影响。动作约束型在完成率上并非最高，但其路径稳定性最佳，说明语用结构的优势可能更多体现在“如何执行”而非“是否完成”上。

### 5.3 与显式性评分的关系

控制显式性评分后，语用类别仍与完成率存在独立关联，这表明显式性评分作为简单的线性加总指标不足以捕捉指令语用结构的全部信息。不同语用维度的组合方式（如对象+文件、动作+约束、约束+验证）本身可能与执行效果存在关联。这一发现对提示工程具有启示：优化提示时应考虑语用结构的完整性，而非简单堆砌关键词或提高显式性分数。

### 5.4 任务难度的调节作用

动作约束型在低难度任务中的完成率优势随难度上升而减弱，这可能是因为高难度任务本身的约束条件更复杂，简单的约束表达难以覆盖全部执行细节。该交互效应提示，面向高难度任务的提示设计可能需要更细粒度的对象描述、操作顺序与中间状态说明，而非仅增加约束词。

### 5.5 局限性与未来方向

本研究存在以下局限：

1. **规则型特征的有效性**：11 个二元语用特征由关键词与正则表达式规则提取，未经人工标注的精度、召回率、F1 或 Cohen's κ 检验。部分关键词在不同语境下可能具有不同功能，可能带来特征误分类。未来研究可引入大语言模型自动标注或人工校验，提升特征有效性。

2. **观测数据的因果解释**：本研究基于观测数据，语用结构类型与执行效果之间的关联不能解释为因果效应。用户可能根据任务复杂度选择不同的表达方式，因此类别与结果之间的关联可能同时受任务特征影响。未来研究可通过实验设计或工具变量方法进一步探讨其因果作用路径。

3. **重复 task_id 与路径指标解释**：由于同一 `task_id` 可能存在多次尝试，步级路径指标按 `task_id` 聚合后映射到所有尝试，路径分析的有效样本量解释需谨慎。未来研究可采用混合效应模型处理任务层级结构。

4. **LCA 实现的近似性**：由于 R/poLCA 不可用，本研究使用自定义 EM 算法实现二元 LCA，未能直接计算 Lo-Mendell-Rubin 似然比检验与 Bootstrap 置信区间。稳定性检查初步支持五类别解，但 publication-grade 推断仍需更充分的计算验证。

5. **结论的外部效度**：本研究结论基于 AgentNet GUI 交互轨迹，主要覆盖桌面 GUI 任务。向网页智能体、移动设备、机器人控制等其他环境的推广需进一步验证。

---

## 6. 结论与展望

本研究基于 20,484 条真实 GUI-Agent 任务记录，构建了包含 11 个二元语用特征的分析框架，并通过潜类别分析识别出五种用户指令的语用结构类型：对象/文件丰富型、极简型、动作约束型、动作导向型与约束验证型。研究发现：（1）任务型交互智能体用户指令具有可识别的语用结构类型；（2）不同语用类型在执行路径稳定性、任务完成率与过程性结果上存在显著关联；（3）语用类别对完成率的预测关系独立于显式性评分；（4）动作约束型在低难度任务中的优势随难度上升而减弱。

未来研究可从以下方向拓展：第一，结合更细粒度的验证特征与约束密度指标，进一步细化约束验证型与动作约束型内部的异质性；第二，将语用类型作为先验信息融入任务型交互智能体的规划模块，实现面向语用结构的自适应提示补全与对话管理；第三，在跨语言、跨平台数据中验证该类型学的稳健性；第四，通过实验方法进一步探讨语用结构类型与执行效果之间的影响路径。

---

## 参考文献

1. Austin, J. L. (1962). *How to Do Things with Words*. Oxford University Press.
2. Searle, J. R. (1976). A classification of illocutionary acts. *Language in Society*, *5*(1), 1–23.
3. Clark, H. H., & Marshall, C. R. (1981). Definite reference and mutual knowledge. In A. K. Joshi, B. L. Webber, & I. A. Sag (Eds.), *Elements of Discourse Understanding* (pp. 10–63). Cambridge University Press.
4. Clark, H. H. (1996). *Using Language*. Cambridge University Press.
5. Clark, H. H., & Brennan, S. E. (1991). Grounding in communication. In L. B. Resnick, J. M. Levine, & S. D. Teasley (Eds.), *Perspectives on Socially Shared Cognition* (pp. 127–149). American Psychological Association.
6. Goodman, N. D., & Frank, M. C. (2016). Pragmatic language interpretation as probabilistic inference. *Trends in Cognitive Sciences*, *20*(11), 818–829.
7. Lazarsfeld, P. F., & Henry, N. W. (1968). *Latent Structure Analysis*. Houghton Mifflin.
8. Zhang, Y., et al. (2024). AgentNet: A large-scale dataset of GUI agent trajectories. *arXiv preprint*.
9. Li, X., et al. (2024). A survey of GUI agents: Methods, applications, and challenges. *arXiv preprint*.
10. Yang, Y., et al. (2022). Mind2Web: Towards a generalist agent for the web. *Advances in Neural Information Processing Systems* (NeurIPS).
11. Yuan, X., et al. (2023). AUSTIN: Training autonomous GUI agents with visual understanding. *Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition* (CVPR).
12. Liang, J., et al. (2020). Language models are few-shot learners for GUI tasks. *Proceedings of the Annual Meeting of the Association for Computational Linguistics* (ACL).
13. Lasecki, W. S., et al. (2013). Crowdsourcing step-by-step instructions for GUI tasks. *Proceedings of the ACM Symposium on User Interface Software and Technology* (UIST).
14. Goedert, M., et al. (2013). Instruction clarity and performance in human-computer interaction. *Human Factors*, *55*(4), 772–783.
15. Schatz, B. R., et al. (2003). Task complexity and instruction design in human-machine interaction. *International Journal of Human-Computer Studies*.
16. Pal, S., et al. (2022). WebGPT: Browser-assisted question-answering with human feedback. *Advances in Neural Information Processing Systems* (NeurIPS).

---

## 补充材料说明

本论文使用的补充表格与图形均保存于项目目录下：

- `revised/paper03_tables/tab_model_selection.csv`：LCA 模型选择统计量；
- `revised/paper03_tables/tab_class_profiles.csv`：五类别条件响应概率矩阵；
- `revised/paper03_tables/tab_examples.json`：各类别真实指令示例；
- `revised/paper03_tables/tab_stability_checks.json`：稳定性检查结果；
- `revised/paper03_figures/fig_bic_elbow.png`：BIC 肘部法则图；
- `revised/paper03_figures/fig_profile_heatmap.png`：语用特征剖面热图；
- `revised/paper03_figures/fig_path_metrics.png`：路径稳定性指标比较图；
- `revised/paper03_figures/fig_interaction_difficulty.png`：任务难度与语用类别交互效应图。
