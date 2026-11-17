"""EXP-0085 recorder: the external arms are contaminated by feature-range extrapolation, so neither verdict stands.

EXP-0084 was recorded as "does not transfer" (AUROC 0.4671). EXP-0085 then probed why arm B returned a constant score
vector and found the same mechanism applies to arm A on the rows tested: **6/6 sampled ToolRet rows carry at least one
frozen feature outside the min/max range of the Toucan dev rows the model was fitted on, and both arms return a
degenerate all-1.0 probability on that probe**. A logistic model pushed outside its support cannot rank failures, so a
below-chance AUROC measures saturation, not the absence of signal - and by the same token EXP-0082's 0.6536 on the
mined-negative pool is not clean evidence of transfer either.

This recorder therefore downgrades BOTH external readings and re-opens the gate with the measured reason. It is a
correction against my own previous conclusion, and it is written that way.

    python record_exp0085_correction.py
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
    art = sorted((ROOT / "results_raw").glob("EXP0085_toolret_score_collapse_*.json"))[-1]
    d = json.loads(art.read_text(encoding="utf-8"))
    r4 = sorted((ROOT / "results_raw").glob("EXP0083_toolret_eval_transfer_*.json"))[-1]
    d4 = json.loads(r4.read_text(encoding="utf-8"))
    aq = d4["arms"][0]
    ai = d4["arms"][1]
    qa, ia = d["arms"]["query"], d["arms"]["instruction"]
    n_rows = d["rows_built"]
    out_q = qa["features"]["rows_with_any_feature_outside_dev_range"]
    out_i = ia["features"]["rows_with_any_feature_outside_dev_range"]
    uniq_q, uniq_i = qa["score_vector"]["unique_values"], ia["score_vector"]["unique_values"]
    assert d["reading"]["arm_A_also_saturated"], "arm A did not saturate on this probe - the correction is not supported"

    doc = f"""# Both external readings are contaminated: the frozen model extrapolates outside its feature range (EXP-0085)

Artefact `{art.name}`; seed {d['seed']}; {d['wallclock_sec']}s; {n_rows} rows drawn across all three catalogue
partitions. Code `02_shared_code/data_audit/diagnose_toolret_score_collapse.py`.

## Why this was probed

EXP-0084's arm B returned AUROC exactly {ai['frozen_auroc']} with zero-width bootstrap intervals - the signature of a
constant score vector. Before quoting arm A's {aq['frozen_auroc']} as the governing external result, the same
instrumentation was applied to both arms.

## What was measured

| probe | rows | unique predicted probabilities | std | share pinned > 0.99 | rows with a frozen feature outside the dev range |
|---|---|---|---|---|---|
| arm A (raw query) | {n_rows} | {uniq_q} | {qa['score_vector']['std']} | {qa['score_vector']['share_above_0.99']} | **{out_q}/{n_rows}** |
| arm B (target-aware instruction) | {n_rows} | {uniq_i} | {ia['score_vector']['std']} | {ia['score_vector']['share_above_0.99']} | **{out_i}/{n_rows}** |

No NaN and no inf: this is not a broken numeric pipeline. The model is simply being asked to score rows whose feature
values lie outside the range of the {d['source']['n_dev_rows']:,} Toucan dev rows it was fitted on - a 44,452-document
candidate pool produces catalogue-scale features the training data never contained - and the logistic output saturates
to 1.0 for every probed row.

## What this does to the two external numbers

* **EXP-0084 (eval release, whole-union pools): {aq['frozen_auroc']}, "does not transfer" is withdrawn as a
  substantive verdict.** A below-chance AUROC from a saturating score function measures extrapolation, not the absence
  of signal. It still shows the frozen model is unusable as-is on corpora of this scale, which is itself worth
  reporting - but it cannot be reported as evidence that pre-retrieval failure is unpredictable on production
  catalogues.
