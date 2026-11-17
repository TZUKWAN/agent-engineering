"""Make every evidence path a package document cites resolve inside that package (spec §0 item 1, "independent").

Sixteen citations across the five packages pointed at files that exist only at the workspace root: the programme-level
novelty expansion (EXP-0060), the superseded-artefact register, P001's gold-tool grounding probe, and the runs of the
E-gap closure round (EXP-0106/0107/0108) plus P003's EXP-0036/0045 and P005's EXP-0071/0072. Those experiment scripts
write their raw output to `agentic-information-behavior/results_raw/`, while the package documents cite the path as it
looks from inside the package - so a reader who opened only `papers/P003_.../` could not open the evidence its own
deviation entry names.

The rule this step enforces is one-sided and mechanical:

* a cited path that exists at the workspace root is **copied** into the package byte for byte (`copy2`, so the mtime the
  raw log carries is preserved);
* a cited path that exists nowhere is reported, and the step exits non-zero, because a citation nobody can open is a
  defect in the manuscript rather than a missing file to be papered over;
* nothing is ever *deleted* from the workspace root, and nothing is copied that no document cites.

    python 02_shared_code/registry/reconcile_package_evidence.py [--paper P003] [--check]
"""
from __future__ import annotations

import argparse, pathlib, re, shutil, sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
PAPERS = sorted(p for p in (ROOT / "papers").glob("P0*") if p.is_dir())
CITE = re.compile(r"(?:results_processed|results_raw|tables|figures|configs|scripts)/[\w.\-]+\."
                  r"(?:csv|json|pdf|svg|py|txt|jsonl|parquet)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", default="")
    ap.add_argument("--check", action="store_true", help="report what would be copied without writing")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    copied, missing = 0, []
    for pkg in PAPERS:
        if a.paper and pkg.name[:4] != a.paper:
            continue
        cited = {}
        for doc in sorted(pkg.glob("*.md")):
            for rel in CITE.findall(doc.read_text(encoding="utf-8", errors="replace")):
                if "*" in rel or "?" in rel:                 # a family citation, not a file citation
                    continue
                cited.setdefault(rel, []).append(doc.name)
        for rel, docs in sorted(cited.items()):
            if (pkg / rel).is_file():
                continue
            src = ROOT / rel
            if src.is_file():
                if not a.check:
                    (pkg / rel).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, pkg / rel)
                copied += 1
                print(f"  {pkg.name[:4]}: {'would copy' if a.check else 'copied'} {rel} "
                      f"({src.stat().st_size} B) cited by {', '.join(sorted(set(docs)))}")
            else:
                missing.append(f"{pkg.name[:4]}: {rel} cited by {docs[0]} exists neither in the package nor at the "
                               "workspace root")
    print(f"[evidence] {copied} artefact(s) reconciled, {len(missing)} unresolvable citation(s)")
    for m in missing:
        print("  OPEN: " + m)
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
