"""Post-run documentation writer for the D13/D14 amendments (limitations, protocol freeze, claims
matrix, reviewer attack, final audit). Kept as a script so the prose edits are reviewable and the
number strings appear exactly once."""

import pathlib

import pandas as pd

P = pathlib.Path(__file__).resolve().parents[1]

# ------------------------------------------------------------------ limitations
q = P / "limitations.md"
t = q.read_text(encoding="utf-8")
if "## L10" not in t:
    head = """## L10 未见目录（catalogue）泛化被高估（本轮最重要限制，已降级结论）

EXP-0017/0018 实测：本语料支配性依赖结构是**目录**而不是 prompt。
- 组内相关 ICC 最高 0.484（Qwen3 按 gold 工具词干分组）、设计效应最高 **4.39**；
- 按目录分组交叉验证使 dev AUROC 下降 **0.0164 / 0.1110 / 0.0048**（按 gold 词干下降 0.027/0.100/0.013）；
- 发布的 split 下 **80.9% / 88.1% / 63.7%** 的 test 行与 dev 行共享完全相同的候选目录（prompt_id 跨块数 = 0）；
- 无法用重划分补救：目录–prompt 连通图最大连通块含 14187/14699/12912 行（86–98%），
  强制目录不相交只剩 553/221/641 个 dev 行，不足以支撑任何估计。

**处理办法（不是文字修补）**：正文把 test AUROC 明确标注为"对未见目录是上界"，并给出按目录分组的保守值
**0.807 / 0.718 / 0.790**；所有置信区间改为**按目录聚类**自助法（EXP-0019），CI 宽度最多放大 **2.955 倍**，
9/9 主对比仍不含 0；另记 GEE 稳健标准误最大为朴素值的 **7.33 倍**，说明此前朴素 p 值过于乐观。
遗留真实风险：在没有独立目录集合的数据上，事前预测能力的下界仍未被证明。

## L11 跨任务域稳健性切割在本语料内不可执行（数据事实，非取舍）

原计划用 `subset_name` 做跨域稳健性切割，实测**每个 config 内 subset_name 只有 1 个取值**，故该切割在语料内
不可估计；已改用 gold 工具词干作为阻断因子，并把这一替代写进附录 A11c 而不是隐去。

"""
    q.write_text(head + t, encoding="utf-8")

# ------------------------------------------------------------------ protocol freeze
pf = P / "protocol_freeze.md"
s = pf.read_text(encoding="utf-8")
if "Amendments after the freeze that change what may be claimed" not in s:
    s += """

---

## Amendments after the freeze that change what may be claimed (D13/D14, 2026-09-18 20:28-20:39)

1. **Inference unit.** Confidence intervals for the development contrasts are resampled on the
   **catalogue fingerprint**, not on `prompt_id` (EXP-0019). Justification: measured ICC and design
   effect show the catalogue is the binding dependence structure, and GEE robust standard errors reach
   7.33x the naive ones. No model, feature set, seed, metric or hypothesis changed.
2. **Claim scope.** The held-out AUROC is quoted as an **upper bound for unseen catalogues**, with the
   catalogue-grouped cross-validation figure reported beside it, because 63.7-88.1% of test rows share
   a catalogue with development rows and no catalogue-disjoint split exists (the largest connected
   component of the catalogue-prompt graph covers 86-98% of rows). This narrows a claim; it does not
   re-open one.
3. **The test split was not re-evaluated.** `test_eval_ledger.json` still records exactly one
   evaluation. The correction comes from re-analysis of development data plus disclosure, which is the
   only route T01.02 leaves once the single evaluation is spent.
"""
    pf.write_text(s, encoding="utf-8")

