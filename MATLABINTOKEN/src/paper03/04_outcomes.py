"""Compare task outcomes across LCA classes."""
import json
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.proportion import proportion_confint
from statsmodels.multivariate.manova import MANOVA

from utils import load_main_data, results_dir, save_json_csv, add_class_to_df


def eta_squared(groups: list):
    """Compute eta-squared from a list of 1-D arrays (ANOVA-style)."""
    all_vals = np.concatenate(groups)
    grand_mean = np.mean(all_vals)
    ss_total = np.sum((all_vals - grand_mean) ** 2)
    ss_between = sum(len(g) * (np.mean(g) - grand_mean) ** 2 for g in groups)
    if ss_total == 0:
        return 0.0
    return float(ss_between / ss_total)


def main():
    df = load_main_data()
    dfm = add_class_to_df(df)

    k = int(dfm["class"].nunique())
    process_vars = ["total_steps", "incorrect_ratio", "redundant_ratio"]

    # ---------- Completion rate by class ----------
    completion = []
    for c in sorted(dfm["class"].unique()):
        sub = dfm[dfm["class"] == c]
        n = len(sub)
        n_succ = int(sub["task_completed"].sum())
        rate = n_succ / n
        ci_low, ci_high = proportion_confint(n_succ, n, alpha=0.05, method="wilson")
        completion.append(
            {
                "class": int(c),
                "label": sub["class_label"].iloc[0],
                "n": n,
                "completed": n_succ,
                "completion_rate": float(rate),
                "ci95_low": float(ci_low),
                "ci95_high": float(ci_high),
            }
        )

    # Chi-square class x completion
    cont = pd.crosstab(dfm["class"], dfm["task_completed"])
    chi2, chi2_p, dof, expected = stats.chi2_contingency(cont)

    # ---------- Process outcomes by class ----------
    anova_records = []
    desc_records = []
    for var in process_vars:
        groups = [dfm[dfm["class"] == c][var].dropna().values for c in sorted(dfm["class"].unique())]
        # Descriptives
        for c, g in zip(sorted(dfm["class"].unique()), groups):
            desc_records.append(
                {
                    "class": int(c),
                    "label": dfm.loc[dfm["class"] == c, "class_label"].iloc[0],
                    "variable": var,
                    "n": len(g),
                    "mean": float(np.mean(g)),
                    "std": float(np.std(g, ddof=1)),
                    "median": float(np.median(g)),
                    "q25": float(np.percentile(g, 25)),
                    "q75": float(np.percentile(g, 75)),
                }
            )
        # ANOVA
        f_stat, p_anova = stats.f_oneway(*groups)
        # Kruskal-Wallis
        try:
            h_stat, p_kw = stats.kruskal(*groups)
        except ValueError:
            h_stat, p_kw = np.nan, np.nan
        eta2 = eta_squared(groups)
        anova_records.append(
            {
                "variable": var,
                "f_stat": float(f_stat),
                "anova_p": float(p_anova),
                "kw_h": float(h_stat),
                "kw_p": float(p_kw),
                "eta_squared": float(eta2),
            }
        )

    # ---------- MANOVA ----------
    manova_data = dfm[["class"] + process_vars].dropna().copy()
    manova_data["class_str"] = manova_data["class"].astype(str)
    manova = MANOVA.from_formula(
        "total_steps + incorrect_ratio + redundant_ratio ~ class_str",
        data=manova_data,
    )
    manova_res = manova.mv_test()
    # Extract Wilks' lambda for the overall class effect
    wilks = manova_res.results["class_str"]["stat"].loc["Wilks' lambda"].to_dict()

    output = {
        "completion_by_class": completion,
        "completion_chi2": {
            "chi2": float(chi2),
            "df": int(dof),
            "p": float(chi2_p),
        },
        "process_descriptives": desc_records,
        "process_anova": anova_records,
        "manova_wilks_lambda": {
            "value": float(wilks.get("Value", np.nan)),
            "num_df": float(wilks.get("Num DF", np.nan)),
            "den_df": float(wilks.get("Den DF", np.nan)),
            "f": float(wilks.get("F Value", np.nan)),
            "p": float(wilks.get("Pr > F", np.nan)),
        },
    }
    save_json_csv(output, "04_outcome_comparison")

    # Plain CSVs for the key tables
    pd.DataFrame(completion).to_csv(
        results_dir() / "04_outcome_comparison_completion.csv", index=False
    )
    pd.DataFrame(anova_records).to_csv(
        results_dir() / "04_outcome_comparison_anova.csv", index=False
    )

    print("Saved outcome comparison.")
    print(f"  Completion chi2({dof}) = {chi2:.2f}, p = {chi2_p:.4g}")
    for rec in anova_records:
        print(
            f"  {rec['variable']}: F={rec['f_stat']:.2f}, p={rec['anova_p']:.4g}, eta2={rec['eta_squared']:.3f}"
        )
    print(
        f"  MANOVA Wilks' lambda = {wilks.get('Value', np.nan):.3f}, p = {wilks.get('Pr > F', np.nan):.4g}"
    )


if __name__ == "__main__":
    main()
