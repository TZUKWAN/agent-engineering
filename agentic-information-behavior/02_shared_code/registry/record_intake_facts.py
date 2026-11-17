"""EXP-0223: fill the columns the 86 intake rows still carry as "pending ...".

The two batches registered on 2026-09-23 entered the funnel with the fields an idea list can supply, and the
pool modules wrote a placeholder for the rest: `core_rq_h` "pending - fixed in the protocol freeze",
`data_feasibility` "pending_funnel_screen", `external_validation_dataset` "see the supplied design",
`theory_basis` "see the supplied design" for the attachment batch, and `primary_dv`/`primary_iv` empty for it.
Every one of those has since been settled by a document that exists on disk - the wave's freeze module, its
premise census, its feature frame and its battery - so the registry still reading "pending" is a stale marker
rather than an open step.

Column policy, fixed before the derivation was written:

* `core_rq_h` and `data_feasibility` are always derived: their intake value is a placeholder by construction.
* `primary_dv` and `primary_iv` are derived from the frozen design where one exists, because the freeze
  supersedes the wording of the idea; where it does not, the intake construct is kept if the batch supplied one
  and an explicit "not fixed" otherwise.
* `theory_basis` and `external_validation_dataset` are derived only where the intake left a placeholder or a
  blank. A value the researcher actually supplied is never overwritten by an inference.

Nothing is typed by hand: the RQ, hypotheses, outcomes, features, kill gate, census line and substrate label
come from `topic_designs_wave*` modules, the premise values from the same modules' machine-filled `PREMISES`
block, the robustness steps from each wave's battery artefact, and the not-frozen cases from the EXP-0115
screen artefact.

    python 02_shared_code/registry/record_intake_facts.py [--dry-run]
"""
from __future__ import annotations

import argparse
import csv
import datetime
import glob
import io
import json
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
sys.path.insert(0, str(ROOT / "02_shared_code" / "package_factory"))

REG = ROOT / "00_program_registry"
OUT = REG / "topic_intake_facts.csv"
COLS = ["topic_id", "core_rq_h", "primary_dv", "primary_iv", "theory_basis", "data_feasibility",
        "external_validation_dataset", "novelty_risk"]
FUNNEL_DECIDED = ("demoted_", "killed_", "not_promoted", "w2_parked", "w3_fold_into_", "w3_merged_into_")
INTAKE = [f"T{n:03d}" for n in list(range(101, 143)) + list(range(151, 195))]
# The strings the two pool modules write when they have nothing to record. An empty string is not a member of
# this tuple on purpose: `x.startswith("")` is true for every x, which would read a supplied value as a placeholder.
PENDING = ("pending -", "pending_funnel_screen", "see the supplied design", "pending_lit_audit")


def unset(v: str) -> bool:
    return not (v or "").strip() or (v or "").startswith(PENDING)


MODULES = sorted(pathlib.Path(ROOT / "02_shared_code" / "package_factory").glob("topic_designs_wave*.py"))


def cap(x, n: int = 900) -> str:
    return (x if isinstance(x, str) else json.dumps(x, ensure_ascii=False))[:n]


