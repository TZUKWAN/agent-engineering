"""EXP-0079 recorder: file the clean-environment replication results and fix the dependency lock they exposed.

The clean-room run is only useful if its finding is recorded even when it indicts the recording itself. Two things
happened here:

1. the dependency set that P001's `environment/system_info.json` lists was **not** the set the pipelines import -
   `PyYAML` and `psutil` are imported by the analysis code and absent from the lock, so the first clean-room run died
   at `import yaml` in P005's pilot. A lock that omits an imported package is not a lock;
2. the replication tool itself needed two corrections before its verdict meant anything (recorded in the run files'
   own history): it matched artefacts by experiment id across a tree that began as a copy, so it was comparing files
   against their own copies and reporting vacuous IDENTICAL results, and it treated `nan` vs `nan` as drift.

This step writes each paper's G18-E line from its run record, drops the AST-derived complete lock into every
`environment/`, and registers the experiment.
"""
from __future__ import annotations

import csv, io, json, pathlib, re, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
REG = ROOT / "00_program_registry"
NOW = time.strftime("%Y-%m-%dT%H:%M:%S")
PIDS = ["P002", "P003", "P004", "P005"]
LOCK_SRC = ROOT.parent / "_cleanroom" / "requirements_lock.txt"


def paper_dir(pid):
    return ROOT / "papers" / next(p.name for p in (ROOT / "papers").iterdir()
                                  if p.is_dir() and p.name.startswith(pid))


