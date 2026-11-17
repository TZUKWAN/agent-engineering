"""EXP-0162: does the hermes release repeat trajectories, and what does that do to a per-turn count?

Wave 5's premise census found that a seeded sample of 4,000 trajectory ids arrived as 6,095 rows - 2,095 rows whose
`traj_id` was already present. Checking the wave-4 frame that ships in P023-P026, **175,334 of its 234,920 turn rows
(74.6%) sit in a (traj_id, turn_index) group that occurs more than once, and all 87,667 of those groups are
byte-identical turns**: the release stores some trajectories in more than one file under the same id. That is not a
rounding detail. Every "N turns", marker prevalence and rate table in this wave's packages has been counting those
trajectories twice, while the cluster-robust variance grouped them once, so the point estimates weighted the
duplicated part of the corpus more heavily than the intervals do.

This experiment measures the fact itself, before any of it is corrected:

* rows and distinct `traj_id`s per file, and how many ids occur in more than one file;
* the distribution of rows-per-id;
* whether the repeated rows are identical (`conversations` compared exactly) or differ;
* what the wave-4 headline prevalences look like with and without the duplicates, so the correction's size is on
  record rather than being asserted to be small.

    python 02_shared_code/package_factory/probe_release_traj_duplication.py
"""
from __future__ import annotations

import argparse
import collections
import glob
import hashlib
import json
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np                                              # noqa: E402
import pandas as pd                                             # noqa: E402
import wave_lib as W                                            # noqa: E402
import exp_wave4_features as EF                                 # noqa: E402
import probe_wave4_premises as P4                                 # noqa: E402  (same lexicons, same tags)

EXP = "EXP-0162"


def conv_hash(c) -> str:
    return hashlib.sha256(json.dumps([[str(m.get("from")), str(m.get("value"))] for m in list(c)],
                                     ensure_ascii=False).encode("utf-8")).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-prevalence", type=int, default=4000, help="trajectories in the before/after comparison")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    files = sorted(glob.glob(str(EF.CORPUS / "data" / "**" / "*.parquet"), recursive=True))
    if not files:
        raise SystemExit(f"ABORT: no parquet under {EF.CORPUS}")
    per_file, ids_by_file = {}, {}
    frames = []
    for f in files:
        df = pd.read_parquet(f)
        df = df[[c for c in ("id", "category", "subcategory", "conversations") if c in df.columns]]
        df["traj_id"] = df["id"].astype(str) if "id" in df.columns else ["R%d" % i for i in range(len(df))]
        per_file[pathlib.Path(f).name] = {"rows": int(len(df)), "distinct_ids": int(df["traj_id"].nunique())}
        ids_by_file[pathlib.Path(f).name] = set(df["traj_id"])
        df["_file"] = pathlib.Path(f).name
        frames.append(df)
    allr = pd.concat(frames, ignore_index=True)
    counts = allr.groupby("traj_id").size()
    multi = {k: v for k, v in ids_by_file.items() if len(v)}
    shared = collections.Counter()
    names = list(multi)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            shared[f"{names[i]}|{names[j]}"] = len(multi[names[i]] & multi[names[j]])
    dup_ids = counts[counts > 1]
    same_hash, diff_hash = 0, 0
    for tid, g in allr[allr["traj_id"].isin(list(dup_ids.index[:300]))].groupby("traj_id"):
        hs = {conv_hash(c) for c in g["conversations"]}
        same_hash += int(len(hs) == 1)
        diff_hash += int(len(hs) > 1)

    # the before/after effect on the three headline marker prevalences, on one seeded sample of ids
    uniq_ids = pd.Index(allr["traj_id"].unique())
    rng = np.random.default_rng(42)
    sample = rng.choice(uniq_ids.to_numpy(), size=min(a.n_prevalence, len(uniq_ids)), replace=False)
    raw = allr[allr["traj_id"].isin(set(sample))]
    ded = raw.drop_duplicates(subset=["traj_id"], keep="first")

    def prev(df):
        turns = 0
        modal = suffic = plan = 0
        for c in df["conversations"]:
            for m in list(c):
                role, v = str(m.get("from")), str(m.get("value"))
                if role not in ("gpt", "assistant"):
                    continue
                body = EF.THINK.sub("", v).strip()
                if len(body) < 20:
                    continue
                turns += 1
                low = v.lower()
                modal += int(any(k in low for k in P4.MODAL))
                suffic += int(any(k in low for k in P4.SUFFIC))
                plan += int("i will" in low or "let me " in low)
        return {"turns": turns, "modal_share": round(modal / max(1, turns), 4),
                "suffic_share": round(suffic / max(1, turns), 4), "plan_share": round(plan / max(1, turns), 4)}

    before, after = prev(raw), prev(ded)
    out = {"exp_id": EXP, "corpus": str(EF.CORPUS.name), "files": per_file,
           "rows_total": int(len(allr)), "distinct_traj_ids": int(allr["traj_id"].nunique()),
           "ids_in_more_than_one_file": {k: v for k, v in sorted(shared.items()) if v},
           "rows_per_id_distribution": {str(int(k)): int(v) for k, v in
                                        counts.value_counts().sort_index().items()},
           "ids_with_duplicates": int(len(dup_ids)),
           "duplicate_ids_byte_identical": same_hash, "duplicate_ids_differing": diff_hash,
           "sampled_ids": int(len(sample)),
           "prevalences_duplicating_rows": before, "prevalences_after_dedup": after,
           "absolute_change": {k: round(after[k] - before[k], 4) for k in
                               ("modal_share", "suffic_share", "plan_share")},
           "verdict": {"release_repeats_trajectory_ids": bool(len(dup_ids)),
                       "duplicates_are_identical": bool(diff_hash == 0 and same_hash > 0),
                       "per_turn_counts_double_count_duplicated_trajectories": bool(before["turns"] > after["turns"])},
           "wallclock_sec": round(time.time() - t0, 1), "started_at": W.now(),
           "invocation": " ".join([sys.executable] + sys.argv), "seed": 42}
    dest = W.write_raw(EXP, "release_traj_duplication", out)
    print(json.dumps(out, indent=1, ensure_ascii=False, default=str)[:2600])
    print(f"\n{EXP}: wrote {dest.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
