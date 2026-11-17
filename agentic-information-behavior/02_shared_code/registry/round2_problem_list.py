"""Round-2 problem list: merge every detector's findings into one numbered, trackable document.

The point of the second pass is not more green checkmarks but a list a person can work down: each item names the
package or artefact, the class of defect, how many instances, the first examples, the severity, and its status.
Severity follows what the objective asks:

* **S1 - is the data real?** a number a package prints that no run of its own produced; a four-way verdict printed
  on an interval that is absent or not a number.
* **S2 - is the method checkable?** a verdict whose direction or Holm correction cannot be re-derived from the row
  the artefact ships; a shipped table cell left blank under a verdict.
* **S3 - is the experiment traceable?** a cited run whose artefact a reader cannot open inside the package.
* **S4 - hygiene.**

Status lives in `results_raw/ROUND2_PROBLEM_STATUS.json` keyed by item id, so re-running the detectors rebuilds
the list while keeping the resolution of items already worked - an item is only closed with a written reason and
the command or file that closed it.

    python 02_shared_code/registry/round2_problem_list.py [--open-only]
"""
from __future__ import annotations

import argparse
import collections
import datetime
import hashlib
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import round2_lib as L                                                    # noqa: E402

ROOT = L.ROOT
RAW = ROOT / "results_raw"
STATUS = RAW / "ROUND2_PROBLEM_STATUS.json"
DOC = ROOT / "docs" / "ROUND2_PROBLEM_LIST.md"
SEV = {"unsupported_prose_number": "S1", "unsupported_table_cell": "S1",
       "hypothesis_decision_is_both_or_neither": "S1",
       "four_way_verdict_on_a_non_finite_or_explosive_fit": "S1",
       "four_way_verdict_without_an_interval": "S1",
       "four_way_verdict_row_missing_fields": "S1",
       "four_way_verdict_with_an_empty_statistical_cell": "S1",
       "interval_width_inconsistent_with_se": "S2",
       "four_way_verdict_without_a_recorded_direction": "S2",
       "verdict_follows_a_non_default_rule": "S2",
       "verdict_not_implied_by_its_own_numbers": "S1",
       "holm_value_not_reproducible": "S1",
       "p_holm_below_the_declared_holm_family": "S1",
       "published_number_computed_from_rounded_inputs": "S2",
       "interval_stored_per_class_not_on_the_row": "S2",
       "cluster_ci_without_a_cluster_count": "S2",
       "cited_artefact_not_in_package": "S3",
       "run_has_no_script_that_can_be_rerun": "S3",
       "no_kept_artefact_for_a_registered_run": "S3",
       "declared_output_glob_matches_nothing": "S3",
       "artefact_files_under_a_different_id": "S3",
       "registry_row_names_no_output_glob": "S3",
       "registered_script_not_on_disk": "S3",
       "superseded_row_names_a_run_that_is_not_registered": "S3",
       "successor_run_has_no_artefact_either": "S3",
       "package_copy_differs_from_the_programme_artefact": "S2",
       "package_ships_only_a_superseded_generation": "S2",
       "recorded_command_line_does_not_name_the_registered_script": "S3",
       "row_seed_differs_from_the_run": "S2",
       "finished_before_it_started": "S4",
       "registry_window_reversed": "S4",
       "registry_row_carries_no_window_kind": "S4",
       "registered_window_not_corroborated_by_any_output": "S3",
       "registered_instant_not_corroborated_by_any_output": "S3",
       "file_count_differs": "S1",
       "row_count_differs": "S1",
       "no_data_files_found": "S1",
       "shard_unreadable": "S1",
       "release_directory_not_on_disk": "S1",
       "manifest_lists_columns_the_release_does_not_have": "S1",
       "config_not_separable_on_disk": "S2",
       "config_separated_only_by_a_column": "S2",
       "cited_table_not_in_package": "S3",
       "cited_figure_not_in_package": "S3",
       "prose_names_a_path_the_package_does_not_hold": "S3",
       "raw_result_file_does_not_resolve": "S3",
       "claim_direction_contradicts_the_shipped_verdict": "S1",
       "reported_digits_not_carried_by_the_package": "S1",
       "interval_arithmetic_inconsistent": "S2",
       "degenerate_table": "S4"}
# every detector the round-2 sweep runs, and the count each one reports for its own coverage
DETECTORS = (("ROUND2_NUMBER_PROVENANCE_*.json", "round2_number_provenance", "packages"),
             ("ROUND2_STAT_CONSISTENCY_*.json", "round2_statistical_consistency", "artefacts"),
             ("ROUND2_STAT_CONSISTENCY_*.json", "round2_statistical_consistency_shipped_tables", "tables_scanned"),
             ("ROUND2_CORPUS_REMEASURE_*.json", "round2_corpus_remeasurement", "configs_checked"),
             ("ROUND2_RUN_REALITY_*.json", "round2_run_reality", "rows_checked"),
             ("ROUND2_CLAIM_SUPPORT_*.json", "round2_claim_support", "claims_checked"),
             ("ROUND2_INTERVAL_ARITHMETIC_*.json", "round2_interval_audit", "rows_checked"),
             ("EXP0235_derivation_precision_*.json", "round2_derivation_precision", "writers_read"))


