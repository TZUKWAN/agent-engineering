# 五轮审计 · 第 2 轮（R2）：问题清单与修复报告

时间：2026-09-26
视角：R1 之后以"交付物一致性"为主线复查——插图/表格副本、生成脚本可运行性、正文-数据交叉验证、AIB 抽样溯源、测试覆盖。

## 发现并已修复

| # | 问题 | 根因 | 修复 | 验证 |
|---|------|------|------|------|
| R2-1 | `revised/paper01–03_figures/` 全部插图与 `paper01_tables/` 终止阶段表仍为 6-22 旧数据版本，而正文已更新为去重后数字 | R1 只重跑了统计管道；图形/DOCX 由独立脚本生成，未纳入重跑 | 运行 `generate_paper01.py`、`paper02/07_generate_word_paper.py`、`generate_paper03_docx.py`、`paper03/revise_paper03_support.py` 重新生成全部图与 DOCX（python-docx，无需 pandoc），并同步到 `revised/*_figures` | 文件时间戳 09-26；paper02 docx 889KB 含 8 表 6 图 |
| R2-2 | `generate_paper03_docx.py` 等脚本硬编码 `D:/MATLABINTOKEN`，工作空间迁移至 G: 后直接崩溃 | 工作空间移动未同步脚本 | 5 处路径改为相对脚本位置（含 `postprocess_docx.py`、`md2latex.py`、`generate_concept_figure.py`、`merge_and_convert.py`） | paper03 生成器成功输出 8 图 + DOCX |
| R2-3 | `compute_terminal_phase_metrics.py` 在 pandas 2.1.4 下抛 `include_groups` TypeError——6-22 的终止阶段表无法由当前脚本+环境复现 | 脚本按 pandas≥2.2 API 编写，环境为 2.1.4 | 兼容 try/except 双路径；重跑生成新表 | `terminal_phase_*3 张表` 时间戳 09-26 03:46 |
| R2-4 | paper01 表 4（终止阶段）全部统计量为旧值，且"最后一步冗余率显著（p=.001）"的结论在重跑后反转为不显著（p=.620） | 同 R2-1（表未重跑） | 整表 12 处更新 + 解读段落改写（H1c 证据现落在最后 25% 指标与异常短轨迹率上） | 与 `terminal_phase_group_comparisons.csv` 逐格一致 |
| R2-5 | `fig_terminal_phase_comparison.png`、paper03 `fig_interaction_difficulty.png` 无任何生成脚本（历史 ad-hoc 产物）——不可复现 | 交付物与代码脱节 | 前者：在 `compute_terminal_phase_metrics.py` 补 `plot_terminal_comparison()` 并重绘；后者：以重跑的 `fig6_难度类别交互效应.png` 替换 | 两图时间戳 09-26 |
| R2-6 | `paper02/07_generate_word_paper.py` 对新的 moderation 输出抛 KeyError（缺多子任务分组标签） | R1 新增的多子任务分割未被文档生成器感知 | split_map 补标签 + 对未知分组/含 error 子模型安全跳过 | 生成器跑通 |
| R2-7 | `tests/` 为空目录，而 README 宣称含测试代码 | 从未落实 | 新增 `tests/test_pipeline_invariants.py`（5 项核心不变量：task_id 唯一性、去重审计一致性、p∈[0,1]、paper05 表列完备、Stage1/2 模型已注册） | 5/5 PASS |

## R2 复核通过项（未发现问题）

- **正文-数据交叉验证**：`crosscheck_papers.py` 对五篇论文 19 项关键引用（OR/IRR/β/χ²/λ/拐点/p/N）与重跑结果文件逐项核对，全部一致。
- **AIB 抽样溯源**：P002 正文 0.4743/0.2584/0.1188（stage shares）与 0.0957 [0.0845,0.1086]、0.1929（gains）均可追溯至 `tables/*.csv` 并与 `results_processed/EXP0031_truncation_curve.csv` 一致；P001 主文数字体系完整、`reproduce.sh` 遵循"测试评估一次且需 ledger+deviation"的冻结协议。
- **AIB 五探测器复跑**：全部 0 finding（stat / run_reality / claim_support / interval / corpus_remeasure）。

## 遗留（记录，不构成本轮缺陷）

- 合并版 DOCX/PDF（`研究报告_*.docx`、`merged_report_unified.docx/pdf`）仍为 6-22 版本，需 pandoc/LaTeX 环境重新导出；Markdown 已是修正后内容（正文以 Markdown 为准，已在 revision_log 声明）。
