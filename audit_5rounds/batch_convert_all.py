# -*- coding: utf-8 -*-
"""批量转换全部 75 篇论文为 Word（v2：PNG 图嵌入）。"""
import sys
from pathlib import Path

sys.path.insert(0, r"G:\刘俊琦\AGENT ENGINEERING\audit_5rounds")
from md_to_docx_v2 import convert

BASE = Path(r"G:\刘俊琦\AGENT ENGINEERING")
AIB = BASE / "agentic-information-behavior" / "papers"
MAT = BASE / "MATLABINTOKEN"
OUT = BASE / "word_output_v2"
OUT.mkdir(parents=True, exist_ok=True)

results = []

# ---- MATLAB 5 篇 ----
mat_papers = [
    (MAT / "revised" / "paper01_rewritten.md", "MATLAB_paper01_验证显性度与执行终止机制"),
    (MAT / "revised" / "paper02_rewritten.md", "MATLAB_paper02_约束密度的非线性效应"),
    (MAT / "revised" / "paper03_rewritten.md", "MATLAB_paper03_语用结构类型学"),
    (MAT / "paper04_reasoning_typology" / "manuscript.md", "MATLAB_paper04_推理链类型学"),
    (MAT / "paper05_prompt_risk_failure" / "manuscript.md", "MATLAB_paper05_提示风险路径"),
]
for md_path, title in mat_papers:
    if not md_path.is_file():
        results.append((title, "SKIP", ""))
        continue
    out = OUT / f"{title}.docx"
    try:
        convert(str(md_path), str(out), base_dir=str(md_path.parent))
        sz = out.stat().st_size
        results.append((title, f"OK ({sz//1024}KB)", str(out)))
    except Exception as e:
        results.append((title, f"ERROR: {e}", str(out)))

# ---- AIB 70 篇 ----
for d in sorted(AIB.iterdir()):
    if not d.is_dir():
        continue
    name = d.name
    md = d / "paper.md"
    out = OUT / f"AIB_{name}.docx"
    if md.is_file():
        try:
            convert(str(md), str(out), base_dir=str(d))
            sz = out.stat().st_size
            results.append((f"AIB_{name}", f"OK ({sz//1024}KB)", str(out)))
        except Exception as e:
            results.append((f"AIB_{name}", f"ERROR: {e}", str(out)))
    else:
        blocked = d / "BLOCKED.md"
        if blocked.is_file():
            out2 = OUT / f"AIB_{name}_BLOCKED_STATUS.docx"
            try:
                convert(str(blocked), str(out2), base_dir=str(d))
                sz = out2.stat().st_size
                results.append((f"AIB_{name}_BLOCKED", f"OK ({sz//1024}KB)", str(out2)))
            except Exception as e:
                results.append((f"AIB_{name}_BLOCKED", f"ERROR: {e}", str(out)))
        else:
            results.append((f"AIB_{name}", "NO CONTENT", ""))

ok = sum(1 for _, s, _ in results if s.startswith("OK"))
err = sum(1 for _, s, _ in results if s.startswith("ERROR"))
print(f"\n转换完成: {ok} OK / {err} ERROR / 总计 {len(results)}")
for name, status, _ in results:
    flag = "✓" if status.startswith("OK") else "✗"
    print(f"  {flag} {status:<16} {name}")
print(f"\n输出: {OUT}")
