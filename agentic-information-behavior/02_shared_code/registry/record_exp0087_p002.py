"""EXP-0087 recorder: the codex is rubric-sensitive, and that goes into P002's record as a negative result.

What the measurement found (two independently written realisations of the protocol's construct definitions, 900 turns
drawn one-per-trajectory across 60 shards, re-randomised order, seed 42):

  * percent agreement 0.647, Cohen kappa **0.502** with an instance-clustered interval, Krippendorff alpha 0.499;
  * on the protocol's own 60-turn subsample, kappa 0.561;
  * `protocol_freeze.md` section 3 states that below kappa 0.75 "the codex is documented as unreliable and the paper is
    not submitted" - so the bar is applied as written and P002's submission gate stays unmet.

This replaces the hand-coded retest as a REGISTERED amendment, not a silent substitution: it measures rubric invariance
(how much the stage distribution depends on the cue table), which is NOT human-intercoder reliability and is not
claimed as such anywhere. The disagreement structure is reported because it is the informative part - the confusion is
concentrated on one construct boundary, not spread over the whole taxonomy.

    python record_exp0087_p002.py
"""
from __future__ import annotations

import csv, io, json, pathlib, re, sys, time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
P = ROOT / "papers" / "P002_isp_stage_measurement"
NOW = time.strftime("%Y-%m-%dT%H:%M:%S")


def line(r):
    b = io.StringIO(); csv.writer(b, lineterminator="\r\n").writerows([r]); return b.getvalue()


