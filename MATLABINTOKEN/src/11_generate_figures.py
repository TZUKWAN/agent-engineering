"""
11_generate_figures.py - 生成图表

生成论文用的图表（使用简单的文本描述，实际图表需要matplotlib）
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
    print("生成图表说明")
    print("=" * 60)

    os.makedirs("results/figures", exist_ok=True)

    figures = {}

    # 图1: 数据筛选流程图
    print("\n--- 图1: 数据筛选流程图 ---")

    data_flow = load_json("results/tables/data_flow.json")
    if data_flow:
        figures["figure1"] = {
            "title": "数据筛选流程图",
            "description": "展示原始任务数、有效样本数、各变量的缺失情况",
            "data": data_flow,
        }
        print(f"数据流程: {json.dumps(data_flow, ensure_ascii=False, indent=2)}")

    # 图2: 操作显性度分布
    print("\n--- 图2: 操作显性度分布 ---")

    analysis_path = "data/processed/analysis_data.parquet"
    if os.path.exists(analysis_path):
        df = pd.read_parquet(analysis_path)

        if "explicitness_score" in df.columns:
            score_dist = df["explicitness_score"].value_counts().sort_index().to_dict()

            figures["figure2"] = {
                "title": "操作显性度分数分布",
                "description": "直方图，展示操作显性度分数在样本中的分布",
                "type": "histogram",
                "data": {str(k): int(v) for k, v in score_dist.items()},
            }
            print("分数分布:")
            for score, count in sorted(score_dist.items()):
                print(f"  {score}: {count}")

        if "explicitness_level" in df.columns:
            level_dist = df["explicitness_level"].value_counts().to_dict()
            figures["figure2_levels"] = {
                "title": "操作显性度级别分布",
                "description": "柱状图，展示low/medium/high三级的样本数",
                "type": "bar",
                "data": level_dist,
            }
            print("级别分布:")
            for level, count in level_dist.items():
                print(f"  {level}: {count}")

    # 图3: 不同显性度组的任务完成率
    print("\n--- 图3: 任务完成率对比 ---")

    main_results = load_json("results/models/main_results.json")
    if main_results and "rq1" in main_results and "by_level" in main_results["rq1"]:
        by_level = main_results["rq1"]["by_level"]

        figures["figure3"] = {
            "title": "不同操作显性度组的任务完成率",
            "description": "柱状图，展示low/medium/high三组的任务完成率及置信区间",
            "type": "bar_with_ci",
            "data": by_level,
        }
        print("完成率对比:")
        for level, info in by_level.items():
            print(f"  {level}: {info.get('rate', 0):.1%} (n={info.get('n', 0)})")

    # 图4: 显性度与效率、对齐评分
    print("\n--- 图4: 效率与对齐评分 ---")

    if main_results and "rq2" in main_results:
        figures["figure4"] = {
            "title": "操作显性度与效率评分、对齐评分的关系",
            "description": "散点图或箱线图，展示显性度与两个评分的关联",
            "type": "scatter_or_box",
            "data": main_results["rq2"],
        }
        print("评分关联:")
        for outcome, result in main_results["rq2"].items():
            print(f"  {outcome}: r={result.get('correlation', 0):.3f}")

    # 图5: 显性度与错误、冗余比例
    print("\n--- 图5: 错误与冗余比例 ---")

    if main_results and "rq3" in main_results:
        figures["figure5"] = {
            "title": "操作显性度与错误步骤比例、冗余步骤比例的关系",
            "description": "散点图，展示显性度与两个过程变量的负相关关系",
            "type": "scatter",
            "data": main_results["rq3"],
        }
        print("过程变量关联:")
        for var, result in main_results["rq3"].items():
            print(f"  {var}: r={result.get('correlation', 0):.3f}")

    # 图6: 中介效应路径图
    print("\n--- 图6: 中介效应 ---")

    if main_results and "rq4" in main_results:
        figures["figure6"] = {
            "title": "错误比例与冗余比例的中介效应路径图",
            "description": "路径图，展示操作显性度→错误/冗余→任务完成的中介路径",
            "type": "path_diagram",
            "data": main_results["rq4"],
        }
        print("中介路径数据:")
        print(json.dumps(main_results["rq4"], ensure_ascii=False, indent=2))

    # 图7: 不同任务难度下的交互效应
    print("\n--- 图7: 难度交互效应 ---")

    robustness = load_json("results/tables/robustness_checks.json")
    if robustness and "subgroups" in robustness and "by_difficulty" in robustness["subgroups"]:
        figures["figure7"] = {
            "title": "不同任务难度下显性度与完成率的关系",
            "description": "分组分析，展示在低/中/高难度任务中的关系稳定性",
            "type": "grouped_bar",
            "data": robustness["subgroups"]["by_difficulty"],
        }
        print("难度分组:")
        for group, result in robustness["subgroups"]["by_difficulty"].items():
            print(f"  {group}: r={result.get('correlation', 0):.3f} (n={result.get('n', 0)})")

    # 保存图表说明
    figures_path = "results/figures/figure_descriptions.json"
    with open(figures_path, "w", encoding="utf-8") as f:
        json.dump(figures, f, ensure_ascii=False, indent=2)

    print(f"\n图表说明已保存: {figures_path}")

    # 生成简单的文本图表
    text_charts_path = "results/figures/text_charts.txt"
    with open(text_charts_path, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("文本格式的图表汇总\n")
        f.write("=" * 60 + "\n\n")

        if "figure2_levels" in figures:
            f.write("图2: 操作显性度级别分布\n")
            f.write("-" * 40 + "\n")
            for level, count in figures["figure2_levels"]["data"].items():
                bar = "█" * int(count / max(1, max(figures["figure2_levels"]["data"].values())) * 50)
                f.write(f"{level:10s} | {bar} {count}\n")
            f.write("\n")

        if "figure3" in figures:
            f.write("图3: 任务完成率对比\n")
            f.write("-" * 40 + "\n")
            for level, info in figures["figure3"]["data"].items():
                rate = info.get("rate", 0)
                bar = "█" * int(rate * 50)
                f.write(f"{level:10s} | {bar} {rate:.1%} (n={info.get('n', 0)})\n")
            f.write("\n")

    print(f"文本图表已保存: {text_charts_path}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
