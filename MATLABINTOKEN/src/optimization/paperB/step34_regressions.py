"""
论文B Step 3-4: 验证效应 + 约束效应分析
包含：Logistic回归、负二项回归、终止阶段、非线性、位置分析、
      全局倒U、条件倒U、子类型、稳健性
"""
import os, json
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

SEED = 42
np.random.seed(SEED)

RESULT_DIR = "results/optimization/paperB"


def load_data():
    df = pd.read_parquet(os.path.join(RESULT_DIR, 'prepared_data.parquet'))
    # 去重（防止join产生重复）
    df = df.drop_duplicates(subset=['task_id']).reset_index(drop=True)
    print(f"载入数据: {len(df)} 样本")
    return df


def fit_logistic(df, formula_str, data):
    """拟合Logistic回归"""
    import statsmodels.formula.api as smf
    model = smf.logit(formula_str, data=data).fit(disp=0)
    return model


def fit_nb(df, formula_str, data):
    """拟合负二项回归"""
    import statsmodels.formula.api as smf
    model = smf.negativebinomial(formula_str, data=data).fit(disp=0)
    return model


def save_json(data, name):
    with open(os.path.join(RESULT_DIR, f"{name}.json"), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def save_csv(df, name):
    df.to_csv(os.path.join(RESULT_DIR, f"{name}.csv"))


def logistic_results_to_dict(model, n):
    """提取Logistic回归结果"""
    params = model.params
    conf = model.conf_int()
    conf.columns = ['low', 'high']
    bse = model.bse
    pvals = model.pvalues

    rows = []
    for term in params.index:
        or_val = float(np.exp(params[term]))
        rows.append({
            'term': term,
            'coef': float(params[term]),
            'std_err': float(bse[term]),
            'z': float(params[term] / bse[term]),
            'p_value': float(pvals[term]),
            'or': or_val,
            'ci_low_or': float(np.exp(conf.loc[term, 'low'])),
            'ci_high_or': float(np.exp(conf.loc[term, 'high'])),
        })

    return {
        'n_obs': int(n),
        'pseudo_r2': float(model.prsquared),
        'loglikelihood': float(model.llf),
        'aic': float(model.aic),
        'bic': float(model.bic),
        'rows': rows,
    }


def nb_results_to_dict(model, n):
    """提取负二项回归结果"""
    params = model.params
    conf = model.conf_int()
    conf.columns = ['low', 'high']
    bse = model.bse
    pvals = model.pvalues

    rows = []
    for term in params.index:
        irr = float(np.exp(params[term]))
        rows.append({
            'term': term,
            'coef': float(params[term]),
            'std_err': float(bse[term]),
            'z': float(params[term] / bse[term]) if bse[term] > 0 else None,
            'p_value': float(pvals[term]),
            'irr': irr,
            'ci_low_irr': float(np.exp(conf.loc[term, 'low'])),
            'ci_high_irr': float(np.exp(conf.loc[term, 'high'])),
        })

    return {
        'n_obs': int(n),
        'pseudo_r2': float(model.prsquared),
        'loglikelihood': float(model.llf),
        'aic': float(model.aic),
        'bic': float(model.bic),
        'alpha': float(model.params.get('alpha', np.nan)) if 'alpha' in model.params else None,
        'rows': rows,
    }


def step3_verification_effects(df):
    """Step 3: 验证效应分析"""
    print("\n" + "=" * 60)
    print("Step 3: 验证效应分析")
    print("=" * 60)

    import statsmodels.formula.api as smf

    reg_data = df.dropna(subset=['task_completed_num', 'task_difficulty', 'word_count', 'os']).copy()
    reg_data['os'] = reg_data['os'].astype(str)
    n = len(reg_data)
    print(f"回归样本: {n}")

    # ---- H1a: Logistic回归 ----
    print("\n-- H1a: Logistic回归 --")
    model_logit = smf.logit(
        'task_completed_num ~ has_completion_criteria + task_difficulty + word_count + C(os)',
        data=reg_data
    ).fit(disp=0)
    logit_dict = logistic_results_to_dict(model_logit, n)
    save_json(logit_dict, '03_logistic_verification')
    # 找has_completion_criteria的OR
    for r in logit_dict['rows']:
        if 'has_completion_criteria' in r['term']:
            print(f"  has_completion_criteria: OR={r['or']:.3f} [95% CI {r['ci_low_or']:.3f}, {r['ci_high_or']:.3f}], p={r['p_value']:.4f}")

    # ---- H1b: 负二项回归 ----
    print("\n-- H1b: 负二项回归 (步数) --")
    reg_data_steps = reg_data.dropna(subset=['total_steps']).copy()
    model_nb = smf.negativebinomial(
        'total_steps ~ has_completion_criteria + task_difficulty + word_count + C(os)',
        data=reg_data_steps
    ).fit(disp=0)
    nb_dict = nb_results_to_dict(model_nb, len(reg_data_steps))
    save_json(nb_dict, '04_negative_binomial_verification')
    for r in nb_dict['rows']:
        if 'has_completion_criteria' in r['term']:
            print(f"  has_completion_criteria: IRR={r['irr']:.3f} [95% CI {r['ci_low_irr']:.3f}, {r['ci_high_irr']:.3f}], p={r['p_value']:.4f}")

    # ---- H1c: 终止阶段分析 ----
    print("\n-- H1c: 终止阶段分析 --")
    steps_df = pd.read_parquet('data/interim/paper04/steps.parquet')
    terminal_stats = compute_terminal_phase(steps_df, df)
    save_json(terminal_stats, '05_terminal_phase_comparison')
    for group, vals in terminal_stats['groups'].items():
        print(f"  {group}: 终止冗余比={vals['terminal_redundant_ratio_mean']:.4f}, 终止错误比={vals['terminal_error_ratio_mean']:.4f}, 异常短轨迹率={vals['short_trajectory_rate']:.4f}")

    # ---- H2: 验证密度非线性检验 ----
    print("\n-- H2: 验证密度非线性检验 --")
    verif_subset = reg_data[reg_data['verification_density'] > 0].copy()
    if len(verif_subset) > 50:
        # 线性模型
        m_linear = smf.logit(
            'task_completed_num ~ verification_density + task_difficulty + word_count + C(os)',
            data=verif_subset
        ).fit(disp=0)
        # 二次模型
        m_quad = smf.logit(
            'task_completed_num ~ verification_density + I(verification_density**2) + task_difficulty + word_count + C(os)',
            data=verif_subset
        ).fit(disp=0)
        lr_stat = 2 * (m_quad.llf - m_linear.llf)
        lr_p = 1 - stats.chi2.cdf(lr_stat, 1)
        nonlinear_result = {
            'n': len(verif_subset),
            'linear_aic': float(m_linear.aic),
            'quadratic_aic': float(m_quad.aic),
            'lr_statistic': float(lr_stat),
            'lr_p_value': float(lr_p),
            'quadratic_coef': float(m_quad.params.get('I(verification_density ** 2)', np.nan)),
            'quadratic_p': float(m_quad.pvalues.get('I(verification_density ** 2)', np.nan)),
            'h2_supported': bool(lr_p > 0.05),  # 不支持非线性=支持H2
        }
        save_json(nonlinear_result, '06_nonlinear_verification')
        print(f"  N={len(verif_subset)}, 二次项p={nonlinear_result['quadratic_p']:.4f}, LR p={lr_p:.4f}")
        print(f"  H2(线性正相关, 非线性不显著): {'支持' if nonlinear_result['h2_supported'] else '不支持'}")

    # ---- H3: 验证位置分析 ----
    print("\n-- H3: 验证位置分析 --")
    pos_result = compute_verification_position(reg_data)
    save_json(pos_result, '07_position_analysis')
    print(f"  开头: {pos_result['groups']['beginning']['completion_rate']:.4f}")
    print(f"  中间: {pos_result['groups']['middle']['completion_rate']:.4f}")
    print(f"  末尾: {pos_result['groups']['end']['completion_rate']:.4f}")
    print(f"  卡方p={pos_result['chi2_p']:.4f}")
    print(f"  H3(位置无影响): {'支持' if pos_result['chi2_p'] > 0.05 else '不支持'}")


def compute_terminal_phase(steps_df, df):
    """计算终止阶段指标（最后25%的步骤）"""
    results = {'groups': {}}

    for group_name, group_mask in [('has_criteria', df['has_completion_criteria'] == 1),
                                     ('no_criteria', df['has_completion_criteria'] == 0)]:
        group_task_ids = set(df.loc[group_mask, 'task_id'])
        group_steps = steps_df[steps_df['task_id'].isin(group_task_ids)]

        terminal_redundant_ratios = []
        terminal_error_ratios = []
        short_traj_count = 0
        total_tasks = 0

        for tid, task_steps in group_steps.groupby('task_id'):
            n = len(task_steps)
            if n < 4:
                continue
            total_tasks += 1
            if n <= 9:
                short_traj_count += 1
            # 最后25%
            cutoff = max(1, int(n * 0.75))
            terminal = task_steps.iloc[cutoff:]
            terminal_redundant_ratios.append(terminal['last_step_redundant'].fillna(False).astype(bool).mean())
            terminal_error_ratios.append((~terminal['last_step_correct'].fillna(True).astype(bool)).mean())

        results['groups'][group_name] = {
            'n_tasks': total_tasks,
            'terminal_redundant_ratio_mean': float(np.mean(terminal_redundant_ratios)) if terminal_redundant_ratios else None,
            'terminal_error_ratio_mean': float(np.mean(terminal_error_ratios)) if terminal_error_ratios else None,
            'short_trajectory_rate': float(short_traj_count / total_tasks) if total_tasks > 0 else None,
        }

    return results


def compute_verification_position(reg_data):
    """计算验证关键词在指令中的位置"""
    import re
    verification_words = ['check', 'verify', 'confirm', 'validate', 'ensure', 'make sure',
                          'done', 'complete', 'correct', 'finished', 'ready']

    positions = {'beginning': [], 'middle': [], 'end': []}
    completions = {'beginning': [], 'middle': [], 'end': []}

    for _, row in reg_data.iterrows():
        text = str(row.get('instruction', ''))
        text_lower = text.lower()
        n_chars = len(text)
        if n_chars == 0:
            continue

        # 找第一个验证关键词的位置
        first_pos = None
        for w in verification_words:
            idx = text_lower.find(w)
            if idx >= 0:
                if first_pos is None or idx < first_pos:
                    first_pos = idx

        if first_pos is None:
            continue

        rel_pos = first_pos / n_chars
        completed = row['task_completed_num']

        if rel_pos < 0.25:
            positions['beginning'].append(rel_pos)
            completions['beginning'].append(completed)
        elif rel_pos < 0.75:
            positions['middle'].append(rel_pos)
            completions['middle'].append(completed)
        else:
            positions['end'].append(rel_pos)
            completions['end'].append(completed)

    result = {'groups': {}}
    for region in ['beginning', 'middle', 'end']:
        comps = completions[region]
        result['groups'][region] = {
            'n': len(comps),
            'completion_rate': float(np.mean(comps)) if comps else None,
        }

    # 卡方检验
    if all(len(completions[r]) > 0 for r in ['beginning', 'middle', 'end']):
        ct = pd.DataFrame({
            'completed': [sum(completions[r]) for r in ['beginning', 'middle', 'end']],
            'not_completed': [len(completions[r]) - sum(completions[r]) for r in ['beginning', 'middle', 'end']],
        })
        chi2, p, dof, expected = stats.chi2_contingency(ct.values)
        total_n = float(ct.values.sum())
        result['chi2'] = float(chi2)
        result['chi2_p'] = float(p)
        result['cramers_v'] = float(np.sqrt(chi2 / (total_n * (min(ct.values.shape) - 1))))

    return result


def step4_constraint_effects(df):
    """Step 4: 约束效应分析"""
    print("\n" + "=" * 60)
    print("Step 4: 约束效应分析")
    print("=" * 60)

    import statsmodels.formula.api as smf

    reg_data = df.dropna(subset=['task_completed_num', 'task_difficulty', 'word_count', 'os']).copy()
    reg_data['os'] = reg_data['os'].astype(str)

    # ---- H4: 有约束词的Logistic回归 ----
    print("\n-- H4: 约束词有无效应 --")
    m_h4 = smf.logit(
        'task_completed_num ~ has_constraint_any + task_difficulty + word_count + C(os)',
        data=reg_data
    ).fit(disp=0)
    h4_dict = logistic_results_to_dict(m_h4, len(reg_data))
    save_json(h4_dict, '08_logistic_constraint')
    for r in h4_dict['rows']:
        if 'has_constraint_any' in r['term']:
            print(f"  has_constraint_any: OR={r['or']:.3f}, p={r['p_value']:.4f}")

    # ---- H5: 全局倒U检验 ----
    print("\n-- H5: 全局倒U检验 --")
    constraint_subset = reg_data[reg_data['constraint_density'] > 0].copy()
    if len(constraint_subset) > 100:
        m_quad = smf.logit(
            'task_completed_num ~ constraint_density + I(constraint_density**2) + task_difficulty + word_count + C(os)',
            data=constraint_subset
        ).fit(disp=0)
        b1 = float(m_quad.params.get('constraint_density', np.nan))
        b2 = float(m_quad.params.get('I(constraint_density ** 2)', np.nan))
        p2 = float(m_quad.pvalues.get('I(constraint_density ** 2)', np.nan))
        turning = -b1 / (2 * b2) if b2 != 0 else None
        global_result = {
            'n': len(constraint_subset),
            'linear_coef': b1,
            'quadratic_coef': b2,
            'quadratic_p': p2,
            'turning_point': turning,
            'h5_supported': bool(p2 > 0.05),
        }
        save_json(global_result, '09_quadratic_global')
        print(f"  N={len(constraint_subset)}, 二次项coef={b2:.4f}, p={p2:.4f}")
        print(f"  H5(无全局倒U): {'支持' if global_result['h5_supported'] else '不支持'}")

    # ---- H6-H8: 条件模型（调节效应） ----
    print("\n-- H6-H8: 条件模型 --")
    moderation_results = {}
    for moderator, mod_label in [('task_difficulty', 'H6_difficulty'),
                                   ('word_count', 'H7_length'),
                                   ('has_multiple_subtasks', 'H8_subtasks')]:
        print(f"  -- {mod_label} --")
        try:
            formula = f'task_completed_num ~ constraint_density * {moderator} + I(constraint_density**2) * {moderator} + word_count + C(os)'
            if moderator == 'word_count':
                formula = f'task_completed_num ~ constraint_density * {moderator} + I(constraint_density**2) * {moderator} + task_difficulty + C(os)'
            m_mod = smf.logit(formula, data=constraint_subset).fit(disp=0)

            # 提取交互项
            rows = []
            for term in m_mod.params.index:
                if 'constraint_density' in term or 'I(constraint_density' in term:
                    rows.append({
                        'term': term,
                        'coef': float(m_mod.params[term]),
                        'std_err': float(m_mod.bse[term]),
                        'p_value': float(m_mod.pvalues[term]),
                        'or': float(np.exp(m_mod.params[term])),
                    })
            moderation_results[mod_label] = {
                'n': len(constraint_subset),
                'key_interactions': rows,
            }

            # 高难度/长指令/多子任务子样本的二次项
            if moderator == 'task_difficulty':
                high_mask = constraint_subset['task_difficulty'] >= 6
            elif moderator == 'word_count':
                high_mask = constraint_subset['word_count'] >= constraint_subset['word_count'].median()
            else:
                high_mask = constraint_subset['has_multiple_subtasks'] == 1

            high_data = constraint_subset[high_mask]
            low_data = constraint_subset[~high_mask]

            for sub_label, sub_data in [('high', high_data), ('low', low_data)]:
                if len(sub_data) > 100:
                    m_sub = smf.logit(
                        'task_completed_num ~ constraint_density + I(constraint_density**2) + task_difficulty + word_count + C(os)',
                        data=sub_data
                    ).fit(disp=0)
                    b2s = float(m_sub.params.get('I(constraint_density ** 2)', np.nan))
                    p2s = float(m_sub.pvalues.get('I(constraint_density ** 2)', np.nan))
                    b1s = float(m_sub.params.get('constraint_density', np.nan))
                    turn_s = -b1s / (2 * b2s) if b2s != 0 else None
                    moderation_results[mod_label][f'{sub_label}_subset'] = {
                        'n': len(sub_data),
                        'quadratic_coef': b2s,
                        'quadratic_p': p2s,
                        'turning_point': turn_s,
                    }
                    print(f"    {sub_label}子样本: N={len(sub_data)}, b2={b2s:.4f}, p={p2s:.4f}, 拐点={turn_s:.3f}" if turn_s else f"    {sub_label}子样本: N={len(sub_data)}, b2={b2s:.4f}, p={p2s:.4f}")
        except Exception as e:
            moderation_results[mod_label] = {'error': str(e)}
            print(f"    错误: {e}")

    save_json(moderation_results, '10_moderation_analysis')

    # ---- H9: 子类型异质性 ----
    print("\n-- H9: 子类型异质性 --")
    subtype_results = {}
    for col, label in [('constraint_prohibitive', 'C1_Prohibitive'),
                        ('constraint_preservative', 'C2_Preservative'),
                        ('constraint_obligative', 'C3_Obligative'),
                        ('constraint_restrictive', 'C4_Restrictive')]:
        sub = constraint_subset[constraint_subset[col] > 0]
        if len(sub) > 100:
            try:
                m = smf.logit(
                    'task_completed_num ~ constraint_density + I(constraint_density**2) + task_difficulty + word_count + C(os)',
                    data=sub
                ).fit(disp=0)
                b2 = float(m.params.get('I(constraint_density ** 2)', np.nan))
                p2 = float(m.pvalues.get('I(constraint_density ** 2)', np.nan))
                b1 = float(m.params.get('constraint_density', np.nan))
                turn = -b1 / (2 * b2) if b2 != 0 else None
                subtype_results[label] = {
                    'n': len(sub),
                    'quadratic_coef': b2,
                    'quadratic_p': p2,
                    'turning_point': turn,
                }
                print(f"  {label}: N={len(sub)}, b2={b2:.4f}, p={p2:.4f}")
            except Exception as e:
                subtype_results[label] = {'error': str(e)}
        else:
            subtype_results[label] = {'n': len(sub), 'note': '样本不足'}
    save_json(subtype_results, '11_subtype_analysis')

    # ---- 稳健性：分平台 ----
    print("\n-- 稳健性检验 --")
    robustness = {}
    for os_val in ['win_mac', 'ubuntu']:
        sub = constraint_subset[constraint_subset['os'] == os_val]
        if len(sub) > 100:
            try:
                m = smf.logit(
                    'task_completed_num ~ constraint_density + I(constraint_density**2) + task_difficulty + word_count',
                    data=sub
                ).fit(disp=0)
                b2 = float(m.params.get('I(constraint_density ** 2)', np.nan))
                p2 = float(m.pvalues.get('I(constraint_density ** 2)', np.nan))
                robustness[f'{os_val}_quadratic'] = {'n': len(sub), 'coef': b2, 'p': p2}
                print(f"  {os_val}: N={len(sub)}, b2={b2:.4f}, p={p2:.4f}")
            except Exception as e:
                robustness[f'{os_val}_quadratic'] = {'error': str(e)}
    save_json(robustness, '12_robustness_check')


if __name__ == '__main__':
    df = load_data()
    step3_verification_effects(df)
    step4_constraint_effects(df)
    print("\n" + "=" * 60)
    print("Step 3-4 完成")
    print("=" * 60)
