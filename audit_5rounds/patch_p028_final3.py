# -*- coding: utf-8 -*-
"""P028 最终冲线（+250 字）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P028_conclusion_before_evidence\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 4.4 表后补 ----
insert_after(
    'Holm 在 3 假设族内执行；两口径计数与逐格率为随行材料。',
    '\n\n三个判定的证据强度并不均等，值得分级标注：H3 的 supported 建立在'
    'CI 远离零的大样本估计上，是最高等级；H2 的 opposite 建立在'
    '1,078 个结论 turn 的子样本上，方向可信、幅度有 sampling 不确定性；'
    'H1 的 not_testable 不是证据而是程序状态。引用本文时区分这三个等级'
    '（强实证 / 中实证 / 程序状态），比笼统引用三个"结果"更能保护结论的精度。',
    )

# ---- 6 局限最后补 ----
insert_after(
    '其行为学意义与长轨迹中的中途预演完全不同；两口径的描述应补充轨迹长度分布。',
    '第九，正文长度下限未设（与 P024 的 20 字符门槛不同），极短 turn 中的'
    '结论标记（如单独一词"Concluded."）计入样本——低信息 turn 的存在'
    '对 H3 的效应是保守偏置（它们稀释了效应），对 H2 的重叠读数是稀释源之一。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P028 total={cjk+words}')
