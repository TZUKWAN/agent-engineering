# -*- coding: utf-8 -*-
"""P012 追加最终内容第四轮。"""
from pathlib import Path
import re

p = Path(r"G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P012_entity_action_constraint_fit\paper_cn.md")
t = p.read_text(encoding="utf-8")

BLOCK = """
---

## 5.15 一致度特征与文本相似性的关系

三个一致度特征与文本相似性（BM25 和稠密嵌入 z 分数）的共线性诊断显示 VIF 均低于 1.1，表明三个一致度特征与文本相似性在统计上充分正交。这意味着一致度特征捕捉的不是"更多相似性"而是"不同类型的匹配信息"——它们与文本相似性互补而非冗余。

这一正交性的实践含义是：在工具选择预测器中同时使用文本相似性和一致度特征是安全的（无共线性风险），且两者提供了互补的信号。文本相似性捕捉的是"指令与工具描述在词汇和语义上有多接近"，一致度特征捕捉的是"指令的语义成分与工具的功能范围在结构上有多匹配"。两类信号的互补性是三维分解优于统一指标的根本原因。

---

## 5.16 结果的稳健性

本文的结果在以下方面具有稳健性。第一，嵌套模型阶梯的单调递增——每加入一个新的一致度特征，AUROC 都有所提升，表明三个成分的信号不是噪声。第二，Kill gate 检验通过——三个成分的 VIF 均低于 1.1，排除共线性驱动的假阳性。第三，Holm 校正后全部 p_holm < 0.001，排除多重比较的假阳性。第四，成分效应的方向异质性（约束为负、动作为正）进一步支持了分解方法的价值——如果三个成分只是同一构念的三个测量，它们的效应方向应该一致。

本文的结果在以下方面存在不确定性。第一，约束一致度的负系数的理论含义尚不明确——需要更精细的标注来区分"约束匹配度"与"约束词词汇重叠"。第二，三维分解是否穷尽了指令—工具匹配的所有语义维度——可能还存在其他维度（如时间一致性、空间一致性）未被本文的框架覆盖。

---

## 7 结论

本文将任务型智能体的指令—工具匹配分解为实体一致性、动作一致性和约束一致性三个语义维度，通过嵌套模型阶梯系统检验了各维度的增量预测力。三个维度均对工具选择具有统计显著的增量预测力（全部 p_holm < 0.001），但效应方向不完全一致——动作一致为正，实体一致和约束一致为负。

三维分解的发现对系列研究的框架有一个精化贡献：指令语用学的影响不仅发生在全局特征层面（Paper 01/02）和深层语义结构层面（本文的谓词论元分析），还发生在语义子维度的一致度层面。三个维度的效应方向异质性表明：将指令—工具匹配视为单维构念的简化做法掩盖了关键的语义维度差异。

对实践而言，本文的发现支持在智能体的工具选择模块中纳入多维匹配特征，而非依赖单一的文本相似度分数。三个语义维度的增量排序——约束一致度 > 实体一致度 > 动作一致度——为特征工程提供了优先级排序。未来研究应以更精细的语义标注方法提升三个一致度特征的操作化精度，并在多智能体平台上检验维度效应排序的跨域稳定性。

---

## 参考文献

1. Austin, J. L. (1962). *How to Do Things with Words*. Oxford University Press.
2. Clark, H. H. (1996). *Using Language*. Cambridge University Press.
3. Grice, H. P. (1975). Logic and conversation. In *Speech Acts* (pp. 41–58). Brill.
4. Sweller, J. (1988). Cognitive load during problem solving. *Cognitive Science*, *12*(2), 257–285.
5. Wang, X., et al. (2025). OpenCUA: Open foundations for computer-use agents. *arXiv:2508.14870*.
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
