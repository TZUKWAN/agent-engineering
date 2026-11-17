"""EXP-0182/0183..0188 two-pass determinism check: build each wave-7 layer twice into scratch and compare the bytes.

gzip stores its own mtime, so the .gz files can never be byte-identical across runs; what has to be identical is the
decompressed content. Every JSON carries a wallclock and a timestamp, so those keys are dropped before the comparison
and everything else - each count in `census_cross_check`, each coefficient, each bootstrap interval - has to match.

    python _w7_layer_two_pass.py designs|frame
"""
import gzip
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
PY = sys.executable
VOLATILE = {"started_at", "wallclock_sec", "invocation", "finished_at", "run_cost", "quick"}
STAGE = sys.argv[1] if len(sys.argv) > 1 else "frame"
SCRIPT = {"frame": "exp_wave7_features.py", "designs": "exp_wave7_designs.py"}[STAGE]
PREFIX = {"frame": "EXP0182", "designs": "EXP018"}[STAGE]


def run(dest: pathlib.Path) -> None:
    env = dict(os_environ(dest))
    subprocess.run([PY, "-u", f"02_shared_code/package_factory/{SCRIPT}"], check=True, cwd=str(ROOT), env=env,
                   capture_output=True)


def os_environ(dest: pathlib.Path) -> dict:
    import os
    (dest / "raw").mkdir(parents=True, exist_ok=True)
    (dest / "proc").mkdir(parents=True, exist_ok=True)
    # every wave-7 layer cross-checks itself against an earlier artefact, so the scratch copy is given those
    for pat in ("EXP0181_wave7_premise_census_*.json",):
        for f in sorted((ROOT / "results_raw").glob(pat)):
            (dest / "raw" / f.name).write_bytes(f.read_bytes())
    return dict(os.environ, AIB_ARTEFACT_DIR=str(dest / "raw"), AIB_PROCESSED_DIR=str(dest / "proc"))


def digests(dest: pathlib.Path) -> dict:
    out = {}
    for f in sorted((dest / "proc").glob("*")):
        raw = gzip.open(f, "rb").read() if f.suffix == ".gz" else f.read_bytes()
        out[f.name.split("_2026")[0]] = hashlib.sha256(raw).hexdigest()[:16]
    for f in sorted((dest / "raw").glob(f"{PREFIX}*.json")):
        a = json.loads(f.read_text(encoding="utf-8"))
        key = f.name.split("_2026")[0]
        out[key] = hashlib.sha256(json.dumps({k: v for k, v in a.items() if k not in VOLATILE},
                                             sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]
    return out


a, b = ROOT / "_w7_pass_a", ROOT / "_w7_pass_b"
for d in (a, b):
    shutil.rmtree(d, ignore_errors=True)
run(a)
run(b)
da, db = digests(a), digests(b)
diff = sorted([k for k in set(da) | set(db) if da.get(k) != db.get(k)])
print(f"{STAGE}: {len(da)} artefacts compared, second pass identical: {not diff}")
for k in sorted(da):
    flag = "" if da[k] == db.get(k) else "   <-- DIFFERS"
    print(f"   {k}: {da[k]} vs {db.get(k)}{flag}")
print("VERDICT:", "DETERMINISTIC" if not diff else f"{len(diff)} artefact(s) differ between passes")
sys.exit(1 if diff else 0)
