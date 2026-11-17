# 五轮审计 · 最终审计报告（R5 终验 + 总结）

审计时间：2026-09-26（R1–R5 五轮）
工作空间：`G:\刘俊琦\AGENT ENGINEERING`
执行方式：全程本会话直接执行（Bash/Read/Edit/Write + 联网核实），未使用任何子智能体。
过程文档：`ROUND1_PROBLEMS.md`、`ROUND1_REPORT.md`、`ROUND2_PROBLEMS_AND_REPORT.md`、
`ROUND3_PROBLEMS_AND_REPORT.md`、`ROUND4_PROBLEMS_AND_REPORT.md`、本文件。

---

## 一、五轮执行轨迹

| 轮次 | 主线 | 发现并修复 |
|------|------|-----------|
| R1 | 全遍历 + 既有审计器 + 逐项溯源 | AIB：EXP-0156 判定词自描述、run_reality 与记账规则对齐（253 误报→0）、4 孤儿入账、状态账本更新。MATLABINTOKEN：`safe_corr` p 值公式错误（负相关 p→2）、93 个重复 task_id + 合并膨胀（22,625→22,811 行，76 例标签冲突）、顶层试点旧表、paper05 表缺 se/p、五篇正文数字全面更新 |
| R2 | 交付物一致性 | 7 项：revised/ 插图与表格副本过期、5 处硬编码 D: 路径、pandas 兼容性崩溃（终止阶段表不可复现）、paper01 表 4 旧值+结论反转、2 张无生成脚本的图、paper02 文档生成器 KeyError、tests/ 空目录 → 新增 5 项不变量测试（5/5 通过）；19 项正文-数据交叉验证全过 |
| R3 | 内容层一致性 | **AIB 最高优先级缺陷：65 个工厂包 claims 层与证据层矛盾**（verdict_lines 仅按 term 子串匹配、忽略 hypothesis 字段 → 全部误标 not_testable + 样本插值为空）。修复匹配逻辑 + HYP_PICK 映射 + substrate 回退，12 波重组装；残 余 4 行逐一核实为产物自身诚实状态。MATLABINTOKEN：**引用真实性**——联网核实 AgentNet 正确出处为 OpenCUA（Wang et al., 2025, arXiv:2508.14870），修正 Mind2Web/WebGPT/AUSTIN 错配，清除 5 条虚构条目并改挂真实文献；数据字典空壳补全 |
| R4 | 可复现性 | `reproduce.sh` 重写为真实端到端链（旧链产出与论文实际数据源不兼容且缺五篇论文管道）；research_plan/data_dictionary 旧 N 修正；旧稿 4 份加"已被取代"横幅 |
| R5 | 终验 | 与并发会话的 `_round2_final_chain.py`（14 步庄园收尾链）协调；登记调和记录；全套探测器复跑（见下） |

## 二、终验结果（R5，2026-09-26 06:09–06:16）

**AIB 庄园（70 包 / 230 注册实验 / 123 主题）**
- `round2_run_reality`：230 行注册实验，**0 finding**
- `round2_statistical_consistency`：403 个判定行重推导，**0 问题**
- `round2_corpus_remeasurement`：32 dataset-config 重测，**0 finding**
- `round2_claim_support` / `round2_interval_audit`：**0 finding**
- `package_audit`：70 包 missing=none；`spec_completion_audit`：74/74 满足
- 自定义扫描：正文级 not_testable 残留仅 4 行（逐一核实为产物自身如实记录的不可判定/前提受限）；
  claims 引用路径失效 0；字面 `{}` 样本插值 0
- `PROGRAM_STATUS.md` 已由收尾链重生成（05:21），各包判定状态如实呈现
  （如 P018: not_interpretable_length_confound/null/partial；P025: opposite/supported/null）

**MATLABINTOKEN（AgentNet 五篇）**
- `crosscheck_papers.py`：19/19 正文关键引用与重跑结果一致
- `tests/test_pipeline_invariants.py`：5/5 通过
- `12_validate_results.py`：16/16 通过
- 全部表格/图形/正文/合并报告基于去重后 22,532 任务（= 官方 meta_data_merged.jsonl 任务数）

## 三、实质性结论变化（诚实披露）

1. **paper02 Stage-1**：约束有无与完成率的"显著正相关"（OR=1.165, p<0.001）在去重后**不再成立**
   （OR=0.947, p=0.459）——判定为重复 task_id 与合并膨胀造成的假象。Stage-3 调节效应
   （高难度/长指令/多子任务倒 U 形）方向与显著性保持。
2. **paper05 模型 3**：risk_index 直接效应由显著（OR=1.11, p=0.012）变为不显著（OR=1.075, p=0.117），
   与"风险经错误间接起效"的路径论述一致而非冲突。
3. **paper01 表 4**：最后一步冗余率由显著（p=.001）变为不显著（p=.620）；H1c 证据改由最后 25% 指标与
   异常短轨迹率承载。
4. paper01/03/04 其余统计量数值平移，全部定性结论与类别结构保持。

## 四、遗留事项（如实记录，不构成未完成）

1. **合并版 DOCX/PDF**（`revised/研究报告_*.docx`、`merged_report_unified.docx/pdf`）需 pandoc/LaTeX
   重新导出——本机无 pandoc。当前 Markdown（merged_report_unified.md，09-26 生成）为权威内容；
   results/papers/ 下五篇 python-docx 生成的单篇 DOCX 已是新版。
2. **AIB premise-blocked 的 9 个包**（P048/049/054/055/057–061）维持庄园既定的"前提受阻"状态，
   引用共享测量 EXP-0190/0196/0203，非本轮范围。
3. **number_provenance 的两类提示**（129 个无数值列的判定词表、53 个跨包共享测量引用）为庄园既有
   约定下的可见性提示，已逐类抽查确认非数据缺陷。
4. **aib_repro_20260918**（9-18 冻结快照）与 **_cleanroom**（洁净房复现环境）维持冻结，无需变更。
5. 根目录 `01_datasets/` 仅含 manifests 副本（与主庄园一致），未删除用户文件。

## 五、审计产物清单（audit_5rounds/）

- `ROUND1_PROBLEMS.md` / `ROUND1_REPORT.md`
- `ROUND2_PROBLEMS_AND_REPORT.md`
- `ROUND3_PROBLEMS_AND_REPORT.md`
- `ROUND4_PROBLEMS_AND_REPORT.md`
- `FINAL_AUDIT_REPORT.md`（本文件）
- `check_claims_paths.py`、`crosscheck_papers.py`（可重复运行的回归防护）
- `patch_paper01–05.py`（五篇正文数字修订的可追溯补丁脚本）
