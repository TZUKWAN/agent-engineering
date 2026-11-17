import os
#!/usr/bin/env python
r"""Convert merged_report.md → merged_report.tex for XeLaTeX + ctexrep.

Features:
  - Title page (covers title, subtitle, abstract separate from body)
  - #→\chapter, ##→\section, ###→\subsection, ####→\subsubsection
  - ![cap](path) → \begin{figure}[htbp]...
  - Markdown tables → three-line tables (booktabs)
  - Numbered lists → \begin{enumerate}...\end{enumerate}
  - Bullet lists → \begin{itemize}...\end{itemize}
  - Inline $...$ preserved; $$...$$ → \[...\]
  - **bold** → \textbf; *italic* → \emph
  - \newpage kept; Word-only instructions removed
  - \begin{thebibliography} for references
  - \appendix for appendix chapters
"""

import re, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
INPUT = os.path.join(BASE, 'merged_report_unified.md')
OUTPUT = os.path.join(BASE, 'merged_report_unified.tex')
DEBUG = '--debug' in sys.argv

# ──────────────────────────────────────────────
#  Preamble
# ──────────────────────────────────────────────

PREAMBLE = r"""% !TEX program = xelatex
% 用户指令语用特征对任务型交互智能体执行效果的影响
% 基于 AgentNet 大规模 GUI 交互轨迹数据的实证研究三部曲

\documentclass[12pt,a4paper,openany,oneside]{ctexrep}

% ── Font & Encoding ──
\setCJKmainfont{SimSun}
\setCJKsansfont{SimHei}
\setCJKmonofont{KaiTi}
\setmainfont{Times New Roman}
\setsansfont{Arial}
\setmonofont{Courier New}

% ── Page Layout ──
\usepackage[paper=a4paper,
            top=2.54cm,
            bottom=2.54cm,
            left=3.18cm,
            right=3.18cm]{geometry}

% ── Spacing ──
\usepackage{setspace}
\onehalfspacing
\setlength{\parindent}{2em}

% ── Headers & Footers ──
\usepackage{fancyhdr}
\setlength{\headheight}{27pt}
\addtolength{\topmargin}{-12pt}
\pagestyle{fancy}
\fancyhf{}
\fancyhead[C]{\small\kaishu\leftmark}
\fancyfoot[C]{\thepage}
\renewcommand{\headrulewidth}{0.4pt}

% ── Tables ──
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{threeparttable}
\usepackage{adjustbox}
\usepackage{array}
\newcommand{\tabindent}{0.5em}

% ── Graphics ──
\usepackage{graphicx}
\usepackage{float}

% ── Math ──
\usepackage{amsmath}
\usepackage{amssymb}

% ── Captions ──
\usepackage{caption}
\captionsetup[figure]{
  font=small,
  labelfont=bf,
  justification=centering,
  skip=6pt
}
\captionsetup[table]{
  font=small,
  labelfont=bf,
  justification=centering,
  skip=6pt,
  position=above
}

% ── Hyperlinks ──
\usepackage[colorlinks=true,
            linkcolor=blue,
            citecolor=blue,
            urlcolor=blue]{hyperref}

% ── Lists ──
\usepackage{enumitem}
\setlist{nosep, leftmargin=2em, itemsep=2pt, parsep=2pt}

% ── TOC ──
\usepackage{tocbibind}
\setcounter{tocdepth}{3}

% ── Miscellaneous ──
\usepackage{xcolor}
\usepackage{csquotes}

% ── Document Info ──
\title{用户指令语用特征对任务型交互智能体执行效果的影响}
\author{}
\date{\\today}
"""

TITLE_PAGE = r"""
% ────────────────────────────────────
%  Cover / Title Page
% ────────────────────────────────────

\begin{titlepage}
\thispagestyle{empty}

\begin{center}

\vspace*{4cm}

{\zihao{0}\heiti 用户指令语用特征对\\[6pt]
任务型交互智能体执行效果的影响}

\vspace{20pt}

{\zihao{3}\kaishu —— 基于 AgentNet 大规模 GUI 交互轨迹数据的\\[4pt]
实证研究三部曲}

\vspace{40pt}

{\zihao{4}}
\vfill

{\zihao{4}\today}

\end{center}

\end{titlepage}

% ── TOC ──
\chapter*{综合摘要}
\tableofcontents
\newpage
"""


