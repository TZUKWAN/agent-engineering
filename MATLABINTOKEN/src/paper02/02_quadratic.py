"""Step 2: Quadratic logistic regression and turning point analysis."""
import json

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from utils import (
    add_constraint_features,
    DATA_PATH,
    dawson_u_test,
    delta_method_turning_point,
    fit_logit,
    prepare_model_data,
    RESULTS_DIR,
    save_json_csv,
    cohens_f2,
    CONSTRAINT_KEYWORDS,
)


def main():
    df = pd.read_parquet(DATA_PATH)
    df = add_constraint_features(df)
    model_df = prepare_model_data(df)
    # Stage-1（约束有无）模型需要二值列；无约束即密度为 0
    model_df = model_df.copy()
    model_df["has_constraint_words"] = (model_df["constraint_density"] > 0).astype(int)

    base_formula = "task_completed_num ~ constraint_density + task_difficulty + word_count + os"
    quad_formula = (
        "task_completed_num ~ constraint_density + I(constraint_density ** 2) + task_difficulty + word_count + os"
    )

    presence_formula = "task_completed_num ~ has_constraint_words + task_difficulty + word_count + os"

    # Stage-1: 约束有无效应（论文正文的 OR 引用来源）
    stage1_res = fit_logit(presence_formula, model_df)

    # Stage-2: 仅含约束任务子样本内的全局密度二次项
    constrained_df = model_df[model_df["has_constraint_words"] == 1]
    stage2_res = fit_logit(quad_formula, constrained_df)

    # Linear model for comparison
    linear_res = fit_logit(base_formula, model_df)
    # Quadratic model
    quad_model = smf.logit(formula=quad_formula, data=model_df)
    try:
        quad_fit = quad_model.fit(disp=0, maxiter=200)
    except Exception:
        quad_fit = quad_model.fit(disp=0, method="bfgs", maxiter=500)
    quad_res = fit_logit(quad_formula, model_df)
    # Reuse the actual fit object for detailed inference.

    params = quad_fit.params
    cov = quad_fit.cov_params()
    b1 = params["constraint_density"]
    b2 = params["I(constraint_density ** 2)"]

    x_min = float(model_df["constraint_density"].min())
    x_max = float(model_df["constraint_density"].max())
    x_mean = float(model_df["constraint_density"].mean())

    # Turning point
    tp, se_tp, ci_low, ci_high = delta_method_turning_point(
        b1, b2,
        cov.loc["constraint_density", "constraint_density"],
        cov.loc["I(constraint_density ** 2)", "I(constraint_density ** 2)"],
        cov.loc["constraint_density", "I(constraint_density ** 2)"],
    )

    # In-range flag
    in_range = bool(ci_low <= tp <= x_max)  # density is non-negative

    # Dawson U-test
    dawson = dawson_u_test(quad_fit, x_min, x_max)

    # Cohen's f2 vs linear
    f2 = cohens_f2(quad_res["pseudo_r2_mcfadden"], linear_res["pseudo_r2_mcfadden"])

    # Exploratory process-outcome models
    process_models = {}
    # Negative binomial for total_steps
    try:
        nb_model = smf.negativebinomial(
            "total_steps ~ constraint_density + I(constraint_density ** 2) + task_difficulty + word_count + os",
            data=model_df,
        )
        try:
            nb_fit = nb_model.fit(disp=0, maxiter=200)
        except Exception:
            nb_fit = nb_model.fit(disp=0, method="bfgs", maxiter=500)
        process_models["total_steps_negativebinomial"] = {
            "nobs": int(nb_fit.nobs),
            "aic": float(nb_fit.aic),
            "bic": float(nb_fit.bic),
            "pseudo_r2_mcfadden": float(1 - nb_fit.llf / nb_fit.llnull),
            "coef_table": [
                {
                    "term": t,
                    "coef": float(nb_fit.params[t]),
                    "se": float(nb_fit.bse[t]),
                    "z": float(nb_fit.params[t] / nb_fit.bse[t]) if nb_fit.bse[t] > 0 else None,
                    "pvalue": float(nb_fit.pvalues[t]),
                    "significant_05": float(nb_fit.pvalues[t]) < 0.05,
                }
                for t in nb_fit.params.index
            ],
        }
    except Exception as e:
        process_models["total_steps_negativebinomial"] = {"error": str(e)}

    # OLS for redundant_ratio
    try:
        ols_model = smf.ols(
            "redundant_ratio ~ constraint_density + I(constraint_density ** 2) + task_difficulty + word_count + os",
            data=model_df,
        )
        ols_fit = ols_model.fit()
        process_models["redundant_ratio_ols"] = {
            "nobs": int(ols_fit.nobs),
            "aic": float(ols_fit.aic),
            "bic": float(ols_fit.bic),
            "r2": float(ols_fit.rsquared),
            "adj_r2": float(ols_fit.rsquared_adj),
            "coef_table": [
                {
                    "term": t,
                    "coef": float(ols_fit.params[t]),
                    "se": float(ols_fit.bse[t]),
                    "t": float(ols_fit.tvalues[t]),
                    "pvalue": float(ols_fit.pvalues[t]),
                    "significant_05": float(ols_fit.pvalues[t]) < 0.05,
                }
                for t in ols_fit.params.index
            ],
        }
    except Exception as e:
        process_models["redundant_ratio_ols"] = {"error": str(e)}

    output = {
        "sample_size": int(len(model_df)),
        "density_range": {"min": x_min, "max": x_max, "mean": x_mean},
        "stage1_presence_model": stage1_res,
        "stage2_constrained_quadratic": stage2_res,
        "linear_model": linear_res,
        "quadratic_model": quad_res,
        "quadratic_term": {
            "coef": float(b2),
            "se": float(quad_fit.bse["I(constraint_density ** 2)"]),
            "pvalue": float(quad_fit.pvalues["I(constraint_density ** 2)"]),
            "negative_and_significant": bool(b2 < 0 and quad_fit.pvalues["I(constraint_density ** 2)"] < 0.05),
        },
        "turning_point": {
            "estimate": float(tp),
            "se": se_tp,
            "ci_95_low": ci_low,
            "ci_95_high": ci_high,
            "inside_observed_range": in_range,
        },
        "dawson_u_test": dawson,
        "cohens_f2_quadratic": f2,
        "exploratory_process_models": process_models,
    }

    save_json_csv(output, "02_quadratic_results")

    # Human-readable CSV: quadratic model coefficient table + key summaries
    csv_rows = []
    for r in quad_res["coef_table"]:
        csv_rows.append({
            "section": "quadratic_model",
            "term": r["term"],
            "coef": r["coef"],
            "se": r["se"],
            "or": r["or"],
            "or_ci_low": r["or_ci_low"],
            "or_ci_high": r["or_ci_high"],
            "pvalue": r["pvalue"],
        })
    csv_rows.append({
        "section": "summary",
        "term": "turning_point",
        "coef": tp,
        "se": se_tp,
        "or_ci_low": ci_low,
        "or_ci_high": ci_high,
        "pvalue": float(quad_fit.pvalues["I(constraint_density ** 2)"]),
    })
    csv_rows.append({
        "section": "summary",
        "term": "cohens_f2_quadratic",
        "coef": f2,
    })
    csv_rows.append({
        "section": "summary",
        "term": "sample_size",
        "coef": len(model_df),
    })
    pd.DataFrame(csv_rows).to_csv(RESULTS_DIR / "02_quadratic_results.csv", index=False)

    print("Step 2 complete.")
    print(f"Quadratic term: coef={b2:.4f}, p={quad_fit.pvalues['I(constraint_density ** 2)']:.4f}")
    print(f"Turning point: {tp:.2f} [{ci_low:.2f}, {ci_high:.2f}]")
    print(f"Dawson U-test: {dawson}")


if __name__ == "__main__":
    main()
