# -*- coding: utf-8 -*-
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P070_agent_trajectory_corpora_as_intelligence_sources\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def ins(anchor, addition):
    global t
    assert anchor in t, 'MISS: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

blocks = [
    ('H3 判 *measured*：八构念的每库平均可用率 2.25/8（28%）；最全的 SWE-ZERO 也只支持 6/8（缺来源归属与工具目录）；四个语料（AgentBank、AgentInstruct、code-act 与多数的 MMAT）几乎全零。',
     '\n\n**逐库画像**是矩阵的行读法，值得逐行给出。'
     'SWE-ZERO（6/8）：软件工程轨迹，带 exit_status 与时长——'
     '除来源归属与工具目录外全支持，是构念研究的头号地基；'
     '它的 1,230 个文件也暗示这是最接近"生产日志"的库。'
     'Toucan（5/8）：工具调用语料，罕见的双质量列——'
     '缺修复与来源，但问题与回答各有评分；'
     'AgentTrove（3/8）：21 列的超宽模式，'
     '结局、修复、来源三构念在列——'
     '宽模式但构念覆盖平庸，'
     '列多不等于构念多（多的是过程元数据：run_id、trial_name、provider）。'
     'MMAT（3/8）：多模态问题库，矛盾、落地、停止三构念可测——'
     '它是 P068 的家。'
     'hermes（1/8）：仅工具目录。'
     'AgentBank、AgentInstruct、code-act（0/8）：'
     '两列结构（id+conversations），纯对话文本——'
     '对语言研究有用，对行为测量是白板。'
     '八行读完，生态的分层一目了然：'
     '一个六构念地基、两个四构念级、'
     '五个从一构念到白板。'),

    ('**读法三（整体）**：28% 的平均可用率意味着**一个典型的信息行为问题，在随手抓起的语料上有七成概率测不了**。',
     '\n\n28% 还有第三个读法——时间维度上的读法。'
     '若把矩阵与各库的发布日期对照（AgentTrove 带 date 列），'
     '可以问：新语料的构念覆盖是否在改善？'
     '本帧的八库横跨多个发布周期，'
     '覆盖最好的 SWE-ZERO 与 Toucan 恰是较新的库——'
     '一个暗示生态在学习的小证据（样本量 2，不足为证，'
     '但足以构造可检验的趋势假设：'
     '构念覆盖随发布年份上升）。'
     '若趋势为真，'
     '矩阵的正确用法是加时间戳的动态路由表——'
     '每季度重跑普查、追加新库行，'
     '让"哪里有土"的答案跟上土地的变化。'
     '普查的低成本（分钟级）使这个动态化完全可行——'
     '本文的脚本就是那个季度任务的雏形。'),

    ('第一，**矩阵即路由表**：研究者带着构念来，查表选库——本文后这步查找从"读遍 README"变成"看一格"。',
     '\n\n矩阵作为路由表的权威性来自它的判定纪律，'
     '与系列实验包同源：'
     '列名对照表冻结于读数前（构念→列名的映射不许事后增补）、'
     '判定机械（在表即勾，不在即空，无人工裁量）、'
     '边界情形留档（AgentTrove 的 result 列语义存疑，'
     '勾照打但存疑注记随行）。'
     '读者可能会问：'
     '列名支持与真实可用之间隔着一层「列里有值吗、值有意义吗」的距离——'
     '是的，这正是第五节第一条局限的内容。'
     '路由表给的是"值得打开看看"的列表，'
     '不是"打开即用"的保证——'
     '地图标记有水井，'
     '井里有没有水要自己打一桶。'
     '但相比此前"在README的海洋里捞井"的作业方式，'
     '一张标了井位的地图已经是生产力的数量级跃迁。'),
]

for anchor, addition in blocks:
    ins(anchor, addition)

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P070 total={cjk+words}')
