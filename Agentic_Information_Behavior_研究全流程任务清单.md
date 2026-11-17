# Agentic Information Behavior 系列研究：真实实验—数据审计—SOTA 核验—论文交付全流程任务清单

> 适用范围：基于 Toucan-1.5M、AgentTrove、MMAT-1M、AgentBank、Hermes Agent Reasoning Traces、SWE-ZERO-12M-trajectories、CodeAct、AgentInstruct 等 Agent trajectory 数据集开展“计算语言学 × 信息管理学 × Agent 行为科学”系列研究。  
> 目标：每个选题都形成真实可复现的研究工程，而不是概念性论文或只跑一个主实验的演示性工作。  
> 核心原则：真实数据、真实运行、真实基线、真实统计、真实结论；任何 SOTA、显著性、效率、泛化、因果或机制结论都必须由可复核证据支持。

---

## 0. 最终交付物定义

每一篇论文必须形成一个独立、可复现、可审计的研究包。最低交付物如下：

1. `paper.md` / `paper.tex`：完整论文正文。
2. `appendix.md` / `appendix.tex`：完整附录，包含补充实验、超参数、额外表格、统计检验、误差分析等。
3. `research_plan.md`：研究问题、理论模型、假设/RQ、变量定义、实验设计、统计方法。
4. `literature_matrix.csv`：与选题直接相关的文献证据矩阵。
5. `sota_audit.md`：当前 SOTA、最强基线、排行榜、评测协议、是否可公平比较的逐项核验。
6. `dataset_card.md`：实际使用数据集、版本、哈希、license、字段、样本数、过滤规则、缺失值、去重、污染检查。
7. `experiment_registry.csv`：所有实验 ID、代码版本、配置、随机种子、开始/结束时间、状态、输出路径。
8. `results_raw/`：原始结果，不允许人工覆盖。
9. `results_processed/`：由脚本从 raw 自动生成的汇总数据。
10. `figures/`：论文全部图。
11. `tables/`：论文全部表。
12. `scripts/`：数据处理、实验、统计、作图脚本。
13. `configs/`：所有实验配置。
14. `logs/`：成功与失败实验日志。
15. `environment/`：依赖锁定文件、系统信息、GPU/CPU、CUDA/ROCm、模型/API 版本。
16. `reproduce.sh` / `reproduce.ps1`：从数据准备到生成核心表图的自动复现入口。
17. `claims_evidence_matrix.csv`：论文每一个核心结论对应哪一张表/图/统计检验。
18. `limitations.md`：限制、失败实验、未达到预期的结果。
19. `reviewer_attack.md`：站在强审稿人角度对论文做反驳性审计。
20. `final_audit.md`：提交前真实性、统计、SOTA、复现性、图表、引用的最终审计记录。

任何一项缺失，不进入“论文完成”状态。

---

# 1. 不可违反的研究诚信约束

## T01.01 禁止虚构或补造实验结果
- 不得凭经验填写任何数字。
- 不得根据论文预期“估算”指标。
- 不得生成看起来合理的 CSV、日志、表格冒充真实输出。
- 每一个结果单元格必须能够追溯到原始运行记录。

**验收：**
- 随机抽取论文表格中的 10 个数字，均能追溯到 raw output、experiment_id、config、seed 和代码 commit。

## T01.02 禁止测试集驱动优化
- 训练、特征、阈值、超参数、prompt、模型结构和实验策略只允许基于 train/dev/validation 决策。
- 测试集必须在方案冻结后评估。
- 如果 benchmark 只能通过公共 leaderboard 获得 test score，必须记录提交次数。
- 禁止因为 test 不漂亮继续针对同一个 test 反复改方法。

**验收：**
- `experiment_registry.csv` 能区分 `development` 与 `final_test`。
- `final_test` 发生前存在带时间戳的 `protocol_freeze.md`。

## T01.03 禁止选择性报告
- 不得只保留最好的 seed。
- 不得删除失败实验来制造一致性。
- 不得在看到结果后更换主指标却不披露。
- 不得只报告支持假设的子群体。

