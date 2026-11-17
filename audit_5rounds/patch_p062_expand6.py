# -*- coding: utf-8 -*-
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P062_discourse_structure_of_successful_and_failed_searches\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def ins(anchor, addition):
    global t
    assert anchor in t, 'MISS: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

ins('这是话语分析从描述科学走向工程查表的路径，',
    '\n\n查表化的最后一格是阈值的工程校准：'
    '话语词表的匹配阈值（出现几次算"提到"）在本文取一次出现，'
    '这是最宽松的读法；'
    '收严到两次出现会同时降低两臂的出现率，'
    '但落差的绝对值可能扩大（偶然一提在两臂 equally 常见，'
    '反复提及才是成功型的习惯）。'
    '阈值-落差曲线是词表工程的标定工具，'
    '它把"算不算提到"从语义判断变成可扫描的参数——'
    '本文冻结在单次出现，'
    '把曲线的完整测绘留给后续')
ins('本文提供了三格中的两格。',
    '——那是把八分类从清单变成仪表的最后一公里。')

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P062 total={cjk+words}')
