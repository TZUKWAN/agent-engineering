"""
Post-process merged_report_unified.docx:
1. Remove duplicate title (Heading1 that mirrors Title)
2. Insert page breaks before major sections (chapters, TOC, refs, appendix)
3. Replace TOC placeholder text with actual Word TOC field
"""
import copy
import zipfile
import os
import shutil
import xml.etree.ElementTree as ET
from lxml import etree

NSMAP = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'mc': 'http://schemas.openxmlformats.org/markup-compatibility/2006',
    'wps': 'http://schemas.microsoft.com/office/word/2010/wordprocessingShape',
    'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture',
}

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

def qn(tag):
    """Return Clark notation qualified name."""
    return '{%s}%s' % (W, tag)

def localname(elem):
    """Strip namespace from tag."""
    return elem.tag.split('}', 1)[-1] if '}' in elem.tag else elem.tag


def process_docx(input_path, output_path):
    # Copy the file first (to work with zipfile safely)
    tmp_path = input_path.replace('.docx', '_tmp.docx')
    shutil.copy2(input_path, input_path.replace('.docx', '_backup.docx'))

    # Read the original
    with zipfile.ZipFile(input_path, 'r') as zin:
        doc_xml = zin.read('word/document.xml')
        all_files = {}
        for name in zin.namelist():
            all_files[name] = zin.read(name)

    root = etree.fromstring(doc_xml)
    body = root.find('{%s}body' % W)

    # --- Step 1: Identify and remove duplicate title ---
    # P0 = Title style, P1 = Heading1 with same text → remove the Title one
    paragraphs = body.findall('{%s}p' % W)

    title_para = None
    heading1_paras = []

    for i, p in enumerate(paragraphs):
        pPr = p.find('{%s}pPr' % W)
        if pPr is not None:
            style = pPr.find('{%s}pStyle' % W)
            if style is not None:
                val = style.get('{%s}val' % W)
                if val == 'Title':
                    texts = [t.text or '' for t in p.findall('.//{%s}t' % W)]
                    title_text = ''.join(texts).strip()
                    title_para = (i, p, title_text)
                elif val == 'Heading1':
                    texts = [t.text or '' for t in p.findall('.//{%s}t' % W)]
                    h1_text = ''.join(texts).strip()
                    heading1_paras.append((i, p, h1_text))

    # If Title and first Heading1 have the same text, remove the Title
    if title_para and heading1_paras:
        if title_para[2] == heading1_paras[0][2]:
            body.remove(title_para[1])
            print(f"  Removed duplicate Title paragraph: '{title_para[2][:60]}'")
            # Re-fetch paragraphs
            paragraphs = body.findall('{%s}p' % W)

    # --- Step 2: Insert page breaks before major sections ---
    # Major sections: Heading1 that start a new chapter/appendix/TOC/refs
    MAJOR_HEADINGS = [
        '目录',
        '第一章', '第二章', '第三章', '第四章', '第五章',
        '参考文献',
        '附录',
    ]

    # Also check for "摘要" Heading2 after TOC
    MAJOR_H2 = ['摘要']

    page_breaks_added = 0

    for i, p in enumerate(paragraphs):
        pPr = p.find('{%s}pPr' % W)
        if pPr is None:
            continue
        style = pPr.find('{%s}pStyle' % W)
        if style is None:
            continue
        val = style.get('{%s}val' % W)

        should_break = False

        if val == 'Heading1':
            texts = [t.text or '' for t in p.findall('.//{%s}t' % W)]
            full_text = ''.join(texts).strip()
            for prefix in MAJOR_HEADINGS:
                if full_text.startswith(prefix):
                    should_break = True
                    break

        if should_break:
            # Check if page break already exists before this paragraph
            # Look at previous element's run properties
            prev_idx = list(body).index(p) - 1
            if prev_idx >= 0:
                prev_elem = body[prev_idx]
                # Check if it's a paragraph with page-break-before or has a br
                has_break = False
                for br in prev_elem.findall('.//{%s}br' % W):
                    if br.get('{%s}type' % W) == 'page':
                        has_break = True
                # Check for sectPr or pageBreakBefore
                prev_pPr = prev_elem.find('{%s}pPr' % W)
                if prev_pPr is not None:
                    pbb = prev_pPr.find('{%s}pageBreakBefore' % W)
                    if pbb is not None:
                        has_break = True
                if has_break:
                    continue

            # Insert page break: add <w:r><w:br w:type="page"/></w:r> as last run of previous paragraph
            # Or create a new empty paragraph with page break before
            # Simplest: add pageBreakBefore to the heading's pPr
            pPr = p.find('{%s}pPr' % W)
            if pPr is None:
                pPr = etree.SubElement(p, qn('pPr'))
                p.insert(0, pPr)

            # Check if pageBreakBefore already exists
            existing = pPr.find('{%s}pageBreakBefore' % W)
            if existing is None:
                pbb = etree.SubElement(pPr, qn('pageBreakBefore'))
                pbb.set('{%s}val' % W, 'true')  # Actually pageBreakBefore doesn't take val in strict schema
                # Let's use a run with a br element instead - more reliable
                pPr.remove(pbb)

                # Add a br run to the paragraph itself
                br_run = etree.SubElement(p, qn('r'))
                br = etree.SubElement(br_run, qn('br'))
                br.set('{%s}type' % W, 'page')
                # Move br_run to be the first child of the paragraph
                p.remove(br_run)
                p.insert(0, br_run)

            page_breaks_added += 1
            print(f"  Page break before: '{full_text[:80]}'")

    print(f"  Total page breaks added: {page_breaks_added}")

    # --- Step 3: Replace TOC placeholder with actual TOC field ---
    for i, p in enumerate(paragraphs):
        texts = [t.text or '' for t in p.findall('.//{%s}t' % W)]
        full_text = ''.join(texts)
        if '请在 Word 中右键此处' in full_text and '更新整个目录' in full_text:
            # Replace this paragraph with a real TOC field
            # Clear existing content
            for child in list(p):
                p.remove(child)

            # Create TOC field: complex field with instrText
            # <w:r><w:fldChar w:fldCharType="begin"/></w:r>
            # <w:r><w:instrText>TOC \o "1-3" \h \z \u</w:instrText></w:r>
            # <w:r><w:fldChar w:fldCharType="separate"/></w:r>
            # <w:r><w:t>[目录内容]</w:t></w:r>
            # <w:r><w:fldChar w:fldCharType="end"/></w:r>

            run_begin = etree.SubElement(p, qn('r'))
            fc_begin = etree.SubElement(run_begin, qn('fldChar'))
            fc_begin.set('{%s}fldCharType' % W, 'begin')

            run_instr = etree.SubElement(p, qn('r'))
            instr = etree.SubElement(run_instr, qn('instrText'))
            instr.set('{%s}space' % 'http://www.w3.org/XML/1998/namespace', 'preserve')
            instr.text = ' TOC \\o "1-3" \\h \\z \\u '

            run_sep = etree.SubElement(p, qn('r'))
            fc_sep = etree.SubElement(run_sep, qn('fldChar'))
            fc_sep.set('{%s}fldCharType' % W, 'separate')

            run_text = etree.SubElement(p, qn('r'))
            t = etree.SubElement(run_text, qn('t'))
            t.text = '[请在 Word 中右键此处 → 更新域 → 更新整个目录]'

            run_end = etree.SubElement(p, qn('r'))
            fc_end = etree.SubElement(run_end, qn('fldChar'))
            fc_end.set('{%s}fldCharType' % W, 'end')

            print(f"  Replaced TOC placeholder with real TOC field")
            break

    # --- Write output ---
    doc_xml_out = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zout:
        for name, data in all_files.items():
            if name == 'word/document.xml':
                zout.writestr(name, doc_xml_out)
            else:
                zout.writestr(name, data)

    print(f"\nOutput: {output_path}")
    print(f"Size: {os.path.getsize(output_path):,} bytes")


if __name__ == '__main__':
    INPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'merged_report_unified.docx')
    OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'merged_report_unified.docx')
    process_docx(INPUT, OUTPUT)
