"""
运行完整统计分析并生成真实结果
"""

import os
import pandas as pd
import numpy as np
from scipy import stats
import statsmodels.api as sm
from statsmodels.formula.api import ols, logit
import json

def load_data():
    """加载分析数据"""
    df = pd.read_parquet("data/processed/analysis_data.parquet")
    print(f"加载数据: {len(df)} 个样本")
    return df

def analyze_rq1(df):
    """
    RQ1: 操作显性度与任务完成率的关系
    H1: 操作显性度越高，任务完成率越高
    """
    print("\n" + "="*60)
    print("RQ1: 操作显性度与任务完成率")
    print("="*60)

    results = {}

    # 相关性分析
    if 'task_completed' in df.columns and 'explicitness_score' in df.columns:
        # Point-biserial correlation
        df_valid = df.dropna(subset=['task_completed', 'explicitness_score'])
        if len(df_valid) > 0:
            corr, pval = stats.pointbiserialr(
                df_valid['explicitness_score'],
                df_valid['task_completed'].astype(int)
            )
            results['correlation'] = {
                'coefficient': float(corr),
                'p_value': float(pval),
                'n': len(df_valid)
            }
            print(f"\n相关性分析:")
            print(f"  相关系数 (r): {corr:.3f}")
            print(f"  P值: {pval:.4f}")
            print(f"  样本数: {len(df_valid)}")

    # 分组比较
    if 'explicitness_level' in df.columns and 'task_completed' in df.columns:
        level_groups = df.groupby('explicitness_level')['task_completed']
        print(f"\n分组完成率:")
        completion_rates = {}
        for level in ['low', 'medium', 'high']:
            if level in level_groups.groups:
                group = level_groups.get_group(level)
                rate = group.mean()
                n = len(group)
                completion_rates[level] = {'rate': float(rate), 'n': n}
                print(f"  {level}: {rate:.1%} (n={n})")

        results['completion_rates'] = completion_rates

        # 卡方检验
        if len(completion_rates) >= 2:
            # 创建列联表
            contingency = pd.crosstab(df['explicitness_level'], df['task_completed'])
            chi2, p, dof, expected = stats.chi2_contingency(contingency)
            results['chi_square'] = {
                'chi2': float(chi2),
                'p_value': float(p),
                'dof': dof
            }
            print(f"\n卡方检验:")
            print(f"  χ²({dof}) = {chi2:.2f}, p = {p:.4f}")

    return results

def analyze_rq2(df):
    """
    RQ2: 操作显性度与效率的关系
    H2: 操作显性度越高，效率评分越高，步骤越少
    """
    print("\n" + "="*60)
    print("RQ2: 操作显性度与效率")
    print("="*60)

    results = {}

    # 效率评分相关
    if 'efficiency_score' in df.columns and 'explicitness_score' in df.columns:
        df_valid = df.dropna(subset=['efficiency_score', 'explicitness_score'])
        if len(df_valid) > 0:
            corr, pval = stats.pearsonr(
                df_valid['explicitness_score'],
                df_valid['efficiency_score']
            )
            results['efficiency_correlation'] = {
                'coefficient': float(corr),
                'p_value': float(pval),
                'n': len(df_valid)
            }
            print(f"\n效率评分相关性:")
            print(f"  r = {corr:.3f}, p = {pval:.4f}, n = {len(df_valid)}")

            # 分组比较
            if 'explicitness_level' in df.columns:
                level_efficiency = df.groupby('explicitness_level')['efficiency_score'].agg(['mean', 'std', 'count'])
                print(f"\n分组效率评分:")
                print(level_efficiency)
                results['efficiency_by_level'] = level_efficiency.to_dict()

    # 步骤数相关
    if 'total_steps' in df.columns and 'explicitness_score' in df.columns:
        df_valid = df.dropna(subset=['total_steps', 'explicitness_score'])
        if len(df_valid) > 0:
            corr, pval = stats.pearsonr(
                df_valid['explicitness_score'],
                df_valid['total_steps']
            )
            results['steps_correlation'] = {
                'coefficient': float(corr),
                'p_value': float(pval),
                'n': len(df_valid)
            }
            print(f"\n步骤数相关性:")
            print(f"  r = {corr:.3f}, p = {pval:.4f}, n = {len(df_valid)}")

    return results

