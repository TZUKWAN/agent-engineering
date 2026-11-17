"""
10_generate_tables.py - 生成结果表格

生成论文用的表格
"""

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime


def load_json(path):
    """加载JSON文件"""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def main():
    """主函数"""
    print("=" * 60)
    print("生成结果表格")
    print("=" * 60)

    os.makedirs("results/tables", exist_ok=True)

    # 表1: 变量定义
    print("\n--- 表1: 变量定义 ---")

    variable_definitions = {
        "explicitness_score": "操作显性度综合指数（0-11分，11个正向特征之和）",
        "explicitness_level": "操作显性度三级分组（low/medium/high）",
        "task_completed": "任务是否完成（主要结果变量）",
        "efficiency_score": "执行效率评分",
        "alignment_score": "人机任务对齐评分",
        "correct_ratio": "正确步骤比例",
        "incorrect_ratio": "错误步骤比例",
        "redundant_ratio": "冗余步骤比例",
        "total_steps": "轨迹总步骤数",
        "word_count": "任务文本词数",
        "task_difficulty": "任务难度",
    }

    # 保存为CSV
    table1 = pd.DataFrame({
        "变量名": list(variable_definitions.keys()),
        "定义": list(variable_definitions.values()),
    })
    table1_path = "results/tables/table1_variable_definitions.csv"
    table1.to_csv(table1_path, index=False, encoding="utf-8-sig")
    print(f"已保存: {table1_path}")

    # 表2: 描述性统计
    print("\n--- 表2: 描述性统计 ---")

    analysis_path = "data/processed/analysis_data.parquet"
    if os.path.exists(analysis_path):
        df = pd.read_parquet(analysis_path)

        key_vars = [
            "explicitness_score", "task_completed", "efficiency_score", "alignment_score",
            "incorrect_ratio", "redundant_ratio", "word_count", "total_steps"
        ]

        available_vars = [v for v in key_vars if v in df.columns]

        if available_vars:
            desc_data = []
            for var in available_vars:
                s = df[var]
                desc_data.append({
                    "变量": var,
                    "样本数": int(s.notna().sum()),
                    "均值": float(s.mean()) if pd.notna(s.mean()) else None,
                    "标准差": float(s.std()) if pd.notna(s.std()) else None,
                    "最小值": float(s.min()) if pd.notna(s.min()) else None,
                    "最大值": float(s.max()) if pd.notna(s.max()) else None,
                })

            table2 = pd.DataFrame(desc_data)
            table2_path = "results/tables/table2_descriptive_stats.csv"
            table2.to_csv(table2_path, index=False, encoding="utf-8-sig")
            print(f"已保存: {table2_path}")
            print(table2.to_string(index=False))

    # 表3: 主要结果
    print("\n--- 表3: 主要结果 ---")

    main_results = load_json("results/models/main_results.json")
    if main_results:
        table3_data = []

        # RQ1
        if "rq1" in main_results:
            rq1 = main_results["rq1"]
            table3_data.append({
                "研究问题": "RQ1",
                "结果": "显性度与任务完成率",
                "相关系数": rq1.get("correlation"),
                "p值": rq1.get("p_value"),
                "样本数": rq1.get("n"),
            })

        # RQ2
        if "rq2" in main_results:
            for outcome, result in main_results["rq2"].items():
                table3_data.append({
                    "研究问题": "RQ2",
                    "结果": f"显性度与{outcome}",
                    "相关系数": result.get("correlation"),
                    "p值": result.get("p_value"),
                    "样本数": result.get("n"),
                })

        # RQ3
        if "rq3" in main_results:
            for process_var, result in main_results["rq3"].items():
                table3_data.append({
                    "研究问题": "RQ3",
                    "结果": f"显性度与{process_var}",
                    "相关系数": result.get("correlation"),
                    "p值": result.get("p_value"),
                    "样本数": result.get("n"),
                })

        if table3_data:
            table3 = pd.DataFrame(table3_data)
            table3_path = "results/tables/table3_main_results.csv"
            table3.to_csv(table3_path, index=False, encoding="utf-8-sig")
            print(f"已保存: {table3_path}")
            print(table3.to_string(index=False))

    # 表4: 按显性度级别的结果
    print("\n--- 表4: 按显性度级别的结果 ---")

    if main_results and "rq1" in main_results and "by_level" in main_results["rq1"]:
        by_level = main_results["rq1"]["by_level"]
        table4_data = []
        for level, info in by_level.items():
            table4_data.append({
                "显性度级别": level,
                "任务完成率": info.get("rate"),
                "样本数": info.get("n"),
            })

        if table4_data:
            table4 = pd.DataFrame(table4_data)
            table4_path = "results/tables/table4_by_explicitness_level.csv"
            table4.to_csv(table4_path, index=False, encoding="utf-8-sig")
            print(f"已保存: {table4_path}")
            print(table4.to_string(index=False))

    # 表5: 稳健性检验汇总
    print("\n--- 表5: 稳健性检验 ---")

    robustness = load_json("results/tables/robustness_checks.json")
    if robustness:
        table5_data = []

        # 不同文本字段
        if "text_fields" in robustness:
            for field, result in robustness["text_fields"].items():
                table5_data.append({
                    "检验类型": "不同文本字段",
                    "具体检验": field,
                    "相关系数": result.get("correlation"),
                    "样本数": result.get("n"),
                })

        # 排除极端值
        if "excluding_extremes" in robustness:
            ee = robustness["excluding_extremes"]
            if "full_sample" in ee:
                table5_data.append({
                    "检验类型": "样本筛选",
                    "具体检验": "完整样本",
                    "相关系数": ee["full_sample"].get("correlation"),
                    "样本数": ee["full_sample"].get("n"),
                })
            if "trimmed_sample" in ee:
                table5_data.append({
                    "检验类型": "样本筛选",
                    "具体检验": "剔除极端值",
                    "相关系数": ee["trimmed_sample"].get("correlation"),
                    "样本数": ee["trimmed_sample"].get("n"),
                })

        if table5_data:
            table5 = pd.DataFrame(table5_data)
            table5_path = "results/tables/table5_robustness_checks.csv"
            table5.to_csv(table5_path, index=False, encoding="utf-8-sig")
            print(f"已保存: {table5_path}")
            print(table5.to_string(index=False))

    print("\n表格生成完成")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
