# -*- coding: utf-8 -*-
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P051_early_signals_of_agent_search_failure\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def ins(anchor, addition):
    global t
    assert anchor in t, 'MISS: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

ins('H1 判 *supported*：前五分之一特征达到交叉验证 AUC=0.6857（95% CI [0.6598, 0.7116]，Holm p=0.0025，n=19,654），干净地越过 0.65 地板。',
    '这是全波 14 个设计里仅有的两个 supported 之一——'
    '它的稀缺性使围绕它的三条警告更有必要：'
    '稀缺的 supported 最容易被断章取义，'
    '因此它的边界条件必须在同一份文档里触手可及。')

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P051 total={cjk+words}')