def latest(pattern: str):
    f = sorted(RAW.glob(pattern), key=lambda p: p.stat().st_mtime)
    return f[-1] if f else None


def items() -> list:
    out = []
    pv = latest("ROUND2_NUMBER_PROVENANCE_*.json") or latest("ROUND2_PROVENANCE_*.json")
    if pv:
        d = json.loads(pv.read_text(encoding="utf-8"))
        for pkg, v in sorted(d["detail"].items()):
            if v["unsupported_table_cells"]:
                out.append({"key": f"{pkg}|unsupported_table_cell", "sev": "S1", "where": pkg,
                            "n": len(v["unsupported_table_cells"]),
                            "examples": [f"{x['table']}[{x['column']}]={x['value']}"
                                         for x in v["unsupported_table_cells"][:4]]})
            if v["unsupported_prose_numbers"]:
                docs = sorted({x["doc"] for x in v["unsupported_prose_numbers"]})
                out.append({"key": f"{pkg}|unsupported_prose_number", "sev": "S1", "where": pkg,
                            "n": len(v["unsupported_prose_numbers"]),
                            "examples": [f"{x['doc']}:{x['value']} :: {x['context'][:70]}"
                                         for x in v["unsupported_prose_numbers"][:4]], "note": ",".join(docs)})
            if v.get("cited_exps_not_in_package"):
                out.append({"key": f"{pkg}|cited_artefact_not_in_package", "sev": "S3", "where": pkg,
                            "n": len(v["cited_exps_not_in_package"]),
                            "examples": v["cited_exps_not_in_package"][:8]})
            if v.get("degenerate_tables"):
                # round 2's own lesson, applied to this file: the widened table scope found shipped result tables
                # that carry no measurement, and the merge silently dropped them because no branch read that key.
                # A list of problems that loses a detector's findings is worse than the unchecked table.
                byp = collections.defaultdict(list)
                for x in v["degenerate_tables"]:
                    byp[x["problem"]].append(f"{x['table']}: {str(x.get('first_row'))[:90]}")
                for prob, xs in sorted(byp.items()):
                    out.append({"key": f"{pkg}|{prob}", "sev": SEV.get(prob, "S4"), "where": pkg,
                                "n": len(xs), "examples": xs[:4]})
    st = latest("ROUND2_STAT_CONSISTENCY_*.json")
    if st:
        d = json.loads(st.read_text(encoding="utf-8"))
        for art, rows in sorted(d["detail"].items()):
            grp = {}
            for x in rows:
                grp.setdefault(x["problem"], []).append(x)
            for prob, xs in sorted(grp.items()):
                out.append({"key": f"{art}|{prob}", "sev": SEV.get(prob, "S4"), "where": art,
                            "n": len(xs), "examples": [json.dumps(x, ensure_ascii=False)[:150] for x in xs[:3]]})
        for tab, rows in sorted((d.get("table_detail") or {}).items()):
            grp = {}
            for x in rows:
                grp.setdefault(x["problem"], []).append(x)
            for prob, xs in sorted(grp.items()):
                out.append({"key": f"{tab}|{prob}", "sev": SEV.get(prob, "S1"), "where": tab, "n": len(xs),
                            "examples": [f"row {x.get('row')} column {x.get('column')} verdict {x.get('verdict')}"
                                         for x in xs[:4]]})
    # the other four detectors all report the same flat shape: a `detail` list of {"problem": ..., one field
    # naming the thing the finding is about}. Merging them here is what makes this document the whole round-2
    # list rather than the list two of the six detectors produced.
    for pat, name, field in (("ROUND2_CORPUS_REMEASURE_*.json", "corpus", "dataset"),
                             ("ROUND2_RUN_REALITY_*.json", "runs", "exp"),
                             ("ROUND2_CLAIM_SUPPORT_*.json", "claims", "package"),
                             ("ROUND2_INTERVAL_ARITHMETIC_*.json", "intervals", "row"),
                             ("EXP0235_derivation_precision_*.json", "derivations", "file")):
        f = latest(pat)
        if not f:
            continue
        for x in json.loads(f.read_text(encoding="utf-8")).get("detail") or []:
            where = str(x.get(field) or x.get("package") or x.get("exp") or x.get("dataset") or name)
            out.append({"key": f"{where}|{x.get('problem', 'finding')}", "sev": SEV.get(x.get("problem") or "", "S4"),
                        "where": where, "n": 1,
                        "examples": [json.dumps({k: v for k, v in x.items()
                                                 if k not in ("problem", field)}, ensure_ascii=False)[:200]]})
    return out


