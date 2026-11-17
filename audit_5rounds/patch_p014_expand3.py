# -*- coding: utf-8 -*-
"""P014 paper_cn.md 扩写补丁（第三轮）。"""
import io

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P014_semantic_prototype_bias\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 2.2 补充：诱饵的反事实定义 ----
insert_after(
    '诱饵机制的完整签名是：位置系数显著为正、正确性系数非正。',
    '\n\n反事实地把这个定义说得更硬：一条非金标候选 c 的典型性加成，是「c 在其候选列中的实际排名」'
    '与「把 c 的描述替换成列内低原型候选的描述后 c 的排名」之差的期望。观测数据无法直接计算这个量，'
    '但 H2 的子样本设计给了它的代理：在适配性耗尽的候选场里，高、低原型候选的排名差'
    '就是典型性在其余变量同等时的平均位次红利。诱饵表把红利换算成了最朴素的比例——'
    '这也是本文同时报告模型系数与 2×2 表的原因：前者给推断，后者给直观。'
)

# ---- 5.5 补充 ----
insert_after(
    '这一处理可移植：',
    '\n\n顺带说明它避免的两个反模式：给刻画性目标编造一个名义检验（如把分歧集比例与 0.5 比较）'
    '以获得「真实的 p 值」，或把刻画目标排除在族外从而使校正基数被悄悄缩小。'
    '占位规则以透明的方式同时避免两者。',
    )

io.open(P, 'w', encoding='utf-8').write(t)

import re
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P014 total={cjk+words}')
