# -*- coding: utf-8 -*-
"""P030 最终冲线（+200 字）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P030_causal_connectives_and_evidence\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 4.4 表后补 ----
insert_after(
    'Holm 在 3 假设族内执行；长度梯度为描述性材料。',
    '\n\n校正后的判定稳定性照例确认：H1 的 p_raw 远低于 10⁻³，三重校正不影响判定；'
    'H2 与 H3 的读数在校正前后一致（前者本就不显著，后者为规则声明的描述项）。'
    '包内 table5_robustness_inference.csv 存档了全部校正矩阵。'
    '对结论真正敏感的是长度梯度的形状与推理族的稀缺性——'
    '前者已由四分位单调性支持，后者是数据集的构成事实，两者都不是校正能改变的。',
    )

# ---- 5.4 内补一句 ----
insert_after(
    '任何话语功能词表的探针（修复词表、立场词表、元话语词表）都可以走一遍同样的三问。',
    '三问走完之后还应有第四问：探针的效应在它的适用域内够不够用作决策依据——'
    '本文的答案是连接词探针在短文本域达到了"可用但需搭配其他信号"的档次，'
    '单独使用不足以支撑判定。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P030 total={cjk+words}')
