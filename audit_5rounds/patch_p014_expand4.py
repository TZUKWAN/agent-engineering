# -*- coding: utf-8 -*-
"""P014 paper_cn.md 扩写补丁（第四轮）。"""
import io

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P014_semantic_prototype_bias\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 结论补充 ----
insert_after(
    '由评估协议支付**。',
    '它同时是系列研究里第一个把偏差定位到评估层而非选择层的证据：'
    '选择层的偏差（P039）可以被更好的推理弥补，评估层的偏差会先于任何推理就污染证据——'
    '这也是把测量前移到评估层的方法论理由。',
    )

# ---- 数据可用性补充 ----
insert_after(
    '底层数据为 AgentNet 公开发布的 Toucan-1.5M 路由帧 dev 切分，零测试切分接触。',
    '中心性的计算只依赖候选列的稠密向量与确定性的余弦函数，无随机成分；'
    'hi 指示的中位切分规则与模型设定在冻结文件中存档，任何复算者在同一数据上会得到逐位一致的结果。',
    )

io.open(P, 'w', encoding='utf-8').write(t)

import re
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P014 total={cjk+words}')
