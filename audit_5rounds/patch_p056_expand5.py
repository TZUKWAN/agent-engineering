# -*- coding: utf-8 -*-
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P056_the_implicit_information_need\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def ins(anchor, addition):
    global t
    assert anchor in t, 'MISS: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

blocks = [
    ('而冻结排序器给出的候选目录就是 Q2-Q3 的产出——**需求与目录之间的覆盖差，就是隐含需求被系统恢复的程度。**',
     '\n\n覆盖差的这个定义还有一个对称的读法值得写明：'
     '本文的覆盖是"目录对需求的覆盖"，'
     '它的补数不是"需求未被满足"，'
     '而是"需求的恢复未被目录支持"——'
     '即便目录不覆盖，智能体也可能靠上下文推理自行恢复需求并完成任务'
     '（这是检索之外的第二条恢复路径）。'
     '因此 32.7% 的未覆盖份额是"检索路径失效"的度量，'
     '不是"任务必然失败"的度量；'
     '两条路径的分工是智能体检索理论的一个开放问题——'
     '推理恢复的边界（哪些需求可以推理出来）'
     '决定了目录覆盖的真实重要性。'
     '一个极端的思想实验可以标出这个边界：'
     '对一个零候选目录的任务，'
     '智能体仍然可能靠参数猜测完成任务——'
     '那时覆盖为 0 而任务成功，'
     '推理路径独力扛下了全部。'
     '本文的读数在这个思想实验的映照下应读作：'
     '检索路径在 67% 的需求上可用，'
     '其余交给推理与运气。'),

    ('**与 P046（计划特异性）**：两包共享"明确性"词根但层次不同',
     '\n\n这个合并结论还有一个可检验的推论，'
     '把它写成预注册式的句子留给后续：'
     '若语言明确性类变量在智能体管线上的效应普遍微小且易被遮蔽，'
     '那么任何以"让模型写得更明确"为核心机制的新设计，'
     '都应默认按本文的 H3 模板配特异性检验——'
     '把长度、枚举、歧义、留白四件套放进同一规格。'
     '四件套模板的成本是四个协变量，'
     '收益是把"明确性"这个词的每个成分分到各自的账上；'
     'P046 与本文的两次 not_specific/partial 经验表明，'
     '这笔投入的期望回报为正——'
     '两次检验两次发现真正的驱动者另有其人'
     '（P046 的实体枚举、本文的词汇歧义）。'),
]

for anchor, addition in blocks:
    ins(anchor, addition)

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P056 total={cjk+words}')
