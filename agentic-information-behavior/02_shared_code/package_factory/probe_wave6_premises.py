"""EXP-0172: the wave-6 premise census - does SWE-ZERO-12M carry a step-level search process at all?

Wave 6 measures the *economics of an agent's search*: whether search depth matches the complexity of the need
(T155), whether the information visible at a step predicts the next choice (T157), whether search persists after its
marginal information gain has fallen (T158), what switching between tool families costs the quality of exploration
(T168), how much the first action determines the rest of the path (T170), and when repetition becomes rumination
(T174). Every one of those needs a trajectory whose steps are recoverable as an action, an observation, and an order -
which is not the same thing as a corpus that has messages in it. EXP-0027/29/30 measured what the eight releases
carry in general, and this census measures the one thing they could not answer: whether the command an assistant
issued, the output that came back, and the outcome label of the run are each recoverable *per step*, and how many
trajectories reach the cell a design needs.

Nothing here computes an association. Outcome labels are counted for availability only - how many distinct values
exist and how many trajectories sit in the smallest of them - because a design whose dependent variable has one
value is not thin, it is untestable, and that is a premise fact rather than a result.

The sample rule is frozen before the first row is opened: 12 of the 1,230 parquet files, drawn with `seed 42`, every
row of each file read, so a file-level draw is the unit of sampling and `instance_id` is the unit of clustering (a
task is rolled out many times, and rollouts of the same task are not independent observations).

    python 02_shared_code/package_factory/probe_wave6_premises.py [--files 12]
"""
from __future__ import annotations

import argparse
import collections
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

EXP = "EXP-0172"
SEED = 42
CORPUS = W.ROOT.parent / "MATLABINTOKEN" / "datasets" / "AlienKevin" / "SWE-ZERO-12M-trajectories" / "data"
N_FILES = 12                                                     # frozen: the file is the sampling unit
STOP = set("the a an of and or to in on for with is are was were be it this that i you we they my your their "
           "will would can could should there here from as at by not no all any".split())

# ------------------------------------------------------------------ the instruments, written before any row was read
COMMAND_BLOCK = re.compile(r"```(?:bash|sh|shell)?\s*\n(.*?)```", re.S)
OBS_START = re.compile(r"^\s*(?:Observation|Output|Result)\s*:?\s*", re.I)
FAIL_MARKERS = ["no such file", "not found", "permission denied", "command not found", "traceback", "error:",
                "failed", "cannot", "unable to", "exit code", "does not exist", "unrecognized", "invalid",
                "exception", "timed out", "segfault", "core dumped"]
SUCCESS_MARKERS = ["passed", "ok", "succeeded", "test suite", "all tests", "build succeeded", "resolved"]
# The command family is the first token of the command line, through this table. Anything the table does not name is
# `other`, which is reported rather than folded into a family that fits.
FAMILY = {
 "search_content": ["grep", "rg", "ag", "ack", "fgrep", "egrep", "zgrep"],
 "search_name": ["find", "locate", "fd"],
 "read_file": ["cat", "head", "tail", "less", "more", "sed", "awk", "nl", "bat", "cut", "tac"],
 "list": ["ls", "tree", "du", "stat", "file"],
 "edit": ["sed", "awk", "patch", "tee", "printf", "echo"],
 "run_python": ["python", "python3", "pip", "pip3", "pytest", "poetry", "uv", "conda"],
 "run_shell": ["bash", "sh", "zsh", "source", "export", "cd", "make", "cmake", "cargo", "npm", "yarn", "node"],
 "version_control": ["git", "svn", "hg"],
 "write_file": ["touch", "mkdir", "rm", "cp", "mv", "ln", "install"],
 "inspect_env": ["env", "printenv", "which", "whereis", "type", "pwd", "ps", "df", "uname", "man", "help"],
 "network": ["curl", "wget", "http", "ping"],
}
FAM_LOOKUP = {c: f for f, cs in FAMILY.items() for c in cs}
EXIT_LABELS = ("resolved", "incomplete", "error", "timeout", "patch_breaks", "no_patches", "success", "failure")


