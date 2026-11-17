"""
04_nonlinear.py - 验证密度二次项的非线性 Logistic 回归
"""
import os
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from helpers import (
    SEED,
    RESULT_DIR,
    load_main_data,
    classify_verification,
    assign_verification_type,
    compute_verification_density,
    make_analysis_subset,
    save_json_csv,
    extract_model_table,
)

np.random.seed(SEED)


def main():
    print("Step 4: 非线性 Logistic 回归（验证密度的二次项）")
    df = load_main_data()

    verif = df["instruction"].apply(classify_verification).apply(pd.Series)
    df = pd.concat([df, verif], axis=1)
    df["verification_type"] = df.apply(assign_verification_type, axis=1)
    df["verification_density"] = df.apply(compute_verification_density, axis=1)

    analysis_df = make_analysis_subset(df, "task_completed_bool")
    analysis_df["task_completed_num"] = analysis_df["task_completed_bool"].astype(int)

    # 二次项
    analysis_df["verification_density_sq"] = analysis_df["verification_density"] ** 2

    formula_linear = "task_completed_num ~ verification_density + task_difficulty + word_count + C(os)"
    formula_quad = "task_completed_num ~ verification_density + verification_density_sq + task_difficulty + word_count + C(os)"

    res_linear = smf.logit(formula=formula_linear, data=analysis_df).fit(disp=False)
    res_quad = smf.logit(formula=formula_quad, data=analysis_df).fit(disp=False)

    table_linear = extract_model_table(res_linear, exponentiate=True)
    table_quad = extract_model_table(res_quad, exponentiate=True)

    quad_density_row = table_quad[table_quad["term"] == "verification_density"].iloc[0]
    quad_sq_row = table_quad[table_quad["term"] == "verification_density_sq"].iloc[0]

    # 计算倒 U 形拐点（基于 log-odds 系数）
    b1 = res_quad.params.get("verification_density", np.nan)
    b2 = res_quad.params.get("verification_density_sq", np.nan)
    if not np.isnan(b1) and not np.isnan(b2) and b2 != 0:
        turning_point = -b1 / (2 * b2)
    else:
        turning_point = np.nan

    # 似然比检验：二次项 vs 线性模型
    lr_stat = 2 * (res_quad.llf - res_linear.llf)
    lr_pvalue = float(
        __import__("scipy.stats").stats.chi2.sf(lr_stat, df=1)
    )

    results = {
        "model_quad": {
            "formula": formula_quad,
            "n_obs": int(res_quad.nobs),
            "pseudo_r2": float(res_quad.prsquared),
            "loglikelihood": float(res_quad.llf),
            "aic": float(res_quad.aic),
            "bic": float(res_quad.bic),
            "converged": bool(res_quad.mle_retvals.get("converged", True)),
            "rows": table_quad.to_dict(orient="records"),
        },
        "model_linear": {
            "formula": formula_linear,
            "n_obs": int(res_linear.nobs),
            "pseudo_r2": float(res_linear.prsquared),
            "loglikelihood": float(res_linear.llf),
            "aic": float(res_linear.aic),
            "bic": float(res_linear.bic),
            "converged": bool(res_linear.mle_retvals.get("converged", True)),
            "rows": table_linear.to_dict(orient="records"),
        },
        "quadratic_term_test": {
            "coef": float(quad_sq_row["coef"]),
            "or": float(quad_sq_row["or"]),
            "ci_low_or": float(quad_sq_row["ci_low_or"]),
            "ci_high_or": float(quad_sq_row["ci_high_or"]),
            "p_value": float(quad_sq_row["p_value"]),
        },
        "density_term": {
            "coef": float(quad_density_row["coef"]),
            "or": float(quad_density_row["or"]),
            "ci_low_or": float(quad_density_row["ci_low_or"]),
            "ci_high_or": float(quad_density_row["ci_high_or"]),
            "p_value": float(quad_density_row["p_value"]),
        },
        "turning_point": float(turning_point) if not np.isnan(turning_point) else None,
        "likelihood_ratio_test": {
            "lr_statistic": float(lr_stat),
            "df": 1,
            "p_value": lr_pvalue,
        },
        "aic_comparison": {
            "quad_aic": float(res_quad.aic),
            "linear_aic": float(res_linear.aic),
            "delta_aic": float(res_linear.aic - res_quad.aic),
            "preferred": "quad" if res_quad.aic < res_linear.aic else "linear",
        },
        "notes": (
            "OR = odds ratio; CI = 95% Wald CI; verification_density = verification keyword count / word_count; "
            "turning_point = -b1/(2*b2) on the log-odds scale."
        ),
    }

    save_json_csv(
        results,
        os.path.join(RESULT_DIR, "04_nonlinear_results.json"),
        os.path.join(RESULT_DIR, "04_nonlinear_results.csv"),
    )

    print(f"Quadratic N={res_quad.nobs}, pseudo-R2={res_quad.prsquared:.4f}, AIC={res_quad.aic:.2f}")
    print(f"Linear    N={res_linear.nobs}, pseudo-R2={res_linear.prsquared:.4f}, AIC={res_linear.aic:.2f}")
    print(f"LR test chi2={lr_stat:.3f}, p={lr_pvalue:.4f}")
    print(f"Turning point density={turning_point:.4f}")
    print(table_quad[["term", "coef", "or", "ci_low_or", "ci_high_or", "p_value"]].to_string(index=False))


if __name__ == "__main__":
    main()
