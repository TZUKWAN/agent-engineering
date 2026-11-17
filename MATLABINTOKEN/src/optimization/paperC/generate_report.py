"""论文C: 生成结果报告"""
import json, os

RESULT_DIR = "results/optimization/paperC"
results = {}
for f in os.listdir(RESULT_DIR):
    if f.endswith('.json'):
        with open(os.path.join(RESULT_DIR, f), encoding='utf-8') as fp:
            results[f.replace('.json','')] = json.load(fp)

lines = []
lines.append("# 论文C：提示风险如何通过推理-指令对齐度影响任务结果 — 结果报告\n")

lines.append("## 1. 研究问题\n")
lines.append("1. 提示风险是否与推理-指令对齐度相关？")
lines.append("2. 对齐度是否与执行错误相关？")
lines.append("3. 提示风险是否通过对齐度→执行错误的间接路径影响任务完成？\n")

lines.append("## 2. 方法\n")
lines.append("### 2.1 对齐度指标构建（纯文本，无循环论证）\n")
lines.append("对齐度 = 指令中特定语用要素（约束词/验证词/分解词）在智能体推理文本中的**覆盖率**。")
lines.append("- alignment_deviation = 1 - 平均覆盖率（越高=对齐越差）")
lines.append("- 核心红线：不使用task_completed或步骤标签构建此指标\n")

ad = results.get('01_alignment_descriptives', {})
lines.append(f"- N = {ad.get('n_total', 'N/A')}")
lines.append(f"- 对齐偏差均值: {ad.get('alignment_deviation_mean', 0):.3f}")
lines.append(f"- 约束覆盖率均值: {ad.get('constraint_coverage_mean', 'N/A')}")
lines.append(f"- 验证覆盖率均值: {ad.get('verification_coverage_mean', 'N/A')}")
lines.append(f"- 分解覆盖率均值: {ad.get('decomposition_coverage_mean', 'N/A')}\n")

lines.append("## 3. 结果\n")
lines.append("### 3.1 提示风险 → 对齐度（H1）\n")
r3 = results.get('03_risk_to_alignment', {})
lines.append(f"- N = {r3.get('n', 0)}")
lines.append(f"- risk_index → alignment_deviation: β={r3.get('risk_index_coef', 0):.4f}, p={r3.get('risk_index_p', 0):.4f}")
lines.append(f"- R² = {r3.get('r_squared', 0):.4f}\n")

lines.append("单项风险效应：\n")
lines.append("| 风险特征 | β | p | 发生率 |")
lines.append("|---------|---|---|--------|")
for k, v in r3.get('single_risk_effects', {}).items():
    lines.append(f"| {k} | {v.get('coef',0):.4f} | {v.get('p',0):.4f} | {v.get('rate',0):.1%} |")

r3_sig = r3.get('risk_index_p', 1) < 0.05
lines.append(f"\n**H1结论**: {'支持' if r3_sig else '不支持'}。提示风险指数与对齐偏差的关联{'显著' if r3_sig else '不显著'}。")
lines.append("注：验证要求缺失（risk_verification_missing）是最显著的单项风险（β=0.0065, p=.004）。\n")

lines.append("### 3.2 对齐度 → 执行错误（H2）\n")
r4 = results.get('04_alignment_to_execution', {})
lines.append(f"- N = {r4.get('n', 0)}")
lines.append(f"- alignment_deviation → execution_error: β={r4.get('alignment_deviation_coef', 0):.4f}, p={r4.get('alignment_deviation_p', 0):.4f}")
r4_sig = r4.get('alignment_deviation_p', 1) < 0.05
lines.append(f"\n**H2结论**: {'支持' if r4_sig else '不支持'}。对齐偏差与执行错误的关联{'显著' if r4_sig else '不显著'}。\n")

lines.append("### 3.3 执行错误 → 任务完成（H3）\n")
r5 = results.get('05_errors_to_completion', {})
coeffs = r5.get('coefficients', {})
lines.append("| 变量 | OR | p |")
lines.append("|------|----|---|")
for term in ['alignment_deviation', 'execution_error', 'risk_index']:
    if term in coeffs:
        c = coeffs[term]
        lines.append(f"| {term} | {c.get('or',0):.4f} | {c.get('p',0):.4f} |")

exec_or = coeffs.get('execution_error', {}).get('or', 0)
exec_p = coeffs.get('execution_error', {}).get('p', 1)
lines.append(f"\n**H3结论**: {'支持' if exec_p < 0.05 else '不支持'}。执行错误与任务完成{'显著负相关' if exec_p < 0.05 else '无显著关联'} (OR={exec_or:.4f})。\n")

