"""EXP-0050 (P005 sensitivity): how much of the "nothing below the card" result is the lexicon, not the files.

The main scan (EXP-0049) decided L6/L7 with one frozen regular expression (`PROV_KEYS`), which mixes two different
things: rights words (licence, copyright, attribution, redistribution) and provenance words (source, model, date,
repository). The union of column names that scan recorded — 42 distinct names across the eight releases — contains
`original_source`, `trace_source`, `model`, `model_provider`, `date`, `repo`, `game_file`, so a rights-absence
headline and a provenance-absence headline cannot both rest on that single regex. Step 4 of the research plan already
committed to re-deriving the instrument under stricter and looser matchers; this is that step, run against the column
sets the main scan stored, so no file is re-read and the comparison is exact.

Frozen before running:
  families   LICENCE  = licen[cs]e | copyright | attribut | redistribut | consent | notice | credit | owner |
                        holder | terms
             PROVENANCE = source | origin | original | provider | model | version | date | created | generated |
                        repo | instance | game_file | meta | path | split | subset | trace | teacher | annotator |
                        url | citation
  lexicons   NARROW = the main scan's regex (primary result, unchanged)
             BROAD  = the two families above, matched on the whole column/metadata key
  verdict    the paper may claim rights-absence below the card only if LICENCE stays 0/8 under BOTH lexicons; a
             PROVENANCE count that rises under the broad lexicon must be reported as a partial refutation of H1,
             not folded into the headline.
  component matcher sensitivity: strict (B3a) vs permissive (B3b) counts already stored per release; permissive is
             reported as an over-generating upper bound because it matches any proper name near a source word.

    python 02_shared_code/data_audit/governance_sensitivity_p005.py
"""
from __future__ import annotations

import json, pathlib, re, sys, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT, PROC = ROOT / "results_raw", ROOT / "results_processed"
sys.path.insert(0, str(ROOT / "02_shared_code" / "data_audit"))
import governance_metadata_pilot_p005 as G      # noqa: E402  (same NARROW regex as the main scan)

