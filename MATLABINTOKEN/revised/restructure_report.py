#!/usr/bin/env python3
"""
Restructure merged_report.md into a unified academic report.
- 5 chapters with continuous numbering
- Figures 1-21, Tables 1-29 continuous
- All section numbers unified
- Cross-references updated
"""
import re, os

BASE = os.path.dirname(os.path.abspath(__file__))
INPUT = os.path.join(BASE, 'merged_report.md')
OUTPUT = os.path.join(BASE, 'merged_report_unified.md')
MAPPING_LOG = os.path.join(BASE, 'renumbering_map.txt')

with open(INPUT, 'r', encoding='utf-8') as f:
    lines = f.read().split('\n')

# ── State ──
out = []
fig_counter = 0
tab_counter = 0
fig_map = {}   # (chapter_key, old_num) → new_num
tab_map = {}   # (chapter_key, old_id_str) → new_num
ch_key = 'front'  # front, ch2, ch3, ch4, back, appendix

# Detect appendix sub-sections
# "## 附录：补充表格" is Paper 02 appendix tables
# "## 附录：补充表格与说明" is Paper 03 appendix tables

i, n = 0, len(lines)

def rewrite_section(s, chapter_key):
    """Rewrite ### N Title → ### X.N Title based on chapter."""
    ch_num = {'ch2': '2', 'ch3': '3', 'ch4': '4'}.get(chapter_key)
    if not ch_num:
        return s
    m = re.match(r'^### (\d+) (.+)$', s)
    if m:
        return f'### {ch_num}.{m.group(1)} {m.group(2)}'
    return s

def rewrite_subsection(s, chapter_key):
    """Rewrite #### N.M Title → #### X.N.M Title."""
    ch_num = {'ch2': '2', 'ch3': '3', 'ch4': '4'}.get(chapter_key)
    if not ch_num:
        return s
    m = re.match(r'^#### (\d+)\.(\d+) (.+)$', s)
    if m:
        return f'#### {ch_num}.{m.group(1)}.{m.group(2)} {m.group(3)}'
    return s

def rewrite_subsubsection(s, chapter_key):
    """Rewrite ##### N.M.K Title → ##### X.N.M.K Title."""
    ch_num = {'ch2': '2', 'ch3': '3', 'ch4': '4'}.get(chapter_key)
    if not ch_num:
        return s
    m = re.match(r'^##### (\d+)\.(\d+)\.(\d+) (.+)$', s)
    if m:
        return f'##### {ch_num}.{m.group(1)}.{m.group(2)}.{m.group(3)} {m.group(4)}'
    return s

