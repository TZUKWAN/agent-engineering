"""Shared utilities for Paper 03 (Pragmatic Typology with LCA)."""
import json
import numpy as np
import pandas as pd
from pathlib import Path

RANDOM_SEED = 42

FEATURE_COLS = [
    "has_application",
    "has_operation_object",
    "has_target_action",
    "has_target_state",
    "has_file_reference",
    "has_object_properties",
    "has_operation_order",
    "has_multiple_subtasks",
    "has_constraint_words",
    "has_completion_criteria",
    "has_initial_state",
]

OUTCOME_COLS = [
    "task_completed",
    "total_steps",
    "incorrect_steps",
    "redundant_ratio",
    "alignment_score",
    "efficiency_score",
]

COVARIATE_COLS = ["task_difficulty", "word_count", "os", "explicitness_score"]


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def results_dir() -> Path:
    d = project_root() / "results" / "papers" / "paper03"
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_main_data() -> pd.DataFrame:
    """Load analysis data, drop rows with missing outcomes, and coerce types."""
    path = project_root() / "data" / "processed" / "analysis_data.parquet"
    df = pd.read_parquet(path)

    # task_completed may be object with True/False/None
    df["task_completed"] = df["task_completed"].map(
        {True: True, False: False, "True": True, "False": False, None: np.nan}
    )
    # numeric columns
    for col in OUTCOME_COLS[1:]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in COVARIATE_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # listwise deletion for key outcomes
    required = ["task_completed", "total_steps", "incorrect_steps", "redundant_ratio"]
    df = df.dropna(subset=required).copy()
    df["task_completed"] = df["task_completed"].astype(bool)
    df["explicitness_score"] = df["explicitness_score"].astype(int)
    return df


def load_steps() -> pd.DataFrame:
    path = project_root() / "data" / "interim" / "steps.parquet"
    steps = pd.read_parquet(path)
    # Coerce booleans where possible
    for col in ["last_step_correct", "last_step_redundant"]:
        if col in steps.columns:
            steps[col] = steps[col].map(
                {True: True, False: False, "True": True, "False": False, None: np.nan}
            )
    return steps


def save_json_csv(data, name: str):
    """Save dict/list as JSON and, if possible, as CSV."""
    out = results_dir()
    json_path = out / f"{name}.json"
    csv_path = out / f"{name}.csv"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

    if isinstance(data, dict):
        # Try to flatten to DataFrame
        try:
            df = pd.json_normalize(data)
            df.to_csv(csv_path, index=False)
            return
        except Exception:
            pass
    if isinstance(data, list):
        try:
            df = pd.DataFrame(data)
            df.to_csv(csv_path, index=False)
            return
        except Exception:
            pass
    # Fallback: single-row DataFrame
    pd.DataFrame([data]).to_csv(csv_path, index=False)


def load_assignments() -> pd.DataFrame:
    """Load class assignments aligned row-wise with load_main_data()."""
    return pd.read_csv(results_dir() / "class_assignments.csv")


def load_class_labels() -> pd.DataFrame:
    return pd.read_csv(results_dir() / "class_labels.csv")


def add_class_to_df(df: pd.DataFrame) -> pd.DataFrame:
    """Add class, label and posterior columns to df by positional alignment (same row order as in 01_lca.py)."""
    assigns = load_assignments()
    labels = load_class_labels()
    if len(df) != len(assigns):
        raise ValueError(
            f"DataFrame length {len(df)} does not match assignments length {len(assigns)}. "
            "Ensure both come from load_main_data()."
        )
    out = df.copy().reset_index(drop=True)
    out["class"] = assigns["class"].values
    if "posterior_max" in assigns.columns:
        out["posterior_max"] = assigns["posterior_max"].values
    label_map = dict(zip(labels["class"], labels["label"]))
    out["class_label"] = out["class"].map(label_map)
    return out


def entropy_from_posterior(posterior: np.ndarray) -> float:
    """Normalized entropy: 1 - mean(-sum p*log p) / log(k)."""
    k = posterior.shape[1]
    if k == 1:
        return 1.0
    # Clip to avoid log(0)
    p = np.clip(posterior, 1e-12, 1.0)
    ent = -np.sum(p * np.log(p), axis=1)
    mean_ent = np.mean(ent)
    return float(1.0 - mean_ent / np.log(k))


def lca_em(
    X: np.ndarray,
    n_classes: int,
    max_iter: int = 300,
    tol: float = 1e-5,
    n_starts: int = 10,
    random_state: int = RANDOM_SEED,
    smoothing: float = 1e-6,
):
    """Custom EM algorithm for binary latent class analysis.

    Returns
    -------
    dict with keys: pi (class prevalences), theta (item response probs, k x J),
        loglik, posteriors, class_labels, n_iter, converged.
    """
    rng = np.random.default_rng(random_state)
    n, j = X.shape
    best = {"loglik": -np.inf}

    for start in range(n_starts if n_classes > 1 else 1):
        # random init
        if n_classes == 1:
            pi = np.ones(1)
            theta = (X.mean(axis=0, keepdims=True) + smoothing) / (1 + 2 * smoothing)
        else:
            # K-means-like seeds from random task rows
            idx = rng.choice(n, size=n_classes, replace=False)
            theta = (X[idx].astype(float) + smoothing) / (1 + 2 * smoothing)
            pi = rng.dirichlet(np.ones(n_classes))

        loglik_old = -np.inf
        for it in range(max_iter):
            # E-step
            # log p(x|z) = sum_j x_ij log theta_zj + (1-x_ij) log(1-theta_zj)
            log_prob_x_given_z = (
                X[:, None, :] * np.log(theta[None, :, :])
                + (1 - X[:, None, :]) * np.log(1 - theta[None, :, :])
            ).sum(axis=2)
            log_post = np.log(pi[None, :]) + log_prob_x_given_z
            log_max = np.max(log_post, axis=1, keepdims=True)
            log_post_stable = log_post - log_max
            post = np.exp(log_post_stable)
            post /= post.sum(axis=1, keepdims=True)

            # M-step
            class_counts = post.sum(axis=0)
            pi = (class_counts + smoothing) / (n + n_classes * smoothing)
            theta = (
                post.T @ X + smoothing
            ) / (class_counts[:, None] + 2 * smoothing)

            # log-likelihood (use original log_post for exact log-sum-exp)
            loglik = float(np.sum(log_max.squeeze() + np.log(np.exp(log_post_stable).sum(axis=1))))
            if np.isnan(loglik):
                break
            if it > 0 and abs(loglik - loglik_old) < tol:
                break
            loglik_old = loglik

        if loglik > best["loglik"] and not np.isnan(loglik):
            best = {
                "pi": pi,
                "theta": theta,
                "loglik": loglik,
                "posteriors": post,
                "class_labels": np.argmax(post, axis=1),
                "n_iter": it,
                "converged": it < max_iter - 1,
            }

    return best


def align_labels(y1: np.ndarray, y2: np.ndarray):
    """Align two label vectors with Hungarian algorithm; returns remapped y2."""
    from scipy.optimize import linear_sum_assignment

    classes1 = np.unique(y1)
    classes2 = np.unique(y2)
    contingency = np.zeros((len(classes1), len(classes2)), dtype=int)
    for i, c1 in enumerate(classes1):
        for j, c2 in enumerate(classes2):
            contingency[i, j] = np.sum((y1 == c1) & (y2 == c2))
    row_ind, col_ind = linear_sum_assignment(-contingency)
    mapping = {classes2[j]: classes1[i] for i, j in zip(row_ind, col_ind)}
    return np.array([mapping.get(v, v) for v in y2])
