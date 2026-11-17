# P001 研究计划（T037）

## 论文定位
- **paper_id**：P001（对应 `topic_registry.csv` 的 T037，并吸收 T001/T002/T003/T005/T016/T017 为其机制、调节与指标成分）
- **题目（中）**：无大模型参与的工具路由失败事前预测：来自 4.5 万条智能体任务指令的跨教师模型证据
- **题目（英）**：Predicting Tool-Routing Failure Before Retrieval, Without Any LLM in the Loop: Cross-Teacher Evidence from 45k Agent Instructions
- **论文类型**：Type B（预测/方法），因此必须做严格基线阶梯与 SOTA 核验（规范 §5 Type B）
- **目标投稿**：SIGIR / CHIIR / Information Processing & Management（三者均需按 venue 重写结构）

## 现实问题
智能体在执行用户指令前，必须先从一个工具目录（含服务器名、函数名、描述文本、参数模式）中把候选工具暴露给模型。目录越大、描述与用户措辞差异越大，正确工具越可能根本不在排序前列——这是 agentic IR 的检索失败，而非生成失败。现有工作用训练型稠密检索器解决它（ToolRet、Tool-DE、CoHyDE），需要一个**不需要模型、不需要标注、可在部署前算出风险**的预测器来分流与预警。

## 研究缺口（撞题审计结论，检索于 2026-09-18）
- 机制本身已被占用（L3–L4）：CoHyDE（EMNLP 2026 wshp）、Tool Retrieval Bridge、Tool-DE、HumanMCP 都已陈述"口语化/欠定查询 vs 技术化 API 词汇"这一落差。因此本文**不主张**该机制。
- 目录规模/描述改写类已被占用：2605.24660（机会校正的候选深度评测）、2602.20426、2602.14878。因此 T002/T033 降为调节变量。
- 未被占领：**用纯词面、部署前可计算的特征预测工具路由失败**，并在多个教师模型语料上复现；QPP 社群（CLARITY/ECLE/quasi-local、ECIR'26、SIGIR'26 QPP-variant）从未被移植到 agent 工具检索。
- Toucan 论文（2510.01179）本身只评 BFCL V3 与 MCP-Universe，**未做任何检索/排序评测**，故 Toucan 上不存在检索排行榜——我们的数字会成为参照，但必须显式披露合成查询与 gold 非穷尽两个限制。

## 理论框架
查询绩效预测（QPP）的三族信号（查询内在、集合感知、准局部分数分布）× 信息检索的词汇落差理论 × 语用学显性度构念。工具目录在查询时刻即已知，因此集合感知特征属于合法的"事前"信息（这一点必须在论文中明确界定，不能含糊为"完全不看语料"）。

## 研究问题与假设（预注册，≤4 个）
- **RQ1 / H1**：仅用查询与目录（不看 gold）计算的词面特征，能预测 BM25 是否会把 gold 工具漏出 top-3，且 AUC 显著高于查询长度基线与常数基线。
- **RQ2 / H2**：该事前预测器在**同一评测协议下不低于事后准局部基线**（BM25 top1−top2 分数差）。
  - pilot 实测（dev，EXP-0006 run2）：事前 0.8192/0.8210/0.8038 vs 事后 0.7503/0.7959/0.6492（OSS/Qwen3/Kimi-K2）。
- **RQ3 / H3**：效应在三个教师模型 config 上方向一致、量级可比（跨模型复现），且在控制目录规模后仍存在。
  - pilot 风险提示：去掉规模的纯语言特征仅 0.6497–0.7292，说明信号部分由规模与长度承载，必须在论文中如实报告分解。
- **RQ4 / H4**：结果对 gold 标签**非穷尽性**稳健——按 ToolEX（2609.08327）方式把"功能等价工具"计入命中后，AUC 排序结论不变。
  - 若变，则主结论降级为"预测词面不可达性"，不得写成"预测路由失败"。

## 变量操作化
| 构念 | 理论定义 | 计算定义（主） | 替代定义 | 已知混淆 |
|---|---|---|---|---|
| 路由失败 | gold 工具未被暴露给模型 | `fail@3 = 1` 若 BM25 top-3 无任一 gold | `fail@1`、`fail@5`、`norm_rank` | 目录大小、gold 数量 |
| 词面可达性 | 查询与资源描述的表达距离 | qpp_coverage / idf_weighted_coverage / CLARITY mean-max / ECLE / doc-sim spread | 纯语言特征集（24 维） | 查询长度（机械相关） |
| 目录拥挤 | 可选资源数量与相似度 | `n_candidates`、两两描述 TF-IDF 相似度 | 服务器数量 | 与失败强共线（pilot：cand≤3 结构上不可能失败） |
| 指令欠定 | 隐含信息需求 | vague_word_n / demonstrative_n / pronoun_clause_start | 序列标记、约束密度 | 长度 |

