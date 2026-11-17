"""Step 1: Classify constraints and describe their distribution."""
import json
from collections import defaultdict

import numpy as np
import pandas as pd

from utils import (
    add_constraint_features,
    CONSTRAINT_KEYWORDS,
    DATA_PATH,
    RESULTS_DIR,
    save_json_csv,
)


def main():
    df = pd.read_parquet(DATA_PATH)
    df = add_constraint_features(df)

    # Overall distribution
    type_counts = df["constraint_type"].value_counts().sort_index()
    type_props = (df["constraint_type"].value_counts(normalize=True) * 100).sort_index()

    distribution = {
        "n_total": int(len(df)),
        "n_with_constraints": int((df["constraint_type"] != "C0_none").sum()),
        "pct_with_constraints": float((df["constraint_type"] != "C0_none").mean() * 100),
        "by_type": {
            typ: {
                "n": int(type_counts.get(typ, 0)),
                "pct_of_total": float(type_props.get(typ, 0.0)),
            }
            for typ in sorted(df["constraint_type"].unique())
        },
    }

    # Descriptive stats for density and richness
    desc_density = df["constraint_density"].describe(percentiles=[0.05, 0.25, 0.5, 0.75, 0.95]).to_dict()
    desc_richness = df["constraint_richness"].describe(percentiles=[0.05, 0.25, 0.5, 0.75, 0.95]).to_dict()
    desc_abs = df["constraint_abs_count"].describe(percentiles=[0.05, 0.25, 0.5, 0.75, 0.95]).to_dict()

    # Examples per type (first 3 with non-empty instruction)
    examples = {}
    for typ in ["C1_prohibitive", "C2_preservative", "C3_obligative", "C4_restrictive", "C5_mixed"]:
        subset = df[df["constraint_type"] == typ]
        n = len(subset)
        sampled = subset.head(3) if n > 0 else subset
        examples[typ] = {
            "n": int(n),
            "sample_instructions": sampled["instruction"].tolist(),
            "sample_task_ids": sampled["task_id"].tolist() if "task_id" in subset.columns else [],
        }

    output = {
        "distribution": distribution,
        "density_descriptives": {k: float(v) for k, v in desc_density.items()},
        "richness_descriptives": {k: float(v) for k, v in desc_richness.items()},
        "abs_count_descriptives": {k: float(v) for k, v in desc_abs.items()},
        "examples_by_type": examples,
    }

    save_json_csv(output, "01_constraint_distribution")

    # Human-readable distribution CSV
    dist_rows = []
    for typ, info in distribution["by_type"].items():
        dist_rows.append({"constraint_type": typ, "n": info["n"], "pct_of_total": info["pct_of_total"]})
    pd.DataFrame(dist_rows).to_csv(RESULTS_DIR / "01_constraint_distribution.csv", index=False)

    # Examples CSV
    rows = []
    for typ, info in examples.items():
        for i, instr in enumerate(info["sample_instructions"]):
            rows.append({"constraint_type": typ, "rank": i + 1, "instruction": instr})
    pd.DataFrame(rows).to_csv(RESULTS_DIR / "01_constraint_distribution_examples.csv", index=False)

    print("Step 1 complete. Constraint types:")
    print(type_counts)


if __name__ == "__main__":
    main()
