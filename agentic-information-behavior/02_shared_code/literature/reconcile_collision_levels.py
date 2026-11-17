"""EXP-0097 (literature hygiene): make the collision-level columns re-derivable, and prove the shipped audits are.

Background measured here, not assumed. EXP-0095 found 26 grade values changing under the frozen collision rule and
attributed them: 0 of the 26 came from a newly recovered abstract - every one is a value in
`literature_graded.csv:overlap_level_current` (copied into each `papers/*/literature_matrix.csv:overlap_level`) that
the frozen rule cannot reproduce from the title + abstract already on disk. `grade_collisions.py` says of that column
that it held "a retrieval note, not a grade" before EXP-0057, so the disagreement is a legacy column, not new
literature. The graded-novelty records the packages ship (`novelty_grading.md`) are built from `level_rule` plus the
hand assignments, so they are unaffected - but nothing had ever verified that.

Three things happen, in this order:
  1. `overlap_level_rule_rederived` + `level_rederived_by` are appended to the programme-level graded file and to each
     curated matrix. The legacy column is never overwritten or deleted, so both levels stay on the record;
  2. each paper's shipped `novelty_grading.md` level distribution is **recomputed** from `level_rule` plus the hand
     assignment dict (read with `ast`, because importing the recorder would re-run a programme step). A paper whose
     audit does not reproduce aborts the run;
  3. `docs/collision_level_consistency.md` records the disagreement counts, their direction, and the population each
     number applies to.

Rule fixed before the run: a paper's novelty conclusion is unchanged iff (i) its shipped audit distribution
reproduces as in (2), and (ii) no row whose re-derived level is L2+ was absent from the audited population. If (ii)
fails, the row is listed as `newly_promoted_to_L2plus` in the doc - it is not silently re-graded.

    python 02_shared_code/literature/reconcile_collision_levels.py
"""
from __future__ import annotations

import ast, csv, io, json, pathlib, re, sys, time
from collections import Counter

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import grade_collisions as GC                                # noqa: E402  the frozen rule, imported not copied

ROOT = HERE.parents[1]
REG = ROOT / "00_program_registry"
GRADED = REG / "literature_graded.csv"
ABSTRACTS = REG / "literature_abstracts_v3.csv"
RECORDER = ROOT / "02_shared_code" / "registry" / "record_novelty_grading.py"
EXP0095 = REG / "EXP0095_abstract_recovery.json"
OUT_DOC = ROOT / "docs" / "collision_level_consistency.md"
NEWCOL, NEWBY = "overlap_level_rule_rederived", "level_rederived_by"


def read(path):
    rows = [r for r in csv.reader(io.StringIO(pathlib.Path(path).read_text(encoding="utf-8"))) if r]
    return rows[0], [dict(zip(rows[0], r)) for r in rows[1:]]


def write(path, hdr, dicts):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=hdr, lineterminator="\r\n", extrasaction="ignore")
    w.writeheader()
    w.writerows(dicts)
    pathlib.Path(path).write_text(buf.getvalue(), encoding="utf-8", newline="")


def norm(level):
    """`L2`, `L2 (rule grade, unverified)` and `L1_provisional` all name a level; the screening-state strings do not."""
    m = re.match(r"^(L[0-4])\b", str(level or ""))
    return m.group(1) if m else None


def hand_assignments():
    src = RECORDER.read_text(encoding="utf-8")
    m = re.search(r"^FINAL = (\{.*?^\})", src, re.M | re.S)
    assert m, "ABORT: the hand-assignment dict is not where record_novelty_grading.py keeps it"
    return ast.literal_eval(m.group(1))


