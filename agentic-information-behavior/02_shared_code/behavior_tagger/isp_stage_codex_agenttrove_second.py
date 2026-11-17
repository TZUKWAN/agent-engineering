"""EXP-0112: the AgentTrove instrument's rubric-invariance test, which addendum C5 promised and owed.

`protocol_freeze_agenttrove.md` section C5 commits, before seeing any number: "Whatever the codability result, the new
instrument is then subjected to the same rubric-invariance test EXP-0087 imposed on the frozen one (an independently
written second AgentTrove codex, bar kappa >= 0.75). A new instrument is not exempt from the test that P002's own codex
failed." EXP-0092 ran the instrument and never ran this test, so P002 still carries the debt (deviations D52) and the
AgentTrove stage distribution cannot yet carry a claim of its own.

What is held constant and what is varied: action extraction (addendum A) and the matching discipline (frozen priority
order, first match wins, command cue before text cue, a turn with no command codable only as `clarification`) are
**imported from the published codex**, not re-implemented, so the only difference between the two coders is the cue
table - which is what "rubric invariance" asks about. It is not human inter-coder reliability and is not claimed as
such, exactly as EXP-0087's record says.

The second table below was written from the construct definitions in `protocol_freeze.md` section 2 (one line per
stage: what the stage *means*), not by perturbing the frozen regexes, and it is reproduced verbatim here so a later
reader can check the two realisations side by side. Both are applied to the identical turn list.

Decision rule, fixed in the docstring above before the sample was read:
  * kappa >= 0.75 with an instance-clustered 95% interval -> the instrument is rubric-invariant enough to carry a
    distribution claim;
  * below -> reported as a failure, the AgentTrove shares stay labelled instrument-dependent, and no threshold, cue or
    sample is re-cut to move the number. Percent agreement, the confusion structure and each table's own RQ1 shares are
    reported because the disagreement pattern is the informative part, as it was for EXP-0087.

    python 02_shared_code/behavior_tagger/isp_stage_codex_agenttrove_second.py [--turns N]
"""
from __future__ import annotations

import argparse, glob, json, pathlib, random, re, sys, time

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "statistics"))
import isp_stage_codex_agenttrove as A           # noqa: E402  the published instrument, imported not copied
import isp_stage_main_p002 as M                   # noqa: E402  TROVE path, SEED, split_turn

ROOT = M.ROOT
OUT_RAW = ROOT / "results_raw"
SEED, SHARDS, ROWS_PER_SHARD = M.SEED, A.SHARDS, A.ROWS_PER_SHARD
KAPPA_BAR = 0.75                                   # addendum C5, as written
DRAW = 2000

