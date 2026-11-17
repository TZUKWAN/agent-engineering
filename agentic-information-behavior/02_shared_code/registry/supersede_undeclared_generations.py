"""Name the artefact generations that sit in the results folders but belong to no citable record.

The estate's convention is that a retired generation stays on disk as the audit trail and is named in
`SUPERSEDED_ARTIFACTS.json` with a reason; the package builders then exclude it from what may be cited. Round 2
found 1,390 files under `results_raw/` and `results_processed/` that are in neither place - no registry row
declares them and the ledger does not retire them. A reader of those folders cannot tell a re-run from a
discarded attempt from a superseded measurement, which is the difference between an audit trail and a dump.

For each such file this finds the generation a registry row does declare for the same run, compares the two with
the estate's own generation comparator, and writes the measured difference as the reason:

* identical apart from the volatile run bookkeeping (timestamps, wallclock, the argv it recorded);
* differing in fields that carry no estimate - verdict words, notes, direction labels;
* differing in an estimate, in which case the file is **not** retired: a generation whose numbers disagree with
  the kept one is a measurement that needs a human-visible answer, not a ledger line that hides it.

`--check` prints the census and writes nothing; `--apply` appends the retirement entries through the same JSON the
existing tool writes.

    python 02_shared_code/registry/supersede_undeclared_generations.py --check
    python 02_shared_code/registry/supersede_undeclared_generations.py --apply
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime
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
import compare_artefact_generations as C                                # noqa: E402
import round2_lib as L                                                   # noqa: E402
import round2_run_reality as RR                                          # noqa: E402

LEDGER = ROOT / "results_raw" / "SUPERSEDED_ARTIFACTS.json"
FOLDERS = ("results_raw", "results_processed")


def declared() -> dict:
    """{filename: exp_id} for every artefact a registry row points at."""
    owners = {}
    for r in L.read_any(ROOT / "00_program_registry" / "experiment_registry.csv") or []:
        for g in RR.parts_of(r.get("outputs") or ""):
            for f in RR.expand(ROOT, g):
                owners[f.name] = r["exp_id"]
    return owners


def census(owners: dict, sup: set, cited: set = ()) -> dict:
    """{stem: [(path, kind, reason_or_detail)]} for every file that belongs to no record.

    `cited` is the set of file names a package names in its own text: those are accounted for by definition, and
    retiring one because the register happens to declare a sibling would destroy evidence a shipped paper points at.
    """
    out, shared = {}, set(shared_stems())
    for fold in FOLDERS:
        for p in sorted((ROOT / fold).glob("EXP0*")):
            if C.stem_of(p.name) in shared:
                continue
            if p.name in owners or p.name in sup or p.name in cited or not p.is_file():
                continue
            stem = C.stem_of(p.name)
            keep = [n for n in owners if C.stem_of(n) == stem]
            out.setdefault(stem, []).append((p, "orphan", sorted(keep)))
    return out


def classify(p: pathlib.Path, keep_names: list, owners: dict) -> tuple:
    """(kind, reason) for one orphan, measured against the generation the register declares.

    An orphan older than the declared generation is an earlier attempt of the same run that was replaced - what it
    measured is recorded in the reason, because that is the difference a reader would otherwise have to reconstruct.
    An orphan *newer* than the declared generation is a different thing: a run whose output the register never
    picked up, which is a stale row, not a retired file, so it is reported rather than buried.
    """
    kin = [ROOT / fold / n for n in keep_names for fold in FOLDERS if (ROOT / fold / n).is_file()]
    if not kin:
        return ("no_declared_sibling", "")
    # the newest declared generation of the same stem is the one a reader is meant to cite
    ref = max(kin, key=lambda q: q.stat().st_mtime)
    exp = owners.get(ref.name, "")
    if p.stat().st_mtime > ref.stat().st_mtime:
        # a later re-run of the same step that no package cites. Retirable, because the citable generation is the
        # declared one and this file cannot be mistaken for evidence - but only with the difference spelled out, so
        # a reader who finds it knows whether it re-measured something the paper relies on.
        return ("later_rerun", f"a re-run of {exp} after the generation the register declares ({ref.name})")
    if p.suffix == ".json" and ref.suffix == ".json":
        try:
            a, b = C.load(p), C.load(ref)
        except Exception as e:                                           # noqa: BLE001 - unreadable is not retirable
            return ("unreadable", str(e)[:120])
        diffs, _, _ = C.compare(a, b)
        moved = C.interesting(diffs)
        rel = "earlier" if p.stat().st_mtime < ref.stat().st_mtime else "later"
        head = f"{'an' if rel[0] in 'aeiou' else 'a'} {rel} generation of {exp}; the citable one is the "                f"declared {ref.name}"
        if not diffs:
            return ("identical", f"{head}; identical apart from the volatile run bookkeeping this tool ignores")
        fields = sorted({k for k, _, _ in diffs})
        detail = (f"{len(moved)} of them an estimate or a verdict" if moved
                  else f"none of them an estimate: " + ", ".join(f.split("/")[-1] for f in fields[:8]))
        return (("estimate_differs" if moved else "labels_only"),
                f"{head}: differs in {len(diffs)} field(s), {detail}. "
                + (f"First differences: {json.dumps([list(m) for m in moved[:3]], ensure_ascii=False)[:260]}"
                   if moved else ""))
    try:
        same = p.read_bytes() == ref.read_bytes()
    except Exception:                                                    # noqa: BLE001
        return ("unreadable", "")
    if same:
        return ("identical", f"an earlier copy of {exp}'s table, byte-identical to the declared {ref.name}")
    return ("bytes_differ", f"an earlier copy of {exp}'s table; differs byte-wise from the declared {ref.name}")


def shared_stems() -> set:
    """Filename stems that more than one registered run claims.

    `P000_gold_tool_grounding_*.json` is written by three of the earliest runs, so a family-based rule cannot say
    which generation belongs to which run - and every family-based rule in this file (collapse, repoint, retire)
    would otherwise move or bury a file a package still cites. Those stems are left exactly as each row declares
    them, which is what the package copies of the register agree on.
    """
    owners = declared()
    out = set()
    for n in owners:
        if len({owners[m] for m in owners if C.stem_of(m) == C.stem_of(n)}) > 1:
            out.add(C.stem_of(n))
    return out


CITED_RX = re.compile(r"EXP\d{4}_[A-Za-z0-9_\-\.\[\]\*]+?\d{8}T\d{6}\.(?:json|csv)")


def cited_names() -> dict:
    """{artefact filename: packages that name it} across every package's prose and tables.

    A file a paper cites is the generation its numbers came from. Where the register declares an earlier generation
    of the same run instead - EXP-0024's row names 22:10:37 while `paper.md`'s figure caption names 22:22:05 - the
    citation lands on a file no record accounts for, which is the failure this step repairs.
    """
    out = collections.defaultdict(set)
    for pkg in L.packages():
        for f in (list(pkg.glob("*.md")) + list(pkg.glob("*.csv")) + list(pkg.glob("tables/*.csv"))
                  + list(pkg.glob("scripts/*.py"))):
            if not f.is_file():
                continue
            for n in CITED_RX.findall(f.read_text(encoding="utf-8", errors="replace")):
                if "*" not in n and any((ROOT / fold / n).is_file() for fold in FOLDERS):
                    out[n].add(pkg.name)
    return out


def declare_cited(rows: list, decl: dict, write: bool) -> list:
    """Point each row at the generation a package actually cites, and retire the one it declared instead.

    Returns the ledger entries the step would write, so `--check` can report them without touching the register.
    """
    owners = {r["exp_id"]: r for r in rows}
    led = json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.is_file() else {
        "purpose": "artefacts kept but not citable", "superseded": []}
    have = {e["file"] for e in led["superseded"]}
    entries, touched = [], set()
    for name, pkgs in sorted(cited_names().items()):
        exp = f"EXP-{name[3:7]}"
        r = owners.get(exp)
        if r is None or name in RR.parts_of(r.get("outputs") or "") or name in decl:
            continue
        fold = next(f for f in FOLDERS if (ROOT / f / name).is_file())
        keep = sorted(n for n in decl if C.stem_of(n) == C.stem_of(name))
        parts = [p.strip() for p in RR.parts_of(r.get("outputs") or "") if p.strip()]
        r["outputs"] = "; ".join(parts + [f"{fold}/{name}"])
        touched.add(exp)
        for old in []:
            if old == name or old in have:
                continue
            p = next((ROOT / f / old for f in FOLDERS if (ROOT / f / old).is_file()), None)
            if p is None:
                continue
            pass                     # appending is the whole correction; retiring a sibling here would fight the
            # census, which is the only step allowed to decide what is unaccounted - and a package that cites an
            # older generation is a citation a row must declare, not a generation to bury
            # a row that declares a file the ledger calls non-citable contradicts itself, so the retired sibling
            # leaves the declaration with it: the row then names exactly what a reader may cite
            r["outputs"] = "; ".join([x for x in RR.parts_of(r.get("outputs") or "")
                                      if x.strip() and not x.strip().endswith("/" + old)])
    if write and (entries or touched):
        led["superseded"].extend(entries)
        LEDGER.write_text(json.dumps(led, indent=1, ensure_ascii=False), encoding="utf-8")
    return entries, sorted(touched)


def adopt_extra_outputs(rows: list, decl: dict, write: bool) -> tuple:
    """Add to each row the files that carry its own id but a different stem.

    `EXP0016_intervention_table.csv` and `EXP0016_intervention_verdict.json` are not generations of the JSON the
    register declares - they are companion outputs of the same run that no row ever named. Retiring them would say
    "not citable" about evidence that simply was not written down, so the register is widened instead. A JSON whose
    own `exp_id` field disagrees with the id in its file name is not adopted: that is a misfiled artefact, and it
    stays blocked for a human-visible answer.
    """
    owners = {r["exp_id"]: r for r in rows}
    adopted, refused = [], []
    for fold in FOLDERS:
        for p in sorted((ROOT / fold).glob("EXP0*")):
            if p.name in decl or not p.is_file():
                continue
            stem = C.stem_of(p.name)
            if any(C.stem_of(n) == stem for n in decl):
                continue                                        # a generation of a family that is declared
            exp = f"EXP-{p.name[3:7]}"
            r = owners.get(exp)
            if r is None:
                refused.append((str(p.relative_to(ROOT)).replace(chr(92), "/"), "no registry row carries this id"))
                continue
            if p.suffix == ".json":
                try:
                    inside = str(json.loads(p.read_text(encoding="utf-8", errors="replace")).get("exp_id") or "")
                except Exception:                               # noqa: BLE001 - unreadable, so not adoptable
                    refused.append((str(p.relative_to(ROOT)).replace(chr(92), "/"), "unreadable JSON"))
                    continue
                # one artefact can carry two runs (EXP-0121 and EXP-0122 are the query-level and candidate-level
                # halves of one script), so a joined id that includes this one is not a misfiling
                named = {RR.norm_id(x) for x in re.split(r"[;,+/]", inside) if x.strip()}
                if named and RR.norm_id(exp) not in named:
                    refused.append((str(p.relative_to(ROOT)).replace(chr(92), "/"),
                                    f"names {inside} inside, {exp} in its file name"))
                    continue
            r["outputs"] = "; ".join([x.strip() for x in RR.parts_of(r.get("outputs") or "") if x.strip()]
                                     + [f"{fold}/{p.name}"])
            adopted.append(f"{exp}: +{fold}/{p.name}")
            decl[p.name] = exp
    if write and adopted:
        import csv
        import io
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), lineterminator=chr(10))
        w.writeheader()
        w.writerows(rows)
        (ROOT / "00_program_registry" / "experiment_registry.csv").write_text(buf.getvalue(), encoding="utf-8")
    return adopted, refused


def purge_own_entries() -> int:
    """Remove the retirement entries this tool wrote, so a re-run recomputes them against the final estate.

    The census is only correct relative to a registry that has stopped moving. The first pass ran mid-round: the
    recorders later re-pointed rows at newer generations, which made some files this tool had retired into the
    live artefact of their own row. Retiring is not deletion - the files never move - so dropping the entries and
    re-deriving them is safe, and it is the difference between a ledger that describes the estate and one that
    describes a snapshot taken while it was being rebuilt.
    """
    if not LEDGER.is_file():
        return 0
    d = json.loads(LEDGER.read_text(encoding="utf-8"))
    keep = [e for e in d["superseded"] if e.get("by") != "supersede_undeclared_generations.py"]
    gone = len(d["superseded"]) - len(keep)
    if gone:
        d["superseded"] = keep
        LEDGER.write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")
    return gone


def collapse_duplicate_generations(rows: list) -> int:
    """Keep one generation per artefact family in each row's `outputs`.

    A recorder that appends rather than replaces leaves a row naming two generations of the same run, and then
    which one the package must ship is undefined. The newest file the row names is kept and the older siblings
    are dropped from the declaration - they stay on disk and are retired by the census beside it.
    """
    decl, shared = {}, shared_stems()
    for r in rows:
        for g in RR.parts_of(r.get("outputs") or ""):
            for f in RR.expand(ROOT, g):
                if C.stem_of(f.name) in shared:
                    continue
                decl.setdefault(C.stem_of(f.name), []).append((f.stat().st_mtime, f))
    n = 0
    for r in rows:
        parts = [p.strip() for p in RR.parts_of(r.get("outputs") or "") if p.strip()]
        drop = []
        for stem, files in decl.items():
            if len(files) < 2:
                continue
            named = [f for _m, f in files if C.stem_of(f.name) == stem]
            keep = max(files)[1]
            drop += [f.name for f in named if f.name != keep.name]
        if not drop:
            continue
        new = [p for p in parts if not any(p.endswith(d) or (d in p and "*" not in p) for d in drop)]
        new = list(dict.fromkeys(new))
        if new != parts:
            r["outputs"] = "; ".join(new)
            n += 1
    return n


def drop_retired_declarations(rows: list) -> int:
    """Remove from each row any declared file the ledger has just retired.

    A row is the register's statement of what a run wrote *and what may be cited*. Once this tool retires a
    generation - because a later one of the same run is what the packages cite, or because the census found it
    unaccounted - leaving it in the declaration would mean the register names a file its own ledger calls
    non-citable, which is the contradiction the round-2 consistency check exists to catch.
    """
    sup = L.superseded()
    n = 0
    for r in rows:
        parts = [p.strip() for p in RR.parts_of(r.get("outputs") or "") if p.strip()]
        keep = [p for p in parts if not any(f.name in sup for f in RR.expand(ROOT, p))]
        if not keep:                                  # a row may not be left declaring nothing
            print(f"  KEPT AS IS {r['exp_id']}: every declared file is retired")
            continue
        if keep != parts:
            r["outputs"] = "; ".join(keep)
            n += 1
    return n


def repoint_to_newest(rows: list, cited: set) -> int:
    """Where the register declares an older generation and a newer one exists that nothing cites, follow the disk.

    Without this the two steps disagree: the ledger retires the older generation because a newer run replaced it,
    while the register still names the older one, leaving a row whose every declaration is non-citable. The rule
    the estate uses elsewhere is that the newest generation is the citable one unless a paper says otherwise, so a
    cited older generation keeps its row pointed at it and nothing here moves.
    """
    n, shared = 0, shared_stems()
    fams = {}
    for fold in FOLDERS:
        for p in (ROOT / fold).glob("EXP0*"):
            if p.name in cited or C.stem_of(p.name) in shared:
                continue
            fams.setdefault(C.stem_of(p.name), []).append((p.stat().st_mtime, fold, p))
    for r in rows:
        parts = [q.strip() for q in RR.parts_of(r.get("outputs") or "") if q.strip()]
        if not parts:
            # An empty declaration is a row that points a reader nowhere - which is what an earlier pass of this
            # tool produced when it retired the only file a row named. Rebuild it from the disk: the newest
            # generation carrying this run's own id is what the run left behind.
            mine = [(f.stat().st_mtime, fold, f) for fold in FOLDERS for f in (ROOT / fold).glob("EXP0*")
                    if f.name.startswith(r["exp_id"].replace("-", "") + "_") and f.name not in cited]
            if not mine:
                continue
            newest = max(mine)
            r["outputs"] = f"{newest[1]}/{newest[2].name}"
            n += 1
            continue
        out, changed = list(parts), False
        for stem, files in fams.items():
            named = [p for p in parts if any(p.endswith("/" + f.name) for _m, _fo, f in files)]
            if not named:
                continue
            newest = max(files)
            # keep the newest generation of the family and drop the siblings the row also names: the register's job
            # is to point a reader at what may be cited, and the ledger has already said the others may not
            keep = [p for p in parts if not any(p.endswith("/" + f.name) for _m, _fo, f in files)]
            add = f"{newest[1]}/{newest[2].name}"
            if add not in keep:
                keep.append(add)
            if keep != parts:
                out, changed = keep, True
        if changed and out:
            r["outputs"] = "; ".join(dict.fromkeys(out))
            n += 1
    return n


def package_register_names() -> set:
    """Every file named by some package's own copy of the experiment register.

    That copy is the package's declaration of its provenance, so a file it names is cited evidence even when the
    prose refers to the run by id rather than by filename.
    """
    import csv as _csv
    out = set()
    for pkg in L.packages():
        f = pkg / "experiment_registry.csv"
        if not f.is_file():
            continue
        for r in _csv.DictReader(io.StringIO(f.read_text(encoding="utf-8"))):
            for g in RR.parts_of(r.get("outputs") or ""):
                out.add(pathlib.Path(g.strip().replace(chr(92), "/")).name)
    return out


def unretire_declared_and_cited() -> int:
    """Drop a retirement entry when the file is both declared by a row and named by a package.

    "Kept but not citable" cannot be true of a file the register points at and a paper cites - that is the ledger
    contradicting the two records that decide citability. Earlier passes of the estate's own bookkeeping tools wrote
    such entries, and the estate's rule is that a contradiction is resolved by the evidence, not by the newest
    writer: so the entry goes, and the file stays citable.
    """
    led = json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.is_file() else {"superseded": []}
    names_declared, names_cited = set(declared()), set(cited_names()) | package_register_names()
    keep, gone = [], 0
    for e in led["superseded"]:
        if e.get("file") in names_declared and e.get("file") in names_cited:
            gone += 1
            continue
        keep.append(e)
    if gone:
        led["superseded"] = keep
        LEDGER.write_text(json.dumps(led, indent=1, ensure_ascii=False), encoding="utf-8")
    return gone


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--check", action="store_true", help="the default: print the census, write nothing")
    ap.add_argument("--limit", type=int, default=25)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    REG = ROOT / "00_program_registry" / "experiment_registry.csv"
    raw = REG.read_text(encoding="utf-8")
    rows = list(csv.DictReader(io.StringIO(raw)))
    cols = list(rows[0].keys())
    if a.apply:
        print(f"purged {purge_own_entries()} retirement entries written against an earlier snapshot of the estate")
        collapsed = collapse_duplicate_generations(rows)
        print(f"re-pointed {repoint_to_newest(rows, set(cited_names()))} row(s) at the newest generation on disk")
        print(f"un-retired {unretire_declared_and_cited()} file(s) that a row declares and a package cites")
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=cols, lineterminator=chr(10))
        w.writeheader()
        w.writerows(rows)
        REG.write_text(buf.getvalue(), encoding="utf-8")
        print(f"collapsed same-family duplicate declarations in {collapsed} row(s)")
    owners0 = declared()
    entries, touched = declare_cited(rows, owners0, write=a.apply)
    print(f"{len(touched)} registry row(s) point at a generation no package cites; "
          f"{len(entries)} earlier generation(s) would be retired beside them")
    for e in entries[:a.limit]:
        print(f"  {e['exp_id']}: {e['file']} -> {e['reason'][:150]}")
    if a.apply and touched:
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=cols, lineterminator=chr(10))
        w.writeheader()
        w.writerows(rows)
        REG.write_text(buf.getvalue(), encoding="utf-8")
        print(f"wrote {REG.name}: {len(touched)} row(s) now declare the cited generation")
    owners = declared()
    adopted, refused = adopt_extra_outputs(rows, owners, write=a.apply)
    print(f"{len(adopted)} companion output(s) adopted by the row of the run that wrote them; "
          f"{len(refused)} refused")
    for f, why in refused[:a.limit]:
        print(f"  REFUSED {f}: {why}")
    if a.apply and adopted:
        print(f"registry rewritten to declare {len(adopted)} additional output(s)")
    sup = L.superseded()
    cen = census(owners, sup, set(cited_names()) | package_register_names())
    kinds = collections.Counter()
    retirable, blocked = [], []
    # `later_rerun` is NOT retired: a generation newer than the one the register names is that run's current
    # artefact, so the honest move is to adopt it into the row. Retiring it leaves a row whose every JSON is
    # non-citable, which is what the wave recorder then correctly refuses to record.
    RETIRE = ("identical", "labels_only", "estimate_differs")
    ADOPT = ("later_rerun",)
    for stem, items in sorted(cen.items()):
        for p, _, keep in items:
            kind, reason = classify(p, keep, owners)
            kinds[kind] += 1
            (retirable if kind in RETIRE else blocked).append(
                {"file": str(p.relative_to(ROOT)).replace(chr(92), "/"), "name": p.name, "stem": stem,
                 "kind": kind, "reason": reason or "no declared generation of the same run exists",
                 "path": p})
    print(f"{sum(len(v) for v in cen.values())} undeclared artefact generation(s) in "
          f"{len(cen)} run families")
    print(json.dumps(kinds, indent=1, ensure_ascii=False))
    for x in blocked[:a.limit]:
        print(f"  NOT RETIRED [{x['kind']}] {x['file']}: {x['reason'][:170]}")
    if not a.apply:
        print(f"\n--check: {len(retirable)} could be retired, {len(blocked)} need an answer first; nothing written")
        return 0
    led = json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.is_file() else {
        "purpose": "artefacts kept but not citable", "superseded": []}
    have = {e["file"] for e in led["superseded"]}
    n = 0
    for x in retirable:
        if x["name"] in have:
            continue
        led["superseded"].append({"file": x["name"], "exp_id": f"EXP-{x['stem'][3:7]}",
                                  "by": "supersede_undeclared_generations.py",
                                  "at": datetime.datetime.now().isoformat(timespec="seconds"),
                                  "reason": x["reason"],
                                  "was_it_quoted": "no - no registry row declares it and no package ships it as "
                                                   "its kept generation"})
        n += 1
    LEDGER.write_text(json.dumps(led, indent=1, ensure_ascii=False), encoding="utf-8")
    adopted_newer = 0
    for x in blocked:
        if x["kind"] not in ADOPT:
            continue
        r = next((y for y in rows if y["exp_id"] == f"EXP-{x['name'][3:7]}"), None)
        if r is None:
            continue
        rel = str(x["path"].relative_to(ROOT)).replace(chr(92), "/")
        if rel not in [q.strip() for q in RR.parts_of(r.get("outputs") or "")]:
            r["outputs"] = "; ".join([q.strip() for q in RR.parts_of(r.get("outputs") or "") if q.strip()] + [rel])
            adopted_newer += 1
    blocked = [x for x in blocked if x["kind"] not in ADOPT]
    print(f"retired {n} generation(s); adopted {adopted_newer} newer generation(s) into the row of the run that "
          f"rewrote them; {LEDGER.name} now holds {len(led['superseded'])} entries")
    import csv as _csv
    dropped = drop_retired_declarations(rows)
    if dropped:
        buf = io.StringIO()
        w = _csv.DictWriter(buf, fieldnames=list(rows[0].keys()), lineterminator=chr(10))
        w.writeheader()
        w.writerows(rows)
        (ROOT / "00_program_registry" / "experiment_registry.csv").write_text(buf.getvalue(), encoding="utf-8")
    print(f"{dropped} row(s) had a now-retired file removed from their declaration")
    print(f"un-retired {unretire_declared_and_cited()} file(s) that the register or a package still names")
    still = [r["exp_id"] for r in rows if not any(RR.expand(ROOT, p) for p in RR.parts_of(r.get("outputs") or ""))]
    print(f"{len(still)} row(s) declare no file on disk: {still} "
          "(EXP-0008 is one of them by design: its console probe left nothing)")
    own = [e for e in led["superseded"]
           if e.get("by") == "supersede_undeclared_generations.py"]
    dest = ROOT / "results_raw" / f"EXP0229_generation_bookkeeping_{time.strftime('%Y%m%dT%H%M%S')}.json"
    dest.write_text(json.dumps({"exp_id": "EXP-0229",
                                "seed": "n/a (a register and ledger correction, not a measurement)",
                                "status": f"{len(own)}_generations_retired_by_this_rule",
                                "rows_repointed_at_the_cited_generation": len(touched),
                                "companion_outputs_adopted": len(adopted),
                                "generations_retired_by_this_run": n,
                                "generations_retired_by_this_rule_total": len(own),
                                "still_unaccounted": [x["file"] for x in blocked],
                                "ledger_entries_after": len(led["superseded"]),
                                "rule": "a generation older or newer than the one the register declares is retired "
                                        "with its measured difference as the reason; a file that carries a run's own "
                                        "id under a different stem is adopted as that run's additional output; "
                                        "nothing is deleted",
                                "at": datetime.datetime.now().isoformat(timespec="seconds")},
                               indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote", dest.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
