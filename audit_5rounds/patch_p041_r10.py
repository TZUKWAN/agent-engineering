# -*- coding: utf-8 -*-
"""P041 round 10 final push."""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P041_tool_namespace_and_candidate_overload\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

additions = [
    # After 4.5 table paragraph
    ('Holm 在 3 假设族内执行；候选规模分层为描述性材料。',
     '\n\n三个判定的组合读法：H1 与 H2 的双 supported 确认了'
     '两个效应的独立存在（命名空间减少缺席、候选数增加缺席），'
     'H3 的 not_specific 表明命名空间的效应不能被服务器集中度'
     '完全解释——感知通道有独立贡献。三个判定合起来的画面是：'
     '候选集有两个可操作的结构杠杆——命名空间分组（减毒）'
     '与候选裁剪（减基线），两者可叠加但机制不同。'),
    # After 4.2 H2 description
    ('这一效应的量级远超 H1 的命名空间效应，应优先执行。',
     '\n\nH2 的候选数量效应还有一个跨包的验证：P039 的候选规模'
     '四分位基线（3.89% 到 29.87%）与本文完全一致——同一帧'
     '同一分箱的结果互为验证。两包共享的基线一致性排除了'
     '单包分析中样本选择偏差的可能——基线的可靠性由'
     '跨包的一致性背书。'),
    # After 5.1 双通道 independence
    ('两者的作用面不同，效应因此独立。',
     '\n\n独立性的实践检验是：如果同时改善命名空间份额'
     '和裁剪候选数，两者的效应应该叠加而非互消。'
     '叠加预测可以从两个独立效应的系数推算：'
     '命名空间份额从 0 到 1（−0.18 logit）加上'
     '候选数从 Q4 到 Q1（−0.87 logit）的联合效应'
     '约为 −1.05 logit——比值比约 0.35，即联合干预'
     '使缺席几率降至基线的三分之一。'
     '这一联合预测的可检验性是双通道模型的实践产出。'),
    # 6 limitations - more items
    ('词面排序栈的结论不外推到语义排序器。',
     '第八，命名空间份额的测量以分隔符的存在为准——'
     '不同命名规范的分隔符约定不同（Java 用点号、'
     'REST 用斜线、Docker 用冒号），'
     '分隔符的覆盖率决定了命名空间份额测量的完整性。'
     '第九，本设计未区分命名空间的层级深度'
     '（aws.s3.list 是两层前缀 vs aws.list 是一层），'
     '层级深度与匹配增益的关系未探索。'),
]

for anchor, addition in additions:
    if anchor in t:
        t = t.replace(anchor, anchor + addition, 1)
        print(f'OK: {anchor[:40]}')
    else:
        print(f'SKIP: {anchor[:40]}')

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P041 total={cjk+words}')
