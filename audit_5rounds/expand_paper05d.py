# -*- coding: utf-8 -*-
"""paper05 深度扩写（第四轮：引言/方法/指标/结论）。"""
from pathlib import Path

p = Path("G:/刘俊琦/AGENT ENGINEERING/MATLABINTOKEN/paper05_prompt_risk_failure/manuscript.md")
t = p.read_text(encoding="utf-8")

R = [
    ("### 3.3 推理错误与执行错误指标",
     """### 3.3 指标构建的构念依据

13 项错误代理指标按“发生在推理侧还是执行侧、错误的心理阶段”划分为两组。**推理错误指数**（7 项）捕捉“想错了”：目标误解（goal_misunderstood）、约束遗漏（constraint_omitted_in_reasoning）、错误环境假设（wrong_environment_assumption）、分解不当（poor_decomposition）、反馈后未修正（no_correction_after_feedback）、重复原策略（reason_repeat_strategy）、提前认为完成（premature_done_belief）。**执行错误指数**（6 项）捕捉“做错了”：无效操作（exec_invalid_operation）、操作与推理不符（action_inconsistent_with_reasoning）、重复动作（exec_repeated_action）、失败终止（exec_failed_termination）、任务未完成（exec_task_incomplete）等。两组的划分依据是错误的可观察位置——前者只出现在文本中，后者伴随环境状态改变。加总为指数而非逐项建模的理由是：单项发生率过低（部分不足 1%），指数在保留方差的同时稳定了测量。"""),
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
