"""Estate-wide read of every live design artefact for the two shapes a coefficient can take when it is not an estimate.

Wave 5 shipped a -3e15 coefficient with a NaN interval and a `null` verdict because a logit link was applied to a
continuous outcome. The same failure cannot only exist in wave 5, so this walks the artefacts the packages actually
cite (the newest per experiment id, minus the ones the supersession ledger excludes) and prints every row whose
coefficient is implausible or whose interval is not a number while a four-way verdict was still assigned.

    python _audit_coefficient_health.py
"""
import glob
import json
import math
import pathlib

FOUR_WAY = {"supported", "partial", "null", "opposite"}
sup = set()
led = pathlib.Path("results_raw/SUPERSEDED_ARTIFACTS.json")
if led.is_file():
    sup = {e["file"] for e in json.loads(led.read_text(encoding="utf-8")).get("superseded", [])}

latest = {}
for f in sorted(glob.glob("results_raw/EXP0*.json")):
    exp = pathlib.Path(f).name[:7]
    if pathlib.Path(f).name in sup:
        continue
    if not any(k in pathlib.Path(f).name for k in ("design", "main", "battery", "matrix")):
        continue
    latest[exp] = f                                    # sorted by timestamp in the filename, so the last wins

def hypothesis_rows(node, path=""):
    """Every dict that carries a verdict, wherever it sits: designs put them in `models`, batteries nest them per topic."""
    if isinstance(node, dict):
        if node.get("verdict") and (node.get("hypothesis") or node.get("term")):
            yield path, node
        for k, v in node.items():
            yield from hypothesis_rows(v, f"{path}/{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from hypothesis_rows(v, f"{path}[{i}]")


flagged = rows = 0
for exp, f in sorted(latest.items()):
    try:
        a = json.loads(pathlib.Path(f).read_text(encoding="utf-8"))
    except Exception as e:                              # noqa: BLE001
        print(f"{exp}: unreadable artefact {e}")
        continue
    for path, m in hypothesis_rows(a, exp):
        rows += 1
        b, lo, hi = m.get("beta"), m.get("ci_lo"), m.get("ci_hi")
        finite = [x for x in (b, lo, hi) if isinstance(x, (int, float)) and not isinstance(x, bool)]
        bad = []
        if any(isinstance(x, (int, float)) and not math.isfinite(float(x)) for x in (b, lo, hi)):
            bad.append("non_finite_value")
        if isinstance(b, (int, float)) and abs(float(b)) >= 1e3:
            bad.append("implausible_magnitude")
        if bad and m.get("verdict") in FOUR_WAY:
            flagged += 1
            print(f"  FLAG {path} {m.get('hypothesis')} {str(m.get('term'))[:40]}: verdict={m.get('verdict')} "
                  f"beta={b} ci=({lo},{hi}) p={m.get('p')} :: {', '.join(bad)}")
        elif bad:
            print(f"  noted {path} {m.get('hypothesis')}: verdict={m.get('verdict')} beta={b} "
                  f"ci=({lo},{hi}) :: {', '.join(bad)}")
print(f"live design artefacts={len(latest)} hypothesis rows={rows} rows needing a not_estimable label={flagged}")
