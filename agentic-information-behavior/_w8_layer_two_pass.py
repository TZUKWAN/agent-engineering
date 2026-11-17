"""Two-pass determinism check for a wave-8 layer: build it twice into scratch and compare the bytes.

Same rule as wave 7's check: gzip stores its own mtime so the .gz files cannot be byte-identical, and every JSON
carries a wallclock, so those keys are dropped and everything else - each count, each coefficient, each bootstrap
interval - has to match across two independent processes. The scratch copy is seeded with the artefact the layer
cross-checks itself against, because a wave-8 layer that cannot find its census aborts rather than guessing.

    python _w8_layer_two_pass.py frame|designs
"""
import gzip
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
PY = sys.executable
STAGE = sys.argv[1] if len(sys.argv) > 1 else "frame"
SCRIPT = {"frame": "exp_wave8_features.py", "designs": "exp_wave8_designs.py",
          "battery": "exp_wave8_battery.py"}[STAGE]
PREFIX = {"frame": "EXP0191", "designs": "EXP019", "battery": "EXP0195"}[STAGE]
SEED_PAT = {"frame": ["EXP0190_wave8_premise_census_*.json"],
            "designs": ["EXP0190_wave8_premise_census_*.json"], "battery": []}[STAGE]
VOLATILE = {"started_at", "wallclock_sec", "invocation", "finished_at", "run_cost", "quick"}


def run(dest: pathlib.Path) -> None:
    (dest / "raw").mkdir(parents=True, exist_ok=True)
    (dest / "proc").mkdir(parents=True, exist_ok=True)
    for pat in SEED_PAT:
        src = sorted((ROOT / "results_raw").glob(pat))[-1]
        (dest / "raw" / src.name).write_bytes(src.read_bytes())
    env = dict(os.environ, AIB_ARTEFACT_DIR=str(dest / "raw"), AIB_PROCESSED_DIR=str(dest / "proc"))
    r = subprocess.run([PY, "-u", f"02_shared_code/package_factory/{SCRIPT}"], cwd=str(ROOT), env=env,
                       capture_output=True)
    if r.returncode:
        print(r.stdout.decode("utf-8", "replace")[-3000:])
        raise SystemExit(f"{SCRIPT} failed with rc={r.returncode}")


def digests(dest: pathlib.Path) -> dict:
    out = {}
    for f in sorted((dest / "proc").glob("*")):
        raw = gzip.open(f, "rb").read() if f.suffix == ".gz" else f.read_bytes()
        out[f.name.split("_2026")[0]] = hashlib.sha256(raw).hexdigest()[:16]
    for f in sorted((dest / "raw").glob(f"{PREFIX}*.json")):
        a = json.loads(f.read_text(encoding="utf-8"))
        out[f.name.split("_2026")[0]] = hashlib.sha256(json.dumps({k: v for k, v in a.items() if k not in VOLATILE},
                                                                  sort_keys=True, default=str).encode("utf-8")
                                                       ).hexdigest()[:16]
    return out


a, b = ROOT / "_w8_pass_a", ROOT / "_w8_pass_b"
for d in (a, b):
    shutil.rmtree(d, ignore_errors=True)
run(a)
run(b)
da, db = digests(a), digests(b)
diff = sorted([k for k in set(da) | set(db) if da.get(k) != db.get(k)])
print(f"{STAGE}: {len(da)} artefacts compared, second pass identical: {not diff}")
for k in sorted(da):
    print(f"   {k}: {da[k]} vs {db.get(k)}{'' if da[k] == db.get(k) else '   <-- DIFFERS'}")
print("VERDICT:", "DETERMINISTIC" if not diff else f"{len(diff)} artefact(s) differ between passes")
sys.exit(1 if diff else 0)
