# -*- coding: utf-8 -*-
"""paper05 深度扩写（第五轮）。"""
from pathlib import Path

p = Path("G:/刘俊琦/AGENT ENGINEERING/MATLABINTOKEN/paper05_prompt_risk_failure/manuscript.md")
t = p.read_text(encoding="utf-8")

R = [
    ("## 1. 引言",
     """## 1. 引言

提示工程研究在过去两年迅速积累了“什么让智能体做得更好”的知识：角色设定、思维链、少样本示例、工具使用说明都被证明能提升任务表现。然而，工程实践的反面问题——**什么让智能体失败**——得到的关注却不成比例。失败分析通常以案例研究的形式出现，缺乏系统的变量化：我们很少能回答“一条指令携带多少风险、风险经由什么机制转化为失败”。

本研究把失败分析前移到指令侧，提出并检验一条可量化的观察性路径：**提示风险 → 推理错误 → 执行错误 → 任务失败**。路径的每一环都对应可规则化测量的变量：提示风险由十项语用特征加总；推理错误与执行错误是由推理文本和步骤标注构建的两个错误指数；任务失败即完成标签。检验这条路径的价值有二：对研究者，它把“提示质量”分解为可归因的中间机制；对实践者，它指出干预的最佳位置——不是笼统地“写好提示”，而是针对性补全缺失的验证与完成信息。"""),
]
old_anchor = "本文沿用前三篇的提示语用特征变量体系" if "本文沿用前三篇的提示语用特征变量体系" in t else None
# 在引言的路径段后补充边界段
anchor2 = "针对性补全缺失的验证与完成信息。"
add2 = "针对性补全缺失的验证与完成信息。本研究严格遵守数据边界：仅使用公开的 AgentNet 轨迹做二次分析，不调用任何大模型 API 生成新轨迹或新标注；所有统计结果来自真实数据；所有结论均表述为“关联”或“观察性统计路径”，不声称因果机制。"
if anchor2 in t and add2 not in t:
    R = R + []
    t = t.replace(anchor2, add2, 1)
miss = []
for o, n in R:
    if o in t:
        t = t.replace(o, n, 1)
    else:
        miss.append(o[:50])
p.write_text(t, encoding="utf-8")
print("applied", len(R) - len(miss), "/", len(R))
for m in miss:
    print("MISS:", m)
