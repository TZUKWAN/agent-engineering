"""What the provenance matcher accepts that no measurement produced, before and after the narrowing.

A one-digit perturbation of a four-decimal figure is a poor model of an invented number: the pool of a package holds
tens of thousands of four-decimal shares, so the neighbourhood of almost every value in [0, 1] already contains a real
measurement, and accepting a figure that differs from one by one unit in the last place is the correct behaviour for a
matcher that must survive rounding. The clean question is the unrelated number: take figures the package never
measured - random values in the range its statistics live in - and see how many pass.

Both are reported, plus the acceptance rate of the package's own table figures, so the three are read together.
"""
import pathlib, sys, random, collections
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(pathlib.Path("02_shared_code/registry").resolve()))
import round2_lib as L

L.FROZEN = L.frozen_constants()
random.seed(3)
tot = collections.Counter()
for name in ("P001", "P005", "P023", "P045", "P070"):
    pkg = next((p for p in L.packages() if p.name.startswith(name)), None)
    if pkg is None:
        continue
    art, tbl, _s, groups, colsums = L.value_pool(pkg)
    pools = L.Pools(art, tbl, groups, colsums)
    kinds = collections.Counter()
    for _ in range(300):
        v = round(random.uniform(-2, 3), 4)
        r = L.support(v, 4, pools, "")
        kinds["pass" if r else "reject"] += 1
        if r:
            kinds[r.split("(")[0]] += 1
    tot["n"] += 300
    tot["pass"] += kinds["pass"]
    for k in ("derived", "table", "artefact"):
        tot[k] += kinds[k]
    # the same matcher must still accept every figure the package's own tables print, or the narrowing has thrown
    # away legitimate derivations rather than only the accidental ones
    own = collections.Counter()
    import csv, io
    for f in sorted((pkg / "tables").glob("table*.csv"))[:14]:
        for row in L.read_any(f) or []:
            for _k, val in (row or {}).items():
                if val in (None, ""):
                    continue
                s = str(val)
                try:
                    x = float(s.replace(",", "").rstrip("%"))
                except ValueError:
                    continue
                dp = len((s.rstrip("%").split(".")[1])) if "." in s else 0
                own["n"] += 1
                own["ok"] += bool(L.support(x, min(dp, 6), pools, ""))
    print(f"{pkg.name[:38]:38s} random 4-dp accepted {kinds['pass']:4d}/300 = {kinds['pass']/3:.3f}"
          f"  (rowops={len(pools.rowops):9d} pool={len(art)+len(tbl):7d}) by branch: "
          f"derived={kinds['derived']} table={kinds['table']} artefact={kinds['artefact']}"
          f" | own numeric table cells accepted {own['ok']}/{own['n']}")
print(f"TOTAL random-figure acceptance: {tot['pass']}/{tot['n']} = {tot['pass']/tot['n']:.3f} "
      f"| branches: derived={tot['derived']} table={tot['table']} artefact={tot['artefact']}")
