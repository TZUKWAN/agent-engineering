"""EXP-0095 amendments A-E: attribute each grade move to its real cause, reuse this script's own v3 output on
re-runs, and report whose text was actually recovered.

Why: the first pass reported "54 abstracts recovered, 26 grades moved" in one breath, which reads as if the recovery
round changed the collision landscape. It did not. All 54 recovered rows hold a screening state rather than an L0-L4
grade, and every one of the 26 moved rows already had the same abstract on disk before the round ran - the frozen rule
reproduces the NEW value from that text. So the moves say the stored level column was stale, not that new literature
was found. This patch makes the run state that itself, per row, and adds a check of how far the curated per-paper
`literature_matrix.csv` columns agree with the rule.

    python 02_shared_code/literature/_patch_exp0095_attribution.py

Idempotent by construction: every anchor must occur exactly once, so a second application aborts instead of doubling.
"""
from __future__ import annotations
import pathlib

P = pathlib.Path(__file__).resolve().parent / "literature_abstract_recovery_round2.py"
t = P.read_text(encoding="utf-8")


def sub1(text, old, new, what):
    assert text.count(old) == 1, f"{what}: anchor found {text.count(old)}x - refusing to guess"
    return text.replace(old, new)


# sub1 returns the new text: an earlier copy of this file called it without assigning, which made it print
# "amendments applied" while writing nothing back. Every call site below therefore reads `t = sub1(...)`.


# ---- A: a re-run must not be able to lose abstracts to a rate limit
t = sub1(t, """    ap.add_argument("--sleep", type=float, default=0.6)
    args = ap.parse_args()""",
       """    ap.add_argument("--sleep", type=float, default=0.6)
    ap.add_argument("--no-cache", dest="no_cache", action="store_true",
                    help="re-query every DOI instead of reusing this script's own previous v3 output; caching is on "
                         "by default so that a correction run cannot silently lose abstracts to a rate limit and "
                         "report a smaller corpus than the run it is correcting")
    args = ap.parse_args()""", "A")

# ---- B: reuse the previous v3 output for the rows it already recovered
t = sub1(t, """    got, fails, by_channel = {}, Counter(), Counter()
    for i, tg in enumerate(targets, 1):
        for name, fn in CHANNELS:""",
       """    # A row the graded file calls title_only has no usable abstract, so any >= 25-word abstract this script's own
    # output holds for such a key can only come from a previous EXP-0095 pass.
    cache = {}
    if not args.no_cache and V3.is_file():
        for r in csv.DictReader(io.StringIO(V3.read_text(encoding="utf-8"))):
            a, src = (r.get("abstract") or "").strip(), r.get("source") or ""
            if len(a.split()) >= 25 and src.startswith("EXP-0095"):
                cache[(r.get("paper_id"), r.get("cite_key"))] = (a, src.split(":", 1)[1])
    got, fails, by_channel, reused = {}, Counter(), Counter(), 0
    for i, tg in enumerate(targets, 1):
        key = (tg["paper_id"], tg["cite_key"])
        if key in cache:
            a, ch = cache[key]
            got[key] = {"abstract": a, "channel": ch, "doi": tg["doi"], "from_cache": True}
            by_channel[ch] += 1
            reused += 1
            continue
        for name, fn in CHANNELS:""", "B")

# ---- C: carry the cause with each move
t = sub1(t, '''            moved.append({"paper_id": g["paper_id"], "cite_key": g["cite_key"], "from": g.get("overlap_level_current"),
                          "to": lvl, "graded_on_before": g.get("graded_on"), "graded_on_now": graded_on})''',
       '''            moved.append({"paper_id": g["paper_id"], "cite_key": g["cite_key"], "from": g.get("overlap_level_current"),
                          "to": lvl, "graded_on_before": g.get("graded_on"), "graded_on_now": graded_on,
                          "abstract_recovered_by_this_round": k in got})''', "C")

