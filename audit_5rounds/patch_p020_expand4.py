# -*- coding: utf-8 -*-
"""P020 paper_cn.md 扩写补丁（第四轮，冲线）。"""
import io, re

P = r'G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers\P020_name_description_congruence\paper_cn.md'
t = io.open(P, encoding='utf-8').read()

def insert_after(anchor, addition):
    global t
    assert anchor in t, 'anchor missing: ' + anchor[:40]
    t = t.replace(anchor, anchor + addition, 1)

# ---- 3.1 补充 ----
insert_after(
    '保证所有特征列与冻结帧一致。',
    '候选级观测的构成需要注意：24,000 条查询摊出 169,203 条候选，平均每查询约 7.05 个候选；'
    '一致性在候选间变异、在查询内比较，这正是其作为目录治理变量的意义——'
    '同一目录内条目之间的写作差异，而非目录之间的风格差异。',
    )

# ---- 5.1 结尾补充 ----
insert_after(
    '分离两者需要以名称结构分层的操纵设计。',
    '在设计完成之前，双重证据机制有一个现成的间接检验：若机制成立，'
    '一致性效应对名称长度应敏感——名称词项越多，可被覆盖的成分越多，'
    '同一覆盖率对应的绝对重叠词数差异越大。本包产物未按名称长度分层，'
    '这一推论同样留作后续分析而非本文结论。',
    )

# ---- 结论运行追溯前补充一句 ----
insert_after(
    '本文贡献了空单元格判定词的完整执行样本；对目录维护者，贡献了按 0.1119 校准预期的规范依据。',
    '两项贡献共享同一个态度：判定系统只说数据能支撑的话——效应多大就说多大，'
    '空格就说空格——这套态度在元数据研究从规范直觉走向经验学科的路上是必需品。',
    )

io.open(P, 'w', encoding='utf-8').write(t)
cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
words = len(re.findall(r'[A-Za-z0-9][A-Za-z0-9._%+\-/]*', t))
print(f'P020 total={cjk+words}')
