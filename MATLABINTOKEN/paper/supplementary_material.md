# 补充材料

## 附录 A：操作显性度特征的详细定义

### A.1 二元特征（11个）

| 特征名 | 定义 | 判断规则 |
|--------|------|----------|
| has_application | 是否明确指出应用或软件 | 包含常见应用关键词（Excel、Word、Chrome等） |
| has_operation_object | 是否明确指出操作对象 | 包含文件、文档、按钮、链接等对象指示词 |
| has_target_action | 是否明确指出目标动作 | 包含打开、保存、删除、点击等动词 |
| has_target_state | 是否明确指出目标状态 | 包含完成、正确、应该等状态描述 |
| has_file_reference | 是否提供文件引用 | 包含文件名、路径、工作表名、URL等 |
| has_object_properties | 是否给出对象属性 | 包含颜色、位置、格式、数量等描述 |
| has_operation_order | 是否说明操作顺序 | 包含首先、然后、最后等顺序词 |
| has_multiple_subtasks | 是否包含多个子任务 | 句子数量≥2或连接词数量≥2 |
| has_constraint_words | 是否包含约束词 | 包含只、不要、保持、必须等词 |
| has_completion_criteria | 是否给出完成标准 | 包含检查、确保、确认等词 |
| has_initial_state | 是否说明初始状态 | 包含当前、已有、假设等描述 |

### A.2 计数特征（5个）

| 特征名 | 定义 |
|--------|------|
| word_count | 文本词数 |
| char_count | 文本字符数 |
| verb_count | 动词数量（基于常见动词列表） |
| conditional_count | 条件从句数量（if、when、unless等） |
| sequence_connector_count | 顺序连接词数量 |

### A.3 综合指数

- **explicitness_score**: 11个正向二元特征之和（0-11分）
- **explicitness_level**: 
  - Low: 0-3分
  - Medium: 4-6分
  - High: 7-11分

---

## 附录 B：完整的统计结果

### B.1 描述性统计

| 变量 | N | 均值 | 标准差 | 最小值 | 最大值 |
|------|---|------|--------|--------|--------|
| task_completed | 22,811 | 0.792 | 0.406 | 0 | 1 |
| explicitness_score | 22,811 | 3.06 | 1.94 | 0 | 11 |
| total_steps | 22,811 | 18.48 | 17.59 | 1 | 345 |
| incorrect_ratio | 22,811 | 0.12 | 0.20 | 0 | 1 |
| redundant_ratio | 22,811 | 0.12 | 0.18 | 0 | 1 |
| word_count | 22,811 | 17.5 | 13.8 | 3 | 210 |
| char_count | 22,811 | 95.2 | 73.4 | 11 | 1120 |

### B.2 显性度级别分布

| 级别 | N | 百分比 |
|------|---|--------|
| Low | 12,118 | 53.1% |
| Medium | 7,477 | 32.8% |
| High | 889 | 3.9% |
| **总计** | **22,811** | **100.0%** |

### B.3 特征流行度排序

| 排名 | 特征 | 存在比例 |
|------|------|----------|
| 1 | has_initial_state | 65.3% |
| 2 | has_target_action | 52.0% |
| 3 | has_operation_object | 38.1% |
| 4 | has_application | 32.8% |
| 5 | has_completion_criteria | 28.3% |
| 6 | has_object_properties | 19.5% |
| 7 | has_multiple_subtasks | 19.1% |
| 8 | has_constraint_words | 15.6% |
| 9 | has_operation_order | 14.7% |
| 10 | has_target_state | 13.4% |
| 11 | has_file_reference | 12.0% |

### B.4 相关性摘要（N = 22,811）

| 变量对 | 相关系数 (r) | p值 |
|--------|--------------|-----|
| explicitness_score ↔ task_completed | 0.021 | 0.002** |
| explicitness_score ↔ efficiency_score | 0.043 | < 0.001*** |
| explicitness_score ↔ alignment_score | 0.063 | < 0.001*** |
| explicitness_score ↔ total_steps | 0.075 | < 0.001*** |
| explicitness_score ↔ incorrect_ratio | -0.047 | < 0.001*** |
| explicitness_score ↔ redundant_ratio | -0.081 | < 0.001*** |

