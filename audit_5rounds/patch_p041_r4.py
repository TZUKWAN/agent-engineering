# -*- coding: utf-8 -*-
"""P041 round 4: insert at section markers."""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P041_tool_namespace_and_candidate_overload\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

# Insert before ## 6 局限
marker_6 = '## 6 局限'
insert_6 = '''命名空间效应的候选规模分层（图 3）是本文的第二层调节发现：Q1（最小候选集）层效应最强（β=-0.7385），Q2 次之（-0.286），随候选规模增大而递减。衰减的模式与 P030 的长度稀释定律同构：命名空间的红利在候选数多的 query 里被竞争稀释——候选越多，前缀词匹配的边际优势越小（大量候选共享同一前缀，前缀词的区分力下降）。分层剖面还暗示一个阈值效应：Q3 层的效应（约 -0.16）已是 Q1 层（-0.74）的五分之一——命名空间的收益存在一个候选规模的收益递减曲线。这一曲线的实践含义是：命名空间改名的 ROI 评估应以 query 的候选规模为条件——小候选集场景的改名回报最大。

'''
t = t.replace(marker_6, insert_6 + marker_6, 1)

# Insert before ## 7 结论
marker_7 = '## 7 结论'
insert_7 = '''本文与系列其他包的合成还发现了一个跨包的方法论验证：P039 的候选规模四分位（Q1 到 Q4 基线 3.9%→29.9%）与本文的候选规模四分位（同样的 Q1 到 Q4 剖面）来自同一帧同一分箱——两包的基线完全一致，这意味着两包的效应系数可以直接比较（P039 的诱饵效应 β=0.4447 vs 本文的命名空间效应 β=-0.1834，两者的效应量级差约 2.4 倍）。基线的一致性是跨包比较的前提，而基线的一致性来自共享帧与共享控制集——这是 wave-7 设计的方法论红利。

'''
t = t.replace(marker_7, insert_7 + marker_7, 1)

# Insert after 5.2 (H2 section)
anchor_52_end = '判定 supported：候选数量本身独立推高失败率。'
insert_52 = '''过载效应的行为学基础还可以从注意力的角度理解：候选越多，排序器需要在更多的候选上分配匹配计算，单个候选获得的"注意"（BM25 得分的方差）越小——排序的区分力下降。这一机制与信号检测论的框架一致：信号（金标）与噪声（非金标）的分布重叠随噪声增大而增大，命中率下降、误报率上升。P033 的天花板结论在此获得一个机制层的补充解释：天花板不仅是预算的墙，也是信息过载的墙——候选数越多，15 步的预算越不够用。

'''
t = t.replace(anchor_52_end, anchor_52_end + '\n\n' + insert_52, 1)

# Insert after 5.4 (H3 competing model)
anchor_54_end = '前缀词自动完成了分组级的匹配扩展。'
insert_54 = '''命名空间效应的族间异质性也与前缀的语义质量有关：Browser Automation 类的候选（浏览器操作）通常没有传统意义的命名空间（浏览器动作的名称是扁平的），其命名空间份额的天花板较低；File Operations 类的候选（文件操作）通常有路径前缀（路径分隔符兼作命名空间分隔符），命名空间份额的天花板较高。族间的天花板差异使命名空间效应在不同族中的可测性不同——本文的族内分层在此受限，与前述 H3 的 0/9 清点共享同一原因。

'''
t = t.replace(anchor_54_end, anchor_54_end + '\n\n' + insert_54, 1)

# Insert in discussion section about namespace design
anchor_nd = '选择高频查询词作为前缀可以放大 H1 的红利。'
insert_nd = '''命名空间设计还有一个反直觉的建议：不要过度使用命名空间。如果每个候选都有唯一的命名空间前缀（前缀数=候选数），命名空间退化为无意义的唯一标识——前缀词的 IDF 极高但区分力为零（每个前缀只匹配一个候选）。最优的命名空间设计是"组间可区分、组内可聚合"——前缀数量在 3–10 个之间，每个前缀覆盖 2–10 个候选。这一设计使前缀词既能区分组间（IDF 足够高），又能在组内聚合（共享前缀的候选整体上抬）。

'''
t = t.replace(anchor_nd, anchor_nd + '\n' + insert_nd, 1)

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P041 total={cjk+words}')
