# Dataset card — P001（规范 T04.05）

所有数字由脚本产出，可用 `reproduce.sh` 重算；来源文件在括号内标注。

## 1. 来源与版本
| 项 | 值 | 来源 |
|---|---|---|
| 仓库 | `Agent-Ark/Toucan-1.5M`（Hugging Face） | dataset_registry.csv |
| Git revision | `0df3cf37f2abefb380370cfb02eabea2a35ae782`（三 config 全部同一 commit，`revision_is_single=True`） | `01_datasets/manifests/Toucan-1.5M.file_manifest.json`（本地 HF 缓存逐文件记录） |
| 每文件 SHA256 | 已逐文件登记（136 个 `.metadata` 条目） | 同上 |
| 下载时间 | 2026-09-18T01:22:31 → 05:10 区间 | dataset_registry.csv |
| License | `apache-2.0`（dataset card front matter 解析） | dataset_registry.csv |
| 实测总行数 | **1,646,546**（卡片按 config 声明之 num_examples 之和一致；仓库名 "1.5M" 与实测不符，本文一律用实测值） | parquet footer 全分片求和 |
| 使用的 config | OSS 457,130 / Qwen3 551,613 / Kimi-K2 518,516 = **1,527,259** | 同上 |
| 排除的 config | **SFT 119,287** | EXP-0003 |

## 2. 排除 SFT 的原因（可复核）
`target_tools` 中的金标注工具必须能在同一行的候选目录中定位。EXP-0003 用确定性 join（服务器名 slug + 函数名，必要时目录内唯一后缀）测得条目级解析率：
OSS **1.0000**（2150 项）/ Qwen3 **1.0000**（2194）/ Kimi-K2 **1.0000**（1511）/ **SFT 0.8880**（1634，抽样 1000 行/分片）。
SFT 的失败是数据本身造成（例如金标注 `search_google`，而该行目录只有 weather 系列工具），且 SFT 的目录列名是 `tools` 而非 `available_tools`。阈值取 0.90，故排除。
结果文件：`results_raw/P000_gold_tool_grounding_20260918T180451.json`。

## 3. 字段真实语义（实读样本，非 README 转述）
| 字段 | 实测语义 | 注意 |
|---|---|---|
| `uuid` | UUIDv5，**按 config 命名空间生成**：同一 prompt_id 在不同 config 下 uuid 不同（EXP-0008f 实测 same-uuid=0/104 共同 prompt_id） | 不能当跨语料实体键 |
| `question` | 用户指令文本；均值 45–60 token 量级 | 由 5 个查询模型**从工具集正向合成**（Toucan 论文 §3.1） |
| `available_tools`（SFT 为 `tools`） | JSON 字符串；每项 `{"type","function":{name,description,parameters}}`，**不含服务器字段** | 服务器归属必须从 metadata 取 |
| `target_tools` | 逗号分隔，两套写法混用：`"Server::func"` 与裸 `func` | 与目录里的 slug 命名不一致（`movie-recommender-get_movies`） |
| `metadata.mcp_servers[i]` | 含 `server_id/server_name/server_info{author,overview,repository_url,license,tags,categories,server_url}` 与 `remote_server_response.tools[{name,description,input_schema}]` | **这是目录→服务器归属的唯一可靠来源** |
| `metadata` 其他键 | `prompt_id`、`row_id`、`server_analysis`、`cross_server_workflow`、`synthetic_data_gen_configs` | `prompt_id` 含 `_follow_up` 后缀 → 同 prompt 多行，必须按组切分 |
| `subset_name` | 覆盖率 1.0；取值如 `single-turn-original`、`multi-turn` | — |

## 4. 构建后的分析数据（EXP-0005/0007/0009）
| 统计 | OSS | Qwen3 | Kimi-K2 |
|---|---|---|---|
| 构建行数 | 15,000 | 15,000 | 15,000 |
| join 拒绝率 | 0.00% | 0.01% | 0.04% |
| 目录规模 mean / p50 / max | 6.34 / 4 / 66 | 6.10 / 4 / 70 | 8.76 / 6 / 67 |
| 每题金标注工具数 mean / max | 1.78 / 5（EXP-0003 抽样） | 同量级 | 同量级 |
| 指令 token 均值 | 见 `tables/table2_dataset_card.csv` | 同表 | 同表 |
| dev/test（按 prompt_id 分组，70/30） | 10,441 / 4,408 | 10,465 / 4,544 | 10,628 / 4,432 |
| **fail@3 有定义**的 dev 行 | 5,714（排除 45.5%） | 5,512（排除 47.6%） | 7,972（排除 25.0%） |

拒绝原因全部登记（`reject_no_gold`、`reject_ambiguous_by_suffix`、`reject_gold_func_not_in_catalog`、`reject_server_mismatch`），见 `results_raw/EXP0005_*.json` 的 `rejection_accounting`。

