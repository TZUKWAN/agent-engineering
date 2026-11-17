# -*- coding: utf-8 -*-
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P051_early_signals_of_agent_search_failure\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def ins(anchor, addition):
    global t
    assert anchor in t, 'MISS: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

blocks = [
    ('这不是行为特征的失败，而是标签构造的影子：Submitted 意味着任务做完提前退出，未完成意味着中途放弃或超长挂起——**结局标签与长度是同一枚硬币的两面**。',
     '\n\n硬币比喻还可以再翻一面：既然标签与长度纠缠，'
     '为什么还要保留这个标签做研究？答案是：'
     'Submitted 是发布集里唯一的、全覆盖的、非人工的结果变量——'
     '同波普查 G13 确认不存在任务成功的人工评分。'
     '在没有金标准的语料里，用代理标签做研究是唯一选择，'
     '而正确的做法就是本文这样：代理标签、打印基线、'
     '量化纠缠（17 倍落差与 0.86 的基线 AUC 就是纠缠的定量描述）、'
     '并把代理的边界写进结论。'
     '一个诚实的代理标签研究比一个伪装成金标签的研究有价值得多——'
     '后者是当前智能体评测文献的常见病，本包是解药配方之一。'),
]

for anchor, addition in blocks:
    ins(anchor, addition)

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P051 total={cjk+words}')
