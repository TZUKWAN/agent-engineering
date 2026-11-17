"""EXP-0036 (P003): is the published conformance matrix an artefact of row-head sampling?

EXP-0029/0030 read, per parquet shard, the FIRST `HEAD` rows of each row group and, for MMAT-1M's jsonl, the first
`ROWS` lines in file order. P003's own limitation 3 says exactly that. This re-runs the *frozen* judgement code
(`canonical_conformance_audit_p003.measure`, same SPEC, same concepts, same thresholds, plus the EXP-0030 nested
probes) over an otherwise identical sample in which every row position is drawn uniformly at random instead, then
diffs the two matrices cell by cell.

Nothing about the instrument changes: same seed for shard selection, same number of shards and rows, same parsers.
Only the within-file row selection changes, which is precisely the quantity limitation 3 says is untested.

Pre-registered decision rule, fixed here before any comparison:
  STABLE iff the set of concepts recoverable in all 8 corpora is identical AND no concept flips between
  {direct, absent} in either direction;  SAMPLING_SENSITIVE otherwise, in which case "2 of 12" must be re-derived.

    python 02_shared_code/data_audit/randomised_resample_p003.py
"""
from __future__ import annotations

import glob, json, random, sys, time, zlib
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "02_shared_code" / "data_audit"))
import canonical_conformance_audit_p003 as pilot
import canonical_conformance_main_p003 as mainmod

DATA = pilot.DATA
SEED = pilot.SEED


def stable_int(s: str) -> int:
    """hash() on str is salted per process, so a per-corpus seed must not use it (reproducibility)."""
    return zlib.crc32(s.encode("utf-8"))


def rsample_parquet(path: Path, rng: random.Random):
    """Same shards and same row count as pilot.sample_parquet; random positions inside each row group."""
    files = [f for f in sorted(glob.glob(str(path / "**/*.parquet"), recursive=True)) if ".cache" not in f]
    if not files:
        return [], "no parquet shards"
    picks = sorted(random.Random(SEED).sample(files, min(pilot.SHARDS, len(files))))
    rows, notes = [], []
    for f in picks:
        pf, got = pq.ParquetFile(f), 0
        cols = list(pf.schema_arrow.names)
        for rg in range(pf.metadata.num_row_groups):
            if got >= pilot.HEAD:
                break
            nrg = pf.metadata.row_group(rg).num_rows
            want = min(pilot.HEAD - got, nrg)
            take = sorted(rng.sample(range(nrg), want))          # the only change vs the frozen sampler
            part = pf.read_row_group(rg, columns=cols).take(take).to_pylist()
            rows.extend(part)
            got += len(part)
        notes.append(f"{Path(f).name}:{got}")
    return rows[:pilot.ROWS], f"{len(files)} shards, randomised within row-group; per-file " + ",".join(notes)


def rsample_jsonl(path: Path, n_rows: int, rng: random.Random):
    """Uniform byte-offset sampling. A head read cannot see records past the first pages of a multi-GB jsonl, which
    is the defect under test; the line at an offset is discarded as partial, so each kept record is complete."""
    files = sorted(glob.glob(str(path / "**/*.jsonl"), recursive=True), key=lambda f: ("val" not in f, f))
    if not files:
        return [], []
    sizes = [(f, Path(f).stat().st_size) for f in files]
    total = sum(s for _, s in sizes)
    rows, used, guard = [], set(), 0
    while len(rows) < n_rows and guard < 8 * n_rows:
        guard += 1
        x = rng.random() * total
        for f, s in sizes:
            if x <= s:
                break
            x -= s
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                fh.seek(max(0, int(x)))
                fh.readline()                                   # drop the partial line
                line = fh.readline()
                if line:
                    rows.append(json.loads(line))
                    used.add(Path(f).name)
        except Exception:                                       # noqa: BLE001 - offsets land mid-record
            continue
    return rows[:n_rows], sorted(used)


def specs_frozen():
    specs = dict(pilot.SPEC)
    specs["MMAT-1M"] = mainmod.MMAT_SPEC
    tc = {"path": specs["Toucan-1.5M"]["path"], "cols": {k: list(v) for k, v in specs["Toucan-1.5M"]["cols"].items()},
          "conflicts": dict(specs["Toucan-1.5M"].get("conflicts", {}))}
    tc["cols"]["C4_model_id"] = tc["cols"]["C4_model_id"] + [pilot.R("meta_nested_model")]
    tc["cols"]["C5_teacher_provider"] = tc["cols"]["C5_teacher_provider"] + [pilot.R("meta_nested_provider")]
    specs["Toucan-1.5M"] = tc                                   # EXP-0030 / D18 corrected probes
    return specs