# ------------------------------------------------------------------ claims matrix
cm = P / "claims_evidence_matrix.csv"
d = pd.read_csv(cm)
if "C12" not in set(d.claim_id):
    rows = [
     dict(claim_id="C12",
      claim=("机制由受控干预确立：向候选目录注入与金标注词汇相近的兄弟工具，单调整例地把 fail@3 流行率从 "
             "0.0777/0.1292/0.0424 抬升到 0.2585/0.3534/0.1433，而冻结事前模型的预测风险几乎同幅上升 "
             "(+0.1808/+0.2243/+0.1010)；把同样的元数据增补施加于金标注工具可把失败率压到 0.0010-0.0022，"
             "但施加于随机非金标注工具反而使路由更差 (+0.031/+0.030/+0.025)。"),
      claim_type="机制（E17 反事实干预 + E12 目录规模剂量效应）",
      experiment_id="EXP-0016", direction="supports_causal_reading_of_mechanism",
      digits_reported=("control prev 0.0777/0.1292/0.0424 with dev AUC reproduced exactly "
        "0.8233/0.8294/0.7951 and 0 label drift; distract_8 0.2585/0.3534/0.1433, dRisk "
        "+0.1808/+0.2243/+0.1010; enrich_gold 0.0012/0.0022/0.0010; enrich_sham "
        "0.1083/0.1593/0.0676; namespace_prefix and order_shuffle near-null; control-fitted "
        "transfer AUROC onto crowded catalogs 0.742/0.720/0.716"),
      table="tables/table10_catalog_interventions.csv; appendix A11b", figure="-",
      statistical_test=("paired cluster (prompt_id) bootstrap, 1000 resamples, on dPrevalence and "
        "dMeanRisk; dose-response slope over k=2/4/8; AUROC of the enrichment arms flagged "
        "non-informative by construction"),
      raw_result_file="results_raw/EXP0016_catalog_intervention_20260918T202157.json",
      where_in_paper="Results robustness/mechanism; Appendix A11b; reviewer_attack A23",
      status="supported"),
     dict(claim_id="C13",
      claim=("统计单位与泛化边界：支配性依赖结构是目录而非 prompt (ICC 最高 0.484, 设计效应最高 4.39, "
             "GEE 稳健标准误最高为朴素值 7.33 倍)；发布 split 下 63.7-88.1% 的 test 行与 dev 共享目录，"
             "且不存在目录不相交的划分 (最大连通块含 86-98% 行)。因此 test AUROC 只是对未见目录的上界，"
             "保守值为按目录分组交叉验证的 0.807/0.718/0.790；改用目录聚类自助后 CI 宽度最多放大 2.955 倍，"
             "但 9/9 主对比仍不含 0。"),
      claim_type="统计效度与结论范围（自我否证式收紧）",
      experiment_id="EXP-0017;EXP-0018;EXP-0019", direction="narrows_scope_confirms_direction",
      digits_reported=("grouped-CV deltas vs published: catalogue -0.0164/-0.1110/-0.0048; gold_stem "
        "-0.0271/-0.1000/-0.0129; catalogue AND stem -0.0220/-0.1113/-0.0043; prompt_id "
        "+0.0009/-0.0000/+0.0039; straddling catalogues 887/498/837; largest component "
        "14187/14699/12912 of 15000; max design effect 4.394; GEE SE inflation 7.334; CI width "
        "inflation up to 2.955; 9/9 contrasts survive"),
      table="tables/table11_dependence_and_inference.csv; appendix A11c", figure="-",
      statistical_test=("ANOVA ICC + design effect; GroupKFold vs StratifiedKFold AUROC; GEE "
        "exchangeable clustered on catalogue; Bayesian logistic mixed model; paired cluster "
        "bootstrap under two resampling units"),
      raw_result_file=("results_raw/EXP0017_hierarchical_dependence_*.json; "
        "results_raw/EXP0018_catalog_disjoint_split_*.json; "
        "results_raw/EXP0019_catalogue_clustered_inference_*.json"),
      where_in_paper="Abstract; Section 8; Limitations L10/L11; protocol_freeze amendments",
      status="supported")]
    d = pd.concat([d, pd.DataFrame(rows)], ignore_index=True)
    d.to_csv(cm, index=False)

# ------------------------------------------------------------------ reviewer attack
ra = P / "reviewer_attack.md"
s = ra.read_text(encoding="utf-8")
A7_old = """| A7 | **Is the statistical unit independent?** | Threat measured | EXP-0008f: 4.5-9.4% of `prompt_id`s recur across configs; up to 3 rows share one `prompt_id`. | Split grouped by `prompt_id` (D5) and **all** bootstrap inference clustered on it (1000 resamples). |"""
A7_new = """| A7 | **Is the statistical unit independent?** | **Failed, then corrected** | EXP-0017: the binding cluster is the **catalogue**, not the prompt - ICC up to 0.484, design effect up to **4.39**, GEE robust SEs up to **7.33x** naive; grouping the CV by catalogue costs up to **0.111 AUROC**. Prompt-only clustering was not enough. | Inference re-run clustered on catalogue (EXP-0019): CIs widen up to 2.955x and **9/9** headline contrasts still exclude zero. All quoted intervals are the corrected ones. |"""
if A7_old.replace("-", "–") in s:
    A7_old = A7_old.replace("-", "–")
