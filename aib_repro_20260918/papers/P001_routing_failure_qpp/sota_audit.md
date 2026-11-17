# SOTA 与基线审计 — P001（规范 §8 T08.01–T08.04）

检索时间：**2026-09-18**（工具检索方向由文献代理以 arXiv API、ACL Anthology、OpenAlex/Crossref、Semantic Scholar 引用图、GitHub 实测检索；Hugging Face 数据集页在该沙箱不可达，DBLP/OpenReview 论坛页被反爬拦截，已在 literature_matrix.csv 的 `verify_status` 标注）。
证据表：`00_program_registry/shared_literature/literature_matrix.csv`（59 条 × 15 字段）。

## 1. 我们 competing 的是什么任务

必须先说清楚：**本文的任务不是"提高工具检索精度"**，而是"在不使用任何大模型的前提下，预测冻结的词面检索器会不会漏掉金标注工具"。这两者的排行榜不是一回事。

## 2. 最近的强结果与我们的可比性判定

| 工作 | 来源 | 报告数字 | 数据/协议 | 与本文可比？ | 判定 |
|---|---|---|---|---|---|
| ToolRet | Findings ACL 2025 | BM25 nDCG@10 **22.32** 平均（ToolBench 26.76 / ToolACE 23.47 / APIGen 26.42 / UltraTool 36.04）；最佳稠密检索器 40.54–48.70 | 43k 工具全库检索，nDCG@10 | ✕ 目录规模（我们每题 1–70 个候选，均值 6.10–8.76）、指标（AUROC vs nDCG@10）、查询来源全不同 | **not directly comparable** |
| CoHyDE | EMNLP 2026 wshp (REALM) | NDCG@5 提升 +2.5pp 总 / +6.3pp held-out 模糊查询 / +8pp 最难档 | ~10k ToolBench 子集 | ✕ 它是"改写查询以提升检索"，我们是"预测检索会不会失败" | 不可比（任务不同），但**撞我们的机制叙述**（L3） |
| Tool Retrieval Bridge | 2026 arXiv | BM25 平均 nDCG 9.73 → 19.59 | 模糊→具体指令对齐 | ✕ 同上 | 不可比；机制叙述被占（L3） |
| Tool-DE | 2025/26 arXiv | ToolRet 上刷新 SOTA（50k 嵌入 / 200k 重排训练实例） | 需训练编码器 | ✕ 我们的环境无可用稠密编码器（torch 为 CPU-only 构建、无权重可下载）稠密编码器（禁 API 且无硬件） | 不可比；**不参与其 SOTA 竞争** |
| 2605.24660（候选深度机会校正评测） | 2026 arXiv | BFCL 370 工具：~7 个候选即 90.3% 覆盖 vs 50 个 90.8%；ToolBench 3251 工具：fixed-5 64.7% vs 61.9%；下游 93.1% vs 87.1% | 注册表规模 20→3251 | △ **指标思想可比**（机会校正），故我们采用 chance-corrected 的 AUROC + 超几何机会基线；但数据规模与 split 完全不同 | 部分可比：我们采纳其"必须机会校正"的结论，不比较数字 |
| 2602.14878（MCP 描述缺陷与改写） | 2026 arXiv | 中位任务成功 +5.85%；部分目标完成 +15.12%；执行步数 +67.46%；回归 16.67% | MCP 服务器描述干预 | ✕ 那是干预实验（需生成/执行），我们只做观测预测 | 不可比；T032（描述改写干预）因此降级为未来工作 |
| Real-Time Detection & Repair of Agent Failures | 2026 arXiv | 非 LLM 监测器 AUROC **0.872**，5% 误报下检出 0.71；迁移 0.745/0.779；**冷部署崩到 0.527**（重校准 0.885） | 遥测/执行特征 | △ 同为"预测失败"，但对象是**执行失败**且用了运行期遥测 | 不可直接比数字；作为我们讨论"冷部署脆弱性"的引用依据 |
| Last Step Matters | EMNLP 2026 Main | 轨迹末尾语言不确定度 AUROC 0.85，但**50% 进度处无任何信号超过 0.60** | 长时程搜索/编码代理 | ✕ 预测对象与输入位置不同 | 不可比；但直接支撑我们"事前（查询时刻）预测"的定位与之互补 |
| CodeAct | ICML 2024 | 代码动作相对 JSON/文本最高 +20% 成功率 | API-Bank 等 | ✕ 结论属于动作表征比较 | 与我们已 kill 的 T010 相关，与本文无关 |

## 3. 公平比较五条件自检（T08.02）