# ──────────────────────────────────────────────
#  Table helpers
# ──────────────────────────────────────────────

def is_table_sep(line):
    s = line.strip()
    if not (s.startswith('|') and s.endswith('|')):
        return False
    inner = s[1:-1]
    return all(
        set(part.strip()).issubset({'-', ':', ' '})
        for part in inner.split('|')
    )


def is_table_row(line):
    s = line.strip()
    return s.startswith('|') and s.endswith('|') and s.count('|') >= 2 and not is_table_sep(s)


def split_row(line):
    s = line.strip()
    if s.startswith('|'): s = s[1:]
    if s.endswith('|'):   s = s[:-1]
    cells, cur = [], []
    in_math = False
    for ch in s:
        if ch == '$':
            in_math = not in_math
            cur.append(ch)
        elif ch == '|' and not in_math:
            cells.append(''.join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    cells.append(''.join(cur).strip())
    return cells


def is_numeric(cell):
    t = cell.strip()
    if not t:
        return False
    t = re.sub(r'\$[^$]+\$', '0', t)
    t = re.sub(r'\*\*[^*]+\*\*', '', t)
    t = t.strip()
    if not t:
        return False
    if re.match(r'^[\d.,{}\s\-–—<>%\[\]]+$', t):
        return True
    if re.match(r'^[\d.,%\-–—\s\[\]]+$', t):
        return True
    return False


def col_aligns(header, rows):
    aligns = []
    for ci in range(len(header)):
        n_num = sum(1 for r in rows if ci < len(r) and r[ci].strip() and is_numeric(r[ci]))
        n_tot = sum(1 for r in rows if ci < len(r) and r[ci].strip())
        aligns.append('r' if (n_tot > 0 and n_num / n_tot > 0.6) else 'l')
    return aligns


def fmt_cell(c):
    parts = re.split(r'(\$[^$]+\$)', c)
    out = []
    for i, p in enumerate(parts):
        if i % 2 == 0:
            p = p.replace('&', '\\&')
            p = p.replace('%', '\\%')
            p = p.replace('#', '\\#')
            p = re.sub(r'(?<!\\)_', r'\\_', p)
            p = re.sub(r'\*\*(.+?)\*\*', r'\\textbf{\1}', p)
            p = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'\\emph{\1}', p)
        out.append(p)
    return ''.join(out)


def md_table_to_tex(lines, start, caption=None):
    tbl = []
    idx = start
    while idx < len(lines):
        s = lines[idx].strip()
        if s == '':
            # Empty line between table rows — skip but stay in table
            idx += 1; continue
        if s.startswith('|') and s.endswith('|') and s.count('|') >= 2:
            tbl.append(lines[idx]); idx += 1
        else:
            break
    if len(tbl) < 2:
        return None, start

    header = split_row(tbl[0])
    sep_i = None
    for i in range(1, len(tbl)):
        if is_table_sep(tbl[i]):
            sep_i = i; break
    if sep_i is None:
        return None, start
    rows = []
    for i in range(sep_i + 1, len(tbl)):
        c = split_row(tbl[i])
        while len(c) < len(header): c.append('')
        rows.append(c[:len(header)])
    if not rows:
        return None, start

    aligns = col_aligns(header, rows)
    colspec = ' '.join(aligns)

    out = []
    out.append(r'\begin{table}[htbp]')
    out.append(r'\centering')
    if caption:
        # Escape special chars in caption (but keep LaTeX math)
        cap_escaped = caption.replace('%', '\\%').replace('#', '\\#').replace('&', '\\&')
        cap_escaped = re.sub(r'(?<!\\)_', r'\\_', cap_escaped)
        out.append(r'\caption{' + cap_escaped + r'}')
    out.append(r'\small')
    out.append(r'\adjustbox{max width=\textwidth}{')
    out.append(r'\begin{tabular}{' + colspec + r'}')
    out.append(r'\toprule')
    out.append(' & '.join(fmt_cell(c) for c in header) + r' \\')
    out.append(r'\midrule')
    for r in rows:
        out.append(' & '.join(fmt_cell(c) for c in r) + r' \\')
    out.append(r'\bottomrule')
    out.append(r'\end{tabular}')
    out.append(r'}')  # close adjustbox
    out.append(r'\end{table}')
    return '\n'.join(out), idx


