"""Round-2 check A: does every number a package prints come from a run it holds?

Two levels, both mechanical:

1. **tables against artefacts.** Every numeric cell of `tables/table*.csv` and of the summary-shaped CSVs under
   `results_processed/` (at most 25 rows - an arms table, an AUC table, a strata table) must appear in the kept
   artefact generation of one of the package's registered experiments. A table cell that only exists in a
   *superseded* generation is a stale number being shipped as current. Row-level dumps stay out of this level and
   are tested by `round2_corpus_remeasurement.py`, which re-measures them from the corpus.
2. **prose against both.** Every number in the package's own documents (paper, appendix, README, freeze,
   limitations, novelty and SOTA audits, reviewer attack, final audit, E-coverage, cost and contamination records,
   deviations, dataset card, pilot report, research plan) must be supported at the precision it is written - or a
   difference/ratio of supported values, or a small structural count.

Output is a detector report, not a verdict: each unsourced number is printed with the sentence around it so a
person can see whether it is a real defect (a figure no run produced) or a formatting artefact (a section
number, a year, a count of something outside the corpus).

    python 02_shared_code/registry/round2_number_provenance.py [--paper P033] [--limit 40]
"""
from __future__ import annotations

import argparse
import collections
import datetime
import json
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import round2_lib as L                                                    # noqa: E402

ROOT = L.ROOT
SKIP_DOC_PATTERNS = (
    re.compile(r"^#{1,6}\s"),                       # headings carry section numbers, not measurements
    re.compile(r"^\s*[|\s+-]+$"),                   # table rules
    re.compile(r"\b(19|20)\d{2}\b.*(-|to|–)\b(19|20)\d{2}\b"),   # year spans (a literature range)
)
YEAR = re.compile(r"^(19|20)\d{2}$")
# identifiers that merely look like quantities: dotted versions, arXiv/DOI ids, urls, and the estate's
# own object names (EXP-0123, P033, table7, fig2, §4.1, v2).
IDENT = re.compile(r"\d+\.\d+\.\d+|\d{4}\.\d{4,5}|https?:|arxiv|doi|v\d|EXP-?\d|P0\d\d|table\s*\d|fig\w*\s*\d|§\s*\d")


def paragraphs(text: str):
    """(line, its paragraph) for every line of a document.

    A sentence a reader computes on is wrapped across lines - P005's "Of the 62 declared links, 52 were testable
    (83.9 %)" has its two terms on different lines - so the arithmetic rule needs the paragraph as its context while
    the numbers are still scored one line at a time, under the same line-level skips that have always applied.
    """
    for block in re.split(r"\n[ \t]*\n", text):
        para = " ".join(l.strip() for l in block.splitlines() if l.strip())
        for line in block.splitlines():
            yield line, para


def prose_numbers(pkg: pathlib.Path, pools) -> list:
    bad = []
    hist = None
    for name in L.package_docs(pkg):
        f = pkg / name
        if not f.is_file():
            continue
        use = pools
        if name in L.HISTORY_DOCS or pathlib.PurePosixPath(name).name.startswith("protocol_freeze"):
            # a freeze is a dated record: it is scored against the generations it was written from, because rewriting
            # a pre-registration to match a later re-run of the same census is exactly what the freeze forbids
            if hist is None:
                hist = pools.with_history(L.historic_numbers(pkg))
            use = hist
        for line, para in paragraphs(f.read_text(encoding="utf-8", errors="replace")):
            if any(p.match(line) for p in SKIP_DOC_PATTERNS):
                continue
            for v, dp, ctx in L.numbers_in(line):
                if v in (0, 1) or (float(v).is_integer() and v <= L.SMALL_STRUCTURAL) or YEAR.match(f"{v:.0f}"):
                    continue
                if IDENT.search(ctx):                          # "2609.08327", "1.2.3", a url: not a measurement
                    continue
                why = L.support(v, dp, use, ctx, para)
                if not why:
                    bad.append({"doc": name, "value": v, "context": ctx[:200]})
    return bad


PLACEHOLDER = re.compile(r"unknown table source|no reader|not populated", re.I)


SUMMARY_ROW_CAP = 25
# how short a numberless table has to be before it is the placeholder defect rather than a table of words
WORD_TABLE_ROWS = 3
# a quantity standing on its own, sign included: not a digit inside an identifier (`P008`, `table5`)
NUMBER_ANYWHERE = re.compile(r"(?<!\w)[-+]?\d+(?:\.\d+)?(?!\w)")
# a row that says in words why it holds no number. The estate's rule is that a negative or an untestable claim is
# recorded rather than dropped, so a checker that called those rows "degenerate" would be a reason to delete them.
DISCLOSURE = re.compile(r"not[ _]measurable|not[ _]recorded|not[ _]estimable|not[ _]testable|no[ _]config[ _]column"
                        r"|not[ _]populated|not[ _]applicable|n/?a\b|no row|impossible|withheld", re.I)


