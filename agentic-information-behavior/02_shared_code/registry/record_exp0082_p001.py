"""EXP-0082 recorder: P001's frozen predictor scored on ToolRet, and the gate wording that follows.

The result is borderline against a band that was frozen before this corpus existed, so the recorder states both the
point verdict and the interval, and does not move the bar. Numbers are read from the artefact; the edits are
marker-guarded and every append is keyed on its own content.

    python record_exp0082_p001.py
"""
from __future__ import annotations

import csv, io, json, pathlib, re, sys, time

HERE = pathlib.Path(__file__).resolve().parent          # 02_shared_code/registry
ROOT = HERE.parents[1]                                   # repository root
P = ROOT / "papers" / "P001_routing_failure_qpp"
NOW = time.strftime("%Y-%m-%dT%H:%M:%S")


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
    art = sorted((ROOT / "results_raw").glob("EXP0082_toolret_external_transfer_*.json"))[-1]
    d = json.loads(art.read_text(encoding="utf-8"))
    a_q, a_i = d["arms"][0], d["arms"][1]
    ind = d["independence"]
    ci = a_q["row_bootstrap_ci95"]
    straddles = ci[0] < d["bands"]["transfers"] <= ci[1]

    doc = f"""# External validation on an independent tool universe: ToolRet (EXP-0082)

Artefact `{art.name}`; seed {d['seed']}; {d['wallclock_sec']}s. Code
`02_shared_code/statistics/toolret_external_transfer_e08.py`. Nothing here was fitted on ToolRet rows: the frozen
predictor was fitted on the published Toucan **dev** splits ({d['source']['n_dev_rows']:,} rows, three configs) and
only scored on the external corpus, and no feature, threshold or C value was chosen from these rows.

## Why this corpus, and how it arrived

P001's external-validation gate had been carried as an environment limit - "the external benchmarks are not
downloadable here" - until EXP-0081 tested that sentence channel by channel and found the benchmark's HuggingFace
release reachable with a working negative control. This step is what that unblocked.
Provenance: `mangopy/ToolRet-Training-20w` through `hf-mirror`, shard
`train-00000-of-00006.parquet`, {d['acquisition_provenance']['shard_bytes_on_disk']:,} B on disk, snapshot
`{d['acquisition_provenance']['revision'].split(' ')[0]}`; the card declares {d['acquisition_provenance']['card_declares']['num_examples']:,}
rows in one train split.

## Corpus construct, measured before any score

* {d['corpus_extraction']['rows_seen']:,} rows in the shard, {d['corpus_extraction']['rows_sampled']:,} sampled at
  seed {d['seed']}, {d['corpus_extraction']['rows_kept']:,} kept, rejection accounting
  `{json.dumps(d['corpus_extraction']['rejection_accounting'])}`;
* catalogue size is near-constant by construction: mean {a_q['mean_n_candidates']} (sd
  {a_q['sd_n_candidates']}) over {a_q['n_rows']:,} rows, because the benchmark pairs each query with its targets plus
  **10 negatives mined by NV-embed-v1** - so a frozen feature that measures how many candidates a row has carries
  almost no variance here, and the reader should discount any such feature's contribution rather than the paper
  quietly dropping it;
* fail@3 prevalence {a_q['fail_at_3_prevalence']} (vs {d['source']['fail_at_3_prevalence']} on the source dev rows) -
  **not comparable numbers**, because the candidate set here is a mined hard-negative set rather than a production
  catalogue. The prevalence coincidence is therefore reported, not interpreted;
* independence from everything P001 has used: {ind['external_tool_names']:,} distinct tool names, of which
  {ind['shared_tool_names']} appear in the source corpora' catalogues
  ({100 * ind['share_of_external_names_unseen_in_source']:.1f}% never seen), and only
  {ind['external_catalog_tokens_covered_by_source']} of the external catalogue tokens are covered by source tokens.
  This is a genuinely different tool universe, much more so than `hermes` was.

## Result against the bands frozen in EXP-0021

| arm | text the features see | rows | positives | AUROC | row-bootstrap 95% | length-only | post-retrieval margin | verdict |
|---|---|---|---|---|---|---|---|---|
| A (primary) | the raw user `query` | {a_q['n_rows']:,} | {a_q['positives']:,} | **{a_q['frozen_auroc']}** | {ci[0]}-{ci[1]} | {a_q['length_only_baseline']} | {a_q['post_retrieval_margin_baseline']} | {a_q['verdict_by_frozen_bands']} |
| B (upper reference) | the benchmark's target-aware `prompt` | {a_i['n_rows']:,} | {a_i['positives']:,} | {a_i['frozen_auroc']} | {a_i['row_bootstrap_ci95'][0]}-{a_i['row_bootstrap_ci95'][1]} | {a_i['length_only_baseline']} | {a_i['post_retrieval_margin_baseline']} | {a_i['verdict_by_frozen_bands']} |

Bands: >= {d['bands']['transfers']} transfers, {d['bands']['partial']}-{d['bands']['transfers']} partial,
< {d['bands']['partial']} does not transfer. "Within-corpus" OOF on the same external rows gives
{', '.join(str(v) for v in a_q['within_corpus_oof_aucroc'])} - reported so the transfer gap is visible rather than
implicit.

**The honest reading of arm A.** The point estimate clears the bar, and {"the interval straddles it" if straddles
else "the interval sits above it"} ({ci[0]}-{ci[1]}), so this is a **borderline pass, not a demonstrated transfer**:
the frozen rule says "transfers" on the number it was written to judge, and the interval says the same data are
compatible with the partial band. Both sentences are part of the result; quoting only the first would be the
cherry-picking the programme forbids. It is far above the length-only baseline on the identical rows
({a_q['length_only_baseline']}), so the signal is not text length - and it is **below** the post-retrieval margin
baseline ({a_q['post_retrieval_margin_baseline']}), which is the same ordering P001 reports in-domain: knowing the
lexical margin beats predicting the failure before retrieval.

**Arm B went the wrong way and that is reported as measured.** The released instructions are generated by a
target-aware strategy - the example in the dataset card names the gold capabilities outright - so arm B was fixed in
advance as a leakage-bounded upper reference. Its AUROC is *lower* than arm A's ({a_i['frozen_auroc']} vs
{a_q['frozen_auroc']}), which means the predicted direction (leaky text should score higher) did not materialise.
No post-hoc re-assignment of which arm is primary is offered: arm A stays the headline, and arm B stays an anomaly
with a disclosed mechanism guess at most.

## What this changes for the gate

Cross-dataset external validation moves from "not possible here" to **executed once, with a borderline result on a
corpus whose construct differs from the paper's own** (mined hard negatives, ~17 candidates per row, no
catalogue-size variance). What it does not do:

* it is not a reproduction of the ToolRet leaderboard - different measure (pre-retrieval fail@3 vs nDCG@10),
  different candidate sets, and these are the benchmark's **training** partition rows, which is fine only because
  nothing was fitted on them;
* it does not settle the subset-generality question EXP-0035 raised for `single-turn-diversify`: ToolRet's own
  instructions are machine-rewritten, so if anything arm A is closer to that weak condition than to the published
  one - and it scores {a_q['frozen_auroc']} there, which is worth a follow-up rather than a claim;
* it does not replace the second human coder or any other outstanding item.

## Reproduce

    python 02_shared_code/statistics/toolret_external_transfer_e08.py --rows 6000 --seed {d['seed']}
"""
    (P / "external_toolret_transfer.md").write_text(doc, encoding="utf-8", newline="")

    # ---- final audit: the gate row, which EXP-0081 opened
    fa = (P / "final_audit.md").read_text(encoding="utf-8")
    fa = sub1(fa, r"\| cross-dataset external validation \|[^\n]*\n",
              f"| cross-dataset external validation | **EXECUTED on an external corpus - borderline (EXP-0082)** | "
              f"the frozen predictor, fitted on the published Toucan dev splits only, scored on 6,000 ToolRet rows "
              f"(independent tool universe: {ind['external_tool_names']:,} names, "
              f"{100 * ind['share_of_external_names_unseen_in_source']:.1f}% never seen in the source catalogues): "
              f"AUROC **{a_q['frozen_auroc']}**, row-bootstrap 95% {ci[0]}-{ci[1]} against the band frozen at "
              f"{d['bands']['transfers']} - the point estimate passes, the interval straddles the bar, and both are "
              f"stated; length-only baseline {a_q['length_only_baseline']}, post-retrieval margin "
              f"{a_q['post_retrieval_margin_baseline']}. Construct differs (10 NV-embed-mined negatives per query, "
              f"catalogue size {a_q['mean_n_candidates']}±{a_q['sd_n_candidates']}), so prevalence is not comparable; "
              "see `external_toolret_transfer.md` |\n",
              "final_audit gate row", marker="EXECUTED on an external corpus")
    (P / "final_audit.md").write_text(fa, encoding="utf-8", newline="")

    # ---- limitations: a new numbered section, content-keyed so a re-run cannot duplicate it
    lim = (P / "limitations.md").read_text(encoding="utf-8")
    if "L22 外部验证已做一次" not in lim:
        lim += f"""
## L22 外部验证已做一次，结果是压线而非确证（EXP-0082，`external_toolret_transfer.md`）

冻结模型只在已发表的 dev 行上拟合，仅对 ToolRet 的 6,000 行打分：AUROC **{a_q['frozen_auroc']}**，
行级自助 95% 区间 {ci[0]}-{ci[1]}，对照事先冻结的 0.65 门槛——点估计过线、区间跨线，两句都是结果的一部分，
只引前一句就是本系列禁止的择优报告。同批行上长度基线 {a_q['length_only_baseline']}，
事后 margin 基线 {a_q['post_retrieval_margin_baseline']}（仍高于预测器，与域内一致的排序）。

四条边界与数字同时成立：

1. 该语料每查询只配 10 个由 NV-embed-v1 挖出的硬负例（目录规模 {a_q['mean_n_candidates']}±{a_q['sd_n_candidates']}），
   不是生产目录，因此 fail@3 普遍率 {a_q['fail_at_3_prevalence']} 与域内 {d['source']['fail_at_3_prevalence']} 不可比；
   目录规模特征在此几乎无方差，涉及它的任何贡献都应打折而不是被悄悄删掉；
2. 这是该基准的**训练分区**行：因为没有任何东西在其上拟合，所以可用，但它不是 ToolRet 榜单复现，
   也不构成任何 leaderboard 比较；
3. 预注册为"上界参照"的 arm B（目标感知改写指令）实测**低于**主臂（{a_i['frozen_auroc']} < {a_q['frozen_auroc']}），
   即预期的泄漏方向没有发生；主臂不改、不做事后重指派，异常如实保留；
4. 独立性实测：外部工具名 {ind['external_tool_names']:,} 个中与源语料目录共享仅 {ind['shared_tool_names']} 个
   （未见比例 {100 * ind['share_of_external_names_unseen_in_source']:.1f}%），目录 token 覆盖率
   {ind['external_catalog_tokens_covered_by_source']}——比 hermes 那次更接近真正的陌生工具宇宙。
"""
        (P / "limitations.md").write_text(lim, encoding="utf-8", newline="")
        print("  limitations: appended L19")

    # ---- claims matrix row
    cmp_path = P / "claims_evidence_matrix.csv"
    rows = [r for r in csv.reader(io.StringIO(cmp_path.read_text(encoding="utf-8"))) if r]
    hdr, body = rows[0], rows[1:]
    if "C23" not in {r[0] for r in body}:
        C = dict.fromkeys(hdr, "")
        C.update({"claim_id": "C23",
                  "claim": "冻结的检索前预测器在完全外部的工具宇宙（ToolRet）上仍能把 BM25 将漏掉的行排在将命中的行之前，"
                           "但只是压线通过",
                  "claim_type": "外部验证（E08 第二语料；G18-B external validation）",
                  "experiment_id": "EXP-0082", "direction": "supports (borderline)",
                  "digits_reported": f"n=6000 positives={a_q['positives']} AUROC={a_q['frozen_auroc']} "
                                     f"CI[{ci[0]},{ci[1]}] band={d['bands']['transfers']}; length-only "
                                     f"{a_q['length_only_baseline']}; margin {a_q['post_retrieval_margin_baseline']}; "
                                     f"tool names unseen in source {100 * ind['share_of_external_names_unseen_in_source']:.1f}%",
                  "statistical_test": f"行级 bootstrap 500 次（seed {d['seed']}）；每个目录即每行唯一，"
                                      "故无法做目录聚类区间，已如实标注为行级；判据带 0.65/0.55 早在 EXP-0021 冻结",
                  "raw_result_file": f"results_raw/{art.name}",
                  "table": "", "figure": "papers/P001_routing_failure_qpp/external_toolret_transfer.md",
                  "where_in_paper": "Limitations L22; final_audit G18-B; external_toolret_transfer.md",
                  "status": "supported, borderline: point estimate above the frozen bar, CI straddles it"})
        C23 = [C[c] for c in hdr]
        if len(C23) != len(hdr):
            raise SystemExit(f"ABORT: C23 has {len(C23)} fields against a {len(hdr)}-column header")
        body.append(C23)
        cmp_path.write_text("".join(_line(x) for x in [hdr] + body), encoding="utf-8", newline="")
        print("  claims matrix: appended C23")

    # ---- registry row, keyed by column name
    rp = ROOT / "00_program_registry" / "experiment_registry.csv"
    rrows = [r for r in csv.reader(io.StringIO(rp.read_text(encoding="utf-8"))) if r]
    rhdr, rbody = rrows[0], rrows[1:]
    if "EXP-0082" not in {r[0] for r in rbody}:
        rec = dict.fromkeys(rhdr, "")
        rec.update({"exp_id": "EXP-0082", "paper_id": "P001", "topic_id": "T037",
                    "stage": "external_corpus_transfer_toolret",
                    "script": "02_shared_code/statistics/toolret_external_transfer_e08.py",
                    "config": f"frozen model (C={FROZEN_C_note(d)}) fitted on published Toucan dev rows only, scored on "
                              f"6,000 ToolRet rows at seed {d['seed']}; inclusion rule n_candidates>3 fixed beforehand; "
                              "two text arms (raw query primary, target-aware instruction as leakage-bounded upper "
                              "reference); bands >=0.65/0.55-0.65/<0.55 frozen in EXP-0021",
                    "seed": f"{d['seed']}", "started_at": d["started_at"], "finished_at": NOW,
                    "status": f"borderline pass: AUROC {a_q['frozen_auroc']} CI {ci[0]}-{ci[1]}",
                    "outputs": f"results_raw/{art.name}; results_processed/EXP0082_toolret_arms.csv; "
                               "results_processed/EXP0082_toolret_rows_sample.csv; "
                               "papers/P001_routing_failure_qpp/external_toolret_transfer.md; "
                               "results_raw/superseded/EXP0082_toolret_external_transfer_20260920T070628.json",
                    "notes": "first external validation of the frozen predictor on an independent tool universe "
                             f"({ind['external_tool_names']:,} tool names, "
                             f"{100 * ind['share_of_external_names_unseen_in_source']:.1f}% unseen in the source "
                             "catalogues); point estimate clears the frozen 0.65 bar while the row-bootstrap interval "
                             "straddles it, and arm B went below arm A against the pre-specified leakage direction",
                    "enters_paper": "yes - claim C23, limitations L19, final_audit G18-B"})
        rbody.append([rec[c] for c in rhdr])
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\r\n").writerows([rhdr] + rbody)
    rp.write_text(buf.getvalue(), encoding="utf-8", newline="")
    check = [r for r in csv.reader(io.StringIO(rp.read_text(encoding="utf-8"))) if r]
    if any(len(r) != len(check[0]) for r in check[1:]):
        raise SystemExit("registry has ragged rows after writing")
    print(f"  registry rows={len(check) - 1}; artefact={art.name}")
    return 0


def _line(r):
    b = io.StringIO()
    csv.writer(b, lineterminator="\n").writerows([r])
    return b.getvalue()


def FROZEN_C_note(d):
    return d["frozen_model"]["C"]


if __name__ == "__main__":
    raise SystemExit(main())