def analyze_rq3(df):
    """
    RQ3: 操作显性度与对齐度的关系
    H3: 操作显性度越高，对齐评分越高
    """
    print("\n" + "="*60)
    print("RQ3: 操作显性度与对齐度")
    print("="*60)

    results = {}

    if 'alignment_score' in df.columns and 'explicitness_score' in df.columns:
        df_valid = df.dropna(subset=['alignment_score', 'explicitness_score'])
        if len(df_valid) > 0:
            corr, pval = stats.pearsonr(
                df_valid['explicitness_score'],
                df_valid['alignment_score']
            )
            results['alignment_correlation'] = {
                'coefficient': float(corr),
                'p_value': float(pval),
                'n': len(df_valid)
            }
            print(f"\n对齐评分相关性:")
            print(f"  r = {corr:.3f}, p = {pval:.4f}, n = {len(df_valid)}")

            # 分组比较
            if 'explicitness_level' in df.columns:
                level_alignment = df.groupby('explicitness_level')['alignment_score'].agg(['mean', 'std', 'count'])
                print(f"\n分组对齐评分:")
                print(level_alignment)
                results['alignment_by_level'] = level_alignment.to_dict()

    return results

def analyze_rq4(df):
    """
    RQ4: 操作显性度与过程质量的关系
    H4: 操作显性度越高，正确步骤比例越高，错误/冗余步骤比例越低
    """
    print("\n" + "="*60)
    print("RQ4: 操作显性度与过程质量")
    print("="*60)

    results = {}

    process_metrics = ['correct_ratio', 'incorrect_ratio', 'redundant_ratio']

    for metric in process_metrics:
        if metric in df.columns and 'explicitness_score' in df.columns:
            df_valid = df.dropna(subset=[metric, 'explicitness_score'])
            if len(df_valid) > 0:
                corr, pval = stats.pearsonr(
                    df_valid['explicitness_score'],
                    df_valid[metric]
                )
                results[f'{metric}_correlation'] = {
                    'coefficient': float(corr),
                    'p_value': float(pval),
                    'n': len(df_valid)
                }
                print(f"\n{metric}:")
                print(f"  r = {corr:.3f}, p = {pval:.4f}, n = {len(df_valid)}")

    return results

def analyze_rq5(df):
    """
    RQ5: 不同显性度特征的相对重要性
    H5: 不同显性度特征对效能的预测力不同
    """
    print("\n" + "="*60)
    print("RQ5: 特征相对重要性")
    print("="*60)

    results = {}

    feature_names = [
        'has_application', 'has_operation_object', 'has_target_action',
        'has_target_state', 'has_file_reference', 'has_object_properties',
        'has_operation_order', 'has_multiple_subtasks', 'has_constraint_words',
        'has_completion_criteria', 'has_initial_state'
    ]

    # 检查哪些特征可用
    available_features = [f for f in feature_names if f in df.columns]

    if available_features and 'task_completed' in df.columns:
        # 单特征与完成率的关系
        feature_effects = {}
        print(f"\n各特征的完成率差异:")
        for feature in available_features:
            if df[feature].dtype == bool or df[feature].nunique() <= 2:
                # 二分类特征
                groups = df.groupby(feature)['task_completed']
                if len(groups.groups) == 2:
                    true_rate = groups.get_group(True).mean() if True in groups.groups else None
                    false_rate = groups.get_group(False).mean() if False in groups.groups else None
                    n_true = len(groups.get_group(True)) if True in groups.groups else 0
                    n_false = len(groups.get_group(False)) if False in groups.groups else 0

                    if true_rate is not None and false_rate is not None:
                        diff = true_rate - false_rate

                        # Fisher精确检验或卡方
                        try:
                            contingency = pd.crosstab(df[feature], df['task_completed'])
                            if (contingency.values >= 5).all():
                                chi2, p, _, _ = stats.chi2_contingency(contingency)
                            else:
                                # Fisher精确检验（2x2）
                                oddsratio, p = stats.fisher_exact(contingency)
                        except:
                            p = np.nan

                        feature_effects[feature] = {
                            'true_rate': float(true_rate),
                            'false_rate': float(false_rate),
                            'difference': float(diff),
                            'n_true': n_true,
                            'n_false': n_false,
                            'p_value': float(p) if not np.isnan(p) else None
                        }
                        print(f"  {feature}: {true_rate:.1%} vs {false_rate:.1%} (diff: {diff:+.1%}, p={p:.3f})")

        results['feature_effects'] = feature_effects

        # 按差异排序
        if feature_effects:
            sorted_features = sorted(
                feature_effects.items(),
                key=lambda x: abs(x[1]['difference']),
                reverse=True
            )
            print(f"\n按效应量排序:")
            for i, (feature, effect) in enumerate(sorted_features[:5], 1):
                print(f"  {i}. {feature}: 差异 {effect['difference']:+.1%}")

            results['sorted_features'] = [(f, float(e['difference'])) for f, e in sorted_features]

    return results