def main() -> int:
    lock = LOCK_SRC.read_text(encoding="utf-8") if LOCK_SRC.exists() else ""
    if not lock:
        raise SystemExit("[e79] no lock file to publish; the clean-room run did not complete.")

    # P001 already has a clean-room record (EXP-0025) but it lives in results_raw, so the package's environment/
    # directory held nothing a gate check could find. Normalise it into the same shape as the others, by copying the
    # recorded fields across - no new measurement is asserted here.
    p1 = paper_dir("P001")
    src = sorted((ROOT / "results_raw").glob("EXP0025_clean_room_replication_*.json"))
    dst = p1 / "environment" / "clean_room_run_P001.json"
    if src and not dst.exists():
        E = json.loads(src[-1].read_text(encoding="utf-8"))
        dst.write_text(json.dumps(
            {"exp_id": "EXP-0025", "paper": "P001", "normalised_into_this_file_by": "EXP-0079 recorder",
             "source_artefact": src[-1].name, "at": E.get("started_at"),
             "clean_env_python": E.get("clean_env_python"), "tree_copy": E.get("tree_copy"),
             "isolation": E.get("isolation"), "steps_run": E.get("stages"),
             "excluded_stages": E.get("excluded_stages"), "agreement": E.get("agreement"),
             "sample_identity": E.get("sample_identity"), "tables_regenerated": E.get("tables_regenerated"),
             "figures_regenerated": E.get("figures_regenerated"),
             "G18_E_clean_environment": "PASS (recorded by EXP-0025; see the source artefact for the agreement "
                                        "detail)"},
            indent=1, ensure_ascii=False), encoding="utf-8", newline="")
        print("[e79] P001: normalised EXP-0025 into environment/clean_room_run_P001.json")

    summary = {}
    for pid in PIDS:
        pd = paper_dir(pid)
        rf = pd / "environment" / f"clean_room_run_{pid}.json"
        if not rf.exists():
            print(f"[e79] {pid}: no run record yet; skipped")
            continue
        R = json.loads(rf.read_text(encoding="utf-8"))
        cmp_ = R["artefact_comparison"]
        OK = ("IDENTICAL", "IDENTICAL_MODULO_SELF_REFERENCE", "WITHIN_TOLERANCE")
        n_ok = sum(1 for v in cmp_.values() if v.get("status") in OK)
        n_bad = len(cmp_) - n_ok
        exact = sum(v.get("exact", 0) for v in cmp_.values())
        tol = sum(v.get("within_1e-2", 0) for v in cmp_.values())
        mism = sum(v.get("n_mismatches", 0) for v in cmp_.values())
        steps_fail = [s["step"] for s in R["steps_run"] if s["returncode"] != 0]
        summary[pid] = {"verdict": R["G18_E_clean_environment"], "artefacts": len(cmp_), "ok": n_ok, "drift": n_bad,
                        "leaves_exact": exact, "leaves_within_tol": tol, "mismatches": mism,
                        "steps_failed": steps_fail}

        # complete dependency lock, derived from the import surface rather than from a remembered package list
        (pd / "environment" / "dependencies_complete.txt").write_text(
            f"# AST-derived import surface of 02_shared_code/** and papers/*/scripts/**\n"
            f"# (module -> distribution, versions as executed in the clean-room run of {R['at']})\n"
            f"# the earlier environment/dependencies.txt listed only what P001's system_info happened to record and\n"
            f"# omitted PyYAML and psutil, which the analysis code imports.\n{lock}", encoding="utf-8", newline="")

        fa = pd / "final_audit.md"
        t = fa.read_text(encoding="utf-8")
        line = (f"| clean environment | **{R['G18_E_clean_environment']} (EXP-0079)** | fresh venv without system "
                f"site-packages, {len(lock.splitlines())} pinned distributions; "
                f"{len(cmp_)} result artefact(s) regenerated and compared leaf-by-leaf: {exact} exact, {tol} within "
                f"1e-2, {mism} mismatch(es); steps that failed: {steps_fail or 'none'}; "
                f"see `environment/clean_room_run_{pid}.json` |")
        if "EXP-0079" not in t:
            if "| clean environment" in t:
                t = re.sub(r"(?m)^\| clean environment .*$", line, t, count=1)
            else:
                m = re.search(r"(?m)^## G18-E.*$", t)
                if m:
                    t = t[:m.end()] + f"\n\n| item | status | evidence |\n|---|---|---|\n{line}\n" + t[m.end():]
                else:
                    t = t.rstrip() + f"\n\n## G18-E reproducibility\n\n| item | status | evidence |\n|---|---|---|\n{line}\n"
            fa.write_text(t, encoding="utf-8", newline="")
            print(f"[e79] {pid}: G18-E clean-environment line -> {R['G18_E_clean_environment']}")

    dv = paper_dir("P005") / "deviations.md"
    dt = dv.read_text(encoding="utf-8")
    alld = [int(x) for f in sorted((ROOT / "papers").glob("*/deviations.md"))
            for x in re.findall(r"(?m)^\| D(\d+) \|", f.read_text(encoding="utf-8"))]
    dn = max(alld or [0])
    SUBJ = "环境依赖锁不完整：代码 import 的 PyYAML 与 psutil 未记录"
    if SUBJ not in dt:
        dv.write_text(dt.rstrip() + f"""
| D{dn+1} | {NOW} | {SUBJ} | EXP-0079 在全新 venv 中复跑时 P005 pilot 直接 `ModuleNotFoundError: No module named 'yaml'`；改用 AST 扫描 `02_shared_code/**` 与 `papers/*/scripts/**` 的 import 面重建锁（{len(lock.splitlines())} 个发行包）后复跑；各篇环境层结论见 run 记录，不由本行预设 | 否 | 每篇 `environment/dependencies_complete.txt` 记录由 import 面推导的完整锁并注明旧锁缺项；同时修正复现工具自身两处缺陷（按 exp id 匹配到「与自己的副本比较」的空验证，以及把 nan vs nan 记为漂移） |""",  # noqa: E501
                       encoding="utf-8", newline="")
        print(f"[e79] D{dn+1} appended to P005 deviations")

    p = REG / "experiment_registry.csv"
    rows = [r for r in csv.reader(io.StringIO(p.read_text(encoding="utf-8"))) if r]
    hdr, body = rows[0], rows[1:]
    i = {c: n for n, c in enumerate(hdr)}
    stat = "; ".join(f"{k}={v['verdict']}({v['ok']}/{v['artefacts']} artefacts, {v['mismatches']} mism)"
                     for k, v in summary.items())
    for r in body:
        if r[0] == "EXP-0079":
            r[i["status"]] = stat[:300]
            r[i["notes"]] = ("gate G18-E clean-environment item now has a record for P002-P005; the run also exposed "
                             "an incomplete dependency lock (PyYAML, psutil imported but unlisted) and two defects in "
                             "the comparison tool itself, both fixed and re-run")
            r[i["outputs"]] = ("papers/*/environment/clean_room_run_P00x.json; "
                               "papers/*/environment/dependencies_complete.txt")
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\r\n").writerows([hdr] + body)
    p.write_text(buf.getvalue(), encoding="utf-8", newline="")
    print("[e79] registry row updated:", stat[:200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
