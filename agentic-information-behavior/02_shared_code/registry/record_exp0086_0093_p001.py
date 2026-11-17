"""Record EXP-0086 (support-respecting external test) and EXP-0093 (error analysis as a census) into P001.

EXP-0086 is the third attempt at external validation and the one that settles what can be claimed: the
pre-registered rule (in-support fraction >= 0.25 and >= 30 positives before any transfer language) fires on the
"not testable" side, and the per-feature table shows why - two features are pure functions of pool size
(`log_n_candidates`, `qpp_ecle`) and are outside the dev range on 100% of the 419 external rows, while 17 of the 33
features are never outside at all. That converts "the model does not transfer" into "this feature set cannot be
evaluated on a pool 1,000x larger than the one it was fitted on", and names the next test (size-matched pools).

EXP-0093 re-runs the identical frozen error taxonomy with `--census`, so the per-case table covers every dev false
negative, false positive and true positive instead of 71 sampled ones, and each row carries the inputs the rule
looked at. The per-group reconciliation is asserted, not assumed.

    python record_exp0086_0093_p001.py
"""
from __future__ import annotations

import csv, io, json, pathlib, re, sys, time

ROOT = next(a for a in [pathlib.Path(__file__).resolve().parent, *pathlib.Path(__file__).resolve().parents]
            if (a / "00_program_registry").is_dir())
P = ROOT / "papers" / "P001_routing_failure_qpp"
NOW = time.strftime("%Y-%m-%dT%H:%M:%S")


def line(r):
    b = io.StringIO(); csv.writer(b, lineterminator="\r\n").writerows([r]); return b.getvalue()


def latest(pat):
    f = sorted((ROOT / "results_raw").glob(pat))
    if not f:
        raise SystemExit(f"ABORT: no artefact matches {pat!r}")
    return f[-1], json.loads(f[-1].read_text(encoding="utf-8"))


def sub1(text, pat, repl, tag, marker=None, flags=re.S):
    if marker and marker in text:
        print(f"  [{tag}] already applied - skipped")
        return text
    n = len(re.findall(pat, text, flags))
    if n != 1:
        raise SystemExit(f"ABORT [{tag}]: matched {n}x: {pat[:70]!r}")
    print(f"  [{tag}] applied")
    return re.sub(pat, repl, text, count=1, flags=flags)


