# -*- coding: utf-8 -*-
"""P024 最终冲线（+200 字）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P024_epistemic_behavioural_gap\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 运行追溯后、数据可用性前的补充 ----
insert_after(
    '判定规则、面孔模式定义（正文 ≥20 字符且含推理块）与 H2 的意外方向条款冻结于 `protocol_freeze.md`。',
    '本研究与 P023 共用同一 turn 级特征帧与情态词表，两包的样本定义差异（147,253 对 87,395 个 turn）'
    '完全来自本文的面孔合格性门槛（正文 ≥20 字符且含推理块）；'
    '任何跨包对比应在合格样本口径上进行。',
    )

# ---- 4.2 结尾补一句 ----
insert_after(
    '公开犹豫不是没有认识内容，它的内容是"任务在收尾"。',
    '与 P023 的位置剖面（后段情态系数 −0.16）并排看，两个独立估计在收尾段给出了同号的负效应——'
    '一条来自合并口径随位置的衰减，一条来自面孔口径在全集上的对比——相互印证。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P024 total={cjk+words}')