**验收：**
- 所有预注册主实验均可在 registry 中找到，无“消失实验”。
- 若更改指标/假设，必须在 `deviations.md` 中说明时间、理由及影响。

## T01.04 “漂亮结果”定义
“漂亮”只能指：
- 结论清晰；
- 统计充分；
- 图表专业；
- 对比完整；
- 规律稳定；
- 正负结果都可解释；
- 方法/理论具有价值；
- 可复现。

“漂亮”不得等同于：
- 强行超过 SOTA；
- 强行显著；
- 强行支持假设；
- 删除异常样本；
- 修改数据使趋势更明显。

---

# 2. 建立总研究工作区

建议目录：

```text
agentic-information-behavior/
├─ 00_program_registry/
│  ├─ topic_registry.csv
│  ├─ dataset_registry.csv
│  ├─ paper_registry.csv
│  └─ shared_literature/
├─ 01_datasets/
│  ├─ raw/
│  ├─ snapshots/
│  ├─ manifests/
│  └─ processed/
├─ 02_shared_code/
│  ├─ trajectory_parser/
│  ├─ information_act_tagger/
│  ├─ statistics/
│  ├─ plotting/
│  └─ evaluation/
├─ papers/
│  ├─ P001_xxx/
│  ├─ P002_xxx/
│  └─ ...
└─ docs/
```

## T02.01 建立选题注册表

字段至少包含：

- paper_id
- 中文题目
- 英文题目
- paper_type
- 核心数据集
- 外部验证数据集
- 理论基础
- 核心 RQ/H
- 主因变量
- 主自变量
- 主要方法
- novelty_risk
- data_feasibility
- compute_cost
- expected_venue
- status
- blocking_issue

**验收：**
- 每个选题唯一 paper_id。
- 任意两个选题必须说明差异，避免“同一数据切成多篇高度重复论文”。

---

# 3. 每篇论文先进行“可做性 + 撞题 + 前沿性”审计

## T03.01 系统检索文献

至少覆盖：

- ACL / EMNLP / NAACL / COLING
- SIGIR / CIKM / WSDM / WWW
- CHI / CHIIR
- NeurIPS / ICML / ICLR
- JASIST
- Information Processing & Management
- Journal of Documentation
- Decision Support Systems / MISQ / ISR（若理论相关）
- arXiv 近 12–18 个月高相关预印本
- benchmark 官方 repo / leaderboard / model card

检索时间必须记录。

每篇候选论文至少形成：
- 20–30 篇“直接相关文献”；
- 50 篇以上“背景与方法文献”；
- 最近 24 个月文献必须占足够比例；
- 至少覆盖 3 个不同研究社群，避免只看 NLP。

## T03.02 建立证据矩阵

字段：
- citation
- year
- venue
- problem
- theory
- dataset
- model
- method
- baseline
- metric
- main_result
- limitation
- relation_to_our_work
- overlap_level
- reproducibility
- code_url
- data_url

## T03.03 进行“撞题判定”

分为：
- L0：仅主题相关；
- L1：研究问题类似，变量不同；
- L2：研究问题与方法接近；
- L3：研究设计高度重合；
- L4：几乎已被完成。

规则：
- L0–L1：可继续。
- L2：必须强化差异。
- L3：原则上换题或重构。
- L4：停止。

**验收门 G03：**
必须写出一页以内的：
1. 已有研究做了什么；
2. 还缺什么；
3. 本文为什么能用现有数据回答；
4. 本文与最近 3–5 篇最相似工作的明确差异。

没有真实 gap，不允许进入实验。

---

# 4. 数据集获取、快照与真实性审计

目标数据源：

- https://huggingface.co/datasets/Agent-Ark/Toucan-1.5M
- https://huggingface.co/datasets/open-thoughts/AgentTrove
- https://huggingface.co/datasets/VIS-MPU-Agent/MMAT-1M
- https://huggingface.co/datasets/Solaris99/AgentBank
- https://huggingface.co/datasets/lambda/hermes-agent-reasoning-traces
- https://huggingface.co/datasets/AlienKevin/SWE-ZERO-12M-trajectories
- https://huggingface.co/datasets/xingyaoww/code-act
- https://huggingface.co/datasets/zai-org/AgentInstruct

