# -*- coding: utf-8 -*-
"""P022 paper_cn.md 扩写补丁（第三轮）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P022_discriminability_and_discoverability\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 1.3 后补充 ----
insert_after(
    '这一结构对元数据评估的含义在第 5 节展开。',
    '\n\n先立一个阅读路标：下文的四个结果（H1、H2、H3、E06）必须作为一个整体来读。'
    '单看 H1，读者会把判别性归档为"又一个无效的质量指标"；单看 H3，'
    '读者会把"在拥挤处有效"读成对无效指标的辩护。两者合起来才是本文的命题：'
    '判别性是一个真实的、有条件的检索资源——它的条件恰好落在元数据评估'
    '过去从不区分的地方。E06 再加上第三条边：即便是同一构念，'
    '仪器的选择也会改变它的可见性。四个结果共同支持的是评估体系的重构，'
    '而不是某个分数的升降。',
    )

# ---- 4.1 结尾补充 ----
insert_after(
    '![图1 三个预注册假设的判定](figures/custom_fig1_verdicts.png)',
    '\n\nnull 的一个替代解释需要先行排除：判别性可能与可达性存在非线性关系'
    '（中段有益、两端有害相互抵消）或被冻结控制集过度吸收。对前者，'
    '本文未预注册非线性项，无法检验，列入局限；对后者，'
    'H2 的阶梯在无控制与有控制两种口径下都接近零增量（产物 ladder 行），'
    '"控制吸收"不是 null 的主要来源。',
    )

# ---- 5.5 准则四 ----
insert_after(
    '本文的全部证据表明它的无条件均值没有意义。',
    '\n\n**准则四：写作训练中区分两类词汇预算。**给目录写手的可操作建议是把描述的词项'
    '分成"入场词汇"（查询可能使用的功能词，必须写清楚）与"区分词汇"'
    '（自家工具独有的参数名、边界、错误语义，在拥挤场景下决定排名）。'
    '两类预算不竞争：入场词汇是必答题，区分词汇是拥挤场景的加分题——'
    '把它们写在同一段描述的不同位置（前者在前、后者在后）还有助于两类通道各自的匹配。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P022 total={cjk+words}')
