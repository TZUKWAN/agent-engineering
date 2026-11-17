# 论文实验任务目录

本目录包含三篇人机语用学实证论文的完整实验任务文档。

## 数据集
全部使用 `data/processed/analysis_data.parquet`（22,811条任务，421,453个步骤）
原始指令在 `instruction` 列，步骤级数据在 `data/interim/steps.parquet`

## 论文列表

| 编号 | 任务文档 | 核心问题 |
|------|---------|---------|
| 01 | paper01_verification_explicitness.md | 验证显性度如何影响智能体执行终止机制 |
| 02 | paper02_constraint_density.md | 约束密度与执行效能的非线性关系 |
| 03 | paper03_pragmatic_typology.md | 提示表达的语用结构类型学与执行路径差异 |

## 执行顺序
01 → 02 → 03（从简单到复杂，01和02的结果可为03提供变量选择依据）

## 实验结果输出位置
每篇论文的结果报告统一输出到 `results/papers/paper{编号}/` 目录下。
