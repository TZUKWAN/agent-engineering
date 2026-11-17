# -*- coding: utf-8 -*-
"""P027 最终冲线（第二轮，+250 字）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P027_discourse_grammar_of_seeking\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 3.3 后补 ----
insert_after(
    '判定词是 direction-free 的，方向的反转是读者有权知道的实质信息。',
    '\n\n顺带交代这次裁定对判定族的影响：H1 与 H2 的判定词都落在 supported 一侧，'
    '但 H1 的 supported 携带方向注记而 H2 不带——判定词表为此类情况准备的'
    '写法是"主词 + 括号注记"，注记不是判定的一部分而是它的诚实性附件。'
    '产物 note 字段保存了 round-1 与 round-2 的两次判定及理由，'
    '审计轨迹完整可查——判定可以改，改的路径必须留痕。',
    )

# ---- 6 局限补 ----
insert_after(
    '词表规模的敏感性分析（随机下采样到等规模后重跑 kappa）可界定这一因素。',
    '第十一，五行为的"位置语法"若要恢复构念身份，除了词表修复还需位置效应的'
    '跨词表复现检验——即修复后的 B 词表上也应重现 plan 后段集聚的方向与量级；'
    '单一词表上的复现不算数，这一点在本文的教训里已是题中之义。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P027 total={cjk+words}')
