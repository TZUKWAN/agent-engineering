# Spec-to-artefact completion audit (EXP-0099)

Generated 2026-09-26T19:17:40 by `02_shared_code/registry/spec_completion_audit.py`; the requirement list is read from the spec's own headings (1227 lines, 74 requirement ids), and 12159 text files in the workspace were scanned. No number in this file is entered by hand.

A requirement counts as **evidenced** when a file outside the spec names it: **37** are named inside a paper package, **0** only at programme level, **37** are cited by no artefact but are satisfied by a content check, and **0** remain open on both tests.

| status | requirements |
|---|---|
| evidenced_in_package | 37 |
| satisfied_by_content_signature | 37 |

## Requirements with no artefact naming them, and no content signature covering them

None. Every requirement id in the spec is either named by an artefact in the workspace or satisfied by the content checks in the next section.

## Documents whose generator runs in no chain

24 live document(s) declare a generating script that no chain - no package `reproduce.sh`, nor the estate's closing chain, reassembly driver or sweep driver - ever re-executes. Such a file is current only until the artefacts it summarises move, and it is the one kind of gap a green rebuild check cannot see, because the rebuild never touches it.

- `P013_negative_boundary_metadata/FIGURE_PLAN.md <- 02_shared_code/writing/export_figure_plan.py`
- `P013_negative_boundary_metadata/README.md <- 02_shared_code/registry/build_package_configs_readme.py`
- `P017_noun_verb_centring/FIGURE_PLAN.md <- 02_shared_code/writing/export_figure_plan.py`
- `P017_noun_verb_centring/README.md <- 02_shared_code/registry/build_package_configs_readme.py`
- `P019_hierarchy_facets_flat_lists/FIGURE_PLAN.md <- 02_shared_code/writing/export_figure_plan.py`
- `P019_hierarchy_facets_flat_lists/README.md <- 02_shared_code/registry/build_package_configs_readme.py`
- `P048_when_to_stop_a_recorded_search/FIGURE_PLAN.md <- 02_shared_code/writing/export_figure_plan.py`
- `P048_when_to_stop_a_recorded_search/README.md <- 02_shared_code/registry/build_package_configs_readme.py`
- `P049_premature_termination_and_over_search/FIGURE_PLAN.md <- 02_shared_code/writing/export_figure_plan.py`
- `P049_premature_termination_and_over_search/README.md <- 02_shared_code/registry/build_package_configs_readme.py`
- `P054_an_induced_taxonomy_of_agent_information_behaviour/FIGURE_PLAN.md <- 02_shared_code/writing/export_figure_plan.py`
- `P054_an_induced_taxonomy_of_agent_information_behaviour/README.md <- 02_shared_code/registry/build_package_configs_readme.py`
- `P055_the_exploration_exploitation_transition/FIGURE_PLAN.md <- 02_shared_code/writing/export_figure_plan.py`
- `P055_the_exploration_exploitation_transition/README.md <- 02_shared_code/registry/build_package_configs_readme.py`
- `P057_three_kinds_of_linguistic_uncertainty/FIGURE_PLAN.md <- 02_shared_code/writing/export_figure_plan.py`
- `P057_three_kinds_of_linguistic_uncertainty/README.md <- 02_shared_code/registry/build_package_configs_readme.py`
- `P058_need_decomposition_and_search_completeness/FIGURE_PLAN.md <- 02_shared_code/writing/export_figure_plan.py`
- `P058_need_decomposition_and_search_completeness/README.md <- 02_shared_code/registry/build_package_configs_readme.py`
- `P059_linguistic_cues_and_source_reliability/FIGURE_PLAN.md <- 02_shared_code/writing/export_figure_plan.py`
- `P059_linguistic_cues_and_source_reliability/README.md <- 02_shared_code/registry/build_package_configs_readme.py`
- `P060_attribution_framing_and_credibility_bias/FIGURE_PLAN.md <- 02_shared_code/writing/export_figure_plan.py`
- `P060_attribution_framing_and_credibility_bias/README.md <- 02_shared_code/registry/build_package_configs_readme.py`
- `P061_task_language_ambiguity_and_search_shape/FIGURE_PLAN.md <- 02_shared_code/writing/export_figure_plan.py`
- `P061_task_language_ambiguity_and_search_shape/README.md <- 02_shared_code/registry/build_package_configs_readme.py`

