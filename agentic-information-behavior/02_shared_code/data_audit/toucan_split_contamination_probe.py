"""EXP-0225: promote the ad-hoc split-contamination probe behind P001's deviation D5 into a script.

EXP-0008 decided a load-bearing thing - that the routing split should be keyed on `prompt_id` rather than `uuid`,
because the same `prompt_id` reaches dev and test under different uuids - and it did so from a console probe: the
registry row names no script, writes "(console evidence; no file written by the ad-hoc probe - flagged as a gap to
close by promoting it to a script)", and the gap stayed open for seven days and one full audit round. The round-2
pass found it in exactly the way a reader would: a registered run whose numbers cannot be opened.

What it measures, on the frozen dev rows only:

1. **uuid/prompt_id disagreement** - how many `prompt_id` values arrive under more than one `uuid`, which is the
   leakage the split key change removes;
2. **exact question overlap across the split boundary** - the share of dev rows whose normalised question also
   occurs on the other side of the split. Only the `split` label and the question string are touched here; no
   outcome column of any test row is read, which is the invariant the programme holds everywhere;
3. **cross-config `prompt_id` recurrence** - how many prompts appear in more than one teacher config, the
   non-independence D5 records as the limit on pooling.

    python 02_shared_code/data_audit/toucan_split_contamination_probe.py [--selftest]
"""
from __future__ import annotations

import argparse
import collections
import datetime
import json
import pathlib
import re
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
PROC = ROOT / "01_datasets" / "processed"
RAW = ROOT / "results_raw"
EXP = "EXP-0225"
CONFIGS = ("OSS", "Qwen3", "Kimi-K2")
NORM = re.compile(r"[^a-z0-9 ]+")


def norm(q: str) -> str:
    return NORM.sub(" ", " ".join(str(q or "").lower().split())).strip()


def measure(frames: dict) -> dict:
    """frames: {config: [(uuid, prompt_id, split, question), ...]}"""
    uuids_per_prompt = collections.defaultdict(set)
    prompts_per_config = {}
    side = collections.defaultdict(set)
    rows = collections.Counter()
    for cfg, rs in frames.items():
        seen = set()
        for uuid, pid, split, q in rs:
            rows[cfg] += 1
            uuids_per_prompt[pid].add(uuid)
            seen.add(pid)
            side[(pid, split)].add(norm(q))
        prompts_per_config[cfg] = seen
    pooled = set().union(*prompts_per_config.values()) if prompts_per_config else set()
    recur = [p for p in pooled if sum(p in prompts_per_config[c] for c in prompts_per_config) > 1]
    multi_uuid = [p for p, u in uuids_per_prompt.items() if len(u) > 1]
    # exact text overlap across the split boundary, per config: the question string and the split label only
    overlap = {}
    for cfg, rs in frames.items():
        dev = {norm(q) for u, p, s, q in rs if s == "dev"}
        test = {norm(q) for u, p, s, q in rs if s != "dev"}
        n = sum(1 for u, p, s, q in rs if s == "dev" and norm(q) in test)
        overlap[cfg] = {"dev_rows": len(dev), "other_split_rows": len(test),
                        "dev_questions_also_on_the_other_side": n,
                        "share": round(n / max(len(dev), 1), 6)}
    return {"rows_read_per_config": dict(rows),
            "prompt_ids_recurring_across_configs": len(recur),
            "recurrence_share_of_pooled_prompts": round(len(recur) / max(len(pooled), 1), 6),
            "pooled_prompt_ids": len(pooled),
            "prompt_ids_arriving_under_more_than_one_uuid": len(multi_uuid),
            "share_of_prompts_with_several_uuids": round(len(multi_uuid) / max(len(uuids_per_prompt), 1), 6),
            "exact_question_overlap_across_the_split_boundary": overlap,
            "columns_touched": ["uuid", "prompt_id", "split", "question"],
            "outcome_columns_read_for_any_test_row": "none - only the split label and the question string are used"}


def selftest() -> bool:
    """A hand-built frame where every quantity is known in advance."""
    f = {"OSS": [("u1", "p1", "dev", "Find the  report!"), ("u2", "p1", "test", "other"),
                 ("u3", "p2", "dev", "same text")],
         "Qwen3": [("u4", "p2", "dev", "SAME  TEXT"), ("u5", "p3", "dev", "x")]}
    m = measure(f)
    # p1 arrives under u1 and u2, p2 under u3 and u4 - two prompts with several uuids, not one; the recurrence is
    # p2 (dev in both configs) and p1 appears in one config only.
    ok = (m["prompt_ids_arriving_under_more_than_one_uuid"] == 2
          and abs(m["share_of_prompts_with_several_uuids"] - 0.666667) < 1e-4
          and m["pooled_prompt_ids"] == 3
          and m["prompt_ids_recurring_across_configs"] == 1
          and m["exact_question_overlap_across_the_split_boundary"]["OSS"]["dev_questions_also_on_the_other_side"] == 0
          and m["outcome_columns_read_for_any_test_row"].startswith("none"))
    print("selftest:", "PASS" if ok else json.dumps(m, indent=1)[:900])
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if a.selftest:
        return 0 if selftest() else 1
    import pandas as pd
    t0 = time.time()
    frames = {}
    for cfg in CONFIGS:
        p = PROC / f"routing_{cfg}.parquet"
        if not p.is_file():
            raise SystemExit(f"ABORT: {p.name} is not on disk, so the probe cannot re-derive D5's numbers")
        d = pd.read_parquet(p, columns=["uuid", "prompt_id", "split", "question"])
        frames[cfg] = list(d.itertuples(index=False, name=None))
    out = measure(frames)
    art = {"exp_id": EXP, "seed": 42, "quick": False,
           "started_at": datetime.datetime.fromtimestamp(t0).isoformat(timespec="seconds"),
           "frames_read": {c: str((PROC / f'routing_{c}.parquet').name) for c in frames},
           "measured": out, "supersedes_the_console_probe_of": "EXP-0008",
           "wallclock_sec": round(time.time() - t0, 1),
           "invocation": " ".join([sys.executable] + sys.argv),
           "finished_at": datetime.datetime.now().isoformat(timespec="seconds")}
    RAW.mkdir(exist_ok=True)
    p = RAW / f"{EXP.replace('-', '')}_split_contamination_promoted_" \
              f"{time.strftime('%Y%m%dT%H%M%S')}.json"
    p.write_text(json.dumps(art, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out, indent=1, ensure_ascii=False)[:900])
    print("wrote", p.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
