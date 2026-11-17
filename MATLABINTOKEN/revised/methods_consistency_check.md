# 方法一致性检查报告

## 1. 数据来源一致性

| 项目 | Paper 01 | Paper 02 | Paper 03 |
|------|----------|----------|----------|
| 数据集 | AgentNet GUI 交互轨迹 | AgentNet GUI 交互轨迹 | AgentNet GUI 交互轨迹 |
| 主数据文件 | `data/processed/analysis_data.parquet` | `data/processed/analysis_data.parquet` | `data/processed/analysis_data.parquet` |
| 步骤数据文件 | `data/interim/steps.parquet` | 未使用 | `data/interim/steps.parquet` |
| 原始样本量 | 22,811 | 22,811 | 22,811 |
| 回归/分析样本量 | 20,484 | 20,484 | 20,484 |
| 删除原因 | 关键变量缺失（task_completed、task_difficulty、word_count 等） | 关键变量缺失 | 关键结果变量缺失 |
| 操作平台分布 | win_mac / ubuntu | win_mac / ubuntu | win_mac / ubuntu |

**一致性结论**：三篇论文使用同一原始数据，主分析样本量一致，均为 20,484。

## 2. 变量命名与操作化一致性

### 2.1 共享变量

| 变量名 | 定义 | 使用论文 |
|--------|------|----------|
| `task_completed` | 任务是否完成（0/1） | 三篇共用 |
| `task_difficulty` | 任务难度评分（1–10） | 三篇共用 |
| `word_count` | 指令词数 | 三篇共用 |
| `os` | 操作系统（ubuntu / win_mac） | 三篇共用 |
| `total_steps` | 总执行步数 | 三篇共用 |
| `incorrect_ratio` | 错误步数占比 | 三篇共用 |
| `redundant_ratio` | 冗余步数占比 | 三篇共用 |
| `explicitness_score` | 11 个二元特征之和 | Paper 03 / Paper 01 |

### 2.2 论文特定变量

| 论文 | 核心变量 | 操作化方式 |
|------|----------|------------|
| Paper 01 | `has_completion_criteria` | 是否包含完成标准/验证条件（0/1） |
| Paper 01 | `verification_type` | V0–V4 分类：动词式/状态式/条件式/混合/不可分类 |
| Paper 01 | `verification_density` | 验证相关词数 / 总词数 |
| Paper 01 | `verification_position` | 开头 / 中间 / 末尾（按字符比例） |
| Paper 02 | `has_constraint_words` | 是否包含约束关键词（0/1） |
| Paper 02 | `constraint_type` | C1–C5：禁止/保留/要求/限制/混合 |
| Paper 02 | `constraint_density` | 约束词总频次 / 总词数 × 100（%） |
| Paper 02 | `constraint_richness` | 出现的不同约束类型数（1–4） |
| Paper 03 | `class`（LCA 类别） | 基于 11 个二元特征的潜类别分配 |

## 3. 样本量口径对照

| 样本口径 | Paper 01 | Paper 02 | Paper 03 |
|----------|----------|----------|----------|
| 原始任务尝试数 | 22,811 | 22,811 | 22,811 |
| 进入回归/主分析数 | 20,484 | 20,484 | 20,484 |
| 特定子样本（原始） | 含完成标准：2,869 | 含约束词：1,465 | 五类总计：20,484 |
| 特定子样本（回归） | 含完成标准：2,684 | 含约束词进入回归：1,261 | — |
| 其他子样本 | 可定位位置：2,512 | — | — |

**说明**：
- Paper 01 中 2,869 与 2,684 的差异源于部分含完成标准任务存在结果变量缺失或步骤数据缺失。
- Paper 02 中 1,465 与 1,261 的差异源于 listwise deletion（task_difficulty、word_count、os 等控制变量缺失）。
- Paper 03 中五类样本量之和为 1,631 + 6,282 + 1,849 + 9,864 + 858 = 20,484，与分析样本量一致。

## 4. 模型与方法一致性

| 论文 | 主分析方法 | 控制变量 | 稳健性检验 |
|------|------------|----------|------------|
| Paper 03 | 二元 EM 潜类别分析（LCA） | 11 个二元语用特征 | train/test split、bootstrap、k=4/5/6 比较 |
| Paper 02 | 二次 Logistic 回归 / 交互模型 | task_difficulty、word_count、os | RCS、绝对频次、丰富度、OS 子样本 |
| Paper 01 | Logistic / 负二项回归 | task_difficulty、word_count、os | 替代密度定义、位置定义、终止阶段指标 |

## 5. 关键结果数字一致性

| 结果 | Paper 01 | Paper 02 | Paper 03 |
|------|----------|----------|----------|
| 完成率总体 | 79.22% | 79.22% | 79.22% |
| 核心自变量效应 | `has_completion_criteria` OR = 1.255 | `has_constraint_words` OR = 1.165 | 类别间完成率 χ²(4) = 26.82 |
| 核心过程效应 | `has_completion_criteria` IRR = 0.883 | 高难度任务密度² b₂ = –0.039 | MANOVA Wilks' λ = 0.977 |

## 6. 发现的不一致问题与处理

| 问题 | 位置 | 处理方式 |
|------|------|----------|
| Paper 03 原稿类别比例四舍五入与原始计数不完全一致 | Paper 03 初稿 | 已根据 `03_class_distribution.json` 重新计算百分比 |
| Paper 03 示例中出现同一 `task_id` 重复记录 | Paper 03 初稿 | 已重新抽取不同 `task_id` 的真实示例 |
| Paper 01 原始未明确区分 2,869 / 2,684 / 2,512 口径 | Paper 01 初稿 | 已统一说明 |
| Paper 02 原稿将“全局倒 U”作为中心结论 | Paper 02 初稿 | 已改为“条件性非线性”，主效应不显著 |
| 三篇论文引用格式不完全统一 | 参考文献部分 | 已要求每篇内部统一，跨篇差异在 reference_audit.md 中说明 |

## 7. 未解决的方法学问题

1. **规则特征效度**：三篇论文的特征均基于关键词规则，未经过人工标注的精度/召回/F1/κ 验证。
2. **task_id 聚类标准误**：尚未系统报告按 `task_id` 聚类的稳健标准误。
3. **重复尝试问题**：同一 `task_id` 多次尝试导致路径分析有效样本量解释需谨慎。
4. **LCA 稳定性**：Paper 03 的 bootstrap 次数不足，需要更充分的随机启动与样本外验证。
5. **因果推断**：所有分析均为观察性研究，无法确立因果。
