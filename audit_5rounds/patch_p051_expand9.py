# -*- coding: utf-8 -*-
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P051_early_signals_of_agent_search_failure\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def ins(anchor, addition):
    global t
    assert anchor in t, 'MISS: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

ins('一个诚实的代理标签研究比一个伪装成金标签的研究有价值得多——后者是当前智能体评测文献的常见病，本包是解药配方之一。',
    '\n\n这句立场话值得配一个操作化的结尾：'
    '任何引用本文 AUC 的下游工作，引用的应当是完整的三元组'
    '（0.6857、0.8604 的长度基线、2.8% 的正例基率），'
    '而不是单独一个数字。三元组中的任何一项缺失都会使'
    '读数失去可比性——这是代理标签研究给自己立的规矩，'
    '也是对读者的最后一道保护。')

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P051 total={cjk+words}')
