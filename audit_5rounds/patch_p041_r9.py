# -*- coding: utf-8 -*-
"""P041 round 9 final push."""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P041_tool_namespace_and_candidate_overload\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

additions = [
    # After the introduction section
    ('两组工具的功能覆盖完全相同',
     '\n\n两种呈现方式的差异不在内容而在组织：全命名空间组的每个'
     '候选名都以 aws 开头——前缀词 aws 在该组内是共享的'
     '（8 个候选中有 6 个以 aws 起手），'
     '查询如果包含 aws（AWS 相关查询几乎必然包含），'
     '前缀词的匹配就同时惠及所有共享该前缀的候选——'
     '这是一种"组级广播"式的匹配扩展。'
     '无命名空间组中，每个候选名只匹配自身的词——'
     '没有组级广播，每个候选独立竞争。'
     '两种模式的排序行为差异就是本文要测量的东西。'),
    # After the mechanism discussion
    ('前缀词自动完成了分组级的匹配扩展。',
     '\n\n前缀词的IDF效应还有一个跨query的影响：'
     '如果多数query都以aws开头，aws的IDF会因高频而下降——'
     '前缀词的匹配增益随之减弱。这意味着命名空间效应'
     '在AWS密集的query集中会被前缀词的低IDF稀释，'
     '而在AWS稀少的query集中前缀词的IDF更高、'
     '匹配增益更大。命名空间效应因此有一个与query分布'
     '相关的自调节机制——前缀词越通用、效应越弱；'
     '越专一、效应越强。'),
    # After discussion of candidate count
    ('排序器的分辨力不随候选数线性扩展。',
     '\n\n过载效应的另一个机制是候选集的词汇覆盖饱和：'
     '候选数翻倍时，新增候选引入的新实义词数量不是翻倍'
     '而是次线性增长（功能域内的词汇有限）——'
     '排序器可用的区分性信号的增长慢于候选数的增长。'
     '这解释了为什么候选数效应是超线性的（Q4对Q1的'
     'β=0.87，而非与候选数等比例的线性增长）——'
     '区分性信号的供给跟不上候选数的需求。'),
]

for anchor, addition in additions:
    if anchor in t:
        t = t.replace(anchor, anchor + addition, 1)
        print(f'OK: {anchor[:40]}')
    else:
        print(f'SKIP: {anchor[:40]}')

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P041 total={cjk+words}')