## T04.01 获取真实数据
必须实际下载/stream 数据，不得依据 README 虚构样本分析。

记录：
- repo revision / commit
- download timestamp
- split
- shard
- local hash
- file size
- license
- dataset card revision

## T04.02 Schema 审计
自动输出：
- columns
- dtype
- nested schema
- null ratio
- unique counts
- list length distribution
- trajectory turn distribution
- model/source distribution
- reward distribution
- tool distribution
- task distribution

## T04.03 随机样本人工式机器审查
由智能体实际读取至少：
- 每个 split 100 个随机样本；
- 每个主要子类至少 20 个；
- 极短/极长轨迹分别抽样。

目的：
- 确认字段语义；
- 发现伪标签；
- 发现空轨迹；
- 发现异常格式；
- 发现 README 与真实内容不一致。

## T04.04 重复与泄漏审计
至少检查：
- exact duplicate
- near duplicate
- same task_id across splits
- same PR / same issue across splits
- same user question paraphrases
- source overlap
- benchmark contamination risk

## T04.05 生成数据卡
必须写明：
- 使用了多少真实样本；
- 为什么过滤；
- 过滤前后分布变化；
- 是否存在 selection bias；
- trajectory 中的 `<think>` 是否真实可解释为“认知过程”——默认不得作强心理化解释；
- 合成轨迹与真实用户轨迹的边界。

**验收门 G04：**
无法确认数据字段真实含义、license 或分割规则时，暂停该数据集的主实验。

---

# 5. 论文类型判定：先决定什么叫“成功”

所有论文必须归入以下至少一种类型。

## Type A：机制 / 行为研究
例：信息迷航、路径依赖、验证行为、语言不确定性。

成功标准：
- 构念定义清楚；
- 测量有效；
- 结果有统计效应量和置信区间；
- 多数据集/多任务稳健；
- 替代解释被检验；
- 外部验证通过。

**不要求 SOTA。**

## Type B：预测 / 分类 / 模型方法论文
例：预测 failure、信息行为 tagger、stopping model。

成功标准：
- 与经典方法、强神经基线、近期 SOTA 公平对比；
- 主指标显著提升或形成明确 Pareto 优势；
- 多 seed；
- 消融；
- 跨数据集；
- 校准/稳健性。

**此类才应系统核验 SOTA。**

## Type C：新指标 / 新 benchmark / 新评测框架
成功标准：
- construct validity；
- convergent / discriminant validity（适用时）；
- 与下游真实结果相关；
- 对不同模型产生可解释区分；
- 对扰动稳定；
- 不被简单 proxy 取代。

## Type D：系统 / Agent 优化
成功标准：
- end-to-end task success；
- 成本；
- latency；
- token/tool calls；
- failure rate；
- 稳健性；
- baseline system 对比；
- 消融。

## Type E：知识管理 / 轨迹复用
成功标准：
- retrieval / reuse 能改善真实任务；
- 不能只证明“相似度高”；
- 必须做下游任务实验；
- 比 raw trajectory、summary、workflow abstraction 等强基线。

---

# 6. 理论与变量操作化

## T06.01 明确研究问题
每篇论文最多：
- 2–4 个核心 RQ；或
- 3–6 个预注册假设。

避免十几个松散问题。

## T06.02 每个构念建立操作化表

例如：

| 构念 | 理论定义 | 计算定义 | 主指标 | 替代指标 | 潜在混淆 |
|---|---|---|---|---|---|
| Information Wandering | 非目标导向的信息搜寻漂移 | 低相关访问 + 高切换 + 低信息增益 | Wandering Index | Action entropy | task difficulty |
| Tool Semantic Crowding | 工具空间语义邻近导致辨识困难 | pairwise embedding similarity | mean cosine | local density | tool count |

## T06.03 禁止“为了显著而造指标”
新指标必须满足至少三项：
- 理论依据；
- 数学定义透明；
- 对 scale/length 等混淆做归一化；
- 与外部 outcome 有关联；
- 替代定义下结论稳定；
- 与已有指标存在可解释关系。

