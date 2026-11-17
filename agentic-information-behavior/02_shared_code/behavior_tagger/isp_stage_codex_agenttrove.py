"""EXP-0092 (P002): measure AgentTrove with the instrument frozen in `protocol_freeze_agenttrove.md`.

EXP-0031 reported AgentTrove as untestable: 9.9% of its assistant turns received a stage, so the RQ2 ladder could
not be run on it and the second-corpus replication stayed unverifiable. That number is a property of the SWE-ZERO
codex's action extractor as much as of the corpus - AgentTrove carries its action as a JSON-ish
`commands`/`keystrokes` payload, not a fenced ```bash block, and only about half of its assistant turns parse as
valid JSON at all. This run separates the three possible causes by coding the **same rows** three ways:

  * **arm0** - frozen extractor + frozen cue table: reproduces EXP-0031, and is checked against it.
  * **arm1** - new extractor + frozen cue table: what the payload fix alone buys.
  * **arm2** - new extractor + the AgentTrove cue table frozen in the addendum: the new instrument, and the one the
    RQ1/RQ2 numbers are reported from.

The construct definitions, stage labels, priority order, thresholds, split rule and bootstrap all come from the
frozen protocol and are reused by import, not re-implemented. Before anything is computed the script asserts that
its own rule table matches the regexes printed in the addendum, so the freeze cannot drift from the code
(`--force-freeze` rewrites the addendum from the code, which is the opposite of what a freeze is for and is refused
unless asked for explicitly).

    python isp_stage_codex_agenttrove.py            # measure
    python isp_stage_codex_agenttrove.py --check    # drift check only, no data read

Writes results_raw/EXP0092_agenttrove_codex_*.json.
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

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "statistics"))
import isp_stage_coder as K                      # noqa: E402  (frozen codex: RULES, code_turn, STAGES)
import isp_stage_main_p002 as M                  # noqa: E402  (loader sample, analyse, bucket, SEED)

ROOT = M.ROOT
TROVE = M.TROVE
OUT_RAW = ROOT / "results_raw"
FREEZE = ROOT / "papers" / "P002_isp_stage_measurement" / "protocol_freeze_agenttrove.md"
SEED, SHARDS, ROWS_PER_SHARD = M.SEED, 16, 1500      # exactly EXP-0031's AgentTrove sample

# ---- the new instrument, transcribed from the addendum (table B) in the frozen priority order
RULES_TROVE = [
    ("end", re.compile(r'''(task_complete["']?\s*:\s*true|\b(exit 0|echo done|submit)\b)'''),
     re.compile(r"\b(done|final answer|task complete|all tests pass|solution is)\b")),
    ("verify", re.compile(r'''^\s*(pytest|python3? -m pytest|python3? .*(test|check|verify)\b'''
                          r'''|bash -lc ['"“]?pytest|\./run.*\.sh|cargo test|npm test|make test|g\+\+ .*-o .* && \./)'''),
     re.compile(r"\b(test|tests|verify|validation|check the output|expected output|sample input|assert)\b")),
    ("documentation", re.compile(r"^\s*(cat *>|tee|printf *>|echo *>|python3? -c .*(open|write)|sed -i"
                                 r"|cp \.\.\.|xxd -r)"),
     re.compile(r"\b(write|create|edit|modify|implement|append|replace|save .* file)\b")),
    ("extraction", re.compile(r"^\s*(cat\b|head\b|tail\b|sed -n|grep\b|rg\b|awk\b|jq\b|wc\b|less\b"
                              r"|git (show|diff|log)|python3? -c .*(read|print\(open))"),
     re.compile(r"\b(read|look at|inspect|check the contents|see what|find out|extract|print the)\b")),
    ("exploration", re.compile(r"^\s*(ls\b|find\b|tree\b|pwd\b|du\b|which\b|ls -la|echo \*|cd .*&& *ls|stat\b"
                               r"|file\b|head -c)"),
     re.compile(r"\b(explore|structure|layout|where is|which files|overview|orient|list the|directory)\b")),
    ("system", re.compile(r"^\s*(pip3?|apt(-get)?|conda|npm install|yarn|cargo\b|export\b|mkdir\b|rm -|mv \b"
                          r"|chmod|source \b|bash -lc|cd \b|virtualenv|service\b|systemctl)"),
     re.compile(r"\b(install|set up|environment|dependency|configure|compile|build)\b")),
    ("clarification", re.compile(r"^\s*$"),
     re.compile(r"\b(i should|i need to|my plan|first,? i|let me (start|think|plan)|the task asks|plan is"
                r"|approach will be)\b")),
]
STAGES = [r[0] for r in RULES_TROVE] + ["uncodable"]

FIELD = re.compile(r"\"(analysis|keystrokes|command|cmd|code|plan|task_complete)\"\s*:\s*\"((?:[^\"\\]|\\.)*)\"")
FENCE = re.compile(r"```(?:bash|sh|shell|python)?\s*\n(.+?)```", re.S)
BOOL = re.compile(r"\"task_complete\"\s*:\s*(true|false)", re.I)


def unesc(s: str) -> str:
    return s.replace("\\n", "\n").replace("\\t", "\t").replace('\\"', '"').replace("\\\\", "\\")


def split_turn_trove(content: str) -> tuple[str, str]:
    """Addendum section A: analysis as thought, first keystrokes as command, fenced/command/code as fallback."""
    fields, order = {}, []
    for m in FIELD.finditer(content):
        order.append(m.group(1))
        fields.setdefault(m.group(1), m.group(2))
    thought = unesc(fields.get("analysis") or fields.get("plan") or "")
    if not thought:
        thought = content.split("{")[0].strip()
    cmd = ""
    if fields.get("keystrokes"):
        cmd = unesc(fields["keystrokes"]).strip().split("\n")[0][:400]
    if not cmd:
        fm = FENCE.search(content)
        if fm:
            cmd = fm.group(1).strip().split("\n")[0][:400]
    for k in ("command", "cmd", "code"):
        if not cmd and fields.get(k):
            cmd = unesc(fields[k]).strip().split("\n")[0][:400]
    if not thought and BOOL.search(content):
        thought = BOOL.search(content).group(0)          # a bare {"task_complete": true} turn still says "end"
    return thought, cmd, order


def code_turn_trove(thought: str, cmd: str) -> str:
    for label, cmd_re, thought_re in RULES_TROVE:
        if (cmd and cmd_re.search(cmd)) or (thought_re.pattern != r"^\s*$" and thought_re.search(thought)):
            if cmd or label == "clarification":
                return label
    return "uncodable"


def freeze_matches_code() -> tuple[bool, list]:
    """Every regex in the addendum's `trove-cues` block must be the regex the code runs."""
    if not FREEZE.is_file():
        return False, ["addendum missing"]
    text = FREEZE.read_text(encoding="utf-8")
    m = re.search(r"```trove-cues\n(.*?)```", text, re.S)
    if not m:
        return False, ["no ```trove-cues block in the addendum"]
    printed = {}
    for ln in m.group(1).strip().splitlines():
        cells = [c.strip() for c in ln.split("\t")]
        if len(cells) >= 3:
            printed[cells[0]] = (cells[1], cells[2])
        elif len(cells) == 2:
            printed[cells[0]] = (r"^\s*$", cells[1])
    bad = []
    for label, cmd_re, th_re in RULES_TROVE:
        got = printed.get(label)
        if got is None:
            bad.append(f"{label}: not printed in the addendum")
            continue
        if got[0] != cmd_re.pattern:
            bad.append(f"{label} command cue drifted:\n    addendum {got[0]!r}\n    code       {cmd_re.pattern!r}")
        if got[1] != th_re.pattern:
            bad.append(f"{label} text cue drifted:\n    addendum {got[1]!r}\n    code       {th_re.pattern!r}")
    for label in set(printed) - {r[0] for r in RULES_TROVE}:
        bad.append(f"addendum prints a stage the code does not implement: {label}")
    return (not bad), bad


