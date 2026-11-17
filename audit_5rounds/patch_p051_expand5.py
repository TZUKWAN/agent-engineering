# -*- coding: utf-8 -*-
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P051_early_signals_of_agent_search_failure\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def ins(anchor, addition):
    global t
    assert anchor in t, 'MISS: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

blocks = [
    ('第二，家族划分沿用组织前缀（805 个家族仅 3 个有足够正例进入 H3），语义任务分类可能给出不同的家族内复现图景。',
     '\n\n第三，窗口切割本身有一个值得申报的选择：前 20% 按"步数"切而非按"时间"切——'
     '步数是记录里的确定量，时间是重放推算量；'
     '两者的差别在等待密集的轨迹上可观（一次长超时占真实时间的大头而只占一步）。'
     '按步切割的窗口在时间意义上可能不是"前 20%"，'
     '但作为部署探针，步数恰好是实时系统可观测的量——'
     '窗口定义与部署条件一致是比时间保真更重要的性质。'
     '第四，交叉验证的折叠按实例分层但未按家族分层，'
     '家族层的 AUC 用家族内滚动折近似，k8s 家族仅 30 个实例使折叠数退化为极小值，'
     '其 CI 的宽（0.378-0.725）一半来自此。'
     '第五，五特征未经变量选择——冻结了全部进入，'
     '避免了选择偏倚但也让可能的弱特征（如 cmd_words）被强特征的方差拖累；'
     '特征级的贡献分解需要不改变判定词的探索性附录，本文未做。'),

    ('**冻结的可行性前提（kill gate）。**' if False else 'wave-9 的多 rollout 框架给这个体裁提供了少见的干净条件：G2 测得结局标签（exit_status→Submitted）覆盖 1.0——每条 rollout 都有结局，没有任何静默缺失；G4 测得 19,713 条 rollout 至少 10 步——前五分之一窗口有实质内容可读。两个前提门都宽裕通过，本文的全部判定都建立在完整标签、真实窗口之上——败因不在数据质量，这正是它作为教材的价值。',
     '\n\n与前提门配套的还有一条同波封锁记录，它从反面证明前提门的必要性：'
     '同波的 T151 与 T156 两个设计因 G9（观察可计算率 ≥0.90）实测 0.7876 被封锁——'
     '21% 的命令步没有任何观察跟随，轨迹就停在那里。'
     '若这两个设计强行运行，它们的新词类特征将在"有观察"与"无观察"的混合层上定义，'
     '同一名称测量两种不同的量。封锁记录与本文的前提行并排陈列，'
     '构成 wave-9 的完整前提档案：三个设计被门拦下、两个设计带前提运行、'
     '一个设计（本文）在前提全过的情况下依然得到负向结论——'
     '门的通过与否不预测结论的方向，它只保证测量对象与冻结句一致。'),
]

for anchor, addition in blocks:
    ins(anchor, addition)

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P051 total={cjk+words}')
