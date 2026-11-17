"""
07_descriptive_statistics.py - 描述性统计

生成描述性统计表格和图表
"""

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime


def load_analysis_data():
    """加载分析数据"""
    path = "data/processed/analysis_data.parquet"
    if os.path.exists(path):
        return pd.read_parquet(path)
    return None


def main():
    """主函数"""
    print("=" * 60)
    print("描述性统计")
    print("=" * 60)

    df = load_analysis_data()

    if df is None or len(df) == 0:
        print("\n未找到分析数据")
        return 1

    print(f"\n样本数: {len(df)}")

    # 创建结果目录
    os.makedirs("results/tables", exist_ok=True)
    os.makedirs("results/figures", exist_ok=True)

    # 数值变量统计
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    print(f"\n数值变量 ({len(numeric_cols)}):")

    if numeric_cols:
        desc_stats = df[numeric_cols].describe()

        # 保存描述性统计
        desc_path = "results/tables/descriptive_statistics.csv"
        desc_stats.to_csv(desc_path)
        print(f"描述性统计已保存: {desc_path}")

        # 显示关键变量
        key_vars = [
            "task_completed", "efficiency_score", "alignment_score",
            "explicitness_score", "word_count", "total_steps",
            "correct_ratio", "incorrect_ratio", "redundant_ratio"
        ]

        print("\n关键变量统计:")
        for var in key_vars:
            if var in df.columns:
                non_null = df[var].notna().sum()
                print(f"\n  {var}:")
                print(f"    非空: {non_null}/{len(df)}")
                if non_null > 0:
                    if var == "task_completed":
                        # 分类变量
                        counts = df[var].value_counts()
                        for val, cnt in counts.items():
                            print(f"    {val}: {cnt} ({cnt/len(df)*100:.1f}%)")
                    else:
                        # 连续变量
                        print(f"    均值: {df[var].mean():.2f}")
                        print(f"    标准差: {df[var].std():.2f}")
                        print(f"    最小值: {df[var].min()}")
                        print(f"    最大值: {df[var].max()}")

    # 分类变量统计
    cat_cols = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    print(f"\n分类变量 ({len(cat_cols)}):")

    cat_summary = {}
    for col in cat_cols:
        counts = df[col].value_counts(dropna=False)
        cat_summary[col] = counts.to_dict()

    cat_path = "results/tables/categorical_summary.json"
    with open(cat_path, "w", encoding="utf-8") as f:
        json.dump(cat_summary, f, ensure_ascii=False, indent=2)
    print(f"分类变量统计已保存: {cat_path}")

    # 数据流程报告
    flow_report = {
        "timestamp": datetime.now().isoformat(),
        "original_tasks": len(df),
        "tasks_with_completion": int(df.get("task_completed", pd.Series()).notna().sum()),
        "tasks_with_efficiency": int(df.get("efficiency_score", pd.Series()).notna().sum()),
        "tasks_with_alignment": int(df.get("alignment_score", pd.Series()).notna().sum()),
        "tasks_with_explicitness": int(df.get("explicitness_score", pd.Series()).notna().sum()),
    }

    flow_path = "results/tables/data_flow.json"
    with open(flow_path, "w", encoding="utf-8") as f:
        json.dump(flow_report, f, ensure_ascii=False, indent=2)

    print(f"\n数据流程报告已保存: {flow_path}")
    print("\n数据流程:")
    for key, value in flow_report.items():
        if key != "timestamp":
            print(f"  {key}: {value}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
