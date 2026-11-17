"""
完成全量数据分析 - 修复类型问题
"""

import os
import json
import pandas as pd
import numpy as np
from scipy import stats

def main():
    print("=" * 70)
    print("完成全量数据分析")
    print("=" * 70)
    
    # 读取已解析的数据
    df = pd.read_parquet("data/processed/analysis_data.parquet")
    
    # 确保数据类型正确
    df['task_completed'] = pd.to_numeric(df['task_completed'], errors='coerce')
    df['explicitness_score'] = pd.to_numeric(df['explicitness_score'], errors='coerce')
    df['efficiency_score'] = pd.to_numeric(df['efficiency_score'], errors='coerce')
    df['alignment_score'] = pd.to_numeric(df['alignment_score'], errors='coerce')
    df['total_steps'] = pd.to_numeric(df['total_steps'], errors='coerce')
    df['correct_ratio'] = pd.to_numeric(df['correct_ratio'], errors='coerce')
    df['incorrect_ratio'] = pd.to_numeric(df['incorrect_ratio'], errors='coerce')
    df['redundant_ratio'] = pd.to_numeric(df['redundant_ratio'], errors='coerce')
    
    # 统计分析
    print("\n进行统计分析...")
    
    results = {
        'sample_info': {
            'n': len(df),
            'n_win_mac': len(df[df['os'] == 'win_mac']),
            'n_ubuntu': len(df[df['os'] == 'ubuntu']),
            'completion_rate': float(df['task_completed'].mean()),
            'mean_explicitness': float(df['explicitness_score'].mean()),
            'sd_explicitness': float(df['explicitness_score'].std())
        }
    }
    
    # RQ1
    valid_rq1 = df[df['task_completed'].notna() & df['explicitness_score'].notna()]
    if len(valid_rq1) > 10:
        corr_rq1 = stats.pearsonr(valid_rq1['explicitness_score'].astype(float), 
                                 valid_rq1['task_completed'].astype(float))
        results['rq1'] = {
            'correlation': {'coefficient': float(corr_rq1[0]), 'p_value': float(corr_rq1[1])}
        }
        
        by_level = valid_rq1.groupby('explicitness_level')['task_completed'].agg(['mean', 'count'])
        results['rq1']['completion_rates'] = {
            level: {'rate': float(row['mean']), 'n': int(row['count'])}
            for level, row in by_level.iterrows()
        }
    
    # RQ2
    valid_eff = df[df['efficiency_score'].notna() & df['explicitness_score'].notna()]
    if len(valid_eff) > 10:
        corr_eff = stats.pearsonr(valid_eff['explicitness_score'].astype(float), 
                                 valid_eff['efficiency_score'].astype(float))
        corr_steps = stats.pearsonr(valid_eff['explicitness_score'].astype(float), 
                                   valid_eff['total_steps'].astype(float))
        results['rq2'] = {
            'efficiency_correlation': {'coefficient': float(corr_eff[0]), 'p_value': float(corr_eff[1])},
            'steps_correlation': {'coefficient': float(corr_steps[0]), 'p_value': float(corr_steps[1])}
        }
    
    # RQ3
    valid_align = df[df['alignment_score'].notna() & df['explicitness_score'].notna()]
    if len(valid_align) > 10:
        corr_align = stats.pearsonr(valid_align['explicitness_score'].astype(float), 
                                   valid_align['alignment_score'].astype(float))
        results['rq3'] = {
            'alignment_correlation': {'coefficient': float(corr_align[0]), 'p_value': float(corr_align[1])}
        }
    
    # RQ4
    valid_proc = df[df['correct_ratio'].notna() & df['explicitness_score'].notna()]
    if len(valid_proc) > 10:
        corr_incorr = stats.pearsonr(valid_proc['explicitness_score'].astype(float), 
                                    valid_proc['incorrect_ratio'].astype(float))
        corr_red = stats.pearsonr(valid_proc['explicitness_score'].astype(float), 
                                 valid_proc['redundant_ratio'].astype(float))
        results['rq4'] = {
            'incorrect_ratio_correlation': {'coefficient': float(corr_incorr[0]), 'p_value': float(corr_incorr[1])},
            'redundant_ratio_correlation': {'coefficient': float(corr_red[0]), 'p_value': float(corr_red[1])}
        }
    
    # RQ5
    feature_cols = [c for c in df.columns if c.startswith('has_')]
    feature_effects = {}
    for feat in feature_cols:
        with_feat = df[df[feat] == 1]['task_completed'].mean()
        without_feat = df[df[feat] == 0]['task_completed'].mean()
        feature_effects[feat] = {
            'with_feature': float(with_feat),
            'without_feature': float(without_feat),
            'difference': float(with_feat - without_feat)
        }
    results['rq5'] = {'feature_effects': feature_effects}
    
    # 保存结果
    with open("results/analysis_results.json", 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # 更新main_results
    main_results = {
        "rq1": {
            "correlation": results.get("rq1", {}).get("correlation", {}).get("coefficient", 0),
            "p_value": results.get("rq1", {}).get("correlation", {}).get("p_value", 1),
            "n": len(df),
            "by_level": {}
        },
        "rq2": {
            "efficiency_score": {
                "correlation": results.get("rq2", {}).get("efficiency_correlation", {}).get("coefficient", 0),
                "p_value": results.get("rq2", {}).get("efficiency_correlation", {}).get("p_value", 1),
                "n": len(df)
            },
            "alignment_score": {
                "correlation": results.get("rq3", {}).get("alignment_correlation", {}).get("coefficient", 0),
                "p_value": results.get("rq3", {}).get("alignment_correlation", {}).get("p_value", 1),
                "n": len(df)
            }
        },
        "rq3": {
            "incorrect_ratio": {
                "correlation": results.get("rq4", {}).get("incorrect_ratio_correlation", {}).get("coefficient", 0),
                "p_value": results.get("rq4", {}).get("incorrect_ratio_correlation", {}).get("p_value", 1),
                "n": len(df)
            },
            "redundant_ratio": {
                "correlation": results.get("rq4", {}).get("redundant_ratio_correlation", {}).get("coefficient", 0),
                "p_value": results.get("rq4", {}).get("redundant_ratio_correlation", {}).get("p_value", 1),
                "n": len(df)
            }
        },
        "rq4": {"error_mediation": {}, "redundant_mediation": {}},
        "correlation_matrix": {}
    }
    
    completion_rates = results.get("rq1", {}).get("completion_rates", {})
    for level, data in completion_rates.items():
        main_results["rq1"]["by_level"][level] = {"rate": data.get("rate", 0), "n": data.get("n", 0)}
    
    with open("results/models/main_results.json", 'w', encoding='utf-8') as f:
        json.dump(main_results, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 70)
    print("全量数据分析完成!")
    print(f"总任务数: {len(df)}")
    print(f"Windows/Mac: {results['sample_info']['n_win_mac']}")
    print(f"Ubuntu: {results['sample_info']['n_ubuntu']}")
    print("=" * 70)
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
