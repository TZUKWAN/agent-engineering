"""
论文B Step 5-7: 验证vs约束对比 + 效度验证
"""
import os, json
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

SEED = 42
np.random.seed(SEED)
RESULT_DIR = "results/optimization/paperB"


def save_json(data, name):
    with open(os.path.join(RESULT_DIR, f"{name}.json"), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def step5_combined_comparison(df):
    """Step 5: 验证 vs 约束的直接对比"""
    print("\n" + "=" * 60)
    print("Step 5: 验证 vs 约束对比")
    print("=" * 60)

    reg_data = df.dropna(subset=['task_completed_num', 'task_difficulty', 'word_count', 'os']).copy()
    reg_data['os'] = reg_data['os'].astype(str)

    # 联合模型
    print("\n-- 联合模型 --")
    m_joint = smf.logit(
        'task_completed_num ~ has_completion_criteria + has_constraint_any + has_completion_criteria:has_constraint_any + task_difficulty + word_count + C(os)',
        data=reg_data
    ).fit(disp=0)

    joint_rows = []
    for term in m_joint.params.index:
        joint_rows.append({
            'term': term,
            'coef': float(m_joint.params[term]),
            'std_err': float(m_joint.bse[term]),
            'p_value': float(m_joint.pvalues[term]),
            'or': float(np.exp(m_joint.params[term])),
        })
    joint_result = {
        'n': len(reg_data),
        'pseudo_r2': float(m_joint.prsquared),
        'aic': float(m_joint.aic),
        'rows': joint_rows,
    }
    save_json(joint_result, '13_combined_model')
    for r in joint_rows:
        if 'criteria' in r['term'] or 'constraint' in r['term']:
            print(f"  {r['term']}: OR={r['or']:.3f}, p={r['p_value']:.4f}")

    # 边际贡献：嵌套模型似然比检验
    print("\n-- 边际贡献（似然比检验）--")
    m_base = smf.logit(
        'task_completed_num ~ task_difficulty + word_count + C(os)',
        data=reg_data
    ).fit(disp=0)
    m_verif = smf.logit(
        'task_completed_num ~ has_completion_criteria + task_difficulty + word_count + C(os)',
        data=reg_data
    ).fit(disp=0)
    m_cons = smf.logit(
        'task_completed_num ~ has_constraint_any + task_difficulty + word_count + C(os)',
        data=reg_data
    ).fit(disp=0)
    m_both = smf.logit(
        'task_completed_num ~ has_completion_criteria + has_constraint_any + task_difficulty + word_count + C(os)',
        data=reg_data
    ).fit(disp=0)

    lr_verif = 2 * (m_verif.llf - m_base.llf)
    lr_cons = 2 * (m_cons.llf - m_base.llf)
    lr_verif_beyond_cons = 2 * (m_both.llf - m_cons.llf)
    lr_cons_beyond_verif = 2 * (m_both.llf - m_verif.llf)

    marginal = {
        'lr_verification_alone': {
            'lr_stat': float(lr_verif),
            'p_value': float(1 - stats.chi2.cdf(lr_verif, 1)),
            'pseudo_r2_delta': float(m_verif.prsquared - m_base.prsquared),
        },
        'lr_constraint_alone': {
            'lr_stat': float(lr_cons),
            'p_value': float(1 - stats.chi2.cdf(lr_cons, 1)),
            'pseudo_r2_delta': float(m_cons.prsquared - m_base.prsquared),
        },
        'lr_verification_beyond_constraint': {
            'lr_stat': float(lr_verif_beyond_cons),
            'p_value': float(1 - stats.chi2.cdf(lr_verif_beyond_cons, 1)),
        },
        'lr_constraint_beyond_verification': {
            'lr_stat': float(lr_cons_beyond_verif),
            'p_value': float(1 - stats.chi2.cdf(lr_cons_beyond_verif, 1)),
        },
    }
    save_json(marginal, '14_marginal_contribution')
    print(f"  验证单独: LR={marginal['lr_verification_alone']['lr_stat']:.2f}, p={marginal['lr_verification_alone']['p_value']:.4f}")
    print(f"  约束单独: LR={marginal['lr_constraint_alone']['lr_stat']:.2f}, p={marginal['lr_constraint_alone']['p_value']:.4f}")
    print(f"  验证(控制约束后): LR={marginal['lr_verification_beyond_constraint']['lr_stat']:.2f}, p={marginal['lr_verification_beyond_constraint']['p_value']:.4f}")
    print(f"  约束(控制验证后): LR={marginal['lr_constraint_beyond_verification']['lr_stat']:.2f}, p={marginal['lr_constraint_beyond_verification']['p_value']:.4f}")

    # 分难度子样本
    print("\n-- 分难度子样本 --")
    difficulty_results = {}
    for diff_level, label in [(1, 'low'), (2, 'medium'), (3, 'high')]:
        if diff_level <= 2:
            sub = reg_data[reg_data['task_difficulty'] <= 3] if diff_level == 1 else reg_data[(reg_data['task_difficulty'] > 3) & (reg_data['task_difficulty'] <= 6)]
        else:
            sub = reg_data[reg_data['task_difficulty'] > 6]
        if len(sub) > 100:
            try:
                m = smf.logit(
                    'task_completed_num ~ has_completion_criteria + has_constraint_any + task_difficulty + word_count + C(os)',
                    data=sub
                ).fit(disp=0)
                v_or = float(np.exp(m.params.get('has_completion_criteria', 0)))
                c_or = float(np.exp(m.params.get('has_constraint_any', 0)))
                difficulty_results[label] = {
                    'n': len(sub),
                    'verification_or': v_or,
                    'verification_p': float(m.pvalues.get('has_completion_criteria', 1)),
                    'constraint_or': c_or,
                    'constraint_p': float(m.pvalues.get('has_constraint_any', 1)),
                }
                print(f"  {label}(N={len(sub)}): 验证OR={v_or:.3f}, 约束OR={c_or:.3f}")
            except Exception as e:
                difficulty_results[label] = {'error': str(e)}
    save_json(difficulty_results, '15_difficulty_specific_effects')


def step7_validity(df):
    """Step 7: 效度验证"""
    print("\n" + "=" * 60)
    print("Step 7: 效度验证")
    print("=" * 60)

    # 聚合效度
    print("\n-- 聚合效度 --")
    convergent_pairs = [
        ('has_completion_criteria', 'verification_density', '应正相关'),
        ('has_constraint_words', 'constraint_density', '应正相关'),
        ('has_constraint_words', 'has_constraint_any', '应高度正相关'),
        ('verification_richness', 'verification_density', '应正相关'),
        ('constraint_richness', 'constraint_density', '应正相关'),
    ]
    convergent = {}
    for v1, v2, expectation in convergent_pairs:
        if v1 in df.columns and v2 in df.columns:
            valid = df[[v1, v2]].dropna()
            if len(valid) > 10:
                r, p = stats.pearsonr(valid[v1].astype(float), valid[v2].astype(float))
                convergent[f'{v1}_vs_{v2}'] = {
                    'r': float(r), 'p': float(p), 'n': len(valid),
                    'expectation': expectation,
                    'met': (r > 0 if '正' in expectation else r < 0),
                }
                print(f"  {v1} vs {v2}: r={r:.3f}, p={p:.4f} → {'符合' if (r > 0 if '正' in expectation else r < 0) else '不符合'}")

    # 区分效度
    print("\n-- 区分效度 --")
    discriminant_pairs = [
        ('has_completion_criteria', 'has_constraint_words', '应低相关(r<0.5)'),
        ('verification_density', 'constraint_density', '应低相关'),
        ('word_count', 'verification_density', '不应高度相关'),
    ]
    discriminant = {}
    for v1, v2, expectation in discriminant_pairs:
        if v1 in df.columns and v2 in df.columns:
            valid = df[[v1, v2]].dropna()
            if len(valid) > 10:
                r, p = stats.pearsonr(valid[v1].astype(float), valid[v2].astype(float))
                discriminant[f'{v1}_vs_{v2}'] = {
                    'r': float(r), 'p': float(p), 'n': len(valid),
                    'expectation': expectation,
                    'met': abs(r) < 0.5,
                }
                print(f"  {v1} vs {v2}: r={r:.3f} → {'符合' if abs(r) < 0.5 else '不符合'}")

    # 已知群组效度
    print("\n-- 已知群组效度 --")
    known_groups = {}
    # 高难度任务约束效应应更强
    high_diff = df[df['task_difficulty'] >= 7]
    low_diff = df[df['task_difficulty'] <= 3]
    if len(high_diff) > 10 and len(low_diff) > 10:
        # 有完成标准的步数应更少
        verif_yes = df[df['has_completion_criteria'] == 1]
        verif_no = df[df['has_completion_criteria'] == 0]
        if 'total_steps' in df.columns:
            t_yes = verif_yes['total_steps'].dropna()
            t_no = verif_no['total_steps'].dropna()
            known_groups['verification_step_difference'] = {
                'mean_steps_with_criteria': float(t_yes.mean()) if len(t_yes) > 0 else None,
                'mean_steps_without': float(t_no.mean()) if len(t_no) > 0 else None,
                'expectation': '有完成标准步数应更少',
                'met': bool(t_yes.mean() < t_no.mean()) if len(t_yes) > 0 and len(t_no) > 0 else False,
            }
            print(f"  有完成标准步数: {t_yes.mean():.1f} vs 无: {t_no.mean():.1f} → {'符合预期' if t_yes.mean() < t_no.mean() else '不符合'}")

    validity_result = {
        'convergent_validity': convergent,
        'discriminant_validity': discriminant,
        'known_groups_validity': known_groups,
    }
    save_json(validity_result, '16_validity_check')


if __name__ == '__main__':
    df = pd.read_parquet(os.path.join(RESULT_DIR, 'prepared_data.parquet'))
    df = df.drop_duplicates(subset=['task_id']).reset_index(drop=True)
    print(f"样本: {len(df)}")

    step5_combined_comparison(df)
    step7_validity(df)
    print("\nStep 5-7 完成")
