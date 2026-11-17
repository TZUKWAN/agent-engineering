# -*- coding: utf-8 -*-
"""P014 paper_cn.md 扩写补丁（第五轮，最终冲线）。"""
import io

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P014_semantic_prototype_bias\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 4.1 H1 结果段补充 ----
insert_after(
    '三张面孔的第一张是灰色的。',
    '对实践者而言，这个 null 是个安心的消息的一半：它说明评估栈在正常运作区间内'
    '并没有给"典型"一个全局加分——第一名位置的主导逻辑仍然是查询适配。'
    '不安的另一半在下一节：偏置不需要全局加分也能起作用。',
    )

# ---- 局限补一条 ----
insert_after(
    '而非全部来自评估栈的典型性偏好。',
    '第八，本文的报告单位是候选而非查询；若以查询为单位重算（每查询取其最高原型非金标候选），'
    '效应的点估计会有小幅移动——候选级推断对本设计是正确的单位（机制作用于候选），'
    '但查询级的复合效应量仍待补充分析。',
    )

io.open(P, 'w', encoding='utf-8').write(t)

import re
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P014 total={cjk+words}')
