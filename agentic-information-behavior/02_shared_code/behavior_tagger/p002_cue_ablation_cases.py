"""EXP-0107 (spec E04, E10, E16, E17 for P002): what the stage codex is made of, and what happens when a part is removed.

P002's E-coverage (EXP-0103) left four steps open because the paper had run the instrument but never taken it apart:

  * **E04** - the seven cue families and the two information sources (command text, reasoning text) are the instrument.
    Nothing measured how much of the published stage structure each one carries.
  * **E10** - the stage shares are reported over all SWE-ZERO trajectories. Nothing asked whether they hold across
    repositories, which is the only "domain" variable this corpus actually records.
  * **E16** - no case was read. An aggregate share cannot show *why* a turn is coded `verify` rather than `extraction`.
  * **E17** - no intervention was made. The spec asks for a controlled change to the input to see whether the labels
    follow the mechanism or the position.

All four are computed from one seeded sample of turns, re-coded under arms fixed in this docstring before the sample
was touched:

arms: `frozen` (the published codex) · `without_rule:<label>` one cue family removed · `command_source_only` reasoning
text hidden · `thought_source_only` command text hidden · `drop_last_turn` / `drop_first_turn` (position intervention) ·
`force_test_command` (every command replaced by `python -m pytest test.py`, reasoning untouched - if labels still say
`verify`, the reasoning text is what drives them).

Statistics per arm: the stage-share vector, its total-variation distance from `frozen`, and the per-label flip rate.
For E10, the frozen arm's top-stage share per repository (>= 200 turns) with a two-sided Fisher test against the rest
of the sample, Holm-corrected across repositories. For E16, up to two real turns per load-bearing arm, quoted from the
sample with their instance ids. Case reading never substitutes for the aggregate: both are reported side by side.

    python 02_shared_code/behavior_tagger/p002_cue_ablation_cases.py [--shards 6] [--rows 400]
"""
from __future__ import annotations
import argparse, collections, glob, json, pathlib, random, re, sys, time
from collections import Counter

import pandas as pd
import pyarrow.parquet as pq
from scipy.stats import fisher_exact

ROOT = next(a for a in [pathlib.Path(__file__).resolve().parent,
                        *pathlib.Path(__file__).resolve().parents] if (a / "00_program_registry").is_dir())
sys.path.insert(0, str(ROOT / "02_shared_code" / "behavior_tagger"))
import isp_stage_coder as C                                                  # noqa: E402
DATA = pathlib.Path(str(C.DATA))
RAW, PROC = ROOT / "results_raw", ROOT / "results_processed"
SEED = 42
MIN_TURNS_PER_REPO = 200
TOP_STAGE_SHARE = 0.15          # a stage is "the paper's finding" if it holds >= this share of turns


def code(thought: str, cmd: str, rules) -> str:
    """`isp_stage_coder.code_turn` with the rule list supplied, so an arm can remove one cue family or one source."""
    for label, cmd_re, thought_re in rules:
        c = cmd_re.search(cmd) if cmd else None
        t = thought_re.search(thought) if thought_re.pattern != r"^\s*$" else None
        if c or t:
            if cmd or label == "clarification":
                return label
    return "uncodable"


def sample_turns(shards, rows_per_shard):
    files = [f for f in sorted(glob.glob(str(DATA / "**/*.parquet"), recursive=True)) if ".cache" not in f]
    picks = sorted(random.Random(SEED).sample(range(len(files)), min(shards, len(files))))
    out = []
    for i in picks:
        t = pq.read_table(files[i], columns=["instance_id", "repo", "messages", "exit_status"])
        for r in t.slice(0, rows_per_shard).to_pylist():
            msgs = r["messages"]
            for j, m in enumerate(msgs):
                if m["role"] != "assistant":
                    continue
                thought, cmd = C.split_turn(str(m["content"]))
                out.append({"instance_id": r["instance_id"], "repo": str(r["repo"]),
                            "exit_status": r["exit_status"], "turn_index": j, "n_turns": len(msgs),
                            "thought": thought, "cmd": cmd})
    return picks, out


def shares(labels):
    n = len(labels) or 1
    c = Counter(labels)
    return {k: round(v / n, 4) for k, v in sorted(c.items())}


def tvd(a, b):
    keys = set(a) | set(b)
    return round(sum(abs(a.get(k, 0.0) - b.get(k, 0.0)) for k in keys) / 2, 4)


