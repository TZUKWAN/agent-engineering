"""
论文C: 推理-指令对齐度 + 中介路径
核心：对齐度=指令中特定语用要素在推理文本中的覆盖率
"""
import os, json, re
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.formula.api as smf

SEED = 42
np.random.seed(SEED)
RESULT_DIR = "results/optimization/paperC"
os.makedirs(RESULT_DIR, exist_ok=True)

CONSTRAINT_WORDS = ["don't", "do not", "never", "avoid", "without", "cannot",
                    "keep", "maintain", "stay", "preserve", "must", "should",
                    "need to", "have to", "only", "just"]
VERIFICATION_WORDS = ['check', 'verify', 'confirm', 'validate', 'ensure',
                      'make sure', 'done', 'complete', 'correct', 'finished', 'ready']
DECOMPOSITION_WORDS = ['first', 'then', 'next', 'after', 'before', 'finally', 'step', 'phase']
ASSUMPTION_WORDS = ['assume', 'suppose', 'might', 'maybe', 'perhaps', 'probably', 'guess']


def save_json(data, name):
    with open(os.path.join(RESULT_DIR, f"{name}.json"), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def compute_coverage(instr_set, reasoning_text):
    """计算指令词集合在推理文本中的覆盖率"""
    if len(instr_set) == 0:
        return None
    found = sum(1 for w in instr_set if w in reasoning_text)
    return found / len(instr_set)


def step1_alignment():
    print("=" * 60)
    print("Step 1: 推理-指令对齐度指标")
    print("=" * 60)

    df = pd.read_parquet('results/optimization/paperB/prepared_data.parquet')
    df = df.drop_duplicates(subset=['task_id']).reset_index(drop=True)
    steps = pd.read_parquet('data/interim/paper04/steps.parquet')

    print("聚合推理文本...")
    reasoning_agg = steps.groupby('task_id').agg({
        'thought': lambda x: ' '.join(str(t) for t in x if pd.notna(t)),
        'reflection': lambda x: ' '.join(str(t) for t in x if pd.notna(t)),
    }).reset_index()
    reasoning_agg['reasoning_text'] = (reasoning_agg['thought'] + ' ' + reasoning_agg['reflection']).str.lower()

    merged = df.merge(reasoning_agg[['task_id', 'reasoning_text']], on='task_id', how='inner')
    print(f"合并后: {len(merged)}")

    print("计算覆盖率...")
    rows = []
    for _, row in merged.iterrows():
        instr = str(row.get('instruction', '')).lower()
        reasoning = str(row.get('reasoning_text', ''))

        # 指令中的各类词集合
        instr_cons = {w for w in CONSTRAINT_WORDS if w in instr}
        instr_verif = {w for w in VERIFICATION_WORDS if w in instr}
        instr_decomp = {w for w in DECOMPOSITION_WORDS if w in instr}

        # 覆盖率
        cons_cov = compute_coverage(instr_cons, reasoning)
        verif_cov = compute_coverage(instr_verif, reasoning)
        decomp_cov = compute_coverage(instr_decomp, reasoning)

        # 平均覆盖率（仅适用维度）
        covs = [c for c in [cons_cov, verif_cov, decomp_cov] if c is not None]
        avg_cov = float(np.mean(covs)) if covs else None
        deviation = (1 - avg_cov) if avg_cov is not None else None

        # 假设无验证
        has_assumption = any(w in reasoning for w in ASSUMPTION_WORDS)
        has_verif_reasoning = len(instr_verif) > 0 and any(w in reasoning for w in VERIFICATION_WORDS)
        assumption_no_verif = int(has_assumption and not has_verif_reasoning)

        rows.append({
            'task_id': row['task_id'],
            'constraint_coverage': cons_cov if cons_cov is not None else np.nan,
            'verification_coverage': verif_cov if verif_cov is not None else np.nan,
            'decomposition_coverage': decomp_cov if decomp_cov is not None else np.nan,
            'avg_coverage': avg_cov if avg_cov is not None else np.nan,
            'alignment_deviation': deviation if deviation is not None else np.nan,
            'assumption_no_verification': assumption_no_verif,
        })

    adf = pd.DataFrame(rows)
    merged = merged.merge(adf, on='task_id', how='inner')
    merged.to_parquet(os.path.join(RESULT_DIR, '01_alignment_features.parquet'), index=False)

    # 描述
    valid = merged[merged['alignment_deviation'].notna()]
    desc = {
        'n_total': len(merged),
        'n_with_alignment': len(valid),
        'alignment_deviation_mean': float(valid['alignment_deviation'].mean()),
        'alignment_deviation_std': float(valid['alignment_deviation'].std()),
        'alignment_deviation_median': float(valid['alignment_deviation'].median()),
        'constraint_coverage_mean': float(valid['constraint_coverage'].mean()) if valid['constraint_coverage'].notna().sum() > 0 else None,
        'verification_coverage_mean': float(valid['verification_coverage'].mean()) if valid['verification_coverage'].notna().sum() > 0 else None,
        'decomposition_coverage_mean': float(valid['decomposition_coverage'].mean()) if valid['decomposition_coverage'].notna().sum() > 0 else None,
        'assumption_no_verification_rate': float(merged['assumption_no_verification'].mean()),
    }
    save_json(desc, '01_alignment_descriptives')
    print(f"  对齐偏差均值: {desc['alignment_deviation_mean']:.3f}")
    print(f"  约束覆盖率: {desc['constraint_coverage_mean']}")
    print(f"  验证覆盖率: {desc['verification_coverage_mean']}")

    return merged


def build_risk_features(merged):
    """构建提示风险指标"""
    data = merged.copy()
    data['risk_initial_state_missing'] = (data['has_initial_state'] == 0).astype(int)
    data['risk_constraint_missing'] = (data['has_constraint_words'] == 0).astype(int)
    data['risk_verification_missing'] = (data['has_completion_criteria'] == 0).astype(int)
    data['risk_subtask_no_order'] = ((data['has_multiple_subtasks'] == 1) & (data['has_operation_order'] == 0)).astype(int)
    data['risk_object_missing'] = (data['has_operation_object'] == 0).astype(int)

    risk_cols = ['risk_initial_state_missing', 'risk_constraint_missing',
                 'risk_verification_missing', 'risk_subtask_no_order', 'risk_object_missing']
    data['risk_index'] = data[risk_cols].sum(axis=1)
    return data, risk_cols


def step3_risk_to_alignment(data, risk_cols):
    print("\n" + "=" * 60)
    print("Step 3: 提示风险 → 对齐度")
    print("=" * 60)

    reg = data[data['alignment_deviation'].notna()].dropna(
        subset=['task_difficulty', 'word_count']).copy()
    reg['os'] = reg['os'].astype(str)

    m = smf.ols('alignment_deviation ~ risk_index + task_difficulty + word_count + C(os)',
                data=reg).fit(disp=0)
    result = {
        'n': len(reg),
        'r_squared': float(m.rsquared),
        'risk_index_coef': float(m.params.get('risk_index', 0)),
        'risk_index_p': float(m.pvalues.get('risk_index', 1)),
    }

    single = {}
    for rc in risk_cols:
        try:
            ms = smf.ols(f'alignment_deviation ~ {rc} + task_difficulty + word_count + C(os)',
                         data=reg).fit(disp=0)
            single[rc] = {
                'coef': float(ms.params.get(rc, 0)),
                'p': float(ms.pvalues.get(rc, 1)),
                'rate': float(reg[rc].mean()),
            }
        except:
            pass
    result['single_risk_effects'] = single
    save_json(result, '03_risk_to_alignment')
    print(f"  risk_index → deviation: β={result['risk_index_coef']:.4f}, p={result['risk_index_p']:.4f}")
    for k, v in single.items():
        print(f"  {k}: β={v['coef']:.4f}, p={v['p']:.4f}")
    return reg


def step4_alignment_to_execution(data):
    print("\n" + "=" * 60)
    print("Step 4: 对齐度 → 执行错误")
    print("=" * 60)

    reg = data[data['alignment_deviation'].notna()].dropna(
        subset=['incorrect_ratio', 'redundant_ratio', 'task_difficulty', 'word_count']).copy()
    reg['execution_error'] = reg['incorrect_ratio'].fillna(0) + reg['redundant_ratio'].fillna(0)

    m = smf.ols('execution_error ~ alignment_deviation + risk_index + task_difficulty + word_count',
                data=reg).fit(disp=0)
    result = {
        'n': len(reg),
        'r_squared': float(m.rsquared),
        'alignment_deviation_coef': float(m.params.get('alignment_deviation', 0)),
        'alignment_deviation_p': float(m.pvalues.get('alignment_deviation', 1)),
        'risk_index_coef': float(m.params.get('risk_index', 0)),
        'risk_index_p': float(m.pvalues.get('risk_index', 1)),
    }
    save_json(result, '04_alignment_to_execution')
    print(f"  deviation → execution_error: β={result['alignment_deviation_coef']:.4f}, p={result['alignment_deviation_p']:.4f}")
    return reg


def step5_errors_to_completion(reg):
    print("\n" + "=" * 60)
    print("Step 5: 对齐度/执行错误 → 任务完成")
    print("=" * 60)

    m = smf.logit(
        'task_completed_num ~ alignment_deviation + execution_error + risk_index + task_difficulty',
        data=reg
    ).fit(disp=0, maxiter=100)

    result = {'n': len(reg), 'pseudo_r2': float(m.prsquared), 'coefficients': {}}
    for term in m.params.index:
        result['coefficients'][term] = {
            'coef': float(m.params[term]),
            'or': float(np.exp(m.params[term])),
            'p': float(m.pvalues[term]),
        }
    save_json(result, '05_errors_to_completion')
    for t in ['alignment_deviation', 'execution_error', 'risk_index']:
        if t in m.params.index:
            print(f"  {t}: OR={np.exp(m.params[t]):.4f}, p={m.pvalues[t]:.4f}")


def step6_mediation(reg):
    print("\n" + "=" * 60)
    print("Step 6: Bootstrap中介分析")
    print("=" * 60)

    data = reg[['task_completed_num', 'risk_index', 'alignment_deviation',
                'execution_error', 'task_difficulty']].dropna()

    n_boot = 500
    indirect, direct = [], []
    indices = np.arange(len(data))
    print(f"  Bootstrap {n_boot}次...")

    for b in range(n_boot):
        if b % 100 == 0:
            print(f"    {b}/{n_boot}")
        bi = np.random.choice(indices, size=len(indices), replace=True)
        bd = data.iloc[bi]
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

    m_total = smf.logit('task_completed_num ~ risk_index + task_difficulty', data=data).fit(disp=0, maxiter=100)
    result = {
        'n_boot': len(indirect),
        'indirect_mean': float(np.mean(indirect)),
        'indirect_ci_low': ci_lo,
        'indirect_ci_high': ci_hi,
        'indirect_significant': not (ci_lo <= 0 <= ci_hi),
        'direct_mean': float(np.mean(direct)),
        'total_coef': float(m_total.params.get('risk_index', 0)),
        'total_p': float(m_total.pvalues.get('risk_index', 1)),
    }
    save_json(result, '06_mediation_analysis')
    print(f"\n  间接效应: mean={result['indirect_mean']:.6f}")
    print(f"  95% CI: [{ci_lo:.6f}, {ci_hi:.6f}]")
    print(f"  间接显著: {'是' if result['indirect_significant'] else '否'}")
    print(f"  总效应: {result['total_coef']:.4f} (p={result['total_p']:.4f})")


def step9_validity(reg):
    print("\n" + "=" * 60)
    print("Step 9: 效度验证")
    print("=" * 60)

    validity = {}
    med = reg['alignment_deviation'].median()
    high = reg[reg['alignment_deviation'] <= med]
    low = reg[reg['alignment_deviation'] > med]
    if len(high) > 0 and len(low) > 0:
        validity['completion_by_alignment'] = {
            'high_alignment_rate': float(high['task_completed_num'].mean()),
            'low_alignment_rate': float(low['task_completed_num'].mean()),
            'met': bool(high['task_completed_num'].mean() > low['task_completed_num'].mean()),
        }
        print(f"  高对齐vs低对齐完成率: {high['task_completed_num'].mean():.4f} vs {low['task_completed_num'].mean():.4f}")

    valid = reg[['alignment_deviation', 'execution_error']].dropna()
    if len(valid) > 10:
        r, p = stats.pearsonr(valid['alignment_deviation'], valid['execution_error'])
        validity['deviation_error_corr'] = {'r': float(r), 'p': float(p), 'met': bool(r > 0)}
        print(f"  偏差与执行错误相关: r={r:.3f}, p={p:.4f}")

    save_json(validity, '09_alignment_validity')


if __name__ == '__main__':
    merged = step1_alignment()
    data, risk_cols = build_risk_features(merged)
    reg3 = step3_risk_to_alignment(data, risk_cols)
    reg4 = step4_alignment_to_execution(data)
    step5_errors_to_completion(reg4)
    step6_mediation(reg4)
    step9_validity(reg4)
    print("\n" + "=" * 60)
    print("论文C 完成")
    print("=" * 60)
