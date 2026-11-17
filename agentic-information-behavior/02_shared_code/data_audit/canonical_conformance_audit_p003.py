"""EXP-0027 (P003 pilot): measure whether eight public agent corpora can be aligned to twelve concepts.

Implements papers/P003_metadata_interoperability/protocol_freeze.md literally: the concept list, the states and
their thresholds, the parser set, the per-corpus hypothesised mapping and the kill gate were all fixed before
this script executed. Nothing here reads a README claim: every cell is decided by measuring sampled rows, and
the deciding evidence (column name or parser plus coverage) is stored with the cell.

    python canonical_conformance_audit_p003.py

Writes results_raw/EXP0027_p003_conformance_pilot_*.json and results_processed/EXP0027_coverage_matrix.csv.
"""

from __future__ import annotations

import glob
import json
import random
import re
import sys
import time
from collections import Counter
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(r"G:/刘俊琦/AGENT ENGINEERING/MATLABINTOKEN/datasets")
OUT_RAW, OUT_PROC = ROOT / "results_raw", ROOT / "results_processed"
SEED, ROWS, SHARDS, HEAD = 42, 2000, 8, 250

CONCEPTS = ["C1_trajectory_id", "C2_group_key", "C3_timestamp", "C4_model_id", "C5_teacher_provider",
            "C6_message_sequence", "C7_role_vocabulary", "C8_user_instruction", "C9_candidate_actions",
            "C10_executed_action", "C11_observation", "C12_outcome_signal"]

BASH = re.compile(r"```(?:bash|sh|shell|python)?\s*\n(.+?)```", re.S)
CALLBLK = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.S)
FREECALL = re.compile(r"(?:\"name\"\s*:\s*\"([A-Za-z0-9_\-]+)\"|<lapi:([A-Za-z0-9_\-]+)|call-name:\s*(\S+))")
OBS_PREFIX = re.compile(r"^\s*Observation:", re.I)


def msgs(row, key):
    m = row.get(key)
    return list(m or [])


def role_of(m, key):
    return m.get(key) if isinstance(m, dict) else None


def content_of(m, key="content"):
    if not isinstance(m, dict):
        return ""
    return str(m.get(key, m.get("value", "")) or "")


P = {}
P["meta_prompt_id"] = lambda r: [json.loads(r["metadata"]).get("prompt_id")] if r.get("metadata") and _jsonable(r["metadata"]) else []
P["meta_model"] = lambda r: [v for k, v in _meta(r).items() if k in ("model_name", "model", "llm", "teacher_model")]
# EXP-0030 (D18): a hand-check of the self-audit sample showed the model id is nested one level deeper in
# Toucan metadata (`synthetic_data_gen_configs[*].model`), so a top-level-only probe produced a false `absent`.
P["meta_nested_model"] = lambda r: [g.get("model") for g in _nested_cfgs(r) if isinstance(g, dict) and g.get("model")]
P["meta_nested_provider"] = lambda r: [g.get("engine") for g in _nested_cfgs(r)
                                       if isinstance(g, dict) and g.get("engine")]
P["meta_provider"] = lambda r: [v for k, v in _meta(r).items() if k in ("provider", "model_provider", "framework", "generator")]
P["role_vocab"] = lambda r: sorted({role_of(m, "role") or role_of(m, "from") for m in msgs(r, _msgkey(r))} - {None})
P["instruction_from_msg"] = lambda r: [content_of(m) for m in msgs(r, _msgkey(r))
                                       if (role_of(m, "role") or role_of(m, "from")) in ("user", "human")][:1]
P["bash_command"] = lambda r: [m.group(1) for m in (BASH.search(content_of(x)) for x in msgs(r, _msgkey(r))
                                                    if content_of(x)) if m]
P["tool_call_block"] = lambda r: [m.group(1) for m in (CALLBLK.search(content_of(x)) for x in msgs(r, _msgkey(r))
                                                       if content_of(x)) if m]
P["free_text_call"] = lambda r: [next((g for g in m.groups() if g), None) for m in
                                 (FREECALL.search(content_of(x)) for x in msgs(r, _msgkey(r)) if content_of(x)) if m]
P["tool_role_obs"] = lambda r: [content_of(m) for m in msgs(r, _msgkey(r))
                                if (role_of(m, "role") or role_of(m, "from")) in ("tool", "function_response", "observation")]
