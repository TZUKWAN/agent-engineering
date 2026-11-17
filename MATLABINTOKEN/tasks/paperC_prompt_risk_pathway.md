# 论文C：提示风险如何通过推理-指令对齐度影响任务结果

## 来源
研究5（风险传导路径）+ 研究4（推理链类型）融合

## 核心问题

1. 用户提示中的哪些语用风险特征最容易诱发推理-指令对齐度低下？
2. 推理-指令对齐度是否与执行错误相关？
3. 提示风险是否通过对齐度→执行错误的间接路径影响任务结果？
4. 提示风险是否诱发不同类型的显式推理链（研究4的4种类型）？

## 核心改造（相比原研究的三大修复）

### 改造一：修复循环论证（最关键）

**原研究问题**：reasoning_error_index 包含了用因变量（task_completed）定义的指标：
- "提前完成判断" = 任务失败 且 推理含终止词 → 用了task_completed
- "失败终止" = task_completed=False → 直接用了因变量
- "错后未修正" = 存在错误步骤 但 无自我修正 → 用了步骤标签
- "重复策略" = 存在错误步骤 且 动作重复 → 用了步骤标签

**修复方案**：剔除所有包含因变量的指标，只用**纯文本特征**构建对齐度指标。

#### Step 1：构建推理-指令对齐度指标（全新设计）

**核心概念重新定义**：

不再叫"推理错误"（暗示知道真实思维），改叫**"推理-指令对齐度"（reasoning-instruction alignment）**——纯文本可观察的概念，指智能体的显式推理文本在多大程度上覆盖了用户指令中的关键要素。

**对齐度指标**（全部基于纯文本匹配，不使用task_completed或步骤标签）：

| 指标 | 定义 | 计算逻辑 |
|------|------|---------|
| `constraint_alignment` | 约束对齐度 | 指令含约束词时，推理文本是否也提及约束（0/1） |
| `verification_alignment` | 验证对齐度 | 指令含完成标准时，推理文本是否含验证词（0/1） |
| `decomposition_alignment` | 分解对齐度 | 指令含多子任务时，推理文本是否含分解词（0/1） |
| `object_alignment` | 对象对齐度 | 指令中的关键名词是否在推理文本中出现 |
| `assumption_without_verification` | 假设无验证 | 推理文本含假设词（assume/suppose/might）但无验证词 |

**总对齐度**：
- `alignment_score` = 上述各对齐指标之和（越高越好）
- `misalignment_score` = 理论应有的对齐数 - 实际对齐数（越高越差）

**关键**：这些指标完全基于指令文本和推理文本的比对，**不使用任何结果变量**。

**输入数据**：
- `data/interim/paper04/steps.parquet`（含thought/reflection字段）
- `data/processed/analysis_data.parquet`（含指令特征）

**输出**：
- `01_alignment_features.parquet`
- `01_alignment_descriptives.json`
- `fig1_alignment_distribution.png`

### 改造二：研究4的推理链类型作为前因变量融入

#### Step 2：推理链类型与提示风险的关联

**原研究4发现**了4种推理链类型（结构化分解型、简洁直觉型、详细展开型、常规综合型）。

**融合方式**：检验不同提示风险是否诱发不同类型的推理链。

**已有数据**：
- `data/interim/paper04/reasoning_features_typed.parquet`（含reasoning_type标签）

**分析**：
```
# 卡方检验：提示风险（高/低）× 推理链类型（4类）
# Logistic多项回归：提示风险特征 → 推理链类型
# 预期：完成标准缺失 → 更可能产生"简洁直觉型"
```

**输出**：
- `02_risk_to_reasoning_type.json`（卡方 + 多项Logistic）
- `fig2_risk_reasoning_heatmap.png`

### 改造三：重建无循环的中介路径

#### Step 3：提示风险 → 对齐度 的OLS回归

**模型**：
```
misalignment_score ~ risk_index + task_difficulty + word_count + C(os)
```

**单项风险分析**（逐个检验10项风险特征与对齐度的关联）：
```
misalignment_score ~ risk_feature_i + controls（对每个i）
```

**预期发现**：
- 完成标准缺失 → 验证对齐度低
- 约束缺失 → 约束对齐度低
- 多子任务无顺序 → 分解对齐度低

**输出**：
- `03_risk_to_alignment.json` + `.csv`
- `fig3_single_risk_effects.png`

#### Step 4：对齐度 → 执行错误 的OLS回归