def run_arm(turns, arm):
    rules = list(C.RULES)
    src_cmd, src_thought, drop_pos, force_cmd = True, True, None, None
    if arm.startswith("without_rule:"):
        lbl = arm.split(":", 1)[1]
        rules = [r for r in rules if r[0] != lbl]
    elif arm == "command_source_only":
        src_thought = False
    elif arm == "thought_source_only":
        src_cmd = False
    elif arm == "drop_last_turn":
        drop_pos = "last"
    elif arm == "drop_first_turn":
        drop_pos = "first"
    elif arm == "force_test_command":
        force_cmd = "python -m pytest test.py"
    labels, flips = [], []
    by_idx = collections.defaultdict(list)
    for i, t in enumerate(turns):
        by_idx[(t["instance_id"],)].append(i)
    keep = set(range(len(turns)))
    if drop_pos:
        for key, idxs in by_idx.items():
            last_assistant = max(idxs)
            first_assistant = min(idxs)
            keep.discard(last_assistant if drop_pos == "last" else first_assistant)
    for i, t in enumerate(turns):
        if i not in keep:
            continue
        thought = t["thought"] if src_thought else ""
        cmd = (force_cmd if force_cmd else (t["cmd"] if src_cmd else ""))
        lab = code(thought, cmd, rules)
        labels.append(lab)
        flips.append((t, lab))
    return shares(labels), flips


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shards", type=int, default=6)
    ap.add_argument("--rows", type=int, default=400, help="rows read per sampled shard")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    if not DATA.is_dir():
        raise SystemExit(f"ABORT: {DATA} is not on this disk")
    picks, turns = sample_turns(a.shards, a.rows)
    if not turns:
        raise SystemExit("ABORT: the sample produced no assistant turns")
    arms = (["frozen"] + [f"without_rule:{r[0]}" for r in C.RULES]
            + ["command_source_only", "thought_source_only", "drop_last_turn", "drop_first_turn",
               "force_test_command"])
    res_arms, flip_examples = {}, collections.defaultdict(list)
    frozen_sh, frozen_flip = run_arm(turns, "frozen")
    res_arms["frozen"] = {"shares": frozen_sh, "tvd_vs_frozen": 0.0, "turns_relabelled": 0, "share_relabelled": 0.0}
    for arm in arms:
        if arm == "frozen":
            continue
        sh, flips = run_arm(turns, arm)
        res_arms[arm] = {"shares": sh}
        moved = sum(1 for (t, lab), (t2, f2) in zip(flips, frozen_flip) if lab != f2)
        res_arms[arm]["tvd_vs_frozen"] = tvd(sh, frozen_sh)
        res_arms[arm]["turns_relabelled"] = moved
        res_arms[arm]["share_relabelled"] = round(moved / max(1, len(frozen_flip)), 4)
        for (t, lab), (t2, f2) in zip(flips, frozen_flip):
            if lab != f2 and len(flip_examples[arm]) < 2:
                flip_examples[arm].append({"instance_id": t["instance_id"], "repo": t["repo"],
                                           "frozen_label": f2, "arm_label": lab,
                                           "cmd": re.sub(r"\s+", " ", t["cmd"])[:120],
                                           "thought": re.sub(r"\s+", " ", t["thought"])[:160]})
    frozen = res_arms["frozen"]["shares"]
    # A representative-sample guard: the arms are computed on a smaller seeded sample than the published main run, so
    # the sample's own frozen shares are checked against the published ones before anything is concluded from the arms.
    pub = pd.read_csv(ROOT / "papers/P002_isp_stage_measurement/tables/table_stage_shares.csv")
    pub = pub[pub["corpus"] == "SWE-ZERO-12M"].set_index("stage")["share"].astype(float).to_dict()
    pub = {k: round(float(v), 4) for k, v in pub.items()}
    drift = tvd(frozen, pub)
    if drift > 0.10:
        raise SystemExit(f"ABORT: the sampled shares drift {drift} (TVD) from the published SWE-ZERO shares "
                         f"{pub} vs sample {frozen} - the ablation arms would be read on an unrepresentative sample")
    top = max(frozen, key=frozen.get)
    # E10: does the top stage's share hold repository by repository?
    per_repo = collections.defaultdict(list)
    for t in turns:
        per_repo[t["repo"]].append(code(t["thought"], t["cmd"], C.RULES))
    repos = {k: v for k, v in per_repo.items() if len(v) >= MIN_TURNS_PER_REPO}
    e10 = {}
    for k, labs in sorted(repos.items()):
        in_k = sum(1 for l in labs if l == top)
        out_k = sum(1 for kk, vv in repos.items() if kk != k for l in vv if l == top)
        out_n = sum(len(vv) for kk, vv in repos.items() if kk != k)
        odds, p = fisher_exact([[in_k, len(labs) - in_k], [out_k, out_n - out_k]])
        e10[k] = {"turns": len(labs), f"share_{top}": round(in_k / len(labs), 4),
                  "rest_share": round(out_k / max(1, out_n), 4), "or": None if (odds != odds or odds in (0, float("inf"))) else round(float(odds), 3),
                  "p_two_sided": round(float(p), 6)}
    holm = holm_correct({k: v["p_two_sided"] for k, v in e10.items()})
    for k, v in e10.items():
        v["p_holm"] = holm[k]
        v["survives_holm_0p05"] = v["p_holm"] < 0.05
    out = {"exp_id": "EXP-0107", "at": time.strftime("%Y-%m-%dT%H:%M:%S"), "seed": SEED,
           "sample": {"shards": [str(DATA.relative_to(DATA.parent)) + f"/shard#{i}" for i in picks],
                      "n_trajectories": len({t['instance_id'] for t in turns}), "n_assistant_turns": len(turns),
                      "rows_per_shard": a.rows,
                      "note": "the arms are recomputations over the SAME seeded turns, so every difference is the rule, "
                              "not the sample"},
           "representativeness": {"published_swe_zero_shares": pub, "sample_frozen_shares": frozen,
                                  "tvd_sample_vs_published": drift,
                                  "guard": "aborted above unless TVD <= 0.10"},
           "arms": res_arms, "frozen_top_stage": {"label": top, "share": frozen[top]},
           "e10_by_repository": e10,
           "e16_cases": {k: v for k, v in flip_examples.items()},
           "wallclock_sec": round(time.time() - t0, 1)}
    load = sorted(((res_arms[k].get("tvd_vs_frozen", 0), k) for k in arms if k != "frozen"), reverse=True)
    cue_load = [k for k in arms if k.startswith("without_rule:") and res_arms[k].get("share_relabelled", 0) > 0.01]
    ftc = res_arms["force_test_command"]["share_relabelled"]
    reading = (f"the arm that moves the labels most is `{load[0][1]}` (TVD {load[0][0]} against the frozen codex); "
               + (f"removing these cue families relabels >1% of turns: {', '.join(cue_load)}" if cue_load else
                  "no single cue family relabels more than 1% of turns on its own, so the published structure is "
                  "distributed over the codex rather than carried by one rule")
               + f"; replacing every command with a fixed test command relabels {ftc} of turns, so "
               + ("the command text is what the codex keys on" if ftc > 0.1 else
                  "the reasoning text is what the codex keys on"))
    out["verdict"] = {"most_load_arm": load[0][1], "most_load_tvd": load[0][0],
                      "cue_families_whose_removal_relabels_over_1pct": cue_load,
                      "repositories_surviving_holm": [k for k, v in e10.items() if v["survives_holm_0p05"]],
                      "force_test_command_relabelled": ftc, "reading": reading}
    (RAW / f"EXP0107_p002_ablation_cases_{time.strftime('%Y%m%dT%H%M%S')}.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    pd.DataFrame([{"arm": k, "turns": len(turns), **v["shares"], "tvd_vs_frozen": v.get("tvd_vs_frozen", 0.0),
                   "share_relabelled": v.get("share_relabelled", 0.0)} for k, v in res_arms.items()]).to_csv(
        PROC / "EXP0107_ablation_arms.csv", index=False)
    print(f"  sampled {out['sample']['n_assistant_turns']} assistant turns from "
          f"{out['sample']['n_trajectories']} trajectories")
    for k in arms:
        v = res_arms[k]
        print(f"  {k:26s} tvd={v.get('tvd_vs_frozen', 0.0):<7} relabelled={v.get('share_relabelled', 0.0)}")
    print(f"  top stage {top} ({frozen[top]}); repositories with >= {MIN_TURNS_PER_REPO} turns: {len(repos)}")
    print("  repositories surviving Holm at 0.05:", out["verdict"]["repositories_surviving_holm"] or "none")
    print("  load-bearing cue families:", out["verdict"]["cue_families_whose_removal_relabels_over_1pct"] or "none")
    print("  wrote EXP0107 artefact + arms csv")
    return 0


def holm_correct(ps):
    items = sorted(ps.items(), key=lambda kv: kv[1])
    m = len(items)
    out, prev = {}, 0.0
    for i, (k, p) in enumerate(items):
        adj = min(1.0, max(prev, (m - i) * p))
        out[k] = round(adj, 6)
        prev = adj
    return out


if __name__ == "__main__":
    sys.exit(main())