---

# 7. 实验协议冻结（Protocol Freeze）

在跑主实验前生成 `protocol_freeze.md`，至少包括：

1. 数据集版本；
2. train/dev/test split；
3. filtering；
4. primary metric；
5. secondary metrics；
6. primary baseline；
7. strongest baseline；
8. seeds；
9. hyperparameter search space；
10. statistical tests；
11. exclusion rule；
12. stopping rule；
13. SOTA comparison rule；
14. expected figures/tables；
15. resource budget。

任何主实验后的改变都写入 `deviations.md`。

---

# 8. SOTA 与基线审计流程

## T08.01 SOTA 检索层级
必须按以下优先级查：

1. benchmark 官方 leaderboard；
2. benchmark 官方仓库；
3. 最新同行评审论文；
4. 作者官方代码/模型；
5. OpenReview / ACL Anthology / PMLR / ACM DL；
6. arXiv 新工作；
7. 聚合网站仅作为线索，不作为唯一证据。

## T08.02 公平比较五条件
只有以下条件基本一致时，才能声称超过 SOTA：

1. 同一数据版本；
2. 同一 split；
3. 同一主指标实现；
4. 同一 evaluation protocol；
5. 同等外部资源/工具权限，或明确说明差异。

若不一致：
- 使用“not directly comparable”；
- 不写 SOTA。

## T08.03 强基线层级
每篇方法型论文最低需要：

- B0：trivial / random / majority / heuristic；
- B1：经典统计/传统 ML；
- B2：强通用模型；
- B3：最接近前作；
- B4：当前强基线/SOTA；
- B5：同模型同预算公平控制组。

## T08.04 基线复现优先级
1. 官方代码 + 官方 checkpoint；
2. 官方代码重训；
3. 作者明确配置的再实现；
4. 第三方可信实现；
5. 仅引用论文数字。

如果无法复现：
- 明确标注“reported number”；
- 不与自己重跑结果混为一谈。

---

# 9. 每篇论文的“最低完整实验包”

以下实验不是每篇机械全部跑，但必须逐项判断是否适用，并在 `experiment_scope.md` 写明“不适用理由”。

## E00 数据描述与基础统计
必须有：
- 样本数；
- 长度；
- 类别；
- 模型；
- 工具；
- reward/outcome；
- 缺失；
- 异常；
- 分布图。

## E01 主效应 / 主任务实验
直接回答论文核心问题。

## E02 基础基线
证明问题不是 trivial。

## E03 强基线 / SOTA 对比
适用于方法/系统型论文。

## E04 消融实验
逐项拿掉：
- 核心模块；
- 核心特征；
- 核心信息源；
- memory/retrieval/reflection 等。

必须回答“提升到底来自哪里”。

## E05 替代操作化
机制研究至少对核心变量使用 2 种合理计算定义。

例如：
- semantic similarity：不同 embedding；
- uncertainty：词汇规则 vs model score；
- diversity：entropy vs unique ratio。

## E06 超参数敏感性
至少覆盖真正影响结论的参数。

## E07 随机种子
训练/随机采样模型原则上至少 3–5 seeds；高方差场景更多。

报告：
- mean
- std
- 95% CI 或适当区间
- 最佳值只能作为补充，不能只报 best seed。

## E08 跨数据集外部验证
至少一个独立数据源，若研究问题允许。

## E09 跨模型验证
如果数据中包含多个 teacher/agent/model，检查模型特异性。

## E10 跨任务/领域稳健性
coding / web / database / multimodal 等条件下是否一致。

## E11 Robustness
按论文性质至少包含：
- noisy labels；
- different thresholds；
- subsampling；
- trajectory truncation；
- embedding model change；
- prompt variation；
- tool distractors；
- alternative parser。

## E12 Scaling
研究效果是否随：
- data size；
- context length；
- tool count；
- task complexity；
- model scale
变化。

## E13 效率与成本
方法型/系统型至少报告：
- GPU hours；
- inference tokens；
- API cost；
- wall-clock；
- tool calls；
- memory；
- latency。

