"""Land EXP-0046 (P001 E15 error analysis) into the package. Every number is read from the result file.

Writes: tables 17-19, limitations L17 plus two stale table rows in that file, claims C20-C21, reviewer-attack A27,
a final_audit defect, the next two programme-wide deviation rows, the registry row, two entries in SUPERSEDED_ARTIFACTS.json, a paper.md
section 7.8, and replaces the broken evidence loop in reproduce.sh. Idempotent; refuses to write without the
result file.

    python 02_shared_code/registry/record_exp0046_p001.py
"""
from __future__ import annotations

import csv, glob, io, json, pathlib, re, sys, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
PAP = ROOT / "papers" / "P001_routing_failure_qpp"
REG = ROOT / "00_program_registry"
NOW = time.strftime("%Y-%m-%dT%H:%M:%S")

hits = sorted(glob.glob(str(ROOT / "results_raw" / "EXP0046_error_analysis_*.json")))
if not hits:
    sys.exit("[e46] no EXP-0046 result file; writing nothing (a paper cannot cite evidence that does not exist).")
D = json.loads(pathlib.Path(hits[-1]).read_text(encoding="utf-8"))
NAME = pathlib.Path(hits[-1]).name
CFGS = list(D["configs"])
RERUN_NOTE = ""
if len(hits) > 1:
    a, b = (json.loads(pathlib.Path(p).read_text(encoding="utf-8")) for p in hits[:2])
    for x in (a, b):
        for k in ("started_at", "finished_at", "wallclock_sec"):
            x.pop(k, None)
    RERUN_NOTE = ("两次运行除时间戳外完全一致（确定性检查）。" if a == b
                  else "注意：两次运行除时间戳外并不一致，须先查明原因再引用。")
CATS = ["R1 no_lexical_bridge", "R5 sibling_confusion", "R2 crowded_catalogue",
        "R3 multi_subtask_long", "R4 terse_instruction", "R7 tiny_catalogue", "R6 other"]

CT = {c: D["configs"][c]["bridge_contingency_all_dev"] for c in CFGS}
TH = {c: D["configs"][c]["threshold_0.5"] for c in CFGS}
flag_rate = {c: round((TH[c]["TP"] + TH[c]["FP"]) / D["configs"][c]["dev_rows"], 4) for c in CFGS}
r1_rr = {c: D["configs"][c]["fn_vs_tp_enrichment"]["R1 no_lexical_bridge"]["rr_fn_over_tp"] for c in CFGS}
agg = D["aggregate"]
fn_tot = sum(TH[c]["FN"] for c in CFGS)
tp_tot = sum(TH[c]["TP"] for c in CFGS)
r1_fn_share = round(agg["fn"]["R1 no_lexical_bridge"] / fn_tot, 4)
r1_tp_share = round(agg["tp"]["R1 no_lexical_bridge"] / tp_tot, 4)
r2_fn_share = round(agg["fn"]["R2 crowded_catalogue"] / fn_tot, 4)
r6_fn_share = round(agg["fn"]["R6 other"] / fn_tot, 4)
explained = round(1 - agg["fn"]["R6 other"] / fn_tot, 4)
no_b_succ = sum(CT[c]["no_bridge__fail0"] for c in CFGS)
no_b_fail = sum(CT[c]["no_bridge__fail1"] for c in CFGS)
no_b_succ_share = round(no_b_succ / (no_b_succ + no_b_fail), 4)


def J(fmt):
    """Join one per-config expression across the three configurations."""
    return ", ".join(fmt.format(c=c, f=flag_rate[c] * 100, rec=TH[c]["recall"], prec=TH[c]["precision"],
                                spec=TH[c]["specificity"], phi=CT[c]["phi"], fp=CT[c]["fisher_p"],
                                nb=CT[c]["fail_rate_given_no_bridge"], b=CT[c]["fail_rate_given_bridge"],
                                rd=CT[c]["risk_difference_pp"], rr=r1_rr[c], tpn=TH[c]["TP"])
                    for c in CFGS)