# ──────────────────────────────────────────────
#  Text helpers
# ──────────────────────────────────────────────

def convert_inline(text):
    """Convert **bold** and *italic* in a single line (outside $...$)."""
    parts = re.split(r'(\$[^$]+\$)', text)
    out = []
    for i, p in enumerate(parts):
        if i % 2 == 0:
            # Escape LaTeX special chars BEFORE bold/italic (so \textbf{%} stays escaped)
            p = p.replace('%', '\\%')
            p = p.replace('#', '\\#')
            p = p.replace('&', '\\&')
            p = re.sub(r'(?<!\\)_', r'\\_', p)
            p = re.sub(r'\*\*(.+?)\*\*', r'\\textbf{\1}', p)
            p = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'\\emph{\1}', p)
        out.append(p)
    return ''.join(out)


def is_numbered_item(line):
    return bool(re.match(r'^\d+[.)]\s', line.strip()))


def is_bullet_item(line):
    return bool(re.match(r'^[-*]\s', line.strip()))


def looks_like_ref(line):
    s = line.strip()
    if not s:
        return False
    return bool(re.match(r'^[A-Z][a-z]+,\s+[A-Z]\.', s))


def ref_key(text):
    m = re.match(r'^([A-Z][a-z]+)', text)
    author = m.group(1).lower() if m else 'anon'
    ym = re.search(r'\((\d{4})\)', text)
    year = ym.group(1) if ym else '0000'
    return f'{author}{year}'


# ──────────────────────────────────────────────
#  Main converter – state-machine driven
# ──────────────────────────────────────────────

