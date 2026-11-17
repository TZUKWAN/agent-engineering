# -*- coding: utf-8 -*-
"""P040 paper_cn.md expand patch."""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P040_affordance_language_and_selection\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def ins(anchor, addition):
    global t
    assert anchor in t, 'MISS: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

ins('图 1 把三条 CI 并排呈现。',
    '\n\n![图1](figures/custom_fig1_verdicts.png)\n\n'
    '![图3](figures/custom_fig3_length_signal.png)\n\n'
    '![图4](figures/custom_fig4_margin_profile.png)')

ins('写作规范的价值最终由检索器的行为裁定。',
    '\n\n用一个真实 query 摆出三问的素材。查询：合并两个 git 分支。'
    '金标描述：合并指定的 git 分支，支持 no-ff 模式与 squash 选项。'
    '可供性动词 3 个、参数名 2 个、实义词 14 个、密度 0.21。'
    '同集另一描述：git 分支合并工具。动词 0、参数 0、'
    '实义词 4、密度 0。金标密度更高、更长。'
    '问题：赢是因为可供性语言还是因为更长？'
    'H1 与 H3 的分工就是拆这两个因素。')

ins('影响结论的外推边界。',
    '\n\n两个通道的分离还有一个工程含义：如果写作规范的排序价值'
    '全部在词面通道，那么换成语义排序器后规范的价值会重估。'
    '这一跨栈检验需要语义排序器的对照，超出本文的'
    '单栈设计——它是写作规范研究下一步的最大缺口。')

ins('合成目录写作的三条数据背书规范：先写够长、密度适中、名称与描述一致。',
    '\n\n三条规范的信息来源不同：长度规范来自本文、'
    '一致性规范来自 P020、密度适中来自本文的 U 型。'
    '排序效应的强弱对应规范执行的优先级——长度是第一优先，'
    '一致性第二，密度第三。')
ins('任何以语言特征为核心的排序优化都应该先过结构与长度这两个更强的控制。',
    '\n\n这一原则的决策树：第一步长度诊断，第二步结构诊断，'
    '第三步才是效应检验。系列的方法论工具正在汇成'
    '一个可复用的检查流程。')

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P040 total={cjk+words}')
