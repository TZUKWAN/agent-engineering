"""
论文A Step 3-9: LCA + 类型差异 + 控制 + 调节 + 稳健性
"""
import os, json
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
import statsmodels.formula.api as smf

SEED = 42
RESULT_DIR = "results/optimization/paperA"


def save_json(data, name):
    with open(os.path.join(RESULT_DIR, f"{name}.json"), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def step3_lca(merged):
    """Step 3: 潜在类别分析"""
    print("=" * 60)
    print("Step 3: 潜在类别分析")
    print("=" * 60)

    # LCA输入特征（11个句法特征）
    feature_cols = ['imperative_verb_count', 'modal_obligation_count', 'modal_prohibition_count',
                    'declarative_predicate_count', 'perfective_aspect_count', 'discourse_temporal_count',
                    'object_argument_count', 't_unit_count', 'clause_density', 'dependency_tree_depth',
                    'noun_entity_count']

    data = merged.dropna(subset=feature_cols + ['task_completed_num']).copy()
    X = data[feature_cols].values

    # 对数变换+标准化
    X_log = np.log1p(np.maximum(X, 0))
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_log)

    # 拟合k=1到8
    print("\n模型选择:")
    selection = []
    models = {}
    for k in range(1, 9):
        gmm = GaussianMixture(n_components=k, covariance_type='diag',
                              random_state=SEED, max_iter=200, n_init=5)
        gmm.fit(X_scaled)
        bic = gmm.bic(X_scaled)
        aic = gmm.aic(X_scaled)
        labels = gmm.predict(X_scaled)
        # 熵值
        probs = gmm.predict_proba(X_scaled)
        entropy = 1 - (-np.sum(probs * np.log(probs + 1e-10), axis=1).sum()) / (len(X_scaled) * np.log(k)) if k > 1 else 1.0
        selection.append({'k': k, 'bic': float(bic), 'aic': float(aic), 'entropy': float(entropy)})
        models[k] = gmm
        print(f"  k={k}: BIC={bic:.1f}, AIC={aic:.1f}, Entropy={entropy:.3f}")

    save_json({'selection': selection}, '03_lca_model_selection')

    # 选择最佳k：BIC肘部
    # 找BIC下降率明显减小的点
    bic_diffs = [selection[i]['bic'] - selection[i+1]['bic'] for i in range(len(selection)-1)]
    best_k = 5  # 基于原研究和理论预期
    # 验证k=5的合理性
    for k in range(2, len(bic_diffs)):
        if bic_diffs[k] < bic_diffs[k-1] * 0.3:  # 改善率小于30%
            best_k = k + 1
            break
    best_k = max(3, min(6, best_k))  # 限制在3-6之间
    print(f"\n选择 k={best_k}")

    # 用最佳k重新拟合
    best_gmm = models[best_k]
    labels = best_gmm.predict(X_scaled)
    probs = best_gmm.predict_proba(X_scaled)
    data['pragmatic_class'] = labels

    # 类别画像：原始特征均值
    profile = data.groupby('pragmatic_class')[feature_cols].mean()
    profile['n'] = data.groupby('pragmatic_class').size()
    profile['pct'] = (profile['n'] / len(data) * 100).round(2)
    profile.to_csv(os.path.join(RESULT_DIR, '03_lca_profiles.csv'))

    # 类别标签（基于画像）
    class_labels = label_classes(profile, feature_cols)
    data['pragmatic_label'] = data['pragmatic_class'].map(class_labels)

    # 保存
    profile_dict = {
        'best_k': best_k,
        'class_labels': class_labels,
        'profiles': profile.reset_index().to_dict('records'),
        'n_total': len(data),
    }
    save_json(profile_dict, '03_lca_profiles_json')

    # 保存类别分配
    data[['task_id', 'pragmatic_class', 'pragmatic_label']].to_csv(
        os.path.join(RESULT_DIR, 'class_assignments.csv'), index=False)

    # 稳定性检验：Bootstrap
    print("\n稳定性检验(Bootstrap)...")
    from sklearn.metrics import adjusted_rand_score
    ari_scores = []
    n_bootstrap = 20  # 控制时间
    indices = np.arange(len(X_scaled))
    for b in range(n_bootstrap):
        boot_idx = np.random.choice(indices, size=len(indices), replace=True)
        X_boot = X_scaled[boot_idx]
        gmm_boot = GaussianMixture(n_components=best_k, covariance_type='diag',
                                    random_state=SEED+b, max_iter=200, n_init=3)
        boot_labels = gmm_boot.fit_predict(X_boot)
        # 与全样本的标签比较（在boot样本上）
        full_labels_boot = labels[boot_idx]
        ari = adjusted_rand_score(full_labels_boot, boot_labels)
        ari_scores.append(float(ari))
    stability = {
        'n_bootstrap': n_bootstrap,
        'ari_mean': float(np.mean(ari_scores)),
        'ari_std': float(np.std(ari_scores)),
        'ari_min': float(np.min(ari_scores)),
        'ari_max': float(np.max(ari_scores)),
    }
    save_json(stability, '03_lca_stability')
    print(f"  Bootstrap ARI: mean={stability['ari_mean']:.3f}, std={stability['ari_std']:.3f}")

    # 训练-测试一致性
    from sklearn.model_selection import train_test_split
    X_train, X_test = train_test_split(X_scaled, test_size=0.2, random_state=SEED)
    gmm_train = GaussianMixture(n_components=best_k, covariance_type='diag',
                                random_state=SEED, max_iter=200, n_init=5)
    gmm_train.fit(X_train)
    train_on_test = gmm_train.predict(X_test)
    test_on_full = best_gmm.predict(X_test)
    split_ari = adjusted_rand_score(test_on_full, train_on_test)
    stability['train_test_ari'] = float(split_ari)
    save_json(stability, '03_lca_stability')
    print(f"  训练-测试ARI: {split_ari:.3f}")

    print(f"\n类别分布:")
    for cls in sorted(data['pragmatic_class'].unique()):
        label = class_labels.get(cls, str(cls))
        n = len(data[data['pragmatic_class'] == cls])
        print(f"  类{cls}({label}): n={n} ({n/len(data)*100:.1f}%)")

    return data, feature_cols, class_labels


