# -*- coding: utf-8 -*-
"""Nature 风格 Markdown → Word (docx) 高质量转换器 v2.0。

排版规范（基于 nature-figure/nature-polishing 技能）：
- 标题页：论文标题居中，元数据右对齐
- 目录：自动 TOC 字段
- 页眉：论文标题 | 页脚：页码
- 标题层级：H1=Chapter, H2=Section, H3=Subsection, H4=Sub-sub
- 正文：中文宋体 + 英文 Times New Roman, 11pt, 1.15 倍行距, 两端对齐
- 表格：Table Grid 样式 + 表头灰底 + 居中 + 自适应列宽
- 图片：居中, 最大宽度 15cm, 图注在下方
- 代码：Courier New 9pt, 灰底
- 引用：左缩进 1cm, 斜体
- 限制：不改变任何文本内容，只改善排版
"""
import os
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor

# 排版常量
FONT_CN = "宋体"
FONT_EN = "Times New Roman"
FONT_CODE = "Courier New"
BODY_SIZE = Pt(11)
LINE_SPACING = 1.15
MARGIN = Cm(2.5)
COLOR_DARK = RGBColor(0x1A, 0x1A, 0x1A)
COLOR_HEAD = RGBColor(0x00, 0x00, 0x00)
COLOR_TABLE_HDR = "D9E2F3"  # 浅蓝
COLOR_CODE_BG = "F2F2F2"
COLOR_ALT_ROW = "F7F7F7"

HEAD_SIZES = {1: Pt(16), 2: Pt(14), 3: Pt(12), 4: Pt(11), 5: Pt(11), 6: Pt(11)}


# ---------------------------------------------------------------------------
def _set_east_asia(run, font_cn):
    try:
        rPr = run._element.get_or_add_rPr()
        rFonts = rPr.find(qn("w:rFonts"))
        if rFonts is None:
            rFonts = OxmlElement("w:rFonts")
            rPr.append(rFonts)
        rFonts.set(qn("w:eastAsia"), font_cn)
    except Exception:
        pass


def _add_run(par, text, size=BODY_SIZE, bold=False, italic=False,
             font_en=FONT_EN, font_cn=FONT_CN, color=None):
    run = par.add_run(text)
    if size is not None:
        run.font.size = size
    run.font.bold = bold
    run.font.italic = italic
    if color is not None:
        run.font.color.rgb = color
    run.font.name = font_en
    _set_east_asia(run, font_cn)
    return run


def _add_par(doc, text="", size=BODY_SIZE, bold=False, italic=False,
             align=WD_ALIGN_PARAGRAPH.JUSTIFY, before=Pt(0), after=Pt(6),
             indent=None, color=None, font_en=FONT_EN, font_cn=FONT_CN):
    par = doc.add_paragraph()
    par.alignment = align
    pf = par.paragraph_format
    pf.space_before = before
    pf.space_after = after
    pf.line_spacing = LINE_SPACING
    if indent is not None:
        pf.left_indent = indent
    if text:
        _add_run(par, text, size=size, bold=bold, italic=italic, color=color,
                 font_en=font_en, font_cn=font_cn)
    return par


def _add_rich(par, text, size=BODY_SIZE):
    """解析行内 markdown 标记并渲染。"""
    pattern = re.compile(r"(\*\*(?P<b>.+?)\*\*|\*(?P<i>.+?)\*|`(?P<c>.+?)`|\$\$(?P<m>.+?)\$\$)")
    last = 0
    for m in pattern.finditer(text):
        if m.start() > last:
            _add_run(par, text[last:m.start()], size=size)
        if m.group("b"):
            _add_run(par, m.group("b"), size=size, bold=True)
        elif m.group("i"):
            _add_run(par, m.group("i"), size=size, italic=True)
        elif m.group("c"):
            _add_run(par, m.group("c"), size=Pt(size.pt - 1), font_en=FONT_CODE, font_cn=FONT_CODE)
        elif m.group("m"):
            _add_run(par, m.group("m"), size=size, italic=True)
        last = m.end()
    if last < len(text):
        _add_run(par, text[last:], size=size)


