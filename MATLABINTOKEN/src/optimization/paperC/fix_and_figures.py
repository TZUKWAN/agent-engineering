"""
论文C: 修复Step2多项Logistic + 重跑2000次Bootstrap + 生成图表
"""
import os, json
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.formula.api as smf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 150

SEED = 42
np.random.seed(SEED)
RESULT_DIR = "results/optimization/paperC"


def save_json(data, name):
    with open(os.path.join(RESULT_DIR, f"{name}.json"), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def fix_step2_mnlogit():
    """修复Step2: 多项Logistic回归（将类型变量编码为数值）"""
    print("=" * 60)
    print("修复Step2: 多项Logistic回归")
    print("=" * 60)

    data = pd.read_parquet(os.path.join(RESULT_DIR, 'data_with_reasoning_type.parquet'))

    # 将reasoning_type转为数值类别
    data['rt_num'] = pd.Categorical(data['reasoning_type']).codes

    risk_cols = ['risk_initial_state_missing', 'risk_constraint_missing',
                 'risk_verification_missing', 'risk_subtask_no_order', 'risk_object_missing']
    available_risk = [c for c in risk_cols if c in data.columns]
    if 'risk_index' not in data.columns:
        data['risk_index'] = data[available_risk].sum(axis=1)

    valid = data.dropna(subset=['rt_num', 'risk_index', 'task_difficulty', 'word_count']).copy()

    result = {}
    try:
        # 用数值编码的类型变量
        m = smf.mnlogit('rt_num ~ risk_index + task_difficulty + word_count',
                        data=valid).fit(disp=0, maxiter=200)
        result = {
            'n': len(valid),
            'pseudo_r2': float(m.prsquared),
            'aic': float(m.aic),
            'converged': bool(m.mle_retvals['converged']),
            'coefficients': {},
        }
        print(f"  收敛: {result['converged']}")
        print(f"  N={len(valid)}, Pseudo R²={m.prsquared:.4f}, AIC={m.aic:.1f}")

        for term in m.params.index:
            result['coefficients'][str(term)] = {
                'coef': float(m.params[term]),
                'p': float(m.pvalues[term]),
                'or': float(np.exp(m.params[term])),
            }
            if isinstance(term, tuple) and 'risk_index' in str(term[1]):
                print(f"    risk_index→类型{term[0]}: coef={m.params[term]:.4f}, p={m.pvalues[term]:.4f}")
    except Exception as e:
        result = {'error': str(e)}
        print(f"  错误: {e}")

    # 保留原有卡方结果
    old = {}
    try:
        with open(os.path.join(RESULT_DIR, '02_risk_to_reasoning_type.json'), encoding='utf-8') as f:
            old = json.load(f)
    except:
        pass

    if 'chi2_test' in old:
        result['chi2_test'] = old['chi2_test']
    result['reasoning_type_distribution'] = old.get('reasoning_type_distribution',
                                                       data['reasoning_type'].value_counts().to_dict())

    save_json(result, '02_risk_to_reasoning_type')
    print("Step2修复完成。")
    return data


def rerun_mediation_2000():
    """重跑2000次Bootstrap中介分析"""
    print("\n" + "=" * 60)
    print("重跑2000次Bootstrap中介分析")
    print("=" * 60)

    data = pd.read_parquet(os.path.join(RESULT_DIR, 'data_with_reasoning_type.parquet'))
    reg = data[data['alignment_deviation'].notna()].dropna(
        subset=['incorrect_ratio', 'redundant_ratio', 'task_difficulty', 'task_completed_num']).copy()
    reg['execution_error'] = reg['incorrect_ratio'].fillna(0) + reg['redundant_ratio'].fillna(0)

    boot_data = reg[['task_completed_num', 'risk_index', 'alignment_deviation',
                      'execution_error', 'task_difficulty']].dropna()

    n_boot = 2000
    indirect, direct = [], []
    indices = np.arange(len(boot_data))
    print(f"  Bootstrap {n_boot}次...")

    for b in range(n_boot):
        if b % 500 == 0:
            print(f"    进度: {b}/{n_boot}")
        bi = np.random.choice(indices, size=len(indices), replace=True)
        bd = boot_data.iloc[bi]
        try:
            ma = smf.ols('alignment_deviation ~ risk_index', data=bd).fit(disp=0)
            a = ma.params['risk_index']
            mb = smf.ols('execution_error ~ alignment_deviation + risk_index', data=bd).fit(disp=0)
            b_coef = mb.params['alignment_deviation']
            mc = smf.logit('task_completed_num ~ execution_error + alignment_deviation + risk_index',
                          data=bd).fit(disp=0, maxiter=50)
            c = mc.params['execution_error']
            indirect.append(a * b_coef * c)
            direct.append(mc.params['risk_index'])
        except:
            continue

    indirect = np.array(indirect)
    direct = np.array(direct)
    ci_lo, ci_hi = float(np.percentile(indirect, 2.5)), float(np.percentile(indirect, 97.5))

    m_total = smf.logit('task_completed_num ~ risk_index + task_difficulty',
                        data=boot_data).fit(disp=0, maxiter=100)
    result = {
        'n_boot': len(indirect),
        'indirect_mean': float(np.mean(indirect)),
        'indirect_median': float(np.median(indirect)),
        'indirect_se': float(np.std(indirect)),
        'indirect_ci_low': ci_lo,
        'indirect_ci_high': ci_hi,
        'indirect_significant': not (ci_lo <= 0 <= ci_hi),
        'direct_mean': float(np.mean(direct)),
        'direct_ci_low': float(np.percentile(direct, 2.5)),
        'direct_ci_high': float(np.percentile(direct, 97.5)),
        'total_coef': float(m_total.params.get('risk_index', 0)),
        'total_p': float(m_total.pvalues.get('risk_index', 1)),
    }
    save_json(result, '06_mediation_analysis')
    print(f"\n  N_boot={result['n_boot']}")
    print(f"  间接效应: mean={result['indirect_mean']:.6f}")
    print(f"  95% CI: [{ci_lo:.6f}, {ci_hi:.6f}]")
    print(f"  间接显著: {'是' if result['indirect_significant'] else '否'}")
    print(f"  总效应: {result['total_coef']:.4f} (p={result['total_p']:.4f})")


def generate_figures():
    """生成论文C 5张图"""
    print("\n" + "=" * 60)
    print("生成论文C图表")
    print("=" * 60)

    def load_json(name):
        with open(os.path.join(RESULT_DIR, f"{name}.json"), encoding='utf-8') as f:
            return json.load(f)

    # fig1: 对齐度分布
    print("  fig1...")
    data = pd.read_parquet(os.path.join(RESULT_DIR, 'data_with_reasoning_type.parquet'))
    valid = data[data['alignment_deviation'].notna()]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].hist(valid['alignment_deviation'], bins=30, color='#4472C4', edgecolor='white')
    axes[0].set_title(f'对齐偏差分布 (N={len(valid)})')
    axes[0].set_xlabel('对齐偏差 (1-平均覆盖率)')
    axes[0].set_ylabel('频数')

    # 覆盖率分维度
    coverages = ['constraint_coverage', 'verification_coverage', 'decomposition_coverage']
    coverages = [c for c in coverages if c in valid.columns]
    means = [valid[c].dropna().mean() for c in coverages]
    axes[1].bar(['约束', '验证', '分解'][:len(coverages)], means, color=['#ED7D31', '#70AD47', '#FFC000'][:len(coverages)])
    axes[1].set_title('各维度平均覆盖率')
    axes[1].set_ylabel('覆盖率')
    axes[1].set_ylim(0, 1)

    plt.tight_layout()
    plt.savefig(os.path.join(RESULT_DIR, 'fig1_alignment_distribution.png'), bbox_inches='tight')
    plt.close()

    # fig2: 单项风险效应
    print("  fig2...")
    r3 = load_json('03_risk_to_alignment')
    single = r3.get('single_risk_effects', {})

    fig, ax = plt.subplots(figsize=(10, 5))
    names = list(single.keys())
    coefs = [single[n]['coef'] for n in names]
    pvals = [single[n]['p'] for n in names]
    colors = ['#4472C4' if p < 0.05 else '#A5A5A5' for p in pvals]

    ax.barh(names, coefs, color=colors)
    ax.axvline(0, color='red', linestyle='--', alpha=0.5)
    ax.set_xlabel('系数（→对齐偏差）')
    ax.set_title('单项提示风险对对齐偏差的效应')
    plt.tight_layout()
    plt.savefig(os.path.join(RESULT_DIR, 'fig2_single_risk_effects.png'), bbox_inches='tight')
    plt.close()

    # fig3: 风险与推理链类型热图
    print("  fig3...")
    r2 = load_json('02_risk_to_reasoning_type')
    chi2_data = r2.get('chi2_test', {})
    ct = chi2_data.get('crosstab', {})

    if ct:
        import seaborn as sns
        df_ct = pd.DataFrame(ct)
        if not df_ct.empty:
            fig, ax = plt.subplots(figsize=(8, 5))
            sns.heatmap(df_ct, annot=True, fmt='.0f', cmap='YlOrRd', ax=ax)
            ax.set_title(f'风险×推理链类型列联表 (χ²={chi2_data.get("chi2",0):.2f}, p={chi2_data.get("p",0):.4f})')
            plt.tight_layout()
            plt.savefig(os.path.join(RESULT_DIR, 'fig3_risk_reasoning_heatmap.png'), bbox_inches='tight')
            plt.close()

    # fig4: 执行错误→完成率
    print("  fig4...")
    r5 = load_json('05_errors_to_completion')
    coeffs = r5.get('coefficients', {})

    fig, ax = plt.subplots(figsize=(8, 5))
    terms = ['alignment_deviation', 'execution_error', 'risk_index']
    ors = [coeffs.get(t, {}).get('or', 0) for t in terms]
    pvals = [coeffs.get(t, {}).get('p', 1) for t in terms]
    colors = ['#4472C4' if p < 0.05 else '#A5A5A5' for p in pvals]

    ax.barh(terms, ors, color=colors)
    ax.axvline(1, color='red', linestyle='--', alpha=0.5)
    ax.set_xlabel('OR')
    ax.set_title(f'对齐偏差/执行错误/风险指数→任务完成 (N={r5.get("n",0)})')
    plt.tight_layout()
    plt.savefig(os.path.join(RESULT_DIR, 'fig4_or_forest.png'), bbox_inches='tight')
    plt.close()

    # fig5: 中介路径图
    print("  fig5...")
    r6 = load_json('06_mediation_analysis')

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.axis('off')

    # 路径系数
    indirect = r6.get('indirect_mean', 0)
    direct = r6.get('direct_mean', 0)
    total = r6.get('total_coef', 0)

    # 画框
    boxes = [('提示风险', 0.1, 0.5), ('对齐偏差', 0.4, 0.8),
             ('执行错误', 0.7, 0.8), ('任务完成', 0.9, 0.5)]
    for name, x, y in boxes:
        ax.text(x, y, name, ha='center', va='center', fontsize=12,
                bbox=dict(boxstyle='round', facecolor='#4472C4', alpha=0.3))

    # 箭头
    ax.annotate('', xy=(0.4, 0.78), xytext=(0.15, 0.55),
                arrowprops=dict(arrowstyle='->', color='black'))
    ax.annotate('', xy=(0.7, 0.78), xytext=(0.42, 0.78),
                arrowprops=dict(arrowstyle='->', color='black'))
    ax.annotate('', xy=(0.88, 0.55), xytext=(0.72, 0.78),
                arrowprops=dict(arrowstyle='->', color='black'))
    ax.annotate('', xy=(0.88, 0.5), xytext=(0.15, 0.5),
                arrowprops=dict(arrowstyle='->', color='red', linestyle='--'))

    ax.text(0.55, 0.85, f'间接效应={indirect:.6f}\n95% CI [{r6.get("indirect_ci_low",0):.6f}, {r6.get("indirect_ci_high",0):.6f}]',
            ha='center', fontsize=9, transform=ax.transAxes)
    ax.text(0.5, 0.35, f'直接效应={direct:.4f}\n总效应={total:.4f} (p={r6.get("total_p",0):.4f})',
            ha='center', fontsize=9, color='red', transform=ax.transAxes)

    ax.set_title(f'提示风险→对齐偏差→执行错误→任务完成 路径\n(Bootstrap N={r6.get("n_boot",0)})')
    plt.tight_layout()
    plt.savefig(os.path.join(RESULT_DIR, 'fig5_pathway_diagram.png'), bbox_inches='tight')
    plt.close()

    print(f"\n论文C 5张图完成，保存在 {RESULT_DIR}")


if __name__ == '__main__':
    fix_step2_mnlogit()
    rerun_mediation_2000()
    generate_figures()
    print("\n" + "=" * 60)
    print("论文C修复+重跑+图表完成")
    print("=" * 60)
