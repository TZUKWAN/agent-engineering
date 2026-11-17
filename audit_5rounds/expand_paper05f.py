# -*- coding: utf-8 -*-
"""paper05 深度扩写（第六轮：操作化、分布、结论）。"""
from pathlib import Path

p = Path("G:/刘俊琦/AGENT ENGINEERING/MATLABINTOKEN/paper05_prompt_risk_failure/manuscript.md")
t = p.read_text(encoding="utf-8")

R = [
    ("### 3.2 提示风险特征",
     """### 3.2 提示风险特征

十项风险特征全部由正则与词表规则在指令文本上计算，可分三组。**缺失组**（5 项）检查必要的语用成分是否缺位：目标抽象（instruction 仅给高层目标而无具体对象/状态）、对象缺失（未指明操作对象）、完成标准缺失、约束缺失（全无约束词）、初始状态缺失；其中四项以“未命中任何相关词表”判定，约束缺失继承 Paper 02 的约束词表。**过载组**（2 项）检查语言成分的超量：约束过密（约束词密度超过样本 95 分位的任务）与约束冲突（“必须/只能”与“不要/不能”共存于同一指令）。**结构组**（3 项）检查组织缺陷：多子任务无顺序（多子任务且无序列连接词）、指代不明（it/this/that 等无明确先行词的指代）、验证要求缺失（全无验证类词汇）。三组划分直接对应路径模型的三类失败诱因：信息不足、信息过载、组织混乱。"""),
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