def words(s) -> set:
    return {w for w in re.findall(r"[a-z0-9_./:-]{3,}", str(s).lower()) if w not in STOP}


def family_of(cmd: str) -> str:
    """The first executable name on the command line, looked up in the frozen table.

    Pipes and chains are read left to right: `grep x | wc -l` is a content search, because the step's information
    action is the first one. The alternative (labelling by the last stage) would call `find . | head` a listing.
    """
    for tok in re.split(r"[|;&\n]+", str(cmd)):
        for w in str(tok).strip().split():
            w = w.strip("()[]{}\"'`$")
            if not w or w.startswith("-"):
                continue
            base = w.split("/")[-1]
            if base in FAM_LOOKUP:
                return FAM_LOOKUP[base]
            if re.fullmatch(r"[a-z][a-z0-9_.-]*", base):
                return "other"
    return "unparsed"


GATES = {   # rule, threshold, and the topic(s) the sentence scopes - all frozen before any row was opened
 "G1_trajectory_rows_recoverable": {
     "rule": ">= 0.95 of sampled trajectory rows yield at least one assistant message whose text is non-empty "
             "(wave 6's subject is the assistant's own step text)", "threshold": 0.95, "scope": "design",
     "blocks": ["T155", "T157", "T158", "T168", "T170", "T174"]},
 "G2_command_block_parseable": {
     "rule": ">= 0.80 of assistant messages that carry a fenced code block yield a command that `family_of` can name "
             "(the action a step took has to be recoverable, not inferred)", "threshold": 0.80, "scope": "design",
     "blocks": ["T155", "T157", "T158", "T168", "T170", "T174"]},
 "G3_outcome_label_multilevel": {
     "rule": "`exit_status` takes >= 2 distinct values and its rarest value carries >= 200 trajectories, else the "
             "wave has no outcome to condition on (T155, T170)", "threshold": 200, "scope": "design",
     "blocks": ["T155", "T170"]},
 "G4_steps_per_trajectory": {
     "rule": ">= 0.80 of trajectories carry >= 3 assistant steps, else a per-step design has no within-trajectory "
             "variation to measure (T157, T158, T168, T174)", "threshold": 0.80, "scope": "design",
     "blocks": ["T157", "T158", "T168", "T174"]},
 "G5_rollouts_per_instance": {
     "rule": ">= 200 instances carry >= 2 trajectories, which is the only place a within-task comparison of search "
             "depth against need complexity can come from (T155)", "threshold": 200, "scope": "H1",
     "blocks": ["T155"]},
 "G6_repeated_command_trajectories": {
     "rule": ">= 200 trajectories contain an exact repeated command, else T174's rumination contrast has no subject",
     "threshold": 200, "scope": "H1", "blocks": ["T174"]},
 "G7_multi_family_trajectories": {
     "rule": ">= 200 trajectories use >= 3 distinct command families, which is what a switching-cost design needs to "
             "have a switch in (T168)", "threshold": 200, "scope": "H1", "blocks": ["T168"]},
 "G8_first_family_varies_across_instances": {
     "rule": "within instances that have >= 2 rollouts, >= 200 instances show two rollouts with different first "
             "command families - without that spread the first action is a task property, not a choice (T170)",
     "threshold": 200, "scope": "H1", "blocks": ["T170"]},
 "G9_observation_text_computable": {
     "rule": ">= 0.80 of steps after the first are followed by an observation whose text is non-empty, because "
             "marginal information gain and scent are both computed against it (T157, T158)", "threshold": 0.80,
     "scope": "design", "blocks": ["T157", "T158"]},
 "G10_need_complexity_proxy": {
     "rule": ">= 200 instances carry an issue text with >= 40 content words and a repository field, the two readings "
             "of need complexity the freeze can compute without a model (T155)", "threshold": 200, "scope": "H1",
     "blocks": ["T155"]},
 "G11_failure_marker_present": {
     "rule": ">= 0.20 of observations carry a failure marker, else 'after a failed step' is an empty cell and the "
             "persistence design has no failure to persist past (T158)", "threshold": 0.20, "scope": "H2",
     "blocks": ["T158"]},
 "G12_cluster_count": {
     "rule": ">= 30 distinct instance_ids in the sample, the floor below which a cluster-robust interval does not "
             "exist (every design in the wave)", "threshold": 30, "scope": "design",
     "blocks": ["T155", "T157", "T158", "T168", "T170", "T174"]},
}


