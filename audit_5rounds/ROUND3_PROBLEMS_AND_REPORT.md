# 五轮审计 · 第 3 轮（R3）：问题清单与修复报告

时间：2026-09-26
视角：内容层一致性——claims 层 vs 证据层、生成器与产物的 schema 匹配、引用真实性、并发修改监控。

## A. agentic-information-behavior

### A-R3-1 [系统性缺陷·最高优先] 65 个工厂生成的包"claims 层与证据层矛盾" — 已修复
- 现象：P006–P070 中 65 个包的 `paper.md` 与 `claims_evidence_matrix.csv` 将预注册假设标记为
  `not_testable`、摘要样本插值打印字面 `{}` 与 "not measured in this run"，而同包 `tables/table3_main_models.csv`
  载有完整测量判定（supported/opposite/null/partial）。
- 根因（代码级）：`wave_package.verdict_lines()` 只按模型行的 `term` 子串匹配假设标签；waves 3+ 的产物
  行携带 `hypothesis: "H1/H2/H3"` 字段但 term 名不含标签 → 匹配失败 → 全部落 not_testable。样本插值读取
  的 matrix 字段在 wave≥2 的 step-features 帧里不存在。
- 修复：`verdict_lines` 先按 `hypothesis` 字段精确匹配；新增构建器级 `HYP_PICK` 映射（EXP-0121/0124/0126/0140
  的 tag→block/term/verdicts 位置，全部对照磁盘产物核实）；摘要 substrate 句加回退链
  （n_turns/n_trajectories/无则声明"sample sizes are recorded inside the design artefact"）。
- 验证：全 12 wave `--assemble-only` 重组装后全量扫描，65 → 6 包含 not_testable 字样；再修 wave1/2 映射
  后仅余 4 行，逐一核实为产物自身如实记录的不可判定/前提受限（P011 H2/H3 产物仅记录 H1 判定词、
  P016 H2 交互块无判定词、P069 H2 β=0 与 G10 前提受限），属诚实状态而非匹配失败。

### A-R3-2 [账务] 重组装与复核产生的 8 个后继代际 — 已处置
- EXP0099/0103×4/0224/0228/0229 的验证性重跑：逐一用庄园比较器量化差异后退役入
  SUPERSEDED_ARTIFACTS（EXP0099 反映规格状态变化 → 注册行重指向最新代）；其中 4 个已被庄园自身的
  --apply 流程先行处置。复核后 --check 与 run_reality 归零（见 R5 终验）。

### A-R3-3 [并发会话] 检测到另一会话的 `_round2_final_chain.py` + `_reassemble_all_waves.py`（04:49 启动）
- 处置：不与之竞争写入；其链条共用本会话修复后的 `wave_package.py` 代码，方向一致。终验安排在
  R5（链条停止后）执行。

## B. MATLABINTOKEN

### B-R3-1 [引用真实性·最高优先] 数据集与智能体文献引用错配/虚构 — 已修复
- 事实核查（联网核实）：AgentNet 的正确出处是 **OpenCUA: Open Foundations for Computer-Use Agents**
  （Wang et al., 2025, arXiv:2508.14870；原始数据自带 README 即该论文页），而非 "Zhang, Y. (2024)
  AgentNet: A large-scale dataset..."（虚构）；Mind2Web 实为 Deng et al., NeurIPS 2023（非 Yang 2022）；
  WebGPT 实为 Nakano et al., 2021, arXiv:2112.09332（非 Pal 2022 NeurIPS）；AUSTIN 实为 Yuan et al.,
  arXiv:2307.10538（题目/venue 已修正）。
- 虚构条目 `goedert2013instruction`（Human Factors 2013 无此文）、`liang2020language`（GPT-3 标题嫁接）、
  `schatz2003task`、`lasecki2013crowdsourcing`、`li2024survey`：正文引用句改挂已核实的真实文献
  （Sweller 1988、Payne et al. 1993、Deng 2023、Nakano 2021、Wang 2025），参考文献列表与
  `paper/references.bib` 同步删改。
- 波及文件：五篇正文 + references.bib + merge/restructure 脚本内嵌文本。合并报告重生成
  （`Wang et al` ×9，`22{,}811|20{,}484` 0 处）。

### B-R3-2 [文档] data_dictionary.md / research_plan.md 为"待下载/待确认"空壳或含旧 N — 已修复
- 根 `data_dictionary.md` 补真实下载记录（commit、日期、文件清单）、去重规则与审计文件位置；
  paper04/05 的 data_dictionary 与 research_plan 的样本量更新为 22,532/416,186 并注明去重。

## R3 复核通过项
- P002 逐级溯源（正文→包表→results_processed EXP0031）一致；P005 链接可得性 0.9615/0.9394 溯源至
  EXP-0071/0072 ✓；P025 表 3 已携带 `verdict_rule=h2_ci_excludes_zero` 列 ✓。
- `crosscheck_papers.py` 19/19 通过（R2 引入的回归防护）。
- `tests/test_pipeline_invariants.py` 5/5 通过。
