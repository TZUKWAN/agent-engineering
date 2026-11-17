# -*- coding: utf-8 -*-
"""P024 paper_cn.md 扩写补丁（第四轮）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P024_epistemic_behavioural_gap\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 摘要后导读 ----
insert_after(
    '对安全性审计，它提供了一个免标注的线索：推理与呈现的系统性分歧本身就是可审计的信号。',
    '\n\n先为读者立起四个格子的全景。87,395 个合格 turn 中，绝大多数（约八成）是双不犹豫——'
    '推理块与正文都不含情态词；15.2% 是本文的主角（推理犹豫/正文自信）；'
    '3.6% 是反面主角（正文犹豫/推理自信）；只有 1.4% 是两处一致犹豫。'
    '一致犹豫如此稀少这件事本身就值得停下来想一下：如果推理块与正文在忠实转译，'
    '两种犹豫应当同步出现——1.4% 的同步率说明它们几乎各说各话。'
    '四个格子的行为读数（第 4 节）将把这个观察变成结论。',
    )

# ---- 4.5 表后 ----
insert_after(
    'Holm 在 3 假设族内执行；描述性率为随行材料。',
    '\n\n族内校正的实际影响照例轻微：三个 p_raw 都在 10⁻³ 以下，校正不翻转任何判定。'
    '本文判定组合的看点在 H2 的判定词：supported / outside_the_frozen_rule_negative_contrast / supported'
    '——两条 supported 夹着一个超出冻结预期的负对比，'
    '这一组合在系列 63 包中首次出现，其可读性依赖判定词表对"意外"的命名能力。',
    )

# ---- 5.1 结尾补充 ----
insert_after(
    '正文说"格式问题均已处理"时，模型的呈现层可能真诚地认为"处理"（进行了转换）与推理层担心的"覆盖不了全部行"并不冲突——粒度不同，断言不冲突，风险只在遗漏。',
    '\n\n这一粒度差异的澄清对审计实践有直接约束：分歧模式是"需要人工看一眼"的标记，'
    '不是"模型在欺骗"的判定。15.2% 的基线率若被当作欺骗率解读，'
    '警报会在第一天就把审计团队淹没；当作"两层文本的断言粒度不一致"的标记，'
    '它指出的恰是那些值得核对遗漏风险的输出。信号的价值取决于读信号的手册——'
    '本文的第 5.4 节就是那份手册的草稿。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P024 total={cjk+words}')
