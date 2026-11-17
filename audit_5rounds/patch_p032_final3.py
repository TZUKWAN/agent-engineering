# -*- coding: utf-8 -*-
"""P032 最终冲线（+100 字）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P032_plan_action_alignment\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 3.1 末尾补 ----
insert_after(
    '全量墙钟 148.7 秒。',
    '148.7 秒里还包括 100 次置换的全部抽样与逐 turn 差值的聚合——'
    '底噪检查的全部算力代价不过如此，任何以成本为由跳过它的设计都站不住。',
    )

# ---- 4.5 表后补 ----
insert_after(
    'Holm 在 3 假设族内执行；对齐分布与族内剖面为描述性材料。',
    '本包的判定组合（null / opposite / not_testable）与 P021、P027 的组合'
    '同属非支持侧密集型——三个包恰好横跨词表、置换与分层三种测量技术，'
    '非支持判定的反复出现是方法多样的副产品而非质量缺陷。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P032 total={cjk+words}')
