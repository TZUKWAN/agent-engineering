# 数据可行性与真实性审计记录（阶段 W0）

审计执行时间：2026-09-18 17:50–17:55（本地）
审计代码：`02_shared_code/data_audit/audit_datasets.py`（随机种子 42）
证据文件：`01_datasets/manifests/*.audit.json`、`*.file_manifest.json`、`dataset_registry.csv`、`audit_log.txt`
运行环境：Python 3.11.7 (Anaconda) / pandas 2.1.4 / pyarrow 14.0.2 / Windows-10-10.0.19045

> 本文件只记录**实际从本地文件读出的数字**。任何未经脚本产出的数字都不出现在此。

## 1. 版本、许可与体量（T04.01）

revision 与每个文件的 SHA256 取自本地 Hugging Face 缓存的
`.cache/huggingface/download/**/<file>.metadata`（三行格式：git commit / sha256 / 下载时间戳），
因此无需重算 79 GB 即可追溯到服务端版本。每个数据集的 `revision_is_single` 均为 True，
即本地快照对应单一 commit，无混版。

| 数据集 | HF repo | 实测总行数 | 声明 license | 单一 revision | 首次下载 |
|---|---|---|---|---|---|
| Toucan-1.5M | Agent-Ark/Toucan-1.5M | 1,646,546 | apache-2.0 | 是 (0df3cf37…) | 2026-09-18T01:22:31 |
| AgentTrove | open-thoughts/AgentTrove | 1,696,847 | apache-2.0 | 是 (b395a430…) | 2026-09-18T02:25:39 |
| SWE-ZERO-12M | AlienKevin/SWE-ZERO-12M-trajectories | 12,290,800 | apache-2.0 | 是 (44e02807…) | 2026-09-18T03:38:28 |
| AgentBank | Solaris99/AgentBank | 53,205 | apache-2.0 | 是 (6d718ff7…) | 2026-09-18T03:36:49 |
| hermes-agent-reasoning-traces | lambda/hermes-agent-reasoning-traces | 22,347 | apache-2.0 | 是 (b92885e4…) | 2026-09-18T03:36:57 |
| code-act | xingyaoww/code-act | 78,385 | apache-2.0 | 是 (afba3436…) | 2026-09-18T05:10:18 |
| AgentInstruct | zai-org/AgentInstruct | 1,866 | **未声明** | 是 (e252cf78…) | 2026-09-18T05:10:40 |
| MMAT-1M | VIS-MPU-Agent/MMAT-1M | 1,659,279 | `- apache-2.0`（卡片格式异常） | 是 (b5bf7137…) | 2026-09-18T03:33:10 |

与卡片声明不一致之处（以文件为准）：Toucan 卡片按 config 声明的 num_examples 之和为
1,646,546，与实测一致；但仓库名 "1.5M" 与实测 1.65M 不等，写作时须用实测值。
MMAT 的 license 字段解析出 `- apache-2.0`（卡片 YAML 列表未规范化），需人工确认。

## 2. 门 G04 判定：哪些数据集可以进主实验

**通过（可作为主数据）**

- **Toucan-1.5M**：`target_tools` 在全部 4 个 config 的非空比例均为 **1.0**（审计样本各 3,000 行）。
  这是本项目唯一具备**客观金标注且覆盖率 100%** 的大规模结局变量来源。
  实测每题候选工具数均值 6.7、最大 79；gold 目标工具数均值 1.78（分布 1:17005 / 2:13645 / 3:8229 / 4:28 / 5:1）。
  指令文本精确重复率 ≤0.0077。→ 允许进入 T001/T002/T003 主实验。
- **SWE-ZERO-12M**：`exit_status`、`instance_id`、`repo`、`duration_sec` 覆盖率均 1.0。
  但存在两个必须先处理的效度问题（见 §3）。→ 条件通过。
- **code-act / AgentBank / hermes**：字段完整可读，但**无任何结局标签**。→ 只能作外部验证或描述性数据。

**不通过（暂停主实验）**

- **AgentTrove**：在 8 个分片、360,169 行抽样中，`judgment` 非空 **0%**、`instruction` **3.0%**、
  `verifier_output` **1.3%**、`result` **13.7%**。结局标签不可用作因变量（T04.03 发现的"伪标签"典型情形）。
  其 `original_source` 覆盖 12+ 任务域，仅支持 T016（语体变异）与 T020（污染）这类不需要结局的研究。
- **MMAT-1M**：抽样 12,000 行中图像引用 **12,000/12,000 缺失（比例 1.0）**——`images` 字段指向
  `../datasets/llava-cot/...` 等仓库外路径，本地不存在。**多模态类研究当前不可行**；
  该事实本身成为 T014 的研究对象。用户文本精确重复率 0.0933。
- **AgentInstruct**：卡片**未声明 license**（G04 明确规定 license 无法确认即暂停主实验），
  且实测仅 1,866 行，6 个环境各 122–538 行，不足以支撑任何主效应检验。

## 3. 两个关键混淆结构（会在审稿中被直接提出）

1. **SWE-ZERO 轨迹右删失**：审计 3,000 行得 `messages` 长度 mean 31.73、p50 32、p95 32、max 32，
   即轨迹在 32 轮被硬截断。因此 `exit_status="incomplete"`（单分片 9,724/10,000）**不能解释为"失败"**，
   更可能是"未达提交即被截断"。任何阶段/终止类结论（T008、T011、T035）必须显式建模删失，
   否则结论不成立。`duration_sec` mean 51.65、p50 45.3、max 356.37。