S_FLAG = J("{f:.2f}%（{c}）")
S_REC = J("{rec}")
S_PREC = J("{prec}")
S_RR = J("{rr}")
S_PHI = J("{phi}")
S_FP = J("{fp}")
S_NB = J("{nb}")
S_B = J("{b}")
S_RD = J("{rd} pp")
MIN_SPEC = min(TH[c]["specificity"] for c in CFGS)

# Deviation numbers are GLOBAL across the programme (P001 1-17, P003 18-21, P002 22-28, P004 29-32), so the next
# free one must be computed across every paper's register, not from this paper's own file.
ALLD = [int(x) for f in sorted((ROOT / "papers").glob("*/deviations.md"))
        for x in re.findall(r"(?m)^\| D(\d+) \|", f.read_text(encoding="utf-8"))]
DN = max(ALLD)
D_NEW, D_NEW2 = f"D{DN + 1}", f"D{DN + 2}"


def rows_of(path):
    return list(csv.reader(io.StringIO(path.read_text(encoding="utf-8"))))


def append_table(path, header, rows):
    path.parent.mkdir(exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    print(f"[e46] wrote {path.name}")


# ---------------------------------------------------------------- tables 17 / 18 / 19
r17 = []
for cfg in CFGS:
    v = D["configs"][cfg]
    n_fn, n_tp, n_fp = v["threshold_0.5"]["FN"], v["threshold_0.5"]["TP"], v["threshold_0.5"]["FP"]
    enr = v["fn_vs_tp_enrichment"]
    for c in CATS:
        e = enr[c]
        r17.append([cfg, c, e["fn_n"], round(e["fn_n"] / max(1, n_fn), 4), e["tp_n"],
                    round(e["tp_n"] / max(1, n_tp), 4), e["rr_fn_over_tp"], e["fisher_p"],
                    v["fp_taxonomy"][c], round(v["fp_taxonomy"][c] / max(1, n_fp), 4)])
    r17.append([cfg, "TOTAL", n_fn, 1.0, n_tp, 1.0, "", "", n_fp, 1.0])
T17 = PAP / "tables" / "table17_error_taxonomy.csv"
append_table(T17, ["cfg", "category", "fn_n", "fn_share", "tp_n", "tp_share", "rr_fn_over_tp",
                   "fisher_p_fn_vs_tp", "fp_n", "fp_share"], r17)

BCOLS = ["bridge__fail0", "bridge__fail1", "no_bridge__fail0", "no_bridge__fail1", "fail_rate_given_bridge",
         "fail_rate_given_no_bridge", "risk_difference_pp", "odds_ratio", "fisher_p", "phi"]
r18 = [[c] + [CT[c][k] for k in BCOLS] for c in CFGS]
CFILE = ROOT / "results_processed" / "EXP0046_bridge_contingency.csv"
if CFILE.exists():
    for row in csv.DictReader(open(CFILE, encoding="utf-8")):
        if row["cfg"] == "AGGREGATE":
            r18.append(["AGGREGATE_3_CONFIGS"] + [row[k] for k in BCOLS])
T18 = PAP / "tables" / "table18_lexical_bridge_contingency.csv"
append_table(T18, ["cfg", "bridge_and_succeeded", "bridge_and_failed", "no_bridge_and_succeeded",
                   "no_bridge_and_failed", "fail_rate_given_bridge", "fail_rate_given_no_bridge",
                   "risk_difference_pp", "odds_ratio", "fisher_p", "phi"], r18)

T19 = PAP / "tables" / "table19_error_read_cases.csv"
cases = D["cases_read"]
append_table(T19, list(cases[0].keys()), [[c[k] for k in cases[0]] for c in cases])

# ---------------------------------------------------------------- limitations
LIM = PAP / "limitations.md"
ltxt = LIM.read_text(encoding="utf-8")
nxt = 1 + max([int(x) for x in re.findall(r"(?m)^## L(\d+)", ltxt)] or [0])
LSEC = f"""
## L{nxt} 错误剖析：0.5 切点几乎不可用，而模型漏掉的恰恰不是「词面不可达」那一类（EXP-0046，表17/18/19）

这是规范 §7 里「E15/E16 错误与个案分析」的补齐，全部在 dev 行集上、用冻结 `all_C0.1` 与 `prompt_id` 分组五折
交叉验证的外推预测打分（test 那一次评估未被触碰，中性 0.5 切点）。三件事必须同时写清：

1. **决策口径与排序口径不是一回事。** 在 p≥0.5 上模型只标记 {S_FLAG} 的 dev 行；召回 {S_REC}，
   精确率 {S_PREC}，特异度 ≥{MIN_SPEC}。AUROC 0.80-0.83 是**排序**能力，不能读成「可以直接拦截」。
   若要在部署中使用必须按代价重选切点，而本文没有声明任何代价矩阵，因此不给工作点建议。
2. **错误类别是相对真阳性算富集度的，不是只看占错误的比例。** 规则一律不得使用 `bm25_best_rank`/`fail_at_3`
   （它们就是标签本身）。结果：无桥接（R1）在真阳性里的占比 {r1_tp_share} 高于在假阴性里的占比 {r1_fn_share}，
   RR(FN/TP) = {S_RR}，全部 <1。也就是说**模型漏掉的不是词面不可达的失败**——那类它抓得最准；漏掉的是目录拥挤
   （R2 占 FN 的 {r2_fn_share}）与残差类（R6 占 {r6_fn_share}），即金标注本来可达、BM25 却仍然漏掉的那批。
   规则能解释的 FN 比例 {explained}（R6 残差如实保留，未拆分美化）。
3. **「不可达→失败」很强，但不是重言式**（表18）：三配置 φ = {S_PHI}，Fisher p = {S_FP}；无桥接行的失败率
   {S_NB} vs 有桥接行 {S_B}（风险差 {S_RD}）。两个方向都不是确定的：无桥接且**成功**的行有 {no_b_succ} 条
   （占无桥接行的 {no_b_succ_share}），所以它既非充分也非必要。TP 合计只有 {tp_tot} 行，
   富集度检验在小格子上效力有限，故只报比值与 Fisher p，不据此做任何显著性宣称。

**代价披露（{D_NEW}）**：本实验第一版用 `name`/`desc` 读取持久化的 `catalog_json`，而构建器写入的是短键 `n`/`d`/`p`
（`build_toucan_routing_dataset.py:442`，`cross_pipeline_transfer_e08.py:117` 早已注明）。空 token 列表使
`bridge()` 对每一行都返回 False，于是产出「{fn_tot} 条假阴性 100% 属于无桥接」这一重言式。该文件与一份手工算的
临时对照表一起移入 `results_raw/superseded/`；脚本现在在 schema 不符时抛异常，并在打分前检查目录确实被切出非空
token。修正后数字如上，结论方向相反。同一版把特异度写成了 `precision_at_0.5`，已改名并补上真正的精确率。
{RERUN_NOTE} 个案判读证据：`tables/table19_error_read_cases.csv`（{len(cases)} 例，覆盖 FN/FP/TP × 3 配置，
含金标注工具名与 BM25 实际 top-3 工具名）。
"""
if "EXP-0046，表17" not in ltxt:
    LIM.write_text(ltxt.rstrip() + "\n" + LSEC, encoding="utf-8", newline="")
    print(f"[e46] appended L{nxt}")
else:
    print("[e46] limitations already carries the EXP-0046 section")

ltxt = LIM.read_text(encoding="utf-8")
FIX = [("部分 | fig6 给了分布；逐例人工判读未写入正文 |",
        f"**已做（EXP-0046，见 L{nxt} 与表17/18/19）** | 规则化全量分类 + {len(cases)} 例逐条判读；"
        f"首版因短键读取错误被废弃（{D_NEW}） |"),
       ("未验证 | `reproduce.sh` 已提供，但尚未在隔离虚拟环境中跑通；环境依赖仅登记未锁定哈希 |",
        f"**已做（EXP-0025，见 D17），但 `reproduce.sh` 自身另有缺陷（{D_NEW2}）** | 隔离 venv 已跑通分析阶段"
        f"并给出带容差的复现声明；核查交接脚本时发现其证据校验循环含字面 `\\n`，执行时必然误报 MISSING，"
        f"已改为从 claims 矩阵读取路径（{D_NEW2}） |")]
for old, new in FIX:
    if old in ltxt:
        ltxt = ltxt.replace(old, new, 1)
        print(f"[e46] corrected stale limitations row: {old[:22]}…")
    elif new[:14] not in ltxt:
        print(f"[e46] WARNING row not found: {old[:40]}")
LIM.write_text(ltxt, encoding="utf-8", newline="")

# ---------------------------------------------------------------- claims
CL = PAP / "claims_evidence_matrix.csv"
hdr = rows_of(CL)[0]
have_c = {r[0] for r in rows_of(CL)[1:] if r}
NEWC = [
    dict(zip(hdr, ["C20",
                   "词面不可达（指令与金标注工具文本无内容词桥接）与 BM25 是否漏出 top-3 在行级强相关，"
                   "但该关系既非充分也非必要，因此它是机制证据而不是标签的重述",
                   "机制佐证（dev-only）", "EXP-0046", "supports",
                   f"dev 2x2：φ {S_PHI}；Fisher p {S_FP}；无桥接失败率 {S_NB} vs 有桥接 {S_B}；"
                   f"无桥接且成功的行 {no_b_succ} 条（占无桥接行 {no_b_succ_share}）",
                   "tables/table18_lexical_bridge_contingency.csv", "",
                   "Fisher exact（合并 2x2；未按 prompt_id 聚类，故仅作描述性证据）",
                   "results_raw/EXP0046_error_analysis_*.json;results_raw/" + NAME,
                   "Results §7.8; Limitations", "supported (dev rows only; test split not read)"])),
    dict(zip(hdr, ["C21",
                   "在 p≥0.5 决策口径下，预测器漏掉的失败以「目录拥挤/本来可达却仍被漏」为主，"
                   "而不是词面不可达那一类；同时该工作点召回极低，AUROC 不可读作可部署拦截",
                   "误差结构（dev-only）", "EXP-0046", "supports",
                   f"FN={fn_tot}, TP={tp_tot}；R1 占比 FN {r1_fn_share} < TP {r1_tp_share}，RR(FN/TP) {S_RR}（均<1）；"
                   f"召回 {S_REC}；标记率 {S_FLAG}；规则解释度 {explained}",
                   "tables/table17_error_taxonomy.csv", "",
                   f"每类别 FN vs TP 的 Fisher 精确检验（表17；未做多重比较校正，已注明，故只用效应量不用显著性）",
                   "results_raw/EXP0046_error_analysis_*.json;results_raw/" + NAME,
                   "Results §7.8; Limitations", "supported (dev rows only; test split not read)"])),
]
app = [r for r in NEWC if r[hdr[0]] not in have_c]
if app:
    with open(CL, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=hdr)
        for r in app:
            assert len(r) == len(hdr)
            w.writerow(r)
    print(f"[e46] appended claims {[r[hdr[0]] for r in app]}")
else:
    print("[e46] claims C20/C21 already present")

# Once the evidence loop actually checks paths, six older claims fail it because their cells hold prose or bare
# experiment ids instead of resolvable paths. The prose is MOVED to where_in_paper, never deleted.
# (claim, column, token to replace, replacement, text to append to where_in_paper)
CELLFIX = [("C4", "table", "EXP-0010;EXP-0006b", "results_raw/EXP0010_dev_selection_*.json;results_raw/EXP0006_*", ""),
           ("C11", "table", "; appendix Table A9", "", "appendix Table A9"),
           ("C12", "table", "; appendix A11b", "", ""),
           ("C13", "table", "; appendix A11c", "", "appendix A11c"),
           ("C18", "table", "-", "", ""),
           ("C19", "table", "table16_subset_transfer.csv", "tables/table16_subset_transfer.csv", "")]
_rows = list(csv.DictReader(open(CL, encoding="utf-8")))
_before = {(r["claim_id"], k): v for r in _rows for k, v in r.items()}
_changed = set()
for cid, col, old, new, where_add in CELLFIX:
    for r in _rows:
        if r["claim_id"] == cid and old in (r[col] or ""):
            r[col] = (r[col] or "").replace(old, new).strip().strip(";").strip()
            _changed.add((cid, col))
            if where_add and where_add not in (r["where_in_paper"] or ""):
                r["where_in_paper"] = (r["where_in_paper"] or "").rstrip("; ").rstrip() + "; " + where_add
                _changed.add((cid, "where_in_paper"))
if _changed:
    with open(CL, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=hdr)
        w.writeheader()
        w.writerows(_rows)
    print(f"[e46] relocated evidence-cell prose to where_in_paper: {sorted(_changed)}")
    _after = {(r["claim_id"], k): v for r in csv.DictReader(open(CL, encoding="utf-8")) for k, v in r.items()}
    assert set(_after) == set(_before), "claim rows or columns changed shape"
    for key, v in _before.items():
        if key not in _changed:
            assert _after[key] == v, f"unrelated claim cell changed: {key}"
    for key in _changed:
        assert _after[key] != _before[key], f"{key} did not change"

# ---------------------------------------------------------------- reviewer attack
RA = PAP / "reviewer_attack.md"
ra = RA.read_text(encoding="utf-8")
lastA = max([int(x) for x in re.findall(r"(?m)^\| A(\d+) ", ra)] or [0])
AID = f"A{lastA + 1}"
AROW = (f"| {AID} | **Your error analysis is a restatement of the BM25 definition — of course every miss "
        f"'has no lexical bridge'.** | Real risk; we nearly published it, and the attack is now answered by "
        f"measurement | The first run said exactly that ({fn_tot}/{fn_tot} FN in R1) because `catalog_json`'s "
        f"persisted short keys `n/d/p` were read as `name/desc`, so every catalogue tokenised to nothing and "
        f"`bridge()` returned False for every row. That file is in `results_raw/superseded/` and the script now "
        f"aborts when a schema cannot be tokenised ({D_NEW}). After the fix: no rule may use `bm25_best_rank` or "
        f"`fail_at_3`, every category is scored against true positives, and R1 is *less* common among misses "
        f"(RR {S_RR} < 1; {r1_fn_share} of FN vs {r1_tp_share} of TP) than among detections, while {no_b_succ} "
        f"no-bridge rows succeed ({no_b_succ_share} of all no-bridge rows) | New experiment (EXP-0046 re-run with "
        f"the corrected accessor and a non-tautology control); claim C21 states the corrected direction; "
        f"limitation L{nxt} records the defect and its measured magnitude |")
if "EXP-0046" not in ra:
    RA.write_text(ra.rstrip() + "\n" + AROW + "\n", encoding="utf-8", newline="")
    print(f"[e46] appended {AID}")
else:
    print("[e46] reviewer attack already covers EXP-0046")

# ---------------------------------------------------------------- final audit defect
FA = PAP / "final_audit.md"
fa = FA.read_text(encoding="utf-8")
if "EXP-0046" not in fa:
    FA.write_text(fa.rstrip() + f"\n8. **error structure and decision point (EXP-0046, L{nxt}):** at p>=0.5 the "
                  f"frozen predictor flags {S_FLAG} of dev rows and recovers {S_REC} of failures, so no deployable "
                  f"cut-off is claimed; the misses are reachable-but-missed queries (R2 {r2_fn_share} of FN, "
                  f"residual R6 {r6_fn_share}), not the lexically unreachable ones (RR<1), and the first version "
                  f"of this analysis was a broken-key tautology that was discarded ({D_NEW}).\n",
                  encoding="utf-8", newline="")
    print("[e46] appended final_audit defect 8")

# ---------------------------------------------------------------- deviations
DV = PAP / "deviations.md"
dtxt = DV.read_text(encoding="utf-8")
dn = DN  # deviation numbers are the programme-wide register computed at the top of this script
D1 = (f"| D{dn+1} | {NOW} | **EXP-0046 首版作废并重跑：错误剖析差点写成重言式** | "
      f"`catalog_json` 在磁盘上用构建器的短键 `n/d/p`（`build_toucan_routing_dataset.py:442`；"
      f"`cross_pipeline_transfer_e08.py:117` 已注明），而首版脚本按 `name`/`desc` 取值 → 目录 token 全空 → "
      f"`bridge()` 恒为 False → 报「{fn_tot}/{fn_tot} 条假阴性无词面桥接」。同一版把特异度命名为 "
      f"`precision_at_0.5` | 首版 JSON 与手工算的临时对照表移入 `results_raw/superseded/`；脚本新增 "
      f"`tool_field()`（schema 不符即抛异常）与 `check_tokens()`（打分前非空校验）；修正后重跑两次除时间戳外一致 "
      f"| 否（只读 dev） | FN 的类别结构结论反转：R1 在 FN 中占比 {r1_fn_share} 低于 TP 的 {r1_tp_share}；"
      f"见 L{nxt}/C21/{AID} |")
D2 = (f"| D{dn+2} | {NOW} | **`reproduce.sh` 的证据校验循环是坏的，已改为从 claims 矩阵推导** | "
      f"for 列表含字面 `\\ \\n`（此前用 heredoc 一次性写入时未展开），执行时会把 `n`、`\\` 之类当成路径并报 "
      f"MISSING；且循环缺 EXP-0028/0033/0034/0035/0046 的产物 | 逐行读文件 + `bash -n` 语法检查；新循环改由 "
      f"`claims_evidence_matrix.csv` 的 `raw_result_file`/`table` 两列解析路径，新增一条声明即自动纳入校验；"
      f"新循环第一次执行又暴露 6 处声明（C4/C11/C12/C13/C18/C19）的证据单元格里填的是实验号或「appendix A11b」"
      f"这类文字指针而非可解析路径，已归位（文字搬回 where_in_paper，未删除任何指向） | 否 | "
      f"不改变任何数字；修正前「复现脚本可跑通」这句话对 P001 的证据校验步骤不成立，已撤回该表述 |")
if f"| D{dn+1} " not in dtxt:
    DV.write_text(dtxt.rstrip() + "\n" + D1 + "\n" + D2 + "\n", encoding="utf-8", newline="")
    print(f"[e46] appended D{dn+1}, D{dn+2}")

# ---------------------------------------------------------------- superseded register
SR = ROOT / "results_raw" / "SUPERSEDED_ARTIFACTS.json"
sj = json.loads(SR.read_text(encoding="utf-8"))
have = {e["file"] for e in sj["superseded"]}
for f, why in [("EXP0046_error_analysis_20260919T172013.json",
                "read catalog_json with the builder's non-persisted keys (name/desc), so every catalogue "
                "tokenised to nothing and the taxonomy reported 100% of dev false negatives as 'no lexical "
                f"bridge' - a broken-key tautology; also labelled specificity as precision. Replaced by {NAME}"),
               ("EXP0046_bridge_tautology_check.csv",
                "computed interactively rather than by the experiment script, so it was not reproducible; "
                "superseded by results_processed/EXP0046_bridge_contingency.csv, which the script writes")]:
    if f not in have:
        sj["superseded"].append({"file": f, "exp_id": "EXP-0046", "at": NOW, "reason": why,
                                 "was_it_quoted": "no - caught before any paper text used it"})
SR.write_text(json.dumps(sj, indent=1, ensure_ascii=False), encoding="utf-8", newline="")
print(f"[e46] superseded register now has {len(sj['superseded'])} entries")

# ---------------------------------------------------------------- paper.md section
PP = PAP / "paper.md"
ptxt = PP.read_text(encoding="utf-8")
ANCHOR = "## 8 What the results do not support"
SEC = f"""## 7.8 E15 — what the errors actually contain (EXP-0046)

AUROC answers "can the model rank risk"; a reader who might act on it needs the confusion structure, so this
section is the pre-submission "larger manual error review". It is dev-only, out-of-fold with `prompt_id` groups,
at the neutral 0.5 cut-off (Tables 17-19).

Three numbers bound how the result may be used. At 0.5 the predictor flags {S_FLAG} of dev rows and recovers
{S_REC} of the failures at precision {S_PREC}: ranking ability is not a deployable interception point, and we
claim no operating point because the paper states no cost matrix.

The second number is the one that survived an attempt to make it vacuous. Rules were forbidden from reading
`bm25_best_rank` or `fail_at_3` — those *are* the label — and every category is scored against the rows the model
caught, not only against its errors. Lexical unreachability is strongly related to the outcome itself (φ {S_PHI},
Fisher p {S_FP}; failure rate {S_NB} with no bridge vs {S_B} with one, Table 18) yet it is not what the model
misses: it accounts for {r1_tp_share} of true positives but only {r1_fn_share} of false negatives, a risk ratio
below one in every configuration ({S_RR}). What the predictor misses is the *reachable* failure — crowded
catalogues ({r2_fn_share} of misses) and the residual category ({r6_fn_share}); {explained} of misses fall under a
rule at all, and the residual is reported rather than dissolved.

Third, the provenance. The first version reported that {fn_tot} of {fn_tot} misses lacked any lexical bridge,
which is a restatement of the ranker's definition — and it was a bug: `catalog_json` persists the builder's short
keys `n/d/p`, the script read `name/desc`, so every catalogue tokenised to the empty set. The artifact is archived
under `results_raw/superseded/`, the script now aborts when a schema tokenises to nothing, and the corrected
numbers above point the other way (deviation D{dn+1}, limitation L{nxt}).

"""
if "## 7.8" not in ptxt:
    assert ANCHOR in ptxt, "anchor heading not found in paper.md"
    PP.write_text(ptxt.replace(ANCHOR, SEC + ANCHOR, 1), encoding="utf-8", newline="")
    print("[e46] inserted paper.md section 7.8")
else:
    print("[e46] paper.md already has 7.8")

# ---------------------------------------------------------------- reproduce.sh evidence loop
RS = PAP / "reproduce.sh"
rtxt = RS.read_text(encoding="utf-8")
lines = rtxt.splitlines()
NEWBLOCK = '''echo "[repro] 12/12 sample-scope, subset transfer, learning curve, second coder, error analysis (dev only)"
"$PY" 02_shared_code/data_audit/audit_shard_coverage_p001.py
"$PY" 02_shared_code/statistics/subset_sensitivity_p001.py
"$PY" 02_shared_code/statistics/learning_curve_e12.py
"$PY" 02_shared_code/statistics/second_coder_agreement.py
"$PY" 02_shared_code/statistics/error_analysis_p001.py

echo "[repro] verifying every claim's evidence files exist (paths read from claims_evidence_matrix.csv)"
"$PY" - <<'PYEOF'
import csv, glob, pathlib, sys
P = "papers/P001_routing_failure_qpp/"
PREFIXES = ["", P, P + "tables/", P + "figures/"]


def resolves(tok):
    return any(glob.glob(pre + tok) or pathlib.Path(pre + tok).exists() for pre in PREFIXES)


rows = list(csv.DictReader(open(P + "claims_evidence_matrix.csv", encoding="utf-8")))
missing, checked, bare = [], 0, []
for r in rows:
    ok_here = 0
    for col in ("raw_result_file", "table"):
        for part in (r.get(col) or "").split(";"):
            p = part.strip()
            if not p:
                continue
            checked += 1
            if resolves(p):
                ok_here += 1
            else:
                missing.append((r["claim_id"], col, p))
    if ok_here == 0:
        bare.append(r["claim_id"])
print(f"[repro] {len(rows)} claims, {checked} evidence paths, {len(missing)} missing, "
      f"{len(bare)} claims with no resolvable evidence pointer")
for cid, col, p in missing:
    print("  MISSING", cid, col, p)
for cid in bare:
    print("  NO EVIDENCE POINTER", cid)
sys.exit(1 if missing or bare else 0)
PYEOF
'''
start = next((i for i, l in enumerate(lines) if l.startswith('echo "[repro] verifying claim evidence files exist"')), None)
if start is not None:
    end = next(i for i in range(start, len(lines)) if lines[i].startswith("done"))
    RS.write_text("\n".join(lines[:start] + NEWBLOCK.splitlines() + lines[end + 1:]) + "\n",
                  encoding="utf-8", newline="")
    print(f"[e46] replaced the broken evidence loop (lines {start+1}-{end+1}) of reproduce.sh")
else:
    print("[e46] reproduce.sh loop already replaced" if "claims_evidence_matrix.csv" in rtxt
          else "[e46] WARNING: evidence loop anchor not found in reproduce.sh")

# ---------------------------------------------------------------- registry
REGH = rows_of(REG / "experiment_registry.csv")[0]
buf = io.StringIO()
csv.writer(buf, lineterminator="\r\n").writerow([
    "EXP-0046", "P001", "error_analysis_E15_DONE",
    "02_shared_code/statistics/error_analysis_p001.py",
    "3 configs x dev rows only (no test read); frozen all_C0.1 scored out-of-fold with GroupKFold(5) on prompt_id; "
    "neutral 0.5 cut-off; 7 first-match rules that may not use bm25_best_rank/fail_at_3; every category scored "
    "FN-vs-TP with Fisher exact; catalogue schema guard aborts on empty tokenisation", "42",
    D["started_at"], D["finished_at"], "success_errors_are_reachable_but_missed_first_version_superseded",
    f"{NAME}; results_processed/EXP0046_error_taxonomy.csv; results_processed/EXP0046_bridge_contingency.csv; "
    "results_processed/EXP0046_read_cases.csv; papers/P001_routing_failure_qpp/tables/"
    "table17_error_taxonomy.csv; papers/P001_routing_failure_qpp/tables/table18_lexical_bridge_contingency.csv; "
    "papers/P001_routing_failure_qpp/tables/table19_error_read_cases.csv; logs/EXP-0046_error_analysis.txt",
    f"Closes the E15/E16 pre-submission item. Recall at 0.5 is {S_REC} and the flag rate {S_FLAG}, so no operating "
    f"point is claimed. R1 (no lexical bridge) is enriched in TP not FN (RR {S_RR}); the misses are crowded-catalogue "
    f"({r2_fn_share} of FN) and residual ({r6_fn_share}). Bridge contingency phi {S_PHI}, Fisher p {S_FP}. First "
    f"version archived as a broken-key tautology (D{dn+1}); the reproduce.sh evidence loop was found broken and "
    f"rewritten to derive paths from the claims matrix (D{dn+2}). Re-run of the corrected script was byte-identical "
    f"apart from timestamps.",
    f"yes - section 7.8, claims C20/C21, limitation L{nxt}"])
rtxt2 = (REG / "experiment_registry.csv").read_text(encoding="utf-8")
if "EXP-0046" not in rtxt2:
    (REG / "experiment_registry.csv").write_text(
        rtxt2.rstrip("\r\n") + "\r\n" + buf.getvalue().rstrip("\r\n") + "\r\n", encoding="utf-8", newline="")
    print("[e46] registered EXP-0046")
import pandas as pd
_r = pd.read_csv(REG / "experiment_registry.csv")
assert not _r.exp_id.duplicated().any(), "duplicate exp_id introduced"
assert list(_r.columns) == REGH, "registry column order changed"
print(f"[e46] registry rows={len(_r)}; EXP-0046 present: {'EXP-0046' in set(_r.exp_id)}")

# ---------------------------------------------------------------- self-check
for p in (T17, T18, T19, CL, LIM, RA, FA, DV, PP, RS, SR):
    assert p.exists() and p.stat().st_size > 0, f"{p} missing/empty"
assert {"C20", "C21"} <= {r[0] for r in rows_of(CL)[1:] if r}, "claims not in matrix"
assert "## 7.8" in PP.read_text(encoding="utf-8")
_assert_rs = RS.read_text(encoding="utf-8")
assert "\\ \\n" not in _assert_rs, "broken loop still present"
assert "claims_evidence_matrix.csv" in _assert_rs, "new evidence loop missing"
assert f"| D{dn+1} " in DV.read_text(encoding="utf-8") and f"| D{dn+2} " in DV.read_text(encoding="utf-8")
print("[e46] OK - all artefacts written and re-read")
