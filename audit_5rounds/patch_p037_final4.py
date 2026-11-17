# -*- coding: utf-8 -*-
"""P037 最终冲线（+700 字）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P037_first_action_path_dependence\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 1.1 结尾补 ----
insert_after(
    '全数据共有约 220 组这样的组内对比（450 条离模 rollout 分布在数百个实例上）。',
    '\n\n220 组对比里还有两组特别值得点名，因为它们的离模程度最深：'
    'read_file 开局与 run_python 开局的 rollout——它们没有走先搜后取的常规路径，直接从读取或脚本执行切入。'
    '这些极端离模样本的行为混合是最锋利的检验材料：'
    '若路径依赖存在，它们的后继应当与主流 rollout 差异最大；'
    '若任务接管，它们的后继应当仍向任务的标准形状收敛。'
    '样本量的限制使它们的单独比较只能停留在描述层，'
    '但描述层的方向与 H1 的统计结论一致——'
    '极端开局也没有把轨迹带偏。',
    )

# ---- 2.3 之前补 ----
insert_after(
    '留守不是坚持的美德，是无计可施的表情。',
    '\n\n把留守的两种身份与本文的开局框架合并，可以得到一个'
    '双轴的行为分类：横轴是开局（search_name 主流 vs list 等离模），'
    '纵轴是后续模式（多样化推进 vs 开局留守）。'
    '四格里，主流开局 + 多样化推进占绝对多数（约八成的 rollout）；'
    '主流开局 + 留守是失败预警的常客；离模开局 + 多样化推进'
    '（本文 H1 的主角）与主流开局行为无异；离模开局 + 留守'
    '则是最孤立的角落。四格的行为学差异就是 H1（横轴）与'
    'H2（纵轴）要检验的内容。',
    )

# ---- 4.4 图4 引用后补 ----
insert_after(
    '留守的总量与开局类型无关，其后果（跑满）也与开局类型无关：它是行为模式的属性，不是开局的属性。',
    '\n\n这一"属性 vs 开局"的分离还有一个深化版本：把留守率与'
    '家族混合（图 2 的六族占比）放进同一个分析，留守率高的'
    'rollout 的混合是否更窄（集中度高）且更偏开局族？'
    '本文的集中度变量（family_concentration）正是这个混合宽度的'
    '度量，H1 的 null 说明它的均值不随开局变化，'
    '但它的分布（集中度的高分位与低分位 rollout 的结局差）'
    '是 H2 的连续版——两个变量一个测宽度、一个测后果，'
    '联合分析是自然的深化方向。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P037 total={cjk+words}')
