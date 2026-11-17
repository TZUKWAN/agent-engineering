# -*- coding: utf-8 -*-
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P051_early_signals_of_agent_search_failure\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def ins(anchor, addition):
    global t
    assert anchor in t, 'MISS: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

blocks = [
    ('重复份额 0.0004（开局几乎不重复——重复是中后段现象，与 P038 的反刍定位一致）。',
     '\n\n五特征窗口的选择有一个隐含的稳健性来源：'
     '它们全部是比例或计数，不依赖任何嵌入模型或外部词表，'
     '换一个模型栈、换一种命令命名方案，特征的定义不变、量纲不变。'
     '这使本文的读数对未来复现友好——不利之处同样明确：'
     '比例与计数只能触及行为的节奏层，'
     '内容层（模型在找什么、找到的东西对不对）完全在特征视野之外。'
     '3.3 的警告一之所以能轻易得手，部分原因正在于此：'
     '节奏层特征天然与轨迹长度纠缠，'
     '而内容层特征（如检索词与任务的相关度）才可能提供长度之外的增量。'),

    ('H1 的 supported 判定在字面上无懈可击：交叉验证 AUC 0.6857，CI 下界 0.6598 高于机遇、点估计高于 0.65 地板，Holm 校正后 p=0.0025。',
     '\n\n这个设计的对抗性值得点明：冻结句不是在帮假设通过，而是在设置'
     '最难通过的关卡组合。H1 的 0.65 地板看似宽松（AUC 0.65 在预测文献里'
     '只算中等），但它被两个陪审包围——家族复现要求（至少 3/5 家族达 0.65）'
     '与基线同台（length-only 打印）。结果恰好呈现三层结构：'
     '字面关卡过了（0.6857>0.65）、家族复现全灭（0/3）、'
     '基线碾压（0.8604）。若设计只保留 H1，论文的摘要会是'
     '"早期信号存在，AUC 0.69"——一个技术上真实、实践上误导的句子。'
     '三层结构迫使摘要写成现在的样子：supported 与三条警告同印。'
     '冻结协议在这里扮演的角色是叙事的防波堤，不是结论的橡皮图章。'),
]

for anchor, addition in blocks:
    ins(anchor, addition)

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P051 total={cjk+words}')
