# -*- coding: utf-8 -*-
"""P026 paper_cn.md 扩写补丁（第四轮）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P026_sufficiency_language_and_stopping\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 4.2 之后补 ----
insert_after(
    '评估者若给"说了够了"的停止标红，标红的将是整个数据里取证最充分的那一批。',
    '\n\nH2 的结果还有一个值得记录的副产物：它间接校准了"其他停止"的构成。'
    '5,910 次无宣称停止平均只有 1.72 次先验检验——其中既有"任务简单自然结束"'
    '的健康停止，也有真正的悄然放弃。宣称停止（2.57 次）显著高于这一混合基线，'
    '说明语言化收尾至少筛选出了取证高于平均的子群；'
    '至于基线内部的优劣分层，那是无语言线索可循的部分——'
    '正是第 5.2 节行为指标的辖区。语言的哨兵角色在此可见一斑：'
    '它报不出坏消息（没有"取证不足"的语言签名），但它的在场标记好消息。',
    )

# ---- 4.4 图2 引用后补 ----
insert_after(
    '![图2 描述性切面](figures/custom_fig1_descriptives.png)',
    '\n\n把图 2 的两个面板按 H1/H2 的逻辑重排一遍，读者可以带走一个记忆锚点：'
    '左面板（停止率 3.5 倍）是"表象"，H1 证明它属于证据状态；'
    '右面板（取证 2.57 对 1.72）是"质地"，H2 证明它偏向优质侧。'
    '表象与质地的组合只有四种，本文数据占据的是最好的一种：'
    '大表象 + 好质地 = 报道论。若数据给出大表象 + 坏质地，语言因果论与过早终止'
    '将同时成立——那会是评估的红色警报。四象限的完整枚举说明 H1 与 H2'
    '为什么必须成对预注册：单独任何一个都足以误读这幅图。',
    )

# ---- 5.1 结尾补 ----
insert_after(
    '把共存的表象当因果。',
    '\n\n四部曲的地图还能标出各词汇的"盲区"：情态词看不见事件后（P025）、'
    '正文词看不见认识状态（P024）、充分性词看不见停止原因（本文 H1 的吸收）。'
    '三个盲区各被一次预注册检验钉明——这是行为学测量区别于直觉测量的地方：'
    '直觉给每个词汇一个无所不能的语义，行为数据给每个词汇一个有边界的岗位。'
    '有边界的指标才是可组合的指标；四部曲的真正产出不是四个系数，'
    '而是四份岗位说明书的组合表。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P026 total={cjk+words}')
