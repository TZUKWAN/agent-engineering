"""Round-2 check: where does a published number come from - a measurement, or a rounding of a rounding?

Two of round 2's three genuine data-truth defects had the same shape, and neither was caught by asking whether the
printed figure appears somewhere in an artefact:

* P001 and P003 published **63.7-88.1%** of test rows sharing a catalogue with development. `EXP-0018`'s record
  stores `share: 0.8805`, itself rounded from 3941/4476 = 88.0474%; turning the stored 0.8805 into a percentage and
  rounding again gives 88.1, while the measured value to one decimal is 88.0.
* P002's pilot gate prints **1.367 bits/trajectory** as `round(0.0916 * round(298359/20000, 2), 3)` - the record's
  4-decimal per-turn delta times a trajectory length rounded to two decimals inside the report script, a number
  (14.92) the record does not contain (it stores 14.918). Full precision gives 1.3665, which prints as 1.366.

Both figures match *something* on disk loosely enough to look plausible and both were reachable by a reader only
through a chain of roundings that exists in the writer, not in the data. This scans the estate's own writers for
that chain: an arithmetic expression whose operands are, or resolve to, values that were already rounded - and
reports the file, the line, the expression, and how deep the chain goes. It is static on purpose. A rounding chain
is a property of the code that publishes the number, so it should be found by reading that code rather than by
waiting for the rounded result to fall outside some tolerance.

    python 02_shared_code/registry/round2_derivation_precision.py [--limit 40]
"""
from __future__ import annotations

import argparse
import ast
import datetime
import json
import pathlib
import re
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "02_shared_code" / "package_factory"))
import round2_lib as L                                                    # noqa: E402

ROOT = L.ROOT
EXP = "EXP-0235"
# `round(x, k)` applied to something that is already a rounded quantity. `int()` is not a rounding of a measurement
# in the same sense, and `float()` is a cast, so neither counts as a link in the chain.
ROUND_CALL = re.compile(r"\bround\(")


class _StripStrings(ast.NodeTransformer):
    """Blank out string literals, so prose that merely contains the word `round(` or a column name like
    `usable_agree` inside a subscript cannot be read as arithmetic. Without this the first run of this check
    reported six "rounding chains" that were really document writers calling `.replace()` on sentences."""

    def visit_Constant(self, node):
        return ast.copy_location(ast.Constant(value="" if isinstance(node.value, str) else node.value,
                                              kind=None), node)


def code(node: ast.AST) -> str:
    return ast.unparse(_StripStrings().visit(ast.parse(ast.unparse(node), mode="eval")).body)


def rounded_names(tree: ast.AST) -> dict:
    """{name: (expression source, line)} for every binding in this module whose value is a round(...) call."""
    out = {}
    for n in ast.walk(tree):
        targets = []
        if isinstance(n, (ast.Assign, ast.AugAssign)):
            targets = n.targets if isinstance(n, ast.Assign) else [n.target]
            value = n.value
        elif isinstance(n, ast.AnnAssign) and n.value is not None:
            targets, value = [n.target], n.value
        else:
            continue
        if not ROUND_CALL.search(code(value)):
            continue
        for t in targets:
            if isinstance(t, ast.Name):
                out[t.id] = (code(value), getattr(n, "lineno", 0))
    return out


def arithmetic(node: ast.AST) -> list:
    """The binary +-*/ subtrees of an expression, innermost first."""
    out = []
    if isinstance(node, (ast.BinOp,)):
        out.append(node)
        out += arithmetic(node.left) + arithmetic(node.right)
    return out


def operands(node: ast.BinOp) -> list:
    return [node.left, node.right]


def chain_depth(expr: str, names: dict, seen=()) -> int:
    """How many links of rounding an expression sits behind: 0 if it is itself raw."""
    hits = []
    for m in re.finditer(r"\b([A-Za-z_][\w.]*)\b", expr):
        nm = m.group(1).split(".")[0]
        if nm in seen or nm not in names:
            continue
        hits.append(1 + chain_depth(names[nm][0], names, seen + (nm,)))
    return max(hits) if hits else 0


