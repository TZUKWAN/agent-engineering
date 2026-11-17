# -*- coding: utf-8 -*-
"""MATLABINTOKEN 管道不变量冒烟测试（R2 审计补齐；此前 tests/ 为空目录）。

运行：python -m pytest tests -q   或   python tests/test_pipeline_invariants.py
需要先完成数据构建与统计分析（reproduce.sh 的 03–10 步）。
"""
import json
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_analysis_data_unique_task_ids():
    df = pd.read_parquet(os.path.join(ROOT, "data/processed/analysis_data.parquet"))
    assert df["task_id"].is_unique, "analysis_data 存在重复 task_id（R1 修复的合并膨胀会再次出现）"


def test_dedup_audit_consistent():
    p = os.path.join(ROOT, "data/interim/dedup_audit.json")
    assert os.path.exists(p), "缺少去重审计文件"
    audit = json.load(open(p, encoding="utf-8"))
    assert audit["raw_record_count"] - audit["dropped_count"] == audit["unique_task_count"]
    assert audit["unique_task_count"] == 22532, "唯一任务数应与官方 meta_data_merged.jsonl 一致"


def test_table3_pvalues_in_range():
    df = pd.read_csv(os.path.join(ROOT, "results/tables/table3_main_results.csv"))
    pcol = [c for c in df.columns if "p" in c.lower()][0]
    assert df[pcol].between(0, 1).all(), "table3 存在 [0,1] 之外的 p 值（R1 修复的公式 bug）"


def test_paper05_model1_has_inference_columns():
    df = pd.read_csv(os.path.join(ROOT, "paper05_prompt_risk_failure/results/tables/model1_risk_to_reasoning.csv"))
    for col in ("se", "p"):
        assert col in df.columns, f"paper05 model1 缺 {col} 列（R1 问题 B4）"


def test_stage1_presence_model_registered():
    p = os.path.join(ROOT, "results/papers/paper02/02_quadratic_results.json")
    d = json.load(open(p, encoding="utf-8"))
    assert "stage1_presence_model" in d and "stage2_constrained_quadratic" in d


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("PASS", name)
            except AssertionError as e:
                fails += 1
                print("FAIL", name, "-", e)
    sys.exit(1 if fails else 0)
