"""Shared utilities for Paper 02: Constraint Density Non-linear Effect."""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

RESULTS_DIR = Path("results/papers/paper02")
DATA_PATH = Path("data/processed/analysis_data.parquet")

# Constraint keyword taxonomy -------------------------------------------------
CONSTRAINT_KEYWORDS = {
    "C1_prohibitive": {
        "phrases": ["do not", "should not", "must not"],
        "words": ["don't", "never", "avoid", "without", "cannot"],
    },
    "C2_preservative": {
        "phrases": [],
        "words": ["keep", "maintain", "stay", "preserve", "leave"],
    },
    "C3_obligative": {
        "phrases": ["need to", "have to"],
        "words": ["must", "should", "required"],
    },
    "C4_restrictive": {
        "phrases": [],
        "words": ["only", "just", "merely", "exclusively"],
    },
}


def _count_phrases(text: str, phrases: list[str]) -> tuple[int, str]:
    """Count non-overlapping phrase occurrences and mask them."""
    count = 0
    # Sort longer phrases first to avoid partial masking issues.
    for phrase in sorted(phrases, key=len, reverse=True):
        pattern = re.compile(r"\b" + re.escape(phrase) + r"\b", re.IGNORECASE)
        matches = list(pattern.finditer(text))
        count += len(matches)
        if matches:
            # Replace matched spans with spaces of equal length to preserve length.
            parts = []
            prev = 0
            for m in matches:
                parts.append(text[prev:m.start()])
                parts.append(" " * (m.end() - m.start()))
                prev = m.end()
            parts.append(text[prev:])
            text = "".join(parts)
    return count, text


def _count_words(text: str, words: list[str]) -> int:
    count = 0
    for word in words:
        pattern = re.compile(r"\b" + re.escape(word) + r"\b", re.IGNORECASE)
        count += len(pattern.findall(text))
    return count


def classify_constraints(instruction: str) -> dict:
    """Classify a single instruction into C1-C4 counts.

    Returns a dict with keys C1..C4 absolute counts.
    """
    text = instruction
    counts = {}
    for key, spec in CONSTRAINT_KEYWORDS.items():
        phrase_count, text_after_phrases = _count_phrases(text, spec["phrases"])
        word_count = _count_words(text_after_phrases, spec["words"])
        counts[key] = phrase_count + word_count
    return counts


