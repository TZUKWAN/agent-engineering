"""EXP-0153: the wave-4 step matrix - one row per assistant turn, language on one side, behaviour on the other.

Every wave-4 design compares what an agent *says* with what it *does*, so the substrate has to keep the two channels
separate and auditable. A turn here is one assistant message: its reasoning block, its user-facing body, and the tool
calls the message itself emitted. The behaviour variables are read off the call record and the message that follows,
never off the prose, which is the defect EXP-0076 measured on AgentNet.

Run with --selftest to check the instruments before anything is written:

    python 02_shared_code/package_factory/exp_wave4_features.py [--selftest] [--cap 20000]
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import glob
import json
import pathlib
import re
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import wave_lib as W                                              # noqa: E402
import topic_designs_wave4 as TD4                                 # noqa: E402

LT, GT = chr(60), chr(62)


def t(name: str, close: bool = False) -> str:
    return f"{LT}{'/' if close else ''}{name}{GT}"


CALL = re.compile(re.escape(t("tool_call")) + r"(.*?)" + re.escape(t("tool_call", True)), re.S)
RESP = re.compile(re.escape(t("tool_response")) + r"(.*?)" + re.escape(t("tool_response", True)), re.S)
THINK = re.compile(re.escape(t("think")) + r"(.*?)" + re.escape(t("think", True)), re.S)
CORPUS = pathlib.Path(str(W.ROOT.parent) + "/MATLABINTOKEN/datasets/lambda/hermes-agent-reasoning-traces")
FRAME = "EXP0153_wave4_step_features.csv.gz"


def any_marker(text: str, lexicon) -> int:
    low = text.lower()
    return int(any(k in low for k in lexicon))


def parse_calls(value: str):
    out = []
    for b in CALL.findall(value):
        try:
            j = json.loads(b.strip())
            out.append(str(j.get("name") or ""))
        except Exception:                                     # noqa: BLE001 - unparseable, counted not guessed
            out.append(None)
    return out


def parse_obs(value: str):
    out = []
    for b in RESP.findall(value):
        try:
            j = json.loads(b.strip())
            out.append((str(j.get("name") or ""), json.dumps(j.get("content"), ensure_ascii=False)))
        except Exception:                                     # noqa: BLE001
            out.append((None, b.strip()[:4000]))
    return out


def load_trajectories(cap: int):
    """The release's conversations, in a seeded sample of at most `cap` trajectories (never re-drawn per step)."""
    import pandas as pd
    files = sorted(glob.glob(str(CORPUS / "data" / "**" / "*.parquet"), recursive=True))
    if not files:
        raise SystemExit(f"ABORT: no parquet under {CORPUS}")
    df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    if "id" in df.columns:
        df["traj_id"] = df["id"].astype(str)
    else:
        df["traj_id"] = ["T%06d" % i for i in range(len(df))]
    # EXP-0162 measured the release: 22,347 rows carry only 14,701 distinct `traj_id`s, because 7,646 trajectories
    # are stored twice over (once in `train.parquet`, once in the sharded copy), byte-identical. Sampling rows would
    # count those trajectories twice in every turn total and marker prevalence while the traj_id-clustered intervals
    # count them once, so the duplicates are dropped here, before the sample is drawn.
    n_before = len(df)
    df = df.drop_duplicates(subset=["traj_id"], keep="first")
    dropped = n_before - len(df)
    uniq = df["traj_id"].drop_duplicates()
    if len(uniq) > cap:                     # compare against the trajectory count, not the row count
        keep = set(uniq.sample(cap, random_state=TD4.SEED))
        df = df[df["traj_id"].isin(keep)]
    df = df.reset_index(drop=True)
    df.attrs["duplicate_traj_ids_dropped"] = int(dropped)
    return df, len(files)


