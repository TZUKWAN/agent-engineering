"""EXP-0084 recorder: the frozen predictor on ToolRet's EVAL split, where it does NOT transfer.

Read the artefact before the prose: arm A lands at AUROC 0.4671 on production-scale union catalogues, below chance and
below the length-only baseline, while EXP-0082's 0.6536 came from the training partition's ten mined negatives. The
construct, not the model, is what changed - so the record says the transfer claim is candidate-set-dependent and the
earlier number may not stand as the external-validation headline.

Arm B is recorded as **undiagnosed, not as a result**: an AUROC of exactly 0.5000 with zero-width row and
subset-clustered intervals is the signature of a constant score vector, which is a pipeline artifact until proven
otherwise.

    python record_exp0084_p001.py
"""
from __future__ import annotations

import csv, glob, io, json, pathlib, re, sys, time

HERE = pathlib.Path(__file__).resolve().parent          # 02_shared_code/registry
ROOT = HERE.parents[1]
P = ROOT / "papers" / "P001_routing_failure_qpp"
NOW = time.strftime("%Y-%m-%dT%H:%M:%S")


def line(r):
    b = io.StringIO()
    csv.writer(b, lineterminator="\r\n").writerows([r])
    return b.getvalue()


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
    art = sorted((ROOT / "results_raw").glob("EXP0083_toolret_eval_transfer_*.json"))[-1]
    d = json.loads(art.read_text(encoding="utf-8"))
    aq, ai = d["arms"][0], d["arms"][1]
    ci_r, ci_s = aq["row_bootstrap_ci95"], aq["subset_clustered_ci95"]
    degenerate_b = (ai["frozen_auroc"] == 0.5 and ai["row_bootstrap_ci95"] == [0.5, 0.5]
                    and ai["subset_clustered_ci95"] == [0.5, 0.5])
    per = pathlib.Path("results_processed/EXP0083_toolret_eval_per_subset.csv")
    rows = list(csv.DictReader(io.StringIO(per.read_text(encoding="utf-8")))) if per.is_file() else []
    spread = sorted({round(float(r["fail3_query"]), 3) for r in rows})

    doc = f"""# The EVAL split says it does not transfer (EXP-0084)

Artefact `{art.name}`; seed {d['seed']}; {d['wallclock_sec']}s. Fitted on the published Toucan dev rows only
({d['source']['n_dev_rows']:,} rows, three configs) and scored on external rows; nothing - no feature, threshold or C
value - was chosen from external data. Bands frozen in EXP-0021: >= {d['bands']['transfers']} transfers,
{d['bands']['partial']}-{d['bands']['transfers']} partial, < {d['bands']['partial']} **does not transfer**.

## What differs from EXP-0082, and that is the whole point

EXP-0082 scored the benchmark's **training partition**, where each query faces its targets plus ten negatives mined
by NV-embed-v1 - a ~17-tool pool with almost no size variance. This step scores the **evaluation release**: every query
faces the union of the three released tool partitions, **{d['union_catalogue_docs']:,} candidate tools per query**,
{d['construct']['subsets']} task subsets, {aq['n_rows']} rows sampled stratified
{d['per_subset_cap']}/subset, zero rejections.

## Result - arm A, the pre-registered primary

| quantity | value |
|---|---|
| AUROC of the frozen predictor | **{aq['frozen_auroc']}** |
| row bootstrap 95% | {ci_r[0]}-{ci_r[1]} |
| subset-clustered 95% (the honest one) | {ci_s[0]}-{ci_s[1]} |
| length-only baseline, same rows | {aq['length_only_baseline']} |
| post-retrieval BM25 margin baseline | {aq['post_retrieval_margin_baseline']} |
| fail@3 prevalence here | {aq['fail_at_3_prevalence']} ({aq['positives']}/{aq['n_rows']}) |
| source dev prevalence | {d['source']['fail_at_3_prevalence']} |
| BM25 hit@3 here | {aq['bm25_hit_at_3']} |
| within-corpus OOF on these rows | {aq['within_corpus_oof_aucroc'][0]} |
| frozen-band verdict | **{aq['verdict_by_frozen_bands']}** |

**Read it plainly: the point estimate is below chance, the interval excludes 0.5 on the low side, and it is worse than
the length-only baseline on identical rows ({aq['length_only_baseline']}).** On production-scale catalogues the frozen
query-and-catalogue features carry no usable signal about whether BM25 will miss the gold tool - and the per-subset
failure rates vary widely ({spread[:6]}... over {len(rows)} subset/category cells), so this is not one odd subset
dragging a mean.

## What this does to the paper's external-validation story

EXP-0082's 0.6536 cleared the frozen bar on a mined-negative pool; EXP-0084's {aq['frozen_auroc']} fails it on a
whole-pool one. The honest synthesis is **construct dependence, not a transfer**: pre-retrieval predictability of the
kind P001 measures exists where the candidate set is the small, curated pool the model was trained to see, and is
absent when the pool is a 44k-tool union assembled by other groups. That is a *narrowing* of P001's claim, and it must
be reported as the headline external result unless a re-analysis shows an error in this run.

Three things this does not do: it does not reproduce the ToolRet leaderboard (nDCG@10 over per-subset pools vs
pre-retrieval fail@3 over the union here - different measure, harder pool); it does not license any statement about
instruction-following, since arm B is unusable (below); and it does not retroactively falsify the in-domain dev/test
results, which are a different corpus and pool.

## Arm B is recorded as undiagnosed, not as a finding

Arm B returned AUROC exactly {ai['frozen_auroc']} with **zero-width** row and subset-clustered intervals
({ai['row_bootstrap_ci95']} / {ai['subset_clustered_ci95']}). A 500-resample interval that never moves is the
signature of a constant score vector - i.e. every row received the same predicted probability - which is a pipeline
artifact, not a null. Candidate causes to test, in order: NaN/inf propagation through the scaler at these feature
magnitudes; a frozen feature that saturates when the catalogue is 44k documents; and the per-query recomputation of
corpus statistics inside `collection_qpp_features` on a pool this size. Until one of those is demonstrated, **no
sentence in the paper may quote arm B**.
"""
    (P / "external_toolret_eval_transfer.md").write_text(doc, encoding="utf-8", newline="")

    # ---- registry
    rp = ROOT / "00_program_registry" / "experiment_registry.csv"
    rows_r = [r for r in csv.reader(io.StringIO(rp.read_text(encoding="utf-8"))) if r]
    hdr, body = rows_r[0], rows_r[1:]
    if "EXP-0084" not in {r[0] for r in body}:
        rec = dict.fromkeys(hdr, "")
        rec.update({"exp_id": "EXP-0084", "paper_id": "P001", "topic_id": "T037",
                    "stage": "external_corpus_transfer_toolret_eval",
                    "script": "02_shared_code/statistics/toolret_eval_transfer_e08.py; "
                              "02_shared_code/registry/record_exp0084_p001.py",
                    "config": f"frozen model (C={d['frozen_model']['C']}) fitted on published Toucan dev rows only, "
                              f"scored on {aq['n_rows']} ToolRet EVAL rows stratified {d['per_subset_cap']}/subset over "
                              f"{d['construct']['subsets']} subsets at seed {d['seed']}; every query faces the union of "
                              f"the three released partitions ({d['union_catalogue_docs']} tools); inclusion and "
                              "gold-in-union rules fixed before scoring; bands >=0.65/0.55-0.65/<0.55 frozen in "
                              "EXP-0021",
                    "seed": str(d["seed"]), "started_at": d["started_at"], "finished_at": NOW,
                    "status": f"DOES NOT TRANSFER: AUROC {aq['frozen_auroc']}, subset-clustered CI "
                              f"{ci_s[0]}-{ci_s[1]}, below the length-only baseline {aq['length_only_baseline']}",
                    "outputs": f"results_raw/{art.name}; results_processed/EXP0083_toolret_eval_arms.csv; "
                               "results_processed/EXP0083_toolret_eval_per_subset.csv; "
                               "papers/P001_routing_failure_qpp/external_toolret_eval_transfer.md",
                    "notes": "contradicts EXP-0082's borderline pass on the same benchmark's TRAINING partition: the "
                             "predictor's apparent cross-corpus transfer is candidate-set dependent, and this "
                             "whole-pool arm is the harder and more faithful construct. Arm B is undiagnosed "
                             "(constant-score-vector signature) and is not quoted",
                    "enters_paper": "yes - claim C24, limitations L20, final_audit G18-B, deviations"})
        body.append([rec[c] for c in hdr])
        rp.write_text("".join(line(x) for x in [hdr] + body), encoding="utf-8", newline="")
        print("  registry: EXP-0084 added")

    # ---- claim C24
    cmp_path = P / "claims_evidence_matrix.csv"
    crows = [r for r in csv.reader(io.StringIO(cmp_path.read_text(encoding="utf-8"))) if r]
    chdr, cbody = crows[0], crows[1:]
    if "C24" not in {r[0] for r in cbody}:
        c = dict.fromkeys(chdr, "")
        c.update({"claim_id": "C24",
                  "claim": "在 ToolRet 评测集（每查询面对 4.4 万工具的全池目录）上，冻结的检索前预测器不能迁移："
                           "AUROC 低于机会且低于长度基线",
                  "claim_type": "外部验证的否证（E08 第二臂；G18-B external validation）",
                  "experiment_id": "EXP-0084", "direction": "against (does not transfer)",
                  "digits_reported": f"n={aq['n_rows']} positives={aq['positives']} AUROC={aq['frozen_auroc']} "
                                     f"rowCI={ci_r[0]}-{ci_r[1]} subsetCI={ci_s[0]}-{ci_s[1]} "
                                     f"length-only={aq['length_only_baseline']} margin={aq['post_retrieval_margin_baseline']} "
                                     f"fail@3={aq['fail_at_3_prevalence']} vs source {d['source']['fail_at_3_prevalence']}",
                  "statistical_test": f"行级 bootstrap 500 次 + 按 {d['construct']['subsets']} 个任务子集聚类的 bootstrap"
                                      f"（seed {d['seed']}）；引更宽的子集区间；判据带在 EXP-0021 冻结，未因结果调整",
                  "raw_result_file": f"results_raw/{art.name}",
                  "table": "results_processed/EXP0083_toolret_eval_arms.csv; "
                           "results_processed/EXP0083_toolret_eval_per_subset.csv",
                  "figure": "papers/P001_routing_failure_qpp/external_toolret_eval_transfer.md",
                  "where_in_paper": "Limitations L20; final_audit G18-B; external_toolret_eval_transfer.md",
                  "status": "supported as a negative: transfer fails on whole-pool catalogues; EXP-0082's "
                            "mined-negative pass must be read as construct-dependent"})
        row = [c[k] for k in chdr]
        if len(row) != len(chdr):
            raise SystemExit(f"ABORT: C24 has {len(row)} fields against a {len(chdr)}-column header")
        cbody.append(row)
        cmp_path.write_text("".join(line(x) for x in [chdr] + cbody), encoding="utf-8", newline="")
        print("  claims matrix: C24 added")

    # ---- limitations L20
    lim = P / "limitations.md"
    s = lim.read_text(encoding="utf-8")
    if "L20 外部验证在全池目录上不成立" not in s:
        s += f"""
## L20 外部验证在全池目录上不成立：EXP-0084 推翻了 EXP-0082 的迁移读数

同一冻结模型、同一判据带（EXP-0021 事先冻结，未因结果改动），换到 ToolRet **评测发布**的整池目录（每查询
{d['union_catalogue_docs']:,} 个候选，{d['construct']['subsets']} 个子集，{aq['n_rows']} 行分层抽样、零拒绝）后：
AUROC **{aq['frozen_auroc']}**，行级 CI {ci_r[0]}-{ci_r[1]}，按子集聚类 CI {ci_s[0]}-{ci_s[1]}，
**低于机会且低于同批行的长度基线 {aq['length_only_baseline']}**；事后 margin 基线为 {aq['post_retrieval_margin_baseline']}。
EXP-0082 在同一基准的**训练分区**（每查询 10 个 NV-embed 挖出的硬负例、目录规模近乎恒定）上拿到的 0.6536 压线通过，
因此不能被读作"跨语料可迁移"：可迁移性依赖候选集构造，本文的外部验证结论以整池这一臂为准，即 **不迁移**。

三条同时成立：失败按子集逐一给出（{len(rows)} 个 category×subset 单元的 fail@3 从 {spread[0]} 到 {spread[-1]}），
不是单个异常子集拖累均值；arm B 返回 AUROC 恰为 {ai['frozen_auroc']} 且两个区间宽度为零，这是分数向量为常数的征兆，
按缺陷处理、在诊断完成前禁止引用（诊断次序与候选成因见 `external_toolret_eval_transfer.md`）；
本条不改动域内 dev/test 的任何数字，它改变的是"外部验证"这一项的结论方向。
"""
        lim.write_text(s, encoding="utf-8", newline="")
        print("  limitations: L20 appended")

    # ---- gate row: both arms, with the negative as the governing one
    fa = P / "final_audit.md"
    s = fa.read_text(encoding="utf-8")
    if "GOVERNING EXTERNAL RESULT" not in s:
        s = sub1(s, r"\| cross-dataset external validation \|[^\n]*\n",
                 "| cross-dataset external validation | **FAILS on the faithful construct (EXP-0084)** | two external "
                 f"arms on ToolRet: mined-negative training partition -> AUROC 0.6536 (row CI 0.6349-0.6733 vs the "
                 f"frozen 0.65 bar, borderline); the benchmark's EVAL release with whole-union catalogues "
                 f"({d['union_catalogue_docs']:,} tools/query) -> **AUROC {aq['frozen_auroc']}, subset-clustered CI "
                 f"{ci_s[0]}-{ci_s[1]}, below chance and below the length-only baseline "
                 f"{aq['length_only_baseline']}**. **GOVERNING EXTERNAL RESULT = does not transfer**; EXP-0082's pass "
                 "is retained only as evidence that the signal is candidate-set dependent. Arm B is undiagnosed and "
                 "not quoted. `external_toolret_eval_transfer.md`, limitations L20, claim C24 |\n",
                 "gate row", marker="GOVERNING EXTERNAL RESULT")
        fa.write_text(s, encoding="utf-8", newline="")

    # ---- deviation: the earlier external number is superseded in interpretation
    used = set()
    for f in glob.glob(str(ROOT / "papers" / "*" / "deviations.md")):
        used |= {int(x) for x in re.findall(r"^\| D(\d+) \|", pathlib.Path(f).read_text(encoding="utf-8"), re.M)}
    did = max(used | {0}) + 1
    dv = P / "deviations.md"
    s = dv.read_text(encoding="utf-8")
    if "从「外部验证据」降级为" not in s:          # content-keyed, not id-keyed: see the scaffolding lesson
        s = s.rstrip() + "\n" + (
            f"| D{did} | {NOW} | EXP-0082 的 0.6536 从「外部验证据」降级为「候选集构造依赖的证据」 | "
            f"EXP-0084 在同一基准的评测发布上重做：每查询面对 {d['union_catalogue_docs']:,} 工具的全池目录，"
            f"AUROC {aq['frozen_auroc']}（子集聚类 CI {ci_s[0]}-{ci_s[1]}），低于机会、低于长度基线 "
            f"{aq['length_only_baseline']}；判据带未动，只换构造 | 否（两臂都是 dev-only 拟合，未读任何测试行） | "
            "门槛结论方向改为不迁移（L20 与 C24 记录，final_audit 标注 GOVERNING EXTERNAL RESULT）；"
            "同轮发现 arm B 分数向量退化为常数征兆，按缺陷登记且禁止引用 |\n")
        dv.write_text(s, encoding="utf-8", newline="")
        print(f"  deviations: appended D{did}")

    # ---- handoff note must stop pointing at an outstanding job
    pk = ROOT / "00_program_registry" / "PROGRAM_STATUS.md"
    s = pk.read_text(encoding="utf-8")
    if "EXP-0084 - ToolRet EVAL-split transfer" in s and "EXP-0084 RECORDED" not in s:
        i = s.find("**EXP-0084 - ToolRet EVAL-split transfer")
        j = s.find("\n\n", i)
        s = (s[:i] + "**EXP-0084 RECORDED — and it is a negative.** The EVAL-split transfer finished "
             f"(artefact `results_raw/{art.name}`, {d['wallclock_sec']}s): AUROC {aq['frozen_auroc']}, "
             f"subset-clustered CI {ci_s[0]}-{ci_s[1]}, below chance and below the length-only baseline "
             f"{aq['length_only_baseline']} -> **does not transfer**. Registered as EXP-0084 with claim C24, "
             "limitations L20, a gate row that names it the governing external result, and a deviation demoting "
             "EXP-0082's 0.6536 to construct-dependent evidence. Open next: (1) diagnose arm B's constant score "
             "vector (candidates: NaN/inf through the scaler, a feature saturating at 44k-document catalogue "
             "magnitudes, per-query recomputation of corpus statistics); (2) decide whether P001's external arm "
             "should be reported as a null in the paper body, which is the honest framing; (3) the standing human "
             "second-coder gaps." + s[j:])
        pk.write_text(s, encoding="utf-8", newline="")
        print("  PROGRAM_STATUS.md updated")
    print(f"EXP-0084 recorded: AUROC {aq['frozen_auroc']} ({aq['verdict_by_frozen_bands']}), "
          f"degenerate arm B = {degenerate_b}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
