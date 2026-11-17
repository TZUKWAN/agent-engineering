# -*- coding: utf-8 -*-
"""paper05 深度扩写（第八轮：数据节与风险机制）。"""
from pathlib import Path

p = Path("G:/刘俊琦/AGENT ENGINEERING/MATLABINTOKEN/paper05_prompt_risk_failure/manuscript.md")
t = p.read_text(encoding="utf-8")

R = [
    ("### 5.1 提示风险如何诱发失败",
     """### 5.1 提示风险如何诱发失败

“风险经由错误传导”的机制可以在三个认知环节上定位。**理解环节**：目标抽象、对象缺失、指代不明直接增加指令解析的歧义，使智能体在首个推理块中就可能锁定错误的目标表征——推理错误指数中的“目标误解”项即该环节的标记。**规划环节**：约束缺失或约束冲突使智能体在生成动作序列时缺少边界检查，规划出的路径可能可行但不合规；多子任务无顺序则使规划的步骤间依赖缺失。**终止环节**：完成标准与验证要求缺失使智能体缺少“停止前核对”的触发器——这正是 Paper 01 的“终止判准”缺失形态；其在数据上的表现是推理含终止词但任务未完成（premature_completion 指标）。三个环节中，理解与规划的失败累计为推理错误指数，终止失败集中体现为执行错误指数与完成标签——这一分解恰好对应本文模型 1（风险→推理）与模型 2/3（推理→执行→完成）的两段式设计。"""),
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
