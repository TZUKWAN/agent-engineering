# 论文B：用户指令中的边界性言语行为对智能体执行效能的影响

## 来源
研究1（验证显性度）+ 研究2（约束密度）融合

## 核心理论框架

将验证标准和约束词统一到**"边界性言语行为"**概念下：
- **验证标准 = 终止边界**（"做到什么程度算完"）— 规定任务的终点
- **约束词 = 行动边界**（"不能做什么/必须保持什么"）— 规定行动的禁区

两者都是用户通过言语行为给智能体设定边界的语用策略。

### 理论依据
- **言语行为理论**（Austin 1962, Searle 1969）：验证和约束都是指令类言语行为的边界设定功能
- **关联理论**（Sperber & Wilson 1986/1995）：边界信息降低智能体的语境推断成本
- **认知负荷理论**（Sweller 1988）：约束过多增加工作记忆负荷
- **行动终止理论**（Anderson 2002）：明确的终止条件减少过冲行为

## 优化要点

### Step 0：数据准备

**输入数据**：
- `data/processed/analysis_data.parquet`（22,811条任务）
- 删除 `task_completed` 缺失的2,327条 → 回归样本 N≈20,484

**输出**：`results/optimization/paperB/00_sample_info.json`

### Step 1：修复研究1的验证类型分类

**问题**：原V1-V4四分类中，V2（状态目标式）仅5条，V3（条件验证式）仅1条，分布严重失衡，H2无法检验。

**方案**：放弃四分类，改为**二分 + 连续**设计：

| 变量 | 类型 | 操作化 |
|------|------|--------|
| `has_completion_criteria` | 二分（0/1） | 原有特征 |
| `verification_density` | 连续 | 验证相关词数（check/verify/confirm/ensure/make sure/done/complete/correct） / 总词数 × 100 |
| `verification_richness` | 计数 | 不同验证词的种类数（1-8） |

**新增分析**：验证密度的描述统计、分布图、与word_count的相关（检验是否只是指令长度的代理变量）

**输出**：
- `01_verification_features.json`
- `01_verification_distribution.csv`
- `fig1_verification_density_histogram.png`

### Step 2：约束词精细分类与密度计算

**约束词四分类**（基于语用学情态系统）：

| 类型 | 情态范畴 | 关键词 |
|------|---------|--------|
| **C1-禁止型** | 道义情态-禁止 | don't, do not, never, avoid, without, cannot, should not, must not |
| **C2-保留型** | 道义情态-保留 | keep, maintain, stay, preserve, leave |
| **C3-要求型** | 道义情态-义务 | must, should, need to, have to, required |
| **C4-限制型** | 认知情态-限定 | only, just, merely, exclusively |

**计算变量**：
- `constraint_density` = 约束词总次数 / 总词数 × 100
- `constraint_richness` = 不同约束类型的种类数（0-4）
- 各子类型密度：`constraint_density_prohibitive` 等

**输出**：
- `02_constraint_features.json`
- `02_constraint_distribution.csv`
- `fig2_constraint_type_distribution.png`

### Step 3：验证的效应分析（原研究1核心）

**假设体系**（重新表述）：
- H1a：有验证标准的任务完成率更高（Logistic回归，OR）
- H1b：有验证标准的任务执行步数更少（负二项回归，IRR）
- H1c：有验证标准的任务终止阶段冗余更低（终止阶段指标比较）
- H2：验证密度与完成率呈线性正相关（非线性检验，预期不显著）
- H3：验证表述位置不影响效果（探索性，三组比较）

**模型设定**：
```
# H1a: Logistic
task_completed ~ has_completion_criteria + task_difficulty + word_count + C(os)

# H1b: 负二项回归 NB2
total_steps ~ has_completion_criteria + task_difficulty + word_count + C(os)

# H1c: 终止阶段比较
终止阶段定义：每个任务最后25%的步骤
比较指标：最后25%步的冗余比例、错误比例、异常短轨迹率

# H2: 非线性检验（仅对有验证标准的子样本）
task_completed ~ verification_density + I(verification_density²) + controls
似然比检验：线性vs二次模型

# H3: 位置分析（仅对可定位验证关键词的子样本）
分三组：开头25% / 中间50% / 末尾25%
卡方检验比较三组完成率
```

**控制变量**：task_difficulty（连续）、word_count（连续）、os（分类：ubuntu/win_mac）

**报告要求**：每个假设明确标注"支持/不支持/部分支持"，报告效应量（OR/IRR/Cohen's d）及95% CI

**输出**：
- `03_logistic_verification.json` + `.csv`
- `04_negative_binomial_verification.json` + `.csv`
- `05_terminal_phase_comparison.json` + `.csv`
- `06_nonlinear_verification.json` + `.csv`
- `07_position_analysis.json` + `.csv`
- `fig3_forest_plot_logistic.png`
- `fig4_forest_plot_nb.png`

### Step 4：约束的效应分析（原研究2核心）

