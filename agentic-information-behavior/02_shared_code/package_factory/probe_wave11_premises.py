"""EXP-0207: the wave-11 premise census - can a recorded search be read as an organisation's memory?

Five designs are screened for this wave: T131 (do successful and failed searches have different discourse
structures), T137 (which linguistic components of a trajectory constitute reusable procedural knowledge), T138 (how
the level of linguistic abstraction affects transfer), T140 (which information is lost first under compression) and
T142 (semantic-relation-based consolidation of stored episodes). All five need the same three things at once: a real
outcome, several recorded attempts of the same task, and assistant prose long enough to code for components. This
census measures all three on the substrate the estate can read at that resolution - the same 12-file, seeded,
content-deduplicated SWE-ZERO rollout draw waves 6 and 9 measured.

The switch of substrate is recorded rather than made quietly (deviation W11-D02). The screened dataset for these topics
is open-thoughts/AgentTrove, and this census measured it first: a structure scan of all 38 shards found 1,696,847
rows, of which 128,435 carry a non-null `task_binary` and 218,706 a non-null `result`, spread over 200,825 task
prefixes attempted more than once. So the release is not empty of what the designs need - but its assistant text
averages 81,013 characters per trajectory and its outcome columns are null on more than 90% of rows, which puts a
*task-complete* sample (both attempts of a task, read together) outside what a wave can afford. The 12-file draw used
by waves 6 and 9 has an outcome label on every rollout, 1,775 instances attempted more than once, and a step-level
text stream already parsed by the estate's own reader. Every gate rule and threshold below is the one written for
AgentTrove; only the corpus they are measured on differs, and no design's dependent variable had been estimated when
the change was made. The AgentTrove scan is kept as an artefact of this same experiment so the abandoned substrate is
documented rather than dismissed.

Each gate is an absolute floor on the cell its estimate will use, never a share of rows (the W10-D01 rule), and each
names the topics it scopes. Structure and prevalence only - no association is computed in this file.

    python 02_shared_code/package_factory/probe_wave11_premises.py [--rows 400] [--agent-trove-scan]
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np                                                # noqa: E402
import pandas as pd                                               # noqa: E402
import pyarrow.parquet as pq                                      # noqa: E402
import wave_lib as W                                              # noqa: E402
import exp_wave6_features as EF6
import probe_wave6_premises as P6                                  # noqa: E402  the estate's fixed rollout draw
import topic_designs_wave6 as TD6                                 # noqa: E402  the same sample cap as waves 6 and 9

EXP = "EXP-0207"
SEED = 42
CAP = int(TD6.COMMON["sample"]["traj_cap"])
AGENT_TROVE = pathlib.Path(str(W.ROOT.parent) + "/MATLABINTOKEN/datasets/open-thoughts/AgentTrove")
AT_COLUMNS = ["agent", "task_binary", "result", "trial_name", "original_source", "trace_source", "verifier_output",
              "judgment", "episode"]

# ------------------------------------------------------------------ the category lexicons, frozen before the read
COMPONENT = {
    "context": ["the task is", "you are", "given", "the user wants", "the problem is", "the issue is"],
    "condition": ["if ", "when ", "unless", "only if", "in case", "assum"],
    "observation": ["output", "returned", "the result", "i see", "the error says", "stdout", "verifier report",
                    "the file contains"],
    "procedure": ["first", "then", "next", "finally", "step ", "i will", "let me", "run ", "execute"],
    "rationale": ["because", "so that", "in order to", "this works", "the reason", "since ", "therefore"],
    "exception": ["fail", "error", "exception", "not found", "denied", "timed out", "wrong", "instead"],
    "provenance": ["according to", "documentation", "read the file", "line ", "reference", "source", "the docs",
                   "as defined in"],
    "result": ["done", "solved", "success", "complete", "final answer", "submitted", "resolved", "passes"],
}
ABSTRACT_MARK = ["the code", "the function", "a file", "the data", "some values", "the input", "the result",
                 "something", "stuff", "etc", "and so on", "the relevant", "appropriate"]
CONCRETE_RX = [r"/[\w./\-]{3,}", r"\b[\w\-]+\.(?:py|sh|csv|json|txt|md|yml|yaml|js|ts)\b", r"\b0x[0-9a-f]+\b",
               r"\b\d{2,}\b", r"\b[a-z_]+_[a-z_0-9]+\b", r"\b[A-Z][a-z]+[A-Z]\w*\b"]
UNCERTAINTY = ["not sure", "unsure", "unclear", "i think", "maybe", "perhaps", "cannot confirm", "appears",
               "seems", "i believe", "presumably", "uncertain"]
NEG_CONSTRAINT = ["must not", "do not", "don t", "don't", "never", "avoid", "without", "no more than",
                  "not allowed", "cannot", "should not"]
MAX_TEXT = 400000                        # characters of agent prose coded per rollout, fixed before the read


def components_of(text: str) -> dict:
    low = str(text).lower()
    return {k: int(any(m in low for m in ms)) for k, ms in COMPONENT.items()}


def marker_counts(text: str) -> dict:
    low = str(text).lower()
    return {"abstract_n": int(sum(1 for m in ABSTRACT_MARK if m in low)),
            "concrete_n": int(sum(len(re.findall(rx, low)) for rx in CONCRETE_RX)),
            "uncert_n": int(sum(1 for m in UNCERTAINTY if m in low)),
            "negcon_n": int(sum(1 for m in NEG_CONSTRAINT if m in low))}


def assistant_text(traj: dict) -> str:
    """Everything the agent itself wrote in one rollout, commands removed so the language is the reasoning's."""
    parts = []
    for m in [dict(x) for x in (traj.get("messages") or [])]:
        if str(m.get("role")) != "assistant":
            continue
        t = str(m.get("content") or "")
        b = P6.COMMAND_BLOCK.search(t)
        parts.append(t[:b.start()] if b else t)
    return " \n ".join(parts)[:MAX_TEXT]


