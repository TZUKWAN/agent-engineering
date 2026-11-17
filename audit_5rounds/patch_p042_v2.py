# -*- coding: utf-8 -*-
"""P042 expansion via text anchors."""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P042_the_catalogue_ecosystem\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

patches = []

patches.append((
    '生态就是同质的。',
    '\n\n两种世界观在数据上的判别可以用一个数字完成：'
    '同服务器对描述的 Jaccard 减去跨服务器对的 Jaccard。'
    '差值大于零即特化（同源更相似），差值等于零即同质（换标复本），'
    '差值小于零即反特化。本文的 H1 就是这个差值的 bootstrap 检验。'
    '\n\n命名空间的形态需要先描述：前缀以分隔符切分工具名称，'
    '通常对应工具的提供方或功能域。份额均值 0.6198 说明'
    '命名空间是主流形态而非例外。'))

patches.append((
    '特化是相对的，不是绝对的。',
    '\n\n特化的相对性有一个直接含义：如果目录新增一个工具，'
    '其描述与已有工具的词汇重叠会改变所有受影响对的 Jaccard——'
    '目录是动态的，特化度也是动态的。'
    '本文测量的是特化度的一个快照，不是固有属性。'))

patches.append((
    '少数大服务器贡献了不成比例的候选份额。',
    '\n\n长尾的含义是：目录的功能覆盖主要由长尾的微服务器贡献'
    '（多数服务器贡献 1-3 个工具），'
    '但排序的计算负担主要由头部的大服务器贡献'
    '（get 一个服务器就有 16,045 个候选插槽）。'
    '功能覆盖与计算负担的分离是生态治理的结构性事实。'))

patches.append((
    '任何涉及数据获取或文件操作的都可能用到。',
    '\n\n高复用名的语义泛化还有一个命名规范的解读：'
    '这些词是英文中语义泛化度最高的名词之一。'
    '泛化性使它们成为跨域复用的自然候选——'
    '不同服务器的开发者独立地选择了相同的通用名词'
    '来命名各自域内的相似操作。'
    '复用因此不是抄袭，是通用名词的自然趋同。'))

patches.append((
    '当前数据远未达到。改善路径是在同服务器的工具描述中',
    '\n\n特化的词汇信号虽然存在，但不足以支撑按服务器浏览的'
    '导航范式。改善路径是在同服务器的工具描述中'
    '引入共享的域术语表，有意识地提高同源重叠。'))

patches.append((
    '命名复用是冗余的信号。',
    '\n\n本文的 H1 框架可以直接扩展到这一判定——'
    '同名跨服务器对的描述 Jaccard 分布是判别的量尺。'
    '判别的操作化：同名工具的描述重叠低于阈值则为合理多态，'
    '高于阈值则为功能冗余。'))

patches.append((
    '三维评估框架是候选空间行为学的完整画面。',
    '\n\n也是 P040 可供性语言第四维的自然扩展空间。'))

patches.append((
    '前者保护，后者治理。',
    '\n\n本文也是系列中第一个在 server 级聚类的包——'
    '聚类单位从 query 或 turn 变为 server。'
    '结论的稳健性不依赖于 query 的抽样方式。'))

patches.append((
    '来源的定义粒度影响特化信号的量级。',
    '\n\n第七，Jaccard 只测词汇重叠——语义同义不计。'
    '第八，服务器规模极度偏斜（中位 1、最大 475），'
    '薄层统计的功效受限。'))

for anchor, addition in patches:
    if anchor in t:
        t = t.replace(anchor, anchor + addition, 1)
        print(f'OK: {anchor[:40]}')
    else:
        print(f'SKIP: {anchor[:40]}')

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P042 total={cjk+words}')