def convert(md_text):
    lines = md_text.split('\n')
    tex = []
    i = 0; n = len(lines)

    # ── Headings that should NOT appear in the LaTeX body ──
    SKIP_H1 = frozenset({
        '用户指令语用特征对任务型交互智能体执行效果的影响',
    })

    # ── State ──
    in_bibliography = False     # inside \begin{thebibliography}...\end{thebibliography}
    in_enum = False             # inside \begin{enumerate}...\end{enumerate}
    in_itemize = False          # inside \begin{itemize}...\end{itemize}
    skip_heading = True         # first real chapter not yet seen → skip preamble material
    last_was_list_item = False  # track for closing lists on blank-line boundaries

    def close_enum():
        nonlocal in_enum, last_was_list_item
        if in_enum:
            tex.append(r'\end{enumerate}')
            tex.append('')
            in_enum = False
            last_was_list_item = False

    def close_itemize():
        nonlocal in_itemize, last_was_list_item
        if in_itemize:
            tex.append(r'\end{itemize}')
            tex.append('')
            in_itemize = False
            last_was_list_item = False

    def close_all_lists():
        close_enum()
        close_itemize()

    def close_bibliography():
        nonlocal in_bibliography
        if in_bibliography:
            tex.append(r'\end{thebibliography}')
            tex.append('')
            in_bibliography = False

    pending_caption = None  # for table captions detected before the table

    while i < n:
        raw = lines[i]
        s = raw.strip()

        # ── \newpage ──
        if s == '\\newpage':
            close_all_lists()
            tex.append('\\newpage')
            i += 1; continue

        # ── --- separator (blank in tex) ──
        if s == '---':
            tex.append('')
            i += 1; continue

        # ── Word-only instructions ──
        if 'Word' in s and ('更新' in s or '右键' in s):
            i += 1; continue

        # ── Table caption (**表 X：...** or **表 X ...**) ──
        m_cap = re.match(r'^\*\*表\s*(\d+)[：\s、]+(.+?)\*\*$', s)
        if m_cap:
            pending_caption = f'表 {m_cap.group(1)}：{m_cap.group(2)}'
            i += 1; continue

        # ── Markdown table ──
        if is_table_row(s) and not is_table_sep(s):
            # Look ahead past empty lines for the separator row
            j = i + 1
            while j < n and lines[j].strip() == '':
                j += 1
            if j < n and is_table_sep(lines[j]):
                close_all_lists()
                close_bibliography()
                tex_table, ni = md_table_to_tex(lines, i, pending_caption)
                if tex_table:
                    tex.append(tex_table)
                    tex.append('')
                    pending_caption = None
                    i = ni; continue
                # fall through: table parsing failed, handle as normal text

        # ── Headings ──
        if s.startswith('#'):
            close_all_lists()

            level = len(raw) - len(raw.lstrip('#'))
            heading_text = raw.lstrip('#').strip()

            # -- Skip document title (# …) --
            if heading_text in SKIP_H1:
                i += 1; continue

            # -- Skip subtitle (## —— …) --
            if level == 2 and (heading_text.startswith('——') or heading_text.startswith('——')):
                i += 1; continue

            # -- Skip "## 综合摘要" (body is rendered by title page) --
            if level == 2 and heading_text == '综合摘要':
                i += 1
                # Eat the abstract body until next `---`, `\newpage`, or `#` heading
                while i < n:
                    ns = lines[i].strip()
                    if ns.startswith('#') or ns == '---' or ns == '\\newpage':
                        break
                    i += 1
                continue

            # -- Skip "# 目录" (LaTeX TOC is auto-generated) --
            if level == 1 and heading_text == '目录':
                i += 1
                while i < n:
                    ns = lines[i].strip()
                    if ns.startswith('#') or ns == '\\newpage':
                        break
                    i += 1
                continue

            # -- First "real" chapter → clear skip_heading flag --
            skip_heading = False

            # -- "# 参考文献" → enter thebibliography --
            if level == 1 and heading_text == '参考文献':
                close_bibliography()
                in_bibliography = True
                tex.append(r'\begin{thebibliography}{99}')
                tex.append('')
                i += 1; continue

            # -- Inside bibliography: sub-headings close it first --
            if in_bibliography and level >= 2:
                close_bibliography()
                # fall through to normal heading processing

            # -- "# 附录" (standalone appendix heading after refs) --
            if level == 1 and heading_text == '附录':
                close_bibliography()
                tex.append(r'\appendix')
                tex.append(r'\chapter{附录}')
                tex.append('')
                i += 1; continue

            # -- Detect table captions in headings (### 表 X　..., #### 表 A1　...) --
            m_tab_head = re.match(r'^表\s*([A-Z]?\d+)\s*[　\s]+(.+)', heading_text)
            if m_tab_head and level >= 3:
                pending_caption = f'表 {m_tab_head.group(1)}：{m_tab_head.group(2)}'

            # -- Normal heading mapping --
            mapping = {1: 'chapter', 2: 'section', 3: 'subsection', 4: 'subsubsection'}
            cmd = mapping.get(level, 'paragraph')

            # Strip "第X章" / "第X部分" prefix for chapter headings to avoid
            # duplicate numbering (ctexrep auto-prepends "第一章" etc.)
            if level == 1:
                heading_text = re.sub(r'^第[一二三四五六七八九十百]+[章节部分][　\s]*', '', heading_text)

            # Strip "附录 X" prefix for section headings to avoid
            # duplicate numbering (ctexrep auto-prepends "A"/"B"/"C" in appendix)
            if level == 2:
                heading_text = re.sub(r'^附录\s+[A-Z]\s*[　\s]+', '', heading_text)

            tex.append(f'\\{cmd}{{{heading_text}}}')
            tex.append('')
            i += 1; continue

        # ── Inside bibliography mode ──
        if in_bibliography:
            if not s:
                tex.append('')
                i += 1; continue
            if looks_like_ref(s):
                tex.append(f'\\bibitem{{{ref_key(s)}}} {convert_inline(s)}')
            elif s.startswith('- ') or s.startswith('* '):
                # File listing inside refs area → close bib, reprocess
                close_bibliography()
                continue  # reprocess this line
            elif is_numbered_item(s):
                close_bibliography()
                continue
            elif is_table_row(s):
                jb = i + 1
                while jb < n and lines[jb].strip() == '':
                    jb += 1
                if jb < n and is_table_sep(lines[jb]):
                    close_bibliography()
                    continue
            elif s.startswith('#'):
                # Sub-heading inside refs area → close bib, reprocess
                close_bibliography()
                continue
            else:
                # Non-ref text inside bibliography → just append as-is
                tex.append(convert_inline(s))
            i += 1; continue

        # ── Empty line ──
        if not s:
            if in_enum or in_itemize:
                # Look ahead: next non-empty determines whether list continues
                j = i + 1
                while j < n and not lines[j].strip():
                    j += 1
                if j < n:
                    ns = lines[j].strip()
                    if in_enum and not is_numbered_item(ns):
                        close_enum()
                    if in_itemize and not is_bullet_item(ns) and not is_numbered_item(ns):
                        close_itemize()
            tex.append('')
            i += 1; continue

        # ── Display math $$...$$ (single or multi-line) ──
        if s == '$$':
            close_all_lists()
            i += 1
            math_lines = []
            while i < n:
                ms = lines[i].strip()
                if ms == '$$':
                    break
                math_lines.append(lines[i])
                i += 1
            tex.append('\\[')
            tex.extend(math_lines)
            tex.append('\\]')
            tex.append('')
            i += 1; continue

        # ── Images ![caption](path) ──
        m = re.match(r'^!\[(.*?)\]\((.*?)\)$', s)
        if m:
            close_all_lists()
            cap = m.group(1)
            path = m.group(2)
            full = os.path.join(BASE, path)
            if DEBUG and not os.path.exists(full):
                print(f'  WARNING: image not found: {full}')
            tex.append(r'\begin{figure}[htbp]')
            tex.append(r'\centering')
            tex.append(r'\includegraphics[width=0.92\textwidth]{' + path + r'}')
            tex.append(r'\caption{' + cap + r'}')
            tex.append(r'\end{figure}')
            tex.append('')
            i += 1; continue

        # ── Numbered item (1. text or 1) text) ──
        if is_numbered_item(s):
            close_itemize()
            m2 = re.match(r'^(\d+)[.)]\s+(.+)$', s)
            if m2:
                if not in_enum:
                    tex.append(r'\begin{enumerate}')
                    in_enum = True
                content = convert_inline(m2.group(2))
                tex.append(f'\\item[{m2.group(1)}.] {content}')
                last_was_list_item = True
            i += 1; continue

        # ── Bullet item (- text or * text) ──
        if is_bullet_item(s):
            close_enum()
            content = s[1:].strip()
            if not in_itemize:
                tex.append(r'\begin{itemize}')
                in_itemize = True
            tex.append(f'\\item {convert_inline(content)}')
            last_was_list_item = True
            i += 1; continue

        # ── Regular text ──
        close_all_lists()
        tex.append(convert_inline(s))
        i += 1

    # ── Flush remaining environments ──
    close_all_lists()
    close_bibliography()

    return '\n'.join(tex)