# ---- D: attribution, curated-matrix agreement, and whose text was recovered
t = sub1(t, '''    res = {"exp_id": "EXP-0095", "at": time.strftime("%Y-%m-%dT%H:%M:%S"), "wallclock_sec": None,''',
       '''    attr = Counter("abstract_recovered_by_this_round" if m["abstract_recovered_by_this_round"]
                   else "stored_level_not_reproducible_from_the_text_already_on_disk" for m in moved)
    mat_agreement = {}
    for pid in sorted({m["paper_id"] for m in moved}):
        pdir = next(iter((ROOT / "papers").glob(pid + "_*")), None)
        mf = (pdir / "literature_matrix.csv") if pdir else None
        if not mf or not mf.is_file():
            mat_agreement[pid] = {"error": "no curated matrix found"}
            continue
        re_by_key = {r["cite_key"]: r["overlap_level_current"] for r in rows_out if r["paper_id"] == pid}
        cmp_rows, disagree = 0, []
        for r in csv.DictReader(io.StringIO(mf.read_text(encoding="utf-8"))):
            lvl = str(r.get("overlap_level") or "")
            if not lvl.startswith("L"):
                continue
            cmp_rows += 1
            new = re_by_key.get(r["cite_key"])
            if new and new != lvl:
                disagree.append({"cite_key": r["cite_key"], "matrix": lvl, "frozen_rule": new})
        mat_agreement[pid] = {"matrix_rows_with_a_level": cmp_rows, "disagree_with_frozen_rule": len(disagree),
                              "examples": disagree[:6]}

    def _holds_grade(k):
        g = next((x for x in graded if (x["paper_id"], x["cite_key"]) == k), {})
        return str(g.get("overlap_level_current") or "").startswith("L")

    res = {"exp_id": "EXP-0095", "at": time.strftime("%Y-%m-%dT%H:%M:%S"), "wallclock_sec": None,''', "D1")

t = sub1(t, '''           "graded_rows": len(rows_out), "grades_moved": len(moved), "moved_detail": moved[:40],''',
       '''           "graded_rows": len(rows_out), "grades_moved": len(moved), "moved_detail": moved[:40],
           "abstracts_reused_from_this_scripts_prior_v3_run": reused,
           "recovered_rows_holding_a_grade": sum(1 for k in got if _holds_grade(k)),
           "recovered_rows_holding_only_a_screening_state": sum(1 for k in got if not _holds_grade(k)),
           "move_attribution": dict(attr),
           "curated_matrix_agreement_with_frozen_rule": mat_agreement,''', "D2")

# ---- E: the verdict must not attribute moves to the recovery round unless the attribution says so
t = sub1(t, '''        res["verdict"] = (f"RECOVERED {added} abstracts via "
                          f"{', '.join(f'{k}={v}' for k, v in by_channel.items())}; "
                          f"{len(moved)} grade(s) moved under the frozen rule and "
                          f"{len(still_title)} records remain title-only (labelled undecidable_on_title)")''',
       '''        by_move = ", ".join(f"{k}={v}" for k, v in sorted(attr.items()))
        res["verdict"] = (f"RECOVERED {added} abstracts via "
                          f"{', '.join(f'{k}={v}' for k, v in sorted(by_channel.items()))} "
                          f"({sum(1 for k in got if _holds_grade(k))} of them on records that carry a grade, "
                          f"{sum(1 for k in got if not _holds_grade(k))} on funnel candidates that were never "
                          f"graded); {len(still_title)} screened record(s) remain title-only and are labelled "
                          f"undecidable_on_title. {len(moved)} grade(s) moved under the frozen rule, attributed "
                          f"as: {by_move}. "
                          + ("The recovery round changed no grade: every move is a stored level the frozen rule does "
                             "not reproduce from the abstract already on disk, so this is a finding about the "
                             "consistency of the level columns, not about the literature. "
                             if attr.get("abstract_recovered_by_this_round", 0) == 0 and moved else "")
                          + "Curated matrix columns disagree with the rule on "
                          + "; ".join(f"{p}: {d.get('disagree_with_frozen_rule', '?')} of "
                                      f"{d.get('matrix_rows_with_a_level', '?')}"
                                      for p, d in sorted(mat_agreement.items())) + " - both levels are kept.")''',
       "E")

P.write_text(t, encoding="utf-8", newline="")
print("amendments A-E applied to", P.name)
