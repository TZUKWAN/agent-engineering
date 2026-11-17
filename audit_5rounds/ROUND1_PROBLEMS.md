# 五轮审计 · 第 1 轮问题清单（R1）

审计时间：2026-09-26
审计范围：`agentic-information-behavior`（P001–P070）、`MATLABINTOKEN`（paper01–05）、`aib_repro_20260918`、`_cleanroom`、根目录 `01_datasets`
方法：运行庄园既有审计器（package_audit / round2_statistical_consistency / round2_number_provenance / round2_claim_support / round2_interval_audit / round2_run_reality）+ 人工逐项溯源检查（禁止子智能体，全部本会话直接执行）。

---

## A. agentic-information-behavior（AIB 庄园）

### A1 [数据-判定词] EXP0156（P025_contradiction_and_modality）H2 判定与审计器重算不一致 — 待修复
- 现象：`EXP0156_wave4_design_0156_20260926T004151.json` models[1]（H2, changed-vs-different contrast）beta=-0.0363, CI [-0.0552,-0.0174], p_holm=0.0006，行印 `supported`；审计器 `round2_statistical_consistency` 按通用 floor=0.15 规则重算得 `partial`，报 verdict_not_implied_by_its_own_numbers。
- 溯源：T126 冻结 thresholds 含 H2 专门条款 "H2 is supported when the changed-vs-different difference has CI excluding 0"，CI 确实不含 0 → 按冻结条款 supported 是对的；但行未声明自己的 verdict_rule，审计器只能按通用规则重算。
- 修复方案：行内声明 `verdict_rule: "h2_ci_excludes_zero"`（引用冻结句），审计器识别该冻结规则并按“CI 不含 0 + p_holm<0.05”重算；重跑探测器确认为 0 finding；P025 无需改数（结论不变），在 deviations/W4 记录本轮审计说明。

### A2 [审计器缺陷] round2_run_reality 与 EXP-0229 记账规则不一致 → 253 个误报 — 待修复
- 现象：run_reality 报 253 个 artefact_generation_no_registry_row_declares，其中 239 个其实已被包证据文件夹引用（按 EXP-0229 约定“包引用即入账”），10 个为 shared-stem，真正未入账仅 4 个。前轮修复声明“重跑为 0”，与本次 253 矛盾——两个工具规则不同步。
- 修复方案：run_reality 增加“包引用豁免 + shared-stem 豁免”（与 supersede_undeclared_generations.census 同一规则），重跑后应只剩 4 个真孤儿。

### A3 [账本缺口] 4 个真孤儿文件 — 待修复
- `results_processed/EXP0143_wave3_query_features.csv`：EXP-0143 同 run 的伴生输出未登记 → 溯源核实后并入 EXP-0143 outputs。
- `results_raw/EXP0207_wave11_agenttrove_structure_scan_20260924T220813.json`：与行声明的 premise_census 同前缀不同 stem → 逐字段比对后按“早期/旁支生成”退役入 SUPERSEDED_ARTIFACTS.json。
- `results_raw/EXP0224_round2_verification_sweep_20260925T222142.json`：EXP-0224 的后继生成 → 比对后退役或改指向。
- `results_raw/EXP0229_generation_bookkeeping_20260925T221705.json`：EXP-0229 自身报告的另一生成 → 比对后退役。

### A4 [包交付] P001 只装被退役代（EXP0032）误报 + kept 选择缺陷 — 待修复
- run_reality 以“最新 mtime”选 kept，对多产物行选了 results_processed 的 CSV，再用 CSV 文件名到包内查 JSON → 误报 package_ships_only_a_superseded_generation。P001 实际同时装有 3 个 JSON（含 kept 235222）。修 kept/交付检查逻辑（同 stem 才比较）。

### A5 [状态账本] ROUND2_PROBLEM_STATUS 中 claim_support|cited_table_not_in_package 仍标 open — 待修复
- 本轮以脚本复核 70 包 claims_evidence_matrix 引用路径：0 项失效 → 该项实际已修，更新状态并注记验证方式与时间。

### A6 [复检待办] gates18 / spec_completion / corpus_remeasurement 本轮后台重跑，结果并入 R1 修复验证。