# ── Chapter transition paragraphs ──
CH1_INTRO = '''
\\newpage

# 第一章　导论

## 1.1　研究背景

以大语言模型（Large Language Model, LLM）为核心、融合视觉感知的任务型交互智能体（task-oriented interactive agent），近年来在人机交互、自动化办公、软件测试与数字助手等领域的应用快速扩展。典型系统如 Mind2Web（Yang et al., 2022）、WebGPT（Pal et al., 2022）以及 AUSTIN（Yuan et al., 2023），展示了智能体在网页浏览、文件管理与复杂多步骤任务中的执行能力；AgentNet（Wang et al., 2025）等大规模真实交互轨迹数据集的发布，则为从自然语言指令维度理解人机协同效能提供了宝贵的经验基础。

从过程视角审视，任务型交互智能体的执行可抽象为一条通用链：**用户任务表达 → 意图解析 → 动作规划 → 环境交互 → 状态评估 → 执行终止**。在这一链条中，用户指令的语言特征——特别是其语用维度——如何影响智能体在各环节的表现，构成了一个亟需系统探索的研究领域。

## 1.2　三层次分析框架

本研究报告从语用学视角出发，构建了一个由微观到宏观的三层次递进分析框架，系统考察用户指令的语用特征如何影响任务型交互智能体的执行效果：

**第一层次（成分层）：单一语用成分的存在/缺失。** 以完成标准/验证信息为核心变量，检验语用成分的有无是否与智能体执行终止行为的差异相关联。该层次回答的核心问题是：指令中的某种语用信息"有没有"是否重要？

**第二层次（剂量层）：语用成分的密度/剂量效应。** 将分析从存在/缺失提升至密度维度，检验约束关键词的密度是否与执行效果呈非线性关系，以及该关系是否受任务复杂度的调节。该层次回答的核心问题是：语用成分"有多少"才恰到好处？

**第三层次（结构层）：整体语用结构类型。** 将分析单元从单一成分提升至整体语用结构配置，利用潜类别分析识别用户指令的语用结构类型，并检验不同类型与执行效果的关联。该层次回答的核心问题是：语用特征的整体"组合方式"如何影响执行？

三个层次由点到面、由成分到结构，构成一个完整的分析闭环。核心论点为：**指令效果 = f(语用成分剂量, 语用结构类型, 任务复杂度)。**

## 1.3　数据基础

本研究基于 AgentNet 大规模 GUI 交互轨迹数据集（Wang et al., 2025）。该数据集包含 22,532 条真实用户与 GUI 交互智能体的任务记录（已按官方元数据剔除 93 条重复 task_id），涵盖操作系统（Windows/macOS）、应用类型（浏览器、文件管理器、办公软件等）和任务复杂度等多个维度。经数据清洗与筛选后，回归分析样本量为 $N=20{,}205$。每条记录包含用户原始指令文本、智能体执行的动作序列、任务完成状态、执行步数及多项元数据。

## 1.4　报告结构

本报告共五章。第一章为导论，概述研究背景与三层次分析框架。第二章至第四章分别对应三个实证研究层次：第二章检验完成标准/验证信息的有无对执行终止的影响（成分层），第三章考察约束密度的条件性非线性效应（剂量层），第四章识别用户指令的语用结构类型及其执行效应（结构层）。第五章为综合讨论，整合三项研究的发现，讨论理论贡献与实践启示，并指出研究局限与未来方向。

\\newpage

'''.strip()

CH2_HEADER = '''
# 第二章　完成标准与执行终止：用户指令验证信息对智能体执行效率的影响

> 本章从语用成分层面出发，考察用户指令中验证信息（完成标准/验证条件）的显性存在如何作为智能体的"终止判准"，影响任务执行终止的时机与质量。作为三层次分析框架的第一层次，本章聚焦单一语用成分（完成标准）的有无对任务完成率与执行效率的统计关联，为后续章节的密度分析和结构分析奠定基础。

'''.strip()

CH3_HEADER = '''
\\newpage

# 第三章　约束密度的条件性效应：从全局定律到边界条件的实证检验

> 在第二章确认完成标准作为终止判准的效应之后，本章将分析层次从单一语用成分的有无提升至语用成分的密度/剂量维度，系统考察用户指令中约束关键词密度对任务完成率的非线性效应及其条件依赖性。核心发现是：约束密度与任务完成率之间不存在全局倒U形关系，但在高难度和长指令等复杂条件下呈现显著倒U形模式，最优密度约 1.7%–1.9%。本章构成三层次分析框架的第二层次——语用成分的密度效应。

'''.strip()

CH4_HEADER = '''
\\newpage

# 第四章　用户指令的语用结构类型学：基于潜类别分析的语用类型及其执行效应

> 第二章和第三章分别从单一成分和密度维度考察了语用特征对智能体执行效果的影响。本章将分析单元从单一成分提升至整体语用结构，利用潜类别分析（LCA）从 11 个二元语用特征中识别用户指令的语用结构类型，并检验各类别在任务执行效果上的系统性差异。本章构成三层次分析框架的第三层次——整体语用结构类型，完成了从"成分→密度→结构"的完整分析闭环。

'''.strip()

