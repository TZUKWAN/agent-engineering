# 论文A：任务型智能体用户指令的语用结构类型——基于AgentNet数据的潜在类别分析

## 来源
研究3（语用结构类型学），但全面升级方法论

## 核心问题

1. 用户指令是否存在可识别的语用结构类型？
2. 不同类型在执行路径稳定性和任务完成率上是否存在系统差异？
3. 语用类型对结果的预测力是否独立于线性显性度评分？
4. 任务难度是否调节语用类型的效应？

## 优化要点（相比原研究的三大升级）

### 升级一：特征从关键词匹配升级为句法/语用特征

**问题**：原研究的11个特征全是关键词匹配，审稿人会质疑"这是语言学还是字符串查找？"

**方案**：用spaCy（en_core_web_lg模型）对每条指令进行NLP分析，提取有语法依据的特征。

#### Step 1：句法/语用特征提取

**输入**：`data/processed/analysis_data.parquet` 的 `instruction` 列

**工具**：spaCy + en_core_web_lg

**提取的特征体系**（每个特征都有明确的语言学依据）：

| # | 特征 | 提取方法 | 语言学依据 |
|---|------|---------|-----------|
| 1 | `imperative_verb_count` | POS=VERB且为句子根节点（spaCy dep=='ROOT'） | 言语行为：指令类 |
| 2 | `modal_obligation_count` | 依存分析：aux指向VERB，且词为must/should/need/have to | 情态系统：道义情态-义务 |
| 3 | `modal_prohibition_count` | 否定标记（neg）+ 助动词 | 情态系统：道义情态-禁止 |
| 4 | `declarative_predicate_count` | 动词为check/verify/confirm/test/validate/ensure | 言语行为：宣告类（终止判准） |
| 5 | `perfective_aspect_count` | 时态标签为完成体（has/have + VBD） | 时体系统：完成体 |
| 6 | `discourse_temporal_count` | 依存标记为mark/advmod，词为then/next/after/before/finally/first | 篇章分析：时序关系 |
| 7 | `object_argument_count` | 语义角色标注中的PATIENT/THEME角色数 | 论元结构：受事 |
| 8 | `t_unit_count` | T单位数（主句+其嵌入从句） | 句法复杂性 |
| 9 | `clause_density` | 从句数 / T单位数 | 句法复杂性 |
| 10 | `dependency_tree_depth` | 依存树的最大深度 | 句法复杂性：层级性 |
| 11 | `noun_entity_count` | 命名实体数（spaCy NER） | 实体指称密度 |

**同时保留原有的11个关键词特征**（用于效度对比）。

**输出**：
- `01_syntactic_features.parquet`（新增的句法特征）
- `01_feature_extraction_report.json`（提取成功率、分布统计）
- 代码：`src/optimization/paperA/01_extract_syntactic_features.py`

#### Step 2：聚合效度与区分效度检验

**目的**：证明新的句法特征确实捕捉到了语用学构念，而不是噪音。

**聚合效度**（理论上应该相关的特征对）：
- `imperative_verb_count` vs 原有 `has_target_action` → 应正相关
- `declarative_predicate_count` vs 原有 `has_completion_criteria` → 应正相关
- `modal_obligation_count` + `modal_prohibition_count` vs 原有 `has_constraint_words` → 应正相关

**区分效度**（理论上不相关的特征对）：
- `perfective_aspect_count` vs `modal_obligation_count` → 应低相关
- `dependency_tree_depth` vs `declarative_predicate_count` → 应低相关

**输出**：
- `02_validity_correlation_matrix.csv`
- `02_validity_summary.json`
- `fig1_validity_heatmap.png`

### 升级二：LCA用标准工具重跑

**问题**：原研究用自定义EM算法，缺少Lo-Mendell-Rubin检验和Bootstrap置信区间。

**方案**：用R的poLCA包重跑（通过rpy2调用，或直接生成R脚本）

#### Step 3：潜在类别分析（标准工具）

**输入特征**：Step 1提取的11个句法特征（标准化后）

**模型选择**：
```
拟合 k=1 到 k=8 的LCA模型
模型选择标准：
  - BIC（主要标准，肘部法则）
  - AIC（参考）
  - Lo-Mendell-Rubin LRT检验（p<.05支持k类优于k-1类）
  - 熵值（Entropy > 0.8 为可接受）
  - 最小类别占比（>5% 避免过细分类）
```

**实现方式**（按优先级）：
1. **首选**：R的poLCA包（通过rpy2或写R脚本）
2. **备选**：Python的sklearn.mixture.GaussianMixture（对二分数据是近似，需在论文中说明）
3. **补充**：如果只能用Python近似，需要做额外的Bootstrap稳定性检验（至少100次）

**稳定性检验**：
- Bootstrap重采样100次，每次重跑LCA，计算类别标签的一致性（Adjusted Rand Index）
- 训练-测试集分割（80/20），在训练集拟合，预测测试集类别，计算一致性

**输出**：
- `03_lca_model_selection.json`（k=1-8的BIC/AIC/Entropy/LRT）
- `03_lca_profiles.csv`（最佳模型的条件响应概率矩阵）
- `03_lca_stability.json`（Bootstrap ARI、训练-测试一致性）
- `fig2_bic_elbow.png`
- `fig3_profile_heatmap.png`

