# -*- coding: utf-8 -*-
"""P039 最终冲线（+200 字）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P039_semantic_decoy_and_misselection\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

blocks = [
    # 3.2 末尾补
    ('无裁判声明：诱饵判定（≥50% 共享）与相似度均为规则计算，无语言模型或人工裁判。',
     '\n\n相似度计算的词表口径与 P028/P034 的实义词定义一致（去停用词后的'
     '内容词），三包的探针在词表层互通——本文的诱饵相似度、'
     'P034 的气味、P028 的重叠，是同一词表家族在三个方向上的'
     '三个读数（向后看证据、向前看命令、横向看邻居）。'),
    # 5.1 结尾补
    ('帧内的败因归因（金标输给谁）可以裁决。',
     '\n\n败因归因的另一个用途是校准"诱饵治理的验收标准"：'
     '治理后（诱饵合并或区分），同 query 的金标 rank-1 是否回升'
     '——回升则治理有效；不回升则说明失败另有原因（查询歧义、'
     '金标描述缺陷），诱饵只是替罪羊。验收的闭环使治理'
     '从一次性清理变成可持续的测量-干预-复测循环。'),
]

for anchor, addition in blocks:
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P039 total={cjk+words}')
