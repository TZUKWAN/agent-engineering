"""Download 8 agent datasets from Hugging Face into D:/MATLABINTOKEN/datasets.

Resumable: snapshot_download with local_dir keeps metadata so reruns pick up
where they left off. Each dataset retries up to 3 times before moving on.
"""
import os
import time
import traceback

os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "60")

from huggingface_hub import snapshot_download

DATASETS = [
    "Agent-Ark/Toucan-1.5M",
    "open-thoughts/AgentTrove",
    "VIS-MPU-Agent/MMAT-1M",
    "Solaris99/AgentBank",
    "lambda/hermes-agent-reasoning-traces",
    "AlienKevin/SWE-ZERO-12M-trajectories",
    "xingyaoww/code-act",
    "zai-org/AgentInstruct",
]

BASE = r"D:\MATLABINTOKEN\datasets"


def log(msg: str) -> None:
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def main() -> None:
    results = {}
    for ds in DATASETS:
        out_dir = os.path.join(BASE, *ds.split("/"))
        log(f"START {ds} -> {out_dir}")
        ok = False
        for attempt in range(1, 11):
            try:
                snapshot_download(
                    repo_id=ds,
                    repo_type="dataset",
                    local_dir=out_dir,
                    max_workers=8,
                )
                ok = True
                break
            except KeyboardInterrupt:
                raise
            except Exception as e:
                log(f"RETRY {attempt}/3 {ds}: {type(e).__name__}: {e}")
                traceback.print_exc()
                time.sleep(30)
        results[ds] = "OK" if ok else "FAILED"
        log(f"{'DONE' if ok else 'FAILED'} {ds}")

    log("==== SUMMARY ====")
    for ds, status in results.items():
        log(f"{status:7s} {ds}")


if __name__ == "__main__":
    main()
