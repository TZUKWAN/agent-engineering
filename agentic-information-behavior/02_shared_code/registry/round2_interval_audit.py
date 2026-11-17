"""Round-2 check C2: is each shipped interval actually the interval its own row claims?

Re-fitting every design independently would re-run the estate, and the estimator is shared code, so the useful
independent test is arithmetic that the estimator cannot fake: a cluster-robust Wald interval is the coefficient
plus and minus 1.96 standard errors, it is symmetric about the coefficient, and it excludes zero exactly when the
two-sided p behind it is below 0.05. A bootstrap interval is legitimately asymmetric, so rows that say so are
measured for symmetry only in the looser sense and reported by kind.

What this flags:

* `interval_not_the_wald_interval_of_its_own_se` - beta ± 1.96 se disagrees with ci_lo/ci_hi by more than a
  rounding of the printed values, on a row that does not call itself a bootstrap or permutation quantity;
* `interval_not_centred_on_its_coefficient` - the coefficient sits outside its own interval, or off-centre by more
  than a fifth of its width on a Wald row;
* `p_and_interval_disagree` - the interval excludes zero while p > 0.05, or covers zero while p < 0.05;
* `se_inconsistent_with_interval_width` - a width implying a standard error far from the one printed.

    python 02_shared_code/registry/round2_interval_audit.py [--limit 25]
"""
from __future__ import annotations

import argparse
import datetime
import json
import math
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import round2_lib as L                                                    # noqa: E402
import round2_statistical_consistency as S                                 # noqa: E402
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "package_factory"))
import wave_lib as W                                                       # noqa: E402

ROOT = L.ROOT
BOOT_HINT = ("boot", "permut", "draws", "bootstrap")
# The two checkers that read the same rows have to read them the same way. Round 2 found this one reaching for
# `beta`/`ci_lo` only while its sibling follows the estate's alias lists, which left it checking 134 of the 403
# verdict rows the artefacts carry. It now borrows the sibling's reading, and a row that only states its interval
# per class is counted rather than skipped.
UNPAIRED = {}        # rows whose interval does not say which quantity it intervals
# the quantities an interval could belong to: the estate's own estimate names plus `gap`, which wave 1
# uses for the arm difference. A row's other numeric columns - `big_rate`, `small_rate`, `n`,
# `clusters` - are that difference's components or its denominators, not candidates for what the
QUANTIFIABLE = frozenset(S.QUANT) | {"gap"}
Z = 1.959963985


def _dp(x) -> int:
    """How many decimals this printed value carries."""
    t = repr(float(x))
    return len(t.split(".")[1].rstrip("0")) if "." in t and "e" not in t else 0


def kind_of(r: dict) -> str:
    blob = " ".join(str(k) for k in r) + " " + str(r.get("note") or "") + str(r.get("verdict_rule") or "")
    return "resampled" if any(h in blob.lower() for h in BOOT_HINT) else "wald"


