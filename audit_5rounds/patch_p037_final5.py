# -*- coding: utf-8 -*-
"""P037 最终冲线（+200 字）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P037_first_action_path_dependence\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 4.5 表后补 ----
insert_after(
    'Holm 在 3 假设族内执行；开局分布、家族混合与集中度对照为描述性材料。',
    '\n\nH2 的校正后读数再强调一次量级：β=−0.9464 的 logit 对应比值比'
    '约 e^0.95≈2.59——留守首家族的 rollout 跑满的几率是多样化推进者的'
    '两倍半。在终止率 97% 跑满的基线上，留守把本已不利的局面再'
    '翻倍恶化——它的预警价值正是从这一倍数里来的。',
    )

# ---- 5.1 结尾补 ----
insert_after(
    '该推论需要上下文操纵实验，超出观测设计，登记为架构侧的后续。',
    '\n\n观测侧也有一个可以先行的一步：轨迹长度与指令锚定的交互。'
    '把 H1 按轨迹长度分层（短轨迹指令稀释少、长轨迹稀释多），'
    '若离模效应（本为零）在长轨迹层浮现，指令稀释假说即获得'
    '观测支持。此检查在帧内可算、不违程序（作为描述性分层报告），'
    '是零成本验证锚定机制的第一步。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P037 total={cjk+words}')