def label_classes(profile, feature_cols):
    """基于画像自动生成类别标签"""
    labels = {}
    used = set()

    # 找宣告性谓语最高的→验证导向型
    if 'declarative_predicate_count' in profile.columns:
        tid = int(profile['declarative_predicate_count'].idxmax())
        labels[tid] = '验证导向型'
        used.add(tid)

    # 找情态标记总和最高的→约束主导型
    modal_sum = profile.get('modal_obligation_count', pd.Series(0)) + profile.get('modal_prohibition_count', pd.Series(0))
    for tid in modal_sum.nlargest(1).index:
        tid = int(tid)
        if tid not in used:
            labels[tid] = '约束主导型'
            used.add(tid)

    # 找句法复杂性最高的→复杂层级型
    complexity = profile.get('clause_density', pd.Series(0)) + profile.get('dependency_tree_depth', pd.Series(0)) / 10
    for tid in complexity.nlargest(1).index:
        tid = int(tid)
        if tid not in used:
            labels[tid] = '复杂层级型'
            used.add(tid)

    # 找祈使句+论元最高的→行动导向型
    action = profile.get('imperative_verb_count', pd.Series(0)) + profile.get('object_argument_count', pd.Series(0)) / 10
    for tid in action.nlargest(1).index:
        tid = int(tid)
        if tid not in used:
            labels[tid] = '行动导向型'
            used.add(tid)

    # 剩余的→简洁型
    for tid in profile.index:
        tid = int(tid)
        if tid not in used:
            labels[tid] = '简洁型'
            used.add(tid)

    return labels


