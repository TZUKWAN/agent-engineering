"""论文B: 生成全部PNG图表"""
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

RESULT_DIR = "results/optimization/paperB"


def load_json(name):
    with open(os.path.join(RESULT_DIR, f"{name}.json"), encoding='utf-8') as f:
        return json.load(f)


def fig1_verification_distribution():
    """fig1: 验证类型分布"""
    data = load_json('01_verification_features')
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # 左：有/无验证标准
    vc = data['has_completion_criteria']
    labels = ['无验证标准', '有验证标准']
    sizes = [vc['n_no'], vc['n_yes']]
    axes[0].bar(labels, sizes, color=['#5B9BD5', '#ED7D31'])
    axes[0].set_title(f'验证标准分布 (N={sizes[0]+sizes[1]})')
    axes[0].set_ylabel('任务数')
    for i, v in enumerate(sizes):
        axes[0].text(i, v + 100, f'{v}\n({v/sum(sizes)*100:.1f}%)', ha='center')

    # 右：验证密度分布
    df = pd.read_parquet(os.path.join(RESULT_DIR, 'prepared_data.parquet'))
    df = df.drop_duplicates(subset=['task_id'])
    verif = df[df['verification_density'] > 0]['verification_density']
    axes[1].hist(verif, bins=50, color='#70AD47', edgecolor='white')
    axes[1].set_title(f'验证密度分布 (N={len(verif)}, 有验证词的任务)')
    axes[1].set_xlabel('验证密度 (验证词数/总词数×100)')
    axes[1].set_ylabel('频数')

    plt.tight_layout()
    plt.savefig(os.path.join(RESULT_DIR, 'fig1_验证类型分布.png'), bbox_inches='tight')
    plt.close()
    print("  fig1 完成")


def fig2_constraint_distribution():
    """fig2: 约束类型分布"""
    data = load_json('02_constraint_features')
    fig, ax = plt.subplots(figsize=(8, 5))

    type_dist = data['constraint_type_distribution']
    # 排除None
    filtered = {k: v for k, v in type_dist.items() if k != 'None'}
    labels_map = {'C1_Prohibitive': '禁止型', 'C2_Preservative': '保留型',
                  'C3_Obligative': '要求型', 'C4_Restrictive': '限制型', 'C5_Mixed': '混合型'}
    labels = [labels_map.get(k, k) for k in filtered.keys()]
    values = list(filtered.values())

    ax.bar(labels, values, color=['#FFC000', '#4472C4', '#ED7D31', '#70AD47', '#A5A5A5'])
    ax.set_title('约束类型分布（有约束词的任务）')
    ax.set_ylabel('任务数')
    for i, v in enumerate(values):
        ax.text(i, v + 10, str(v), ha='center')

    plt.tight_layout()
    plt.savefig(os.path.join(RESULT_DIR, 'fig2_约束类型分布.png'), bbox_inches='tight')
    plt.close()
    print("  fig2 完成")


def fig3_forest_logistic():
    """fig3: Logistic回归森林图"""
    data = load_json('03_logistic_verification')
    rows = [r for r in data['rows'] if r['term'] != 'Intercept']

    fig, ax = plt.subplots(figsize=(8, 4))
    terms = [r['term'] for r in rows]
    ors = [r['or'] for r in rows]
    ci_lows = [r['ci_low_or'] for r in rows]
    ci_highs = [r['ci_high_or'] for r in rows]

    y_pos = range(len(terms))
    ax.errorbar(ors, y_pos, xerr=[ [o - cl for o, cl in zip(ors, ci_lows)],
                                     [ch - o for o, ch in zip(ors, ci_highs)]],
                fmt='o', capsize=3, color='#4472C4')
    ax.axvline(1, color='red', linestyle='--', alpha=0.5)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(terms)
    ax.set_xlabel('OR (95% CI)')
    ax.set_title(f'验证标准Logistic回归森林图 (N={data["n_obs"]})')

    plt.tight_layout()
    plt.savefig(os.path.join(RESULT_DIR, 'fig3_逻辑回归系数森林图.png'), bbox_inches='tight')
    plt.close()
    print("  fig3 完成")


