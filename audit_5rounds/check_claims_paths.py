"""R1 check: every file path named in a package's claims_evidence_matrix.csv must resolve.

Resolution order: package-relative first, then programme root. Prints the findings as JSON so the
round problem list can ingest them.
"""
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a / "agentic-information-behavior" for a in HERE.parents
            if (a / "agentic-information-behavior" / "00_program_registry").is_dir())
sys.path.insert(0, str(ROOT / "02_shared_code" / "registry"))
import round2_lib as L  # noqa: E402

FILE_RE = re.compile(r"[\w./\\-]+\.(?:csv|json|md|pdf|svg|png)")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    bad = []
    for pkg in L.packages():
        cm = pkg / "claims_evidence_matrix.csv"
        if not cm.is_file():
            continue
        for r in L.read_any(cm) or []:
            cid = r.get("claim_id") or r.get("claim") or ""
            for k, v in r.items():
                if not v:
                    continue
                for m in FILE_RE.findall(str(v)):
                    p = pathlib.PurePosixPath(m.replace("\\", "/"))
                    name = p.name
                    hits = list(pkg.rglob(name))
                    if not hits and not (L.ROOT / p).is_file():
                        bad.append({"package": pkg.name, "claim": str(cid)[:60],
                                    "cell": k, "reference": m[:120]})
    print(json.dumps({"count": len(bad), "findings": bad[:60]}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
