# deviations — P001（规范 §7 / T01.03）

所有在主实验协议周围发生的改动，按时间记录。测试集至今未被评估过一次，因此以下每一项都属"冻结前/冻结后但 test 未见"的修正。

| # | 时间 | 改动 | 触发证据 | 是否见到 test 结果 | 影响 |
|---|---|---|---|---|---|
| D1 | 2026-09-18 18:07 | gold→目录 join 由"名字前缀启发式"改为"`metadata.mcp_servers[*].remote_server_response.tools` 确定性映射" | EXP-0004 显示前缀规则误杀 OSS 26.7% 行，且 EXP-0003 证明存在两套标识规范 | 否（dev） | 拒绝率 26.7% → 0.00–0.04%；消除了"因解析器缺陷而挑选样本"的偏倚 |
| D2 | 2026-09-18 18:13 | 弃用原始 hit@k 作为主指标，改用一个"结构化信息量"约束：`n_candidates ≤ k` 的查询不进入 fail@k | EXP-0005 分层实测该层 `fail@3 = 0.0000` 且 `chance_hit@3 = 0.0000` | 否（dev） | 主分析样本从 dev 全量降到 5,512–7,972（占 52.4%–75.0%），必须作为选择条件披露；不改动 test 定义 |
| D3 | 2026-09-18 18:24 | 新增集合感知事前 QPP 特征族（coverage / idf-weighted coverage / CLARITY mean-max / ECLE / doc-sim spread） | EXP-0006 run1：仅语言特征 AUC 0.6497–0.7292，**低于**事后 margin 基线，且去掉目录规模后掉到 0.5716–0.6449 | 否（dev） | 事前模型 AUC 升到 0.7924–0.8309，超过事后基线（3 config 中 3/3 不低于、2/3 明显更高）。属规范 §12 允许的"机制性修改 + dev 验证 + 消融确认"（消融 = B1c vs B1d vs B1b） |
| D4 | 2026-09-18 18:29 | 修复：`analyze_routing_failure.py` 折内中位数插补（原实现因边界 NaN 直接 `ValueError: Input X contains NaN`）；零方差列入模型前剔除并报列名 | EXP-0006 run1 崩溃；实测 NaN 只出现在 `qpp_max_doc_sim / qpp_mean_doc_sim / qpp_doc_sim_spread` 三列 | 否（dev） | 插补在训练折内完成，不产生跨折信息泄漏；三列 NaN 率已写入结果 JSON |
| D5 | 2026-09-18 18:32 | split 依据由 `md5(uuid)` 改为 `md5(prompt_id)` | EXP-0008 污染审计：同一 `prompt_id` 的 original 与 `_follow_up` 行获得不同 uuid，会在 uuid 分层下跨 dev/test 相邻；跨 config 的 prompt_id 重现约 7.1%，但**精确问题文本重叠 ≤0.5%** | 否（test 从未读取） | 改变 dev/test 成员：POOLED 事前 AUC 0.7931 → 0.7942（无实质变化），说明原结论不是泄漏造成；同时把"约 7% prompt_id 跨 config 重现"记为 H3 的非独立性限制，合并估计后续需按 prompt_id 聚类稳健 |
| D6 | 2026-09-18 18:36 | 修复元数据不一致：`seeds` 字段与 pooled 的种子数由字面量 `[42,43,44]` 改为 `SEEDS[:repeats]`；此前存在"报告 3 个种子、实际运行 5 个"的记录错误 | 自查 EXP-0006 输出 JSON 与命令行参数不一致 | 否 | 现记录 `seeds=[42,43,44,45,46]` 且 pooled per_seed 有 5 个值 |
| D7 | 2026-09-18 18:30 | 早期标签错误更正：EXP-0005 内嵌代码块里 `desc_only_fail@3_rate` 实际存的是 full 排序的命中率的表达式，已删除并改为真正按 `bm25_desc_best_rank` 计算的 `desc_only_hit@3` | 代码自查 | 否 | 只影响该中间量，不影响任何已引用的主结论 |

