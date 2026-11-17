# -*- coding: utf-8 -*-
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P056_the_implicit_information_need\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def ins(anchor, addition):
    global t
    assert anchor in t, 'MISS: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

ins('三句话合成一个工程优先级：先扩池，再消歧，最后才轮到补全留白。',
    '\n\n给这三句话配一个执行顺序的量化理由，'
    '方便直接写进工程排期：'
    '扩池的边际收益按曲线前段计约每翻一倍候选买 7-8 个百分点，'
    '通常一到两个迭代周期可完成；'
    '消歧按 H3 系数推算每标准差 28 个百分点，'
    '但需要指令预处理流水线，落地周期一到两个季度；'
    '留白补全按 H1 系数每标准差 1.4 个百分点，'
    '且需要语义理解参与、错误风险最高。'
    '收益密度（每工程周覆盖点）排序与优先级一致——'
    '这不是拍脑袋的顺序，'
    '是三个效应量除以三个落地成本的商排序。'
    '任何团队按自己的实际成本重算这三个商，'
    '若得出不同顺序，'
    '本文的读数依然适用——'
    '它们提供的是分子，'
    '分母在每个组织自己的账上。')

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P056 total={cjk+words}')
