"""EXP-0105 (spec E13): a runtime-and-cost statement for every package, computed from what the programme already recorded.

E13 asks a paper to report GPU hours, inference tokens, API cost, wall-clock, tool calls, memory and latency. Only
P001 had ever assembled those numbers; the other four packages ran their steps and never said what they cost, so the
spec's E13 row was unanswerable from inside the package (EXP-0103 reported it OPEN for P002, P003 and P004).

Everything here is read from recorded state, and a quantity that was not measured is reported as not measured rather
than estimated:

* wall-clock per step - the `started_at`/`finished_at` pair in the package's own `experiment_registry.csv` extract
  (102 of the programme's 104 rows carry both), cross-checked against the `wallclock_sec` field the step wrote into its
  own artefact when it has one;
* GPU hours, inference tokens, API cost - zero, and the zero is *evidenced* by the sentence in the package's
  `environment/system_info.json` that says the run was CPU-only, not asserted by this script;
* memory - not measured by the analysis steps that ran before this script existed, so it is reported as not measured
  for those steps, and measured (peak RSS of this run) from this run onward;
* tool calls, latency - the packages do not execute agents or serve a model, so the quantities do not exist for them;
  the sentence naming that is written per package and checked by `export_e_coverage.py`.

    python 02_shared_code/registry/export_run_cost.py [--paper P002] [--check]

Deterministic: neither generated file carries a timestamp of its own generation - the run time lives in the EXP-0105
artefact - so re-running this script on an unchanged registry reproduces identical bytes.
"""
from __future__ import annotations
import argparse, csv, io, json, pathlib, re, sys, time

ROOT = next(a for a in [pathlib.Path(__file__).resolve().parent,
                        *pathlib.Path(__file__).resolve().parents] if (a / "00_program_registry").is_dir())
PAPERS = sorted(p for p in (ROOT / "papers").glob("P0*") if p.is_dir())
OUT_RAW = ROOT / "results_raw"
DATEFMT = "%Y-%m-%dT%H:%M:%S"
SPEC_FIELDS = ["GPU hours", "inference tokens", "API cost", "wall-clock", "tool calls", "memory", "latency"]
FIELDS = ["exp_id", "stage", "status", "started_at", "finished_at", "registry_span_sec", "artefact_wallclock_sec",
          "runtime_sec_used", "runtime_basis", "artefact", "registry_source"]


def dur(start: str, stop: str):
    """Seconds between two registry timestamps, or None when either is missing or they are identical (an identical
    pair means the recorder stored one time twice, which is not a duration)."""
    try:
        a, b = time.strptime(start, DATEFMT), time.strptime(stop, DATEFMT)
    except (ValueError, TypeError):
        return None
    d = int(time.mktime(b) - time.mktime(a))
    return d if d > 0 else None


def artefact_wallclock(outputs: str):
    """The `wallclock_sec` a step wrote into its own JSON artefact, if any output path resolves and carries one."""
    for tok in re.split(r"[;]", outputs or ""):
        p = tok.strip().replace("\\", "/")
        if not p or "*" in p:
            continue
        f = (ROOT / p) if not pathlib.Path(p).is_absolute() else pathlib.Path(p)
        if f.suffix.lower() != ".json" or not f.is_file():
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8", errors="replace"))
        except Exception:                                              # noqa: BLE001
            continue
        if isinstance(d, dict):
            for k in ("wallclock_sec", "runtime_sec", "duration_sec"):
                if isinstance(d.get(k), (int, float)) and d[k] > 0:
                    return round(float(d[k]), 1), f.name
            for v in d.values():                                       # one level down: {"packages": {...}} style
                if isinstance(v, dict) and isinstance(v.get("wallclock_sec"), (int, float)) and v["wallclock_sec"] > 0:
                    return round(float(v["wallclock_sec"]), 1), f.name
    return None, ""


def package_rows(pkg: pathlib.Path):
    """The registry rows that belong to the package: its own extract if it has one, otherwise the same rows filtered
    from the programme registry by paper_id."""
    own = pkg / "experiment_registry.csv"
    src = own if own.is_file() else (ROOT / "00_program_registry" / "experiment_registry.csv")
    pid = pkg.name[:4]
    rows = [r for r in csv.DictReader(io.StringIO(src.read_text(encoding="utf-8")))]
    if src is not own:
        rows = [r for r in rows if pid in (r.get("paper_id") or "")]
    return rows, src