P["observation_prefix"] = lambda r: [content_of(m) for m in msgs(r, _msgkey(r)) if OBS_PREFIX.match(content_of(m))]
P["tool_named_reply"] = lambda r: [content_of(m) for m in msgs(r, _msgkey(r))
                                   if (role_of(m, "role") or role_of(m, "from")) == "tool"]


def _msgkey(row):
    return "messages" if "messages" in row and row["messages"] is not None else "conversations"


def _meta(row):
    v = row.get("metadata")
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return {}
    return v if isinstance(v, dict) else {}


def _nested_cfgs(row):
    """`metadata.synthetic_data_gen_configs` is a list of generation-config dicts (model, engine, params)."""
    cfgs = _meta(row).get("synthetic_data_gen_configs")
    if isinstance(cfgs, str):
        try:
            cfgs = json.loads(cfgs)
        except Exception:
            return []
    if isinstance(cfgs, dict):
        return [cfgs]
    return list(cfgs) if isinstance(cfgs, list) else []


def _jsonable(v):
    try:
        json.loads(v)
        return True
    except Exception:
        return False


D = lambda col: ("direct", col)
R = lambda name: ("derived", name)
SPEC = {
    "Toucan-1.5M": {"path": "Agent-Ark/Toucan-1.5M", "cols": {
        "C1_trajectory_id": [D("uuid")], "C2_group_key": [R("meta_prompt_id")], "C3_timestamp": [],
        "C4_model_id": [R("meta_model")], "C5_teacher_provider": [R("meta_provider")],
        "C6_message_sequence": [D("messages")], "C7_role_vocabulary": [R("role_vocab")],
        "C8_user_instruction": [D("question")], "C9_candidate_actions": [D("available_tools")],
        "C10_executed_action": [D("target_tools")], "C11_observation": [R("tool_role_obs")],
        "C12_outcome_signal": [D("question_quality_assessment")]},
        "conflicts": {"C12_outcome_signal": ["question_quality_assessment", "response_quality_assessment"]}},
    "SWE-ZERO-12M": {"path": "AlienKevin/SWE-ZERO-12M-trajectories", "cols": {
        "C1_trajectory_id": [], "C2_group_key": [D("instance_id")], "C3_timestamp": [], "C4_model_id": [],
        "C5_teacher_provider": [], "C6_message_sequence": [D("messages")],
        "C7_role_vocabulary": [R("role_vocab")], "C8_user_instruction": [R("instruction_from_msg")],
        "C9_candidate_actions": [], "C10_executed_action": [R("bash_command")],
        "C11_observation": [R("observation_prefix")], "C12_outcome_signal": [D("exit_status")]}},
    "hermes-agent-reasoning-traces": {"path": "lambda/hermes-agent-reasoning-traces", "cols": {
        "C1_trajectory_id": [D("id")], "C2_group_key": [], "C3_timestamp": [], "C4_model_id": [],
        "C5_teacher_provider": [], "C6_message_sequence": [D("conversations")],
        "C7_role_vocabulary": [R("role_vocab")], "C8_user_instruction": [D("task")],
        "C9_candidate_actions": [D("tools")], "C10_executed_action": [R("tool_call_block")],
        "C11_observation": [R("tool_named_reply")], "C12_outcome_signal": []}},
    "AgentTrove": {"path": "open-thoughts/AgentTrove", "cols": {
        "C1_trajectory_id": [D("run_id")], "C2_group_key": [D("trial_name")], "C3_timestamp": [D("date")],
        "C4_model_id": [D("model")], "C5_teacher_provider": [D("original_teacher")],
        "C6_message_sequence": [D("conversations")], "C7_role_vocabulary": [R("role_vocab")],
        "C8_user_instruction": [D("instruction"), R("instruction_from_msg")], "C9_candidate_actions": [],
        "C10_executed_action": [R("free_text_call")], "C11_observation": [R("tool_named_reply")],
        "C12_outcome_signal": [D("result"), D("judgment"), D("task_binary")]}},
    "AgentBank": {"path": "Solaris99/AgentBank", "cols": {
        "C1_trajectory_id": [D("id")], "C2_group_key": [], "C3_timestamp": [], "C4_model_id": [],
        "C5_teacher_provider": [], "C6_message_sequence": [D("conversations")],
        "C7_role_vocabulary": [R("role_vocab")], "C8_user_instruction": [R("instruction_from_msg")],
        "C9_candidate_actions": [], "C10_executed_action": [R("free_text_call")],
        "C11_observation": [R("tool_named_reply")], "C12_outcome_signal": []}},
    "code-act": {"path": "xingyaoww/code-act", "cols": {
        "C1_trajectory_id": [D("id")], "C2_group_key": [], "C3_timestamp": [], "C4_model_id": [],
        "C5_teacher_provider": [], "C6_message_sequence": [D("conversations")],
        "C7_role_vocabulary": [R("role_vocab")], "C8_user_instruction": [R("instruction_from_msg")],
        "C9_candidate_actions": [], "C10_executed_action": [R("bash_command"), R("free_text_call")],
        "C11_observation": [R("tool_named_reply")], "C12_outcome_signal": []}},
    "AgentInstruct": {"path": "zai-org/AgentInstruct", "cols": {
        "C1_trajectory_id": [D("id")], "C2_group_key": [], "C3_timestamp": [], "C4_model_id": [],
        "C5_teacher_provider": [], "C6_message_sequence": [D("conversations")],
        "C7_role_vocabulary": [R("role_vocab")], "C8_user_instruction": [R("instruction_from_msg")],
        "C9_candidate_actions": [], "C10_executed_action": [R("free_text_call")],
        "C11_observation": [R("tool_named_reply")], "C12_outcome_signal": []}},
}


