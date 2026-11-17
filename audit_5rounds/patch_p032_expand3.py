# -*- coding: utf-8 -*-
"""P032 paper_cn.md 扩写补丁（第三轮）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P032_plan_action_alignment\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 4.1 图引用补 ----
insert_after(
    '![图2 对齐率的分布](figures/custom_fig2_alignment_distribution.png)',
    '\n\n三判定的全景与退化的对比见图 1 与图 3。\n\n'
    '![图1 两个主假设的判定](figures/custom_fig1_verdicts.png)\n\n'
    '![图3 真实与置换的退化对比](figures/custom_fig3_degenerate_contrast.png)',
    )

# ---- 4.4 表后补 ----
insert_after(
    'Holm 在 3 假设族内执行；对齐分布与族内剖面为描述性材料。',
    '\n\nH2 的 p_raw 在本样本低于 10⁻³，三重校正后判定不变；H1 的 p_holm=1.0'
    '与 H3 的占位 1.0 均为程序状态而非检验失败。判定组合'
    '（null / opposite / not_testable）的三个成员再次全部为"非支持侧"——'
    '本包与 P021、P027、P031 构成系列的"非支持侧四重奏"，'
    '它们的密集出现是对"预注册只产支持结果"疑虑的最有力回应：'
    '当冻结的判定规则遇到不合预期的事实，它输出的是事实。',
    )

# ---- 5.1 后补 ----
insert_after(
    'P027 的 kappa、本文的置换对照，是系列为"测量自我怀疑"装备的两件工具：前者校正巧合共识，后者校正领域底噪。',
    '\n\n把两件工具的适用时机写成一问一答。何时用 kappa：当你声称一个构念被两套工具同时测量时（构念信度问题）。'
    '何时用置换：当你声称文本与某个特定对象存在超出类别基率的关联时'
    '（对照基线问题）。本文的两个对照对象（置换调用、kappa 的随机一致）'
    '都不是真实数据里的对手，而是统计构造的"虚无对手"——'
    '测量的意义只有在战胜虚无对手后才需要面对真实对手。'
    '顺序不能反：先打虚无对手，赢了再谈真实对手。',
    )

# ---- 5.4 补充 ----
insert_after(
    '类别特征先行，内容特征需过底噪检查**。',
    '\n\n这条规矩与 P031 的结尾判例可以合成一个"话语特征上架流程"：'
    '一，类别检验（词表命中与行为的耦合，如 P023 的情态词）；'
    '二，内容检验（词汇/语义与行为内容的对齐，过置换对照，如本文）；'
    '三，信度检验（双版本词表 kappa，如 P027）；四，分层校准'
    '（位置/长度/面孔，如 P023/P030/P024）。四道工序全过的特征'
    '才有资格进入监测与预测系统——系列至今没有任何一个特征'
    '四道全过，这既是诚实的现状，也是后续工作的清单。',
    )

# ---- 7 结论前补 ----
insert_after(
    '类别信号能穿透领域底噪（"有计划"的 turn 确实更多检验），内容信号被底噪淹没。这一对比为话语-行为预测的特征工程立了规矩：**类别特征先行，内容特征需过底噪检查**。',
    '\n\n还要为 H2 的发现补一个它应得的强调：饱和测量里浮出的反向变差'
    '不是噪声——LR χ²=331 在十五万观测上意味着这是一个极其稳定的'
    '行为规律。它的存在说明对齐率的分母（领域词汇的普遍亲缘）'
    '虽然淹没了均值层面的信号，却没有淹没分子层面的结构变差：'
    '在底噪之上，复读型 turn 系统性地比首发型 turn 对齐更高、'
    '失败更多。饱和不是信息的终结，是信息换了承载层——'
    '从"计划的指向性"换到了"复读的倾向性"。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P032 total={cjk+words}')
