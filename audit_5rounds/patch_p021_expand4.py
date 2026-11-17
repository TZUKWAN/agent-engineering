# -*- coding: utf-8 -*-
"""P021 paper_cn.md 扩写补丁（第四轮，冲线）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P021_synonym_normalisation_consistency\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 1.1 结尾补充 ----
insert_after(
    '处方消灭了一个问题（找不到），制造了另一个（分不开）。',
    '\n\n这个两难不是同义词映射独有的——它是所有"表示归一"类技术的共同张力：'
    '归一提升召回经济学（一个概念一条通道），代价是区分度（通道内的成员彼此更像）。'
    '经典文献对这一张力的处理是任务相对的：在文档召回任务里归一的收益通常压倒代价'
    '（用户会翻检召回列表），在单点选择任务里代价可能反超（用户只看第一名）。'
    '本文的贡献是把这一理论上的张力在真实智能体数据上变成三个带置信区间的数字。',
    )

# ---- 3.3 边界补充 ----
insert_after(
    '本文的总体是自动管线的候选检索行为，向人类检索的外推被数据边界排除。',
    '无裁判声明的另一半是操控侧的：SYN_MAP 的应用是确定性的字符串操作，'
    '同一版本词表对同一描述永远产出同一改写——臂间对比不含"改写质量"的随机成分，'
    '效应的可重复性由规则保证。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P021 total={cjk+words}')
