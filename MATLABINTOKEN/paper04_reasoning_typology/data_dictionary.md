# 论文四数据字典

## 数据集

- **名称**：AgentNet
- **来源**：Hugging Face（xlangai/AgentNet）
- **样本量**：22,532 条任务，416,186 个步骤（原始轨迹文件 22,625 行含 93 个重复 `task_id`；2026-09-26 R1 审计按官方元数据 `meta_data_merged.jsonl` 去重，规则：step_num 匹配优先，否则保留末次出现；审计见 `data/interim/paper04/dedup_audit.json`）
- **使用范围**：论文四显式推理链类型学分析

## 任务级字段

| 字段名 | 类型 | 描述 |
|--------|------|------|
| task_id | 字符串 | 任务唯一标识 |
| instruction | 文本 | 用户自然语言指令 |
| natural_language_task | 文本 | 任务的自然语言描述 |
| actual_task | 文本 | 实际任务内容 |
| task_completed | 布尔 | 任务是否完成 |
| alignment_score | 整数 | 任务对齐评分 |
| efficiency_score | 整数 | 执行效率评分 |
| task_difficulty | 整数 | 任务难度评分 |
| reason | 文本 | 任务完成/失败的事后说明 |
| domain | 文本 | 任务领域 |
| os | 字符串 | 操作系统（ubuntu / win_mac） |

## 步骤级字段

| 字段名 | 类型 | 描述 |
|--------|------|------|
| task_id | 字符串 | 所属任务标识 |
| step_index | 整数 | 步骤序号 |
| observation | 文本 | 环境观察 |
| thought | 文本 | 当前步骤的显式推理文本 |
| action | 文本 | 自然语言动作描述 |
| code | 文本 | 执行代码（如 pyautogui 代码） |
| reflection | 文本 | 步骤后的反思文本 |
| last_step_correct | 布尔 | 该步骤是否正确 |
| last_step_redundant | 布尔 | 该步骤是否冗余 |

## 推理链特征字段（任务级）

| 字段名 | 类型 | 描述 |
|--------|------|------|
| reasoning_words | 整数 | 任务内 thought + reflection 总词数 |
| structure_markers | 整数 | 规划/顺序标记总数 |
| decomposition_words | 整数 | 子任务/步骤分解词总数 |
| constraint_mentions | 整数 | 约束词在推理中的出现次数 |
| verification_mentions | 整数 | 验证/检查词出现次数 |
| feedback_phrases | 整数 | 反馈引用表达数 |
| self_correction_phrases | 整数 | 自我修正表达数 |
| termination_last20_mentions | 整数 | 最后 20% 步骤中的终止判断词数 |
| reasoning_action_alignment | 浮点 | 动作关键词与推理文本的交集比例 |
| tool_mentions_in_reasoning | 整数 | 动作/代码关键词在推理中出现的种类数 |

## 类型标签字段

| 字段名 | 类型 | 描述 |
|--------|------|------|
| reasoning_type | 整数 | 聚类编号（0–3） |
| reasoning_type_label | 字符串 | 类型名称 |

## 结果字段

| 字段名 | 类型 | 描述 |
|--------|------|------|
| total_steps | 整数 | 任务总步数 |
| incorrect_steps | 整数 | 错误步数 |
| redundant_steps | 整数 | 冗余步数 |
| incorrect_ratio | 浮点 | 错误步比例 |
| redundant_ratio | 浮点 | 冗余步比例 |

## 备注

- 所有推理链特征均基于规则与正则从文本中提取，未调用语言模型 API。
- `thought`/`reflection` 是事后生成的轨迹解释，不等同于模型内部思维。