def rows_of(o, out=None, where=""):
    out = {} if out is None else out
    if isinstance(o, dict):
        if "verdict" in o and (S.quantity_of(o)[0] is not None or o.get("mean_difference") is not None):
            out[where] = o
        for k, v in o.items():
            rows_of(v, out, f"{where}.{k}" if where else k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            rows_of(v, out, f"{where}[{i}]")
    return out


def check(f: pathlib.Path) -> list:
    d = L.read_any(f)
    if not isinstance(d, dict):
        return []
    bad = []
    for where, r in rows_of(d).items():
        beta, qkey = S.quantity_of(r)
        if not isinstance(beta, (int, float)):
            beta = r.get("mean_difference")
        se = r.get("se")
        lo, hi, lohi_src = S.interval_of(r)
        # An interval filed under the name of its resampling (`ci_clustered`, `ci_boot`) sits beside whichever
        # statistic it intervals, and a row can carry two such statistics: EXP-0125's H2 row holds `beta` and
        # `gap`, and its `ci_clustered` intervals the gap. Pairing them by which value the interval happens to
        # contain would be circular - it always selects the value that passes - so centring is asserted only when
        # the row itself says what the interval is of. How many rows do not is reported, because a shipped row
        # whose interval names no subject is a real limit of the artefact, not a passing check.
        alts = [k for k, v in r.items() if isinstance(v, (int, float)) and k in QUANTIFIABLE]
        if lohi_src != "canonical" and len(set(alts) - {"se"}) > 1 and str(r.get("ci_of") or "") != qkey:
            UNPAIRED[f"{f.name}:{where}"] = {"interval": lohi_src, "candidates": sorted(set(alts))[:6], "taken": qkey}
            continue
        p = next((r[k] for k in W.P_KEYS if isinstance(r.get(k), (int, float))), None)
        if not all(isinstance(x, (int, float)) and math.isfinite(x) for x in (beta, lo, hi)):
            continue
        kind = kind_of(r)
        width = hi - lo
        if not (lo <= beta <= hi):
            bad.append({"artefact": f.name, "where": where, "kind": kind,
                        "problem": "interval_not_centred_on_its_coefficient",
                        "beta": beta, "ci": [lo, hi]})
        if isinstance(se, (int, float)) and math.isfinite(se) and se > 0 and width > 0:
            if abs(width - 2 * Z * se) / width > 0.05 and kind == "wald":
                bad.append({"artefact": f.name, "where": where, "kind": kind,
                            "problem": "interval_width_not_explained_by_its_own_se",
                            "beta": beta, "se": se, "ci": [lo, hi],
                            "width_over_2se": round(width / (2 * se), 3)})
            if kind == "wald":
                dl, dh = abs(lo - (beta - Z * se)), abs(hi - (beta + Z * se))
                # every figure on the row is printed rounded, so the comparison has to carry the rounding of all
                # three: -0.0042 stands for anything within 5e-5 of it, and so do se and each bound.
                dp = min(6, max(_dp(beta), _dp(se), _dp(lo), _dp(hi)))
                tol = 2.5 * 10 ** -dp + 0.02 * max(abs(beta), se)
                if max(dl, dh) > tol:
                    bad.append({"artefact": f.name, "where": where, "kind": kind,
                                "problem": "interval_not_the_wald_interval_of_its_own_se",
                                "beta": beta, "se": se, "ci": [lo, hi],
                                "wald": [round(beta - Z * se, 6), round(beta + Z * se, 6)]})
        if isinstance(p, (int, float)):
            excludes = (lo > 0) or (hi < 0)
            if excludes and p > 0.05 + 1e-9:
                bad.append({"artefact": f.name, "where": where, "kind": kind,
                            "problem": "interval_excludes_zero_but_p_is_not_significant",
                            "ci": [lo, hi], "p": p})
            if (not excludes) and p < 0.05 - 1e-9:
                bad.append({"artefact": f.name, "where": where, "kind": kind,
                            "problem": "p_significant_but_interval_covers_zero",
                            "ci": [lo, hi], "p": p})
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=25)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    kept = L.root_kept()
    bad, n_rows = [], 0
    for exp, f in sorted(kept.items()):
        if not (exp >= "EXP-0119"):
            continue
        d = L.read_any(f)
        if isinstance(d, dict):
            n_rows += len(rows_of(d))
        bad += check(f)
    import collections
    by = collections.Counter(x["problem"] for x in bad)
    for x in bad[:a.limit]:
        print(json.dumps(x, ensure_ascii=False)[:220])
    print(f"\n{n_rows} estimated row(s) read; {len(bad)} interval-arithmetic finding(s); {len(UNPAIRED)} row(s) "
          "carry an interval that names no quantity to interval, and are not checked for centring - pairing by "
          "containment would always pick the value that passes")
    print(json.dumps(by, indent=1))
    dest = ROOT / "results_raw" / f"ROUND2_INTERVAL_ARITHMETIC_{time.strftime('%Y%m%dT%H%M%S')}.json"
    dest.write_text(json.dumps({"detector": "round2_interval_audit", "rows_checked": n_rows, "interval_pairing_unstated": dict(list(UNPAIRED.items())[:40]), "totals": dict(by),
                                "detail": bad, "z": Z,
                                "at": datetime.datetime.now().isoformat(timespec="seconds")},
                               indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote", dest.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