def measure(drawn: list) -> dict:
    parsed = 0
    outcomes = collections.Counter()
    inst = collections.Counter()
    repos = collections.Counter()
    turns, kinds, chars = [], [], []
    comp_rows = collections.Counter()
    abs_c, con_c, unc_c, neg_c = [], [], [], []
    long6 = two_kinds = with_uncert = with_negcon = with_concrete = obs_pairs = 0
    for k, t in enumerate(drawn):
        rows = EF6.step_rows(t, f"census-{k}")
        msgs = [dict(x) for x in (t.get("messages") or [])]
        a_idx = [i for i, m in enumerate(msgs) if str(m.get("role")) == "assistant" and P6.COMMAND_BLOCK.search(
            str(m.get("content") or "")) or str(m.get("role")) == "assistant"]
        if not rows and not a_idx:
            continue
        parsed += 1
        ex = str(t.get("exit_status") or "")
        outcomes["exit_status_non_null"] += int(ex.strip().lower() not in ("", "none", "nan"))
        outcomes["submitted"] += int(ex.strip().lower() == "submitted")
        outcomes["incomplete"] += int(ex.strip().lower() == "incomplete")
        inst[str(t.get("instance_id"))] += 1
        repos[str(t.get("repo") or "none").split("/")[0]] += 1
        turns.append(len(a_idx))
        text = assistant_text(t)
        comp = components_of(text)
        comp_rows.update(comp)
        kinds.append(sum(comp.values()))
        mc = marker_counts(text)
        abs_c.append(mc["abstract_n"])
        con_c.append(mc["concrete_n"])
        unc_c.append(mc["uncert_n"])
        neg_c.append(mc["negcon_n"])
        chars.append(len(text))
        long6 += int(len(a_idx) >= 6)
        two_kinds += int(sum(comp.values()) >= 2)
        with_uncert += int(mc["uncert_n"] >= 1)
        with_negcon += int(mc["negcon_n"] >= 1)
        with_concrete += int(mc["concrete_n"] >= 1)
        obs_pairs += int(any(str(msgs[i].get("role")) == "user" for i in range(min(a_idx[-1] + 1, len(msgs)))
                             if i > (a_idx[0] if a_idx else 0)))
    grp = pd.Series(inst, dtype=float)
    return {"corpus": "the same 12-file SWE-ZERO rollout draw waves 6 and 9 measured, whole (no subsample)",
            "rollouts_drawn": len(drawn), "rollouts_parsed": parsed,
            "median_assistant_turns": float(np.median(turns)) if turns else None,
            "mean_assistant_turns": round(float(np.mean(turns)), 2) if turns else None,
            "mean_chars_of_agent_text": round(float(np.mean(chars)), 0) if chars else None,
            "outcome_counts": {str(k): int(v) for k, v in outcomes.items()},
            "outcome_label_share": round(outcomes["exit_status_non_null"] / max(1, parsed), 4),
            "submitted_share": round(outcomes["submitted"] / max(1, parsed), 4),
            "task_instances": int(grp.size), "instances_with_2plus_rollouts": int((grp >= 2).sum()),
            "instances_with_3plus_rollouts": int((grp >= 3).sum()),
            "max_rollouts_per_instance": int(grp.max()) if grp.size else 0,
            "repos_200plus_rollouts": int(sum(1 for v in repos.values() if v >= 200)),
            "distinct_repos": int(len(repos)), "rollouts_with_6plus_assistant_turns": long6,
            "rollouts_with_an_observation_after_a_command": obs_pairs,
            "component_row_counts": {str(k): int(v) for k, v in comp_rows.items()},
            "median_component_kinds_per_rollout": float(np.median(kinds)) if kinds else None,
            "rollouts_with_2plus_component_kinds": two_kinds,
            "rollouts_with_uncertainty_language": with_uncert,
            "rollouts_with_negative_constraints": with_negcon,
            "rollouts_with_code_identifiers": with_concrete,
            "mean_abstract_markers": round(float(np.mean(abs_c)), 3) if abs_c else None,
            "mean_concrete_markers": round(float(np.mean(con_c)), 3) if con_c else None}


