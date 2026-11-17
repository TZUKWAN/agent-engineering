# -*- coding: utf-8 -*-
"""P042 add governance section."""
import io

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P042_the_catalogue_ecosystem\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

old = '前者保护。后者治理。'
new = '''前者保护不要合并有特化差异的服务器。后者治理统一命名规范或加强命名空间区分。

治理的具体行动方案可以按照生态结构的三个维度展开。第一是来源维度。鼓励新来源的加入以维持分散度。HHI的监测值为准入门槛。第二是内容维度。审计近同义对以控制诱饵密度。P039的阈值可以直接复用。第三是命名维度。建立局部名的唯一性检查。本文的命名复用率作为合规指标。三个维度的检查全部可以脚本化。扫描器的实现成本与本文的分析脚本同量级。

目录生态的治理不仅是技术问题也是社区治理问题。命名规范的执行需要社区共识。特化度的维持需要激励微服务器提供者。分散度的保护需要防止大服务器垄断。三个维度需要三种不同的治理工具。但它们的共同前提是测量——没有测量就没有治理的基线。本文的贡献正是提供了这个测量的基线。'''

t = t.replace(old, new, 1)
io.open(P, 'w', encoding='utf-8').write(t)
print('done')