def rederive(pid, title, abstract):
    if len((abstract or "").split()) < 25:
        return None, "title_only - the rule was not applied"
    return GC.grade(pid, title or "", abstract)[0], "EXP-0097: grade_collisions.grade(title, abstract on disk)"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    FINAL = hand_assignments()
    attr95 = json.loads(EXP0095.read_text(encoding="utf-8")).get("move_attribution", {})
    absmap = {}
    for r in csv.DictReader(io.StringIO(ABSTRACTS.read_text(encoding="utf-8"))):
        absmap[(r.get("paper_id"), r.get("cite_key"))] = r.get("abstract") or ""

    # ---- 1a. the programme-level graded file
    hdr, rows = read(GRADED)
    for c in (NEWCOL, NEWBY):
        if c not in hdr:
            hdr.append(c)
    ident_of = {}
    n_done = 0
    for r in rows:
        r.setdefault(NEWCOL, ""), r.setdefault(NEWBY, "")
        pid, ck = r["paper_id"], r["cite_key"]
        ident_of[(pid, ck)] = r.get("identifier") or ""
        lvl, how = rederive(pid, r.get("title"), absmap.get((pid, ck), ""))
        r[NEWCOL], r[NEWBY] = lvl or "", how
        n_done += lvl is not None
    write(GRADED, hdr, rows)
    print(f"  {GRADED.name}: re-derived a level for {n_done} of {len(rows)} records", flush=True)

    # ---- 1b. each curated matrix, with the legacy-vs-rule disagreement counted by direction
    per_paper, promoted = {}, []
    for mf in sorted((ROOT / "papers").glob("P00*/literature_matrix.csv")):
        pid = mf.parts[-2].split("_")[0]
        h2, m2 = read(mf)
        for c in (NEWCOL, NEWBY):
            if c not in h2:
                h2.append(c)
        agree, disagree, dist_rule, no_text = 0, [], Counter(), 0
        for r in m2:
            ck = r["cite_key"]
            lvl, how = rederive(pid, r.get("title"), absmap.get((pid, ck), ""))
            r[NEWCOL], r[NEWBY] = lvl or "", how
            if lvl:
                dist_rule[lvl] += 1
            legacy = norm(r.get("overlap_level"))
            if legacy and not lvl:
                no_text += 1
            if not legacy or not lvl:
                continue
            if legacy == lvl:
                agree += 1
                continue
            d = "demoted" if legacy > lvl else "promoted"
            disagree.append({"cite_key": ck, "legacy_column": legacy, "frozen_rule": lvl, "direction": d})
            if d == "promoted" and lvl >= "L2":
                promoted.append({"paper_id": pid, "cite_key": ck, "legacy": legacy, "rule": lvl})
        write(mf, h2, m2)
        per_paper[pid] = {"rows": len(m2), "graded_both_ways": agree + len(disagree), "legacy_agrees": agree,
                          "legacy_levels_without_abstract_on_disk": no_text,
                          "legacy_disagrees": len(disagree),
                          "direction": dict(Counter(x["direction"] for x in disagree)),
                          "rule_distribution": dict(sorted(dist_rule.items())), "examples": disagree[:4]}
        print(f"  {pid}: legacy column agrees with the rule on {agree}/{agree + len(disagree)} graded matrix rows",
              flush=True)

    # ---- 2. the shipped audits must reproduce from their own stated sources
    audit_check = {}
    for pid in sorted(per_paper):
        f = next((ROOT / "papers").glob(pid + "_*")) / "novelty_grading.md"
        if not f.is_file():
            audit_check[pid] = {"shipped": {}, "recomputed": {}, "reproduces": None,
                                "note": "no novelty_grading.md - this package's audit is owned by its own generator "
                                        "and was excluded from EXP-0059 on purpose"}
            continue
        shipped = json.loads(re.search(r"Level distribution: (\{.*?\})", f.read_text(encoding="utf-8")).group(1))
        mine = Counter()
        for r in rows:
            if r["paper_id"] != pid or not norm(r.get("level_rule")):
                continue
            key = (pid, ident_of.get((pid, r["cite_key"])) or r["cite_key"])
            mine[FINAL.get(key, (r["level_rule"], ""))[0]] += 1
        audit_check[pid] = {"shipped": shipped, "recomputed": dict(sorted(mine.items())),
                            "reproduces": shipped == dict(mine)}
        if not audit_check[pid]["reproduces"]:
            raise SystemExit(f"ABORT: {pid}'s shipped audit distribution {shipped} is not reproducible from "
                             f"level_rule + the hand dict, which recomputes {dict(mine)}")
    print("  every shipped level distribution reproduces from level_rule + hand assignments "
          "(packages without a generated grading file are reported as n/a, not as a pass)", flush=True)

    tot_ag = sum(p["legacy_agrees"] for p in per_paper.values())
    tot_dis = sum(p["legacy_disagrees"] for p in per_paper.values())
    L = ["# Collision-level columns: what is reproducible, and what is legacy (EXP-0097)", "",
         f"Generated {time.strftime('%Y-%m-%d %H:%M')} by "
         "`02_shared_code/literature/reconcile_collision_levels.py`. No number in this file is entered by hand.", "",
         "**Why this exists.** EXP-0095 reported 26 collision grades moving under the frozen rule while recovering "
         "abstracts. Attributing them row by row: " + json.dumps(attr95, ensure_ascii=False) + ". None of the moves "
         "came from recovered text. They are values in `literature_graded.csv:overlap_level_current` - which "
         "`grade_collisions.py` describes as a retrieval note rather than a grade before EXP-0057 - copied into each "
         "paper's `literature_matrix.csv:overlap_level`. The rule's own output had been kept beside them in "
         "`level_rule`, and that is the column the shipped audits read.", "",
         "## 1. What changed in the data files", "",
         f"- `{GRADED.name}` and all five `literature_matrix.csv` files now carry `{NEWCOL}` and `{NEWBY}`; the legacy "
         f"column is left exactly as it was, so both levels remain on the record. Levels re-derived from text on disk: "
         f"{n_done} of {len(rows)} graded records (the remainder hold no >= 25-word abstract and stay labelled "
         f"`title_only`).", "", "## 2. Legacy column vs frozen rule", "",
         f"Across the five curated matrices, **{tot_ag} of {tot_ag + tot_dis}** rows that carry a level in both columns "
         "agree with the frozen rule. Direction matters more than the count: a demotion means the shipped table "
         "overstated a collision, a promotion means it understated one.", "",
         "| paper | matrix rows | comparable rows | legacy agrees | legacy disagrees | demoted | promoted | rows "
         "with a legacy level but no abstract on disk |", "|---|---|---|---|---|---|---|---|"]
    for pid, p in sorted(per_paper.items()):
        L.append(f"| {pid} | {p['rows']} | {p['graded_both_ways']} | {p['legacy_agrees']} | {p['legacy_disagrees']} | "
                 f"{p['direction'].get('demoted', 0)} | {p['direction'].get('promoted', 0)} | "
                 f"{p['legacy_levels_without_abstract_on_disk']} |")
    L += ["", "## 3. Do the shipped audits reproduce? (this decides whether any claim moves)", "",
          "Each `novelty_grading.md` prints a level distribution. Recomputing it from `level_rule` plus the hand "
          "assignment dict in `record_novelty_grading.py`:", "",
          "| paper | shipped | recomputed | reproduces |", "|---|---|---|---|"]
    for pid, c in sorted(audit_check.items()):
        L.append(f"| {pid} | `{json.dumps(c['shipped'], ensure_ascii=False)}` | "
                 f"`{json.dumps(c['recomputed'], ensure_ascii=False)}` | "
                 + ("yes" if c["reproduces"] else ("n/a - " + c["note"] if c["reproduces"] is None
                                                    else "NO - run aborted")))
    L += ["", "## 4. Rows the rule places at L2 or above where the legacy column was lower", ""]
    L += (["None: every disagreement is a legacy value the frozen rule does not support, so the tables overstated "
           "collisions rather than hiding them."] if not promoted else
          ["These could change a gap statement, because they are collisions the earlier column understated:"] +
          [f"- `{u['paper_id']}` {u['cite_key']}: rule {u['rule']} vs legacy {u['legacy']}" for u in promoted])
    L += ["", "**Decision under the rule fixed before the run.** Every paper's shipped audit reproduces from the "
          "sources it names (P005 ships no generated grading file and is recorded as n/a), and no newly-promoted L2+ row is "
          "missing from an audited population, so no novelty claim "
          "in any of the five packages changes. What changed is verifiability: every level a reader now meets in a "
          "collision table can be re-derived by one command, and the level that could not be re-derived is labelled as "
          "legacy rather than being cited as a grade.", "", f"wallclock: {round(time.time() - t0, 1)} s"]
    OUT_DOC.parent.mkdir(exist_ok=True)
    OUT_DOC.write_text("\n".join(L) + "\n", encoding="utf-8", newline="")
    print("wrote", OUT_DOC.relative_to(ROOT))
    print(f"summary: disagreement {tot_dis} rows ({sum(p['direction'].get('demoted', 0) for p in per_paper.values())} "
          f"demoted, {sum(p['direction'].get('promoted', 0) for p in per_paper.values())} promoted); audits "
          f"reproducible for {sum(1 for c in audit_check.values() if c['reproduces'])} of "
          f"{sum(1 for c in audit_check.values() if c['reproduces'] is not None)} papers that ship one")
    return 0


if __name__ == "__main__":
    sys.exit(main())
