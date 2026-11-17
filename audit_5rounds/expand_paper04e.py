# -*- coding: utf-8 -*-
"""paper04 深度扩写（第五轮：数据节、稳健性、结果解读）。"""
from pathlib import Path

p = Path("G:/刘俊琦/AGENT ENGINEERING/MATLABINTOKEN/paper04_reasoning_typology/manuscript.md")
t = p.read_text(encoding="utf-8")

R = [
    ("本研究使用公开数据集 **AgentNet**（xlangai/AgentNet），从 Hugging Face 下载。该数据集包含 Windows/macOS/Ubuntu 桌面 GUI 环境下的任务轨迹。原始数据包括两个 JSONL 文件：`agentnet_ubuntu_5k.jsonl`（5,000 条）和 `agentnet_win_mac_18k.jsonl`（17,625 条），合计 22,625 行记录，其中 93 条为重复 `task_id`（官方元数据 `meta_data_merged.jsonl` 为 22,532 条）；按官方 step_num 匹配优先、否则保留末次出现的规则去重后为 **22,532 条任务**、**416,186 个步骤**。每条任务包含用户指令、任务完成标签、对齐评分、效率评分、难度评分以及轨迹步骤。每个步骤包含 `observation`、`thought`、`action`、`code`、`reflection`、`last_step_correct`、`last_step_redundant` 等字段。",
     "本研究使用公开数据集 **AgentNet**（xlangai/AgentNet，Wang et al., 2025），从 Hugging Face 下载。该数据集包含 Windows/macOS/Ubuntu 桌面 GUI 环境下的任务轨迹。原始数据包括两个 JSONL 文件：`agentnet_ubuntu_5k.jsonl`（5,000 条）和 `agentnet_win_mac_18k.jsonl`（17,625 条），合计 22,625 行记录，其中 93 条为重复 `task_id`（官方元数据 `meta_data_merged.jsonl` 为 22,532 条）；按官方 step_num 匹配优先、否则保留末次出现的规则去重后为 **22,532 条任务**、**416,186 个步骤**（逐条裁决记录见 `data/interim/paper04/dedup_audit.json`；被去重的 93 条中有 76 条与保留行的完成/评分标签互相冲突，说明重复行并非无害冗余，去重是保证结论可信的必要步骤）。每条任务包含用户指令、任务完成标签、对齐评分、效率评分、难度评分以及轨迹步骤。每个步骤包含 `observation`、`thought`、`action`、`code`、`reflection`、`last_step_correct`、`last_step_redundant` 等字段。进入聚类的分析样本为 20,298 行（20,205 个唯一任务上推理特征完整的记录）。"),
    ("k = 4 时轮廓系数为 0.164，BIC 为 449,167.9，在统计拟合与类型可解释性之间取得平衡。",
     "k = 4 时轮廓系数为 0.164，BIC 为 449,167.9，在统计拟合与类型可解释性之间取得平衡。轮廓系数 0.164 属于\"弱分离\"区间，这是推理文本特征空间的常态：任务形态是连续谱而非离散盒，任何硬划分都会在相邻类边界处产生重叠。因此，本文对类型边界的解读保持概率式口径——类型刻画的是\"以该组织方式为主\"的任务群，而非同质无异的单质组。"),
    ("结果显示，在控制任务难度、操作系统和推理长度后，**简洁直觉型**的任务完成 odds 显著低于常规综合型（OR = 0.60），而**详细展开型**的完成 odds 显著高于常规综合型（OR = 1.30）。结构化分解型与常规综合型之间差异不显著（p = 0.778）——值得注意的是，该型虽在描述层面拥有最高的完成率（81.9%），但其优势被更长的推理（推理长度控制项）与任务难度所吸收：结构化分解型任务的推理更长、难度分布不同，控制这些因素后其残余优势不再显著。两个控制变量本身均显著：难度每升 1 分完成 odds 下降约 14%（OR = 0.863），win_mac 平台约为 Ubuntu 的一半（OR = 0.484），后者与 Paper 01 的平台效应方向一致。",
     "结果显示，在控制任务难度、操作系统和推理长度后，**简洁直觉型**的任务完成 odds 显著低于常规综合型（OR = 0.60），而**详细展开型**的完成 odds 显著高于常规综合型（OR = 1.30）。结构化分解型与常规综合型之间差异不显著（p = 0.778）——值得注意的是，该型虽在描述层面拥有最高的完成率（81.9%），但其优势被更长的推理（推理长度控制项）与任务难度所吸收：结构化分解型任务的推理更长、难度分布不同，控制这些因素后其残余优势不再显著。两个控制变量本身均显著：难度每升 1 分完成 odds 下降约 14%（OR = 0.863），win_mac 平台约为 Ubuntu 的一半（OR = 0.484），后者与 Paper 01 的平台效应方向一致。推理长度的系数量级极小（每词 0.00006）但高度显著：在类型与难度之外，推理每多一词仅带来可忽略的完成率增益——这再次印证\"写得多\"不是\"做得好\"的来源，组织方式才是。"),
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
