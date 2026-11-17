"""EXP-0109 into the record: register the canonicalisation test suite and say what it pins.

§21.4 asks for a unit test per transformation of the canonical intermediate representation. Until this run none existed
anywhere in the workspace, and the completion audit could not see the requirement because it parses only headings whose
label is T/E/G/B - §21.4 is labelled numerically. This recorder registers the suite, points each package's
`CONTAMINATION_AND_COST.md` audience at it through a programme-level note, and re-runs it so the registry row's status is
the outcome of the run that wrote it rather than of a copy.

    python 02_shared_code/registry/record_exp0109_docs.py
"""
from __future__ import annotations
import csv, glob, io, json, pathlib, subprocess, sys, time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
REG = ROOT / "00_program_registry" / "experiment_registry.csv"
ART = ROOT / "results_raw" / "EXP0109_canonical_ir_tests.json"
TESTS = "02_shared_code/trajectory_parser/test_canonical_ir.py"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    p = subprocess.run([sys.executable, str(ROOT / TESTS), "--json", str(ART)], cwd=str(ROOT),
                       capture_output=True, text=True, encoding="utf-8")
    tail = [l for l in (p.stdout or "").splitlines() if "canonicalisation tests pass" in l]
    print("  suite:", tail[-1] if tail else "(no summary line)", "| exit", p.returncode)
    assert p.returncode == 0 and tail, "the canonicalisation suite is failing - fix the transformation, not the test"
    d = json.loads(ART.read_text(encoding="utf-8"))
    assert d["verdict"] == "ALL_TESTS_PASS" and not d["failed"], d["failed"]
    raw = [r for r in csv.reader(io.StringIO(REG.read_text(encoding="utf-8"))) if r]
    hdr, have = raw[0], {r[0] for r in raw[1:]}
    at, wc = d.get("at", ""), float(d.get("wallclock_sec") or 0)
    try:
        start = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.mktime(time.strptime(at, "%Y-%m-%dT%H:%M:%S")) - wc))
    except (ValueError, TypeError):
        start = at
    row = {"exp_id": "EXP-0109", "paper_id": "programme", "topic_id": "", "stage": "canonical_ir_unit_tests",
           "script": TESTS,
           "config": "12 cases over the four canonical surfaces the papers read: message-key vocabularies "
                     "(role/content, from/value, from/loss/value) and Toucan's JSON-string message column, the "
                     "metadata/nested generation-config readers, catalogue parsing and rejection, the prompt_id "
                     "dev/test bucket, and the stage coder's turn split, cue priority and observation kinds. The tests "
                     "import the production functions, so a changed transformation breaks a test rather than a number.",
           "seed": "n/a (no sampling)", "started_at": start, "finished_at": at,
           "status": f"ALL_TESTS_PASS_{d['cases']}_of_{d['cases']}",
           "outputs": f"results_raw/{ART.name}; docs/canonical_ir_tests.md",
           "notes": "Closes the spec's 21.4 requirement that each transformation of the canonical intermediate "
                    "representation carry a unit test; the requirement had been invisible to the completion audit "
                    "because 21.x headings are labelled numerically, and no test file existed anywhere before this run. "
                    "Two of the pinned behaviours were discovered here: the coder's thought is only the prose before the "
                    "first fenced command (text after a command is not read), and a turn with no command can only be "
                    "`clarification` or `uncodable`, which is what keeps the `end` share from inflating.",
           "enters_paper": "programme-level instrument record"}
    if row["exp_id"] in have:
        rows = [r if r[0] != row["exp_id"] else [row[c] for c in hdr] for r in raw]
        action = "status refreshed"
    else:
        rows, action = raw + [[row[c] for c in hdr]], "appended"
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    for r in rows:
        w.writerow(r)
    REG.write_text(buf.getvalue(), encoding="utf-8", newline="")
    back = [r for r in csv.reader(io.StringIO(REG.read_text(encoding="utf-8"))) if r]
    assert back[0] == hdr and all(len(r) == len(hdr) for r in back), "registry shape broke"
    ids = [r[0] for r in back[1:]]
    assert len(ids) == len(set(ids)), "duplicate exp_id"
    print(f"  registry: EXP-0109 {action} | rows={len(back) - 1}")

    lines = ["# Canonical intermediate representation: the unit tests behind it (EXP-0109)", "",
             "Spec 21.4 allows a cross-schema study to map different original formats onto one canonical representation,",
             "but requires **each transformation to have a unit test** and the original schema to be kept. This is the",
             "record that the second half of that sentence is now true, and what each group of cases pins.", "",
             "| case | what it pins |", "|---|---|"]
    lines += [f"| `{c['test']}` | {c['doc']} |" for c in d["results"]]
    lines += ["", f"Suite status: **{d['verdict']}**, {d['cases']} cases, {d['wallclock_sec']} s, run by "
              f"`python {TESTS}`. The module imports the production functions "
              "(`build_toucan_routing_dataset`, `isp_stage_coder`, `canonical_conformance_audit_p003`) rather than "
              "copies, so a change to a transformation fails a test instead of moving a published number.", "",
              "Two behaviours became explicit while writing these tests:",
              "* the stage coder's *thought* is only the prose **before** the first fenced command - text after a command",
              "  is not part of the input to the label, which is why `clarification` keys on opening prose;",
              "* a turn with no command can only be `clarification` or `uncodable`: a thought that merely contains the",
              "  word `done` cannot mark an episode finished, so the `end` share is not inflated by wishful phrasing.",
              "", "Neither behaviour was documented before; both are now asserted on every run of the chain."]
    out = ROOT / "docs" / "canonical_ir_tests.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="")
    print("  wrote", out.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