def add_constraint_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add constraint type/density/richness features to the dataframe."""
    df = df.copy()
    df["task_completed_num"] = pd.to_numeric(df["task_completed"], errors="coerce")

    # Apply classification
    constraint_counts = df["instruction"].apply(classify_constraints).apply(pd.Series)
    for col in CONSTRAINT_KEYWORDS.keys():
        df[col] = constraint_counts[col].fillna(0).astype(int)

    # Absolute count
    df["constraint_abs_count"] = df[list(CONSTRAINT_KEYWORDS.keys())].sum(axis=1)

    # Richness: distinct C1-C4 categories present
    c_cols = list(CONSTRAINT_KEYWORDS.keys())
    df["constraint_richness"] = (df[c_cols] > 0).sum(axis=1)

    # Constraint density (%)
    df["constraint_density"] = df["constraint_abs_count"] / df["word_count"] * 100.0

    # Subtype densities
    for col in c_cols:
        short = col.replace("C1_", "density_").replace("C2_", "density_").replace(
            "C3_", "density_"
        ).replace("C4_", "density_")
        df[short] = df[col] / df["word_count"] * 100.0

    # Constraint type label
    def label_type(row):
        present = [c for c in c_cols if row[c] > 0]
        if len(present) == 0:
            return "C0_none"
        if len(present) >= 2:
            return "C5_mixed"
        return present[0]

    df["constraint_type"] = df.apply(label_type, axis=1)
    return df


def prepare_model_data(df: pd.DataFrame, formula_extra: str = "") -> pd.DataFrame:
    """Return model-ready subset with complete cases for base covariates."""
    cols = [
        "task_completed_num",
        "constraint_density",
        "task_difficulty",
        "word_count",
        "os",
        "total_steps",
        "redundant_ratio",
        "constraint_abs_count",
        "constraint_richness",
    ] + [f"density_{k.split('_')[1]}" for k in CONSTRAINT_KEYWORDS.keys()]
    if "has_operation_object" in df.columns:
        cols.append("has_operation_object")
    if "has_multiple_subtasks" in df.columns:
        cols.append("has_multiple_subtasks")
    if formula_extra:
        # Extract variable names roughly from formula string for completeness.
        extra_cols = [c for c in df.columns if c in formula_extra]
        cols += extra_cols
    cols = list(set(cols))
    model_df = df[cols].dropna()
    return model_df


def fit_logit(formula: str, data: pd.DataFrame, **fit_kwargs) -> dict:
    """Fit a statsmodels Logit and return a compact summary dict."""
    model = smf.logit(formula=formula, data=data)
    try:
        result = model.fit(disp=0, maxiter=200, **fit_kwargs)
    except Exception:
        # Fallback to BFGS when default Newton fails.
        result = model.fit(disp=0, method="bfgs", maxiter=500, **fit_kwargs)
    return summarize_logit(result)


def summarize_logit(result) -> dict:
    """Create a serializable summary from a statsmodels Logit result."""
    params = result.params
    bse = result.bse
    conf = result.conf_int(alpha=0.05)
    pvalues = result.pvalues

    rows = []
    for term in params.index:
        coef = float(params[term])
        se = float(bse[term])
        or_ = float(np.exp(np.clip(coef, -700, 700)))
        ci_low, ci_high = float(np.exp(np.clip(conf.loc[term, 0], -700, 700))), float(
            np.exp(np.clip(conf.loc[term, 1], -700, 700))
        )
        p = float(pvalues[term])
        rows.append(
            {
                "term": term,
                "coef": coef,
                "se": se,
                "or": or_,
                "or_ci_low": ci_low,
                "or_ci_high": ci_high,
                "z": coef / se if se > 0 else None,
                "pvalue": p,
                "significant_05": p < 0.05,
            }
        )

    # McFadden pseudo R^2
    pseudo_r2 = float(1 - result.llf / result.llnull)

    return {
        "nobs": int(result.nobs),
        "llf": float(result.llf),
        "llnull": float(result.llnull),
        "pseudo_r2_mcfadden": pseudo_r2,
        "aic": float(result.aic),
        "bic": float(result.bic),
        "converged": bool(result.mle_retvals.get("converged", True)),
        "iterations": int(result.mle_retvals.get("iterations", -1)),
        "coef_table": rows,
    }


def delta_method_turning_point(b1: float, b2: float, var_b1: float, var_b2: float, cov_b1_b2: float):
    """Turning point = -b1 / (2*b2). Delta-method SE and 95% CI."""
    tp = -b1 / (2.0 * b2)
    d_db1 = -1.0 / (2.0 * b2)
    d_db2 = b1 / (2.0 * b2 ** 2)
    var_tp = d_db1 ** 2 * var_b1 + d_db2 ** 2 * var_b2 + 2 * d_db1 * d_db2 * cov_b1_b2
    se_tp = float(np.sqrt(np.maximum(var_tp, 0)))
    ci_low = float(tp - 1.96 * se_tp)
    ci_high = float(tp + 1.96 * se_tp)
    return tp, se_tp, ci_low, ci_high


def dawson_u_test(result, x_min: float, x_max: float, x_col: str = "constraint_density"):
    """Test slope at observed bounds: slope = b1 + 2*b2*x."""
    params = result.params
    cov = result.cov_params()
    x2_col = f"I({x_col} ** 2)"
    b1 = params[x_col]
    b2 = params[x2_col]
    var_b1 = cov.loc[x_col, x_col]
    var_b2 = cov.loc[x2_col, x2_col]
    cov_b1_b2 = cov.loc[x_col, x2_col]

    out = []
    for x, label in [(x_min, "lower_bound"), (x_max, "upper_bound")]:
        slope = b1 + 2 * b2 * x
        d_db1 = 1.0
        d_db2 = 2 * x
        var_slope = d_db1 ** 2 * var_b1 + d_db2 ** 2 * var_b2 + 2 * d_db1 * d_db2 * cov_b1_b2
        se_slope = float(np.sqrt(np.maximum(var_slope, 0)))
        z = float(slope / se_slope) if se_slope > 0 else None
        p = float(2 * (1 - stats.norm.cdf(abs(z)))) if z is not None else None
        out.append(
            {
                "boundary": label,
                "x": float(x),
                "slope": float(slope),
                "se": se_slope,
                "z": z,
                "pvalue": p,
                "significant_05": p is not None and p < 0.05,
            }
        )
    return out


def save_json_csv(data: dict, prefix: str):
    """Save dict as JSON and flatten coef_table to CSV."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = RESULTS_DIR / f"{prefix}.json"
    csv_path = RESULTS_DIR / f"{prefix}.csv"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=float)

    # CSV friendly version: if coef_table present, save it.
    if "coef_table" in data:
        pd.DataFrame(data["coef_table"]).to_csv(csv_path, index=False)
    elif isinstance(data, dict) and all(isinstance(v, (int, float, str, bool)) for v in data.values()):
        pd.DataFrame([data]).to_csv(csv_path, index=False)
    else:
        # Generic fallback: write top-level scalar entries.
        flat = {k: v for k, v in data.items() if isinstance(v, (int, float, str, bool))}
        if flat:
            pd.DataFrame([flat]).to_csv(csv_path, index=False)
        else:
            csv_path.write_text("# See JSON for nested structure\n")


def cohens_f2(pseudo_r2_full: float, pseudo_r2_reduced: float) -> float:
    """Cohen's f^2 for logistic model comparison."""
    denom = 1 - pseudo_r2_full
    if denom <= 0:
        return np.inf
    return float((pseudo_r2_full - pseudo_r2_reduced) / denom)
