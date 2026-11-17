"""Record the two wave-2 topics that the premise census blocked, into the topic table's evidence file.

T112 (negative boundary language) and T117 (noun- vs verb-centred descriptions) were screened, queued and designed, and
then EXP-0135 measured that their constructs are not identifiable on this corpus: negation markers appear in 2.9% of
candidate descriptions against a 5% identifiability gate, and the centring rule puts 89.0% of texts in one bin against
an 80% gate (with the independently written second rule agreeing only at kappa 0.414).

The spec's rule is that a fired kill gate is a result, not an obstacle: the topics are recorded as blocked with the
measured numbers, and no experiment is run on a construct the corpus cannot carry.
"""
import csv
import io
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
F = ROOT / "00_program_registry" / "topic_evidence.csv"
COLS = ["topic_id", "package", "exp_ids", "measured_coverage", "figures_tables", "collision_verdict", "status"]
CENSUS_FILES = sorted((ROOT / "results_raw").glob("EXP0135_wave2_premise_census_*.json"),
                      key=lambda f: f.stat().st_mtime)
if not CENSUS_FILES:
    raise SystemExit("ABORT: EXP-0135 has not run, so no premise measurement exists to record")
CENSUS = json.loads(CENSUS_FILES[-1].read_text(encoding="utf-8"))
M, G = CENSUS["measured"], CENSUS["kill_gates"]

rows = list(csv.DictReader(io.StringIO(F.read_text(encoding="utf-8")))) if F.is_file() else []
add = {
 "T112": {"status": "w2_blocked_premise_negation_prevalence_0p029_below_gate_0p05",
          "collision_verdict": "gate T112_negation_identifiable fired"},
 "T117": {"status": "w2_blocked_premise_centring_dominance_0p890_above_gate_0p80_kappa_0p414",
          "collision_verdict": "gate T117_centring_contrast fired; second centring rule agrees only at kappa 0.414"},
}
for tid, extra in add.items():
    rows = [r for r in rows if r.get("topic_id") != tid]
    rows.append({"topic_id": tid, "package": "", "exp_ids": "EXP-0135",
                 "measured_coverage": json.dumps(M, ensure_ascii=False)[:900],
                 "figures_tables": "none - no experiment was run on an unidentifiable construct",
                 "collision_verdict": extra["collision_verdict"], "status": extra["status"]})
buf = io.StringIO()
w = csv.DictWriter(buf, fieldnames=COLS, lineterminator=chr(10))
w.writeheader()
for r in sorted(rows, key=lambda x: x.get("topic_id", "")):
    w.writerow({c: str(r.get(c) or "") for c in COLS})
F.write_text(buf.getvalue(), encoding="utf-8")

# The design directory was created when these topics were queued, so package_audit would otherwise report each of
# them as a package missing 28 deliverables. A blocked topic is a recorded decision, so it gets a generated notice
# naming the gate and the artefact that measured it - and the audit checks that the named artefact exists, which is
# what stops "blocked" from becoming a way to make a package disappear without a trace.
for tid, extra in add.items():
    pkg_dir = __import__("topic_designs_wave2").DESIGNS.get(tid, {}).get("pkg", "")
    if not pkg_dir:
        continue
    d = ROOT / "papers" / pkg_dir
    if not d.is_dir():
        continue
    gate = next((k for k, v in G.items() if tid in str(k) or tid in str(v)), "")
    (d / "BLOCKED.md").write_text("\n".join([
        f"# {tid} - blocked at the premise gate, no package", "",
        f"Written by `02_shared_code/package_factory/record_wave2_blocked.py`; do not hand-edit.", "",
        f"Status: `{extra['status']}`",
        f"Kill gate: `{gate or extra['collision_verdict'].split(';')[0]}`",
        f"Verdict record: {extra['collision_verdict']}", "",
        f"Measurement: `results_raw/{CENSUS_FILES[-1].name}` (EXP-0135, the wave-2 premise census).",
        "Measured values: " + json.dumps(M, ensure_ascii=False)[:700], "",
        "No experiment was run on a construct this corpus cannot carry, and no threshold was lowered after the "
        "measurement. The protocol freeze in this directory predates the census and is kept as the record of what "
        "was intended.", "", ""]) + "\n", encoding="utf-8")
    print("wrote", (d / "BLOCKED.md").relative_to(ROOT))
print("wrote", F.name, "for", sorted(add), "| gates:", G)
