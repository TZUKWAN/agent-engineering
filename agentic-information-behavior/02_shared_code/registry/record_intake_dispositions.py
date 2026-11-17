"""EXP-0222: give the funnel's own decisions the evidence columns the topic table asks for.

The screen (EXP-0115) and the construct-level retriage (EXP-0116) ended 20 of the 86 topics registered on
2026-09-23 - 13 as crowded, 7 by folding one into another - and both wrote their measurement into their own
artefact while leaving the topic table's four evidence columns empty. An empty column cannot be told apart
from a step nobody ran, so this step copies the decision's own numbers across: the crowding count and the
channel it came from for a demotion, and for a fold the host design's experiment ids, coverage and shipped
figures. Nothing here is typed by hand: every field is read from `EXP0115_*`, `EXP0116_*`, or the host's row
in `topic_evidence.csv`.

Where a fold has no packaged host - the funnel folded T186 onto T125, which the same screen had already
demoted - that is written out as the finding it is rather than smoothed over.

The same rule then reads back the six pre-wave rows (T004, T007, T008, T012, T013, T024): P001-P005 were
assembled before `wave_package.write_evidence` existed, so their topic rows name no package and no run even
though both are on disk. A row with no registered run is left alone - its decision lives in `blocking_issue`,
and this step writes only what an artefact or a package can vouch for.

    python 02_shared_code/registry/record_intake_dispositions.py [--dry-run]
"""
from __future__ import annotations

import argparse
import csv
import datetime
import glob
import io
import json
import pathlib
import re
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "02_shared_code" / "package_factory"))

REG = ROOT / "00_program_registry"
EV = REG / "topic_evidence.csv"
COLS = ["topic_id", "package", "exp_ids", "measured_coverage", "figures_tables", "collision_verdict", "status"]
# A premise block already carries its measured gate through `record_blocked.py`; this step is only for the rows the
# funnel ended on the literature or construct leg, which no other writer records.
DECIDED = re.compile(r"^(demoted_|killed_|not_promoted|w2_parked|w3_fold_into_|w3_merged_into_)")
HOST = re.compile(r"_(?:fold|merge)d?_into_([TP]\d{3})")
INTAKE = {f"T{n:03d}" for n in list(range(101, 143)) + list(range(151, 195))}
FOLDED = re.compile(r"^(demoted_|killed_|not_promoted|w2_parked|w2_merge|w3_fold_into_|w3_merged_into_|w_blocked)")


def latest(pat: str) -> pathlib.Path:
    f = sorted(glob.glob(str(ROOT / pat)), key=lambda x: pathlib.Path(x).stat().st_mtime)
    if not f:
        raise SystemExit(f"ABORT: no artefact matches {pat}")
    return pathlib.Path(f[-1])


def cap(s, n: int = 900) -> str:
    return json.dumps(s, ensure_ascii=False)[:n] if not isinstance(s, str) else s[:n]


