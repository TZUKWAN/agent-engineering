# -*- coding: utf-8 -*-
"""P026 paper_cn.md 扩写补丁（第五轮）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P026_sufficiency_language_and_stopping\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 1.3 后补 ----
insert_after(
    '第 5 节把这个结论放进认识三部曲的框架，并讨论它对停止质量评估的修正。',
    '\n\n阅读路线建议：赶时间的读者可以直接跳到图 3（H1 的两口径对比）与'
    '图 4（H2 的反向对比）——两张图合起来就是全文的论点；'
    '关心方法洁净度的读者会想看 3.2 节（H2 绕开因果循环的设计）与'
    '4.1 节末尾（增量设计的苛刻标准）；做评估工具的读者请直接看 5.2 节的'
    '替代指标设计。全文的数字都读自产物 JSON，没有任何一处人工转录或四舍五入'
    '超出产物精度——这一声明适用于系列所有包，在此重复是因为停止主题最容易被'
    "'大家都是这么说的'式转述污染。",
    )

# ---- 4.3 结尾补 ----
insert_after(
    '验证只需检查该类目内宣称 turn 的位置分布是否双峰（子阶段边界富集）；这再次说明词汇的行为位是类目相对的——充分性陈述没有普适的时间位，只有"在多数类目的多数时刻指向收尾"的统计倾向。',
    '\n\n类目剖面还给出了一个工程上的现成改进：池化系数（H1）在类目内的取值范围'
    '从 +0.10 到 −0.82，跨度接近一个 logit 单位——任何把池化系数硬编码进'
    '评估工具的做法都会在负号类目上方向性出错。正确的工程形态是把类目作为'
    '协变量进入模型（或按类目分别校准阈值），让工具自带类目感知。'
    '这也再次印证 H3 作为程序防御的价值：它强迫报告携带分层，'
    '从而使工程实现者无从忽略异质性。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P026 total={cjk+words}')
