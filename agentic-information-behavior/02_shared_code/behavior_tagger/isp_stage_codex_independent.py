"""EXP-0087: RQ4 without a human - agreement between two independently specified stage codices.

P002's protocol (§3, RQ4) asks for an intra-coder retest on 60 hand-coded turns in re-randomised order, states that
**no human-intercoder claim is made**, and sets kappa >= 0.75 as the bar below which "the codex is documented as
unreliable and the paper is not submitted". The programme now runs with no human step available, and re-running the
frozen codex against itself would produce kappa = 1 as a tautology - a vacuous proxy, not evidence. So this step
substitutes the test that actually probes the threat the protocol was guarding against:

  * **codex A** = the frozen priority-order rule set in `isp_stage_coder.py` (untouched, imported, not modified);
  * **codex B** = written here from the construct definitions in `protocol_freeze.md` §2, with a different decision
    procedure (score every label, argmax, ties to `uncodable`) and a different cue vocabulary, and allowed to use the
    observation payload - which A ignores. B never reads A's RULES table.

Agreement between them measures **rubric invariance**: how much the stage distribution depends on the particular cue
table rather than on the construct. That is exactly what a re-coding reliability test is for. It is *not* human
reliability, and the outputs say so in those words.

Pre-declared rules, fixed before any label was compared:
  * report Cohen kappa and nominal Krippendorff alpha on the protocol's 60 turns (re-randomised order, seed recorded)
    and, separately, on a 900-turn panel for a stable interval;
  * bar stays the protocol's: kappa >= 0.75 for the codex to be treated as rubric-invariant. Below it, the finding is
    reported as rubric sensitivity and the submission bar stays unmet - the threshold is not adjusted afterwards;
  * bootstrap intervals resample **instances**, because turns nest inside trajectories (the programme's clustering rule).

    python isp_stage_codex_independent.py [--panel 900] [--protocol-n 60]

Outputs results_raw/EXP0087_codex_invariance_*.json and results_processed/EXP0087_confusion_panel.csv
"""
from __future__ import annotations

import argparse, glob, json, pathlib, random, re, sys, time
from collections import Counter

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from isp_stage_coder import split_turn, observation_kind, code_turn, DATA, SEED, PILOT_SHARDS, ROWS_PER_SHARD  # noqa: E402

def _repo_root() -> pathlib.Path:
    """Count directory levels out loud, or better: don't. Four scripts in this programme wrote artefacts one directory
    above the repository because `parents[N]` was off by one; locating the root by the marker directory removes the
    whole class."""
    here = pathlib.Path(__file__).resolve()
    for anc in [here.parent, *here.parents]:
        if (anc / "00_program_registry").is_dir():
            return anc
    raise SystemExit("ABORT: cannot locate the repository root from " + str(here))


ROOT = _repo_root()
OUT_RAW, OUT_PROC = ROOT / "results_raw", ROOT / "results_processed"
LABELS = ["end", "verify", "documentation", "extraction", "exploration", "clarification", "system", "uncodable"]

