# -*- coding: utf-8 -*-
"""P025 最终冲线（+300 字）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P025_contradiction_and_modality\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 5.1 后补一段 ----
insert_after(
    '矛盾提供的不是待决的状态而是明确的行动理由。',
    '\n\n用一句对比收拢这个剧本：盘算式犹豫出现在"要不要查还没决定"的时刻，'
    '行动式沉默出现在"必须查已经决定"的时刻。矛盾是后者的教科书触发器——'
    '两次读数冲突本身就是再查一次的完整理由，无需语言层的铺垫。'
    '这也反过来解释了 P023 开放段的高情态：任务刚开始时，"要不要查、查什么、查几次"'
    '全部悬而未决，语言是唯一的规划草稿纸。犹豫的产量与决策的开放度成正比——'
    '这句总结同时覆盖了三部曲的全部主效应。',
    )

# ---- 7 结论中补一句 ----
insert_after(
    '充分性语言与情态不同向（H3，null），且描述数据显示矛盾后充分性陈述翻倍。',
    '三色的组合里，opposite 提供方向的意外，supported 提供特异性的确认，'
    'null 与描述数据的张力提供解释的边界——每一个判定词都在为时序模型贡献一条边。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P025 total={cjk+words}')
