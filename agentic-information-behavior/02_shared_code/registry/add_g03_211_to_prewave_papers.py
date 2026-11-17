"""Give the two pre-wave manuscripts the sections the estate's shared writers already assemble.

P002 and P003 were built before `manuscript_sections.py` existed, so their `paper.md` never received the two blocks
the spec asks every paper to carry: gate G03's one-page positioning and §21.1's statement that the population is
recorded agent data. Both blocks are generated here from artefacts the package already owns - the graded literature
matrix, the SOTA comparison rows, the dataset card - by the same functions the wave packages call, and each is
refused rather than written if its source is missing. Nothing is composed by hand, and re-running changes nothing.

    py -3.11 02_shared_code/registry/add_g03_211_to_prewave_papers.py [--check]
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "writing"))
import manuscript_sections as MS                                              # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
PACKAGES = ("P002_isp_stage_measurement", "P003_metadata_interoperability")
G03_HEAD = "## Positioning in one page (spec gate G03)"


def block_for(pkg: pathlib.Path) -> tuple:
    """(text to add, what was assembled) for one package, or (None, why nothing can be written yet)."""
    parts, meta = [], []
    text = (pkg / "paper.md").read_text(encoding="utf-8", errors="replace")
    g03, why = MS.g03_one_pager(pkg)
    if G03_HEAD not in text:
        if not g03:
            return None, f"G03 refused: {why}"
        parts.append(g03 if g03.startswith("#") else f"{G03_HEAD}\n\n{g03}")
        meta.append(f"G03 ({why})")
    scope, swhy = MS.scope_211(pkg)
    if "Data scope (spec 21.1)" not in text:
        if not scope:
            return None, f"21.1 refused: {swhy}"
        parts.append(scope)
        meta.append(f"21.1 ({swhy})")
    if not parts:
        return None, "both blocks are already in the manuscript"
    return "\n\n".join(parts) + "\n", "; ".join(meta)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report what would be added without writing")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for name in PACKAGES:
        pkg = ROOT / "papers" / name
        body, note = block_for(pkg)
        if body is None:
            print(f"  {name}: nothing written - {note}")
            continue
        if a.check:
            print(f"  {name}: would add {len(body)} chars ({note})")
            continue
        f = pkg / "paper.md"
        text = f.read_text(encoding="utf-8")
        # the blocks belong with the argument, not after the references: insert before the first of the headings
        # that follow the introduction, so the one-pager sits where a reviewer looks for positioning
        m = re.search(r"(?m)^## (?:2|References|§2)\b", text)
        at = m.start() if m else len(text)
        f.write_text(text[:at].rstrip() + "\n\n" + body + "\n" + text[at:], encoding="utf-8")
        print(f"  {name}: paper.md updated ({note})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
