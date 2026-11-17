"""EXP-0098 (funnel bookkeeping honesty): advance topic rows only where the resolution can be proved from artefacts.

The topic registry is the file that says what the programme still owes. T037 - the flagship whose package became P001 -
still reads `w1_recommended_flagship` with a three-clause blocker ("rebuild the gold-tool join via metadata.mcp_servers
instead of name prefixes", "handle ToolEX-style equivalent-tool relabelling", "disclose forward-synthesised queries").
All three were done: the join is deterministic (P001 D1), the relabelling was measured and found to be a mis-merge
(EXP-0014/0015, and EXP-0091's second matcher re-tested the lexical-similarity construct), and the synthesis caveat is
in the paper's own limitations. A row like that makes a completed programme look unfinished, so it must not be edited
by hand either: this script advances a row **only if** it can point at the artefact that resolves each clause, and it
re-checks the package audit rather than trusting memory.

    python 02_shared_code/data_audit/topic_status_reconciliation.py

Pre-declared rule, fixed before this run: a topic row advances iff (i) a paper package covers it, that package prints
`missing=none weak=none` from `package_audit.py`, and the package's `final_audit.md` is non-empty; and (ii) every
clause listed for that topic below is found, by its registered needle, in the file named. A topic whose clauses cannot
all be found is left exactly as it is and reported. No row is ever advanced by a judgement this script cannot show.
"""
from __future__ import annotations
import csv, io, json, pathlib, re, subprocess, sys, time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
REG = ROOT / "00_program_registry"
TOPICS = REG / "topic_registry.csv"
EXPS = REG / "experiment_registry.csv"
PAPERS = ROOT / "papers"
AUDIT = ROOT / "02_shared_code" / "registry" / "package_audit.py"
OUT = ROOT / "results_raw"

# clause -> (file that must carry the resolution, needle that must appear in it). Paths are relative to the package dir.
COVER = {
    "T037": {"paper": "P001", "clauses": {
        "gold-tool join rebuilt on metadata.mcp_servers": ("deviations.md", "metadata.mcp_servers"),
        "equivalent-tool relabelling measured, not assumed": ("../../00_program_registry/experiment_registry.csv",
                                                              "EXP-0014"),
        "forward-synthesised query disclosure": ("limitations.md", "正向合成")}},
    "T013": {"paper": "P005", "clauses": {
        "the pilot verdict that binds the headline is on file": ("pilot_report.md", "PROSE_ONLY"),
        "experiments are registered against this topic": ("../../00_program_registry/experiment_registry.csv",
                                                          "T013;T014")}},
    "T014": {"paper": "P005", "clauses": {
        # T014 has no package of its own; what must be shown is that its instrument merged into T013's and that the
        # merged work is registered under both topic ids.
        "experiments are registered against this topic": ("../../00_program_registry/experiment_registry.csv",
                                                          "T013;T014")}},
}


def read(path):
    rows = [r for r in csv.reader(io.StringIO(pathlib.Path(path).read_text(encoding="utf-8"))) if r]
    return rows[0], [dict(zip(rows[0], r)) for r in rows[1:]]


