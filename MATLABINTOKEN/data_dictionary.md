# 数据字典

## 数据集信息
- 名称：AgentNet
- 来源：Hugging Face (xlangai/AgentNet)
- 下载日期：2026-06-21T04:22:01（见 data/raw/download_record.json）
- 版本：commit d76ee50a63fad81cfdbe576416757d7c2091ed50（单一 revision，last_modified 2026-01-09）
- 官方任务数：meta_data_merged.jsonl 共 22,532 条（= 唯一 task_id 数）
- 轨迹文件：agentnet_ubuntu_5k.jsonl（5,000 行）+ agentnet_win_mac_18k.jsonl（17,625 行）= 22,625 行，
  其中 93 个 task_id 在文件内重复（91 个同指令，其中 76 个标签互相冲突）。
- **去重规则（2026-09-26 R1 审计）**：保留 traj 长度与官方 step_num 一致的记录（93 例中 91 例可由此唯一
  判定，且第二行为正身）；无法唯一判定时保留末次出现。去重后 22,532 任务 / 416,186 步骤；
  被弃记录与裁决理由见 data/interim/dedup_audit.json（及 paper04/05 的 interim 目录同名文件）。

## 字段映射

### 已检查文件

### download_record.json
- 记录数: 1
- 字段: commit_hash, download_path, download_timestamp, failed, files, last_modified, repo_id, success

### file_list.json
- 记录数: 1
- 字段: all_files, selected_files, timestamp


### 任务级字段
| 字段名 | 类型 | 描述 | 来源 |
|--------|------|------|------|
| task_id | 字符串 | 任务唯一标识 | 待确认 |
| instruction | 文本 | 指令文本 | 待确认 |
| natural_language_task | 文本 | 自然语言任务描述 | 待确认 |
| actual_task | 文本 | 实际任务 | 待确认 |
| task_completed | 布尔/整数 | 任务是否完成 | 待确认 |
| alignment_score | 数值 | 任务对齐评分 | 待确认 |
| efficiency_score | 数值 | 执行效率评分 | 待确认 |
| task_difficulty | 数值/分类 | 任务难度 | 待确认 |
| OS | 字符串 | 操作系统 | 待确认 |
| traj | 列表/对象 | 轨迹数据 | 待确认 |

### 轨迹步骤字段
| 字段名 | 类型 | 描述 | 来源 |
|--------|------|------|------|
| index | 整数 | 步骤索引 | 待确认 |
| observation | 文本/对象 | 观察 | 待确认 |
| thought | 文本 | 后生成推理标注 | 待确认 |
| action | 文本/对象 | 动作 | 待确认 |
| code | 文本 | 代码 | 待确认 |
| last_step_correct | 布尔 | 上一步是否正确 | 待确认 |
| last_step_redundant | 布尔 | 上一步是否冗余 | 待确认 |
| reflection | 文本 | 反思 | 待确认 |

## 注意事项
字段信息将在实际读取数据文件后更新。不得假设所有字段完全一致。