def read_arms():
    """One pass over the EXP-0031 sample, coding each turn three ways."""
    files = [f for f in sorted(glob.glob(str(TROVE / "**/*.parquet"), recursive=True)) if ".cache" not in f]
    if len(files) < SHARDS:
        raise SystemExit(f"ABORT: only {len(files)} AgentTrove shards on disk - the sample cannot be reproduced")
    picks = sorted(random.Random(SEED).sample(files, min(SHARDS, len(files))))
    if picks != sorted(random.Random(SEED).sample(files, min(SHARDS, len(files)))):
        raise SystemExit("ABORT: shard selection is not deterministic")
    recs = {0: [], 1: [], 2: []}
    n_turns = n_json_valid = n_keystrokes = 0
    for f in picks:
        pf = pq.ParquetFile(f)
        n = min(ROWS_PER_SHARD, pf.metadata.num_rows)
        got = 0
        for rg in range(pf.metadata.num_row_groups):
            if got >= n:
                break
            blk = pf.read_row_group(rg).slice(0, n - got)
            for r in blk.to_pylist():
                per = {0: [], 1: [], 2: []}
                heads = {0: [], 1: [], 2: []}
                text_only = {0: [], 1: [], 2: []}
                for m in (r.get("conversations") or []):
                    role = m.get("role") or m.get("from")
                    if role not in ("assistant", "gpt"):
                        continue
                    content = m.get("content") or m.get("value") or ""
                    n_turns += 1
                    try:
                        json.loads(content)
                        n_json_valid += 1
                    except Exception:
                        pass
                    # arm0: exactly what EXP-0031 did
                    t0, c0 = M.split_turn(content)
                    per[0].append(M.code_turn(t0, c0))
                    heads[0].append(M.head_token(c0))
                    text_only[0].append(M.code_turn(t0, ""))
                    # arms 1 and 2 share the new extractor
                    t1, c1, order = split_turn_trove(content)
                    if "keystrokes" in order:
                        n_keystrokes += 1
                    per[1].append(M.code_turn(t1, c1))
                    heads[1].append(M.head_token(c1))
                    text_only[1].append(M.code_turn(t1, ""))
                    per[2].append(code_turn_trove(t1, c1))
                    heads[2].append(M.head_token(c1))
                    text_only[2].append(code_turn_trove(t1, ""))   # the EXP-0031 perturbation, on the new codex
                if not per[0]:
                    continue
                grp = r.get("run_id") or r.get("task") or r.get("trial_name")
                for arm in (0, 1, 2):
                    recs[arm].append({"instance_id": str(grp), "stages": per[arm], "heads": heads[arm],
                                      "thoughts_only": text_only[arm],
                                      "exit_status": str(r.get("result") or "n/a")})
            got += len(blk)
    dfs = {a: pd.DataFrame(recs[a]) for a in recs}
    return dfs, {"assistant_turns": n_turns, "valid_json_share": round(n_json_valid / max(1, n_turns), 4),
                 "keystrokes_share": round(n_keystrokes / max(1, n_turns), 4),
                 "shards_read": len(picks), "trajectories": int(len(dfs[2]))}


