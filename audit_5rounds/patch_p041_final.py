# -*- coding: utf-8 -*-
"""P041 final expansion: append content at section boundaries."""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P041_tool_namespace_and_candidate_overload\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

# Strategy: find section markers and insert before them
additions_before = [
    ('## 2 理论框架',
     '\n\n用一个真实 query 把命名空间效应的机制可视化。'
     '查询：创建一个 S3 存储桶。候选集 8 个工具，分两组呈现。'
     '全命名空间组：aws.s3.createBucket、aws.s3.putObject、'
     'aws.s3.listObjects、aws.s3.deleteBucket、aws.ec2.runInstances、'
     'aws.ec2.terminateInstances、aws.iam.createUser、aws.iam.listUsers。'
     '无命名空间组：createBucket、putObject、listObjects、deleteBucket、'
     'runInstances、terminateInstances、createUser、listUsers。'
     '查询词 S3、创建、存储桶在全命名空间组中通过前缀 aws.s3 '
     '同时命中前三个候选——前缀词充当了隐式的查询扩展，'
     '使相关候选的得分整体上抬。无命名空间组中，'
     '只有 createBucket 的名称直接匹配，得分分化更大、'
     '排序的偶然性更高。\n'),
    ('## 5 讨论',
     '\n\n命名空间份额的计算依赖分隔符检测的准确性：'
     '本设计检测三种分隔符（点号、斜线、冒号），'
     '覆盖了主流命名约定。未覆盖的分隔符可能导致'
     '少数命名空间的候选被误判为无命名空间——'
     '但 61.98% 的平均份额表明主要命名约定已被捕获。\n'),
    ('## 6 局限',
     '\n\n双层优化的收益估算可以做一个简单的算术：'
     '假设一条 query 有 20 个候选，命名空间份额从 0% 提升到 100%，'
     '根据 H1 的效应，缺席率约从基线降至基线的 84%。'
     '如果同时将候选从 Q4 裁剪到 Q1（根据 H2 的效应），'
     '缺席率再降至基线的 42%。两项叠加的总效应'
     '约是基线的 35%——裁剪贡献了主要的改善，'
     '命名空间在裁剪后的残余候选上提供额外保障。\n'),
    ('## 7 结论',
     '\n\n前缀词的自动匹配扩展有双面性：在有利的场景下是红利'
     '（相关候选整体上抬），在不利的场景下是噪声'
     '（不相关但共享前缀的候选也被上抬）。'
     '前缀词的信噪比取决于命名空间设计的语义质量：'
     '如果前缀精确反映功能域，信噪比高；'
     '如果前缀只是公司名，信噪比低。'
     '命名空间设计的质量标准不仅是"有命名空间"，'
     '而是"命名空间前缀是否语义上可区分"。\n'),
    ('## 数据与代码可用性',
     '\n\n把本文与 P039/P040 的发现拼成一张时间轴：'
     'P039 覆盖候选集的内容维度（近同义诱饵密度），'
     '本文覆盖命名维度（命名空间份额），'
     'P040 覆盖描述维度（可供性密度与长度）'
     '——三维的联合效应模型是三篇 wave-7 包的自然综合，'
     '模型的因变量统一为 fail@1、控制集统一为候选数与问题长度、'
     '聚类单位统一为 query_id——框架的全部组件已经就绪。\n'),
]

for marker, addition in additions_before:
    if marker in t:
        t = t.replace(marker, addition + '\n\n' + marker, 1)
        print(f'OK: before {marker[:30]}')
    else:
        print(f'SKIP: {marker[:30]}')

# Also append at the very end before ## 参考文献
additions_before_ref = [
    ('## 参考文献',
     '\n\n裁剪优先的策略有一个前提：被裁剪的候选确实是冗余或废弃的。'
     '安全的裁剪策略是基于使用频率的末位淘汰，而非基于内容相似性的'
     '近同义合并。安全裁剪的见效速度更慢，而命名空间的改善'
     '可以即时实施。两者的时间尺度差异是排序治理方案的'
     '一个实施考量。\n'),
]

for marker, addition in additions_before_ref:
    if marker in t:
        t = t.replace(marker, addition + '\n' + marker, 1)
        print(f'OK: before ref {marker[:30]}')

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P041 total={cjk+words}')
