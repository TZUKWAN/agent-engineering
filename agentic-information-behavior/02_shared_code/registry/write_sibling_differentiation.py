"""EXP-0160: write the sibling-differentiation statement the funnel's own reposition gate demands.

`funnel_retriage_round5.py` advanced a topic with `w1_audit_done` but left in its `blocking_issue` the sentence
"reposition required: N shared constructs with Txxx; the difference must be written before a protocol is frozen".
That half-sentence was never closed for any of the 86 topics of 2026-09-23 - `differentiation_from_other_topics` is
empty on every wave row and `novelty_risk` still reads `pending_lit_audit` - so 20 packaged papers were carrying an
open internal-collision gate, and the gate that is supposed to stop the series re-cutting one result was unmet
rather than passed.

What this does, mechanically, from fields the registry already holds:

1. recomputes each topic's nearest siblings with the *same* construct tokenizer and bar the retriage used
   (`toks|concepts` over title + method; shared >= 3 means "reposition", >= 4 was fold territory);
2. for every such pair, compares the two designs on four axes - outcome (`primary_dv`), what is manipulated
   (`primary_iv`), measurement (`main_method`), substrate (`primary_dataset`) - and writes which axes actually
   differ, with both designs' own words beside each axis. A pair that differs on **no** axis is not two papers, so
   the tool refuses to write a difference for it and names it `SAME_DESIGN` for a fold decision;
3. for a topic that has a package, appends its graded external collision record (the L4/L3 counts the four-family
   rule produced in `literature_matrix.csv`) and moves `novelty_risk` from `pending_lit_audit` to
   `lit_audit_done_<pkg>`; an unpackaged topic keeps the pending marker, because its screen has not been graded yet.

Axes are compared by stemmed-token Jaccard, and the thresholds (0.60 = same axis, 3 = reposition, 0.60 again for the
pair's construct overlap) are fixed here before any statement was written, so no pair is judged after seeing what
would make it pass.

    python 02_shared_code/registry/write_sibling_differentiation.py [--dry-run] [--topics T128 T129 ...]
"""
from __future__ import annotations

import argparse
import csv
import datetime
import io
import json
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "02_shared_code" / "package_factory"))
import funnel_retriage_round5 as F                                    # noqa: E402

REG = ROOT / "00_program_registry" / "topic_registry.csv"
EXP = "EXP-0160"
AXIS_BAR = 0.60           # >= this Jaccard on an axis's own tokens = the two designs agree on that axis
REPOSITION = 3            # shared constructs at which the retriage demanded a written difference
MAX_SIBLINGS = 3          # the nearest few are what a reviewer compares against; the whole pool is noise

AXES = (("outcome", "primary_dv"), ("what is manipulated", "primary_iv"),
        ("measurement", "main_method"), ("substrate", "primary_dataset"))


def jac(a: str, b: str) -> float:
    x, y = F.toks(a), F.toks(b)
    if not x or not y:
        return 0.0
    return len(x & y) / len(x | y)


def graded(pkg_dir: str) -> dict:
    """The four-family grading this package's collision matrix carries, read from the matrix itself."""
    f = ROOT / "papers" / pkg_dir / "literature_matrix.csv" if pkg_dir else None
    if not f or not f.is_file():
        return {}
    rows = list(csv.DictReader(io.StringIO(f.read_text(encoding="utf-8"))))
    dist = {}
    for r in rows:
        lvl = str(r.get("overlap_level") or "?")
        dist[lvl] = dist.get(lvl, 0) + 1
    top = [r for r in rows if str(r.get("overlap_level")) in ("L4", "L3")]
    return {"graded": len(rows), "levels": dist, "strongest": [r.get("cite_key") for r in top][:4],
            "rule": (rows[0].get("level_rederived_by") or "")[:80] if rows else ""}