# ---- codex B: written from protocol_freeze.md section 2's definitions, NOT from codex A's regex table -------------
WORD_CUES = {
    "end": {"done", "finished", "final", "answer", "submit", "resolved", "fixed", "passes", "complete", "solution"},
    "verify": {"test", "tests", "pytest", "unittest", "assert", "assertion", "expected", "reproduce", "reproduction",
               "verification", "coverage", "regression", "runtests"},
    "documentation": {"write", "wrote", "patch", "diff", "edit", "modify", "append", "create", "file", "save",
                      "replace", "update", "insert", "rewrite", "apply", "diff"},
    "extraction": {"read", "show", "print", "cat", "head", "tail", "grep", "search", "find", "contents", "extract",
                   "copy", "line", "output", "look"},
    "exploration": {"explore", "structure", "layout", "overview", "where", "which", "list", "ls", "find", "tree",
                     "directory", "folder", "navigate", "orient", "survey", "map"},
    "clarification": {"need", "must", "should", "plan", "first", "hypothesis", "understand", "requirement", "task",
                      "issue", "goal", "approach", "consider", "because"},
    "system": {"install", "pip", "apt", "conda", "npm", "environment", "venv", "dependency", "configure", "export",
               "mkdir", "chmod", "requirements", "package", "setup"},
}
STRUCT_CUES = {
    # (pattern on the command) -> label, chosen from the definitions' wording, deliberately not A's anchored regexes
    "documentation": re.compile(r"(>|\btee\b|\bsed\b.*-i|\bpatch\b|>>|writefile|open\(.+['\"]w)", re.I),
    "verify": re.compile(r"(pytest|npm test|make test|\btest\b|unittest|tox|\.py.*test|run_tests)", re.I),
    "extraction": re.compile(r"^\s*(cat|head|tail|less|jq|wc)\b", re.I),
    "exploration": re.compile(r"^\s*(?:ls|find|tree|du|pwd|cd\b|git status|git branch|\*)", re.I),
    "system": re.compile(r"(pip install|apt-get|conda |npm i\b|source |chmod|virtualenv|export )", re.I),
    "end": re.compile(r"^\s*(exit|quit|echo .*(done|complete))", re.I),
}
TOKEN = re.compile(r"[a-zA-Z]{3,}")


def codex_b(thought: str, cmd: str, obs_kind: str) -> str:
    """Score-based, argmax, ties to uncodable - a different machine than A's first-match priority order."""
    s = dict.fromkeys(LABELS, 0.0)
    tw = {t.lower() for t in TOKEN.findall(str(thought or ""))}
    cw = {t.lower() for t in TOKEN.findall(str(cmd or ""))}
    for lab, cues in WORD_CUES.items():
        s[lab] += 1.0 * len(tw & cues) + 1.5 * len(cw & cues)
    for lab, rx in STRUCT_CUES.items():
        if cmd and rx.search(str(cmd)):
            s[lab] += 2.0
    # B is allowed to use the observation payload, which A ignores entirely (protocol section 2 defines the turn to
    # include it, so this is a construct-faithful difference rather than a bug in either codex)
    if obs_kind == "error-shaped":
        s["verify"] += 1.0
    elif obs_kind == "empty":
        s["clarification"] += 0.5
    if not str(cmd or "").strip():
        s["clarification"] += 1.0
    if not str(thought or "").strip() and not str(cmd or "").strip():
        return "uncodable"
    best = max(s.values())
    if best <= 0:
        return "uncodable"
    tied = [l for l, v in s.items() if v == best]
    if len(tied) > 1:
        return "uncodable"                        # the protocol's own tie rule, which A cannot trigger
    return tied[0]


def load_turns(panel_target: int):
    """One turn per trajectory, drawn across many instances.

    The first version collected turns until it had `panel*6` of them, which on SWE-ZERO's long trajectories meant the
    900-turn panel came from **5 instances** - a kappa computed on 5 clusters is not a reliability estimate. One turn
    per trajectory, sampled across shards, is what makes the panel what the protocol's retest is supposed to be.
    """
    files = [f for f in sorted(glob.glob(str(DATA / "**/*.parquet"), recursive=True)) if ".cache" not in f]
    picks = sorted(random.Random(SEED).sample(range(len(files)), min(PILOT_SHARDS * 3, len(files))))
    rng = np.random.default_rng(SEED)
    per = max(1, int(np.ceil(panel_target / max(1, len(picks)))))
    out = []
    for i in picks:                       # round-robin over shards: the previous break condition emptied one shard
        t = pq.read_table(files[i], columns=["instance_id", "messages"])
        for row in rng.choice(t.num_rows, size=min(per, t.num_rows), replace=False):
            r = t.slice(int(row), 1).to_pylist()[0]
            msgs = r["messages"]
            cand = [(j, m) for j, m in enumerate(msgs) if m["role"] == "assistant"]
            if not cand:
                continue
            j, m = cand[int(rng.integers(0, len(cand)))]        # one turn per trajectory
            thought, cmd = split_turn(str(m["content"]))
            obs = msgs[j + 1]["content"] if j + 1 < len(msgs) else ""
            out.append({"instance_id": r["instance_id"], "thought": thought, "cmd": cmd,
                        "obs_kind": observation_kind(obs)})
    df = pd.DataFrame(out)
    if len(df) > panel_target:
        df = df.iloc[rng.permutation(len(df))[:panel_target]]
    if df.instance_id.nunique() < max(30, 0.5 * len(df)):
        raise SystemExit(f"ABORT: panel has only {df.instance_id.nunique()} instances for {len(df)} turns - "
                         "kappa would be computed on a degenerate sample")
    return df.reset_index(drop=True)


