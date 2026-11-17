"""
论文B：边界性言语行为（验证+约束融合）
Step 0-2: 数据准备 + 验证特征 + 约束特征
"""
import os, json, re
import numpy as np
import pandas as pd
from scipy import stats

SEED = 42
np.random.seed(SEED)

RESULT_DIR = "results/optimization/paperB"
os.makedirs(RESULT_DIR, exist_ok=True)

# ==================== 验证相关词 ====================
VERB_VERIFICATION = ['check', 'verify', 'confirm', 'validate', 'ensure', 'make sure', 'test']
STATE_VERIFICATION = ['done', 'complete', 'completed', 'correct', 'proper', 'finished', 'ready', 'success', 'successful']
CONDITION_VERIFICATION = ['until', 'once', 'after']
ALL_VERIFICATION = VERB_VERIFICATION + STATE_VERIFICATION + CONDITION_VERIFICATION

# ==================== 约束词四分类 ====================
CONSTRAINT_PROHIBITIVE = ["don't", "do not", "never", "avoid", "without", "cannot", "should not", "must not"]
CONSTRAINT_PRESERVATIVE = ["keep", "maintain", "stay", "preserve", "leave"]
CONSTRAINT_OBLIGATIVE = ["must", "should", "need to", "have to", "required"]
CONSTRAINT_RESTRICTIVE = ["only", "just", "merely", "exclusively"]

