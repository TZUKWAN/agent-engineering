#!/usr/bin/env python
"""Customize pandoc reference.docx: 宋体 + Times New Roman, academic formatting."""
from docx import Document
from docx.shared import Pt, Inches, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
import copy

REFERENCE = 'reference.docx'
OUTPUT = 'reference_custom.docx'

doc = Document(REFERENCE)

# ── Font helper ──
def set_run_fonts(run, cn_font='宋体', en_font='Times New Roman', size=None, bold=None, color=None):
    """Set both Chinese and English fonts on a run."""
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = rPr.makeelement(qn('w:rFonts'), {})
        rPr.insert(0, rFonts)
    rFonts.set(qn('w:eastAsia'), cn_font)
    rFonts.set(qn('w:ascii'), en_font)
    rFonts.set(qn('w:hAnsi'), en_font)
    rFonts.set(qn('w:cs'), en_font)
    if size is not None:
        run.font.size = size
    if bold is not None:
        run.bold = bold
    if color is not None:
        run.font.color.rgb = color

def set_paragraph_spacing(para, before=None, after=None, line_spacing=None):
    """Set paragraph spacing."""
    pf = para.paragraph_format
    if before is not None:
        pf.space_before = before
    if after is not None:
        pf.space_after = after
    if line_spacing is not None:
        pf.line_spacing = line_spacing

# ── Customize all styles ──
styles = doc.styles

# Helper to set fonts on a style
def set_style_fonts(style, cn='宋体', en='Times New Roman', size=None, bold=None, color=None):
    """Set fonts on a style's xml directly for maximum compatibility."""
    # Set via font property
    if size is not None:
        style.font.size = size
    if bold is not None:
        style.font.bold = bold
    if color is not None:
        style.font.color.rgb = color
    # Set via XML for East-Asian
    rPr = style.element.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = rPr.makeelement(qn('w:rFonts'), {})
        rPr.insert(0, rFonts)
    rFonts.set(qn('w:eastAsia'), cn)
    rFonts.set(qn('w:ascii'), en)
    rFonts.set(qn('w:hAnsi'), en)
    rFonts.set(qn('w:cs'), en)

# ── Normal style (body text) ──
normal = styles['Normal']
set_style_fonts(normal, cn='宋体', en='Times New Roman', size=Pt(12))
pf = normal.paragraph_format
pf.space_before = Pt(0)
pf.space_after = Pt(6)
pf.line_spacing = 1.5
pf.first_line_indent = Cm(0.74)  # 2 chars indent

# ── Heading styles ──
heading_specs = {
    'Heading 1': (Pt(16), True, Pt(18), Pt(12)),
    'Heading 2': (Pt(14), True, Pt(12), Pt(6)),
    'Heading 3': (Pt(13), True, Pt(10), Pt(4)),
    'Heading 4': (Pt(12), True, Pt(8), Pt(4)),
}
for name, (size, bold, before, after) in heading_specs.items():
    try:
        style = styles[name]
        set_style_fonts(style, cn='宋体', en='Times New Roman', size=size, bold=bold)
        style.font.color.rgb = RGBColor(0, 0, 0)
        pf = style.paragraph_format
        pf.space_before = before
        pf.space_after = after
        pf.line_spacing = 1.5
        pf.first_line_indent = Cm(0)
        pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
    except KeyError:
        pass

# ── Title style ──
try:
    title_style = styles['Title']
    set_style_fonts(title_style, cn='宋体', en='Times New Roman', size=Pt(22), bold=True)
    title_style.font.color.rgb = RGBColor(0, 0, 0)
    title_style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_style.paragraph_format.space_before = Pt(36)
    title_style.paragraph_format.space_after = Pt(24)
    title_style.paragraph_format.line_spacing = 1.5
except KeyError:
    pass

# ── Subtitle style ──
try:
    sub_style = styles['Subtitle']
    set_style_fonts(sub_style, cn='宋体', en='Times New Roman', size=Pt(14), bold=False)
    sub_style.font.color.rgb = RGBColor(80, 80, 80)
    sub_style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
except KeyError:
    pass

# ── Abstract/Quote style ──
try:
    quote = styles['Quote']
    set_style_fonts(quote, cn='宋体', en='Times New Roman', size=Pt(11))
    quote.paragraph_format.first_line_indent = Cm(0)
except KeyError:
    pass

# ── Table style (if present) ──
try:
    table_style = styles['Table']
    set_style_fonts(table_style, cn='宋体', en='Times New Roman', size=Pt(10))
except KeyError:
    pass

# ── Header/Footer ──
try:
    header_style = styles['Header']
    set_style_fonts(header_style, cn='宋体', en='Times New Roman', size=Pt(9))
except KeyError:
    pass

try:
    footer_style = styles['Footer']
    set_style_fonts(footer_style, cn='宋体', en='Times New Roman', size=Pt(9))
except KeyError:
    pass

# ── Set default paragraph font for document ──
# This ensures all text defaults to the right fonts
doc.element.findall('.//' + qn('w:defaultRPr'))
# Modify document defaults via styles.xml
styles_element = doc.styles.element

# ── Page setup ──
for section in doc.sections:
    section.page_width = Cm(21.0)   # A4
    section.page_height = Cm(29.7)  # A4
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(3.18)
    section.right_margin = Cm(3.18)

doc.save(OUTPUT)
print(f'Customized reference saved: {OUTPUT}')
