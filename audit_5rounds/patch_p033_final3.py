# -*- coding: utf-8 -*-
"""P033 最终冲线（+150 字）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P033_search_depth_vs_need_complexity\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 3.2 末尾补 ----
insert_after(
    '无裁判声明：步数计数、需求词数、提交标签均为发布方或规则产出，无语言模型或人工裁判。',
    '\n\n天花板数字的口径统一说明：15 步的上限是" issuing 命令的 assistant 歯"口径'
    '（不含纯文本回合），实例内最大观察步数的中位数与最大值均为 15——'
    '两个口径在帧内一致，全文的步数均沿用同一口径。',
    )

# ---- 5.3 之前补 ----
insert_after(
    '多 rollout 帧的引入因此不只是加了一个包，而是给整个系列装上了一面后视镜。',
    '\n\n后视镜的第二瞥指向因果语言：系列至今所有"特征 X 与行为 Y 相关"的结论'
    '（约束密度、欠规范、原型偏置）都可以在多 rollout 帧上做一次'
    '实例内复检——若 X 与 Y 在任务固定时仍相关，相关是 within-instance 的'
    '行为规律；若消失，相关是任务间构成差异的影子。'
    '本文的 H1 就是第一例 within-instance 复检（措辞长度与步数：消失并反号）。'
    '复检清单的长度等于系列的假设总数——这是多 rollout 数据'
    '给整个系列安排的长期作业。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P033 total={cjk+words}')