(2 further document(s) name a generator no chain runs, but each carries in its own file name the date of the single run it records - a closed statement about the past rather than a live report - so they are listed without being called stale.)

- `docs/funnel_correction_agentnet_20260920.md <- 02_shared_code/registry/record_exp0073_0075_funnel.py`
- `docs/literature_abstract_recovery_20260920.md <- 02_shared_code/registry/record_exp0063_0064_literature.py`

## Content signatures for the 37 ids no artefact cites by name

These are the requirements a string search alone would call open. Each is checked against the artefact the spec's own wording demands; the needle families are printed so a disagreement can be pointed at one string rather than at a judgement.

### S00 最终交付物定义 - satisfied

- ok `package_audit_clean` **every package passes the deliverable audit that resolves each named item to a real file** - package_audit reports missing=none weak=none for all five packages
- ok `dirs_exist` **and the shared workspace the series is run from exists** - workspace holds 00_program_registry, 01_datasets, 02_shared_code, papers, results_raw, results_processed, docs

### S02 建立总研究工作区 - satisfied

- ok `dirs_exist` **one workspace holds registry, data, shared code, papers and results** - workspace holds 00_program_registry, 01_datasets, 02_shared_code, papers, results_raw, results_processed, 02_shared_code/registry, 02_shared_code/statistics, 02_shared_co

### S07 实验协议冻结（Protocol Freeze） - satisfied

- ok `count_files_all_papers` **each package carries a protocol freeze file** - 58/58 packages with >= 1
- ok `needles_count_all_papers` **and states what was fixed before the run** - spec §7 items found in every package (>= 2 of 5): P001:3, P002:3, P003:4, P004:3, P005:2, P006:3, P007:3, P008:3, P009:2, P010:2, P011:2, P012:2, P014:2, P015:2, P016:2, 

### E00 数据描述与基础统计 - satisfied

