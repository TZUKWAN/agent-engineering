"""
02_logistic.py - 任务完成率的 Logistic 回归
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
    print("Step 2: Logistic 回归（task_completed ~ has_completion_criteria + controls）")
    df = load_main_data()

    # 复用标注字段
    verif = df["instruction"].apply(classify_verification).apply(pd.Series)
    df = pd.concat([df, verif], axis=1)
    df["verification_type"] = df.apply(assign_verification_type, axis=1)
    df["verification_density"] = df.apply(compute_verification_density, axis=1)

    analysis_df = make_analysis_subset(df, "task_completed_bool")
    analysis_df["task_completed_num"] = analysis_df["task_completed_bool"].astype(int)

    formula = "task_completed_num ~ has_completion_criteria + task_difficulty + word_count + C(os)"
    model = smf.logit(formula=formula, data=analysis_df)
    result = model.fit(disp=False)

    table = extract_model_table(result, exponentiate=True)
    rows = table.to_dict(orient="records")

    results = {
        "model": "logistic",
        "formula": formula,
        "n_obs": int(result.nobs),
        "pseudo_r2": float(result.prsquared),
        "loglikelihood": float(result.llf),
        "aic": float(result.aic),
        "bic": float(result.bic),
        "converged": bool(result.mle_retvals.get("converged", True)),
        "iterations": int(result.mle_retvals.get("iterations", 0)),
        "notes": "OR = odds ratio; CI = 95% Wald confidence interval",
        "rows": rows,
    }

    save_json_csv(
        results,
        os.path.join(RESULT_DIR, "02_logistic_results.json"),
        os.path.join(RESULT_DIR, "02_logistic_results.csv"),
    )

    print(f"N={result.nobs}, pseudo-R2={result.prsquared:.4f}, AIC={result.aic:.2f}")
    print(table[["term", "or", "ci_low_or", "ci_high_or", "p_value"]].to_string(index=False))


if __name__ == "__main__":
    main()