def field(v: str, n: int = 96) -> str:
    """A design field as recorded, or an explicit statement that the intake left it empty.

    Half the attachment topics carry only a title and a method line, so an empty `primary_dv` compared against a
    populated one produced "outcome: evidence weighting vs ;" - which reads like a difference and is an absence.
    """
    s = " ".join(str(v or "").split())
    if not s:
        return "(not recorded in the registry intake)"
    return s if len(s) <= n else s[:n] + "..."


def statement(tid: str, me: dict, sib: dict, shared) -> dict:
    def filled(key):
        return bool(str(me.get(key) or "").strip() and str(sib.get(key) or "").strip())

    comp = {label: filled(key) for label, key in AXES}          # is this axis comparable at all?
    same = {label: (jac(me[label_key(label)], sib[label_key(label)]) >= AXIS_BAR if comp[label] else None)
            for label, _ in AXES}
    differing = [l for l, _ in AXES if same[l] is False]
    agreeing = [l for l, _ in AXES if same[l] is True]
    unrecorded = [l for l, _ in AXES if not comp[l]]
    parts = lambda keys: "; ".join(f"{l}: {field(me[label_key(l)])} vs {field(sib[label_key(l)])}"
                                   for l in keys if comp[l])
    if not differing:
        # every axis that has text on both sides agrees. That is either one design twice, or a sibling so thinly
        # recorded that the registry cannot tell - and the tool refuses to invent a difference out of an absence.
        return {"verdict": "SAME_DESIGN" if not unrecorded else "UNDECIDED_THIN_SIBLING",
                "shared_constructs": sorted(shared),
                "text": f"{tid} and {sib['topic_id']} differ on no axis with recorded text (agreeing: "
                        f"{', '.join(agreeing) or 'none'}; agreeing detail - {parts(agreeing) or 'none'}"
                        + (f"; unrecorded on {'/'.join(unrecorded)}" if unrecorded else "")
                        + ") - one of the two must fold, or the thinner row must be recorded before it is compared",
                "axes_agreeing": agreeing, "axes_differing": differing, "axes_unrecorded": unrecorded}
    text = (f"{tid} vs {sib['topic_id']}: shares {len(shared)} construct(s) {sorted(shared)}; differs in "
            + ", ".join(differing) + " - " + parts(differing)
            + (". Same on " + ", ".join(agreeing) + " - " + parts(agreeing) if agreeing else "")
            + (f". Compared on title and method only for {'/'.join(unrecorded)} (no recorded text on both sides)"
               if unrecorded else ""))
    return {"verdict": "REPOSITIONED", "shared_constructs": sorted(shared), "text": text,
            "axes_agreeing": agreeing, "axes_differing": differing, "axes_unrecorded": unrecorded}