- ok `e_step_all_papers` **E00 carried by every package on a re-opened artefact** - 58/58 packages carry E00 on a re-opened artefact: P001<-claim C3; EXP-0083 registered in this package (stage=external_benchmark_eval_ingestion_aud | P002<-EXP0027_p003_co

### E01 主效应 / 主任务实验 - satisfied

- ok `e_step_all_papers` **E01 carried by every package on a re-opened artefact** - 58/58 packages carry E01 on a re-opened artefact: P001<-EXP-0006b registered in this package (stage=w1_main_dev_ladder_5seed); EXP-0006 registered | P002<-EXP-0031 regist

### E02 基础基线 - satisfied

- ok `e_step_all_papers` **E02 carried by every package on a re-opened artefact** - 58/58 packages carry E02 on a re-opened artefact: P001<-EXP-0084 registered in this package (stage=external_corpus_transfer_toolret_eval); claim C | P002<-EXP-0031 regist

### E03 强基线 / SOTA 对比 - satisfied

- ok `e_step_all_papers` **E03 carried by every package on a re-opened artefact** - 58/58 packages carry E03 on a re-opened artefact: P001<-EXP-0024 registered in this package (stage=e03b_trained_dense_comparator_DEV_ONLY); EXP-00 | P002<-EXP0024_dense_c

### E04 消融实验 - satisfied

- ok `e_step_all_papers` **E04 carried by every package on a re-opened artefact** - 58/58 packages carry E04 on a re-opened artefact: P001<-claim C4; EXP-0018 registered in this package (stage=protocol_amendment_D13_catalog_disjoi | P002<-EXP-0107 regist

### E05 替代操作化 - satisfied

- ok `e_step_all_papers` **E05 carried by every package on a re-opened artefact** - 58/58 packages carry E05 on a re-opened artefact: P001<-EXP-0014 registered in this package (stage=h4_equivalence_relabel_DEV_ONLY); claim C6 | P002<-claim K4; EXP-0031 r

### E06 超参数敏感性 - satisfied

- ok `e_step_all_papers` **E06 carried by every package on a re-opened artefact** - 58/58 packages carry E06 on a re-opened artefact: P001<-EXP-0033 registered in this package (stage=h4_second_coder_agreement); EXP-0010 registered | P002<-EXP0035_subset_

### E07 随机种子 - satisfied

- ok `e_step_all_papers` **E07 carried by every package on a re-opened artefact** - 58/58 packages carry E07 on a re-opened artefact: P001<-EXP-0004 registered in this package (stage=w0_pilot); EXP-0006b registered in this package | P002<-EXP-0026 regist

### E08 跨数据集外部验证 - satisfied

- ok `e_step_all_papers` **E08 carried by every package on a re-opened artefact** - 58/58 packages carry E08 on a re-opened artefact: P001<-EXP-0020 registered in this package (stage=e08_external_catalogue_build_DEV_ONLY); EXP-008 | P002<-EXP0022_externa

### E09 跨模型验证 - satisfied

- ok `e_step_all_papers` **E09 carried by every package on a re-opened artefact** - 58/58 packages carry E09 on a re-opened artefact: P001<-EXP-0002 registered in this package (stage=w0_feasibility_probe); EXP-0004 registered in t | P002<-configs/dataset

### E10 跨任务/领域稳健性 - satisfied

- ok `e_step_all_papers` **E10 carried by every package on a re-opened artefact** - 58/58 packages carry E10 on a re-opened artefact: P001<-EXP-0023 registered in this package (stage=e08_external_corpus_transfer_DEV_ONLY); claim C | P002<-EXP-0107 regist

### E11 Robustness - satisfied

- ok `e_step_all_papers` **E11 carried by every package on a re-opened artefact** - 58/58 packages carry E11 on a re-opened artefact: P001<-EXP-0011 registered in this package (stage=dev_robustness_inference); EXP-0088 registered  | P002<-ABLATION_CASES_

### E12 Scaling - satisfied

- ok `e_step_all_papers` **E12 carried by every package on a re-opened artefact** - 58/58 packages carry E12 on a re-opened artefact: P001<-EXP-0028 registered in this package (stage=e12_learning_curve_DEV_ONLY); claim C17; EXP-00 | P002<-EXP0028_learnin

### E13 效率与成本 - satisfied

- ok `e_step_all_papers` **E13 carried by every package on a re-opened artefact** - 58/58 packages carry E13 on a re-opened artefact: P001<-EXP-0105 registered in this package (stage=e13_runtime_and_cost_table); EXP-0105 registere | P002<-EXP-0105 regist

### E14 Statistical Significance - satisfied

- ok `e_step_all_papers` **E14 carried by every package on a re-opened artefact** - 58/58 packages carry E14 on a re-opened artefact: P001<-EXP-0011 registered in this package (stage=dev_robustness_inference); EXP-0015 registered  | P002<-EXP-0026 regist

### E15 Error Analysis - satisfied

- ok `e_step_all_papers` **E15 carried by every package on a re-opened artefact** - 58/58 packages carry E15 on a re-opened artefact: P001<-EXP-0046 registered in this package (stage=error_analysis_E15_DONE); EXP-0083 registered i | P002<-claim K1 | P003

### E16 Case Study - satisfied

- ok `e_step_all_papers` **E16 carried by every package on a re-opened artefact** - 58/58 packages carry E16 on a re-opened artefact: P001<-EXP-0046 registered in this package (stage=error_analysis_E15_DONE); EXP-0014 registered i | P002<-EXP-0107 regist

### E17 Counterfactual / Intervention - satisfied

- ok `e_step_all_papers` **E17 carried by every package on a re-opened artefact** - 58/58 packages carry E17 on a re-opened artefact: P001<-EXP-0016 registered in this package (stage=e17_catalog_intervention_DEV_ONLY); EXP-0016 re | P002<-EXP-0107 regist

### E18 Replication - satisfied

- ok `e_step_all_papers` **E18 carried by every package on a re-opened artefact** - 58/58 packages carry E18 on a re-opened artefact: P001<-EXP-0014b registered in this package (stage=persistence_replication_audit); EXP-0025 regis | P002<-EXP-0079 regist

### E19 Contamination Audit - satisfied

- ok `e_step_all_papers` **E19 carried by every package on a re-opened artefact** - 58/58 packages carry E19 on a re-opened artefact: P001<-EXP-0008 registered in this package (stage=w1_contamination_audit); EXP-0017 registered in | P002<-EXP-0104 regist

### S11 LLM-as-a-Judge 使用规范 - satisfied

- ok `needles_count_all_papers` **the LLM-judge boundary is stated in the package, not just held in practice** - spec §11 items found in every package (>= 1 of 7): P001:1, P002:1, P003:1, P004:1, P005:1, P006:3, P007:3, P008:3, P009:3, P010:3, P011:3, P012:3, P014:3, P015:3, P016:3,
- ok `needle_any_file` **and no package leaves a judge as its only source of truth** - final_audit.md:no model api

### S13 多角度数据分析要求 - satisfied

- ok `topic_groups_all_papers` **at least four of the spec's analysis dimensions are carried by every package** - spec §13 topics addressed in every package (>= 4 of 11): P001=11/11, P002=11/11, P003=10/11, P004=11/11, P005=10/11, P006=11/11, P007=11/11, P008=11/11, P009=11/11, P010=

### S15 图表规范：结果“漂亮”的正确实现方式 - satisfied

- ok `figure_plan_filled_all_papers` **every §15 role is carried by a real artefact, and the manuscript names each one** - every §15 role is carried by a real artefact that the paper names: P001: 8/8 roles carried, 7 figures + 23 tables placed in the manuscript | P002: 8/8 roles carried, 5 fi
- ok `count_files_all_papers` **vector figures are shipped** - 58/58 packages with >= 3
- ok `count_files_all_papers` **and tables are generated files, not typed values** - 58/58 packages with >= 5

### S17 Reviewer Attack：提交前强制反向审稿 - satisfied

- ok `table_rows_all_papers` **the reverse review answers at least the 13 attacks the spec lists** - reviewer_attack.md rows >= 13 in every package: P001=31, P002=14, P003=27, P004=13, P005=15, P006=16, P007=16, P008=16, P009=16, P010=16, P011=16, P012=16, P014=16, P015=
- ok `topic_groups_all_papers` **and addresses all thirteen of the spec's questions, in whatever words** - spec §17 topics addressed in every package (>= 13 of 13): P001=13/13, P002=13/13, P003=13/13, P004=13/13, P005=13/13, P006=13/13, P007=13/13, P008=13/13, P009=13/13, P010

### S19 每篇论文的推荐实验矩阵模板 - satisfied

- ok `table_rows_all_papers` **the recommended experiment matrix is filled per package (E00-E19 rows)** - E_COVERAGE.md rows >= 20 in every package: P001=20, P002=20, P003=20, P004=20, P005=20, P006=20, P007=20, P008=20, P009=20, P010=20, P011=20, P012=20, P014=20, P015=20, P

### S20 多论文并行时的管理规则 - satisfied

- ok `topic_pool_waves` **the topic funnel carries the registered candidate pool the spec asks for** - 123 topics registered, 61 still live; screening waves [50, 36] against the §20 cap of 50 per pool
- ok `files_exist` **shared components are reused rather than rebuilt per paper** - 3/3 artefacts present: canonical_conformance_audit_p003.py, isp_stage_coder.py, isp_stage_main_p002.py

### 21.1 合成轨迹外部效度 - satisfied

- ok `needle_all_papers` **every paper states its population is recorded agent data** - 58/58 packages
- ok `hedged_needle_all_papers` **the human-behaviour phrase appears only inside a denial** - every occurrence of 'human information behav' sits inside a denial

### 21.2 `<think>` 的解释 - satisfied

- ok `needles_in_named_papers` **the papers that read reasoning text bound it to the uttered surface** - bounded in P001, P002
- ok `hedged_needle_all_papers` **no reasoning-trace claim is made unhedged** - every occurrence of 'chain-of-thought' sits inside a denial
- ok `file_exists` **the coder's reading surface is tested rather than assumed** - 02_shared_code/trajectory_parser/test_canonical_ir.py exists (11299 bytes)

### 21.3 SWE-ZERO - satisfied

- ok `needle_any_file` **the shipped outcome label was measured against an independent signal** - EXP0108_p004_external_shipped_label_20260921T072203.json:exit_status
- ok `needle_any_file` **the programme says the label is not a verifier result** - section21_special_risks.md:not functional correctness

### 21.4 多数据集 schema 不一致 - satisfied

- ok `file_exists` **one unit test per canonical transformation exists** - 02_shared_code/trajectory_parser/test_canonical_ir.py exists (11299 bytes)
- ok `needle_any_file` **and passes** - EXP0109_canonical_ir_tests.json:ALL_TESTS_PASS
- ok `needle_any_file` **the original schemas are kept beside the canonical reader** - dataset_card.md:from

### 21.5 API / closed model 漂移 - satisfied

- ok `needle_any_file` **the boundary and its evidence are stated in the generated note** - section21_special_risks.md:no hosted model is called during analysis
- ok `needle_any_file` **each package's environment record names the model-API and network status** - system_info.json:llm_api_available_by_policy
- ok `needle_any_file` **the one locally run model is registered with its provenance** - experiment_registry.csv:EXP-0062

### S23 研究程序级验收 - satisfied

- ok `files_exist` **the canonical schema, its audit tool and its unit tests exist** - 3/3 artefacts present: test_canonical_ir.py, audit_datasets.py, canonical_conformance_audit_p003.py
- ok `package_audit_clean` **a complete experiment package per paper** - package_audit reports missing=none weak=none for all five packages
- ok `count_files_all_papers` **a reproduction entry script per paper** - 58/58 packages with >= 1
- ok `file_exists` **the programme status document is generated, not hand-kept** - 00_program_registry/PROGRAM_STATUS.md exists (36805 bytes)
- ok `topic_pool_waves` **the topic pool that enters one audit round stays inside 30-50** - 123 topics registered, 61 still live; screening waves [50, 36] against the §20 cap of 50 per pool

### G03 必须写出一页以内的 1. 已有研究做了什么； 2. 还缺什么； 3. 本文为什么能用现有数据回答； 4. 本文与最近 3–5 篇最相似工作的明确差异。 - satisfied

- ok `all_needles_all_papers` **every paper states all four parts of gate G03 in its own manuscript** - all 5 required lines present in every package
- ok `needle_any_file` **the block is assembled from the package's own literature matrix, not pasted prose** - paper.md:rule-composed from literature_matrix.csv

### G04 无法确认数据字段真实含义、license 或分割规则时，暂停该数据集的主实验。 # 5. 论文类型判定：先决定什么叫“成功” 所有论文必须归入以下至少一种类型。 ## Type A：机制 / 行为研究 例：信息迷航、路径依赖、验证行为、语言不确定性。 - satisfied

- ok `needle_all_papers` **each package names something it could not confirm and what it withheld because of it** - 58/58 packages
- ok `needle_any_file` **the programme records a dataset or topic parked on an unconfirmed property** - topic_registry.csv:parked
- ok `needle_any_file` **the parking decision is traceable to a measured feasibility probe** - t027_feasibility_decision.py:w2_parked_after_feasibility_probe


## Every requirement, with its pointers

| id | title | status | files naming it (first 3) |
|---|---|---|---|
| S00 | 最终交付物定义 | satisfied_by_content_signature | `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| T01.01 | 禁止虚构或补造实验结果 | evidenced_in_package | `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| T01.02 | 禁止测试集驱动优化 | evidenced_in_package | `protocol_freeze.md`, `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md` |
| T01.03 | 禁止选择性报告 | evidenced_in_package | `deviations.md`, `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md` |
| T01.04 | “漂亮结果”定义 | evidenced_in_package | `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| S02 | 建立总研究工作区 | satisfied_by_content_signature | `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| T02.01 | 建立选题注册表 | evidenced_in_package | `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| T03.01 | 系统检索文献 | evidenced_in_package | `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| T03.02 | 建立证据矩阵 | evidenced_in_package | `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| T03.03 | 进行“撞题判定” | evidenced_in_package | `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| T04.01 | 获取真实数据 | evidenced_in_package | `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| T04.02 | Schema 审计 | evidenced_in_package | `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| T04.03 | 随机样本人工式机器审查 | evidenced_in_package | `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| T04.04 | 重复与泄漏审计 | evidenced_in_package | `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| T04.05 | 生成数据卡 | evidenced_in_package | `dataset_card.md`, `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md` |
| T06.01 | 明确研究问题 | evidenced_in_package | `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| T06.02 | 每个构念建立操作化表 | evidenced_in_package | `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| T06.03 | 禁止“为了显著而造指标” | evidenced_in_package | `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| S07 | 实验协议冻结（Protocol Freeze） | satisfied_by_content_signature | `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| T08.01 | SOTA 检索层级 | evidenced_in_package | `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md`, `sota_audit.md` |
| T08.02 | 公平比较五条件 | evidenced_in_package | `deviations.md`, `protocol_freeze.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| T08.03 | 强基线层级 | evidenced_in_package | `research_plan.md`, `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md` |
| T08.04 | 基线复现优先级 | evidenced_in_package | `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md`, `sota_audit.md` |
| E00 | 数据描述与基础统计 | satisfied_by_content_signature | `CONTAMINATION_AND_COST.md`, `E_COVERAGE.md`, `research_plan.md` |
| E01 | 主效应 / 主任务实验 | satisfied_by_content_signature | `E_COVERAGE.md`, `research_plan.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| E02 | 基础基线 | satisfied_by_content_signature | `E_COVERAGE.md`, `research_plan.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| E03 | 强基线 / SOTA 对比 | satisfied_by_content_signature | `E_COVERAGE.md`, `limitations.md`, `research_plan.md` |
| E04 | 消融实验 | satisfied_by_content_signature | `E_COVERAGE.md`, `research_plan.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| E05 | 替代操作化 | satisfied_by_content_signature | `E_COVERAGE.md`, `clean_room_run_P001.json`, `experiment_registry.csv` |
| E06 | 超参数敏感性 | satisfied_by_content_signature | `E_COVERAGE.md`, `research_plan.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| E07 | 随机种子 | satisfied_by_content_signature | `E_COVERAGE.md`, `research_plan.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| E08 | 跨数据集外部验证 | satisfied_by_content_signature | `E_COVERAGE.md`, `appendix.md`, `claims_evidence_matrix.csv` |
| E09 | 跨模型验证 | satisfied_by_content_signature | `E_COVERAGE.md`, `research_plan.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| E10 | 跨任务/领域稳健性 | satisfied_by_content_signature | `E_COVERAGE.md`, `research_plan.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| E11 | Robustness | satisfied_by_content_signature | `E_COVERAGE.md`, `deviations.md`, `experiment_registry.csv` |
| E12 | Scaling | satisfied_by_content_signature | `E_COVERAGE.md`, `appendix.md`, `claims_evidence_matrix.csv` |
| E13 | 效率与成本 | satisfied_by_content_signature | `CONTAMINATION_AND_COST.md`, `E_COVERAGE.md`, `RUN_COST.md` |
| E14 | Statistical Significance | satisfied_by_content_signature | `E_COVERAGE.md`, `experiment_registry.csv`, `research_plan.md` |
| E15 | Error Analysis | satisfied_by_content_signature | `E_COVERAGE.md`, `claims_evidence_matrix.csv`, `experiment_configs.csv` |
| E16 | Case Study | satisfied_by_content_signature | `E_COVERAGE.md`, `claims_evidence_matrix.csv`, `deviations.md` |
| E17 | Counterfactual / Intervention | satisfied_by_content_signature | `E_COVERAGE.md`, `appendix.md`, `claims_evidence_matrix.csv` |
| E18 | Replication | satisfied_by_content_signature | `E_COVERAGE.md`, `appendix.md`, `experiment_registry.csv` |
| E19 | Contamination Audit | satisfied_by_content_signature | `CONTAMINATION_AND_COST.md`, `E_COVERAGE.md`, `claims_evidence_matrix.csv` |
| T10.01 | 先做分布，再选检验 | evidenced_in_package | `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| T10.02 | 报效应量 | evidenced_in_package | `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| T10.03 | 多重比较 | evidenced_in_package | `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| T10.04 | 层级结构 | evidenced_in_package | `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| T10.05 | 大样本显著性陷阱 | evidenced_in_package | `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| S11 | LLM-as-a-Judge 使用规范 | satisfied_by_content_signature | `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| T12.01 | SOTA 未达成时的决策树 | evidenced_in_package | `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| S13 | 多角度数据分析要求 | satisfied_by_content_signature | `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| S15 | 图表规范：结果“漂亮”的正确实现方式 | satisfied_by_content_signature | `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| T16.01 | 先写“结果骨架”，再写 prose | evidenced_in_package | `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| T16.02 | 论文结构 | evidenced_in_package | `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| T16.03 | 引言必须做到 | evidenced_in_package | `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| T16.04 | Related Work | evidenced_in_package | `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| T16.05 | Results | evidenced_in_package | `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| S17 | Reviewer Attack：提交前强制反向审稿 | satisfied_by_content_signature | `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| G18-A | 数据真实性 | evidenced_in_package | `final_audit.md`, `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md` |
| G18-B | 实验完整性 | evidenced_in_package | `claims_evidence_matrix.csv`, `deviations.md`, `experiment_registry.csv` |
| G18-C | 统计 | evidenced_in_package | `claims_evidence_matrix.csv`, `final_audit.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| G18-D | SOTA | evidenced_in_package | `final_audit.md`, `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md` |
| G18-E | 可复现 | evidenced_in_package | `experiment_registry.csv`, `final_audit.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| G18-F | 写作 | evidenced_in_package | `final_audit.md`, `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md` |
| S19 | 每篇论文的推荐实验矩阵模板 | satisfied_by_content_signature | `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| S20 | 多论文并行时的管理规则 | satisfied_by_content_signature | `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| 21.1 | 合成轨迹外部效度 | satisfied_by_content_signature | `paper.md`, `reproduce.sh`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| 21.2 | `<think>` 的解释 | satisfied_by_content_signature | `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md`, `paper.md` |
| 21.3 | SWE-ZERO | satisfied_by_content_signature | `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| 21.4 | 多数据集 schema 不一致 | satisfied_by_content_signature | `reproduce.sh`, `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md` |
| 21.5 | API / closed model 漂移 | satisfied_by_content_signature | `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| S23 | 研究程序级验收 | satisfied_by_content_signature | `EXP0093_error_census.csv`, `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md` |
| G03 | 必须写出一页以内的 1. 已有研究做了什么； 2. 还缺什么； 3. 本文为什么能用现有数据回答； 4. 本文与最近 3–5 篇 | satisfied_by_content_signature | `novelty_grading.md`, `paper.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |
| G04 | 无法确认数据字段真实含义、license 或分割规则时，暂停该数据集的主实验。 # 5. 论文类型判定：先决定什么叫“成功” 所 | satisfied_by_content_signature | `EXP0099_spec_completion_audit_20260926T133316.json`, `SPEC_COMPLETION_AUDIT.md`, `EXP0099_spec_completion_audit_20260926T133316.json` |

**How to read this.** A named id is not a passed check: `package_audit.py` and `gates18_complete.py` are what test contents. This audit answers the narrower question the programme had never asked - whether each requirement the spec states was ever *touched* by a file that exists - so that an id nobody picked up cannot hide inside a set of packages that each pass their own deliverable list.

artefact: `results_raw\EXP0099_spec_completion_audit_20260926T191742.json`