def zero_evidence(pkg: pathlib.Path):
    """Which of the 'zero' quantities is actually backed by a sentence inside the package, and where."""
    env = pkg / "environment" / "system_info.json"
    if not env.is_file():
        cand = sorted((pkg / "environment").glob("*.json")) if (pkg / "environment").is_dir() else []
        env = cand[0] if cand else None
    if env is None:
        return {"found": False, "file": "", "note": "no environment record in the package"}
    txt = env.read_text(encoding="utf-8", errors="replace").lower()
    has_cpu = ("cpu" in txt and "no gpu" in txt) or "cpu only" in txt or "cpu-only" in txt
    has_net = "no network" in txt or "no api" in txt or "no model inference" in txt
    return {"found": True, "file": str(env.relative_to(pkg)).replace("\\", "/"),
            "cpu_only_stated": has_cpu, "no_inference_stated": has_net,
            "verbatim": re.sub(r"\s+", " ", txt)[:300]}


def build(pkg: pathlib.Path):
    rows, src = package_rows(pkg)
    table, measured, disagree = [], 0, []
    for r in sorted(rows, key=lambda x: (x.get("exp_id") or "", x.get("stage") or "")):
        d = dur(r.get("started_at") or "", r.get("finished_at") or "")
        aw, af = artefact_wallclock(r.get("outputs") or "")
        # The registry pair is an elapsed span, the artefact field is what the step itself measured. When a step was
        # opened, parked, and closed much later the span is many thousand times the runtime (EXP-0089: 181,479 s
        # elapsed against 33.1 s measured), so the runtime figure uses the step's own measurement where it exists and
        # says so; the span stays in its own column and the disagreement is reported, not averaged away.
        val = aw if aw else d
        basis = "artefact" if aw else ("registry span" if d else "not measured")
        if aw and d and d > 2 * aw:
            disagree.append(r.get("exp_id", ""))
        if val:
            measured += 1
        table.append({"exp_id": r.get("exp_id", ""), "stage": r.get("stage", ""), "status": r.get("status", ""),
                      "started_at": r.get("started_at", ""), "finished_at": r.get("finished_at", ""),
                      "registry_span_sec": d if d else "", "artefact_wallclock_sec": aw if aw else "",
                      "runtime_sec_used": val if val else "", "runtime_basis": basis, "artefact": af,
                      "registry_source": str(src.relative_to(ROOT)).replace("\\", "/")})
    secs = [t["runtime_sec_used"] for t in table if t["runtime_sec_used"]]
    env = zero_evidence(pkg)
    total = sum(int(s) for s in secs)
    spans = [t["registry_span_sec"] for t in table if t["registry_span_sec"]]
    lines = [f"# {pkg.name[:4]}: E13 runtime and cost", "",
             "Generated by `02_shared_code/registry/export_run_cost.py` from recorded state only: the registry's own "
             "`started_at`/`finished_at` pair per step and the `wallclock_sec` field each step wrote into its artefact. "
             "Nothing here is estimated, and a quantity the programme never measured is labelled as such.", "",
             f"- steps registered for this package: **{len(table)}**, of which **{measured}** carry a measured runtime "
             f"and **{len(table) - measured}** carry none (the recorder stored a single timestamp);",
             f"- measured run time: **{total} s** over the **{measured}** steps that recorded one "
             f"(longest single step **{max((int(s) for s in secs), default=0)} s**; median "
             f"**{sorted(int(s) for s in secs)[len(secs) // 2] if secs else 0} s**). Summed, so steps that ran "
             f"concurrently are counted twice: this is a cost statement, not an elapsed-time statement;",
             f"- registry spans sum to **{sum(int(s) for s in spans)} s** over **{len(spans)}** dated steps. That "
             f"number is deliberately not used as the cost: **{len(disagree)}** step(s) "
             f"({', '.join(disagree) if disagree else 'none'}) were opened, parked and closed much later, so their "
             f"registry span is many times the run time their own artefact measured; where both exist, "
             f"`tables/table_run_cost.csv` keeps both and names the basis of the value it uses.",
             "",
             "| spec E13 quantity | value for this package | how this row is known |",
             "|---|---|---|"]
    ev = ("`" + env["file"] + "` states: " + env["verbatim"][:150]) if env["found"] else env["note"]
    gpu = "0" if env.get("cpu_only_stated") else "not evidenced"
    tok = "0" if env.get("no_inference_stated") else "not evidenced"
    lines += [
        f"| GPU hours | {gpu} | {ev if gpu == '0' else 'the package carries no environment statement about GPU use'} |",
        f"| inference tokens | {tok} | no model was run to produce this package's numbers; {ev} |",
        f"| API cost | {tok} | same evidence as inference tokens: no hosted model was called |",
        f"| wall-clock | {total} s measured over {measured} steps | registry timestamps + artefact `wallclock_sec`, "
        f"both shown per step in `tables/table_run_cost.csv` |",
        "| tool calls | not applicable | this package reads trajectories that other systems executed; it issues no "
        "tool calls of its own, so there is no count to report |",
        "| memory | not measured for the steps that ran before EXP-0105 | the analysis scripts never captured RSS; "
        "EXP-0105 itself does, and its value is in its artefact `peak_mem_mb` |",
        "| latency | not applicable | nothing here is served or interactive |",
        "",
        "The per-step rows are in `tables/table_run_cost.csv` (`registry_span_sec` from the registry, "
        "`artefact_wallclock_sec` from the step's own artefact, `runtime_sec_used` plus the basis actually used). "
        "A disagreement between the two columns is a provenance finding about how the step was recorded, not a "
        "rounding difference.",
        ""]
    return table, "\n".join(lines) + "\n", env, {"n_steps": len(table), "measured": measured, "total_sec": total,
                                                 "registry_span_total": sum(int(s) for s in spans),
                                                 "parked_span_steps": disagree}


