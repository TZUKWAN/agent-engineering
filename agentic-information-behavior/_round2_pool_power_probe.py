"""Second control for the provenance detector: what would it fail to catch?

The first control measured acceptance of a package's own table numbers against a foreign package's pool: 95.0 %
accepted, which by itself looks like a check with no power. That number needs the right baseline, because the estate's
packages genuinely share evidence - every package of a wave cites that wave's feature matrix and the programme's
censuses - so a foreign real number often *is* present in this package's evidence base too.

The question the detector actually answers is "was this figure produced by a measurement, or written by hand". So the
second control perturbs each number the way a fabricated figure would be: one digit changed, and separately a value
shifted in the last printed place. A detector with power rejects nearly all of those while accepting the untouched
value. Both controls are reported together with the overlap between two packages' pools, which is what makes the
95 % figure interpretable.

Read-only; nothing here writes into the estate.
"""
import pathlib, sys, random, collections
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(pathlib.Path("02_shared_code/registry").resolve()))
import round2_lib as L

ROOT = L.ROOT
L.FROZEN = L.frozen_constants()
pkgs = [p for p in L.packages()][:24]
random.seed(7)


def table_numbers(pkg):
    out = []
    for f in sorted((pkg / "tables").glob("table*.csv")):
        for r in L.read_any(f) or []:
            for k, val in (r or {}).items():
                if val in (None, ""):
                    continue
                s = str(val)
                try:
                    v = float(s.replace(",", "").rstrip("%"))
                except ValueError:
                    for v2, dp2, _c in L.numbers_in(s):
                        out.append((f.name, v2, min(dp2, 6)))
                    continue
                dp = len((s.rstrip("%").split(".")[1])) if "." in s else 0
                out.append((f.name, v, min(dp, 6)))
    return out


pools, nums = {}, {}
for p in pkgs:
    art, tbl, _s, groups, colsums = L.value_pool(p)
    pools[p.name] = L.Pools(art, tbl, groups, colsums)
    nums[p.name] = table_numbers(p)


def bump(v, dp):
    """Same magnitude, one digit changed in the last printed place."""
    if dp == 0:
        return v + (1 if v >= 0 else -1) * (abs(v) // 10 or 1)          # shift one digit of an integer
    step = 10.0 ** -dp
    d = int(round(abs(v) / step)) % 10
    return round(v + step * ((d + 3) % 10 and 1 or 2) * (1 if v >= 0 else -1), dp)


res = collections.Counter()
tots = collections.Counter()
by_dp = collections.defaultdict(collections.Counter)
shared = []
for i, p in enumerate(pkgs):
    mine = [x for x in nums[p.name] if abs(x[1]) > L.SMALL_STRUCTURAL or not float(x[1]).is_integer()]
    other = pools[pkgs[(i + 7) % len(pkgs)].name]
    shared.append(len(set(pools[p.name].art) & set(other.art)) / max(1, len(set(other.art))))
    for tab, v, dp in random.sample(mine, min(60, len(mine))):
        tots["n"] += 1
        ok_own = bool(L.support(v, dp, pools[p.name], ""))
        ok_pert = bool(L.support(bump(v, dp), dp, pools[p.name], ""))
        ok_pert_for = bool(L.support(bump(v, dp), dp, other, ""))
        res["own_exact"] += ok_own
        res["perturbed_own"] += ok_pert
        res["perturbed_foreign"] += ok_pert_for
        by_dp[dp]["n"] += 1
        by_dp[dp]["pert_accepted"] += ok_pert
print(f"sampled table figures: {tots['n']}")
print(f"  exact value accepted by its own package ......... {res['own_exact']}/{tots['n']}"
      f" = {res['own_exact']/tots['n']:.3f}")
print(f"  one-digit-perturbed value accepted by own pkg ... {res['perturbed_own']}/{tots['n']}"
      f" = {res['perturbed_own']/tots['n']:.3f}   <- the detector's power against an invented figure")
print(f"  perturbed value accepted by a foreign pool ...... {res['perturbed_foreign']}/{tots['n']}"
      f" = {res['perturbed_foreign']/tots['n']:.3f}")
print(f"  mean share of a foreign pool that this pool also holds: {sum(shared)/len(shared):.3f}"
      "  (shared wave evidence, not a bug)")
print("  acceptance of the perturbed value by printed precision:",
      {dp: f"{c['pert_accepted']}/{c['n']}" for dp, c in sorted(by_dp.items())})
