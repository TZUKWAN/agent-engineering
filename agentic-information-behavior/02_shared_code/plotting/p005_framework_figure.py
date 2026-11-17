"""Spec §15 item 1 for P005: the research framework figure the package did not ship.

P005 opens with a level ladder, a component-coverage panel, a reference-host panel and a lexicon-sensitivity panel - all
results - but nothing that shows the design those results come out of, so `export_figure_plan.py` reported §15 item 1
as "no figure serves this role". This step draws that diagram from the package's own frozen documents rather than from
a description written here:

* the seven evidence levels and their definitions are parsed from the level table in `protocol_freeze.md`, and grouped
  into read sites by the words that definition itself uses (card front matter, repository root, record/column level,
  container metadata);
* the counts on the left of the diagram are the sums of `results_processed/EXP0049_level_census.csv` - releases read,
  files seen, parquet footers opened, named components, components carrying a rights statement;
* the per-level depth in the middle is the number of releases with a declaration at that level, from the same census;
* the boxes on the right are the hypotheses and their verdicts as recorded in `tables/table7_hypothesis_verdicts.csv`.

Nothing in the figure is typed: if a source file is absent the script stops instead of drawing a diagram with invented
labels.

    python 02_shared_code/plotting/p005_framework_figure.py
"""
from __future__ import annotations

import csv, pathlib, re, sys, textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

plt.rcParams.update({"svg.hashsalt": "aib", "font.size": 7.5, "figure.dpi": 150, "savefig.bbox": "tight"})

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
PKG = next(p for p in sorted((ROOT / "papers").glob("P005*")) if p.is_dir())
PROC, FIG = PKG / "results_processed", PKG / "figures"
PDF_META = {"CreationDate": None, "ModDate": None, "Producer": "aib plotting"}

# a level belongs to the read site its own definition names first; the order below is the order the protocol lists.
SITE_OF = [("card front matter / card body", ("front matter", "front-matter", "card body")),
           ("repository root and tree", ("repository root", "anywhere in the tree")),
           ("record / column level", ("record/column", "record level", "column names")),
           ("container metadata", ("container metadata", "footer"))]