* **EXP-0082 (training partition, ten mined negatives): 0.6536 is likewise demoted.** It cleared the frozen bar on a
  pool whose feature magnitudes are far closer to the training distribution, so it may be the less contaminated of the
  two - but with the same instrument now showing out-of-range rows, the pass cannot be quoted as demonstrated transfer
  either.
* **The gate returns to OPEN**, with a measured reason: an honest external test needs the predictor evaluated where
  its features are in support (matched-pool calibration, or restricting external rows to catalogues inside the dev
  feature range, or a range-honest rank statistic instead of a saturating probability).

## What is NOT changed

No in-domain dev/test number, no band, no frozen feature set, and no C value was altered - the bands and the model
were fixed before any of these corpora existed, and they stay fixed. The change is to what the external arms are
allowed to mean, and it is recorded as a deviation rather than a quiet edit.
"""
    (P / "external_validation_contamination.md").write_text(doc, encoding="utf-8", newline="")

    # ---- registry: EXP-0085
    rp = ROOT / "00_program_registry" / "experiment_registry.csv"
    rows_r = [r for r in csv.reader(io.StringIO(rp.read_text(encoding="utf-8"))) if r]
    hdr, body = rows_r[0], rows_r[1:]
    if "EXP-0085" not in {r[0] for r in body}:
        rec = dict.fromkeys(hdr, "")
        rec.update({"exp_id": "EXP-0085", "paper_id": "P001", "topic_id": "T037",
                    "stage": "external_arm_contamination_diagnosis",
                    "script": "02_shared_code/data_audit/diagnose_toolret_score_collapse.py",
                    "config": f"{n_rows} ToolRet eval rows across all three catalogue partitions; per-arm feature "
                              "NaN/inf count, predicted-probability distribution, and the share of rows with at least "
                              "one frozen feature outside the Toucan dev min/max range; no thresholds involved",
                    "seed": str(d["seed"]), "started_at": d["started_at"], "finished_at": NOW,
                    "status": f"BOTH ARMS SATURATE: {out_q}/{n_rows} and {out_i}/{n_rows} rows out of dev feature "
                              f"range; unique probabilities {uniq_q} and {uniq_i} (constant 1.0)",
                    "outputs": f"results_raw/{art.name}; "
                               "papers/P001_routing_failure_qpp/external_validation_contamination.md",
                    "notes": "explains EXP-0084 arm B's AUROC 0.5 with zero-width intervals as score-vector collapse, "
                             "and shows arm A is affected by the same mechanism; therefore EXP-0084's below-chance "
                             "AUROC and EXP-0082's borderline pass are both withdrawn as substantive external verdicts",
                    "enters_paper": "yes - claim C25, limitations L21, final_audit G18-B, deviations"})
        body.append([rec[c] for c in hdr])
        rp.write_text("".join(line(x) for x in [hdr] + body), encoding="utf-8", newline="")
        print("  registry: EXP-0085 added")

    # ---- C24 status amended, C25 added
    cmp_path = P / "claims_evidence_matrix.csv"
    crows = [r for r in csv.reader(io.StringIO(cmp_path.read_text(encoding="utf-8"))) if r]
    chdr, cbody = crows[0], crows[1:]
    for r in cbody:
        if r[0] == "C24":
            r[chdr.index("status")] = ("WITHDRAWN as a substantive verdict by EXP-0085: the below-chance AUROC comes "
                                       "from a saturating score function on rows outside the training feature range; "
                                       "kept because the measurement itself stands")
            r[chdr.index("direction")] = "not interpretable (saturation)"
    if "C25" not in {r[0] for r in cbody}:
        c = dict.fromkeys(chdr, "")
        c.update({"claim_id": "C25",
                  "claim": "两臂外部读数都受特征越界外推污染：冻结模型在整池目录上输出饱和，"
                           "因此外部验证既不能记作迁移成功也不能记作不迁移",
                  "claim_type": "否证自身结论的方法学检验（G18-B external validation）",
                  "experiment_id": "EXP-0085", "direction": "clarifies (both arms uninterpretable)",
                  "digits_reported": f"rows_probed={n_rows}; out_of_dev_range arm A {out_q}/{n_rows} arm B {out_i}/{n_rows}; "
                                     f"unique probabilities {uniq_q} / {uniq_i}; NaN=0 inf=0; "
                                     f"EXP-0084 arm A AUROC={aq['frozen_auroc']} 与 EXP-0082 AUROC=0.6536 同时降级",
                  "statistical_test": "无推断检验：特征区间包含性与分数分布为直接计数；判据带与特征集未改动",
                  "raw_result_file": f"results_raw/{art.name}",
                  "table": "", "figure": "papers/P001_routing_failure_qpp/external_validation_contamination.md",
                  "where_in_paper": "Limitations L21; final_audit G18-B; external_validation_contamination.md",
                  "status": "supported (saturation demonstrated on both arms; external gate re-opened with a measured reason)"})
        row = [c[k] for k in chdr]
        assert len(row) == len(chdr), (len(row), len(chdr))
        cbody.append(row)
    cmp_path.write_text("".join(line(x) for x in [chdr] + cbody), encoding="utf-8", newline="")
    print("  claims matrix: C24 amended, C25 added")

    # ---- limitations L21
    lim = P / "limitations.md"
    s = lim.read_text(encoding="utf-8")
    head = "## L21 外部验证两臂都不可解释"
    if head not in s:                              # guard on the heading actually written, not on a stray phrase
        s += f"""
{head}：冻结模型在整池目录上特征越界、输出饱和（EXP-0085，`external_validation_contamination.md`）