# ==================== 工具函数 ====================
def save_json_csv(data, name, df_csv=None):
    """同时保存json和csv"""
    with open(os.path.join(RESULT_DIR, f"{name}.json"), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    if df_csv is not None:
        df_csv.to_csv(os.path.join(RESULT_DIR, f"{name}.csv"))

def count_pattern(text, patterns):
    """统计pattern在text中的出现次数（按词边界）"""
    text_lower = text.lower()
    count = 0
    found_types = set()
    for p in patterns:
        if ' ' in p:
            if p in text_lower:
                count += text_lower.count(p)
                found_types.add(p)
        else:
            matches = re.findall(r'\b' + re.escape(p) + r'\b', text_lower)
            count += len(matches)
            if matches:
                found_types.add(p)
    return count, found_types


def step0_prepare_data():
    """Step 0: 数据准备"""
    print("=" * 60)
    print("Step 0: 数据准备")
    print("=" * 60)

    df = pd.read_parquet('data/processed/analysis_data.parquet')
    print(f"原始样本: {len(df)}")

    # 去重（同一task_id可能有多次执行，取第一次）
    df = df.drop_duplicates(subset=['task_id'], keep='first').reset_index(drop=True)
    print(f"去重后(按task_id): {len(df)}")

    # 删除task_completed缺失
    df = df[df['task_completed'].notna()].copy()
    df['task_completed_num'] = df['task_completed'].astype(int)
    print(f"删除task_completed缺失后: {len(df)}")

    # 删除task_difficulty缺失
    df = df[df['task_difficulty'].notna()].copy()
    print(f"删除task_difficulty缺失后: {len(df)}")

    # 确保word_count
    if 'word_count' not in df.columns:
        df['word_count'] = df['instruction'].fillna('').apply(lambda x: len(str(x).split()))

    info = {
        'n_total': len(df),
        'n_completed': int(df['task_completed_num'].sum()),
        'completion_rate': float(df['task_completed_num'].mean()),
        'os_distribution': df['os'].value_counts().to_dict(),
        'mean_difficulty': float(df['task_difficulty'].mean()),
        'mean_word_count': float(df['word_count'].mean()),
    }
    save_json_csv(info, '00_sample_info')
    print(f"完成率: {info['completion_rate']:.4f}")
    print(f"样本已保存到内存")
    return df


def step1_verification_features(df):
    """Step 1: 验证特征（二分+连续+丰富度）"""
    print("\n" + "=" * 60)
    print("Step 1: 验证特征构建")
    print("=" * 60)

    verification_data = []
    for _, row in df.iterrows():
        text = str(row.get('instruction', '')).lower()
        words = text.split()
        n_words = max(len(words), 1)

        # 各类验证词计数
        verb_count, verb_found = count_pattern(text, VERB_VERIFICATION)
        state_count, state_found = count_pattern(text, STATE_VERIFICATION)
        cond_count, cond_found = count_pattern(text, CONDITION_VERIFICATION)
        all_count, all_found = count_pattern(text, ALL_VERIFICATION)

        # 密度 = 验证词次数 / 总词数 × 100
        density = all_count / n_words * 100
        # 丰富度 = 不同验证词的种类数
        richness = len(all_found)

        verification_data.append({
            'task_id': row['task_id'],
            'verification_verb_count': verb_count,
            'verification_state_count': state_count,
            'verification_cond_count': cond_count,
            'verification_total_count': all_count,
            'verification_density': density,
            'verification_richness': richness,
        })

    vdf = pd.DataFrame(verification_data).set_index('task_id')
    df = df.join(vdf, on='task_id')

    # 描述统计
    has_verif = df['has_completion_criteria'] == 1
    desc = {
        'has_completion_criteria': {
            'n_yes': int(has_verif.sum()),
            'n_no': int((~has_verif).sum()),
            'pct_yes': float(has_verif.mean()),
        },
        'verification_density': {
            'mean': float(df['verification_density'].mean()),
            'std': float(df['verification_density'].std()),
            'median': float(df['verification_density'].median()),
            'min': float(df['verification_density'].min()),
            'max': float(df['verification_density'].max()),
            'pct_nonzero': float((df['verification_density'] > 0).mean()),
        },
        'verification_richness': {
            'mean': float(df['verification_richness'].mean()),
            'max': int(df['verification_richness'].max()),
        },
        'correlation_density_wordcount': float(stats.pearsonr(
            df['verification_density'], df['word_count'])[0]),
        'correlation_has_criteria_density': float(stats.pearsonr(
            df['has_completion_criteria'].astype(int),
            df['verification_density'])[0]),
    }
    save_json_csv(desc, '01_verification_features',
                  df[['task_id','verification_density','verification_richness',
                      'verification_total_count']].describe())
    print(f"有验证标准: {desc['has_completion_criteria']['n_yes']} ({desc['has_completion_criteria']['pct_yes']:.1%})")
    print(f"验证密度均值: {desc['verification_density']['mean']:.3f}")
    print(f"验证密度与词数相关: r={desc['correlation_density_wordcount']:.3f}")
    print(f"has_criteria与density相关: r={desc['correlation_has_criteria_density']:.3f}")
    return df


def step2_constraint_features(df):
    """Step 2: 约束词四分类+密度计算"""
    print("\n" + "=" * 60)
    print("Step 2: 约束词四分类+密度计算")
    print("=" * 60)

    constraint_data = []
    for _, row in df.iterrows():
        text = str(row.get('instruction', '')).lower()
        words = text.split()
        n_words = max(len(words), 1)

        prohib_count, _ = count_pattern(text, CONSTRAINT_PROHIBITIVE)
        preserv_count, _ = count_pattern(text, CONSTRAINT_PRESERVATIVE)
        oblig_count, _ = count_pattern(text, CONSTRAINT_OBLIGATIVE)
        restrict_count, _ = count_pattern(text, CONSTRAINT_RESTRICTIVE)

        total = prohib_count + preserv_count + oblig_count + restrict_count

        # 类型分类
        types_present = sum(1 for c in [prohib_count, preserv_count, oblig_count, restrict_count] if c > 0)
        if types_present == 0:
            ctype = 'None'
        elif types_present == 1:
            if prohib_count > 0: ctype = 'C1_Prohibitive'
            elif preserv_count > 0: ctype = 'C2_Preservative'
            elif oblig_count > 0: ctype = 'C3_Obligative'
            else: ctype = 'C4_Restrictive'
        else:
            ctype = 'C5_Mixed'

        constraint_data.append({
            'task_id': row['task_id'],
            'constraint_prohibitive': prohib_count,
            'constraint_preservative': preserv_count,
            'constraint_obligative': oblig_count,
            'constraint_restrictive': restrict_count,
            'constraint_total': total,
            'constraint_density': total / n_words * 100,
            'constraint_richness': types_present,
            'constraint_type': ctype,
            'has_constraint_any': int(total > 0),
        })

    cdf = pd.DataFrame(constraint_data).set_index('task_id')
    df = df.join(cdf, on='task_id')

    # 描述统计
    type_dist = df['constraint_type'].value_counts().to_dict()
    has_cons = df['has_constraint_any'] == 1

    desc = {
        'has_constraint_any': {
            'n_yes': int(has_cons.sum()),
            'pct_yes': float(has_cons.mean()),
        },
        'constraint_type_distribution': type_dist,
        'constraint_density': {
            'mean_all': float(df['constraint_density'].mean()),
            'mean_among_constrained': float(df[has_cons]['constraint_density'].mean()),
            'std_among_constrained': float(df[has_cons]['constraint_density'].std()),
            'median_among_constrained': float(df[has_cons]['constraint_density'].median()),
            'min': float(df.loc[has_cons, 'constraint_density'].min()),
            'max': float(df.loc[has_cons, 'constraint_density'].max()),
        },
        'constraint_richness_distribution': df['constraint_richness'].value_counts().sort_index().to_dict(),
        'subtype_means': {
            'prohibitive': float(df['constraint_prohibitive'].mean()),
            'preservative': float(df['constraint_preservative'].mean()),
            'obligative': float(df['constraint_obligative'].mean()),
            'restrictive': float(df['constraint_restrictive'].mean()),
        },
    }
    save_json_csv(desc, '02_constraint_features',
                  df[['constraint_prohibitive','constraint_preservative',
                      'constraint_obligative','constraint_restrictive',
                      'constraint_total','constraint_density','constraint_richness']].describe())
    print(f"有约束词: {desc['has_constraint_any']['n_yes']} ({desc['has_constraint_any']['pct_yes']:.1%})")
    print(f"约束类型分布: {type_dist}")
    print(f"约束任务密度均值: {desc['constraint_density']['mean_among_constrained']:.3f}")
    return df


if __name__ == '__main__':
    df = step0_prepare_data()
    df = step1_verification_features(df)
    df = step2_constraint_features(df)
    # 保存带特征的数据供后续步骤使用
    df.to_parquet(os.path.join(RESULT_DIR, 'prepared_data.parquet'))
    print(f"\n数据已保存: {os.path.join(RESULT_DIR, 'prepared_data.parquet')}")
    print(f"列: {list(df.columns)}")
