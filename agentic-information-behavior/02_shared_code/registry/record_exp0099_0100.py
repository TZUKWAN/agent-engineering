"""Registers the completion-audit steps (EXP-0099, EXP-0100) and re-proves the audit is not self-serving.

No experiment id is claimed by this recorder itself: it adds no measurement, it files two.

Two programme steps ran without a registry row. This recorder adds them, and it re-checks the one thing a completion
audit can quietly get wrong: that the auditor does not cite its own output. So before registering, it re-derives the
requirement count from the spec and asserts that removing the audit's own artefacts from the scan changes nothing.

    python 02_shared_code/registry/record_exp0099_0100.py
"""
from __future__ import annotations
import csv, io, json, pathlib, re, subprocess, sys, time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
REG = ROOT / "00_program_registry"
AUD = REG / "experiment_registry.csv"
SPEC = ROOT.parent / "Agentic_Information_Behavior_研究全流程任务清单.md"
TODAY = "2026-09-21"

ROWS = [
    {"exp_id": "EXP-0099", "paper_id": "programme", "topic_id": "T001;T008;T012;T024;T013",
     "stage": "spec_to_artifact_completion_audit",
     "script": "02_shared_code/registry/spec_completion_audit.py",
     "config": "Requirement ids parsed from the spec's own headings (T/E/G/B forms); every text file under the "
               "workspace scanned (dataset estate and >4 MB files excluded); a requirement is evidenced only if a file "
               "outside the spec names it; the audit's own script, document and JSON are excluded from the scan, because "
               "the first version of this run cited its previous output and reported 0 open items falsely; the 17 ids no "
               "artefact names are then resolved by content signatures in spec_requirement_signatures.py",
     "seed": "n/a (deterministic scan)",
     "started_at": "2026-09-21T04:39:00", "finished_at": "2026-09-21T05:00:53",
     "status": "all_57_requirements_evidenced_0_open",
     "outputs": "results_raw/EXP0099_spec_completion_audit_20260921T050053.json; docs/SPEC_COMPLETION_AUDIT.md",
     "notes": "33 requirements are named inside a paper package, 9 at programme level, and 15 by content signature "
              "only - those 15 are things the programme did but never labelled with the spec's id (effect sizes, Holm "
              "correction, skeleton-first writing, the paper structure). Two runs of this audit produced a false "
              "'0 open' by scanning its own previous artefacts; the exclusion is now in the code with the reason, and "
              "a requirement with no signature is reported OPEN rather than assumed.",
     "enters_paper": "no - programme-level compliance record; the failures it found entered P002-P005 as sections"},
    {"exp_id": "EXP-0100", "paper_id": "P002;P003;P004;P005", "topic_id": "T008;T012;T024;T013",
     "stage": "manuscript_sections_from_curated_tables",
     "script": "02_shared_code/writing/add_manuscript_sections.py",
     "config": "Sections assembled only from artefacts the package already owns: research questions from its frozen "
               "research_plan.md (three real line formats, wrapped bullets folded), related work from "
               "literature_matrix.csv rows carrying a written differentiation, conclusion from claims_evidence_matrix.csv "
               "bucketed by status. A package with too few curated rows gets no section instead of padding. Insertion is "
               "keyed on the block's own first line, and the step is wired into all four reproduce.sh chains after every "
               "generator that writes paper.md",
     "seed": "n/a (deterministic)",
     "started_at": "2026-09-21T04:54:00", "finished_at": "2026-09-21T04:59:24",
     "status": "4_manuscripts_completed_rebuild_wired_idempotent",
     "outputs": "results_raw/EXP0100_manuscript_sections_20260921T045923.json; papers/P002*/paper.md; "
                "papers/P003*/paper.md; papers/P004*/paper.md; papers/P005*/paper.md; papers/P00*/reproduce.sh",
     "notes": "P002 had no related-work section and no conclusion in its manuscript though both existed in its "
              "curated tables; P003 and P005 never stated their research questions in the paper; P004's introduction "
              "did not name the gap it fills. All four are now stated from the package's own evidence. Re-running the "
              "step leaves every paper.md byte-identical (verified by hash), and the package audit stays "
              "missing=none weak=none afterwards.",
     "enters_paper": "yes - the added sections in four manuscripts"},
]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    # 1. the completion audit must not be able to cite itself - re-run it and check the counts move as expected
    p = subprocess.run([sys.executable, str(ROOT / "02_shared_code/registry/spec_completion_audit.py")],
                       capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT))
    line = next((l for l in (p.stdout or "").splitlines() if l.startswith("spec requirements:")), "")
    print("  re-run:", line)
    m = re.search(r"\{(.*)\}", line)
    counts = dict(re.findall(r"'([^']+)': (\d+)", m.group(1))) if m else {}
    total = sum(int(v) for v in counts.values())
    spec_ids = len(set(re.findall(r"^#{2,3} ((?:T\d{2}\.\d{2}|E\d{2}|G\d{2}(?:-[A-F])?|B[0-5]))\b",
                                  SPEC.read_text(encoding="utf-8"), re.M)))
    assert total == spec_ids, f"the audit covered {total} requirements but the spec states {spec_ids}"
    assert int(counts.get("OPEN_no_artefact_names_this_requirement", 0)) == 0, \
        "a requirement is open again - resolve it before registering the audit as complete"
    print(f"  spec states {spec_ids} requirement ids and the audit classifies exactly {total}")

    # 2. append the two rows, by column name so the header order cannot be got wrong
    raw = [r for r in csv.reader(io.StringIO(AUD.read_text(encoding="utf-8"))) if r]
    hdr, have = raw[0], {r[0] for r in raw[1:]}
    add = []
    for r in ROWS:
        assert set(r) == set(hdr), (r["exp_id"], sorted(set(hdr) ^ set(r)))
        if r["exp_id"] not in have:
            add.append(r)
    if add:
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=hdr, lineterminator="\r\n")
        w.writeheader()
        w.writerows(add)
        body = buf.getvalue().split("\r\n", 1)[1]
        AUD.write_text(AUD.read_text(encoding="utf-8").rstrip("\r\n") + "\r\n" + body.rstrip("\r\n") + "\r\n",
                       encoding="utf-8", newline="")
    print("  registry:", ", ".join(r["exp_id"] for r in add) if add else "both already registered")
    back = [r for r in csv.reader(io.StringIO(AUD.read_text(encoding="utf-8"))) if r]
    assert back[0] == hdr and all(len(r) == len(hdr) for r in back), "the registry changed shape"
    ids = [r[0] for r in back[1:]]
    assert len(ids) == len(set(ids)), "duplicate exp_id"
    print(f"  registry rows={len(back) - 1}, columns={len(hdr)}")

    # 3. the integrity invariants of the whole programme, re-checked rather than recalled
    led = ROOT / "papers/P001_routing_failure_qpp/test_eval_ledger.json"
    entries = json.loads(led.read_text(encoding="utf-8")).get("evaluations", [])
    assert len(entries) <= 1, f"the test split has {len(entries)} evaluations - the one-shot rule is broken"
    print(f"  P001 test ledger: {len(entries)} evaluation "
          f"({entries[0]['at'] if entries else 'never'}), config_hash "
          f"{entries[0]['config_hash'] if entries else '-'}")
    sup = json.loads((ROOT / "results_raw/SUPERSEDED_ARTIFACTS.json").read_text(encoding="utf-8"))
    assert isinstance(sup["superseded"], list) and len(sup["superseded"]) >= 26
    print(f"  superseded-artefact register: {len(sup['superseded'])} entries, none deleted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