def appender(md_path, row, tag, guard):
    t = md_path.read_text(encoding="utf-8")
    if guard in t:
        print(f"  {tag}: already present - skipped")
        return
    md_path.write_text(t.rstrip() + "\n" + row, encoding="utf-8", newline="")
    print(f"  {tag}: appended")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    f86, E = latest("EXP0086_support_respecting_external_*.json")
    f93, G = latest("EXP0093_error_census_*.json")
    S = E["support"]
    arms = {a["arm"]: a for a in E["arms"]}
    import pandas as pd
    pdf = pd.read_csv(ROOT / "results_processed" / "EXP0086_per_feature_support.csv")
    always = pdf[pdf.share_rows_outside >= 0.999].feature.tolist()
    never = int((pdf.share_rows_outside == 0).sum())
    top = pdf.sort_values("share_rows_outside", ascending=False).head(4)
    # the build time is read from the run log, not remembered: the cached re-run reports 1.2s and would otherwise
    # make the expensive step invisible
    log = (ROOT / "logs" / "EXP-0086_support_external.txt")
    m = re.search(r"built (\d+) rows.*?in ([\d.]+)s", log.read_text(encoding="utf-8", errors="replace"))         if log.is_file() else None
    BUILD_MIN = f"{round(float(m.group(2)) / 60)} (log: {m.group(0)[:60]!r})" if m else "over an hour (first run)"
    cen = G["census"]
    n_rows = sum(v["rows"] for v in cen.values())
    if not all(v["labels_reconcile"] for v in cen.values()):
        raise SystemExit("ABORT: EXP-0093's per-row labels do not reconcile with the taxonomy counts")

    doc86 = f"""# External validation is not testable at this pool scale - and the reason is a feature, not a verdict (EXP-0086)

Artefact `{f86.name}`; code `02_shared_code/statistics/toolret_support_respecting_external.py`;
{E['sample']['rows_built']} rows, seed {E['seed']}, {E['wallclock_sec']}s on the cached feature build.
This is the third external measurement after EXP-0082 (training partition) and EXP-0084 (eval release); EXP-0085
withdrew both readings because the frozen model's probability saturated. The rule below was fixed before any AUROC
was computed.

## Pre-registered rule and what it returned

| item | frozen value | measured |
|---|---|---|
| minimum in-support fraction before any transfer language | {E['rules_fixed_before_any_auroc']['in_support_min_fraction']} | **{S['in_support_fraction']}** |
| minimum positives in the in-support subset | {E['rules_fixed_before_any_auroc']['min_positives_for_an_auc']} | {S['positives_in_support']} |
| model | identical dev-fitted frozen pipeline and frozen feature list, nothing refitted | - |
| external rows | {E['sample']['rows_after_inclusion']} queries, mean catalogue {E['sample']['mean_n_candidates']:,.0f} documents | - |
| fail@3 prevalence on the external rows | - | {E['sample']['fail_at_3_prevalence']} |

In-support means every frozen feature of a row lies inside the dev min/max of the model that was fitted on dev.
0 of {S['rows']} rows qualify, so neither "transfers" nor "does not transfer" is an admissible statement, and the
AUROCs are reported as description only: {arms['frozen probability']['auroc_all_rows']}
(CI {arms['frozen probability']['ci95_all_rows']}) for the frozen probability and
{arms['linear predictor (no link)']['auroc_all_rows']} ({arms['linear predictor (no link)']['ci95_all_rows']}) for
the same weights with the link removed.

## Which features leave support, and what that means

| feature | dev range | external range | share of rows outside |
|---|---|---|---|
""" + "\n".join(f"| `{r.feature}` | [{r.dev_min:.3g}, {r.dev_max:.3g}] | [{r.external_min:.3g}, {r.external_max:.3g}] "
               f"| {r.share_rows_outside:.1%} |" for r in top.itertuples()) + f"""

{len(always)} feature(s) are outside on every row ({', '.join('`%s`' % f for f in always)}) and {never} of the
{len(pdf)} are never outside at all. The two are not arbitrary: `log_n_candidates` is the logarithm of the catalogue
size, and dev catalogues span {float(pdf.loc[pdf.feature == 'log_n_candidates', 'dev_min'].iloc[0]):.2f} to
{float(pdf.loc[pdf.feature == 'log_n_candidates', 'dev_max'].iloc[0]):.2f} (about 4 to 70 tools) while the external
pool is a fixed {E['sample']['mean_n_candidates']:,.0f} documents ({float(pdf.loc[pdf.feature == 'log_n_candidates', 'external_min'].iloc[0]):.2f}).
`qpp_ecle` is an expected-calibration-length feature computed over the whole pool, so it moves with pool size too.
Mean number of out-of-range features per row is {S['mean_features_outside_per_row']}, and the marginal shares sum to
{float(pdf.share_rows_outside.sum()):.2f} across {len(pdf)} features.

Two consequences, both stated as limits rather than as findings:

1. **The barrier is two size-scaling inputs, not general drift.** The query-text and most retrieval-quality features
   are in range almost everywhere, which is why the honest description of the external pool is "a different catalogue
   size", not "different queries".
2. **A joint all-features-in-range criterion is a hard test at 33 features.** With marginal out-of-range rates of a
   few percent each, the expected share of rows that pass all of them is small even when the pool is only mildly
   different, so `in_support_fraction = 0.0` on a 1,000x pool does not by itself show radical extrapolation. The
   marginal table above is published so a reader can judge this for the pool at hand instead of taking the rule's
   output on trust; the rule was not relaxed after seeing the number.

## What would make the external test real

Sample the external candidate pool down to the dev catalogue size (40-70 documents, gold included, same queries),
which puts `log_n_candidates` and its downstream QPP sibling inside the fitted range by construction, and re-apply
this exact rule. That is an experiment, not a re-interpretation: if the in-support fraction clears 0.25 with at
least 30 positives, the frozen bands at 0.55/0.65 decide a transfer verdict; if it does not, "not testable with this
feature set" stands again, and the only remaining route is a model that does not take pool size as an input.

## Housekeeping

The feature build cost {BUILD_MIN} minutes for {E['sample']['rows_built']} rows (BM25 plus corpus QPP over
a 44,452-document pool) and is cached at `01_datasets/processed/toolret_eval_features.parquet`; `reproduce.sh` runs
this step only when that cache exists and says so otherwise, so a clean machine does not silently spend two hours and
the recorded artefact is never credited to a run that did not happen. Two interface bugs surfaced only after the
long build on the first attempt (reading the DV before the arm prefix is stripped, and treating the frozen
`scaled_pipeline` object as an sklearn `Pipeline`); both are fixed, both are silent in the cached path, and the
column-count assertion above now fails fast instead.
"""
    (P / "external_testability_exp0086.md").write_text(doc86, encoding="utf-8", newline="")
    if re.search(r"\|\s*-\s*\|\s*$|\bNone\b", doc86):
        raise SystemExit("ABORT: EXP-0086 document has an empty or None field")
    print(f"  wrote external_testability_exp0086.md ({len(doc86.split())} words)")

    agg = G["aggregate"]
    doc93 = f"""# The error taxonomy as a census, not a read sample (EXP-0093)

Artefact `{f93.name}`; code `02_shared_code/statistics/error_analysis_p001.py --census`; no sampling stage is
involved (the dev split and the {G['oof']} folds are fixed by the protocol); {G['wallclock_sec']}s. Same frozen model, same dev rows, same seven rules and the same first-match order as
EXP-0046 - the AUROCs and contingency tables reproduce it exactly, which is the point of re-running rather than
rewriting.

## Coverage

| config x kind | rows written | labels reconcile with the taxonomy |
|---|---|---|
""" + "\n".join(f"| {k} | {v['rows']} | {v['labels_reconcile']} |" for k, v in cen.items()) + f"""

**{n_rows} rows, which is every dev false negative, false positive and true positive of the three configurations.**
EXP-0046 printed 71 of these as a read sample; the census replaces that claim with a complete table
(`results_processed/EXP0093_error_census.csv`), and each row carries the quantities its rule looked at
(`bridge_tokens`, `n_candidates`, `n_gold`, `n_servers`, `n_subtasks`, `n_tokens`, the config median and 10th
percentile) next to the label, so any single classification can be checked without re-running anything.

Reconciliation is asserted in the script: the per-group label counts recomputed from the written rows must equal the
taxonomy counts the artefact reports, and the row count must equal the group size. Both checks pass for all
{len(cen)} groups.

## What the census adds to the reading

Aggregate across the three configurations:

| category | false negatives | true positives | false positives |
|---|---|---|---|
""" + "\n".join(f"| {c} | {agg['fn'][c]} | {agg['tp'][c]} | {agg['fp'][c]} |"
               for c in ["R1 no_lexical_bridge", "R2 crowded_catalogue", "R5 sibling_confusion",
                         "R3 multi_subtask_long", "R4 terse_instruction", "R7 tiny_catalogue", "R6 other"]) + f"""

The enrichment conclusion of EXP-0046 is unchanged in direction and now rests on the full population: the model's
misses are *less* likely to be lexically unreachable than its catches, and the residual category is reported at its
size rather than distributed. What the census makes possible and the sample did not: a reader can filter the table by
any rule input (for instance every false negative with a lexical bridge and more than 40 candidates) and see the
count directly instead of extrapolating from eight sampled cases per cell.
"""
    (P / "error_census_exp0093.md").write_text(doc93, encoding="utf-8", newline="")
    print(f"  wrote error_census_exp0093.md ({len(doc93.split())} words)")

    # ---- claims
    cp = P / "claims_evidence_matrix.csv"
    rows = [r for r in csv.reader(io.StringIO(cp.read_text(encoding="utf-8"))) if r]
    hdr, body = rows[0], rows[1:]
    add = {
        "C27": ["C27", "外部验证在当前特征集下不可测：419 行 ToolRet 查询目录平均 44,452 篇，冻结模型的 33 个特征中有 "
                f"{len(always)} 个（{', '.join(always)}）在 100% 的行上越出 dev 支持域，而 {never} 个特征从不越界；"
                "按预先固定的 in-support>=0.25 且正例>=30 判据，既不能声称迁移也不能声称不迁移",
                "外部效度（E08 第三次尝试）", "EXP-0086", "not testable (support exhausted)",
                f"in_support_fraction={S['in_support_fraction']} rows={S['rows']} positives_in_support="
                f"{S['positives_in_support']} auroc_prob={arms['frozen probability']['auroc_all_rows']} "
                f"auroc_lin={arms['linear predictor (no link)']['auroc_all_rows']} "
                f"mean_outside_features={S['mean_features_outside_per_row']}",
                "results_processed/EXP0086_per_feature_support.csv",
                "papers/P001_routing_failure_qpp/external_testability_exp0086.md",
                "逐特征 dev min/max 与外部值域对照；AUROC 按 prompt_id 聚类自助 2000 次；判据在算 AUROC 前固定",
                f"results_raw/{f86.name}", "6.4; limitations L24; final_audit 行",
                "reported as a measurement limit, not a transfer result"],
        "C28": ["C28", "错误剖析已从 71 例抽样判读升级为全量普查：三配置 dev 上全部假阴性/假阳性/真阳性共 "
                f"{n_rows} 行逐行落表，每行附带其规则输入量，分组标签计数与分类表逐组核对一致",
                "E15/E16 覆盖度（规范 §7）", "EXP-0093", "completes EXP-0046's read sample",
                f"groups={len(cen)} rows={n_rows} reconcile=all_true "
                f"FN_R1={agg['fn']['R1 no_lexical_bridge']} FN_R2={agg['fn']['R2 crowded_catalogue']} "
                f"FN_R6={agg['fn']['R6 other']} TP_R1={agg['tp']['R1 no_lexical_bridge']}",
                "results_processed/EXP0093_error_census.csv",
                "papers/P001_routing_failure_qpp/error_census_exp0093.md",
                "与 EXP-0046 同一冻结模型/规则/顺序；AUROC 与列联表逐值复现，另对每组做行级重算核对",
                f"results_raw/{f93.name}", "7; limitations L17; final_audit E15 行", "supported"],
    }
    changed = False
    for cid, row in add.items():
        if cid in {r[0] for r in body}:
            print(f"  claim {cid} already present - skipped")
            continue
        assert len(row) == len(hdr), (cid, len(row), len(hdr))
        body.append(row)
        changed = True
    if changed:
        cp.write_text("".join(line(x) for x in [hdr] + body), encoding="utf-8", newline="")
        print(f"  claims matrix: now {len(body)} rows")

    # ---- limitations: new L24 and the E15/E16 coverage row
    lim = P / "limitations.md"
    t = lim.read_text(encoding="utf-8")
    t = sub1(t, r"\| E15/E16 错误与个案分析（人工读样本） \|[^\n]*\n",
             "| E15/E16 错误与个案分析 | **已做（EXP-0046 规则全量 + EXP-0093 逐行普查）** | "
             f"三配置 dev 上全部 {n_rows} 个 FN/FP/TP 逐行落表并附规则输入量，分组计数与分类表核对一致；"
             "原先的 71 例抽样判读被替换为可过滤的全量表（见 L17 与 `error_census_exp0093.md`）|\n",
             "E15 row", marker="EXP-0093 逐行普查")
    lim.write_text(t, encoding="utf-8", newline="")
    # The section number is taken from the file when the section is already there: deriving `max+1` on every run and
    # keying the guard on it is how this recorder appended a second identical L25 the first time it was re-run.
    LKEY = "该池规模上不可测"
    have = re.search(r"^## L(\d+).*" + LKEY, t, re.M)
    nl = int(have.group(1)) if have else max({int(x) for x in re.findall(r"^## L(\d+)", t, re.M)} | {0}) + 1
    appender(lim, f"""
## L{nl} 外部验证：不是"不迁移"，而是"这套特征在该池规模上不可测"（EXP-0086）

冻结模型有 {len(pdf)} 个特征，其中 {len(always)} 个（{', '.join('`%s`' % f for f in always)}）在 419 行外部查询上
100% 越出 dev 支持域——两者都是目录规模的函数（dev 目录约 4–70 篇，外部池固定为
{E['sample']['mean_n_candidates']:,.0f} 篇），而 {never} 个特征从不越界。按在算 AUROC 之前固定的判据
（in-support 比例 ≥ {E['rules_fixed_before_any_auroc']['in_support_min_fraction']} 且正例 ≥ 30），此处的正确结论是
**不可测**：迁移与不迁移都不成立。两点必须同时写明：(i) 全 33 特征"同时落在域内"的联合判据在高维下本身就苛刻，
逐特征边际表已公开，读者可自行判断该池的外推程度；(ii) 判据未因结果放宽。真正可执行的下一步是把外部候选池缩到
dev 目录规模（含金标注、同一批查询）后重跑同一判据——那是新实验，不是对旧数字的重新解释。见
`external_testability_exp0086.md`、C27、EXP-0086。
""", f"limitations L{nl}", guard=LKEY)

    # ---- final audit: the external-validation row
    fa = P / "final_audit.md"
    t = fa.read_text(encoding="utf-8")
    t = sub1(t, r"\| cross-dataset external validation \|[^\n]*\n",
             "| cross-dataset external validation | **OPEN - measured as NOT TESTABLE (EXP-0086)** | three external "
             "readings now exist and none supports a transfer claim: EXP-0082's 0.6536 was mined-negative-dependent, "
             "EXP-0084's 0.4671 came from a saturated probability (EXP-0085), and EXP-0086 shows the frozen feature "
             f"set leaves the dev support on {S['rows']}/{S['rows']} eval rows because two inputs are pool-size "
             "functions. The gate therefore does not read 'does not transfer'; it reads untested at this scale, with "
             "a concrete next test (size-matched pools). `external_testability_exp0086.md`, C27, L"
             f"{nl} |\n",
             "external gate row", marker="NOT TESTABLE (EXP-0086)")
    t = sub1(t, r"\| error analysis \|[^\n]*\n",
              "| error analysis | COMPLETE as a census (EXP-0093) | every dev FN/FP/TP row classified with its "
              f"rule inputs attached ({n_rows} rows across 3 configs), labels reconciled group by group | "
              "`error_census_exp0093.md`, C28 |\n",
              "E15 audit row", marker="COMPLETE as a census")
    fa.write_text(t, encoding="utf-8", newline="")

    # ---- deviations, content-keyed
    dv = P / "deviations.md"
    t = dv.read_text(encoding="utf-8")
    if "EXP-0086" not in t:
        used_d = {int(x) for x in re.findall(r"^\| D(\d+) \|", t, re.M)}
        for g in (ROOT / "papers").glob("*/deviations.md"):
            if g != dv:
                used_d |= {int(x) for x in re.findall(r"^\| D(\d+) \|", g.read_text(encoding="utf-8"), re.M)}
        d1 = max(used_d | {0}) + 1
        d2 = d1 + 1
        t = t.rstrip() + "\n" + (
            f"| D{d1} | {NOW} | EXP-0086 登记为外部验证的第三次测量，结论为「不可测」，并把两条接口缺陷的修复记入 | "
            f"EXP-0085 证明饱和概率下的 AUROC 读不得，故按预先固定的 in-support 判据重测：{S['rows']} 行全部越出联合支持域，"
            f"{len(always)} 个池规模特征 100% 越界，{never} 个从不越界。首跑在 108 分钟特征构建之后才因 DV 列名前缀与 "
            "`scaled_pipeline` 返回自定义 Pre（非 sklearn Pipeline）报错，两处已修并加列数断言；特征缓存改为显式依赖 | "
            "否（未改判据、模型或冻结特征；未给出迁移结论） | "
            f"后果：新增 C27 与 L{nl}、外部门槛行改写为 NOT TESTABLE，下一步实验（等规模候选池）明确列出 |\n"
            f"| D{d2} | {NOW} | EXP-0046 的 71 例抽样判读升级为 EXP-0093 全量普查 | 规范要求 E15/E16 错误与个案分析具备"
            f"覆盖度；同一冻结规则与模型在 dev 行集上逐行落表（{n_rows} 行），分组标签计数与分类表核对一致，且每行附规则输入 | "
            "否（EXP-0046 的 AUROC、列联表与富集结论逐值复现，未改任何阈值） | "
            "后果：新增 C28 与 `error_census_exp0093.md`；limitations 的 E15 行与 final_audit 相应行改为「普查已完成」|\n")
        dv.write_text(t, encoding="utf-8", newline="")
        print(f"  deviations: appended D{d1}, D{d2}")

    # ---- registry
    rp = ROOT / "00_program_registry" / "experiment_registry.csv"
    rrows = [r for r in csv.reader(io.StringIO(rp.read_text(encoding="utf-8"))) if r]
    rhdr, rbody = rrows[0], rrows[1:]

    def add9(exp, stage, script, cfg, status, outputs, notes, started, enters, seed):
        if exp in {r[0] for r in rbody}:
            print(f"  registry: {exp} already present - skipped")
            return
        rec = dict.fromkeys(rhdr, "")
        rec.update({"exp_id": exp, "paper_id": "P001", "topic_id": "T001", "stage": stage, "script": script,
                    "config": cfg, "seed": str(seed), "started_at": started, "finished_at": NOW,
                    "status": status, "outputs": outputs, "notes": notes, "enters_paper": enters})
        rbody.append([rec[x] for x in rhdr])

    add9("EXP-0086", "e08_support_respecting_external_test",
         "02_shared_code/statistics/toolret_support_respecting_external.py",
         f"same dev-fitted frozen model and frozen {len(pdf)}-feature set, nothing refitted; {S['rows']} ToolRet eval "
         f"queries with catalogues above the inclusion floor (mean {E['sample']['mean_n_candidates']:,.0f} docs); "
         "in-support = every feature inside the dev min/max; rule fixed before any AUROC: fraction >= 0.25 and >= 30 "
         "positives, bands 0.55/0.65 unchanged",
         f"NOT TESTABLE: in-support {S['in_support_fraction']} (0 rows), {len(always)} pool-size features outside on "
         f"100% of rows, {never} features never outside",
         f"results_raw/{f86.name}; results_processed/EXP0086_per_feature_support.csv; "
         "papers/P001_routing_failure_qpp/external_testability_exp0086.md; "
         "01_datasets/processed/toolret_eval_features.parquet",
         "settles the external question as a measurement limit rather than a verdict; names the size-matched-pool "
         "follow-up; the 108-minute feature build is cached and reproduce.sh only runs the step when the cache exists",
         E["started_at"], "yes - claim C27, limitations L" + str(nl) + ", final_audit external-validation row",
         E["seed"])
    add9("EXP-0093", "e15_error_analysis_census",
         "02_shared_code/statistics/error_analysis_p001.py --census",
         "identical frozen model (all_C0.1), identical seven rules and first-match order, dev rows only, "
         "GroupKFold(5) by prompt_id; every FN/FP/TP written instead of 8 per cell; per-group label counts asserted "
         "against the taxonomy counts",
         f"CENSUS COMPLETE: {n_rows} rows over {len(cen)} config x kind groups, all reconciled",
         f"results_raw/{f93.name}; results_processed/EXP0093_error_census.csv; "
         f"results_processed/EXP0093_{'error_taxonomy' if (ROOT / 'results_processed' / 'EXP0093_error_taxonomy.csv').is_file() else 'error_census'}.csv; "
         "papers/P001_routing_failure_qpp/error_census_exp0093.md",
         "replaces EXP-0046's 71-case read sample with complete coverage; AUROCs and contingency tables reproduce "
         "EXP-0046 exactly, so the census adds coverage rather than changing any number",
         G["started_at"], "yes - claim C28, limitations E15 row, final_audit E15 row",
         "n/a (deterministic: fixed split and folds, no sampling stage)")
    rp.write_text("".join(line(x) for x in [rhdr] + rbody), encoding="utf-8", newline="")
    chk = [r for r in csv.reader(io.StringIO(rp.read_text(encoding="utf-8"))) if r]
    print(f"  registry rows={len(chk) - 1} ragged={sum(1 for r in chk[1:] if len(r) != len(chk[0]))}")

    # ---- reproduce.sh: source-maintained, so verify and patch with exact anchors
    sh = P / "reproduce.sh"
    s = sh.read_text(encoding="utf-8")
    if "EXP-0093" not in s:
        anchor = '"$PY" 02_shared_code/statistics/error_analysis_p001.py\n'
        if s.count(anchor) != 1:
            raise SystemExit(f"ABORT: reproduce.sh anchor matched {s.count(anchor)}x")
        s = s.replace(anchor, anchor + '''
echo "[repro] 13/14 error analysis as a census (EXP-0093, dev only; the same frozen rules on every case)"
"$PY" 02_shared_code/statistics/error_analysis_p001.py --census

echo "[repro] 14/14 E08 support-respecting external test (EXP-0086)"
# The feature build costs ~108 min over a 44,452-document pool, so it is cached. Without the cache this step is
# reported as skipped rather than spending two hours or, worse, passing on a stale artefact it never rebuilt.
if [ -f 01_datasets/processed/toolret_eval_features.parquet ]; then
  "$PY" 02_shared_code/statistics/toolret_support_respecting_external.py --rows 420
else
  echo "[repro] 14 SKIPPED: no feature cache. Build it with the same command (it writes the cache itself)."
fi

''')
        sh.write_text(s, encoding="utf-8", newline="")
        print("  reproduce.sh: census + cached external test wired in")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
