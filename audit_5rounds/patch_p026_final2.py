# -*- coding: utf-8 -*-
"""P026 paper_cn.md 扩写补丁（第六轮，冲线）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P026_sufficiency_language_and_stopping\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 5.3 后补一段 ----
insert_after(
    '这一对比可以校验剧本的完备性，登记为后续。',
    '\n\n剧本还有一个反向的应用价值：既然充分性宣言标记优质收官，'
    '那么它的**缺席**（取证已经很多却迟迟不说"够了"）就标记另一类异常——'
    '取证已足而不敢收束的过度搜寻。过度搜寻在成本上表现为冗余调用，'
    '在质量上可能表现为过度迟疑（把已经一致的证据反复核对）。'
    '把"取证分位数高 + 无收尾陈述 + 轨迹仍在继续"定义为一个监测单元格，'
    '就得到了与"疑似过早终止"对称的"疑似过度搜寻"探测器——'
    '两个探测器合起来，才是停止质量的完整监控面。'
    '这是 H2 的反向（opposite）结果送给评估的第二件礼物：'
    '它不仅纠正了一个误报源，还顺手点亮了盲区里的另一类错误。',
    )

# ---- 6 局限后、7 结论前不加；直接在 7 结论第一段后补 ----
insert_after(
    '且宣称后的停止带着更多的先验收证（2.57 对 1.72 次；H2，opposite，β=1.7059）——语言化的"够了"是充分取证的收官宣言，不是仓促放弃的托词。',
    '两个判定合起来的推理强度值得向读者摊开：H1 的 null 排除了"语言推动停止"的因果读法，'
    'H2 的 opposite 排除了"语言伴随低质量停止"的质量读法——'
    '剩下的唯一一致解释就是报道论：语言与停止同源于证据状态，'
    '而说出这句话的停止恰是取证更充分的停止。'
    '两条排除法各挡住一侧，中间的解释便无处可逃——'
    '这是判定组合（null + opposite）比任何单一显著结果都更有力的原因。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P026 total={cjk+words}')
