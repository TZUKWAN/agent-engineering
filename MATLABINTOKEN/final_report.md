# 论文四与论文五项目完成报告

## 1. 项目概述

在当前已包含三篇论文的工作空间基础上，新增了两个研究项目：

- **论文四**：《任务型交互智能体的显式推理链类型及其行动转化机制》
- **论文五**：《什么样的提示更容易诱发智能体失败：用户指令风险特征与推理—执行错误路径》

两个项目复用了前三篇论文的“任务型交互智能体”概念、AgentNet 数据集和提示语用特征变量体系，但建立了独立的目录、脚本、文稿与结果，未覆盖已有三篇论文的任何文件。

## 2. 数据边界与来源

- **主数据集**：AgentNet（xlangai/AgentNet），Hugging Face 公开数据集。
- **数据量**：22,532 条任务，416,186 个步骤（原始轨迹文件为 22,625 行/421,453 步，其中 93 行为重复 `task_id`；已按官方元数据 `meta_data_merged.jsonl` 的 step_num 匹配优先、否则保留末次出现的规则去重，去重审计见 `data/interim/dedup_audit.json`。2026-09-26 五轮审计 R1 修订）。
- **已使用字段**：
  - 任务级：`task_id`、`instruction`、`task_completed`、`task_difficulty`、`alignment_score`、`efficiency_score`、`os`。
  - 步骤级：`thought`、`reflection`、`action`、`code`、`observation`、`last_step_correct`、`last_step_redundant`。
- **未使用模型 API**：所有分析仅基于公开现成数据与规则型文本特征提取，未调用 OpenAI、Claude、Gemini、DeepSeek 等任何模型 API。
- **关于 Hermes/SWE 数据**：工作空间原无 Hermes Agent Reasoning Traces 或 SWE-agent-trajectories 数据。经评估，AgentNet 已同时包含用户指令、显式推理链文本、任务级完成标签和步骤级正确/冗余标签，足以支撑论文四与论文五的研究问题；引入缺乏统一任务完成标签的外部数据集反而会增加变量不可混合的风险。因此本项目以 AgentNet 为单一主数据集。

## 3. 已完成内容

### 3.1 共享文档

- `shared_reasoning_framework.md`：统一界定“显式推理链”概念、经验边界、特征体系与数据来源。
- `cross_paper_04_05_positioning.md`：明确论文四与论文五在研究问题、核心构念、方法上的区分与衔接。

### 3.2 论文四交付物

| 文件/目录 | 说明 |
|-----------|------|
| `paper04_reasoning_typology/manuscript.md` | 完整论文手稿 |
| `paper04_reasoning_typology/research_plan.md` | 研究计划 |
| `paper04_reasoning_typology/data_dictionary.md` | 数据字典 |
| `paper04_reasoning_typology/revision_notes.md` | 修改说明与未完成任务 |
| `paper04_reasoning_typology/results/tables/` | 聚类选择、类型画像、ANOVA、Logistic 回归等 CSV/JSON |
| `paper04_reasoning_typology/results/figures/` | 3 张结果图（PNG） |
| `src/paper04/` | 5 个可复现脚本 |

### 3.3 论文五交付物

| 文件/目录 | 说明 |
|-----------|------|
| `paper05_prompt_risk_failure/manuscript.md` | 完整论文手稿 |
| `paper05_prompt_risk_failure/research_plan.md` | 研究计划 |
| `paper05_prompt_risk_failure/data_dictionary.md` | 数据字典 |
| `paper05_prompt_risk_failure/revision_notes.md` | 修改说明与未完成任务 |
| `paper05_prompt_risk_failure/results/tables/` | 相关矩阵、回归系数、中介分析等 CSV/JSON |
| `paper05_prompt_risk_failure/results/figures/` | 4 张结果图（PNG） |
| `src/paper05/` | 5 个可复现脚本 |

## 4. 主要发现

### 4.1 论文四主要发现

- 从 AgentNet 显式推理链文本中提取 10 项特征，通过 K-Means 聚类识别出 **4 种显式推理链类型**：结构化分解型、详细展开型、常规综合型、简洁直觉型。
- 结构化分解型任务步数最长（平均 42.15 步），完成率最高（82.5%）；简洁直觉型步数最短（7.61 步），完成率最低（69.2%）。
- 在控制任务难度、操作系统和推理长度后：
  - 简洁直觉型显著负向预测任务完成（OR = 0.52，p < 0.001）；
  - 详细展开型显著正向预测任务完成（OR = 1.23，p < 0.001）。
- 所有类型在总步数、错误比例、冗余比例、对齐评分和效率评分上均存在显著差异。

### 4.2 论文五主要发现

- 构建了 10 项提示风险特征、8 项推理错误代理指标和 5 项执行错误代理指标。
- 提示风险指数显著正向预测推理错误指数（β = 0.025，p < 0.001）。
- 推理错误指数显著正向预测执行错误指数（β = 0.966，p < 0.001）。
- 执行错误指数（OR = 0.025）和推理错误指数（OR = 0.031）均显著负向预测任务完成（p < 0.001）。
- Bootstrap 顺序中介分析显示，提示风险通过推理错误与执行错误对任务完成的间接效应为 **-0.088**（95% CI [-0.121, -0.053]）。
- 单独风险特征中，**完成标准缺失**（β = 0.107，p < 0.001）和**验证要求缺失**（β = 0.186，p < 0.001）与推理错误指数关联最强。

## 5. 复现命令

### 5.1 论文四

```bash
python src/paper04/01_parse_agentnet.py
python src/paper04/02_extract_reasoning_features.py
python src/paper04/03_identify_types.py
python src/paper04/04_outcomes.py
python src/paper04/05_generate_figures.py
```

### 5.2 论文五

```bash
python src/paper05/01_parse_agentnet.py
python src/paper05/02_prompt_risk_features.py
python src/paper05/03_reasoning_execution_errors.py
python src/paper05/04_path_analysis.py
python src/paper05/05_generate_figures.py
```

### 5.3 一键复现

```bash
bash reproduce_paper04_paper05.sh
```

（该脚本在项目根目录下新建，调用上述 10 个脚本。）

## 6. 未完成事项

- 未引入 Hermes Agent Reasoning Traces 或 SWE-agent-trajectories 进行跨数据集稳健性检验。
- 论文四聚类结果可进一步通过 bootstrap 或不同特征子集检验稳定性。
- 论文五的错误指标为规则型代理指标，未进行人工抽样效度校验。
- 未探索提示风险特征之间的交互效应（如约束冲突 × 多子任务）。
- 未将论文四的推理链类型与论文五的错误路径进行联合分析（可作为后续工作）。

## 7. 结论

本项目成功在现有三篇论文工作空间基础上新增了两个独立研究项目，均基于同一公开 AgentNet 数据集，未调用任何大模型 API，所有统计结果均来自真实数据脚本。论文四建立了显式推理链类型学，论文五揭示了提示风险—推理错误—执行错误—任务失败的观察性统计路径，二者在理论上相互衔接、在研究问题与方法上相互区分。