## E14 Statistical Significance
主结论必须对应：
- effect size；
- confidence interval；
- 合理统计检验；
- 必要时多重比较校正。

## E15 Error Analysis
不得只展示成功案例。

至少：
- 随机错误样本；
- 高置信错误；
- 典型 failure modes；
- subgroup failures；
- rare cases。

## E16 Case Study
只用于解释机制，不能代替总体统计。

## E17 Counterfactual / Intervention
机制论文在可行时通过：
- 替换工具描述；
- 增加无关工具；
- 改变 namespace；
- 打乱顺序；
- 删除信息；
- 改写 query
做受控干预。

这能显著强化因果解释。

## E18 Replication
核心结果必须能够在干净环境由自动脚本重新生成。

## E19 Contamination Audit
对于公开 benchmark / LLM：
- 检查训练污染风险；
- 记录模型发布日期与数据发布日期；
- 必要时使用动态/新样本外部验证。

---

# 10. 统计分析规范

## T10.01 先做分布，再选检验
不得默认所有数据服从正态。

按数据类型选择：
- 二分类：proportion CI、McNemar、logistic regression；
- 多组独立样本：ANOVA / Welch / Kruskal-Wallis；
- 配对样本：paired t / Wilcoxon；
- 同任务多 rollout：mixed-effects model / hierarchical model；
- 时间/turn 序列：survival analysis、hazard model、state transition；
- count data：Poisson / negative binomial；
- repeated measures：mixed effects；
- network：network statistics + null model；
- 路径/序列：process mining、sequence analysis。

## T10.02 报效应量
不能只报 p-value。

例如：
- Cohen's d；
- odds ratio；
- Cliff's delta；
- η² / partial η²；
- standardized coefficient；
- risk ratio。

## T10.03 多重比较
大量 subgroup / feature tests：
- Holm；
- Benjamini–Hochberg；
- 其他有理论依据的方法。

## T10.04 层级结构
SWE-ZERO 一类“同 PR 多 rollout”数据禁止把所有 trajectory 当完全独立样本。

应考虑：
- PR/task random effect；
- model random/fixed effect；
- repository clustering。

这是关键。

## T10.05 大样本显著性陷阱
百万级数据极易出现极小 p-value。

因此更重视：
- effect size；
- practical significance；
- confidence intervals；
- out-of-sample prediction；
- robustness。

---

# 11. LLM-as-a-Judge 使用规范

LLM judge 不能成为唯一真实性来源，尤其是可执行任务。

优先级：
1. executable ground truth；
2. benchmark official evaluator；
3. exact structured criterion；
4. gold label；
5. calibrated LLM judge。

如果使用 LLM judge：
- 至少两个 judge 或一个 judge + rule-based；
- 报模型版本、prompt、temperature；
- 对抽样子集做 agreement audit；
- 报 judge sensitivity；
- 不允许让同一个模型既生成答案又无校准地独立判定自己正确。

---

# 12. “未达到 SOTA”后的合法优化循环

允许继续优化，但必须遵守以下闭环：

```text
开发集结果
↓
定位失败类型
↓
提出机制性修改
↓
只在 train/dev 验证
↓
做消融确认修改有效
↓
冻结版本
↓
最终 test
```

允许优化：
- 数据预处理 bug；
- 算法；
- prompt；
- architecture；
- retrieval；
- hyperparameter；
- efficiency；
- training；
- calibration；
- tool organization。

禁止优化：
- 根据 final test 错误逐例修改；
- 删除 test 中难样本；
- 修改 benchmark evaluator；
- 更换主指标直到获胜；
- 只挑有利模型/数据；
- 看到 test 后重新定义假设而伪装成事前假设。

## T12.01 SOTA 未达成时的决策树

### 情况 A：明显低于强基线
检查：
- implementation bug；
- baseline 是否公平；
- 数据处理；
- prompt；
- hyperparameter；
- metric；
- train/dev mismatch。

修复后重新开发。

### 情况 B：与 SOTA 持平
看是否存在：
- 更低成本；
- 更少参数；
- 更少工具调用；
- 更强泛化；
- 更强稳健性；
- 可解释性；
- 更简单方法。

