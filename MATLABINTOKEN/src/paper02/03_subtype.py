"""Step 3: Subtype-specific quadratic logistic models (C1-C4)."""
import pandas as pd
import statsmodels.formula.api as smf

from utils import (
    add_constraint_features,
    CONSTRAINT_KEYWORDS,
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

    subtype_results = []
    for ckey in CONSTRAINT_KEYWORDS.keys():
        short = ckey.split("_")[1]  # prohibitive, preservative, obligative, restrictive
        density_col = f"density_{short}"
        # Only tasks that ever use this subtype still included; density is 0 for others.
        formula = (
            f"task_completed_num ~ {density_col} + I({density_col} ** 2) + task_difficulty + word_count + os"
        )
        try:
            res = fit_logit(formula, model_df)
            model = smf.logit(formula=formula, data=model_df)
            try:
                fit = model.fit(disp=0, maxiter=200)
            except Exception:
                fit = model.fit(disp=0, method="bfgs", maxiter=500)
            params = fit.params
            cov = fit.cov_params()
            b1 = params[density_col]
            b2 = params[f"I({density_col} ** 2)"]
            x_min = float(model_df[density_col].min())
            x_max = float(model_df[density_col].max())
            tp, se_tp, ci_low, ci_high = delta_method_turning_point(
                b1, b2,
                cov.loc[density_col, density_col],
                cov.loc[f"I({density_col} ** 2)", f"I({density_col} ** 2)"],
                cov.loc[density_col, f"I({density_col} ** 2)"],
            )
            dawson = dawson_u_test(fit, x_min, x_max, x_col=density_col)
            # Replace generic density term names in dawson output for clarity
            for d in dawson:
                d["density_col"] = density_col
            subtype_results.append(
                {
                    "subtype": ckey,
                    "density_col": density_col,
                    "n_nonzero": int((model_df[density_col] > 0).sum()),
                    "nobs": res["nobs"],
                    "aic": res["aic"],
                    "bic": res["bic"],
                    "pseudo_r2_mcfadden": res["pseudo_r2_mcfadden"],
                    "b1": float(b1),
                    "b1_pvalue": float(fit.pvalues[density_col]),
                    "b2": float(b2),
                    "b2_pvalue": float(fit.pvalues[f"I({density_col} ** 2)"]),
                    "negative_quadratic_significant": bool(b2 < 0 and fit.pvalues[f"I({density_col} ** 2)"] < 0.05),
                    "turning_point": float(tp),
                    "turning_point_se": se_tp,
                    "turning_point_ci_low": ci_low,
                    "turning_point_ci_high": ci_high,
                    "density_range_min": x_min,
                    "density_range_max": x_max,
                    "dawson_u_test": dawson,
                    "coef_table": res["coef_table"],
                }
            )
        except Exception as e:
            subtype_results.append(
                {
                    "subtype": ckey,
                    "density_col": density_col,
                    "error": str(e),
                }
            )

    output = {"subtype_models": subtype_results}
    save_json_csv(output, "03_subtype_analysis")

    # Human-readable subtype summary CSV
    summary_rows = []
    for m in subtype_results:
        if "error" in m:
            summary_rows.append({"subtype": m["subtype"], "error": m["error"]})
        else:
            summary_rows.append(
                {
                    "subtype": m["subtype"],
                    "n_nonzero": m["n_nonzero"],
                    "nobs": m["nobs"],
                    "b1": m["b1"],
                    "b1_pvalue": m["b1_pvalue"],
                    "b2": m["b2"],
                    "b2_pvalue": m["b2_pvalue"],
                    "negative_quadratic_significant": m["negative_quadratic_significant"],
                    "turning_point": m["turning_point"],
                    "turning_point_ci_low": m["turning_point_ci_low"],
                    "turning_point_ci_high": m["turning_point_ci_high"],
                    "aic": m["aic"],
                    "bic": m["bic"],
                    "pseudo_r2_mcfadden": m["pseudo_r2_mcfadden"],
                }
            )
    pd.DataFrame(summary_rows).to_csv(RESULTS_DIR / "03_subtype_analysis.csv", index=False)

    print("Step 3 complete.")
    for r in subtype_results:
        if "error" in r:
            print(f"  {r['subtype']}: ERROR {r['error']}")
        else:
            print(
                f"  {r['subtype']}: b2={r['b2']:.4f} p={r['b2_pvalue']:.4f} "
                f"TP={r['turning_point']:.2f} [{r['turning_point_ci_low']:.2f}, {r['turning_point_ci_high']:.2f}]"
            )


if __name__ == "__main__":
    main()
