# -*- coding: utf-8 -*-
"""重建 P012 paper_cn.md 的章节顺序：
- 把误排在"6 结论"之后的 5.6-5.12 移回第 5 节内并重新编号；
- 合并重复的效应方向小节（旧 5.9 并入 5.10 的三小节结构）；
- 清理重复的 --- 分隔线；
- 结论保持为最后一节。
"""
import io
import re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P012_entity_action_constraint_fit\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

# 按标题切分主体
head_end = t.index('## 6 结论')
body = t[:head_end].rstrip().rstrip('-').rstrip()  # 去掉尾部分隔线
tail = t[head_end:]

def grab(section_title, next_title):
    """从原文提取 [section_title, next_title) 之间的内容（不含标题行本身）。"""
    i = t.index(section_title)
    j = t.index(next_title)
    return t[i + len(section_title):j].strip()

# 提取误排段落的内容（跳过标题行，取正文）
s56 = grab('## 5.6 三个维度的操作化细节', '## 5.7 嵌套模型阶梯的设计逻辑')
s57 = grab('## 5.7 嵌套模型阶梯的设计逻辑', '## 5.8 增量预测力的排序与特征信息量的关系')
s58 = grab('## 5.8 增量预测力的排序与特征信息量的关系', '## 5.9 效应方向的异质性')
# 旧 5.9 与 5.10 重复——只取 5.10 的三小节结构（保留其小节标题）
s510 = grab('## 5.10 三个一致度成分的效应方向解读', '## 5.11 三维分解的方法论价值')
s511 = grab('## 5.11 三维分解的方法论价值', '## 5.12 实践启示')
s512 = grab('## 5.12 实践启示', '## 6 结论')

# 结论部分保持原样
conclusion = tail.strip()

# 新的第 5 节增补内容（新写的实质段落）
s56_extra = (

    "\n\n词表冻结的意义值得对读者明说。三个词表合计约 110 个词项，全部在读取结果数据之前写定；"
    "若允许事后增删，研究者总可以（通常是无意识地）朝着放大显著性的方向调整词表——删掉一个所谓稀释信号的动词、"
    "补进一个所谓增强信号的名词。冻结切断了这条路径：任何词表改动在审计层都表现为对冻结文件的偏离，需要单独声明与辩护。"
    "这也是三个一致度特征可以完全复算的前提：给定词表版本号与正则规则，任何人对同一行数据算出的特征值必然相同。"
)

new_body = body + "\n\n"

new_body += "### 5.6 三个维度的操作化细节\n\n" + s56 + s56_extra + "\n\n"
new_body += "### 5.7 嵌套模型阶梯的设计逻辑\n\n" + s57 + "\n\n"
new_body += "### 5.8 增量预测力的排序与特征信息量的关系\n\n" + s58 + "\n\n"
new_body += "### 5.9 三个一致度成分的效应方向解读\n\n" + s510 + "\n\n"
new_body += "### 5.10 三维分解的方法论价值\n\n" + s511 + "\n\n"
new_body += "### 5.11 实践启示\n\n" + s512 + "\n\n"

full = new_body + "---\n\n" + conclusion + "\n"

# 清理重复分隔线与多余空行
full = re.sub(r'\n{3,}', '\n\n', full)
full = re.sub(r'(\n---\n)\n*(---\n)+', r'\1', full)

io.open(P, 'w', encoding='utf-8').write(full)

# 复核
t2 = io.open(P, encoding='utf-8').read()
import sys
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t2))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t2))
order = re.findall(r'^#{2,3} .+$', t2, re.M)
print(f"total={cjk+words}")
print("section order tail:", order[-14:])
