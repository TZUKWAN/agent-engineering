# -*- coding: utf-8 -*-
"""P031 paper_cn.md 扩写补丁（第四轮）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P031_explanatory_coherence_and_evidential_gaps\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 4.1 图1 引用补（放在 H2 小节后、4.3 前） ----
insert_after(
    '![图2 链长与取材的描述性曲线](figures/custom_fig2_chain_length_curve.png)',
    '\n\n两个主假设的判定森林与 H1 的解剖（两格规模、零点估计、紧 CI 与中带线的距离）见图 1 与图 3。\n\n'
    '![图1 两个主假设的判定](figures/custom_fig1_nulls.png)\n\n'
    '![图3 H1 的解剖](figures/custom_fig3_h1_anatomy.png)',
    )

# ---- 4.4 表后补 ----
insert_after(
    'Holm 在 3 假设族内执行；链长描述曲线为随行材料。',
    '\n\nH3 的占位 p_holm=1.0 同系列惯例：分层复核是构造性检查，无单一抽样检验可执行，'
    '以 p=1 占位并在判定词中写明构造（三个四分位、符号保持要求、未通过的事实）。'
    '三个判定合起来在系列判定词表里创下两个首次：第一次以 null 为包的主判定，'
    '第一次使用"复现失败"（not_reproduced）类判定词——空结果与稳健性失败'
    '各得其所，互不冒名。',
    )

# ---- 5.4 后补 ----
insert_after(
    '它是有意寻求空结果的第一个包——担忧驱动的设计（为了排除一个可怕的可能而检验）与发现驱动的设计同等正当。',
    '\n\n担忧驱动设计的方法论特征也值得存档：它的假设方向由担忧决定（负号），'
    '判定的意义在排除而不在确认——这使它的 CI 解读与发现驱动设计相反：'
    '发现驱动设计里 CI 下限是金子（效应存在性的下界），担忧驱动设计里'
    'CI 的"危险侧边界"是金子（H1 的 0.050 说明隐藏效应至多 0.05——'
    '远小于 0.15 的危险线）。读者引用本文时，引用的应当是这条危险侧边界，'
    '而不是那个几乎为零的点估计。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P031 total={cjk+words}')
