"""EXP-0197: wave 9's step frame - the wave-6 spine plus the position, lag and phase columns wave 9's designs name.

The reader, the seeded 12-file draw, the content deduplication and the command parser are wave 6's, imported rather
than restated, so a `family`, a `new_information` share and a `failed_observation` mean the same thing in both waves.
What is added here is everything the four surviving designs condition on and the two stopped ones would have needed:

* `in_first_fifth` / `in_last_fifth` - the first and last ceil(n_steps / 5) commanded steps of the rollout, which is
  the phase split T178 predicts from;
* `changed_at_lag_1..5` and `first_change_lag` - whether the command k steps after a failed observation differs in
  *both* name and arguments from the failing one, the window T179 measures;
* `steps_without_observation` - how many of a rollout's commands are followed by nothing, which is the 21% EXP-0196
  measured and the reason T151 and T156 are stopped;
* the rollout-level feature block T178 and T193 use, with the family mixture, the switch rate, the repetition share
  and the release's own `exit_status` and `duration_sec`.

The frame cross-checks every aggregate it shares with EXP-0196 and refuses to write if a pair diverges, and the join
from steps to rollouts is guarded against a column shadowing another, both of which are the failures wave 8 recorded
as W8-D04 and W8-D05. Nothing here estimates an association.

    python 02_shared_code/package_factory/exp_wave9_features.py
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np                                                # noqa: E402
import pandas as pd                                               # noqa: E402
import wave_lib as W                                              # noqa: E402
import exp_wave6_features as EF6                                  # noqa: E402  the reader and the step builder
import probe_wave9_premises as P9                                 # noqa: E402  the same derivations, one place
import topic_designs_wave9 as TD9                                 # noqa: E402

EXP = "EXP-0197"
SEED = TD9.SEED
LAGS = (1, 2, 3, 4, 5)


def derived(rows: list) -> list:
    """The step-level columns wave 9 adds, in one pass over one rollout's commanded steps.

    The lag is anchored on the rollout's **first** failed observation, which is the event T179's sentence names, and
    the flag is carried on every step of that rollout so a row-level model and a rollout-level rollup read the same
    quantity rather than two similar ones.
    """
    n = len(rows)
    fams = [r["family"] for r in rows]
    cut = math.ceil(n / 5.0)
    fails = [i for i, r in enumerate(rows) if r["failed_observation"]]
    first = fails[0] if fails else None
    lags = {}
    for k in LAGS:
        j = None if first is None else first + k
        lags[k] = int(j is not None and j < n and rows[j]["command_sha"] != rows[first]["command_sha"])
    first_change = min([k for k, v in lags.items() if v] or [0])
    for i, r in enumerate(rows):
        r["n_steps"] = n
        r["position"] = round((i + 1) / max(1, n), 4)
        r["switched"] = int(i > 0 and fams[i] != fams[i - 1])
        r["in_first_fifth"] = int(i < cut)
        r["in_last_fifth"] = int(i >= n - cut)
        r["steps_without_observation"] = int(not (r.get("obs_chars") or 0))
        r["has_failure"] = int(first is not None)
        r["after_first_failure"] = int(first is not None and i > first)
        r["steps_since_first_failure"] = int(i - first) if first is not None and i >= first else 0
        r["first_change_lag"] = first_change
        for k in LAGS:
            r[f"changed_at_lag_{k}"] = lags[k]
    return rows


def rollup(traj: dict, rows: list) -> dict:
    """One rollout -> the row the trajectory-level models are fitted on."""
    n = len(rows)
    fams = collections.Counter(r["family"] for r in rows)
    new = [r["new_information"] for r in rows if r["new_information"] == r["new_information"]]
    ex = str(traj.get("exit_status") or "")
    return {"traj_key": rows[0]["traj_key"], "instance_id": str(traj.get("instance_id")),
            "repo": str(traj.get("repo") or ""), "task_family": str(traj.get("repo") or "").split("/")[0],
            "n_steps": n, "duration": float(traj.get("duration_sec") or np.nan),
            "outcome": ex, "submitted": int(ex.strip().lower() == "submitted"),
            "switch_rate": round(sum(r["switched"] for r in rows[1:]) / max(1, n - 1), 4),
            "family_concentration": round(max(fams.values()) / n, 4),
            "distinct_families": int(len(fams)),
            "repeat_share": round(float(np.mean([r["is_repeat"] for r in rows])), 4),
            "max_repeat_index": int(max([r["repeat_index"] for r in rows]) if rows else 0),
            "newness_mean": round(float(np.mean(new)), 4) if new else float("nan"),
            "steps_without_observation": int(sum(r["steps_without_observation"] for r in rows)),
            "obs_chars_mean": round(float(np.mean([r["obs_chars"] for r in rows])), 1),
            "failures": int(sum(1 for r in rows if r["failed_observation"])),
            "failure_then_a_further_command": int(any(r["failed_observation"] and i < len(rows) - 1
                                                       for i, r in enumerate(rows))),
            "first_failure_index": int(next((i + 1 for i, r in enumerate(rows) if r["failed_observation"]), 0)),
            "changed_at_lag_1": int(any(r["changed_at_lag_1"] for r in rows)),
            "changed_at_lag_3": int(any(r["changed_at_lag_3"] for r in rows)),
            "changed_at_lag_5": int(any(r["changed_at_lag_5"] for r in rows)),
            "first_change_lag": int(min([r["first_change_lag"] for r in rows if r["first_change_lag"]] or [0])),
            "ff_switch_rate": round(float(np.mean([r["switched"] for r in rows if r["in_first_fifth"]] or [0])), 4),
            "ff_distinct_families": int(len({r["family"] for r in rows if r["in_first_fifth"]})),
            "ff_repeat_share": round(float(np.mean([r["is_repeat"] for r in rows if r["in_first_fifth"]] or [0])), 4),
            "ff_newness_mean": (round(float(np.mean([r["new_information"] for r in rows if r["in_first_fifth"]
                                                     and r["new_information"] == r["new_information"]])), 4)
                                if any(r["in_first_fifth"] and r["new_information"] == r["new_information"]
                                       for r in rows) else float("nan")),
            "ff_cmd_words": round(float(np.mean([r["step_words"] for r in rows if r["in_first_fifth"]] or [0])), 2),
            "lf_newness_mean": (round(float(np.mean([r["new_information"] for r in rows if r["in_last_fifth"]
                                                     and r["new_information"] == r["new_information"]])), 4)
                                if any(r["in_last_fifth"] and r["new_information"] == r["new_information"]
                                       for r in rows) else float("nan")),
            "lf_switch_rate": round(float(np.mean([r["switched"] for r in rows if r["in_last_fifth"]] or [0])), 4)}


def build():
    drawn, picks, rows_in_files, dupes = EF6.load_trajectories(int(TD9.COMMON["sample"]["traj_cap"]))
    steps, rolls = [], []
    for k, t in enumerate(drawn):
        rows = EF6.step_rows(t, f"{t.get('instance_id')}|{k}")
        if not rows:
            continue
        rows = derived(rows)
        steps.extend(rows)
        rolls.append(rollup(t, rows))
    return steps, pd.DataFrame(rolls), picks, rows_in_files, dupes, len(drawn)


def census() -> dict:
    for f in sorted(W.RAWRES.glob("EXP0196_wave9_premise_census_*.json"), reverse=True):
        a = json.loads(f.read_text(encoding="utf-8"))
        if "--traj-cap" in str(a.get("invocation", "")):
            continue
        return {"file": f.name, "measured": a["measured"]}
    raise SystemExit("ABORT: no whole-sample EXP-0196 census exists, so this frame has nothing to check itself "
                     "against")


def selftest() -> int:
    fence = "```bash\n"
    msgs = [{"role": "user", "content": "fix the parser in x.py"}]
    for i, cmd in enumerate(["cat x.py", "ls -la", "grep -n parser x.py", "python t.py", "cat y.py"]):
        msgs.append({"role": "assistant", "content": "step %d\n" % (i + 1) + fence + cmd + "\n```"})
        msgs.append({"role": "user",
                     "content": "Output: " + ("no such file" if i == 0 else "done with x.py y.py z.py w%d" % i)})
    traj = {"instance_id": "i1", "exit_status": "Submitted", "duration_sec": 12.0, "repo": "acme/thing",
            "messages": msgs}
    rows = derived(EF6.step_rows(traj, "t1"))
    assert len(rows) == 5, len(rows)
    assert rows[0]["failed_observation"] == 1 and rows[0]["changed_at_lag_1"] == 1
    assert rows[0]["first_change_lag"] == 1 and sum(r["switched"] for r in rows) >= 3
    assert rows[0]["in_first_fifth"] == 1 and rows[-1]["in_last_fifth"] == 1
    tl = rollup(traj, rows)
    assert tl["n_steps"] == 5 and tl["submitted"] == 1 and tl["distinct_families"] >= 3
    assert 0.0 <= tl["switch_rate"] <= 1.0 and tl["newness_mean"] == tl["newness_mean"]
    print("SELFTEST OK: phases, switches, failure lags and the rollout rollup all land on a built rollout")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if a.selftest:
        return selftest()
    t0 = time.time()
    selftest()
    W.OUT.mkdir(parents=True, exist_ok=True)
    steps, T, picks, rows_in_files, dupes, drawn = build()
    if not steps:
        raise SystemExit("ABORT: no commanded step was read, so the wave has no subject")
    S = pd.DataFrame(steps)
    tcols = ["traj_key", "task_family", "submitted"]
    clash = sorted({c for c in tcols if c in S.columns} - {"traj_key"})
    if clash:
        raise SystemExit(f"ABORT: the rollout summary re-supplies {clash}, which the join would rename to "
                         f"<name>_x and <name>_y")
    before = len(S)
    S = S.merge(T[tcols], on="traj_key", how="left", validate="many_to_one")
    if len(S) != before:
        raise SystemExit(f"ABORT: the rollout join changed the step count from {before} to {len(S)}")
    S["position_decile"] = (np.ceil(S["position"].astype(float) * 10).clip(1, 10)).astype(int)
    S["log_obs_chars"] = np.log1p(S["obs_chars"].astype(float))
    T["log_steps"] = np.log1p(T["n_steps"].astype(float))
    T["duration_log"] = np.log1p(T["duration"].astype(float))
    T["steps_without_obs_share"] = (T["steps_without_observation"] / T["n_steps"]).round(4)
    T["length_quartile"] = pd.qcut(T["n_steps"].rank(method="first"), 4,
                                   labels=["q1_shortest", "q2", "q3", "q4_longest"]).astype(str)
    T["rollouts_per_instance"] = T.groupby("instance_id")["traj_key"].transform("size")
    T["success_only_rank"] = T.groupby("instance_id")["submitted"].rank(ascending=False, method="first")
    c = census()
    cen, cm = c["file"], c["measured"]
    inst_sizes = T.groupby("instance_id").size()
    x = {"rollouts": (int(T.shape[0]), int(cm["trajectories_parsed"])),
         "steps": (int(len(S)), int(cm["steps_total"])),
         "instances": (int(T["instance_id"].nunique()), int(cm["instances"])),
         "instances_with_2plus_rollouts": (int(inst_sizes.ge(2).sum()), int(cm["instances_with_2plus_rollouts"])),
         "submitted_rollouts": (int(T["submitted"].sum()), int(cm["outcome_values"].get("Submitted") or 0)),
         "mean_steps": (round(float(T["n_steps"].mean()), 2), float(cm["mean_steps"])),
         "median_steps": (float(T["n_steps"].median()), float(cm["median_steps"])),
         "distinct_command_families": (int(S["family"].nunique()), int(cm["distinct_command_families"])),
         "rollouts_with_a_failure_then_a_command": (int(T["failure_then_a_further_command"].sum()),
                                                    int(cm["trajectories_with_a_failure_then_a_further_command"])),
         "newness_available_share": (round(float(S["new_information"].notna().mean()), 4),
                                      float(cm["newness_available_share"]))}
    off = {k: v for k, v in x.items() if abs(float(v[0]) - float(v[1])) > max(1.0, 0.02 * abs(float(v[1])))}
    if off:
        raise SystemExit(f"ABORT: the frame and {cen} disagree on {off} as (frame, census) - one reader with one "
                         f"rule set, so a definition changed in only one of them. No artefact was written.")
    dest_s = W.OUT / "EXP0197_wave9_step_features.csv.gz"
    dest_t = W.OUT / "EXP0197_wave9_rollout_features.csv.gz"
    S.to_csv(dest_s, compression="gzip", index=False, encoding="utf-8")
    T.to_csv(dest_t, compression="gzip", index=False, encoding="utf-8")
    art = {"exp_id": EXP, "corpus": "the same 12-file, seeded, content-deduplicated rollout draw wave 6 measured",
           "seed": SEED, "files_read": picks, "rows_in_files": rows_in_files,
           "duplicate_rollout_rows_dropped_before_sampling": dupes, "rollouts_drawn": drawn,
           "rollouts_measured": int(len(T)), "steps_measured": int(len(S)),
           "instances": int(T["instance_id"].nunique()), "cluster_unit": TD9.COMMON["sample"]["cluster_unit"],
           "census_artefact": cen, "census_cross_check": {k: [v[0], v[1]] for k, v in x.items()},
           "cross_check_verdict": "every shared aggregate reproduced",
           "newness_available_share_frame": round(float(T["newness_mean"].notna().mean()), 4),
           "submitted_rollouts": int(T["submitted"].sum()),
           "submitted_share": round(float(T["submitted"].mean()), 4),
           "mean_steps": round(float(T["n_steps"].mean()), 2), "median_steps": float(T["n_steps"].median()),
           "steps_without_observation_total": int(S["steps_without_observation"].sum()),
           "steps_without_observation_share": round(float(S["steps_without_observation"].mean()), 4),
           "rollouts_with_a_failure": int((T["failures"] > 0).sum()),
           "rollouts_changing_at_lag_1": int(T["changed_at_lag_1"].sum()),
           "mean_switch_rate": round(float(T["switch_rate"].mean()), 4),
           "mean_newness": round(float(T["newness_mean"].mean()), 4),
           "frames": [dest_s.name, dest_t.name], "started_at": W.now(),
           "wallclock_sec": round(time.time() - t0, 1), "invocation": " ".join([sys.executable] + sys.argv),
           "run_cost": W.run_cost_row(EXP, t0, int(len(S)), int(S.shape[1]), "wave-9 step frame")}
    dest = W.write_raw(EXP, "wave9_step_matrix", art)
    print(json.dumps({k: v for k, v in art.items() if k not in ("files_read", "census_cross_check")},
                     indent=1, ensure_ascii=False, default=str)[:1300])
    print(f"\n{EXP}: wrote {dest_s.name} ({len(S)} steps), {dest_t.name} ({len(T)} rollouts) and {dest.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