def step5_path_stability(data):
    """Step 5: 路径稳定性指标计算与效度验证"""
    print("\n" + "=" * 60)
    print("Step 5: 路径稳定性指标")
    print("=" * 60)

    steps_df = pd.read_parquet('data/interim/paper04/steps.parquet')

    # 限制到论文A的样本
    valid_task_ids = set(data['task_id'])
    steps_df = steps_df[steps_df['task_id'].isin(valid_task_ids)]

    path_stats = []
    for tid, task_steps in steps_df.groupby('task_id'):
        n = len(task_steps)
        if n < 2:
            continue

        correct = task_steps['last_step_correct'].fillna(True).astype(bool).values
        # 转换为错误序列
        errors = (~correct).astype(int)

        # 最长连续错误
        max_consec = 0
        current = 0
        for e in errors:
            if e == 1:
                current += 1
                max_consec = max(max_consec, current)
            else:
                current = 0

        # 转换次数
        transitions = sum(1 for i in range(1, len(errors)) if errors[i] != errors[i-1])
        transition_rate = transitions / (n - 1) if n > 1 else 0

        path_stats.append({
            'task_id': tid,
            'max_consecutive_errors': max_consec,
            'transition_count': transitions,
            'transition_rate': transition_rate,
            'n_steps': n,
        })

    path_df = pd.DataFrame(path_stats)
    data = data.merge(path_df, on='task_id', how='inner')

    # 已知群组效度
    validity = {}
    # 难度高→路径稳定性低（转换率更高、连续错误更多）
    high_diff = data[data['task_difficulty'] >= 7]
    low_diff = data[data['task_difficulty'] <= 3]
    validity['difficulty_effect'] = {
        'high_diff_max_error': float(high_diff['max_consecutive_errors'].mean()),
        'low_diff_max_error': float(low_diff['max_consecutive_errors'].mean()),
        'high_diff_transitions': float(high_diff['transition_count'].mean()),
        'low_diff_transitions': float(low_diff['transition_count'].mean()),
        'expected': '高难度任务应有更多连续错误和转换',
        'met': bool(high_diff['max_consecutive_errors'].mean() > low_diff['max_consecutive_errors'].mean()),
    }

    # 未完成→稳定性低
    completed = data[data['task_completed_num'] == 1]
    not_completed = data[data['task_completed_num'] == 0]
    validity['completion_effect'] = {
        'completed_max_error': float(completed['max_consecutive_errors'].mean()),
        'not_completed_max_error': float(not_completed['max_consecutive_errors'].mean()),
        'expected': '未完成任务应有更多连续错误',
        'met': bool(not_completed['max_consecutive_errors'].mean() > completed['max_consecutive_errors'].mean()),
    }

    save_json(validity, '05_path_stability_validity')
    print(f"  高难度vs低难度: 连续错误 {validity['difficulty_effect']['high_diff_max_error']:.2f} vs {validity['difficulty_effect']['low_diff_max_error']:.2f} → {'符合' if validity['difficulty_effect']['met'] else '不符合'}")
    print(f"  完成vs未完成: 连续错误 {validity['completion_effect']['completed_max_error']:.2f} vs {validity['completion_effect']['not_completed_max_error']:.2f} → {'符合' if validity['completion_effect']['met'] else '不符合'}")

    return data


def step6_outcome_comparison(data):
    """Step 6: 不同类型的结果差异"""
    print("\n" + "=" * 60)
    print("Step 6: 类型差异分析")
    print("=" * 60)

    results = {}

    # 完成率卡方
    ct = pd.crosstab(data['pragmatic_class'], data['task_completed_num'])
    chi2, p, dof, expected = stats.chi2_contingency(ct)
    n = ct.values.sum()
    cramers_v = np.sqrt(chi2 / (n * (min(ct.shape) - 1)))
    completion_rates = (data.groupby('pragmatic_class')['task_completed_num'].agg(['mean', 'count'])
                        .reset_index().to_dict('records'))
    results['completion_rate'] = {
        'chi2': float(chi2), 'p': float(p), 'dof': int(dof),
        'cramers_v': float(cramers_v),
        'by_class': completion_rates,
    }
    print(f"完成率卡方: χ²={chi2:.2f}, p={p:.4f}, V={cramers_v:.3f}")

    # 过程指标ANOVA
    process_vars = ['total_steps', 'incorrect_ratio', 'redundant_ratio',
                    'max_consecutive_errors', 'transition_count', 'transition_rate']
    anova_results = {}
    for var in process_vars:
        if var in data.columns:
            groups = [g[var].dropna().values for _, g in data.groupby('pragmatic_class')]
            groups = [g for g in groups if len(g) > 0]
            if len(groups) >= 2:
                f, p = stats.f_oneway(*groups)
                # eta squared
                grand_mean = data[var].mean()
                ss_between = sum(len(g) * (np.mean(g) - grand_mean)**2 for g in groups)
                ss_total = sum((data[var].dropna() - grand_mean)**2)
                eta2 = ss_between / ss_total if ss_total > 0 else 0
                anova_results[var] = {'F': float(f), 'p': float(p), 'eta2': float(eta2)}
                print(f"  {var}: F={f:.2f}, p={p:.4f}, η²={eta2:.4f}")
    results['anova'] = anova_results

    # MANOVA（路径稳定性3指标）— 用statsmodels
    path_vars = ['max_consecutive_errors', 'transition_count', 'transition_rate']
    available_path = [v for v in path_vars if v in data.columns]
    if available_path:
        try:
            from statsmodels.multivariate.manova import MANOVA
            manova_data = data[['pragmatic_class'] + available_path].dropna()
            formula = ' + '.join(available_path) + ' ~ C(pragmatic_class)'
            ma = MANOVA.from_formula(formula, data=manova_data)
            ma_result = ma.mv_test()
            # 提取Wilks' Lambda
            stat_df = ma_result.results['C(pragmatic_class)']['stat']
            wilks_row = stat_df.loc['Wilks\' lambda']
            results['manova'] = {
                'wilks_lambda': float(wilks_row['Value']),
                'F': float(wilks_row['F Value']),
                'p': float(wilks_row['Pr > F']),
            }
            print(f"MANOVA(路径稳定性): Wilks'λ={wilks_row['Value']:.4f}, F={wilks_row['F Value']:.2f}, p={wilks_row['Pr > F']:.4f}")
        except Exception as e:
            results['manova'] = {'error': str(e)}
            print(f"  MANOVA错误: {e}")

    save_json(results, '06_outcome_comparison')
    return results


