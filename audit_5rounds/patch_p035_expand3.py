# -*- coding: utf-8 -*-
"""P035 paper_cn.md 扩写补丁（第三轮）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P035_marginal_gain_and_search_persistence\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 4.1 图引用补 ----
insert_after(
    '![图2 新信息十分位与延续率](figures/custom_fig2_decile_curve.png)',
    '\n\n三判定的全景与 H1 的量尺效度检验见图 1 与图 3。\n\n'
    '![图1 两个可估假设的判定](figures/custom_fig1_verdicts.png)\n\n'
    '![图3 新信息量的效度检验](figures/custom_fig3_repetition_validity.png)',
    )

# ---- 4.4 补充 ----
insert_after(
    '正反馈不是某一族命令的局部现象。',
    '\n\n族间系数的幅度差异同样有信息：list 族（+0.57）与高系数族的丰收'
    '最能"续命"，other 族（+0.17）最弱——列表返回的丰收（发现一片'
    '新文件名）天然指向下一步动作（去读其中一个），丰收与下一步的'
    '语义衔接最紧；other 类杂项动作的丰收与后续的衔接最松。'
    '丰收-继续耦合的强度因此随"丰收的下一步可行动性"变化——'
    '丰收不只是情绪上的鼓励，它在语义上给出了下一步的具体选项。'
    '这一解读可检验：丰收率高的步，其下一步与该步观察的词汇对齐'
    '（P032 的对齐探针）应当更高——两个包的探针可以在帧内交叉。',
    )

# ---- 5.2 后补 ----
insert_after(
    '预算监控该盯的不是转圈，是上瘾。',
    '\n\n"上瘾"的判定需要一个操作化定义，本文的数据足以给出候选：'
    '连续 k 步的新信息率都高于轨迹自身均值（正反馈持续期），'
    '且剩余预算不足连续期的两倍——满足即进入"过度开采预警"。'
    '预警的本意不是停止（丰收说明任务在正轨），而是触发一次'
    '**收束评审**：当前收获是否已可交付？若可，把剩余预算花在'
    '整理与提交上；若不可，评估剩余缺口与预算的匹配度。'
    '预警不代替决策，它把决策的时点从"预算耗尽的被动时刻"'
    '提前到"丰收持续期的主动时刻"——这正是 P033 揭示的'
    '"提交者提前收工"模式的制度化。',
    )

# ---- 6 局限补 ----
insert_after(
    '缓解但未消除这一解释负担。',
    '\n\n第七，新信息率与步位强相关'
    '（rollout 早期的观察天然更新），位置控制后 H1 的系数是同位置内的丰收效应——'
    '它排除了位置混杂，但也意味着效应的实践利用必须伴随位置信息'
    '（不能把早期丰收与晚期丰收等同视之）。'
    '第八，继续率的基线本身极高（86.8%–97.6%），分布的顶部拥挤会使'
    '高丰收端的真实差异被天花板（1.0）压缩——logit 口径部分缓解'
    '但不消除；若以连续的剩余轨迹长度替代二值 continues，'
    '丰收效应的完整剂量反应曲线可以展开。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P035 total={cjk+words}')
