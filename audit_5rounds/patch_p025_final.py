# -*- coding: utf-8 -*-
"""P025 paper_cn.md 扩写补丁（第四轮）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P025_contradiction_and_modality\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 2.2 后补 ----
insert_after(
    '它使本文不需要在数据到达后重新解释为什么负号也算数。',
    '\n\n对方向自由条款的一个常见误读需要排除：它不是"事后什么方向都能说成支持"。'
    'direction_free 只豁免方向的承诺，不豁免幅度的承诺——CI 必须排除零；'
    '也不豁免特异性的内容——H2 检验的仍是"矛盾与不同工具信息的差"，'
    '而不是任何随意的对比。自由的是预言方向的特权，不自由的是证据的标准。'
    '这一区分写进冻结文件，是预注册纪律对机制探索型假设的适配。',
    )

# ---- 4.5 表后补 ----
insert_after(
    'Holm 在 3 假设族内执行；描述性状态率与分层为随行材料。',
    '\n\n族内校正的敏感度照例可一句带过：H1 与 H2 的 p_raw（0.0057、0.0002）在三重校正后'
    '（0.0114、0.0006）仍稳稳过线；H3 本就不显著。'
    '组合的读法再次强调：opposite / supported / null 的三色不是三个孤立判定，'
    '它们共同描述一个"矛盾被特殊而安静地处理"的过程——特殊（H2）、安静（H1）、'
    '且安静不等于没有语言反应（充分性翻倍的描述证据，尽管条件化后未达显著）。',
    )

# ---- 5.2 结尾补 ----
insert_after(
    '现有帧可直接计算，登记为后续。',
    '\n\n若复盘假设为真（行动完成后情态回升），监测实践还需加一条时间窗规则：'
    '事件后扫描情态词不是永远错误，而是要等行动完成——矛盾后第一个 turn 的低情态'
    '是行动占用的信号，第三、四个 turn 的情态回升才是复盘的信号。'
    '情态指标的时间窗应当从"事件后一步"改为"事件后行动完成时"——'
    '这是把时序模型转化为监测参数的一个具体建议。',
    )

# ---- 6 局限补充 + 结论前 ----
insert_after(
    '其影响方向是稀释两极对比、使 H3 的 null 更保守。',
    '第十一，本文的三臂（Kimi-K2/OSS/Qwen3 合并分析）未做模型间对比——'
    '"行动优先"的时序模型若为架构普遍性质，应跨模型稳定；若为某一家族的生成风格，'
    '系数应有家族签名。分臂估计在现有帧上可直接计算，登记为后续而非本文结论。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P025 total={cjk+words}')
