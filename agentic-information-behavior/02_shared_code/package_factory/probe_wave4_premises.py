"""EXP-0152: the wave-4 premise census - structure and prevalence only, no outcome read.

Wave 4 asks whether an agent's *language about its own uncertainty* tracks what it then does (T123 hedging ->
verification action, T124 commitment order, T126 contradiction -> modality shift, T127 sufficiency claims ->
stopping, T191 verification count -> outcome). Every one of those designs stands or falls on three measurable
preconditions, and this programme has already been bitten twice by assuming them:

* the corpus must carry assistant free text at all (Toucan's routing rows carry a synthetic dialogue, EXP-0118);
* the behavioural outcome must NOT be a function of the same text, or the association is mechanical. EXP-0076
  measured exactly that trap on AgentNet, where `last_step_correct` judges the action the reflection comments on,
  so verification language scored at chance (AUC 0.489) and repair language inverted (0.165);
* the construct's cell must hold enough rows to estimate (a 2.9% negation share killed T112/T117/T121).

So this census reads roles, marker prevalence and cell sizes, and fixes the gates below *before* any estimate is
computed. Nothing here touches an effect, a coefficient or a p-value.

    python 02_shared_code/package_factory/probe_wave4_premises.py [--rows 4000]
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import pathlib
import random
import re
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import wave_lib as W                                              # noqa: E402

ROOT = W.ROOT
CORPUS = pathlib.Path(str(W.ROOT.parent) + "/MATLABINTOKEN/datasets/lambda/hermes-agent-reasoning-traces")

# ---------------------------------------------------------------- the three lexicons, fixed before the census
# Modality/hedging: the classic epistemic-possibility family plus explicit uncertainty statements.
MODAL = ["may ", "might ", "could ", "possibly", "probably", "perhaps", "unclear", "unsure", "not sure",
         "seems", "appears to", "likely", "unlikely", "assume", "assumption", "i think", "believe",
         "if i read", "need to verify", "to confirm", "not certain", "could be", "should be able"]
# Sufficiency / information-state claims: the agent asserting it has or has not got enough.
SUFFIC = ["enough", "sufficient", "that should do", "that will do", "we have what", "insufficient",
          "not enough", "more information", "need more", "missing", "complete information", "all the information"]
# Inspection-as-behaviour, read off the called tool's NAME rather than off any prose - that is the independence the
# designs need, and the reason EXP-0076's AgentNet trap cannot recur here.
INSPECT_NAME = re.compile(r"(^|_)(read|cat|grep|search|find|list|ls|view|inspect|get|show|open|query|fetch|"
                          r"status|check|test|verify|validate|diff|explore)(_|$)|read_file|search_files|"
                          r"session_search|skill_view|skills_list", re.I)
OUTCOME_COLS = ("outcome", "resolved", "success", "reward", "passed", "correct", "is_correct")
WRITE_NAME = re.compile(r"(^|_)(write|edit|patch|create|delete|remove|commit|push|deploy|install)(_|$)"
                        r"|write_file", re.I)
# `terminal`, `execute_code` and `process` can read or produce depending on what was run inside them, so they form a
# third family. Lumping them into "production" made 68% of calls look like writes and hid the inspection share.
EXEC_NAME = re.compile(r"(^|_)(terminal|execute_code|process|bash|shell|run_command)(_|$)", re.I)
LT, GT = chr(60), chr(62)         # the message format is XML-ish; built from codes so this file stays readable


def t(name: str, close: bool = False) -> str:
    return f"{LT}{'/' if close else ''}{name}{GT}"


CALL = re.compile(re.escape(t("tool_call")) + r"(.*?)" + re.escape(t("tool_call", True)), re.S)
RESP = re.compile(re.escape(t("tool_response")) + r"(.*?)" + re.escape(t("tool_response", True)), re.S)
THINK = re.compile(re.escape(t("think")) + r"(.*?)" + re.escape(t("think", True)), re.S)

GATES = {   # frozen here, evaluated on the census below; a fired gate stops the design it scopes
    # `blocks` is the pre-registered list of topics this gate's sentence scopes. It is not a measurement: it is the
    # scope sentence in machine-readable form, and the first generation of this census omitted it, which let
    # `record_blocked.py` file a fired gate under its own name instead of under the topic it stops.
    "G1_assistant_text_available": {"rule": ">= 0.50 of trajectories carry >= 1 assistant turn of >= 20 chars",
                                    "threshold": 0.50, "scope": "design",
                                    "blocks": ["T123", "T124", "T126", "T127", "T191"]},
    "G2_modality_prevalence": {"rule": ">= 0.05 of assistant turns carry a modality marker, else the construct has "
                                       "no identifiable variation", "threshold": 0.05, "scope": "H1",
                               "blocks": ["T123", "T124"]},
    "G3_inspection_action_prevalence": {"rule": ">= 0.10 of function calls are inspection-family calls, else there "
                                                "is no behavioural verification DV", "threshold": 0.10,
                                        "scope": "design", "blocks": ["T123", "T124", "T126"]},
    "G4_trajectories_with_three_assistant_turns": {"rule": ">= 500 trajectories with >= 3 assistant turns, the "
                                                           "smallest cell a transition estimate needs",
                                                  "threshold": 500, "scope": "rows",
                                                  "blocks": ["T123", "T124", "T126", "T127"]},
    "G5_contradiction_cell": {"rule": ">= 200 trajectories with two non-identical observations from the same tool "
                                      "in a row (T126's subject)", "threshold": 200, "scope": "H3",
                              "blocks": ["T126"]},
    "G6_sufficiency_cell": {"rule": ">= 200 trajectories carrying a sufficiency expression (T127's subject)",
                            "threshold": 200, "scope": "H1", "blocks": ["T127"]},
    "G7_outcome_label_available": {"rule": ">= 0.50 of trajectories carry a release-side outcome field, else T191 "
                                           "cannot be scored", "threshold": 0.50, "scope": "design",
                                   "blocks": ["T191"]},
    "G8_T123_contrast_smallest_arm": {"rule": "both arms of the hedged-vs-plain follow-up-inspection contrast hold >= 200 "
                                      "turns, else T123's H1 is a description not a test", "threshold": 200,
                              "scope": "H1", "blocks": ["T123"]},
    "G9_discordant_hedge_turns": {"rule": ">= 200 assistant turns hedge in the reasoning block while the user-facing body "
                             "does not, else T124's H1 has no subject", "threshold": 200, "scope": "H1",
                             "blocks": ["T124"]},
    "G10_turns_after_error_observation": {"rule": ">= 200 assistant turns immediately follow an observation carrying a "
                              "failure marker, else T123's H2 cannot be estimated", "threshold": 200, "scope": "H2",
                              "blocks": ["T123"]},
    "G11_stops_preceded_by_sufficiency_claim": {"rule": ">= 200 trajectory endings preceded by a sufficiency claim, else T127's H1 is "
                             "reported as a prevalence measurement", "threshold": 200, "scope": "H1",
                             "blocks": ["T127"]},
}


def parse_calls(value: str):
    """(name, arguments) per call the assistant turn emitted; name None when the JSON will not parse."""
    out = []
    for b in CALL.findall(value):
        try:
            j = json.loads(b.strip())
            out.append((str(j.get("name") or ""), json.dumps(j.get("arguments") or {}, ensure_ascii=False)))
        except Exception:                                     # noqa: BLE001 - a malformed call is a data fact
            out.append((None, b.strip()[:200]))
    return out


def parse_observations(value: str):
    """(name, content) per observation block; name None when the block will not parse."""
    out = []
    for b in RESP.findall(value):
        try:
            j = json.loads(b.strip())
            out.append((str(j.get("name") or ""), json.dumps(j.get("content"), ensure_ascii=False)[:4000]))
        except Exception:                                     # noqa: BLE001
            out.append((None, b.strip()[:4000]))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=4000)
    ap.add_argument("--seed", type=int, default=W.SEED)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    files = sorted(glob.glob(str(CORPUS / "data" / "**" / "*.parquet"), recursive=True))
    if not files:
        raise SystemExit(f"ABORT: no parquet under {CORPUS} - the census has no subject")
    import pandas as pd
    frames = [pd.read_parquet(f) for f in files]
    df = pd.concat(frames, ignore_index=True)
    # EXP-0162: the release stores 7,646 of its 14,701 trajectories twice over, so the sample is drawn over
    # distinct ids; the first version sampled rows and counted those trajectories twice in every gate denominator.
    df["traj_id"] = df["id"].astype(str) if "id" in df.columns else [str(i) for i in range(len(df))]
    dupes = int(len(df) - df["traj_id"].nunique())
    take = df.drop_duplicates(subset=["traj_id"], keep="first").sample(
        min(a.rows, int(df["traj_id"].nunique())), random_state=a.seed).reset_index(drop=True)

    roles = collections.Counter()
    n_traj = len(take)
    # Every quantity below is a share of trajectories or of assistant turns, so the counters are per-unit flags
    # summed once: the first version incremented the trajectory flag inside the message loop and reported a "share"
    # of 10.67. The gate sentence says an assistant *turn* carries a marker, and a turn is its reasoning block plus
    # its body, so the prevalence counts the whole turn and the two faces are additionally reported.
    with_body = bodies = modal_turns = modal_bodies = modal_thinks = 0
    suffic_turns = suffic_bodies = suffic_thinks = three_asst = suffic_traj = thinks = 0
    calls_named = calls_bad = inspect_calls = write_calls = exec_calls = 0
    obs_named = obs_bad = contrad = outcome_rows = transitions = 0
    # joint cells the wave-4 gates need (see JOINT below): turn-level crosses of the two prose faces with the
    # behaviour that follows, all prevalence counts rather than effects
    jt = collections.Counter()
    outcome_fields = collections.Counter()
    for r in take.itertuples(index=False):
        msgs = [dict(m) for m in (list(r.conversations) if r.conversations is not None else [])]
        for m in msgs:
            roles[str(m.get("from"))] += 1
        seq = []                                              # the behaviour stream; prose stays off it
        steps = []                                            # turns and actions in order, for the joint cells
        asst_in_traj = traj_suff = traj_has_body = 0
        row_outcome = False
        for m in msgs:
            role, v = str(m.get("from")), str(m.get("value"))
            if role in ("gpt", "assistant"):
                asst_in_traj += 1
                body = THINK.sub("", v).strip()
                think = " ".join(THINK.findall(v)).strip()
                low = v.lower()
                bodies += 1
                traj_has_body = traj_has_body or len(body) >= 20
                modal_turns += int(any(k in low for k in MODAL))
                suff = any(k in low for k in SUFFIC)
                suffic_turns += int(suff)
                traj_suff = traj_suff or suff
                mb = int(any(k in body.lower() for k in MODAL)) if len(body) >= 20 else 0
                mt = int(any(k in think.lower() for k in MODAL)) if think else 0
                sb = int(any(k in body.lower() for k in SUFFIC)) if len(body) >= 20 else 0
                st_ = int(any(k in think.lower() for k in SUFFIC)) if think else 0
                modal_bodies += mb
                suffic_bodies += sb
                if think:
                    thinks += 1
                    modal_thinks += mt
                    suffic_thinks += st_
                steps.append(("turn", {"modal": int(bool(mb or mt)), "modal_body": mb, "modal_think": mt,
                                       "suffic": int(bool(suff or sb or st_)), "body_len": len(body)}))
                called = False
                for nm, _args in parse_calls(v):
                    if nm is None:
                        calls_bad += 1
                        continue
                    calls_named += 1
                    insp = bool(INSPECT_NAME.search(nm))
                    if insp:
                        inspect_calls += 1
                    if EXEC_NAME.search(nm):
                        exec_calls += 1
                    if WRITE_NAME.search(nm) and not insp and not EXEC_NAME.search(nm):
                        write_calls += 1
                    seq.append(("call", nm))
                    steps.append(("call", nm))
                    called = True
                jt["turns"] += 1
                jt["turns_with_call"] += int(called)
            elif role in ("tool", "function", "observation"):
                for nm, content in parse_observations(v):
                    if nm is None:
                        obs_bad += 1
                        continue
                    obs_named += 1
                    seq.append(("obs", (nm, content)))
                    steps.append(("obs", (nm, content)))
        # joint cells: for each assistant turn, what the immediately following behaviour was, and what the
        # immediately preceding observation said
        for i, (kind, payload) in enumerate(steps):
            if kind != "turn":
                continue
            nxt = steps[i + 1] if i + 1 < len(steps) else None
            prev = steps[i - 1] if i > 0 else None
            nxt_call = bool(nxt and nxt[0] == "call")          # no following step *is* the stop, so guard first
            nxt_inspect = bool(nxt_call and INSPECT_NAME.search(nxt[1]))
            prev_err = bool(prev and prev[0] == "obs" and any(
                k in json.dumps(prev[1]).lower() for k in ("error", "not found", "failed", "traceback",
                                                            "permission denied", "no such", "exception")))
            jt["turn_after_obs"] += int(bool(prev and prev[0] == "obs"))
            jt["turn_after_error_obs"] += int(prev_err)
            jt["turn_after_error_obs_modality"] += int(prev_err and payload["modal"] == 1)
            jt["turn_before_stop"] += int(not nxt_call)
            jt["turn_before_stop_suffic"] += int(not nxt_call and payload["suffic"] == 1)
            jt["turn_with_next_call_modality"] += int(nxt_call and payload["modal"] == 1)
            jt["turn_with_next_inspect_modality"] += int(nxt_inspect and payload["modal"] == 1)
            jt["turn_with_next_call_plain"] += int(nxt_call and payload["modal"] == 0)
            jt["turn_with_next_inspect_plain"] += int(nxt_inspect and payload["modal"] == 0)
            jt["discordant_hedge_turns"] += int(payload["modal_think"] == 1 and payload["modal_body"] == 0)
            jt["concordant_hedge_turns"] += int(payload["modal_think"] == 1 and payload["modal_body"] == 1)
            jt["body_only_hedge_turns"] += int(payload["modal_body"] == 1 and payload["modal_think"] == 0)
            if not nxt_call:
                jt["stop_prior_inspections_sum"] += sum(1 for k, p in steps[:i]
                                                        if k == "call" and INSPECT_NAME.search(p))
                jt["stop_prior_writes_sum"] += sum(1 for k, p in steps[:i]
                                                   if k == "call" and not INSPECT_NAME.search(p))
        with_body += int(bool(traj_has_body))
        three_asst += int(asst_in_traj >= 3)
        suffic_traj += int(bool(traj_suff))
        transitions += sum(1 for i, x in enumerate(seq)
                           if x[0] == "obs" and i + 1 < len(seq) and seq[i + 1][0] == "call")
        if any(seq[i][0] == "obs" and seq[i + 1][0] == "obs" and seq[i][1][0] == seq[i + 1][1][0]
               and seq[i][1][1].strip() and seq[i][1][1].strip() != seq[i + 1][1][1].strip()
               for i in range(len(seq) - 1)):
            contrad += 1
        for k in OUTCOME_COLS:
            # a column that exists is not a column that has content: count the row only on a non-empty value
            if k in take.columns and str(getattr(r, k, "") or "").strip():
                outcome_fields[k] += 1
                row_outcome = True
        outcome_rows += int(row_outcome)
    JOINT = {
        "G8_hedged_turns_followed_by_inspection": jt["turn_with_next_inspect_modality"],
        "plain_turns_followed_by_inspection": jt["turn_with_next_inspect_plain"],
        "G9_discordant_hedge_turns": jt["discordant_hedge_turns"],
        "concordant_hedge_turns": jt["concordant_hedge_turns"],
        "body_only_hedge_turns": jt["body_only_hedge_turns"],
        "G10_turns_after_error_observation": jt["turn_after_error_obs"],
        "modality_rate_after_error_observation": round(
            jt["turn_after_error_obs_modality"] / max(1, jt["turn_after_error_obs"]), 4),
        "G11_stops_preceded_by_sufficiency_claim": jt["turn_before_stop_suffic"],
        "stops_total": jt["turn_before_stop"],
        "sufficiency_rate_before_stop": round(jt["turn_before_stop_suffic"] / max(1, jt["turn_before_stop"]), 4),
        "mean_prior_inspections_at_stop": round(jt["stop_prior_inspections_sum"] / max(1, jt["turn_before_stop"]), 2),
        "mean_prior_non_inspections_at_stop": round(jt["stop_prior_writes_sum"] / max(1, jt["turn_before_stop"]), 2),
        "turns_with_a_following_call": jt["turns_with_call"],
        # the smaller of the two arms of T123's contrast: a cell that is large in the hedged arm and tiny in the
        # plain one cannot carry a comparison, so the gate reads the minimum
        "G8_T123_contrast_smallest_arm": min(jt["turn_with_next_inspect_modality"], jt["turn_with_next_inspect_plain"]),
    }
    measured = {
        "corpus": str(CORPUS.name), "files_read": len(files), "trajectories_sampled": n_traj,
        "roles_observed": dict(roles),
        "assistant_turns_read": bodies, "assistant_turns_with_reasoning_block": thinks,
        "calls_parsed": calls_named, "calls_unparseable": calls_bad,
        "observations_parsed": obs_named, "observations_unparseable": obs_bad,
        "observation_to_next_call_transitions": transitions,
        "G1_assistant_text_available": round(with_body / max(1, n_traj), 4),
        "G2_modality_prevalence": round(modal_turns / max(1, bodies), 4),
        "modality_prevalence_in_body_only": round(modal_bodies / max(1, bodies), 4),
        "modality_prevalence_in_reasoning_block": round(modal_thinks / max(1, thinks), 4),
        "G3_inspection_action_prevalence": round(inspect_calls / max(1, calls_named), 4),
        "execution_family_call_share": round(exec_calls / max(1, calls_named), 4),
        "write_only_call_share": round(write_calls / max(1, calls_named), 4),
        "G4_trajectories_with_three_assistant_turns": three_asst,
        "G5_contradiction_cell": contrad,
        "G6_sufficiency_cell": suffic_traj,
        "sufficiency_marker_turn_share": round(suffic_turns / max(1, bodies), 4),
        "sufficiency_marker_body_share": round(suffic_bodies / max(1, bodies), 4),
        "sufficiency_marker_in_reasoning_share": round(suffic_thinks / max(1, thinks), 4),
        "G7_outcome_label_available": round(outcome_rows / max(1, n_traj), 4),
        "outcome_fields_with_values": dict(outcome_fields),
    }
    measured.update(JOINT)   # the wave-4 designs' own cells, measured in the same pass (see joint_cells_below)
    def fires(g: str) -> bool:
        v = measured[g]
        return not (isinstance(v, (int, float)) and v >= GATES[g]["threshold"])

    verdict = {"blocked_gates": [], "blocked_whole_design": [], "claim_limited": {},
               "note": "a fired gate is a result: it stops exactly what its frozen sentence scopes "
                       "(the whole design, one named hypothesis, or rows to exclude and count)"}
    for g in GATES:
        if not fires(g):
            continue
        verdict["blocked_gates"].append(g)
        if GATES[g]["scope"] == "design":
            # the topics, not the gate: `record_blocked.py` writes one BLOCKED.md per stopped topic
            verdict["blocked_whole_design"] += [x for x in GATES[g]["blocks"]
                                                if x not in verdict["blocked_whole_design"]]
        else:
            verdict["claim_limited"][g] = GATES[g]["scope"]
    out = {"sampled_rows": n_traj, "duplicate_traj_ids_dropped_before_sampling": dupes,
           "measured": measured,
           "gates": {k: (not fires(k)) for k in GATES},
           "gate_rules": {k: GATES[k]["rule"] for k in GATES},
           "gate_scopes": {k: {"scope": GATES[k]["scope"], "blocks": GATES[k]["blocks"],
                               "threshold": GATES[k]["threshold"]} for k in GATES},
           "verdict": verdict,
           "seed": a.seed, "started_at": W.now(), "wallclock_sec": round(time.time() - t0, 1),
           "invocation": " ".join([sys.executable] + sys.argv)}
    dest = W.write_raw("EXP-0152", "wave4_premise_census", out)
    print(json.dumps(out, indent=1, ensure_ascii=False, default=str)[:2400])
    print(f"\nEXP-0152: wrote {dest.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
