"""
论文A Step 9: 稳健性检验
1. 分平台LCA（win_mac vs ubuntu）
2. 句法特征 vs 关键词特征 vs 两者结合的LCA对比
3. 样本量敏感性（50%/70%子样本）
"""
import os, json
import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import adjusted_rand_score

SEED = 42
RESULT_DIR = "results/optimization/paperA"

SYNTACTIC_COLS = ['imperative_verb_count', 'modal_obligation_count', 'modal_prohibition_count',
                  'declarative_predicate_count', 'perfective_aspect_count', 'discourse_temporal_count',
                  'object_argument_count', 't_unit_count', 'clause_density', 'dependency_tree_depth',
                  'noun_entity_count']

KEYWORD_COLS = ['has_application', 'has_operation_object', 'has_target_action',
                'has_target_state', 'has_file_reference', 'has_object_properties',
                'has_operation_order', 'has_multiple_subtasks', 'has_constraint_words',
                'has_completion_criteria', 'has_initial_state']


def save_json(data, name):
    with open(os.path.join(RESULT_DIR, f"{name}.json"), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def run_lca(X, k_range=range(1, 9)):
    """运行LCA模型选择，返回最佳k的标签和BIC序列"""
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    bics = []
    models = {}
    for k in k_range:
        gmm = GaussianMixture(n_components=k, covariance_type='diag',
                              random_state=SEED, max_iter=200, n_init=3)
        gmm.fit(X_scaled)
        bics.append(float(gmm.bic(X_scaled)))
        models[k] = gmm
    # 选k=5或BIC肘部
    best_k = 5
    if best_k not in models:
        best_k = min(models.keys(), key=lambda x: bics[list(k_range).index(x)])
    labels = models[best_k].predict(X_scaled)
    return labels, bics, best_k


def step9_robustness():
    print("=" * 60)
    print("Step 9: 稳健性检验")
    print("=" * 60)

    # 加载数据
    data = pd.read_parquet(os.path.join(RESULT_DIR, 'data_with_classes.parquet'))
    print(f"样本: {len(data)}")

    results = {}

    # ---- 1. 分平台LCA ----
    print("\n-- 1. 分平台LCA --")
    # 加载原始全样本（含os信息）
    full_data = pd.read_parquet(os.path.join(RESULT_DIR, 'merged_data.parquet'))

    platform_results = {}
    # 全样本的类别标签（作为参照）
    full_labels = data['pragmatic_class'].values

    for platform in ['win_mac', 'ubuntu']:
        sub_mask = data['os'] == platform
        sub_data = data[sub_mask].copy()
        if len(sub_data) < 500:
            print(f"  {platform}: 样本不足({len(sub_data)})，跳过")
            continue

        X = sub_data[SYNTACTIC_COLS].values
        X_log = np.log1p(np.maximum(X, 0))
        sub_labels, sub_bics, sub_k = run_lca(X)

        # 与全样本在该子集上的标签比较ARI
        full_labels_sub = full_labels[sub_mask.values]
        ari = adjusted_rand_score(full_labels_sub, sub_labels)

        # 各类别占比
        class_dist = pd.Series(sub_labels).value_counts(normalize=True).sort_index().to_dict()

        platform_results[platform] = {
            'n': len(sub_data),
            'best_k': int(sub_k),
            'ari_vs_full': float(ari),
            'class_distribution': {int(k): float(v) for k, v in class_dist.items()},
        }
        print(f"  {platform}: N={len(sub_data)}, k={sub_k}, ARI vs full={ari:.3f}")

    results['cross_platform'] = platform_results

    # ---- 2. 特征集对比 ----
    print("\n-- 2. 特征集对比（句法 vs 关键词 vs 结合）--")
    feature_set_results = {}

    # 确保关键词特征列存在且为数值
    available_keyword = [c for c in KEYWORD_COLS if c in data.columns]
    available_syntactic = [c for c in SYNTACTIC_COLS if c in data.columns]

    for set_name, cols in [('syntactic_only', available_syntactic),
                            ('keyword_only', available_keyword),
                            ('combined', available_syntactic + available_keyword)]:
        if len(cols) == 0:
            continue
        X = data[cols].values
        X_log = np.log1p(np.maximum(X, 0))
        labels, bics, best_k = run_lca(X)

        # 与全样本句法特征LCA的标签比较
        ari = adjusted_rand_score(full_labels, labels)
        class_dist = pd.Series(labels).value_counts(normalize=True).sort_index().to_dict()

        feature_set_results[set_name] = {
            'n_features': len(cols),
            'best_k': int(best_k),
            'ari_vs_syntactic': float(ari),
            'class_distribution': {int(k): float(v) for k, v in class_dist.items()},
            'bic_at_k5': float(bics[4]) if len(bics) >= 5 else None,
        }
        print(f"  {set_name}: {len(cols)}特征, k={best_k}, ARI vs syntactic={ari:.3f}")

    results['feature_set_comparison'] = feature_set_results

    # ---- 3. 样本量敏感性 ----
    print("\n-- 3. 样本量敏感性 --")
    sample_results = {}

    X_full = data[available_syntactic].values
    X_full_log = np.log1p(np.maximum(X_full, 0))

    for frac in [0.5, 0.7]:
        np.random.seed(SEED)
        sample_idx = np.random.choice(len(data), size=int(len(data) * frac), replace=False)
        X_sub = X_full_log[sample_idx]
        labels_sub, _, sub_k = run_lca(X_sub)

        # 全样本在这些样本上的标签
        full_labels_sub = full_labels[sample_idx]
        ari = adjusted_rand_score(full_labels_sub, labels_sub)

        sample_results[f'frac_{frac}'] = {
            'n': len(sample_idx),
            'best_k': int(sub_k),
            'ari_vs_full': float(ari),
        }
        print(f"  {frac*100:.0f}%子样本: N={len(sample_idx)}, k={sub_k}, ARI={ari:.3f}")

    results['sample_sensitivity'] = sample_results

    save_json(results, '09_robustness_check')
    print("\n稳健性检验完成，结果已保存。")
    return results


if __name__ == '__main__':
    step9_robustness()
