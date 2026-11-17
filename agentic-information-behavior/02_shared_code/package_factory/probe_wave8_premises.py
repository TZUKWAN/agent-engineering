"""EXP-0190: the wave-8 premise census - does the hermes release carry what five transcript designs ask for?

The substrate is the same seeded whole-release read waves 4 and 5 measured: 14,701 distinct trajectories (the release
stores 7,646 of them twice over, and `exp_wave4_features.load_trajectories` drops the duplicates before anything is
counted), 147,253 assistant turns, each with a think block, a body and zero or more tool calls, with tool responses
returned as observations. Wave 8's five designs ask that release for five different things:

* T171 - a hypothesis stated early enough for "later search" to be measurable against it;
* T175 - a turn that ends a trajectory, plus the marginal information, consistency, uncertainty, repetition and
  length a stop decision can be conditioned on;
* T176 - two behaviourally distinct ways a trajectory can go wrong, which needs error-marked observations and
  repeated calls, and which does **not** have a task outcome in this release;
* T182 - a plan whose specificity can be counted (entities, actions, ordering, constraints) before the actions run;
* T190 - an explicit verbal correction, and the call that follows it, so a change of behaviour can be compared to it.

Every gate names the sentence it scopes and the topic it blocks, and was written before a trajectory was opened. No
dependent variable of any design is computed here and no association is estimated: this is a prevalence and structure
census. Where a construct turns out to be rare the consequence is a claim limited by its own frozen sentence, not a
moved threshold. The instrument lexicons are wave 5's wherever wave 5 already had one, so a "hypothesis" or a "plan"
means the same thing in both waves; the correction, uncertainty, ordering, constraint and entity instruments are new
and are declared here.

    python 02_shared_code/package_factory/probe_wave8_premises.py [--traj-cap 400]
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
import pandas as pd                                               # noqa: E402
import wave_lib as W                                              # noqa: E402
import exp_wave4_features as EF                                   # noqa: E402  the same spine, the same reader
import probe_wave5_premises as P5                                 # noqa: E402  act and plan lexicons, unchanged
import topic_designs_wave4 as TD4                                 # noqa: E402  failure and sufficiency markers

EXP = "EXP-0190"
SEED = 42
STOP = P5.STOP
HYPOTHESIS = P5.ACT["hypothesis"] + P5.ACT_B["hypothesis"]
PLAN = P5.ACT["plan"] + P5.ACT_B["plan"]
EVIDENCE_REQUEST = P5.ACT["evidence_request"] + P5.ACT_B["evidence_request"]
SUFFICIENCY = list(getattr(TD4, "SUFFICIENCY_MARKERS", ["that is enough", "i have enough", "sufficient",
                                                        "already have", "no need to", "that answers",
                                                        "this confirms", "i now have", "that will do"]))
FAILURE = list(TD4.FAILURE_MARKERS)
# T190's verbal correction is an admission the agent makes about its own prior act. An error inside an observation is
# not a correction, so the two lists stay separate and a turn can carry one without the other.
CORRECTION = ["i was wrong", "my mistake", "i made a mistake", "i made an error", "my error", "i was mistaken",
              "i misread", "i misunderstood", "that was incorrect", "that is incorrect", "that's incorrect",
              "let me correct", "correction:", "i apologize", "i am sorry", "sorry,", "oops", "i should have",
              "wrong approach", "that did not work", "this did not work", "let me fix that", "i forgot",
              "typo"]
UNCERTAINTY = ["not sure", "unsure", "unclear", "i think", "maybe", "perhaps", "cannot confirm", "can not confirm",
               "not certain", "appears", "seems", "i believe", "presumably", "likely", "possibly", "hard to tell",
               "no idea", "wondering"]
ORDERING = ["first ", "then ", "next ", "finally", "after that", "before that", "step 1", "step 2", "step one",
            "1.", "2.", "3.", "4.", "at the end"]
CONSTRAINT = ["must", "should not", "must not", "only ", "exactly", "at least", "no more than", "required",
              "without ", "keep ", "avoid", "ensure", "preserve", "format", "duplicate", "dedup", "each ",
              "every ", "never ", "always "]
ACTION_VERB = ["read", "write", "create", "run", "execute", "check", "search", "grep", "list", "open", "edit",
               "install", "test", "verify", "print", "count", "parse", "convert", "copy", "move", "delete", "add",
               "remove", "fix", "update", "query", "inspect", "compute", "generate", "compare", "summarise",
               "summarize"]
ENTITY_RX = re.compile(r"([A-Za-z]:\\[\w\\.\-]+|/[\w./\-]{3,}|\b[\w\-]+\.(?:py|js|ts|csv|json|md|txt|sh|yml|yaml"
                       r"|ipynb)\b|`[^`\n]{2,60}`|\"[^\n\"]{2,60}\"|'[^'\n]{2,60}'|\b[A-Z][a-z]+[A-Z]\w*\b)")
CALL_RX = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.S)


def words(s) -> set:
    return P5.words(s)


def call_args(v: str) -> list:
    """The tool calls inside one assistant message as (name, canonical arguments) pairs, in the order they appear."""
    out = []
    for m in CALL_RX.finditer(str(v)):
        try:
            j = json.loads(m.group(1))
        except Exception:                                          # noqa: BLE001 - a broken call is counted, not used
            out.append(("unparsed", ""))
            continue
        args = json.dumps(j.get("arguments"), sort_keys=True, ensure_ascii=False)[:400] \
            if j.get("arguments") is not None else ""
        out.append((str(j.get("name") or ""), args))
    return out


def counts_of(low: str, terms) -> int:
    return sum(1 for t in terms if t in low)


def trajectory_facts(row) -> dict:
    """One release row -> the turn and observation facts the gates and the frame both read, in a single pass."""
    msgs = [dict(m) for m in (list(row.conversations) if row.conversations is not None else [])]
    turns, obs = [], []
    for m in msgs:
        role, v = str(m.get("from")), str(m.get("value"))
        if role in ("tool", "function", "observation"):
            for nm, content in EF.parse_obs(v):
                obs.append((str(nm or ""), content or ""))
            continue
        if role not in ("gpt", "assistant"):
            continue
        low = str(v).lower()
        body = CALL_RX.sub(" ", low)
        calls = call_args(v)
        turns.append({"n_calls": len(calls), "calls": calls, "chars": len(str(v)),
                      "has_think": "<think>" in low,
                      "hypo": counts_of(body, HYPOTHESIS), "plan": counts_of(body, PLAN),
                      "evid_req": counts_of(body, EVIDENCE_REQUEST), "suffic": counts_of(body, SUFFICIENCY),
                      "correct": counts_of(body, CORRECTION), "uncert": counts_of(body, UNCERTAINTY),
                      "ordering": counts_of(body, ORDERING), "constraint": counts_of(body, CONSTRAINT),
                      "verbs": counts_of(" " + body, [" " + a for a in ACTION_VERB]),
                      "entities": len(set(ENTITY_RX.findall(str(v)))), "words": words(body)})
    ends_on_gpt = bool(msgs) and str(msgs[-1].get("from")) in ("gpt", "assistant")
    return {"turns": turns, "obs": obs, "task": str(row.task or ""), "category": str(row.category or ""),
            "sub": str(row.subcategory or ""), "ends_on_gpt": int(ends_on_gpt),
            "outcome_field": None}


GATES = {   # rule, threshold, and the topic(s) the sentence scopes - all frozen before any value was measured
 "G1_trajectories_parseable": {
     "rule": ">= 0.95 of drawn trajectories yield at least one readable assistant turn", "threshold": 0.95,
     "scope": "design", "blocks": ["T171", "T175", "T176", "T182", "T190"]},
 "G2_task_instruction_present": {
     "rule": ">= 0.90 of trajectories carry a non-empty task instruction, which is what 'later search' is later than "
             "and what an entity count counts against", "threshold": 0.90, "scope": "design",
     "blocks": ["T171", "T182"]},
 "G3_early_hypothesis_trajectories": {
     "rule": ">= 200 trajectories state a hypothesis within their first two assistant turns - the arm T171 compares "
             "against", "threshold": 200, "scope": "H1", "blocks": ["T171"]},
 "G4_trajectories_with_later_turns": {
     "rule": ">= 500 trajectories have >= 4 assistant turns, so a turn-by-turn concentration profile has a later half",
     "threshold": 500, "scope": "design", "blocks": ["T171", "T175", "T182"]},
 "G5_terminal_turn_identifiable": {
     "rule": ">= 0.95 of trajectories end on an assistant turn, so STOP is a measurable event rather than a guess "
             "about a truncated log", "threshold": 0.95, "scope": "design", "blocks": ["T175", "T176"]},
 "G6_observations_parseable": {
     "rule": ">= 0.80 of trajectories return at least one observation for every call they emitted - marginal "
             "information is computed from that content", "threshold": 0.80, "scope": "design",
     "blocks": ["T175", "T176", "T190"]},
 "G7_error_marked_observations": {
     "rule": ">= 0.05 of observations carry a failure marker, the conditioning event T176's premature arm and T190's "
             "correction arm both stand on", "threshold": 0.05, "scope": "H1", "blocks": ["T176"]},
 "G8_verbal_corrections": {
     "rule": ">= 200 trajectories contain at least one explicit self-correction from the frozen list; below this the "
             "construct T190 names is rare in this corpus rather than uninformative", "threshold": 200,
     "scope": "design", "blocks": ["T190"]},
 "G9_plan_specificity_computable": {
     "rule": ">= 200 trajectories have a first assistant turn carrying at least two ordering markers and at least two "
             "action verbs, the low end of 'a plan whose specificity can be counted'", "threshold": 200,
     "scope": "H1", "blocks": ["T182"]},
 "G10_repeated_call_trajectories": {
     "rule": ">= 200 trajectories re-issue an identical (name, arguments) call - the observable over-search arm T176 "
             "and the behavioural-change baseline T190 both need", "threshold": 200, "scope": "H1",
     "blocks": ["T176", "T190"]},
 "G11_cluster_count": {
     "rule": ">= 1,000 trajectories readable at all, so a traj_id-clustered interval exists for every design",
     "threshold": 1000, "scope": "design", "blocks": ["T171", "T175", "T176", "T182", "T190"]},
 "G12_category_breadth": {
     "rule": ">= 5 task categories with >= 100 trajectories each, which is the stratum T175 and T176 report inside",
     "threshold": 5, "scope": "strata", "blocks": ["T175", "T176"]},
 "G13_outcome_label_available": {
     "rule": "the release carries a per-trajectory task outcome (success, reward, pass, exit status) that a "
             "premature-versus-over-search mismatch could be scored against. This gate is reported as measured "
             "either way, because the sentence it scopes - T176's - can be narrowed to behaviour without moving any "
             "threshold, and a fired gate here is a statement about what the release does not record",
     "threshold": 1, "scope": "design", "blocks": ["T176"]},
}


def measure(df: pd.DataFrame) -> dict:
    n = int(len(df))
    parsed = task_ok = hypo_early = long_enough = ends_gpt = 0
    obs_total = obs_err = 0
    calls_total = calls_unparsed = answered = 0
    corr_traj = repeat_traj = plan_traj = 0
    cats = collections.Counter()
    turn_counts, obs_per_traj, entities_first, verbs_first = [], [], [], []
    correction_examples, first_turn_words = [], None
    for r in df.itertuples(index=False):
        f = trajectory_facts(r)
        t = f["turns"]
        if not t:
            continue
        parsed += 1
        if f["task"].strip():
            task_ok += 1
        cats[f["category"]] += 1
        turn_counts.append(len(t))
        obs_per_traj.append(len(f["obs"]))
        if any(x["hypo"] for x in t[:2]):
            hypo_early += 1
        if len(t) >= 4:
            long_enough += 1
        ends_gpt += f["ends_on_gpt"]
        if any(x["correct"] for x in t):
            corr_traj += 1
            if len(correction_examples) < 3:
                i = next(k for k, x in enumerate(t) if x["correct"])
                correction_examples.append({"turn_index": i + 1, "markers": f["turns"][i]["correct"],
                                            "excerpt": " ".join(str(t[i]["calls"]))[:90]})
        seen = set()
        dup = False
        for x in t:
            for c in x["calls"]:
                calls_total += 1
                calls_unparsed += int(c[0] == "unparsed")
                if c in seen:
                    dup = True
                seen.add(c)
        repeat_traj += int(dup)
        first = t[0]
        if first["ordering"] >= 2 and first["verbs"] >= 2:
            plan_traj += 1
        entities_first.append(first["entities"])
        verbs_first.append(first["verbs"])
        if first_turn_words is None:
            first_turn_words = sorted(first["words"])[:8]
        err_here = sum(1 for _, o in f["obs"] if any(x in o.lower() for x in FAILURE))
        obs_err += err_here
        obs_total += len(f["obs"])
        answered += int(sum(1 for x in t if x["n_calls"] > 0) <= len(f["obs"]))
    per_cat = {k: int(v) for k, v in cats.items() if v >= 100}
    return {"corpus": "hermes-agent-reasoning-traces, whole release after the duplicate-trajectory drop",
            "trajectories": n, "trajectories_parsed": parsed,
            "trajectory_parse_share": round(parsed / max(1, n), 4),
            "task_instruction_share": round(task_ok / max(1, parsed), 4),
            "assistant_turns_total": int(sum(turn_counts)),
            "median_turns_per_trajectory": float(pd.Series(turn_counts).median()) if turn_counts else None,
            "mean_turns_per_trajectory": round(float(pd.Series(turn_counts).mean()), 2) if turn_counts else None,
            "trajectories_with_4plus_turns": long_enough,
            "trajectories_stating_a_hypothesis_in_the_first_two_turns": hypo_early,
            "trajectories_ending_on_an_assistant_turn_share": round(ends_gpt / max(1, parsed), 4),
            "observations_total": obs_total,
            "observations_with_a_failure_marker_share": round(obs_err / max(1, obs_total), 4),
            "calls_total": calls_total, "calls_unparsed_share": round(calls_unparsed / max(1, calls_total), 4),
            "trajectories_answering_every_call_share": round(answered / max(1, parsed), 4),
            "trajectories_with_a_repeated_identical_call": repeat_traj,
            "trajectories_with_an_explicit_self_correction": corr_traj,
            "trajectories_with_a_countable_first_turn_plan": plan_traj,
            "median_entities_in_the_first_turn": float(pd.Series(entities_first).median()) if entities_first else None,
            "median_action_verbs_in_the_first_turn": float(pd.Series(verbs_first).median()) if verbs_first else None,
            "categories_with_100plus_trajectories": len(per_cat), "category_counts": per_cat,
            "mean_observations_per_trajectory": round(float(pd.Series(obs_per_traj).mean()), 2) if obs_per_traj else None,
            "sample_first_turn_words": first_turn_words,
            "correction_examples": correction_examples,
            "outcome_field_present": False,
            "outcome_field_note": "the release ships id, conversations, tools, category, subcategory and task only - "
                                  "there is no success, reward, pass or exit-status column on any row, so a "
                                  "premature-versus-over-search mismatch has no reference label here and T176 is "
                                  "specified on behaviour alone"}


def apply_gates(m: dict) -> dict:
    checks = {"G1_trajectories_parseable": m["trajectory_parse_share"],
              "G2_task_instruction_present": m["task_instruction_share"],
              "G3_early_hypothesis_trajectories":
                  m["trajectories_stating_a_hypothesis_in_the_first_two_turns"],
              "G4_trajectories_with_later_turns": m["trajectories_with_4plus_turns"],
              "G5_terminal_turn_identifiable": m["trajectories_ending_on_an_assistant_turn_share"],
              "G6_observations_parseable": m["trajectories_answering_every_call_share"],
              "G7_error_marked_observations": m["observations_with_a_failure_marker_share"],
              "G8_verbal_corrections": m["trajectories_with_an_explicit_self_correction"],
              "G9_plan_specificity_computable": m["trajectories_with_a_countable_first_turn_plan"],
              "G10_repeated_call_trajectories": m["trajectories_with_a_repeated_identical_call"],
              "G11_cluster_count": m["trajectories_parsed"],
              "G12_category_breadth": m["categories_with_100plus_trajectories"],
              "G13_outcome_label_available": int(bool(m["outcome_field_present"]))}
    out = {}
    for k, g in GATES.items():
        v = checks[k]
        out[k] = {"measured": v, "fires": bool(v < g["threshold"]) if k != "G13_outcome_label_available"
                  else bool(v < g["threshold"]), "threshold": g["threshold"], "scope": g["scope"],
                  "blocks": list(g["blocks"]), "rule": g["rule"]}
    fired = [k for k, v in out.items() if v["fires"]]
    whole = sorted({t for k in fired for t in out[k]["blocks"] if out[k]["scope"] == "design"})
    limited = {k: out[k]["scope"] for k in fired if out[k]["scope"] != "design"}
    return {"gates": out, "verdict": {"blocked_gates": fired, "blocked_whole_design": whole,
                                      "claim_limited": limited}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--traj-cap", type=int, default=0, help="draw at most this many trajectories (0 = the whole "
                                                            "release, which is what the freeze was written against)")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    df, n_files = EF.load_trajectories(a.traj_cap or 10 ** 9)
    m = measure(df)
    g = apply_gates(m)
    art = {"exp_id": EXP, "seed": SEED, "files_read": n_files, "rows_requested": a.traj_cap or "all trajectories",
           "duplicate_traj_ids_dropped_before_sampling": int(df.attrs.get("duplicate_traj_ids_dropped") or 0),
           "measured": m, "gate_rules": {k: v["rule"] for k, v in GATES.items()}, **g,
           "cluster_unit": "traj_id", "started_at": W.now(), "wallclock_sec": round(time.time() - t0, 1),
           "invocation": " ".join([sys.executable] + sys.argv),
           "run_cost": W.run_cost_row(EXP, t0, int(len(df)), 0, "wave-8 premise census")}
    dest = W.write_raw(EXP, "wave8_premise_census", art)
    print(json.dumps({"measured": m, "verdict": art["verdict"],
                      "gates": {k: [v["measured"], v["fires"]] for k, v in art["gates"].items()}},
                     indent=1, ensure_ascii=False, default=str)[:3000])
    print("\nwrote", dest.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