def matrix_for():
    out = {}
    for name, spec in specs_frozen().items():
        rng = random.Random(SEED + stable_int(name))
        if name == "MMAT-1M":
            rows, _ = rsample_jsonl(DATA / spec["path"], pilot.ROWS, rng)
        else:
            rows, _ = rsample_parquet(DATA / spec["path"], rng)
        if not rows:
            out[name] = {"error": "no rows", "concepts": {}}
            continue
        cells, _conf = pilot.measure(name, spec, rows)
        out[name] = {"n_rows": len(rows),
                     "concepts": {c: {"state": cells[c]["state"],
                                      "best": round(max((e["coverage"] for e in cells[c]["evidence"]), default=0.0), 4)}
                                  for c in pilot.CONCEPTS}}
        print(f"  {name:34s} n={len(rows):5d} "
              f"direct={sum(1 for v in out[name]['concepts'].values() if v['state'] == 'direct'):2d}")
    return out


def states(m):
    return {corp: {c: v["state"] for c, v in d.get("concepts", {}).items()} for corp, d in m.items() if d.get("concepts")}


def alignable(smap):
    ok = [c for c in pilot.CONCEPTS if all(smap[k].get(c) in ("direct", "derived") for k in smap)]
    return ok


def published_states(pub):
    """EXP-0030 stores each corpus as {n_rows, container, cells:{concept:{state,...}}, ...}."""
    out = {}
    for corp, d in pub.get("corpora", {}).items():
        cells = d.get("cells") or d.get("coverage") or d.get("concepts") or {}
        out[corp] = {c: (v.get("state") if isinstance(v, dict) else v) for c, v in cells.items()}
    return {k: v for k, v in out.items() if v}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    pf = sorted((ROOT / "results_raw").glob("EXP0030_p003_conformance_main_*.json"))
    if not pf:
        print("[e36] no EXP-0030 file to compare against; stopping.")
        return 0
    published = json.loads(pf[-1].read_text(encoding="utf-8"))
    res = {"exp_id": "EXP-0036", "paper_id": "P003", "seed": SEED, "compared_against": pf[-1].name,
           "rule": "STABLE iff the all-corpus alignable concept set is identical and no concept flips direct<->absent",
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    print("[e36] randomised resample of the same eight corpora:")
    new = matrix_for()
    res["randomised_matrix"] = new
    n_st, p_st = states(new), published_states(published)
    # Guards against the vacuous-truth bug this script originally shipped with: `all()` over an empty mapping is
    # True, so a parsing failure used to read as "12 concepts alignable" and a zero-cell comparison as "stable".
    for label, smap in (("published EXP-0030", p_st), ("randomised", n_st)):
        if len(smap) != len(published.get("corpora", {})):
            sys.exit(f"[e36] ABORT: parsed {len(smap)} corpora from {label}, expected "
                     f"{len(published.get('corpora', {}))}. Refusing to decide on a partial matrix.")
        missing = [corp for corp, v in smap.items() if len(v) < len(pilot.CONCEPTS)]
        if missing:
            sys.exit(f"[e36] ABORT: {label} matrix incomplete, corpora missing concepts: {missing}")
    print(f"[e36] both matrices parsed fully: {len(p_st)}x{len(pilot.CONCEPTS)} published, "
          f"{len(n_st)}x{len(pilot.CONCEPTS)} randomised")
    flips = [[corp, con, p_st[corp][con], n_st[corp][con]]
             for corp in n_st if corp in p_st for con in n_st[corp]
             if con in p_st[corp] and n_st[corp][con] != p_st[corp][con]
             and {n_st[corp][con], p_st[corp][con]} <= {"direct", "absent"}]
    all_flips = [[corp, con, p_st[corp][con], n_st[corp][con]]
                 for corp in n_st if corp in p_st for con in n_st[corp]
                 if con in p_st[corp] and n_st[corp][con] != p_st[corp][con]]
    a_new, a_old = alignable(n_st), alignable(p_st)
    res["verdict"] = {"alignable_randomised": [len(a_new), a_new], "alignable_published": [len(a_old), a_old],
                      "hard_direct_absent_flips": flips, "all_state_changes": len(all_flips),
                      "decision": "STABLE" if (set(a_new) == set(a_old) and not flips) else "SAMPLING_SENSITIVE"}
    res["wallclock_sec"], res["finished_at"] = round(time.time() - t0, 1), time.strftime("%Y-%m-%dT%H:%M:%S")
    (ROOT / "results_raw").mkdir(exist_ok=True)
    out = ROOT / "results_raw" / f"EXP0036_randomised_resample_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    import pandas as pd
    pd.DataFrame(all_flips, columns=["corpus", "concept", "published_state", "randomised_state"]).to_csv(
        ROOT / "results_processed" / "EXP0036_state_changes.csv", index=False)
    print(json.dumps(res["verdict"], ensure_ascii=False)[:700])
    print("wrote", out, f"({res['wallclock_sec']}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
