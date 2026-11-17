# PROTOCOL FREEZE — P001（T037）

冻结时间：**2026-09-18 18:31:30（本地）**
冻结人：研究执行代理（依用户规范 §7 在正式 test 评估之前）
约束力：本文件之后对主指标、split、排除规则、基线集合、假设的任何改动，都必须写入同目录 `deviations.md`，注明时间、理由与影响；**禁止**基于 final test 结果反向修改方法（规范 §1.02 / T01.02、§12）。

test split 在本文件生效前从未被评估过：EXP-0004 与 EXP-0006 的全部指标都在 dev 上计算（`build_toucan_routing_dataset.py` 与 `analyze_routing_failure.py` 均在代码中显式 `df[df.split == "dev"]`），test 行数仅作保留登记。

## 1. 数据集版本
| 项 | 值 |
|---|---|
| 主数据 | `Agent-Ark/Toucan-1.5M`，HF git revision `0df3cf37f2abefb380370cfb02eabea2a35ae782` |
| 使用 config | OSS(457,130) / Qwen3(551,613) / Kimi-K2(518,516)；**排除 SFT**（EXP-0003 实测 gold→目录解析率 0.888 < 0.99） |
| license | apache-2.0（dataset_registry.csv） |
| 下载时间 | 2026-09-18T01:22:31 起，单 commit（`revision_is_single=True`） |
| 二级验证 | ToolRet `mangopy/benchmarking-tool-retrieval`（待下载，E08） |
| 生态效度 | AgentNet `data/processed/analysis_data.parquet`（22,811 条人类指令） |
| 构建产物 | `01_datasets/processed/routing_{OSS,Qwen3,Kimi-K2}.parquet`（EXP-0007，45,000 行，拒绝率 0.00–0.04%） |

## 2. split（已实现，不可改）
`split = "dev" if md5(uuid)[:8] % 1000 < 700 else "test"` —— 70/30，按 uuid 哈希，跨 config 一致、可重算、不依赖随机数流。
pilot 实际规模：OSS dev 10,592 → 信息量充分子集 5,761；Qwen3 10,456 → 5,597；Kimi-K2 10,581 → 7,947。test 保留行数分别 4,408 / 4,544 / 4,432（登记于 EXP-0005 输出）。
同一服务器/同一 prompt_id 的行可能散落在两侧 —— 该泄漏风险在 E19 中量化，若显著则在 test 评估前追加按 `metadata.prompt_id` 分组的隔离（属冻结前已识别的例外，须记入 deviations.md）。

## 3. 过滤规则
见 research_plan.md「排除规则」1–5；其中规则 3（`n_candidates ≤ k` 不进入 fail@k）为**强制**，依据是 EXP-0005 实测该层 `fail@3 = 0.0000` 且 `chance_hit@3 = 0.0000`（top-3 即全目录）。

## 4. 主指标
`fail_at_3` 的 **out-of-fold AUROC**（5 折分层 CV），逐 config 报告 + 合并；跨 seed 报 mean 与 std。
理由：EXP-0004 实测随机排序 hit@1 达 0.44–0.55，原始命中率无信息量，故一切比较必须机会校正。

## 5. 次指标
AP、Brier、top-5% 高风险召回覆盖、`norm_rank`、`fail_at_1`、`fail_at_5`、LLR（bits vs 超几何机会）。

## 6. 主基线 / 最强基线
- 主基线（必须超越）：B0 仅查询长度（pilot AUC 0.5516–0.6620）
- 最强可比基线：B1 事后准局部 QPP = BM25 (top1−top2) margin + top1 分数（pilot 0.6492–0.7959）
- 前作复现比较：CoHyDE 式分层（按其分层逻辑，不用其模型）
- 已发表数字：ToolRet BM25 nDCG@10 22.32 / 稠密 40.54–48.70 → **not directly comparable**，不得写入"超过 SOTA"

## 7. 待评模型集合（冻结）
B1b 事前 logistic（全部 38 特征 + log 规模）、B1c 事前仅语言（24 特征 + log 规模）、B1d 事前仅集合感知（14 特征 + log 规模）、B2 HistGradientBoosting（max_iter 200 / lr 0.06 / depth 4 / early_stopping 0.15）。折内中位数插补 + 标准化 + L2 logistic（C=1；长度基线 C=1e6 近似无正则）。