## 数据
- 主数据：Toucan-1.5M（HF revision `0df3cf37f2ab…`，license apache-2.0，实测 1,646,546 行），用 OSS / Qwen3 / Kimi-K2 三 config；SFT 已因 gold 与目录不一致（解析率 0.888）排除。
- 二级验证：ToolRet（`mangopy/benchmarking-tool-retrieval`，43k 工具语料，需下载）——用于回答"是否只在短目录上成立"。
- 生态效度对照：AgentNet 22,811 条真实人类指令（`MATLABINTOKEN/data/processed/analysis_data.parquet`）。

## 基线阶梯（规范 §8 T08.03）
- B0 常数/随机、B0 仅查询长度
- B1 事后准局部 QPP（BM25 top1−top2 margin、top1 分数）
- B1b 事前正则 logistic（全特征 + log 规模）
- B1c 事前仅语言特征（不含任何目录相似度）
- B1d 事前仅集合感知 QPP
- B2 事前树模型（HistGradientBoosting，原生处理 NaN）
- B3 最接近前作：CoHyDE 式"vague 查询更差"的分层对比（我们无其模型，按其分层逻辑复现比较条件）
- B4 已发表数字：ToolRet BM25 nDCG@10 22.32、最佳稠密 40.54–48.70 → **标记 not directly comparable**（43k 工具语料 vs 我们 1–70 短目录；我们的标签非穷尽；我们无稠密编码器）

## 主指标 / 次指标
- 主：OOF AUROC（fail@3），逐 config 与合并；三 seeds 的 mean±std
- 次：AP（正例稀少更敏感）、Brier、校准曲线、PR-AUC、决策曲线下成本（top 5% 高风险查询的召回覆盖率）
- 机制：单变量 OR + Holm；规模分层；长度残差化后的净效应

## 实验矩阵（E 编号 → 是否适用）
E00 数据审计（已完成 EXP-0001/0003/0005/0007）；E01 主实验（预测阶梯）；E02 基线（B0/B1 已完成）；E03 SOTA 对比（ToolRet，标注不可比）；E04 消融（B1c vs B1d vs 全特征，已完成初步）；E05 替代操作化（fail@1/@3/@5、norm_rank；coverage 的 3 种定义）；E06 参数敏感（BM25 k1/b；top-k）；E07 多随机（5 seeds）；E08 跨数据集（ToolRet、AgentNet）；E09 跨模型（3 config 互检验，leave-one-config-out 训练/测试）；E10 跨任务/领域（subset_name 与目录域）；E11 鲁棒（标签噪声注入、不同分词器、不同检索器 TF-IDF cosine）；E12 scaling（训练量 1k→45k 学习曲线）；E13 成本（CPU 秒、特征计算耗时/查询、内存）；E14 统计推断（DeLong 或 bootstrap AUC 差 + Holm）；E15 错误分析（假阴/假阳各 200 例分层抽样）；E16 case study（仅解释机制）；E17 反事实干预（目录内加入/移除干扰工具、描述模板改写）；E18 干净环境复现（reproduce.sh）；E19 污染审计（Toucan 是否被 3 个 config 的生成模型训练过、跨 config 近重复）；E20 = E18。

## 排除规则（已冻结）
1. `target_tools` 为空 → 排除并计数；
2. gold 无法按确定性 join 规则落到目录 → 排除（pilot 0.00–0.04%）；
3. `n_candidates ≤ k` → 该查询不进入 fail@k 分析（结构上无定义），报告该层占比（实测 24.9%–46.5%）；
4. 零方差/全 NaN 特征列 → 不入模型，报告列名与 NaN 率；
5. 排除前后必须比较目录规模与长度分布，以说明选择偏倚。

## 资源预算
CPU only（无 API；GPU 存在但 torch 为 CPU-only 构建，实际仍只能 CPU 运行）。pilot 45k 行构建 57 s、分析约 90 s；全量 1.53M 行估算：构建 ≤ 2 小时（10 shards/config 采样已足够，全量分片遍历约 6–8 小时，仅在需要 E12 scaling 时做），分析在 5折×5 seed 下 < 30 分钟。内存峰值 < 4 GB（逐分片读取）。