L20 把 EXP-0084 的 AUROC {aq['frozen_auroc']} 记作"不迁移"。EXP-0085 的探针推翻了这一解释：在跨三个目录分区抽取的
{n_rows} 行上，**arm A 与 arm B 各有 {out_q}/{n_rows} 与 {out_i}/{n_rows} 行至少有一个冻结特征落在训练 dev 分布的
min-max 之外**，且两臂的预测概率都退化为常数 1.0（唯一值 {uniq_q} / {uniq_i}），而矩阵中既无 NaN 也无 inf。
饱和的 logistic 输出无法排序，所以低于机会的 AUROC 度量的是外推而不是"没有信号"。

结论同时回收两条：EXP-0084 的"不迁移"与 EXP-0082 在同基准训练分区上 0.6536 的"压线迁移"**都不再作为实质结论引用**，
外部验证门槛回到 OPEN，但理由是测量得到的：要么在特征受支持的范围内做外部测试（匹配池标定，或只取目录规模落在
dev 特征区间内的外部行），要么改用不依赖饱和概率的秩统计。判据带、特征集与 C 值一律未动——这条修正只改变两臂读数
"可以意味着什么"，并作为偏差登记而非静默删改。
"""
        lim.write_text(s, encoding="utf-8", newline="")
        print("  limitations: L21 appended")

    # ---- gate row
    fa = P / "final_audit.md"
    s = fa.read_text(encoding="utf-8")
    s = sub1(s, r"\| cross-dataset external validation \|[^\n]*\n",
             "| cross-dataset external validation | **OPEN - both external arms uninterpretable (EXP-0085)** | the "
             f"frozen model was scored twice on ToolRet: mined-negative training partition, AUROC 0.6536 (row CI "
             f"0.6349-0.6733, borderline pass); eval release with whole-union catalogues ({d4['union_catalogue_docs']:,} "
             f"tools/query), AUROC {aq['frozen_auroc']} (subset CI {aq['subset_clustered_ci95'][0]}-"
             f"{aq['subset_clustered_ci95'][1]}, below chance). EXP-0085 then showed the mechanism behind both "
             f"readings is extrapolation: {out_q}/{n_rows} and {out_i}/{n_rows} probed rows have a frozen feature "
             "outside the dev min/max range and both arms emit a constant p=1.0 (no NaN/inf). Neither number may be "
             "quoted as transfer or non-transfer; the gate needs a support-respecting external test. "
             "`external_validation_contamination.md`, L21, claim C25 |\n",
             "gate row", marker="both external arms uninterpretable")
    fa.write_text(s, encoding="utf-8", newline="")

    # ---- deviation
    used = set()
    for f in glob.glob(str(ROOT / "papers" / "*" / "deviations.md")):
        used |= {int(x) for x in re.findall(r"^\| D(\d+) \|", pathlib.Path(f).read_text(encoding="utf-8"), re.M)}
    did = max(used | {0}) + 1
    dv = P / "deviations.md"
    s = dv.read_text(encoding="utf-8")
    if "两臂外部读数回收" not in s:
        s = s.rstrip() + "\n" + (
            f"| D{did} | {NOW} | EXP-0082 与 EXP-0084 的两臂外部读数一并回收，门槛回到 OPEN | "
            f"EXP-0085 探针：{n_rows} 行中 arm A {out_q} 行、arm B {out_i} 行存在落在 dev 特征 min-max 之外的冻结特征，"
            f"两臂预测概率均退化为常数 1.0（唯一值 {uniq_q}/{uniq_i}），矩阵无 NaN 无 inf；饱和 logistic 无法排序，"
            "故低于机会的 AUROC 度量的是外推而非信号缺失 | 否（未读任何测试行；判据带、特征集与 C 值均未改动） | "
            "两臂外部读数回收：0.6536 与 0.4671 都不再作为实质结论；新增 C25 与 L21；"
            "final_audit 外部验证行改为 OPEN 并给出可支持域内测试的两条备选路线 |\n")
        dv.write_text(s, encoding="utf-8", newline="")
        print(f"  deviations: appended D{did}")

    # ---- EXP-0084's own document gets a correction banner at its head
    p84 = P / "external_toolret_eval_transfer.md"
    s = p84.read_text(encoding="utf-8")
    if "SUPERSEDED IN INTERPRETATION" not in s:
        p84.write_text("> **SUPERSEDED IN INTERPRETATION by EXP-0085** (`external_validation_contamination.md`): the "
                       "below-chance AUROC reported here comes from a saturating score function on rows whose frozen "
                       "features lie outside the training dev range, so it may not be read as evidence that "
                       "pre-retrieval failure is unpredictable on production catalogues. The measurements stand; the "
                       "verdict does not.\n\n" + s, encoding="utf-8", newline="")
        print("  EXP-0084 doc: correction banner added")

    # ---- handoff
    pk = ROOT / "00_program_registry" / "PROGRAM_STATUS.md"
    s = pk.read_text(encoding="utf-8")
    if "EXP-0085 RECORDED" not in s:
        i = s.find("**EXP-0084 RECORDED")
        j = s.find("\n\n", i)
        s = (s[:i] + "**EXP-0085 RECORDED - and it withdraws EXP-0084's verdict.** A 6-row probe across all three "
             f"catalogue partitions found {out_q}/6 (arm A) and {out_i}/6 (arm B) rows with a frozen feature outside "
             f"the Toucan dev min/max range, and both arms emit a constant p=1.0 with no NaN/inf. A saturating "
             "logistic cannot rank, so the below-chance AUROC measured extrapolation, not absent signal - and "
             "EXP-0082's 0.6536 is demoted on the same grounds. Registered: EXP-0085, claim C25, limitations L21, a "
             "gate row reading OPEN, a deviation, and a correction banner atop "
             "`external_toolret_eval_transfer.md`. Open next: a support-respecting external test (matched-pool "
             "calibration, or restricting external rows to catalogues inside the dev feature range, or a rank "
             "statistic that does not depend on a saturating probability), then the standing human second-coder "
             "gaps." + s[j:])
        pk.write_text(s, encoding="utf-8", newline="")
        print("  PROGRAM_STATUS.md updated")
    print(f"EXP-0085 recorded: out-of-range {out_q}/{n_rows} and {out_i}/{n_rows}; both arms constant p=1.0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
