# -*- coding: utf-8 -*-
"""P021 paper_cn.md 扩写补丁（第三轮，冲线）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P021_synonym_normalisation_consistency\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 4.1 图1 前补充 ----
insert_after(
    '次证据同向：金标候选的 BM25 秩平均变差 +0.0101 位（95% CI [+0.0025, +0.0182]，p_boot=0.012）。',
    '次证据的存在价值在于排除一种轻巧的开脱——"hit1 差是第一名的门槛噪声，整体排序其实没动"。'
    '秩差证明排序整体也在向坏处移动；门槛事件只是连续位移的可见尖峰。',
    )

# ---- 5.5 补充 ----
insert_after(
    '判定词表里 null / partial / supported / not_testable / opposite 的五分法在本文完成了五分之五的实弹演习（本系列其他包已各见其余四种）。',
    '\n\nopposite 的报告义务还有一个常被忽略的维度：它要求作者对"预测为什么错了"给出机制候选，'
    '并把这个候选写成可反驳的形式。只报告"与预测相反"而不交付反向机制，'
    '是把判定成本转嫁给读者；本文第 5.1 节的合成匹配假说与第 5.2 节的单边漏斗论证，'
    '就是这笔义务的清偿——它们各自的反驳路径都已写明。',
    )

# ---- 数据可用性补充 ----
insert_after(
    '底层数据为 AgentNet 公开发布的 Toucan-1.5M 路由帧 dev 切分，共享特征矩阵经逐行断言与冻结帧一致，零测试切分接触。',
    '配对差的逐查询分布、家族结构的完整清单（25,341 个家族的成员构成）与 bootstrap 抽样的设置参数均随包交付；'
    '任何复核者可以在分钟级重算三个判定词。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P021 total={cjk+words}')
