"""Compute and label LCA profiles for the selected model."""
import json
import numpy as np
import pandas as pd

from utils import FEATURE_COLS, load_main_data, results_dir, save_json_csv


def label_class(theta_row: np.ndarray, feature_cols: list) -> dict:
    """Assign a pragmatic label based on the conditional response profile."""
    vals = dict(zip(feature_cols, theta_row))
    top = sorted(vals.items(), key=lambda x: x[1], reverse=True)
    top_feats = [f for f, v in top]
    high = {f: v for f, v in vals.items() if v >= 0.7}

    if len(high) == 0 or max(vals.values()) < 0.35:
        label = "Minimal"
        explanation = (
            "Very low probability on all pragmatic features; instructions are short and underspecified."
        )
    elif (
        vals["has_operation_object"] >= 0.8
        and vals["has_file_reference"] >= 0.6
        and vals["has_target_action"] >= 0.7
    ):
        label = "Object/File-Rich"
        explanation = (
            "Strongly specifies the operation object and the file/reference to be manipulated, "
            "often combined with multiple subtasks."
        )
    elif (
        vals["has_constraint_words"] >= 0.85
        and vals["has_completion_criteria"] >= 0.7
        and vals["has_target_action"] >= 0.85
    ):
        label = "Action-Constrained"
        explanation = (
            "Clear action target plus explicit constraints and completion criteria; highly directive."
        )
    elif (
        vals["has_constraint_words"] >= 0.85
        and vals["has_completion_criteria"] >= 0.7
        and vals["has_target_action"] < 0.6
    ):
        label = "Constraint-Verification"
        explanation = (
            "Focuses on restrictions and verification standards rather than detailed actions."
        )
    elif vals["has_target_action"] >= 0.75 and vals["has_multiple_subtasks"] >= 0.75:
        label = "Action-Oriented"
        explanation = (
            "Specifies what to do and frequently contains several subtasks, but with fewer files, "
            "constraints, or completion criteria."
        )
    else:
        label = "Mixed"
        explanation = (
            "Intermediate pattern combining several pragmatic features without a single dominant strategy."
        )

    return {
        "label": label,
        "explanation": explanation,
        "top_features": top_feats[:4],
        "high_features": list(high.keys()),
    }


def main():
    df = load_main_data()
    X = df[FEATURE_COLS].astype(int).values

    with open(results_dir() / "lca_model.json", "r", encoding="utf-8") as f:
        model = json.load(f)

    k = model["k"]
    theta = np.array(model["theta"])
    pi = np.array(model["pi"])

    # Model-based conditional response probabilities
    profile_records = []
    class_labels = []
    for c in range(k):
        info = label_class(theta[c], FEATURE_COLS)
        class_labels.append(info["label"])
        rec = {
            "class": c,
            "label": info["label"],
            "class_prevalence": float(pi[c]),
            "explanation": info["explanation"],
            "top_features": info["top_features"],
            "high_features": info["high_features"],
        }
        for feat, val in zip(FEATURE_COLS, theta[c]):
            rec[feat] = float(val)
        profile_records.append(rec)

    # Observed proportions by assigned class (positional alignment because task_id is not unique)
    from utils import add_class_to_df
    dfm = add_class_to_df(df[["task_id"] + FEATURE_COLS])
    observed = (
        dfm.groupby("class")[FEATURE_COLS]
        .mean()
        .round(4)
        .reset_index()
        .to_dict(orient="records")
    )

    output = {
        "k": k,
        "feature_cols": FEATURE_COLS,
        "model_profiles": profile_records,
        "observed_profiles": observed,
        "class_labels": {str(c): lbl for c, lbl in enumerate(class_labels)},
    }
    save_json_csv(output, "02_lca_profiles")

    # Also save a handy label lookup for downstream scripts
    label_df = pd.DataFrame(
        {"class": range(k), "label": class_labels, "prevalence": pi}
    )
    label_df.to_csv(results_dir() / "class_labels.csv", index=False)

    print(f"Saved profiles for k={k}.")
    for rec in profile_records:
        print(f"  Class {rec['class']}: {rec['label']} (prev={rec['class_prevalence']:.3f})")


if __name__ == "__main__":
    main()
