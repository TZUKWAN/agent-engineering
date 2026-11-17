# -*- coding: utf-8 -*-
"""P023 paper_cn.md 扩写补丁（第四轮，冲线）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P023_modality_and_verification\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 3.4 后补充 ----
insert_after(
    '判定词如实记录失效原因而非强行走 null。',
    '\n\n这一判定词与系列已有的 not_testable 族（P016 的估计量不可估、P020 的单元格为空、'
    '本文的对照退化）共同构成"不可判"的细分类目：估计量为空、对比侧为空、对照退化——'
    '三种失效各有各的原因、各有各的修复路径（重新参数化、操纵实验、词表重设计），'
    '合并成一个笼统的 not_testable 会抹掉修复的线索。判定词表的粒度应该服务于下一步行动的精度。',
    )

# ---- 5.3 人类文献段补充 ----
insert_after(
    '本文的结果与人类研究既有呼应也有分岔。',
    '\n\n呼应的部分还应当记下量级的一致性：人类研究中不确定表达后的查证几率提升通常在一到两倍'
    '（odds ratio 口径），本文的 e^0.42≈1.52 恰落在该区间内——'
    '尽管底层机制（人类是元认知监控、模型是序列生成）未必同源，'
    '行为统计上的相似性本身就是一个值得深挖的巧合：它要么暗示序列生成在足够强的'
    '任务约束下收敛到了类似的认知经济，要么提示这种语言-行为耦合是任务结构的产物而非认知的产物。'
    '区分两者需要跨架构的比较——不同模型家族的情态-检验系数是否稳定——'
    '这也是后续实验清单上的一项。',
    )

# ---- 7 结论最后补充 ----
insert_after(
    '对认识语言研究，机器轨迹提供了一个行为后果可观测的认识语言实验室——这是本文愿意留下的最大资产。',
    '最后值得为 H3 的失败说一句公道话：它不是设计的失败，而是设计的诚实。'
    '一个不那么严格的管线会把 −0.6257 的对照系数包装成"特异性成立——主题词与情态词效应不同"，'
    '而本文的判定系统把它拆穿为"对照在追踪同一方差"。'
    '认识语言的实验室刚开张，第一课就是实验台的诚实度比实验的数量更重要。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P023 total={cjk+words}')