def levels_from_protocol():
    txt = (PKG / "protocol_freeze.md").read_text(encoding="utf-8", errors="replace")
    out = []
    for m in re.finditer(r"^\|\s*(L\d)\s*\|\s*([^|]+?)\s*\|", txt, re.M):
        lvl, definition = m.group(1), m.group(2)
        site = next((s for s, keys in SITE_OF if any(k in definition.lower() for k in keys)), "other")
        out.append((lvl, definition, site))
    if len(out) < 4:
        sys.exit("ABORT: the frozen level table in protocol_freeze.md could not be parsed, so the diagram has no subject")
    return out


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    lv = levels_from_protocol()
    census_f = PROC / "EXP0049_level_census.csv"
    if not census_f.is_file():
        sys.exit(f"ABORT: {census_f.name} is absent")
    rows = list(csv.DictReader(open(census_f, encoding="utf-8", errors="replace")))
    n_rel = len(rows)
    depth = {l: sum(int(r[l]) for r in rows) for l, _d, _s in lv}
    tot = {c: sum(int(r[c]) for r in rows if r[c].strip().isdigit())
           for c in ("footers_read", "files", "components_strict", "components_with_rights")
           if c in rows[0]}
    hyp_f = PKG / "tables" / "table7_hypothesis_verdicts.csv"
    hyp = list(csv.DictReader(open(hyp_f, encoding="utf-8", errors="replace"))) if hyp_f.is_file() else []

    sites: dict[str, list] = {}
    for l, d, s in lv:
        sites.setdefault(s, []).append((l, d))
    order = [k for k, _ in SITE_OF] + [k for k in sites if k not in [a for a, _ in SITE_OF]]
    col2 = [(s, sites[s]) for s in order if s in sites]

    fig, ax = plt.subplots(figsize=(10.2, 4.8))
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")

    def box(x, y, w, h, title, body, fc="#eef3fa"):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.5,rounding_size=1.0",
                                    linewidth=0.7, edgecolor="#3a5a80", facecolor=fc))
        ax.text(x + w / 2, y + h - 1.6, title, ha="center", va="top", fontsize=7.0, weight="bold")
        ax.text(x + 1.0, y + h - 5.0 - 3.0 * (title.count(chr(10))), body, ha="left", va="top",
                fontsize=6.0, linespacing=1.5)

    def arrow(x1, y1, x2, y2):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=7,
                                     linewidth=0.8, color="#3a5a80", shrinkA=1, shrinkB=1))

    # the four read-site boxes set the vertical rhythm; everything else is centred on their combined height
    def site_body(items):
        out = []
        for l, d in items:
            out += [f"{l}: " + t for t in textwrap.wrap(d, 48, break_long_words=False)] or [f"{l}:"]
        return out

    bodies = [(s, site_body(v)) for s, v in col2]
    lh = min(5.6, (86.0 - 2.0 * (len(bodies) - 1)) / sum(1 + len(b) for _s, b in bodies))
    hs = [lh * (1 + len(b)) for _s, b in bodies]
    span = sum(hs) + 2.0 * (len(hs) - 1)
    top = 8 + span

    rel = sorted(r["corpus"] for r in rows)
    wrapped = "\n".join(", ".join(rel[i:i + 2]).rstrip(", ") for i in range(0, len(rel), 2))
    left = (f"{len(rel)} releases read from disk:\n{wrapped}\n\n"
            + "\n".join(f"{k.replace('_', ' ')}: {v:,}" for k, v in sorted(tot.items())))
    box(1, top - min(span, top - 8), 21, min(span, top - 8), "Input (frozen sample)", left, "#f7f7f2")

    y = top
    for (s, body), h in zip(bodies, hs):
        box(24, y - h, 27, h, f"read site - {s}", "\n".join(body))
        arrow(22.4, top - min(span, top - 8) / 2, 23.6, y - h / 2)
        y -= h + 2.0

    body = "\n".join(f"{l:<3s} {depth[l]}/{n_rel} releases" for l, _d, _s in lv)
    box(53, top - span, 15, span, "evidence levels\n(depth the census sees)", body)
    arrow(51.4, top - span / 2, 52.6, top - span / 2)

    hb = "\n".join(f"{r['hypothesis'].split('_')[0]}: "
                   + ("established" if r["established"] == "True" else
                      "refuted" if r["refuted"] == "True" else "not decided")
                   for r in hyp) or "no hypothesis table shipped"
    box(70, top - span, 15.5, span, "claims the design\ntests (recorded verdicts)", hb, "#f2f7f2")
    arrow(68.4, top - span / 2, 69.6, top - span / 2)
    ax.text(50, 3.4, "Labels are read from `protocol_freeze.md` §2, counts from "
                     "`results_processed/EXP0049_level_census.csv`, verdicts from "
                     "`tables/table7_hypothesis_verdicts.csv`; the diagram states no claim of its own.",
            ha="center", va="center", fontsize=5.8, color="0.3", wrap=True)
    ax.set_title("P005 framework: where a rights or provenance declaration could live, and how deep the census sees",
                 fontsize=8.4, loc="left", y=0.99)
    fig.tight_layout()

    FIG.mkdir(parents=True, exist_ok=True)
    name = "fig0_framework"
    fig.savefig(FIG / f"{name}.pdf", metadata=PDF_META)
    fig.savefig(FIG / f"{name}.svg", format="svg")
    (FIG / f"{name}.caption.txt").write_text(
        f"Figure 0 (spec §15 item 1) - research framework. The {len(lv)} evidence levels and their definitions are the "
        "frozen ones in `protocol_freeze.md` §2, grouped by the read site each definition names; the depth beside each "
        f"level is the number of the {n_rel} releases carrying a declaration there, summed from "
        "`results_processed/EXP0049_level_census.csv` (which also supplies the file, footer and component counts on the "
        "left). The right-hand boxes are the hypotheses that census decides, with the verdicts recorded in "
        "`tables/table7_hypothesis_verdicts.csv`. The diagram adds no claim: it is the design the other four figures "
        "report results from. Drawn by `02_shared_code/plotting/p005_framework_figure.py`.\n",
        encoding="utf-8", newline="")
    plt.close(fig)
    print(f"  figures/{name}.pdf + .svg + .caption.txt | {len(lv)} levels, {n_rel} releases, {len(hyp)} hypotheses, "
          f"sites={list(sites)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
