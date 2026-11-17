# -*- coding: utf-8 -*-
"""字数统计：CJK 字符 + 英文/数字词 token（Word 口径近似）。"""
import re
import sys
from pathlib import Path


def count(text: str) -> int:
    cjk = len(re.findall(r"[\u4e00-\u9fff\u3400-\u4dbf]", text))
    words = len(re.findall(r"[A-Za-z0-9][A-Za-z0-9._%+\-/]*", text))
    return cjk + words


def main() -> int:
    base = Path(r"G:\刘俊琦\AGENT ENGINEERING")
    rows = []
    for p in sorted((base / "MATLABINTOKEN/revised").glob("paper0[123]_rewritten.md")):
        rows.append((f"MATLAB/{p.name}", count(p.read_text(encoding="utf-8"))))
    for i in (4, 5):
        d = base / f"MATLABINTOKEN/paper0{i}_reasoning_typology" if i == 4 else base / f"MATLABINTOKEN/paper05_prompt_risk_failure"
        f = d / "manuscript.md"
        rows.append((f"MATLAB/paper0{i}_manuscript.md", count(f.read_text(encoding="utf-8"))))
    for d in sorted((base / "agentic-information-behavior/papers").iterdir()):
        if not d.is_dir():
            continue
        cn = d / "paper_cn.md"
        en = d / "paper.md"
        # 中文稿优先；标注实际统计的是哪个文件
        f = cn if cn.is_file() else en
        if f.is_file():
            rows.append((f"AIB/{d.name} [{f.name}]", count(f.read_text(encoding="utf-8"))))
    short = 0
    for name, n in rows:
        flag = "OK " if n >= 9000 else "LOW"
        if n < 9000:
            short += 1
        print(f"{flag} {n:6d}  {name}")
    print(f"\n{len(rows)} papers, {short} below 9000")
    return 0


if __name__ == "__main__":
    sys.exit(main())