**假设体系**：
- H4：有约束词的任务完成率更高（Logistic回归）
- H5：约束密度不存在全局倒U形（二次项不显著）
- H6：约束密度的倒U形效应受任务难度调节（交互项显著）
- H7：约束密度的倒U形效应受指令长度调节
- H8：约束密度的倒U形效应受子任务数量调节
- H9：不同约束子类型的最优密度不同（探索性）

**模型设定**：
```
# H4: Logistic（完整样本）
task_completed ~ has_constraint_words + task_difficulty + word_count + C(os)

# H5: 全局倒U形（约束任务子样本）
task_completed ~ constraint_density + I(constraint_density²) + controls
Dawson (2014) U形检验：观测区间两端斜率

# H6-H8: 条件模型
task_completed ~ constraint_density * moderator + I(constraint_density²) * moderator + controls
moderator 分别为：task_difficulty / word_count / has_multiple_subtasks

# H9: 子类型异质性
对C1-C4分别拟合二次模型，比较拐点
```

**稳健性检验**：
- 用限制性立方样条（RCS，3节点）替代二次多项式
- 分平台（win_mac / ubuntu）子样本
- 替代密度定义（绝对词数 vs 相对密度 vs 丰富度）
- 替代因变量（总步数、冗余步数比）

**输出**：
- `08_logistic_constraint.json` + `.csv`
- `09_quadratic_global.json` + `.csv`（含Dawson检验）
- `10_moderation_analysis.json` + `.csv`（难度/长度/子任务三个调节变量）
- `11_subtype_analysis.json` + `.csv`
- `12_robustness_check.json` + `.csv`（RCS + 分平台 + 替代定义）
- `model_comparison.csv`（线性/二次/RCS的AIC/BIC）
- `fig5_constraint_curves_by_difficulty.png`
- `fig6_subtype_forest_plot.png`

### Step 5：验证 vs 约束的直接对比

**这是融合后的新增分析，原研究1和研究2没有做**

| 分析 | 方法 |
|------|------|
| 两者联合预测力 | Logistic: task_completed ~ has_completion_criteria + has_constraint_words + 交互项 + controls |
| 边际贡献比较 | 嵌套模型似然比检验：仅验证 vs 仅约束 vs 两者 |
| 协同效应 | 交互项 OR 是否显著偏离1 |
| 不同难度下的相对重要性 | 分难度子样本，比较两者的标准化系数 |

**输出**：
- `13_combined_model.json` + `.csv`
- `14_marginal_contribution.json` + `.csv`
- `15_difficulty_specific_effects.json` + `.csv`
- `fig7_combined_effects.png`

### Step 6：认知负荷的理论解释（新增）

为H6-H8的条件性倒U形提供理论解释，需要：

1. **引用认知负荷理论**（Sweller 1988）：约束占用工作记忆资源
2. **引用工作记忆容量**（Baddeley 2000）：高难度任务本身已占用较多容量，约束的边际负荷更容易超载
3. **构建"约束认知预算"假说**：每个任务有一个约束处理预算，难度越高预算越小，越早达到过载拐点

**输出**：这部分写入论文讨论部分，不单独输出文件。

### Step 7：效度验证（不做人工标注）

**聚合效度**：
- has_completion_criteria 应该与 verification_density 显著正相关
- has_constraint_words 应该与 constraint_density 显著正相关

**区分效度**：
- has_completion_criteria 与 has_constraint_words 的相关不应过高（r < 0.5）
- 如果过高，说明两者测的是同一个构念，需合并

**已知群组效度**：
- 高难度任务的约束效应应该更强（已在H6检验）
- 有完成标准的任务步数应该更少（已在H1b检验）

**输出**：
- `16_validity_check.json` + `.csv`
- `fig8_correlation_matrix.png`

## 论文结构建议

```
1. 引言（终止边界与行动边界的语用学统一）
2. 理论框架与假设
   2.1 边界性言语行为的定义
   2.2 验证（终止边界）的假设 H1-H3
   2.3 约束（行动边界）的假设 H4-H9
3. 数据与方法
   3.1 数据来源（AgentNet，N=20,484）
   3.2 变量操作化
   3.3 统计模型
4. 结果
   4.1 验证的效应（H1-H3）
   4.2 约束的效应（H4-H9）
   4.3 验证与约束的对比
   4.4 效度验证
5. 讨论
   5.1 边界性言语行为的双重功能
   5.2 条件性倒U形的认知负荷解释
   5.3 实践启示
6. 局限与展望
```

## 完成标准

- [ ] 所有Step 0-7的分析代码保存到 `src/optimization/paperB/`
- [ ] 所有JSON/CSV结果保存到 `results/optimization/paperB/`
- [ ] 所有图表保存到 `results/optimization/paperB/`
- [ ] `report.md` 撰写完成，包含所有假设的检验结果、效应量、稳健性检验
- [ ] 效度验证完成
