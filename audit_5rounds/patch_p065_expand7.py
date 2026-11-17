# -*- coding: utf-8 -*-
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P065_what_a_compression_loses_first\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def ins(anchor, addition):
    global t
    assert anchor in t, 'MISS: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

blocks = [
    ('第二，词面命中定义存活：被压缩保留但换了说法的话语算丢失——存活率是字面存活的下界。',
     '\n\n补四条局限。第七，H3 的结局是行政标签（submitted），'
     '"异常丢失无行为代价"不等于"无质量代价"——'
     '下一个尝试可能照样提交但质量更差（重复踩坑后的将就），'
     '质量标注缺失是全系列的共同天花板。'
     '第八，压缩模拟未建模"记忆被使用的方式"：'
     '下一个尝试未必读到被压缩的记忆全文——'
     '若记忆经检索进入（只取相关段落），'
     '头截断的损耗画像与实际进入模型的内容画像不同。'
     '第九，十类话语的词表命中不分主次——'
     '一次随口的"可能"与一段认真的不确定性分析'
     '在 uncert 类里等权，'
     '存活率的语义因此是粗粒度的。'
     '第十，H1 的"预测"由本文设计者冻结，'
     '预测者的代表性（能否代表社区直觉）无法验证——'
     '判定词反驳的是这一份预测，不是所有可能的直觉。'),

    ('工程的一句话版本：别把论文的结论页撕掉再存档——头截断的记忆策略每天都在这么干。',
     '\n\n把十类存活表与系列的另外三张表并排，'
     'wave-11 的话语研究群完成了它的拼图：'
     'P062 给出各类话语的结局权重（结果最强），'
     'P063 给出各类的跨尝试携带（异常最强），'
     '本文给出各类的压缩易损性（结果最脆），'
     'P064 给出词汇层的传递（具体性 0.48）。'
     '四张表交叉之处是最重要的工程优先级：'
     '**结果话语在结局权重、携带强度、易损性三个维度上'
     '全部位于极端——最重要、最可传、最先死。**'
     '这个三重身份使结果话语成为记忆工程的头号保护对象，'
     '任何压缩策略的第一个验收问题都应该是：'
     '结果话语活下来了吗？'
     '本文的 3.4% 就是这个问题的现状答案。'),
]

for anchor, addition in blocks:
    ins(anchor, addition)

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P065 total={cjk+words}')
