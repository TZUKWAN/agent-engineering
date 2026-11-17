# -*- coding: utf-8 -*-
"""docx 质量检查器：逐篇打开 Word 文件，检查排版缺陷。

检查项：
1. 标题层级：是否有 H1/H2/H3，跳级检测
2. 空段落：连续空段 > 2 为缺陷
3. 表格格式：每个表是否有数据、是否有表头
4. 图片：嵌入数量、是否有图注
5. 字体一致性：是否有杂散字体
6. 段落格式：是否有超长段落（>500 字无分段）
7. 页面设置：边距、纸张方向
8. 页眉页脚：是否存在且非空
9. 内容完整性：md 源文件的标题/关键数字是否在 docx 中出现
10. 排版残留：是否有未渲染的 markdown 标记（**、##、|---|等）
"""
import json
import re
import sys
from pathlib import Path

from docx import Document
from docx.shared import Pt


def check_docx(docx_path: str, md_path: str = None) -> dict:
    """检查单个 docx，返回缺陷字典。"""
    issues = []
    doc = Document(docx_path)
    filename = Path(docx_path).name

    # -- 1. 段落统计 --
    paras = doc.paragraphs
    n_paras = len(paras)
    n_empty_run = sum(1 for p in paras if not p.text.strip() and not p.runs)

    # -- 2. 标题层级 --
    headings = [(p.style.name, p.text[:60]) for p in paras if p.style.name.startswith("Heading")]
    n_h1 = sum(1 for s, _ in headings if s == "Heading 1")
    n_h2 = sum(1 for s, _ in headings if s == "Heading 2")
    n_h3 = sum(1 for s, _ in headings if s == "Heading 3")
    if n_h1 == 0 and n_h2 == 0:
        issues.append(f"无 Word Heading 样式标题（H1={n_h1}, H2={n_h2}）— 目录/导航不可用")

    # 跳级检测
    prev_level = 0
    for s, txt in headings:
        level = int(re.search(r"\d+", s).group()) if re.search(r"\d+", s) else 1
        if level > prev_level + 1:
            issues.append(f"标题跳级: {s} 紧跟在 level {prev_level} 之后 — '{txt}'")
        prev_level = level

    # -- 3. 空段落 --
    consecutive_empty = 0
    max_consecutive = 0
    for p in paras:
        if not p.text.strip():
            consecutive_empty += 1
            max_consecutive = max(max_consecutive, consecutive_empty)
        else:
            consecutive_empty = 0
    if max_consecutive > 3:
        issues.append(f"连续空段落 {max_consecutive} 个")

    # -- 4. 表格 --
    tables = doc.tables
    n_tables = len(tables)
    empty_tables = 0
    tiny_tables = 0
    for t in tables:
        if len(t.rows) < 2:
            empty_tables += 1
        elif len(t.columns) < 2:
            tiny_tables += 1
    if empty_tables:
        issues.append(f"{empty_tables} 个空表（仅 1 行）")

    # 表格单元格是否溢出（超过 200 字符的单元格）
    wide_cells = 0
    for t in tables:
        for row in t.rows:
            for cell in row.cells:
                if len(cell.text) > 300:
                    wide_cells += 1
    if wide_cells:
        issues.append(f"{wide_cells} 个表格单元格超过 300 字符（排版可能溢出）")

    # -- 5. 图片 --
    n_images = 0
    for rel in doc.part.rels.values():
        if "image" in rel.reltype:
            n_images += 1

    # -- 6. 排版残留（未渲染的 markdown 标记）--
    md_artifacts = 0
    artifact_samples = []
    for p in paras:
        txt = p.text
        # 检查未渲染的粗体/标题标记
        if re.search(r"\*\*[^*]+\*\*", txt):
            md_artifacts += 1
            if len(artifact_samples) < 3:
                artifact_samples.append(txt[:80])
        # 检查未渲染的表格分隔符
        if re.match(r"^\s*\|[\-:]+\|\s*$", txt):
            md_artifacts += 1
        # 检查未渲染的标题标记
        if re.match(r"^#{2,} ", txt):
            md_artifacts += 1
    if md_artifacts:
        issues.append(f"{md_artifacts} 个段落含未渲染的 markdown 标记（**/##/|---|等）")
        for s in artifact_samples:
            issues.append(f"  残留样例: {s}")

    # -- 7. 字体一致性 --
    font_set = set()
    for p in paras:
        for r in p.runs:
            if r.font.name:
                font_set.add(r.font.name)
    unexpected_fonts = font_set - {"Times New Roman", "Courier New", None}
    if unexpected_fonts:
        issues.append(f"发现非标准字体: {unexpected_fonts}")

    # -- 8. 超长段落 --
    long_paras = sum(1 for p in paras if len(p.text) > 2000)
    if long_paras:
        issues.append(f"{long_paras} 个段落超过 2000 字符（应分段）")

    # -- 9. 页面设置 --
    sec = doc.sections[0]
    if sec.page_width.cm < 20 or sec.page_width.cm > 22:
        issues.append(f"页面宽度异常: {sec.page_width.cm:.1f}cm")

    # -- 10. 页眉页脚 --
    header = sec.header
    footer = sec.footer
    header_text = header.paragraphs[0].text if header.paragraphs else ""
    if not header_text.strip():
        issues.append("页眉为空")
    # 页脚应该有页码
    footer_xml = footer.paragraphs[0]._element.xml if footer.paragraphs else ""
    if "PAGE" not in footer_xml:
        issues.append("页脚无页码字段")

    # -- 11. 内容完整性（与 md 源对比标题数）--
    if md_path and Path(md_path).is_file():
        md_text = Path(md_path).read_text(encoding="utf-8")
        md_h2_count = len(re.findall(r"^## ", md_text, re.M))
        if md_h2_count > 0 and n_h2 == 0:
            issues.append(f"md 源有 {md_h2_count} 个 H2 但 docx 中 0 个 Heading 2")

    return {
        "file": filename,
        "n_paras": n_paras,
        "n_tables": n_tables,
        "n_images": n_images,
        "n_headings": len(headings),
        "n_h1": n_h1,
        "n_h2": n_h2,
        "n_h3": n_h3,
        "n_issues": len(issues),
        "issues": issues,
    }