**执行错误指标**（这些可以使用步骤标签，因为它们是"执行错误"而非"推理错误"）：
- `execution_error_index` = incorrect_ratio + redundant_ratio（连续）
- 或分别用 incorrect_ratio 和 redundant_ratio

**模型**：
```
execution_error_index ~ misalignment_score + risk_index + task_difficulty + word_count + C(os)
```

**关键检验**：控制对齐度后，提示风险的直接效应是否减弱（暗示中介效应）。

**输出**：
- `04_alignment_to_execution.json` + `.csv`

#### Step 5：对齐度/执行错误 → 任务完成 的Logistic回归

**模型**：
```
task_completed ~ misalignment_score + execution_error_index + risk_index + controls
```

**输出**：
- `05_errors_to_completion.json` + `.csv`
- `fig4_or_forest_plot.png`

#### Step 6：Bootstrap顺序中介分析

**路径**：
```
提示风险 → 推理-指令对齐度 → 执行错误 → 任务完成
```

**方法**：
- Bootstrap抽样2000次（原研究只做了500次，需要增加）
- 报告间接效应均值、95% CI、直接效应
- 分别检验每条具体路径（如：完成标准缺失 → 验证对齐度 → 执行错误 → 完成）

**输出**：
- `06_mediation_analysis.json`
- `fig5_pathway_diagram.png`

### Step 7：推理链类型的调节效应（新增）

**研究问题**：不同推理链类型下，对齐度→执行错误的路径强度是否不同？

**模型**：
```
execution_error_index ~ misalignment_score * C(reasoning_type) + controls
```

**预期**：简洁直觉型中，对齐度低的负面影响可能更强（因为推理链本身就短，对齐度低更致命）。

**输出**：
- `07_moderation_by_reasoning_type.json`
- `fig6_moderation_plot.png`

### Step 8：稳健性检验

1. **替代对齐度定义**：用二元对齐（0/1）vs 连续对齐（词重叠比例）
2. **分平台**：win_mac和ubuntu子样本
3. **排除异常值**：排除步数>100的极端任务
4. **替代中介方法**：除了Bootstrap，用KHB方法（Karlson-Holm-Breen）交叉验证

**输出**：
- `08_robustness_check.json`

### Step 9：效度验证

**对齐度指标的已知群组效度**：
- 理论预期1：对齐度高的任务，完成率应该更高
- 理论预期2：对齐度高的任务，执行错误应该更少
- 理论预期3：难度高的任务，对齐度可能更低（因为任务复杂更难对齐）

**输出**：
- `09_alignment_validity.json`

## 论文结构建议

```
1. 引言
   1.1 从"提示质量打分"到"失败路径分析"
   1.2 推理-指令对齐度的概念引入
2. 理论框架
   2.1 提示风险的语用学含义
   2.2 推理-指令对齐度：连接提示与行动的中间层
   2.3 显式推理链类型的调节作用
   2.4 假设体系（H1-H7）
3. 数据与方法
   3.1 数据来源
   3.2 提示风险特征
   3.3 推理-指令对齐度指标（纯文本构建）
   3.4 执行错误指标
   3.5 统计模型（OLS + Logistic + Bootstrap中介）
4. 结果
   4.1 提示风险对推理链类型的影响
   4.2 提示风险 → 对齐度
   4.3 对齐度 → 执行错误
   4.4 执行错误 → 任务完成
   4.5 中介路径分析
   4.6 推理链类型的调节效应
   4.7 稳健性检验
5. 讨论
   5.1 为什么总效应不显著但间接效应显著
   5.2 推理-指令对齐度作为过程诊断指标
   5.3 对齐研究4的推理链类型学
   5.4 实践启示：高风险提示的交互性补救
6. 局限与展望
```

## 完成标准

- [ ] 循环论证指标全部剔除，对齐度指标只用纯文本特征
- [ ] Bootstrap中介分析至少2000次抽样
- [ ] 推理链类型作为调节变量融入
- [ ] 稳健性检验至少3种
- [ ] 对齐度指标的效度验证通过
- [ ] 所有结果保存到 `results/optimization/paperC/`
- [ ] `report.md` 撰写完成

## 注意事项

1. **核心红线**：构建对齐度指标时，**绝对不能**使用 task_completed、last_step_correct、last_step_redundant 任何结果变量。只能用指令文本和推理文本的对比。
2. **概念定位**：全文用"推理-指令对齐度"替代"推理错误"，避免暗示知道模型真实思维。
3. **数据口径**：需要同时用 analysis_data.parquet（指令层）和 paper04/steps.parquet（推理文本层），通过task_id关联。
