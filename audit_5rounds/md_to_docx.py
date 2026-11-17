# -*- coding: utf-8 -*-
"""通用 Markdown → Word (docx) 转换器，Nature 风格排版。
支持：标题层级、段落、粗体/斜体/行内代码、管道表格、图片嵌入、代码块、引用块、有序/无序列表、水平线。
中英文混排：中文用宋体，英文/数字用 Times New Roman。
"""
import io
import os
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, Emu

# ---------------------------------------------------------------------------
# 字体与样式常量
FONT_CN = "宋体"
FONT_EN = "Times New Roman"
FONT_CODE = "Courier New"
BODY_SIZE = Pt(11)
H1_SIZE = Pt(18)
H2_SIZE = Pt(15)
H3_SIZE = Pt(13)
H4_SIZE = Pt(12)
SMALL_SIZE = Pt(9)
LINE_SPACING = 1.15
PAGE_MARGIN = Cm(2.5)


def set_run_font(run, size=None, bold=None, italic=None, font_en=FONT_EN, font_cn=FONT_CN, color=None):
    """设置 run 的中英文字体。python-docx 的 font.name 只影响西文，需要额外设置东亚字体。"""
    if size is not None:
        run.font.size = size
    if bold is not None:
        run.font.bold = bold
    if italic is not None:
        run.font.italic = italic
    if color is not None:
        run.font.color.rgb = color
    run.font.name = font_en
    try:
        r = run._element
        rPr = r.get_or_add_rPr()
        rFonts = rPr.find(qn("w:rFonts"))
        if rFonts is None:
            rFonts = OxmlElement("w:rFonts")
            rPr.append(rFonts)
        rFonts.set(qn("w:eastAsia"), font_cn)
    except Exception:
        pass


def add_styled_paragraph(doc, text="", size=BODY_SIZE, bold=False, italic=False,
                         align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_before=Pt(0), space_after=Pt(6),
                         font_en=FONT_EN, font_cn=FONT_CN, color=None):
    p = doc.add_paragraph()
    p.alignment = align
    pf = p.paragraph_format
    pf.space_before = space_before
    pf.space_after = space_after
    pf.line_spacing = LINE_SPACING
    if text:
        run = p.add_run(text)
        set_run_font(run, size=size, bold=bold, italic=italic, font_en=font_en, font_cn=font_cn, color=color)
    return p


def add_rich_text(paragraph, text, size=BODY_SIZE):
    """解析行内 markdown（粗体、斜体、行内代码）并添加到段落。"""
    # 用正则分割 **bold**、*italic*、`code`
    pattern = re.compile(r"(\*\*(?P<bold>.+?)\*\*|\*(?P<italic>.+?)\*|`(?P<code>.+?)`)")
    last = 0
    for m in pattern.finditer(text):
        if m.start() > last:
            run = paragraph.add_run(text[last:m.start()])
            set_run_font(run, size=size)
        if m.group("bold"):
            run = paragraph.add_run(m.group("bold"))
            set_run_font(run, size=size, bold=True)
        elif m.group("italic"):
            run = paragraph.add_run(m.group("italic"))
            set_run_font(run, size=size, italic=True)
        elif m.group("code"):
            run = paragraph.add_run(m.group("code"))
            set_run_font(run, size=Pt(size.pt - 1), font_en=FONT_CODE, font_cn=FONT_CODE)
        last = m.end()
    if last < len(text):
        run = paragraph.add_run(text[last:])
        set_run_font(run, size=size)


