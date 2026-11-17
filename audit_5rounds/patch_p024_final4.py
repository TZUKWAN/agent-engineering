# -*- coding: utf-8 -*-
"""P024 paper_cn.md 扩写补丁（第七轮，最终冲线）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P024_epistemic_behavioural_gap\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 2.1 结尾补 ----
insert_after(
    '每个格子的行为读数都在检验"哪一层在说话"这一句话的两个方向。',
    '\n\n这一形式化还有一个不易察觉的优点：它把"哪层在说话"从解释项变成了被检验项。'
    '在此前的讨论里，"推理块更真实"往往是解释行为差异时的默认假设——一个从未被'
    '单独检验的假设。四格设计把它推上被告席：若假设成立，分歧格的行为应偏离'
    '正文口径的预测而靠近推理口径；若不成立，分歧格的行为应落在两口径之间。'
    '25.28% 对 3.45% 的对比落在"靠近推理口径"的远端——假设不但成立，'
    '而且以数据集中最强的行为对比之一成立。',
    )

# ---- 5.4 后补一段 ----
insert_after(
    '混入口径的校准曲线平均了两个相反的效应，其结论不可解释——这是 P023 与本文共同锁定的技术要点。',
    '\n\n最后是给后续研究的清单。第一，把面孔分解回灌 P023：按推理块/正文拆开情态变量、'
    '按位置分层，填出 2×3 的效应分解表。第二，把分歧模式与任务结局相连：'
    '分歧率高的轨迹最终成功率如何——这决定分歧是风险信号还是无害的文体现象。'
    '第三，跨模型家族复测四格的行为读数：两层规范是否为架构的普遍性质。'
    '三者共享本文的帧、词表与判定管线，任何一项都是一次现成的预注册。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P024 total={cjk+words}')