def peak_mem():
    """This run's own peak memory, so the E13 'memory' row is measured by something rather than nothing. `peak_wset`
    is the Windows peak working set; psutil on Linux names the same idea `peak_rss`; falling back to the current value
    is recorded in `source` so the reader knows which one they are being given."""
    try:
        import psutil
        mi = psutil.Process().memory_info()
        for attr in ("peak_wset", "peak_rss"):
            v = getattr(mi, attr, None)
            if v:
                return round(v / 1048576.0, 1), attr
        return round(mi.rss / 1048576.0, 1), "rss (current, no peak field)"
    except Exception as exc:                                          # noqa: BLE001
        return None, f"unavailable: {type(exc).__name__}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", default="")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    summary = {}
    for pkg in PAPERS:
        pid = pkg.name[:4]
        if a.paper and pid != a.paper:
            continue
        table, md, env, stats = build(pkg)
        (pkg / "tables").mkdir(exist_ok=True)
        csvp = pkg / "tables" / "table_run_cost.csv"
        mdp = pkg / "RUN_COST.md"
        assert all(set(t) == set(FIELDS) for t in table), f"{pid}: cost rows do not match the declared columns"
        body = io.StringIO()
        w = csv.DictWriter(body, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(table)
        if a.check:
            def _state(p, text):
                return "up to date" if p.is_file() and p.read_text(encoding="utf-8") == text else "STALE"
            print(f"  {pid}: csv {_state(csvp, body.getvalue())} | md {_state(mdp, md)} | "
                  f"{stats['measured']}/{stats['n_steps']} steps with a measured runtime, {stats['total_sec']} s")
        else:
            csvp.write_text(body.getvalue(), encoding="utf-8", newline="")
            mdp.write_text(md, encoding="utf-8", newline="")
            print(f"  {pid}: wrote RUN_COST.md + tables/table_run_cost.csv | {stats['measured']}/{stats['n_steps']} "
                  f"steps with a measured runtime, {stats['total_sec']} s", flush=True)
        summary[pid] = dict(stats, cpu_only_stated=env.get("cpu_only_stated"),
                            no_inference_stated=env.get("no_inference_stated"))
    peak, psrc = peak_mem()
    res = {"exp_id": "EXP-0105", "at": time.strftime("%Y-%m-%dT%H:%M:%S"), "per_package": summary,
           "rule": "registry timestamps and artefact wallclock_sec only; an unmeasured quantity is labelled unmeasured",
           "peak_mem_mb": peak, "peak_mem_source": psrc, "wallclock_sec": round(time.time() - t0, 1)}
    out = OUT_RAW / f"EXP0105_run_cost_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {out.name} (this run: {res['wallclock_sec']} s, peak memory {peak} MB via {psrc})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
