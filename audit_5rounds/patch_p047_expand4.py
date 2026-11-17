# -*- coding: utf-8 -*-
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P047_verbal_versus_behavioural_correction\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def ins(anchor, addition):
    global t
    assert anchor in t, 'MISS: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

ins('两台仪表在两个方向上的互测误差都是数量级级别的——',
    '\n\n补一个算术量级供校准：按观察级错误份额 57% 估算，'
    '全波错误回合约在八万量级，而承认只有 906 例；'
    '即使 633 例错误前置承认全部命中，承认通道对错误的覆盖率也不足 1%。'
    '反向的假阳率至少 30%（273/906）。两个数字合起来给出了')
ins('语言仪表测模型对自身状态变化的申报，环境仪表测外部世界的语法裁决。',
    '一个用单行就能记住的审计结论：承认通道对错误检测是 1% 召回、30% 假阳的仪表——'
    '任何把这两个数字读反的监控系统都会在错误最密集的地方保持沉默，'
    '而在模型礼貌性道歉时拉响警报。')

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P047 total={cjk+words}')