def latest(pat: str):
    f = sorted(glob.glob(str(ROOT / pat)), key=lambda x: pathlib.Path(x).stat().st_mtime)
    return pathlib.Path(f[-1]) if f else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    reg = {r["topic_id"]: r for r in csv.DictReader(io.StringIO(
        (REG / "topic_registry.csv").read_text(encoding="utf-8-sig")))}
    ev = {r["topic_id"]: r for r in csv.DictReader(io.StringIO(
        (REG / "topic_evidence.csv").read_text(encoding="utf-8")))}
    screen_f = latest("results_raw/EXP0115_funnel_screen_round5_*.json")
    screen = {t["topic_id"]: t for t in json.loads(screen_f.read_text(encoding="utf-8"))["topics"]}

    designs, mods = {}, {}
    for mp in MODULES:
        m = __import__(mp.stem)
        mods[mp.stem] = m
        for tid, d in (getattr(m, "DESIGNS", {}) or {}).items():
            if tid in designs:
                raise SystemExit(f"ABORT: {tid} is frozen twice ({designs[tid]} and {mp.stem})")
            designs[tid] = mp.stem

    out, unbuilt = {}, []
    for tid in INTAKE:
        cur, status = reg[tid], reg[tid]["status"]
        d = (mods[designs[tid]].DESIGNS.get(tid) if tid in designs else None) or {}
        m = mods.get(designs.get(tid, "")) if tid in designs else None
        if d:
            rq = cap(f"{d['rq']} || " + " / ".join(d.get("hypotheses") or []), 1800)
            dv, iv = cap(d.get("dvs") or {}, 600), cap(d.get("features") or {}, 900)
            gates = {g: v for g, v in ((getattr(m, "PREMISES", {}) or {}).get("gates") or {}).items()
                     if isinstance(v, dict) and (g.startswith(tid + "_") or tid in (v.get("blocks") or []))}
            feas = {"census": (getattr(m, "PREMISES", {}) or {}).get("census"),
                    "substrate": getattr(m, "SUBSTRATE_LABEL", ""),
                    "gates_naming_this_topic": gates,
                    "design_kill_gate": (d.get("kill_gate") or "")[:400],
                    "runs": [getattr(m, k, "") for k in ("PREMISE_EXP", "FEATURE_EXP", "BATTERY_EXP")]}
            bat = (latest(getattr(m, "BATTERY_GLOB", "")) if m else None)
            b = (json.loads(bat.read_text(encoding="utf-8")).get(tid) if bat and bat.is_file() else None) or {}
            steps = sorted(k for k in b if not k.startswith("_"))
            ext = {"substrate": getattr(m, "SUBSTRATE_LABEL", ""), "robustness_steps_run": steps or None,
                   "battery_artefact": bat.name if bat else None,
                   "second_corpus_transfer": (cap(b.get("e08") or b.get("e08_external"), 300)
                                              if (b.get("e08") or b.get("e08_external")) else
                                              "none - this design's checks are within its own substrate")}
            tb = ("no named theory anchor is claimed by the frozen design: it fixes its own constructs and their "
                  f"measurement rule (papers/{d.get('pkg')}/protocol_freeze.md)")
            nrisk = ""                                      # EXP-0160 grades this row from its own matrix
        else:
            why = "no protocol freeze - the funnel ended it as `%s`" % status
            sc = screen.get(tid) or {}
            rq = f"{why}; the question as supplied at intake: {cur['title_en']} - {cur['main_method']}"
            dv = cur["primary_dv"] or f"not fixed: {why}"
            iv = cur["primary_iv"] or f"not fixed: {why}"
            blocked = ev.get(tid) or {}
            feas = ({"screen_measurement": sc.get("reason"), "source": screen_f.name}
                    if sc.get("reason") else
                    {"premise_gate_measurement": blocked.get("measured_coverage"),
                     "not_measured": "no design was frozen, so no field census beyond the gate itself"})
            ext = {"second_corpus_transfer": "none - " + why}
            tb = "not supplied at intake, and no design was frozen for it"
            # EXP-0160 owns `novelty_risk` for every topic still in the funnel's live set; these are exactly the rows
            # it skips because the funnel already ended them, and for them the screen's own count is the verdict.
            nrisk = (f"screened, not four-family graded: EXP-0115 measured - {sc.get('reason')}; {screen_f.name}; "
                     f"the decision recorded in the status is `{status}`") \
                if status.startswith(FUNNEL_DECIDED) else ""
        rec = {"topic_id": tid, "core_rq_h": cap(rq, 1800), "primary_dv": cap(dv, 600), "primary_iv": cap(iv, 900),
               "theory_basis": cap(tb, 600) if unset(cur["theory_basis"]) else cur["theory_basis"],
               "data_feasibility": cap(feas, 900),
               "external_validation_dataset": cap(ext, 900) if unset(cur["external_validation_dataset"])
               else cur["external_validation_dataset"],
               "novelty_risk": cap(nrisk, 900)}
        unbuilt += [tid] if tid not in designs else []
        out[tid] = rec

    print(f"{len(out)} topic(s): {len(out) - len(unbuilt)} with a frozen design, {len(unbuilt)} without: {unbuilt}")
    for tid in ("T105", "T155", "T186"):
        print(f"  {tid}: dv={out[tid]['primary_dv'][:70]} | theory={out[tid]['theory_basis'][:60]}")
    payload = {"exp_id": "EXP-0223", "seed": "n/a (a read of the freeze modules and their artefacts)",
               "sources": {"modules": [p.name for p in MODULES], "screen": screen_f.name},
               "policy": list(COLS[1:]), "with_design": sorted(set(INTAKE) - set(unbuilt)),
               "without_design": sorted(unbuilt), "facts": out,
               "started_at": datetime.datetime.now().isoformat(timespec="seconds"),
               "invocation": " ".join([sys.executable] + sys.argv)}
    dest = ROOT / "results_raw" / f"EXP0223_intake_facts_{time.strftime('%Y%m%dT%H%M%S')}.json"
    if a.dry_run:
        print("dry run: nothing written")
        return 0
    dest.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLS, lineterminator=chr(10))
    w.writeheader()
    for tid in sorted(out):
        w.writerow({c: str(out[tid].get(c) or "") for c in COLS})
    OUT.write_text(buf.getvalue(), encoding="utf-8")
    print(f"wrote {OUT.name} and {dest.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