def _graded(pkg: str) -> dict:
    """The four-family grading a package's own literature matrix carries, read from the matrix."""
    f = ROOT / "papers" / pkg / "literature_matrix.csv" if pkg else None
    if not f or not f.is_file():
        return {}
    rows = list(csv.DictReader(io.StringIO(f.read_text(encoding="utf-8"))))
    dist = {}
    for r in rows:
        lvl = str(r.get("overlap_level") or "?")
        dist[lvl] = dist.get(lvl, 0) + 1
    top = [r.get("cite_key") for r in rows if str(r.get("overlap_level")) in ("L4", "L3")]
    return {"graded": len(rows), "levels": dist, "strongest": top[:4]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    f115, f116 = latest("results_raw/EXP0115_funnel_screen_round5_*.json"), \
                 latest("results_raw/EXP0116_funnel_retriage_*.json")
    s = json.loads(f115.read_text(encoding="utf-8"))
    r = json.loads(f116.read_text(encoding="utf-8"))
    screen = {t["topic_id"]: t for t in s["topics"]}
    retriage = r.get("decided") or {}
    reg = {x["topic_id"]: x for x in csv.DictReader(io.StringIO(
        (REG / "topic_registry.csv").read_text(encoding="utf-8-sig")))}
    ev = {x["topic_id"]: x for x in csv.DictReader(io.StringIO(EV.read_text(encoding="utf-8")))} \
        if EV.is_file() else {}
    exps = list(csv.DictReader(io.StringIO((REG / "experiment_registry.csv").read_text(encoding="utf-8-sig"))))
    by_paper = {}
    for e in exps:
        by_paper.setdefault(str(e.get("paper_id") or "")[:4], []).append(e["exp_id"])

    want = [t for t, x in sorted(reg.items())
            if t in INTAKE and DECIDED.match(x["status"] or "") and not (x["package"] or "").strip()
            and (t in screen or t in retriage)]
    skipped = [t for t, x in sorted(reg.items())
               if t in INTAKE and DECIDED.match(x["status"] or "") and not (x["package"] or "").strip()
               and not (t in screen or t in retriage)]
    if skipped:
        raise SystemExit(f"ABORT: {skipped} carry a funnel-decided status but no record in either artefact, so "
                         f"their evidence could not be derived from a measurement")
    out, rows = {}, list(ev.values())
    for tid in want:
        cur = reg[tid]
        sc, rt = screen.get(tid) or {}, retriage.get(tid) or {}
        ids = ["EXP-0115"] + (["EXP-0116"] if rt else [])
        cov = {"screen": f115.name, "retriage": f116.name if rt else None,
               "funnel_legs_measured": sc.get("reason") or rt.get("reason"),
               "construct_census": rt.get("census"),
               "fields_the_design_named": sc.get("fields") or {},
               "substitutes_considered": sc.get("substitutes") or [],
               "not_measured": "no protocol freeze, no local row read for an outcome, no model fitted - "
                               "the funnel ended this topic on the evidence below"}
        fold = HOST.search(cur["status"] or "")
        if fold:
            host = fold.group(1)
            # A fold names either a topic or, for the two folds onto the pre-wave packages, the package id itself.
            # P001 and P002 belong to T037 and T008, which predate both the evidence table and the package column,
            # so their deliverables are read back from the package directory on disk.
            hr = reg.get(host) if host in reg else next(
                (x for x in reg.values() if (x.get("package") or "").startswith(host)), {})
            hid = hr.get("topic_id") or ""
            he = ev.get(hid) or {}
            pdir = next((p for p in sorted((ROOT / "papers").iterdir())
                         if p.is_dir() and host.startswith("P") and p.name.startswith(host + "_")), None) \
                or next((p for p in sorted((ROOT / "papers").iterdir())
                         if p.is_dir() and p.name == he.get("package")), None)
            host_pkg = (hr.get("package") or he.get("package") or (pdir.name if pdir else "")).strip()
            host_deliv = (he.get("figures_tables") if he else None) or (
                cap({"figures": sorted(x.name for x in (pdir / "figures").glob("*.pdf")),
                     "tables": sorted(x.name for x in (pdir / "tables").glob("*.csv"))}, 700) if pdir else None)
            own = by_paper.get((host_pkg or "")[:4]) or []
            host_exp = he.get("exp_ids") or (
                f"{len(own)} runs registered against {host_pkg[:4]}: " + ";".join(own) if own else
                f"see papers/{host_pkg}/tables" if host_pkg else "")
            ids.append(host_pkg[:4] if host_pkg else host)
            if rt.get("census") is not None:
                cov["construct_census"] = rt.get("census")
            if not host_pkg:
                cov["host"] = {"topic_id": host, "host_status": hr.get("status"), "host_package": None,
                               "host_exp_ids": host_exp or None}
                figs = (f"none of its own, and none inherited: the funnel folded {tid} onto {host}, which the same "
                        f"screen ended as `{hr.get('status')}`, so this claim ships in no package - the fold has no "
                        f"host and is reported as an unresolved overlap rather than as a delivered result")
                verdict = (f"not graded on its own: EXP-0116 folded it into {host} - {rt.get('reason')} - but "
                           f"{host} is itself `{hr.get('status')}` (EXP-0115: {sc.get('reason')})")
            else:
                cov["host"] = {"topic_id": hid or None, "host_package": host_pkg, "host_exp_ids": host_exp,
                               "host_measured_coverage": he.get("measured_coverage")
                               or "the host predates the evidence table; its provenance is its own package"}
                figs = cap({"own": "none - folded, so no deliverable of its own",
                            "shipped_in": host_pkg, "host_exp_ids": host_exp, "host_figures_tables": host_deliv})
                verdict = (f"not crowded on its own: EXP-0116 folded it into {host} ({host_pkg}) - "
                           f"{rt.get('reason')}; that host's graded collision record is "
                           f"papers/{host_pkg}/literature_matrix.csv. EXP-0115's own screen of {tid}: "
                           f"{sc.get('reason')}")
        else:
            figs = ("none - the screen ended this topic before a design was frozen, so no figure or table of the "
                    "20 deliverables was made for it")
            lvl = (re.search(r"L[0-4]", cur["status"] or "") or ["the screen"])[0]
            verdict = (f"{lvl} as decided by EXP-0115 and recorded in the status `{cur['status']}`: "
                       f"{sc.get('reason')}; screen rule: {s.get('rule', '')[:180]}")
        out[tid] = {"status": cur["status"], "exp_ids": ";".join(ids), "measured_coverage": cov,
                    "figures_tables": figs, "collision_verdict": cap(verdict)}
        rows = [x for x in rows if x.get("topic_id") != tid]
        rows.append({"topic_id": tid, "package": "", "exp_ids": ";".join(ids),
                     "measured_coverage": cap(cov), "figures_tables": cap(figs, 900),
                     "collision_verdict": cap(verdict), "status": ""})   # the decision stays where it was written
    print(f"{len(want)} funnel-decided row(s) to write: {want}")
    for tid, v in out.items():
        print(f"  {tid}: {v['exp_ids']:22s} | {v['collision_verdict'][:96]}")

    factory = set()
    for mp in sorted(pathlib.Path(ROOT / "02_shared_code" / "package_factory").glob("topic_designs_wave*.py")):
        factory |= set(getattr(__import__(mp.stem), "DESIGNS", {}) or {})
    legacy = [t for t, x in sorted(reg.items())
              if t not in INTAKE and t not in factory
              and any(t in (e.get("topic_id") or "") for e in exps)]
    # The pre-wave rows P001-P005 left out of this table: they were assembled before
    # `wave_package.write_evidence` existed, so their topic rows carry no package, no experiment ids and no
    # deliverable list even though all four things exist on disk. Read them back from the registry and the package.
    # A row with no registered run at all is not filled here: it owes its decision to `blocking_issue`, and this
    # step writes only what an artefact or a package can vouch for. A row a factory already wrote is never touched.
    for tid in legacy:
        cur = reg[tid]
        own = [e for e in exps if tid in (e.get("topic_id") or "")]
        single = sorted({e["paper_id"] for e in own if re.fullmatch(r"P\d{3}", e["paper_id"] or "")})
        # A package is claimed in the `package` column only by the row that owns it. A folded or demoted sibling whose
        # probes fed that package gets the pointer inside its evidence cells instead, or the table would say that
        # P001 has three topics and the audit's package-to-topic reading of it would be false.
        owns = single[0] if len(single) == 1 and not FOLDED.match(cur["status"] or "") else ""
        pkg = ""
        if owns:
            dirs = [p for p in sorted((ROOT / "papers").iterdir())
                    if p.is_dir() and p.name.startswith(owns + "_")]
            pkg = dirs[0].name if dirs else owns
        ships = single[0] if len(single) == 1 and not owns else ""
        ship_dir = next((p.name for p in sorted((ROOT / "papers").iterdir())
                         if p.is_dir() and ships and p.name.startswith(ships + "_")), ships)
        g = _graded(pkg) or _graded(ship_dir)
        pd = ROOT / "papers" / (pkg or ship_dir)
        figs = {"own": "none of its own - " + ("this topic's deliverables are the pre-wave package's own files"
                                               if pkg else f"its probes fed {ship_dir}, whose own files carry them"),
                "shipped_in": pkg or ship_dir or None,
                "figures": sorted(x.name for x in (pd / "figures").glob("*.pdf")) if (pkg or ship_dir) else None,
                "tables": sorted(x.name for x in (pd / "tables").glob("*.csv")) if (pkg or ship_dir) else None}
        rows = [x for x in rows if x.get("topic_id") != tid]
        rows.append({"topic_id": tid, "package": pkg,
                     "exp_ids": ";".join(e["exp_id"] for e in own),
                     "measured_coverage": cap({"runs_registered_against_this_topic": len(own),
                                               "stages": sorted({e["stage"][:60] for e in own}),
                                               "assembled_before_the_evidence_table": bool(pkg)}),
                     "figures_tables": cap(figs),
                     "collision_verdict": cap({"graded_records": g.get("graded"), "levels": g.get("levels"),
                                               "strongest": g.get("strongest"),
                                               "source": f"papers/{pkg or ship_dir}/literature_matrix.csv" if g else None,
                                               "as_written_by_the_funnel": (cur["blocking_issue"] or "")[:300]}),
                     "status": ""})
        out[tid] = {"status": cur["status"], "exp_ids": ";".join(e["exp_id"] for e in own), "package": pkg,
                    "measured_coverage": "pre-wave row read back from the experiment registry"}
        print(f"  legacy {tid}: package={pkg or '-'} exp_ids={out[tid]['exp_ids'][:60]}")

    payload = {"exp_id": "EXP-0222", "seed": "n/a (a read of two frozen artefacts)",
               "sources": {"screen": f115.name, "retriage": f116.name},
               "rule": "every topic whose registry status is a funnel decision and which carries no package gets "
                       "its four evidence columns filled from the artefact that made the decision, and a fold "
                       "takes its host's experiment ids, coverage and shipped figures from the host's own row",
               "topics": out, "n_written": len(out),
               "started_at": datetime.datetime.now().isoformat(timespec="seconds"),
               "invocation": " ".join([sys.executable] + sys.argv)}
    dest = ROOT / "results_raw" / f"EXP0222_intake_dispositions_{time.strftime('%Y%m%dT%H%M%S')}.json"
    if a.dry_run:
        print("dry run: nothing written")
        return 0
    dest.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLS, lineterminator=chr(10))
    w.writeheader()
    for x in sorted(rows, key=lambda y: y.get("topic_id", "")):
        w.writerow({c: str(x.get(c) or "") for c in COLS})
    EV.write_text(buf.getvalue(), encoding="utf-8")
    print(f"wrote {EV.name} and {dest.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
