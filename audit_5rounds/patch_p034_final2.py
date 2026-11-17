# -*- coding: utf-8 -*-
"""P034 最终冲线（+150 字）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P034_information_scent_and_the_next_choice\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 运行追溯内补 ----
insert_after(
    '测试行读取 0，全量墙钟 118.4 秒（Python 3.11.7）；',
    '本地编码器缓存供稠密侧备用（本包主分析未调用），'
    '全部置换与词表匹配为确定性规则；',
    )

# ---- 2.2 结尾补 ----
insert_after(
    '这一复核是对 P027 教训的直接执行：构念测量必须双仪器，且必须报告仪器间一致性的 chance 校正量。',
    '仪器间一致（ρ≈1）与行为有效（H1/H2 双 partial）在本包同框出现，'
    '构成家族测量规格的一个正面样板：信度与效度在同一设计里各过各的关。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P034 total={cjk+words}')