def checks() -> list:
    """One line per detector: what it read, what it found, and where the report is.

    A check that found nothing is still a result, and the problem list is the only place a reader of the second
    pass can see which questions were asked. Without this the list would silently shrink to the detectors that are
    currently complaining.
    """
    rows = []
    for pat, name, cov in DETECTORS:
        f = latest(pat)
        if not f:
            rows.append({"detector": name, "report": "not run", "coverage": "-", "findings": "-"})
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        cov_n = d.get(cov)
        if isinstance(cov_n, dict):
            cov_n = len(cov_n)
        rows.append({"detector": name, "report": f.name, "coverage": str(cov_n if cov_n is not None else "?"),
                     "findings": sum((d.get("totals") or {}).values()) if isinstance(d.get("totals"), dict)
                     else len(d.get("detail") or [])})
    return rows


def merge(its: list) -> list:
    """One item per (place, defect class), whatever order the detectors reported them in."""
    by = {}
    for x in its:
        y = by.get(x["key"])
        if y is None:
            by[x["key"]] = dict(x)
            continue
        y["n"] += x["n"]
        y["examples"] = (y["examples"] + x["examples"])[:4]
        y["note"] = ",".join(sorted({v for k in (y.get("note"), x.get("note")) for v in (k or "").split(",") if v}))
    return list(by.values())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--open-only", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    stat = json.loads(STATUS.read_text(encoding="utf-8")) if STATUS.is_file() else {}
    its = merge(items())
    its.sort(key=lambda x: (x["sev"], -x["n"], x["key"]))
    for i, x in enumerate(its, 1):
        # an id derived from the item's own key, not from its position: a positional id changes meaning every time
        # an item is resolved or a new detector speaks up, which makes it useless in a written resolution note
        slug = hashlib.sha1(x["key"].encode("utf-8")).hexdigest()[:6].upper()
        x["id"], x["no"] = f"R2-{x['sev']}-{slug}", i
        # a status may be recorded for the exact item, or once for the whole problem class with the reason the
        # class is not a defect (the word-only tables) - both are legitimate, and the list shows which was used
        problem = x["key"].split("|")[-1]
        s = (stat.get(x["key"]) or stat.get(f"{problem}|class_triage") or stat.get(f"{problem}|fix")
             or stat.get(f"{problem}|class_fix")
             or stat.get(f"{x['where']}|{problem}") or {})
        x["status"], x["resolution"] = s.get("status", "open"), s.get("resolution", "")
    if a.open_only:
        its = [x for x in its if x["status"] == "open"]
    counts = {}
    for x in its:
        counts[x["status"]] = counts.get(x["status"], 0) + 1
    ck = checks()
    L_ = ["# Round-2 verification problem list", "",
          f"Generated by `02_shared_code/registry/round2_problem_list.py` at "
          f"{datetime.datetime.now().isoformat(timespec='seconds')}; statuses come from "
          "`results_raw/ROUND2_PROBLEM_STATUS.json`. Do not hand-edit this file.", "",
          f"Severity: S1 the data or the verdict itself, S2 the method cannot be re-checked from what is shipped, "
          "S3 the run cannot be opened inside the package, S4 hygiene.", "",
          "## What the six detectors covered, and what each one found", "",
          "| detector | read | report | findings |", "|---|---|---|---|"]
    for c in ck:
        L_.append(f"| `{c['detector']}` | {c['coverage']} | `{c['report']}` | {c['findings']} |")
    L_ += ["", f"## Open and resolved items", "",
           f"**{len(its)} item(s): " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) + "**", "",
           "| # | id | sev | where | instances | status |", "|---|---|---|---|---|---|"]
    for x in its:
        L_.append(f"| {x['no']} | {x['id']} | {x['sev']} | `{x['where'][:58]}` | {x['n']} | {x['status']} |")
    L_ += ["", "## Details", ""]
    for x in its:
        L_ += [f"### {x['id']} · {x['key'].split('|')[1]} · `{x['where']}`",
               f"* instances: {x['n']} · severity {x['sev']} · status **{x['status']}**"]
        if x.get("note"):
            L_.append(f"* docs involved: {x['note']}")
        L_ += [f"  - `{str(e)[:200]}`" for e in x["examples"]]
        if x["resolution"]:
            L_.append(f"* resolution: {x['resolution']}")
        L_.append("")
    if not a.open_only:
        L_ += ["## Resolved (no longer detected; kept so the round is auditable)", ""]
        live = {x["key"] for x in merge(items())}
        for key, v in sorted(stat.items()):
            if key in live or not isinstance(v, dict):
                continue
            L_ += [f"### `{key}`", f"* status **{v.get('status')}** at {v.get('at', '')}",
                   f"* {v.get('resolution', '')}", ""]
    DOC.parent.mkdir(exist_ok=True)
    DOC.write_text("\n".join(L_) + "\n", encoding="utf-8")
    print(f"wrote {DOC.relative_to(ROOT)}: {len(its)} item(s), {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