| D8 | 2026-09-18 18:47 | §9 允许的搜索范围收窄为**仅分类器 C 与特征集合**；BM25 的 k1/b 由"待调"改为"固定 + 仅作稳健性检验" | 因变量定义为"该排序器是否漏掉金标注"，调排序器等于改因变量定义（循环） | 否（dev） | 记于 `configs/P001_frozen_model.json` 的 note；排序器变化改在 E11 报告（desc-only 排序器 DV，EXP-0011） |
| D9 | 2026-09-18 18:54 | 特征列表改为在 dev 上一次性确定 32 列并全局复用；模型由"逐 config 取最优"改为"按三 config 平均 dev AUC 取单一全局配置" | EXP-0012 首次尝试在 leave-one-config-out 处崩溃：pooled 训练 33 列 vs 单 config 测试 32 列（`ValueError: X has 32 features, but StandardScaler is expecting 33`）；逐 config 取最优亦等同跨数据集挑最好配置 | **否：该次运行在读取 test 前抛异常，未产生任何 test 数字，账本当时仍为空** | 冻结于 `configs/P001_frozen_model.json`（canonical_features 32 列）；EXP-0010 重跑给出同一全局模型 all_C0.1（mean dev 0.8159），EXP-0011 的 ΔAUC 未变（vs 长度 +0.1595/+0.2799/+0.2366；vs 事后 +0.0858/+0.0322/+0.1660） |
| D10 | 2026-09-18 18:59 | 为 EXP-0011 增补单变量 OR + Holm 表（`E05c`），并把图 4(a)/表 6 的读取源从"不存在的 in-sample 联合 logistic OR"改为该表 | 联合 logistic 在此特征集上病态（EXP-0005 曾报 `LinAlgError: Singular matrix`）；沿用旧读取路径会画空面板或写入假数据 | 否 | 逐特征岭正则 Newton 拟合；加入保护：若无 Holm 显著项则**抛错而不是出图** |

| D11 | 2026-09-18 19:21 | **样本漂移事故（已恢复）**：为 H4/反事实实验重跑数据集构建器以持久化 `question`+`catalog_json` 时，使用了构建器的默认 `--shards-per-config 8`，而 EXP-0009 的发布参数是 10，导致 OSS/Qwen3 的行集合被替换 | 快照对比：OSS dev（ unrestricted）fail@3 0.0423→0.0354、Qwen3 0.0677→0.0724、Kimi-K2 0.0318→0.0318（其 15006 条可见行在 8 shard 内已取满，故未变）；uuid 集合 OSS/Qwen3 不一致、Kimi-K2 一致 | 否（仅 dev 统计量，未读 test） | 立即从 `01_datasets/snapshots/exp0009_published/` 还原发布文件，并按冻结参数 `--rows-per-config 15000 --shards-per-config 10` 重建；根因修复：构建器现在把 `sha256(sorted uuid)` 前 16 位写入 parquet 并与 `01_datasets/manifests/routing_sample_identity.json` 锚点对比，不一致即 `SystemExit`（除非显式 `--allow-resample` 并要求重新冻结协议） |
| D12 | 2026-09-18 19:22 | EXP-0014 等价性判据删去 `same_server` 合取项 | 预运行实测：三个 config 的 `available_tools` 目录列都只存**裸函数名**（`create_plugin`，而非 `framer::create_plugin`），服务器命名空间只存在于 `metadata.mcp_servers`，而构建器在 gold join 后即丢弃；因此"同服务器"在持久化目录中不可判定 | 否（dev） | 规则改为仅用 `param_jaccard`/`name_jaccard`/`desc_cosine` 的可检式合取；同时把"目录列不含命名空间"作为数据事实写入 dataset card（这本身排除了以目录列做命名空间拥挤度分析的可能） |

| D13 | 2026-09-18 20:28 | **分割缺陷（已定量并降级结论，未重跑 test）**：EXP-0017 发现语料的支配性依赖结构不是 prompt 而是**目录（catalogue）**；EXP-0018 尝试构造"目录不相交"的 split_v6 时发现目录-prompt 连通图只有一个巨连通块（最大块占 86–98% 行），因此不存在可用的不相交划分 | 实测：发布 split 下 887/498/837 个目录同时出现在 dev 与 test；test 行中与 dev 共享完全相同目录的比例为 **80.9% / 88.1% / 63.7%**（prompt_id 跨块数 = 0，说明原分组对 prompt 有效但对目录无效）；按目录分组交叉验证使 dev AUROC 下降 0.0164/0.1110/0.0048 | **否：账本仍为 1 次 test 评估，未做任何第二次评估** | 处理的不是模型而是**解释范围**：论文中 test AUROC 明确改称"对未见目录是上界"，并同时给出按目录分组的 dev AUROC 作为保守的未见目录估计；`split_v6` 保留为诊断列而非可用划分，原因写入附录 |
| D14 | 2026-09-18 20:39 | 推断的聚类单位由 prompt_id 改为**目录指纹**（并保留两者对照） | EXP-0017：GEE 稳健标准误最大为朴素值的 **7.33 倍**，目录级设计效应最大 4.39，说明此前所有 dev 置信区间过窄 | 否（dev） | EXP-0019 重算三个主对比：CI 宽度最多放大 **2.955 倍**，但 9/9 对比仍不含 0（pre > 长度、pre > 事后 margin、pre > 仅语言特征 在 3 个语料全部成立）。方向不变、不确定性上调，正文改引目录聚类的区间 |

