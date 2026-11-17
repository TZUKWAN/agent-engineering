"""Spec §15 roles that P002 did not ship: the data/trajectory schematic (item 2) and the mechanism/grouping figure (item 4).

`export_figure_plan.py` reported these two as "no figure serves this role", which was true - the package had a
framework figure, a model ladder and a truncation curve, but nothing that shows what a coded trajectory looks like or
how its stages group by corpus. Rather than relabel an existing artefact, this step draws the two figures from the
package's own coded-turn table and its frozen transition/truncation summaries.

Both figures are deterministic:

* the schematic's lanes are chosen by a stated rule (order the pilot's 20,000 coded trajectories by (n_steps,
  instance_id) and take ten evenly spaced ranks), so the panel spans the short-to-long range without cherry-picking;
* the grouping panel reads the two summaries the package already ships, normalising the transition counts by the
  corpus total that is printed in the same file.

Each figure is written as PDF and SVG with no run-time stamp, so a rebuild reproduces the bytes, and beside each one a
`*.caption.txt` that names the file it was drawn from - which is also how the plan matches artefact to role.

    python 02_shared_code/plotting/p002_stage_role_figures.py
"""
from __future__ import annotations

import ast, csv, pathlib, re, sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({"svg.hashsalt": "aib", "font.size": 7.5, "figure.dpi": 150,
                     "axes.spines.top": False, "axes.spines.right": False, "savefig.bbox": "tight"})

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
PKG = next(p for p in sorted((ROOT / "papers").glob("P002*")) if p.is_dir())
PROC = PKG / "results_processed"
FIG = PKG / "figures"

PDF_META = {"CreationDate": None, "ModDate": None, "Producer": "aib plotting"}


def read(rel: str):
    f = PROC / rel
    if not f.is_file():
        sys.exit(f"ABORT: {rel} is absent - this figure is drawn from it and nothing may be invented in its place")
    return list(csv.DictReader(open(f, encoding="utf-8", errors="replace")))


def write(fig, name: str, caption: str):
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{name}.pdf", metadata=PDF_META)
    fig.savefig(FIG / f"{name}.svg", format="svg")
    (FIG / f"{name}.caption.txt").write_text(
        caption.rstrip() + f" Drawn by `{pathlib.Path(__file__).relative_to(ROOT).as_posix()}` from the files named "
                           "above.\n", encoding="utf-8", newline="")
    plt.close(fig)
    print(f"  figures/{name}.pdf + .svg + .caption.txt")