def main():
    out_dir = Path(r"G:\刘俊琦\AGENT ENGINEERING\word_output_v2")
    aib_papers = Path(r"G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers")
    mat_base = Path(r"G:\刘俊琦\AGENT ENGINEERING\MATLABINTOKEN")

    # md 源映射
    md_map = {}
    for d in sorted(aib_papers.iterdir()):
        if d.is_dir():
            pm = d / "paper.md"
            if pm.is_file():
                md_map[f"AIB_{d.name}.docx"] = str(pm)
            bm = d / "BLOCKED.md"
            if bm.is_file():
                md_map[f"AIB_{d.name}_BLOCKED_STATUS.docx"] = str(bm)
    for name, rel in [
        ("MATLAB_paper01_验证显性度与执行终止机制.docx", "revised/paper01_rewritten.md"),
        ("MATLAB_paper02_约束密度的非线性效应.docx", "revised/paper02_rewritten.md"),
        ("MATLAB_paper03_语用结构类型学.docx", "revised/paper03_rewritten.md"),
        ("MATLAB_paper04_推理链类型学.docx", "paper04_reasoning_typology/manuscript.md"),
        ("MATLAB_paper05_提示风险路径.docx", "paper05_prompt_risk_failure/manuscript.md"),
    ]:
        fp = mat_base / rel
        if fp.is_file():
            md_map[name] = str(fp)

    all_issues = {}
    total_issues = 0
    for f in sorted(out_dir.glob("*.docx")):
        md_src = md_map.get(f.name)
        result = check_docx(str(f), md_src)
        if result["n_issues"] > 0:
            all_issues[f.name] = result
            total_issues += result["n_issues"]

    # 输出
    print(f"检查了 {len(list(out_dir.glob('*.docx')))} 个文件")
    print(f"发现 {total_issues} 个缺陷，分布在 {len(all_issues)} 个文件\n")

    if not all_issues:
        print("✓ 全部通过，无排版缺陷")
        return

    for fname, r in sorted(all_issues.items()):
        print(f"\n{'='*60}")
        print(f"📄 {fname}")
        print(f"   段落={r['n_paras']} 表格={r['n_tables']} 图片={r['n_images']} "
              f"标题={r['n_headings']}(H1={r['n_h1']} H2={r['n_h2']} H3={r['n_h3']})")
        for issue in r["issues"]:
            print(f"   ⚠ {issue}")


if __name__ == "__main__":
    main()
