# 执行提示词（发给其他智能体用）

> 以下内容可作为完整提示词，在新建对话窗口中发送给智能体，使用 goal 模式逐篇执行。

---

## 任务概述

现有工作目录：`D:\MATLABINTOKEN`

已有一个完整的AgentNet数据集分析结果：
- **22,811条任务**（17,811 Windows/Mac + 5,000 Ubuntu），**421,453个步骤**
- 数据文件：`data/processed/analysis_data.parquet` + `data/interim/steps.parquet`
- 已提取11个二元显性度特征（has_application, has_target_action 等）+ 过程质量指标

你需要按顺序完成以下**三篇论文**的**实验和结果报告**（不是写论文成文，是做实验出具详细结果报告）。

---

## 通用执行规则（所有论文共享）

1. **输出定位**：所有实验的结果报告输出到 `results/papers/paper{编号}/` 目录
2. **代码定位**：所有实验代码保存到 `src/paper{编号}/` 目录
3. **随机种子**：固定为 `42`
4. **数据加载**：
   ```python
   import pandas as pd
   df = pd.read_parquet('data/processed/analysis_data.parquet')  # 主数据
   steps = pd.read_parquet('data/interim/steps.parquet')         # 步骤数据
   ```
5. **结果格式**：同时输出 `.json`（程序读取用）和 `.csv`（人阅读用）
6. **报告格式**：每个目录下的 `report.md` 需包含：
   - 研究问题和假设简述
   - 方法描述（变量操作化、模型设定）
   - 结果表格（含效应量、置信区间、p值）
   - 稳健性检验
   - 初步结论（3-5条要点）
   - 自身局限性（1-2条）
7. **复现要求**：所有代码可独立运行、随机种子固定

---

## 论文01：验证显性度与执行终止机制

**目标**：分析用户指令中"完成标准/验证方式"的提及如何影响智能体的执行终止行为。

**任务文档**：`tasks/paper01_verification_explicitness.md`

**执行步骤**：

### Step 1：验证标准语言分类标注
- 对 `has_completion_criteria == 1` 的2,869条指令，细分为：
  - V1-动词指令式（check, verify, confirm, validate, ensure, make sure）
  - V2-状态目标式（done, complete, correct, proper, finished, ready）
  - V3-条件验证式（until, when...then, once, after）
  - V4-混合式（同时包含以上）
  - V0-不可分类（伪阳性，手工复核）
- 输出：各类别频数、比例、典型指令样例

### Step 2：验证标准对执行终止的影响
- 因变量：task_completed, total_steps, redundant_ratio, 首次错误位置
- 核心自变量：`has_completion_criteria`（0/1）
- 控制变量：task_difficulty, word_count, os
- 模型：
  - 完成率 → Logistic回归
  - 步数 → 负二项回归
  - 冗余比例 → Tobit回归（若数据0堆积太多则用零膨胀beta回归）

### Step 3：验证表述细化程度的非线性效应
- 自变量：`verification_density` = 验证相关词数 / 总词数
- 模型：`task_completed ~ poly(verification_density, 2) + controls`
- 检验二次项是否显著，判断是否存在倒U形

### Step 4：验证标准位置分析
- 将指令分为【开头25% | 中间50% | 末尾25%】三段
- 定位验证关键词出现的区段
- 比较不同位置的完成率差异

**交付物清单**：
- [ ] `src/paper01/` — 所有分析代码
- [ ] `results/papers/paper01/01_feature_distribution.json`
- [ ] `results/papers/paper01/02_logistic_results.json`
- [ ] `results/papers/paper01/03_step_count_results.json`
- [ ] `results/papers/paper01/04_nonlinear_results.json`
- [ ] `results/papers/paper01/05_position_analysis.json`
- [ ] `results/papers/paper01/report.md` — 完整结果报告

---

## 论文02：约束密度的非线性效应

**目标**：检验用户指令中的约束密度与执行效能是否存在倒U形关系。

**任务文档**：`tasks/paper02_constraint_density.md`

**执行步骤**：

### Step 1：约束词精细分类与密度计算
- 关键词列表：
  - C1-禁止型：don't, do not, never, avoid, without, cannot, should not, must not
  - C2-保留型：keep, maintain, stay, preserve, leave
  - C3-要求型：must, should, need to, have to, required
  - C4-限制型：only, just, merely, exclusively
  - C5-混合型（包含两种及以上）
- 计算：
  - 约束词绝对出现次数
  - **约束密度** = 约束词总次数 / 总词数 × 100
  - **约束丰富度** = 不同约束词类型的种类数

