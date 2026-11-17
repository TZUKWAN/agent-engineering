"""Lightweight LCA stability checks for revised Paper 03."""
import json
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.metrics import adjusted_rand_score
from scipy.optimize import linear_sum_assignment

import sys
sys.path.insert(0, str(Path(__file__).parent))
from utils import FEATURE_COLS, load_main_data, lca_em, entropy_from_posterior, RANDOM_SEED

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT = PROJECT_ROOT / "revised" / "paper03_tables"
OUT.mkdir(parents=True, exist_ok=True)


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
    return lca_em(X, n_classes=k, max_iter=300, tol=1e-5, n_starts=n_starts, random_state=seed)


def train_test_split_stability(X, k=5, test_frac=0.2, seed=RANDOM_SEED + 20):
    rng = np.random.default_rng(seed)
    n = len(X)
    perm = rng.permutation(n)
    test_size = int(n * test_frac)
    test_idx = perm[:test_size]
    train_idx = perm[test_size:]
    fit_train = fit_k(X[train_idx], k, n_starts=10, seed=seed)
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
    fit_full = fit_k(X, k, n_starts=15, seed=RANDOM_SEED + 1)
    aligned = align_labels(fit_full["class_labels"][test_idx], test_labels_pred)
    ari = adjusted_rand_score(fit_full["class_labels"][test_idx], aligned)
    return {
        "test_frac": test_frac,
        "test_n": int(len(test_idx)),
        "ari": float(ari),
    }


def k_comparison(X, ks=[4, 5, 6], seed=RANDOM_SEED + 30):
    results = {}
    for k in ks:
        fit = fit_k(X, k, n_starts=10 if k == 5 else 5, seed=seed + k)
        n_params = (k - 1) + k * X.shape[1]
        aic = -2 * fit["loglik"] + 2 * n_params
        bic = -2 * fit["loglik"] + n_params * np.log(len(X))
        ent = entropy_from_posterior(fit["posteriors"])
        results[str(k)] = {
            "k": k,
            "loglik": float(fit["loglik"]),
            "aic": float(aic),
            "bic": float(bic),
            "entropy": float(ent),
            "n_params": int(n_params),
        }
    return results


def small_bootstrap(X, k=5, n_boot=5, seed=RANDOM_SEED + 40):
    rng = np.random.default_rng(seed)
    base = fit_k(X, k, n_starts=10, seed=RANDOM_SEED + 1)
    base_labels = base["class_labels"]
    aris = []
    for b in range(n_boot):
        idx = rng.integers(0, len(X), size=len(X))
        fit = lca_em(X[idx], n_classes=k, max_iter=250, tol=1e-5, n_starts=2, random_state=seed + b)
        boot_labels_full = np.full(len(X), -1)
        boot_labels_full[idx] = fit["class_labels"]
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


def main():
    df = load_main_data().reset_index(drop=True)
    X = df[FEATURE_COLS].astype(int).values
    print(f"N={len(df)}, features={X.shape[1]}")

    print("Running train/test split stability...")
    tt = train_test_split_stability(X, k=5)
    print(tt)

    print("Running k=4/5/6 comparison...")
    kc = k_comparison(X)
    print(kc)

    print("Running small bootstrap...")
    boot = small_bootstrap(X, k=5, n_boot=5)
    print(boot)

    result = {
        "note": "Lightweight stability checks due to computational constraints. Bootstrap used only 5 resamples with 2 random starts; train/test split used 10 starts on training set. For publication-grade inference, increase bootstrap resamples to 200+ and random starts to 30.",
        "train_test_split": tt,
        "k_comparison": kc,
        "small_bootstrap": boot,
    }
    with open(OUT / "tab_stability_checks.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"Saved {OUT / 'tab_stability_checks.json'}")


if __name__ == "__main__":
    main()
