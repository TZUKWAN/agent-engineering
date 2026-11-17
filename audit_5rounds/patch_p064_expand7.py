# -*- coding: utf-8 -*-
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P064_abstraction_level_of_a_trace_and_transfer\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def ins(anchor, addition):
    global t
    assert anchor in t, 'MISS: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

blocks = [
    ('它们是轨迹间最可靠的对齐锚点。',
     '\n\n**关于 H3 判定词的一句方法论附注。**'
     'not_specific_the_alien_level_carries_it_too 的十一拍'
     '与 P063 的 not_specific_the_alien_category_carries_it_too'
     '几乎同构——'
     '姊妹设计的判定词也成对出现，'
     '这不是巧合而是模板化的红利：'
     '判定词的格式化（结论_原因_数字）使跨包检索成为可能——'
     '在全部 70 个包的判定词里搜 not_specific，'
     '能一次拉出所有被特异性规则咬过的设计，'
     '再按原因后缀分组，'
     '规则误咬的模式一目了然。'
     '判定词从结论标签升级为可查询的数据库字段，'
     '这是冻结协议在知识管理层的意外收益。'),

    ('## 一、问题定位：具体性轴从修辞学到轨迹库',
     '\n\n在展开之前，一个阅读提示：'
     '本文有三条互相独立的主线——'
     '传递线（H1/H3，具体性作为记忆）、'
     '结局线（H2，具体性作为预测元）、'
     '结构线（关系分类，重试的形态学）。'
     '三条线共享数据但结论互不依赖，'
     '读者可以只取所需：'
     '做知识库的取传递线与结构线，'
     '做结局预测的读结局线并记住它的 null，'
     '做方法论的看三臂模板如何同时服务三条线。'
     '这种多线结构是 wave-11 姊妹设计的共同特征——'
     '一次构建、多轴收割，'
     '代价是单篇论文要同时交代三条线的边界。'),

    ('分解读法：约 5/6 的传递是紧邻记忆（上次写了这些路径，这次记得），约 1/6 是任务土壤（这个任务本来就长这样）。',
     '\n\n土壤成分的实践意义在选型场景最突出：'
     '若两个模型栈的土壤系数不同'
     '（A 栈把所有任务写得同样具体，B 栈跟随任务变化），'
     '则 B 栈的轨迹携带更多任务结构信息、'
     '更适合做知识源。'
     '土壤系数因此是模型选型的一个候选指标——'
     '"语言对任务的响应度"：'
     '响应度高意味着散文忠实反映任务差异，'
     '响应度低意味着散文被模型自身的文体偏好主导。'
     '本帧只有单栈，无法给出两个栈的对照，'
     '但 alien 臂的测量方法栈间通用——'
     '多栈对比是这个设计的直接扩展，'
     '也是"语言响应度"这个新指标的诞生地。'),
]

for anchor, addition in blocks:
    ins(anchor, addition)

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P064 total={cjk+words}')
