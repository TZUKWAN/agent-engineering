"""Control for explicitness_score when estimating class effects on completion."""
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm
import statsmodels.formula.api as smf

from utils import load_main_data, results_dir, save_json_csv, add_class_to_df


def main():
    df = load_main_data()
    dfm = add_class_to_df(df)

    # ---------- Within each explicitness_score level: class x completion ----------
    level_results = []
    for score in sorted(dfm["explicitness_score"].unique()):
        sub = dfm[dfm["explicitness_score"] == score]
        if sub["class"].nunique() < 2:
            continue
        cont = pd.crosstab(sub["class"], sub["task_completed"])
        if cont.size == 0 or cont.shape[1] < 2:
            continue
        # Only run chi-square if expected frequencies allow
        if (stats.chi2_contingency(cont)[3] >= 5).all():
            chi2, p, dof, expected = stats.chi2_contingency(cont)
            test = "chi2"
        else:
            chi2, p, dof = np.nan, np.nan, np.nan
            test = "skipped_small_expected"
        level_results.append(
            {
                "explicitness_score": int(score),
                "n": int(len(sub)),
                "n_classes": int(sub["class"].nunique()),
                "test": test,
                "chi2": float(chi2) if not np.isnan(chi2) else None,
                "df": int(dof) if not np.isnan(dof) else None,
                "p": float(p) if not np.isnan(p) else None,
            }
        )

    # ---------- Logistic regression controlling for explicitness_score ----------
    dfm["class_str"] = dfm["class"].astype(str)
    dfm["completed_int"] = dfm["task_completed"].astype(int)
    formula_full = "completed_int ~ C(class_str) + explicitness_score"
    formula_null = "completed_int ~ explicitness_score"
    model_full = smf.logit(formula_full, data=dfm).fit(disp=0)
    model_null = smf.logit(formula_null, data=dfm).fit(disp=0)

    lr_stat = 2 * (model_full.llf - model_null.llf)
    lr_df = int(round(model_full.df_model - model_null.df_model))
    lr_p = float(stats.chi2.sf(lr_stat, lr_df))

    coef_table = (
        model_full.summary2().tables[1]
        .reset_index()
        .rename(columns={"index": "term"})
        .to_dict(orient="records")
    )
    # Clean NaNs
    for rec in coef_table:
        for key in rec:
            if isinstance(rec[key], float) and np.isnan(rec[key]):
                rec[key] = None

    output = {
        "model": "single-level logistic regression (observations treated as independent)",
        "formula": formula_full,
        "n": int(model_full.nobs),
        "class_lrt": {
            "statistic": float(lr_stat),
            "df": int(lr_df),
            "p": float(lr_p),
        },
        "model_fit": {
            "loglik": float(model_full.llf),
            "aic": float(model_full.aic),
            "bic": float(model_full.bic),
            "pseudo_r2": float(model_full.prsquared),
        },
        "coefficients": coef_table,
        "by_explicitness_score": level_results,
    }
    save_json_csv(output, "05_controlled_analysis")

    # CSV of level results
    pd.DataFrame(level_results).to_csv(
        results_dir() / "05_controlled_analysis_by_score.csv", index=False
    )
    pd.DataFrame(coef_table).to_csv(
        results_dir() / "05_controlled_analysis_coefficients.csv", index=False
    )

    print("Saved controlled analysis.")
    print(f"  Class LRT: chi2({int(lr_df)}) = {lr_stat:.2f}, p = {lr_p:.4g}")
    print(f"  Coefficients for class dummies (ref = class 0) are included in JSON/CSV.")


if __name__ == "__main__":
    main()
