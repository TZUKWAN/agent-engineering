# -*- coding: utf-8 -*-
import pandas as pd

cp = pd.read_csv('paper04_reasoning_typology/results/tables/cluster_profiles_labeled.csv')
feat = [c for c in cp.columns if c.endswith('_log1p') or c == 'reasoning_action_alignment']
print(cp[['reasoning_type_label'] + feat].round(2).to_string())

r = pd.read_parquet('data/interim/paper05/prompt_risk_features.parquet')
rf = [c for c in r.columns if c not in ('task_id', 'risk_index', 'word_count', 'os')]
print(r[rf].mean().round(3).to_string())
