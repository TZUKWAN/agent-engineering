# -*- coding: utf-8 -*-
"""paper05 深度扩写（第三轮：讨论与实践）。"""
from pathlib import Path

p = Path("G:/刘俊琦/AGENT ENGINEERING/MATLABINTOKEN/paper05_prompt_risk_failure/manuscript.md")
t = p.read_text(encoding="utf-8")

R = [
    ("### 5.3 理论与实践启示",
     """### 5.3 逐特征机制的讨论

四个显著或边缘显著的特征值得逐个讨论。**验证要求缺失**（β = 0.190）是效应最大的风险项：没有验证要求的指令，智能体的推理中缺少“终止核对”环节，错误在未被检查的情况下累积。这与 Paper 01 的发现互为镜像——验证信息的存在降低终止偏差，其缺失则放大执行错误。**完成标准缺失**（β = 0.106）位居第二：与验证缺失相比，完成标准缺失更隐蔽——它不直接指向检查动作，而是让整个任务的目标状态模糊，推理的每一步都缺少“向哪里收敛”的参照。**约束过密**（β = 0.125）的效应方向与 Paper 02 的条件性倒 U 形一致：过密约束意味着执行时要逐项核对边界，任何一步的疏漏都计入错误。**初始状态缺失**不显著（β = 0.003）值得一提：说明智能体在多数任务中能够自行探测初始状态，“从零开始”并不必然诱发错误——这对提示建议的优先级有直接含义：先补验证与完成标准，初始状态可以后置。

### 5.4 理论与实践启示"""),
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