## 8. 随机种子
`42, 43, 44, 45, 46`（5 个 CV/子采样种子，全部运行，报 mean±std；**禁止只报最佳**）。

## 9. 超参数搜索空间（仅允许在 dev 上搜索）
BM25 `k1 ∈ {0.9, 1.2, 1.4, 2.0}` × `b ∈ {0.0, 0.4, 0.75}`；L2 `C ∈ {0.1, 1, 10}`；树 `depth ∈ {3,4,6}`、`lr ∈ {0.03,0.06}`；`k ∈ {1,3,5}`。搜索准则固定为 dev AUROC(fail@3)，胜出组合一经选定不得因 test 表现再改。

## 10. 统计检验
AUC 差异用配对 bootstrap（10,000 次，按查询重抽样，seed 42）报 95% CI 与双侧 p；回归机制用单变量 logistic OR + **Holm** 校正（38 特征全族）；规模分层用 Mantel-Haenszel 趋势检验；效应量同时报 Cohen's d 与 OR。**不以 p 值替代效应量**（规范 §10.05）。

## 11. 停止规则
- 若 5 个种子的 dev AUROC 95% CI 上界不超过 B0 长度基线 → 停止该论文（H1 不成立）。
- 若事前模型无法在 ≥2/3 config 上达到事后基线的 95% → 转向 Type A 机制论文（预测不是贡献），并显式改写假设，不得改指标。
- 若 E19 发现 config 间近重复 >5% → 按 prompt_id 重隔离后重跑，结果并列报告。

## 12. SOTA 比较规则
仅在数据版本、split、指标实现、评测协议、外部资源权限五要素基本一致时才允许声称超过；否则一律写 `not directly comparable`（规范 §8 T08.02）。本项目结构性地无稠密编码器（禁 API/无 GPU），因此**不参与**检索精度 SOTA 竞争，竞争对象仅限同协议的无模型基线族。

## 13. 预期图与表
图1 研究框架；图2 目录/查询结构与规模分布；图3 主结果（基线阶梯 AUC + CI）；图4 机制（规模/长度分层 + 单变量森林图）；图5 稳健性（替代操作化、扰动、学习曲线）；图6 错误分析（假阴/假阳分布 + 2 例剖面）；表1 数据卡；表2 主对比；表3 消融；表4 跨 config/跨数据集复现；表5 完整结果。

## 14. 资源预算
CPU only；禁止任何大模型推理 API。全量分析预算 < 2 小时；如需 E12 全量扫描另计 6–8 小时并先记录理由。

## 15. 诚信声明
本文件所有数字均来自 `results_raw/EXP000{4,5,6,7}_*.json` 与 `01_datasets/manifests/*.audit.json`，无一为估计或补齐；EXP-0002、EXP-0004 的负面与缺陷结果完整保留在 `00_program_registry/experiment_registry.csv` 中，不因后续改进而删除。


---

## Amendments after the freeze that change what may be claimed (D13/D14, 2026-09-18 20:28-20:39)

1. **Inference unit.** Confidence intervals for the development contrasts are resampled on the
   **catalogue fingerprint**, not on `prompt_id` (EXP-0019). Justification: measured ICC and design
   effect show the catalogue is the binding dependence structure, and GEE robust standard errors reach
   7.33x the naive ones. No model, feature set, seed, metric or hypothesis changed.
2. **Claim scope.** The held-out AUROC is quoted as an **upper bound for unseen catalogues**, with the
   catalogue-grouped cross-validation figure reported beside it, because 63.7-88.1% of test rows share
   a catalogue with development rows and no catalogue-disjoint split exists (the largest connected
   component of the catalogue-prompt graph covers 86-98% of rows). This narrows a claim; it does not
   re-open one.
3. **The test split was not re-evaluated.** `test_eval_ledger.json` still records exactly one
   evaluation. The correction comes from re-analysis of development data plus disclosure, which is the
   only route T01.02 leaves once the single evaluation is spent.
