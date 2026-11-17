# -*- coding: utf-8 -*-
"""P020 paper_cn.md 扩写补丁（第三轮）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P020_name_description_congruence\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 5.2 补充 ----
insert_after(
    '这与分层证据（长描述层效应最强，且长描述本身在 P016 中受益）合起来指向同一个投入排序。',
    '\n\n换一种成本视角算同一笔账。提升一致性的边际成本几乎为零：把名称里已有的词在描述首句中'
    '复述一次、给缩写一个全称展开，都是分钟级的编辑；相比之下，把一份 16 token 的描述'
    '扩写到长描述层需要实质的内容投入。按每单位编辑投入的回报计，'
    '一致性是元数据清单上回报/成本比最高的项目之一——前提是预期收益按 0.1119 而非 0.1566 记账。'
    '规范推广材料若引用本文，应引用衰减后的数字并注明条件：这是控制了描述质量之后的净回报。',
    )

# ---- 5.5 准则四 ----
insert_after(
    '本设计的操作化以"未被覆盖的唯一词项占比"计量，塞词策略在更好的操作化下反而受损。',
    '\n\n**准则四：把一致性检查做成流水线的静态检查项。**本文的操作化（标识符切分 + 唯一词项覆盖率 + '
    '谓词兑现）是一个可以在提交时机械执行的检查：覆盖率低于阈值时提示作者在描述中解释名称成分、'
    '谓词未兑现时提示补写。检查的全部逻辑来自冻结词表与规则，零模型成本，'
    '且其判定与本文测量的效应直接对应——这是把观测结论转化为工程约束的最短路径。',
    )

# ---- 4.5 判定汇总后补充 ----
insert_after(
    'Holm 在 3 假设族内执行；分层估计与两层 gold-rate 差距为描述性材料。',
    '\n\n族内校正对结论的实际影响可以一句话交代：H1 与 H2 的 p_raw 低于 10⁻⁴³，'
    '任何合理的校正方案下都远在阈值之下；H3 的 p_holm=1.0 是占位约定而非检验结果。'
    '包内 table5_robustness_inference.csv 以矩阵形式存档了这组数字。'
    '对结论真正敏感的是第 4.3 节的空单元格处理——而那是设计纪律问题，不是统计问题。',
    )

# ---- 6 局限第八条 ----
insert_after(
    '其效果的线性外推可能失真。',
    '第八，gold 的构成把智能体推理与检索排序混在同一个结果变量里：一致性对两者的贡献比例'
    '（多少经由检索字段、多少经由智能体对名称信号的直接使用）未被识别，'
    '对机制的完整归因需要能分别观测排序位次与最终选择的中间变量设计。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P020 total={cjk+words}')
