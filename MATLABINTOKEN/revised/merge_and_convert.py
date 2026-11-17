#!/usr/bin/env python
"""Merge three papers into one unified research report, then convert to DOCX."""
import re
import subprocess
import os

BASE = os.path.dirname(os.path.abspath(__file__))  # 随工作空间迁移自动定位（原为 D:/MATLABINTOKEN/revised）
PAPERS = ['paper01_rewritten.md', 'paper02_rewritten.md', 'paper03_rewritten.md']

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def downgrade_headings(text, levels=1):
    """Increase heading levels by `levels` (e.g. # → ##)."""
    def repl(m):
        return '#' * (len(m.group(1)) + levels) + m.group(2)
    return re.sub(r'^(#{1,6})( .+)$', repl, text, flags=re.MULTILINE)

def extract_sections(text):
    """Split markdown into sections at ## headings."""
    # Find the first ## (section) heading
    sections = {}
    current_section = 'preamble'
    current_lines = []

    # Find all major parts
    parts = re.split(r'\n(?=## )', text)
    return parts

def remove_references(text):
    """Remove the reference section and everything after it."""
    # Match ## 参考文献 or ## References (possibly with spaces)
    # Remove from that heading to end of file
    text = re.sub(r'\n---\n## 参考文献.*$', '', text, flags=re.DOTALL)
    text = re.sub(r'\n## 参考文献.*$', '', text, flags=re.DOTALL)
    text = re.sub(r'\n---\n## 补充数据文件.*$', '', text, flags=re.DOTALL)
    text = re.sub(r'\n## 补充数据文件.*$', '', text, flags=re.DOTALL)
    text = re.sub(r'\n---\n## 附录：补充表格与说明.*$', '', text, flags=re.DOTALL)
    text = re.sub(r'\n## 附录：补充表格与说明.*$', '', text, flags=re.DOTALL)
    return text.strip()

def remove_separators(text):
    """Remove --- horizontal rule lines."""
    text = re.sub(r'\n---\n', '\n', text)
    return text

def extract_title_and_body(text):
    """Extract the # title line and the rest of body."""
    lines = text.strip().split('\n')
    title = ''
    body_start = 0
    for i, line in enumerate(lines):
        if line.startswith('# ') and not line.startswith('## '):
            title = line[2:].strip()
            body_start = i + 1
            break
    body = '\n'.join(lines[body_start:]).strip()
    return title, body

def extract_abstracts(text):
    """Extract Chinese and English abstracts from preamble."""
    # Find abstract blocks - they're before the first ## heading
    # Return both for use in overall abstract
    abstracts = {'zh': '', 'en': ''}

    # Chinese abstract
    m = re.search(r'## 摘要\s*\n(.+?)(?=\n## |\n# )', text, re.DOTALL)
    if m:
        abstracts['zh'] = m.group(1).strip()

    # English abstract
    m = re.search(r'## Abstract\s*\n(.+?)(?=\n## |\n# )', text, re.DOTALL)
    if m:
        abstracts['en'] = m.group(1).strip()

    return abstracts

# ── Step 1: Read and process each paper ──
processed = []
all_refs = []
ref_section = False

for i, paper_file in enumerate(PAPERS):
    text = read_file(os.path.join(BASE, paper_file))

    # Extract paper title
    title, body = extract_title_and_body(text)
    short_label = f'研究{"一二三"[i]}'

    # Extract individual paper references before removing them
    ref_match = re.search(r'## 参考文献\s*\n(.*?)$', text, re.DOTALL)
    if ref_match:
        refs = ref_match.group(1).strip()
        all_refs.append(refs)

    # Remove references, data files, appendices
    body = remove_references(body)

    # Remove abstracts (we'll add unified ones)
    body = re.sub(r'## 摘要\s*\n.+?(?=\n## )', '', body, flags=re.DOTALL)
    body = re.sub(r'## Abstract\s*\n.+?(?=\n## )', '', body, flags=re.DOTALL)

    # Remove horizontal rules
    body = remove_separators(body)

    # Downgrade all headings in body: ## → ###, ### → ####, etc.
    body = downgrade_headings(body, levels=1)

    # Clean up empty lines
    body = re.sub(r'\n{3,}', '\n\n', body)

    processed.append({
        'title': title,
        'short_label': short_label,
        'body': body,
        'chapter_num': i + 1,
    })

# ── Step 2: Build the merged markdown ──
lines = []

# Main title
lines.append('# 用户指令语用特征对任务型交互智能体执行效果的影响')
lines.append('')
lines.append('## —— 基于 AgentNet 大规模 GUI 交互轨迹数据的实证研究三部曲')
lines.append('')
lines.append('---')
lines.append('')