**p < 0.01, ***p < 0.001

### B.5 分组比较结果

#### B.5.1 任务完成率

| 显性度级别 | 完成率 | N |
|------------|--------|---|
| Low | 78.4% | 12,118 |
| Medium | 80.0% | 7,477 |
| High | 83.5% | 889 |

### B.6 单个特征的效应量

| 特征 | 有特征的完成率 | 无特征的完成率 | 差异 |
|------|---------------|---------------|------|
| has_completion_criteria | 82.3% | 78.8% | +3.5% |
| has_constraint_words | 81.1% | 78.5% | +2.5% |
| has_application | 81.0% | 78.8% | +2.2% |
| has_file_reference | 80.8% | 79.0% | +1.8% |
| has_operation_object | 80.4% | 78.7% | +1.7% |
| has_initial_state | 80.5% | 79.1% | +1.4% |
| has_target_state | 80.3% | 79.2% | +1.1% |
| has_multiple_subtasks | 79.7% | 78.4% | +1.2% |
| has_operation_order | 79.6% | 79.0% | +0.5% |
| has_object_properties | 78.4% | 79.6% | -1.2% |
| has_target_action | 78.6% | 80.2% | -1.6% |

---

## 附录 C：数据边界合规性声明

本研究严格遵守以下数据使用边界：

1. ✅ **未调用任何大模型推理API** - 所有特征提取使用基于规则的方法
2. ✅ **未重新运行GUI智能体** - 仅使用已有的轨迹数据
3. ✅ **未重新采集交互日志** - 使用AgentNet公开数据集
4. ✅ **未建立虚拟机或GUI环境** - 纯离线数据分析
5. ✅ **未使用大模型进行自动标注** - 特征提取基于简单关键词匹配
6. ✅ **仅下载和分析公开数据** - 所有数据来自Hugging Face的公开仓库

分析方法：使用Python的pandas、scipy等传统统计库进行数据处理和分析。

**数据规模**：22,811条任务（17,811条Windows/Mac + 5,000条Ubuntu），共421,453个执行步骤。

---

## 附录 D：代码可用性

所有分析代码保存在 `src/` 目录下：

| 文件名 | 功能 |
|--------|------|
| 01_download_data.py | 从Hugging Face下载AgentNet数据 |
| 02_inspect_files.py | 检查下载的数据文件 |
| 03_parse_trajectories.py | 解析轨迹数据 |
| 04_extract_instruction_features.py | 提取操作显性度特征 |
| 05_extract_process_features.py | 提取过程质量特征 |
| 06_build_analysis_data.py | 构建最终分析数据集 |
| 07_descriptive_statistics.py | 生成描述性统计 |
| 08_fit_models.py | 拟合统计模型 |
| 09_robustness_checks.py | 稳健性检验 |
| 10_generate_tables.py | 生成结果表格 |
| 11_generate_figures.py | 生成结果图表 |
| 12_validate_results.py | 验证分析结果 |
| reproduce.sh | 一键复现完整分析流程的Shell脚本 |

运行 `reproduce.sh` 可以从已下载数据开始，复现本研究的完整分析流程。

---

## 附录 E：稳健性检验结果

### E.1 不同显性度定义的检验

使用仅包含前5个特征的简化显性度分数重新分析：

| 分析 | 结果 |
|------|------|
| 与任务完成率的相关 | r = 0.018, p = 0.007 |
| 低分组完成率 | 78.8% |
| 高分组完成率 | 81.5% |

### E.2 平台间一致性

| 平台 | N | 相关系数 | p值 |
|------|---|----------|-----|
| Windows/Mac | 17,811 | 0.020 | 0.008 |
| Ubuntu | 5,000 | 0.024 | 0.088 |

效应方向在两种平台上一致（正相关），Windows/Mac上达到统计显著性。

### E.3 控制变量后的回归分析

Logistic回归控制步骤数后：

| 变量 | OR | 95% CI | p值 |
|------|----|--------|-----|
| explicitness_score | 1.022 | 1.008-1.036 | 0.002** |
| total_steps | 0.990 | 0.988-0.992 | < 0.001*** |

**p < 0.01, ***p < 0.001

结果表明，即使控制步骤数后，操作显性度与任务完成率仍呈显著正相关。
