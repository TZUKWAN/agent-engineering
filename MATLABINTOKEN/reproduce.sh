#!/bin/bash
# AgentNet 研究可复现脚本（2026-09-26 R1 审计后重写）
# 从已下载数据开始，端到端重新生成五篇论文的全部结果。
#
# 与旧版的差异（旧版存档于 reproduce_legacy_v1.sh.bak）：
# - 主数据构建走 src/reanalyze_full_data.py（官方元数据 step_num 去重 + 原始文本列 +
#   os 标注），这是论文实际引用的 analysis_data 来源；旧 03–06 链产出的模式与论文
#   管道不兼容（缺 instruction/os），仅作对照。
# - 纳入 paper01–paper05 五篇论文的完整管道（此前 reproduce.sh 只覆盖顶层试点表）。
# - 合并报告 DOCX 需要 pandoc，缺失时跳过并给出提示（Markdown 为准）。

set -e

PY="${PYTHON:-python}"

echo "========================================="
echo "AgentNet人机交互实证研究 - 可复现流程"
echo "========================================="

echo ""
echo "[1/16] 检查Python环境..."
"$PY" --version || { echo "Python未找到"; exit 1; }

echo ""
echo "[2/16] 检查依赖包..."
"$PY" -m pip install -q -r requirements.txt || echo "（依赖已满足或离线环境，继续）"

echo ""
echo "[3/16] 检查原始数据..."
if [ ! -d "data/raw" ] || [ -z "$(ls -A data/raw/)" ]; then
    echo "错误: data/raw/ 为空，请先下载数据"
    echo "运行: python src/01_download_data.py"
    exit 1
fi

echo ""
echo "[4/16] 全量解析（含 task_id 去重）+ 特征 + 分析数据集 + 主统计..."
# 写 data/interim/{tasks,steps,instruction_features,process_features}.parquet、
# data/interim/dedup_audit.json、data/processed/analysis_data.parquet、results/models/main_results.json
"$PY" src/reanalyze_full_data.py

echo ""
echo "[5/16] 描述性统计..."
"$PY" src/07_descriptive_statistics.py

echo ""
echo "[6/16] 拟合统计模型..."
"$PY" src/08_fit_models.py

echo ""
echo "[7/16] 稳健性检验..."
"$PY" src/09_robustness_checks.py

echo ""
echo "[8/16] 生成结果表格..."
"$PY" src/10_generate_tables.py

echo ""
echo "[9/16] 生成结果图形..."
"$PY" src/11_generate_figures.py

echo ""
echo "[10/16] 论文一：验证显性度与执行终止机制..."
for s in 01_classify_verification 02_logistic 03_negative_binomial 04_nonlinear 05_position 06_report compute_terminal_phase_metrics; do
    "$PY" "src/paper01/$s.py"
done
"$PY" src/generate_paper01.py

echo ""
echo "[11/16] 论文二：约束密度的非线性效应..."
"$PY" src/paper02/run_all.py
"$PY" src/paper02/07_generate_word_paper.py

echo ""
echo "[12/16] 论文三：提示表达的语用结构类型学..."
"$PY" src/paper03/run_all.py
"$PY" src/paper03/revise_paper03_support.py
"$PY" src/generate_paper03_docx.py

echo ""
echo "[13/16] 论文四：显式推理链类型学..."
for s in 01_parse_agentnet 02_extract_reasoning_features 03_identify_types 04_outcomes 05_generate_figures; do
    "$PY" "src/paper04/$s.py"
done

echo ""
echo "[14/16] 论文五：提示风险与推理—执行错误路径..."
for s in 01_parse_agentnet 02_prompt_risk_features 03_reasoning_execution_errors 04_path_analysis 05_generate_figures; do
    "$PY" "src/paper05/$s.py"
done

echo ""
echo "[15/16] 验证结果..."
"$PY" src/12_validate_results.py

echo ""
echo "[16/16] 管道不变量测试..."
"$PY" tests/test_pipeline_invariants.py

echo ""
echo "合并报告（Markdown，无需 pandoc）..."
(cd revised && "$PY" merge_and_convert.py) || echo "（merge_and_convert 未完成：无 pandoc 时 DOCX 步骤会失败，Markdown 已生成）"
(cd revised && "$PY" restructure_report.py) || true

echo ""
echo "========================================="
echo "分析完成！"
echo "========================================="
echo ""
echo "结果文件位置："
echo "- 表格: results/tables/"
echo "- 图形: results/figures/"
echo "- 模型: results/models/"
echo "- 论文一至三: results/papers/paper01..03/"
echo "- 论文四: paper04_reasoning_typology/results/"
echo "- 论文五: paper05_prompt_risk_failure/results/"
echo "- 去重审计: data/interim/dedup_audit.json"
echo ""