### Step 2：倒U形假说检验
- 模型：`task_completed ~ constraint_density + I(constraint_density²) + controls`
- 关键检验：
  - 二次项系数显著为负
  - 拐点位置 = -b₁ / (2×b₂) 在密度观测范围内
  - Dawson (2014) U形检验
- 对比线性模型 vs 二次模型（AIC/BIC）

### Step 3：约束类型异质性
- 分别对C1-C4各子类型拟合Step2的模型
- 比较各类型的最优拐点是否不同

### Step 4：任务难度调节效应
- 将 task_difficulty（或 word_count）作为调节变量
- 检验密度×难度、密度²×难度的交互项

### Step 5：稳健性检验
- 替换密度定义为：绝对词数、丰富度
- 分平台（win_mac / ubuntu）子样本检验
- 用限制性立方样条（RCS，3个节点）替代二次多项式

**交付物清单**：
- [ ] `src/paper02/` — 所有分析代码
- [ ] `results/papers/paper02/01_constraint_distribution.json`
- [ ] `results/papers/paper02/02_quadratic_results.json`（含拐点、U形检验）
- [ ] `results/papers/paper02/03_subtype_analysis.json`
- [ ] `results/papers/paper02/04_moderation_analysis.json`
- [ ] `results/papers/paper02/05_robustness_check.json`
- [ ] `results/papers/paper02/model_comparison.csv`
- [ ] `results/papers/paper02/report.md`

---

## 论文03：提示表达的语用结构类型学

**目标**：用潜在类别分析（LCA）识别用户提示的语用结构类型，并比较不同类型的执行路径差异。

**任务文档**：`tasks/paper03_pragmatic_typology.md`

**注意**：建议在前两篇完成后执行，因为其结果可为变量选择提供依据。

### Step 1：潜在类别分析
- 输入变量：11个二元特征
- 拟合1-8个类别的LCA模型
- 模型选择：BIC最低 + Entropy>0.8 + LRT显著
- 实现：先用 `sklearn.mixture.GaussianMixture` 探索，再尝试专用LCA实现（statsmodels或R-poLCA）

### Step 2：类别特征描述与语用标签
- 打印每个类别的条件响应概率矩阵
- 基于特征模式给出语用学标签（如"行动导向型"、"约束验证型"等）
- 每个类别列出2-3条典型指令样本

### Step 3：不同类型的结果差异
- 完成率：卡方检验 + 各类型的完成率（95%CI）
- 步数/错误比例/冗余比例：ANOVA/Kruskal-Wallis + η²效应量
- MANOVA：联合检验

### Step 4：控制显性度分数后的类型效应
- 在每个显性度分数水平（0-11分）内，比较不同类型间的完成率
- 多水平Logistic回归：`task_completed ~ class + explicitness_score`
- 核心问题：即使分数相同，类型不同结果也不同？

### Step 5：类型×任务难度交互
- `task_completed ~ class * task_difficulty`
- 看不同难度下各类型的完成率变化曲线

### Step 6：执行路径细粒度分析（需步骤数据）
- 为每个类型计算：首次错误位置、最大连续错误步数、步骤转换频率
- 用ANOVA/卡方检验比较

**交付物清单**：
- [ ] `src/paper03/` — 所有分析代码
- [ ] `results/papers/paper03/01_lca_model_selection.json`
- [ ] `results/papers/paper03/02_lca_profiles.json`
- [ ] `results/papers/paper03/03_class_distribution.json`
- [ ] `results/papers/paper03/04_outcome_comparison.json`
- [ ] `results/papers/paper03/05_controlled_analysis.json`
- [ ] `results/papers/paper03/06_interaction_analysis.json`
- [ ] `results/papers/paper03/07_path_analysis.json`
- [ ] `results/papers/paper03/report.md`

---

## 执行流程建议

```
论文01（验证显性度）→ 论文02（约束密度）→ 论文03（语用类型学）
     ↓                     ↓
 结果给论文03参考    结果给论文03参考
```

### 每篇论文的完成标准

**只有当你满足以下条件时，才算完成一篇论文的实验：**

1. ✅ 所有分析代码已保存到 `src/paper{编号}/`
2. ✅ 所有数值结果已保存到 `results/papers/paper{编号}/`
3. ✅ `report.md` 已撰写完成，包含：
   - 完整的方法描述（变量操作化、样本量、模型设定）
   - 完整的统计结果（含效应量、置信区间）
   - 稳健性检验至少1种
   - 初步结论3-5条
   - 自身局限性1-2条
   - 下一步建议（给下一篇论文的参考）
4. ✅ 代码可以重新运行且结果可复现

**不要**在此阶段撰写正式论文文本，**只需要**出具详细的结果报告。
