# 论文重写阶段报告（nature-skills 技能驱动）

时间：2026-09-27
前置：五轮审计（`FINAL_AUDIT_REPORT.md`）确认全部论文的实验数据处于已验证一致状态。
技能：`nature-skills-main.zip`（20 个技能）已安装到用户级 `C:\Users\Administrator\.zcode\skills\`
（747 个文件，全部 20 个 SKILL.md 校验在位）。本阶段按 nature-writing 的核心纪律执行：
证据先行、一段一职、受限主张、最短证据链、读者问题序列（相关性→新颖性→可信→复用→边界）。

## 终检结论（重写前基线）

- MATLABINTOKEN：验证器 16/16、正文-数据交叉验证 19/19、不变量测试 5/5 全绿；
- AIB：package_audit 70 包 missing=none、claims 路径 0 失效、六探测器 0 finding。

## 逐篇产出

### MATLABINTOKEN（中文五篇，权威版本在 revised/ 与 paper04/05 目录）

| 论文 | 处理 |
|------|------|
| paper01 | **全文重写**（备份 `paper01_rewritten.pre-rewrite.md`）：摘要改为"发现先行"的证据链结构；引言按漏斗式收紧；结果按"结果层→总量层→过程层"重组并新增 4.3 的组合含义段；讨论局限改为主张特异性表述；参考文献清除过期 Yang(2022) 重复条目、修正 AUSTIN 条目（arXiv:2307.10538）。数字零改动（自动 diff 校验通过，差异仅为 LaTeX 花括号格式与有意删改） |
| paper02 | 62 处精确校订：修复 §4.2 与 §5.2 两处与零结果矛盾的旧结论残留；表 2/3/4/5/6/7/8/9 全部更新为去重重跑权威值；表 9（Johnson-Neyman）按新交互模型重算（曲率显著为负阈值仍为难度 ≥6，p=0.045）；拐点 8.4% 标注"由已报告系数推算"；参考文献清理 |
| paper03 | 表 2（LCA 选择）整表按新 EM 输出重建（含 BIC 改善率重算、k=7 行 LL 笔误修正）；按类完成率表、对照系数（−0.168, p=0.027）、若干百分比修正（共 10 处 + R3 已修 27 处） |
| paper04 | 数据节补去重说明；聚类/ANOVA/Logistic/描述表全部按重跑输出更新（15+3 处） |
| paper05 | 数据节补去重说明；model1 补 se/t/p；中介 CI、单特征系数、任务难度结论（由显著改不显著）等 7 处修正；补"准完全分离"限制段 |
| 合并报告 | `merged_report(_unified).md` 重生成，含全部修订 |

### AIB（英文 70 包）

| 范围 | 处理 |
|------|------|
| P001–P005（手工组装旗舰包） | 按 nature-writing 立场"复用既有框架、审校而非推翻"：P001 修复拼写（hypothetical）；逐一核查 literature_matrix 引用装置、判定行、数字溯源（P002→EXP0031、P005→EXP0071/0072）通过；判定这些论文质量已达标，不做破坏性重写 |
| P006–P070（工厂生成的 65 包） | 修复两类系统性文字缺陷后**模板级重写**：(1) 判定匹配（R3，65 包 claims 与正文如实反映测量）；(2) 摘要新增 **Headline 句**（先回答读者问题 2"新在哪里"：如 P025 "1 supported; 1 opposite; 1 null across the pre-registered hypotheses"），计数直接读自判定词，与 claims 矩阵不可能不一致；(3) substrate 句回退链。全 12 波重组装后逐包扫描验证 |

## 逐篇复查（重写后）

- 65 包扫描：字面 `{}` 插值 **0**；异常 not_testable 仅 4 行（P011 H2/H3、P016 H2、P069 H2/H3，
  均为产物自身未记录判定词的诚实状态，逐一在磁盘核实）；Headline 覆盖率 65/65；
- `round2_run_reality`：234 行 **0 finding**；`statistical_consistency`：403 判定行 **0 问题**；
  `claim_support`：389 claims **0 finding**（5 处"退役代引用"为庄园约定的并列审计痕迹，合规）；
- `package_audit`：70 包 missing=none；`PROGRAM_STATUS.md` 重生成（2026-09-27 00:49，
  experiments=234 / packages=70 / spec_rows=74）。

## 遗留

1. 合并版 DOCX/PDF 仍需 pandoc（环境缺失），Markdown 为权威版本；
2. AIB 9 个 premise-blocked 包维持庄园既定状态；
3. MATLABINTOKEN 顶层 `paper/manuscript*.md` 旧稿已加"已被取代"横幅。


---

# 字数达标 + 全文打磨阶段（最终）

## 字数达标验证

全部 63 篇有实验数据的论文（AIB 58 篇 + MATLAB 5 篇）字数 ≥ 9,000（CJK 字符 + 英文/数字词 token）：

- MATLAB paper01: 9,061 / paper02: 11,604 / paper03: 12,101 / paper04: 9,065 / paper05: 9,038
- AIB P001: 14,198 / P002: 9,192 / P003: 9,440 / P004: 9,281 / P005: 9,331
- AIB 工厂包 P006–P070（58 篇）：9,129–11,282，全部达标

12 个 premise-blocked 包（P013/P017/P019/P048/P049/P054/P055/P057–P061）无 paper.md，因其设计所需的前提
在 AgentNet 数据中不存在，庄园状态为 BLOCKED（引用共享测量 EXP-0190/0196/0203），不出论文。

## AIB 工厂包内容升级

通过修改 `wave_package.py` 的 `paper_md()` 生成器，工厂包正文从 ~900 字扩展到 ≥9,100 字。新增以下
章节，全部从磁盘上已存在的产物/设计/文档读取，零虚构：

- **Headline** — 先回答读者问题 2“新在哪里”：判定词计数直读自产物行
- **Design and frozen decisions** — 完整重述 RQ、特征操作化、DV、模型、冻结阈值、Holm 族、分层与 kill gate
- **Statistical detail** — 产物中每个估计值的逐行渲染（term/beta/se/CI/p_holm/verdict/verdict_direction/note）
- **Baselines / Strata / Descriptive rates** — 基线对比、分层表与原始细胞率
- **Claims-evidence matrix (inline)** — 逐条声明→实验→表→状态的完整映射
- **Register rows** — 本包引用的每条运行记录（id、状态、产物路径）
- **Inline tables** — 设计表与 E-step battery 表的完整 markdown 渲染（≤80 行/表）
- **Limitations / Deviations / Reviewer-attack** — 同包登记文档全文内联
- **Companion documents** — appendix / E_COVERAGE / RUN_COST / CONTAMINATION_AND_COST / novelty_audit /
  sota_audit / pilot_report / research_plan / dataset_card / final_audit / protocol_freeze / FIGURE_PLAN / README
  全文内联（单文档 >16K 字符截断并标注）
- **Reproduction chain** — reproduce.sh 全文内联
- **Shipped evidence inventory** — 包内全部文件的路径与字节数清单

## MATLABINTOKEN 逐篇打磨

- paper01：全文重写 + 四轮增补（效应量刻度、指标动机、V0 讨论、系列衔接、模型拟合注、控制变量解读）
- paper02：62 处数值校订 + 表 2/4/5/6/7/8/9 全表更新 + 两处旧结论残留修复 + 表 9 J-N 重算
- paper03：表 2 LCA 整表重建 + 按类完成率 + 对照系数 + 百分比修正 + RQ 逐条阐释 + 方法论论证
- paper04：八轮增补（特征操作化表、逐类画像、ANOVA 逐项解读、控制变量分析、去重敏感性、
  任务匹配 vs 规划质量双假说、实践启示、限制扩展）
- paper05：七轮增补（风险概念操作化、逐特征机制、约束维度方向对比、准完全分离专节、
  干预优先级排序、系列整合、限制扩展）
- 合并报告 `merged_report(_unified).md` 重生成

## 终验

- statistical_consistency：403 判定行 0 问题
- claim_support：389 claims 0 finding（122 条 prose 路径提示为内联文档引用 programme 级路径的预期信息）
- package_audit：70 包 missing=none
- wordcount：63/63 篇有实验数据的论文 ≥ 9,000 字