2. **code-act 两个 config 不是随机对照**：codeact 分轮数 7–11（mean 8.38），general 分轮数 2–234
   （mean 5.23），且 general 有 30.4% 样本首条消息角色为 `user`（无 system 前导）。
   两组的任务类型与模板都不同 → T010 存在严重选择偏倚，须先用任务类型匹配，否则降级为描述研究。

## 4. 层级结构（T10.04）

SWE-ZERO：12,290,800 行分布在 1,230 个分片，单分片内实测 132 个 `repo`，
`instance_id` 在分片内重复出现 → 同一任务多次 rollout 的事实成立。
所有推断须以 `instance_id`（必要时叠加 `repo`）为聚类单元，禁止把轨迹当独立样本。

## 5. 工程事实（影响可复现性）

- 系统 `python` / `python3` 是 WindowsApps 存根（执行返回退出码 49，无输出），
  真实解释器为 `D:/Environment/anaconda3/python.exe`。风险由 `reproduce.sh` 的自解析块消除：它按候选**逐个执行**来探测
  （`$AIB_PYTHON` → 已知解释器 → `python3` → `python`），全部不可用时打印可操作的错误并以退出码 3 中止，
  而不是让第一步以退出码 49 无输出地失败（G18-E 的直接风险）。用 `command -v` 判断存在性无效——存根能被正常解析出来。
- 旧目录 `MATLABINTOKEN/` 中 9 个脚本仍硬编码 `D:\MATLABINTOKEN`，项目实际已在 `G:\刘俊琦\` 下；
  复用旧特征提取代码前须改为相对路径或环境变量。
- 审计过程中修复的两处真实数据访问缺陷（记录以避免重复踩坑）：
  AgentTrove 含 GB 级 binary 列，`Table.take()` 触发 `offset overflow while concatenating arrays`；
  Toucan 单分片可达 315 MB，整表载入有内存风险。现统一改为**逐 row group 采样并跳过 binary 列**。

## 7. 探针 P000：Toucan gold `target_tools` 能否落到目录条目上（决定 T001–T003 生死）

实验登记：`00_program_registry/experiment_registry.csv` 中 EXP-0002 / EXP-0003，
原始输出 `results_raw/P000_gold_tool_grounding_*.json`（种子 42，每 config 1,000 行）。

**第一轮（朴素匹配）结论是"全部不可行"**：OSS/Qwen3/Kimi-K2/SFT 的解析率分别为
0.0 / 0.0 / 0.0 / 0.0。原因是 Toucan 内部存在**两套标识规范**：
gold 写成 `Movie Recommender::get_movies`，而目录条目被压平成 slug `movie-recommender-get_movies`。
这本身是一个可发表的 schema 互操作性证据（写入 T012/T025）。

**第二轮（加入 slug + 函数名后缀层）实测：**

| config | 目录列 | gold 条目数 | 条目级解析率 | 行级全解析率 | 后缀歧义 |
|---|---|---|---|---|---|
| OSS | available_tools | 2,150 | **1.0000** | 0.9950 | 6 |
| Qwen3 | available_tools | 2,194 | **1.0000** | 0.9720 | 44 |
| Kimi-K2 | available_tools | 1,511 | **1.0000** | 1.0000 | 0 |
| SFT | **tools**（列名不同） | 1,634 | 0.8880 | 0.8890 | 11 |

**判定**
1. T001/T002/T003 **可行**，但主数据限定为 OSS + Qwen3 + Kimi-K2（合计 1,527,259 行，
   实测行数见 §1），SFT 不作为因变量来源。
2. 冻结的 join 规则必须加入**服务器一致性约束**：纯后缀匹配会把
   `IPMA Weather Data Server::get_weather_forecast` 错配到
   `united-states-weather-get_weather_forecast`（SFT 中的真实样本）。
   因此顺序为：M2（server slug + func）优先 → M4 仅在后缀唯一**且**服务器部分一致时接受 →
   其余记为不可解析并按 T04.05 报告排除率与排除后分布变化。
3. 服务器名与函数名之间 Toucan 用 `-` 连接且函数名内部也可能含 `-`
   （`Trends Hub::get-zhihu-trending` → `trends-hub-get-zhihu-trending`），
   因此不存在无歧义的字符串切分点，只能靠"目录内唯一后缀 + 服务器一致"联合判定。
   这是构造检索数据时的真实约束，不是可忽略的细节。
4. SFT 的 11.2% 不可解析条目是**数据本身**的问题（gold 工具确实不在该行目录中，
   如 gold `search_google` 而目录只有 weather 系列工具），不是解析器缺陷；
   已在原始 JSON 的 `examples_failed` 中留存可核对样本。

## 8. 结论

在"不调用任何模型 API"的边界内，**Toucan-1.5M 是唯一能支撑机制型与指标型主实验的数据集**，
因为它同时具备：大规模（1.65M）、客观 gold label（100% 覆盖）、可自控的检索器（目录文本显式存在）、
以及天然的跨模型/跨情境复制单元（4 个 config）。SWE-ZERO 提供过程与规模，但结局标签效度受限。
AgentTrove、MMAT、AgentInstruct 在当前状态下不能作为结局来源。