#### Step 4：类别标签与语用学解释

对识别出的每个类别：
1. 计算句法特征的条件均值（profile）
2. 基于特征模式赋予语用学标签
3. 列出2-3条真实指令示例（从数据中直接抽取）

**预期可能的类型**（基于原研究发现的5类，但用句法特征重新识别可能变化）：
- 行动导向型（高imperative_verb，低modal）
- 约束主导型（高modal_obligation + modal_prohibition）
- 验证导向型（高declarative_predicate）
- 复杂层级型（高clause_density + dependency_depth）
- 简洁型（所有特征低）

**注意**：不预设类型数量和标签，让数据说话。如果新特征跑出的类型和原来不同，如实报告。

**输出**：
- `04_class_labels.json`
- `04_class_examples.csv`（各类别的真实指令示例）
- `fig4_class_distribution.png`

### 升级三：路径稳定性的构念效度验证

**问题**：原研究提出"路径稳定性"作为核心指标，但没有验证这个构念的有效性。

#### Step 5：路径稳定性指标的计算与验证

**路径稳定性指标**（从步骤数据计算）：
- `max_consecutive_errors`：最长连续错误步数
- `transition_count`：正确↔错误的转换次数
- `transition_rate`：转换次数 / 总步数

**构念效度验证**（已知群组效度）：
- 理论预期1：高难度任务的路径稳定性应该更低
- 理论预期2：未完成任务比已完成任务的路径稳定性更低
- 理论预期3：效率评分高的任务路径稳定性应该更高

如果三个预期都成立，说明路径稳定性是一个有效的构念。

**输出**：
- `05_path_stability_validity.json`
- `05_path_stability_descriptives.csv`
- `fig5_path_stability_by_difficulty.png`

### Step 6：不同类型的结果差异分析

**分析方法**：

| 指标 | 方法 | 效应量 |
|------|------|--------|
| 完成率 | 卡方检验 | Cramer's V |
| 步数 | Kruskal-Wallis | ε² |
| 错误比例 | Kruskal-Wallis | ε² |
| 冗余比例 | Kruskal-Wallis | ε² |
| 路径稳定性（3指标） | MANOVA | Wilks' λ, η² |
| 联合差异 | MANOVA（多因变量） | Wilks' λ |

**输出**：
- `06_outcome_comparison.json` + `.csv`
- `fig6_completion_rate_by_class.png`
- `fig7_path_stability_by_class.png`

### Step 7：控制显性度后的独立效应

**核心检验**：即使显性度分数相同，不同类型的完成率也不同？

**模型**：
```
# Logistic回归
task_completed ~ C(class) + explicitness_score + controls

# 似然比检验：加入class是否显著提升模型
# 对比：仅explicitness_score vs explicitness_score + class
```

**输出**：
- `07_controlled_analysis.json`（似然比检验、各类别OR）
- `07_coefficients.csv`

### Step 8：任务难度的调节效应

**模型**：
```
task_completed ~ C(class) * task_difficulty + explicitness_score + controls
```

**输出**：
- `08_interaction_analysis.json`
- `08_predicted_curves.csv`（各难度水平下各类别的预测完成率）
- `fig8_interaction_plot.png`

### Step 9：稳健性检验

1. **分平台**：win_mac和ubuntu子样本分别跑LCA，看类型结构是否一致
2. **特征集对比**：用句法特征 vs 用原关键词特征 vs 两者结合，比较LCA结果差异
3. **样本量敏感性**：随机抽取50%、70%子样本重跑LCA

**输出**：
- `09_robustness_check.json`
- `09_cross_platform_lca.json`

## 论文结构建议

```
1. 引言
   1.1 从"显性度高低"到"语用结构类型"
   1.2 现有研究的局限：关键词匹配与简单加总
2. 理论框架
   2.1 语用类型学与言语行为分类学
   2.2 共同基础理论与指令理解
   2.3 路径稳定性作为执行质量指标
3. 数据与方法
   3.1 数据来源（AgentNet, N=20,484）
   3.2 句法/语用特征提取（spaCy）
   3.3 效度验证设计
   3.4 潜在类别分析（poLCA）
   3.5 路径稳定性指标
4. 结果
   4.1 特征效度验证
   4.2 LCA模型选择与类型识别
   4.3 语用类型的执行效应
   4.4 控制显性度后的独立效应
   4.5 任务难度的调节
   4.6 稳健性检验
5. 讨论
   5.1 语用结构类型的理论意义
   5.2 完成率与路径稳定性的脱耦
   5.3 方法学贡献：从关键词到句法特征
6. 局限与展望
```

## 完成标准

- [ ] spaCy句法特征提取代码完成且可运行
- [ ] 效度检验结果合理（聚合效度正相关，区分效度低相关）
- [ ] LCA用标准工具（poLCA或带Bootstrap的GMM）完成
- [ ] 路径稳定性的构念效度通过验证
- [ ] 所有结果保存到 `results/optimization/paperA/`
- [ ] `report.md` 撰写完成
