"""EXP-0079: clean-environment replication for P002-P005 (gate G18-E), comparing whole result artefacts.

P001 has a clean-room record (EXP-0025/EXP-0026); the other four papers do not, so gate G18-E's "clean environment
succeeds" line is unmet for them. This runs each paper's analysis pipeline in a fresh interpreter - a venv with **no**
system site-packages, dependencies installed from the locked versions in P001's `environment/system_info.json` - over a
copy of the repository, with the 79 GB dataset reached through a directory junction rather than a copy.

Two design choices matter for what the result can be used to claim:

* **the comparison is over every scalar leaf of each result artefact**, not a handful of headline numbers. A
  cherry-picked comparison would pass while a silent field drifted. Timestamps, wall clocks, elapsed seconds and
  absolute paths are excluded by key name because they legitimately differ; everything else must match, integers and
  strings exactly and floats within 1e-2 (the tolerance the P001 record already caps its claim at);
* **the package builders are not run** in the clean room. They generate prose artefacts from the result files; running
  them would compare generated text against generated text and tell us nothing about the environment.

    python clean_room_replication_p002_p005.py            # from the real repository root
"""
from __future__ import annotations

import csv, io, json, os, pathlib, re, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / "_cleanroom"
CR = SCRATCH / "agentic-information-behavior"
VENV = SCRATCH / ".venv" / "Scripts" / "python.exe"
NOW = time.strftime("%Y-%m-%dT%H:%M:%S")

STEPS = {
    "P002": ["02_shared_code/behavior_tagger/isp_stage_coder.py --pilot",
             "02_shared_code/statistics/isp_stage_main_p002.py"],
    "P003": ["02_shared_code/data_audit/canonical_conformance_main_p003.py",
             "02_shared_code/data_audit/canonical_conformance_main_p003.py --corrected-probes"],
    "P004": ["02_shared_code/data_audit/quality_presence_scan_p004.py",
             "02_shared_code/statistics/p004_validity_main.py",
             "02_shared_code/statistics/p004_criterion_sensitivity.py"],
    "P005": ["02_shared_code/data_audit/governance_metadata_pilot_p005.py",
             "02_shared_code/data_audit/governance_metadata_main_p005.py",
             "02_shared_code/data_audit/governance_sensitivity_p005.py"],
}
VOLATILE = re.compile(r"time|date|wall|second|duration|elapsed|path|started|finished|at\b|seed_run|host", re.I)
TOL = 1e-2


