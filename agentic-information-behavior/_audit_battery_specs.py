"""Scratch: which shipped battery artefacts were fitted a model with a duplicated column, or with NaN intervals.

`exp_wave1_battery.fit()` built its term list as [x] + covars without deduplicating, so any spec whose manipulated
variable is also a control fitted the same column twice and got a singular cluster-robust covariance. The battery is
shared by every wave, so the question is which shipped artefacts show the symptom.
"""
import glob
import json
import math
import pathlib

sup = {e["file"] for e in json.loads(pathlib.Path("results_raw/SUPERSEDED_ARTIFACTS.json").read_text(
    encoding="utf-8")).get("superseded", [])}
files = [f for f in sorted(glob.glob("results_raw/EXP0*battery*.json")) if pathlib.Path(f).name not in sup]
print(f"live battery artefacts: {len(files)}")


def walk(node, path=""):
    if isinstance(node, dict):
        if "beta" in node and ("se" in node or "ci_lo" in node):
            yield path, node
        for k, v in node.items():
            yield from walk(v, f"{path}/{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk(v, f"{path}[{i}]")


for f in files:
    a = json.loads(pathlib.Path(f).read_text(encoding="utf-8"))
    bad_nan = [p for p, m in walk(a) if any(isinstance(m.get(k), float) and not math.isfinite(m[k])
                                            for k in ("beta", "se", "ci_lo", "ci_hi", "p"))]
    allnull = [p for p, m in walk(a) if isinstance(m.get("beta"), float) and not math.isfinite(m["beta"])]
    print(f"  {pathlib.Path(f).name[:46]:46s} rows_with_non_finite_stat={len(bad_nan)} "
          f"{':: ' + '; '.join(bad_nan[:4]) if bad_nan else ''}")

# and which specs even have a manipulated term inside their own control list
import sys
sys.path.insert(0, "02_shared_code/package_factory")
for mod, wave in (("exp_wave1_battery", 1), ("exp_wave2_battery", 2), ("exp_wave3_battery", 3),
                  ("exp_wave4_battery", 4), ("exp_wave5_battery", 5)):
    try:
        m = __import__(mod)
    except Exception as e:                                      # noqa: BLE001
        print(f"  wave {wave}: {mod} not importable ({e})")
        continue
    sp = getattr(m, "SPEC", {})
    dup = {t: sorted(set(s.get("covars") or []) & {s.get("x")}) for t, s in sp.items() if s.get("x") in (
        s.get("covars") or [])}
    print(f"  wave {wave}: {len(sp)} topics, x_also_a_control=" + str({k: v for k, v in dup.items() if v} or "none"))
