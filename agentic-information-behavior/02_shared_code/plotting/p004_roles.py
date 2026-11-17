"""Spec §15 roles P004 did not ship: the data-structure schematic (item 2) and the full comparison table (item 8).

`export_figure_plan.py` reported both as unfilled, and both were genuinely unfilled. The package plots its framework,
its criterion validity, its confound/gating panel and its criterion sensitivity, but nothing that shows what the eight
releases actually contain at the level the scores were extracted from, and its shipped tables each carry one slice of
the statistics (validity, sensitivity, gating, presence) rather than the whole comparison.

Both artefacts are read from this package's own measurements, not assembled by hand:

* `figures/fig4_data_structure.pdf` is drawn from this package's own EXP-0041 scan as shipped in
  `tables/table_presence_scan.csv`: one bar per release, its height the number of quality-score fields found and its
  label the rows sampled and the container the scanner reached. A release with no field is drawn at zero, which is a
  measurement, not an assumption - six of the eight were `scanned_without_candidates`.
* `tables/table9_full_score_comparison.csv` is flattened from the newest `results_raw/EXP0043_*.json`, which carries
  RQ1 (per-configuration coherence and item-total correlations), RQ2 (criterion validity), RQ3 (partial and
  stratum-wise correlations) and RQ4 (gating consequence). Every row names the block it came from, so the table can be
  checked against the raw file it claims to summarise.

    python 02_shared_code/plotting/p004_roles.py
"""
from __future__ import annotations

import csv, glob, json, pathlib, sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({"svg.hashsalt": "aib", "font.size": 7.5, "figure.dpi": 150,
                     "axes.spines.top": False, "axes.spines.right": False, "savefig.bbox": "tight"})

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
PKG = next(p for p in sorted((ROOT / "papers").glob("P004*")) if p.is_dir())
PROC, RAW, FIG, TAB = (PKG / "results_processed", PKG / "results_raw", PKG / "figures", PKG / "tables")
PDF_META = {"CreationDate": None, "ModDate": None, "Producer": "aib plotting"}


def data_structure() -> str:
    """The schematic is drawn from P004's own EXP-0041 presence scan, not from another paper's census.

    An earlier version read `results_processed/EXP0045_data_derived_units.csv`, which is a copy of P003's conformance
    census that had been dropped into this folder: the picture would have been accurate about the corpora but would
    have presented another package's measurement as this paper's data schematic.
    """
    f = TAB / "table_presence_scan.csv"
    if not f.is_file():
        sys.exit(f"ABORT: {f.name} is absent - the schematic is drawn from it")
    rows = list(csv.DictReader(open(f, encoding="utf-8", errors="replace")))
    rows.sort(key=lambda r: (-int(r["score_fields_found"]), r["corpus"]))
    labs = [r["corpus"] for r in rows]
    fields = [int(r["score_fields_found"]) for r in rows]
    sampled = [int(r["rows_sampled"]) for r in rows]
    qual = [r["qualifies"].strip().lower() == "true" for r in rows]
    cont = [r["container"] for r in rows]

    fig, ax = plt.subplots(figsize=(7.0, 3.3))
    y = range(len(rows))
    ax.barh(list(y), fields, color=["#238b45" if q else "#b2182b" for q in qual], height=0.62)
    for i, (n, s, c, q) in enumerate(zip(fields, sampled, cont, qual)):
        # a bar of length zero has no room for a label, so the container type moves into the annotation instead of
        # being printed at x=0, where it collided with the text
        if n:
            ax.text(n + 0.12, i, f"{n} score field(s), {s:,} rows sampled", va="center", fontsize=6.2, color="0.25")
            ax.text(0.06, i, c, va="center", fontsize=5.8, color="white")
        else:
            ax.text(0.12, i, f"0 fields - {c} container, "
                             + (f"{s:,} rows sampled" if s else "no candidate file reached"),
                    va="center", fontsize=6.2, color="0.25")
    ax.set_yticks(list(y), labs, fontsize=7)
    ax.invert_yaxis()
    ax.set_xlim(0, max(fields) + 4.6)
    ax.set_xlabel("shipped quality-score fields found in the release (container type named on each line)")
    ax.set_ylabel("release (the eight corpora this paper scanned)")
    ax.set_title("Where a shipped score exists at all: 1 of the 8 releases carries one", fontsize=8.5,
                 loc="left")
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    fig.tight_layout()
    FIG.mkdir(parents=True, exist_ok=True)
    name = "fig4_data_structure"
    fig.savefig(FIG / f"{name}.pdf", metadata=PDF_META)
    fig.savefig(FIG / f"{name}.svg", format="svg")
    nq = sum(qual)
    (FIG / f"{name}.caption.txt").write_text(
        f"Figure 4 (spec §15 item 2) - data/structure schematic, drawn from this package's own EXP-0041 scan as "
        f"shipped in `tables/{f.name}`. Each release is one bar: the number of quality-score fields the scanner found "
        f"in the rows it read, with the number of rows sampled and the container format written on the line. Green is "
        f"a release the scanner qualified as carrying a score ({nq} of {len(rows)}); red is a release with none, "
        f"including the corpora it could not reach a candidate file in "
        f"(`scanned_without_candidates`). This is the structure the shipped quality scores are computed over, and the "
        "figure is what makes the single-green-bar finding visible rather than asserted. Drawn by "
        "`02_shared_code/plotting/p004_roles.py`.\n", encoding="utf-8", newline="")
    plt.close(fig)
    return f"{len(rows)} releases, {nq} qualifying, max {max(fields)} fields"


