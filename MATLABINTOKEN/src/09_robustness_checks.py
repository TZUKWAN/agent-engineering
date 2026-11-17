"""
09_robustness_checks.py - 稳健性检验

进行多种稳健性检验：不同变量定义、子样本分析等
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
    # 皮尔逊相关与精确 p 值；此前的 exp 近似公式在负相关时给出 p>1
    corr, p = stats.pearsonr(x_valid, y_valid)
    n = len(x_valid)
    return corr, p, n


def main():
    """主函数"""
    print("=" * 60)
    print("稳健性检验")
    print("=" * 60)

    df = load_analysis_data()

    if df is None or len(df) == 0:
        print("\n未找到分析数据")
        return 1

    print(f"\n样本数: {len(df)}")

    os.makedirs("results/tables", exist_ok=True)

    robustness_results = {}

    # 检验1: 使用不同的文本字段
    print("\n--- 检验1: 不同文本字段 ---")

    text_fields = []
    for prefix in ["instruction", "natural_language_task", "actual_task"]:
        field = f"{prefix}_explicitness_score"
        if field in df.columns:
            text_fields.append(prefix)

    field_results = {}
    for prefix in text_fields:
        exp_col = f"{prefix}_explicitness_score"
        if exp_col in df.columns and "task_completed" in df.columns:
            corr, p, n = safe_corr(df[exp_col], pd.to_numeric(df["task_completed"], errors="coerce"))
            field_results[prefix] = {
                "correlation": float(corr) if not np.isnan(corr) else None,
                "p_value": float(p) if not np.isnan(p) else None,
                "n": int(n),
            }
            print(f"{prefix}: r={corr:.3f} (p={p:.3f}, n={n})")

    robustness_results["text_fields"] = field_results

    # 检验2: 使用单项特征而非综合指数
    print("\n--- 检验2: 单项特征 ---")

    binary_features = [
        "has_application", "has_operation_object", "has_target_action",
        "has_target_state", "has_file_reference", "has_object_properties",
        "has_operation_order", "has_multiple_subtasks", "has_constraint_words",
        "has_completion_criteria", "has_initial_state",
    ]

    feature_results = {}
    for feat in binary_features:
        if feat in df.columns and "task_completed" in df.columns:
            corr, p, n = safe_corr(
                pd.to_numeric(df[feat], errors="coerce"),
                pd.to_numeric(df["task_completed"], errors="coerce")
            )
            feature_results[feat] = {
                "correlation": float(corr) if not np.isnan(corr) else None,
                "p_value": float(p) if not np.isnan(p) else None,
                "n": int(n),
            }
            print(f"{feat}: r={corr:.3f}")

    robustness_results["individual_features"] = feature_results

    # 检验3: 控制文本长度
    print("\n--- 检验3: 控制文本长度 ---")

    if all(v in df.columns for v in ["explicitness_score", "word_count", "task_completed"]):
        # 计算偏相关（简化版本）
        exp_comp, p1, n1 = safe_corr(df["explicitness_score"], pd.to_numeric(df["task_completed"], errors="coerce"))
        exp_len, p2, n2 = safe_corr(df["explicitness_score"], df["word_count"])
        len_comp, p3, n3 = safe_corr(df["word_count"], pd.to_numeric(df["task_completed"], errors="coerce"))

        # 一阶偏相关近似
        if not np.isnan(exp_comp) and not np.isnan(exp_len) and not np.isnan(len_comp):
            partial_corr = (exp_comp - exp_len * len_comp) / np.sqrt((1 - exp_len**2) * (1 - len_comp**2))
        else:
            partial_corr = np.nan

        robustness_results["controlling_length"] = {
            "simple_correlation": float(exp_comp) if not np.isnan(exp_comp) else None,
            "partial_correlation": float(partial_corr) if not np.isnan(partial_corr) else None,
            "explicitness_length_correlation": float(exp_len) if not np.isnan(exp_len) else None,
            "length_completion_correlation": float(len_comp) if not np.isnan(len_comp) else None,
        }
        print(f"简单相关: {exp_comp:.3f}")
        print(f"控制长度后的偏相关: {partial_corr:.3f}")

    # 检验4: 排除极端轨迹
    print("\n--- 检验4: 排除极端轨迹 ---")

    if "total_steps" in df.columns and "explicitness_score" in df.columns and "task_completed" in df.columns:
        # 排除最长10%的轨迹
        p90 = df["total_steps"].quantile(0.9)
        mask = df["total_steps"] <= p90
        df_trimmed = df[mask]

        corr_full, p1, n1 = safe_corr(df["explicitness_score"], pd.to_numeric(df["task_completed"], errors="coerce"))
        corr_trimmed, p2, n2 = safe_corr(df_trimmed["explicitness_score"], pd.to_numeric(df_trimmed["task_completed"], errors="coerce"))

        robustness_results["excluding_extremes"] = {
            "full_sample": {"correlation": float(corr_full) if not np.isnan(corr_full) else None, "n": int(n1)},
            "trimmed_sample": {"correlation": float(corr_trimmed) if not np.isnan(corr_trimmed) else None, "n": int(n2)},
            "excluded_percent": 10.0,
        }
        print(f"完整样本: r={corr_full:.3f} (n={n1})")
        print(f"剔除极端值: r={corr_trimmed:.3f} (n={n2})")

    # 检验5: 分组检验
    print("\n--- 检验5: 分组检验 ---")

    subgroup_results = {}

    # 按任务难度分组（如果有）
    if "task_difficulty" in df.columns:
        difficulty_groups = {}
        q25 = df["task_difficulty"].quantile(0.25)
        q75 = df["task_difficulty"].quantile(0.75)

        for name, mask in [
            ("low_difficulty", df["task_difficulty"] <= q25),
            ("medium_difficulty", (df["task_difficulty"] > q25) & (df["task_difficulty"] < q75)),
            ("high_difficulty", df["task_difficulty"] >= q75),
        ]:
            if mask.sum() >= 10:
                corr, p, n = safe_corr(
                    df.loc[mask, "explicitness_score"],
                    pd.to_numeric(df.loc[mask, "task_completed"], errors="coerce")
                )
                difficulty_groups[name] = {
                    "correlation": float(corr) if not np.isnan(corr) else None,
                    "n": int(n),
                }
                print(f"{name}: r={corr:.3f} (n={n})")

        subgroup_results["by_difficulty"] = difficulty_groups

    # 按操作系统分组（如果有）
    if "os" in df.columns:
        os_groups = {}
        for os_val in df["os"].dropna().unique():
            mask = df["os"] == os_val
            if mask.sum() >= 10:
                corr, p, n = safe_corr(
                    df.loc[mask, "explicitness_score"],
                    pd.to_numeric(df.loc[mask, "task_completed"], errors="coerce")
                )
                os_groups[str(os_val)] = {
                    "correlation": float(corr) if not np.isnan(corr) else None,
                    "n": int(n),
                }
                print(f"OS={os_val}: r={corr:.3f} (n={n})")

        subgroup_results["by_os"] = os_groups

    robustness_results["subgroups"] = subgroup_results

    # 保存结果
    results_path = "results/tables/robustness_checks.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(robustness_results, f, ensure_ascii=False, indent=2)

    print(f"\n稳健性检验结果已保存: {results_path}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
