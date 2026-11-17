"""Step 4: Moderation by task difficulty and other complexity proxies."""
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
    CONSTRAINT_KEYWORDS,
)


def _fit_with_fallback(formula: str, data: pd.DataFrame):
    model = smf.logit(formula=formula, data=data)
    try:
        fit = model.fit(disp=0, maxiter=200)
    except Exception:
        fit = model.fit(disp=0, method="bfgs", maxiter=500)
    return fit


def fit_moderation(data: pd.DataFrame) -> dict:
    formula = (
        "task_completed_num ~ constraint_density * task_difficulty + "
        "I(constraint_density ** 2) * task_difficulty + word_count + os"
    )
    res = fit_logit(formula, data)
    fit = _fit_with_fallback(formula, data)
    return {"summary": res, "fit": fit}


def fit_split(data: pd.DataFrame, split_var: str, median: float) -> dict:
    low = data[data[split_var] <= median]
    high = data[data[split_var] > median]
    formula = (
        "task_completed_num ~ constraint_density + I(constraint_density ** 2) + task_difficulty + word_count + os"
    )
    results = {}
    for label, subset in [("low", low), ("high", high)]:
        if len(subset) < 50:
            results[label] = {"error": "too few observations"}
            continue
        try:
            res = fit_logit(formula, subset)
            fit = _fit_with_fallback(formula, subset)
            params = fit.params
            cov = fit.cov_params()
            b1 = params["constraint_density"]
            b2 = params["I(constraint_density ** 2)"]
            x_min = float(subset["constraint_density"].min())
            x_max = float(subset["constraint_density"].max())
            tp, se_tp, ci_low, ci_high = delta_method_turning_point(
                b1, b2,
                cov.loc["constraint_density", "constraint_density"],
                cov.loc["I(constraint_density ** 2)", "I(constraint_density ** 2)"],
                cov.loc["constraint_density", "I(constraint_density ** 2)"],
            )
            dawson = dawson_u_test(fit, x_min, x_max)
            results[label] = {
                "nobs": res["nobs"],
                "aic": res["aic"],
                "bic": res["bic"],
                "pseudo_r2_mcfadden": res["pseudo_r2_mcfadden"],
                "b1": float(b1),
                "b1_pvalue": float(fit.pvalues["constraint_density"]),
                "b2": float(b2),
                "b2_pvalue": float(fit.pvalues["I(constraint_density ** 2)"]),
                "negative_quadratic_significant": bool(b2 < 0 and fit.pvalues["I(constraint_density ** 2)"] < 0.05),
                "turning_point": float(tp),
                "turning_point_se": se_tp,
                "turning_point_ci_low": ci_low,
                "turning_point_ci_high": ci_high,
                "dawson_u_test": dawson,
                "coef_table": res["coef_table"],
            }
        except Exception as e:
            results[label] = {"error": str(e)}
    return results


def main():
    df = pd.read_parquet(DATA_PATH)
    df = add_constraint_features(df)
    model_df = prepare_model_data(df)

    # Interaction model
    mod = fit_moderation(model_df)

    # Split samples
    med_diff = model_df["task_difficulty"].median()
    med_words = model_df["word_count"].median()
    splits = {
        "task_difficulty": fit_split(model_df, "task_difficulty", med_diff),
        "word_count": fit_split(model_df, "word_count", med_words),
    }
    # 多子任务探索性分割：论文正文引用了该探索性结论，必须有管道产出支撑（R1 审计补齐）
    if "has_multiple_subtasks" in model_df.columns:
        splits["has_multiple_subtasks"] = fit_split(model_df, "has_multiple_subtasks", 0.0)
    if "has_operation_object" in model_df.columns:
        splits["has_operation_object"] = {
            str(v): fit_split(model_df, "has_operation_object", 0.0) for v in []
        }
        # Simpler direct split on binary variable
        binary_splits = {}
        for val in [0, 1]:
            subset = model_df[model_df["has_operation_object"] == val]
            if len(subset) < 50:
                binary_splits[str(val)] = {"error": "too few observations"}
                continue
            formula = (
                "task_completed_num ~ constraint_density + I(constraint_density ** 2) + "
                "task_difficulty + word_count + os"
            )
            try:
                res = fit_logit(formula, subset)
                fit = _fit_with_fallback(formula, subset)
                params = fit.params
                cov = fit.cov_params()
                b1 = params["constraint_density"]
                b2 = params["I(constraint_density ** 2)"]
                x_min = float(subset["constraint_density"].min())
                x_max = float(subset["constraint_density"].max())
                tp, se_tp, ci_low, ci_high = delta_method_turning_point(
                    b1, b2,
                    cov.loc["constraint_density", "constraint_density"],
                    cov.loc["I(constraint_density ** 2)", "I(constraint_density ** 2)"],
                    cov.loc["constraint_density", "I(constraint_density ** 2)"],
                )
                binary_splits[str(val)] = {
                    "nobs": res["nobs"],
                    "aic": res["aic"],
                    "bic": res["bic"],
                    "pseudo_r2_mcfadden": res["pseudo_r2_mcfadden"],
                    "b2": float(b2),
                    "b2_pvalue": float(fit.pvalues["I(constraint_density ** 2)"]),
                    "turning_point": float(tp),
                    "turning_point_ci_low": ci_low,
                    "turning_point_ci_high": ci_high,
                    "dawson_u_test": dawson_u_test(fit, x_min, x_max),
                    "coef_table": res["coef_table"],
                }
            except Exception as e:
                binary_splits[str(val)] = {"error": str(e)}
        splits["has_operation_object"] = binary_splits

    output = {
        "interaction_model": mod["summary"],
        "median_split_thresholds": {
            "task_difficulty": float(med_diff),
            "word_count": float(med_words),
        },
        "split_sample_models": splits,
    }

    save_json_csv(output, "04_moderation_analysis")

    # Human-readable moderation summary CSV
    rows = []
    # Interaction model key terms
    for r in output["interaction_model"].get("coef_table", []):
        if "constraint_density" in r["term"] or "task_difficulty" in r["term"]:
            rows.append(
                {
                    "model": "interaction",
                    "term": r["term"],
                    "coef": r["coef"],
                    "or": r["or"],
                    "pvalue": r["pvalue"],
                }
            )
    # Split sample summaries
    for split_name, split_res in output["split_sample_models"].items():
        for group, gres in split_res.items():
            if "error" in gres:
                rows.append(
                    {
                        "model": f"split_{split_name}",
                        "group": group,
                        "error": gres["error"],
                    }
                )
            else:
                rows.append(
                    {
                        "model": f"split_{split_name}",
                        "group": group,
                        "nobs": gres["nobs"],
                        "b2": gres["b2"],
                        "b2_pvalue": gres["b2_pvalue"],
                        "turning_point": gres["turning_point"],
                        "turning_point_ci_low": gres["turning_point_ci_low"],
                        "turning_point_ci_high": gres["turning_point_ci_high"],
                        "aic": gres["aic"],
                    }
                )
    pd.DataFrame(rows).to_csv(RESULTS_DIR / "04_moderation_analysis.csv", index=False)

    print("Step 4 complete.")
    print(f"Interaction model AIC={mod['summary']['aic']:.2f} BIC={mod['summary']['bic']:.2f}")


if __name__ == "__main__":
    main()
