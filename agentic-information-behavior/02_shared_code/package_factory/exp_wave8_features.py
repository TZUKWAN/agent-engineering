"""EXP-0191: wave 8's turn frame - one row per assistant turn, with its own trajectory's history resolved.

Wave 8's designs ask about a turn's relationship to what came before it in the *same* trajectory: the hypothesis the
trajectory stated early, the observations it had already seen, the calls it had already issued, the error that
preceded this turn. The wave-4 and wave-5 spines carry turn structure but not those linkages, so this frame is built
from the release's own conversations with the instruments EXP-0190 froze - the same call parser and the same lexicons,
imported rather than restated - one trajectory at a time.

What the frame carries, beyond each turn's own marker counts:

* `hypo_overlap`, the share of a turn's content words already present in its own trajectory's first early-hypothesis
  statement, and `alien_overlap`, the same share against a hypothesis statement borrowed from another trajectory of
  the same category by a seeded draw (T171's specificity arm);
* `obs_new_share`, the share of the observation following a turn whose content words the trajectory had not seen
  before it - the only mechanical reading of "this told me something" available without a model;
* `call_changed`, `repeat_call` and `repeat_name_prev`, which relate this turn's first call to the previous call and
  to every call the trajectory had already issued (T190's behavioural arm);
* the four first-turn specificity counts and the trajectory's own repeat and error shares, carried on every row so a
  trajectory-level model can hold them fixed (T182).

The frame cross-checks itself against EXP-0190 on every aggregate the two share and refuses to write when a pair
diverges - the guard that caught two of wave 7's definitional slips before any coefficient existed. This frame keeps
the >= 20 character assistant-turn floor waves 4 and 5 used, which the census did not apply, so the two are compared
on trajectory-level counts and both turn totals are reported.

    python 02_shared_code/package_factory/exp_wave8_features.py
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import random
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np                                                # noqa: E402
import pandas as pd                                               # noqa: E402
import wave_lib as W                                              # noqa: E402
import exp_wave4_features as EF                                   # noqa: E402  the release reader, unchanged
import probe_wave8_premises as P8                                 # noqa: E402  the instruments, unchanged

EXP = "EXP-0191"
TD8 = __import__("topic_designs_wave8")
SEED = TD8.SEED
MIN_BODY = 20                        # the assistant-turn floor waves 4 and 5 both used, unchanged
PLAN_TURNS = 2                       # "early" is the first two assistant turns, as EXP-0190's G3 sentence says


def turn_of(v: str) -> dict:
    """One assistant message -> the counts its text carries, with the call payload stripped out of the language."""
    low = str(v).lower()
    body = P8.CALL_RX.sub(" ", low)
    calls = P8.call_args(v)
    return {"chars": len(str(v)), "words": P8.words(body), "calls": calls,
            "has_think": int("<think>" in low),
            "hypo": P8.counts_of(body, P8.HYPOTHESIS), "plan": P8.counts_of(body, P8.PLAN),
            "evid_req": P8.counts_of(body, P8.EVIDENCE_REQUEST), "suffic": P8.counts_of(body, P8.SUFFICIENCY),
            "correct": P8.counts_of(body, P8.CORRECTION), "uncert": P8.counts_of(body, P8.UNCERTAINTY),
            "ordering": P8.counts_of(body, P8.ORDERING), "constraint": P8.counts_of(body, P8.CONSTRAINT),
            "verbs": P8.counts_of(" " + body, [" " + x for x in P8.ACTION_VERB]),
            "entities": len(set(P8.ENTITY_RX.findall(str(v))))}


def parse(row) -> dict:
    """One release row -> ordered events plus the trajectory-level facts the census and this frame must agree on."""
    evs, obs, calls = [], [], []
    for m in [dict(x) for x in (list(row.conversations) if row.conversations is not None else [])]:
        role, v = str(m.get("from")), str(m.get("value"))
        if role in ("tool", "function", "observation"):
            for nm, content in EF.parse_obs(v):
                o = (str(nm or ""), content or "")
                obs.append(o)
                evs.append(("o", o))
        elif role in ("gpt", "assistant"):
            t = turn_of(v)
            calls.extend(t["calls"])
            evs.append(("t", t))
    anchor, i = None, 0
    for kind, x in evs:
        if kind != "t":
            continue
        i += 1
        if i > PLAN_TURNS:
            break
        if x["hypo"]:
            anchor = x["words"]
            break
    first = next((x for k, x in evs if k == "t"), None)
    return {"evs": evs, "obs": obs, "calls": calls, "anchor": anchor, "first": first,
            "n_turns_all": sum(1 for k, _ in evs if k == "t"),
            "ends_on_assistant": int(bool(evs) and evs[-1][0] == "t"),
            "n_err_obs": sum(1 for o in obs if any(x in o[1].lower() for x in P8.FAILURE)),
            "n_call_turns": sum(1 for k, x in evs if k == "t" and x["calls"]),
            "repeat": int(bool(calls) and len(set(calls)) < len(calls)),
            "countable_plan": int(bool(first) and first["ordering"] >= 2 and first["verbs"] >= 2),
            "correct": int(any(x["correct"] for k, x in evs if k == "t")),
            "final_clean": int(bool(obs) and not any(x in obs[-1][1].lower() for x in P8.FAILURE))}


def rows_for(f: dict, traj: str, cat: str, task: str, alien) -> list:
    """One dict per assistant turn of a trajectory, with the history it is a relation to resolved as it goes."""
    task_words = P8.words(task)
    seen, issued, prev, out, i = set(), set(), None, [], 0
    n_turns = f["n_turns_all"]
    for j, (kind, x) in enumerate(f["evs"]):
        if kind == "o":
            seen |= P8.words(x[1])
            continue
        i += 1
        after = next((e[1] for e in f["evs"][j + 1:] if e[0] == "o"), None)
        aw = P8.words(after[1]) if after else set()
        before = [e[1] for e in f["evs"][:j] if e[0] == "o"]
        fc = x["calls"][0] if x["calls"] else None
        w = x["words"]
        out.append({"traj_id": traj, "category": cat, "turn_index": i, "n_turns": int(n_turns),
                    "position": round(i / max(1, n_turns), 4), "is_final_turn": int(i == n_turns),
                    "traj_ends_on_assistant": int(f["ends_on_assistant"]),
                    "stops_here": int(i == n_turns and f["ends_on_assistant"] == 1),
                    "body_chars": int(x["chars"]), "has_think": int(x["has_think"]),
                    "turn_words": int(len(w)), "hypo": int(x["hypo"]), "plan": int(x["plan"]),
                    "evid_req": int(x["evid_req"]), "suffic": int(x["suffic"]), "uncert": int(x["uncert"]),
                    "correct": int(x["correct"]), "ordering": int(x["ordering"]),
                    "constraint": int(x["constraint"]), "verbs": int(x["verbs"]), "entities": int(x["entities"]),
                    "n_calls": int(len(x["calls"])), "first_call_name": (fc[0] if fc else ""),
                    "call_changed": float("nan") if not (fc and prev)
                    else float(fc[0] != prev[0] or fc[1] != prev[1]),
                    "repeat_call": int(bool(fc) and fc in issued),
                    "repeat_name_prev": int(bool(fc) and bool(prev) and fc[0] == prev[0]),
                    "prior_error": int(bool(before) and any(k2 in before[-1][1].lower() for k2 in P8.FAILURE)),
                    "obs_new_share": float("nan") if not aw
                    else round(float(len(aw - seen) / max(1, len(aw))), 4),
                    "obs_error_next": int(bool(after) and any(k2 in after[1].lower() for k2 in P8.FAILURE)),
                    "hypo_overlap": float("nan") if not (f["anchor"] and w)
                    else round(float(len(w & f["anchor"]) / max(1, len(w))), 4),
                    "alien_overlap": float("nan") if not (alien and w)
                    else round(float(len(w & alien) / max(1, len(w))), 4),
                    "task_overlap": float("nan") if not (task_words and w)
                    else round(float(len(w & task_words) / max(1, len(w))), 4),
                    "has_early_hypo": int(f["anchor"] is not None)})
        issued.update(x["calls"])
        if x["calls"]:
            prev = x["calls"][0]
        seen |= w
    return out


def build() -> tuple:
    """Every trajectory of the release -> its turn rows plus one trajectory-level row of its own measures."""
    df, n_files = EF.load_trajectories(10 ** 9)
    facts, meta = {}, []
    for r in df.itertuples(index=False):
        f = parse(r)
        tr = str(r.traj_id)
        facts[tr] = (f, str(r.category or ""), str(r.task or ""))
        first = f["first"] or {"entities": 0, "verbs": 0, "ordering": 0, "constraint": 0, "chars": 0}
        meta.append({"traj_id": tr, "category": str(r.category or ""), "n_turns_all": f["n_turns_all"],
                     "n_obs": len(f["obs"]), "n_calls_traj": len(f["calls"]),
                     "n_unparsed": sum(1 for c in f["calls"] if c[0] == "unparsed"),
                     "n_err_obs": f["n_err_obs"], "call_turns_answered": int(f["n_call_turns"] <= len(f["obs"])),
                     "ends_on_assistant": f["ends_on_assistant"], "early_hypo": int(f["anchor"] is not None),
                     "correct": f["correct"], "repeat": f["repeat"], "countable_plan": f["countable_plan"],
                     "final_obs_clean": f["final_clean"], "task_words": len(P8.words(str(r.task or ""))),
                     "first_entities": int(first["entities"]), "first_verbs": int(first["verbs"]),
                     "first_ordering": int(first["ordering"]), "first_constraint": int(first["constraint"]),
                     "first_chars": int(first["chars"]),
                     "repeat_share": round(1 - len(set(f["calls"])) / len(f["calls"]), 4) if f["calls"] else 0.0,
                     "error_share": round(f["n_err_obs"] / max(1, len(f["obs"])), 4)})
    by_cat = collections.defaultdict(list)
    for tr, (f, cat, _t) in facts.items():
        if f["anchor"]:
            by_cat[cat].append(tr)
    alien = {}
    for tr, (f, cat, _t) in facts.items():
        pool = sorted(a for a in by_cat[cat] if a != tr) if f["anchor"] else []
        if pool:
            alien[tr] = facts[random.Random(f"{SEED}|{tr}").choice(pool)][0]["anchor"]
    rows = []
    for tr in sorted(facts):
        f, cat, task = facts[tr]
        rows.extend([x for x in rows_for(f, tr, cat, task, alien.get(tr)) if x["body_chars"] >= MIN_BODY])
    return rows, pd.DataFrame(meta), n_files, int(len(df))


def census() -> dict:
    """EXP-0190's whole-release numbers, so a frame counting differently cannot be mistaken for the census."""
    for f in sorted(W.RAWRES.glob("EXP0190_wave8_premise_census_*.json"), reverse=True):
        a = json.loads(f.read_text(encoding="utf-8"))
        if "--traj-cap" not in str(a.get("invocation", "")):
            return {"file": f.name, "measured": a["measured"]}
    raise SystemExit("ABORT: no whole-release EXP-0190 census artefact exists, so this frame has nothing to check "
                     "its own counts against")


