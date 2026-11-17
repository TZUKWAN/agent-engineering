# -*- coding: utf-8 -*-
"""paper01 深度扩写（第五轮，锚定实际文本）。"""
from pathlib import Path

p = Path("G:/刘俊琦/AGENT ENGINEERING/MATLABINTOKEN/revised/paper01_rewritten.md")
t = p.read_text(encoding="utf-8")

R = [
    ("- **完成率**：Logistic 回归，报告 OR 与 95% Wald CI；",
     "- **任务完成率**：Logistic 回归，报告 OR 与 95% Wald CI。选择 Logistic 而非线性概率模型的原因有二：完成率为二值变量，线性模型会让预测概率越界；OR 的乘数解释便于在不同基线率的子样本间迁移比较；"),
    ("**用户侧**：在指令末尾附加一到两句显式验证要求（“最后请确认文件已存在于目标目录”），成本低而潜在收益明确。",
     "**用户侧**：在指令末尾附加一到两句显式验证要求（“最后请确认文件已存在于目标目录”），成本低而潜在收益明确。需要避免“验证表演”——只写“检查一下”而不给出可核查的判据（文件名、数量、位置），这样的验证动词不携带终止信息，本文的编码规则也会将其归入伪阳性之列。"),
]
miss = []
for o, n in R:
    if o in t:
        t = t.replace(o, n, 1)
    else:
        miss.append(o[:50])
p.write_text(t, encoding="utf-8")
print("applied", len(R) - len(miss), "/", len(R))
for m in miss:
    print("MISS:", m)
