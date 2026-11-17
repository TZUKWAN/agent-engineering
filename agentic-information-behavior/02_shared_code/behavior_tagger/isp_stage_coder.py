"""EXP-0026 (P002 pilot): does a frozen, non-LLM rule codex turn agent trajectories into stages at all?

Implements papers/P002_isp_stage_measurement/protocol_freeze.md sections 1-3 literally. The codex below was
written into that freeze file BEFORE this script ran, so the pilot is a survival test and not a tuning loop: if
RQ1 fails, T008 is killed rather than re-scoped.

Reported per the freeze:
  RQ1 codability  - share of assistant turns receiving exactly one stage, share uncodable, largest stage share;
  RQ2 (indicative)- per-trajectory log-likelihood of a first-order Markov model versus zero-order versus the
                    position-only predictor B4, with a cluster bootstrap over instance_id. The decision-grade
                    version fits on dev and evaluates on the report split in the main experiment; here it only
                    tells us whether the question is answerable at all;
  RQ3 censoring   - stage shares and last-stage distribution after truncating each trajectory to 5 / 10 / 15
                    observed steps, because 50% of trajectories sit exactly at the 32-message cap.

    python isp_stage_coder.py --pilot

Writes results_raw/EXP0026_p002_stage_pilot_*.json and results_processed/EXP0026_stage_*.csv.
"""

from __future__ import annotations

import glob
import hashlib
import json
import random
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(r"G:/刘俊琦/AGENT ENGINEERING/MATLABINTOKEN/datasets/AlienKevin/SWE-ZERO-12M-trajectories")
OUT_RAW = ROOT / "results_raw"
OUT_PROC = ROOT / "results_processed"
SEED = 42
PILOT_SHARDS, ROWS_PER_SHARD = 20, 1000

# ---- the frozen codex (priority order, first match wins; see protocol_freeze.md section 2) --------
RULES = [
    ("end", re.compile(r"\b(done|final answer|submit|resolved|fixed the issue|all tests pass)\b", re.I),
     re.compile(r"^\s*$")),
    ("verify", re.compile(r"^\s*(pytest|py\.test|python -m pytest|tox|nosetests|make test|npm test|"
                          r"python -m unittest|./run_tests|curl .*issue)\b", re.I),
     re.compile(r"\b(test|tests|reproduce|expected output|assert)\b", re.I)),
    ("documentation", re.compile(r"^\s*(patch|sed -i|cat *>|printf *>|tee|echo *>|python - <<|"
                                 r"git apply|cp .* \.\.\.)", re.I),
     re.compile(r"\b(write|create|edit|modify|append|replace|add .* file|update .* file)\b", re.I)),
    ("extraction", re.compile(r"^\s*(cat|head|tail|sed -n|grep|rg|less|awk|git (show|diff|log)|wc|jq)\b", re.I),
     re.compile(r"\b(read|look at|check the contents|inspect|see what|find out|show me|extract)\b", re.I)),
    ("exploration", re.compile(r"^\s*(ls|find|tree|pwd|du|which|locate|git status|git branch|grep -r|"
                               r"rg .*--files|echo \*|cd .*&& *ls)\b", re.I),
     re.compile(r"\b(explore|structure|where is|which files|layout|understand how|orient|overview|list)\b", re.I)),
    ("system", re.compile(r"^\s*(pip|apt|conda|npm install|export|mkdir|rm |mv |chmod|source |virtualenv|"
                          r"python -m pip|set )\b", re.I),
     re.compile(r"\b(install|set up|environment|dependency|configure)\b", re.I)),
    ("clarification", re.compile(r"^\s*$"),
     re.compile(r"\b(first,? i need to|i should|my plan|let me (start|think|plan)|the issue asks|"
                r"i need to understand|hypothesis)\b", re.I)),
]
LABELS = [r[0] for r in RULES] + ["uncodable"]

CMD_RE = re.compile(r"```(?:bash|sh|shell)?\s*(.+?)```", re.S)
ERR_RE = re.compile(r"(traceback|error|no such|not found|permission denied|failed|non-zero|"
                    r"exception|usage:)", re.I)


def split_turn(content: str) -> tuple[str, str]:
    """Return (thought text, first command) of one assistant turn, using the corpus template."""
    m = CMD_RE.search(content)
    cmd = ""
    thought = content
    if m:
        cmd = m.group(1).strip().split("\n")[0][:400]
        thought = content[:m.start()]
    return thought, cmd


def code_turn(thought: str, cmd: str) -> str:
    for label, cmd_re, thought_re in RULES:
        if (cmd and cmd_re.search(cmd)) or (thought_re.pattern != r"^\s*$" and thought_re.search(thought)):
            if cmd or label == "clarification":
                return label
    return "uncodable"


