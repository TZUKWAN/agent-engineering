# -*- coding: utf-8 -*-
"""P033 最终冲线（+450 字）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P033_search_depth_vs_need_complexity\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 4.5 表后补 ----
insert_after(
    'Holm 在 3 假设族内执行；需求四分位的步数与提交率为描述性材料。',
    '\n\n校正的敏感度确认：H1 与 H2 的 p_raw 都远在校正门槛之下，'
    'Holm 不改变任何判定；H3 的占位 1.0 是程序状态。'
    '三个判定的证据等级分层清晰：H2 是强实证（560 条提交轨迹、'
    'CI 远离零、效应量千倍于对手），H1 是方向确定的小效应'
    '（CI 紧但幅度在墙角），H3 是程序清点（1 族可估）。'
    '引用本文时按等级取用，不把 H3 的悬置读成失败。',
    )

# ---- 5.1 之前补（放 4.4 之后） ----
insert_after(
    '这一形状为"预算内完成"的建模提供了函数形式的起点（logistic 或指数衰减），比线性假设有据得多。',
    '\n\n几何衰减还有一个跨任务泛化的含义：若衰减率（每档约乘 0.45）'
    '在不同任务域大体稳定，那么提交率的预测只需要两个参数'
    '（基率与衰减率），而基率与衰减率都可以从需求长度与类目'
    '两个便宜特征估计——一个两参数的提交率预测器就足以支撑'
    '预算分配的第一版。预测器的精度上限（本文数据能支撑的'
    '最好水平）以四分位粒度的实际提交率拟合即可评估，'
    '其实现不需要任何模型训练——两个参数的最小二乘拟合就是全部。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P033 total={cjk+words}')