def add_table_from_rows(doc, header, rows, col_widths=None):
    """添加格式化表格。"""
    ncols = len(header) if header else max(len(r) for r in rows) if rows else 0
    if ncols == 0:
        return
    table = doc.add_table(rows=1 + len(rows), cols=ncols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"

    # 表头
    if header:
        for j, cell_text in enumerate(header):
            cell = table.rows[0].cells[j]
            cell.text = ""
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(str(cell_text))
            set_run_font(run, size=Pt(10), bold=True)
            # 表头底色
            shading = OxmlElement("w:shd")
            shading.set(qn("w:fill"), "E8E8E8")
            cell._element.get_or_add_tcPr().append(shading)

    # 数据行
    for i, row in enumerate(rows):
        for j in range(ncols):
            cell = table.rows[i + 1].cells[j]
            cell.text = ""
            val = str(row[j]) if j < len(row) else ""
            p = cell.paragraphs[0]
            run = p.add_run(val)
            set_run_font(run, size=Pt(10))

    # 后间距
    doc.add_paragraph()


def add_image(doc, img_path, caption=None, max_width=Cm(15)):
    """嵌入图片并添加图注。跳过不支持的格式（如 SVG）。"""
    if not os.path.isfile(img_path):
        return
    try:
        doc.add_picture(str(img_path), width=max_width)
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    except Exception:
        add_styled_paragraph(doc, f"[图片: {os.path.basename(img_path)} — 格式不支持嵌入]",
                             size=SMALL_SIZE, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    if caption:
        p = add_styled_paragraph(doc, caption, size=SMALL_SIZE, italic=True,
                                 align=WD_ALIGN_PARAGRAPH.CENTER, space_before=Pt(4), space_after=Pt(10))


# ---------------------------------------------------------------------------
# Markdown 解析器
class MarkdownParser:
    """逐行解析 markdown，产生结构化 token 流。"""

    def __init__(self, text: str):
        self.lines = text.split("\n")
        self.pos = 0

    def peek(self):
        return self.lines[self.pos] if self.pos < len(self.lines) else None

    def next(self):
        line = self.lines[self.pos]
        self.pos += 1
        return line

    def has_more(self):
        return self.pos < len(self.lines)


def is_table_line(line):
    return line.strip().startswith("|") and line.strip().endswith("|")


def is_table_separator(line):
    return bool(re.match(r"^\s*\|[\s\-:|]+\|\s*$", line))


def is_code_fence(line):
    return line.strip().startswith("```")


def is_heading(line):
    return bool(re.match(r"^#{1,6} ", line))


def is_blockquote(line):
    return line.strip().startswith(">")


def is_list_item(line):
    return bool(re.match(r"^\s*[-*+] |\s*\d+\. ", line))


def is_hr(line):
    return bool(re.match(r"^-{3,}\s*$", line)) or bool(re.match(r"^\*{3,}\s*$", line))


def is_image_line(line):
    return bool(re.match(r"^!\[.*\]\(.+\)$", line.strip()))


def extract_image(line):
    m = re.match(r"^!\[(.*?)\]\((.+?)\)$", line.strip())
    return (m.group(1), m.group(2)) if m else (None, None)


# ---------------------------------------------------------------------------
def convert_md_to_docx(md_path: str, docx_path: str, base_dir: str = None):
    """将 markdown 文件转换为 Word 文档。"""
    md_path = Path(md_path)
    if base_dir is None:
        base_dir = str(md_path.parent)

    text = md_path.read_text(encoding="utf-8")
    parser = MarkdownParser(text)

    doc = Document()

    # 页面设置
    section = doc.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.left_margin = PAGE_MARGIN
    section.right_margin = PAGE_MARGIN
    section.top_margin = PAGE_MARGIN
    section.bottom_margin = PAGE_MARGIN

    # 默认字体
    style = doc.styles["Normal"]
    style.font.name = FONT_EN
    style.font.size = BODY_SIZE
    rpr = style.element.find(qn("w:rPr"))
    if rpr is None:
        rpr = OxmlElement("w:rPr")
        style.element.append(rpr)
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), FONT_CN)

    while parser.has_more():
        line = parser.next()
        stripped = line.strip()

        # 空行
        if not stripped:
            continue

        # 代码块
        if is_code_fence(line):
            code_lines = []
            while parser.has_more():
                l = parser.next()
                if is_code_fence(l):
                    break
                code_lines.append(l)
            code_text = "\n".join(code_lines)
            p = add_styled_paragraph(doc, code_text, size=Pt(9),
                                     font_en=FONT_CODE, font_cn=FONT_CODE,
                                     align=WD_ALIGN_PARAGRAPH.LEFT,
                                     space_before=Pt(4), space_after=Pt(4))
            # 代码底色
            shading = OxmlElement("w:shd")
            shading.set(qn("w:fill"), "F5F5F5")
            p._element.get_or_add_pPr().append(shading)
            continue

        # 标题
        if is_heading(line):
            level = len(line) - len(line.lstrip("#"))
            text = line.lstrip("#").strip()
            sizes = {1: H1_SIZE, 2: H2_SIZE, 3: H3_SIZE, 4: H4_SIZE, 5: BODY_SIZE, 6: BODY_SIZE}
            size = sizes.get(level, BODY_SIZE)
            p = add_styled_paragraph(doc, text, size=size, bold=True,
                                     align=WD_ALIGN_PARAGRAPH.LEFT,
                                     space_before=Pt(12 if level <= 2 else 8),
                                     space_after=Pt(6))
            continue

        # 水平线
        if is_hr(line):
            p = doc.add_paragraph()
            pPr = p._element.get_or_add_pPr()
            pBdr = OxmlElement("w:pBdr")
            bottom = OxmlElement("w:bottom")
            bottom.set(qn("w:val"), "single")
            bottom.set(qn("w:sz"), "6")
            bottom.set(qn("w:color"), "AAAAAA")
            pBdr.append(bottom)
            pPr.append(pBdr)
            continue

        # 图片
        if is_image_line(stripped):
            alt, img_ref = extract_image(stripped)
            # 解析相对路径
            img_path = Path(base_dir) / img_ref
            if not img_path.is_file():
                img_path = Path(base_dir) / img_ref.replace("/", os.sep)
            if img_path.is_file():
                add_image(doc, str(img_path), caption=alt if alt else None)
            else:
                add_styled_paragraph(doc, f"[图片未找到: {img_ref}]", size=SMALL_SIZE, italic=True)
            continue

        # 表格
        if is_table_line(line):
            header_line = line
            # 跳过分隔符行
            if parser.has_more() and is_table_separator(parser.peek()):
                parser.next()
            rows = []
            while parser.has_more() and is_table_line(parser.peek()):
                rows.append(parser.next())

            def parse_row(r):
                cells = r.strip().strip("|").split("|")
                return [c.strip() for c in cells]

            header = parse_row(header_line)
            data_rows = [parse_row(r) for r in rows]
            add_table_from_rows(doc, header, data_rows)
            continue

        # 引用块
        if is_blockquote(line):
            content = line.lstrip("> ").strip()
            if content:
                p = add_styled_paragraph(doc, size=BODY_SIZE, italic=True,
                                         align=WD_ALIGN_PARAGRAPH.JUSTIFY,
                                         space_before=Pt(4), space_after=Pt(4))
                p.paragraph_format.left_indent = Cm(1)
                add_rich_text(p, content, size=BODY_SIZE)
            continue

        # 列表项
        if is_list_item(line):
            ordered = bool(re.match(r"^\s*\d+\. ", line))
            content = re.sub(r"^\s*[-*+] |\s*\d+\. ", "", line)
            p = doc.add_paragraph(style="List Bullet" if not ordered else "List Number")
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = LINE_SPACING
            add_rich_text(p, content, size=BODY_SIZE)
            continue

        # 普通段落
        p = add_styled_paragraph(doc, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_before=Pt(0), space_after=Pt(6))
        add_rich_text(p, stripped, size=BODY_SIZE)

    doc.save(docx_path)
    return docx_path


# ---------------------------------------------------------------------------
def batch_convert(paper_dirs, output_dir=None):
    """批量转换目录下的所有 paper.md / manuscript.md。"""
    results = []
    for d in paper_dirs:
        d = Path(d)
        if not d.is_dir():
            continue
        md = d / "paper.md"
        if not md.is_file():
            md = d / "manuscript.md"
        if not md.is_file():
            continue
        out_dir = Path(output_dir) if output_dir else d
        out_name = md.stem + ".docx"
        out_path = out_dir / out_name
        try:
            convert_md_to_docx(str(md), str(out_path), base_dir=str(d))
            results.append((d.name, "OK", str(out_path)))
        except Exception as e:
            results.append((d.name, f"ERROR: {e}", str(out_path)))
    return results


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        convert_md_to_docx(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python md_to_docx.py <input.md> <output.docx>")
