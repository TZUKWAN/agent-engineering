# -*- coding: utf-8 -*-
"""P037 最终冲线（+1,800 字）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P037_first_action_path_dependence\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 4.1 图引用后补 ----
insert_after(
    '![图1 开局的压倒性共识](figures/custom_fig1_first_family_shares.png)',
    '\n\n开局共识还有一个序列层的佐证：首步的 search_name 之后，'
    '第二步最常见的动作是 read_file（消费搜索的命中）或继续 '
    'search_name（换词重搜）——开局之后的动作分布（图 2 的'
    'search_name 行）显示后续并未锁死在搜索族内：读取与'
    '内容搜索合计占了后继行为的一半。开局是一次的，'
    '而它的后继是多样的——这句话就是 H1 的图版本。',
    )

# ---- 5.1 之前补（4.5 表后） ----
insert_after(
    'Holm 在 3 假设族内执行；开局分布、家族混合与集中度对照为描述性材料。',
    '\n\n校正的敏感度：H2 的 p_raw 接近零、校正后判定不变；'
    'H1/H3 的 p_raw 本就高于 0.38，校正无实质变化。'
    '包内 table5_robustness_inference.csv 存档校正矩阵。'
    '三个判定的组合（null / opposite / null）在系列的判定词分布里'
    '是第四次"全非支持"型组合——非支持侧判定的持续出现，'
    '配合每一次的机制层讨论，构成这套管线最有辨识度的指纹。',
    )

# ---- 5.4 结尾补 ----
insert_after(
    '留守的代价（失败几率的变化幅度）大到 −0.95 的 logit，是系列行为效应里的第三强。处方与代价都有了数字，多样性建议第一次有了完整的成本收益表。',
    '\n\n成本收益表还有一行"反向条目"：留守的代价虽然大，'
    '但留守率本身的分布（22%–24%）说明留守是普遍行为——'
    '若留守纯属有害，自然选择式的评测早应淘汰它。'
    '更细看，留守的短阶段（首步后立即同族）可能是健康的'
    '（开局动作通常需要二次确认），只有长阶段的留守'
    '（中段仍大面积同族）才是病理。留守率的健康/病理分界'
    '是预警指标校准的核心参数——P029 的"重试语言消失率"'
    '与本文的"中段留守率"是同一监控思想的两个探针。',
    )

# ---- 6 局限再补 ----
insert_after(
    '序列层面的形状（家族切换的节律）是否也被任务接管，需要序列核方法的检验。',
    '第十一，两行家族混合的几乎重合还有一个备择解释未被排除：'
    '后继行为由任务与预算共同决定，而预算对所有 rollout 相同——'
    '重合可能部分来自预算的均一化而非任务的接管。'
    '区分两者的检验是把混合对比限定在预算充裕的提交'
    'rollout 子集内——若子集内两行仍然重合，任务接管'
    '的解释更干净。登记为后续。',
    )

# ---- 7 结论最后补 ----
insert_after(
    '锚在，依赖不在。',
    '\n\n为系列的方法论记一笔收尾：本文的 H1/H3 双 null 与 H2 的'
    '强 opposite 构成的组合，与 P031（三重 null）、P032（null + opposite）'
    '同属"否定与意外"家族——wave-5/wave-6 的十二个包里，'
    '这一家族占了五席。它们的共同贡献是给"智能体行为学"'
    '划清了直觉失效的边界：连贯遮罩不在、计划指向不在、'
    '递减收束不在、开局锁定不在——而换挡红利、丰收正反馈、'
    '留守代价在。正反两份清单合起来，才是这门新学科的第一版教科书。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P037 total={cjk+words}')
