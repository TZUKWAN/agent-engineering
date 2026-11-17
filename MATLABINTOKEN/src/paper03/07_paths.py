"""Fine-grained execution-path differences by LCA class."""
import json
import numpy as np
import pandas as pd
from scipy import stats

from utils import load_main_data, load_steps, results_dir, save_json_csv, add_class_to_df


def compute_path_metrics(steps: pd.DataFrame):
    """Return path metrics indexed by task_id."""
    # Ensure numeric/bool where needed
    steps = steps.sort_values(["task_id", "step_index"]).copy()
    steps["correct_bool"] = steps["last_step_correct"].map(
        lambda x: True if x is True else (False if x is False else np.nan)
    )
    steps["redundant_bool"] = steps["last_step_redundant"].map(
        lambda x: True if x is True else (False if x is False else np.nan)
    )

    rows = []
    for tid, grp in steps.groupby("task_id"):
        n_steps = len(grp)
        correct = grp["correct_bool"].values
        redundant = grp["redundant_bool"].values
        indices = grp["step_index"].values

        # First error position (relative)
        false_mask = correct == False
        first_error_pos = np.nan
        if false_mask.any():
            first_error_pos = int(indices[false_mask].min()) / n_steps

        # Max consecutive incorrect steps (False only; None breaks the run)
        max_consec = 0
        cur = 0
        for val in correct:
            if val is False:
                cur += 1
                max_consec = max(max_consec, cur)
            else:
                cur = 0

        # Transition frequency between correct and incorrect (skip NaN)
        raw_transitions = 0
        valid_pairs = 0
        for i in range(n_steps - 1):
            a, b = correct[i], correct[i + 1]
            if pd.isna(a) or pd.isna(b):
                continue
            valid_pairs += 1
            if a != b:
                raw_transitions += 1
        transition_rate = raw_transitions / valid_pairs if valid_pairs > 0 else np.nan

        # Final step redundancy
        final_redundant = redundant[-1] if len(redundant) > 0 else np.nan
        any_last3_redundant = np.nan
        if len(redundant) >= 3:
            any_last3_redundant = bool(np.any(redundant[-3:] == True))
        elif len(redundant) > 0:
            any_last3_redundant = bool(np.any(redundant == True))

        rows.append(
            {
                "task_id": tid,
                "n_steps": n_steps,
                "first_error_position": first_error_pos,
                "max_consecutive_incorrect": max_consec,
                "transition_count": raw_transitions,
                "transition_rate": transition_rate,
                "final_step_redundant": final_redundant,
                "any_last3_redundant": any_last3_redundant,
            }
        )
    return pd.DataFrame(rows)


def anova_kw(groups: list):
    f, p_anova = stats.f_oneway(*groups)
    try:
        h, p_kw = stats.kruskal(*groups)
    except ValueError:
        h, p_kw = np.nan, np.nan
    return float(f), float(p_anova), float(h), float(p_kw)


def main():
    df = load_main_data()
    dfm = add_class_to_df(df)
    steps = load_steps()
    path_metrics = compute_path_metrics(steps)

    # Merge path metrics back to attempt-level data by task_id.
    # Duplicate task_ids receive the same path metrics (data limitation noted in report).
    dfm = dfm.merge(path_metrics, on="task_id", how="left")

    continuous_vars = [
        "first_error_position",
        "max_consecutive_incorrect",
        "transition_count",
        "transition_rate",
    ]
    binary_vars = ["final_step_redundant", "any_last3_redundant"]

    desc_records = []
    cont_records = []
    for var in continuous_vars:
        groups = [
            dfm[dfm["class"] == c][var].dropna().values
            for c in sorted(dfm["class"].unique())
        ]
        for c, g in zip(sorted(dfm["class"].unique()), groups):
            desc_records.append(
                {
                    "class": int(c),
                    "label": dfm.loc[dfm["class"] == c, "class_label"].iloc[0],
                    "variable": var,
                    "n": len(g),
                    "mean": float(np.mean(g)) if len(g) else None,
                    "std": float(np.std(g, ddof=1)) if len(g) > 1 else None,
                    "median": float(np.median(g)) if len(g) else None,
                }
            )
        f, p_a, h, p_k = anova_kw(groups)
        cont_records.append(
            {
                "variable": var,
                "f_stat": f,
                "anova_p": p_a,
                "kw_h": h,
                "kw_p": p_k,
            }
        )

    binary_records = []
    for var in binary_vars:
        for c in sorted(dfm["class"].unique()):
            sub = dfm[dfm["class"] == c][var].dropna()
            n = len(sub)
            n_yes = int((sub == True).sum())
            rate = n_yes / n if n > 0 else np.nan
            binary_records.append(
                {
                    "class": int(c),
                    "label": dfm.loc[dfm["class"] == c, "class_label"].iloc[0],
                    "variable": var,
                    "n": n,
                    "n_yes": n_yes,
                    "rate": float(rate) if not np.isnan(rate) else None,
                }
            )
        # Chi-square for binary var vs class
        cont = pd.crosstab(dfm["class"], dfm[var].dropna())
        if cont.shape[1] == 2:
            chi2, p, dof, expected = stats.chi2_contingency(cont)
            binary_records.append(
                {
                    "class": "all",
                    "label": "",
                    "variable": var,
                    "chi2": float(chi2),
                    "df": int(dof),
                    "p": float(p),
                }
            )

    output = {
        "continuous_path_metrics": cont_records,
        "continuous_descriptives": desc_records,
        "binary_path_metrics": binary_records,
        "definitions": {
            "first_error_position": "step_index of first last_step_correct==False divided by total steps; NaN if no incorrect step",
            "max_consecutive_incorrect": "maximum run of steps with last_step_correct==False (None breaks the run)",
            "transition_count": "number of adjacent correct/incorrect changes within a task",
            "transition_rate": "transition_count divided by number of valid adjacent pairs",
            "final_step_redundant": "whether the last recorded step was redundant",
            "any_last3_redundant": "whether any of the last three steps were redundant",
        },
    }
    save_json_csv(output, "07_path_analysis")
    pd.DataFrame(cont_records).to_csv(
        results_dir() / "07_path_analysis_continuous.csv", index=False
    )
    pd.DataFrame(binary_records).to_csv(
        results_dir() / "07_path_analysis_binary.csv", index=False
    )

    print("Saved path analysis.")
    for rec in cont_records:
        print(
            f"  {rec['variable']}: F={rec['f_stat']:.2f}, p={rec['anova_p']:.4g}; KW p={rec['kw_p']:.4g}"
        )


if __name__ == "__main__":
    main()
