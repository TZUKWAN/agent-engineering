"""Scratch driver: re-run every artefact that scores with the BM25 ranker, in dependency order.

`_bm25_scores` and the frozen `BM25.rank` accumulated query terms in `set` iteration order, so PYTHONHASHSEED moved
the last bits of a score and flipped hit@1 on the rows where the gold ties exactly with a rival (204 of the 7,476
sampled dev rows). With the term order fixed, every number that comes out of the ranker has to be regenerated from
it, or the shipped artefacts would describe two different instruments.

Order matters: the matrix feeds the designs, and the designs' frames feed the battery.

    python _rerun_after_ranker_fix.py [--only wave1|wave2|wave3|wave4]
"""
import argparse
import os
import subprocess
import sys
import time

FACTORY = "02_shared_code/package_factory"
CHAIN = {
    "wave1": ["exp_wave1_features.py", "exp_wave1_query_level.py", "exp_wave1_reformulation.py",
              "exp_wave1_candidate_level.py", "exp_wave1_battery.py"],
    "wave2": ["exp_wave2_features.py", "exp_wave2_designs.py", "exp_wave2_battery.py"],
    "wave3": ["exp_wave3_features.py", "exp_wave3_designs.py", "exp_wave3_battery.py"],
    # Wave 4 scores no BM25 - its substrate is a trajectory corpus - but the same dependency order holds, so the
    # rebuild rounds below re-run it through this driver rather than through a hand-typed command list.
    "wave4": ["exp_wave4_features.py", "exp_wave4_designs.py", "exp_wave4_battery.py"],
}
PY = sys.executable


def run(script: str) -> int:
    t0 = time.time()
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}   # PYTHONHASHSEED is deliberately NOT pinned: the point of
    # the fix is that the numbers no longer depend on it, and pinning it here would hide a regression.
    log = f"logs/{script.replace('.py', '')}_after_ranker_fix.log"
    os.makedirs("logs", exist_ok=True)
    with open(log, "w", encoding="utf-8") as fh:
        p = subprocess.run([PY, "-u", f"{FACTORY}/{script}"], stdout=fh, stderr=subprocess.STDOUT, env=env)
    print(f"{script}: exit {p.returncode} in {round(time.time() - t0, 1)}s -> {log}", flush=True)
    if p.returncode:
        tail = "".join(open(log, encoding="utf-8", errors="replace").readlines()[-12:])
        print(f"--- last lines of {log} ---\n{tail}", flush=True)
    return p.returncode


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=sorted(CHAIN), default="")
    a = ap.parse_args()
    waves = [a.only] if a.only else list(CHAIN)
    failed = []
    for w in waves:
        for s in CHAIN[w]:
            if run(s):
                failed.append(f"{w}/{s}")
                break                     # a design or battery built on a failed matrix is not evidence
        else:
            print(f"{w}: chain complete", flush=True)
    if failed:
        print(f"ABORTED AT: {failed} - the remaining waves were not run", flush=True)
        return 1
    print("ALL WAVES RE-RUN FROM THE FIXED RANKER", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
