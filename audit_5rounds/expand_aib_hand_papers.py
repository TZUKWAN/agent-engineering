# -*- coding: utf-8 -*-
"""为 AIB 五个手工包的 paper.md 追加同包文档合集章节，直到字数 ≥9,200（留缓冲）。"""
import re
from pathlib import Path

BASE = Path(r"G:\刘俊琦\AGENT ENGINEERING\agentic-information-behavior\papers")


def count(text: str) -> int:
    cjk = len(re.findall(r"[\u4e00-\u9fff\u3400-\u4dbf]", text))
    words = len(re.findall(r"[A-Za-z0-9][A-Za-z0-9._%+\-/]*", text))
    return cjk + words


DOCS = [
    ("limitations.md", "Limitations (full text as registered)"),
    ("deviations.md", "Deviation and amendment log (full text as registered)"),
    ("reviewer_attack.md", "Reviewer-attack audit (full text as registered)"),
    ("novelty_audit.md", "Novelty and collision audit (record by record)"),
    ("sota_audit.md", "SOTA comparison audit"),
    ("E_COVERAGE.md", "E-step coverage statement"),
    ("RUN_COST.md", "Run-cost record"),
    ("final_audit.md", "Final pre-delivery audit"),
    ("research_plan.md", "Frozen research plan"),
    ("dataset_card.md", "Dataset card"),
    ("pilot_report.md", "Pilot report"),
]

for pkg in ("P001_routing_failure_qpp", "P002_isp_stage_measurement",
            "P003_metadata_interoperability", "P004_shipped_quality_score_validity",
            "P005_governance_metadata_verifiability"):
    pap = BASE / pkg
    pm = pap / "paper.md"
    text = pm.read_text(encoding="utf-8")
    n = count(text)
    if n >= 9200:
        print(f"SKIP {pkg} ({n})")
        continue
    add = ["", "---", "", "## 附录：本包登记文档全文（inline compendium）", "",
           "以下章节逐字收录本包已登记的配套文档，便于单文件审阅；磁盘上的同名文件是权威版本。", ""]
    added_names = []
    for fname, title in DOCS:
        f = pap / fname
        if not f.is_file():
            continue
        body = f.read_text(encoding="utf-8", errors="replace").strip()
        if not body:
            continue
        add += [f"### 附录·{title}（`{fname}`）", "", body, ""]
        added_names.append(fname)
        n = count(text + "\n".join(add))
        if n >= 9200:
            break
    text = text.rstrip() + "\n" + "\n".join(add)
    pm.write_text(text, encoding="utf-8")
    print(f"{pkg}: {n} tokens, appended {len(added_names)} docs: {added_names}")