CH5_HEADER = '''
\\newpage

# 第五章　综合讨论与展望

> 前述三章分别从"成分层"（验证信息的有无）、"剂量层"（约束密度的非线性效应）和"结构层"（语用结构的整体类型）三个递进层次，系统考察了用户指令语用特征对任务型交互智能体执行效果的影响。本章将三类分析的发现进行交叉整合，提炼跨层次的理论命题，评估其对提示工程实践的启示，并识别当前三层次框架的局限性，为后续研究指明方向。
'''.strip()

# ═══════════════════════════════════════════════
# LINE-BY-LINE PROCESSING
# ═══════════════════════════════════════════════

while i < n:
    line = lines[i]
    s = line.strip()

    # ── 0. "三部曲" → remove ──
    if s == '## —— 基于 AgentNet 大规模 GUI 交互轨迹数据的实证研究三部曲':
        out.append('## —— 基于 AgentNet 大规模 GUI 交互轨迹数据的实证研究')
        i += 1; continue

    # ── 0b. 综合摘要 → 摘要 ──
    if s == '## 综合摘要':
        out.append('## 摘要')
        i += 1; continue

    # ── 0c. 目录 section ──
    if s == '# 目录':
        out.append(line)
        i += 1
        # Skip the Word instruction line
        while i < n:
            nl = lines[i].strip()
            out.append(lines[i])
            i += 1
            if nl.startswith(r'\newpage'):
                break
        continue

    # ── 1. Paper 01 → Chapter 2 + add Chapter 1 before it ──
    if s.startswith('# 第1部分'):
        ch_key = 'ch2'
        out.append(CH1_INTRO)
        out.append('')
        out.append(CH2_HEADER)
        out.append('')
        i += 1
        # skip the --- separator line if present
        if i < n and lines[i].strip() == '---':
            i += 1
        continue

    # ── 2. Paper 02 → Chapter 3 ──
    if s.startswith('# 第2部分'):
        ch_key = 'ch3'
        out.append(CH3_HEADER)
        out.append('')
        i += 1
        if i < n and lines[i].strip() == '---':
            i += 1
        continue

    # ── 3. Paper 03 → Chapter 4 ──
    if s.startswith('# 第3部分'):
        ch_key = 'ch4'
        out.append(CH4_HEADER)
        out.append('')
        i += 1
        if i < n and lines[i].strip() == '---':
            i += 1
        continue

    # ── 4. 综合讨论 → Chapter 5 ──
    if s == '# 综合讨论与展望':
        ch_key = 'back'
        # Clean trailing ---, \newpage, blank lines before inserting Ch5
        while out and out[-1] in ('', '---', '\\newpage'):
            out.pop()
        out.append(CH5_HEADER)
        out.append('')
        i += 1
        continue

    # ── 5. Appendix section markers ──
    if s == '## 附录：补充表格':
        ch_key = 'appendix_p02'  # Paper 02 appendix tables
        out.append(line)
        i += 1; continue

    if s == '## 附录：补充表格与说明':
        ch_key = 'appendix_p03'  # Paper 03 appendix tables
        out.append(line)
        i += 1; continue

    if s == '# 附录':
        ch_key = 'appendix'
        out.append(line)
        i += 1; continue

    # ── 6. ### section headings (within ch2/ch3/ch4) ──
    if ch_key in ('ch2','ch3','ch4') and s.startswith('### ') and not s.startswith('### 表'):
        m = re.match(r'^### (\d+) (.+)$', s)
        if m:
            ch_num = {'ch2':'2','ch3':'3','ch4':'4'}[ch_key]
            out.append(f'### {ch_num}.{m.group(1)} {m.group(2)}')
            i += 1; continue

    # ── 7. #### subsection headings ──
    if ch_key in ('ch2','ch3','ch4') and s.startswith('#### '):
        m = re.match(r'^#### (\d+)\.(\d+) (.+)$', s)
        if m:
            ch_num = {'ch2':'2','ch3':'3','ch4':'4'}[ch_key]
            out.append(f'#### {ch_num}.{m.group(1)}.{m.group(2)} {m.group(3)}')
            i += 1; continue

    # ── 8. ##### subsubsection headings ──
    if ch_key in ('ch2','ch3','ch4') and s.startswith('##### '):
        m = re.match(r'^##### (\d+)\.(\d+)\.(\d+) (.+)$', s)
        if m:
            ch_num = {'ch2':'2','ch3':'3','ch4':'4'}[ch_key]
            out.append(f'##### {ch_num}.{m.group(1)}.{m.group(2)}.{m.group(3)} {m.group(4)}')
            i += 1; continue

    # ── 9. Figure image: ![图 X　...](path) ──
    m_fig = re.match(r'^!\[图 (\d+)[　\s]+(.+)\]\((.+)\)$', s)
    if m_fig:
        old = int(m_fig.group(1))
        fig_counter += 1
        fig_map[(ch_key, str(old))] = fig_counter
        out.append(f'![图 {fig_counter}　{m_fig.group(2)}]({m_fig.group(3)})')
        i += 1; continue

    # ── 10. Figure bold caption: **图 X　...** ──
    m_fig_bold = re.match(r'^\*\*图 (\d+)[　\s]+(.+)\*\*$', s)
    if m_fig_bold:
        old = m_fig_bold.group(1)
        new = fig_map.get((ch_key, old), old)
        out.append(f'**图 {new}　{m_fig_bold.group(2)}**')
        i += 1; continue

    # ── 11. Table BOLD caption: **表 X　...** (fullwidth-space-separated, ends with **) ──
    m_tab = re.match(r'^\*\*表 (\d+)[　\s：:]+(.+)\*\*$', s)
    if m_tab:
        old = m_tab.group(1)
        tab_counter += 1
        tab_map[(ch_key, old)] = tab_counter
        out.append(f'**表 {tab_counter}　{m_tab.group(2)}**')
        i += 1; continue

    # ── 12. Table HEADING caption: ### 表 X　... or ### 表 A1　... ──
    m_tab_head = re.match(r'^### 表 ([A-Z]?\d+)[　\s]+(.+)$', s)
    if m_tab_head:
        old = m_tab_head.group(1)
        tab_counter += 1
        tab_map[(ch_key, old)] = tab_counter
        out.append(f'### 表 {tab_counter}　{m_tab_head.group(2)}')
        i += 1; continue

    # ── 13. Default ──
    out.append(line)
    i += 1

