# -*- coding: utf-8 -*-
"""P043 round 4: append at section markers."""
import io

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P043_irrelevant_candidate_contamination\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

# Insert content before section markers
inserts = [
    ('## 5 讨论',
     '排序质量的分析还需要区分两个层次。排序器输出的质量是本文测量的 margin。排序器输入的质量是候选集的构成质量。污染是输入质量的问题。零重叠候选的出现说明候选集里混入了与查询无关的条目。margin 下降是输出质量的问题。排序器在污染候选存在的条件下无法有效区分金标与非金标。两个层次的区分是重要的。改善输入质量可以同时改善输出质量。但改善输出质量不一定改善输入质量。本文的干预建议因此集中在输入侧。\n\n'),
    ('## 6 局限',
     '零重叠候选的检测有一个实践上的灰色地带。实义词交集为零的判定取决于停用词表的选择。不同的停用词表对哪些词不算实义词的判定不同。交集的大小因此随停用词表而变。本设计使用的停用词表在冻结文件中写定。但不同停用词表下的污染率需要敏感性分析来确认稳健性。\n\n'),
    ('## 7 结论',
     '从目录治理的角度看零重叠候选和候选过载是两个独立的治理维度。零重叠是描述质量的维度。它的治理工具是描述改善和查询扩展。候选过载是候选数量的维度。它的治理工具是候选裁剪和命名空间分组。两个维度可以独立改善且收益叠加。\n\n'),
]

for marker, addition in inserts:
    if marker in t:
        t = t.replace(marker, addition + marker, 1)
        print(f'OK: {marker[:30]}')
    else:
        print(f'SKIP: {marker[:30]}')

io.open(P, 'w', encoding='utf-8').write(t)
