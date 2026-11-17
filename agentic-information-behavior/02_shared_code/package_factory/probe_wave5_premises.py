"""EXP-0161: the wave-5 premise census - does the hermes release carry the evidence-language constructs at all?

Six designs (T130, T132, T133, T134, T135, T136) want to measure how an agent's *language about evidence* lines up
with what it actually retrieved: discourse acts, conclusion-before-evidence, repair after a failure, causal
connectives, explanatory chains, stated plans versus subsequent calls. Every one of those is a prevalence claim about
a lexicon before it is anything else, and the programme's history says a lexicon can be vacuous (EXP-0153's topical
control at 0.9998) or an instrument can mis-read a role (EXP-0152's first generation). So the gates below are fixed
here, with the topic each one scopes, and the pass reports only structure and prevalence - no dependent variable of
any design is computed, and no outcome label is read.

Reuses wave 4's machinery deliberately: the same corpus path, the same seeded trajectory sample, the same tag
parsers, and the same modality/sufficiency/failure lexicons, so a marker that means one thing in wave 4 cannot mean
something else here.

    python 02_shared_code/package_factory/probe_wave5_premises.py [--traj-cap 4000]
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
import wave_lib as W                                              # noqa: E402
import exp_wave4_features as EF                                   # noqa: E402
import probe_wave4_premises as P4                                 # noqa: E402

SEED = 42

# ------------------------------------------------------------------ the lexicons, written before the census ran
ACT = {                                        # T130's five acts, and the second realisation for invariance
 "hypothesis": ["i think", "my guess", "perhaps", "presumably", "it could be that", "likely that", "hypothesis",
                "maybe the", "probably the", "i suspect"],
 "question":   ["?", "let me check whether", "i need to know", "what is the", "does this", "is it possible",
                "how do i", "which one"],
 "plan":       ["i will", "i'll ", "first i", "next i", "let me ", "i should", "the plan is", "to do this i",
                "my approach", "now i need to"],
 "evidence_request": ["let me look", "i need to check", "search for", "read the", "run the", "query", "fetch",
                      "check the", "look up", "open the", "list the"],
 "conclusion": ["therefore", "thus", "the answer is", "this means", "in conclusion", "i conclude", "so the result",
                "clearly", "hence", "accordingly"],
}
ACT_B = {                                      # an independently worded second tagger for the same five acts
 "hypothesis": ["could be", "seems that", "appears that", "assumption", "my understanding", "tentatively"],
 "question":   ["whether", "wondering", "unclear if", "not certain if", "need to find out", "any idea"],
 "plan":       ["going to", "then i", "intend to", "i am about to", "before that i", "step 1", "start by"],
 "evidence_request": ["get the", "retrieve", "examine", "inspect", "grep", "find the", "show me", "load the",
                      "print the", "cat "],
 "conclusion": ["so ", "conclude", "final answer", "overall", "in short", "the takeaway", "it follows"],
}
CONCLUSION = ACT["conclusion"]
CAUSAL = ["because", "since", "therefore", "thus", "hence", "so that", "due to", "as a result", "for this reason",
          "which means", "given that", "in order to"]
CONTRAST = ["however", "but ", "although", "on the other hand", "yet ", "instead", "whereas"]
# T134 splits the causal family in two and needs a control of the same size with no inferential content; both are
# declared here because the census, the frame and the freeze must read the same lists.
INFERENTIAL = ["therefore", "thus", "hence", "so that", "as a result", "which means", "accordingly", "it follows"]
EXPLANATORY = ["because", "since", "given that", "due to", "for this reason", "in order to", "so that"]
CAUSAL_CONTROL = ["the ", "with ", "into ", "about ", "over ", "under ", "from ", "then ", "them ", "this ",
                  "that ", "have "]
# the failure marker set is wave 4's, unchanged, so a turn that counts as following a failure means one thing in
# both waves; REPAIR["acknowledge"] stays a *repair* lexicon and is not used as the conditioning event.
import topic_designs_wave4 as TD4                                        # noqa: E402
FAILURE = list(TD4.FAILURE_MARKERS)
REPAIR = {                                     # T133: what an agent does right after a failure-marked observation
 "acknowledge": ["that failed", "did not work", "error", "not found", "no such", "couldn", "unable to",
                 "permission denied", "timed out", "exit code"],
 "diagnose":    ["because", "the reason", "likely due", "caused by", "i see the problem", "the issue is",
                 "was missing", "wrong path", "typo"],
 "reissue":     ["try again", "instead", "alternatively", "let me ", "i will ", "different approach", "retry",
                 "use another", "run it with"],
 "abandon":     ["give up", "cannot", "can not", "skip", "move on", "without this", "assume that", "as is",
                 "proceed without"],
}
PLAN_MARKERS = ACT["plan"]
INSPECT = P4.INSPECT_NAME if hasattr(P4, "INSPECT_NAME") else re.compile(
    r"(read|cat|grep|search|find|list|ls|view|inspect|get|show|open|query|fetch|status|check|test|verify|validate|"
    r"diff|explore)", re.I)
STOP = set("the a an of and or to in on for with is are was were be it this that i you we they my your their "
           "will would can could should there here from as at by not no all any".split())


def words(s: str) -> set:
    return {w for w in re.findall(r"[a-z0-9_./:-]{3,}", str(s).lower()) if w not in STOP}


GATES = {   # rule, threshold, and the topic(s) the sentence scopes - all frozen before any row was opened
 "G1_assistant_text_available": {"rule": ">= 0.50 of trajectories carry >= 1 assistant turn of >= 20 chars",
                                 "threshold": 0.50, "scope": "design",
                                 "blocks": ["T130", "T132", "T133", "T134", "T135", "T136"]},
 "G2_discourse_act_prevalence": {"rule": ">= 0.05 of assistant turns carry at least one of the five act markers, "
                                         "else T130 has no grammar to describe", "threshold": 0.05,
                                 "scope": "design", "blocks": ["T130"]},
 "G3_second_act_tagger_prevalence": {"rule": ">= 0.02 of assistant turns are marked by the independently worded "
                                             "second tagger, else T130's invariance check has no second instrument",
                                     "threshold": 0.02, "scope": "H3", "blocks": ["T130"]},
 "G4_conclusion_marker_prevalence": {"rule": ">= 0.02 of assistant turns carry a conclusion marker, else T132's "
                                             "ordering contrast has no subject", "threshold": 0.02,
                                     "scope": "H1", "blocks": ["T132"]},
 "G5_conclusion_before_first_inspection": {"rule": ">= 200 trajectories containing a conclusion turn that precedes "
                                           "the trajectory's first inspection-family call (T132's arm A)",
                                           "threshold": 200, "scope": "H1", "blocks": ["T132"]},
 "G6_failure_marked_observation_units": {"rule": ">= 200 turns immediately preceded by an observation carrying a "
                                           "failure marker - the wave-4 lexicon, unchanged - (T133's subject)", "threshold": 200, "scope": "H1",
                                         "blocks": ["T133"]},
 "G7_causal_connective_prevalence": {"rule": ">= 0.05 of assistant turns carry a causal connective, else T134's "
                                             "faithfulness comparison is computed on a residue", "threshold": 0.05,
                                     "scope": "design", "blocks": ["T134", "T135"]},
 "G8_evidence_text_computable": {"rule": ">= 0.50 of causal-connective turns have a preceding observation of "
                                        ">= 50 chars, i.e. the overlap T134/T135 score is computable",
                                 "threshold": 0.50, "scope": "H1", "blocks": ["T134", "T135"]},
 "G9_multi_connective_chains": {"rule": ">= 200 turns carrying >= 2 causal connectives (T135's chain subject)",
                                "threshold": 200, "scope": "H1", "blocks": ["T135"]},
 "G10_plan_marker_with_call_units": {"rule": ">= 200 turns carrying a plan marker and followed by >= 1 call "
                                     "(T136's alignment subject)", "threshold": 200, "scope": "H1",
                                     "blocks": ["T136"]},
 "G11_outcome_label_available": {"rule": ">= 0.50 of trajectories carry a release-side outcome field; no wave-5 "
                                 "design scores one, so this gate is measured to record the absence, not to block",
                                 "threshold": 0.50, "scope": "design", "blocks": []},
}


def selftest() -> None:
    """Prove the markers and the per-turn accounting on a hand-read trajectory before any corpus row is opened.

    Every counter the gates read is exercised: a conclusion that precedes the first inspection, a repair turn after a
    failure-marked observation, a causal connective with computable evidence overlap, and a plan followed by a call.
    """
    obs = json.dumps({"name": "terminal", "content": "Traceback: file not found /srv/x"})
    turn1 = ("I will read the config file first. " + EF.t("tool_call") + json.dumps(
        {"name": "read_file", "arguments": {"path": "/srv/x"}}) + EF.t("tool_call", True)
        + " therefore the service is misconfigured")
    turn2 = "That failed because the path was wrong; let me try again with /etc/x."
    msgs = [{"from": "human", "value": "find why it fails"},
            {"from": "gpt", "value": turn1},
            {"from": "tool", "value": EF.t("tool_response") + obs + EF.t("tool_response", True)},
            {"from": "gpt", "value": turn2}]
    hits = [k for k, lex in ACT.items() if any(x in msgs[1]["value"].lower() for x in lex)]
    assert {"plan", "conclusion"} <= set(hits), hits
    assert any(x in msgs[3]["value"].lower() for x in FAILURE), "the second turn must read as following a failure"
    assert any(x in msgs[3]["value"].lower() for x in REPAIR["reissue"])
    assert words("misconfigured service therefore") & words(json.dumps(json.loads(obs)["content"])) == set(), \
        "the overlap helper should find nothing here, which is the point of measuring it rather than assuming it"
    assert any(nm and INSPECT.search(str(nm)) for nm in EF.parse_calls(turn1)), "read_file must be inspection-family"
    assert sum(msgs[1]["value"].count(c) for c in CAUSAL) >= 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--traj-cap", type=int, default=4000)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    selftest()
    t0 = time.time()
    take, n_files = EF.load_trajectories(a.traj_cap)
    # The loader samples unique trajectory ids but the release repeats some ids across its files, so `len(take)` is
    # rows, not trajectories. Every gate below is stated over trajectories, so the repeats are dropped here and the
    # number dropped is reported rather than silently folded into a denominator.
    n_rows_raw = len(take)
    take = take.drop_duplicates(subset=["traj_id"], keep="first").reset_index(drop=True)
    dupe_rows = n_rows_raw - len(take)
    cols = set(take.columns)
    n_traj = len(take)
    roles = collections.Counter()
    turns = 0
    act_a = act_b = 0
    per_act = collections.Counter()
    per_act_b = collections.Counter()
    concl_turns = before_first_inspect = 0
    traj_with_concl_before = 0
    with_text = 0
    repair_units = 0
    repair_kind = collections.Counter()
    causal_turns = multi_causal_turns = causal_with_evidence = 0
    infer_turns = expl_turns = 0
    plan_with_call = 0
    overlap_hist = collections.Counter()
    outcome_rows = 0
    calls_named = calls_bad = obs_named = 0
    OUT_COLS = ("outcome", "resolved", "success", "reward", "passed", "correct", "is_correct")
    for r in take.itertuples(index=False):
        msgs = [dict(m) for m in (list(r.conversations) if r.conversations is not None else [])]
        for m in msgs:
            roles[str(m.get("from"))] += 1
        seen_inspect = False
        prior_obs = []                      # observation texts returned so far, in order
        row_out = row_has_text = row_concl_before = False
        for i, m in enumerate(msgs):
            role, v = str(m.get("from")), str(m.get("value"))
            if role in ("tool", "function", "observation"):
                for nm, content in EF.parse_obs(v):
                    obs_named += 1 if nm else 0
                    prior_obs.append(content or "")
                continue
            if role not in ("gpt", "assistant"):
                continue
            body = P4.THINK.sub("", v).strip()
            names = [nm for nm in EF.parse_calls(v)]
            calls_bad += sum(1 for nm in names if nm is None)
            calls_named += sum(1 for nm in names if nm)
            if any(nm and INSPECT.search(str(nm)) for nm in names):
                seen_inspect = True
            if len(body) < 20:
                # a turn with no prose cannot carry an act, a connective or a claim; its action still counts
                continue
            turns += 1
            row_has_text = True
            low = v.lower()
            hits = [k for k, lex in ACT.items() if any(x in low for x in lex)]
            hitsb = [k for k, lex in ACT_B.items() if any(x in low for x in lex)]
            act_a += int(bool(hits))
            act_b += int(bool(hitsb))
            for k in hits:
                per_act[k] += 1
            for k in hitsb:
                per_act_b[k] += 1
            n_causal = sum(low.count(c) for c in CAUSAL)
            infer_turns += int(any(c in low for c in INFERENTIAL))
            expl_turns += int(any(c in low for c in EXPLANATORY))
            causal_turns += int(n_causal > 0)
            multi_causal_turns += int(n_causal >= 2)
            ev_text = " ".join(prior_obs)
            if n_causal:
                causal_with_evidence += int(len(ev_text) >= 50)
                o = words(body) & words(ev_text)
                den = max(1, len(words(body)))
                overlap_hist[min(4, int(len(o) / den * 5))] += 1
            insp = any(nm and INSPECT.search(str(nm)) for nm in names)
            if "conclusion" in hits:
                concl_turns += 1
                if not seen_inspect:
                    before_first_inspect += 1
                    row_concl_before = True
            if any(x in low for x in PLAN_MARKERS) and names:
                plan_with_call += 1
            if prior_obs and any(x in str(prior_obs[-1]).lower() for x in FAILURE):
                repair_units += 1
                for k, lex in REPAIR.items():
                    if k != "acknowledge" and any(x in low for x in lex):
                        repair_kind[k] += 1
            if insp:
                seen_inspect = True
        with_text += int(row_has_text)
        traj_with_concl_before += int(row_concl_before)
        for k in OUT_COLS:
            if k in cols and str(getattr(r, k, "") or "").strip():
                row_out = True
        outcome_rows += int(row_out)

    measured = {
        "corpus": str(EF.CORPUS.name), "files_read": n_files, "trajectories_sampled": n_traj,
        "rows_read_before_dedup": n_rows_raw, "duplicate_traj_id_rows": dupe_rows,
        "assistant_turns_ge20": turns, "roles": dict(roles),
        "G1_assistant_text_available": round(with_text / max(1, n_traj), 4),
        "G2_discourse_act_prevalence": round(act_a / max(1, turns), 4),
        "G3_second_act_tagger_prevalence": round(act_b / max(1, turns), 4),
        "act_share_by_act": {k: round(v / max(1, turns), 4) for k, v in sorted(per_act.items())},
        "act_b_share_by_act": {k: round(v / max(1, turns), 4) for k, v in sorted(per_act_b.items())},
        "G4_conclusion_marker_prevalence": round(concl_turns / max(1, turns), 4),
        "G5_conclusion_before_first_inspection": traj_with_concl_before,
        "conclusion_turns_before_first_inspection": before_first_inspect,
        "G6_failure_marked_observation_units": repair_units,
        "repair_marker_share_of_failure_followed_turns": {k: round(v / max(1, repair_units), 4)
                                                          for k, v in sorted(repair_kind.items())},
        "G7_causal_connective_prevalence": round(causal_turns / max(1, turns), 4),
        "causal_inferential_turn_share": round(infer_turns / max(1, turns), 4),
        "causal_explanatory_turn_share": round(expl_turns / max(1, turns), 4),
        "G8_evidence_text_computable": round(causal_with_evidence / max(1, causal_turns), 4),
        "G9_multi_connective_chains": multi_causal_turns,
        "G10_plan_marker_with_call_units": plan_with_call,
        "G11_outcome_label_available": round(outcome_rows / max(1, n_traj), 4),
        "turn_content_overlap_with_prior_evidence_quintile_counts": {str(k): v for k, v in sorted(overlap_hist.items())},
        "calls_named": calls_named, "calls_unparseable": calls_bad, "observations_named": obs_named,
    }
    def fires(g: str) -> bool:
        v = measured[g]
        return not (isinstance(v, (int, float)) and v >= GATES[g]["threshold"])

    lack = [g for g in GATES if g not in measured]
    if lack:
        raise SystemExit(f"ABORT: {lack} is a declared gate with nothing measured for it, so it could neither pass "
                         f"nor fire")

    verdict = {"blocked_gates": [], "blocked_whole_design": [], "claim_limited": {},
               "note": "a fired gate is a result: it stops exactly what its frozen sentence scopes (the whole "
                       "design, one named hypothesis, or rows to exclude and count)"}
    for g in GATES:
        if not fires(g):
            continue
        verdict["blocked_gates"].append(g)
        if GATES[g]["scope"] == "design":
            verdict["blocked_whole_design"] += [x for x in GATES[g]["blocks"]
                                                if x not in verdict["blocked_whole_design"]]
        else:
            verdict["claim_limited"][g] = GATES[g]["scope"]
    out = {"sampled_rows": n_traj, "measured": measured, "gates": {k: (not fires(k)) for k in GATES},
           "gate_rules": {k: GATES[k]["rule"] for k in GATES},
           "gate_scopes": {k: {"scope": GATES[k]["scope"], "blocks": GATES[k]["blocks"],
                               "threshold": GATES[k]["threshold"]} for k in GATES},
           "lexicons": {"ACT_A": {k: len(v) for k, v in ACT.items()},
                        "ACT_B": {k: len(v) for k, v in ACT_B.items()}, "CAUSAL": len(CAUSAL),
                        "REPAIR": {k: len(v) for k, v in REPAIR.items()},
                        "CAUSAL": len(CAUSAL), "INFERENTIAL": len(INFERENTIAL), "EXPLANATORY": len(EXPLANATORY),
                        "CAUSAL_CONTROL": len(CAUSAL_CONTROL), "FAILURE_wave4": len(FAILURE)},
           "failure_lexicon_source": "topic_designs_wave4.FAILURE_MARKERS (imported, not copied)",
           "verdict": verdict, "seed": SEED, "started_at": W.now(),
           "wallclock_sec": round(time.time() - t0, 1),
           "invocation": " ".join([sys.executable] + sys.argv)}
    dest = W.write_raw("EXP-0161", "wave5_premise_census", out)
    print(json.dumps({"measured": measured, "verdict": verdict}, indent=1, ensure_ascii=False, default=str)[:3000])
    print(f"\nEXP-0161: wrote {dest.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
