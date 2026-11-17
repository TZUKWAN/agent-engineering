# -*- coding: utf-8 -*-
"""P021 paper_cn.md 扩写补丁（第五轮，最终冲线）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P021_synonym_normalisation_consistency\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 2.3 结尾补充 ----
insert_after(
    '又不至于把语义不同的任务捆在一起。',
    '以这个粒度为基础，家族成员的典型构成值得描绘：同一家族的成员多是同一功能域的近邻工具'
    '（同一动词、同一对象的不同实现），它们正是检索时彼此最强竞争者的集合——'
    '系统对这个集合的排序行为，是"检索一致性"最有操作意义的样本：'
    '一致性差的系统会在同族成员之间给出不稳定的相对顺序，'
    '一致性好的系统则给出可复现的优劣判断。',
    )

# ---- 4.2 结尾补充 ----
insert_after(
    '决定了一致性通路不通电。',
    '这个解读同时是对下一版词表的设计输入：若一致性是被追寻的目标，'
    '词表不应是对称的同义组，而应是带规范形优选级的单向映射——'
    '组内指定唯一的规范成员、其余成员单向归并，替换因此天然不均匀，'
    '家族内排名才可能收敛。这是把 H2 的 null 转化为设计知识的一步。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P021 total={cjk+words}')
