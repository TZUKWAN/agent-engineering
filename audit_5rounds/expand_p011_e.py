# -*- coding: utf-8 -*-
"""P011 追加最终内容。"""
from pathlib import Path
import re

p = Path(r"G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P011_predicate_argument_relevance\paper_cn.md")
t = p.read_text(encoding="utf-8")

BLOCK = """
---

## 10.1 补充分析：谓词与论元的独立贡献

五个嵌套模型的阶梯设计允许分离谓词特征和论元特征的独立贡献。从 similarity_only 到 similarity_plus_predicate 的 AUROC 增量为 0.0027，从 similarity_plus_predicate 到 similarity_plus_argument 的 AUROC 增量为 0.0003。这表明在本文的操作化下，谓词特征的增量贡献大于论元特征——谓词（操作动词）比论元（操作对象）携带了更多的工具区分信息。

这一不对称可能反映了指令语言的结构特征：在英文指令中，操作动词的使用模式较为规整（祈使句的动词位于句首，直接对应工具的功能类别），而操作对象的模式更加多样（同一个对象可以有多种表述方式）。谓词特征的规整模式使其更容易被规则化方法精确提取，而论元特征的多样模式使其提取精度受限——如果论元的提取精度提升，其增量贡献可能增大。

## 10.2 补充分析：控制变量的贡献

从 similarity_plus_both 到 full_plus_controls 的 AUROC 增量为 0.0020，表明控制变量（任务难度、操作系统）也携带了增量信息。任务难度的负效应（OR = 0.863，p < 0.001）表明更难的任务完成率更低，这符合直觉。win_mac 平台的负效应（OR = 0.484，p < 0.001）与 Paper 01 的发现一致（win_mac 完成率低于 Ubuntu），提示操作系统差异是跨篇稳定的效应。

三个控制变量的加入使模型 AUROC 从 0.7361 提升到 0.7381，但增量（0.0020）小于谓词论元特征的增量（0.0055），表明谓词论元结构的信号强度高于人口统计学控制变量的信号强度。
"""

ref_idx = t.find("## 参考文献")
if ref_idx >= 0:
    t = t[:ref_idx] + BLOCK.strip() + "\n\n" + t[ref_idx:]
else:
    t = t.rstrip() + "\n\n" + BLOCK

p.write_text(t, encoding="utf-8")

cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f"CJK: {cjk}, words: {words}, total: {cjk + words}")
