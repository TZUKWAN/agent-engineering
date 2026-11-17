# -*- coding: utf-8 -*-
"""P014 最终冲线补丁。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P014_semantic_prototype_bias\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

old = '**运行追溯**：EXP-0138（wave-2 设计），seed 42，dev 切分，测试行读取 0，全量墙钟 1,457.9 秒（Python 3.11.7）；所有数字读自 `results_raw/EXP0138_wave2_design_*.json` 与 `tables/`，判定规则冻结于 `protocol_freeze.md`。'
new = '**运行追溯**：EXP-0138（wave-2 设计），seed 42，dev 切分，测试行读取 0 行，全量墙钟 1,457.9 秒（Python 3.11.7，本地编码器、无任何 API 调用）；所有数字读自 `results_raw/EXP0138_wave2_design_*.json` 与 `tables/`，判定规则、支持阈值与 kill gate 冻结于 `protocol_freeze.md`，Holm 族构成见产物 family_note。'
assert old in t
t = t.replace(old, new)

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P014 total={cjk+words}')