A11_old = ("| A11 | **Test-set leakage / tuning?** | Clean | `test_eval_ledger.json`: exactly **1** "
           "evaluation, 2026-09-18T18:58:02, hash `9c0c3344e0a0cf62`, `override_reason=null`. "
           "Selection, canonical feature list, grid and H4 analysis all dev-only. EXP-0012's first "
           "attempt raised before reading any test row. | Second test evaluation is refused by the "
           "ledger unless an override reason is supplied. |")
A11_new = ("| A11 | **Test-set leakage / tuning?** | Clean, but **catalogue leakage found separately** "
           "(see A11a) | `test_eval_ledger.json`: exactly **1** evaluation, 2026-09-18T18:58:02, hash "
           "`9c0c3344e0a0cf62`, `override_reason=null`. Selection, canonical feature list, grid, H4 and "
           "the intervention analysis are all dev-only. EXP-0012's first attempt raised before reading "
           "any test row. | Second test evaluation is refused by the ledger unless an override reason "
           "is supplied; none was given.\n"
           "| A11a | **Catalogue leakage across the split?** | **Found and disclosed** | EXP-0018: "
           "887/498/837 catalogues straddle dev and test, so **63.7-88.1% of test rows** are scored on "
           "a competitive situation present in training. No repair exists: one connected component holds "
           "86-98% of rows, so a catalogue-disjoint split leaves 553/221/641 dev rows. | Test AUROC "
           "relabelled an **upper bound for unseen catalogues** with the catalogue-grouped dev figure "
           "(0.807/0.718/0.790) beside it. **No second test evaluation was run.** Logged as D13. |")
A23_old = ("| A23 | **Causal/mechanism identification?** | Not claimed | No intervention experiment "
           "yet; the catalog is observational. | Mechanistic reading in A6's side-result is framed as an "
           "interpretation, and the counterfactual catalog intervention (E17) is listed as outstanding. |")
A23_new = ("| A23 | **Causal/mechanism identification?** | **Now identified by intervention** | "
           "EXP-0016: injected confusable siblings raise failure monotonically to 0.2585/0.3534/0.1433 "
           "and move the predictor's risk by +0.181/+0.224/+0.101 (near 1:1); gold-description "
           "enrichment cuts failure to ~0.001 while the **sham** arm - the same edit on a non-gold tool - "
           "makes routing *worse*; namespace renaming and order shuffling are no-ops. | Appendix A11b. "
           "The mechanism is now backed by manipulation with a specificity control, not correlation. The "
           "enrichment arms' AUROC~1 is flagged as a low-prevalence artifact, not sold as improvement. |")
for old, new in ((A7_old, A7_new), (A11_old, A11_new), (A23_old, A23_new)):
    if old in s:
        s = s.replace(old, new)
    else:
        print("NOTE: reviewer-attack anchor not found for", old[:40])
s = s.replace("""4. **No intervention** (A23), so the mechanism reading stays interpretive.

Items 1, 2 and 4 require new runs, and they are the standing to-do list in `limitations.md`; item 3 is
inherent to defining failure operationally and is handled by disclosure plus an alternative-ranker check.""",
"""4. **Unseen-catalogue generalisation is bounded, not measured on held-out data** (A7/A11a): the corpus
   cannot supply a catalogue-disjoint test set, so 0.718 on Qwen3 is a conservative surrogate.

Item 4 was created by this audit and is answered as far as these data allow (grouped CV, corrected
clustering, narrowed claim). Items 1-3 need new data or new runs and remain the to-do list in
`limitations.md`. The intervention gap that used to sit here is closed by EXP-0016.""")
ra.write_text(s, encoding="utf-8")
print("docs updated; claims now", list(pd.read_csv(cm).claim_id))
