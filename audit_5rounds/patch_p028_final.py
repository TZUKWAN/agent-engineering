# -*- coding: utf-8 -*-
"""P028 paper_cn.md 扩写补丁（第四轮，冲线）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P028_conclusion_before_evidence\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 1.1 末尾补 ----
insert_after(
    '而 H1 的前提普查发现：样本乙大大多于样本甲——甲类轨迹稀少到无法支撑对比。',
    '\n\n"稀少"本身是这条研究线上的第一个发现。在一万四千余条真实任务轨迹里，'
    '在没有任何检验的情况下就宣布结论的轨迹只占千分之几（普查 114/4,000、'
    '设计帧 472/20,000，约 2.4%）——智能体在绝大多数轨迹里都先动了手再下结论。'
    '这个基率对两个读者群有不同含义：对担心"模型闭眼瞎答"的安全性研究者，'
    '2.4% 是一个可以接受的低流行率（尽管其后果权重未必低）；'
    '对想研究"结论先行"现象的认知科学家，2.4% 意味着自然数据是稀缺的——'
    '想做大样本对比只能靠设计帧的累加或人工诱发。'
    '基率的稀缺性反过来为 H1 的底线条款提供了正当性：'
    '对千分之几的事件设 200 条轨迹的门槛，是对功效的诚实而非过度的谨慎。',
    )

# ---- 4.5 表后补 ----
insert_after(
    'Holm 在 3 假设族内执行；两口径计数与逐格率为随行材料。',
    '\n\n校正的敏感度照例一句带过：H2 与 H3 的 p_raw（0.0029 以下）经三重校正后'
    '判定不变。三个判定词的组合（not_testable / opposite / supported）'
    '在系列里是第二次出现（首次为 P021 的 partial / null / opposite），'
    '但这次的 not_testable 是前提失效而非机制失效——判定词表的分工'
    '让两种"没做成"在文献里不会被混为一谈。',
    )

# ---- 7 结论最后补 ----
insert_after(
    '预注册的信誉不是靠不犯错维系的，是靠这种时刻维系的。',
    '\n\n把全文收拢成三句话给三类读者。做预注册的：前提条款要指名测量者，'
    '指了就认。做行为分析的：顺序效应在做协变量控制之前不要下结论，'
    '控制之后若反转，把反转本身当发现。做智能体评测的：结论话语是免费的'
    '收束信号（H3），但它的话语学身份还押在词表复核（P027 遗留）上——'
    '用它的方向，留档它的幅度，等它的身份证。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P028 total={cjk+words}')
