# -*- coding: utf-8 -*-
"""P024 paper_cn.md 扩写补丁（第五轮）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P024_epistemic_behavioural_gap\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 2.4 补充 ----
insert_after(
    '分歧模式的 15.2% 占比说明它是常态现象而非罕见异常——这为"推理与呈现的系统性分歧"提供了流行病学基线。',
    '\n\n与之对照，一致犹豫模式只有 1.4%（1,223 个 turn）。这个不对称本身携带信息：'
    '若两块文本在忠实转译同一认识状态，"推理犹豫"应当把正文也拉入犹豫（语言习惯的一致性），'
    '一致犹豫的出现率至少应与分歧模式同量级；实测只有十分之一。'
    '最经济的解释是两块文本的生成条件不同——推理块在任务语境中生成、'
    '正文在"对用户说什么"的语境中生成，后者的规范压力（自信、简洁、得体）'
    '系统性地抑制犹豫词。分歧不是转译误差，是两套规范的并行输出。',
    )

# ---- 3.2 后补充：判定词 ----
insert_after(
    '这一处理保住了预注册的完整性，同时不浪费意外发现的信息量。',
    '\n\n与 not_testable 族不同（那些是"问题问不了"），outside_the_frozen_rule 记录的是'
    '"问题问成了、答案的方向出乎预料"——它要求后续讨论同时处理两件事：'
    '意外方向的机制解释（本文 5.1/4.2 节的收尾富集假说），'
    '以及原预期句的失效审计（为什么设计者没想到）。两者都进产物，'
    '使判定词表成为设计认知的改进回路而不只是质量标签。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P024 total={cjk+words}')
