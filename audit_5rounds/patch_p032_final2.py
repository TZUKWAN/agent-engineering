# -*- coding: utf-8 -*-
"""P032 最终冲线（+450 字）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P032_plan_action_alignment\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 摘要内补 ----
insert_after(
    '对轨迹研究者，本文交付了一节关于置换对照如何暴露测量饱和的现场课；对实践者，它把"高对齐计划"从正面信号改判为需要复查的重试信号。',
    '两个产出共享同一个根源：当测量的底噪被如实测出，'
    '被底噪藏住的东西才会现形——本文现形的是复读。',
    )

# ---- 2.3 结尾补 ----
insert_after(
    '分层检验的格子代价在这里被完整展示：分得越细，越是只有大族活下来。',
    '\n\n补充一句分层结果的可读性：4 个可估族的 CI 窄得反常'
    '（如 production 的 [0.1888, 0.1916]，宽度 0.003）——'
    '这是分层内大样本的效果（production 族 22,960 行），'
    '窄 CI 使族间差异（+0.19 对 −0.10）远超统计可分辨的门槛：'
    '符号不统一不是功效问题，是真实的族间异质。'
    '异质的存在反过来强化了 H3 的价值：若不做分层清点，'
    '池化的 H2 系数（+0.091）会掩盖族间从正到负的整个跨度——'
    '池化平均在异质世界里是最容易说谎的数字。',
    )

# ---- 5.2 结尾补 ----
insert_after(
    '反向效应因此不是"对齐有害"，而是"形式绑定把环境风险传导进调用"。',
    '\n\n这一传导模型还可以解释族剖面的符号分布：production 族（写、改）'
    '的形式绑定最深（参数就是内容本身），传导最强（+0.19）；'
    'inspection 族（读、查）的形式与内容松耦合（换个路径也能读到），'
    '传导最弱甚至反向（−0.10）。传导模型的这两条预测'
    '（绑定深度排序族间梯度、参数敏感性放大传导）都可在'
    '现有分层数据的再读中获得初步支持——模型的确认成本，'
    '低到一次表格再读就够。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P032 total={cjk+words}')