# ---- the second realisation: one pattern pair per construct, written from the section-2 definitions
RULES2 = [
    # 1 "command or thought declares completion/answer/submit, or no command remains"
    ("end", re.compile(r'''("task_complete"\s*:\s*true|\b(echo\s+"?(done|complete)|exit\s+0|submit|finish)\b'''
                       r'''|\b(finalize|complete the task)\b)'''),
     re.compile(r"\b(i (have |am )?(done|finished|complete)|task (is )?(done|complete)|the (final|complete) (answer"
                r"|solution)|answer is|in summary, the (fix|solution|answer))\b")),
    # 2 "runs tests / reproduction of the issue, or greps for an expected string in output"
    ("verify", re.compile(r'''(pytest\b|\bunittest\b|npm (run )?test|yarn test|cargo test|make (test|check)|'''
                          r'''\.\/(tests?|run_tests?|verify)\b|rspec|phpunit|(diff|cmp)\b.*(\.exp|expected)|'''
                          r'''grep .*('|")(expected|should|ok|pass|traceback)('|"))'''),
     re.compile(r"\b(test(s|ing)? (suite|case|output)|run the tests|reproduce|expected (output|behaviour|result)|"
                r"verif(y|ies)|confir(m|ms)? that|assert|it passes)\b")),
    # 3 "writing/appending to files"
    ("documentation", re.compile(r'''(>>|>\s*[^\s&|;]|tee\b|sed -i|perl -i|patch\b|apply_patch|\b(edit|write_file|'''
                                 r'''create_file)\b|open\(\s*['"][^'"]+['"]\s*,\s*['"]w)'''),
     re.compile(r"\b(write|create|edit|modify|append|overwrite|patch|update) (the|a|an|my) "
                r"(file|code|script|test|function|class)\b|\bsave (the|to)\b|\badd .* to (the|a) .*(file|script)")),
    # 4 "reading a specific artefact to copy from it"
    ("extraction", re.compile(r'''\b(cat|head|tail|less|more|sed -n|jq|awk)\b[^\n]*[\w./-]+\.(py|sh|txt|json|md|'''
                              r'''yaml|yml|c|cpp|java|js|ts|go|rs|log|out|cfg|ini)\b|git (show|diff|log|blame)|'''
                              r'''grep -n\b'''),
     re.compile(r"\b(read|open|show|print|dump|inspect|look at|copy from|extract) (the|this|that|its|file)"
                r"|what (does|is) (the|this) (file|code|function)\b")),
    # 5 "surveying structure"
    ("exploration", re.compile(r'''\b(ls|find|tree|pwd|du|stat|file|wc|locate)\b|\becho \*|grep -r|rg\b|'''
                               r'''\bglob\b|git status|ls -a'''),
     re.compile(r"\b(explore|survey|list|overview|what (files|is|in)|structure of|layout|where (is|are)|"
                r"which (files|directory))\b|directory (contents|tree|listing)|see what.*(exists|there is)")),
    # 6 "the thought restates/narrows the task or lists hypotheses/plan steps without a file-targeting command"
    ("clarification", re.compile(r"^\s*$"),
     re.compile(r"\b(the (task|problem|issue) (asks|is|requires|wants|states)|i (should|need to|have to|will|"
                r"must|am going to)|my (plan|approach|strategy|hypothesis)|first,? i|then i |let me (think|plan|"
                r"consider|re-?read)|(two|three|several) (options|approaches|possibilities|hypotheses))\b")),
    # 7 "environment setup/installs"
    ("system", re.compile(r'''\b(pip3?|apt(-get)?|yum|conda|npm|yarn|pnpm|cargo (add|build|install)|export\b|'''
                          r'''source\b|mkdir|rm\b|mv\b|cp\b|chmod|chown|cd\b|virtualenv|service\b|systemctl|'''
                          r'''docker|wget|curl -o|unzip|tar\b|git (clone|init|config))\b'''),
     re.compile(r"\b(install|set up|setup|configure|environment|dependencies|virtualenv|conda env|build from "
                r"source|compile|clone|download)\b")),
]
STAGES2 = [r[0] for r in RULES2] + ["uncodable"]


def code_turn_second(thought: str, cmd: str) -> str:
    """The published matching discipline, applied to the second cue table (priority order, first match wins)."""
    for label, cmd_re, thought_re in RULES2:
        if (cmd and cmd_re.search(cmd)) or (thought_re.pattern != r"^\s*$" and thought_re.search(thought)):
            if cmd or label == "clarification":
                return label
    return "uncodable"


def read_turns():
    """The frozen EXP-0031 sample, one record per trajectory, holding both coders' labels on identical turns."""
    files = [f for f in sorted(glob.glob(str(M.TROVE / "**/*.parquet"), recursive=True)) if ".cache" not in f]
    if len(files) < SHARDS:
        raise SystemExit(f"ABORT: only {len(files)} AgentTrove shards - the frozen sample cannot be reproduced")
    picks = sorted(random.Random(SEED).sample(files, min(SHARDS, len(files))))
    recs, n_turns = [], 0
    for f in picks:
        pf = pq.ParquetFile(f)
        n = min(ROWS_PER_SHARD, pf.metadata.num_rows)
        got = 0
        for rg in range(pf.metadata.num_row_groups):
            if got >= n:
                break
            blk = pf.read_row_group(rg).slice(0, n - got)
            for r in blk.to_pylist():
                a_lab, b_lab = [], []        # one pair of label lists per trajectory, not per row group
                for m in (r.get("conversations") or []):
                    role = m.get("role") or m.get("from")
                    if role not in ("assistant", "gpt"):
                        continue
                    content = m.get("content") or m.get("value") or ""
                    n_turns += 1
                    t, c, _order = A.split_turn_trove(content)
                    a_lab.append(A.code_turn_trove(t, c))
                    b_lab.append(code_turn_second(t, c))
                if not a_lab:
                    continue
                recs.append({"instance_id": str(r.get("run_id") or r.get("task") or r.get("trial_name")),
                             "a": a_lab, "b": b_lab})
            got += len(blk)
    return recs, n_turns, len(picks)