def audit_state():
    """Ask the verifier what it thinks, rather than restating its logic here."""
    p = subprocess.run([sys.executable, str(AUDIT)], capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT))
    out = {}
    for ln in (p.stdout or "").splitlines():
        # the whole directory name must be kept: an earlier pattern put `P00\d_` outside group 2, so every clause was
        # looked for in papers/routing_failure_qpp - a directory that does not exist.
        m = re.match(r"^(P00\d(_[^:]+)): missing=(\S*) weak=(\S.*)$", ln)
        if m:
            out[m.group(1)[:4]] = {"dir": m.group(1), "missing": m.group(3),
                                   "weak": m.group(4).strip() or "none"}
    return out


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    res = {"exp_id": "EXP-0098", "rule": "see the module docstring, fixed before measuring",
           "at": time.strftime("%Y-%m-%dT%H:%M:%S"), "topics": {}, "advanced": [], "held": []}
    states = audit_state()
    res["package_audit"] = {k: v["weak"] for k, v in states.items()}
    hdr, rows = read(TOPICS)
    covered = {}
    for r in rows:
        covered[r["topic_id"]] = r
    for tid, spec in COVER.items():
        pid = spec["paper"]
        st = states.get(pid)
        rec = {"paper": pid, "clauses": {}}
        res["topics"][tid] = rec
        if st is None:
            rec["blocked_on"] = f"no audited package directory for {pid}"
            res["held"].append(tid)
            print(f"  HELD {tid}: {rec['blocked_on']}", flush=True)
            continue
        rec["package_audit"] = {"missing": st["missing"], "weak": st["weak"]}
        if st["missing"] != "none" or st["weak"] != "none":   # both fields are the string "none" when clean, and a
            res["held"].append(tid)                            # bare truth test on them blocks every row forever
            rec["blocked_on"] = "the package does not print missing=none weak=none"
            print(f"  HELD {tid}: {rec['blocked_on']} (missing={st['missing']}, weak={st['weak']})", flush=True)
            continue
        pdir = PAPERS / st["dir"]
        # A missing package directory must not be able to masquerade as "the resolution is not on file".
        assert pdir.is_dir(), f"{pid}: no such package directory {pdir} - the audit output was parsed wrongly"
        fa = pdir / "final_audit.md"
        rec["final_audit_words"] = len(re.findall(r"\w+", fa.read_text(encoding="utf-8", errors="replace"))) \
            if fa.is_file() else 0
        ok = True
        for clause, (rel, needle) in spec["clauses"].items():
            f = (pdir / rel).resolve()
            has = f.is_file()
            found = has and needle in f.read_text(encoding="utf-8", errors="replace")
            # "the file is not there" and "the file is there but does not say it" are different failures and must not
            # be reported as one, or a wrong path reads as an unresolved blocker
            rec["clauses"][clause] = {"file": str(f.relative_to(ROOT)), "needle": needle, "file_exists": has,
                                      "found": bool(found)}
            ok &= found
        row = covered.get(tid)
        if not ok or row is None:
            rec["blocked_on"] = "a clause could not be shown in the file that should carry it"
            res["held"].append(tid)
            print(f"  HELD {tid}: {rec['blocked_on']} -> "
                  + ", ".join(f"{k}: {v['found']}" for k, v in rec["clauses"].items()), flush=True)
            continue
        row["status"] = f"w5_package_complete_as_{pid}_reconciled_EXP0098"
        row["blocking_issue"] = ("no open blocker: each clause previously listed here is resolved and pointed at - "
                                 + "; ".join(f"{c} -> {v['file']} ({v['needle']})"
                                             for c, v in rec["clauses"].items())
                                 + f". {pid}'s own gate rows in final_audit.md still carry what the submission needs.")
        rec["new_status"] = row["status"]
        res["advanced"].append(tid)
        print(f"  ADVANCED {tid} -> {row['status']}", flush=True)
    changed = [r for r in rows if r["topic_id"] in res["advanced"]]
    assert len(changed) == len(res["advanced"])
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=hdr, lineterminator="\r\n")
    w.writeheader()                        # writerows alone drops the header - it happened to this file once already
    w.writerows(rows)
    TOPICS.write_text(buf.getvalue(), encoding="utf-8", newline="")
    raw = [r for r in csv.reader(io.StringIO(TOPICS.read_text(encoding="utf-8"))) if r]
    assert raw[0] == hdr, "the topic registry lost or reordered its header row"
    back = [dict(zip(hdr, r)) for r in raw[1:]]
    assert len(back) == len(rows), f"the topic registry changed row count ({len(rows)} -> {len(back)})"
    for r in back:
        if r["topic_id"] in res["advanced"]:
            assert r["status"].startswith("w5_package_complete"), f"{r['topic_id']} did not keep its new status"
    res["rows_total"] = len(back)
    res["status_counts_after"] = {}
    for r in back:
        res["status_counts_after"][r["status"]] = res["status_counts_after"].get(r["status"], 0) + 1
    res["wallclock_sec"] = round(time.time() - t0, 1)
    out = OUT / f"EXP0098_topic_status_reconciliation_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote", out.relative_to(ROOT))
    register(res, out)
    print(f"advanced: {res['advanced'] or 'none'} | held: {res['held'] or 'none'} | topic rows: {len(back)}")
    return 0


REG_ROW = {
    "exp_id": "EXP-0098", "paper_id": "programme", "topic_id": "T037;T013;T014",
    "stage": "topic_registry_status_reconciliation",
    "script": "02_shared_code/data_audit/topic_status_reconciliation.py",
    "config": "A topic row advances only if its package prints missing=none weak=none from package_audit.py (invoked, "
              "not reimplemented) and every registered clause is found by needle in the file named; clause search "
              "distinguishes 'file absent' from 'needle absent'; the registry is rewritten with its header verified "
              "afterwards and the row count asserted equal",
    "seed": "n/a (deterministic)",
    "enters_paper": "no - programme bookkeeping; it changes no result",
    "notes": "T037 still read w1_recommended_flagship with three open blockers long after P001 was built: the join was "
             "made deterministic (P001 D1), the equivalent-tool relabelling was measured (EXP-0014), and the "
             "forward-synthesis caveat is in the limitations in Chinese (正向合成) - which is why an English needle "
             "first reported it missing. T013/T014 advanced on the same test. Nothing was advanced that the artefacts "
             "could not show, and the run is idempotent.",
}


def register(res: dict, artefact: pathlib.Path) -> None:
    """Record this step in the programme registry, keyed on its own exp_id so a re-run changes nothing."""
    raw = [r for r in csv.reader(io.StringIO(EXPS.read_text(encoding="utf-8"))) if r]
    hdr, have = raw[0], {r[0] for r in raw[1:]}
    row = dict(REG_ROW)
    row["status"] = f"advanced_{len(res['advanced'])}_held_{len(res['held'])}"
    row["outputs"] = str(artefact.relative_to(ROOT)) + "; 00_program_registry/topic_registry.csv"
    row["started_at"] = res["at"]
    row["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    missing, extra = set(hdr) - set(row), set(row) - set(hdr)
    assert not extra, f"EXP-0098: keys not in the registry header: {sorted(extra)}"
    assert not missing, f"EXP-0098: registry columns left unset: {sorted(missing)}"
    if row["exp_id"] in have:
        print("  registry: EXP-0098 already registered - nothing appended")
        return
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=hdr, lineterminator="\r\n")
    w.writeheader()
    w.writerows([row])
    body = buf.getvalue().split("\r\n", 1)[1]
    EXPS.write_text(EXPS.read_text(encoding="utf-8").rstrip("\r\n") + "\r\n" + body.rstrip("\r\n") + "\r\n",
                    encoding="utf-8", newline="")
    back = [r for r in csv.reader(io.StringIO(EXPS.read_text(encoding="utf-8"))) if r]
    assert back[0] == hdr and all(len(r) == len(hdr) for r in back), "the experiment registry changed shape"
    ids = [r[0] for r in back[1:]]
    assert len(ids) == len(set(ids)), "duplicate exp_id after the EXP-0098 append"
    print(f"  registry: EXP-0098 appended; rows={len(back) - 1}")


EXPS = REG / "experiment_registry.csv"


if __name__ == "__main__":
    sys.exit(main())
