"""论文A: 生成全部PNG图表"""
import os, json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 150

RESULT_DIR = "results/optimization/paperA"


def load_json(name):
    with open(os.path.join(RESULT_DIR, f"{name}.json"), encoding='utf-8') as f:
        return json.load(f)


def fig1_validity_heatmap():
    """fig1: 效度相关矩阵热图"""
    corr = pd.read_csv(os.path.join(RESULT_DIR, '02_validity_correlation_matrix.csv'), index_col=0)

    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(corr, annot=True, fmt='.2f', cmap='RdBu_r', center=0,
                square=True, ax=ax, cbar_kws={'label': 'Pearson r'})
    ax.set_title('句法特征间相关矩阵')
    plt.tight_layout()
    plt.savefig(os.path.join(RESULT_DIR, 'fig1_validity_heatmap.png'), bbox_inches='tight')
    plt.close()
    print("  fig1 完成")


def fig2_bic_elbow():
    """fig2: BIC肘部法则"""
    data = load_json('03_lca_model_selection')
    sel = data['selection']

    fig, ax = plt.subplots(figsize=(8, 5))
    ks = [s['k'] for s in sel]
    bics = [s['bic'] for s in sel]
    ax.plot(ks, bics, 'o-', color='#4472C4', linewidth=2)
    ax.set_xlabel('潜在类别数 k')
    ax.set_ylabel('BIC')
    ax.set_title('LCA模型选择：BIC随k变化')
    ax.axvline(5, color='red', linestyle='--', alpha=0.5, label='k=5')
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(RESULT_DIR, 'fig2_BIC肘部法则.png'), bbox_inches='tight')
    plt.close()
    print("  fig2 完成")


def fig3_profile_heatmap():
    """fig3: 类别特征热图"""
    profile = pd.read_csv(os.path.join(RESULT_DIR, '03_lca_profiles.csv'), index_col=0)

    feature_cols = [c for c in profile.columns if c not in ['n', 'pct']]
    profile_features = profile[feature_cols]

    fig, ax = plt.subplots(figsize=(12, 5))
    sns.heatmap(profile_features.T, annot=True, fmt='.2f', cmap='YlOrRd',
                ax=ax, cbar_kws={'label': '特征均值'})
    ax.set_xlabel('语用类别')
    ax.set_ylabel('句法特征')
    ax.set_title('五类别语用特征条件响应概率热图')
    plt.tight_layout()
    plt.savefig(os.path.join(RESULT_DIR, 'fig3_类别特征热图.png'), bbox_inches='tight')
    plt.close()
    print("  fig3 完成")


def fig4_class_distribution():
    """fig4: 类别规模分布"""
    data = pd.read_parquet(os.path.join(RESULT_DIR, 'data_with_classes.parquet'))
    labels_map = load_json('03_lca_profiles_json').get('class_labels', {})

    counts = data['pragmatic_class'].value_counts().sort_index()

    fig, ax = plt.subplots(figsize=(8, 5))
    labels = [labels_map.get(str(c), f'类{c}') for c in counts.index]
    ax.bar(labels, counts.values, color=['#4472C4', '#ED7D31', '#A5A5A5', '#FFC000', '#70AD47', '#5B9BD5'][:len(counts)])
    ax.set_ylabel('任务数')
    ax.set_title('语用类别样本分布')
    for i, v in enumerate(counts.values):
        ax.text(i, v + 50, f'{v}\n({v/len(data)*100:.1f}%)', ha='center')
    plt.xticks(rotation=15)
    plt.tight_layout()
    plt.savefig(os.path.join(RESULT_DIR, 'fig4_类别规模分布.png'), bbox_inches='tight')
    plt.close()
    print("  fig4 完成")