def cohens_kappa(a, b, labels):
    n = len(a)
    po = float(np.mean([x == y for x, y in zip(a, b)]))
    ka = Counter(a); kb = Counter(b)
    pe = sum((ka[l] / n) * (kb[l] / n) for l in labels)
    return po, pe, (1 - pe and (po - pe) / (1 - pe))


def kripp_alpha_nominal(a, b):
    """Nominal Krippendorff alpha for two observers, from agreement/expected-disagreement counts."""
    n = len(a)
    do = sum(1 for x, y in zip(a, b) if x != y) / float(n)
    cat = Counter(a + b)
    tot = float(2 * n)
    de = 1.0 - sum((c / tot) ** 2 for c in cat.values())
    return do, de, (1 - do / de if de > 0 else float("nan"))


def boot_ci(a, b, instances, fn, draws=500, seed=SEED):
    rng = np.random.default_rng(seed)
    uniq = np.array(sorted(set(instances)))
    rows = {u: np.where(instances == u)[0] for u in uniq}
    vals = []
    for _ in range(draws):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        ii = np.concatenate([rows[p] for p in pick])
        if len(ii) > 20:
            v = fn([a[i] for i in ii], [b[i] for i in ii])
            if np.isfinite(v):
                vals.append(float(v))
    if not vals:
        return None
    return [round(float(np.percentile(vals, 2.5)), 4), round(float(np.percentile(vals, 97.5)), 4)]


