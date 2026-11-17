# 论文02：用户提示中约束密度对GUI智能体执行效能的非线性影响

## 研究背景与问题

前期分析中，`has_constraint_words`（是否有约束词）的效应量为+2.5%（有该特征的完成率81.1% vs 无该特征的78.5%），在所有特征中排第二。但简单的"有vs无"二值化处理掩盖了一个重要的研究问题：**约束到底是越多越好，还是存在一个最优水平？**

从语用学视角看，这是一对经典张力：
- **合作原则的质量/方式准则**（Grice 1975）：提供充分信息、避免模糊 → 约束越细越好
- **关联理论**（Sperber & Wilson 1986）：过多的约束增加智能体的语境处理成本 → 约束存在最优值

从智能体执行视角看：
- **过少约束**（low density）：智能体方向不明 → 探索性操作多、错误率高、冗余步数多
- **适度约束**（optimal density）：既有方向指引又不失灵活 → 效率最高
- **过度约束**（high density）：限制了智能体的路径优化空间、频繁验证约束满足性 → 效率下降

如果这一假设成立，约束密度与任务完成率之间应呈现**倒U形曲线**而非线性关系。

## 理论基础

- **Grice合作原则**（1975）：量的准则（信息量适中）、质的准则（真实）、关系准则（相关）、方式准则（清晰）
- **关联理论**（Sperber & Wilson 1986）：认知代价与语境收益的权衡
- **"过犹不及"假说**（Yeung 2016）：工作指令中信息量过多反而降低执行绩效

## 核心假设

| 编号 | 假设 | 预期 |
|------|------|------|
| H1 | 约束密度与任务完成率呈**倒U形**关系（非线性显著，二次项系数为负） | 二次项显著为负 |
| H2 | 约束密度与执行步数呈**U形**关系（低约束→探索步数多，高约束→验证步数多） | 二次项显著为正 |
| H3 | 约束类型不同，最优密度阈值不同 | 禁止型约束的阈值低于要求型约束 |
| H4 | 任务难度调节约束密度的最优值：简单任务的最佳约束密度低于复杂任务 | 交互项显著 |

## 实验设计

### 第一步：约束词的精细分类标注

**目标**：对6,122条有约束词的任务，进一步分类

**标注方案**：

| 类型 | 定义 | 关键词 |
|------|------|--------|
| **C1-禁止型** | 禁止某些操作/行为 | don't, do not, never, avoid, without, cannot, should not, must not |
| **C2-保留型** | 要求保持/保留某状态 | keep, maintain, stay, preserve, leave |
| **C3-要求型** | 要求必须做某事 | must, should, need to, have to, required |
| **C4-限制型** | 仅限某范围/方式 | only, just, merely, exclusively |
| **C5-混合型** | 同时包含多种约束 | |

**约束密度**：约束词出现总次数 / 指令总词数 × 100（百分比）

**约束丰富度**：不同约束词类型的种类数（1-5）

### 第二步：非线性关系检验

**主模型**：
```
task_completed ~ constraint_density + I(constraint_density²) + task_difficulty + word_count + os
```

**检验标准**：
- 二次项系数显著为负 → 支持倒U形假说
- 计算拐点：`-b₁ / (2×b₂)`
- 检验拐点是否在约束密度的观测范围内（Dawson 2014的U形检验）

### 第三步：约束类型的异质性分析

分别对C1-C4各子类型拟合倒U形模型，比较：
- 各类型是否都呈现倒U形
- 各类型的最优约束密度拐点是否不同
- 各类型的效应量大小排序

### 第四步：任务难度的调节效应

```
task_completed ~ constraint_density * task_difficulty + I(constraint_density²) * task_difficulty
```

- 预期的交互模式：简单任务中，约束密度的负效应更早出现（拐点左移）
- 复杂任务中，约束密度的正效应持续更长（拐点右移）

执行方法：将`has_operation_object`和`word_count`作为任务复杂度的代理变量，进行分样本检验。

### 第五步：稳健性分析

1. **不同约束密度定义**：绝对约束词数 vs 相对密度（除以词数）vs 约束丰富度
2. **排除平台差异**：分别对win_mac和ubuntu子样本检验
3. **非线性检验**：使用限制性立方样条（RCS）替代二次多项式，检验非线性是否稳健
4. **模型比较**：线性模型 vs 二次模型 vs 样条模型，用AIC/BIC比较

## 数据需求

- 主数据：`data/processed/analysis_data.parquet`
- 新增列：
  - `constraint_type`（C1-C5）
  - `constraint_density`（百分比）
  - `constraint_richness`（种类数）
  - `constraint_abs_count`（约束词绝对出现次数）
  - 各子类型的密度列（如`constraint_density_prohibitive`等）

## 结果报告要求

输出到 `results/papers/paper02/` 目录，包含：
1. `01_constraint_distribution.json` — 约束类型的分布、密度描述
2. `02_quadratic_results.json` — 非线性回归结果（含拐点、U形检验）
3. `03_subtype_analysis.json` — 各子类型的异质性分析
4. `04_moderation_analysis.json` — 任务难度的调节效应
5. `05_robustness_check.json` — 稳健性检验结果
6. `model_comparison.csv` — 线性/二次/样条模型的AIC/BIC对比
7. `report.md` — 完整结果报告
8. 所有分析代码保存到 `src/paper02/`

## 复现性要求

- 随机种子 `42`
- 所有代码为 `.py` 文件
- 报告效应量（Cohen's f², R²变化量等）
- 报告拐点及其95%置信区间（Delta method或bootstrap）
