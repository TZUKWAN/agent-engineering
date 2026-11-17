# -*- coding: utf-8 -*-
"""P020 最终冲线补丁（+150 字以上）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P020_name_description_congruence\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

insert_after(
    '与真实目录的写作习惯相符：核心动词被描述复述，产品代号与缩写往往不解释。',
    '这一分布形态也提示了效应的集中区：两端条目（一致度取 0 与 1 的）各自占相当比例，'
    '它们之间的选择率对比承担了效应的大部分——中段条目的边际改进空间与边际效应同时有限。',
    )

insert_after(
    '而那是设计纪律问题，不是统计问题。',
    '纪律的可贵之处在于它在没有外部压力时依然执行：把空格并进中性组不会被发现，'
    '反而会让结果表多一行整齐的数字——拒绝这样做的唯一理由是判定系统与事实的对应关系。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P020 total={cjk+words}')