def flat(recs, key):
    return [s for r in recs for s in r[key]]


def cohen(a, b, labels):
    """Cohen's kappa over two label lists; unmatched category sets are handled by the shared label alphabet."""
    ia = {l: i for i, l in enumerate(labels)}
    n = len(a)
    if not n:
        return float("nan")
    Mx = np.zeros((len(labels), len(labels)))
    for x, y in zip(a, b):
        Mx[ia[x], ia[y]] += 1
    po = np.trace(Mx) / n
    ra, rb = Mx.sum(1) / n, Mx.sum(0) / n
    pe = float((ra * rb).sum())
    return float("nan") if pe >= 1.0 else (po - pe) / (1.0 - pe)


def clustered_kappa_ci(recs, labels, draws=DRAW, seed=SEED):
    """Percentile interval for kappa, resampling whole trajectories: turns from one run are not independent.

    Implemented as a weighted sum over per-trajectory confusion vectors. Resampling and re-looping 116,581 label pairs
    two thousand times in Python would take hours, and the statistic is identical either way: a bootstrap draw of the
    confusion matrix is the counts matrix times the cluster weights.
    """
    L = {l: i for i, l in enumerate(labels)}
    n = len(labels)
    counts = np.zeros((len(recs), n * n))
    for i, r in enumerate(recs):
        for x, y in zip(r["a"], r["b"]):
            counts[i, L[x] * n + L[y]] += 1
    tot = counts.sum(0)
    if not tot.any():
        return [float("nan")] * 2, 0
    rng = np.random.default_rng(seed)
    k = len(recs)
    vals = []
    for _ in range(draws):
        w = rng.multinomial(k, np.full(k, 1.0 / k))
        vals.append(_kappa_from_counts(counts.T @ w, n))
    vals = [v for v in vals if not np.isnan(v)]
    if not vals:
        return [float("nan")] * 2, 0
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))], len(vals)


def _kappa_from_counts(flat_counts, n):
    M = np.asarray(flat_counts, dtype=float).reshape(n, n)
    t = M.sum()
    if not t:
        return float("nan")
    po = float(np.trace(M)) / t
    ra, rb = M.sum(1) / t, M.sum(0) / t
    pe = float((ra * rb).sum())
    return float("nan") if pe >= 1.0 else (po - pe) / (1.0 - pe)


def shares(labs):
    s = pd.Series(labs).value_counts(normalize=True)
    return {k: round(float(v), 4) for k, v in s.items()}


