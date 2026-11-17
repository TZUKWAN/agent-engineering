# 论文03：GUI智能体用户提示的语用结构类型学——基于AgentNet数据的潜在类别分析

## 研究背景与问题

现有研究（包括我们自己的前期分析）通常采用两种方式处理用户提示：
1. **加总指标法**：将11个特征简单加总为"显性度分数"（0-11分）— 信息损失严重，异质模式被混为一谈
2. **单特征法**：逐一检验每个特征与结果的关系 — 忽略了特征间的结构共变关系

这两种方法都无法回答一个更根本的问题：**用户的提示表达是否存在可识别的语用结构类型？** 即，不同特征并非独立存在，而是倾向于以特定组合模式出现，形成自然的语用类型。

例如，包含"应用提及"的指令往往也包含"操作对象"和"目标动作"（因为提到某个应用后就自然要说在里边做什么），而单独出现某个特征而没有其他特征配合的类型可能很少见。

本研究从语用类型学的视角出发，使用**潜在类别分析（Latent Class Analysis, LCA）**，在11个二元特征的基础上识别用户提示的语用结构类型，然后考察不同类型在完成率、执行路径、错误模式上的差异。

这一研究的核心价值在于：不假设"显性度是线性的、越高越好"，而是承认存在**多种等价的语用策略**，不同策略在不同任务场景下各有优劣。

## 理论基础

- **语用类型学**（Levinson 2012）：语言使用在不同交际场景中存在系统性的类型差异
- **言语行为分类学**（Searle 1976）：指令类、承诺类、宣告类等不同类型的语用效力不同
- **共同基础理论**（Clark 1996）：不同类型的语用策略在建立共同基础时的效率不同

## 核心假设

| 编号 | 假设 | 预期 |
|------|------|------|
| H1 | 用户提示存在可辨识的语用结构类型（LCA识别出3-5个潜在类别） | 最优模型BIC最低 |
| H2 | 不同类型的任务完成率存在显著差异 | 卡方检验p<0.05 |
| H3 | 不同类型的执行路径（步数、错误模式、冗余模式）存在显著差异 | ANOVA显著 |
| H4 | 特征强度（显性度分数）相同的任务，因语用类型不同，执行结果也不同 | 控制分数后类型仍显著 |
| H5 | 不同类型对任务难度的敏感性不同 | 类型×难度交互显著 |

## 实验设计

### 第一步：潜在类别分析（LCA）

**输入变量**：11个二元特征
- has_application, has_operation_object, has_target_action, has_target_state,
  has_file_reference, has_object_properties, has_operation_order,
  has_multiple_subtasks, has_constraint_words, has_completion_criteria, has_initial_state

**模型选择**：
- 依次拟合1-8个类别的LCA模型
- 使用BIC、AIC、LRT（Lo-Mendell-Rubin似然比检验）确定最佳类别数
- 各模型的熵值（Entropy）>0.8为可接受

**实现方式**（二选一）：
1. 用 `statsmodels` 的 `MixtureModel` 或 `sklearn` 的 `LatentDirichletAllocation` 逼近
2. 用 `poLCA`（R包）通过Rpy2接口调用

**推荐方案**：先用sklearn的GaussianMixture做探索性分析，再用专门的LCA实现做确认性分析。

### 第二步：类别的语用学解释

对识别出的每个潜在类别：
1. 计算11个特征的条件响应概率（profile）
2. 基于特征模式赋予语用学标签
3. 给出典型指令示例

**预期的可能类型**（根据数据探索的预判）：

| 类型 | 特征模式 | 语用标签 |
|------|---------|---------|
| T1 | 高target_action+高operation_object+低其他 | **行动导向型**：只说做什么，不说限制和验证 |
| T2 | 高application+高target_action+高file_reference | **应用操作型**：明确说在哪个应用里操作什么文件 |
| T3 | 高constraint_words+高completion_criteria+高target_state | **约束验证型**：强调限制条件和完成标准 |
| T4 | 高initial_state+高operation_order+高multiple_subtasks | **流程描述型**：详细描述初始状态和操作顺序 |
| T5 | 所有特征平均偏低 | **简洁型**：信息最少的指令 |

### 第三步：不同类型的结果差异分析

**分析方法**：

| 分析 | 方法 |
|------|------|
| 完成率差异 | 卡方检验 + 各类型完成率（含95%CI） |
| 步数差异 | ANOVA / Kruskal-Wallis检验 + 效应量η² |
| 错误比例差异 | ANOVA + 效应量 |
| 冗余比例差异 | ANOVA + 效应量 |
| 多变量差异 | MANOVA（步数、错误、冗余作为联合因变量） |

### 第四步：控制显性度分数后的类型效应

关键检验：**即使显性度分数相同，不同类型的结果也不同？**

方法：
1. 对每个显性度分数水平（0-11分），用卡方检验比较不同类型间的完成率差异
2. 多水平Logistic回归：`task_completed ~ class + explicitness_score + (1|class)` — 看class是否有独立预测力

### 第五步：类型×任务难度的交互

**任务难度操作化**：
- `task_difficulty`列（数据集中已有的评分）
- 或 `word_count` 作为代理变量

**分析**：
```
task_completed ~ class * task_difficulty + explicitness_score
```
看交互项是否显著，以及不同难度下各类型的完成率变化曲线。

### 第六步：执行路径差异的细粒度分析

**路径指标**（需要步骤级数据）：
- 首次错误步骤出现的位置
- 错误集中度（最大连续错误步数）
- 步骤类型转换（正确→错误→正确 的转换频率）
- 验证行为（任务末尾是否出现"check"类步骤）

**分析**：对每个类型，计算上述路径指标，用ANOVA比较。

## 数据需求

- 主数据：`data/processed/analysis_data.parquet`
- 步骤数据：`data/interim/steps.parquet`
- 新生成：LCA模型对象、类别分配结果

## 对论文01和论文02的继承

- 论文01的验证标准类型分类结果可作为论文03中LCA的辅助变量
- 论文02的约束密度变量可作为论文03中类型差异解释的证据

最好等前两篇完成后再执行本论文的分析。

## 结果报告要求

输出到 `results/papers/paper03/` 目录，包含：
1. `01_lca_model_selection.json` — 1-8类模型的拟合优度比较表
2. `02_lca_profiles.json` — 最佳模型的条件响应概率矩阵
3. `03_class_distribution.json` — 各类别的大小、典型指令样本
4. `04_outcome_comparison.json` — 各类别在完成率/步数/错误/冗余上的差异
5. `05_controlled_analysis.json` — 控制显性度分数后的类型效应
6. `06_interaction_analysis.json` — 类型×任务难度的交互
7. `07_path_analysis.json` — 执行路径差异分析
8. `report.md` — 完整结果报告
9. 所有分析代码保存到 `src/paper03/`

## 复现性要求
- 随机种子 `42`
- 代码为 `.py` 文件
- 报告所有模型的BIC、AIC、Entropy、LRT p值
- 类型标签需附带语用学解释说明
