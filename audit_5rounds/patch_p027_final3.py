# -*- coding: utf-8 -*-
"""P027 最终冲线（+600 字）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P027_discourse_grammar_of_seeking\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 2.4 后补 ----
insert_after(
    '两条合格线必须独立达标——行为效度回答"它有用吗"，工具信度回答"它是它所说的东西吗"，缺一不可。',
    '\n\n用一个比喻把两条合格线的关系固定下来。行为效度像猎枪打得准（指哪打哪，'
    '与行为稳定耦合），工具信度像枪的准星没有歪（不同射手看同一个准星读数一致）。'
    '一把打得准的枪完全可能准星是歪的——射手（研究者）与枪（词表）磨合出了'
    '固定的补偿习惯，每发都命中，但命中的不是瞄的地方。'
    'P023-P026 证明了家族的枪打得准（与行为稳定耦合），'
    '本文发现准星可能歪了（换一个射手读数就变）。'
    '校准准星不影响已经命中的弹孔（行为耦合的发现是真的），'
    '但影响下一发打向哪里（构念层面的推广要等校准）。',
    )

# ---- 7 结论第一段后补 ----
insert_after(
    '本文按冻结规则交付的最终立场是：**位置语法存在于词表之内，作为言语行为语法的身份未被证明**。',
    '这一立场的两个成分不应被分别夸大。夸大前者（只谈位置结构）会把词表投影'
    '当成行为规律，重演 H3 拦下的转述；夸大后者（只谈工具失败）会把'
    '真实存在的巨大位置差异当成测量噪声丢掉——62% 到 77% 的集聚不是'
    '任何合理的测量误差能解释的量级，它是待解释的语言事实。'
    '正确的姿态是同时持有两者：一个强信号，一张暂缓的身份证。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P027 total={cjk+words}')
