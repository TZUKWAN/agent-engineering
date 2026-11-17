"""Round-2 check E: does each claim's wording match the support its own package can show?

`claims_evidence_matrix.csv` is the package's promise to a reviewer - this claim, from this run, in this table and
figure, with this direction. The first audit round checked the file exists and that the paths are non-empty; this
checks the five ways it can be true as a file and false as a statement:

* the cited run's actual verdict for that hypothesis versus the `direction` the row claims;
* a cited table or figure that is not in the package;
* a `raw_result_file` that does not resolve inside the package;
* digits the row says it reported that no kept artefact carries;
* a file a shipped document names by path, in prose rather than in the matrix, that the package does not hold.

The last of these is not covered by the matrix checks: a sentence can promise a file the folder never carried, and
`resolves()` deliberately falls back to the programme root, which is right for `01_datasets/` and
`02_shared_code/` citations and wrong for a paragraph that says "this package ships" the record it quotes.

The direction comparison reads the verdict from the package's own `table3`-family table (what a reader sees), not
from a restatement, because the defect worth finding is a manuscript sentence that outlived the number under it.

    python 02_shared_code/registry/round2_claim_support.py [--limit 30]
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime
import io
import json
import pathlib
from pathlib import Path
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import round2_lib as L                                                    # noqa: E402

ROOT = L.ROOT
FOUR_WAY = ("supported", "partial", "null", "opposite")
PREDICTED = {"as predicted": ("supported", "partial"),
             "against prediction": ("opposite",),
             "opposite": ("opposite",),
             "not established": ("null", "not_testable", "not_estimable", "below", "not_reproduced",
                                 "not_specific", "not_monotone", "not_at_or_above", "measured_descriptively",
                                 "not_interpretable", "not_invariant", "not_all_classes")}


def resolves(pkg: pathlib.Path, v: str) -> bool:
    """Does this citation point at something a reader of the package can open?

    The matrix writes the same object four ways - a bare `table3_main_models.csv`, a package-relative
    `tables/table3_main_models.csv`, a glob like `results_raw/EXP0021_*_transfer_*.json`, and `-` when the claim
    has no figure. All four are checked; only a citation none of them satisfies is a broken one.
    """
    v = (v or "").strip()
    if not v or v in {"-", "n/a", "none", "N/A", "—"}:
        return True
    cands = [v, Path(v).name, f"tables/{Path(v).name}", f"figures/{Path(v).name}",
             f"results_raw/{Path(v).name}", f"results_processed/{Path(v).name}"]
    for c in cands:
        if "*" in c or "?" in c:
            if list(pkg.glob(c)):
                return True
        elif (pkg / c).is_file() or (pkg / c.rstrip("/")).is_dir():
            # a claims row may cite a whole folder as the evidence for a qualitative appendix, and a directory is
            # not a file - treating it as one reported four packages as broken citations over a path that opens fine
            return True
    return (ROOT / v).is_file() or bool(list((ROOT / v).parent.glob(Path(v).name)) if "*" in v else False)


def verdicts_from_tables(pkg: pathlib.Path) -> dict:
    """{(hypothesis, term-ish): verdict} from whatever main-models table the package ships."""
    out = {}
    for f in sorted((pkg / "tables").glob("table[3-6]_*.csv")):
        for r in L.read_any(f) or []:
            h = str(r.get("hypothesis") or "").strip()
            v = str(r.get("verdict") or "").strip()
            if h and v:
                out[(f.name, h)] = v
                out[("_any", h)] = out.get(("_any", h), v)
    return out


PROSE_PATH = re.compile(r"(?<![\w/])((?:results_raw|results_processed|tables|figures)/"
                        r"[\w.\-\u4e00-\u9fff]*/?[\w.\-]*\.(?:json|csv|md|jsonl|parquet|tsv|txt|log|npy|png|pdf))")


def prose_paths(pkg: pathlib.Path) -> list:
    """Every file path a shipped document names, and whether the package holds it.

    Only the four folders a package carries are read, because a citation of `01_datasets/...` or
    `02_shared_code/...` points at the estate rather than at the package, and a glob names a family of runs rather
    than a file. Two kinds of miss are counted rather than reported, because both are true statements a reader can
    follow: a path under `results_raw/superseded/`, which is the programme's own retirement folder that no package
    ships by design, and a timestamped record whose run is present in the package under a later generation - a dated
    document names what was on disk the day it was written. Only a path whose run is nowhere in the package is a
    citation the package cannot support.
    """
    out = []
    held = {f.name for f in pkg.rglob("*") if f.is_file()}
    sup = L.superseded()
    for doc in L.package_docs(pkg):
        try:
            text = (pkg / doc).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for p in sorted(set(PROSE_PATH.findall(text))):
            if (pkg / p).is_file():
                continue
            name = Path(p).name
            if "superseded/" in p or name in sup:
                out.append({"path": p, "doc": doc, "kind": "retired_generation"})
                continue
            stem = re.sub(r"_\d{8}T\d{6}", "", name).split("_2026092")[0]
            if any(stem.rstrip("._-") in h and h.endswith(Path(name).suffix) for h in held):
                out.append({"path": p, "doc": doc, "kind": "superseded_by_a_later_generation"})
                continue
            out.append({"path": p, "doc": doc, "kind": "not_in_the_package"})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=30)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    bad = []
    nclaims = 0
    paths = collections.Counter()
    for pkg in L.packages():
        for x in prose_paths(pkg):
            paths[x["kind"]] += 1
            if x["kind"] != "not_in_the_package":
                continue
            bad.append({"package": pkg.name, "problem": "prose_names_a_path_the_package_does_not_hold",
                        "where": x["doc"], "value": x["path"]})
        f = pkg / "claims_evidence_matrix.csv"
        if not f.is_file():
            # a blocked design record assembles no package, so it has no claims to matrix: 
            # writes BLOCKED.md in its place and the audit reports it as a blocked record.
            if (pkg / "BLOCKED.md").is_file():
                continue
            bad.append({"package": pkg.name, "problem": "no_claims_matrix"})
            continue
        rows = list(csv.DictReader(io.StringIO(f.read_text(encoding="utf-8-sig"))))
        art, tbl, _, groups, colsums, sibs = L.value_pool(pkg)
        pools = L.Pools(art, tbl, groups, colsums, sibs)
        verd = verdicts_from_tables(pkg)
        for r in rows:
            cid = r.get("claim_id") or "?"
            nclaims += 1
            for key in ("table", "figure"):
                v = (r.get(key) or "").strip()
                # the matrix writes some rows as a bare file name, others as `tables/x.csv`, others as a glob, and
                # some as two citations in one cell (`x.md; results_processed/`) - all of them have to resolve.
                parts = [p.strip() for p in re.split(r"[;,]", v) if p.strip()] or [""]
                if not all(resolves(pkg, p) for p in parts):
                    bad.append({"package": pkg.name, "claim": cid, "problem": f"cited_{key}_not_in_package",
                                "value": v})
            rf = (r.get("raw_result_file") or "").strip()
            if not all(resolves(pkg, part) for part in re.split(r"[;,]", rf) if part.strip()):
                bad.append({"package": pkg.name, "claim": cid, "problem": "raw_result_file_does_not_resolve",
                            "value": rf[:90]})
            h = (re.search(r"\bH\\d", str(r.get("claim") or "")) or [None, ""])[1] if r.get("claim") else ""
            d = (r.get("direction") or "").strip().lower()
            v = verd.get(("_any", h)) if h else None
            if v and d in PREDICTED:
                allowed = PREDICTED[d]
                if not any(v.startswith(allow) for allow in allowed):
                    bad.append({"package": pkg.name, "claim": cid, "hypothesis": h,
                                "problem": "claim_direction_disagrees_with_the_shipped_verdict",
                                "direction": d, "shipped_verdict": v[:60]})
            digits = r.get("digits_reported") or "{}"
            try:
                digits = json.loads(digits) if digits.strip().startswith(("{", "[")) else {}
            except json.JSONDecodeError:
                # some rows record the digits in prose rather than as a map; the paths above are still checked
                digits = {}
            for _k, num in (digits or {}).items():
                try:
                    val = float(str(num))
                except (TypeError, ValueError):
                    continue
                if abs(val) > L.SMALL_STRUCTURAL and not L.support(val, 4, pools):
                    bad.append({"package": pkg.name, "claim": cid, "problem": "reported_digit_unsupported",
                                "field": _k, "value": val})
    by = {}
    for x in bad:
        by[x["problem"]] = by.get(x["problem"], 0) + 1
    for x in bad[:a.limit]:
        print(json.dumps(x, ensure_ascii=False)[:210])
    print(f"\n{len(bad)} claim-support finding(s)")
    print(json.dumps(by, indent=1))
    print(f"prose path citations: {json.dumps(dict(paths))}")
    dest = ROOT / "results_raw" / f"ROUND2_CLAIM_SUPPORT_{time.strftime('%Y%m%dT%H%M%S')}.json"
    dest.write_text(json.dumps({"detector": "round2_claim_support", "totals": by, "detail": bad,
                                "claims_checked": nclaims, "packages": len(L.packages()),
                                "prose_path_citations": dict(paths),
                                "at": datetime.datetime.now().isoformat(timespec="seconds")},
                               indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote", dest.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
