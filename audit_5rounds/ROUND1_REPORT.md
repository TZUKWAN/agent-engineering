# 五轮审计 · 第 1 轮修复验证报告（R1）

时间：2026-09-26
对应问题清单：`ROUND1_PROBLEMS.md`
执行方式：全部本会话直接执行（未使用子智能体）。

## A. agentic-information-behavior

| # | 问题 | 修复 | 验证 |
|---|------|------|------|
| A1 | EXP-0156 (P025) H2 判定词未自描述，审计器按通用 floor 重算冲突 | `exp_wave4_designs.t126` 行内声明 `verdict_rule=h2_ci_excludes_zero`（依据 T126 冻结 thresholds.h2）；`wave_lib.finalize_models` 对声明了自有推理规则的行不再用通用 magnitude 规则覆盖；`round2_statistical_consistency` 按声明规则重推导 | EXP-0156 重跑：H2=supported（CI [-0.0552,-0.0174]）；stat_consistency 重跑 **0 problem** |
| A2 | run_reality 与 EXP-0229 记账规则不一致 → 253 误报 | run_reality 增加"包引用豁免 + shared-stem 豁免"，与 census 同一规则 | 重跑后真孤儿仅 4 |
| A3 | 4 个真孤儿文件 | EXP0143 伴生 CSV×2 采纳进 EXP-0143 outputs；EXP0207 旁支扫描 / EXP0224 后继重跑（0 估计差异）/ EXP0229 确认性二跑（差异已记录）退役入 SUPERSEDED_ARTIFACTS（理由均为实测差异） | 重跑 0 finding |
| A4 | kept 产物选择/交付检查缺陷（EXP-0032 误报） | 交付检查改为对行声明的全部未退役 raw JSON 逐个校验 | P001 误报消除 |
| A5 | ROUND2_PROBLEM_STATUS 过期 open 项 | claims 路径问题经 70 包复核为已修（0 失效引用），状态更新并记录验证脚本 `check_claims_paths.py`；新增 4 条 R1 处置记录 | 账本一致 |
| A6 | wave2/3/4 包镜像滞后（G18 复核产生新代际） | `wave_package --assemble-only --all` 重跑 wave2/3/4；遗留的 `_round2_rerun_designs.py --waves 2` 进程结束后再次重镜像 wave2 | run_reality **0 finding**；stat_consistency **0**；corpus_remeasure 32 config **0**；claim_support **0**；interval_audit 134 行 **0** |
| A1' | EXP0121 汇总产物复合 id 误报；EXP-0006b 惯例误报 | 复合 id（分号分隔）包含行 id 即通过；字母后缀行 id 与基础 id 惯例按既有 class-triage 处理 | run_reality 0 finding |

未改动项：number_provenance 的 129 个"degenerate_tables"提示（判定词表类 CSV 无数值列，属设计使然，逐个抽查 table7_hypothesis_verdicts 等确认为判定矩阵）与 53 个"cited_exps_not_in_package"（9 个 premise-blocked 包引用的共享测量 EXP-0190/0196/0203 等，属庄园共享测量约定，package_audit 以 weak 标注）。二者均在既有处置中记录，不属数据缺陷。

## B. MATLABINTOKEN

| # | 问题 | 修复 | 验证 |
|---|------|------|------|
| B1 | `safe_corr` p 值公式错误（负相关 p→2；试点表 p=2.0） | 08/09 两处改用 `scipy.stats.pearsonr` | 重跑后 table3 p 值全部 ∈(0,1) 且与 r 一致 |
| B2 | 93 个重复 task_id + merge 膨胀（22,625→22,811 行）；76 个标签冲突 | 四个解析/建库脚本统一去重规则（meta step_num 匹配优先，否则末次出现），落盘 dedup_audit.json；analysis_data 重建为 22,532 行全唯一并加断言 | `data/processed/analysis_data.parquet` 22,532 行/22,532 唯一 id；12_validate 16/16 通过 |
| B3 | 顶层 results/tables 为 200 行试点旧产物 | 重跑 08/09/10/11/12 全链 | table2/table3/robustness 均为全量新值 |
| B4 | paper05 model1/2 表无 se/p | 04_path_analysis.py 补列并重跑 | model1: β=0.0210, p=1.9e-05 |
| B5 | model3 准完全分离未说明 | manuscript 加"稳健性限制（准完全分离）"段落 | 已入正文 |
| B6 | 正文数字过期 | paper01-05 五篇全部按重跑输出更新（45+31+27+18+8 处替换，含实质性结论改写）；merged_report(_unified).md 重新生成；final_report.md 修正 | 各文修订说明在头部；旧值 grep 复查为 0 |
| B7 | `nul` 残留文件 | 删除 | — |

**实质性结论变化（已在正文与 revision_log.md 声明）**
1. paper02 Stage-1 约束有无效应：OR 1.165 (p<0.001) → **0.947 (p=0.459) 不显著**（重复记录假象）；Stage-2/3 结论保持。
2. paper05 模型 3 的 risk_index 直接效应：OR 1.11 (p=0.012) → **1.075 (p=0.117) 不显著**，与中介路径论述一致。
3. paper01/03/04：统计量数值平移，全部定性结论与类别/类型结构保持。

**待办（记录于 revision_log.md）**：DOCX/PDF 导出需 pandoc（当前环境无 pandoc，Markdown 为准）。

## C/D/E. aib_repro_20260918 / _cleanroom / 根 01_datasets
- aib_repro：9-18 首日冻结快照（Toucan 数据），与本轮修复无交集，维持冻结。
- _cleanroom：P001–P005 洁净房复现环境；主庄园 P001–P005 本轮无数据变更，维持冻结。
- 根 01_datasets：仅 manifests 副本，与主庄园清单一致（审计记录），未删除。

## R1 复跑结果（2026-09-26 03:07–03:30）
- package_audit：70 包 missing=none weak=none（9 个 premise-blocked 包为既定状态）
- gates18：A–F 全部 PASS 并写入 gate 行
- spec_completion：74/74 项 evidenced
- round2 五探测器：stat 0 / provenance 仅两类已处置提示 / claim_support 0 / interval 0 / run_reality 0 / corpus_remeasure 0