def selftest() -> int:
    """The instruments are proved on a hand-built trajectory before any release row is read."""
    msgs = [{"role": "system", "content": "solve the issue"},
            {"role": "user", "content": "Please solve this issue in the repository a/b. ## Issue Title: fix the "
                                        "test **Title** steps broken; run the suite."},
            {"role": "assistant", "content": "THOUGHT: look at the tree.\n```bash\nfind . -name '*.py' | head\n```"},
            {"role": "user", "content": "Observation: ./a/test.py\n./b/main.py"},
            {"role": "assistant", "content": "```bash\ngrep -r injection .\n```"},
            {"role": "user", "content": "Observation: no such file or directory"},
            {"role": "assistant", "content": "```bash\ncat ./a/test.py\n```"},
            {"role": "user", "content": "Observation: import pytest\n"},
            {"role": "assistant", "content": "```bash\nfind . -name '*.py' | head\n```"},
            {"role": "user", "content": "Observation: ./a/test.py\n./b/main.py"}]
    fams = []
    for m in msgs:
        if m["role"] != "assistant":
            continue
        b = COMMAND_BLOCK.search(m["content"])
        assert b, "the fenced command block must be found"
        fams.append(family_of(b.group(1)))
    assert fams == ["search_name", "search_content", "read_file", "search_name"], fams
    assert OBS_START.match("Observation: ./a/test.py") and not OBS_START.match("please solve this")
    assert any(x in "no such file or directory" for x in FAIL_MARKERS)
    ws = words("the test steps broken run the suite")
    assert "test" in ws and "the" not in ws, ws
    print("SELFTEST OK: command blocks, families, observation prefixes, failure markers and words all land")
    return 0


def walk_trajectory(row: dict) -> dict:
    """Per-trajectory structure counts only: how many steps, families, repeats, and the premise cells it fills."""
    msgs = row.get("messages") or []
    steps = []                                      # (family, command, obs_text) per assistant step with a command
    seen_cmds = set()
    obs_after = obs_with_failure = 0
    first_family = ""
    for i, m in enumerate(msgs):
        if str(m.get("role")) != "assistant":
            continue
        b = COMMAND_BLOCK.search(str(m.get("content") or ""))
        if not b:
            continue
        cmd = re.sub(r"\s+", " ", b.group(1)).strip()
        if not cmd:
            continue
        fam = family_of(cmd)
        nxt = msgs[i + 1] if i + 1 < len(msgs) else None
        obs = ""
        if nxt is not None and str(nxt.get("role")) == "user" and OBS_START.match(str(nxt.get("content") or "")):
            obs = OBS_START.sub("", str(nxt.get("content") or "")).strip()
            obs_after += 1
            if any(x in obs.lower() for x in FAIL_MARKERS):
                obs_with_failure += 1
        steps.append((fam, cmd, bool(obs), cmd in seen_cmds))
        seen_cmds.add(cmd)
        if not first_family:
            first_family = fam
    issue = next((str(m.get("content") or "") for m in msgs if str(m.get("role")) == "user"), "")
    fams = [s[0] for s in steps]
    return {"n_steps": len(steps),
            "families": [f for f in fams if f != "unparsed"],
            "n_unparsed": sum(1 for f in fams if f == "unparsed"),
            "distinct_families": len(set(fams) - {"unparsed"}),
            "exact_repeats": int(sum(1 for s in steps if s[3])),
            "switches": int(sum(1 for a, b in zip(fams, fams[1:]) if a != b and "unparsed" not in (a, b))),
            "first_family": first_family,
            "obs_after_steps": obs_after, "obs_failure": obs_with_failure,
            "issue_words": len(words(issue)),
            "outcome": str(row.get("exit_status") or ""),
            "duration": str(row.get("duration_sec") or ""),
            "assistant_msgs": sum(1 for m in msgs if str(m.get("role")) == "assistant"),
            "any_assistant_text": int(any(str(m.get("content") or "").strip() for m in msgs
                                          if str(m.get("role")) == "assistant")),
            "repo": str(row.get("repo") or ""), "instance_id": str(row.get("instance_id") or "")}