def sub1(text, pat, repl, tag, marker=None):
    if marker and marker in text:
        print(f"  [{tag}] already applied - skipped")
        return text
    n = len(re.findall(pat, text, re.S))
    if n != 1:
        raise SystemExit(f"ABORT [{tag}]: matched {n} times, expected 1: {pat[:70]!r}")
    print(f"  [{tag}] applied")
    return re.sub(pat, repl, text, count=1, flags=re.S)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    art = sorted((ROOT / "results_raw").glob("EXP0087_codex_invariance_*.json"))[-1]
    d = json.loads(art.read_text(encoding="utf-8"))
    pa, pr, pn = d["panel_agreement"], d["protocol_60"], d["panel"]
    k, ci, alpha = pa["cohens_kappa"], pa["kappa_instance_bootstrap_ci95"], pa["krippendorff_alpha_nominal"]
    if art.name.endswith("_20260921T010818.json"):
        raise SystemExit("ABORT: this is the superseded 5-instance panel artefact")
    assert pr["meets_frozen_bar_0_75"] is False, "the bar is now met - the record below would be wrong"

    doc = f"""# RQ4 without a human: two independently written codices disagree more than the bar allows (EXP-0087)

Artefact `{art.name}`; seed {d['seed']}; {d['wallclock_sec']}s. Code
`02_shared_code/behavior_tagger/isp_stage_codex_independent.py`.

## Why this exists

`protocol_freeze.md` section 3 makes RQ4 an intra-coder retest on 60 hand-coded turns in re-randomised order, with
kappa >= 0.75 as the condition for submitting, and states that **no human-intercoder claim is made**. The programme
runs with no human coding step, and re-running the frozen codex against itself would give kappa = 1 by construction -
a tautology, not evidence. So the test was re-instantiated as **rubric invariance**: a second codex (codex B) was
written from the construct definitions in section 2, with a different decision procedure (score all labels, argmax,
ties to `uncodable`, and the observation payload is admitted) and a different cue vocabulary, and agreement between
the two is reported against the protocol's own bar.

What this is and is not: it measures how much the stage assignment depends on the particular cue table rather than on
the construct. It is not human reliability, and no sentence here or in the paper claims that.

## Panel

{pn['turns']} turns from {pn['instances']} distinct instances (one turn per trajectory, drawn across 60 pilot shards,
re-randomised presentation order), {pn['with_command']:.1%} of them carrying a command. The first attempt produced a
900-turn panel from 5 instances and was superseded rather than reported
(`results_raw/superseded/EXP0087_codex_invariance_20260921T010818.json`); the script now aborts when the panel's
instance count falls below max(30, n/2).

## Agreement

| quantity | value |
|---|---|
| percent agreement | {pa['percent_agreement']} |
| agreement expected by chance | {pa['expected_by_chance']} |
| Cohen kappa | **{k}** (instance-clustered 95% {ci[0]}-{ci[1]}) |
| Krippendorff alpha (nominal) | {alpha} |
| protocol's 60-turn subsample | kappa {pr['cohens_kappa']} |
| frozen bar | 0.75 |
| verdict | **{d['verdict']}** |

Un-coded share is low on both sides (A {d['uncodable_share']['A']:.1%}, B {d['uncodable_share']['B']:.1%}), so the
disagreement is not one codex refusing to decide. It is concentrated on one boundary:

{chr(10).join('- `' + t + '`' for t in d['top_disagreements'][:6])}

## What this does to the paper

`extraction` vs `exploration` is the dominant confusion ({d['top_disagreements'][0]} and its mirror), i.e. whether a
command that reads files is surveying structure or copying from an artefact - a boundary the protocol defines by
command *shape* (`grep -r`, wildcards) rather than by intent. Consequences, applied as the protocol requires rather
than negotiated:

1. the stage **distribution** claims are labelled rubric-sensitive: two faithful realisations of the definitions
   disagree at kappa {k}, well under 0.75;
2. the ladder/gain claims are less exposed because they are computed on the same codex for every model (a shared
   mislabelling shifts absolute likelihoods, not the comparison), but that argument is now stated as a limitation
   rather than assumed;
3. **P002's submission gate stays unmet**: the protocol says a codex below 0.75 is documented as unreliable and the
   paper is not submitted. No threshold was adjusted, and the automated substitute is not allowed to inherit a weaker
   bar than the human test it replaced.

## What would change this

A third realisation restricted to the extraction/exploration boundary (e.g. deciding by presence of a wildcard or
recursive flag alone, with no lexical cues) would localise whether the disagreement is definitional underspecification
or cue-table contingency. That is a new instrument, so it would be frozen before its agreement is ever looked at.
"""
    (P / "codex_invariance_exp0087.md").write_text(doc, encoding="utf-8", newline="")

    # Determinism evidence: if the experiment has been re-executed, say so with the hash rather than leaving a second
    # artefact in results_raw/ unexplained.
    extra = sorted((ROOT / "results_raw").glob("EXP0087_codex_invariance_*.json"))
    if len(extra) > 1:
        import hashlib

        def sig(p):
            j = json.loads(p.read_text(encoding="utf-8"))
            keep = {k: j[k] for k in ("panel_agreement", "protocol_60", "panel", "uncodable_share", "verdict",
                                       "top_disagreements", "seed")}
            return hashlib.sha256(json.dumps(keep, sort_keys=True).encode()).hexdigest()[:16]
        hashes = [sig(p) for p in extra]
        same = len(set(hashes)) == 1
        (P / "codex_invariance_exp0087.md").write_text(
            doc + f"""
## Re-executions

{len(extra)} runs of this script are in `results_raw/` ({', '.join(p.name for p in extra)}). The measured
quantities are identical across them (sha256 of the agreement, panel, protocol-60 and verdict block:
{', '.join(sorted(set(hashes))) if same else 'DIFFER: ' + ', '.join(hashes)}) - the panel is drawn from a fixed seed
over a fixed shard list, so this is a determinism check, not a replication.
""" if same else doc, encoding="utf-8", newline="")
        print(f"  determinism: {len(extra)} runs, identical measurements ({hashes[0]})")

    # ---- gate row B (RQ4) and the audit's RQ4 line
    fa = (P / "final_audit.md").read_text(encoding="utf-8")
    fa = sub1(fa, r"\| RQ4 agreement \(frozen\) \|[^\n]*\n",
              f"| RQ4 agreement (frozen) | **EXECUTED as automated rubric invariance - BELOW BAR** | two "
              f"independently written codices agree at percent {pa['percent_agreement']} / kappa **{k}** "
              f"(instance-clustered {ci[0]}-{ci[1]}), alpha {alpha}; protocol's 60-turn subsample kappa "
              f"{pr['cohens_kappa']}; the frozen bar is 0.75 and the protocol states the paper is not submitted below "
              f"it, so the gate stays open on a measured result rather than an unexecuted step. "
              f"`codex_invariance_exp0087.md`, EXP-0087 |\n",
              "RQ4 gate row", marker="BELOW BAR")
    (P / "final_audit.md").write_text(fa, encoding="utf-8", newline="")

    # ---- claims matrix: K3-style reliability claim gets an explicit status; add K7 for the invariance result
    cp = P / "claims_evidence_matrix.csv"
    rows = [r for r in csv.reader(io.StringIO(cp.read_text(encoding="utf-8"))) if r]
    hdr, body = rows[0], rows[1:]
    if "K7" not in {r[0] for r in body}:
        c = dict.fromkeys(hdr, "")
        c.update({"claim_id": "K7",
                  "claim": "阶段 codex 对提示词表不具不变性：按协议 §2 定义独立实现的第二 codex 与冻结 codex 的一致性为 "
                           f"kappa {k}（实例聚类 CI {ci[0]}-{ci[1]}）、alpha {alpha}，低于协议事先冻结的 0.75 门槛",
                  "claim_type": "测量工具的稳健性（RQ4；无人工编码的替代检验）",
                  "experiment_id": "EXP-0087", "direction": "against (rubric-sensitive)",
                  "digits_reported": f"turns={pn['turns']} instances={pn['instances']} agreement={pa['percent_agreement']} "
                                     f"kappa={k} CI={ci} alpha={alpha} n60_kappa={pr['cohens_kappa']} bar=0.75",
                  "statistical_test": f"Cohen kappa 与标称 Krippendorff alpha；区间按 instance 自助 500 次；"
                                      "判据 0.75 在协议 §3 冻结，未因结果调整",
                  "raw_result_file": f"results_raw/{art.name}",
                  "table": "results_processed/EXP0087_confusion_panel.csv",
                  "figure": "papers/P002_isp_stage_measurement/codex_invariance_exp0087.md",
                  "where_in_paper": "RQ4; limitations; final_audit gate row",
                  "status": "supported as a negative: the instrument fails its own pre-registered invariance bar"})
        row = [c[x] for x in hdr]
        assert len(row) == len(hdr), (len(row), len(hdr))
        body.append(row)
        cp.write_text("".join(line(x) for x in [hdr] + body), encoding="utf-8", newline="")
        print("  claims matrix: K7 added")

    # ---- limitations
    lim = (P / "limitations.md").read_text(encoding="utf-8")
    head_lim = "## Automated rubric invariance instead of a human retest"
    if head_lim not in lim:
        lim = lim.rstrip() + f"""

## Automated rubric invariance instead of a human retest - and the codex fails it (EXP-0087, K7)

The protocol's RQ4 asked for 60 hand-coded turns re-coded in re-randomised order with kappa >= 0.75. There is no human
coding step in this programme, and re-applying the frozen codex to itself would give kappa = 1 by construction. A
second codex was therefore written from the section 2 definitions with a different decision procedure and cue
vocabulary. Agreement: percent {pa['percent_agreement']}, **kappa {k}** (instance-clustered {ci[0]}-{ci[1]}),
alpha {alpha}, {pr['cohens_kappa']} on the protocol's 60-turn subsample - below the frozen bar.

What follows from that, stated as consequences rather than as hedging:

1. the stage *distribution* numbers are rubric-sensitive, and the dominant confusion is the extraction/exploration
   boundary, which the protocol defines by command shape rather than intent;
2. the ladder comparisons are less exposed (every model is scored by the same codex, so shared mislabelling moves
   absolute likelihoods rather than the contrasts), but that is now an argument the reader can check, not an
   assumption;
3. the submission gate stays unmet: the protocol says a codex below 0.75 is documented as unreliable and the paper is
   not submitted. The threshold was not moved to fit an automated substitute, and the substitute is not allowed a
   weaker bar than the test it replaces;
4. this measurement is *not* human-intercoder reliability and is nowhere offered as such.
"""
        (P / "limitations.md").write_text(lim, encoding="utf-8", newline="")
        print("  limitations: invariance section appended")

    # ---- reviewer attack
    rv = (P / "reviewer_attack.md").read_text(encoding="utf-8")
    if "EXP-0087" not in rv:
        # this table numbers its rows with bare integers, so take the next integer (the old `^\| A(\d+) \|` probe
        # matched nothing in it and emitted an "A1" row into a 1..11 table)
        existing = [int(x) for x in re.findall(r"^\| (\d+) \|", rv, re.M)]
        nxt = max(existing or [0]) + 1
        rv = rv.rstrip() + f"""
| {nxt} | "Your whole instrument is one person's regex table; a different faithful implementation would give a different distribution." | **Tested, and the paper loses the test**: EXP-0087's second codex, written independently from the frozen definitions, agrees at kappa {k} (alpha {alpha}) - below the protocol's 0.75 bar - and the confusion concentrates on extraction vs exploration | K7, `codex_invariance_exp0087.md`, limitations 1 |
"""
        (P / "reviewer_attack.md").write_text(rv, encoding="utf-8", newline="")
        print("  reviewer attack: row appended")

    # ---- deviation: protocol amendment, content-keyed. The key has to be a string the row itself writes - the
    # previous English phrase never appeared in the Chinese row, so a rebuild appended a second identical deviation.
    dv = (P / "deviations.md").read_text(encoding="utf-8")
    if "自动 rubric 不变性检验" not in dv:
        used = set()
        for f in (ROOT / "papers").glob("*/deviations.md"):
            used |= {int(x) for x in re.findall(r"^\| D(\d+) \|", f.read_text(encoding="utf-8"), re.M)}
        did = max(used | {0}) + 1
        dv = dv.rstrip() + "\n" + (
            f"| D{did} | {NOW} | RQ4 的人工重测由**自动 rubric 不变性检验**取代（EXP-0087；协议 §3 的替代登记，非静默替换） | "
            f"程序改为全自动，无人工编码可用；把冻结 codex 对自己重跑必然 kappa=1，属同义反复，故按 §2 定义独立实现第二 "
            f"codex（argmax 判决、允许使用 observation、词表不同）。结果 kappa {k}（实例聚类 {ci[0]}-{ci[1]}）、alpha {alpha}、"
            f"60 轮子样本 {pr['cohens_kappa']}，低于冻结门槛 0.75 | 否（未改动 RQ1-RQ3 任何主数字；门槛与判据未调） | "
            "后果：分布性结论标注为 rubric-sensitive（K7、limitations），投稿门槛保持未达成；同轮另有一次 5 实例退化面板运行"
            "被登记为 superseded 而非引用，脚本新增实例数下限预检 |\n")
        (P / "deviations.md").write_text(dv, encoding="utf-8", newline="")
        print(f"  deviations: appended D{did}")

    # ---- registry
    rp = ROOT / "00_program_registry" / "experiment_registry.csv"
    rrows = [r for r in csv.reader(io.StringIO(rp.read_text(encoding="utf-8"))) if r]
    rhdr, rbody = rrows[0], rrows[1:]
    if "EXP-0087" not in {r[0] for r in rbody}:
        rec = dict.fromkeys(rhdr, "")
        rec.update({"exp_id": "EXP-0087", "paper_id": "P002", "topic_id": "T008",
                    "stage": "rq4_automated_rubric_invariance",
                    "script": "02_shared_code/behavior_tagger/isp_stage_codex_independent.py",
                    "config": f"codex A = frozen isp_stage_coder.RULES imported unmodified; codex B written from "
                              f"protocol_freeze.md section 2 definitions with argmax scoring, tie-to-uncodable and the "
                              f"observation payload admitted; {pn['turns']} turns / {pn['instances']} instances, one "
                              f"turn per trajectory across 60 shards, re-randomised order, seed {d['seed']}; bar 0.75 "
                              "frozen in protocol section 3",
                    "seed": str(d["seed"]), "started_at": d["started_at"], "finished_at": NOW,
                    "status": f"BELOW BAR: kappa {k} CI {ci[0]}-{ci[1]}, alpha {alpha}",
                    "outputs": f"results_raw/{art.name}; results_processed/EXP0087_confusion_panel.csv; "
                               "papers/P002_isp_stage_measurement/codex_invariance_exp0087.md; "
                               "results_raw/superseded/EXP0087_codex_invariance_20260921T010818.json",
                    "notes": "replaces the human retest as a registered amendment and FAILS the frozen invariance bar; "
                             "stage-distribution claims are labelled rubric-sensitive and P002's submission gate stays "
                             "unmet; not human-intercoder reliability and not claimed as such",
                    "enters_paper": "yes - claim K7, limitations, final_audit RQ4 row, reviewer attack, deviations"})
        rbody.append([rec[x] for x in rhdr])
        rp.write_text("".join(line(x) for x in [rhdr] + rbody), encoding="utf-8", newline="")
        print("  registry: EXP-0087 added")
    chk = [r for r in csv.reader(io.StringIO(rp.read_text(encoding="utf-8"))) if r]
    print(f"  registry rows={len(chk)-1} ragged={sum(1 for r in chk[1:] if len(r)!=len(chk[0]))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
