"""Housekeeping: P001's experiment inventory still said E12 was not done.

It was - EXP-0028 ran the training-size sweep and `limitations.md` even carries a section "L14 训练规模敏感性（E12
实测）" reporting it. The inventory table is the list a reviewer reads to find out what is missing, so a stale "未做"
there is a false admission, not a harmless leftover. This script corrects the row and prints the cross-check that
justifies it, then reports how many claim-evidence paths resolve across the five packages.

    python fix_e12_inventory_row_p001.py
"""
from __future__ import annotations

import csv, glob, io, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parents[2]
P = ROOT / "papers" / "P001_routing_failure_qpp"


def main() -> int:
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    lim = P / "limitations.md"
    s = lim.read_text(encoding="utf-8")
    row = re.search(r"^\| E12[^\n]*$", s, re.M)
    if not row:
        print("no E12 inventory row found")
    else:
        line = row.group(0)
        if "未做" in line:
            fixed = ("| E12 学习曲线（1k→45k 训练量） | **已做（EXP-0028，见 L14 与表14）** | 合并增益 +0.0627（30× 训练量，"
                     "每十年 0.0402），但 config 间高度异质（Kimi-K2 +0.114 vs OSS +0.033）→ 小目录族应按 0.69-0.78 预期；"
                     "本行原写「未做」，是在 L14 成文后未回收的过期陈述 |")
            s = s.replace(line, fixed, 1)
            lim.write_text(s, encoding="utf-8", newline="")
            print("E12 inventory row corrected (was: " + line[:60] + "...)")
        else:
            print("E12 row already carries a completion marker; left as is")

    # the cross-check that justifies it
    print("  evidence that E12 exists:")
    reg = ROOT / "00_program_registry" / "experiment_registry.csv"
    rows = [r for r in csv.reader(io.StringIO(reg.read_text(encoding="utf-8"))) if r]
    hdr = rows[0]
    for r in rows[1:]:
        d = dict(zip(hdr, r))
        blob = " ".join(str(d.get(k, "")) for k in ("stage", "notes", "config"))
        if "EXP-0028" == d["exp_id"] or "learning" in blob.lower() or "学习曲线" in blob or "训练规模" in blob:
            print(f"    {d['exp_id']}: {d.get('status','')[:70]}")
    print("  L14 section present:", bool(re.search(r"^## L14 训练规模敏感性", lim.read_text(encoding="utf-8"), re.M)))

    print("=== claim-evidence path resolution, all five packages ===")
    tot = ok_all = 0
    for cm in sorted((ROOT / "papers").glob("P00*/claims_evidence_matrix.csv")):
        pre = ["", cm.parent.relative_to(ROOT).as_posix() + "/", ROOT.as_posix() + "/"]
        rows_c = list(csv.DictReader(io.StringIO(cm.read_text(encoding="utf-8"))))
        n = k = 0
        for r in rows_c:
            for col in ("raw_result_file", "table", "figure"):
                for part in (r.get(col) or "").split(";"):
                    q = part.strip()
                    if not q or q == "-":
                        continue
                    n += 1
                    if any(glob.glob(p + q) or pathlib.Path(p + q).exists() for p in pre):
                        k += 1
        tot += n
        ok_all += k
        print(f"    {cm.parent.name[:4]}: claims={len(rows_c):3d}  evidence paths={n:3d}  unresolved={n - k}")
    print(f"  TOTAL paths={tot} resolved={ok_all} unresolved={tot - ok_all}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
