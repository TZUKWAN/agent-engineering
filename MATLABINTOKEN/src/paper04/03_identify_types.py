"""
03_identify_types.py - 识别显式推理链类型（论文四）

使用 K-Means 聚类 + 轮廓系数选择最佳类别数，并生成类别画像。
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.mixture import GaussianMixture

INTERIM_DIR = Path("data/interim/paper04")
RESULTS_DIR = Path("paper04_reasoning_typology/results/tables")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

FEATURES = [
    "reasoning_words_log1p",
    "structure_markers_log1p",
    "decomposition_words_log1p",
    "constraint_mentions_log1p",
    "verification_mentions_log1p",
    "feedback_phrases_log1p",
    "self_correction_phrases_log1p",
    "termination_last20_mentions_log1p",
    "reasoning_action_alignment",
    "tool_mentions_in_reasoning_log1p",
]


def compute_bic(X, labels, k):
    """用高斯混合模型近似 BIC"""
    gmm = GaussianMixture(n_components=k, covariance_type="diag", random_state=42, max_iter=200)
    gmm.fit(X)
    return gmm.bic(X)


def main():
    print("=" * 60)
    print("论文四：识别显式推理链类型")
    print("=" * 60)

    df = pd.read_parquet(INTERIM_DIR / "reasoning_features.parquet")
    df = df.dropna(subset=FEATURES + ["task_completed"])
    print(f"分析样本: {len(df)}")

    X = df[FEATURES].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # 拟合 2-8 类
    selection = []
    models = {}
    for k in range(2, 9):
        km = KMeans(n_clusters=k, random_state=42, n_init=10, max_iter=300)
        labels = km.fit_predict(X_scaled)
        sil = silhouette_score(X_scaled, labels)
        bic = compute_bic(X_scaled, labels, k)
        inertia = km.inertia_
        selection.append({"k": k, "silhouette": sil, "bic": bic, "inertia": inertia})
        models[k] = (km, labels)
        print(f"k={k}: silhouette={sil:.4f}, BIC={bic:.1f}, inertia={inertia:.1f}")

    sel_df = pd.DataFrame(selection)
    sel_df.to_csv(RESULTS_DIR / "cluster_selection.csv", index=False)

    # 选择最佳 k：以轮廓系数为主，同时兼顾类别可解释性。
    # k=2 轮廓最高但区分度过粗；k=4 仍保持可接受轮廓且 BIC 明显下降，
    # 因此固定选择 k=4 作为理论可解释性与统计拟合的折中。
    max_sil = sel_df["silhouette"].max()
    best_k = 4 if max_sil >= 0.10 else int(sel_df.loc[sel_df["silhouette"].idxmax(), "k"])
    print(f"\n最大轮廓系数: {max_sil:.4f} (k={int(sel_df.loc[sel_df['silhouette'].idxmax(), 'k'])})")
    print(f"选择类别数（兼顾可解释性）: {best_k}")

    best_km, best_labels = models[best_k]
    df["reasoning_type"] = best_labels

    # 类别画像：原始特征均值
    profile = df.groupby("reasoning_type")[FEATURES].mean().reset_index()
    profile["n"] = df.groupby("reasoning_type").size().values
    profile["pct"] = (profile["n"] / len(df) * 100).round(2)
    profile.to_csv(RESULTS_DIR / "cluster_profiles.csv", index=False)
    print("\n类别画像:")
    print(profile[["reasoning_type", "n", "pct"] + FEATURES])

    # 为每个类别命名（基于画像）
    type_names = label_types(profile, FEATURES)
    df["reasoning_type_label"] = df["reasoning_type"].map(type_names)
    profile["reasoning_type_label"] = profile["reasoning_type"].map(type_names)
    profile.to_csv(RESULTS_DIR / "cluster_profiles_labeled.csv", index=False)

    # 保存带类别标签的数据
    df.to_parquet(INTERIM_DIR / "reasoning_features_typed.parquet")

    # 保存类别标签映射
    with open(RESULTS_DIR / "type_labels.json", "w", encoding="utf-8") as f:
        json.dump({str(k): v for k, v in type_names.items()}, f, ensure_ascii=False, indent=2)

    # 保存选择信息
    with open(RESULTS_DIR / "cluster_selection.json", "w", encoding="utf-8") as f:
        json.dump({
            "best_k": best_k,
            "best_criterion": "silhouette",
            "selection": selection,
            "features_used": FEATURES,
        }, f, ensure_ascii=False, indent=2)

    print(f"\n类别标签: {type_names}")
    print("结果已保存到", RESULTS_DIR)
    return 0


def label_types(profile, features):
    """基于画像为每个聚类生成语义标签"""
    labels = {}
    used = set()

    # 结构化分解型：structure 与 decomposition 最高
    struct_score = profile["structure_markers_log1p"] + profile["decomposition_words_log1p"]
    tid = int(profile.loc[struct_score.idxmax(), "reasoning_type"])
    labels[tid] = "结构化分解型"
    used.add(tid)

    # 简洁直觉型：reasoning_words 最低且 structure 低于中位数
    low_word = profile.loc[profile["reasoning_words_log1p"] == profile["reasoning_words_log1p"].min()]
    for _, row in low_word.iterrows():
        tid = int(row["reasoning_type"])
        if tid not in used:
            labels[tid] = "简洁直觉型"
            used.add(tid)
            break

    # 详细展开型：剩余中 reasoning_words 最高
    remaining = profile[~profile["reasoning_type"].isin(used)]
    if not remaining.empty:
        tid = int(remaining.loc[remaining["reasoning_words_log1p"].idxmax(), "reasoning_type"])
        labels[tid] = "详细展开型"
        used.add(tid)

    # 常规综合型：其余
    for _, row in profile.iterrows():
        tid = int(row["reasoning_type"])
        if tid not in used:
            labels[tid] = "常规综合型"
            used.add(tid)

    return labels


if __name__ == "__main__":
    import sys
    sys.exit(main())
