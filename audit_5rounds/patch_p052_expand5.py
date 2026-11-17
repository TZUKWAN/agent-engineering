# -*- coding: utf-8 -*-
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P052_the_recovery_window_after_a_failed_step\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def ins(anchor, addition):
    global t
    assert anchor in t, 'MISS: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

blocks = [
    ('q4 的对照臂（不换者）少到标准误爆炸（41.96），CI 横跨正负 64。',
     '\n\n补一个对照臂在四层间的分布账，它解释了病态为何集中在两端：'
     '44 条不换者按轨迹长度的自然分布落位后，'
     '最短层与最长层各自只分到个位数的对照臂——'
     '而这两层恰好也是暴露变异最需要对照臂的层。'
     '小对照臂加层内切分，是准分离与标准误爆炸的标准配方；'
     'q3 的可用纯粹是运气：恰有足够的不换者落在中层。'
     '这个分布账还有设计层面的读法：'
     '若在冻结阶段做过对照臂的层间预算，'
     'H3 的四层符号复现设计会当场改为两层合并设计——'
     '预算检查又一次在读数前就能改写设计的命运。'),

    ('类比已经成熟的领域：人类外科手术的"是否洗手"在塞麦尔维斯之后不再是研究变量（执行率≈100%），研究全部转向"怎么洗、何时洗、洗什么"——智能体的失败响应正站在自己的塞麦尔维斯时刻。',
     '\n\n把时刻的判断再压实一点：'
     '塞麦尔维斯的转折不是执行率达到 100% 的那一天，'
     '而是有人指出「执行率的方差已经消失、剩余的死亡差异必须来自别处」的那一天。'
     '本文对智能体失败响应做的就是同样的指出：'
     '44/17,229 的对照臂说明"是否立即换"的方差已经见底，'
     '2.46% 的提交率说明结局差异必然来自别处——'
     '来自更换的质量、来自失败之间的轨迹结构（138.93 的贡献）、'
     '来自与失败无关的任务难度。'
     '指出的价值在于把整个研究社区的注意力'
     '从一个已死的变量上移开——'
     '这比本文三个判定词中的任何一个都更接近贡献的本质。'),
]

for anchor, addition in blocks:
    ins(anchor, addition)

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P052 total={cjk+words}')
