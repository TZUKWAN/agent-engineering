# -*- coding: utf-8 -*-
"""批量将 AIB 包中的 PDF 图转为 PNG（300 DPI，适合打印嵌入 Word）。"""
import os
import sys
from pathlib import Path

import fitz  # PyMuPDF


def pdf_to_png(pdf_path: str, dpi: int = 300) -> str:
    """将单页 PDF 转为 PNG。返回 PNG 路径。"""
    png_path = str(Path(pdf_path).with_suffix(".png"))
    if os.path.isfile(png_path):
        return png_path  # 已有则跳过
    doc = fitz.open(pdf_path)
    page = doc[0]  # 单页图
    mat = fitz.Matrix(dpi / 72, dpi / 72)  # 72 DPI 为基准
    pix = page.get_pixmap(matrix=mat, alpha=False)
    pix.save(png_path)
    doc.close()
    return png_path


def batch_convert(base_dir: str):
    base = Path(base_dir)
    total, done, skip, err = 0, 0, 0, 0
    for d in sorted(base.iterdir()):
        fig_dir = d / "figures"
        if not fig_dir.is_dir():
            continue
        for pdf_file in sorted(fig_dir.glob("*.pdf")):
            total += 1
            png_file = pdf_file.with_suffix(".png")
            if png_file.is_file():
                skip += 1
                continue
            try:
                pdf_to_png(str(pdf_file), dpi=300)
                done += 1
            except Exception as e:
                err += 1
                print(f"  ERROR: {pdf_file.name}: {e}")
    print(f"PDF→PNG: {total} 总计, {done} 转换, {skip} 已存在跳过, {err} 错误")


if __name__ == "__main__":
    base = sys.argv[1] if len(sys.argv) > 1 else r"G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers"
    batch_convert(base)
