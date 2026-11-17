"""Class distribution and representative instruction examples."""
import pandas as pd
import numpy as np

from utils import load_main_data, results_dir, save_json_csv, add_class_to_df


def main():
    df = load_main_data()
    labels = pd.read_csv(results_dir() / "class_labels.csv")
    dfm = add_class_to_df(df[["task_id", "instruction", "task_completed", "explicitness_score"]])
    label_map = dict(zip(labels["class"], labels["label"]))
    dfm["label"] = dfm["class"].map(label_map)

    counts = dfm["class"].value_counts().sort_index()
    total = counts.sum()

    distribution = []
    examples = []
    for c in sorted(dfm["class"].unique()):
        sub = dfm[dfm["class"] == c].copy()
        label = labels.loc[labels["class"] == c, "label"].iloc[0]
        # pick top-3 by posterior probability, prefer completed tasks for readability
        sub_sorted = sub.sort_values(
            ["posterior_max", "task_completed"], ascending=[False, False]
        )
        chosen = sub_sorted.head(3)
        distribution.append(
            {
                "class": int(c),
                "label": label,
                "n": int(counts[c]),
                "proportion": float(counts[c] / total),
                "pct": float(counts[c] / total * 100),
            }
        )
        for _, row in chosen.iterrows():
            examples.append(
                {
                    "class": int(c),
                    "label": label,
                    "task_id": row["task_id"],
                    "posterior_max": float(row["posterior_max"]),
                    "task_completed": bool(row["task_completed"]),
                    "explicitness_score": int(row["explicitness_score"]),
                    "instruction": str(row["instruction"])[:300],
                }
            )

    output = {
        "total_n": int(total),
        "distribution": distribution,
        "representative_examples": examples,
    }
    save_json_csv(output, "03_class_distribution")

    # Simple CSV of distribution
    pd.DataFrame(distribution).to_csv(results_dir() / "03_class_distribution.csv", index=False)

    print("Saved class distribution.")
    for d in distribution:
        print(f"  Class {d['class']} ({d['label']}): n={d['n']} ({d['pct']:.1f}%)")


if __name__ == "__main__":
    main()
