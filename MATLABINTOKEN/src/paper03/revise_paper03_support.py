"""Generate support materials for revised Paper 03.

- Pull real instruction examples per class with features, posterior, and completion.
- Run LCA stability checks (bootstrap, train/test split, k=4/5/6 comparison).
- Generate supplementary tables/figures saved under revised/paper03_*.
"""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.metrics import adjusted_rand_score
from scipy.optimize import linear_sum_assignment

import sys
sys.path.insert(0, str(Path(__file__).parent))
from utils import (
    FEATURE_COLS,
    load_main_data,
    lca_em,
    entropy_from_posterior,
    RANDOM_SEED,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REVISED = PROJECT_ROOT / "revised"
REVISED_FIGS = REVISED / "paper03_figures"
REVISED_TABS = REVISED / "paper03_tables"
REVISED_FIGS.mkdir(parents=True, exist_ok=True)
REVISED_TABS.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. Real examples
# ---------------------------------------------------------------------------

def load_labeled_data():
    df = load_main_data().reset_index(drop=True)
    assigns = pd.read_csv(PROJECT_ROOT / "results" / "papers" / "paper03" / "class_assignments.csv")
    labels = pd.read_csv(PROJECT_ROOT / "results" / "papers" / "paper03" / "class_labels.csv")
    label_map = dict(zip(labels["class"], labels["label"]))
    assert len(df) == len(assigns), f"{len(df)} != {len(assigns)}"
    df["class"] = assigns["class"].values
    df["class_label"] = df["class"].map(label_map)
    df["posterior_max"] = assigns["posterior_max"].values
    return df


def translate_instruction(text):
    """Return a simple Chinese paraphrase/translation placeholder.

    Real translations would require an LLM; here we provide faithful paraphrase
    summaries that capture the task content for the paper.
    """
    # This function is intentionally lightweight; examples are edited manually
    # in the final markdown. We return the original to avoid hallucination.
    return text


def pick_examples(df, n_per_class=3, seed=RANDOM_SEED):
    rng = np.random.default_rng(seed)
    examples = []
    for cls, sub in df.groupby("class"):
        label = sub["class_label"].iloc[0]
        # Try to balance completion status while keeping high posterior
        completed = sub[sub["task_completed"] == True].sort_values("posterior_max", ascending=False)
        incomplete = sub[sub["task_completed"] == False].sort_values("posterior_max", ascending=False)
        chosen = []
        # alternate to get diversity
        for i in range(n_per_class):
            src = incomplete if (i % 2 == 1 and len(incomplete) > 0) else completed
            if len(src) == 0:
                src = sub
            idx = min(i, len(src) - 1)
            row = src.iloc[idx]
            chosen.append(row)
        for row in chosen:
            feat_list = [f for f in FEATURE_COLS if row.get(f, False)]
            examples.append({
                "class": int(cls),
                "label": label,
                "task_id": row["task_id"],
                "instruction": row["instruction"],
                "posterior_max": float(row["posterior_max"]),
                "task_completed": bool(row["task_completed"]),
                "explicitness_score": int(row["explicitness_score"]),
                "hit_features": feat_list,
            })
    return pd.DataFrame(examples)


# ---------------------------------------------------------------------------
# 2. Stability checks
# ---------------------------------------------------------------------------

def align_labels(y_ref, y_new):
    classes_ref = np.unique(y_ref)
    classes_new = np.unique(y_new)
    cont = np.zeros((len(classes_ref), len(classes_new)), dtype=int)
    for i, c1 in enumerate(classes_ref):
        for j, c2 in enumerate(classes_new):
            cont[i, j] = np.sum((y_ref == c1) & (y_new == c2))
    row_ind, col_ind = linear_sum_assignment(-cont)
    mapping = {classes_new[j]: classes_ref[i] for i, j in zip(row_ind, col_ind)}
    return np.array([mapping.get(v, v) for v in y_new])


def fit_k(X, k, n_starts=10, seed=RANDOM_SEED):
    fit = lca_em(X, n_classes=k, max_iter=400, tol=1e-5, n_starts=n_starts, random_state=seed)
    return fit


def stability_bootstrap(X, k=5, n_boot=20, seed=RANDOM_SEED + 10):
    rng = np.random.default_rng(seed)
    base = fit_k(X, k, n_starts=30, seed=RANDOM_SEED + 1)
    base_labels = base["class_labels"]
    aris = []
    for b in range(n_boot):
        idx = rng.integers(0, len(X), size=len(X))
        fit = lca_em(X[idx], n_classes=k, max_iter=300, tol=1e-5, n_starts=3, random_state=seed + b)
        # map bootstrap labels back to full-sample labels via aligned indices
        boot_labels_full = np.full(len(X), -1)
        boot_labels_full[idx] = fit["class_labels"]
        # only compare rows where both are defined
        mask = boot_labels_full >= 0
        if mask.sum() < 100:
            continue
        aligned = align_labels(base_labels[mask], boot_labels_full[mask])
        aris.append(adjusted_rand_score(base_labels[mask], aligned))
    return {
        "n_boot": n_boot,
        "ari_mean": float(np.mean(aris)) if aris else None,
        "ari_std": float(np.std(aris)) if aris else None,
        "ari_min": float(np.min(aris)) if aris else None,
        "ari_max": float(np.max(aris)) if aris else None,
        "aris": [float(a) for a in aris],
    }


def stability_traintest(X, k=5, test_frac=0.2, seed=RANDOM_SEED + 20):
    rng = np.random.default_rng(seed)
    n = len(X)
    perm = rng.permutation(n)
    test_size = int(n * test_frac)
    train_idx = perm[test_size:]
    test_idx = perm[:test_size]
    fit_train = lca_em(X[train_idx], n_classes=k, max_iter=400, tol=1e-5, n_starts=20, random_state=seed)
    # predict test posteriors using train parameters
    theta = fit_train["theta"]
    pi = fit_train["pi"]
    X_test = X[test_idx]
    log_prob = (
        X_test[:, None, :] * np.log(theta[None, :, :])
        + (1 - X_test[:, None, :]) * np.log(1 - theta[None, :, :])
    ).sum(axis=2)
    log_post = np.log(pi[None, :]) + log_prob
    log_max = np.max(log_post, axis=1, keepdims=True)
    post = np.exp(log_post - log_max)
    post /= post.sum(axis=1, keepdims=True)
    test_labels_pred = np.argmax(post, axis=1)
    # refit on full data for reference
    fit_full = fit_k(X, k, n_starts=30, seed=RANDOM_SEED + 1)
    aligned = align_labels(fit_full["class_labels"][test_idx], test_labels_pred)
    ari = adjusted_rand_score(fit_full["class_labels"][test_idx], aligned)
    return {
        "test_frac": test_frac,
        "test_n": int(len(test_idx)),
        "ari": float(ari),
    }


def stability_k_comparison(X, ks=[4, 5, 6], seed=RANDOM_SEED + 30):
    results = {}
    for k in ks:
        fit = fit_k(X, k, n_starts=10 if k == 5 else 5, seed=seed + k)
        n_params = (k - 1) + k * X.shape[1]
        aic = -2 * fit["loglik"] + 2 * n_params
        bic = -2 * fit["loglik"] + n_params * np.log(len(X))
        ent = entropy_from_posterior(fit["posteriors"])
        results[k] = {
            "k": k,
            "loglik": float(fit["loglik"]),
            "aic": float(aic),
            "bic": float(bic),
            "entropy": float(ent),
            "n_params": int(n_params),
        }
    return results


def run_stability(df):
    X = df[FEATURE_COLS].astype(int).values
    print("Running bootstrap stability (this may take a few minutes)...")
    boot = stability_bootstrap(X, k=5, n_boot=50)
    print(f"Bootstrap ARI: M={boot['ari_mean']:.3f}, SD={boot['ari_std']:.3f}, min={boot['ari_min']:.3f}, max={boot['ari_max']:.3f}")
    tt = stability_traintest(X, k=5)
    print(f"Train/test ARI: {tt['ari']:.3f}")
    kcomp = stability_k_comparison(X)
    print("k comparison:", kcomp)
    return {"bootstrap": boot, "train_test": tt, "k_comparison": kcomp}


# ---------------------------------------------------------------------------
# 3. Supplementary tables/figures
# ---------------------------------------------------------------------------

def save_model_selection_table(em_table):
    tab = pd.DataFrame(em_table)
    tab["bic_relative_gain"] = [None] + [
        (tab.loc[i - 1, "bic"] - tab.loc[i, "bic"]) / abs(tab.loc[i - 1, "bic"])
        for i in range(1, len(tab))
    ]
    tab.to_csv(REVISED_TABS / "tab_model_selection.csv", index=False, float_format="%.4f")
    return tab


def save_profile_table(profiles):
    rows = []
    for p in profiles:
        row = {"class": p["class"], "label": p["label"], "prevalence": p["class_prevalence"]}
        for f in FEATURE_COLS:
            row[f] = p[f]
        rows.append(row)
    tab = pd.DataFrame(rows)
    tab.to_csv(REVISED_TABS / "tab_class_profiles.csv", index=False, float_format="%.3f")
    return tab


def make_profile_heatmap(profiles):
    mat = np.array([[p[f] for f in FEATURE_COLS] for p in profiles])
    labels = [p["label"] for p in profiles]
    fig, ax = plt.subplots(figsize=(10, 5))
    im = ax.imshow(mat, aspect="auto", cmap="YlOrRd", vmin=0, vmax=1)
    ax.set_xticks(np.arange(len(FEATURE_COLS)))
    ax.set_xticklabels([f.replace("has_", "") for f in FEATURE_COLS], rotation=45, ha="right")
    ax.set_yticks(np.arange(len(labels)))
    ax.set_yticklabels(labels)
    for i in range(len(labels)):
        for j in range(len(FEATURE_COLS)):
            ax.text(j, i, f"{mat[i, j]:.2f}", ha="center", va="center", color="black", fontsize=7)
    fig.colorbar(im, ax=ax, label="Conditional response probability")
    ax.set_title("Conditional Response Probability Heatmap (k=5)")
    fig.tight_layout()
    fig.savefig(REVISED_FIGS / "fig_profile_heatmap.png", dpi=300)
    plt.close(fig)


def make_bic_elbow(em_table):
    tab = pd.DataFrame(em_table)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(tab["k"], tab["bic"], marker="o")
    ax.axvline(5, color="red", linestyle="--", label="selected k=5")
    ax.set_xlabel("Number of classes k")
    ax.set_ylabel("BIC")
    ax.set_title("BIC by number of latent classes (custom binary EM-LCA)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(REVISED_FIGS / "fig_bic_elbow.png", dpi=300)
    plt.close(fig)


def make_path_metrics_figure(path_json):
    cont = path_json["continuous_descriptives"]
    metrics = ["max_consecutive_incorrect", "transition_count", "transition_rate"]
    # first_error_position not significant, skip
    data = {m: {} for m in metrics}
    for row in cont:
        if row["variable"] in data:
            data[row["variable"]][row["label"]] = row["mean"]
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    for ax, metric in zip(axes, metrics):
        labels_list = list(data[metric].keys())
        vals = list(data[metric].values())
        ax.bar(range(len(labels_list)), vals, color="steelblue")
        ax.set_xticks(range(len(labels_list)))
        ax.set_xticklabels(labels_list, rotation=30, ha="right", fontsize=8)
        ax.set_title(metric.replace("_", " "))
    fig.suptitle("Path stability metrics by pragmatic class")
    fig.tight_layout()
    fig.savefig(REVISED_FIGS / "fig_path_metrics.png", dpi=300)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    df = load_labeled_data()
    print(f"Loaded labeled data: N={len(df)}")

    # Examples
    ex_df = pick_examples(df, n_per_class=3)
    ex_df.to_json(REVISED_TABS / "tab_examples.json", orient="records", force_ascii=False, indent=2)
    print(f"Saved {len(ex_df)} examples.")

    # Stability (run separately if too slow; placeholder here)
    stab = {"status": "pending", "note": "Run via run_stability_only() due to computational cost"}
    with open(REVISED_TABS / "tab_stability_checks.json", "w", encoding="utf-8") as f:
        json.dump(stab, f, indent=2, ensure_ascii=False)

    # Tables/figures from existing results
    with open(PROJECT_ROOT / "results" / "papers" / "paper03" / "01_lca_model_selection.json", encoding="utf-8") as f:
        sel = json.load(f)
    save_model_selection_table(sel["em_model_selection"])

    with open(PROJECT_ROOT / "results" / "papers" / "paper03" / "02_lca_profiles.json", encoding="utf-8") as f:
        prof = json.load(f)
    save_profile_table(prof["model_profiles"])
    make_profile_heatmap(prof["model_profiles"])
    make_bic_elbow(sel["em_model_selection"])

    with open(PROJECT_ROOT / "results" / "papers" / "paper03" / "07_path_analysis.json", encoding="utf-8") as f:
        path = json.load(f)
    make_path_metrics_figure(path)

    print("Support materials generated under revised/paper03_figures and revised/paper03_tables.")


if __name__ == "__main__":
    main()
