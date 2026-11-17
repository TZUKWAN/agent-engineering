# -*- coding: utf-8 -*-
"""P037 paper_cn.md 扩写补丁（第三轮）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P037_first_action_path_dependence\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 4.1 图1 引用后补 ----
insert_after(
    '![图1 开局的压倒性共识](figures/custom_fig1_first_family_shares.png)',
    '\n\n开机动作的单折性还有一个跨实例的稳定性佐证：1,784 个实例中，'
    '模态首家族为 search_name 的占绝大多数（首家族份额表见产物），'
    'list 开局集中在少数实例——离模不是均匀分布在所有实例里的'
    '随机噪声，而是特定实例的局部现象。这一分布使 H1 的离模对比'
    '自然地聚焦在"少数实例的少数 rollout"上，功效的先天约束'
    '正是从这里来的。',
    )

# ---- 4.4 补充 ----
insert_after(
    '锁定机制假说无着落（图 3 下行）。',
    '\n\nH3 还有一个设计侧的注记：is_search_first 的变量在全部步上'
    '常数化于 search_name 主导的 rollout 子集（其分层的'
    'search_name 层因常数而不可估），可估对比实际上只来自'
    'list 开局的 rollout——H3 的全步估计因此主要是'
    '"search_name 开局 vs list 开局"的对比。这一口径限制'
    '与 H1 相同：两个 null 都是"在既有离模材料上未检出"，'
    '不是"任何开局的锁定都不存在"的全称否定。',
    )

# ---- 5.1 结尾补 ----
insert_after(
    '该推论需要上下文操纵实验，超出观测设计，登记为架构侧的后续。',
    '\n\n操纵实验的形态可以具体化：在 rollout 的中段把指令文本从'
    '上下文移除（或替换为中性占位），观察后续动作是否开始'
    '依赖开局路径——若移除指令后家族混合出现开局分化，'
    '路径依赖的存在条件即被定位为"指令在场"。'
    '这是把本文的零结果转化为积极发现（锚的存在性证明）的'
    '标准路径：零结果的机制解释总是可以设计一个'
    '让零变非零的操纵来验证。',
    )

# ---- 6 局限前补 ----
insert_after(
    '为预算干预（提前澄清、转移资源）争取时间。',
    '\n\n回到本文的三个判定，把它们的联合含义再压缩一层：'
    'H1（开局不影响形状）与 H2（留守预示失败）合起来给出了'
    '一个不对称的行为学：**开局不塑造行为，行为塑造结局**——'
    '第一动作是可替换的变量，动作的持续模式才是有后果的变量。'
    '这一不对称对"起点重要性"的直觉是一个直接的矫正：'
    '在任务锚定的生成系统里，起点是廉价的，路径是昂贵的。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P037 total={cjk+words}')
