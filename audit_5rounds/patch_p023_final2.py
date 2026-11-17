# -*- coding: utf-8 -*-
"""P023 最终冲线补丁（+250 字以上）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P023_modality_and_verification\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 1.3 预告后补一段 ----
insert_after(
    '任何把情态当作单一特征的使用方式都会把两个相反的效应加总成噪声。',
    '\n\n方法学的一个预告也放在这里：本文是系列第一个 turn 级设计（前三波以查询或候选为单位），'
    '分析单位从"一次选择"变成"一次表述加一次行动"，这带来两个技术变化——'
    '控制集从检索栈特征换成轨迹结构特征（位置、长度、先验史），'
    '聚类单位从 query_id 换成 traj_id。两个变化都被证明可行且必要：'
    '没有 turn 级的分辨率，情态-检验联结根本无法定义；'
    '没有轨迹聚类，十五万 turn 的名义样本会制造出荒谬的置信区间。',
    )

# ---- 4.5 表后补充 ----
insert_after(
    'Holm 在 3 假设族内执行；位置分层为描述性材料。',
    '\n\n族内校正的实际影响与系列各包一致地轻微：H1 与 H3 的 p_raw 都在 10⁻³ 以下，'
    '校正不改变任何判定；H2 的 p_raw 本就高达 0.36。'
    '真正承载本文证据分工的是三个判定词的语义差异——supported 记录一个成立的联结，'
    'null 记录一个被否定的机制剧本，not_specific 记录一次未开赛的对照——'
    '三者合起来才是对"情态词作为认识状态测量"这一候选的完整资格审查。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P023 total={cjk+words}')
