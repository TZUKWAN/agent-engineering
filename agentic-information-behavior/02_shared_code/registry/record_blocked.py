"""Record the topics a wave's premise census stopped, into the evidence file and into their design directories.

A fired kill gate is a result, not an obstacle, and the spec's queue discipline says it stops the claim instead of
being renegotiated once an estimate exists. Two things therefore have to survive the wave:

1. a row in `00_program_registry/topic_evidence.csv` - which `build_topic_registry.py` overlays onto the topic table -
   carrying the *measured* value, the gate it fell short of, and the experiment that measured it;
2. a `BLOCKED.md` in the design directory, so `package_audit.py` reports the directory as a blocked record instead of
   a package missing 28 deliverables, and so the block can be traced to an artefact that exists on disk. The audit
   checks that the named experiment has an artefact, which is what stops "blocked" from being a way to make a topic
   disappear without a trace.

The scope comes from the design itself: `gate_scope` says whether a fired gate stops the whole design ("design"),
one named hypothesis ("H1"/"H3"), or merely excludes rows ("rows"). Only the first writes a BLOCKED.md.

    python 02_shared_code/registry/record_blocked.py --designs topic_designs_wave3
"""
from __future__ import annotations

import argparse
import csv
import glob
import io
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
sys.path.insert(0, str(ROOT / "02_shared_code" / "package_factory"))

F = ROOT / "00_program_registry" / "topic_evidence.csv"
COLS = ["topic_id", "package", "exp_ids", "measured_coverage", "figures_tables", "collision_verdict", "status"]


def latest(pat):
    f = sorted(glob.glob(str(ROOT / pat)), key=lambda x: pathlib.Path(x).stat().st_mtime)
    return pathlib.Path(f[-1]) if f else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--designs", required=True)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    TD = __import__(a.designs)
    census_file = latest(getattr(TD, "PREMISE_GLOB", "")) if getattr(TD, "PREMISE_GLOB", "") else None
    if census_file is None:
        raise SystemExit(f"ABORT: {a.designs} names no premise-census artefact, so no measurement exists to record")
    cen = json.loads(census_file.read_text(encoding="utf-8"))
    verdict = cen.get("verdict") or {}
    blocked = list(verdict.get("blocked_whole_design") or [])
    bad = [b for b in blocked if not re.fullmatch(r"T\d{3}", str(b))]
    if bad:
        # Wave 4's first four generations put the gate key here, which filed an evidence row whose topic_id was
        # `G7_outcome_label_available`: a real block, recorded under a name no topic carries.
        raise SystemExit(f"ABORT: {a.designs} census names {bad} as a blocked design, and those are not topic ids - "
                         f"a design-scope gate must emit the topics its sentence scopes")
    inherited = getattr(TD, "INHERITED_BLOCKS", {}) or {}
    blocked = blocked + [k for k in inherited if k not in blocked]
    if not blocked:
        print(f"{a.designs}: no whole-design block recorded by {census_file.name}; nothing to write")
        return 0
    rows = list(csv.DictReader(io.StringIO(F.read_text(encoding="utf-8")))) if F.is_file() else []
    gk = cen.get("kill_gates") or cen.get("gates") or {}      # wave-3 and wave-4 name the block differently
    scopes = cen.get("gate_scopes") or {}                     # gate -> {scope, blocks, threshold}, pre-registered
    if not scopes and gk and all(isinstance(v, dict) and "blocks" in v for v in gk.values()):
        # wave 7 and wave 8 carry the scope and the blocked topics inside each gate record, so that is what says
        # which topic a fired gate stops - and a block has to name the value that stopped it, not just the gate
        scopes = {k: {"scope": v.get("scope"), "blocks": v.get("blocks") or []} for k, v in gk.items()}
    for tid in blocked:
        d = TD.DESIGNS.get(tid) or {}
        gates = {k: v for k, v in gk.items() if k.startswith(tid + "_")}
        for g, s in scopes.items():                           # plus every gate whose declared scope names this topic
            if tid in (s.get("blocks") or []):
                gates[g] = gk.get(g)
        if tid in inherited:                                  # an inherited block cites the earlier run's measurement verbatim
            measured = dict(inherited[tid]["measured"])
            why = inherited[tid]["why"]
        else:
            measured = {k: v for k, v in (cen.get("measured") or {}).items() if k.startswith(tid + "_")}
            if not measured and gates:
                # a census that names its gates rather than its topics still measured the value that fired; the
                # block row has to carry that number, or "blocked" degrades into an assertion
                measured = {g: (v or {}).get("measured") for g, v in gates.items()}
            why = (d.get("kill_gate") or "").strip()
        pkg = d.get("pkg", "")
        status = f"w_blocked_premise_{tid}_" + "_".join(f"{k.split('_', 1)[-1]}={v}" for k, v in measured.items())
        rows = [r for r in rows if r.get("topic_id") != tid]
        rows.append({"topic_id": tid, "package": "", "exp_ids": getattr(TD, "PREMISE_EXP", ""),
                     "measured_coverage": json.dumps({"census": census_file.name, "measured": measured,
                                                      "gates": gates}, ensure_ascii=False)[:900],
                     "figures_tables": "none - no experiment was run on a construct this corpus cannot carry",
                     "collision_verdict": f"gate fired: {why}"[:900], "status": status[:240]})
        # An inherited block has no design entry, hence no package directory: writing to `papers/<empty>` would
        # drop a BLOCKED.md at the root of the papers tree, which is what the first version did.
        pdir = (ROOT / "papers" / pkg) if pkg else None
        if pdir is not None and pdir.is_dir():
            (pdir / "BLOCKED.md").write_text("\n".join([
                f"# {tid} - blocked at its own premise gate, no package",
                "",
                f"Written by `02_shared_code/registry/record_blocked.py --designs {a.designs}`; do not hand-edit.",
                "",
                (f"Inherited, not re-measured: {inherited[tid]['measured']['source']}" if tid in inherited else ""),
                "",
                f"Kill gate as frozen: {why}",
                f"Gate values as measured (`{census_file.name}`): "
                + json.dumps({**gates, **measured}, ensure_ascii=False),
                "",
                "No experiment was run on a construct this corpus cannot carry, and no threshold was lowered after "
                "the measurement was read. The protocol freeze in this directory predates the census and is kept as "
                "the record of what was intended.", "", ""]) + "\n", encoding="utf-8")
            print(f"  {tid}: {pdir.name}/BLOCKED.md written")
        elif pdir is None:
            print(f"  {tid}: no package directory (block inherited from an earlier wave); evidence row only")
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLS, lineterminator=chr(10))
    w.writeheader()
    for r in sorted(rows, key=lambda x: x.get("topic_id", "")):
        w.writerow({c: str(r.get(c) or "") for c in COLS})
    F.write_text(buf.getvalue(), encoding="utf-8")
    print(f"wrote {F.name}: blocked rows now {blocked} (census {census_file.name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
