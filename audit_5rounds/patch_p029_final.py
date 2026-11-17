# -*- coding: utf-8 -*-
"""P029 paper_cn.md 扩写补丁（第四轮，冲线）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P029_discourse_repair_after_failure\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 2.3 结尾补 ----
insert_after(
    'H3 的读数应理解为"控制线性位置后"的负效应，其稳健性在第 6 节局限中挂钩。',
    '\n\n正向预期的来源也值得复盘一次，因为它暴露了冻结直觉的一个系统性风险：'
    '"放弃→终止"的预测不是从数据先验来的，是从词面语义来的——'
    '设计者看到 abandon 就写了终止。P021 的同义词反向、P025 的矛盾反向、'
    '本文的放弃反向，三次 opposite 的共同点是：预测都来自词面语义的直觉'
    '而非话语功能的分析。话语词是语用生态的产物，词面只是它的化石——'
    '三次反向反复证明：化石不能当活体解剖。后续包的冻结方向若仍从词面来，'
    '应当在预注册里附带"方向的反面也构成可报告结果"的预案——'
    '这已经在系列的部分设计中实现（direction_free 条款）。',
    )

# ---- 4.5 表后补 ----
insert_after(
    'Holm 在 3 假设族内执行；类目分层与触发率剖面为描述性材料。',
    '\n\n校正的敏感度照例轻微：三个 p_raw 都在 10⁻³ 以下，三重校正不改变判定。'
    '组合的读法再一次落在 H3 上：两个 supported 保住了修复话语的"正面剧目"'
    '（诊断回应失败、重试兑现行动），opposite 揭示了"反面角色"（放弃语言）'
    '根本没有登台——它在剧目单上写着终止，实际上演的是继续。'
    '判定词表对这类"剧目不符"的命名能力（opposite）是预注册体系对'
    '语义直觉最系统的纠错机制。',
    )

# ---- 7 结论前补一段 ----
insert_after(
    '这是修复话语研究从词表统计走向语用解剖的下一步。',
    '\n\n对监测系统的落地方案，本文可以直接给出一个两级配置。一级（高精度）：'
    '重试语言监测——命中即预告行动（H2），用于资源预分配与进度预测，'
    '其误报风险低（H2 的 CI 下限 0.72 对应比值比 2.06）。'
    '二级（需重设计）：放弃语言监测——关键词命中不构成弃任务证据（H3），'
    '应替换为"重试语言消失率"或"终止前取证不足"的行为指标（P026 框架）。'
    '两级配置的成本都只是词表与规则，部署的瓶颈在于把本文的方向性结论'
    '翻译进监测系统的默认参数——这恰是论文与工程之间的最后一公里。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P029 total={cjk+words}')