| 条件 | 我们的状态 |
|---|---|
| 同一数据版本 | 我们自建：Toucan-1.5M revision `0df3cf37f2ab…`，无任何已发表工作在其上做检索评测（已核对其论文只评 BFCL V3 与 MCP-Universe） |
| 同一 split | 不存在公开 split：我们自建 70/30 按 prompt_id 分组 | 
| 同一主指标实现 | ✕ 我们报 AUROC(fail@k)，公开工作报 nDCG@10 / 成功率 |
| 同一评测协议 | ✕ 我们无 LLM、无稠密编码器（GPU 存在但 torch 为 CPU-only 构建，且预训练权重不可下载） |
| 同等外部资源 | ✕ 我们禁 API（项目硬边界） |

→ **结论：五项中仅第一项部分成立。本文一律不写 "SOTA"，也不写"超过已有检索方法"。**

允许写的表述（已按此措辞写进正文）：
1. 在同协议、同预算的无模型基线族内，事前预测器优于平凡基线与事后准局部基线；
2. 与公开数字的关系标注为 not directly comparable；
3. 由于 Toucan 上不存在已发表检索评测，我们的数字构成该语料上的**首个参照基线（reference, not SOTA）**，后续工作可据此比较。

## 4. 基线阶梯实际落实情况（T08.03）

| 层级 | 我们的实现 | 状态 |
|---|---|---|
| B0 平凡 | 常数（AUROC 0.5）；仅查询长度（test 0.5322–0.6677） | ✔ 已跑（EXP-0012） |
| B1 经典统计/传统 ML | 正则 logistic（L2）；HistGradientBoosting 树模型 | ✔ dev 已跑（EXP-0006b：树 0.8017–0.8718）；test 以冻结 logistic 为准 |
| B1' 事后准局部 QPP | BM25 top1−top2 分数差 + top1 分数 | ✔ 这是本文的主对手（test 0.6489–0.8061） |
| B2+ 自训双塔稠密检索器（E03b/EXP-0024） | 同一 dev 行集、同一 prompt_id 分组交叉验证、无预训练权重 | **已运行**：dense hit@3 0.9643 vs BM25 0.9222（chance 0.4718）。因此本文不把"优于 BM25"当作贡献，也不与预训练编码器榜单比较；跨排序器预测迁移未达判据（见 A13） |
| B2 强通用模型 | 稠密编码器（DPR/BGE 级） | ✕ **无法按同等条件运行**：禁调用推理 API；本机虽有 RTX 3060 但 torch 为 CPU-only 构建、无 sentence_transformers/faiss，且预训练权重不可下载。已明确记为缺失项（L6 给出可行的替代路线 E03b），不用文献数字冒充（limitations.md §L6） |
| B3 最接近前作 | CoHyDE 的"模糊查询分层"分析逻辑，用我们的分层复现（目录规模 × 覆盖率分位） | △ 以分层分析形式部分实现（EXP-0011 表 8），不声称复现其模型 |
| B4 当前强基线/SOTA | Tool-DE / ToolRet 微调编码器 | ✕ 不可比，见 §2 |
| B5 同预算公平对照 | 同特征、同 CV、同种子的事前 vs 事后比较，聚类 bootstrap 配对检验 | ✔ EXP-0011 E14 |

## 5. 排行榜提交次数（T08.02 第 3 条）

本文**未向任何公开 leaderboard 提交**（ToolRet 官方 repo 无对应任务：我们的目录与 split 与其不同）。测试集评估次数由账本强制：
`papers/P001_routing_failure_qpp/test_eval_ledger.json` → 目前 `evaluations` 长度为 **1**，config_hash `9c0c3344e0a0cf62`，时间 2026-09-18T18:58:02，`override_reason` 为 null。任何第二次 test 评估都必须显式给出理由并写入 deviations.md。


## Outstanding verification duty (logged 2026-09-18 19:54)

A search on 2026-09-18 surfaced **"Latency-Quality Routing for Functionally Equivalent Tools"**
(arXiv `2605.14241v2`, dated 2026-05-28) — a topic adjacent to EXP-0014's equivalence-relabelling
analysis. **Its full text could not be retrieved in this session** (the fetch was refused), so the
abstract, method, dataset and metrics are unknown and no claim in this paper depends on it. It is
recorded in `literature_matrix.csv` at `overlap_level = L1_provisional` with
`verify_status = UNVERIFIED`. Before submission this must be read and the overlap re-classified: if it
turns out to define or label equivalent tool sets for retrieval evaluation, §H4 and appendix A6 must
cite it and state the difference explicitly.

This entry exists because the alternative — silently omitting a hit that a reviewer could find — is the
failure mode §17/A10 is meant to prevent.