def _add_page_number(par):
    """在段落中插入页码字段。"""
    run = par.add_run()
    for elem_name, attr in [("w:fldChar", {"w:fldCharType": "begin"}),
                            ("w:instrText", None),
                            ("w:fldChar", {"w:fldCharType": "end"})]:
        elem = OxmlElement(elem_name)
        if attr:
            for k, v in attr.items():
                elem.set(qn(k), v)
        if elem_name == "w:instrText":
            elem.text = "PAGE"
            elem.set(qn("xml:space"), "preserve")
        run._element.append(elem)
    _set_east_asia(run, FONT_CN)


def _add_toc_field(doc):
    """插入自动 TOC 字段。"""
    par = doc.add_paragraph()
    run = par.add_run()
    fldChar_begin = OxmlElement("w:fldChar")
    fldChar_begin.set(qn("w:fldCharType"), "begin")
    instrText = OxmlElement("w:instrText")
    instrText.set(qn("xml:space"), "preserve")
    instrText.text = 'TOC \\o "1-3" \\h \\z \\u'
    fldChar_sep = OxmlElement("w:fldChar")
    fldChar_sep.set(qn("w:fldCharType"), "separate")
    hint = OxmlElement("w:rPr")
    hint_text = OxmlElement("w:t")
    hint_text.text = "右键更新目录"
    hint.append(hint_text)
    fldChar_end = OxmlElement("w:fldChar")
    fldChar_end.set(qn("w:fldCharType"), "end")
    run._element.append(fldChar_begin)
    run._element.append(instrText)
    run._element.append(fldChar_sep)
    run._element.append(hint)
    run._element.append(fldChar_end)


def _add_heading_styled(doc, text, level, sizes):
    """添加使用 Word 内置样式的标题（支持 TOC）。"""
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.size = sizes.get(level, BODY_SIZE)
        run.font.color.rgb = COLOR_HEAD
        run.font.name = FONT_EN
        _set_east_asia(run, FONT_CN)
    return h