def non_empty(v):
    if v is None:
        return False
    if isinstance(v, (list, tuple)):
        return any(non_empty(x) for x in v)
    if isinstance(v, str):
        return bool(v.strip()) and v.strip().lower() not in ("none", "null", "nan", "{}", "[]")
    return True


def sample_parquet(path: Path):
    files = [f for f in sorted(glob.glob(str(path / "**/*.parquet"), recursive=True)) if ".cache" not in f]
    if not files:
        return [], "no parquet shards (container format differs)"
    picks = sorted(random.Random(SEED).sample(files, min(SHARDS, len(files))))
    rows, notes = [], []
    for f in picks:
        pf = pq.ParquetFile(f)
        cols = list(pf.schema_arrow.names)
        got = 0
        # row-group-wise reads: reading a whole multi-chunk file with nested list columns raises
        # "Nested data conversions not implemented for chunked array outputs" in pyarrow 14
        for rg in range(pf.metadata.num_row_groups):
            if got >= HEAD:
                break
            t = pf.read_row_group(rg, columns=cols).slice(0, min(HEAD - got,
                                                                  pf.metadata.row_group(rg).num_rows))
            part = t.to_pylist()
            rows.extend(part)
            got += len(part)
        notes.append(f"{Path(f).name}:{got}")
    return rows[:ROWS], f"{len(files)} parquet shards; per-file rows " + ",".join(notes)


