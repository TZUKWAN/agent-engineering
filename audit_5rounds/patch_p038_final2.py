# -*- coding: utf-8 -*-
"""P038 最终冲线（+550 字）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P038_repetition_and_rumination\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

blocks = [
    # 摘要末尾补
    ('行为分类学获得一个三分类框架（留守深耕、换挡探索、复核空转）。反刍这个临床隐喻在机器轨迹上的第一次受审，以改判复核告终——而判决的可靠性，由系列最大的一条 LRχ² 背书。',
     '改判的完整证据链随判定词一并存档：悬崖（H1）、结局（H2）、形状（H3）三线互证，任何单独一线都不足以完成改判。'),
    # 4.3 结尾补
    ('干预含义随之确定：缓存返回优于循环检测。',
     '\n\n缓存方案的边界条件与悬崖的成因同源：悬崖的存在证明环境的确定性，'
     '缓存的安全性依赖同一确定性——若任务域扩展到动态数据源'
     '（实时行情、滚动日志），确定性失效，悬崖变坡，'
     '缓存方案需要附带失效检测。缓存的启用范围因此应当'
     '与悬崖的实测范围（只读文件与仓库类命令）一致，'
     '而不是想当然地全局启用。'),
    # 4.4 后补
    ('图 4 的八条高频命令串是后者的快照。',
     '\n\n快照的另一个读法是风险提示：高频命令串的跨轨迹复用'
     '（6,291 次出现的那条命令平均每 3 条 rollout 就出现一次）'
     '意味着一个系统性依赖——若该命令的行为在环境的某次变更中改变，'
     '波及的是全部依赖它的轨迹。跨轨迹共性因此不只是'
     '重复研究的边界注记，它是环境依赖审计的入口：'
     '高频命令串清单就是系统对环境的依赖清单。'),
    # 5.2 结尾补
    ('三分类是步级行为学的完备分类框架，比二元（有效/无效）精细且可操作。',
     '\n\n三分类的操作化全部落在帧内：留守等于同族非重复（P036 的留守判定）、'
     '换挡等于跨族（P036 的切换判定）、复读等于同命令精确重复（本文）。'
     '三类的行为待遇已经齐备：留守有 P036 的红利读数、换挡有本文引用的红利'
     '（+0.22）、复读有本文的悬崖（−1.34）。框架的完备性检验是'
     '三类是否穷尽步间关系——同一命令的参数微调（近重复）'
     '是第四类的候选，其边界按第 6 节第四条例归入首跑。'),
]

for anchor, addition in blocks:
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P038 total={cjk+words}')
