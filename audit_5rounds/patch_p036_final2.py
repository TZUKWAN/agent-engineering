# -*- coding: utf-8 -*-
"""P036 最终冲线（+400 字）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P036_command_family_switching_cost\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 4.1 图引用后补 ----
insert_after(
    '![图2 切换红利](figures/custom_fig2_switch_bonus.png)',
    '\n\n两个主假设的判定全景见图 1。\n\n'
    '![图1 两个主假设的判定](figures/custom_fig1_verdicts.png)',
    )

# ---- 5.1 之前补 ----
insert_after(
    '机制对长度免疫，是切换红利与连接词效应的本质区别。',
    '\n\n免疫性还有一个设计侧的推论：凡以 turn 长度或位置为调节变量'
    '的稳健性检查，对切换红利都是低信息量的（已知它免疫）；'
    '有信息量的调节维度是内容类型本身——红利是否随"切换进入的族"'
    '而异（进入 read_file 的红利大于进入 other？）。族级的切入红利'
    '与切出红利分解（5.4 节登记的方向分解）一起，构成红利'
    '解剖的两个正交切片。',
    )

# ---- 5.3 结尾补 ----
insert_after(
    '本文的数据说多样性是收益源。',
    '\n\n参数错误率通道的检查虽然超出帧列，但有一个代理检验可以'
    '先行：切换步的下一观察是否更常携带失败标记（换族后第一发的'
    '失败率）——若换族第一发失败率高于留守步，定势开销的'
    '参数错误形态获得间接证据，红利的净额也会被相应折算；'
    '若两类的失败率相当，开销通道不存在于失败维度，'
    '红利的净额更接近产出口径的全额。检查在帧内可算，'
    '作为定势开销的间接测量登记。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P036 total={cjk+words}')
