# -*- coding: utf-8 -*-
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P066_relation_classes_between_attempts_of_one_task\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def ins(anchor, addition):
    global t
    assert anchor in t, 'MISS: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

blocks = [
    ('**精炼对（86%）→ 增量合并**——保留第一次的版本、把第二次的新增与修订并入，版本历史即知识演化史；',
     '\n\n三类流行度还有一个与 P063 携带发现的联动值得挑明：'
     '精炼占 86% 说明绝大多数重试在词汇层连续——'
     '这正是 P063 测到的携带（话语成分跨尝试 0.13-0.32）'
     '得以发生的土壤：'
     '若重试都是白纸重写，'
     '前次的成分根本没有被复述的机会。'
     '两个包从两端夹住了同一个机制：'
     'P063 测的是连续性的结果（成分被携带），'
     '本文测的是连续性的本身（86% 的对词面连续）。'
     '把这个联动写进知识库规范的意义在于：'
     '合并器的增量分支不仅是存储优化，'
     '它还保护了话语携带的载体——'
     '把精炼对合并成单一版本时保留版本历史，'
     '就是保留携带链的每一环。'),

    ('**模型。** H2：logistic on later_submitted ~ relation_class + jaccard + 长度控制，实例聚类。',
     '\n\n关于矛盾标记的定义还需要两行精确化。'
     '矛盾标记由冻结的结论冲突模式触发：'
     '两次尝试的散文中对同一对象给出互斥状态判断'
     '（"测试通过"对"测试失败"、"文件存在"对"文件不存在"）。'
     '模式库约二十条，覆盖状态动词的反义对；'
     '不含数值矛盾（版本号不同未计入）。'
     '8.6% 的矛盾率因此是状态类矛盾的计数，'
     '数值类与推理类矛盾不在内——'
     '真实的不一致率高于此。'
     '这个保守性在审计语义下是安全的'
     '（标出的矛盾几乎必真），'
     '在流行率语义下是低估的——'
     '引用时需注明口径。'),

    ('它描述重试的形态（86% 是修订），但形态不决定命运。',
     '\n\n把本包的判定放进 wave-11 五连发的总谱里看格局：'
     'P062（话语×结局）supported 但被 H3 驯化；'
     'P063（话语×话语）supported 干净；'
     'P064（具体性×传递）supported 干净、×完成 null；'
     '本文（关系×完成）not_estimable。'
     '四包的判定质量呈梯度递减——'
     '越靠近"完成预测"这个金矿的假设死得越惨，'
     '越远离它的（传递、携带）越健康。'
     '这个格局本身就是 wave-11 最大的元发现：'
     '**完成标签的信息量几乎被长度与难度耗尽，'
     '文本变量的预测空间只剩话语功能的窄门。**'
     '任何想在下一个波次预测完成的团队，'
     '应把预算投给实例分层而非文本特征工程。'),
]

for anchor, addition in blocks:
    ins(anchor, addition)

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P066 total={cjk+words}')