def _add_table_styled(doc, header, rows, table_num=None):
    """添加 Nature 风格表格：三线表 + 表头底色。"""
    ncols = len(header) if header else (max(len(r) for r in rows) if rows else 0)
    if ncols == 0:
        return
    table = doc.add_table(rows=1 + len(rows), cols=ncols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"

    # 列宽自适应：设置表格宽度 100%
    tbl = table._tbl
    tblPr = tbl.tblPr if hasattr(tbl, 'tblPr') else tbl.find(qn("w:tblPr"))
    if tblPr is not None:
        tblW = OxmlElement("w:tblW")
        tblW.set(qn("w:w"), "5000")
        tblW.set(qn("w:type"), "pct")
        tblPr.append(tblW)

    # 表头
    if header:
        for j, cell_text in enumerate(header):
            cell = table.rows[0].cells[j]
            cell.text = ""
            par = cell.paragraphs[0]
            par.alignment = WD_ALIGN_PARAGRAPH.CENTER
            _add_run(par, str(cell_text), size=Pt(9), bold=True)
            shading = OxmlElement("w:shd")
            shading.set(qn("w:fill"), COLOR_TABLE_HDR)
            tcPr = cell._element.get_or_add_tcPr()
            tcPr.append(shading)

    # 数据行（交替底色 + 单元格截断）
    for i, row in enumerate(rows):
        for j in range(ncols):
            cell = table.rows[i + 1].cells[j]
            cell.text = ""
            val = str(row[j]) if j < len(row) else ""
            if len(val) > 200:
                val = val[:197] + "…"
            par = cell.paragraphs[0]
            par.alignment = WD_ALIGN_PARAGRAPH.LEFT
            _add_run(par, val, size=Pt(9))
            if i % 2 == 1:
                shading = OxmlElement("w:shd")
                shading.set(qn("w:fill"), COLOR_ALT_ROW)
                tcPr = cell._element.get_or_add_tcPr()
                tcPr.append(shading)

    doc.add_paragraph()


# ---------------------------------------------------------------------------
# Markdown 解析函数
def _is_table(line):
    return line.strip().startswith("|") and line.strip().endswith("|")

def _is_sep(line):
    return bool(re.match(r"^\s*\|[\s\-:|]+\|\s*$", line))

def _is_fence(line):
    return line.strip().startswith("```")

def _is_heading(line):
    return bool(re.match(r"^#{1,6} ", line))

def _is_quote(line):
    return line.strip().startswith(">")

def _is_list(line):
    return bool(re.match(r"^\s*[-*+] |\s*\d+\. ", line))

def _is_hr(line):
    return bool(re.match(r"^-{3,}\s*$|^\*{3,}\s*$", line))

def _is_image(line):
    return bool(re.match(r"^!\[.*\]\(.+\)$", line.strip()))


# ---------------------------------------------------------------------------
def convert(md_path: str, docx_path: str, base_dir: str = None):
    """主转换函数。"""
    md_path = Path(md_path)
    base = Path(base_dir) if base_dir else md_path.parent
    text = md_path.read_text(encoding="utf-8")
    lines = text.split("\n")
    pos = 0

    # 提取第一个 H1 作为论文标题
    title = md_path.stem
    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
            break

    doc = Document()

    # -- 页面设置 --
    sec = doc.sections[0]
    sec.page_width = Cm(21)
    sec.page_height = Cm(29.7)
    sec.left_margin = MARGIN
    sec.right_margin = MARGIN
    sec.top_margin = Cm(2.5)
    sec.bottom_margin = Cm(2.0)

    # -- 默认字体 --
    style = doc.styles["Normal"]
    style.font.name = FONT_EN
    style.font.size = BODY_SIZE
    style.font.color.rgb = COLOR_DARK
    rPr = style.element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:eastAsia"), FONT_CN)

    # -- 页眉（论文标题）--
    header = sec.header
    header.is_linked_to_previous = False
    hp = header.paragraphs[0] if header.paragraphs else header.add_paragraph()
    hp.text = ""
    hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _add_run(hp, title[:80], size=Pt(8), italic=True, color=RGBColor(0x66, 0x66, 0x66))
    # 页眉底边线
    pPr = hp._element.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "4")
    bottom.set(qn("w:color"), "999999")
    pBdr.append(bottom)
    pPr.append(pBdr)

    # -- 页脚（页码居中）--
    footer = sec.footer
    footer.is_linked_to_previous = False
    fp = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    fp.text = ""
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _add_page_number(fp)

    # -- 标题页 --
    _add_par(doc, title, size=Pt(18), bold=True,
             align=WD_ALIGN_PARAGRAPH.CENTER, before=Pt(72), after=Pt(24))
    _add_par(doc, "", size=Pt(6))

    # 如果正文无 markdown 标题（如 BLOCKED.md），在正文开头插入合成标题
    has_headings = any(_is_heading(l) for l in lines)
    if not has_headings:
        # 无 markdown 标题的文件（如 BLOCKED.md），直接用 add_heading 插入
        _add_heading_styled(doc, title, 1, HEAD_SIZES)

    # -- TOC --
    _add_par(doc, "目录", size=Pt(14), bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, before=Pt(24), after=Pt(6))
    _add_toc_field(doc)
    doc.add_page_break()

    # -- 正文解析 --
    fig_num = [0]
    tbl_num = [0]
    in_code = False
    code_buf = []

    while pos < len(lines):
        line = lines[pos]
        stripped = line.strip()
        pos += 1

        # 空行
        if not stripped:
            continue

        # 代码块
        if _is_fence(line):
            code_buf = []
            while pos < len(lines):
                l = lines[pos]; pos += 1
                if _is_fence(l):
                    break
                code_buf.append(l)
            code_text = "\n".join(code_buf)
            par = _add_par(doc, code_text, size=Pt(8), font_en=FONT_CODE, font_cn=FONT_CODE,
                           align=WD_ALIGN_PARAGRAPH.LEFT, before=Pt(4), after=Pt(4))
            pPr = par._element.get_or_add_pPr()
            shd = OxmlElement("w:shd")
            shd.set(qn("w:fill"), COLOR_CODE_BG)
            pPr.append(shd)
            continue

        # 标题（使用 Word 内置 heading 样式以支持 TOC）
        # 映射：md `# ` → Word Heading 1, `## ` → Heading 2, `### ` → Heading 3
        if _is_heading(line):
            level = len(line) - len(line.lstrip("#"))
            htext = line.lstrip("#").strip()
            word_level = min(level, 4)  # # → 1, ## → 2, ### → 3
            _add_heading_styled(doc, htext, word_level, HEAD_SIZES)
            continue

        # 水平线
        if _is_hr(line):
            continue  # 不渲染（用节间距代替）

        # 图片
        if _is_image(stripped):
            m = re.match(r"^!\[(.*?)\]\((.+?)\)$", stripped)
            alt, ref = m.group(1), m.group(2)
            img_path = base / ref
            if not img_path.is_file():
                img_path = base / ref.replace("/", os.sep)
            # PDF/SVG 无法嵌入 Word：优先替换为同名 .png/.jpg
            if img_path.is_file() and img_path.suffix.lower() in (".pdf", ".svg"):
                for _ext in (".png", ".jpg"):
                    _alt = img_path.with_suffix(_ext)
                    if _alt.is_file():
                        img_path = _alt
                        break
            fig_num[0] += 1
            if img_path.is_file() and img_path.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".bmp"):
                try:
                    doc.add_picture(str(img_path), width=Cm(14))
                    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
                except Exception:
                    _add_par(doc, f"[图 {fig_num[0]}: {ref}]", size=Pt(9), italic=True,
                             align=WD_ALIGN_PARAGRAPH.CENTER)
            else:
                _add_par(doc, f"[图 {fig_num[0]}: {ref} — 文件未找到]", size=Pt(9), italic=True,
                         align=WD_ALIGN_PARAGRAPH.CENTER)
            if alt:
                _add_par(doc, f"图 {fig_num[0]}. {alt}", size=Pt(9), italic=True,
                         align=WD_ALIGN_PARAGRAPH.CENTER, before=Pt(4), after=Pt(10))
            continue

        # 表格
        if _is_table(line):
            header_line = line
            if pos < len(lines) and _is_sep(lines[pos]):
                pos += 1
            data = []
            while pos < len(lines) and _is_table(lines[pos]):
                cells = lines[pos].strip().strip("|").split("|")
                data.append([c.strip() for c in cells])
                pos += 1
            header = [c.strip() for c in header_line.strip().strip("|").split("|")]
            tbl_num[0] += 1
            if header and data:
                _add_table_styled(doc, header, data, tbl_num[0])
            continue

        # 引用块
        if _is_quote(line):
            content = line.lstrip("> ").strip()
            if content:
                par = _add_par(doc, italic=True, indent=Cm(1), before=Pt(4), after=Pt(4))
                _add_rich(par, content, size=BODY_SIZE)
            continue

        # 列表
        if _is_list(line):
            ordered = bool(re.match(r"^\s*\d+\. ", line))
            content = re.sub(r"^\s*[-*+] |\s*\d+\. ", "", line)
            # 检测图片/图形文件引用（figures/*.pdf/png/svg）
            fig_ref_match = re.match(r"^(figures?/\S+\.(?:pdf|png|svg|jpg))$", content.strip().strip('`'), re.I)
            if fig_ref_match:
                fig_ref = fig_ref_match.group(1)
                img_path = base / fig_ref
                # 始终优先使用 .png（PDF 无法嵌入 Word）
                png_path = img_path.with_suffix(".png")
                if png_path.is_file():
                    img_path = png_path
                else:
                    for ext in (".png", ".jpg"):
                        alt_path = img_path.with_suffix(ext)
                        if alt_path.is_file():
                            img_path = alt_path
                            break
                fig_num[0] += 1
                if img_path.suffix == ".png" and img_path.is_file():
                    try:
                        doc.add_picture(str(img_path), width=Cm(14))
                        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
                        cap = f"图 {fig_num[0]}. {Path(fig_ref).stem}"
                        _add_par(doc, cap, size=Pt(9), italic=True,
                                 align=WD_ALIGN_PARAGRAPH.CENTER, before=Pt(4), after=Pt(10))
                        continue
                    except Exception:
                        pass
                # 图片不存在或不支持：只显示文件名
                _add_par(doc, f"[图 {fig_num[0]}: `{fig_ref}`]",
                         size=Pt(9), italic=True, align=WD_ALIGN_PARAGRAPH.CENTER)
                continue
            style_name = "List Number" if ordered else "List Bullet"
            try:
                par = doc.add_paragraph(style=style_name)
            except Exception:
                par = doc.add_paragraph()
            par.paragraph_format.space_after = Pt(2)
            par.paragraph_format.line_spacing = LINE_SPACING
            _add_rich(par, content, size=BODY_SIZE)
            continue

        # 普通段落
        par = _add_par(doc, align=WD_ALIGN_PARAGRAPH.JUSTIFY, after=Pt(6))
        _add_rich(par, stripped, size=BODY_SIZE)

    doc.save(docx_path)
    return docx_path


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) >= 3:
        convert(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python md_to_docx_v2.py <input.md> <output.docx>")