# ═══════════════════════════════════════════════
# SECOND PASS: Inline reference replacement
# ═══════════════════════════════════════════════
# Use TWO-PHASE approach to avoid cascading replacement bugs:
# Phase 1: old numbers → unique placeholders
# Phase 2: placeholders → new numbers
# This handles permutation mappings (e.g., Paper 01 图7→5, 图5→3)
# where old and new number sets overlap.

joined = '\n'.join(out)

# Split by chapter boundaries
chapter_splits = re.split(r'(?=^# 第[一二三四五]章\s)', joined, flags=re.MULTILINE)
new_parts = []

for part in chapter_splits:
    ch_m = re.match(r'^# 第([一二三四五])章', part, re.MULTILINE)
    if not ch_m:
        new_parts.append(part)
        continue

    ch_name = ch_m.group(1)
    num_map = {'一': '1', '二': '2', '三': '3', '四': '4', '五': '5'}
    ch_num = num_map.get(ch_name, '0')
    key_map = {'2': 'ch2', '3': 'ch3', '4': 'ch4'}
    ck = key_map.get(ch_num, 'front')

    local_fig = {old: str(new) for (k, old), new in fig_map.items() if k == ck}
    local_tab = {old: str(new) for (k, old), new in tab_map.items() if k == ck}

    # Include appendix mappings so cross-references in main text are updated
    if ck == 'ch3':
        for (k, old), new in tab_map.items():
            if k == 'appendix_p02':
                local_tab[old] = str(new)
    elif ck == 'ch4':
        for (k, old), new in tab_map.items():
            if k == 'appendix_p03':
                local_tab[old] = str(new)

    # ── PHASE 1: Replace old numbers with unique placeholders ──
    # Four patterns: plain 图X, bold **图X**, plain 表X, bold **表X**

    def _sort_key(x):
        """Sort key: numeric (int) descending, then alphabetic descending."""
        try:
            return (0, int(x))
        except ValueError:
            return (1, x)

    if local_fig:
        # Sort longest number first to avoid partial matches (图10 before 图1)
        sorted_keys = sorted(local_fig.keys(), key=_sort_key, reverse=True)
        for old in sorted_keys:
            pid = f'__FIGREF_{ck}_{old}__'
            # Bold inline: **图 X**
            part = re.sub(
                r'\*\*图\s*' + re.escape(old) + r'\*\*',
                f'**__BFIGREF_{ck}_{old}__**',
                part
            )
            # Plain inline: 图 X (not preceded by ![, not preceded by **)
            part = re.sub(
                r'(?<!\[)(?<!\*\*)图\s*' + re.escape(old) + r'(?!\d)',
                f'__FIGREF_{ck}_{old}__',
                part
            )

    if local_tab:
        sorted_keys = sorted(local_tab.keys(), key=_sort_key, reverse=True)
        for old in sorted_keys:
            pid = f'__TABREF_{ck}_{old}__'
            # Bold inline: **表 X**
            part = re.sub(
                r'\*\*表\s*' + re.escape(old) + r'\*\*',
                f'**__BTABREF_{ck}_{old}__**',
                part
            )
            # Plain inline: 表 X (not preceded by **)
            part = re.sub(
                r'(?<!\*\*)表\s*' + re.escape(old) + r'(?!\d)',
                f'__TABREF_{ck}_{old}__',
                part
            )

    # ── PHASE 2: Resolve placeholders to new numbers ──
    for old, new in local_fig.items():
        part = part.replace(f'__FIGREF_{ck}_{old}__', f'图 {new}')
        part = part.replace(f'__BFIGREF_{ck}_{old}__', f'图 {new}')

    for old, new in local_tab.items():
        part = part.replace(f'__TABREF_{ck}_{old}__', f'表 {new}')
        part = part.replace(f'__BTABREF_{ck}_{old}__', f'表 {new}')

    new_parts.append(part)

