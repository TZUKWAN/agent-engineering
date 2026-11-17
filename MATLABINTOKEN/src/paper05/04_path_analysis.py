"""
04_path_analysis.py - 提示风险 → 推理错误 → 执行错误 → 任务失败路径分析（论文五）

使用 OLS 和 Logistic 回归构建观察性统计路径，并通过 bootstrap 估计间接效应。
"""

import json
import pandas as pd
import numpy as np
import statsmodels.formula.api as smf
from pathlib import Path
from scipy import stats

INTERIM_DIR = Path("data/interim/paper05")
RESULTS_DIR = Path("paper05_prompt_risk_failure/results/tables")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

RANDOM_SEED = 42


def bootstrap_sequential_mediation(df, x, m1, m2, y, controls, n_boot=500):
    """
    顺序中介：x -> m1 -> m2 -> y
    同时估计 x -> m1 (a), m1 -> m2 (b), m2 -> y (c)
    间接效应 = a * b * c
    """
    np.random.seed(RANDOM_SEED)
    n = len(df)
    indirect_effects = []
    for _ in range(n_boot):
        sample = df.sample(n=n, replace=True)
        # model 1: x -> m1
        f1 = f"{m1} ~ {x}" + (" + " + " + ".join(controls) if controls else "")
        r1 = smf.ols(f1, data=sample).fit()
        a = r1.params[x]

        # model 2: m1 -> m2
        f2 = f"{m2} ~ {m1} + {x}" + (" + " + " + ".join(controls) if controls else "")
        r2 = smf.ols(f2, data=sample).fit()
        b = r2.params[m1]

        # model 3: m2 -> y
        f3 = f"{y} ~ {m2} + {m1} + {x}" + (" + " + " + ".join(controls) if controls else "")
        r3 = smf.logit(f3, data=sample).fit(disp=False)
        c = r3.params[m2]

        indirect_effects.append(a * b * c)

    indirect_effects = np.array(indirect_effects)
    return {
        "indirect_mean": float(np.mean(indirect_effects)),
        "indirect_median": float(np.median(indirect_effects)),
        "indirect_se": float(np.std(indirect_effects)),
        "ci_lower": float(np.percentile(indirect_effects, 2.5)),
        "ci_upper": float(np.percentile(indirect_effects, 97.5)),
        "prop_positive": float(np.mean(indirect_effects > 0)),
    }


def main():
    print("=" * 60)
    print("论文五：提示风险—推理错误—执行错误—任务失败路径分析")
    print("=" * 60)

    risk = pd.read_parquet(INTERIM_DIR / "prompt_risk_features.parquet")
    err = pd.read_parquet(INTERIM_DIR / "reasoning_execution_errors.parquet")

    df = risk.merge(err[["task_id", "reasoning_error_index", "execution_error_index",
                           "incorrect_steps", "redundant_steps", "incorrect_ratio", "redundant_ratio",
                           "total_steps"]], on="task_id", how="inner")
    df["completed_num"] = df["task_completed"].fillna(False).astype(int)
    df["word_count_c"] = df["word_count"] - df["word_count"].mean()

    # 基本相关矩阵
    corr_vars = ["risk_index", "reasoning_error_index", "execution_error_index", "completed_num"]
    corr = df[corr_vars].corr()
    corr.to_csv(RESULTS_DIR / "correlation_matrix.csv")
    print("\n相关矩阵:")
    print(corr)

    controls = ["task_difficulty", "word_count_c", "C(os)"]

    # 模型 1: 风险 -> 推理错误
    f1 = f"reasoning_error_index ~ risk_index + {' + '.join(controls)}"
    m1 = smf.ols(f1, data=df).fit()
    print("\n模型 1: 风险指数 → 推理错误指数")
    print(m1.summary().tables[1])
    pd.DataFrame({"coef": m1.params, "se": m1.bse, "t": m1.tvalues, "p": m1.pvalues}).to_csv(
        RESULTS_DIR / "model1_risk_to_reasoning.csv")

    # 模型 2: 推理错误 -> 执行错误（控制风险）
    f2 = f"execution_error_index ~ reasoning_error_index + risk_index + {' + '.join(controls)}"
    m2 = smf.ols(f2, data=df).fit()
    print("\n模型 2: 推理错误指数 → 执行错误指数")
    print(m2.summary().tables[1])
    pd.DataFrame({"coef": m2.params, "se": m2.bse, "t": m2.tvalues, "p": m2.pvalues}).to_csv(
        RESULTS_DIR / "model2_reasoning_to_execution.csv")

    # 模型 3: 执行错误 -> 任务失败（控制推理错误和风险）
    f3 = f"completed_num ~ execution_error_index + reasoning_error_index + risk_index + {' + '.join(controls)}"
    m3 = smf.logit(f3, data=df).fit(disp=False)
    print("\n模型 3: 执行/推理错误指数 → 任务完成")
    print(pd.DataFrame({"coef": m3.params, "OR": np.exp(m3.params), "p": m3.pvalues}))
    pd.DataFrame({"coef": m3.params, "OR": np.exp(m3.params), "p": m3.pvalues}).to_csv(
        RESULTS_DIR / "model3_errors_to_completion.csv")

    # 模型 4: 风险 -> 任务完成（总效应）
    f4 = f"completed_num ~ risk_index + {' + '.join(controls)}"
    m4 = smf.logit(f4, data=df).fit(disp=False)
    print("\n模型 4: 风险指数 → 任务完成（总效应）")
    print(pd.DataFrame({"coef": m4.params, "OR": np.exp(m4.params), "p": m4.pvalues}))
    pd.DataFrame({"coef": m4.params, "OR": np.exp(m4.params), "p": m4.pvalues}).to_csv(
        RESULTS_DIR / "model4_risk_to_completion.csv")

    # Bootstrap 顺序中介
    print("\n正在进行 bootstrap 顺序中介分析（500 次）...")
    med = bootstrap_sequential_mediation(
        df, x="risk_index", m1="reasoning_error_index", m2="execution_error_index",
        y="completed_num", controls=controls, n_boot=500)
    print(med)
    with open(RESULTS_DIR / "mediation_bootstrap.json", "w", encoding="utf-8") as f:
        json.dump(med, f, ensure_ascii=False, indent=2)

    # 单独风险特征对推理错误的影响
    risk_features = [
        "goal_abstraction", "object_missing", "completion_standard_missing",
        "constraint_missing", "constraint_overdense", "multi_subtask_no_order",
        "constraint_conflict", "vague_reference", "initial_state_missing", "verification_missing",
    ]
    for feat in risk_features:
        df[feat] = df[feat].astype(int)
    single_results = []
    for feat in risk_features:
        f = f"reasoning_error_index ~ {feat} + task_difficulty + word_count_c + C(os)"
        r = smf.ols(f, data=df).fit()
        single_results.append({
            "feature": feat,
            "coef": r.params[feat],
            "se": r.bse[feat],
            "p": r.pvalues[feat],
        })
    single_df = pd.DataFrame(single_results)
    single_df.to_csv(RESULTS_DIR / "single_risk_feature_to_reasoning.csv", index=False)
    print("\n单独风险特征 → 推理错误指数:")
    print(single_df)

    # 保存分析就绪数据
    df.to_parquet(INTERIM_DIR / "analysis_ready.parquet")
    print(f"\n分析就绪数据保存到 {INTERIM_DIR / 'analysis_ready.parquet'}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