def build_rows(df) -> list:
    """One dict per assistant turn. `bad_*` counters are returned through the module-level BAD, see selftest."""
    rows = []
    for r in df.itertuples(index=False):
        msgs = [dict(m) for m in list(r.conversations)]
        traj = str(r.traj_id)
        cat = str(getattr(r, "category", "") or "")
        sub = str(getattr(r, "subcategory", "") or "")
        n_turns = sum(1 for m in msgs if str(m.get("from")) in ("gpt", "assistant"))
        # the action stream, in order, tagged so a turn can be joined to what it did and to what came before
        stream = []
        for m in msgs:
            role = str(m.get("from"))
            if role in ("gpt", "assistant"):
                stream.append(("turn", m))
            elif role in ("tool", "function", "observation"):
                stream.append(("obs", m))
            else:
                stream.append(("other", m))
        prior_inspect = prior_other = 0
        turn_i = seen_calls_total = 0
        obs_hist = []                                   # (tool, content) in order: the evidence state, not the prose
        # the action stream, in order, tagged so a turn can be joined to what it did and to what came before
        stream = []
        for m in msgs:
            role = str(m.get("from"))
            if role in ("gpt", "assistant"):
                stream.append(("turn", m))
            elif role in ("tool", "function", "observation"):
                stream.append(("obs", m))
            else:
                stream.append(("other", m))
        for i, (kind, m) in enumerate(stream):
            if kind == "obs":
                for nm, content in parse_obs(str(m.get("value"))):
                    if nm is None:
                        BAD["observations_unparseable"] += 1
                        continue
                    obs_hist.append((nm, content))
                continue
            if kind != "turn":
                continue
            turn_i += 1
            v = str(m.get("value"))
            body = THINK.sub("", v).strip()
            think = " ".join(THINK.findall(v)).strip()
            names = parse_calls(v)
            named = [n for n in names if n is not None]
            BAD["calls_unparseable"] += len(names) - len(named)
            seen_calls_total += len(named)
            insp = [n for n in named if INSPECT.search(n)]
            execs = [n for n in named if EXEC.search(n)]
            writes = [n for n in named if WRITE.search(n) and n not in insp and n not in execs]
            nxt = stream[i + 1] if i + 1 < len(stream) else None
            prev_state = "none"
            prev_err = 0
            if len(obs_hist) >= 2:
                (tn, tc), (pn, pc) = obs_hist[-1], obs_hist[-2]
                prev_state = ("same_tool_changed" if tn == pn and tc.strip() != pc.strip() else
                              "same_tool_same" if tn == pn else "different_tool")
            elif len(obs_hist) == 1:
                prev_state = "first_observation"
            prev_err = int(any(k in (obs_hist[-1][1] or "").lower() for k in TD4.FAILURE_MARKERS)) if obs_hist else 0
            rows.append(dict(
                traj_id=traj, category=cat, subcategory=sub, turn_index=turn_i, n_turns_traj=n_turns,
                # a digest of the two faces, so a prevalence claim can be checked against how many distinct texts
                # produced it rather than how many turns
                turn_sha=hashlib.sha256((think + "" + body).encode("utf-8")).hexdigest()[:16],
                has_think=int(bool(think)), body_len=len(body), think_len=len(think),
                modal_turn=int(bool(any_marker(v, TD4.MODAL))),
                modal_body=int(bool(any_marker(body, TD4.MODAL))) if len(body) >= 20 else 0,
                modal_think=int(bool(any_marker(think, TD4.MODAL))) if think else 0,
                suffic_turn=int(bool(any_marker(v, TD4.SUFFIC))),
                suffic_body=int(bool(any_marker(body, TD4.SUFFIC))) if len(body) >= 20 else 0,
                suffic_think=int(bool(any_marker(think, TD4.SUFFIC))) if think else 0,
                topical_control=int(bool(any_marker(v, TD4.TOPICAL_CONTROL))),
                # EXP-0153 measured the indicator at prevalence 0.9998, i.e. it fires on nearly every turn and
                # cannot identify a coefficient. The count of the same lexicon's occurrences is the pre-registered
                # specificity control's usable form: same words, same corpus, real variance.
                topical_count=sum(v.lower().count(k) for k in TD4.TOPICAL_CONTROL),
                emits_call=int(bool(named)), n_calls_this_turn=len(named),
                first_call_name=(named[0] if named else ""),
                next_is_inspect=int(bool(insp)), next_is_exec=int(bool(execs)), next_is_write=int(bool(writes)),
                next_action_kind=("call" if named else ("human" if nxt and nxt[0] == "other" else
                                                        ("end" if nxt is None else "observe_only"))),
                prior_inspections=prior_inspect, prior_non_inspections=prior_other,
                prev_obs_error=prev_err, prev_state=prev_state,
                prev_obs_tool=(obs_hist[-1][0] if obs_hist else ""),
                last_call_tool=(named[-1] if named else ""),
                traj_turns_at_turn=turn_i))
            prior_inspect += len(insp)
            prior_other += len(named) - len(insp)
    return rows


# The same three tool-name families EXP-0152 counted. `terminal`, `execute_code` and `process` are an execution
# family of their own: what they read or produce depends on the command inside them, so they are neither inspection
# nor production, and lumping them in there once put 68% of calls in the write family.
INSPECT = re.compile(r"(^|_)(read|cat|grep|search|find|list|ls|view|inspect|get|show|open|query|fetch|"
                     r"status|check|test|verify|validate|diff|explore)(_|$)|read_file|search_files|"
                     r"session_search|skill_view|skills_list", re.I)
EXEC = re.compile(r"(^|_)(terminal|execute_code|process|bash|shell|run_command)(_|$)", re.I)
WRITE = re.compile(r"(^|_)(write|edit|patch|create|delete|remove|commit|push|deploy|install)(_|$)|write_file", re.I)
BAD = collections.Counter()