若有，可形成 Pareto contribution。

### 情况 C：低于 SOTA，但产生稳定理论发现
若论文属于机制研究：
- 不必追 SOTA；
- 改为解释型贡献；
- 强化统计、因果、跨域验证。

### 情况 D：核心假设不成立
不得伪造支持。

选择：
- 报告 null result（若重要）；
- 重新构造理论；
- 转向更有证据的研究问题；
- 停止该选题。

---

# 13. 多角度数据分析要求

每篇论文至少从以下维度选择 4–8 个有理论意义的分析，而非堆图：

- task difficulty
- trajectory length
- agent/model
- dataset/source
- tool count
- semantic density
- domain
- success/failure
- cost
- uncertainty
- search depth
- search breadth
- switching
- repetition
- information gain
- source diversity
- modality
- early/late trajectory stage

每个 subgroup 分析必须说明：
- 为什么分析；
- 是否事前预期；
- 样本量；
- 是否校正多重比较；
- 是否存在 Simpson's paradox / confounding。

---

# 14. 因果与机制研究的额外要求

仅凭 observational correlation 不写：
- “导致”
- “提升机制是”
- “X 造成 Y”

至少采用其中之一增强识别：
- matching；
- propensity score；
- inverse probability weighting；
- fixed effects；
- mixed effects；
- difference design；
- instrumental variable（有合理工具变量时）；
- natural experiment；
- controlled intervention；
- counterfactual perturbation。

如果做不到，表述为 association / predictive relationship。

---

# 15. 图表规范：结果“漂亮”的正确实现方式

每篇论文至少规划：

1. 一张研究框架图；
2. 一张数据/trajectory 示意图；
3. 一张主结果图；
4. 一张机制/分组图；
5. 一张 robustness / ablation 图；
6. 一张 error taxonomy / case figure（适用时）；
7. 一张关键主表；
8. 一张完整对比表。

规则：
- 图表由脚本从结果自动生成；
- 禁止 Excel 手改数值；
- vector 优先：PDF/SVG；
- 坐标轴单位明确；
- error bars 有定义；
- 不截断 y-axis 制造视觉优势；
- 不用 3D 柱图；
- 颜色对色盲友好；
- 同一变量跨图保持一致编码；
- 每张图必须服务一个结论。

---

# 16. 论文写作流程

## T16.01 先写“结果骨架”，再写 prose
先生成：
- Claim 1 → Table/Figure → Evidence；
- Claim 2 → ...
- RQ1 answer；
- RQ2 answer。

## T16.02 论文结构

建议：

1. Abstract
2. Introduction
3. Related Work
4. Conceptual / Theoretical Framework
5. Data
6. Methods
7. Experimental Setup
8. Results
9. Robustness / Additional Analyses
10. Discussion
11. Implications for Computational Linguistics
12. Implications for Information Management
13. Limitations
14. Conclusion

不同 venue 再调整。

## T16.03 引言必须做到
- 明确现实问题；
- 明确研究缺口；
- 明确为什么现有数据首次/更好地允许回答；
- 3–4 个可验证贡献；
- 不夸大。

## T16.04 Related Work
按问题组织，不按作者罗列。

每个板块最后明确：
“已有研究到哪里；本文在哪个具体维度推进。”

## T16.05 Results
每个 RQ：
1. 先给事实；
2. 再给统计；
3. 再给解释；
4. 再给 robustness；
5. 最后回到 RQ。

禁止先讲故事再找数字。

---

# 17. Reviewer Attack：提交前强制反向审稿

智能体必须以“最苛刻审稿人”身份回答：