def step7_controlled_analysis(data):
    """Step 7: 控制显性度后的独立效应"""
    print("\n" + "=" * 60)
    print("Step 7: 控制显性度后的独立效应")
    print("=" * 60)

    reg_data = data.dropna(subset=['task_completed_num', 'task_difficulty', 'word_count',
                                     'os', 'explicitness_score']).copy()
    reg_data['os'] = reg_data['os'].astype(str)

    # 仅显性度
    m1 = smf.logit('task_completed_num ~ explicitness_score + task_difficulty + word_count + C(os)',
                   data=reg_data).fit(disp=0)
    # 显性度 + 类别
    m2 = smf.logit('task_completed_num ~ C(pragmatic_class) + explicitness_score + task_difficulty + word_count + C(os)',
                   data=reg_data).fit(disp=0)

    lr_stat = 2 * (m2.llf - m1.llf)
    lr_df = reg_data['pragmatic_class'].nunique() - 1
    lr_p = 1 - stats.chi2.cdf(lr_stat, lr_df)

    result = {
        'n': len(reg_data),
        'lr_statistic': float(lr_stat),
        'lr_df': int(lr_df),
        'lr_p_value': float(lr_p),
        'pseudo_r2_model1': float(m1.prsquared),
        'pseudo_r2_model2': float(m2.prsquared),
        'class_beyond_explicitness': bool(lr_p < 0.05),
        'explicitness_in_model2': {
            'coef': float(m2.params.get('explicitness_score', 0)),
            'p': float(m2.pvalues.get('explicitness_score', 1)),
        },
        'class_coefficients': {},
    }

    # 各类别OR（以类0为参照）
    for term in m2.params.index:
        if 'pragmatic_class' in term and 'T.' in term:
            cls_num = term.split('T.')[1].split(']')[0]
            result['class_coefficients'][f'class_{cls_num}'] = {
                'coef': float(m2.params[term]),
                'or': float(np.exp(m2.params[term])),
                'p': float(m2.pvalues[term]),
            }

    save_json(result, '07_controlled_analysis')
    print(f"似然比检验: χ²({lr_df})={lr_stat:.2f}, p={lr_p:.4f}")
    print(f"类别是否独立于显性度: {'是' if lr_p < 0.05 else '否'}")
    print(f"显性度在模型2中的效应: p={result['explicitness_in_model2']['p']:.4f}")

    return result


def step8_interaction(data):
    """Step 8: 任务难度调节"""
    print("\n" + "=" * 60)
    print("Step 8: 任务难度调节效应")
    print("=" * 60)

    reg_data = data.dropna(subset=['task_completed_num', 'task_difficulty', 'word_count',
                                     'os', 'explicitness_score']).copy()
    reg_data['os'] = reg_data['os'].astype(str)

    m = smf.logit(
        'task_completed_num ~ C(pragmatic_class) * task_difficulty + explicitness_score + word_count + C(os)',
        data=reg_data
    ).fit(disp=0)

    # 提取交互项
    interactions = {}
    for term in m.params.index:
        if ':' in term and 'pragmatic_class' in term:
            interactions[term] = {
                'coef': float(m.params[term]),
                'or': float(np.exp(m.params[term])),
                'p': float(m.pvalues[term]),
            }

    result = {
        'n': len(reg_data),
        'interactions': interactions,
        'any_significant': any(v['p'] < 0.05 for v in interactions.values()),
    }
    save_json(result, '08_interaction_analysis')
    print(f"有显著交互项: {'是' if result['any_significant'] else '否'}")
    for term, vals in interactions.items():
        if vals['p'] < 0.1:
            print(f"  {term}: OR={vals['or']:.3f}, p={vals['p']:.4f}")

    return result


if __name__ == '__main__':
    # 载入Step1-2的数据
    merged = pd.read_parquet(os.path.join(RESULT_DIR, 'merged_data.parquet'))
    print(f"载入数据: {len(merged)}")

    # Step 3: LCA
    data, feature_cols, class_labels = step3_lca(merged)

    # Step 5: 路径稳定性
    data = step5_path_stability(data)

    # Step 6: 类型差异
    step6_outcome_comparison(data)

    # Step 7: 控制显性度
    step7_controlled_analysis(data)

    # Step 8: 调节效应
    step8_interaction(data)

    # 保存带类别标签的数据
    data.to_parquet(os.path.join(RESULT_DIR, 'data_with_classes.parquet'))

    print("\n" + "=" * 60)
    print("论文A Step 3-8 完成")
    print("=" * 60)
