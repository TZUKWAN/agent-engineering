# -*- coding: utf-8 -*-
"""P031 最终冲线（+150 字）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P031_explanatory_coherence_and_evidential_gaps\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 摘要末尾补一句 ----
insert_after(
    '话语审计的前提因此更加稳固。',
    '稳固之余也划出了边界：排除以词汇取材为口径、以 1–3 步链为范围、'
    '以当前架构为条件——三重限定随判定词一并存档。',
    )

# ---- 4.5 表后补一句 ----
insert_after(
    '空结果与稳健性失败各得其所，互不冒名。',
    '链长描述曲线的平坦与四分位符号的散乱在图上互为印证——'
    '均值层与分层层给出一致的空画面，是空结果完整的两条腿。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P031 total={cjk+words}')
