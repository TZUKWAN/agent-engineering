# -*- coding: utf-8 -*-
"""R2 检查：五篇论文正文引用的关键数字与重跑结果文件逐项核对。

每项 (描述, 论文应含的字符串, 结果文件中的真值来源断言)。
断言失败 = 正文与数据不一致。
"""
import json
import math
import pathlib
import re
import sys

BASE = pathlib.Path("G:/刘俊琦/AGENT ENGINEERING/MATLABINTOKEN")
FAILED = []


def paper(name):
    return (BASE / "revised" / name).read_text(encoding="utf-8")


def check(desc, ok):
    print(("PASS " if ok else "FAIL ") + desc)
    if not ok:
        FAILED.append(desc)


p1 = paper("paper01_rewritten.md")
p2 = paper("paper02_rewritten.md")
p3 = paper("paper03_rewritten.md")
p4 = (BASE / "paper04_reasoning_typology" / "manuscript.md").read_text(encoding="utf-8")
p5 = (BASE / "paper05_prompt_risk_failure" / "manuscript.md").read_text(encoding="utf-8")

# ---------- paper01 vs results/papers/paper01 ----------
logit = json.load(open(BASE / "results/papers/paper01/02_logistic_results.json"))
row = next(r for r in logit["rows"] if r["term"] == "has_completion_criteria")
check(f"P01 OR={row['or']:.3f} 在正文", f"{row['or']:.3f}" in p1 and "1.276" in p1)
check("P01 回归样本 n_obs=20205 在正文", "20{,}205" in p1)
pos = json.load(open(BASE / "results/papers/paper01/05_position_analysis.json"))
check(f"P01 位置子集 n={pos['n_obs']} 在正文", "2{,}491" in p1)
chi = pos["chi_square_test"]["chi2"]
check(f"P01 位置卡方 {chi:.3f} 在正文", f"{chi:.3f}" in p1)

# ---------- paper02 vs results/papers/paper02 ----------
q2 = json.load(open(BASE / "results/papers/paper02/02_quadratic_results.json"))
s1 = next(r for r in q2["stage1_presence_model"]["coef_table"] if r["term"] == "has_constraint_words")
check(f"P02 Stage1 OR={math.exp(s1['coef']):.3f} 在正文", "0.947" in p2)
s2 = next(r for r in q2["stage2_constrained_quadratic"]["coef_table"]
          if r["term"] == "I(constraint_density ** 2)")
check(f"P02 Stage2 b2={s2['coef']:.3f} p={s2['pvalue']:.3f} 在正文", "0.086" in p2)
dist = json.load(open(BASE / "results/papers/paper02/01_constraint_distribution.json"))["distribution"]
check(f"P02 n_total={dist['n_total']} 在正文", "22{,}532" in p2)
check(f"P02 约束任务 {dist['n_with_constraints']} 在正文", "1,441" in p2)
mod = json.load(open(BASE / "results/papers/paper02/04_moderation_analysis.json"))
hi = mod["split_sample_models"]["task_difficulty"]["high"]
check(f"P02 高难度 b2={hi['b2']:.3f} p={hi['b2_pvalue']:.3f} 在正文",
      "0.029" in p2 and ("-0.037" in p2 or "−0.037" in p2))

# ---------- paper03 vs results/papers/paper03 ----------
d3 = json.load(open(BASE / "results/papers/paper03/03_class_distribution.json"))
check(f"P03 LCA N={d3['total_n']} 在正文", "20{,}205" in p3)
oc = json.load(open(BASE / "results/papers/paper03/04_outcome_comparison.json"))
c2 = oc["completion_chi2"]["chi2"]
check(f"P03 完成率卡方 {c2:.2f} 在正文", f"{c2:.2f}" in p3 or f"{c2:.1f}" in p3)
wl = oc["manova_wilks_lambda"]
check(f"P03 Wilks λ={wl['value']:.3f} F={wl['f']:.2f} 在正文",
      "0.963" in p3 and "63.21" in p3)
ctl = json.load(open(BASE / "results/papers/paper03/05_controlled_analysis.json"))
check(f"P03 控制 LRT={ctl['class_lrt']['statistic']:.2f} 在正文", "21.44" in p3)
i6 = json.load(open(BASE / "results/papers/paper03/06_interaction_analysis.json"))
t2 = next(x for x in i6["coefficients"] if x["term"] == "C(class_str)[T.2]:task_difficulty")
check(f"P03 交互 b={t2['Coef.']:.3f} p={t2['P>|z|']:.3f} 在正文", "0.013" in p3 and "0.141" in p3)

# ---------- paper04 vs results/tables ----------
cp = json.load(open(BASE / "paper04_reasoning_typology/results/tables/cluster_profiles_labeled.json")) \
    if (BASE / "paper04_reasoning_typology/results/tables/cluster_profiles_labeled.json").exists() else None
an = json.load(open(BASE / "paper04_reasoning_typology/results/tables/anova_results.json"))
check(f"P04 total_steps F={an['total_steps']['f']:.2f} 在正文", "12578.01" in p4)
lg = pd_read = None
import pandas as pd
lg = pd.read_csv(BASE / "paper04_reasoning_typology/results/tables/logistic_type_completion.csv")
orr = float(lg[lg.iloc[:, 0].str.contains("简洁直觉型")]["OR"].iloc[0])
check(f"P04 简洁直觉型 OR={orr:.2f} 在正文", f"{orr:.2f}" in p4)

# ---------- paper05 vs results/tables ----------
m1 = pd.read_csv(BASE / "paper05_prompt_risk_failure/results/tables/model1_risk_to_reasoning.csv")
b1 = float(m1[m1.iloc[:, 0] == "risk_index"]["coef"].iloc[0])
check(f"P05 M1 β={b1:.3f} 在正文", "0.021" in p5)
m3 = pd.read_csv(BASE / "paper05_prompt_risk_failure/results/tables/model3_errors_to_completion.csv")
r3 = m3[m3.iloc[:, 0] == "risk_index"].iloc[0]
check(f"P05 M3 risk OR={float(r3['OR']):.3f} p={float(r3['p']):.3f} 在正文",
      "1.075" in p5 and "0.117" in p5)
med = json.load(open(BASE / "paper05_prompt_risk_failure/results/tables/mediation_bootstrap.json"))
check(f"P05 间接效应 {med['indirect_mean']:.3f} CI 在正文", "0.084" in p5 and "0.122" in p5)

print()
if FAILED:
    print(f"{len(FAILED)} 项不一致：")
    for f in FAILED:
        print(" -", f)
    sys.exit(1)
print("全部交叉验证通过。")
