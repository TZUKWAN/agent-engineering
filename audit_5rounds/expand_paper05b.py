# -*- coding: utf-8 -*-
"""paper05 深度扩写（第二轮：理论、机制、限制）。"""
from pathlib import Path

p = Path("G:/刘俊琦/AGENT ENGINEERING/MATLABINTOKEN/paper05_prompt_risk_failure/manuscript.md")
t = p.read_text(encoding="utf-8")

R = [
    ("### 2.1 提示风险的概念",
     """### 2.1 提示风险的概念

**提示风险**（prompt risk）指用户指令中可观测的语言特征，这些特征在既有研究与任务分析中被认为会增加智能体执行失败的概率。与“指令质量”这一笼统概念不同，提示风险强调三点：其一，风险是**可观测的语言事实**（某个必要成分是否缺失、某种冲突是否出现），而非对用户能力的评价；其二，风险是**分维度的**——验证缺失、约束缺失、指代不明等是不同的失败诱因，需要分开测量；其三，风险与失败的关系是**概率性**的——风险特征提高失败的先验概率，不决定单次任务的成败。这一概念化使提示风险可以脱离专家直觉、以规则化方式在大规模语料上测量，也与本文“无模型调用”的数据边界一致。

### 2.2 推理错误与执行错误"""),
]
miss = []
for o, n in R:
    if o in t:
        t = t.replace(o, n, 1)
    else:
        miss.append(o[:60])
p.write_text(t, encoding="utf-8")
print("applied", len(R) - len(miss), "/", len(R))
for m in miss:
    print("MISS:", m)
