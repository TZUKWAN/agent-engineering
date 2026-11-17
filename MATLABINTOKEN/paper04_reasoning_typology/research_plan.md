# 论文四研究计划：任务型交互智能体的显式推理链类型及其行动转化机制

## 1. 研究主题

探讨任务型交互智能体在执行用户指令过程中形成的显式推理链（explicit reasoning chain）是否存在可识别的类型，以及这些类型如何与行动步数、错误率、冗余率、任务完成等执行结果相关联。

## 2. 核心问题

- 大模型在任务型交互中如何把用户指令转化为显式推理链？
- 显式推理链在长度、结构、分解、约束、验证、反馈、修正、终止、对齐等维度上呈现哪些差异模式？
- 这些差异模式是否与执行路径和任务完成存在系统关联？

## 3. 理论基础

- 言语行为理论（Austin, 1962; Searle, 1969）
- 共同基础理论（Clark, 1996）
- 关联理论（Sperber & Wilson, 1986）

## 4. 数据

- **主数据集**：AgentNet（xlangai/AgentNet），Hugging Face 公开数据集。
- **样本量**：22,532 条任务，416,186 个步骤（原始 22,625 行含 93 个重复 `task_id`，2026-09-26 R1 审计去重，规则与审计文件见 data_dictionary.md / dedup_audit.json）。
- **核心字段**：`instruction`、`task_completed`、`alignment_score`、`efficiency_score`、`task_difficulty`、`os`；步骤级 `thought`、`reflection`、`action`、`code`、`observation`、`last_step_correct`、`last_step_redundant`。

## 5. 研究步骤与对应脚本

| 步骤 | 脚本 | 输出 |
|------|------|------|
| 解析原始轨迹 | `src/paper04/01_parse_agentnet.py` | `data/interim/paper04/tasks.parquet`、`steps.parquet` |
| 提取推理链特征 | `src/paper04/02_extract_reasoning_features.py` | `data/interim/paper04/reasoning_features.parquet` |
| 识别推理链类型 | `src/paper04/03_identify_types.py` | `results/tables/cluster_selection.csv`、`cluster_profiles_labeled.csv` |
| 类型与结果关联 | `src/paper04/04_outcomes.py` | `results/tables/outcome_descriptives.csv`、`anova_results.json`、`logistic_type_completion.csv` |
| 生成图表 | `src/paper04/05_generate_figures.py` | `results/figures/fig*.png` |

## 6. 特征体系

共 10 项特征：推理长度、结构化程度、任务分解、约束保持、验证意识、反馈利用、自我修正、终止判断、推理—行动对齐、工具/对象提及。

## 7. 分析方法

- K-Means 聚类（k = 2–8），以轮廓系数和 BIC 辅助选择 k。
- 方差分析（ANOVA）比较连续结果变量。
- 卡方检验比较任务完成率。
- Logistic 回归控制任务难度、操作系统、推理长度。

## 8. 预期结论

- 显式推理链可稳定划分为若干类型；
- 不同类型在执行步数、错误率、冗余率、任务完成上存在差异；
- 推理链的结构化与多维度覆盖可能与更高的完成率相关，但需控制任务难度与长度。

## 9. 限制与边界

- 仅分析 AgentNet GUI 数据，结论外推需谨慎；
- `thought`/`reflection` 为事后生成的文本，不等同于真实内部思维；
- 所有结论为观察性统计关联，非因果证明。
