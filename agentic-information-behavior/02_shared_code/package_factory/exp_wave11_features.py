"""EXP-0208: wave 11's trace frame - what each rollout said, in what order, and what its neighbour inherited.

Two tables come out of one pass over the estate's fixed 12-file rollout draw:

* `EXP0208_wave11_rollout_features.csv.gz`, one row per rollout: whether each of the eight component categories is
  present anywhere in the agent's own prose (commands removed), the turn index at which each is first mentioned over
  the rollout's turn count, whether each survives three deterministic compressions that keep the first 10%, 25% and
  50% of its assistant turns, the abstraction and uncertainty marker counts, the instance and repository the rollout
  belongs to and its attempt index inside that instance;
* `EXP0208_wave11_attempt_pairs.csv.gz`, one row per consecutive attempt pair of an instance: whether each category is
  present in the earlier attempt and in the later one, the same pair for a seeded *other* instance in the same
  repository (T137's alien arm), the content-word Jaccard between the two, the relation class the freeze bands
  (restatement / refinement / new), a contradiction flag, and both attempts' own labels.

The instruments are imported from EXP-0207 rather than restated, and the frame reproduces every aggregate the census
shares with it or refuses to write - the guard that has caught a definitional drift in every wave since wave 7. A
compression here is a re-coding of text the release already contains, never a re-run of the agent, which the
programme forbids. Attempt order inside an instance is the draw's row order, recorded as `attempt_index` (W11-D04).

    python 02_shared_code/package_factory/exp_wave11_features.py --selftest
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
import exp_wave6_features as EF6                                  # noqa: E402  the release reader
import probe_wave6_premises as P6                                 # noqa: E402  the command block, unchanged
import probe_wave11_premises as P11                          # noqa: E402  the instruments, one definition

EXP = "EXP-0208"
TD11 = __import__("topic_designs_wave11")
SEED = TD11.SEED
CATS = list(P11.COMPONENT)
BUDGETS = (0.10, 0.25, 0.50)                      # the three compression levels the freeze names


def turn_words(text: str) -> set:
    return P6.words(text)          # wave 6's content words, the ones the pair Jaccard is defined on


def code_rollout(traj: dict, idx: int) -> tuple:
    """One rollout -> its per-turn coding and the rollout-level row the designs are fitted on."""
    msgs = [dict(x) for x in (traj.get("messages") or [])]
    per_turn = []
    for m in msgs:
        if str(m.get("role")) != "assistant":
            continue
        t = str(m.get("content") or "")
        b = P6.COMMAND_BLOCK.search(t)
        prose = (t[:b.start()] if b else t)
        per_turn.append({"words": turn_words(prose), "comp": P11.components_of(prose),
                         "mc": P11.marker_counts(prose)})
    n = len(per_turn)
    if n == 0:
        return None, set()
    text_all = P11.assistant_text({'messages': msgs})
    whole_comp = P11.components_of(text_all)          # EXP-0207's rule, on the whole rollout text
    row = {"rollout_key": f"{traj.get('instance_id')}|{idx}", "instance_id": str(traj.get("instance_id")),
           "repo_prefix": str(traj.get("repo") or "none").split("/")[0],
           "submitted": int(str(traj.get("exit_status") or "").strip().lower() == "submitted"),
           "exit_status": str(traj.get("exit_status") or ""), "n_turns": int(n),
           "prose_chars": int(len(text_all))}
    words_all: set = set()
    for c in range(n):
        words_all |= per_turn[c]["words"]
    for cat in CATS:
        present = [c for c in range(n) if per_turn[c]["comp"][cat]]
        row[f"comp_{cat}"] = int(whole_comp[cat])
        row[f"first_pos_{cat}"] = round(present[0] / n, 4) if present else float("nan")
        for b in BUDGETS:
            keep = max(1, int(np.ceil(n * b)))
            row[f"surv{int(b * 100)}_{cat}"] = int(any(per_turn[c]["comp"][cat] for c in range(min(keep, n))))
    mc_all = P11.marker_counts(text_all)          # EXP-0207's counting: presence of each marker over the whole
    row["concrete_n"] = int(mc_all["concrete_n"])  # text, not a per-turn sum, so the two layers agree by
    row["abstract_n"] = int(mc_all["abstract_n"])  # construction rather than by luck
    row["uncert_n"] = int(mc_all["uncert_n"])
    row["negcon_n"] = int(mc_all["negcon_n"])
    for b in BUDGETS:
        keep = max(1, int(np.ceil(n * b)))
        row[f"surv{int(b * 100)}_uncert"] = int(any(per_turn[c]["mc"]["uncert_n"] for c in range(min(keep, n))))
        row[f"surv{int(b * 100)}_negcon"] = int(any(per_turn[c]["mc"]["negcon_n"] for c in range(min(keep, n))))
    row["turn_words"] = int(len(words_all))
    return row, words_all


def build() -> tuple:
    drawn, picks, rows_in_files, dupes = EF6.load_trajectories(int(TD11.COMMON["sample"]["traj_cap"]))
    rows, words_by = [], {}
    for i, t in enumerate(drawn):
        row, w = code_rollout(t, i)
        if row is None:
            continue
        rows.append(row)
        words_by[row["rollout_key"]] = w
    R = pd.DataFrame(rows)
    R["attempt_index"] = R.groupby("instance_id").cumcount() + 1
    R["n_attempts"] = R.groupby("instance_id")["rollout_key"].transform("size")
    # --- consecutive attempt pairs, with the alien arm drawn from another instance of the same repository ------
    by_repo = R.groupby("repo_prefix")["rollout_key"].apply(list).to_dict()
    lookup = R.set_index("rollout_key", drop=False)
    pairs = []
    for inst, g in R.groupby("instance_id", sort=True):
        g = g.sort_values("attempt_index")
        keys = g["rollout_key"].tolist()
        for a, b in zip(keys, keys[1:]):
            ea, eb = lookup.loc[a], lookup.loc[b]
            wa, wb = words_by[a], words_by[b]
            jac = len(wa & wb) / max(1, len(wa | wb)) if (wa or wb) else float("nan")
            cls = ("restatement" if jac >= 0.6 else "refinement" if jac >= 0.25 else "new") if jac == jac else "none"
            pool = sorted(k for k in by_repo.get(str(ea["repo_prefix"]), [])
                          if k.split("|")[0] != str(inst))
            alien = random.Random(f"{SEED}|{a}|{b}").choice(pool) if pool else None
            aw = words_by.get(alien, set())
            ajac = len(aw & wb) / max(1, len(aw | wb)) if aw else float("nan")
            acl = ("restatement" if ajac >= 0.6 else "refinement" if ajac >= 0.25 else "new") \
                if ajac == ajac else "none"
            rec = {"pair_key": f"{a}::{b}", "instance_id": str(inst), "repo_prefix": str(ea["repo_prefix"]),
                   "earlier": a, "later": b, "jaccard": round(jac, 4), "relation_class": cls,
                   "alien_pair_key": alien or "", "alien_jaccard": (round(ajac, 4) if ajac == ajac else None),
                   "alien_relation_class": acl,
                   "earlier_submitted": int(ea["submitted"]), "later_submitted": int(eb["submitted"]),
                   "earlier_turns": int(ea["n_turns"]), "later_turns": int(eb["n_turns"]),
                   "negcon_diff": int(abs(int(ea["negcon_n"]) - int(eb["negcon_n"]))),
                   "concreteness_earlier": int(ea["concrete_n"]) - int(ea["abstract_n"]),
                   "concreteness_later": int(eb["concrete_n"]) - int(eb["abstract_n"]),
                   "alien_concreteness_earlier": None}
            ar = lookup.loc[alien] if alien and alien in lookup.index else None
            if ar is not None:
                ar = ar.iloc[0] if isinstance(ar, pd.DataFrame) else ar
                rec["alien_concreteness_earlier"] = int(ar["concrete_n"]) - int(ar["abstract_n"])
            for cat in CATS:
                rec[f"earlier_{cat}"] = int(ea[f"comp_{cat}"])
                rec[f"later_{cat}"] = int(eb[f"comp_{cat}"])
                rec[f"alien_earlier_{cat}"] = (int(ar[f"comp_{cat}"]) if ar is not None else None)
            rec["contradiction"] = int(rec["relation_class"] != "new" and rec["negcon_diff"] >= 2)
            pairs.append(rec)
    P = pd.DataFrame(pairs)
    for cat in CATS:
        R[f"removal_{cat}"] = ((R[f"comp_{cat}"] == 1) & (R[f"surv25_{cat}"] == 0)).astype(int)
    R["concreteness"] = R["concrete_n"] - R["abstract_n"]
    return R, P, picks, rows_in_files, dupes, len(drawn)


def census() -> dict:
    for f in sorted(W.RAWRES.glob("EXP0207_wave11_premise_census_*.json"), reverse=True):
        a = json.loads(f.read_text(encoding="utf-8"))
        if "--rows" in str(a.get("invocation", "")):
            continue
        return {"file": f.name, "measured": a["measured"]}
    raise SystemExit("ABORT: no whole-sample EXP-0207 census exists, so this frame cannot check its own counting")


def selftest() -> int:
    """The per-turn, compression and pair codings proven on a hand-built instance of two rollouts."""
    fence = chr(96) * 3 + "bash" + chr(10)
    close = chr(96) * 3

    def mk(first, second, inst="i9"):
        return {"instance_id": inst, "exit_status": first, "repo": "acme/thing",
                "messages": [{"role": "user", "content": "the task is to fix the parser in /repo/x.py"},
                             {"role": "assistant", "content": "First I will read the file because the documentation "
                                                              "defines it." + fence + "cat x.py" + chr(10) + close},
                             {"role": "user", "content": "Output: no such file"},
                             {"role": "assistant", "content": second},
                             {"role": "user", "content": "Output: 1 passed"}]}
    a, _w = code_rollout(mk("Submitted", "Then I run the test; the result is a failure, so finally I am done."), 0)
    assert a["n_turns"] == 2 and a["comp_procedure"] == 1 and a["comp_result"] == 1, a
    assert a["surv10_procedure"] == 1 and 0.0 <= a["first_pos_procedure"] <= 1.0
    b, _w2 = code_rollout(mk("incomplete", "Then I look elsewhere; the output is empty."), 1)
    assert b["submitted"] == 0 and b["comp_procedure"] == 1
    print("SELFTEST OK: per-turn categories, first-mention positions, compression survival and labels land on built "
          "rollouts")
    return 0


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
    R, P, picks, rows_in_files, dupes, drawn = build()
    if R.empty:
        raise SystemExit("ABORT: no rollout produced assistant prose, so the wave has no subject")
    cm = census()["measured"]
    x = {"rollouts_parsed": (int(len(R)), int(cm["rollouts_parsed"])),
         "task_instances": (int(R["instance_id"].nunique()), int(cm["task_instances"])),
         "instances_with_2plus": (int((R["n_attempts"] >= 2).sum() and R.groupby("instance_id").size().ge(2).sum()),
                                  int(cm["instances_with_2plus_rollouts"])),
         "submitted": (int(R["submitted"].sum()),
                       int(round(float(cm["submitted_share"]) * float(cm["rollouts_parsed"])))), 
         "mean_chars_of_agent_text": (round(float(R["prose_chars"].mean()), 0), float(cm["mean_chars_of_agent_text"])),
         "median_assistant_turns": (float(R["n_turns"].median()), float(cm["median_assistant_turns"])),
         "rollouts_with_6plus_turns": (int((R["n_turns"] >= 6).sum()), int(cm["rollouts_with_6plus_assistant_turns"])),
         "rollouts_with_uncertainty": (int((R["uncert_n"] >= 1).sum()), int(cm["rollouts_with_uncertainty_language"])),
         "rollouts_with_negconstraints": (int((R["negcon_n"] >= 1).sum()),
                                          int(cm["rollouts_with_negative_constraints"])),
         "rollouts_with_identifiers": (int((R["concrete_n"] >= 1).sum()),
                                       int(cm["rollouts_with_code_identifiers"])),
         "mean_concrete_markers": (round(float(R["concrete_n"].mean()), 3), float(cm["mean_concrete_markers"])),
         "mean_abstract_markers": (round(float(R["abstract_n"].mean()), 3), float(cm["mean_abstract_markers"])),
         "median_component_kinds": (float(R[[f"comp_{c}" for c in CATS]].sum(axis=1).median()),
                                    float(cm["median_component_kinds_per_rollout"])),
         "repos_200plus": (int((R["repo_prefix"].value_counts() >= 200).sum()), int(cm["repos_200plus_rollouts"]))}
    for cat in CATS:
        x[f"rollouts_with_{cat}"] = (int(R[f"comp_{cat}"].sum()),
                                     int(cm["component_row_counts"].get(cat, 0)))
    off = {k: v for k, v in x.items()
           if abs(float(v[0]) - float(v[1])) > (0.005 if abs(float(v[1])) <= 1.0 else
                                                max(1.0, 0.005 * abs(float(v[1]))))}
    if off:
        raise SystemExit(f"ABORT: the frame and EXP-0207 disagree on {off} as (frame, census) - one reader with one "
                         f"rule set, so a definition changed in only one of them. Nothing was written.")
    dest_r = W.OUT / "EXP0208_wave11_rollout_features.csv.gz"
    dest_p = W.OUT / "EXP0208_wave11_attempt_pairs.csv.gz"
    R.to_csv(dest_r, compression="gzip", index=False, encoding="utf-8")
    P.to_csv(dest_p, compression="gzip", index=False, encoding="utf-8")
    art = {"exp_id": EXP, "corpus": "the estate's fixed 12-file SWE-ZERO rollout draw, as in waves 6 and 9",
           "seed": SEED, "files_read": picks, "rows_in_files": rows_in_files,
           "duplicate_rollout_rows_dropped_before_sampling": dupes, "rollouts_drawn": drawn,
           "rollouts_measured": int(len(R)), "attempt_pairs": int(len(P)),
           "pairs_by_class": {str(k): int(v) for k, v in P["relation_class"].value_counts().items()} if len(P) else {},
           "instances_with_2plus": int(R.groupby("instance_id").size().ge(2).sum()),
           "cluster_unit": TD11.COMMON["sample"]["cluster_unit"],
           "categories": CATS, "budgets": list(BUDGETS),
           "census_artefact": census()["file"], "census_cross_check": {k: [v[0], v[1]] for k, v in x.items()},
           "cross_check_verdict": "every shared aggregate reproduced",
           "survival_at_25_by_category": {c: round(float(R[f"surv25_{c}"].mean()), 4) for c in CATS},
           "survival_at_10_by_category": {c: round(float(R[f"surv10_{c}"].mean()), 4) for c in CATS},
           "submitted_share": round(float(R["submitted"].mean()), 4),
           "frames": [dest_r.name, dest_p.name], "started_at": W.now(),
           "wallclock_sec": round(time.time() - t0, 1), "invocation": " ".join([sys.executable] + sys.argv),
           "run_cost": W.run_cost_row(EXP, t0, int(len(R)), int(R.shape[1]), "wave-11 trace frame")}
    dest = W.write_raw(EXP, "wave11_trace_matrix", art)
    print(json.dumps({k: v for k, v in art.items() if k not in ("files_read", "census_cross_check")},
                     indent=1, ensure_ascii=False, default=str)[:1500])
    print(f"\n{EXP}: wrote {dest_r.name} ({len(R)} rollouts), {dest_p.name} ({len(P)} pairs) and {dest.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
