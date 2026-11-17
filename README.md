# AGENT ENGINEERING — 智能体信息行为（AIB）研究工作区

本仓库是"智能体信息行为（Agentic Information Behavior, AIB）"研究工程的代码与文档归档。
保留了原始目录树，脚本间的相对路径引用（如 `01_datasets/...`、`02_shared_code/...`）在拉取本地后依然有效。

## 目录结构

| 路径 | 说明 |
|---|---|
| `agentic-information-behavior/` | 主研究代码库：审计脚本（根目录 `_*.py`）、`02_shared_code/` 共享代码、`00_program_registry/` 程序注册表、`docs/` 文档 |
| `MATLABINTOKEN/` | 论文复现工程：`src/` 分析流水线（01_download → 09_robustness）、`tasks/` 任务书、`tests/`、`paper/`、`revised/` LaTeX 报告工具链、`reproduce*.sh` |
| `aib_repro_20260918/` | 2026-09-18 干净室复现快照的代码与文档部分 |
| `audit_5rounds/` | 五轮审计脚本 |
| `Agentic_Information_Behavior_研究全流程任务清单.md` | 全流程任务清单 |
| `智能体信息行为研究总览.pptx` | 研究总览 |

## 未入库内容

以下内容为数据集或大规模生成产物，**不在本仓库中**（体积原因）：

- 原始数据集：`01_datasets/`、`MATLABINTOKEN/datasets/`、`MATLABINTOKEN/data/`（`01_datasets/manifests` 中的清单已入库，可按清单重新下载）
- 运行结果：`results_raw/`、`results_processed/`、`MATLABINTOKEN/results/`、`logs/`
- 生成论文产物：`agentic-information-behavior/papers/`、`word_output*/`

如需共享结果数据，建议通过 GitHub Releases 或 Git LFS 另行分发。
