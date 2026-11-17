# -*- coding: utf-8 -*-
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P046_plan_specificity_and_search_quality\paper_cn.md'
t = io.open(P, encoding='utf-8').read()
anchor = '换言之，在最特异的一端，轨迹以更多的错误观察和更不干净的收尾为特征。'
assert anchor in t
add = ('\n\n四分位图还藏着两个值得单独指出的细节。其一，s2 是整条曲线的拐点：'
       '重复份额在此处完成绝大部分下降（11.67%→4.46%），s3 与 s4 几乎不再变化——'
       '这提示特异性的边际收益在极低区间就耗尽了，超过最低限度的枚举不再带来任何聚焦收益，'
       '只有代价继续累积。其二，s4 的错误份额（51.85%）显著低于 s1 至 s3（59.4%-62.4%）'
       '却仍高于朴素预期，且终末干净份额仅从 s3 的 24.95% 回升至 26.78%——'
       '最特异的开篇既没有把错误压下去多少，也没有让收尾干净多少。'
       '把两点合起来，四分位证据给出的不是一条先降后升的 U 型救场曲线，而是一面墙：'
       '特异性没有在任何一段区间上兑现它的承诺。')
t = t.replace(anchor, anchor + add, 1)
io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print('P046 total =', cjk + words)