def fig5_completion_rate():
    """fig5: 各类别完成率"""
    data = load_json('06_outcome_comparison')
    cr = data['completion_rate']
    by_class = cr['by_class']

    fig, ax = plt.subplots(figsize=(8, 5))
    classes = sorted([c['pragmatic_class'] for c in by_class])
    rates = [next(c['mean'] for c in by_class if c['pragmatic_class'] == cls) for cls in classes]
    ns = [next(c['count'] for c in by_class if c['pragmatic_class'] == cls) for cls in classes]

    ax.bar([f'类{c}' for c in classes], rates,
           color=['#4472C4', '#ED7D31', '#A5A5A5', '#FFC000', '#70AD47', '#5B9BD5'][:len(classes)])
    ax.set_ylabel('完成率')
    ax.set_title(f'各类别任务完成率 (χ²={cr["chi2"]:.2f}, p={cr["p"]:.4f})')
    ax.set_ylim(0, 1)
    for i, (r, n) in enumerate(zip(rates, ns)):
        ax.text(i, r + 0.01, f'{r:.3f}\n(n={n})', ha='center')
    plt.tight_layout()
    plt.savefig(os.path.join(RESULT_DIR, 'fig5_完成率比较.png'), bbox_inches='tight')
    plt.close()
    print("  fig5 完成")


def fig6_path_stability():
    """fig6: 过程指标箱线图"""
    data = pd.read_parquet(os.path.join(RESULT_DIR, 'data_with_classes.parquet'))

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    metrics = [('max_consecutive_errors', '最长连续错误步数'),
               ('transition_count', '转换次数'),
               ('transition_rate', '转换率')]

    for idx, (col, title) in enumerate(metrics):
        if col in data.columns:
            valid = data[data[col].notna()]
            sns.boxplot(x='pragmatic_class', y=col, data=valid, ax=axes[idx])
            axes[idx].set_title(title)
            axes[idx].set_xlabel('语用类别')

    plt.suptitle('各类别路径稳定性指标', y=1.02)
    plt.tight_layout()
    plt.savefig(os.path.join(RESULT_DIR, 'fig6_路径稳定性指标.png'), bbox_inches='tight')
    plt.close()
    print("  fig6 完成")


def fig7_robustness_platform():
    """fig7: 分平台稳健性"""
    data = load_json('09_robustness_check')
    platform = data.get('cross_platform', {})

    fig, ax = plt.subplots(figsize=(8, 5))
    platforms = list(platform.keys())
    aris = [platform[p]['ari_vs_full'] for p in platforms]
    ns = [platform[p]['n'] for p in platforms]

    ax.bar(platforms, aris, color=['#4472C4', '#ED7D31'][:len(platforms)])
    ax.set_ylabel('ARI vs 全样本')
    ax.set_title('分平台LCA稳健性')
    ax.set_ylim(0, 1)
    for i, (a, n) in enumerate(zip(aris, ns)):
        ax.text(i, a + 0.02, f'ARI={a:.3f}\n(N={n})', ha='center')
    plt.tight_layout()
    plt.savefig(os.path.join(RESULT_DIR, 'fig7_分平台稳健性.png'), bbox_inches='tight')
    plt.close()
    print("  fig7 完成")


def fig8_feature_comparison():
    """fig8: 特征集对比"""
    data = load_json('09_robustness_check')
    fs = data.get('feature_set_comparison', {})

    fig, ax = plt.subplots(figsize=(8, 5))
    sets = list(fs.keys())
    aris = [fs[s]['ari_vs_syntactic'] for s in sets]

    ax.bar(sets, aris, color=['#4472C4', '#ED7D31', '#A5A5A5'][:len(sets)])
    ax.set_ylabel('ARI vs 句法特征')
    ax.set_title('不同特征集的LCA结构对比')
    for i, a in enumerate(aris):
        ax.text(i, a + 0.01, f'{a:.3f}', ha='center')
    plt.tight_layout()
    plt.savefig(os.path.join(RESULT_DIR, 'fig8_特征集对比.png'), bbox_inches='tight')
    plt.close()
    print("  fig8 完成")


if __name__ == '__main__':
    print("生成论文A图表...")
    fig1_validity_heatmap()
    fig2_bic_elbow()
    fig3_profile_heatmap()
    fig4_class_distribution()
    fig5_completion_rate()
    fig6_path_stability()
    fig7_robustness_platform()
    fig8_feature_comparison()
    print(f"\n论文A 8张图完成，保存在 {RESULT_DIR}")
