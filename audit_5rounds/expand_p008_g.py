# -*- coding: utf-8 -*-
"""P008 追加最终内容块 C（达标用）。"""
from pathlib import Path
import re

p = Path(r"G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P008_query_reformulation_fidelity\paper_cn.md")
t = p.read_text(encoding="utf-8")

ADDITIONAL = """
---

## 5.17 改写保真度与智能体训练的关系

改写保真度的概念也对智能体的训练方法有启示。当前智能体的训练通常以最终任务完成率为优化目标，推理链的质量仅通过间接方式（如作为中间生成步骤）影响训练信号。如果在训练目标中加入改写保真度的正则项——例如，要求智能体在推理中显式复述原始指令的关键成分——可能通过提高推理链的信息保真度来间接提升任务完成率。这种训练策略的理论基础是：改写保真度作为领先指标，可以在执行结果尚未确定时就识别出高失败风险的轨迹；以保真度为辅助训练信号，相当于在训练过程中增加了一个中间监督点，可能改善梯度信号的质量和训练效率。

此外，改写保真度的三层框架还可以用于诊断不同训练阶段或不同模型规模的智能体在信息保留能力上的差异。如果保真度随模型规模增加而提升，则说明信息保留能力是可以通过规模化改善的；如果不随规模变化，则说明信息丢失是推理链范式的结构性约束，需要通过架构创新（如增加显式信息追踪模块）来解决。
"""

ref_idx = t.find("## 参考文献")
if ref_idx >= 0:
    t = t[:ref_idx] + ADDITIONAL.strip() + "\n\n---\n\n" + t[ref_idx:]
else:
    t = t.rstrip() + "\n\n" + ADDITIONAL

p.write_text(t, encoding="utf-8")

cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f"CJK: {cjk}, words: {words}, total: {cjk + words}")
