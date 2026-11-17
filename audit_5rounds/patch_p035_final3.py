# -*- coding: utf-8 -*-
"""P035 最终冲线（+300 字）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P035_marginal_gain_and_search_persistence\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 2.3 后补 ----
insert_after(
    '量尺对"新"敏感、对"复读"盲，H1 的估计建立在有效的量尺上。',
    '\n\n效度表还附带了一个行为发现：4,295 步的显式同调用重复本身'
    '就是"复读-空转"行为的直接计数——它们占总步数的 1.8%，'
    '全部贡献近零新知。结合 P029 的复读-失败耦合，'
    '显式重复在两个数据面上都指向无效消耗。'
    '一个零成本的效率改造因此浮出水面：对同一调用的重复返回'
    '做缓存提示（"该调用已执行过，返回内容相同"），'
    '按本文的新信息率口径，这类提示可以避免约 1.8% 的步数浪费'
    '——零模型改动、纯环境侧提示的节能空间。',
    )

# ---- 4.3 结尾补 ----
insert_after(
    '这与 P033 的天花板结论合拍：rollout 的结局主要由预算结构（跑满 vs 提前完成）决定，过程的新知丰度改变步伐的节奏，不改变终点。',
    '\n\n单步强、全程无的两级分化还有一个纯统计的候选解释：'
    '累计新信息率的分母随步数增长，长 rollout 的累计均值'
    '被早期步锚定（前几步的新知率决定均值的大部分），'
    '其对结局的预测力被锚定效应稀释。H3 的检验若改用'
    '最近 k 步的滑动新知率（滚动的近期丰收率），'
    '锚定效应可以剥离——滑动版检验是比累计版更公平的'
    '第二机会，登记在 H3 的复核清单上。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P035 total={cjk+words}')
