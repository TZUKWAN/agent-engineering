# -*- coding: utf-8 -*-
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P050_a_cross_task_grammar_of_agent_search\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def ins(anchor, addition):
    global t
    assert anchor in t, 'MISS: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

blocks = [
    ('转移计数分布高度右偏：8 步以内占多数（8 步 97 条、7 步 67 条……），长尾延伸至 30 步以上（图 1d）。',
     '\n\n长度分布的两个尾部对分析有相反的影响。短尾（1-5 步，101 条）是方言份额最高的层'
     '（36%），但样本太少，任何短层结论都要贴上不稳定的标签；'
     '长尾（>15 步）是合并增益的主场——长序列给转移表更多发挥机会，'
     '也使全局节奏的优势累积得更充分。主分析不在长度上切分，'
     '而是在长度带上做异质性诊断（图 2b），让两个尾部各自报告而不是被迫平均。'
     '这种"主分析不动刀、异质性单独报告"的次序是冻结协议的一部分：'
     '若反过来（先找显著分层再定主结论），长度就成了无限量供应的显著性矿脉。'),

    ('**判定规则。** supported 需 |β|≥0.15 nats、CI 排除零、Holm p<0.05；不足但 CI 排除零为 partial。',
     '\n\nnats 量尺上的效应带需要单独标定，这是本设计冻结时的一处自觉。'
     '0.05/0.15/0.30 的带沿用系列回归设计（标准化系数）的刻度，'
     '但似然差的分布尺度完全不同——一个 nats 量尺上 0.33 的效应'
     '在行为预测里是"把一步预测的概率提高 39%"的强效应，'
     '而在回归量尺上 0.33 只是中等。冻结句的处理是把单位写进判定句：'
     '"the estimand is a mean log-likelihood difference per transition, '
     'so the band is applied in nats and the unit it is compared against is named in the artefact"。'
     '结果 H1 的 0.3319 在 nats 带下属于 large（≥0.30）——'
     '但由于前提门未过，这个 large 没有资格变成 supported。'
     '单位敏感的效应带是系列里新出现的一层方法论自觉：'
     '同一个数字 0.15，在不同量尺上是三个不同的世界。'),

    ('分家族看（图 1c）：kubernetes-sigs 0.0216（CI [0.0075, 0.0348]，352 条 rollout、30 个实例），google 点估计 0.0261（288 条）。',
     '\n\n两个家族的方言 CI 恰好是一个可以教读图的样本：kubernetes 的 CI [0.0075, 0.0348]'
     '整个落在 medium 带（0.15）以下，点估计 0.0216 与汇总 0.0805 相差近四倍——'
     '这个差距不是矛盾而是构成：汇总值按 rollout 加权，'
     '而两个达标家族只占 rollout 总量的 3.2%（640/19,981），'
     '其余 96.8% 的 rollout 属于不足 200 条的小家族，'
     '它们的"家族增益"是在极小样本矩阵上估计的，方差大、偶然高增益的家族把汇总拉高。'
     '这正是设计句子"the gain is reported per family rather than pooled, '
     'so a single large family cannot carry the average"的用意——'
     '防的不是大家族刷平均，而是小家族的噪声刷平均。'
     '读者在引用方言增益时应优先引用 per-family 行：0.0216 与 0.0261'
     '这两个达标注脚上的数字，比 0.0805 更接近方言层的真相。'),

    ('实质读法必须由读者自己完成，本文把它写清楚：shuffle 对照显著为负说明**打乱顺序不仅失去增益、还招致确定的损失**——被破坏的转移结构携带 0.3572 nats 的信息（0.3319 的增益 + 0.0253 的伤害）。',
     '\n\n为什么打乱后的序列比 unigram 还差 0.0253 nats？一个过渡态的解释：'
     '打乱保留了每个 rollout 的边际词频，但破坏了它的局部共现——'
     '被打乱的序列会频繁出现"不该连的家族对"（如提交后紧跟广度检索），'
     'bigram 模型给这些组合极低的概率，比 unigram 对同样组合给出的平均概率更低。'
     '所以负伤害的来源恰恰是 bigram 模型学到了"哪些转移不发生"——'
     '禁止性知识（哪些组合不该出现）是顺序信息中被忽视的一半。'
     '这给工程一个提示：行为异常检测器最有信号的部分不是预测"下一步做什么"，'
     '而是识别"下一步不该做什么"——本文的 shuffle 负增益就是这个检测器的理论下界。'),
]

for anchor, addition in blocks:
    ins(anchor, addition)

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P050 total={cjk+words}')
