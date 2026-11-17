# -*- coding: utf-8 -*-
"""P027 paper_cn.md 扩写补丁（第三轮）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P027_discourse_grammar_of_seeking\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 3.1 补充 ----
insert_after(
    '全量墙钟 91.0 秒。',
    '\n\nwave-5 帧相对 wave-4 的扩展值得记一笔：81 列对 48 列，新增的列主要是'
    'B 词表（五行为各一套）与位置三等分索引。B 词表的存在使本文成为系列里'
    '第一个"出厂自带复核工具"的设计——此前的包若要做 H3 式复核，'
    '需要补跑一次特征帧；本文的复核与主检验同帧同批完成，'
    '复核的不可偷懒性由数据管线保证。这一升级应当回灌到后续所有 wave：'
    '凡以词表为测量核心的设计，B 版本应作为标配列出厂。',
    )

# ---- 5.3 补充 ----
insert_after(
    '这是词表修复的标准流程，也是本文留给后续的最具体任务。',
    '\n\n三成因的诊断还可以借助一个现成的统计线索：kappa 在五行为上的排序'
    '（plan 0.083 > evidence_request 0.076 > hypothesis 0.055 > question 0.043 > conclusion 0.032）'
    '与触发率排序并不一致——若纯由稀有性驱动，conclusion（最稀有）与 question'
    '应有最低的 kappa 调整损失；实测 conclusion 最低、plan 最高。'
    'kappa 的排序更接近"行为的话语离散度"：plan 话语（计划句式高度程式化）'
    '两词表尚有 8% 共识，conclusion 话语（结论的表达方式最多样）几乎无共识。'
    '若这一解读成立，成因更偏向一（表达域分歧）与三（连续构念二分化）的混合，'
    '而修复的杠杆在连续化：给每 turn 输出行为强度分数而非二分判定，'
    'kappa 换成相关或 ICC，部分构念信号可能立即复活。',
    )

# ---- 6 局限第九条 ----
insert_after(
    '合并报告的"全灭"掩盖了行为间的信度梯度——尽管梯度的顶端（0.083）也远低于线。',
    '第十，五套词表的规模未经平衡（某行为词表若条目数倍于另一行为，触发率的'
    '差异部分来自词表广度而非话语本身），行为的跨词表可比性受限；'
    '词表规模的敏感性分析（随机下采样到等规模后重跑 kappa）可界定这一因素。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P027 total={cjk+words}')