def agent_trove_structure_scan() -> dict:
    """What the abandoned substrate actually holds, measured rather than asserted (deviation W11-D02)."""
    files = sorted((AGENT_TROVE / "data").glob("*.parquet"))
    if not files:
        raise SystemExit(f"ABORT: no parquet under {AGENT_TROVE / 'data'}")
    rows = 0
    nn = collections.Counter()
    groups = collections.Counter()
    agents, sources, chars = collections.Counter(), collections.Counter(), []
    for f in files:
        pf = pq.ParquetFile(f)
        have = [c for c in AT_COLUMNS if c in pf.schema_arrow.names]
        for b in pf.iter_batches(batch_size=20000, columns=have):
            d = b.to_pydict()
            n = len(d[have[0]])
            rows += n
            for c in have:
                nn[c] += sum(1 for x in d[c] if x is not None and str(x).strip().lower() not in ("none", "nan", ""))
            agents.update(str(x) for x in d.get("agent", []))
            sources.update(str(a or b or "none") for a, b in zip(d.get("original_source", [None] * n),
                                                                 d.get("trace_source", [None] * n)))
            groups.update(str(t).split("__")[0] for t in d.get("trial_name", []))
    grp = pd.Series(groups, dtype=float)
    return {"corpus": "open-thoughts/AgentTrove, all shards, the small columns only", "shards": len(files),
            "rows": rows, "non_null_per_column": {str(k): int(v) for k, v in nn.items()},
            "outcome_column_names_with_any_value": [k for k in ("task_binary", "result", "verifier_output",
                                                                "judgment") if nn.get(k, 0) > 0],
            "task_prefixes": int(grp.size), "tasks_with_2plus_attempts": int((grp >= 2).sum()),
            "max_attempts_per_task": int(grp.max()) if grp.size else 0,
            "agents_200plus_rows": {str(k): int(v) for k, v in agents.items() if v >= 200},
            "sources_200plus_rows": int(sum(1 for v in sources.values() if v >= 200)),
            "distinct_sources": int(len(sources))}
