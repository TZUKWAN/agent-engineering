# -*- coding: utf-8 -*-
"""P022 paper_cn.md 扩写补丁（第四轮）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P022_discriminability_and_discoverability\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 2.4 补充 ----
insert_after(
    '它指出构念的哪一条通道与检索栈的匹配机制同源。',
    '\n\n双仪器设计还服务于一个更谨慎的目的：防止单仪器假阳性。若只用词面仪器得到 null'
    '（如本文 H1），质疑者可以说"你的仪器太粗糙，没测到真正的判别性"；'
    '若只用稠密仪器得到正效应，支持者可以说"功能性质量得到验证"。'
    '两台仪器同时在场，null 与正效应各自成立又互相制衡——'
    '分歧本身被登记为信息（第 4.4 节）而不是被辩护或忽略。'
    '这是 E06 框架（系列共享的第二仪器义务）在设计上的一次完整兑现。',
    )

# ---- 3.4 补充 ----
insert_after(
    '总体为自动管线的选择行为，外推边界同系列。',
    '\n\n一个计算成本的附注：判别性的两台仪器都只需要缓存向量与词频统计，'
    '对整个目录的一次性计算成本与一次全量检索相当；'
    '把它加入元数据审计管线的边际成本几乎为零——'
    '这使本文的"条件计价"建议在工程上不需要任何新的基础设施投资。',
    )

# ---- 4.5 表后补充 ----
insert_after(
    'Holm 在 3 假设族内执行；分层斜率与 E06 为随行材料。',
    '\n\n族内校正的实际影响与系列各包一致地微小：H3 的 p_raw 低于 10⁻³，'
    '校正后仍远在阈值下；H1/H2 的 p_raw 本就不显著，校正无实质变化。'
    '包内 table5_robustness_inference.csv 存档了校正矩阵。'
    '对结论真正敏感的是第 3.1 节的邻居排除（条件样本略偏拥挤）与第 6 节第七条的视角差异——'
    '两者都指向同一方向：在更宽的样本上，H3 的量级可能略小，方向不受威胁。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P022 total={cjk+words}')
