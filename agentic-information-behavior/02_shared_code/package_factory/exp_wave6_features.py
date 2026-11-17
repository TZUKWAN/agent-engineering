"""EXP-0173: wave 6's step frame - one row per commanded assistant step of a SWE-ZERO rollout.

The census (EXP-0172) read every row of the twelve drawn files to measure the premises. The frame is the wave's
frozen draw: 20,000 trajectory rows selected with seed 42 from those same files, keeping every commanded step of
each selected rollout, so a cell in this wave is the same kind of cell it is in waves 4 and 5. Each row carries the
step's own measured properties and the properties of the trajectory and the instance it sits in:

* `family` - the command's information-action family from the frozen 12-family table, `switched` against the
  previous step's family, `stays_in_family` against the rollout's first one;
* `new_information` - the share of the observation's content words present in no earlier observation and not in the
  issue text, which is the only mechanical reading of "this step told me something" available without a model;
* `is_repeat`, `repeat_index` - whether this exact command was issued earlier in the same rollout, and how many
  times, so rumination is a count rather than an impression;
* `scent_jaccard`, `scent_contain` - how far the text the agent wrote before the command reaches into the command
  it then typed, symmetric and asymmetric;
* `continues`, `submitted`, `n_steps`, `step_budget` - the step's place in the search and how the search ended.

Everything derived at trajectory and instance level is computed once here, so no design can quietly define depth, a
switch or a repetition differently from another. The self-test reads a hand-built rollout and asserts each flag,
which is what catches an instrument that stopped matching before the association it feeds is reported as null.

    python 02_shared_code/package_factory/exp_wave6_features.py [--cap 20000]
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import pathlib
import random
import re
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np                                                # noqa: E402
import pandas as pd                                               # noqa: E402
import pyarrow.parquet as pq                                      # noqa: E402
import wave_lib as W                                              # noqa: E402
import probe_wave6_premises as P6                                 # noqa: E402  one instrument set, both steps

EXP = "EXP-0173"
TD6 = __import__("topic_designs_wave6")
SEED = TD6.SEED
CAP = int(TD6.COMMON["sample"]["traj_cap"])
N_FILES = 12
SUBMITTED_LABEL = "Submitted"                                     # the release's own submission label
BAD = collections.Counter()


def load_trajectories(cap: int = CAP):
    """The 12 files the census drew, deduplicated by exact content, then a seeded draw of `cap` trajectory rows.

    A release that stores the same rollout twice would otherwise be sampled twice, which inflates every per-step
    prevalence and leaves the cluster-robust intervals untouched - the defect EXP-0162 found in the hermes release.
    Here the test is the whole row: same instance, same messages, same label. Rollouts that differ anywhere, even in
    one step, are kept, because repeated attempts at one task are the wave's comparison, not duplicates.
    """
    files = sorted(p for p in P6.CORPUS.glob("*.parquet"))
    if not files:
        raise SystemExit(f"ABORT: no parquet under {P6.CORPUS}")
    picks = sorted(random.Random(SEED).sample(files, min(N_FILES, len(files))))
    rows = []
    for f in picks:
        pf = pq.ParquetFile(f)
        for batch in pf.iter_batches(batch_size=2000, columns=["instance_id", "messages", "exit_status",
                                                              "duration_sec", "repo"]):
            rows.extend(batch.to_pylist())
    seen, uniq = set(), []
    for r in rows:
        h = hashlib.sha256((str(r.get("instance_id")) + json.dumps(r.get("messages"), sort_keys=True,
                                                                   default=str)).encode("utf-8")).hexdigest()
        if h in seen:
            continue
        seen.add(h)
        uniq.append(r)
    drawn = random.Random(SEED).sample(uniq, min(cap, len(uniq)))
    return drawn, [f.name for f in picks], len(rows), len(rows) - len(uniq)


def step_rows(traj: dict, traj_key: str) -> list:
    """Every commanded assistant step of one rollout, with the within-rollout state each feature needs."""
    msgs = traj.get("messages") or []
    issue = next((str(m.get("content") or "") for m in msgs if str(m.get("role")) == "user"), "")
    issue_words = P6.words(issue)
    seen_words = set(issue_words)                  # the issue text is not news to the agent
    seen_cmds = collections.Counter()
    steps = []
    for i, m in enumerate(msgs):
        if str(m.get("role")) != "assistant":
            continue
        text = str(m.get("content") or "")
        b = P6.COMMAND_BLOCK.search(text)
        if not b:
            continue
        cmd = re.sub(r"\s+", " ", b.group(1)).strip()
        if not cmd:
            continue
        fam = P6.family_of(cmd)
        pre = text[:b.start()]
        nxt = msgs[i + 1] if i + 1 < len(msgs) else None
        obs = ""
        if nxt is not None and str(nxt.get("role")) == "user" and P6.OBS_START.match(str(nxt.get("content") or "")):
            obs = P6.OBS_START.sub("", str(nxt.get("content") or "")).strip()
        ow = P6.words(obs)
        new_share = (round(len(ow - seen_words) / max(1, len(ow)), 4) if ow else np.nan)
        seen_words |= ow
        pw, cw = P6.words(pre), P6.words(cmd)
        inter = len(pw & cw)
        steps.append({
         "traj_key": traj_key, "instance_id": str(traj.get("instance_id") or ""), "repo": str(traj.get("repo") or ""),
         "step_index": len(steps) + 1, "family": fam,
         "command_sha": hashlib.sha256(cmd.encode("utf-8")).hexdigest()[:16],
         "pre_text_words": len(pw), "step_words": len(pw | cw),
         "scent_jaccard": (round(inter / max(1, len(pw | cw)), 4) if (pw or cw) else np.nan),
         "scent_contain": (round(inter / max(1, len(pw)), 4) if pw else np.nan),
         "new_information": new_share, "obs_chars": len(obs),
         "failed_observation": int(any(x in obs.lower() for x in P6.FAIL_MARKERS)),
         "success_language": int(any(x in obs.lower() for x in P6.SUCCESS_MARKERS)),
         "repeat_index": int(seen_cmds[cmd]), "is_repeat": int(seen_cmds[cmd] > 0),
         "issue_words": len(issue_words),
         "outcome": str(traj.get("exit_status") or ""),
         "duration": str(traj.get("duration_sec") or ""),
        })
        seen_cmds[cmd] += 1
    return steps


def add_trajectory_and_instance(F: pd.DataFrame) -> pd.DataFrame:
    """Depth, concentration, switching rate, budget and the leave-one-out modal first family, computed once."""
    F = F.sort_values(["traj_key", "step_index"]).reset_index(drop=True)
    g = F.groupby("traj_key", sort=False)
    F["n_steps"] = g["step_index"].transform("size").astype(int)
    F["log_steps"] = np.log1p(F["n_steps"].astype(float))
    F["first_family"] = g["family"].transform("first")
    F["prev_family"] = g["family"].shift(1)
    F["switched"] = ((F["family"] != F["prev_family"]) & F["prev_family"].notna()).astype(int)
    F["stays_in_family"] = ((F["family"] == F["first_family"]) & F["step_index"].gt(1)).astype(int)
    F["family_concentration"] = (F["family"] == F["first_family"]).groupby(F["traj_key"]).transform("mean").astype(float)
    F["has_exact_repeat"] = g["is_repeat"].transform("max").astype(int)
    F["max_repeat_index"] = g["repeat_index"].transform("max").astype(int)
    F["cumulative_newness"] = F.groupby("traj_key")["new_information"].transform(lambda s: s.expanding().mean())
    F["continues"] = (g["step_index"].shift(-1).notna()).astype(int)
    F["submitted"] = (F["outcome"] == SUBMITTED_LABEL).astype(int)
    F["step_position"] = F["step_index"] / F["n_steps"].clip(lower=1)
    # instance-level: the budget its rollouts reached, the need length standardised inside it, and the modal first
    # family of its *other* rollouts - a rollout is never its own comparison.
    gi = F.groupby("instance_id", sort=False)
    F["step_budget"] = gi["n_steps"].transform("max").astype(int)
    F["need_words"] = gi["issue_words"].transform("first").astype(int)
    sd = F["need_words"].astype(float).std(ddof=0)
    F["need_words_z"] = (F["need_words"].astype(float) - F["need_words"].astype(float).mean()) / (sd if sd else 1.0)
    firsts = F.drop_duplicates("traj_key")[["traj_key", "instance_id", "first_family"]]
    per_inst = collections.defaultdict(collections.Counter)
    for iid, fam in firsts[["instance_id", "first_family"]].itertuples(index=False):
        per_inst[iid][fam] += 1

    def modal_leave_one_out(iid, fam):
        """The instance's modal first family among its *other* rollouts; ties break on the family name."""
        c = dict(per_inst[iid])
        c[fam] = c.get(fam, 0) - 1
        c = {k: v for k, v in c.items() if v > 0}
        if not c:                                       # the instance's only rollout: no contrast exists for it
            return fam
        return sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]

    firsts = firsts.assign(instance_modal_first=[modal_leave_one_out(i, f) for i, f in
                                                 zip(firsts["instance_id"], firsts["first_family"])])
    F = F.merge(firsts[["traj_key", "instance_modal_first"]], on="traj_key", how="left")
    F["off_modal_first"] = (F["first_family"] != F["instance_modal_first"]).astype(int)
    rolls = firsts.groupby("instance_id")["traj_key"].nunique()
    F["rollouts_in_instance"] = F["instance_id"].map(rolls).astype(int)
    F["single_rollout_instance"] = (F["rollouts_in_instance"] <= 1).astype(int)
    F["switch_rate"] = F.groupby("traj_key")["switched"].transform("mean").astype(float)
    F["task_family"] = F["repo"].str.split("/").str[0].fillna("unknown")
    return F