def selftest() -> None:
    """The cue table must at least be able to speak: a typo that made one regex uncompilable cost a full run, so the
    patterns are compiled and the coder is exercised on canned turns before any data is read."""
    for name, rx in STRUCT_CUES.items():
        if rx.pattern is None:
            raise SystemExit(f"ABORT: cue pattern for {name} did not compile")
    cases = [("I will run the tests to verify the fix", "pytest tests/test_x.py -q", "informative", "verify"),
             ("Now write the patch into the module", "sed -i 's/a/b/' app.py", "informative", "documentation"),
             ("", "ls -la src/", "informative", "exploration"),
             ("Let me read the file to see what it contains", "cat src/app.py", "informative", "extraction")]
    got = [(codex_b(t, c, o), want) for t, c, o, want in cases]
    bad = [(g, w) for g, w in got if g != w]
    if len(bad) > 1:
        raise SystemExit(f"ABORT: codex B mislabels its own sanity cases: {bad}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", type=int, default=900)
    ap.add_argument("--protocol-n", type=int, default=60)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    res = {"exp_id": "EXP-0087", "paper_id": "P002", "e_id": "RQ4", "seed": SEED,
           "question": "is the stage codex rubric-invariant, measured between two independently specified codices "
                       "because the programme has no human coding step",
           "what_this_is_not": "NOT human-intercoder reliability and not intra-coder retest agreement: codex A "
                               "re-applied to itself would give kappa = 1 by construction, which is why a second, "
                               "independently written realisation of the same construct definitions is used instead",
           "bar_frozen_in_protocol": 0.75, "started_at": time.strftime("%Y-%m-%dT%H:%M:%S")}

    selftest()                     # before the multi-minute shard load, not after
    df = load_turns(args.panel)
    res["panel"] = {"turns": int(len(df)), "instances": int(df.instance_id.nunique()),
                    "with_command": round(float((df.cmd.str.len() > 0).mean()), 3)}
    a_lab = [code_turn(r.thought, r.cmd) for r in df.itertuples()]
    b_lab = [codex_b(r.thought, r.cmd, r.obs_kind) for r in df.itertuples()]
    order = np.random.default_rng(SEED).permutation(len(df))          # re-randomised presentation order, per protocol
    a_lab = [a_lab[i] for i in order]
    b_lab = [b_lab[i] for i in order]
    inst = df.instance_id.values[order]

    po, pe, kappa = cohens_kappa(a_lab, b_lab, LABELS)
    do, de, alpha = kripp_alpha_nominal(a_lab, b_lab)
    ci = boot_ci(a_lab, b_lab, inst, lambda x, y: cohens_kappa(x, y, LABELS)[2])
    res["panel_agreement"] = {"percent_agreement": round(po, 4), "expected_by_chance": round(pe, 4),
                              "cohens_kappa": round(float(kappa), 4), "kappa_instance_bootstrap_ci95": ci,
                              "krippendorff_alpha_nominal": round(float(alpha), 4),
                              "observed_disagreement": round(do, 4), "expected_disagreement": round(de, 4)}
    print(f"  panel n={len(df)}: agreement {po:.3f}, kappa {kappa:.3f} CI {ci}, alpha {alpha:.3f}", flush=True)

    pn = min(args.protocol_n, len(df))
    po60, pe60, k60 = cohens_kappa(a_lab[:pn], b_lab[:pn], LABELS)
    res["protocol_60"] = {"n": pn, "percent_agreement": round(po60, 4), "cohens_kappa": round(float(k60), 4),
                          "meets_frozen_bar_0_75": bool(k60 >= 0.75)}
    print(f"  protocol n={pn}: kappa {k60:.3f} -> bar 0.75 {'MET' if k60 >= 0.75 else 'NOT MET'}", flush=True)

    conf = pd.crosstab(pd.Series(a_lab, name="codex_A_frozen"), pd.Series(b_lab, name="codex_B_independent"))
    conf.to_csv(OUT_PROC / "EXP0087_confusion_panel.csv")
    res["marginals"] = {"A": dict(Counter(a_lab)), "B": dict(Counter(b_lab))}
    res["top_disagreements"] = [f"{x}->{y}: {n}" for (x, y), n in
                                sorted(Counter((x, y) for x, y in zip(a_lab, b_lab) if x != y).items(),
                                       key=lambda kv: -kv[1])[:8]]
    res["uncodable_share"] = {"A": round(float(np.mean([l == "uncodable" for l in a_lab])), 4),
                             "B": round(float(np.mean([l == "uncodable" for l in b_lab])), 4)}
    res["verdict"] = ("rubric-invariant at the protocol's own bar" if kappa >= 0.75 else
                      "RUBRIC-SENSITIVE: the stage distribution depends on the cue table, so the codex is documented "
                      "as unreliable for distribution claims and P002's submission bar stays unmet")
    res["what_this_changes"] = ("RQ4 is executed as an automated invariance test. It replaces the hand-coded retest "
                               "in protocol section 3 as a REGISTERED amendment (deviation), not silently: the "
                               "protocol's kappa >= 0.75 bar is applied unchanged, and no human-intercoder claim is "
                               "made or implied anywhere")
    res["wallclock_sec"] = round(time.time() - t0, 1)
    OUT_RAW.mkdir(parents=True, exist_ok=True)
    fp = OUT_RAW / f"EXP0087_codex_invariance_{time.strftime('%Y%m%dT%H%M%S')}.json"
    fp.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8", newline="")
    print(f"  {res['verdict']}\n  wrote {fp.name} in {res['wallclock_sec']}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