def measure(files: list) -> dict:
    rows, per_instance = [], collections.defaultdict(list)
    t0 = time.time()
    for k, f in enumerate(files):
        pf = pq.ParquetFile(f)
        for batch in pf.iter_batches(batch_size=2000, columns=["instance_id", "messages", "exit_status",
                                                               "duration_sec", "repo"]):
            for rec in batch.to_pylist():
                r = walk_trajectory(rec)
                rows.append(r)
                per_instance[r["instance_id"]].append(r)
        print(f"  census: file {k + 1}/{len(files)} -> {len(rows)} trajectories", flush=True)
    D = pd.DataFrame(rows)
    n = int(len(D))
    steps = int(D["n_steps"].sum())
    parsed = int((D["n_steps"] - D["n_unparsed"]).sum())
    roll = {i: len(v) for i, v in per_instance.items()}
    multi_roll = {i: v for i, v in per_instance.items() if len(v) >= 2}
    diff_first = sum(1 for v in multi_roll.values() if len({x["first_family"] for x in v}) >= 2)
    outcomes = collections.Counter(D["outcome"])
    rarest = min(outcomes.values()) if len(outcomes) > 1 else 0
    multi = D[D["n_steps"] >= 3]
    obs_ok = float((multi["obs_after_steps"] / multi["n_steps"] >= 0.8).mean()) if len(multi) else 0.0
    fam_steps = collections.Counter(f for v in D["families"] for f in v)
    n_fam_steps = sum(fam_steps.values())
    return {"corpus": CORPUS.name, "files_read": [f.name for f in files], "trajectories": n,
            "instances": len(roll), "assistant_steps": steps, "parsed_steps": parsed,
            "median_steps_per_trajectory": float(D["n_steps"].median()),
            "share_ge3_steps": round(float((D["n_steps"] >= 3).mean()), 4),
            "any_assistant_text_share": round(float(D["any_assistant_text"].mean()), 4),
            "command_parse_share": round(parsed / max(1, steps), 4),
            "unparsed_steps": int(D["n_unparsed"].sum()),
            "outcome_levels": {k: int(v) for k, v in outcomes.items()},
            "outcome_named_levels": int(sum(1 for k in outcomes if k in EXIT_LABELS)),
            "rarest_outcome_trajectories": int(rarest),
            "instances_with_2plus_rollouts": len(multi_roll),
            "instances_with_differing_first_family": int(diff_first),
            "trajectories_with_exact_repeat": int((D["exact_repeats"] >= 1).sum()),
            "trajectories_with_3plus_families": int((D["distinct_families"] >= 3).sum()),
            "mean_switches_per_trajectory": round(float(D["switches"].mean()), 4),
            "first_family_share": {str(k): round(float(v), 4) for k, v in
                                   D["first_family"].value_counts(normalize=True).head(12).items()},
            "family_share_of_steps": {str(k): round(v / max(1, n_fam_steps), 4) for k, v in fam_steps.most_common()},
            "obs_after_first_step_share_of_multi_step_rows": round(obs_ok, 4),
            "failure_marker_share_of_observation_bearing_steps":
                round(float(D["obs_failure"].sum() / max(1, D["obs_after_steps"].sum())), 4),
            "issue_ge40_words_instances": int(sum(1 for v in per_instance.values()
                                                  if max(x["issue_words"] for x in v) >= 40)),
            "repo_field_present_share": round(float((D["repo"] != "").mean()), 4),
            "duration_present_share": round(float((D["duration"].astype(str) != "").mean()), 4),
            "wallclock_sec": round(time.time() - t0, 1), "seed": SEED}


