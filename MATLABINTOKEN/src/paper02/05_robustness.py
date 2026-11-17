"""Step 5: Robustness checks and model comparison."""
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from patsy import dmatrix

from utils import (
    add_constraint_features,
    DATA_PATH,
    dawson_u_test,
    delta_method_turning_point,
    fit_logit,
    prepare_model_data,
    RESULTS_DIR,
    save_json_csv,
)


def main():
    df = pd.read_parquet(DATA_PATH)
    df = add_constraint_features(df)
    model_df = prepare_model_data(df)

    robust = {}

    # (a) Absolute constraint word count
    formula_abs = (
        "task_completed_num ~ constraint_abs_count + I(constraint_abs_count ** 2) + "
        "task_difficulty + word_count + os"
    )
    robust["absolute_count_quadratic"] = fit_logit(formula_abs, model_df)

    # (b) Constraint richness
    formula_rich = (
        "task_completed_num ~ constraint_richness + I(constraint_richness ** 2) + "
        "task_difficulty + word_count + os"
    )
    robust["richness_quadratic"] = fit_logit(formula_rich, model_df)

    # (c) OS subsamples
    robust["os_subsamples"] = {}
    for os_val in model_df["os"].unique():
        subset = model_df[model_df["os"] == os_val]
        if len(subset) < 200:
            continue
        try:
            res = fit_logit(
                "task_completed_num ~ constraint_density + I(constraint_density ** 2) + "
                "task_difficulty + word_count",
                subset,
            )
            robust["os_subsamples"][str(os_val)] = res
        except Exception as e:
            robust["os_subsamples"][str(os_val)] = {"error": str(e)}

    # (d) RCS with 3 knots via patsy cr()
    formula_rcs = "task_completed_num ~ cr(constraint_density, df=3) + task_difficulty + word_count + os"
    try:
        rcs_model = smf.logit(formula=formula_rcs, data=model_df)
        try:
            rcs_fit = rcs_model.fit(disp=0, maxiter=200)
        except Exception:
            rcs_fit = rcs_model.fit(disp=0, method="bfgs", maxiter=500)
        rcs_summary = fit_logit(formula_rcs, model_df)
        robust["rcs_3knots"] = {
            **rcs_summary,
            "knots": list(
                np.percentile(model_df["constraint_density"], [10, 50, 90])
            ),
        }
    except Exception as e:
        robust["rcs_3knots"] = {"error": str(e)}

    save_json_csv(robust, "05_robustness_check")

    # Human-readable robustness summary CSV
    robust_rows = []
    for key, val in robust.items():
        if key == "os_subsamples":
            for os_name, os_res in val.items():
                if "error" in os_res:
                    robust_rows.append({"specification": f"os_{os_name}", "error": os_res["error"]})
                else:
                    robust_rows.append(
                        {
                            "specification": f"os_{os_name}",
                            "nobs": os_res["nobs"],
                            "aic": os_res["aic"],
                            "bic": os_res["bic"],
                            "pseudo_r2_mcfadden": os_res["pseudo_r2_mcfadden"],
                        }
                    )
        elif "error" in val:
            robust_rows.append({"specification": key, "error": val["error"]})
        else:
            robust_rows.append(
                {
                    "specification": key,
                    "nobs": val["nobs"],
                    "aic": val["aic"],
                    "bic": val["bic"],
                    "pseudo_r2_mcfadden": val["pseudo_r2_mcfadden"],
                }
            )
    pd.DataFrame(robust_rows).to_csv(RESULTS_DIR / "05_robustness_check.csv", index=False)

    # Model comparison CSV
    models = {
        "linear_density": "task_completed_num ~ constraint_density + task_difficulty + word_count + os",
        "quadratic_density": (
            "task_completed_num ~ constraint_density + I(constraint_density ** 2) + "
            "task_difficulty + word_count + os"
        ),
        "absolute_count_quadratic": formula_abs,
        "richness_quadratic": formula_rich,
        "rcs_3knots": formula_rcs,
    }

    comparison = []
    for name, formula in models.items():
        try:
            res = fit_logit(formula, model_df)
            comparison.append(
                {
                    "model": name,
                    "nobs": res["nobs"],
                    "aic": res["aic"],
                    "bic": res["bic"],
                    "pseudo_r2_mcfadden": res["pseudo_r2_mcfadden"],
                    "llf": res["llf"],
                }
            )
        except Exception as e:
            comparison.append({"model": name, "error": str(e)})

    pd.DataFrame(comparison).to_csv(RESULTS_DIR / "model_comparison.csv", index=False)

    print("Step 5 complete.")
    print(pd.DataFrame(comparison).to_string(index=False))


if __name__ == "__main__":
    main()
