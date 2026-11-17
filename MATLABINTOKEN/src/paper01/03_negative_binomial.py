"""
03_negative_binomial.py - 总执行步数的负二项回归
"""
import os
import numpy as np
import pandas as pd
import statsmodels.api as sm
from patsy import dmatrices
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
    print("Step 3: 负二项回归（total_steps ~ has_completion_criteria + controls）")
    df = load_main_data()

    verif = df["instruction"].apply(classify_verification).apply(pd.Series)
    df = pd.concat([df, verif], axis=1)
    df["verification_type"] = df.apply(assign_verification_type, axis=1)
    df["verification_density"] = df.apply(compute_verification_density, axis=1)

    analysis_df = make_analysis_subset(df, "task_completed_bool")

    formula = "total_steps ~ has_completion_criteria + task_difficulty + word_count + C(os)"
    y, X = dmatrices(formula, analysis_df, return_type="dataframe")

    model = sm.NegativeBinomial(y, X, loglike_method="nb2")
    result = model.fit(disp=False)

    table = extract_model_table(result, exponentiate=True)
    rows = table.to_dict(orient="records")

    results = {
        "model": "negative_binomial_nb2",
        "formula": formula,
        "n_obs": int(result.nobs),
        "pseudo_r2": float(result.prsquared),
        "loglikelihood": float(result.llf),
        "aic": float(result.aic),
        "bic": float(result.bic),
        "alpha": float(result.params["alpha"]),
        "alpha_ci": [
            float(result.conf_int(alpha=0.05).loc["alpha", 0]),
            float(result.conf_int(alpha=0.05).loc["alpha", 1]),
        ],
        "converged": bool(result.mle_retvals.get("converged", True)),
        "iterations": int(result.mle_retvals.get("iterations", 0)),
        "notes": "IRR = incidence rate ratio; CI = 95% Wald confidence interval; alpha = NB2 dispersion parameter",
        "rows": rows,
    }

    save_json_csv(
        results,
        os.path.join(RESULT_DIR, "03_step_count_results.json"),
        os.path.join(RESULT_DIR, "03_step_count_results.csv"),
    )

    print(f"N={result.nobs}, pseudo-R2={result.prsquared:.4f}, alpha={result.params['alpha']:.4f}, AIC={result.aic:.2f}")
    print(table[["term", "or", "ci_low_or", "ci_high_or", "p_value"]].to_string(index=False))


if __name__ == "__main__":
    main()
