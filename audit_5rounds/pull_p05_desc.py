# -*- coding: utf-8 -*-
import pandas as pd

r = pd.read_parquet('data/interim/paper05/prompt_risk_features.parquet')
e = pd.read_parquet('data/interim/paper05/reasoning_execution_errors.parquet')
print('risk_index mean/sd:', round(r['risk_index'].mean(), 3), round(r['risk_index'].std(), 3))
for c in ['reasoning_error_index', 'execution_error_index']:
    print(c, round(e[c].mean(), 3), round(e[c].std(), 3))
df = e.merge(r[['task_id']], on='task_id', how='left') if False else e
t = pd.read_parquet('data/interim/paper05/tasks.parquet')[['task_id', 'task_completed', 'os']]
df = df.merge(t, on='task_id', how='left')
df['grp'] = pd.qcut(df['execution_error_index'], 4, duplicates='drop')
print(df.groupby('grp', observed=True).agg(n=('task_id', 'size'), comp=('task_completed', 'mean')).round(3).to_string())
print('os comp:', df.groupby('os')['task_completed'].mean().round(3).to_dict())
