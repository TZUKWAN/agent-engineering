# -*- coding: utf-8 -*-
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P052_the_recovery_window_after_a_failed_step\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def ins(anchor, addition):
    global t
    assert anchor in t, 'MISS: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

ins('对照臂只剩 44 条不换者——H2 判 *not_monotone*：三个可估滞后给出 +0.4048（lag1）、-0.6773（lag3，CI 排除零）、-0.3841（lag5）——先正后负，不存在"衰减到零"的剂量结构（lag2、lag4 因样本 35 条与 1 条不可估）。' if False else 'H2 判 *not_monotone*：三个可估滞后给出 +0.4048（lag1）、-0.6773（lag3，CI 排除零）、-0.3841（lag5）——先正后负，不存在"衰减到零"的剂量结构（lag2、lag4 因样本 35 条与 1 条不可估）。',
    '剂量结构的崩塌比优势的缺失更值得记住：'
    '即使未来的数据测出滞后优势，它也几乎不可能是'
    '「每延迟一步固定折价」的线性剂量形态——'
    '因为本帧的中段档位（lag2、lag4）在行为层面是真空，'
    '智能体的响应要么立即、要么根本不发生，'
    '「中间速度」不是未采样，而是不存在。')

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P052 total={cjk+words}')