def observation_kind(text: str) -> str:
    t = str(text or "").strip()
    if not t or t.lower().startswith("observation: *"):
        return "empty"
    return "error-shaped" if ERR_RE.search(t[:600]) else "informative"


def load_pilot() -> pd.DataFrame:
    files = [f for f in sorted(glob.glob(str(DATA / "**/*.parquet"), recursive=True)) if ".cache" not in f]
    picks = sorted(random.Random(SEED).sample(range(len(files)), PILOT_SHARDS))
    rows = []
    for i in picks:
        t = pq.read_table(files[i], columns=["instance_id", "repo", "messages", "exit_status"])
        for r in t.slice(0, ROWS_PER_SHARD).to_pylist():
            msgs = r["messages"]
            turns = []
            for j, m in enumerate(msgs):
                if m["role"] != "assistant":
                    continue
                thought, cmd = split_turn(str(m["content"]))
                obs = msgs[j + 1]["content"] if j + 1 < len(msgs) else ""
                turns.append((code_turn(thought, cmd), observation_kind(obs), cmd))
            if turns:
                rows.append({"instance_id": r["instance_id"], "repo": r["repo"],
                             "exit_status": r["exit_status"],
                             "stages": [t[0] for t in turns], "obs": [t[1] for t in turns],
                             "cmds": [t[2] for t in turns]})
    return pd.DataFrame(rows)


def ll_per_turn(seqs, order: int) -> float:
    """Mean log2-likelihood PER TURN under a memoryless (0) or first-order (1) Markov model (add-1 smoothing).

    Units matter: the pilot must compare zero-order, first-order and the position-only baseline B4 on the same
    scale, otherwise a per-trajectory sum beats a per-turn mean by construction. Everything here is per turn.
    """
    if order == 0:
        c = Counter(s for seq in seqs for s in seq)
        tot = sum(c.values())
        return float(np.mean([np.mean([np.log2((c.get(s, 0) + 1.0) / (tot + len(LABELS))) for s in seq])
                              for seq in seqs if seq]))
    nxt, ctx = Counter(), Counter()
    for seq in seqs:
        for a, b in zip(seq, seq[1:]):
            nxt[(a, b)] += 1
            ctx[a] += 1
    return float(np.mean([np.mean([np.log2((nxt[(a, b)] + 1.0) / (ctx[a] + len(LABELS)))
                                    for a, b in zip(seq, seq[1:])])
                          for seq in seqs if len(seq) > 1]))