lines.append("### 3.4 中介路径分析（H4-H5）\n")
r6 = results.get('06_mediation_analysis', {})
lines.append(f"- Bootstrap次数: {r6.get('n_boot', 0)}")
lines.append(f"- 间接效应: mean={r6.get('indirect_mean', 0):.6f}")
lines.append(f"- 95% CI: [{r6.get('indirect_ci_low', 0):.6f}, {r6.get('indirect_ci_high', 0):.6f}]")
lines.append(f"- 直接效应: mean={r6.get('direct_mean', 0):.4f}")
lines.append(f"- 总效应: coef={r6.get('total_coef', 0):.4f}, p={r6.get('total_p', 0):.4f}\n")

ind_sig = r6.get('indirect_significant', False)
tot_sig = r6.get('total_p', 1) < 0.05
lines.append(f"**H4结论**: {'支持' if ind_sig else '不支持'}。间接效应{'显著' if ind_sig else '不显著'}（CI{'不' if ind_sig else ''}包含0）。")
lines.append(f"**H5结论**: 总效应{'显著' if tot_sig else '不显著'}（p={r6.get('total_p',0):.4f}），但间接效应{'也显著' if ind_sig else '不显著'}。\n")

lines.append("### 3.5 效度验证\n")
r9 = results.get('09_alignment_validity', {})
ca = r9.get('completion_by_alignment', {})
if ca:
    lines.append(f"- 高对齐组完成率: {ca.get('high_alignment_rate',0):.4f}")
    lines.append(f"- 低对齐组完成率: {ca.get('low_alignment_rate',0):.4f}")
    lines.append(f"- 符合预期: {'是' if ca.get('met') else '否'}")
dc = r9.get('deviation_error_corr', {})
if dc:
    lines.append(f"- 偏差与执行错误相关: r={dc.get('r',0):.3f}, p={dc.get('p',0):.4f}")
    lines.append(f"- 符合预期: {'是' if dc.get('met') else '否'}\n")

lines.append("## 4. 假设检验汇总\n")
lines.append("| 假设 | 内容 | 结果 |")
lines.append("|------|------|------|")
lines.append(f"| H1 | 提示风险→对齐度 | {'✅ 支持' if r3_sig else '❌ 不支持'} (p={r3.get('risk_index_p',0):.4f}) |")
lines.append(f"| H2 | 对齐度→执行错误 | {'✅ 支持' if r4_sig else '❌ 不支持'} (p={r4.get('alignment_deviation_p',0):.4f}) |")
lines.append(f"| H3 | 执行错误→完成 | {'✅ 支持' if exec_p<0.05 else '❌ 不支持'} (OR={exec_or:.4f}) |")
lines.append(f"| H4 | 间接路径 | {'✅ 支持' if ind_sig else '❌ 不支持'} |")
lines.append(f"| H5 | 总效应显著但间接效应也显著 | {'⚠️ 部分' if tot_sig and not ind_sig else ('✅' if tot_sig and ind_sig else '❌')} |")

lines.append("\n## 5. 核心结论\n")
lines.append("1. **执行错误是任务完成的最强预测因子**（OR=0.024, p<.001），但这一关系不新鲜。")
lines.append("2. **提示风险的总效应显著**（coef=-0.109, p=.0001），表明风险特征越多，完成率越低。")
lines.append("3. **但间接路径（通过对齐度→执行错误）不显著**——这与原PDF报告的发现不同。在去重后的数据上，对齐度指标的区分力有限。")
lines.append("4. **验证要求缺失是最稳定的单项风险**（β=0.0065, p=.004），呼应论文B的发现。")
lines.append("5. **对齐度效度未通过**——高对齐vs低对齐组完成率几乎无差异（0.80 vs 0.80），提示当前的覆盖率指标需要改进。\n")

lines.append("## 6. 局限性\n")
lines.append("1. 对齐度指标基于关键词覆盖，推理文本很长导致覆盖率普遍偏高，区分度不足。")
lines.append("2. 中介效应不显著可能是指标灵敏度问题，而非真实无效应。")
lines.append("3. 推理文本可能为后生成解释，不代表真实推理过程。")
lines.append("4. Bootstrap仅500次（受时间限制），建议正式分析增至2000次。\n")

lines.append("## 7. 与原PDF报告的差异说明\n")
lines.append("原PDF报告发现间接效应显著（-0.088, 95% CI [-0.121, -0.053]），但本研究去除了循环论证指标后，间接效应不再显著。可能原因：")
lines.append("- 原研究的reasoning_error_index包含了用task_completed定义的指标（循环论证）")
lines.append("- 去重后样本结构变化（原研究未严格去重）")
lines.append("- 纯文本对齐度指标的灵敏度低于包含结果变量的复合指标")
lines.append("这一差异本身就是有价值的发现——说明原研究的'显著间接效应'可能部分源于循环论证。")

report = '\n'.join(lines)
with open(os.path.join(RESULT_DIR, 'report.md'), 'w', encoding='utf-8') as f:
    f.write(report)
print(f"论文C报告已生成，长度: {len(report)} 字符")
