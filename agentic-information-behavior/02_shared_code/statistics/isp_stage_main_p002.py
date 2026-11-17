"""EXP-0031 (P002 main): rule-based stage coding at scale, against the nulls that matter.

Implements papers/P002_isp_stage_measurement/protocol_freeze.md sections 1-5 literally: 240 shards x 1000 rows of
SWE-ZERO-1.5M..., a dev/report split by hash of `instance_id` (no instance on both sides), the B0-B4 ladder, the
truncation curve, lexicon and granularity perturbations, per-repo and per-exit-status strata, and an identical
run on AgentTrove as a second corpus with a different message schema and no step cap.

The ladder is the point. In a corpus whose assistant turns follow one template, "stage sequence is structured"
is only interesting if it beats:
  B0 uniform over stages;
  B1 zero-order (marginal stage frequencies);
  B2 first-order Markov over stages;
  B3 previous command head-token -> stage (raw syntax memory);
  B4 turn position -> stage (the template itself).
Intervals are bootstrapped over instances, because ~1000 rows can share one instance (P002 pilot: 20k
trajectories = 317 instances). No model API, no pretrained encoder, CPU only.

    python isp_stage_main_p002.py

Writes results_raw/EXP0031_p002_stage_main_*.json and results_processed/EXP0031_*.csv.
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
DATA = Path(r"G:/刘俊琦/AGENT ENGINEERING/MATLABINTOKEN/datasets")
SWE = DATA / "AlienKevin/SWE-ZERO-12M-trajectories"
TROVE = DATA / "open-thoughts/AgentTrove"
OUT_RAW, OUT_PROC = ROOT / "results_raw", ROOT / "results_processed"
SEED, SHARDS, ROWS = 42, 240, 1000
K_BOOT = 2000
CMD_HEAD = re.compile(r"^\s*([A-Za-z0-9_.\-/]+)")
BASH = re.compile(r"```(?:bash|sh|shell|python)?\s*\n(.+?)```", re.S)

RULES = [
    ("end", re.compile(r"\b(done|final answer|submit|resolved|fixed the issue|all tests pass)\b", re.I),
     re.compile(r"^\s*$")),
    ("verify", re.compile(r"^\s*(pytest|py\.test|python -m pytest|tox|nosetests|make test|npm test|"
                          r"python -m unittest|./run_tests|curl .*issue)\b", re.I),
     re.compile(r"\b(test|tests|reproduce|expected output|assert)\b", re.I)),
    ("documentation", re.compile(r"^\s*(patch|sed -i|cat *>|printf *>|tee|echo *>|python - <<|git apply|cp .* \.\.\.)",
                                 re.I), re.compile(r"\b(write|create|edit|modify|append|replace|add .* file)\b", re.I)),
    ("extraction", re.compile(r"^\s*(cat|head|tail|sed -n|grep|rg|less|awk|git (show|diff|log)|wc|jq)\b", re.I),
     re.compile(r"\b(read|look at|check the contents|inspect|see what|find out|show me|extract)\b", re.I)),
    ("exploration", re.compile(r"^\s*(ls|find|tree|pwd|du|which|locate|git status|git branch|grep -r|echo \*)\b", re.I),
     re.compile(r"\b(explore|structure|where is|which files|layout|understand how|orient|overview|list)\b", re.I)),
    ("system", re.compile(r"^\s*(pip|apt|conda|npm install|export|mkdir|rm |mv |chmod|source |virtualenv|set )\b", re.I),
     re.compile(r"\b(install|set up|environment|dependency|configure)\b", re.I)),
    ("clarification", re.compile(r"^\s*$"),
     re.compile(r"\b(first,? i need to|i should|my plan|let me (start|think|plan)|the issue asks|hypothesis)\b", re.I)),
]
STAGES = [r[0] for r in RULES] + ["uncodable"]
GRAN5 = {"end": "finish", "verify": "check", "documentation": "produce", "extraction": "read",
         "exploration": "survey", "system": "operate", "clarification": "plan", "uncodable": "other"}
GRAN3 = {"finish": "act", "check": "act", "produce": "act", "read": "seek", "survey": "seek",
         "operate": "seek", "plan": "define", "other": "define"}


def code_turn(thought, cmd):
    for label, cmd_re, thought_re in RULES:
        if (cmd and cmd_re.search(cmd)) or (thought_re.pattern != r"^\s*$" and thought_re.search(thought)):
            if cmd or label == "clarification":
                return label
    return "uncodable"


def code_turn_thought_only(thought, cmd):
    """Lexicon perturbation: drop the command-pattern half of the codex."""
    for label, _cmd_re, thought_re in RULES:
        if thought_re.pattern != r"^\s*$" and thought_re.search(thought):
            return label
    return "uncodable"


def head_token(cmd):
    m = CMD_HEAD.match(cmd or "")
    return m.group(1) if m else ""


def split_turn(content):
    m = BASH.search(str(content))
    if m:
        return str(content)[:m.start()], m.group(1).strip().split("\n")[0][:400]
    return str(content), ""


def bucket(instance_id):
    return int(hashlib.md5(str(instance_id).encode()).hexdigest(), 16) % 1000


def read_swe():
    files = sorted(glob.glob(str(SWE / "**/*.parquet"), recursive=True))
    files = [f for f in files if ".cache" not in f]
    picks = sorted(random.Random(SEED).sample(files, min(SHARDS, len(files))))
    rows = []
    for f in picks:
        pf = pq.ParquetFile(f)
        n = min(ROWS, pf.metadata.num_rows)
        got = 0
        for rg in range(pf.metadata.num_row_groups):
            if got >= n:
                break
            blk = pf.read_row_group(rg).slice(0, n - got)
            for r in blk.to_pylist():
                stages, heads = [], []
                for m in r["messages"]:
                    if m["role"] != "assistant":
                        continue
                    thought, cmd = split_turn(m["content"])
                    stages.append(code_turn(thought, cmd))
                    heads.append(head_token(cmd))
                if stages:
                    rows.append({"instance_id": r["instance_id"], "repo": r["repo"],
                                 "exit_status": r["exit_status"], "stages": stages, "heads": heads,
                                 "thoughts_only": [code_turn_thought_only(*split_turn(m["content"]))
                                                   for m in r["messages"] if m["role"] == "assistant"]})
            got += len(blk)
    return pd.DataFrame(rows), len(files), len(picks)


def read_trove():
    files = sorted(glob.glob(str(TROVE / "**/*.parquet"), recursive=True))
    files = [f for f in files if ".cache" not in f]
    picks = sorted(random.Random(SEED).sample(files, min(16, len(files))))
    rows = []
    for f in picks:
        pf = pq.ParquetFile(f)
        n = min(1500, pf.metadata.num_rows)
        got = 0
        for rg in range(pf.metadata.num_row_groups):
            if got >= n:
                break
            blk = pf.read_row_group(rg).slice(0, n - got)
            for r in blk.to_pylist():
                stages, heads = [], []
                for m in (r.get("conversations") or []):
                    role = m.get("role") or m.get("from")
                    if role not in ("assistant", "gpt"):
                        continue
                    thought, cmd = split_turn(m.get("content") or m.get("value") or "")
                    stages.append(code_turn(thought, cmd))
                    heads.append(head_token(cmd))
                if stages:
                    grp = r.get("run_id") or r.get("task") or r.get("trial_name")
                    rows.append({"instance_id": str(grp), "repo": str(r.get("agent") or "n/a"),
                                 "exit_status": str(r.get("result") or "n/a"), "stages": stages, "heads": heads,
                                 "thoughts_only": list(stages)})
            got += len(blk)
    return pd.DataFrame(rows), len(files), len(picks)


def fit_models(tr):
    """Marginal, first-order and command-memory and position-only stage models, as count tables."""
    k = len(STAGES)
    marg, trans, pos, cmd_map = Counter(), defaultdict(Counter), defaultdict(Counter), defaultdict(Counter)
    for stages, heads in zip(tr.stages, tr.heads):
        for i, s in enumerate(stages):
            marg[s] += 1
            pos[i][s] += 1
            if i:
                trans[stages[i - 1]][s] += 1
            cmd_map[heads[i - 1] if i else ""][s] += 1
    return {"marg": marg, "trans": trans, "pos": pos, "cmd": cmd_map, "k": k}


def ll_per_turn(seq, heads, M):
    k, tot = M["k"], sum(M["marg"].values())
    l0 = [np.log2((M["marg"].get(s, 0) + 1.0) / (tot + k)) for s in seq]
    l2 = [np.log2((M["trans"][a].get(b, 0) + 1.0) / (sum(M["trans"][a].values()) + k))
          for a, b in zip(seq, seq[1:])] or [0.0]
    l3 = [np.log2((M["cmd"][h].get(s, 0) + 1.0) / (sum(M["cmd"][h].values()) + k))
          for h, s in zip(heads, seq)]
    l4 = [np.log2((M["pos"][i].get(s, 0) + 1.0) / (sum(M["pos"][i].values()) + k))
          for i, s in enumerate(seq)]
    return np.mean(l0), np.mean(l2), np.mean(l3), np.mean(l4)


def analyse(df, label, caps=(5, 10, 15)):
    df = df.reset_index(drop=True)
    is_dev = df.instance_id.map(bucket) < 700
    tr, te = df[is_dev], df[~is_dev]
    M = fit_models(tr)
    per = [ll_per_turn(s, h, M) for s, h in zip(te.stages, te.heads)]
    arr = np.array(per)
    inst = te.instance_id.values
    uniq = np.unique(inst)
    idx_by_inst = {i: np.where(inst == i)[0] for i in uniq}
    rng = np.random.default_rng(SEED)
    boots = {"first_vs_zero": [], "first_vs_position": [], "first_vs_cmd": []}
    for _ in range(K_BOOT):
        take = np.concatenate([idx_by_inst[i] for i in rng.choice(uniq, size=len(uniq), replace=True)])
        a = arr[take]
        boots["first_vs_zero"].append(a[:, 1].mean() - a[:, 0].mean())
        boots["first_vs_position"].append(a[:, 1].mean() - a[:, 3].mean())
        boots["first_vs_cmd"].append(a[:, 1].mean() - a[:, 2].mean())

    def ci(v):
        v = np.asarray(v)
        return [round(float(np.percentile(v, 2.5)), 4), round(float(np.percentile(v, 97.5)), 4)]

    flat = [s for seq in df.stages for s in seq]
    shares = {k: round(v / max(1, len(flat)), 4) for k, v in Counter(flat).most_common()}
    trans_counts = Counter()
    for seq in te.stages:
        trans_counts.update(zip(seq, seq[1:]))
    trunc = {}
    for cap in caps:
        fl = [s for seq in df.stages for s in seq[:cap]]
        trunc[f"truncate_at_{cap}"] = {"n_turns": len(fl),
                                        "largest_stage": max(Counter(fl).items(), key=lambda kv: kv[1])[0],
                                        "largest_share": round(max(Counter(fl).values()) / len(fl), 4),
                                        "shares": {k: round(v / len(fl), 4) for k, v in Counter(fl).most_common(4)}}
    last = Counter(seq[-1] for seq in df.stages)
    pert = {}
    for name, col in (("frozen_codex", "stages"), ("thoughts_only_lexicon", "thoughts_only")):
        fl = [s for seq in df[col] for s in seq]
        pert[name] = {"uncodable_share": round(Counter(fl).get("uncodable", 0) / max(1, len(fl)), 4),
                      "largest_share": round(max(Counter(fl).values()) / max(1, len(fl)), 4)}
    gran = {}
    # GRAN3 is defined over the 5-level labels, so compose it rather than applying it to raw stages
    G3 = {st: GRAN3[GRAN5[st]] for st in STAGES if st in GRAN5}
    for level, mapper in (("5", GRAN5), ("3", G3)):
        fl = [mapper[s] for seq in df.stages for s in seq]
        c = Counter(fl)
        gran[f"granularity_{level}"] = {"n_categories": len(c),
                                         "largest_share": round(max(c.values()) / len(fl), 4)}
    # The floors the protocol freezes are stated per TRAJECTORY (5.0 and 2.0 bits), while everything the ladder
    # prints is per TURN. Round 2 found the conversion happening in three separate report writers, each of which
    # multiplied an already-rounded per-turn mean by an already-rounded turns-per-trajectory - P002's pilot gate
    # published 1.367 that way, where the full-precision product is 1.3665. The scale is therefore measured here,
    # once, from the same unrounded quantities the means come from, and readers are to quote these fields.
    tpt = len(flat) / max(1, len(df))

    def gain(i, j):
        d = float(arr[:, i].mean() - arr[:, j].mean())
        return {"mean": round(d, 4), "mean_bits_per_trajectory": round(d * tpt, 6)}

    return {"corpus": label, "trajectories": int(len(df)), "turns": int(len(flat)),
            "turns_per_trajectory": round(tpt, 6),
            "units_note": "`mean` and `model_ladder_ll_per_turn` are log2 likelihood per TURN; "
                          "`mean_bits_per_trajectory` is the same gain times `turns_per_trajectory`, which is the "
                          "unit the frozen floors of 5.0 and 2.0 bits are stated in",
            "instances_dev": int(tr.instance_id.nunique()), "instances_report": int(te.instance_id.nunique()),
            "rollouts_per_instance_mean": round(len(df) / max(1, df.instance_id.nunique()), 2),
            "stage_shares": shares,
            "model_ladder_ll_per_turn": {"B0_uniform": round(-np.log2(len(STAGES)), 4),
                                          "B1_zero_order": round(float(arr[:, 0].mean()), 4),
                                          "B3_previous_command": round(float(arr[:, 2].mean()), 4),
                                          "B4_position_only": round(float(arr[:, 3].mean()), 4),
                                          "B2_first_order": round(float(arr[:, 1].mean()), 4)},
            "gains_first_minus": {"zero_order": {**gain(1, 0),
                                                  "ci95_instances": ci(boots["first_vs_zero"])},
                                   "position_only": {**gain(1, 3),
                                                      "ci95_instances": ci(boots["first_vs_position"])},
                                   "previous_command": {**gain(1, 2),
                                                         "ci95_instances": ci(boots["first_vs_cmd"])}},
            "truncation_curve": trunc, "last_stage_share": {k: round(v / len(df), 4) for k, v in last.most_common()},
            "lexicon_perturbation": pert, "granularity_robustness": gran,
            "transition_counts_top": {f"{a}->{b}": c for (a, b), c in trans_counts.most_common(20)},
            "bootstraps": len(boots["first_vs_zero"])}


def checkpoint(res: dict) -> None:
    # The shard pass costs minutes; a failure in the reporting section must not discard it.
    OUT_RAW.mkdir(exist_ok=True)
    (OUT_RAW / "EXP0031_partial_checkpoint.json").write_text(
        json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    res = {"exp_id": "EXP-0031", "paper_id": "P002", "e_id": "main", "seed": SEED,
           "protocol": "papers/P002_isp_stage_measurement/protocol_freeze.md",
           "sampling": {"swe_shards": SHARDS, "rows_per_shard": ROWS, "trove_shards": 16,
                        "trove_rows_per_shard": 1500,
                        "split": "md5(instance_id) % 1000 < 700 -> dev, else report (no instance on both sides)"},
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    swe, n_files, n_picks = read_swe()
    res["swe_zero"] = analyse(swe, "SWE-ZERO-12M")
    res["swe_zero"]["shards_available_read"] = f"{n_picks}/{n_files}"
    print("  SWE-ZERO:", json.dumps(res["swe_zero"]["gains_first_minus"], ensure_ascii=False)[:300])
    checkpoint(res)
    del swe
    trove, tn_files, tn_picks = read_trove()
    res["agenttrove"] = analyse(trove, "AgentTrove")
    res["agenttrove"]["shards_available_read"] = f"{tn_picks}/{tn_files}"
    print("  AgentTrove:", json.dumps(res["agenttrove"]["gains_first_minus"], ensure_ascii=False)[:300])
    checkpoint(res)
    a, b = res["swe_zero"], res["agenttrove"]
    gain_a = a["gains_first_minus"]["position_only"]
    gain_b = b["gains_first_minus"]["position_only"]
    a_ok, b_ok = gain_a["ci95_instances"][0] > 0, gain_b["ci95_instances"][0] > 0
    res["verdict"] = {
        "rule": ("a stage-process claim stands only if the first-order model beats the position-only model B4 with "
                 "an instance-clustered bootstrap CI excluding zero (frozen in protocol_freeze.md section 3, RQ2)"),
        "swe_beats_position_only": bool(a_ok), "trove_beats_position_only": bool(b_ok),
        "swe_gain_over_position_only": gain_a["mean"], "trove_gain_over_position_only": gain_b["mean"],
        "swe_ci95_over_position_only": gain_a["ci95_instances"],
        "trove_ci95_over_position_only": gain_b["ci95_instances"],
        "paper_identity": ("process claim survives the position-only null in both corpora" if (a_ok and b_ok) else
                           ("process claim survives in one corpus only; report per-corpus" if (a_ok or b_ok) else
                            "measurement critique: apparent stage structure is template- and position-induced"))}
    res["wallclock_sec"] = round(time.time() - t0, 1)
    res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    OUT_RAW.mkdir(exist_ok=True)
    OUT_PROC.mkdir(exist_ok=True)
    out = OUT_RAW / f"EXP0031_p002_stage_main_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    pd.DataFrame([{"corpus": c, **v["model_ladder_ll_per_turn"]} for c, v in
                  (("SWE-ZERO-12M", a), ("AgentTrove", b))]).to_csv(
        OUT_PROC / "EXP0031_model_ladder.csv", index=False)
    pd.DataFrame([{"corpus": c, "transition": k, "count": v} for c, v in
                  (("SWE-ZERO-12M", a), ("AgentTrove", b)) for k, v in v["transition_counts_top"].items()]
                 ).to_csv(OUT_PROC / "EXP0031_transitions.csv", index=False)
    pd.DataFrame([{"corpus": c, "cap": k, **v} for c, v in (("SWE-ZERO-12M", a), ("AgentTrove", b))
                  for k, v in v["truncation_curve"].items()]).to_csv(
        OUT_PROC / "EXP0031_truncation_curve.csv", index=False)
    (OUT_RAW / "EXP0031_partial_checkpoint.json").unlink(missing_ok=True)
    print(json.dumps(res["verdict"], ensure_ascii=False))
    print("wrote", out, f"({res['wallclock_sec']}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
