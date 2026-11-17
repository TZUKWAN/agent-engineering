# -*- coding: utf-8 -*-
"""paper05 深度扩写（最终轮：方法论细节与数据边界）。"""
from pathlib import Path

p = Path("G:/刘俊琦/AGENT ENGINEERING/MATLABINTOKEN/paper05_prompt_risk_failure/manuscript.md")
t = p.read_text(encoding="utf-8")

R = [
    ("### 3.4 分析方法",
     """### 3.4 分析方法

模型的因变量与链接函数按测量层次选择：推理错误指数与执行错误指数为近似连续的加总指数，用 OLS；任务完成为二值变量，用 Logistic 并报告 OR。控制变量的选择遵循系列统一口径（任务难度、指令词数中心化、操作系统），词数中心化以降低与风险特征的共线性——风险特征多与指令长度正相关。标准误为模型默认的非稳健标准误；作为补充，中介分析使用 bootstrap 重抽样（500 次）直接构造间接效应的百分位置信区间，避免对间接效应分布形态的正态假设。"""),
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
