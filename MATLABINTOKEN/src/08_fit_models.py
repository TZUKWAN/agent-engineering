"""
08_fit_models.py - 拟合统计模型

进行主要的统计分析：相关性、回归、中介分析
"""

import os
import json
import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime


def load_analysis_data():
    """加载分析数据"""
    path = "data/processed/analysis_data.parquet"
    if os.path.exists(path):
        return pd.read_parquet(path)
    return None


def safe_corr(x, y):
    """安全计算相关系数（p 值为 Pearson 精确 t 检验，双侧）"""
    valid = ~(pd.isna(x) | pd.isna(y))
    if valid.sum() < 3:
        return np.nan, np.nan, valid.sum()
    x_valid = x[valid]
    y_valid = y[valid]
    # 皮尔逊相关与精确 p 值（t 分布，双侧）；此前的 exp 近似公式在负相关时给出 p>1
    corr, p = stats.pearsonr(x_valid, y_valid)
    n = len(x_valid)
    return corr, p, n


def main():
    """主函数"""
    print("=" * 60)
    print("统计建模")
    print("=" * 60)

    df = load_analysis_data()

    if df is None or len(df) == 0:
        print("\n未找到分析数据")
        return 1

    print(f"\n样本数: {len(df)}")

    os.makedirs("results/tables", exist_ok=True)
    os.makedirs("results/models", exist_ok=True)

    results = {}

    # RQ1: 显性度与任务完成率的关联
    print("\n--- RQ1: 显性度与任务完成率 ---")

    if "explicitness_score" in df.columns and "task_completed" in df.columns:
        exp_col = df["explicitness_score"]
        comp_col = df["task_completed"]

        # 转换为数值
        comp_numeric = pd.to_numeric(comp_col, errors="coerce")

        corr, p, n = safe_corr(exp_col, comp_numeric)

        results["rq1"] = {
            "correlation": float(corr) if not np.isnan(corr) else None,
            "p_value": float(p) if not np.isnan(p) else None,
            "n": int(n),
        }

        print(f"相关系数: {corr:.3f} (p={p:.3f}, n={n})")

        # 按显性度级别分组的完成率
        if "explicitness_level" in df.columns:
            level_completion = {}
            for level in ["low", "medium", "high"]:
                mask = df["explicitness_level"] == level
                if mask.sum() > 0:
                    level_data = comp_numeric[mask]
                    completion_rate = level_data.mean()
                    level_completion[level] = {
                        "rate": float(completion_rate) if not pd.isna(completion_rate) else None,
                        "n": int(mask.sum()),
                    }
            results["rq1"]["by_level"] = level_completion
            print("\n按显性度级别:")
            for level, info in level_completion.items():
                print(f"  {level}: {info['rate']:.1%} (n={info['n']})")

    # RQ2: 显性度与效率、对齐评分的关联
    print("\n--- RQ2: 显性度与效率、对齐评分 ---")

    rq2_results = {}
    for outcome in ["efficiency_score", "alignment_score"]:
        if outcome in df.columns and "explicitness_score" in df.columns:
            corr, p, n = safe_corr(df["explicitness_score"], df[outcome])
            rq2_results[outcome] = {
                "correlation": float(corr) if not np.isnan(corr) else None,
                "p_value": float(p) if not np.isnan(p) else None,
                "n": int(n),
            }
            print(f"{outcome}: r={corr:.3f} (p={p:.3f}, n={n})")

    results["rq2"] = rq2_results

    # RQ3: 显性度与错误、冗余的关联
    print("\n--- RQ3: 显性度与错误、冗余 ---")

    rq3_results = {}
    for process_var in ["incorrect_ratio", "redundant_ratio"]:
        if process_var in df.columns and "explicitness_score" in df.columns:
            corr, p, n = safe_corr(df["explicitness_score"], df[process_var])
            rq3_results[process_var] = {
                "correlation": float(corr) if not np.isnan(corr) else None,
                "p_value": float(p) if not np.isnan(p) else None,
                "n": int(n),
            }
            print(f"{process_var}: r={corr:.3f} (p={p:.3f}, n={n})")

    results["rq3"] = rq3_results

    # RQ4: 中介分析（错误、冗余作为中介）
    print("\n--- RQ4: 中介分析 ---")

    rq4_results = {}

    # 路径1: 显性度 -> 错误比例 -> 任务完成
    if all(v in df.columns for v in ["explicitness_score", "incorrect_ratio", "task_completed"]):
        exp_to_error, p1, n1 = safe_corr(df["explicitness_score"], df["incorrect_ratio"])
        error_to_comp, p2, n2 = safe_corr(df["incorrect_ratio"], pd.to_numeric(df["task_completed"], errors="coerce"))
        exp_to_comp, p3, n3 = safe_corr(df["explicitness_score"], pd.to_numeric(df["task_completed"], errors="coerce"))

        rq4_results["error_mediation"] = {
            "explicitness_to_error": float(exp_to_error) if not np.isnan(exp_to_error) else None,
            "error_to_completion": float(error_to_comp) if not np.isnan(error_to_comp) else None,
            "explicitness_to_completion": float(exp_to_comp) if not np.isnan(exp_to_comp) else None,
        }
        print("错误比例中介路径:")
        print(f"  显性度 -> 错误: {exp_to_error:.3f}")
        print(f"  错误 -> 完成: {error_to_comp:.3f}")
        print(f"  显性度 -> 完成: {exp_to_comp:.3f}")

    # 路径2: 显性度 -> 冗余比例 -> 任务完成
    if all(v in df.columns for v in ["explicitness_score", "redundant_ratio", "task_completed"]):
        exp_to_red, p1, n1 = safe_corr(df["explicitness_score"], df["redundant_ratio"])
        red_to_comp, p2, n2 = safe_corr(df["redundant_ratio"], pd.to_numeric(df["task_completed"], errors="coerce"))

        rq4_results["redundant_mediation"] = {
            "explicitness_to_redundant": float(exp_to_red) if not np.isnan(exp_to_red) else None,
            "redundant_to_completion": float(red_to_comp) if not np.isnan(red_to_comp) else None,
        }
        print("\n冗余比例中介路径:")
        print(f"  显性度 -> 冗余: {exp_to_red:.3f}")
        print(f"  冗余 -> 完成: {red_to_comp:.3f}")

    results["rq4"] = rq4_results

    # 相关性矩阵
    print("\n--- 相关性矩阵 ---")

    key_vars = [
        "explicitness_score", "task_completed", "efficiency_score", "alignment_score",
        "incorrect_ratio", "redundant_ratio", "word_count", "total_steps"
    ]

    available_vars = [v for v in key_vars if v in df.columns]
    if available_vars:
        corr_matrix = {}
        for v1 in available_vars:
            corr_matrix[v1] = {}
            for v2 in available_vars:
                corr, p, n = safe_corr(
                    pd.to_numeric(df[v1], errors="coerce"),
                    pd.to_numeric(df[v2], errors="coerce")
                )
                corr_matrix[v1][v2] = {
                    "r": float(corr) if not np.isnan(corr) else None,
                    "p": float(p) if not np.isnan(p) else None,
                    "n": int(n),
                }

        results["correlation_matrix"] = corr_matrix

        # 显示相关性矩阵
        print("\t" + "\t".join(available_vars))
        for v1 in available_vars:
            row = [v1[:10]]
            for v2 in available_vars:
                r = corr_matrix[v1][v2]["r"]
                row.append(f"{r:.2f}" if r is not None else "NA")
            print("\t".join(row))

    # 保存结果
    results_path = "results/models/main_results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n主要结果已保存: {results_path}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