def printed_tables(pkg: pathlib.Path) -> list:
    """Every CSV the package shows a reader as a result: `tables/table*.csv`, plus the summary-shaped CSVs in
    `results_processed/`.

    Shape decides, not folder. A per-query score dump is the data a statistic was computed from; an arms table, an
    AUC table or a strata table of a dozen rows is a printed result - and the estate keeps both kinds under
    `results_processed/`, so scanning that folder by name alone left 141 summary-shaped shipped tables unchecked
    while this checker's own docstring said it read them. The 179 larger files stay out: re-checking a row-level
    dump cell by cell tests the corpus, not the reporting, and `round2_corpus_remeasurement.py` is the check that
    reads the corpus.
    """
    out = sorted((pkg / "tables").glob("table*.csv"))
    for f in sorted((pkg / "results_processed").glob("*.csv")):
        try:
            rows = L.read_any(f) or []
        except Exception:                                          # noqa: BLE001 - an unreadable CSV is reported elsewhere
            continue
        if 0 < len(rows) <= SUMMARY_ROW_CAP:
            out.append(f)
    return out


def degenerate_tables(pkg: pathlib.Path) -> list:
    """A shipped table that carries no measurement at all.

    `package_audit` counts deliverable 11 by presence and non-emptiness, so a one-row file whose only cell reads
    `unknown table source <name>` passes it while telling the reader nothing. This is the round-2 answer to that:
    a table is degenerate when it has no numeric column or every row is a note of that kind.
    """
    bad = []
    for f in printed_tables(pkg):
        rows = L.read_any(f) or []
        if not rows:
            bad.append({"table": f.name, "problem": "empty_table"})
            continue
        cols = list(rows[0])
        # a number anywhere in a cell counts, because these packages' result tables often hold a printed dictionary
        # in one cell - `value = "{'beta': -0.7825, 'ci_clustered': [-0.1879, -0.1511]}"` carries the measurement,
        # and reading only cells that *start* with a digit called 115 of those tables numberless
        numeric = [c for c in cols if any(NUMBER_ANYWHERE.search(str(r.get(c) or "")) for r in rows)]
        notes = [r for r in rows if any(PLACEHOLDER.search(str(v or "")) for v in r.values())]
        disclosed = [r for r in rows if any(DISCLOSURE.search(str(v or "")) for v in r.values())]
        if len(notes) == len(rows) or not rows:
            bad.append({"table": f.name, "problem": "table_ships_no_measurement",
                        "columns": cols[:6], "first_row": str(rows[0])[:140]})
        elif not numeric and len(rows) <= WORD_TABLE_ROWS and len(disclosed) < len(rows):
            # a table of words rather than numbers is not automatically empty: a provenance table, or one that
            # records `not applicable / the artefact holds no row for this topic`, is a disclosure. Only a short one
            # reads as the placeholder defect this rule was written for - widening the file set to every shipped
            # summary first produced 129 "findings", and almost all of them were case lists, instrument tables and
            # arms descriptions whose rows differ from one another, which is measurement in words rather than
            # nothing. A long table with no numbers is a data dump, and `round2_corpus_remeasurement` reads those.
            bad.append({"table": f.name, "problem": "table_has_no_numeric_column",
                        "columns": cols[:6], "first_row": str(rows[0])[:140]})
    return bad


def table_numbers(pkg: pathlib.Path, pools) -> list:
    bad = []
    for f in printed_tables(pkg):
        rows = L.read_any(f) or []
        for r in rows:
            for k, val in (r or {}).items():
                if val is None or val == "":
                    continue
                s = str(val)
                try:
                    v = float(s.replace(",", "").rstrip("%"))
                except ValueError:
                    # a cell that is not a number can still carry one: P005's `inputs` column holds the JSON of the
                    # quantities its decision was made on, and reading only whole-cell floats let those numbers past
                    # the check unmeasured
                    for v2, dp2, ctx2 in L.numbers_in(s):
                        if v2 in (0, 1) or (float(v2).is_integer() and v2 <= L.SMALL_STRUCTURAL) \
                                or YEAR.match(f"{v2:.0f}") or IDENT.search(ctx2):
                            continue
                        if not L.support(v2, min(dp2, 6), pools, ctx2):
                            bad.append({"table": f.name, "column": k, "value": v2, "cell": s[:80]})
                    continue
                dp = len((s.rstrip("%").split(".")[1])) if "." in s else 0
                if s.endswith("%"):
                    v, dp = v, dp + 2                     # a percentage cell: compare at its own precision
                if abs(v) <= L.SMALL_STRUCTURAL and float(v).is_integer():
                    continue
                if not L.support(v, min(dp, 6), pools):
                    bad.append({"table": f.name, "column": k, "value": v})
    return bad