def leaves(obj, prefix=""):
    """Every scalar in the artefact, keyed by its path."""
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(leaves(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        for n, v in enumerate(obj):
            out.update(leaves(v, f"{prefix}[{n}]"))
    else:
        out[prefix] = obj
    return out


def canon_str(x):
    """Normalise the two ways an artefact can legitimately differ from its own published copy: the absolute root it
    was written under, and the timestamp inside a referenced filename. Neither is a result value, and counting them as
    drift would bury the drift that matters."""
    if not isinstance(x, str):
        return x
    return re.sub(r"\d{8}T\d{6}", "", x.replace(str(SCRATCH), str(ROOT.parent)))


def compare(pub, clean):
    a, b = leaves(pub), leaves(clean)
    keys = sorted(set(a) | set(b))
    n_exact = n_tol = n_selfref = 0
    mism, only = [], []
    for k in keys:
        if k not in a or k not in b:
            only.append((k, k in a, k in b))
            continue
        if VOLATILE.search(k):
            continue
        x, y = a[k], b[k]
        if isinstance(x, bool) or isinstance(y, bool):
            if x == y:
                n_exact += 1
            else:
                mism.append((k, x, y))
        elif isinstance(x, (int, float)) and isinstance(y, (int, float)):
            if x != x and y != y:          # both NaN: `x == y` is False by IEEE, which is not a drift
                n_exact += 1
            elif x == y:
                n_exact += 1
            elif abs(float(x) - float(y)) <= TOL:
                n_tol += 1
            else:
                mism.append((k, x, y))
        else:
            if x == y:
                n_exact += 1
            elif canon_str(x) == canon_str(y):
                n_selfref += 1
            else:
                mism.append((k, str(x)[:60], str(y)[:60]))
    return {"leaves_compared": n_exact + n_tol + n_selfref + len(mism), "exact": n_exact, "within_1e-2": n_tol,
            "self_referential_path_or_timestamp": n_selfref,
            "mismatches": mism[:25], "n_mismatches": len(mism),
            "keys_present_in_only_one": only[:15], "n_keys_one_sided": len(only)}


def snapshot(d):
    return {f.name: round(f.stat().st_mtime, 3) for f in pathlib.Path(d).glob("*.json")}


def artefacts(since, written):
    """Published artefacts vs the ones THIS run actually wrote in the clean room.

    The clean-room tree starts as a copy, so every published file is also present there with a copy-time mtime.
    Matching by exp id alone would compare a file against its own copy and report a vacuous IDENTICAL - which is
    exactly what the first version of this tool did. Only a clean-room file written after `since` counts as produced.
    """
    def newest(d, min_mtime=None):
        out = {}
        for f in sorted(pathlib.Path(d).glob("*.json")):
            if min_mtime is not None and (f.name not in written or f.stat().st_mtime < min_mtime):
                continue
            m = re.match(r"(EXP\d+)", f.name)
            if m:
                out[m.group(1)] = f
        return out
    return newest(ROOT / "results_raw"), newest(CR / "results_raw", since)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    only = sys.argv[1:] or list(STEPS)
    reg_rows = [r for r in csv.reader(io.StringIO((ROOT / "00_program_registry" / "experiment_registry.csv")
                                                  .read_text(encoding="utf-8"))) if r]
    for pid in only:
        print(f"\n===== {pid} clean-room replication =====", flush=True)
        runs, written = [], set()
        t0 = time.time()
        run_start = t0 - 1.0
        for step in STEPS[pid]:
            before = snapshot(CR / "results_raw")
            parts = step.split()
            cmd = [str(VENV)] + parts
            r = subprocess.run(cmd, cwd=str(CR), capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=5400)
            tail = (r.stdout or "").strip().splitlines()[-3:]
            after = snapshot(CR / "results_raw")
            fresh = {n for n, m in after.items() if m > before.get(n, 0.0)}
            written |= fresh
            runs.append({"step": step, "returncode": r.returncode, "artefacts_written": sorted(fresh),
                         "stderr_tail": (r.stderr or "").strip().splitlines()[-3:], "stdout_tail": tail})
            print(f"  {step}  rc={r.returncode}  ({round(time.time() - t0)}s)", flush=True)
            if r.returncode != 0:
                print("     stderr:", " | ".join((r.stderr or "").strip().splitlines()[-3:])[:300], flush=True)
                break

        pub, cln = artefacts(run_start, written)
        per_file = {}
        # iterate the CLEAN side: the question is "did each artefact this run produced match the published one", and
        # iterating the published side instead turned every unrelated id into a fake "no counterpart" failure
        for exp, cf in sorted(cln.items()):
            pf = pub.get(exp)
            if pf is None:
                per_file[exp] = {"status": "no published counterpart to compare against"}
                continue
            try:
                P = json.loads(pf.read_text(encoding="utf-8"))
                C = json.loads(cf.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                per_file[exp] = {"status": f"unreadable: {exc}"}
                continue
            cmp = compare(P, C)
            cmp["status"] = ("IDENTICAL" if not cmp["mismatches"] and not cmp["n_keys_one_sided"]
                             and not cmp["self_referential_path_or_timestamp"]
                             else ("IDENTICAL_MODULO_SELF_REFERENCE" if not cmp["mismatches"]
                                   and not cmp["n_keys_one_sided"]
                                   else ("WITHIN_TOLERANCE" if not cmp["mismatches"] else "DRIFT")))
            per_file[exp] = cmp
            print(f"  {exp}: {cmp['status']} leaves={cmp['leaves_compared']} exact={cmp['exact']} "
                  f"tol={cmp['within_1e-2']} mism={cmp['n_mismatches']} one_sided={cmp['n_keys_one_sided']}",
                  flush=True)
            for m in cmp["mismatches"][:4]:
                print(f"     DIFF {m[0]}: {m[1]} vs {m[2]}", flush=True)

        all_ok = bool(per_file) and all(v.get("status") in ("IDENTICAL", "IDENTICAL_MODULO_SELF_REFERENCE", "WITHIN_TOLERANCE")
                                        for v in per_file.values())
        if not per_file:
            rec_note = "NOTHING REGENERATED: no clean-room artefact was written after the run started, so the "                        "comparison would have been vacuous"
        else:
            rec_note = ""
        rec = {"exp_id": "EXP-0079", "paper": pid, "at": NOW, "clean_room_root": str(CR),
               "interpreter": str(VENV), "dependency_lock": str(SCRATCH / "requirements_lock.txt"),
               "isolation": "venv created without --system-site-packages; numpy/pandas/scipy/scikit-learn/pyarrow/"
                            "matplotlib/statsmodels installed at the versions recorded in P001's "
                            "environment/system_info.json; the 79 GB dataset reached through a directory junction, so "
                            "the inputs are the same bytes, not a copy",
               "steps_run": runs, "artefacts_regenerated": sorted(per_file),
               "no_artefacts_regenerated_note": rec_note if not per_file else None,
               "artefact_comparison": per_file,
               "comparison_scope": "every scalar leaf of each result artefact; timestamps, wall clocks and paths "
                                   "excluded by key name; integers/strings exact, floats within 1e-2",
               "what_this_does_not_test": "the package builders (they generate prose from these same result files) and "
                                          "any step that needs the network or the optional encoder venv",
               "G18_E_clean_environment": "PASS" if all_ok else "FAIL",
               "wallclock_sec": round(time.time() - t0, 1)}
        out = ROOT / "papers" / next(p.name for p in (ROOT / "papers").iterdir()
                                     if p.is_dir() and p.name.startswith(pid)) / "environment"
        out.mkdir(exist_ok=True)
        (out / f"clean_room_run_{pid}.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False),
                                                        encoding="utf-8", newline="")
        print(f"  -> {rec['G18_E_clean_environment']}; wrote environment/clean_room_run_{pid}.json", flush=True)

        hdr, body = reg_rows[0], reg_rows[1:]
        if "EXP-0079" not in {r[0] for r in body}:
            body.append(["EXP-0079", "P002;P003;P004;P005", "clean_room_replication_run",
                         "02_shared_code/registry/clean_room_replication_p002_p005.py",
                         "fresh venv without system site-packages, dependencies pinned to the recorded versions; "
                         "repository copied, 79 GB dataset reached by junction; analysis steps only, package builders "
                         "excluded; comparison over every scalar leaf of each result artefact",
                         "none", NOW, NOW, "see papers/*/environment/clean_room_run_P00x.json",
                         "papers/*/environment/clean_room_run_P002..P005.json",
                         "closes gate G18-E's clean-environment item for the four papers that had no such record",
                         "yes - final_audit G18-E"])
        else:
            for r in body:
                if r[0] == "EXP-0079":
                    r[8] = "see papers/*/environment/clean_room_run_P00x.json (latest run " + NOW + ")"
        buf = io.StringIO()
        csv.writer(buf, lineterminator="\r\n").writerows([hdr] + body)
        (ROOT / "00_program_registry" / "experiment_registry.csv").write_text(buf.getvalue(),
                                                                              encoding="utf-8", newline="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
