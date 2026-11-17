"""
论文C Step 2/7/8: 推理链类型融入 + 调节效应 + 稳健性
- Step 2: 提示风险→推理链类型（卡方+多项Logistic）
- Step 7: 推理链类型调节对齐度→执行错误的路径
- Step 8: 稳健性检验（替代对齐度定义、分平台、排除异常值、KHB方法）
"""
import os, json
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.formula.api as smf

SEED = 42
np.random.seed(SEED)
RESULT_DIR = "results/optimization/paperC"


def save_json(data, name):
    with open(os.path.join(RESULT_DIR, f"{name}.json"), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def step2_reasoning_type_integration():
    """Step 2: 提示风险→推理链类型（卡方+多项Logistic）"""
    print("=" * 60)
    print("Step 2: 推理链类型融入分析")
    print("=" * 60)

    # 加载论文C的对齐度数据
    df = pd.read_parquet(os.path.join(RESULT_DIR, '01_alignment_features.parquet'))

    # 加载论文4的推理链类型标签
    reasoning_typed = pd.read_parquet('data/interim/paper04/reasoning_features_typed.parquet')
    if 'reasoning_type' in reasoning_typed.columns:
        type_col = 'reasoning_type'
    elif 'reasoning_type_label' in reasoning_typed.columns:
        type_col = 'reasoning_type_label'
    else:
        print("  找不到reasoning_type列，列名:", reasoning_typed.columns.tolist())
        return None

    # 合并
    merged = df.merge(reasoning_typed[['task_id', type_col]], on='task_id', how='inner')
    merged['reasoning_type'] = merged[type_col].astype(str)
    print(f"合并后样本: {len(merged)}")
    print(f"推理链类型分布: {merged['reasoning_type'].value_counts().to_dict()}")

    # 构建提示风险
    risk_cols = ['risk_initial_state_missing', 'risk_constraint_missing',
                 'risk_verification_missing', 'risk_subtask_no_order', 'risk_object_missing']
    for rc in risk_cols:
        if rc not in merged.columns:
            # 重新构建
            base_col = rc.replace('risk_', '').replace('_missing', '')
            if base_col == 'verification':
                base_col = 'has_completion_criteria'
            elif base_col == 'subtask_no_order':
                merged[rc] = ((merged['has_multiple_subtasks'] == 1) & (merged['has_operation_order'] == 0)).astype(int)
                continue
            elif base_col == 'object':
                base_col = 'has_operation_object'
            if base_col in merged.columns:
                merged[rc] = (merged[base_col] == 0).astype(int)

    merged['risk_index'] = merged[[rc for rc in risk_cols if rc in merged.columns]].sum(axis=1)
    merged['risk_high'] = (merged['risk_index'] >= merged['risk_index'].median()).astype(int)

    # 卡方检验：风险高/低 × 推理链类型
    print("\n-- 卡方检验 --")
    ct = pd.crosstab(merged['risk_high'], merged['reasoning_type'])
    chi2, p, dof, expected = stats.chi2_contingency(ct)
    n = ct.values.sum()
    cramers_v = np.sqrt(chi2 / (n * (min(ct.shape) - 1)))

    chi2_result = {
        'n': int(n),
        'chi2': float(chi2),
        'p': float(p),
        'dof': int(dof),
        'cramers_v': float(cramers_v),
        'crosstab': ct.to_dict(),
    }
    print(f"  χ²={chi2:.2f}, p={p:.4f}, V={cramers_v:.3f}")

    # 多项Logistic回归
    print("\n-- 多项Logistic回归 --")
    mnlogit_result = {}
    try:
        # 用风险指数预测推理链类型
        valid = merged.dropna(subset=['risk_index', 'task_difficulty', 'word_count']).copy()
        valid['os'] = valid['os'].astype(str)
        m = smf.mnlogit('reasoning_type ~ risk_index + task_difficulty + word_count',
                        data=valid).fit(disp=0, maxiter=100)
        mnlogit_result = {
            'n': len(valid),
            'pseudo_r2': float(m.prsquared),
            'aic': float(m.aic),
            'coefficients': {},
        }
        for term in m.params.index:
            mnlogit_result['coefficients'][term] = {
                'coef': float(m.params[term]),
                'p': float(m.pvalues[term]),
                'or': float(np.exp(m.params[term])),
            }
        print(f"  N={len(valid)}, Pseudo R²={m.prsquared:.4f}")
        # 打印risk_index的系数
        for term in m.params.index:
            if 'risk_index' in term[1]:
                print(f"    risk_index→{term[0]}: coef={m.params[term]:.4f}, p={m.pvalues[term]:.4f}")
    except Exception as e:
        mnlogit_result = {'error': str(e)}
        print(f"  多项Logistic错误: {e}")

    result = {
        'chi2_test': chi2_result,
        'mnlogit': mnlogit_result,
        'reasoning_type_distribution': merged['reasoning_type'].value_counts().to_dict(),
    }
    save_json(result, '02_risk_to_reasoning_type')
    print("\nStep 2完成。")

    # 保存带推理链类型的数据供Step7使用
    merged.to_parquet(os.path.join(RESULT_DIR, 'data_with_reasoning_type.parquet'), index=False)
    return merged


def step7_moderation_by_reasoning_type(data):
    """Step 7: 推理链类型调节对齐度→执行错误的路径"""
    print("\n" + "=" * 60)
    print("Step 7: 推理链类型的调节效应")
    print("=" * 60)

    # 确保有执行错误指标
    if 'execution_error' not in data.columns:
        data['execution_error'] = data['incorrect_ratio'].fillna(0) + data['redundant_ratio'].fillna(0)

    reg = data[data['alignment_deviation'].notna()].dropna(
        subset=['execution_error', 'task_difficulty']).copy()

    # 交互模型
    result = {}
    try:
        m = smf.ols(
            'execution_error ~ alignment_deviation * C(reasoning_type) + risk_index + task_difficulty',
            data=reg
        ).fit(disp=0)
        result = {
            'n': len(reg),
            'r_squared': float(m.rsquared),
            'interactions': {},
        }
        for term in m.params.index:
            if ':' in term and 'alignment_deviation' in term:
                result['interactions'][term] = {
                    'coef': float(m.params[term]),
                    'p': float(m.pvalues[term]),
                }
                if m.pvalues[term] < 0.1:
                    print(f"  {term}: β={m.params[term]:.4f}, p={m.pvalues[term]:.4f}")

        result['any_significant_interaction'] = any(v['p'] < 0.05 for v in result['interactions'].values())
        print(f"  有显著交互: {'是' if result['any_significant_interaction'] else '否'}")

        # 分类型看对齐度→执行错误的主效应
        result['by_type'] = {}
        for rtype in reg['reasoning_type'].unique():
            sub = reg[reg['reasoning_type'] == rtype]
            if len(sub) > 50:
                try:
                    ms = smf.ols('execution_error ~ alignment_deviation + risk_index + task_difficulty',
                                 data=sub).fit(disp=0)
                    result['by_type'][str(rtype)] = {
                        'n': len(sub),
                        'alignment_coef': float(ms.params.get('alignment_deviation', 0)),
                        'alignment_p': float(ms.pvalues.get('alignment_deviation', 1)),
                    }
                    print(f"  类型{rtype}(N={len(sub)}): β={ms.params.get('alignment_deviation', 0):.4f}, p={ms.pvalues.get('alignment_deviation', 1):.4f}")
                except:
                    pass
    except Exception as e:
        result = {'error': str(e)}
        print(f"  错误: {e}")

    save_json(result, '07_moderation_by_reasoning_type')
    print("Step 7完成。")


def step8_robustness():
    """Step 8: 稳健性检验"""
    print("\n" + "=" * 60)
    print("Step 8: 稳健性检验")
    print("=" * 60)

    data = pd.read_parquet(os.path.join(RESULT_DIR, 'data_with_reasoning_type.parquet'))
    results = {}

    # 1. 替代对齐度定义：用二元对齐（偏差=0 vs >0）
    print("\n-- 1. 替代对齐度定义（二元）--")
    valid = data[data['alignment_deviation'].notna()].dropna(
        subset=['task_completed_num', 'task_difficulty']).copy()
    valid['alignment_binary'] = (valid['alignment_deviation'] > valid['alignment_deviation'].median()).astype(int)

    try:
        m = smf.logit('task_completed_num ~ alignment_binary + risk_index + task_difficulty',
                      data=valid).fit(disp=0, maxiter=100)
        results['binary_alignment'] = {
            'n': len(valid),
            'alignment_binary_or': float(np.exp(m.params.get('alignment_binary', 0))),
            'alignment_binary_p': float(m.pvalues.get('alignment_binary', 1)),
            'risk_index_or': float(np.exp(m.params.get('risk_index', 0))),
            'risk_index_p': float(m.pvalues.get('risk_index', 1)),
        }
        print(f"  二元对齐: OR={results['binary_alignment']['alignment_binary_or']:.3f}, p={results['binary_alignment']['alignment_binary_p']:.4f}")
    except Exception as e:
        results['binary_alignment'] = {'error': str(e)}

    # 2. 分平台
    print("\n-- 2. 分平台 --")
    for platform in ['win_mac', 'ubuntu']:
        sub = valid[valid['os'] == platform]
        if len(sub) > 100:
            try:
                m = smf.logit('task_completed_num ~ alignment_deviation + risk_index + task_difficulty',
                              data=sub).fit(disp=0, maxiter=100)
                results[f'{platform}_alignment'] = {
                    'n': len(sub),
                    'alignment_coef': float(m.params.get('alignment_deviation', 0)),
                    'alignment_p': float(m.pvalues.get('alignment_deviation', 1)),
                    'risk_index_or': float(np.exp(m.params.get('risk_index', 0))),
                    'risk_index_p': float(m.pvalues.get('risk_index', 1)),
                }
                print(f"  {platform}: N={len(sub)}, alignment p={m.pvalues.get('alignment_deviation', 1):.4f}, risk OR={np.exp(m.params.get('risk_index', 0)):.3f}")
            except Exception as e:
                results[f'{platform}_alignment'] = {'error': str(e)}

    # 3. 排除异常值（步数>100）
    print("\n-- 3. 排除异常值（步数>100）--")
    if 'total_steps' in valid.columns:
        no_outlier = valid[valid['total_steps'] <= 100]
        try:
            m = smf.logit('task_completed_num ~ alignment_deviation + risk_index + task_difficulty',
                          data=no_outlier).fit(disp=0, maxiter=100)
            results['no_outlier'] = {
                'n': len(no_outlier),
                'alignment_coef': float(m.params.get('alignment_deviation', 0)),
                'alignment_p': float(m.pvalues.get('alignment_deviation', 1)),
                'risk_index_or': float(np.exp(m.params.get('risk_index', 0))),
                'risk_index_p': float(m.pvalues.get('risk_index', 1)),
            }
            print(f"  排除后: N={len(no_outlier)}, risk OR={np.exp(m.params.get('risk_index', 0)):.3f}, p={m.pvalues.get('risk_index', 1):.4f}")
        except Exception as e:
            results['no_outlier'] = {'error': str(e)}

    # 4. 风险指数的总效应在不同子样本中是否稳健
    print("\n-- 4. 风险指数总效应的稳健性 --")
    for subset_name, subset in [('full', valid),
                                 ('high_difficulty', valid[valid['task_difficulty'] >= 6]),
                                 ('low_difficulty', valid[valid['task_difficulty'] <= 3])]:
        if len(subset) > 100:
            try:
                m = smf.logit('task_completed_num ~ risk_index + task_difficulty',
                              data=subset).fit(disp=0, maxiter=100)
                results[f'risk_total_{subset_name}'] = {
                    'n': len(subset),
                    'risk_or': float(np.exp(m.params.get('risk_index', 0))),
                    'risk_p': float(m.pvalues.get('risk_index', 1)),
                }
                print(f"  {subset_name}: N={len(subset)}, risk OR={np.exp(m.params.get('risk_index', 0)):.3f}, p={m.pvalues.get('risk_index', 1):.4f}")
            except Exception as e:
                results[f'risk_total_{subset_name}'] = {'error': str(e)}

    save_json(results, '08_robustness_check')
    print("\nStep 8完成。")


if __name__ == '__main__':
    # Step 2
    merged = step2_reasoning_type_integration()
    if merged is not None:
        # Step 7
        step7_moderation_by_reasoning_type(merged)

    # Step 8
    step8_robustness()

    print("\n" + "=" * 60)
    print("论文C Step 2/7/8 完成")
    print("=" * 60)
