"""EXP-0142: the wave-3 premise census, run before any wave-3 outcome exists.

Wave 3 has five designs whose dependent variables are either a rank change under a rule rewrite (T113, T120) or a
column that has to exist in the catalogue text (T118's name segments, T119's contradiction cell, T122's neighbours).
Each of those can be silently absent - a synonym map that covers nothing, names that are all single-segment, a
negation vocabulary that never fires - and then the design would print a confident number about an empty set. This
census measures each quantity the gates are written against, and nothing else: no relationship between a feature and
an outcome is estimated here, so no threshold in `topic_designs_wave3.py` is informed by a result.

    python 02_shared_code/package_factory/probe_wave3_premises.py
"""
from __future__ import annotations

import datetime
import json
import pathlib
import sys

import numpy as np
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import wave_lib as W                                              # noqa: E402
import topic_designs_wave3 as TD3                                 # noqa: E402

def prior_negation_share():
    """The negation prevalence EXP-0135 already measured, read from its artefact rather than re-measured."""
    f = sorted((W.ROOT / "results_raw").glob("EXP0135_wave2_premise_census_*.json"),
               key=lambda x: x.stat().st_mtime)
    if not f:
        return None
    return json.loads(f[-1].read_text(encoding="utf-8")).get("measured", {}).get("negation_marker_share_of_candidates")


ROWS = 4000                                        # bounded: the census is about prevalence, not about effects


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    out = {"exp_id": "EXP-0142", "seed": W.SEED, "rows_census": ROWS,
           "started_at": W.now(), "measured": {}, "kill_gates": {}, "inherited_blocks": {}}
    d = W.load_routing(cfgs=W.CONFIGS, bucket="dev")
    d = d[d["subset_name"].astype(str).str.contains("single-turn-original", na=False)].head(ROWS)
    seg_n, contra, synth_rows, rows_seen, change_pcts, neigh_ok, neigh_n = (
        [], 0, 0, 0, [], 0, [])
    for r in d.itertuples(index=False):
        ent = W.read_catalog(r.catalog_json, r.n_candidates, r.query_id)
        if not ent:
            continue
        rows_seen += 1
        q = str(r.question)
        qm = W.constraint_markers(q)
        touched = False
        for e in ent:
            name, desc = str(e.get("name") or ""), str(e.get("desc") or "")
            seg_n.append(len([x for x in name.split("-") if x.strip()]))
            # T113's rewrite arm: how much text does the template add?
            rewritten = W.usecase_frame(name, desc, e.get("params") or [])
            if W.toks(desc) and W.toks(rewritten):
                change_pcts.append(len(W.toks(rewritten)) / len(W.toks(desc)) - 1.0)
            # T120's arm: does the frozen synonym map actually touch this description?
            if W.apply_syn_map(desc) != desc:
                touched = True
            # T119's contradiction cell: name asserts a family the description negates
            nm, dm = W.constraint_markers(name), W.constraint_markers(desc)
            if any(nm[f] > 0 and dm[f] == 0 and W.NEG_MARK.search(desc) for f in
                   ("temporal", "numeric", "format", "scope")):
                contra += 1
        synth_rows += int(touched)
        # T122: does this query's catalogue have neighbours at all?
        neigh_n.append(len(ent))
        neigh_ok += int(len(ent) >= 3)
    med_seg = float(np.median(seg_n)) if seg_n else 0.0
    share_multi = round(float(np.mean([s > 1 for s in seg_n])), 4) if seg_n else None
    med_change = round(float(np.median(np.abs(change_pcts))), 4) if change_pcts else None
    syn_share = round(synth_rows / max(1, rows_seen), 4)
    thin = round(float(np.mean([n < 3 for n in neigh_n])), 4) if neigh_n else None
    out["measured"] = {
        "rows_census_actual": rows_seen,
        "T113_median_abs_token_change_of_usecase_rewrite_pct": med_change,
        "T118_median_name_segments": med_seg,
        "T118_share_of_entries_with_more_than_one_segment": share_multi,
        "T119_candidate_rows_with_name_asserting_a_family_the_description_negates": contra,
        "T120_share_of_queries_with_any_description_the_synonym_map_touches": syn_share,
        "T122_share_of_queries_with_fewer_than_three_candidates": thin,
        "T122_median_catalogue_size": (float(np.median(neigh_n)) if neigh_n else None),
        "T121_negation_share_of_candidate_descriptions": prior_negation_share(),
    }
    M = out["measured"]
    out["kill_gates"] = {
        # each value answers "is this premise measurable?", so False is the blocked case
        "T113_rewrite_length_within_tolerance": bool(med_change is not None and med_change <= 0.40),
        "T118_hierarchy_exists": bool(share_multi is not None and share_multi >= 0.20),
        "T119_contradiction_cell_testable": bool(contra >= 200),
        "T120_synonym_map_coverage_enough": bool(syn_share >= 0.10),
        "T122_neighbours_estimable": bool(thin is not None and thin <= 0.50),
    }
    # Every gate value answers the same question - "is this premise measurable?" - so one rule reads them all.
    # What each *does* when it fails is decided by the gate's own frozen sentence, recorded in the design as
    # `gate_scope`: "design" stops the package, "H1"/"H3" stops that claim only, "rows" excludes and counts rows.
    scope = {t_: TD3.DESIGNS[t_].get("gate_scope", "design") for t_ in TD3.DESIGNS}
    failed = {k: scope.get(k.split("_")[0], "design") for k, v in out["kill_gates"].items() if v is False}
    blocked_gates = sorted(k for k, v in failed.items() if v == "design")
    blocked = sorted({g.split("_")[0] for g in blocked_gates})     # topic ids: "T118", not the gate label
    claim_limited = {k: v for k, v in failed.items() if v != "design"}
    out["verdict"] = {"runnable": [t for t in TD3.RUNNABLE if t not in blocked],
                      "blocked_whole_design": blocked, "blocked_gates": blocked_gates,
                      "claim_limited": claim_limited,
                      "note": "a fired gate is a result, not an obstacle: it stops exactly what its frozen sentence "
                              "says it stops (the whole design, one named hypothesis, or a set of rows to exclude and "
                              "count) and nothing is renegotiated after an estimate exists"}
    out["inherited_blocks"] = {
        "T121": "not re-measured here: EXP-0135 found negation markers in 2.9% of candidate descriptions against the "
                "5% identifiability gate it set for the same construct (negative applicability metadata), so T121 "
                "inherits that block instead of paying for a second census of the same column"}
    out["finished_at"] = W.now()
    out["invocation"] = " ".join([sys.executable] + sys.argv)
    dest = W.write_raw("EXP-0142", "wave3_premise_census", out)
    print(json.dumps(out["measured"], ensure_ascii=False, indent=1)[:1400])
    print("gates:", json.dumps(out["kill_gates"]))
    print("verdict:", json.dumps(out["verdict"])[:300])
    print("wrote", dest.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