GATES = {   # rules, thresholds and scopes carried over unchanged from the AgentTrove draft (W11-D02)
 "G1_trajectories_readable": {
     "rule": ">= 1,000 parsed rollouts with at least one assistant turn", "threshold": 1000, "scope": "design",
     "blocks": ["T131", "T137", "T138", "T140", "T142"]},
 "G2_outcome_label_populated": {
     "rule": ">= 500 rollouts carry a non-null outcome label, which is what separates a successful from a failed "
             "discourse in T131 and scores an attempt in T142", "threshold": 500, "scope": "design",
     "blocks": ["T131", "T142"]},
 "G3_repeated_attempts_of_one_task": {
     "rule": ">= 300 tasks with two or more recorded attempts - the organisational memory the carry-forward designs "
             "read", "threshold": 300, "scope": "design", "blocks": ["T137", "T138", "T140", "T142"]},
 "G4_trajectories_long_enough_to_compress": {
     "rule": ">= 500 rollouts with six or more assistant turns, below which a compression schedule has nothing to "
             "drop", "threshold": 500, "scope": "H1", "blocks": ["T140"]},
 "G5_two_plus_component_kinds": {
     "rule": ">= 1,000 rollouts whose agent prose carries at least two of the eight frozen component categories, "
             "since T137 asks which kind carries forward", "threshold": 1000, "scope": "H1", "blocks": ["T137"]},
 "G6_abstraction_contrast_computable": {
     "rule": ">= 1,000 rollouts containing at least one code identifier, the concrete end of the abstraction axis",
     "threshold": 1000, "scope": "H1", "blocks": ["T138"]},
 "G7_relation_classes_computable": {
     "rule": ">= 200 task groups with two or more attempts, at which a relation between two attempts (restatement, "
             "refinement, distant) can be classified at all", "threshold": 200, "scope": "H1", "blocks": ["T142"]},
 "G8_observation_pairs_present": {
     "rule": ">= 1,000 rollouts contain a user turn after an assistant command, i.e. a real observation the discourse "
             "responds to", "threshold": 1000, "scope": "H2", "blocks": ["T131"]},
 "G9_provenance_and_uncertainty_language": {
     "rule": ">= 500 rollouts each carrying uncertainty language, which with the provenance and exception categories "
             "is what T140's H2 asks survives a compression", "threshold": 500, "scope": "H2", "blocks": ["T140"]},
 "G10_agent_diversity_for_strata": {
     "rule": ">= 3 scaffold agents with >= 200 rollouts each, the stratum the carry-forward models report inside",
     "threshold": 3, "scope": "strata", "blocks": ["T137", "T138"],
     "note": "the estate's fixed 12-file draw is a single-scaffold corpus, so this gate is measured as one and is "
             "expected to fire; it scopes only the strata, and the stratum actually reported is the repository, "
             "which is named in every stratum row"},
 "G11_negative_constraints_present": {
     "rule": ">= 500 rollouts carrying a negative constraint, the class T140's hypothesis expects to be lost first",
     "threshold": 500, "scope": "H1", "blocks": ["T140"]},
 "G12_source_diversity": {
     "rule": ">= 3 sources with >= 200 rollouts each, so a pooled trajectory statistic is not one collection's "
             "artefact", "threshold": 3, "scope": "strata",
     "blocks": ["T131", "T137", "T138", "T140", "T142"]},
}


def apply_gates(m: dict) -> dict:
    checks = {"G1_trajectories_readable": m["rollouts_parsed"],
              "G2_outcome_label_populated": m["outcome_counts"].get("exit_status_non_null", 0),
              "G3_repeated_attempts_of_one_task": m["instances_with_2plus_rollouts"],
              "G4_trajectories_long_enough_to_compress": m["rollouts_with_6plus_assistant_turns"],
              "G5_two_plus_component_kinds": m["rollouts_with_2plus_component_kinds"],
              "G6_abstraction_contrast_computable": m["rollouts_with_code_identifiers"],
              "G7_relation_classes_computable": m["instances_with_2plus_rollouts"],
              "G8_observation_pairs_present": m["rollouts_with_an_observation_after_a_command"],
              "G9_provenance_and_uncertainty_language": m["rollouts_with_uncertainty_language"],
              "G10_agent_diversity_for_strata": 1,
              "G11_negative_constraints_present": m["rollouts_with_negative_constraints"],
              "G12_source_diversity": m["repos_200plus_rollouts"]}
    out = {}
    for k, g in GATES.items():
        v = checks[k]
        out[k] = {"measured": v, "fires": bool(v < g["threshold"]), "threshold": g["threshold"], "scope": g["scope"],
                  "blocks": list(g["blocks"]), "rule": g["rule"]}
        if "note" in g:
            out[k]["note"] = g["note"]
    fired = [k for k, v in out.items() if v["fires"]]
    whole = sorted({t for k in fired if out[k]["scope"] == "design" for t in out[k]["blocks"]})
    limited = {k: out[k]["scope"] for k in fired if out[k]["scope"] != "design"}
    return {"gates": out, "verdict": {"blocked_gates": fired, "blocked_whole_design": whole,
                                      "claim_limited": limited}}


