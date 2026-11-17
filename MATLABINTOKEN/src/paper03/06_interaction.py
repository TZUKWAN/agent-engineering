"""Class x task difficulty interaction on completion."""
import json
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.formula.api as smf
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from utils import load_main_data, results_dir, save_json_csv, add_class_to_df


def main():
    df = load_main_data()
    dfm = add_class_to_df(df)
    dfm["class_str"] = dfm["class"].astype(str)
    dfm["completed_int"] = dfm["task_completed"].astype(int)

    formula = "completed_int ~ C(class_str) * task_difficulty + explicitness_score"
    model = smf.logit(formula, data=dfm).fit(disp=0)

    coef_table = (
        model.summary2().tables[1]
        .reset_index()
        .rename(columns={"index": "term"})
        .to_dict(orient="records")
    )
    for rec in coef_table:
        for key in rec:
            if isinstance(rec[key], float) and np.isnan(rec[key]):
                rec[key] = None

    # Interaction terms Wald test (all class_str x difficulty coefficients)
    interaction_terms = [r["term"] for r in coef_table if "task_difficulty" in r["term"]]
    interaction_pvalues = {
        term: float(next(r["P>|z|"] for r in coef_table if r["term"] == term))
        for term in interaction_terms
    }

    # ---------- Predicted probabilities by difficulty (continuous) ----------
    difficulty_grid = np.linspace(dfm["task_difficulty"].min(), dfm["task_difficulty"].max(), 50)
    mean_explicitness = dfm["explicitness_score"].mean()
    pred_records = []
    for c in sorted(dfm["class"].unique()):
        grid_df = pd.DataFrame(
            {
                "class_str": str(c),
                "task_difficulty": difficulty_grid,
                "explicitness_score": mean_explicitness,
            }
        )
        probs = model.predict(grid_df)
        for d, p in zip(difficulty_grid, probs):
            pred_records.append(
                {"class": int(c), "label": dfm.loc[dfm["class"] == c, "class_label"].iloc[0],
                 "task_difficulty": float(d), "predicted_completion": float(p)}
            )

    pred_df = pd.DataFrame(pred_records)

    # ---------- Binned difficulty table (low/medium/high terciles) ----------
    dfm["difficulty_bin"] = pd.qcut(
        dfm["task_difficulty"], q=3, labels=["low", "medium", "high"]
    )
    bin_records = []
    for c in sorted(dfm["class"].unique()):
        for b in ["low", "medium", "high"]:
            sub = dfm[(dfm["class"] == c) & (dfm["difficulty_bin"] == b)]
            if len(sub) == 0:
                continue
            pred = model.predict(sub[["class_str", "task_difficulty", "explicitness_score"]])
            bin_records.append(
                {
                    "class": int(c),
                    "label": sub["class_label"].iloc[0],
                    "difficulty_bin": b,
                    "n": int(len(sub)),
                    "observed_completion_rate": float(sub["task_completed"].mean()),
                    "mean_predicted_completion": float(pred.mean()),
                }
            )

    # Joint interaction LRT
    formula_no_int = "completed_int ~ C(class_str) + task_difficulty + explicitness_score"
    model_no_int = smf.logit(formula_no_int, data=dfm).fit(disp=0)
    lr_stat = 2 * (model.llf - model_no_int.llf)
    lr_df = int(round(model.df_model - model_no_int.df_model))
    lr_p = float(stats.chi2.sf(lr_stat, lr_df))

    output = {
        "model": "single-level logistic regression with interaction",
        "formula": formula,
        "n": int(model.nobs),
        "model_fit": {
            "loglik": float(model.llf),
            "aic": float(model.aic),
            "bic": float(model.bic),
            "pseudo_r2": float(model.prsquared),
        },
        "interaction_joint_lrt": {
            "statistic": lr_stat,
            "df": lr_df,
            "p": lr_p,
        },
        "interaction_wald_pvalues": interaction_pvalues,
        "coefficients": coef_table,
        "predicted_by_difficulty": pred_records,
        "predicted_by_difficulty_bin": bin_records,
    }
    save_json_csv(output, "06_interaction_analysis")

    # CSVs
    pd.DataFrame(pred_records).to_csv(
        results_dir() / "06_interaction_analysis_predicted.csv", index=False
    )
    pd.DataFrame(bin_records).to_csv(
        results_dir() / "06_interaction_analysis_binned.csv", index=False
    )
    pd.DataFrame(coef_table).to_csv(
        results_dir() / "06_interaction_analysis_coefficients.csv", index=False
    )

    # Plot
    fig, ax = plt.subplots(figsize=(8, 5))
    for c in sorted(dfm["class"].unique()):
        sub = pred_df[pred_df["class"] == c]
        ax.plot(
            sub["task_difficulty"],
            sub["predicted_completion"],
            label=f"Class {c}: {sub['label'].iloc[0]}",
        )
    ax.set_xlabel("Task difficulty")
    ax.set_ylabel("Predicted completion probability")
    ax.set_title("Class × task difficulty interaction on predicted completion")
    ax.legend(title="Class", loc="best", fontsize="small")
    ax.set_ylim(0, 1)
    fig.tight_layout()
    plot_path = results_dir() / "06_interaction_plot.png"
    fig.savefig(plot_path, dpi=150)
    print(f"Saved interaction analysis and plot to {plot_path}")
    print(f"  Joint interaction LRT: chi2({lr_df}) = {lr_stat:.2f}, p = {lr_p:.4g}")


if __name__ == "__main__":
    main()
