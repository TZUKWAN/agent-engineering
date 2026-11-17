# -*- coding: utf-8 -*-
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P051_early_signals_of_agent_search_failure\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def ins(anchor, addition):
    global t
    assert anchor in t, 'MISS: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

blocks = [
    ('**重判条件。** 下列证据到达时应重估本文的判定结构：',
     '\n\n此外还有第四条与第三条对称的重判路径：'
     '若拖沓度重构在本文特征组上失败（行为特征对长度正交化的结局仍无增量），'
     '则本包的结论升级为更强的形式——节奏层特征对结局层'
     '在除去长度机制后没有任何独立信息，早期信号研究应整体转向内容层。'
     '注意这条路径使本文变得可反驳：它指明了什么样的数据'
     '会证明本文的怀疑过度，并把证明的成本压到一个具体实验上。'
     '一个不允许自己被更强证据推翻的怀疑与一个不允许被推翻的'
     '断言一样教条——四条重判路径就是这个对称性的落实。'),

    ('第一，标签的语义窄：Submitted 只记录"提交了"，不记录提交内容的质量——一个提交了错误答案的 rollout 与提交正确答案的标签相同。',
     '\n\n这个局限还有一种更尖锐的表述：本文的 AUC 测量的是'
     '"对一种行政结局的判别力"，行政结局（提交与否）与'
     '认识结局（对错与否）的相关系数未知，且没有数据可以估计它。'
     '早期信号文献的多数工作同样卡在这里——'
     '它们报告的"失败预测"几乎都是行政结局的预测。'
     '把行政结局换成认识结局需要人工或模型的答案评分，'
     '那是一笔独立的标注投资；本包的设计阶段评估过并放弃'
     '（成本超出单设计预算），把它记为全系列共同的最大缺口，'
     '比记为本包的过失更符合事实。'),
]

for anchor, addition in blocks:
    ins(anchor, addition)

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P051 total={cjk+words}')