1. 这是一个新问题吗？
2. 与最近 5 篇最像的工作差别在哪里？
3. 核心变量是不是人为造出来的？
4. 指标是否有 construct validity？
5. 数据是不是 synthetic，能否外推？
6. 是否把 `<think>` 误当真实认知？
7. 统计单位是否独立？
8. 是否有 task/model/source confounding？
9. baseline 是否过弱？
10. 是否漏掉 2026 最新 SOTA？
11. 是否存在 test leakage？
12. 是否有 benchmark contamination？
13. 是否只报一个 dataset？
14. 是否只报一个 model？
15. 是否只报平均数，没有方差？
16. 是否只有显著性，没有效应量？
17. 是否跑太多 subgroup 导致 p-hacking？
18. 是否 LLM judge 自说自话？
19. case study 是否 cherry-pick？
20. 图是否误导？
21. 失败案例是否充分？
22. 结论是否超出数据支持范围？
23. “causal/mechanism”是否真的有识别设计？
24. SOTA 比较是否同协议？
25. 所有表图能否自动复现？

任何关键问题答不上来，返回对应阶段修复。

---

# 18. 最终 Gate：论文只有满足以下条件才算完成

## G18-A 数据真实性
- [ ] 数据真实下载；
- [ ] hash/版本记录；
- [ ] 无虚构；
- [ ] 过滤规则可复现。

## G18-B 实验完整性
- [ ] 主实验；
- [ ] 基线；
- [ ] 强基线/SOTA（适用）；
- [ ] 消融；
- [ ] 稳健性；
- [ ] 外部验证；
- [ ] 错误分析；
- [ ] 成本分析（适用）。

## G18-C 统计
- [ ] 多 seed；
- [ ] CI/error bars；
- [ ] effect size；
- [ ] significance；
- [ ] multiple comparison；
- [ ] hierarchical dependence 已处理。

## G18-D SOTA
- [ ] 检索时间明确；
- [ ] SOTA 来源真实；
- [ ] protocol 可比；
- [ ] 不能比较的地方明确标记；
- [ ] 未把“competitive”写成“SOTA”。

## G18-E 可复现
- [ ] clean environment 成功；
- [ ] 一条命令生成主结果；
- [ ] 图表自动生成；
- [ ] README；
- [ ] dependency lock；
- [ ] seed；
- [ ] hardware；
- [ ] runtime。

## G18-F 写作
- [ ] 结论与数据一致；
- [ ] 引用真实；
- [ ] 无虚构 DOI；
- [ ] 限制充分；
- [ ] 贡献不过度；
- [ ] 附录完整。

---

# 19. 每篇论文的推荐实验矩阵模板

```text
Paper ID:
Paper Type:
Primary Dataset:
External Dataset:
Main RQ:
Primary Metric:

E00 Data audit
E01 Descriptive analysis
E02 Main experiment
E03 Simple baseline
E04 Strong baseline
E05 Current SOTA
E06 Ablation
E07 Parameter sensitivity
E08 Alternative operationalization
E09 Cross-dataset
E10 Cross-model
E11 Cross-domain/task
E12 Robustness
E13 Counterfactual intervention
E14 Scaling
E15 Cost/efficiency
E16 Statistical inference
E17 Error analysis
E18 Case study
E19 Contamination audit
E20 Clean-environment replication
```

每一项必须记录：
- 是否适用；
- 实验 ID；
- 输入；
- 输出；
- 结论；
- 是否进入论文；
- 不进入论文的原因。

---

# 20. 多论文并行时的管理规则

允许并行准备：
- 文献检索；
- 数据下载；
- schema 审计；
- 公共 parser；
- 公共行为标签体系；
- 公共可视化工具。

不建议同时无序跑几十篇主实验。

按以下队列：

```text
候选池 30–50
↓
可做性审计
↓
Top 10
↓
pilot
↓
Top 5
↓
完整实验
↓
成熟后继续补下一批
```

原因：
- 能尽早淘汰撞题；
- 防止算力浪费；
- 让后续论文继承前文工具链；
- 避免数据与理论重复切片。

---

# 21. 针对这批 Agent 数据的特殊风险

## 21.1 合成轨迹外部效度
很多 trajectory 是模型生成/蒸馏数据。

论文应写：
- “Agent behavior in recorded trajectories”
而非未经证据声称：
- “human information behavior”。

## 21.2 `<think>` 的解释
`<think>` 可研究：
- linguistic planning trace；
- explicit reasoning text；
- expressed uncertainty。

不能无条件声称：
- 真实内部认知；
- 心理状态；
- 完整 hidden reasoning。

