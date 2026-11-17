# -*- coding: utf-8 -*-
"""P030 最终冲线（+400 字）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P030_causal_connectives_and_evidence\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 摘要内补一句与引言 1.1 前补 ----
insert_after(
    '当智能体写下"因为"或"因此"时，它所连接的内容真的来自给它的观察吗——还是因果连接词只是话语的组织骨架，与证据无关？',
    '这个问题是话语测量学的一个试金石：连接词是话语中最普遍的功能词汇之一，'
    '若连它们的行为耦合都测得干净，词表探针的方法学就有了一个标杆；'
    '若测得混杂，探针的使用边界就得重新画。',
    )

# ---- 1.2 后补 ----
insert_after(
    '支持判定要求 |β|≥0.15、CI 排除零、p_holm<0.05；Holm 在 3 假设族内执行。',
    '\n\n三个假设的对象都建立在 P028 交付的探针之上，方法连续性的价值在此显现：'
    'evidence_overlap 的定义、实义词的切分规则、标准化的口径全部沿用，'
    '两文的系数可以直接对话——P028 的顺序效应是这枚探针的"条件化敏感性"测试，'
    '本文的连接词效应是它的"共变敏感性"测试。一枚探针、两次标定、'
    '一份不断完备的使用说明——系列的方法论资产就是这样累积的。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P030 total={cjk+words}')