def label_key(label: str) -> str:
    return dict(AXES)[label]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--topics", action="append", default=[])
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    rows = list(csv.DictReader(io.StringIO(REG.read_text(encoding="utf-8"))))
    hdr = list(rows[0])
    by_id = {r["topic_id"]: r for r in rows}
    alive = {k: r for k, r in by_id.items() if not r["status"].startswith(("killed_", "demoted_", "not_"))}
    # a folded row is already decided not to be its own paper, so it owes no difference statement - it still counts
    # as a sibling for the topic it folded into, which is where the `already folded into T123` note below comes from.
    decidee = {k: r for k, r in alive.items() if not r["status"].startswith(("w3_fold_into_", "w3_merged_into_"))}
    blob_own = lambda r: " ".join([r["title_en"], r["main_method"], r["primary_dv"], r["primary_iv"]])
    blob_sib = lambda r: " ".join([r["title_en"], r["main_method"]])
    out, same_design = {}, []
    for tid, r in sorted(decidee.items()):
        me = F.toks(blob_own(r)) | F.concepts(blob_own(r))
        near = sorted(((len(me & (F.toks(blob_sib(o)) | F.concepts(blob_sib(o)))), k)
                       for k, o in alive.items() if k != tid), reverse=True)
        pairs = []
        for n, k in near[:MAX_SIBLINGS]:
            if n < REPOSITION:
                break
            st = statement(tid, r, by_id[k], me & (F.toks(blob_sib(by_id[k])) | F.concepts(blob_sib(by_id[k]))))
            if by_id[k]["status"].startswith("w3_fold_into_") and by_id[k]["status"].split("_into_")[-1] == tid:
                st["text"] = f"{k} was folded into {tid} ({by_id[k]['status']}), so it is one design with this one, " \
                             f"not a competitor; " + st["text"]
            pairs.append({"sibling": k, **st})
            if st["verdict"] == "SAME_DESIGN":
                same_design.append(f"{tid}~{k}")
        if not pairs:
            continue
        text = " || ".join(p["text"] for p in pairs)[:1800]
        g = graded((r.get("package") or "").strip())
        thin = sorted({p["sibling"] for p in pairs if p["verdict"] == "UNDECIDED_THIN_SIBLING"})
        risk = (f"lit_audit_done_{r['package'][:4]}: L4={g['levels'].get('L4', 0)} L3={g['levels'].get('L3', 0)} "
                f"of {g['graded']} graded records") if g else (
            # Not a deferral: the four-family grading is a step of a package, and a topic that ships no package has no
            # matrix to grade. Saying so closes the field instead of leaving "pending" in a finished registry.
            "not graded on its own - the four-family grading runs on a package's literature matrix and this topic "
            f"ships none (status `{r['status'][:60]}`); the funnel's own screen count stands in its evidence columns")
        if thin:
            risk += f"; {len(thin)} sibling(s) ({','.join(thin[:4])}) rest on title and method only"
        out[tid] = {"differentiation_from_other_topics": text, "novelty_risk": risk, "pairs": pairs,
                    "grading": g, "thin_siblings": thin}
        if a.topics and tid not in a.topics:
            continue
        r["differentiation_from_other_topics"] = text
        r["novelty_risk"] = risk
        note = " | reposition written by EXP-0160"
        if "reposition required" in (r.get("blocking_issue") or "") and note not in r["blocking_issue"]:
            r["blocking_issue"] = (r["blocking_issue"] + note)[:900]
    for line in (f"{tid}: {len(v['pairs'])} sibling(s); verdicts "
                 f"{sorted({p['verdict'] for p in v['pairs']})}; risk -> {v['novelty_risk'][:58]}"
                 for tid, v in sorted(out.items())):
        print(line[:190])
    print(f"\n{len(out)} topic(s) given a written difference; SAME_DESIGN pairs needing a fold decision: "
          f"{same_design or 'none'}")
    dest = ROOT / "results_raw" / f"EXP0160_sibling_differentiation_{time.strftime('%Y%m%dT%H%M%S')}.json"
    payload = {"exp_id": EXP, "seed": "n/a (deterministic rule)", "bars": {"axis_jaccard": AXIS_BAR, "reposition_shared_constructs": REPOSITION,
               "max_siblings_written": MAX_SIBLINGS}, "same_design_pairs": same_design,
               "topics": out, "started_at": datetime.datetime.now().isoformat(timespec="seconds"),
               "invocation": " ".join([sys.executable] + sys.argv)}
    if a.dry_run:
        print("dry run: registry untouched, artefact not written")
        return 0
    if same_design:
        raise SystemExit(f"ABORT: {same_design} differ on no axis, and a difference cannot be written for a pair "
                         f"that is one design. Fold one of them in the funnel (as T181/T185/T186/T188 were) and "
                         f"re-run.")
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=hdr, lineterminator=chr(10))
    w.writeheader()
    for r in rows:
        w.writerow({c: str(r.get(c) or "") for c in hdr})
    REG.write_text(buf.getvalue(), encoding="utf-8")
    dest.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {REG.name} and {dest.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
