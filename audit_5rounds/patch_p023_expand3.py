# -*- coding: utf-8 -*-
"""P023 paper_cn.md 扩写补丁（第三轮）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P023_modality_and_verification\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 2.4 补充 ----
insert_after(
    '位置剖面因此是对 2.1 节机制的直接剖面检验。',
    '\n\n位置假说还有一个可检验的旁支：若前段的犹豫是规划性的，它应与轨迹的后续长度正相关'
    '（有计划的轨迹更长）；若后段的犹豫是拖延性的，它应与轨迹临近终止相关。'
    '两个旁支都可以在现有帧上检验而不需新数据，本文把它们记为后续分析——'
    '预注册的门内只放三道主关，门外的问题明确登记，是同一纪律的两面。',
    )

# ---- 4.1 图1 后补充 ----
insert_after(
    '认识语言不是结构性背景的回声。',
    '\n\n一个对照性反问可以钉牢这个增量的意义：随机抽一个与情态 turn 等长、等位置、'
    '等先验史的非情态 turn，它后接检验的几率是 14.5%；换成情态 turn，几率升到约 19.4%。'
    '在十五万个 turn 的尺度上，这 4.9 个百分点的位移对应数千次额外的检验调度——'
    '认识语言的差异不只是统计显著，它在行为规模上真实可感。',
    )

# ---- 5.4 后补充 ----
insert_after(
    '这一用途把本文的联结从描述统计变成了筛选器，其查全查准特性值得在标注样本上单独校准。',
    '\n\n对词表设计者的反向馈赠同样明确：本文的 H1 为 MODAL 词表提供了第一次行为效度证据——'
    '词表触发的 turn 在行为上可分辨（更倾向检验），说明词表捕捉的不是任意词汇而是'
    '与决策状态耦合的语言。行为效度是词表质量金字塔顶端的证据：在它之下还有覆盖率与'
    '一致性检验，之上还有与人工认识状态标注的聚合效度——本文完成的是中间那层，'
    '三层的完整阶梯是词表工程可以按图施工的路线。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P023 total={cjk+words}')
