"""
01_classify_verification.py - 验证标准语言分类标注与分布统计
"""
import os
import numpy as np
import pandas as pd
from helpers import (
    SEED,
    RESULT_DIR,
    load_main_data,
    classify_verification,
    assign_verification_type,
    compute_verification_density,
    locate_first_verification_position,
    save_json_csv,
)

np.random.seed(SEED)


def main():
    print("Step 1: 验证标准分类标注")
    os.makedirs(RESULT_DIR, exist_ok=True)
    df = load_main_data()

    # 标注验证特征
    verification_features = df["instruction"].apply(classify_verification).apply(pd.Series)
    df = pd.concat([df, verification_features], axis=1)

    df["verification_type"] = df.apply(assign_verification_type, axis=1)
    df["verification_density"] = df.apply(compute_verification_density, axis=1)

    position_df = df["instruction"].apply(locate_first_verification_position).apply(pd.Series)
    df["verification_position_rel"] = position_df["relative_position"]
    df["verification_position_region"] = position_df["position_region"]

    # 保存带标注的数据（便于复现与后续论文使用）
    annotated_path = os.path.join(RESULT_DIR, "annotated_data.parquet")
    df.to_parquet(annotated_path, index=False)
    print(f"Saved annotated data: {annotated_path}")

    # 分布统计
    type_order = ["V0", "V1", "V2", "V3", "V4"]
    distribution_rows = []

    # 全量样本
    total_n = len(df)
    type_counts_all = df["verification_type"].value_counts().reindex(type_order, fill_value=0)
    type_props_all = (type_counts_all / total_n).round(6)

    # has_completion_criteria == 1 的子集
    criteria_df = df[df["has_completion_criteria"] == 1].copy()
    subset_n = len(criteria_df)
    type_counts_sub = criteria_df["verification_type"].value_counts().reindex(type_order, fill_value=0)
    type_props_sub = (type_counts_sub / subset_n).round(6)

    # 为每个类型随机抽取 5 条典型指令（V0 限定 has_completion_criteria==1；V1-V4 不限定）
    rng = np.random.default_rng(SEED)
    examples = {}
    for vt in type_order:
        if vt == "V0":
            sub = criteria_df[criteria_df["verification_type"] == vt]
        else:
            sub = df[df["verification_type"] == vt]
        if len(sub) == 0:
            examples[vt] = []
            continue
        # 优先选择词数适中（10-80 词）的样本，避免过长
        candidate = sub[(sub["word_count"] >= 10) & (sub["word_count"] <= 80)]
        if len(candidate) == 0:
            candidate = sub
        n_sample = min(5, len(candidate))
        sampled = candidate.sample(n=n_sample, random_state=rng)
        examples[vt] = sampled["instruction"].tolist()

    for vt in type_order:
        distribution_rows.append(
            {
                "verification_type": vt,
                "type_label": {
                    "V0": "不可分类/伪阳性",
                    "V1": "动词指令式",
                    "V2": "状态目标式",
                    "V3": "条件验证式",
                    "V4": "混合式",
                }[vt],
                "n_all": int(type_counts_all[vt]),
                "prop_all": float(type_props_all[vt]),
                "n_has_criteria": int(type_counts_sub[vt]),
                "prop_has_criteria": float(type_props_sub[vt]),
                "example_instructions": examples[vt],
            }
        )

    results = {
        "total_n": int(total_n),
        "has_criteria_n": int(subset_n),
        "classification_rules": {
            "v1_verbs": ["check", "verify", "confirm", "validate", "ensure", "make sure"],
            "v2_states": ["done", "complete", "correct", "proper", "finished", "ready"],
            "v3_conditions": ["until", "when", "once", "after"],
            "v3_heuristic": (
                "until 直接视为完成条件；when/once/after 仅当周围 15 词窗口内出现 V1/V2 关键词时，"
                "才视为完成条件，否则按时间/顺序状语排除。"
            ),
            "v4_rule": "至少同时出现 V1/V2/V3 中的两类",
            "v0_rule": "has_completion_criteria==1 但未命中任何 V1/V2/V3 关键词",
        },
        "distribution": distribution_rows,
    }

    save_json_csv(
        results,
        os.path.join(RESULT_DIR, "01_feature_distribution.json"),
        os.path.join(RESULT_DIR, "01_feature_distribution.csv"),
    )

    print("\n验证类型分布（has_completion_criteria==1 子集）：")
    for row in distribution_rows:
        print(
            f"  {row['verification_type']} {row['type_label']}: "
            f"{row['n_has_criteria']} ({row['prop_has_criteria']:.1%})"
        )


if __name__ == "__main__":
    main()
