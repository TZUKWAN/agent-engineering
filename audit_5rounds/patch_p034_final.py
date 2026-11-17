# -*- coding: utf-8 -*-
"""P034 最终冲线（+550 字）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P034_information_scent_and_the_next_choice\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 摘要末尾补 ----
insert_after(
    '对信息觅食理论的机器迁移，这是一次带信度复核的诚实标定。',
    '标定的三行结论——气味有效但不强、测量稳但不独、杠杆在命令族——'
    '每一行都携带自己的证据等级与适用条件，引用时不可拆开单卖。',
    )

# ---- 4.5 表后补 ----
insert_after(
    'Holm 在 3 假设族内执行；命令族画像与位置剖面为描述性材料。',
    '\n\n三判定的组合读法：两个 partial 加一个 not_specific——'
    '本包是系列里第一个"主效应成立但特异性失败"的组合'
    '（P029 是 supported/supported/opposite，P031 是三 null）。'
    '组合的解读规则写在判定词本身：not_specific 不撤销 partial，'
    '它撤销的是 partial 的机制解释——效应存在（可预测）、'
    '但归属共享（不可独占）。这一组合在监测系统的落法是：'
    '气味作为特征可用（有预测力），气味作为解释不可用（归因不纯）。',
    )

# ---- 5.3 之前补 ----
insert_after(
    '与医生"多检查少用药"的处方同构——都是把行动组合向高信息收益的动作倾斜。',
    '\n\n处方之外还有一张禁忌表：edit（新信息率 29.8%）与 run_shell'
    '（新信息率 54.2% 且气味较高 2.04%）的组合在什么场景下合理？'
    '答案在任务阶段：edit 属于交付期动作，此时新知已无必要；'
    '若探索期大量出现 edit，按本文的画像它是在消耗预算的低新知动作——'
    '这是"阶段-命令错配"的监测信号：任务前段的 edit 密集'
    '值得标记复查。阶段错配监测把命令族画像与位置日历'
    '（P027/P023）拼成一张二维检查表。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P034 total={cjk+words}')