def descriptive_statistics(df):
    """生成描述性统计"""
    print("\n" + "="*60)
    print("描述性统计")
    print("="*60)

    stats_dict = {}

    # 样本数
    stats_dict['n_total'] = len(df)

    # 任务完成率
    if 'task_completed' in df.columns:
        completion_rate = df['task_completed'].mean()
        stats_dict['completion_rate'] = float(completion_rate)
        print(f"\n任务完成率: {completion_rate:.1%}")
        print(f"  完成: {df['task_completed'].sum()}")
        print(f"  未完成: {(~df['task_completed']).sum()}")

    # 显性度分布
    if 'explicitness_score' in df.columns:
        print(f"\n显性度分数:")
        print(f"  均值: {df['explicitness_score'].mean():.2f}")
        print(f"  标准差: {df['explicitness_score'].std():.2f}")
        print(f"  最小值: {df['explicitness_score'].min()}")
        print(f"  最大值: {df['explicitness_score'].max()}")
        stats_dict['explicitness_score'] = {
            'mean': float(df['explicitness_score'].mean()),
            'std': float(df['explicitness_score'].std()),
            'min': int(df['explicitness_score'].min()),
            'max': int(df['explicitness_score'].max())
        }

    if 'explicitness_level' in df.columns:
        print(f"\n显性度级别分布:")
        level_counts = df['explicitness_level'].value_counts()
        for level, count in level_counts.items():
            print(f"  {level}: {count} ({count/len(df):.1%})")
        stats_dict['explicitness_levels'] = level_counts.to_dict()

    # 评分统计
    for score_col in ['efficiency_score', 'alignment_score', 'task_difficulty']:
        if score_col in df.columns:
            print(f"\n{score_col}:")
            print(f"  均值: {df[score_col].mean():.2f}")
            print(f"  标准差: {df[score_col].std():.2f}")
            stats_dict[score_col] = {
                'mean': float(df[score_col].mean()),
                'std': float(df[score_col].std())
            }

    # 步骤统计
    if 'total_steps' in df.columns:
        print(f"\n步骤数:")
        print(f"  均值: {df['total_steps'].mean():.1f}")
        print(f"  标准差: {df['total_steps'].std():.1f}")
        print(f"  总步骤: {df['total_steps'].sum()}")
        stats_dict['steps'] = {
            'mean': float(df['total_steps'].mean()),
            'std': float(df['total_steps'].std()),
            'total': int(df['total_steps'].sum())
        }

    # 特征流行度
    feature_names = [
        'has_application', 'has_operation_object', 'has_target_action',
        'has_target_state', 'has_file_reference', 'has_object_properties',
        'has_operation_order', 'has_multiple_subtasks', 'has_constraint_words',
        'has_completion_criteria', 'has_initial_state'
    ]

    available_features = [f for f in feature_names if f in df.columns]
    if available_features:
        print(f"\n特征流行度:")
        feature_popularity = {}
        for feature in available_features:
            pop = df[feature].mean()
            feature_popularity[feature] = float(pop)
            print(f"  {feature}: {pop:.1%}")
        stats_dict['feature_popularity'] = feature_popularity

    return stats_dict

def main():
    """主分析函数"""
    print("="*60)
    print("AgentNet实证研究统计分析")
    print("="*60)

    # 加载数据
    df = load_data()

    # 描述性统计
    desc_stats = descriptive_statistics(df)

    # RQ1
    rq1_results = analyze_rq1(df)

    # RQ2
    rq2_results = analyze_rq2(df)

    # RQ3
    rq3_results = analyze_rq3(df)

    # RQ4
    rq4_results = analyze_rq4(df)

    # RQ5
    rq5_results = analyze_rq5(df)

    # 保存所有结果
    all_results = {
        'descriptive': desc_stats,
        'rq1': rq1_results,
        'rq2': rq2_results,
        'rq3': rq3_results,
        'rq4': rq4_results,
        'rq5': rq5_results
    }

    os.makedirs("results", exist_ok=True)

    with open("results/analysis_results.json", 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\n" + "="*60)
    print("分析完成!")
    print("="*60)
    print(f"\n结果已保存: results/analysis_results.json")

    return all_results

if __name__ == "__main__":
    main()
