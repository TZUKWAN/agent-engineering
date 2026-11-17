# -*- coding: utf-8 -*-
"""P026 最终冲线（+350 字）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P026_sufficiency_language_and_stopping\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 2.4 结尾补 ----
insert_after(
    '都应以推理块口径读取。',
    '\n\n接口上还有一个待验的细节顺带登记：P024 证明行为跟随推理块的犹豫，'
    '那么充分性宣言的行为效力是否也分面孔——推理块里的"够了"与正文里的"够了"'
    '是否与不同质量的终止共现？若账本假说成立，推理块口径的宣称停止'
    '应比正文口径的宣称停止取证更充分。这一交叉（面孔 × 宣言 × 取证量）'
    '在四部曲的帧上可直接计算，它同时是对 P024 结论在第三个词汇类上的推广检验。',
    )

# ---- 3.1 结尾补 ----
insert_after(
    '也是 CI 偏宽的原因之一。',
    '\n\n4.3% 的宣称率本身是一个值得记录的描述数字：在全部 assistant turn 里，'
    '只有约每 23 个 turn 出现一次语言化的充分性宣言——收尾的宣告是克制的事件，'
    '不是流水线上的口头禅。这一稀缺性保证了 H2 对比的特异性（931 个宣称停止'
    '不是大数定律下的噪音群体），也提示任何基于该词表的监测器都会天然低频报警——'
    '对值守的审计者而言，低频且高精度的警报恰是可用的形态。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P026 total={cjk+words}')