# ──────────────────────────────────────────────
#  Post-process
# ──────────────────────────────────────────────

def postprocess(tex_body):
    # Collapse 3+ blank lines → 2
    tex_body = re.sub(r'\n{4,}', '\n\n\n', tex_body)
    # Remove trailing whitespace
    tex_body = re.sub(r'[ \t]+$', '', tex_body, flags=re.MULTILINE)
    return tex_body


def assemble(body):
    return '\n'.join([
        PREAMBLE,
        r'\begin{document}',
        TITLE_PAGE,
        body,
        '',
        r'\end{document}',
    ])


# ──────────────────────────────────────────────
#  Main
# ──────────────────────────────────────────────

def main():
    print('Reading merged_report.md ...')
    md = open(INPUT, encoding='utf-8').read()
    print(f'  {len(md)} chars, {len(md.splitlines())} lines')

    print('Converting ...')
    body = convert(md)
    body = postprocess(body)
    final = assemble(body)

    open(OUTPUT, 'w', encoding='utf-8').write(final)
    print(f'\nWritten: {OUTPUT}')
    print(f'  {len(final)} chars, {len(final.splitlines())} lines')

    # Quick stats
    for tag, pat in [
        ('\\chapter{',    r'\\chapter\{'),
        ('\\chapter*{',   r'\\chapter\*\{'),
        ('\\section{',    r'\\section\{'),
        ('\\subsection{', r'\\subsection\{'),
        ('\\begin{figure}',   r'\\begin\{figure\}'),
        ('\\begin{table}',    r'\\begin\{table\}'),
        ('\\begin{tabular}',  r'\\begin\{tabular\}'),
        ('\\bibitem{',        r'\\bibitem\{'),
        ('\\begin{enumerate}', r'\\begin\{enumerate\}'),
        ('\\begin{itemize}',   r'\\begin\{itemize\}'),
    ]:
        cnt = len(re.findall(pat, final))
        print(f'  {tag}: {cnt}')


if __name__ == '__main__':
    main()
