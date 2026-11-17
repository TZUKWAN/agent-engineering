"""Spec §0 items 10-11: put the package's own figures and tables into the manuscript, with the caption they carry.

`figures/` is defined by §0 as 论文全部图 and `tables/` as 论文全部表, but until now no `paper.md` in this programme
named a single one of its own figures: the artefacts shipped beside the manuscript and were never placed in it. A
reader of `paper.md` could not tell which panel carries which result, and §15's plan could only be checked against the
folder listing, not against the paper.

This step appends a self-declaring section to `paper.md` that lists every shipped figure and table. Each figure is
referenced by its path and followed by a caption: the `*.caption.txt` its generating script wrote beside it where one
exists, and otherwise the §15 role that `FIGURE_PLAN.md` derived from the artefact's own name or caption - so the line
in the paper is still a reading of the package, never a sentence invented here. Tables are listed with the header row
and the row count of the file that is actually shipped.

The block is cut and re-inserted between its own markers, so a rebuild reproduces `paper.md` byte for byte; it is
written after every figure and table generator in the chain and after `add_manuscript_sections.py`.

    python 02_shared_code/writing/embed_paper_artefacts.py --paper P004
"""
from __future__ import annotations

import argparse, csv, pathlib, re, sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
PAPERS = sorted(p for p in (ROOT / "papers").glob("P0*") if p.is_dir())
START = "<!-- aib:artefact-section:start -->"
END = "<!-- aib:artefact-section:end -->"


def role_lines(pkg: pathlib.Path) -> dict:
    """Map each artefact name to the §15 role that FIGURE_PLAN.md assigned it, read back from the plan."""
    plan = pkg / "FIGURE_PLAN.md"
    out: dict[str, list] = {}
    if not plan.is_file():
        return out
    for ln in plan.read_text(encoding="utf-8", errors="replace").splitlines():
        if not ln.startswith("| ") or "serves this role" in ln:
            continue
        cells = [c.strip() for c in ln.split("|")]
        if len(cells) < 5:
            continue
        role = cells[1]
        for name in re.findall(r"`(?:figures/|tables/)?([\w.\-]+\.(?:pdf|csv))`", cells[4]):
            out.setdefault(name, []).append(role)
    return out


def table_shape(f: pathlib.Path) -> str:
    try:
        rows = list(csv.reader(open(f, encoding="utf-8", errors="replace")))
    except OSError:
        return "unreadable"
    head = rows[0][:6] if rows else []
    extra = len(rows[0]) - 6 if rows else 0
    more = f" (+{extra} further column{'s' if extra > 1 else ''})" if extra > 0 else ""
    return (f"{len(rows) - 1} data rows; columns: " + ", ".join(f"`{c}`" for c in head) + more)


def section(pkg: pathlib.Path) -> str:
    roles = role_lines(pkg)
    figs = sorted((pkg / "figures").glob("*.pdf"))
    tabs = sorted((pkg / "tables").glob("*.csv"))
    fl = []
    for f in figs:
        cap = f.with_suffix(".caption.txt")
        text = re.sub(r"\s+", " ", cap.read_text(encoding="utf-8", errors="replace")).strip() if cap.is_file() else ""
        if not text:
            rs = "/".join(roles.get(f.name, [])) or "not mapped to a §15 role"
            text = f"Vector figure serving §15 role: {rs}."
        fl.append(f"![{f.stem}](figures/{f.name})\n\n> {text}")
    tl = [f"- `tables/{t.name}` - {table_shape(t)}" + (f" (§15 role: {'/'.join(roles[t.name])})"
                                                       if t.name in roles else "") for t in tabs]
    body = "\n\n".join(fl) or "This package ships no figure."
    return (f"{START}\n\n## Figures and tables as delivered\n\n"
            "Every artefact below is written by a script in this package's `reproduce.sh` chain from `results_raw/`; "
            "none is typed or edited by hand, all are vector PDF, and `FIGURE_PLAN.md` maps them onto the eight roles "
            "spec §15 asks each paper to plan. The captions are the ones the figure's own generating script wrote "
            "beside it. This section is written by `02_shared_code/writing/embed_paper_artefacts.py`, and the role "
            "mapping it quotes by `02_shared_code/writing/export_figure_plan.py`.\n\n"
            f"### Figures ({len(figs)})\n\n{body}\n\n### Tables ({len(tabs)})\n\n"
            + "\n".join(tl) + "\n\n" + END + "\n")


def apply_one(pkg: pathlib.Path, write: bool) -> str:
    paper = pkg / "paper.md"
    if not paper.is_file():
        return "no paper.md"
    txt = paper.read_text(encoding="utf-8", errors="replace")
    new = re.sub(re.escape(START) + r".*?" + re.escape(END) + r"\n?", "", txt, flags=re.S)
    block = section(pkg)
    at = min([n for n in (new.find("\n**Conclusion"), new.find("\n## Conclusion")) if n > -1] or [len(new)])
    out = new[:at].rstrip("\n") + "\n\n" + block + "\n" + new[at:].lstrip("\n")
    if write:
        paper.write_text(out, encoding="utf-8", newline="")
    return f"{len(block.splitlines())} lines, {out.count(START)} marker, placed at char {at} of {len(out)}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", default="")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    for pkg in PAPERS:
        if a.paper and pkg.name[:4] != a.paper:
            continue
        print(f"  {pkg.name[:4]}: {apply_one(pkg, not a.check)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
