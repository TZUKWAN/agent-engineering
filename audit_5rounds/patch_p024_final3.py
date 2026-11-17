# -*- coding: utf-8 -*-
"""P024 paper_cn.md 扩写补丁（第六轮，冲线）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P024_epistemic_behavioural_gap\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 1.3 预告后补 ----
insert_after(
    '其"犹豫"词汇服务于礼貌与免责，与认识状态脱钩**。',
    '\n\n这一命题的可操作推论立刻可以列出三条，作为后文的预告。其一，行为预测的任务'
    '应当只喂推理块文本——正文词汇在行为预测里是噪声甚至反向信号（H2）。'
    '其二，任何以语言化信心为对象的校准研究必须声明口径——混合口径的信心指标'
    '平均了 0.56 与 −0.92 两个相反的效应，其曲线不可解释。'
    '其三，分歧率本身是新的监测对象——它不该被当作要消灭的误差（两层各有其规范），'
    '而该被当作要理解的现象：什么任务、什么阶段、什么内容上两层最容易各说各话。',
    )

# ---- 4.1 结尾补 ----
insert_after(
    '![图1 一个 turn 的两张脸](figures/custom_fig1_face_patterns.png)',
    '\n\n图 1 的三根柱子还藏着一个次级观察：中间的"其余 turn"（19.34%）略高于 P023 的'
    '情态 turn 总体检验率（19.43%）基本持平——因为这一组以双不犹豫为主体，'
    '是整个数据的行为基线。把三根柱子按"推理块是否有犹豫"重新分组（左柱有、中柱无、右柱无），'
    '检验率 25.28 / 19.34 / 3.45 的排序说明：正文的状态几乎不影响检验率，'
    '推理块的状态才是分组变量——这正是"行为听推理块的"在图上的形状。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P024 total={cjk+words}')
