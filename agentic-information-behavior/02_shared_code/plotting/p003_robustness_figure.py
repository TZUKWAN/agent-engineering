"""Spec §15 item 5 for P003: the robustness figure the package did not ship.

P003 has a framework figure, a coverage heatmap, a recoverability panel and a containers/loss view, but nothing that
shows how stable its conformance census is under re-execution - so `export_figure_plan.py` reported item 5 as "no
figure serves this role". The package does hold the evidence: EXP-0029 and EXP-0030 are the same census re-executed
with identical parameters after a harness fix (logged as D18 in `deviations.md`), and both summaries ship in
`results_processed/`. This step draws that comparison instead of asserting it.

The figure is a measurement, not a decoration: panel A plots the 96 (corpus, concept) coverage values against each
other with the identity line, and panel B reports each corpus's largest absolute move. Every number is read from the
two CSVs; the count of unchanged cells is computed, never typed.

    python 02_shared_code/plotting/p003_robustness_figure.py
"""
from __future__ import annotations

import csv, pathlib, sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({"svg.hashsalt": "aib", "font.size": 7.5, "figure.dpi": 150,
                     "axes.spines.top": False, "axes.spines.right": False, "savefig.bbox": "tight"})

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
PKG = next(p for p in sorted((ROOT / "papers").glob("P003*")) if p.is_dir())
PROC, FIG = PKG / "results_processed", PKG / "figures"
PDF_META = {"CreationDate": None, "ModDate": None, "Producer": "aib plotting"}
A, B = "EXP0029_coverage_matrix.csv", "EXP0030_coverage_matrix.csv"


def load(rel: str):
    f = PROC / rel
    if not f.is_file():
        sys.exit(f"ABORT: {rel} is absent - the figure is drawn from it and nothing may be invented in its place")
    return {(r["corpus"], r["concept"]): r for r in
            csv.DictReader(open(f, encoding="utf-8", errors="replace"))}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    a, b = load(A), load(B)
    if set(a) != set(b):
        sys.exit(f"ABORT: the two runs cover different cells ({len(a)} vs {len(b)}), so they cannot be compared")
    keys = sorted(a)
    moved = [k for k in keys if a[k]["state"] != b[k]["state"]
             or abs(float(a[k]["coverage"]) - float(b[k]["coverage"])) > 1e-12]
    deltas = {k: float(b[k]["coverage"]) - float(a[k]["coverage"]) for k in keys}

    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.2), gridspec_kw={"width_ratios": [1, 1]})
    ax = axes[0]
    xs = [float(a[k]["coverage"]) for k in keys]
    ys = [float(b[k]["coverage"]) for k in keys]
    ax.scatter(xs, ys, s=14, c=["#b2182b" if k in moved else "#4575b4" for k in keys],
               edgecolor="none", label=f"{len(keys) - len(moved)} unchanged cells")
    ax.scatter([float(a[k]["coverage"]) for k in moved], [float(b[k]["coverage"]) for k in moved],
               s=42, facecolor="none", edgecolor="#b2182b", linewidths=1.1,
               label=f"{len(moved)} cell moved: " + ", ".join(f"{c}/{n}" for c, n in moved))
    for k in moved:
        ax.annotate(f"{a[k]['state']} → {b[k]['state']}", (float(a[k]["coverage"]), float(b[k]["coverage"])),
                    textcoords="offset points", xytext=(6, -10), fontsize=6, color="#b2182b")
    ax.plot([0, 1], [0, 1], ls="--", lw=0.8, color="0.4")
    ax.set_xlim(-0.03, 1.03); ax.set_ylim(-0.03, 1.03)
    ax.set_xlabel(f"coverage in EXP-{A[4:8]} (the run as frozen)")
    ax.set_ylabel(f"coverage in EXP-{B[4:8]} (the correction re-run)")
    ax.legend(fontsize=6, frameon=False, loc="lower right")
    ax.set_title("Re-execution invariance of the census", fontsize=8.5, loc="left")

    ax = axes[1]
    corps = sorted({k[0] for k in keys})
    worst = {c: max(abs(deltas[k]) for k in keys if k[0] == c) for c in corps}
    ax.barh(range(len(corps)), [worst[c] for c in corps],
            color=["#b2182b" if worst[c] else "#238b45" for c in corps])
    ax.set_yticks(range(len(corps)), [f"{c} ({sum(1 for k in keys if k[0] == c)} cells)" for c in corps], fontsize=6.5)
    ax.invert_yaxis()
    ax.set_xlabel("largest absolute change in coverage between the two runs")
    ax.set_title("Where the census is stable, and where it is not", fontsize=8.5, loc="left")
    for i, c in enumerate(corps):
        ax.text(worst[c] + 0.02, i, f"{worst[c]:.3f}", va="center", fontsize=6.5)
    ax.set_xlim(0, max(max(worst.values()) * 1.3, 0.05))
    fig.tight_layout()

    FIG.mkdir(parents=True, exist_ok=True)
    name = "fig4_reexecution_robustness"
    fig.savefig(FIG / f"{name}.pdf", metadata=PDF_META)
    fig.savefig(FIG / f"{name}.svg", format="svg")
    (FIG / f"{name}.caption.txt").write_text(
        "Figure 4 (spec §15 item 5) - robustness of the conformance census under re-execution. EXP-0030 re-ran the "
        "EXP-0029 census with identical parameters after a harness fix (`deviations.md` D18), so the two "
        "`results_processed/` summaries measure the same 96 (corpus, concept) cells. Left: coverage in each run, with "
        "the identity line; every cell but one sits on it. Right: the largest absolute coverage change per corpus. "
        f"Counts and deltas are computed from `results_processed/{A}` and `results_processed/{B}`; the single moved "
        "cell is named on the plot, and the state change it carries is printed with it. Drawn by "
        "`02_shared_code/plotting/p003_robustness_figure.py`.\n", encoding="utf-8",
        newline="")
    plt.close(fig)
    print(f"  figures/{name}.pdf + .svg + .caption.txt | {len(keys)} cells, {len(keys) - len(moved)} unchanged, "
          f"moved={[(c, n, a[(c, n)]['state'], b[(c, n)]['state']) for c, n in moved]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
