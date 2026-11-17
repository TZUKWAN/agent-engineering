# -*- coding: utf-8 -*-
"""P034 paper_cn.md 扩写补丁（第三轮）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P034_information_scent_and_the_next_choice\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 4.1 图引用补（4.1 节缺图1引用） ----
insert_after(
    '判定 partial：显著、稳健、低于中等带——觅食逻辑在机器猎场上成立，但气味的单独杠杆力量有限。',
    '\n\n三判定的全景（含 H3 对照的反超）见图 1。\n\n'
    '![图1 三个预注册假设的判定](figures/custom_fig1_verdicts.png)',
    )

# ---- 5.3 后补 ----
insert_after(
    '两种目的用两种设计，混用会得到本文与 P027 两个极端之间的任意读数。',
    '\n\n把本文的双仪器规格与 P027 的失败规格并排成一张对照表，设计指南就完整了：'
    '输入（同对字符串 vs 不同措辞域）、代数（两种标准化 vs 两种词汇表）、'
    '构念维度（连续标量 vs 多类离散）、结果（ρ=0.995 vs κ=0.03）。'
    '表格的读法不是"本文好 P027 差"，而是"两种设计回答两种问题"：'
    '本文回答"这个构念的测量对定义选择敏感吗"（不敏感，好），'
    'P027 回答"这个构念的词汇覆盖稳定吗"（不稳定，需修复）。'
    '测量工程的完整流程两问都要答——先 P027 式词汇域复核，'
    '再本文式代数复核，顺序不能换（词汇域不稳时，代数复核无意义）。',
    )

# ---- 5.4 后补 ----
insert_after(
    'P033 的天花板发现就是在 wave-6 帧上复检"深度"概念时发现的——跨波复检的第一单生意就是改写一个核心构念的前提。',
    '\n\n跨波联合的下一单生意已经排定：把 wave-5 的五行为话语语法'
    '（P027）在 wave-6 帧上按 rollout 位置重切——若五行为的位置结构'
    '在多 rollout 数据上依然成立，P027 的词表 A 口径结论获得跨波稳健性；'
    '若不成立（不同 rollout 的位置结构不同），话语语法就要改写成'
    'rollout 级的概念。wave-5 的另一半资产（情态/充分性词表）'
    '在 wave-6 的复检（P033 已用到 SUFFIC）也在同一清单上。',
    )

# ---- 7 结论最后补 ----
insert_after(
    '对智能体系统，它把"多写、会搜"这四字处方放在了数据的地基上。',
    '\n\n这四字处方的性价比还可以算到投入产出级：多写（更长的命令前文本）'
    '的成本是每步多几十个 token 的生成开销；会搜（优先命名搜索）的成本'
    '是零（只是换命令族）。收益端：多写换 0.3 个百分点的新信息率提升，'
    '会搜换来的是把 60%–84% 新知率的动作排在 30% 新知率的动作之前——'
    '同样的步数预算下，后者带来的新知总量差异是倍数级的。'
    '处方四字里，"会搜"两个字值回全部票价。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P034 total={cjk+words}')