LICENCE = re.compile(r"(licen[cs]e|copyright|attribut|redistribut|consent|notice|credit|owner|holder|terms)", re.I)
PROVENANCE = re.compile(r"(source|origin|original|provider|model|version|date|created|generated|repo|instance|"
                        r"game_file|meta|path|split|subset|trace|teacher|annotator|url|citation)", re.I)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    src = sorted(OUT.glob("EXP0049_governance_census_*.json"))[-1]
    D = json.loads(src.read_text(encoding="utf-8"))
    R = D["releases"]
    res = {"exp_id": "EXP-0050", "paper_id": "P005", "derived_from": src.name,
           "rule": "rights-absence may be claimed only if LICENCE is 0 under both lexicons; a PROVENANCE rise under "
                   "the broad lexicon is reported as a partial refutation of H1",
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "per_release": []}
    fam_counts = {"licence": {"narrow": 0, "broad": 0}, "provenance": {"narrow": 0, "broad": 0}}
    for r in R:
        cols = r["all_column_names"] + r["L7_governance_metadata_keys"]
        row = {"corpus": r["corpus"], "n_keys": len(r["all_column_names"]),
               "narrow": sorted(c for c in cols if G.PROV_KEYS.search(c)),
               "licence_broad": sorted(c for c in cols if LICENCE.search(c)),
               "provenance_broad": sorted(c for c in cols if PROVENANCE.search(c))}
        row["licence_narrow"] = sorted(c for c in cols if LICENCE.search(c) and G.PROV_KEYS.search(c))
        row["provenance_narrow"] = sorted(c for c in cols if PROVENANCE.search(c) and G.PROV_KEYS.search(c)
                                          and not LICENCE.search(c))
        for fam in ("licence", "provenance"):
            fam_counts[fam]["narrow"] += 1 if row[f"{fam}_narrow"] else 0
            fam_counts[fam]["broad"] += 1 if row[f"{fam}_broad"] else 0
        row["components_strict_n"], row["components_permissive_n"] = len(r["components_strict"]), r["components_permissive_n"]
        res["per_release"].append(row)
        print(f"  {r['corpus']:13s} licence narrow/broad = {len(row['licence_narrow']):2d}/{len(row['licence_broad']):2d}   "
              f"provenance narrow/broad = {len(row['provenance_narrow']):2d}/{len(row['provenance_broad']):2d}")
    n = len(R)
    census = {}
    for fam, variants in fam_counts.items():
        census[fam] = {}
        for lex, k in variants.items():
            p, d = k / n, 1 + 1.96 ** 2 / n
            c = (p + 1.96 ** 2 / (2 * n)) / d
            h = 1.96 * (p * (1 - p) / n + 1.96 ** 2 / (4 * n * n)) ** .5 / d
            census[fam][lex] = {"k": k, "n": n, "wilson95": [round(max(0.0, c - h), 4), round(min(1.0, c + h), 4)],
                                "note": (f"0/{n} bounds the rate below {round(3 / n, 3) * 100:.0f}% (rule of three)"
                                         if k == 0 else "")}
    res["family_census"] = census
    res["rights_absence_survives_both_lexicons"] = bool(fam_counts["licence"]["narrow"] == 0 and fam_counts["licence"]["broad"] == 0)
    res["h1_partial_refutation"] = {"provenance_releases_narrow": fam_counts["provenance"]["narrow"],
                                    "provenance_releases_broad": fam_counts["provenance"]["broad"],
                                    "refutes_H1_if_broad_ge_4": fam_counts["provenance"]["broad"] >= 4,
                                    "note": "H1's establishing pattern counted L6 with the narrow lexicon; under the "
                                            "broad lexicon most releases do carry execution provenance, so the "
                                            "rights-only reading of H1 must be stated as a *licence-family* claim"}
    d2 = [i for r in R for i in r["disagreements"] if i["class"].startswith("D2")]
    obs = [o for r in R for o in r["observations"]]
    tests = [t for r in R for t in r.get("size_tests", [])]
    ratios = [t["ratio"] for t in tests if t.get("ratio") is not None]

    def fires(lo, hi):
        return sum(1 for x in ratios if not (lo <= x <= hi))
    res["d2_band_sensitivity"] = {
        "tests_executed": len(tests), "ratios_compared": len(ratios),
        "min_ratio": min(ratios) if ratios else None, "max_ratio": max(ratios) if ratios else None,
        "instances_at_frozen_band_pm25": fires(0.8, 1.25), "instances_at_pm10": fires(0.9, 1.1),
        "instances_at_pm100": fires(0.5, 2.0), "instances_at_exact_zero_tolerance": sum(1 for x in ratios if x != 1.0),
        "band_field_instances": len(d2), "declarations_unattributable_before_aggregate": len(obs),
        "informative": len(tests) >= 5,
        "note": "the band is varied over every declaration/row pair the main scan actually compared, not over the "
                "subset that fired, so a conclusion of robustness here is earned; the disagreements reported come "
                "from the card's own band field, which is a different measurement from the split-level sums"}
    res["component_matcher"] = {"strict": sum(r["components_strict_n"] for r in res["per_release"]),
                                "permissive": sum(r["components_permissive_n"] for r in res["per_release"]),
                                "note": "the permissive matcher over-generates (it accepts any proper name near a "
                                        "source word), so it is an upper bound and is never quoted as a count of "
                                        "components"}
    res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    out = OUT / f"EXP0050_governance_sensitivity_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8", newline="")
    with open(PROC / "EXP0050_lexicon_sensitivity.csv", "w", encoding="utf-8", newline="") as fh:
        fh.write("corpus,licence_narrow,licence_broad,provenance_narrow,provenance_broad,components_strict,components_permissive\n")
        for row in res["per_release"]:
            fh.write(",".join([row["corpus"], str(len(row["licence_narrow"])), str(len(row["licence_broad"])),
                               str(len(row["provenance_narrow"])), str(len(row["provenance_broad"])),
                               str(row["components_strict_n"]), str(row["components_permissive_n"])]) + "\n")
    print(json.dumps({"family_census": {f: c for f, c in fam_counts.items()},
                      "rights_survives": res["rights_absence_survives_both_lexicons"],
                      "h1": res["h1_partial_refutation"]["refutes_H1_if_broad_ge_4"],
                      "d2_informative": res["d2_band_sensitivity"]["informative"]}, ensure_ascii=False))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