def selftest() -> int:
    """A hand-built rollout in which every wave-6 flag has a known value, asserted before the release is read."""
    msgs = [{"role": "system", "content": "solve the issue"},
            {"role": "user", "content": "Please solve this issue in the repository a/b. Title: drop the obsolete "
                                        "injection command; run the test suite for the parser module."},
            {"role": "assistant", "content": "THOUGHT: find the test files.\n```bash\nfind . -name '*test*'\n```"},
            {"role": "user", "content": "Observation: ./tests/test_parser.py\n./tests/cli_test.py"},
            {"role": "assistant", "content": "look at the parser test for injection\n```bash\ngrep -n injection "
                                             "./tests/test_parser.py\n```"},
            {"role": "user", "content": "Observation: no such file or directory"},
            {"role": "assistant", "content": "```bash\nfind . -name '*test*'\n```"},
            {"role": "user", "content": "Observation: ./tests/test_parser.py\n./tests/cli_test.py"},
            {"role": "assistant", "content": "```bash\ncat ./tests/cli_test.py\n```"},
            {"role": "user", "content": "Observation: def test_cli(): assert True\n"}]
    rows = step_rows({"instance_id": "i1", "messages": msgs, "exit_status": SUBMITTED_LABEL, "repo": "a/b",
                      "duration_sec": "12.0"}, "t1")
    F = add_trajectory_and_instance(pd.DataFrame(rows))
    assert [r for r in F["family"]] == ["search_name", "search_content", "search_name", "read_file"], list(F["family"])
    assert list(F["step_index"]) == [1, 2, 3, 4] and int(F["n_steps"].iloc[0]) == 4
    assert list(F["switched"]) == [0, 1, 1, 1], list(F["switched"])
    assert list(F["is_repeat"]) == [0, 0, 1, 0] and list(F["repeat_index"]) == [0, 0, 1, 0]
    assert list(F["stays_in_family"]) == [0, 0, 1, 0], list(F["stays_in_family"])
    assert F.loc[1, "failed_observation"] == 1 and F.loc[0, "failed_observation"] == 0
    assert F.loc[2, "new_information"] == 0.0, "the repeated find returns nothing it had not already seen"
    assert F.loc[0, "new_information"] > 0.5, "the first observation is all new"
    assert F.loc[2, "scent_jaccard"] >= 0.0 and F.loc[1, "scent_jaccard"] > F.loc[2, "scent_jaccard"]
    assert list(F["continues"]) == [1, 1, 1, 0] and int(F["submitted"].iloc[0]) == 1
    assert F.loc[0, "family_concentration"] > 0.4 and int(F["has_exact_repeat"].iloc[0]) == 1
    assert F["instance_modal_first"].nunique() == 1 and (F["off_modal_first"] == 0).all(), \
        "a single-rollout instance cannot be off its own modal first family"
    assert float(F["step_position"].iloc[-1]) == 1.0
    # the instance-level contrast: two rollouts of one task and one rollout of another, opened with different
    # families, so the leave-one-out modal family and the single-rollout flag are both exercised
    def traj(first_cmd, iid):
        return {"instance_id": iid, "exit_status": "incomplete", "repo": "a/b", "duration_sec": "9",
                "messages": msgs[:2] + [{"role": "assistant", "content": "```bash\n" + first_cmd + "\n```"},
                                        {"role": "user", "content": "Observation: done"}]}
    rows2 = (step_rows(traj("find . -name x", "i1"), "a") + step_rows(traj("cat ./a/b.py", "i1"), "b")
             + step_rows(traj("grep -r q .", "i2"), "c"))
    G = add_trajectory_and_instance(pd.DataFrame(rows2))
    flags = dict(zip(G["traj_key"], G["single_rollout_instance"]))
    assert flags == {"a": 0, "b": 0, "c": 1}, flags
    off = dict(zip(G["traj_key"], G["off_modal_first"]))
    assert off == {"a": 1, "b": 1, "c": 0}, off          # each of a,b is off the other's family; c has no contrast
    print("SELFTEST OK: families, switches, repeats, newness, scent, continuation and the instance contrast all land")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap", type=int, default=CAP)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if a.selftest:
        return selftest()
    t0 = time.time()
    selftest()
    W.OUT.mkdir(parents=True, exist_ok=True)
    trajs, files, rows_in_files, dupes = load_trajectories(a.cap)
    if not trajs:
        raise SystemExit("ABORT: the drawn files yielded no trajectory rows - the frame has no subject")
    rows = []
    for k, t in enumerate(trajs):
        rows.extend(step_rows(t, f"{k}"))
        if (k + 1) % 4000 == 0:
            print(f"  frame: {k + 1}/{len(trajs)} rollouts walked, {len(rows)} steps", flush=True)
    if not rows:
        raise SystemExit("ABORT: no commanded assistant step was recovered, so wave 6 has no subject")
    F = add_trajectory_and_instance(pd.DataFrame(rows))
    rolls = F.drop_duplicates("traj_key").groupby("instance_id")["traj_key"].nunique()
    dest_csv = W.OUT / "EXP0173_wave6_step_features.csv.gz"
    F.to_csv(dest_csv, compression="gzip", index=False)

    def share(col):
        return round(float(F[col].mean()), 4) if col in F else None

    art = {"exp_id": EXP, "corpus": P6.CORPUS.name, "files_read": files, "rows_in_drawn_files": rows_in_files,
           "trajectories": int(F["traj_key"].nunique()), "instances": int(F["instance_id"].nunique()),
           "steps": int(len(F)), "sample_cap": int(a.cap), "cluster_unit": TD6.COMMON["sample"]["cluster_unit"],
           "median_steps_per_trajectory": float(F.groupby("traj_key")["step_index"].size().median()),
           "family_share_of_steps": {str(k): round(float(v), 4) for k, v in
                                     F["family"].value_counts(normalize=True).items()},
           "switch_share": share("switched"), "repeat_step_share": share("is_repeat"),
           "trajectories_with_exact_repeat": int(F.groupby("traj_key")["has_exact_repeat"].max().sum()),
           "off_modal_first_trajectories": int(F.groupby("traj_key")["off_modal_first"].max().sum()),
           "failed_observation_share": share("failed_observation"),
           "commands_with_observation_share": round(float((F["obs_chars"] > 0).mean()), 4),
           "new_information_mean": round(float(F["new_information"].mean()), 4),
           "scent_jaccard_mean": round(float(F["scent_jaccard"].mean()), 4),
           "scent_contain_mean": round(float(F["scent_contain"].mean()), 4),
           "submitted_share": share("submitted"), "outcome_levels":
               {str(k): int(v) for k, v in F.drop_duplicates("traj_key")["outcome"].value_counts().items()},
           "instances_with_only_one_outcome_level": int(sum(
               1 for _, gg in F.groupby("instance_id") if gg["submitted"].nunique() < 2)),
           "unparsed_family_steps": int((F["family"] == "unparsed").sum()),
           "rollouts_in_multi_rollout_instances": int(rolls[rolls >= 2].sum()),
           "instances_with_a_single_rollout": int((rolls == 1).sum()),
           "duplicate_rollout_rows_dropped_before_sampling": int(dupes),
           "frame_file": str(dest_csv.relative_to(W.ROOT)), "seed": SEED, "started_at": W.now(),
           "wallclock_sec": round(time.time() - t0, 1), "invocation": " ".join([sys.executable] + sys.argv),
           "run_cost": W.run_cost_row(EXP, t0, int(len(F)), int(F.shape[1]), "wave-6 frame")}
    dest = W.write_raw(EXP, "wave6_step_matrix", art)
    print(json.dumps(art, indent=1, ensure_ascii=False, default=str)[:1900])
    print(f"\n{EXP}: wrote {dest_csv.name} ({len(F)} steps) and {dest.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