def apply_gates(m: dict) -> dict:
    checks = {
     "G1_trajectory_rows_recoverable": m["any_assistant_text_share"],
     "G2_command_block_parseable": m["command_parse_share"],
     "G3_outcome_label_multilevel": m["rarest_outcome_trajectories"],
     "G4_steps_per_trajectory": m["share_ge3_steps"],
     "G5_rollouts_per_instance": m["instances_with_2plus_rollouts"],
     "G6_repeated_command_trajectories": m["trajectories_with_exact_repeat"],
     "G7_multi_family_trajectories": m["trajectories_with_3plus_families"],
     "G8_first_family_varies_across_instances": m["instances_with_differing_first_family"],
     "G9_observation_text_computable": m["obs_after_first_step_share_of_multi_step_rows"],
     "G10_need_complexity_proxy": m["issue_ge40_words_instances"],
     "G11_failure_marker_present": m["failure_marker_share_of_observation_bearing_steps"],
     "G12_cluster_count": m["instances"],
    }
    fired, scopes = [], {}
    for g, v in checks.items():
        th = GATES[g]["threshold"]
        fires = (v is None) or (float(v) < float(th))
        GATES[g]["measured"] = round(float(v), 4) if v is not None else None
        GATES[g]["fires"] = bool(fires)
        if not GATES[g].get("blocks"):
            raise SystemExit(f"ABORT: gate {g} has an empty `blocks` list, so a fired gate would stop nothing and "
                             f"the record would claim a scope the census cannot show")
        if fires:
            fired.append(g)
        scopes[g] = {"scope": GATES[g]["scope"], "blocks": GATES[g]["blocks"],
                     "measured": GATES[g]["measured"], "fires": bool(fires)}
    stopped = []
    for g in fired:
        if GATES[g]["scope"] == "design":
            stopped += [x for x in GATES[g]["blocks"] if x not in stopped]
    return {"blocked_gates": fired, "blocked_whole_design": stopped,
            "claim_limited": {g: GATES[g]["scope"] for g in fired if GATES[g]["scope"] != "design"},
            "gate_scopes": scopes, "gate_rules": {k: GATES[k]["rule"] for k in GATES},
            "note": "a fired gate stops exactly what its frozen sentence scopes; the measurement it fired on is "
                    "printed with it, so a thin cell is distinguishable from an instrument that could not read "
                    "the field"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", type=int, default=N_FILES)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if a.selftest:
        return selftest()
    t0 = time.time()
    selftest()
    if not CORPUS.is_dir():
        raise SystemExit(f"ABORT: {CORPUS} is not a directory - the census cannot measure a corpus that is absent")
    all_files = sorted(p for p in CORPUS.glob("*.parquet"))
    if not all_files:
        raise SystemExit(f"ABORT: no parquet under {CORPUS}")
    picks = sorted(random.Random(SEED).sample(all_files, min(a.files, len(all_files))))
    m = measure(picks)
    verdict = apply_gates(m)
    out = {"exp_id": EXP,
           "measured": m,
           "gates": {g: {"measured": s["measured"], "fires": s["fires"], "scope": s["scope"],
                         "blocks": s["blocks"]} for g, s in verdict["gate_scopes"].items()},
           "verdict": {k: verdict[k] for k in ("blocked_gates", "blocked_whole_design", "claim_limited")},
           "gate_rules": verdict["gate_rules"], "files_requested": a.files, "files_available": len(all_files),
           "rows_per_file_note": "every row of each drawn file, so the file is the sampling unit and "
                                 "instance_id the cluster",
           "started_at": W.now(), "invocation": " ".join([sys.executable] + sys.argv),
           "wallclock_sec": round(time.time() - t0, 1)}
    dest = W.write_raw(EXP, "wave6_premise_census", out)
    print(json.dumps({"measured": {k: v for k, v in m.items() if k != "first_family_share"},
                      "gates": {k: (v["measured"], v["fires"]) for k, v in verdict["gate_scopes"].items()},
                      "stopped": verdict["blocked_whole_design"],
                      "claim_limited": verdict["claim_limited"]}, indent=1, ensure_ascii=False, default=str)[:2600])
    print(f"{EXP}: wrote {dest.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