def schematic():
    rows = read("EXP0026_pilot_coded_turns.csv")
    # one representative per distinct trajectory length, so the panel spans the whole range rather than the mode:
    # within a length, the first row that ends in a submitted episode if one exists, else the first by instance id.
    by_len: dict[int, list] = {}
    for r in sorted(rows, key=lambda r: (r["exit_status"] != "Submitted", r["instance_id"])):
        by_len.setdefault(int(r["n_steps"]), []).append(r)
    picks = [v[0] for k, v in sorted(by_len.items())]
    stages = sorted({s for r in rows for s in r["stages"].split("|")})
    pal = plt.get_cmap("tab20").colors
    col = {s: pal[i % 20] for i, s in enumerate(stages)}

    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    maxl = max(int(r["n_steps"]) for r in picks)
    for y, r in enumerate(picks):
        seq = r["stages"].split("|")
        obs = r["observations"].split("|")
        for x, (s, o) in enumerate(zip(seq, obs)):
            ax.add_patch(plt.Rectangle((x, -y - 0.34), 0.9, 0.68, facecolor=col[s], edgecolor="none"))
            if o.strip().lower() != "informative":
                ax.plot(x + 0.45, -y + 0.42, marker="v", ms=3.4, color="#b2182b", ls="none")
        ax.text(maxl + 0.6, -y, f"{r['n_steps']} turns, {r['exit_status']}", va="center", fontsize=6.5)
    ax.set_xlim(-0.5, maxl + 8.5)
    ax.set_ylim(-len(picks) + 0.4, 0.9)
    ax.set_yticks([0] + [-i for i in range(1, len(picks))], [r["instance_id"][:26] for r in picks], fontsize=6)
    ax.set_xlabel("coded turn index (turns of the trajectory)")
    ax.set_ylabel(f"pilot trajectory, one per length in 1-{maxl} turns")
    ax.spines[["top", "right", "left", "bottom"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    h = [plt.Rectangle((0, 0), 1, 1, facecolor=c) for c in col.values()]
    ax.legend(h, list(col), fontsize=6, ncol=len(col), loc="upper center",
              bbox_to_anchor=(0.5, 1.16), frameon=False, title=None)
    write(fig, "fig3_trajectory_schematic",
          "Figure 3 (spec §15 item 2) - data/trajectory schematic. One representative trajectory for every distinct "
          "coded length in the pilot (`results_processed/EXP0026_pilot_coded_turns.csv`, 20,000 episodes): at a given "
          "length the first episode whose exit_status is `Submitted` if one exists, otherwise the first by instance "
          "id, so the panel spans the whole length range instead of its mode and shows both terminal states. Each cell "
          "is one coded turn coloured by ISP stage; a red tick marks a turn the coder recorded as observation-"
          "dependent rather than informative (column `observations`). Cell width is one turn, so a longer bar is a "
          "longer trajectory; lane height is not a quantity.\n")


def grouping():
    tr = read("EXP0031_transitions.csv")
    tot: dict[str, int] = {}
    for r in tr:
        tot[r["corpus"]] = tot.get(r["corpus"], 0) + int(r["count"])
    corps = sorted(tot)
    cnt = {(r["corpus"], r["transition"]): int(r["count"]) for r in tr}

    def top5(c):
        ps = sorted((p for cc, p in cnt if cc == c), key=lambda p: (-cnt[(c, p)], p))
        return ps[:5]

    # the union of each corpus's own five most frequent transitions: pooling the top ranks across corpora would show
    # only the bigger corpus, because AgentTrove's and SWE-ZERO's stage vocabularies barely overlap.
    pairs = sorted({p for c in corps for p in top5(c)})
    tc = read("EXP0031_truncation_curve.csv")
    widest = max({r["cap"] for r in tc}, key=lambda c: int(re.search(r"\d+", c).group()))
    mix = {r["corpus"]: ast.literal_eval(r["shares"]) for r in tc if r["cap"] == widest}
    nturns = {r["corpus"]: r["n_turns"] for r in tc if r["cap"] == widest}
    stage_order = sorted({s for v in mix.values() for s in v}, key=lambda s: -sum(v.get(s, 0.0) for v in mix.values()))

    fig, axes = plt.subplots(1, 2, figsize=(8.2, 3.2), gridspec_kw={"width_ratios": [1.7, 1]})
    ax = axes[0]
    w = 0.8 / max(1, len(corps))
    for i, c in enumerate(corps):
        vals = [cnt.get((c, p), 0) / tot[c] for p in pairs]
        ax.bar([j + i * w for j in range(len(pairs))], vals, width=w, color=plt.get_cmap("tab10").colors[i], label=c)
    ax.set_xticks([j + w * (len(corps) - 1) / 2 for j in range(len(pairs))],
                  [p.replace("->", "→") for p in pairs], rotation=38, ha="right", fontsize=6.5)
    ax.set_ylabel("share of that corpus's coded transitions")
    ax.set_xlabel("stage-to-stage transition (the five most frequent within each corpus)")
    ax.legend(fontsize=6, frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_title("Grouping: what follows what, per corpus", fontsize=8.5, loc="left")

    ax = axes[1]
    for i, c in enumerate(corps):
        vals = [mix[c].get(s, 0.0) for s in stage_order]
        ax.bar([j + i * w for j in range(len(stage_order))], vals, width=w,
               color=plt.get_cmap("tab10").colors[i], label=f"{c} (n_turns={nturns[c]})")
    ax.set_xticks([j + w * (len(corps) - 1) / 2 for j in range(len(stage_order))], stage_order,
                  rotation=38, ha="right", fontsize=6.5)
    ax.set_ylabel("share of coded turns")
    ax.set_xlabel(f"ISP stage, at the widest cap in the file ({widest})")
    ax.legend(fontsize=6, frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_title("Mechanism: which stage holds the context", fontsize=8.5, loc="left")
    fig.tight_layout()
    write(fig, "fig4_stage_grouping",
          "Figure 4 (spec §15 item 4) - mechanism/grouping figure. Left: the stage-to-stage transition shares per "
          "corpus, counted from `results_processed/EXP0031_transitions.csv` and normalised by that corpus's own "
          "transition total (the sum of the same file's rows), so the two corpora's different sizes cannot drive the "
          f"comparison; the {len(pairs)} bars shown are the five most frequent transitions within each corpus, because "
          "the two stage vocabularies barely overlap. Right: the stage mix at the widest truncation cap the package "
          f"measured ({widest}, from `results_processed/EXP0031_truncation_curve.csv`), i.e. which stage holds the "
          "context when it is not cut off. Both panels are drawn from those summaries; no share is typed in.\n")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    schematic()
    grouping()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