def selftest() -> int:
    """The category, marker and grouping instruments proven on a hand-built rollout."""
    fence = chr(96) * 3 + "bash" + chr(10)
    msgs = [{"role": "user", "content": "the task is to fix the parser in /repo/x.py"},
            {"role": "assistant", "content": "I think the error says line 12 is wrong. First I will read the file "
                                             "because the documentation defines the format." + fence +
                                             "cat /repo/x.py" + chr(10) + chr(96) * 3},
            {"role": "user", "content": "Output: no such file or directory"},
            {"role": "assistant", "content": "Then I run the test and the result is a failure; finally I must not "
                                             "leave it broken." + fence + "pytest -q" + chr(10) + chr(96) * 3},
            {"role": "user", "content": "Output: 1 passed"}]
    traj = {"instance_id": "i1", "exit_status": "Submitted", "duration_sec": 42.0, "repo": "acme/thing",
            "messages": msgs}
    text = assistant_text(traj)
    comp = components_of(text)
    assert comp["procedure"] and comp["rationale"] and comp["provenance"] and comp["exception"], comp
    assert sum(comp.values()) >= 5
    mc = marker_counts(text)
    assert mc["uncert_n"] >= 1 and mc["negcon_n"] >= 1 and mc["concrete_n"] >= 1, mc
    drawn = [traj, dict(traj, instance_id="i1", exit_status="incomplete"), dict(traj, instance_id="i2")]
    m = measure(drawn)
    assert m["rollouts_parsed"] == 3 and m["task_instances"] == 2, m
    assert m["instances_with_2plus_rollouts"] == 1 and m["max_rollouts_per_instance"] == 2
    assert m["outcome_counts"]["exit_status_non_null"] == 3 and m["outcome_counts"]["submitted"] == 2
    assert m["rollouts_with_2plus_component_kinds"] == 3
    g = apply_gates(m)
    assert g["gates"]["G1_trajectories_readable"]["fires"] is True
    assert g["verdict"]["blocked_whole_design"] == ["T131", "T137", "T138", "T140", "T142"], g["verdict"]
    print("SELFTEST OK: component categories, marker counts, outcome labels and instance grouping land on a built "
          "rollout, and the gates fire on a three-rollout draw as they must")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=0, help="draw at most this many rollouts (0 = the frozen sample)")
    ap.add_argument("--agent-trove-scan", action="store_true", help="measure the abandoned substrate and stop")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    if a.agent_trove_scan:
        st = agent_trove_structure_scan()
        dest = W.write_raw(EXP, "wave11_agenttrove_structure_scan",
                           {"exp_id": EXP, "seed": SEED, "scan": st, "started_at": W.now(),
                            "wallclock_sec": round(time.time() - t0, 1),
                            "invocation": " ".join([sys.executable] + sys.argv),
                            "why": "recorded so the substrate wave 11 abandoned is documented by measurement rather "
                                   "than by assertion (deviation W11-D02)"})
        print(json.dumps(st, indent=1, ensure_ascii=False, default=str)[:1400])
        print("wrote", dest.name)
        return 0
    selftest()
    drawn, picks, rows_in_files, dupes = EF6.load_trajectories(a.rows or CAP)
    m = measure(drawn)
    g = apply_gates(m)
    art = {"exp_id": EXP, "seed": SEED, "files_read": picks, "rows_in_files": rows_in_files,
           "duplicate_rollout_rows_dropped_before_sampling": dupes,
           "rows_requested": a.rows or f"the frozen sample of {CAP} rollouts", "measured": m,
           "gate_rules": {k: v["rule"] for k, v in GATES.items()}, **g,
           "cluster_unit": "instance_id", "started_at": W.now(),
           "wallclock_sec": round(time.time() - t0, 1), "invocation": " ".join([sys.executable] + sys.argv),
           "run_cost": W.run_cost_row(EXP, t0, len(drawn), 0, "wave-11 premise census")}
    dest = W.write_raw(EXP, "wave11_premise_census", art)
    print(json.dumps({"measured": {k: v for k, v in m.items() if k != "component_row_counts"},
                      "verdict": art["verdict"],
                      "gates": {k: [v["measured"], v["fires"]] for k, v in art["gates"].items()}},
                     indent=1, ensure_ascii=False, default=str)[:2900])
    print(chr(10) + "wrote " + dest.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
