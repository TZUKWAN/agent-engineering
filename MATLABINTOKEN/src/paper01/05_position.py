"""
05_position.py - 验证标准位置分析
"""
import os
import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency
from statsmodels.stats.proportion import proportions_ztest
from helpers import (
    SEED,
    RESULT_DIR,
    load_main_data,
    classify_verification,
    assign_verification_type,
    compute_verification_density,
    locate_first_verification_position,
    save_json_csv,
)

np.random.seed(SEED)


def cramers_v(chi2, n, r, c):
    return np.sqrt(chi2 / (n * min(r - 1, c - 1)))


def main():
    print("Step 5: 验证标准位置分析")
    df = load_main_data()

    verif = df["instruction"].apply(classify_verification).apply(pd.Series)
    df = pd.concat([df, verif], axis=1)
    df["verification_type"] = df.apply(assign_verification_type, axis=1)
    df["verification_density"] = df.apply(compute_verification_density, axis=1)

    position_df = df["instruction"].apply(locate_first_verification_position).apply(pd.Series)
    df["verification_position_rel"] = position_df["relative_position"]
    df["verification_position_region"] = position_df["position_region"]

    # 位置分析聚焦 has_completion_criteria==1 且能定位到关键词的子集
    sub = df[(df["has_completion_criteria"] == 1) & (df["verification_position_region"] != "no_keyword")].copy()
    sub = sub.dropna(subset=["task_completed_bool", "task_difficulty"])
    sub["task_completed_num"] = sub["task_completed_bool"].astype(int)

    region_order = ["start", "middle", "end"]
    summary_rows = []
    for region in region_order:
        region_data = sub[sub["verification_position_region"] == region]
        n = len(region_data)
        completed = int(region_data["task_completed_num"].sum())
        rate = region_data["task_completed_num"].mean() if n > 0 else np.nan
        summary_rows.append(
            {
                "position_region": region,
                "n": n,
                "completed": completed,
                "completion_rate": float(rate) if not np.isnan(rate) else None,
                "mean_word_count": float(region_data["word_count"].mean()),
                "mean_verification_density": float(region_data["verification_density"].mean()),
            }
        )

    # 卡方检验
    contingency = pd.crosstab(sub["verification_position_region"], sub["task_completed_num"])
    contingency = contingency.reindex(region_order, fill_value=0)
    chi2, pvalue, dof, expected = chi2_contingency(contingency)
    n_total = contingency.sum().sum()
    cv = cramers_v(chi2, n_total, *contingency.shape)

    # 两两比较（Z 检验）+ Bonferroni 校正
    pairs = [("start", "middle"), ("start", "end"), ("middle", "end")]
    pairwise = []
    counts = {r: int(contingency.loc[r, 1]) if 1 in contingency.columns else 0 for r in region_order}
    totals = {r: int(contingency.loc[r].sum()) for r in region_order}
    rates = {r: counts[r] / totals[r] if totals[r] > 0 else np.nan for r in region_order}

    for a, b in pairs:
        count_arr = np.array([counts[a], counts[b]])
        nobs_arr = np.array([totals[a], totals[b]])
        z_stat, p_raw = proportions_ztest(count_arr, nobs_arr)
        pairwise.append(
            {
                "pair": f"{a}_vs_{b}",
                "rate_a": rates[a],
                "rate_b": rates[b],
                "diff": rates[a] - rates[b] if not np.isnan(rates[a]) and not np.isnan(rates[b]) else None,
                "z_statistic": float(z_stat),
                "p_value_raw": float(p_raw),
                "p_value_bonferroni": min(float(p_raw) * len(pairs), 1.0),
            }
        )

    results = {
        "subset": "has_completion_criteria == 1 and verification keyword locatable",
        "n_obs": int(len(sub)),
        "position_thresholds": {"start_end": 0.25, "middle_end": 0.75},
        "threshold_description": "relative character position < 0.25 = start; 0.25-0.75 = middle; >= 0.75 = end",
        "summary": summary_rows,
        "chi_square_test": {
            "chi2": float(chi2),
            "df": int(dof),
            "p_value": float(pvalue),
            "cramers_v": float(cv),
        },
        "contingency_table": contingency.to_dict(orient="index"),
        "pairwise_comparisons": pairwise,
        "notes": "Pairwise p-values are Bonferroni-adjusted (3 comparisons).",
    }

    save_json_csv(
        results,
        os.path.join(RESULT_DIR, "05_position_analysis.json"),
        os.path.join(RESULT_DIR, "05_position_analysis.csv"),
    )

    print(f"N={len(sub)}, chi2={chi2:.3f}, p={pvalue:.4f}, Cramer's V={cv:.4f}")
    for row in summary_rows:
        print(
            f"  {row['position_region']}: n={row['n']}, completed={row['completed']}, "
            f"rate={row['completion_rate']:.3f}"
        )


if __name__ == "__main__":
    main()
