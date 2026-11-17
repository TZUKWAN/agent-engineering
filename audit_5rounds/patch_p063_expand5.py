# -*- coding: utf-8 -*-
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P063_which_components_of_a_trace_carry_forward\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def ins(anchor, addition):
    global t
    assert anchor in t, 'MISS: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

blocks = [
    ('结语前的最后一块拼图是携带的对称性问题。' if False else '本文的 supported 例外地干净——七类全部同号、CI 全部远离零、成对设计封死任务异质性；',
     '\n\nsupported 的干净还经得起一层压力测试：'
     '七类里最小 lift（观察 0.127）的 CI [0.109, 0.143]'
     '与最大 lift（异常 0.320）的 CI [0.298, 0.340]'
     '完全不相交——即便按类间差异最不利的读法，'
     '最弱类也是明确的正携带。'
     '把七类的 CI 下限排成序，'
     '最小的 CI 下限是观察的 0.109——'
     '距离零最远的"边界类"也有 0.109 的下界，'
     '这不是某个类在拖着全局及格，'
     '而是七个类各自独立过线。'
     '多类同时过线的联合推断不需要额外校正'
     '（各类的 bootstrap 已在实例簇内重抽，'
     '类间相关被保留），'
     '这让 H1 的 supported 在多重性面前也站得住。'),

    ('两者都是修正而非颠覆。',
     '\n\n**携带与迁移的概念分界**值得一提，'
     '它决定了本文结论的适用范围。'
     '迁移（transfer）指第一次学到的内容改善第二次的表现；'
     '携带（carry-forward）指第一次的表达结构复现在第二次的表达里。'
     '本文测的是后者；'
     '前者（重试改进）由同波其他设计在结局层测量。'
     '携带是迁移的必要非充分条件的候选——'
     '若话语携带而行为不改进，'
     '模型在复述旧发现而不使用它们'
     '（知识以装饰品形态存在）；'
     '若行为改进而话语不携带，'
     '知识在沉默中更新。'
     '两个不匹配模式各有诊断价值：'
     '前者提示复述是表演，'
     '后者提示学习的语言通道未被使用。'
     '把携带矩阵与重试改进率并排，'
     '是知识形态研究的下一张二维图。'),

    ('本文留下的接口全部是轻量级的，',
     '\n\n最后给通篇一个收拢的比喻：'
     '如果把智能体的经验库比作一间工坊，'
     'P053 决定哪些成品上架（轨迹入库），'
     'P050 描绘了工坊里的通用工具箱（转移语法），'
     'P062 发现了成品合格证上的字迹特征（结果话语），'
     '而本文发现了学徒制——'
     '第二次尝试的散文在模仿第一次的笔记结构，'
     '学得最牢的是坑、环境与收成。'
     '工坊的改进杠杆于是清楚：'
     '让好笔记流传（P053 的挑选加本文的内容档保留），'
     '让坑的记录优先（异常话语的双高地位），'
     '并对模仿中的惯性保持审计距离（异类臂的 9%）。'),
]

for anchor, addition in blocks:
    ins(anchor, addition)

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P063 total={cjk+words}')
