"""Housekeeping fix: P001's limitations file carried TWO sections numbered L19.

The second was appended by `record_exp0082_p001.py` without checking the numbering that already existed (the first
L19 is EXP-0062's pretrained-comparator limitation, older and cited elsewhere). A duplicated section id in a delivered
package is exactly what a reviewer catches, so the newer section becomes L22 and the generator is changed too -
otherwise the next rebuild recreates the collision.

    python fix_l19_collision_p001.py
"""
from __future__ import annotations

import csv, io, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
P = ROOT / "papers" / "P001_routing_failure_qpp"
OLD_HEAD = "## L19 外部验证已做一次"
NEW_HEAD = "## L22 外部验证已做一次"


def write_rows(path, hdr, body):
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\r\n").writerows([hdr] + body)
    path.write_text(buf.getvalue(), encoding="utf-8", newline="")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")

    # 1. the section heading itself (only the newer section matches this exact prefix)
    lim = P / "limitations.md"
    s = lim.read_text(encoding="utf-8")
    n = s.count(OLD_HEAD)
    if n == 1:
        s = s.replace(OLD_HEAD, NEW_HEAD, 1)
        lim.write_text(s, encoding="utf-8", newline="")
        print("limitations.md: renamed the appended L19 -> L22")
    else:
        print(f"limitations.md: found {n} matches for the appended heading - left untouched")
    heads = re.findall(r"^## (L\d+)", lim.read_text(encoding="utf-8"), re.M)
    dups = sorted({h for h in heads if heads.count(h) > 1})
    print("  headings:", len(heads), "| duplicates:", dups or "none")

    # 2. references that point at the external-validation section
    for f in (P / "external_toolret_transfer.md", P / "final_audit.md",
              ROOT / "00_program_registry" / "PROGRAM_STATUS.md"):
        if not f.is_file():
            continue
        t = f.read_text(encoding="utf-8")
        new = t.replace("limitations L19", "limitations L22").replace("Limitations L19", "Limitations L22")
        if new != t:
            f.write_text(new, encoding="utf-8", newline="")
            print(f"  re-pointed L19 -> L22 in {f.name}")

    # 3. the claims matrix row (rewritten by column name, CRLF preserved)
    cp = P / "claims_evidence_matrix.csv"
    rows = [r for r in csv.reader(io.StringIO(cp.read_text(encoding="utf-8"))) if r]
    hdr, body = rows[0], rows[1:]
    w = hdr.index("where_in_paper")
    hits = 0
    for r in body:
        if r[0] in {"C23", "C24", "C25"} and "L19" in r[w]:
            r[w] = r[w].replace("L19", "L22")
            hits += 1
    if hits:
        write_rows(cp, hdr, body)
        print(f"  claims matrix: {hits} row(s) re-pointed to L22")

    # 4. the generator that created the collision
    gen = ROOT / "02_shared_code" / "registry" / "record_exp0082_p001.py"
    t = gen.read_text(encoding="utf-8")
    n = len(re.findall(r"L19 外部验证已做一次|Limitations L19", t))
    if n:
        t = t.replace("L19 外部验证已做一次", "L22 外部验证已做一次").replace("Limitations L19", "Limitations L22")
        gen.write_text(t, encoding="utf-8", newline="")
        print(f"  record_exp0082_p001.py: {n} occurrence(s) switched to L22 so a rebuild cannot recreate the clash")
    else:
        print("  record_exp0082_p001.py: no L19 reference found (already fixed?)")

    # 5. prove the guard in that generator still recognises the renamed section
    t = gen.read_text(encoding="utf-8")
    assert "L22 外部验证已做一次" in t, "the generator guard no longer matches the heading it writes"
    print("  generator guard matches its own heading:", "L22 外部验证已做一次" in t and "not in lim" in t)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
