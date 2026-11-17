# -*- coding: utf-8 -*-
"""P022 paper_cn.md 扩写补丁（第六轮，最终冲线 +300 字以上）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P022_discriminability_and_discoverability\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 5.3 结尾补充 ----
insert_after(
    '分离设计是现成的：以残差化构造三个正交成分分别入模——这可以列为下一个包的预注册内容，而非本文的事后尝试。',
    '\n\n值得强调的是这一分歧对质量评估实践的即时含义：在分离完成之前，'
    '稠密判别性不宜直接进入质量仪表盘——它的正系数有适配混淆的嫌疑，'
    '基于它的排名可能奖励"语义上离群"而非"区分得好"的描述；'
    '词面判别性虽无效但无害，作为诊断列（不作为分数）保留是当前的稳妥选择。'
    '本文把两个仪器的原始估计连同 CI 全部公开，正是为了让使用者在分离证据到来之前'
    '有完整的决策依据。',
    )

# ---- 7 结论前补充一段 ----
insert_after(
    '把它们写在同一段描述的不同位置（前者在前、后者在后）还有助于两类通道各自的匹配。',
    '\n\n回到本文的出发点作结。完整性范式答不了"内容有没有功能"，因为功能是关系性质；'
    '本文用判别性示范了关系性质如何被测量、被增量检验、被条件化——三道闸门各司其职。'
    '这套流程对任何新质量构念都是开放的：写出操作化、找到对照集、找到调节变量、'
    '配上第二仪器，然后让数据在冻结的判定规则下说话。'
    '元数据质量研究需要的不是更多听起来正确的构念，而是更多被这样检验过的构念。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P022 total={cjk+words}')