---

## B. MATLABINTOKEN（AgentNet 五篇）

### B1 [统计错误·高危] `safe_corr` p 值公式完全错误（08_fit_models.py:36、09_robustness_checks.py:33）— 待修复
- `p = 2*(1 - 0.5*(1+sign(t)*(1-exp(-t²/2))))`：负相关时 p→2（表3 中 RQ3 两行 p=1.99999… 即此 bug），正相关时也严重失真（RQ1 r=0.105,n=200 印 p=0.329，真值 ≈0.138）。
- 修复：改用 scipy.stats.pearsonr 的精确 p；重跑 08/09，重生成 results/models/main_results.json、results/tables。

### B2 [数据完整性·高危] AgentNet 原始轨迹文件含 93 个重复 task_id，被管道放大 — 待修复
- 实测：ubuntu_5k(5,000)+win_mac_18k(17,625)=22,625 行，唯一 task_id=22,532；官方 meta_data_merged.jsonl 恰 22,532 条。93 个重复 id 中 91 个同指令，其中 76 个标签互相冲突（task_completed/alignment 等），2 个指令文本也不同。
- 放大链：tasks.parquet 22,625 行 → 06_build 按 task_id 与 process_features(22,532) 多对多 merge → analysis_data.parquet 22,811 行（+186 笛卡尔积行）。paper01–03 全部基于该文件（正文 N=22,811 / 主模型 20,484）。paper04/05 自行解析 raw，同样含重复（analysis_ready 20,298 行/20,205 唯一）。
- 修复：以 meta_data_merged 的 22,532 唯一 task_id 为准，解析/建库阶段 first-occurrence 去重并输出审计文件（记录 93 个被删 id 与标签冲突清单）；重建 analysis_data（应为 22,532 行）并加唯一性断言；重跑 paper01–05 全部下游表格/图形；更新五篇正文所有受影响 N 与统计量；revision_notes 记录。

### B3 [陈旧产物] 顶层 results/tables 为 200 行试点时代的旧产物 — 待修复
- table2_descriptive_stats.csv（n=200）、table3_main_results.csv（n=200 且含 p=2.0）与现行论文（N≈20,484）矛盾。随 B1/B2 重跑一并重生成。

### B4 [证据链] paper05 model1/model2 表只有 coef 列，无 se/p，但正文引用 p<0.001 — 待修复
- 修复：生成表时输出 se/z/p；重跑并更新正文引用。

### B5 [统计稳健性] paper05 model3 存在准完全分离迹象（execution_error_index OR=0.025, p≈1e-276；截距 OR≈1.4e6）— 待修复
- 修复：在 limitation 注明分离/近确定性路径问题（错误指数由 last_step_correct 构建，与完成标签近共线），不删除结果。

### B6 [文档] final_report.md 写“22,625 条任务” — 待修复
- 修复后改为 22,532（去重后），并注记 93 个重复 id 的处理。

### B7 [卫生] 根目录 `nul` 文件（Windows 保留名残留）— 删除。

---

## C. aib_repro_20260918
- 定性：2026-09-18 首日冻结快照（仅 P001，Toucan 数据），与主庄园 9-18 记录一致，未发现需修改项。本轮维持冻结，仅归档说明。（无动作）

## D. _cleanroom
- 定性：P001–P005 的洁净房复现环境（9-20 冻结）。主庄园 P001–P005 本轮无数据变更，无需重跑。（无动作）

## E. 根目录 01_datasets
- 仅含 manifests 副本（461KB）。与 agentic-information-behavior/01_datasets/manifests 比对一致性后，在 R1 报告中注明其地位（暂不删除用户文件）。

---

## 修复执行顺序
1. B1（公式修复）→ B2/B3（去重重建+重跑五篇管道）→ B4/B5/B6/B7。
2. A2/A4（审计器逻辑对齐）→ A1（行声明+探测器识别）→ A3（4 孤儿入账）→ A5（状态更新）→ A6 复检。
3. 全部修复后重跑全部 AIB 审计器 + 本轮自定义检查，写入 R1 修复验证报告。