## 5. 选择偏倚与外部效度（必须主动声明）
1. **结构排除**：`n_candidates ≤ k` 的查询（dev 的 25.0%–47.6%）在 fail@k 上不可能为正例，已从该因变量分析中剔除；被剔除者目录更小、任务更短，因此**结论只适用于目录规模 > k 的情形**。
2. **合成查询**：问题是模型从工具集正向生成的，指令措辞与目标工具描述的词面重叠部分来自生成过程本身，不是真实用户行为 → 本文一切结论表述为" Recorded agent-instruction data 中的词面可达性"，不表述为"人类信息行为"。
3. **金标注非穷尽**：Toucan 论文 §3.1 自述 `target_tools` 不穷尽；EXP-0011 进一步测得不同排序器的正例集合仅重叠 3.4–10.6% → "失败"是排序器相对概念（claim C6/C11）。
4. **教师与框架混杂**：三个 config 同时改变教师模型、生成框架与质量过滤（Toucan §3.1），故"跨模型复现"不等于"纯模型效应"。
5. **跨 config 非独立**：prompt_id 重叠 4.5–9.4% → 合并推断按 prompt_id 做聚类 bootstrap。
6. 真实人类指令对照（AgentNet 22,811）尚未纳入本篇，列为后续（T004）。

## 6. 缺失值与异常（EXP-0007 实测）
`target_tools` 非空率 1.0；`available_tools` 可解析率 ≈1.0（拒绝率 ≤0.04% 含不可解析与无法定位）；派生特征中 `qpp_max_doc_sim / qpp_mean_doc_sim / qpp_doc_sim_spread` 存在边界 NaN（查询无命中项时），训练折内以中位数插补并登记 NaN 率；若干零方差指令特征（如部分语料的 `url_n`）在建模范式外被剔除并登记列名。

## 7. 复算
```
python 02_shared_code/data_audit/audit_datasets.py            # 版本/license/规模/字段
python 02_shared_code/data_audit/probe_gold_tool_grounding.py # join 可行性
python 02_shared_code/data_audit/audit_split_integrity.py     # 重复与切分完整性
python 02_shared_code/trajectory_parser/build_toucan_routing_dataset.py --rows-per-config 15000 --shards-per-config 10
python 02_shared_code/statistics/run_p001_experiments.py --stage dev-select --repeats 5
python 02_shared_code/statistics/run_p001_experiments.py --stage robust    --repeats 5
python 02_shared_code/statistics/run_p001_experiments.py --stage test      --repeats 5   # 账本限制为一次
python papers/P001_routing_failure_qpp/scripts/make_figures_tables.py
```


## Two schema facts measured rather than assumed (added after EXP-0013/0014)

1. **The catalog column carries no server namespace.** All three configs' `available_tools` entries are
   bare function names (`create_plugin`, not `framer::create_plugin`). Server identity exists only in
   `metadata.mcp_servers[*].remote_server_response.tools`, which the builder consumes for the gold join
   and then discards. Consequence: no namespace-/server-level analysis (e.g. crowding by server prefix)
   is possible from this column, and EXP-0014 had to drop its `same_server` conjunct (deviation D12).
2. **Per-query catalogs are dense with same-server sibling tools** that share a parameter schema and
   differ by one token (`delete`/`get`, `references`/`citations`, `npm`/`pypi`, `subtract`/`multiply`).
   This was established by reading 40 sampled sibling pairs against their instructions (EXP-0015), and
   it is the structure the pre-retrieval predictor keys on.

**Persistence (v4/v5):** `question` (<=4000 chars; measured max 1403, so lossless) and the **full** tool
catalog as `catalog_json` are stored per row so relabelling and catalog interventions can run without
re-reading the 79 GB source. Re-scoring the persisted catalog with the frozen BM25 reproduces the
published `fail_at_3` on **all 19,198 dev rows (0 label changes)**; 2 rows differ only in the order of an
exact score tie at the cut (EXP-0014b).


## E08 round (EXP-0020..EXP-0023): two additional sources, verified from the files

**Toucan `SFT` config** - same repository, revision and apache-2.0 licence as the published three. Columns
actually present: `uuid, subset_name, question, target_tools, tools, messages`; the catalogue column is `tools`
(not `available_tools`) and there is **no `metadata`**, so gold labels resolve by exact name / unique suffix only
and cannot be cross-checked against a per-row MCP server tool index. Sampled `subset_name` is uniformly
`single-turn-original`. Built at seed 42 with the frozen invocation
(`--rows-per-config 15000 --shards-per-config 10`); its uuid digest is auto-anchored in
`01_datasets/manifests/routing_sample_identity.json`. Measured 15000/15000 kept, catalogue mean
5.14, dev fail@3 prevalence 0.0201. EXP-0021 then falsified the assumption that it is external:
it shares 1797/1797 tool names and 848 catalogue fingerprints with the source dev pool.

**lambda/hermes-agent-reasoning-traces** (apache-2.0 per the dataset registry; 4 shards, 22,347 rows measured).
Columns: `id, conversations, tools, category, subcategory, task`. Verified from the files rather than the card:
`tools` is a JSON array of `{name, description, parameters}` present for only part of the rows; the reference
model's invocations appear inside `gpt` messages as a `tool_call` block holding
`{"name": ..., "arguments": {...}}`, and a `tool` role returns the observation. Catalogue sizes 6-17 tools but only
5 distinct catalogues over 3000 sampled rows, and category is dominated by
`Terminal & Coding`. After the n_candidates>3 rule: 6000 rows, fail@3 prevalence 0.1777, extraction
rejections {'reject_catalog_empty': 13646}. Gold here is the tool the reference model actually invoked - the same construct as
Toucan's `target_tools`, and likewise not a human-verified admissible set. Licence and provenance of this corpus
were taken from the dataset registry; its README claims were not used anywhere in the analysis.
