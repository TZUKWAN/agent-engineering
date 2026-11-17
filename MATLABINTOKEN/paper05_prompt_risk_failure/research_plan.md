# 论文五研究计划：什么样的提示更容易诱发智能体失败

## 1. 研究主题

探讨用户指令中的风险特征如何通过显式推理链诱发推理错误，并进一步传导为执行错误和任务失败。

## 2. 核心问题

- 什么样的用户提示更容易导致智能体推理链偏离？
- 提示风险如何转化为推理错误和执行错误？
- 推理错误与执行错误在提示风险与任务失败之间扮演何种角色？

## 3. 理论基础

- 言语行为理论（Austin, 1962; Searle, 1969）
- Grice 合作原则（Grice, 1975）
- 关联理论（Sperber & Wilson, 1986）

## 4. 数据

- **主数据集**：AgentNet（xlangai/AgentNet），Hugging Face 公开数据集。
- **样本量**：22,532 条任务，416,186 个步骤（原始 22,625 行含 93 个重复 `task_id`，2026-09-26 R1 审计去重，规则与审计文件见 data_dictionary.md / dedup_audit.json）。
- **核心字段**：`instruction`、`task_completed`、`task_difficulty`、`os`；步骤级 `thought`、`reflection`、`action`、`observation`、`last_step_correct`、`last_step_redundant`。

## 5. 研究步骤与对应脚本

| 步骤 | 脚本 | 输出 |
|------|------|------|
| 解析原始轨迹 | `src/paper05/01_parse_agentnet.py` | `data/interim/paper05/tasks.parquet`、`steps.parquet` |
| 构建提示风险特征 | `src/paper05/02_prompt_risk_features.py` | `data/interim/paper05/prompt_risk_features.parquet` |
| 构建推理/执行错误指标 | `src/paper05/03_reasoning_execution_errors.py` | `data/interim/paper05/reasoning_execution_errors.parquet` |
| 路径分析 | `src/paper05/04_path_analysis.py` | `results/tables/model*.csv`、`mediation_bootstrap.json` |
| 生成图表 | `src/paper05/05_generate_figures.py` | `results/figures/fig*.png` |

## 6. 变量体系

- **提示风险特征**：目标抽象、对象缺失、完成标准缺失、约束缺失、约束过密、多子任务无顺序、约束冲突、指代不明、初始状态缺失、验证要求缺失。
- **推理错误指标**：目标误解、约束遗漏、错误环境假设、任务分解错误、反馈后未修正、重复原策略、提前认为完成、缺少验证。
- **执行错误指标**：错误工具/动作、无效操作、重复动作、错误反馈次数、冗余步骤、失败终止、任务未完成。

## 7. 分析方法

- OLS 回归
- Logistic 回归
- Bootstrap 顺序中介分析

## 8. 预期结论

- 提示风险指数正向预测推理错误指数；
- 推理错误指数正向预测执行错误指数；
- 执行错误指数负向预测任务完成；
- 提示风险通过推理错误和执行错误对任务完成产生间接负向效应。

## 9. 限制与边界

- 仅使用 AgentNet 数据，结论外推需谨慎；
- 错误指标为规则型代理指标，非人工精细标注；
- 所有结论为观察性统计路径，不构成因果证明；
- `thought`/`reflection` 为后生成文本，不等同于模型内部思维。