def scan(path: pathlib.Path) -> list:
    """Every rounded-result assignment in one file whose inputs are themselves rounded values."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, OSError, ValueError):
        return []
    names = rounded_names(tree)
    out = []
    for n in ast.walk(tree):
        if not isinstance(n, (ast.Assign, ast.Return, ast.Expr)):
            continue
        value = n.value if isinstance(n, (ast.Assign, ast.Return, ast.Expr)) else None
        if value is None:
            continue
        src = code(value)
        if not ROUND_CALL.search(src):
            continue
        # the expression inside round(...): what is being rounded here?
        inner = None
        for c in ast.walk(value):
            if isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id == "round" and c.args:
                inner = c.args[0]
                break
        if inner is None or not arithmetic(inner):
            continue
        refs = [m.group(1).split(".")[0] for m in re.finditer(r"\b([A-Za-z_][\w.]*)\b", code(inner))]
        rounded_inputs = sorted({r for r in refs if r in names})
        if not rounded_inputs:
            continue
        out.append({"problem": "published_number_computed_from_rounded_inputs",
                    "file": str(path.relative_to(ROOT)).replace(chr(92), "/"), "line": getattr(n, "lineno", 0),
                    "expression": src[:200], "rounded_inputs": rounded_inputs[:6],
                    "depth": 1 + chain_depth(code(inner), names),
                    "inputs_defined_at": {r: names[r][1] for r in rounded_inputs[:4]}})
    return out


def writers() -> list:
    """The scripts that put numbers into packages: every package's own `scripts/`, plus the programme's writers."""
    files = []
    for pkg in L.packages():
        files += sorted((pkg / "scripts").glob("*.py"))
    for sub in ("registry", "package_factory", "behavior_tagger", "statistics", "data_audit", "trajectory_parser"):
        files += sorted((ROOT / "02_shared_code" / sub).glob("*.py"))
    return [f for f in files if f.is_file()]


def ensure_row(started: str, finished: str) -> None:
    """Carry this run in the master register before it writes, so its own report is never its only record."""
    import csv
    import io
    reg = ROOT / "00_program_registry" / "experiment_registry.csv"
    rows = list(csv.DictReader(io.StringIO(reg.read_text(encoding="utf-8"))))
    cols = list(rows[0])
    hit = next((r for r in rows if r["exp_id"] == EXP), None)
    if hit is None:
        hit = {c: "" for c in cols}
        hit["exp_id"] = EXP
        rows.append(hit)
    want = {"paper_id": "programme", "stage": "round2_derivation_precision_scan",
            "script": "02_shared_code/registry/round2_derivation_precision.py",
            "config": "every writer that puts a number into a package: each package's own `scripts/`, plus "
                      "02_shared_code/{registry,package_factory,behavior_tagger,statistics,data_audit,"
                      "trajectory_parser}. Read as syntax trees, with string literals blanked so prose that "
                      "mentions `round(` is not read as arithmetic. No measurement is taken and no package is "
                      "written by this run",
            "seed": "n/a (a static scan)", "started_at": started, "finished_at": finished,
            "status": "derivation_chains_reported",
            "outputs": "results_raw/EXP0235_derivation_precision_*.json", "enters_paper": "no",
            "notes": "round-2: built from two real defects of this shape - P002's 1.367 bits/trajectory (a 2-dp "
                     "turns-per-trajectory that no record stores) and the 88.1% catalogue share (a double rounding "
                     "of a 4-dp share field); the estate's own published figure for that share is 88.0%"}
    n = 0
    for k, v in want.items():
        if k in cols and hit.get(k) != v:
            hit[k] = v
            n += 1
    if not n:
        return
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator=chr(10))
    w.writeheader()
    for r in rows:
        w.writerow({c: str(r.get(c) or "") for c in cols})
    reg.write_text(buf.getvalue(), encoding="utf-8")
    print(f"registry: {EXP} row set ({n} field(s) written)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--check", action="store_true", help="write the report but not the register row")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    t0 = time.time()
    started = datetime.datetime.now().isoformat(timespec="seconds")
    if not a.check:
        ensure_row(started, started)
    files = writers()
    found, scanned = [], 0
    for f in files:
        rows = scan(f)
        scanned += 1
        found += rows
    deep = [x for x in found if x["depth"] >= 2]
    for x in found[:a.limit]:
        print(json.dumps(x, ensure_ascii=False)[:220])
    print(f"\n{scanned} writer(s) read; {len(found)} assignment(s) publish a round() of an already-rounded "
          f"quantity, {len(deep)} of them behind two or more rounding links")
    worst = [{"where": d["file"] + ":" + str(d["line"]), "depth": d["depth"]}
             for d in sorted(deep, key=lambda y: -y["depth"])[:6]]
    print("worst offenders: " + json.dumps(worst))
    dest = (ROOT / "results_raw" / f"EXP0235_derivation_precision_CHECK_{time.strftime('%Y%m%dT%H%M%S')}.json"
            if a.check else
            ROOT / "results_raw" / f"EXP0235_derivation_precision_{time.strftime('%Y%m%dT%H%M%S')}.json")
    dest.write_text(json.dumps({"exp_id": EXP, "detector": "round2_derivation_precision", "seed": "n/a (a static "
                                "scan of the estate's own writers)", "started_at": started,
                                "finished_at": datetime.datetime.now().isoformat(timespec="seconds"),
                                "wallclock_sec": round(time.time() - t0, 1), "writers_read": scanned,
                                "totals": {"rounding_chains": len(found), "chains_of_depth_2_plus": len(deep)},
                                "detail": found,
                                "meaning": "a published figure computed from values that were already rounded is "
                                           "reproducible only by repeating the writer's rounding, not from the data"},
                               indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote", dest.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