| D15 | 2026-09-18 21:15 | **E08 由计划改为实测，并新增两个 dev-only 实验**：(a) 用从未被协议引用的 Toucan `SFT` config 做跨 pipeline 迁移；(b) 在独立语料 hermes-agent-reasoning-traces 上做出未见工具宇宙迁移；(c) leave-one-tool-family-out。同时把 D13 的“上界”表述改为给出实测值 | EXP-0022 实测：本地八语料只有两个带每查询候选目录，外部基准站点在本环境不可下载；EXP-0021 实测 SFT 与源语料共享 100% 工具名与 848 个相同目录指纹，因此它不是未见目录，真正的未见性检验只能落在工具家族与外部语料层面 | **否：账本仍为 1 次 test 评估。EXP-0020/0021/0023 全部只用 dev 或外部语料，冻结模型的 C 与特征列未因新结果改动** | 跨 pipeline AUROC 0.8138 (catalogue CI [0.7576, 0.8545])；目录组合不相交子集 801 行 0.8316；答案家族留出使 0.7823 -> 0.7282（触发 0.02 判据）；跨语料 hermes AUROC 0.6939 vs 域内 0.8118，仍高于长度基线 0.4413 与事后 margin 0.6481。结论：D13 的上界现在有了实测对应物——未见工具宇宙上的判别力约为 0.6939，而非 0.81。

| D16 | 2026-09-18 22:05 | **补齐学习型稠密基线（E03b/EXP-0024），并据此把"排序器相对"从限制升级为论文结论的一部分** | 预训练编码器在本环境不可得（EXP-0022 + 环境更正记录），故改为从零训练双塔 TF-IDF→128 维投影模型，在同一 dev 行集、同一 prompt_id 分组交叉验证下与冻结 BM25 对比 | **否：本实验完全不读 test 行，账本仍为 1 次 test 评估** | 结果一半为正一半为负：dense 更强（hit@3 0.9643 vs 0.9222），失败集合几乎不相交（Jaccard 0.0846）；针对 dense 失败重训仍可达 AUROC 0.7816，但用 BM25 失败训练的冻结模型在 dense 失败上只有 0.6451，**低于事先设定的 0.65 判据**，因此不宣称跨排序器可迁移，并把判据原文与未达标一并写入正文与附录。|

## test 评估次数（T08.02 第 3 条）

`test_eval_ledger.json` 记录评估 **1 次**：2026-09-18T18:58:02，config_hash `9c0c3344e0a0cf62`，override_reason=null。D9 之前的那次调用在读取任何 test 行之前即因特征数不一致抛异常，未产生数字，因此不计为一次评估。

## 未变更项（明确声明）
主指标定义、假设集合 H1–H4、基线阶梯、多重比较方法（Holm + bootstrap AUC 差）、5 个种子、排除规则 1–5 均未按结果调整；没有任何一版结果被删除（EXP-0002 的 0.0 解析率与 EXP-0004 的两处缺陷仍完整保留在 `00_program_registry/experiment_registry.csv`）。

## 环境记录更正（2026-09-18 21:39，不改动 protocol_freeze.md 的历史文本）

多处曾写"本机无 GPU"。核查 `environment/system_info.json` 与实际解释器后更正为：**存在 RTX 3060 12 GB，但已安装的 torch 2.5.1 是 CPU-only 构建（`torch.cuda.is_available() == False`）**，且未安装 sentence_transformers/transformers/faiss、本地无预训练权重缓存、权重不可下载（EXP-0022 实测）。因此"分析实际只跑在 CPU 上"成立，但理由不是没有显卡。`protocol_freeze.md` 作为冻结时的历史记录**不修改**，更正只写入 L6 / sota_audit / appendix / final_audit；这也改变了剩余缺口的性质：稠密基线仍可做，只是必须**从零训练、不依赖任何预训练权重**（新列计划项 E03b），而不是以"没有算力"为由缺席。
