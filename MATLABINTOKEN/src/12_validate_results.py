"""
12_validate_results.py - 验证结果

检查所有结果的一致性，生成最终验证报告
"""

import os
import json
import pandas as pd
from datetime import datetime


def check_file_exists(path):
    """检查文件是否存在"""
    return os.path.exists(path)


def main():
    """主函数"""
    print("=" * 60)
    print("结果验证")
    print("=" * 60)

    validation_report = {
        "timestamp": datetime.now().isoformat(),
        "checks": [],
        "all_passed": True,
    }

    # 检查1: 数据文件检查
    print("\n--- 检查数据文件 ---")

    data_files = [
        ("data/interim/tasks.parquet", "任务数据"),
        ("data/interim/steps.parquet", "步骤数据"),
        ("data/interim/instruction_features.parquet", "指令特征"),
        ("data/interim/process_features.parquet", "过程特征"),
        ("data/processed/analysis_data.parquet", "分析数据"),
    ]

    for path, description in data_files:
        exists = check_file_exists(path)
        validation_report["checks"].append({
            "type": "data_file",
            "path": path,
            "description": description,
            "passed": exists,
        })
        status = "✓" if exists else "✗"
        print(f"  {status} {description}: {path}")
        if not exists:
            validation_report["all_passed"] = False

    # 检查2: 结果文件检查
    print("\n--- 检查结果文件 ---")

    result_files = [
        ("results/tables/descriptive_statistics.csv", "描述性统计表"),
        ("results/tables/table1_variable_definitions.csv", "变量定义表"),
        ("results/tables/table2_descriptive_stats.csv", "描述性统计表"),
        ("results/tables/table3_main_results.csv", "主要结果表"),
        ("results/models/main_results.json", "主要分析结果"),
        ("results/tables/robustness_checks.json", "稳健性检验结果"),
        ("results/figures/figure_descriptions.json", "图表说明"),
    ]

    for path, description in result_files:
        exists = check_file_exists(path)
        validation_report["checks"].append({
            "type": "result_file",
            "path": path,
            "description": description,
            "passed": exists,
        })
        status = "✓" if exists else "✗"
        print(f"  {status} {description}: {path}")
        if not exists:
            validation_report["all_passed"] = False

    # 检查3: 检查主要结果一致性
    print("\n--- 检查结果一致性 ---")

    # 检查分析数据中的样本量一致性
    analysis_path = "data/processed/analysis_data.parquet"
    if os.path.exists(analysis_path):
        df = pd.read_parquet(analysis_path)
        n_samples = len(df)

        main_results_path = "results/models/main_results.json"
        if os.path.exists(main_results_path):
            with open(main_results_path, "r", encoding="utf-8") as f:
                main_results = json.load(f)

            # 检查RQ1的样本量：RQ1 只用 task_completed 非缺失的行，应与其有效样本一致
            if "rq1" in main_results:
                rq1_n = main_results["rq1"].get("n")
                rq1_valid_n = int(df["task_completed"].notna().sum())
                consistent = rq1_n is None or abs(rq1_n - rq1_valid_n) < 10
                validation_report["checks"].append({
                    "type": "consistency",
                    "check": "RQ1样本量一致性",
                    "analysis_n": n_samples,
                    "rq1_valid_n": rq1_valid_n,
                    "rq1_n": rq1_n,
                    "passed": consistent,
                })
                status = "✓" if consistent else "✗"
                print(f"  {status} 样本量一致性: 分析数据={n_samples}, RQ1有效样本={rq1_valid_n}, RQ1={rq1_n}")
                if not consistent:
                    validation_report["all_passed"] = False

    # 检查4: 论文文件检查
    print("\n--- 检查论文文件 ---")

    paper_files = [
        ("paper/manuscript.md", "论文初稿"),
        ("paper/references.bib", "参考文献"),
        ("paper/supplementary_material.md", "补充材料"),
    ]

    for path, description in paper_files:
        exists = check_file_exists(path)
        validation_report["checks"].append({
            "type": "paper_file",
            "path": path,
            "description": description,
            "passed": exists,
        })
        status = "✓" if exists else "✗"
        print(f"  {status} {description}: {path}")
        if not exists:
            validation_report["all_passed"] = False

    # 保存验证报告
    os.makedirs("results", exist_ok=True)
    report_path = "results/validation_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(validation_report, f, ensure_ascii=False, indent=2)

    print(f"\n验证报告已保存: {report_path}")

    # 总结
    print("\n" + "=" * 60)
    if validation_report["all_passed"]:
        print("✓ 所有检查通过")
    else:
        print("✗ 部分检查未通过")
    print("=" * 60)

    passed = sum(1 for c in validation_report["checks"] if c["passed"])
    total = len(validation_report["checks"])
    print(f"\n通过: {passed}/{total}")

    return 0 if validation_report["all_passed"] else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
