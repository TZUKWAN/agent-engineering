"""EXP-0088 recorder: P001's dependent variable is join-rule invariant, and D1's rejection pathology is absent.

What was measured (three faithful resolvers over 7,852 raw rows from 30 seeded shards, two arms of bookkeeping):
pooled Cohen kappa R1-vs-R2 = 0.9956 and R1-vs-R3 = 0.9927; `fail@3` changes on 0.04% / 0.06% of rows
(prompt_id-clustered intervals [0, 0.0009] and [0.0001, 0.0013]); the three rules resolve 100% / 100% / 99.66% of
rows, a selection gap of 0.34%. Against the bars fixed before computing (kappa >= 0.80, DV change <= 5%, selection
gap <= 5%) the DV is join-rule invariant.

What it does NOT do: close the human inter-coder item. That gap is about the corpus's own human-written quality
scores, whose labels are single-category, so kappa is inestimable there - a limit that stays declared. This
experiment retires only the worry that P001's outcome depends on which resolver was used, and it independently
confirms that D1's 26.7% over-rejection belonged to the retired name-prefix heuristic, not to the published rule.

    python record_exp0088_p001.py
"""
from __future__ import annotations

import csv, glob, io, json, pathlib, re, sys, time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
P = ROOT / "papers" / "P001_routing_failure_qpp"
NOW = time.strftime("%Y-%m-%dT%H:%M:%S")


