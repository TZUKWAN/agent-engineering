# -*- coding: utf-8 -*-
"""P041 round 8 final."""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P041_tool_namespace_and_candidate_overload\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

additions = [
    ('命名空间份额每升一档',
     '\n\nH1 的效应量换算为实践语言：'
     '缺席 logit 下降约 0.18——比值比 0.83，'
     '即缺席几率降低约 17%。'
     '在缺席基率 17.86% 的条件下，'
     '这约 3 个百分点的改善意味着每 100 条 query 约 3 条从失败转为成功。'),
    ('感知机制有独立贡献。',
     '\n\n独立效应的量级也值得注意：控制集中度后命名空间的系数'
     '绝对值增大。集中度的加入释放了命名空间被集中度正效应'
     '抵消的部分。'),
    ('两类重复的分离已由定义完成。',
     '\n\n第十一，重复判定的跨轨迹共性（图 4 的八条高频命令串）'
     '虽然不影响 H1 的样本（定义限于 rollout 内），但它们'
     '污染了跨轨迹的命令频次统计——如果后续研究使用命令频次'
     '作为行为特征（如命令熵），需要先剥离跨轨迹的通用命令。'),
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