def rq1(labs, gate=0.80):
    coded = [x for x in labs if x != "uncodable"]
    coded_share = len(coded) / max(1, len(labs))
    unc = labs.count("uncodable") / max(1, len(labs))
    top = max(shares(coded).values()) if coded else 1.0
    return {"codable": round(coded_share, 4), "uncodable": round(unc, 4), "largest_stage_share": round(top, 4),
            "passes_riq1": bool(coded_share >= gate and unc <= 0.20 and top <= 0.80)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--turns", type=int, default=0, help="cap turns per coder for a smoke run (0 = the frozen sample)")
    ap.add_argument("--draws", type=int, default=DRAW)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    recs, n_turns, n_shards = read_turns()
    if not a.turns:
        # this walk must reproduce the population EXP-0092 published, or kappa would be measured on a different sample
        pub = sorted(glob.glob(str(OUT_RAW / "EXP0092_agenttrove_codex_*.json")))
        if pub:
            j = json.loads(pathlib.Path(pub[-1]).read_text(encoding="utf-8"))
            s = j.get("sample", {})
            if s.get("assistant_turns") not in (None, n_turns) or s.get("trajectories") not in (None, len(recs)):
                raise SystemExit(f"ABORT: my walk saw {n_turns} turns / {len(recs)} trajectories, EXP-0092 published "
                                 f"{s.get('assistant_turns')} / {s.get('trajectories')} - the sample is not the frozen one")
            print(f"  sample reproduces EXP-0092: {n_turns} turns, {len(recs)} trajectories, {n_shards} shards")
    if a.turns:                                 # smoke runs cap by whole trajectory, so labels and clusters stay aligned
        keep, nt = [], 0
        for r in recs:
            if nt and nt + len(r["a"]) > a.turns:
                break
            nt += len(r["a"])
            keep.append(r)
        recs = keep
    la, lb = flat(recs, "a"), flat(recs, "b")
    labels = sorted(set(la) | set(lb))
    k = cohen(la, lb, labels)
    ci, n_boot = clustered_kappa_ci(recs, labels, draws=a.draws)
    agree = float(np.mean([x == y for x, y in zip(la, lb)])) if la else float("nan")
    conf = {}
    for x, y in zip(la, lb):
        if x != y:
            conf[f"{x} -> {y}"] = conf.get(f"{x} -> {y}", 0) + 1
    top_conf = dict(sorted(conf.items(), key=lambda kv: -kv[1])[:8])
    marg_a, marg_b = shares(la), shares(lb)
    moved = {s: round(abs(marg_b.get(s, 0.0) - marg_a.get(s, 0.0)), 4) for s in sorted(labels)}
    verdict = "RUBRIC_INVARIANT_ENOUGH" if (not np.isnan(k) and k >= KAPPA_BAR) else "NOT_RUBRIC_INVARIANT"
    res = {"exp_id": "EXP-0112", "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "wallclock_sec": round(time.time() - t0, 1),
           "sample": {"seed": SEED, "shards": n_shards, "rows_per_shard": ROWS_PER_SHARD,
                      "assistant_turns_scanned": n_turns, "trajectories": len(recs),
                      "turns_compared": len(la)},
           "kappa": round(float(k), 4), "kappa_clustered_ci95": [round(x, 4) for x in ci],
           "bootstrap_draws_with_a_value": n_boot, "percent_agreement": round(agree, 4),
           "kappa_bar": KAPPA_BAR, "verdict": verdict,
           "confusion_top": top_conf, "marginals_by_table": {"frozen_instrument": marg_a,
                                                             "second_instrument": marg_b},
           "share_moves_pp": {s: round(v * 100, 2) for s, v in sorted(moved.items(), key=lambda kv: -kv[1])},
           "rq1_under_each_table": {"frozen": rq1(la), "second": rq1(lb)},
           "held_constant": "addendum A extraction (imported from isp_stage_codex_agenttrove) and the frozen "
                            "priority/first-match/text-only discipline; only the cue table differs",
           "claim_not_made": "this is rubric invariance, not human inter-coder reliability (EXP-0087's distinction)",
           "rule": f"kappa >= {KAPPA_BAR} or the AgentTrove distribution stays labelled instrument-dependent; "
                   "no threshold, cue or sample re-cut after seeing the number"}
    OUT_RAW.mkdir(exist_ok=True)
    o = OUT_RAW / f"EXP0112_agenttrove_rubric_invariance_{time.strftime('%Y%m%dT%H%M%S')}.json"
    o.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k2: res[k2] for k2 in ("sample", "kappa", "kappa_clustered_ci95", "percent_agreement",
                                             "verdict", "rq1_under_each_table")}, indent=1, ensure_ascii=False))
    print("share moves (pp):", json.dumps(res["share_moves_pp"], ensure_ascii=False))
    print("top confusion:", json.dumps(top_conf, ensure_ascii=False))
    print("wrote", o.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