def line(r):
    b = io.StringIO(); csv.writer(b, lineterminator="\r\n").writerows([r]); return b.getvalue()


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    art = sorted((ROOT / "results_raw").glob("EXP0088_join_rule_invariance_*.json"))[-1]
    d = json.loads(art.read_text(encoding="utf-8"))
    p, rs = d["pooled"], d["pooled"]["resolvable_share"]

    doc = f"""# The dependent variable does not depend on the join rule (EXP-0088)

Artefact `{art.name}`; seed {d['seed']}; {d['wallclock_sec']}s. Code
`02_shared_code/statistics/join_rule_invariance_p001.py`.

## Question, and the bars fixed before any number

P001's gold labels are a deterministic join of a gold tool name onto the row's own catalogue, and the programme has
already been hurt by a join once (D1: a name-prefix heuristic that over-rejected 26.7% of OSS rows). So before
treating `fail@3` as a fact about retrieval, the same rows were resolved three ways:

| resolver | decision procedure |
|---|---|
| R1 | the published `resolve_gold_v2`: server-consistent, unique-suffix, rejects ambiguity |
| R2 | the retired loose behaviour reconstructed deliberately: exact name else the **first** prefix/suffix match, never rejecting for ambiguity |
| R3 | unique-suffix join with the server check removed |

Pre-declared acceptance: **invariant** iff kappa >= 0.80 against R1 for each alternative, the share of rows whose
`fail@3` changes is <= 5%, and the resolvable-share gap is <= 5%. Rows were **not** pre-filtered on R1 - filtering
them out would have measured label agreement while hiding the selection effect that D1 was about.

## Result

| quantity | R1 vs R2 | R1 vs R3 |
|---|---|---|
| Cohen kappa on `fail@3` | **{p['kappa_R1_R2']}** | **{p['kappa_R1_R3']}** |
| raw agreement | {p['agreement_R1_R2']} | {p['agreement_R1_R3']} |
| share of rows whose label changes | {p['dv_change_share_R1_R2']} (CI {p['dv_change_ci_R1_R2'][0]}-{p['dv_change_ci_R1_R2'][1]}) | {p['dv_change_share_R1_R3']} (CI {p['dv_change_ci_R1_R3'][0]}-{p['dv_change_ci_R1_R3'][1]}) |
| exact gold-set agreement | {p['exact_set_rate_R1_R2']} | {p['exact_set_rate_R1_R3']} |
| mean Jaccard of gold sets | {p['mean_jaccard_R1_R2']} | {p['mean_jaccard_R1_R3']} |
| rows resolvable | {rs['R1']} / {rs['R2']} | {rs['R1']} / {rs['R3']} |

Fail rates themselves move from {p['fail_rate_R1']} (R1) to {p['fail_rate_R2']} (R2) and {p['fail_rate_R3']} (R3); the
selection gap across all three rules is {d['selection_gap']}. **Verdict: {d['verdict']}**

## A second finding, about D1

The published resolver rejected **nothing** in this sample ({rs['R1']:.0%} resolvable across
{sum(v['rows'] for v in d['per_config'].values()):,} raw rows), so D1's 26.7% over-rejection is confirmed as a
property of the retired prefix heuristic rather than of the rule the paper uses. That is the first time the D1
correction has been checked forward instead of only backward.

## What this does not buy

It does not produce human inter-coder reliability for the corpus's own human-written quality scores, and that stays a
declared limit: those labels are single-category, so kappa is inestimable there, and the programme has no human
coding step to substitute. What is retired is specifically the worry that P001's outcome variable is an artefact of
the resolver chosen to build it.
"""
    (P / "join_rule_invariance_exp0088.md").write_text(doc, encoding="utf-8", newline="")

    cp = P / "claims_evidence_matrix.csv"
    rows = [r for r in csv.reader(io.StringIO(cp.read_text(encoding="utf-8"))) if r]
    hdr, body = rows[0], rows[1:]
    if "C26" not in {r[0] for r in body}:
        c = dict.fromkeys(hdr, "")
        c.update({"claim_id": "C26",
                  "claim": "因变量 fail@3 对金标注 join 规则不变：三种忠实实现（严格/宽松唯一后缀）之间 kappa 0.9956 与 "
                           "0.9927，标签翻转率 0.04%/0.06%，可解析率差 0.34%",
                  "claim_type": "测量稳健性（无人工条件下的信度替代检验）",
                  "experiment_id": "EXP-0088", "direction": "supports",
                  "digits_reported": f"kappa_R1_R2={p['kappa_R1_R2']} kappa_R1_R3={p['kappa_R1_R3']} "
                                     f"dv_change={p['dv_change_share_R1_R2']}/{p['dv_change_share_R1_R3']} "
                                     f"resolvable={rs['R1']}/{rs['R2']}/{rs['R3']} selection_gap={d['selection_gap']} "
                                     f"rows={sum(v['rows'] for v in d['per_config'].values()):,}",
                  "statistical_test": "Cohen kappa；标签翻转率按 prompt_id 聚类自助 500 次给出区间；判据 "
                                      "kappa>=0.80 且变化率<=5% 在选择规则前写定",
                  "raw_result_file": f"results_raw/{art.name}",
                  "table": "results_processed/EXP0088_join_rows_sample.csv",
                  "figure": "papers/P001_routing_failure_qpp/join_rule_invariance_exp0088.md",
                  "where_in_paper": "Limitations L23; final_audit G18-B/G18-C; join_rule_invariance_exp0088.md",
                  "status": "supported (and explicitly not a human-reliability claim)"})
        row = [c[k] for k in hdr]
        if len(row) != len(hdr):
            raise SystemExit(f"ABORT: C26 has {len(row)} fields against a {len(hdr)}-column header")
        body.append(row)
        cp.write_text("".join(line(x) for x in [hdr] + body), encoding="utf-8", newline="")
        print("  claims matrix: C26 added")

    lim = (P / "limitations.md").read_text(encoding="utf-8")
    head = "## L23 金标注 join 规则不变性"
    # An append-only recorder can never improve its own wording: this section first shipped "κ is still owed and
    # cannot be automated", which mis-states a measured applicability boundary as an outstanding human step. The old
    # section is therefore cut and the current text re-inserted on every run, so the generator stays the source.
    sec = f"""{head}已测（EXP-0088，`join_rule_invariance_exp0088.md`）

P001 的 κ 欠项原本指语料自带的人工质量分标签。EXP-0033 实测该标签只有一个类别，所以 κ 在这里不是一个等人工补做的
步骤，而是一条测得的适用性边界：没有负类，任何一致性统计量都无定义（确定性第二编码者与人工标注一致 97.5%，且从不比
人工更宽松）。能被自动补的是另一个真正威胁结论的问题：因变量是否取决于金标注 join 规则。三种实现（published 严格 /
故意宽松 / 去服务器校验唯一后缀）在 {sum(v['rows'] for v in d['per_config'].values()):,} 条原始行上：
kappa {p['kappa_R1_R2']} 与 {p['kappa_R1_R3']}，fail@3 翻转率 {p['dv_change_share_R1_R2']} 与
{p['dv_change_share_R1_R3']}（prompt_id 聚类区间 {p['dv_change_ci_R1_R2']} / {p['dv_change_ci_R1_R3']}），
可解析率差 {d['selection_gap']}；判据在算任何数之前写定。
顺带向前验证了 D1：现行 resolver 在本样本零拒绝，26.7% 过度拒绝属于已废弃的前缀启发式。

边界：这不构成人工编码者信度，也不改变人工标签单类别导致 κ 不可估这一事实；它只排除"因变量是 join 规则的产物"。
"""
    at = lim.find(head)
    sec = sec.strip() + "\n"
    if at != -1:
        nxt = lim.find("\n## ", at + len(head))
        # replaced in place, so the section keeps its position in the file instead of drifting to the end each rebuild
        lim = lim[:at] + sec + (lim[nxt + 1:] if nxt != -1 else "")
    else:
        lim = lim.rstrip() + "\n\n" + sec
    (P / "limitations.md").write_text(lim, encoding="utf-8", newline="")
    print("  limitations:", "L23 re-inserted in place" if at != -1 else "L23 appended")

    fa = (P / "final_audit.md").read_text(encoding="utf-8")
    if "EXP-0088" not in fa:
        fa = re.sub(r"(\| strong neural / dense-encoder baseline \|[^\n]*\n)",
                    r"\1| label-provenance robustness of the DV | **MEASURED (EXP-0088)** | three faithful resolvers "
                    f"agree at kappa {p['kappa_R1_R2']}/{p['kappa_R1_R3']}, fail@3 changes on "
                    f"{p['dv_change_share_R1_R2']}/{p['dv_change_share_R1_R3']} of rows, selection gap "
                    f"{d['selection_gap']}; human inter-coder reliability on the corpus's own single-category quality "
                    "labels remains inestimable and stays declared as such |\n", fa, count=1)
        (P / "final_audit.md").write_text(fa, encoding="utf-8", newline="")
        print("  final_audit: EXP-0088 row added")

    rp = ROOT / "00_program_registry" / "experiment_registry.csv"
    rrows = [r for r in csv.reader(io.StringIO(rp.read_text(encoding="utf-8"))) if r]
    rhdr, rbody = rrows[0], rrows[1:]
    if "EXP-0088" not in {r[0] for r in rbody}:
        rec = dict.fromkeys(rhdr, "")
        rec.update({"exp_id": "EXP-0088", "paper_id": "P001", "topic_id": "T037",
                    "stage": "dv_join_rule_invariance",
                    "script": "02_shared_code/statistics/join_rule_invariance_p001.py",
                    "config": "three resolvers on identical raw rows (published resolve_gold_v2 / deliberately loose "
                              "first-match / unique-suffix without server check); 30 seeded shards per published "
                              f"config, up to 3000 rows each, seed {d['seed']}; BM25 k1=1.4 b=0.4, fail@3; rows NOT "
                              "pre-filtered on the published rule so the selection effect stays visible; bars "
                              "kappa>=0.80 and change<=5% fixed before computing",
                    "seed": str(d["seed"]), "started_at": d["started_at"], "finished_at": NOW,
                    "status": f"INVARIANT: kappa {p['kappa_R1_R2']}/{p['kappa_R1_R3']}, DV change "
                              f"{p['dv_change_share_R1_R2']}/{p['dv_change_share_R1_R3']}, selection gap "
                              f"{d['selection_gap']}",
                    "outputs": f"results_raw/{art.name}; results_processed/EXP0088_join_rows_sample.csv; "
                               "papers/P001_routing_failure_qpp/join_rule_invariance_exp0088.md",
                    "notes": "retires the worry that the DV is a product of the resolver, and confirms forward that "
                             "D1's 26.7% over-rejection belonged to the retired heuristic; does not and is not claimed "
                             "as human inter-coder reliability",
                    "enters_paper": "yes - claim C26, limitations L23, final_audit G18-B row"})
        rbody.append([rec[k] for k in rhdr])
        rp.write_text("".join(line(x) for x in [rhdr] + rbody), encoding="utf-8", newline="")
        print("  registry: EXP-0088 added")
    chk = [r for r in csv.reader(io.StringIO(rp.read_text(encoding="utf-8"))) if r]
    print(f"  registry rows={len(chk)-1} ragged={sum(1 for r in chk[1:] if len(r)!=len(chk[0]))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