def selftest() -> int:
    """Every instrument proven on a hand-built trajectory before a single release row is read."""
    def msg(role, value):
        return {"from": role, "value": value}
    o, c = chr(60), chr(62)
    call = o + "tool_call" + c + '{"name": "read_file", "arguments": {"path": "data.csv"}}' \
        + o + "/tool_call" + c

    def obs(payload):
        return o + "tool_response" + c + " " + payload + " " + o + "/tool_response" + c
    task = "Read data.csv, remove the duplicate rows and write report.md"

    class Row:
        traj_id = "selftest"
        conversations = [
            msg("human", task),
            msg("gpt", "I think the duplicated rows in data.csv are the problem. First I will read data.csv, then "
                       "count the rows. " + call),
            msg("tool", obs('{"name": "read_file", "content": "error: no such file or directory, 12 rows of data"}')),
            msg("gpt", "My mistake - the duplicated values must be dropped. Let me read data.csv again, then write "
                       "report.md. " + call)]

    f = parse(Row)
    assert f["n_turns_all"] == 2 and f["ends_on_assistant"] == 1, [k for k, _ in f["evs"]]
    assert len(f["obs"]) == 1 and f["n_err_obs"] == 1 and f["final_clean"] == 0, f["obs"]
    assert f["anchor"] and f["repeat"] == 1 and f["countable_plan"] == 1 and f["correct"] == 1
    r = rows_for(f, "selftest", "Terminal & Coding", task, None)
    assert r[0]["hypo_overlap"] > 0.9 and r[1]["hypo_overlap"] > 0.2, [x["hypo_overlap"] for x in r]
    assert r[0]["n_calls"] == 1 and r[0]["first_call_name"] == "read_file" and r[0]["obs_new_share"] == 1.0
    assert r[0]["prior_error"] == 0 and r[0]["obs_error_next"] == 1, r[0]
    assert r[1]["prior_error"] == 1 and r[1]["repeat_call"] == 1 and r[1]["call_changed"] == 0.0
    assert r[1]["correct"] >= 1 and r[1]["is_final_turn"] == 1 and r[1]["stops_here"] == 1
    assert 0.0 <= r[0]["task_overlap"] <= 1.0
    rr = rows_for(f, "selftest", "x", "read data.csv report.md email", {"email", "name", "columns"})
    assert 0.0 <= rr[0]["alien_overlap"] <= 1.0 and rr[0]["task_overlap"] > 0.0, rr[0]
    print("SELFTEST OK: anchor, overlap, newness, error, repeat and correction columns all land on a built trace")
    return 0


