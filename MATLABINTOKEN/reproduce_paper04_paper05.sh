#!/usr/bin/env bash
# 复现论文四与论文五全部结果

set -e

echo "============================================"
echo "复现论文四：显式推理链类型学"
echo "============================================"
python src/paper04/01_parse_agentnet.py
python src/paper04/02_extract_reasoning_features.py
python src/paper04/03_identify_types.py
python src/paper04/04_outcomes.py
python src/paper04/05_generate_figures.py

echo ""
echo "============================================"
echo "复现论文五：提示风险与推理—执行错误机制"
echo "============================================"
python src/paper05/01_parse_agentnet.py
python src/paper05/02_prompt_risk_features.py
python src/paper05/03_reasoning_execution_errors.py
python src/paper05/04_path_analysis.py
python src/paper05/05_generate_figures.py

echo ""
echo "============================================"
echo "复现完成"
echo "============================================"
