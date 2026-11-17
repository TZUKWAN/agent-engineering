"""Fit LCA-like models (1-8 classes) and select best k."""
import json
import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture
from sklearn.metrics import adjusted_rand_score
from scipy.stats import chi2

from utils import (
    RANDOM_SEED,
    FEATURE_COLS,
    load_main_data,
    results_dir,
    save_json_csv,
    entropy_from_posterior,
    lca_em,
    align_labels,
)


def gmm_lca(X: np.ndarray, k: int):
    model = GaussianMixture(
        n_components=k,
        covariance_type="tied",
        random_state=RANDOM_SEED,
        max_iter=500,
        n_init=5,
        tol=1e-5,
        reg_covar=1e-6,
    )
    model.fit(X)
    post = model.predict_proba(X)
    labels = np.argmax(post, axis=1)
    # Param count for tied covariance: (k-1) mixing + k*J means + J*(J+1)/2 covariance
    n_params = (k - 1) + k * X.shape[1] + X.shape[1] * (X.shape[1] + 1) // 2
    return {
        "k": k,
        "log_likelihood": float(model.lower_bound_ * X.shape[0]),
        "aic": float(model.aic(X)),
        "bic": float(model.bic(X)),
        "entropy": entropy_from_posterior(post),
        "n_params": n_params,
        "labels": labels,
        "posteriors": post,
    }


def lrt_p(ll_k: float, ll_km1: float, df: int):
    if ll_km1 is None:
        return None
    stat = 2 * (ll_k - ll_km1)
    if stat < 0:
        stat = 0.0
    return float(chi2.sf(stat, df))