def z(s: pd.Series) -> pd.Series:
    v = pd.to_numeric(s, errors="coerce")
    sd = float(v.std(ddof=0))
    return (v - float(v.mean())) / sd if sd > 0 else v * 0.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if a.selftest:
        return selftest()
    t0 = time.time()
    selftest()
    W.OUT.mkdir(parents=True, exist_ok=True)
    rows, M, n_files, n_rows_offered = build()
    if not rows:
        raise SystemExit("ABORT: no assistant turn survived the reader, so the wave has no subject - and EXP-0190 "
                         "measured 1.0 parse coverage, so this is a broken reader rather than an empty release")
    F = pd.DataFrame(rows)
    before = len(F)
    tcols = ["traj_id", "n_turns_all", "n_obs", "n_calls_traj", "n_err_obs", "repeat_share",
             "error_share", "final_obs_clean", "early_hypo", "task_words", "first_entities", "first_verbs",
             "first_ordering", "first_constraint", "first_chars"]
    clash = sorted({c for c in tcols if c in F.columns} - {"traj_id"})
    if clash:
        raise SystemExit(f"ABORT: the trajectory summary re-supplies {clash}, which the merge would silently rename to "
                         f"<name>_x and <name>_y - a design reading the plain name would then be missing a column")
    F = F.merge(M[tcols], on="traj_id", how="left", validate="many_to_one")
    if len(F) != before:
        raise SystemExit(f"ABORT: the trajectory-level join moved the row count from {before} to {len(F)}, so a "
                         f"traj_id is duplicated in the summary and every turn row would inherit it twice")
    F["log_turns"] = np.log1p(F["n_turns"].astype(float))
    F["body_chars_log"] = np.log1p(F["body_chars"].astype(float))
    F["first_chars_log"] = np.log1p(F["first_chars"].astype(float))
    F["task_words_log"] = np.log1p(F["task_words"].astype(float))
    F["spec_sum"] = F[["first_entities", "first_verbs", "first_ordering", "first_constraint"]].sum(axis=1)
    for c in ("spec_sum", "first_entities", "first_verbs", "first_ordering", "first_constraint"):
        F[c + "_z"] = z(F[c])
    F["hypo_overlap_z"] = z(F["hypo_overlap"])
    F["alien_overlap_z"] = z(F["alien_overlap"])
    F["task_overlap_z"] = z(F["task_overlap"])
    F["obs_new_z"] = z(F["obs_new_share"])
    F["uncert_z"] = z(F["uncert"])
    F["suffic_z"] = z(F["suffic"])
    F["turn_quartile"] = pd.qcut(F["n_turns"].rank(method="first"), 4,
                                 labels=["q1_shortest", "q2", "q3", "q4_longest"]).astype(str)
    F["position_third"] = pd.cut(F["position"], [0.0, 1 / 3, 2 / 3, 1.0001],
                                 labels=["first_third", "middle_third", "last_third"]).astype(str)
    cats = M["category"].value_counts()
    cen = census()
    cm = cen["measured"]
    x = {"trajectories": (int(M["traj_id"].nunique()), int(cm["trajectories_parsed"])),
         "assistant_turns": (int(M["n_turns_all"].sum()), int(cm["assistant_turns_total"])),
         "observations": (int(M["n_obs"].sum()), int(cm["observations_total"])),
         "unparsed_call_share": (round(float(M["n_unparsed"].sum() / max(1, M["n_calls_traj"].sum())), 4),
                                 float(cm["calls_unparsed_share"])),
         "early_hypothesis_trajectories": (int(M["early_hypo"].sum()),
                                           int(cm["trajectories_stating_a_hypothesis_in_the_first_two_turns"])),
         "trajectories_with_4plus_turns": (int((M["n_turns_all"] >= 4).sum()),
                                           int(cm["trajectories_with_4plus_turns"])),
         "terminal_turn_share": (round(float(M["ends_on_assistant"].mean()), 4),
                                 float(cm["trajectories_ending_on_an_assistant_turn_share"])),
         "every_call_answered_share": (round(float(M["call_turns_answered"].mean()), 4),
                                       float(cm["trajectories_answering_every_call_share"])),
         "failure_marker_share": (round(float(M["n_err_obs"].sum() / max(1, M["n_obs"].sum())), 4),
                                  float(cm["observations_with_a_failure_marker_share"])),
         "self_correcting_trajectories": (int(M["correct"].sum()),
                                          int(cm["trajectories_with_an_explicit_self_correction"])),
         "countable_plan_trajectories": (int(M["countable_plan"].sum()),
                                         int(cm["trajectories_with_a_countable_first_turn_plan"])),
         "repeated_call_trajectories": (int(M["repeat"].sum()),
                                        int(cm["trajectories_with_a_repeated_identical_call"])),
         "median_first_turn_entities": (float(M["first_entities"].median()),
                                        float(cm["median_entities_in_the_first_turn"])),
         "median_first_turn_verbs": (float(M["first_verbs"].median()), float(cm["median_action_verbs_in_the_first_turn"])),
         "categories_100plus": (int((cats >= 100).sum()), int(cm["categories_with_100plus_trajectories"]))}
    off = {k: v for k, v in x.items() if abs(float(v[0]) - float(v[1])) > max(0.005, 0.002 * abs(float(v[1])))}
    if off:
        raise SystemExit(f"ABORT: the frame and EXP-0190 ({cen['file']}) disagree on {off} as (frame, census) - the "
                         f"two are one reader with one rule set, so a definition changed in only one of them")
    dest_f = W.OUT / "EXP0191_wave8_turn_features.csv.gz"
    dest_t = W.OUT / "EXP0191_wave8_trajectory_summary.csv.gz"
    F.to_csv(dest_f, compression="gzip", index=False, encoding="utf-8")
    M.to_csv(dest_t, compression="gzip", index=False, encoding="utf-8")
    art = {"exp_id": EXP, "corpus": "hermes-agent-reasoning-traces, whole release after the duplicate drop",
           "seed": SEED, "files_read": n_files, "rows_offered": n_rows_offered,
           "trajectories": int(M["traj_id"].nunique()), "turns_measured": int(len(F)),
           "turns_in_release": int(M["n_turns_all"].sum()),
           "turns_dropped_below_20_chars": int(M["n_turns_all"].sum() - len(F)),
           "census_artefact": cen["file"], "census_cross_check": {k: [v[0], v[1]] for k, v in x.items()},
           "cluster_unit": TD8.COMMON["sample"]["cluster_unit"],
           "by_category": {str(k): int(v) for k, v in cats.items()},
           "mean_turns_per_measured_trajectory": round(float(len(F) / max(1, M["traj_id"].nunique())), 2),
           "trajectories_with_early_hypothesis": int(M["early_hypo"].sum()),
           "mean_hypo_overlap": round(float(F["hypo_overlap"].mean()), 4),
           "mean_alien_overlap": round(float(F["alien_overlap"].mean()), 4),
           "mean_obs_new_share": round(float(F["obs_new_share"].mean()), 4),
           "correction_turns": int((F["correct"] > 0).sum()),
           "calls_total": int(M["n_calls_traj"].sum()), "observations_total": int(M["n_obs"].sum()),
           "final_obs_clean_share": round(float(M["final_obs_clean"].mean()), 4),
           "mean_repeat_share": round(float(M["repeat_share"].mean()), 4),
           "mean_error_share": round(float(M["error_share"].mean()), 4),
           "median_spec_sum": float(M[["first_entities", "first_verbs", "first_ordering",
                                       "first_constraint"]].sum(axis=1).median()),
           "frames": [dest_f.name, dest_t.name], "started_at": W.now(),
           "wallclock_sec": round(time.time() - t0, 1), "invocation": " ".join([sys.executable] + sys.argv),
           "run_cost": W.run_cost_row(EXP, t0, int(len(F)), int(F.shape[1]), "wave-8 turn frame")}
    dest = W.write_raw(EXP, "wave8_turn_matrix", art)
    print(json.dumps({k: v for k, v in art.items() if k not in ("by_category", "census_cross_check")},
                     indent=1, ensure_ascii=False, default=str)[:1400])
    print(f"\n{EXP}: wrote {dest_f.name} ({len(F)} turns), {dest_t.name} ({len(M)} trajectories) and {dest.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
