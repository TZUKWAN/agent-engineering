# -*- coding: utf-8 -*-
"""P009 追加统一决策模型解释段。"""
from pathlib import Path
import re

p = Path(r"G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P009_lexical_match_bias\paper_cn.md")
t = p.read_text(encoding="utf-8")

old_text = "不存在独立于金标相关性的偏倚（H3 零效应）。这一结论对智能体评测的含义是"

new_text = """不存在独立于金标相关性的偏倚（H3 零效应）。

这一三重发现的内部一致性可以通过一个简化的两步决策模型来理解。第一步，检索器根据词汇重叠度对所有候选排序。第二步，智能体从排名靠前的候选中选择一个。在这一模型中，金标工具因为与指令的语义匹配度最高（指令就是针对它写的），天然获得最高的词汇重叠度和最高的 BM25 排名。高重叠非金标候选虽然也有较高的词汇重叠度，但低于金标工具——因此它们在排序中位于金标之后。H1 的反向位移率正是因为金标工具的保护效应：金标工具占据了 Top-1，高重叠非金标候选无法超越。H2 的支持结果出现在包含金标工具的查询中：高重叠非金标候选虽然不及金标工具，但远超低重叠非金标候选。H3 的零效应则因为一旦金标哑变量控制了候选是否为正确答案，词汇重叠的额外贡献被完全吸收。三个结果从三个互补角度共同描绘了词汇匹配在工具选择中的完整作用图景。

这一结论对智能体评测的含义是"""

t = t.replace(old_text, new_text, 1)
p.write_text(t, encoding="utf-8")

cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f"CJK: {cjk}, words: {words}, total: {cjk + words}")