## 21.3 SWE-ZERO
大量同 task 多 rollout 是优势，但：
- outcome 标签含义必须核验；
- Submitted/exit status 不必然等于 functional correctness；
- 最好引入 executable verifier / gold patch / test outcome。

## 21.4 多数据集 schema 不一致
不能强行把不同 tool-call 格式拼成一个统一标签。

应：
- 保留原始 schema；
- 建立 canonical intermediate representation；
- 每个转换都有 unit tests。

## 21.5 API / closed model 漂移
如果调用在线模型：
- 记录 model name；
- 版本；
- 日期；
- endpoint；
- temperature；
- system prompt；
- retry；
- seed（若支持）。

---

# 22. 推荐的方法论工具箱

只在研究问题真正需要时使用，不允许为了“方法多”而堆方法。

## 描述与探索
- descriptive statistics
- distribution analysis
- correlation
- network analysis
- process mining
- sequence mining
- clustering
- UMAP/t-SNE 仅作可视化，不作核心推断

## 预测
- logistic regression
- random forest / XGBoost
- sequence model
- Transformer
- survival model

## 序列/行为
- Markov chain
- HMM
- change-point detection
- PrefixSpan
- process mining
- dynamic time warping
- trajectory embedding

## 层级与因果
- mixed-effects model
- fixed effects
- propensity approaches
- controlled perturbation
- mediation（满足假设时）
- survival / hazard model

## 文本与计算语言学
- semantic embeddings
- NLI
- discourse acts
- epistemic modality
- uncertainty markers
- query reformulation
- semantic role / action extraction
- information-theoretic measures

每一种方法必须回答：
“它解决哪个 RQ，为什么比更简单的方法合适？”

---

# 23. 研究程序级验收

整个系列研究最终应形成：

1. 一个统一 Agent trajectory canonical schema；
2. 一个可靠的数据审计工具；
3. 一个 information-act taxonomy；
4. 一个可复用统计分析包；
5. 一个自动图表系统；
6. 一个 SOTA / baseline 审计模板；
7. 30–50 个选题注册；
8. 每篇论文完整实验包；
9. 一个跨论文共享的 Agentic Information Behavior 研究框架；
10. 所有核心结果可自动复现。

---

# 24. 当前公认研究规范参考基线

执行时必须进一步检查最新版本，以下仅作为最低基线：

1. NeurIPS Paper Checklist：要求实验设置、可复现性、统计显著性/误差区间、开放代码/数据说明等。
   - https://neurips.cc/public/guides/PaperChecklist

2. ACL Rolling Review Responsible NLP Research / Reproducibility Checklist：
   - 明确要求报告超参数如何选择；
   - 不应在 held-out evaluation set 上调参；
   - 应明确单次/均值/最大值并报告统计信息。
   - https://aclrollingreview.org/responsibleNLPresearch/

3. ACM Artifact Review and Badging：
   - 强调 artifact documented、consistent、complete、exercisable；
   - 可复现实验应提供环境、README 和生成主要表图的脚本。
   - https://www.acm.org/publications/policies/artifact-review-and-badging-current

4. Benchmark contamination：
   - 对公开 LLM benchmark 必须考虑训练污染和重复评测带来的失真。
   - Chen et al., EMNLP 2025, “Benchmarking Large Language Models Under Data Contamination: A Survey from Static to Dynamic Evaluation”.

---

# 25. 总执行原则

整个项目遵循：

```text
真实问题
→ 真实文献缺口
→ 真实数据
→ 可证伪研究设计
→ 冻结协议
→ 真实运行
→ 完整基线
→ 多角度稳健性
→ 严格统计
→ 公平 SOTA 核验
→ 失败也记录
→ 自动复现
→ 论文写作
→ 对抗性审稿
→ 最终交付
```

最终评价一篇论文，不看“数字是否最好看”，看四件事：

1. 研究问题是否值得回答；
2. 证据是否真实、充分、可复核；
3. 结论是否超出已有研究；
4. 别人是否能够复现并相信它。

只有这四项成立，论文才进入“完成”状态。