# Overall Abstract
lines.append('## 综合摘要')
lines.append('')
lines.append('本研究报告由三项递进式实证研究构成，均基于 AgentNet 大规模 GUI 交互轨迹数据集（去重后原始样本 $N=22{,}532$，回归分析样本 $N=20{,}205$），从语用学视角系统考察用户指令的语言特征如何影响任务型交互智能体的执行效果。三项研究分别聚焦于三个逐层递进的分析层次：')
lines.append('')
lines.append('**研究一（层次一：单一语用成分的存在/缺失）** 将用户指令中的完成标准/验证条件重新概念化为智能体的"终止判准"，检验了验证信息与任务完成率和执行步数的关联。结果支持：含完成标准的任务完成率显著更高（OR = 1.255, $p<.001$），执行步数显著更少（IRR = 0.883, $p<.001$），终止阶段冗余与错误亦更低。')
lines.append('')
lines.append('**研究二（层次二：语用成分的密度/剂量效应）** 将约束密度界定为"条件性边界资源"，通过三阶段建模揭示了约束密度与完成率之间不存在全局倒 U 形关系，但在高难度和长指令等复杂条件下呈现显著倒 U 形模式，最优密度约 1.7%–1.9%。')
lines.append('')
lines.append('**研究三（层次三：整体语用结构类型）** 将分析单元从单一成分提升至整体语用结构，利用潜类别分析（LCA）从 11 个二元语用特征中识别出五类用户指令语用结构类型，并验证了各类别在完成率、过程指标和路径稳定性上的系统性差异。')
lines.append('')
lines.append('三项研究共同构建了一个从"成分"到"密度"再到"结构"的三层次分析框架，核心论点是：指令效果 = f (语用成分剂量, 语用结构类型, 任务复杂度)。')
lines.append('')
lines.append('**关键词：** 任务型交互智能体；用户指令；语用特征；完成标准；约束密度；语用结构类型；潜类别分析；执行终止；认知负荷；AgentNet')
lines.append('')
lines.append('---')
lines.append('')

# Table of Contents placeholder
lines.append('\\newpage')
lines.append('')
lines.append('# 目录')
lines.append('')
lines.append('[请在 Word 中右键此处 → 更新域 → 更新整个目录]')
lines.append('')
lines.append('\\newpage')
lines.append('')

# ── Add each paper as a chapter ──
for p in processed:
    lines.append(f'# 第{p["chapter_num"]}部分　{p["title"]}')
    lines.append('')
    lines.append(p['body'])
    lines.append('')
    lines.append('\\newpage')
    lines.append('')

# ── Add unified discussion ──
lines.append('# 综合讨论与展望')
lines.append('')
lines.append('## 核心发现回顾')
lines.append('')
lines.append('本系列三项研究构建了一个递进式的分析框架，分别从"单一语用成分的存在性"、"语用成分的密度/剂量效应"和"整体语用结构类型"三个层次，考察了用户指令语用特征对任务型交互智能体执行效果的影响。')
lines.append('')
lines.append('研究一表明，验证信息（完成标准）作为终止判准，提供了智能体判断"何时停止"的关键语言线索。研究二进一步揭示，约束信息的效应并非简单的线性关系，而是取决于任务情境——在高难度和长指令条件下呈现显著倒 U 形。研究三将分析单元提升至语用结构的整体组织方式，发现了五类稳定的指令类型，其中动作约束型在路径稳定性上表现最优。')
lines.append('')
lines.append('## 理论贡献')
lines.append('')
lines.append('1. **言语行为理论的拓展**：将 Austin 和 Searle 的经典言语行为理论拓展至人机交互领域，揭示了指令内部语用结构的多样性及其行为后果。')
lines.append('2. **关联理论的量化检验**：为 Sperber 和 Wilson 的关联理论在人机交互情境中的应用提供了大规模经验证据。验证信息降低认知成本、约束信息存在"过犹不及"效应——两者从不同侧面支撑了认知经济性原则。')
lines.append('3. **认知负荷理论在智能体系统中的延伸**：证明了即便对于 LLM 驱动的智能体系统，输入端的语用密度仍会通过规划、验证和冲突消解机制影响任务执行效果。')
lines.append('4. **共同基础理论的过程层面实证**：Clark 和 Brennan 的共同基础理论被拓展至智能体执行的过程层面——语用结构的充分性不仅影响"能否完成"，更影响"如何完成"（路径稳定性）。')
lines.append('')
lines.append('## 实践启示')
lines.append('')
lines.append('1. **指令设计原则**：对高难度、长指令任务，约束密度建议控制在 1.7%–1.9% 左右，避免约束过载。')
lines.append('2. **完成标准的价值**：明确包含验证条件的指令与更高的执行效率相关联，建议在提示工程和指令模板中嵌入明确的完成判据。')
lines.append('3. **语用结构诊断**：五类语用结构类型为用户指令质量评估提供了类型学框架，可用于智能体提示优化的前置诊断。')
lines.append('4. **终止机制设计**：智能体系统应增强对指令中完成标准的识别与利用能力，将终止判断从启发式规则升级为语言驱动的内部终止规则。')
lines.append('')
lines.append('## 局限与未来方向')
lines.append('')
lines.append('1. **观测性数据局限**：AgentNet 为观测性轨迹数据，所有发现均为统计关联而非因果效应。未来研究可采用实验设计，随机分配约束密度和完成标准条件，实现因果推断。')
lines.append('2. **数据集代表性**：AgentNet 的指令主要来源于英文环境下的桌面/网页 GUI 任务。中文及跨语言、跨操作系统场景的适用性有待验证。')
lines.append('3. **智能体架构差异**：不同智能体系统（如基于视觉的 vs. 基于 DOM 的）可能对同一语用特征产生不同响应，本研究未能区分架构类型的调节效应。')
lines.append('4. **语用特征细粒度**：11 个二元语用特征虽覆盖了主要维度，但未能捕捉语义强度、约束优先级、歧义程度等连续谱系信息。')
lines.append('5. **动态适应**：约束密度的最优值可能随智能体能力演进和任务域迁移而变化，未来需建立自适应约束密度估计框架。')
lines.append('6. **终止机制的因果检验**：本研究提出的"完成标准→终止判准→执行效率"理论链尚需通过实验操控来检验其因果方向。')
lines.append('')
lines.append('\\newpage')
lines.append('')

