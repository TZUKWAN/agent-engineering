# 五轮审计 · 第 4 轮（R4）：可复现性与文档一致性

时间：2026-09-26
视角：换一条主线——"一个新人拿到工作空间，能否按文档从零复现论文"。

## 发现并已修复

| # | 问题 | 修复 |
|---|------|------|
| R4-1 | `reproduce.sh` 走的是旧 03–06 链：`06_build_analysis_data.py` 产出的 schema 缺 `instruction`/`os`，paper01/02 脚本会直接崩溃；且不含 paper01–05 五篇论文管道、不含 dedup | 重写 `reproduce.sh`（16 步）：以 `reanalyze_full_data.py`（去重+文本列+os）为数据主链，纳入五篇论文全部脚本、终止阶段指标、DOCX 生成器（python-docx）、不变量测试与合并报告；旧版存档为 `reproduce_legacy_v1.sh.bak` |
| R4-2 | paper04/05 `research_plan.md`、`data_dictionary.md` 样本量为旧值 22,625/421,453 | 更新为 22,532/416,186 并注明去重规则与审计文件位置 |
| R4-3 | 根 `data_dictionary.md` 为"待下载/待确认"空壳（下载已发生 3 个月） | 补齐：commit d76ee50a、下载时间、文件清单、93 个重复 id 的裁决规则与 dedup_audit.json 位置 |

## 复核通过项
- AIB 侧 P025/P018 重组装后正文、claims、表格、`verdict_rule` 四层一致。
- MATLABINTOKEN 五篇正文数字与重跑结果 19 项交叉验证持续通过（`crosscheck_papers.py`）。
- 本轮未发现新的统计或数据缺陷。

## 并发说明
AIB 工作区存在另一会话的 `_round2_final_chain.py`/`_reassemble_all_waves.py`（04:49 启动）在执行全量
重跑+重组装。其共用本审计修复后的 `wave_package.py`（判定匹配修复对其生效）。终验（R5）在该链条
结束后统一执行，避免写入竞争。
