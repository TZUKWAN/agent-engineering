# -*- coding: utf-8 -*-
"""P030 paper_cn.md 扩写补丁（第四轮，冲线 + 补图1引用）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P030_causal_connectives_and_evidence\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 4.1 补图1引用（判定汇总前） ----
insert_after(
    '![图2 H1 的两种口径](figures/custom_fig2_h1_two_scalings.png)',
    '\n\n三假设的判定全景（含 H2 的近零对比与 H3 的对照近零）见图 1。\n\n'
    '![图1 三个预注册假设的判定](figures/custom_fig1_verdicts.png)',
    )

# ---- 5.3 结尾补 ----
insert_after(
    '任何后续使用 evidence_overlap 的设计都必须同时携带这两个分层——这是两包共同写下的使用手册。',
    '\n\n使用手册还可以加一条从本文新学到的：探针的因变量口径（原始率或标准化 z）'
    '应按分层设计选择——层内比较用层内标准化（消除层间方差的干扰），'
    '跨层比较用全样本标准化（保持系数可比）。本文的分层系数用全样本标准化，'
    '因此梯度可以直接跨层比较；若改用层内标准化，梯度可能变形——'
    '两种口径不可混排在同一张图上。这类口径纪律琐碎但关键，'
    '方法学的可复现性往往就住在这些细节里。',
    )

# ---- 6 局限后补一条 ----
insert_after(
    '粒度的加细是稀释定律机制化的一步，登记为后续。',
    '第九，长度分层的因果身份有限：turn 长度与任务类型、轨迹阶段共变，'
    '长度梯度可能是任务构成的梯度（长 turn 集中在组织性任务）——'
    '按任务类目与长度的交叉分层可以区分"长度的效应"与"长 turn 所属任务类型的效应"，'
    '登记为稳健性候选。',
    )

# ---- 结论前补实践段 ----
insert_after(
    '任何话语功能词表的探针（修复词表、立场词表、元话语词表）都可以走一遍同样的三问。',
    '\n\n给目录维护者与提示工程师的落地版：若希望智能体的因果话语更贴证据'
    '（更可审计），本文的梯度给出的处方是**短化结论句**——把"因为/因此"'
    '引导的论证压缩进一两句话的独立 turn，而不是埋进多段报告的中段。'
    '短化不改变推理的内容，只改变它的语体环境，而语体环境决定'
    '连接词上不上推理的班。这是从测量规律反推的写作规范——'
    '与 P016 的长度预算、P018 的改写约束同属一类：'
    '话语工程的规范应当由测量规律供货，而不是由文风直觉供货。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P030 total={cjk+words}')