# ── Unified References ──
lines.append('# 参考文献')
lines.append('')

# Deduplicate and merge references
seen = set()
unified_refs = []
for i, ref_block in enumerate(all_refs):
    for ref_line in ref_block.strip().split('\n'):
        ref_line = ref_line.strip()
        if not ref_line:
            continue
        # Simple dedup based on first 60 chars
        key = ref_line[:60].lower()
        if key not in seen:
            seen.add(key)
            unified_refs.append(ref_line)

for ref in unified_refs:
    lines.append(ref)
    lines.append('')

lines.append('')
lines.append('\\newpage')
lines.append('')

# ── Appendices ──
lines.append('# 附录')
lines.append('')
lines.append('## 附录 A　Paper 01 补充数据文件索引')
lines.append('')
lines.append('- `paper01_tables/terminal_phase_metrics_by_task.csv`：每条任务的终止阶段指标')
lines.append('- `paper01_tables/terminal_phase_summary_by_criteria.csv`：按是否含完成标准分组的描述性汇总')
lines.append('- `paper01_tables/terminal_phase_group_comparisons.csv`：终止阶段指标的组间比较统计量')
lines.append('')
lines.append('## 附录 B　Paper 02 补充数据文件索引')
lines.append('')
lines.append('- `paper02_tables/table1_constraint_taxonomy.md` — 约束分类法')
lines.append('- `paper02_tables/table4_stage1_stage2_models.csv` — Stage 1/2 模型结果')
lines.append('- `paper02_tables/table5_conditional_effects.csv` — 条件效应模型')
lines.append('- `paper02_tables/table8_stage2_full_coefficients.csv` — Stage 2 完整系数')
lines.append('- `paper02_tables/table9_johnson_neyman_simple_slopes.csv` — Johnson-Neyman 简单斜率')
lines.append('')
lines.append('## 附录 C　Paper 03 补充数据文件索引')
lines.append('')
lines.append('- `paper03_tables/tab_model_selection.csv` — LCA 模型选择统计量')
lines.append('- `paper03_tables/tab_class_profiles.csv` — 类别条件响应概率')
lines.append('- `paper03_tables/tab_examples.json` — 各类别代表性指令示例')
lines.append('- `paper03_tables/tab_stability_checks.json` — LCA 稳定性检查结果')

merged = '\n'.join(lines)
output_path = os.path.join(BASE, 'merged_report.md')
write_file(output_path, merged)
print(f'Merged markdown saved: {output_path}')

# ── Step 3: Convert to DOCX using pandoc ──
docx_output = os.path.join(BASE, '研究报告_AgentNet语用特征三部曲.docx')
ref_docx = os.path.join(BASE, 'reference_custom.docx')

cmd = [
    'pandoc',
    output_path,
    '-o', docx_output,
    '--from=markdown',
    '--to=docx',
    f'--reference-doc={ref_docx}',
    '--resource-path=' + BASE,
    '--wrap=none',
    '--markdown-headings=atx',
    '--metadata=title:用户指令语用特征对任务型交互智能体执行效果的影响',
    '--toc',
    '--toc-depth=3',
    '--number-sections',
]

print(f'Running: {" ".join(cmd)}')
result = subprocess.run(cmd, capture_output=True, text=True, cwd=BASE)
if result.returncode == 0:
    print(f'DOCX saved: {docx_output}')
    # Verify
    import zipfile
    with zipfile.ZipFile(docx_output) as z:
        images = [n for n in z.namelist() if n.startswith('word/media/')]
        print(f'Embedded images: {len(images)}')
        size_kb = os.path.getsize(docx_output) // 1024
        print(f'File size: {size_kb}KB')
else:
    print(f'Pandoc error: {result.stderr}')