def main():
    df = load_main_data()
    X = df[FEATURE_COLS].astype(int).values
    n = X.shape[0]
    j = X.shape[1]
    df_diff = j + 1  # additional parameters when adding one class in binary LCA

    # ---------- Gaussian Mixture (exploratory) ----------
    gmm_results = []
    for k in range(1, 9):
        res = gmm_lca(X, k)
        gmm_results.append(res)

    gmm_table = []
    for i, res in enumerate(gmm_results):
        lrtp = lrt_p(
            res["log_likelihood"],
            gmm_results[i - 1]["log_likelihood"] if i > 0 else None,
            df_diff,
        )
        gmm_table.append(
            {
                "k": res["k"],
                "log_likelihood": res["log_likelihood"],
                "aic": res["aic"],
                "bic": res["bic"],
                "entropy": res["entropy"],
                "n_params": res["n_params"],
                "lrt_p": lrtp,
            }
        )

    # ---------- Custom EM LCA (dedicated/confirmatory) ----------
    em_results = []
    for k in range(1, 9):
        fit = lca_em(
            X,
            n_classes=k,
            max_iter=400,
            tol=1e-5,
            n_starts=10,
            random_state=RANDOM_SEED,
        )
        n_params = (k - 1) + k * j
        aic = -2 * fit["loglik"] + 2 * n_params
        bic = -2 * fit["loglik"] + n_params * np.log(n)
        em_results.append(
            {
                "k": k,
                "log_likelihood": fit["loglik"],
                "aic": aic,
                "bic": bic,
                "entropy": entropy_from_posterior(fit["posteriors"]),
                "n_params": n_params,
                "pi": fit["pi"],
                "theta": fit["theta"],
                "labels": fit["class_labels"],
                "posteriors": fit["posteriors"],
            }
        )

    em_table = []
    for i, res in enumerate(em_results):
        lrtp = lrt_p(
            res["log_likelihood"],
            em_results[i - 1]["log_likelihood"] if i > 0 else None,
            df_diff,
        )
        em_table.append(
            {
                "k": res["k"],
                "log_likelihood": res["log_likelihood"],
                "aic": res["aic"],
                "bic": res["bic"],
                "entropy": res["entropy"],
                "n_params": res["n_params"],
                "lrt_p": lrtp,
            }
        )

    # ---------- Model selection ----------
    def select_lowest_bic(table):
        best_idx = int(np.argmin([r["bic"] for r in table]))
        return table[best_idx]["k"], best_idx

    gmm_best_k, _ = select_lowest_bic(gmm_table)
    em_raw_best_k, _ = select_lowest_bic(em_table)

    # Choose final k by BIC elbow + parsimony. The EM BIC keeps decreasing in this
    # large sample, but the relative gain slows markedly after k=5. We select the
    # smallest k where two consecutive relative BIC improvements fall below 0.15%.
    bics = [r["bic"] for r in em_table]
    rel_improvements = [
        (bics[i] - bics[i + 1]) / abs(bics[i]) if np.isfinite(bics[i]) else 0.0
        for i in range(len(bics) - 1)
    ]
    threshold = 0.0015
    best_k = em_raw_best_k  # fallback
    for i in range(len(rel_improvements) - 1):
        if rel_improvements[i] < threshold and rel_improvements[i + 1] < threshold:
            best_k = i + 1
            break

    # Refit selected k with more random starts for stable downstream results
    final_refit = lca_em(
        X,
        n_classes=best_k,
        max_iter=500,
        tol=1e-5,
        n_starts=30,
        random_state=RANDOM_SEED + 1,
    )
    em_results[best_k - 1].update(
        {
            "log_likelihood": final_refit["loglik"],
            "pi": final_refit["pi"],
            "theta": final_refit["theta"],
            "labels": final_refit["class_labels"],
            "posteriors": final_refit["posteriors"],
        }
    )
    # Recompute table entry for selected k
    n_params = (best_k - 1) + best_k * j
    em_table[best_k - 1]["log_likelihood"] = final_refit["loglik"]
    em_table[best_k - 1]["aic"] = -2 * final_refit["loglik"] + 2 * n_params
    em_table[best_k - 1]["bic"] = -2 * final_refit["loglik"] + n_params * np.log(n)
    em_table[best_k - 1]["entropy"] = entropy_from_posterior(final_refit["posteriors"])
    if best_k > 1:
        em_table[best_k - 1]["lrt_p"] = lrt_p(
            final_refit["loglik"],
            em_results[best_k - 2]["log_likelihood"],
            df_diff,
        )

    # Compare assignments at chosen k
    em_labels = em_results[best_k - 1]["labels"]
    gmm_labels = gmm_results[best_k - 1]["labels"]
    aligned_gmm = align_labels(em_labels, gmm_labels)
    ari_gmm_em = adjusted_rand_score(em_labels, aligned_gmm)

    selection = {
        "implementation": "Custom EM LCA used as final; GaussianMixture as exploratory approximation",
        "final_best_k": int(best_k),
        "final_selection_basis": (
            "BIC elbow on dedicated EM LCA: smallest k where two consecutive relative BIC gains "
            f"are below {threshold*100:.2f}%; entropy and LRT reported. Raw BIC minimum is k={int(em_raw_best_k)}."
        ),
        "gmm_best_k": int(gmm_best_k),
        "em_raw_best_k": int(em_raw_best_k),
        "gmm_vs_em_ari_at_final_k": float(ari_gmm_em),
        "bic_relative_improvements": [float(x) for x in rel_improvements],
        "gmm_model_selection": gmm_table,
        "em_model_selection": em_table,
        "note": "No R/poLCA available; custom EM implements standard binary LCA. GaussianMixture provides exploratory comparison.",
    }

    save_json_csv(selection, "01_lca_model_selection")

    # Save class assignments from final model
    assign_df = pd.DataFrame(
        {
            "task_id": df["task_id"].values,
            "class": em_labels,
            "posterior_max": em_results[best_k - 1]["posteriors"].max(axis=1),
        }
    )
    for c in range(best_k):
        assign_df[f"post_class_{c}"] = em_results[best_k - 1]["posteriors"][:, c]
    assign_path = results_dir() / "class_assignments.csv"
    assign_df.to_csv(assign_path, index=False)

    # Save a small serialized model for downstream use
    model_info = {
        "k": best_k,
        "pi": em_results[best_k - 1]["pi"].tolist(),
        "theta": em_results[best_k - 1]["theta"].tolist(),
        "feature_cols": FEATURE_COLS,
    }
    with open(results_dir() / "lca_model.json", "w", encoding="utf-8") as f:
        json.dump(model_info, f, indent=2)

    print(f"Saved model selection. Final selected k = {best_k} (EM). Raw BIC min k = {em_raw_best_k}. GMM best k = {gmm_best_k}. ARI(GMM,EM) = {ari_gmm_em:.3f}")


if __name__ == "__main__":
    main()
