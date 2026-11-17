# 论文五数据字典

## 数据集

- **名称**：AgentNet
- **来源**：Hugging Face（xlangai/AgentNet）
- **样本量**：22,532 条任务，416,186 个步骤（原始轨迹文件 22,625 行含 93 个重复 `task_id`；2026-09-26 R1 审计按官方元数据 `meta_data_merged.jsonl` 去重，规则：step_num 匹配优先，否则保留末次出现；审计见 `data/interim/paper05/dedup_audit.json`）
- **使用范围**：论文五提示风险与推理—执行错误机制分析

## 任务级字段

| 字段名 | 类型 | 描述 |
|--------|------|------|
| task_id | 字符串 | 任务唯一标识 |
| instruction | 文本 | 用户自然语言指令 |
| task_completed | 布尔 | 任务是否完成 |
| task_difficulty | 整数 | 任务难度评分 |
| os | 字符串 | 操作系统（ubuntu / win_mac） |
| alignment_score | 整数 | 任务对齐评分 |
| efficiency_score | 整数 | 执行效率评分 |

## 提示语用特征字段（继承前三篇）

| 字段名 | 类型 | 描述 |
|--------|------|------|
| has_application | 布尔 | 是否提及应用 |
| has_operation_object | 布尔 | 是否指明操作对象 |
| has_target_action | 布尔 | 是否指明目标动作 |
| has_target_state | 布尔 | 是否指明目标状态 |
| has_file_reference | 布尔 | 是否引用文件 |
| has_operation_order | 布尔 | 是否说明操作顺序 |
| has_multiple_subtasks | 布尔 | 是否包含多子任务 |
| has_completion_criteria | 布尔 | 是否给出完成标准 |
| has_initial_state | 布尔 | 是否说明初始状态 |
| has_vague_reference | 布尔 | 是否含模糊指代 |
| word_count | 整数 | 指令词数 |
| explicitness_score | 整数 | 显性度总分 |

## 提示风险特征字段

| 字段名 | 类型 | 描述 |
|--------|------|------|
| goal_abstraction | 布尔 | 目标动作存在但对象与状态缺失 |
| object_missing | 布尔 | 无操作对象 |
| completion_standard_missing | 布尔 | 无完成标准词 |
| constraint_missing | 布尔 | 无约束词 |
| constraint_overdense | 布尔 | 约束密度 > 5% |
| multi_subtask_no_order | 布尔 | 多子任务但无顺序 |
| constraint_conflict | 布尔 | 同时含要求型与禁止型约束 |
| vague_reference | 布尔 | 含模糊指代 |
| initial_state_missing | 布尔 | 无初始状态描述 |
| verification_missing | 布尔 | 无明确验证动词 |
| risk_index | 整数 | 风险特征加总指数 |

## 推理错误指标字段

| 字段名 | 类型 | 描述 |
|--------|------|------|
| err_goal_misunderstanding | 整数 | 目标误解 |
| err_constraint_omission | 整数 | 约束遗漏 |
| err_wrong_env_assumption | 整数 | 错误环境假设 |
| err_task_decomposition | 整数 | 任务分解错误 |
| err_no_correction_after_error | 整数 | 反馈后未修正 |
| err_repeat_strategy | 整数 | 重复原策略 |
| err_premature_completion | 整数 | 提前认为完成 |
| err_lack_verification | 整数 | 缺少验证 |
| reasoning_error_index | 整数 | 推理错误指标加总 |

## 执行错误指标字段

| 字段名 | 类型 | 描述 |
|--------|------|------|
| exec_wrong_tool_action | 整数 | 存在错误动作步骤 |
| exec_invalid_operation | 整数 | 观察文本含错误信息 |
| exec_repeated_action | 整数 | 存在冗余步骤 |
| exec_failed_termination | 整数 | 任务失败终止 |
| exec_task_incomplete | 整数 | 任务未完成 |
| execution_error_index | 整数 | 执行错误指标加总 |

## 备注

- 所有指标均通过规则与正则从文本或步骤标签中提取，未调用语言模型 API。
- 错误指标为代理指标，不等同于人工标注的错误类型。