def measure(corp, spec, rows):
    cells, conflict_notes = {}, []
    n = len(rows)
    for con in CONCEPTS:
        cands = spec["cols"].get(con, [])
        stats = []
        for kind, ref in cands:
            if kind == "direct":
                cov = sum(1 for r in rows if non_empty(r.get(ref))) / max(1, n)
                stats.append((kind, ref, cov))
            else:
                fn = P[ref]
                try:
                    cov = sum(1 for r in rows if non_empty(fn(r))) / max(1, n)
                except Exception as e:
                    cov = 0.0
                    stats.append(("parser_error", f"{ref}:{type(e).__name__}", 0.0))
                    continue
                stats.append((kind, ref, cov))
        both = spec.get("conflicts", {}).get(con) or [s[1] for s in stats if s[0] == "direct"]
        conflict = False
        if len(both) > 1:
            pres = [(a, b) for a, b in
                    zip((non_empty(r.get(both[0])) for r in rows), (non_empty(r.get(both[1])) for r in rows))
                    if a and b]
            if pres:
                dis = sum(1 for r, (a, b) in zip(rows, [(x, y) for x, y in
                        zip((non_empty(r.get(both[0])) for r in rows),
                            (non_empty(r.get(both[1])) for r in rows)) if x and y])
                          if str(r.get(both[0])).strip().lower() != str(r.get(both[1])).strip().lower())
                if dis / len(pres) >= 0.05:
                    conflict, frac = True, dis / len(pres)
                    conflict_notes.append({"concept": con, "columns": both, "both_populated_rows": len(pres),
                                           "disagreeing_share": round(frac, 4)})
        good = [s for s in stats if s[2] >= 0.60]
        if conflict:
            state = "conflict"
        elif len([s for s in good if s[2] >= 0.95]) > 1 or len(good) > 1:
            state = "ambiguous" if not any(s[2] >= 0.95 for s in good) else "direct"
        elif any(s[0] == "direct" and s[2] >= 0.95 for s in stats):
            state = "direct"
        elif good:
            state = "derived"
        elif stats and max(s[2] for s in stats) > 0.05:
            state = "ambiguous"
        else:
            state = "absent"
        cells[con] = {"state": state, "evidence": [{"kind": k, "source": s, "coverage": round(c, 4)}
                                                  for k, s, c in stats]}
    return cells, conflict_notes


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    res = {"exp_id": "EXP-0027", "paper_id": "P003", "seed": SEED,
           "protocol": "papers/P003_metadata_interoperability/protocol_freeze.md",
           "sampling": {"rows_target": ROWS, "shards": SHARDS, "head_per_shard": HEAD},
           "corpora": {}, "started_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    for name, spec in SPEC.items():
        rows, note = sample_parquet(DATA / spec["path"])
        if not rows:
            res["corpora"][name] = {"error": note, "n_rows": 0}
            print(f"  {name}: {note}")
            continue
        cells, conflicts = measure(name, spec, rows)
        groups = {c: int(pd.Series([r.get(spec["cols"][c][0][1]) for r in rows if c in spec["cols"]
                                   and spec["cols"][c] and spec["cols"][c][0][0] == "direct"]).nunique())
                  for c in ("C2_group_key", "C1_trajectory_id")
                  if c in spec["cols"] and spec["cols"][c] and spec["cols"][c][0][0] == "direct"}
        states = Counter(v["state"] for v in cells.values())
        res["corpora"][name] = {"n_rows": len(rows), "cells": cells, "conflicts": conflicts,
                                "loss_ratio": round((states["absent"] + states["ambiguous"] + states["conflict"])
                                                    / len(CONCEPTS), 4),
                                "state_counts": dict(states), "distinct_group_values_in_sample": groups,
                                "role_vocabulary": sorted({k for r in rows for k in
                                                           ([role_of(m, "role") or role_of(m, "from")
                                                             for m in msgs(r, _msgkey(r))] or [])
                                                           if k} | set())[:8]}
        print(f"  {name}: rows={len(rows)} loss={res['corpora'][name]['loss_ratio']} states={dict(states)}")
    usable = {c: sum(1 for v in res["corpora"].values() if "cells" in v
                     and v["cells"][c]["state"] in ("direct", "derived")) for c in CONCEPTS}
    res["coverage_by_concept"] = usable
    res["n_corpora_audited"] = sum(1 for v in res["corpora"].values() if "cells" in v)
    res["concepts_direct_or_derived_in_7_of_8"] = [c for c, n in usable.items() if n >= 7]
    res["kill_gate"] = {"rule": "drop P003 if >=10 of 12 concepts are direct|derived in >=7 of 8 corpora",
                        "concepts_passing": len(res["concepts_direct_or_derived_in_7_of_8"]),
                        "verdict": ("KILL P003 - no interoperability problem measurable here"
                                    if len(res["concepts_direct_or_derived_in_7_of_8"]) >= 10
                                    else "PROCEED - alignability is partial and typed failures are reportable")}
    res["wallclock_sec"] = round(time.time() - t0, 1)
    res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    OUT_RAW.mkdir(exist_ok=True)
    out = OUT_RAW / f"EXP0027_p003_conformance_pilot_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    pd.DataFrame([{"corpus": c, "n_rows": v.get("n_rows"), "loss_ratio": v.get("loss_ratio"),
                   **{k: (v["cells"][k]["state"] if "cells" in v else "error") for k in CONCEPTS}}
                  for c, v in res["corpora"].items()]).to_csv(OUT_PROC / "EXP0027_coverage_matrix.csv", index=False)
    print("coverage by concept:", json.dumps(usable, ensure_ascii=False))
    print("kill gate:", res["kill_gate"])
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