def position_only_per_turn(seqs) -> float:
    """B4: predict the stage from the turn index alone - the awkward baseline a templatised corpus invites."""
    priors = defaultdict(Counter)
    for seq in seqs:
        for i, s in enumerate(seq):
            priors[i][s] += 1
    per = []
    for seq in seqs:
        vals = []
        for i, s in enumerate(seq):
            d, tot = priors[i], sum(priors[i].values())
            vals.append(np.log2((d.get(s, 0) + 1.0) / (tot + len(LABELS))))
        per.append(np.mean(vals))
    return float(np.mean(per))


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    df = load_pilot()
    n_turns = int(sum(len(s) for s in df.stages))
    flat = [s for seq in df.stages for s in seq]
    share = {k: round(v / max(1, n_turns), 4) for k, v in Counter(flat).most_common()}
    coded = 1 - share.get("uncodable", 0.0)
    largest = max((v for k, v in share.items() if k != "uncodable"), default=0.0)
    obs_share = {k: round(v / max(1, n_turns), 4) for k, v in
                 Counter(o for seq in df.obs for o in seq).most_common()}
    loop = round(float(np.mean([len(set(c)) < len(c) for c in df.cmds])), 4)

    seqs = df.stages.tolist()
    ll0, ll1, b4 = ll_per_turn(seqs, 0), ll_per_turn(seqs, 1), position_only_per_turn(seqs)

    rng = np.random.default_rng(SEED)
    inst = df.instance_id.unique()
    boots = []
    for _ in range(400):
        take = np.isin(df.instance_id.values, rng.choice(inst, size=len(inst), replace=True))
        s2 = [seq for seq, keep in zip(seqs, take) if keep]
        if len(s2) > 50:
            boots.append(ll_per_turn(s2, 1) - ll_per_turn(s2, 0))
    ci = [round(float(np.percentile(boots, q)), 3) for q in (2.5, 97.5)] if boots else None

    censor = {}
    for cap in (5, 10, 15):
        fl = [s for seq in df.stages for s in seq[:cap]]
        censor[f"truncate_at_{cap}"] = {k: round(v / max(1, len(fl)), 4) for k, v in Counter(fl).most_common(4)}
        censor[f"truncate_at_{cap}"]["_largest"] = max(
            (v / max(1, len(fl)) for k, v in Counter(fl).items() if k != "uncodable"), default=0)
        censor[f"truncate_at_{cap}"]["_n_turns"] = len(fl)
    last_stage = {k: round(v / len(df), 4) for k, v in Counter(df.stages.apply(lambda s: s[-1])).most_common()}
    # Round 2: the gain per trajectory has to be a measured quantity, not a reader-side multiplication. The pilot's
    # own report quotes "1.367 bits/trajectory" for the B4 contrast against a frozen 2-bit threshold, and that
    # number is the product of the full-precision per-turn delta and the full-precision mean trajectory length -
    # but the record published only both factors rounded (0.0916 and 14.918), whose product is 1.366. A document
    # can therefore not reproduce its own headline figure from the file that carries it, which is exactly what a
    # survivorship gate should not rest on. The products are computed here, once, at full precision.
    turns_per_traj = float(np.mean([len(s) for s in df.stages]))

    res = {"exp_id": "EXP-0026", "paper_id": "P002", "stage": "pilot_survival_test", "seed": SEED,
           "protocol": "papers/P002_isp_stage_measurement/protocol_freeze.md sections 1-3",
           "corpus": {"rows": int(len(df)), "distinct_instances": int(df.instance_id.nunique()),
                      "distinct_repos": int(df.repo.nunique()), "assistant_turns": n_turns,
                      "mean_turns_per_trajectory": round(float(np.mean([len(s) for s in df.stages])), 3),
                      "turns_p50": int(np.percentile([len(s) for s in df.stages], 50)),
                      "exit_status_counts": {k: int(v) for k, v in df.exit_status.value_counts().items()},
                      "shards_read": PILOT_SHARDS, "rows_per_shard": ROWS_PER_SHARD},
           "RQ1_codability": {"share_single_stage": round(coded, 4), "share_uncodable": share.get("uncodable", 0),
                              "largest_coded_stage_share": round(largest, 4), "stage_shares": share,
                              "observation_outcome_shares": obs_share,
                              "trajectories_with_repeated_command": loop,
                              "survival_rule": ">=0.70 coded, <=0.15 uncodable, no stage >0.60 of coded turns",
                              "survives": bool(coded >= 0.70 and share.get("uncodable", 0) <= 0.15
                                               and largest <= 0.60)},
           "units": "log2 likelihood per turn; identical scale for all three models",
           "RQ2_indicative": {"mean_ll_per_turn_zero_order": round(ll0, 4), "mean_ll_per_turn_first_order": round(ll1, 4),
                               "mean_ll_per_turn_position_only_B4": round(b4, 4),
                               "delta_first_minus_zero": round(ll1 - ll0, 4),
                               "delta_first_minus_position_only": round(ll1 - b4, 4),
                               "delta_first_minus_zero_bits_per_trajectory": round((ll1 - ll0) * turns_per_traj, 6),
                               "delta_first_minus_position_only_bits_per_trajectory": round((ll1 - b4)
                                                                                            * turns_per_traj, 6),
                               "turns_per_trajectory_used_for_the_scale": round(turns_per_traj, 6),
                               "scale_note": "the per-trajectory figures multiply the FULL-PRECISION per-turn "
                                             "difference by the full-precision mean trajectory length; the rounded "
                                             "pair printed above and in `corpus` reproduces them only to ~0.001",
                               "ci95_cluster_bootstrap_delta_first_minus_zero": ci,
                               "bootstraps": len(boots),
                               "note": "indicative only: the decision-grade fit uses the dev/report instance "
                                       "split in the main experiment; no tuning of the codex happened here"},
           "RQ3_censoring_sensitivity": censor,
           "last_observed_stage_share": last_stage,
           "wallclock_sec": round(time.time() - t0, 1),
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t0)),
           "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    res["decision"] = ("PROCEED to main experiment" if res["RQ1_codability"]["survives"]
                       else "KILL T008: rule codex is not a measurement instrument")
    OUT_RAW.mkdir(exist_ok=True)
    out = OUT_RAW / f"EXP0026_p002_stage_pilot_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    pd.DataFrame({"instance_id": df.instance_id, "repo": df.repo, "exit_status": df.exit_status,
                  "n_steps": df.stages.apply(len), "stages": df.stages.apply(lambda s: "|".join(s)),
                  "observations": df.obs.apply(lambda s: "|".join(s))}).to_csv(
        OUT_PROC / "EXP0026_pilot_coded_turns.csv", index=False)
    print(json.dumps({k: res[k] for k in ("corpus", "RQ1_codability", "RQ2_indicative", "decision")},
                     indent=1, ensure_ascii=False)[:2600])
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