def matcher_specificity(pools, paras=(), draws: int = 200, seed: int = 20260925) -> dict:
    """How often the matcher accepts a figure this package never measured.

    A detector that reports "0 unsupported numbers" says nothing unless its acceptance rate for numbers that are not
    real is low, and that rate is a property of the package's own pool: a package holding 200k measured values, of
    which thousands are four-decimal shares, will accept a stranger's figure far more often than a small one. So the
    control is measured here, on every package, next to the result it qualifies. Two rates are reported, because two of
    the reading rules are context-dependent: `rejected` scores the figure on its own (the conservative reading, which
    is what a table cell gets), and `rejected_in_a_real_passage` scores it inside one of the package's own paragraphs,
    which is how prose is read and therefore the number that qualifies the prose result.
    """
    import random
    rng = random.Random(seed)
    plain = incon = 0
    for i in range(draws):
        v = round(rng.uniform(-2, 3), 4)
        plain += bool(L.support(v, 4, pools, ""))
        if paras:
            para = paras[i % len(paras)]
            incon += bool(L.support(v, 4, pools, para[:160], para))
        else:
            incon += bool(L.support(v, 4, pools, ""))
    return {"draws": draws, "passages_used": len(paras),
            "accepted_unrelated": plain, "rejected": round(1 - plain / draws, 3),
            "accepted_unrelated_in_a_passage": incon,
            "rejected_in_a_real_passage": round(1 - incon / draws, 3)}


def sample_paragraphs(pkg: pathlib.Path, cap: int = 40) -> list:
    out = []
    for name in ("paper.md", "appendix.md", "final_audit.md", "dataset_card.md"):
        f = pkg / name
        if not f.is_file():
            continue
        for _line, para in paragraphs(f.read_text(encoding="utf-8", errors="replace")):
            if len(para) > 120:
                out.append(para)
                if len(out) >= cap:
                    return out
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", default="")
    ap.add_argument("--limit", type=int, default=25, help="examples printed per package")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    L.FROZEN = L.frozen_constants()
    report, tot = {}, collections.Counter()
    spec_tot = collections.Counter()
    for pkg in L.packages():
        if a.paper and not pkg.name.startswith(a.paper):
            continue
        art, tbl, _src, groups, colsums, sibs = L.value_pool(pkg)
        pools = L.Pools(art, tbl, groups, colsums, sibs)
        tb = table_numbers(pkg, pools)
        pb = prose_numbers(pkg, pools)
        mc = L.missing_copies(pkg)
        dg = degenerate_tables(pkg)
        spec = matcher_specificity(pools, sample_paragraphs(pkg))
        report[pkg.name] = {"values_in_kept_artefacts": len(art), "values_in_shipped_tables": len(tbl),
                            "cited_exps_not_in_package": mc,
                            "degenerate_tables": dg,
                            "unsupported_table_cells": tb, "unsupported_prose_numbers": pb,
                            "matcher_specificity": spec}
        tot["table_cells"] += len(tb)
        tot["prose"] += len(pb)
        tot["missing_copies"] += len(mc)
        tot["degenerate_tables"] += len(dg)
        spec_tot["accepted"] += spec["accepted_unrelated"]
        spec_tot["accepted_passage"] += spec["accepted_unrelated_in_a_passage"]
        spec_tot["draws"] += spec["draws"]
        print(f"{pkg.name[:44]:44s} art={len(art):5d} tbl={len(tbl):5d} unsourced_cells={len(tb):4d} "
              f"unsourced_prose={len(pb):4d} degenerate_tables={len(dg)} cited_but_absent={len(mc)} "
              f"matcher_rejects_unrelated={1 - spec['accepted_unrelated'] / spec['draws']:.3f}"
              f"/in_passage={1 - spec['accepted_unrelated_in_a_passage'] / spec['draws']:.3f}")
        for x in tb[:a.limit]:
            print(f"    TABLE  {x['table']}[{x['column']}] = {x['value']}")
        for x in pb[:a.limit]:
            print(f"    PROSE  {x['doc']}: {x['value']} :: {x['context'][:130]}")
        if mc:
            print(f"    ABSENT {', '.join(mc)}")
        for x in dg[:a.limit]:
            print(f"    DEGEN  {x['table']} :: {x['first_row'][:110]}")
    payload = {"detector": "round2_number_provenance", "packages": len(report),
               "totals": dict(tot), "detail": report,
               "matcher_specificity": {"draws": spec_tot["draws"], "accepted_unrelated": spec_tot["accepted"],
                                       "rejected": round(1 - spec_tot["accepted"] / max(1, spec_tot["draws"]), 3),
                                       "accepted_unrelated_in_a_passage": spec_tot["accepted_passage"],
                                       "rejected_in_a_real_passage": round(
                                           1 - spec_tot["accepted_passage"] / max(1, spec_tot["draws"]), 3),
                                       "meaning": "fraction of unrelated four-decimal figures the matcher refuses, "
                                                  "alone and inside one of the package's own passages; the "
                                                  "zero-findings result is only as strong as these numbers"},
               "at": datetime.datetime.now().isoformat(timespec="seconds"),
               "invocation": " ".join([sys.executable] + sys.argv)}
    dest = pathlib.Path(a.out) if a.out else \
        ROOT / "results_raw" / f"ROUND2_NUMBER_PROVENANCE_{time.strftime('%Y%m%dT%H%M%S')}.json"
    dest.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\ntotals: {dict(tot)}  ->  {dest.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