joined = ''.join(new_parts)

# ── Global replacements (cross-chapter) ──
# Handle combined patterns BEFORE individual replacements
joined = joined.replace('Paper 01/02', '第二章与第三章')
joined = joined.replace('Paper 01', '第二章')
joined = joined.replace('Paper 02', '第三章')
joined = joined.replace('Paper 03', '第四章')
joined = joined.replace('研究一', '第二章')
joined = joined.replace('研究二', '第三章')
joined = joined.replace('研究三', '第四章')
joined = joined.replace('附录 A　Paper 01', '附录 A　第二章')
joined = joined.replace('附录 B　Paper 02', '附录 B　第三章')
joined = joined.replace('附录 C　Paper 03', '附录 C　第四章')

# ── Write output ──
with open(OUTPUT, 'w', encoding='utf-8') as f:
    f.write(joined)

# ── Mapping log ──
with open(MAPPING_LOG, 'w', encoding='utf-8') as f:
    f.write("Figure renumbering:\n" + "=" * 60 + "\n")
    for (k, old), new in sorted(fig_map.items(), key=lambda x: x[1]):
        f.write(f"  [{k}] 图{old} → 图{new}\n")
    f.write(f"\nTotal figures: {fig_counter}\n\n")

    f.write("Table renumbering:\n" + "=" * 60 + "\n")
    for (k, old), new in sorted(tab_map.items(), key=lambda x: x[1]):
        f.write(f"  [{k}] 表{old} → 表{new}\n")
    f.write(f"\nTotal tables: {tab_counter}\n")

print(f"Output: {OUTPUT}")
print(f"Figures: {fig_counter}")
print(f"Tables: {tab_counter}")
print(f"Fig mappings: {len(fig_map)}")
print(f"Tab mappings: {len(tab_map)}")
print("Done.")