def selftest() -> int:
    """Prove the instrument before writing an artefact: tags, alignment, and a hand-read turn."""
    import pandas as pd
    sample = pd.DataFrame({"traj_id": ["s1"], "category": [""], "subcategory": [""], "conversations": [[
        {"from": "system", "value": "tools"},
        {"from": "human", "value": "find the config"},
        {"from": "gpt", "value": t("think") + " I may need to look first" + t("think", True) +
         " Let me search." + t("tool_call") + '{"name": "search_files", "arguments": {"q": "cfg"}}' +
         t("tool_call", True)},
        {"from": "tool", "value": t("tool_response") +
         '{"name": "search_files", "content": {"hits": 2}}' + t("tool_response", True)},
        {"from": "gpt", "value": "That is enough."}]]})
    rows = build_rows(sample)
    assert len(rows) == 2, f"expected 2 assistant turns, got {len(rows)}"
    a, b = rows[0], rows[1]
    assert a["emits_call"] == 1 and a["next_is_inspect"] == 1, f"call not read: {a}"
    assert a["modal_turn"] == 1 and a["modal_think"] == 1, f"reasoning hedge missed: {a}"
    assert a["modal_body"] == 0, f"body has no hedge, so this must be 0: {a}"
    assert b["emits_call"] == 0 and b["next_action_kind"] == "end", f"last turn must read as a stop: {b}"
    assert b["suffic_turn"] == 1, f"'That is enough.' must register as a sufficiency claim: {b}"
    assert b["prev_obs_tool"] == "search_files", f"evidence state lost: {b}"
    assert BAD["calls_unparseable"] == 0, BAD
    print("SELFTEST OK: tags parsed, the hedge sits in the reasoning face only, stops and evidence state align")
    return 0


def summarise(rows, files, t0, dupes=0) -> dict:
    import pandas as pd
    F = pd.DataFrame(rows)
    out = {"exp_id": "EXP-0153", "corpus": CORPUS.name, "files_read": files,
           "trajectories": int(F["traj_id"].nunique()), "assistant_turns": int(len(F)),
           "turns_emitting_a_call": int(F["emits_call"].sum()),
           "calls_total": int(F["n_calls_this_turn"].sum()), "calls_unparseable": int(BAD["calls_unparseable"]),
           "modal_turn_share": round(float(F["modal_turn"].mean()), 4),
           "modal_body_share": round(float(F["modal_body"].mean()), 4),
           "modal_think_share_of_turns_with_think": round(
               float(F.loc[F["has_think"] == 1, "modal_think"].mean()), 4),
           "suffic_turn_share": round(float(F["suffic_turn"].mean()), 4),
           "topical_control_share": round(float(F["topical_control"].mean()), 4),
           "topical_count_mean": round(float(F["topical_count"].mean()), 3),
           "topical_count_sd": round(float(F["topical_count"].std(ddof=0)), 3),
           "topical_count_zero_share": round(float((F["topical_count"] == 0).mean()), 4),
           "discordant_hedge_turns": int(((F["modal_think"] == 1) & (F["modal_body"] == 0)).sum()),
           "concordant_hedge_turns": int(((F["modal_think"] == 1) & (F["modal_body"] == 1)).sum()),
           "body_only_hedge_turns": int(((F["modal_think"] == 0) & (F["modal_body"] == 1)).sum()),
           "turns_followed_by_inspection": int(F["next_is_inspect"].sum()),
           "inspection_share_of_calling_turns": round(
               float(F.loc[F["emits_call"] == 1, "next_is_inspect"].mean()), 4),
           "execution_share_of_calling_turns": round(
               float(F.loc[F["emits_call"] == 1, "next_is_exec"].mean()), 4),
           "prev_obs_error_turns": int(F["prev_obs_error"].sum()),
           "stop_turns": int((F["next_action_kind"] == "end").sum()),
           "human_continued_turns": int((F["next_action_kind"] == "human").sum()),
           "observe_only_turns": int((F["next_action_kind"] == "observe_only").sum()),
           "cluster_unit": "traj_id", "seed": TD4.SEED, "sample_cap": int(TD4.SAMPLE["traj_cap"]),
           "duplicate_traj_ids_dropped_before_sampling": int(dupes),
           "started_at": W.now(), "wallclock_sec": round(time.time() - t0, 1)}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--cap", type=int, default=TD4.SAMPLE["traj_cap"])
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if a.selftest:
        return selftest()
    t0 = time.time()
    W.OUT.mkdir(parents=True, exist_ok=True)
    df, files = load_trajectories(a.cap)
    rows = build_rows(df)
    if not rows:
        raise SystemExit("ABORT: the release yielded no assistant turns - the matrix has no subject")
    import pandas as pd
    F = pd.DataFrame(rows)
    F.to_csv(W.OUT / FRAME, index=False, compression="gzip")
    art = summarise(rows, files, t0, df.attrs.get("duplicate_traj_ids_dropped", 0))
    art["frame_file"] = f"results_processed/{FRAME}"
    art["invocation"] = " ".join([sys.executable] + sys.argv)
    dest = W.write_raw("EXP-0153", "wave4_step_matrix", art)
    print(json.dumps(art, indent=1, ensure_ascii=False)[:1600])
    print(f"\nEXP-0153: wrote {dest.name} and {FRAME} ({len(F)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