def comparison_table() -> str:
    files = sorted(glob.glob(str(RAW / "EXP0043_p004_validity_main_*.json")))
    if not files:
        sys.exit("ABORT: no EXP-0043 raw file - the comparison table summarises it and invents nothing")
    src = pathlib.Path(files[-1])
    d = json.loads(src.read_text(encoding="utf-8"))
    out = []

    def row(block, unit, measurement, est, ci=(), p="", verdict="", n="", criterion=""):
        out.append({"exp_id": d["exp_id"], "block": block, "unit": unit, "measurement": measurement,
                    "criterion": criterion, "n": n, "estimate": "" if est is None else est,
                    "ci95_lo": ci[0] if len(ci) == 2 else "", "ci95_hi": ci[1] if len(ci) == 2 else "",
                    "p_holm": p, "verdict": verdict, "source_file": f"results_raw/{src.name}",
                    "generated_by": "02_shared_code/plotting/p004_roles.py", "seed": d.get("seed", "")})

    pooled_n = next((v["n"] for v in d["RQ2"].values() if v.get("n")), "")
    for tag, blk in list(d["RQ1"]["per_config"].items()) + [("pooled", d["RQ1"]["pooled"])]:
        cfg_rows = (d.get("configs", {}).get(tag, {}) or {}).get("rows", "") or pooled_n
        row("RQ1 coherence", tag, "cronbach_alpha_prompt_clustered", blk["alpha"],
            blk.get("alpha_ci_prompt_clustered", ()), "", blk.get("verdict", ""), cfg_rows)
        for k, v in (blk.get("item_total_rho") or {}).items():
            row("RQ1 coherence", k, f"item_total_rho_vs_{tag}_score", v, (), "", "", cfg_rows)
        for k, v in (blk.get("overall_vs_components") or {}).items():
            row("RQ1 coherence", k, f"overall_vs_component_rho_{tag}", v, (), "", "", cfg_rows)
    for k, v in d["RQ2"].items():
        row("RQ2 criterion validity", k, "spearman_rho_vs_criterion", v["rho"],
            v.get("ci95_prompt_clustered", ()), v.get("p_holm", ""), v.get("verdict", ""), v.get("n", ""),
            v.get("criterion", ""))
    for k, v in d.get("RQ3", {}).items():
        row("RQ3 confound control", k, "rho_vs_fail_at_3_pooled", v.get("pooled_rho_vs_fail_at_3"),
            (), "", "", "", "fail_at_3")
        row("RQ3 confound control", k, "partial_rho_given_catalogue_and_length",
            v.get("partial_rho_given_catalogue_and_length"), (), "", "", "", "fail_at_3")
        row("RQ3 confound control", k, "r2_of_ranks_on_n_candidates", v.get("r2_of_ranks_on_n_candidates"))
        for s, sv in (v.get("rho_by_catalogue_stratum") or {}).items():
            row("RQ3 confound control", k, f"rho_within_catalogue_stratum_{s}", sv.get("rho"), (), "", "",
                sv.get("n", ""), "fail_at_3")
    for tag, v in d.get("RQ4", {}).items():
        for f_ in ("rows_all", "rows_kept", "kept_share", "fail_at_3_all", "fail_at_3_kept", "mean_n_candidates_all",
                   "mean_n_candidates_kept", "instances_all", "instances_kept"):
            if f_ in v:
                row("RQ4 gating consequence", tag, f_, v[f_])
        for f_, e in (v.get("relative_shift") or {}).items():
            row("RQ4 gating consequence", tag, f"relative_shift_{f_}", e)
        row("RQ4 gating consequence", tag, "verdict", "", (), "", v.get("verdict", ""))

    TAB.mkdir(parents=True, exist_ok=True)
    cols = list(out[0])
    with (TAB / "table9_full_score_comparison.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(out)
    units = {r["unit"] for r in out}
    return f"{len(out)} rows over {len(units)} units and {len({r['block'] for r in out})} blocks"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    print("  fig4_data_structure:", data_structure())
    print("  table9_full_score_comparison.csv:", comparison_table())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