def shares(df):
    flat = [s for seq in df.stages for s in seq]
    c = Counter(flat)
    tot = max(1, len(flat))
    return {"codable": round(1 - c["uncodable"] / tot, 4), "uncodable": round(c["uncodable"] / tot, 4),
            "largest_share": round(max((v for k, v in c.items() if k != "uncodable"), default=0) / tot, 4),
            "turns": tot, "stage_shares": {k: round(v / tot, 4) for k, v in c.most_common()}}


def rq1(s, gate=0.80):
    return {"codable_ge_0_80": s["codable"] >= gate, "uncodable_le_0_20": s["uncodable"] <= 1 - gate,
            "largest_le_0_80": s["largest_share"] <= 0.80, "passes_all_three": (s["codable"] >= gate
                                                                                and s["uncodable"] <= 1 - gate
                                                                                and s["largest_share"] <= 0.80)}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ok, bad = freeze_matches_code()
    if not ok:
        raise SystemExit("ABORT: the addendum and the code disagree - fix one deliberately, never silently:\n  "
                         + "\n  ".join(bad))
    print("  freeze check ok: every cue printed in protocol_freeze_agenttrove.md is the regex the code runs")
    if "--check" in sys.argv:
        return 0
    t0 = time.time()
    dfs, meta = read_arms()
    for arm, name in ((0, "frozen extractor + frozen cues"), (1, "new extractor + frozen cues"),
                      (2, "new extractor + AgentTrove cues (the frozen instrument)")):
        if len(dfs[arm]) < 50:
            raise SystemExit(f"ABORT: arm {arm} ({name}) yielded {len(dfs[arm])} trajectories - too few to report")
    s0, s1, s2 = (shares(dfs[a]) for a in (0, 1, 2))
    a2 = M.analyse(dfs[2], "AgentTrove-EXP0092") if s2["codable"] > 0.20 else None
    print("  arm0 (EXP-0031's instrument) codable:", s0["codable"], "| arm1:", s1["codable"], "| arm2:", s2["codable"])
    if a2:
        g = a2["gains_first_minus"] if "gains_first_minus" in a2 else {}
        print("  arm2 RQ2 gains:", json.dumps({k: v.get("mean") for k, v in g.items()}, ensure_ascii=False)[:220])

    res = {"exp_id": "EXP-0092", "paper_id": "P002", "seed": SEED,
           "instrument_freeze": "papers/P002_isp_stage_measurement/protocol_freeze_agenttrove.md",
           "freeze_verified_against_code": True, "sample": meta,
           "arms": {"arm0_frozen_extractor_frozen_cues": {"shares": s0, "rq1": rq1(s0)},
                    "arm1_new_extractor_frozen_cues": {"shares": s1, "rq1": rq1(s1)},
                    "arm2_new_extractor_agenttrove_cues": {"shares": s2, "rq1": rq1(s2)}},
           "exp0031_reference": None, "ladder": a2,
           "wallclock_sec": round(time.time() - t0, 1), "started_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    ref = sorted((ROOT / "results_raw").glob("EXP0031_p002_stage_main_*.json"))
    if ref:
        R = json.loads(ref[-1].read_text(encoding="utf-8"))
        res["exp0031_reference"] = {"file": ref[-1].name, "codable": R["agenttrove"].get("codable_share"),
                                    "uncodable": R["agenttrove"]["stage_shares"].get("uncodable"),
                                    "arm0_reproduces": abs(R["agenttrove"]["stage_shares"].get("uncodable", -1)
                                                           - s0["uncodable"]) < 1e-9}
    if a2:
        g = a2.get("gains_first_minus", {})
        po = g.get("position_only", {})
        zs = g.get("zero_order", {})
        # Round 2: this block's keys said `_bits_per_trajectory` while holding the per-TURN means beside floors
        # stated per trajectory, so the record read as comparing 0.2041 with 5.0. The names now say which unit
        # each number is in, and the per-trajectory products are the ones the ladder measured rather than a
        # reader's multiplication.
        res["rq2_frozen_criterion"] = {
            "ci_excludes_zero_vs_position_only": bool(po) and (po["ci95_instances"][0] > 0 or po["ci95_instances"][1] < 0),
            "b2_minus_b1_bits_per_turn": zs.get("mean"),
            "b2_minus_b4_bits_per_turn": po.get("mean"),
            "b2_minus_b1_bits_per_trajectory": zs.get("mean_bits_per_trajectory"),
            "b2_minus_b4_bits_per_trajectory": po.get("mean_bits_per_trajectory"),
            "turns_per_trajectory": a2.get("turns_per_trajectory"),
            "floors": {"b2_minus_b1": 5.0, "b2_minus_b4": 2.0}, "floors_are_bits_per_trajectory": True,
            "note": "the floors were set for SWE-ZERO's capped 15-step trajectories and are applied unchanged; "
                    "AgentTrove turns per trajectory differ, so a magnitude failure here is reported as a limit of "
                    "the criterion across corpora, not as a reason to move the floor"}
    else:
        res["rq2_frozen_criterion"] = {"testable": False, "why": "codability still below 0.20 after the payload fix"}
    pass2 = res["arms"]["arm2_new_extractor_agenttrove_cues"]["rq1"]["passes_all_three"]
    if pass2 and a2:
        res["verdict"] = (f"AGENTTROVE IS REACHABLE with the new instrument: codable {s2['codable']} (arm0 "
                          f"{s0['codable']}, arm1 {s1['codable']}), so RQ1's three conjuncts and the ladder are now "
                          "testable on a second corpus. Whether RQ2's criterion is met is reported from the ladder "
                          "block, not decided by codability")
    elif s1["codable"] - s0["codable"] > 0.30 and not pass2:
        res["verdict"] = (f"EXTRACTION EXPLAINS MOST OF IT but the instrument still fails RQ1: codability moves "
                          f"{s0['codable']} -> {s1['codable']} with the payload fix alone and reaches "
                          f"{s2['codable']} with the corpus cue table, below the 0.80 conjunct. The replication "
                          "stays untestable, and the reason is now measured rather than assumed")
    else:
        res["verdict"] = (f"STILL NOT REACHABLE: codability {s0['codable']} -> {s2['codable']} under the new "
                          "instrument, below the frozen RQ1 conjuncts, so the second-corpus replication is "
                          "untestable under a faithful second codex as well as under the frozen one")
    out = OUT_RAW / f"EXP0092_agenttrove_codex_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps({k: res["arms"][k]["shares"]["codable"] for k in res["arms"]}, ensure_ascii=False))
    print("verdict:", res["verdict"])
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
