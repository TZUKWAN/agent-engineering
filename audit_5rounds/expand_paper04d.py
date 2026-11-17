# -*- coding: utf-8 -*-
"""paper04 深度扩写（第四轮：新增小节）。"""
from pathlib import Path

p = Path("G:/刘俊琦/AGENT ENGINEERING/MATLABINTOKEN/paper04_reasoning_typology/manuscript.md")
t = p.read_text(encoding="utf-8")

R = [
    ("### 3.3 类型识别方法",
     """### 3.3 特征处理与建模选择

10 项特征量纲不一（计数、比例、对齐度），聚类前统一做 z 标准化；计数类特征先行 log1p 变换以压缩长尾——推理词数与提及次数在高产任务中可达数十倍于中位数，不压缩会使距离度量被少数极端任务支配。

聚类算法选择 K-Means 而非潜类别分析（LCA），依据有三：其一，特征以连续计数为主，K-Means 的欧氏距离目标与“画像差异”的研究问题直接对应；其二，K-Means 的类中心可以逐特征读出，类型命名与画像表一一对应，可解释性最强；其三，K-Means 对本规模数据（两万级）计算稳定、随机种子固定后完全可复现。作为稳健性参考，本研究同时报告了 k = 3 与 k = 5 的画像，核心类型的相对高低在这两个邻域解下保持一致；k 的最终选择在统计准则（轮廓系数、BIC）与可命名性之间取平衡。

### 3.4 类型识别方法"""),
]
miss = []
for o, n in R:
    if o in t:
        t = t.replace(o, n, 1)
    else:
        miss.append(o[:60])
p.write_text(t, encoding="utf-8")
print("applied", len(R) - len(miss), "/", len(R))
for m in miss:
    print("MISS:", m)
