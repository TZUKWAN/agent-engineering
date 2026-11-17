# -*- coding: utf-8 -*-
"""P029 最终冲线（+250 字）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P029_discourse_repair_after_failure\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 3.1 末尾补 ----
insert_after(
    '全量墙钟 96.2 秒。',
    '\n\n三族修复词表的触发基率本身构成一个话语生态的快照：reissue 词表以 54%–73% 的'
    '触发率高居首位——智能体的失败后话语里过半充满重试措辞，行动导向是绝对主流；'
    'diagnose（约 2%）与 abandon（2%–6%）都是低频事件。这个快照对模型行为'
    '的一般印象是一个有用的修正：失败后的智能体话不多、更不恋战，'
    '它的默认姿态是换法再干——话语研究的显微镜下，"喋喋不休解释失败"'
    '的刻板印象并没有数据支持。',
    )

# ---- 7 结论第一段后补 ----
insert_after(
    '**修辞性的"放弃"说的是情绪，不是决定**。',
    '描述层的触发率剖面（图 2）给这个结论补上了空间维度：放弃语言的两个高发区'
    '——无失败 turn 的 5.57%——指向任务转换与难度评估的话语位，'
    '远离失败-终止的行为链条。一词一词地看，"放弃"语言的行为学身份'
    '更接近过渡标记而非决定宣告；把过渡标记当决定宣告来报警，'
    '是语义直觉在监测系统里最典型的翻车方式。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P029 total={cjk+words}')