def fig4_forest_nb():
    """fig4: 负二项回归森林图"""
    data = load_json('04_negative_binomial_verification')
    rows = [r for r in data['rows'] if r['term'] != 'Intercept']

    fig, ax = plt.subplots(figsize=(8, 4))
    terms = [r['term'] for r in rows]
    irrs = [r['irr'] for r in rows]
    ci_lows = [r['ci_low_irr'] for r in rows]
    ci_highs = [r['ci_high_irr'] for r in rows]

    y_pos = range(len(terms))
    ax.errorbar(irrs, y_pos, xerr=[[i - cl for i, cl in zip(irrs, ci_lows)],
                                     [ch - i for i, ch in zip(irrs, ci_highs)]],
                fmt='s', capsize=3, color='#ED7D31')
    ax.axvline(1, color='red', linestyle='--', alpha=0.5)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(terms)
    ax.set_xlabel('IRR (95% CI)')
    ax.set_title(f'验证标准负二项回归森林图 (N={data["n_obs"]})')

    plt.tight_layout()
    plt.savefig(os.path.join(RESULT_DIR, 'fig4_负二项回归系数森林图.png'), bbox_inches='tight')
    plt.close()
    print("  fig4 完成")


def fig5_terminal_comparison():
    """fig5: 终止阶段指标对比"""
    data = load_json('05_terminal_phase_comparison')
    groups = data['groups']

    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    metrics = [('terminal_redundant_ratio_mean', '终止冗余比'),
               ('terminal_error_ratio_mean', '终止错误比'),
               ('short_trajectory_rate', '异常短轨迹率')]

    labels = ['无验证标准', '有验证标准']
    colors = ['#5B9BD5', '#ED7D31']

    for idx, (key, title) in enumerate(metrics):
        vals = [groups['no_criteria'].get(key, 0), groups['has_criteria'].get(key, 0)]
        axes[idx].bar(labels, vals, color=colors)
        axes[idx].set_title(title)
        axes[idx].set_ylabel('比例')
        for i, v in enumerate(vals):
            axes[idx].text(i, v + 0.002, f'{v:.4f}', ha='center')

    plt.suptitle('终止阶段指标：有/无验证标准对比', y=1.02)
    plt.tight_layout()
    plt.savefig(os.path.join(RESULT_DIR, 'fig5_终止阶段指标对比.png'), bbox_inches='tight')
    plt.close()
    print("  fig5 完成")


def fig6_marginal_contribution():
    """fig6: 边际贡献对比"""
    data = load_json('14_marginal_contribution')

    fig, ax = plt.subplots(figsize=(8, 5))
    models = ['验证单独', '约束单独', '验证(控制约束后)', '约束(控制验证后)']
    keys = ['lr_verification_alone', 'lr_constraint_alone',
            'lr_verification_beyond_constraint', 'lr_constraint_beyond_verification']
    lr_stats = [data[k]['lr_stat'] for k in keys]
    p_vals = [data[k]['p_value'] for k in keys]

    colors = ['#4472C4' if p < 0.05 else '#A5A5A5' for p in p_vals]
    ax.barh(models, lr_stats, color=colors)
    ax.set_xlabel('似然比统计量')
    ax.set_title('验证 vs 约束的边际贡献（似然比检验）')
    for i, (lr, p) in enumerate(zip(lr_stats, p_vals)):
        sig = '***' if p < 0.001 else ('**' if p < 0.01 else ('*' if p < 0.05 else 'ns'))
        ax.text(lr + 0.3, i, f'{lr:.2f} ({sig})', va='center')

    plt.tight_layout()
    plt.savefig(os.path.join(RESULT_DIR, 'fig6_边际贡献对比.png'), bbox_inches='tight')
    plt.close()
    print("  fig6 完成")


if __name__ == '__main__':
    print("生成论文B图表...")
    fig1_verification_distribution()
    fig2_constraint_distribution()
    fig3_forest_logistic()
    fig4_forest_nb()
    fig5_terminal_comparison()
    fig6_marginal_contribution()
    print(f"\n论文B 6张图完成，保存在 {RESULT_DIR}")
