"""Land EXP-0053 (P005's value-level threat test) into the package, and record EXP-0054's funnel decision.

The census (EXP-0049) decided rights absence from column and metadata-key NAMES. P005's limitation L2 admitted that
a licence inside a *value* would be missed, and its final audit named the value-level scan as the first real threat to
the headline. This recorder states what that test found, including the two instrument exclusions discovered while
inspecting it (D-P8: the release's own README is the card, not payload; D-P9: jsonl payloads had no coverage).

    python 02_shared_code/registry/record_exp0053_p005.py
"""
from __future__ import annotations

import csv, glob, io, json, pathlib, re, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
PAP = ROOT / "papers" / "P005_governance_metadata_verifiability"
REG = ROOT / "00_program_registry"
NOW = time.strftime("%Y-%m-%dT%H:%M:%S")
hits = sorted(glob.glob(str(ROOT / "results_raw" / "EXP0053_value_level_rights_*.json")))
if not hits:
    raise SystemExit("[e53] no EXP-0053 result file; writing nothing.")
NAME = pathlib.Path(hits[-1]).name
D = json.loads(pathlib.Path(hits[-1]).read_text(encoding="utf-8"))
R = {r["corpus"]: r for r in D["releases"]}
ORDER = list(R)
TOT_HITS = sum(r["rights_hits"] for r in R.values())
TOT_INSTR = sum(r["instruction_hits"] for r in R.values())
rows = {k: R[k]["rows_sampled"] for k in ORDER}
zero_rel = [k for k in ORDER if R[k]["rights_hits"] == 0]
nz_rel = [k for k in ORDER if R[k]["rights_hits"] > 0]
sup = [f for f in sorted(pathlib.Path(str(ROOT / "results_raw" / "superseded")).glob("EXP0053*.json"))]

TBL = PAP / "tables" / "table8_value_level_scan.csv"
with open(TBL, "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["release", "parquet_files_present", "files_read", "file_coverage", "rows_sampled", "cells_sampled",
                "chars_scanned_MB", "payload_rights_hits", "instruction_only_hits_excluded",
                "card_self_hits_excluded", "columns_where_hits_occurred", "distinct_hit_strings", "verdict"])
    for k in ORDER:
        r = R[k]
        w.writerow([k, r.get("parquet_files_present"), r.get("parquet_files_read"), r.get("file_coverage"),
                    r["rows_sampled"], r["cells_sampled"], round(r["chars_scanned"] / 1e6, 1), r["rights_hits"],
                    r["instruction_hits"], r.get("card_self_hits_excluded"), "|".join(r["hit_columns"]) or "none",
                    r["distinct_hit_strings"], r["verdict_for_release"]])
print(f"[e53] wrote {TBL.name}")

SEC = f"""## A7 Value-level threat test (EXP-0053) — does rights text appear inside the payload?

`02_shared_code/data_audit/governance_value_level_scan_p005.py`, seed {D['seed']}. The rule is in that module's
docstring and was written before any value was read: the headline changes only if some release yields ≥5 sampled rows
whose **value** text carries a rights expression, outside the instruction fields, outside the card itself, and
surviving inspection of every distinct matching string.

Coverage actually obtained: {sum(rows.values()):,} rows, {sum(r['cells_sampled'] for r in R.values()):,} cells,
{round(sum(r['chars_scanned'] for r in R.values())/1e6, 1)} MB of text, up to {max(r.get('parquet_files_read', 0) for r in R.values())}
randomly chosen parquet files per release (one random row group each, never head-of-file) plus {max(r.get('jsonl_lines_scanned', 0) for r in R.values()):,}
jsonl lines for the jsonl-only release.

Result: **{TOT_HITS} payload hits in total, concentrated in {len(nz_rel)} release(s)**
({", ".join(f"{k}: {R[k]['rights_hits']}" for k in nz_rel) or "none"}); {len(zero_rel)} of 8 releases have zero.
Every one of those {TOT_HITS} hits was inspected — they are the strings themselves, quoted in
`results_raw/{NAME}` — and all of them sit in model-written quality-rationale prose about a third-party asset
("MIT license = $0", "copyright, data privacy for animation assets"), i.e. content discussing licences, not a rights
notice attaching to the corpus. Under the rule's inspection clause the CHANGE_HEADLINE branch therefore does not
fire: the formal verdict recorded by the script is `{D['verdict']}` and it is reported as such, not upgraded — the
headline survives the threat test with its residual uncertainty stated in limitation L2.

Two exclusions were added after looking at the first run's hits, both of which can only **reduce** the count:
**D-P8** the release's own `README.md` was being scanned as a "small document", so six of the seven first-pass hits
were the card's own `license:` line being counted as payload evidence — the card is exactly the level L2/L4 that this
test is supposed to threaten; **D-P9** jsonl payloads had no coverage at all, so MMAT-1M contributed 0 rows. The
first-run file is kept in `results_raw/superseded/` ({len(sup)} superseded EXP-0053 file(s)).

Also recorded, because it is the interesting negative: rights words are *abundant* inside instructions
({TOT_INSTR:,} hits in question/message fields, up to {max(r['instruction_hits'] for r in R.values()):,} in one
release), and those are excluded by rule — a user asking about licensing is not the corpus declaring its licence.
"""
ap = PAP / "appendix.md"
atxt = ap.read_text(encoding="utf-8")
if "A7 Value-level threat test" not in atxt:
    ap.write_text(atxt.rstrip() + "\n\n" + SEC, encoding="utf-8", newline="")
    print("[e53] appended appendix A7")

LIM = PAP / "limitations.md"
lt = LIM.read_text(encoding="utf-8")
old2 = "2. **Names, not contents, at record level.**"
if "EXP-0053" not in lt:
    lt = lt.replace(old2, "2. **Names, not contents, was tested, not assumed (EXP-0053).**", 1)
    lt = lt.replace("""lexicon sensitivity (K5) quantifies part of this exposure but not the value-embedding case.""",
                    f"""lexicon sensitivity (K5) quantifies the detector exposure, and EXP-0053 attacked the
   value-embedding case directly: {TOT_HITS} payload hits across {sum(rows.values()):,} sampled rows and
   {round(sum(r['chars_scanned'] for r in R.values())/1e6, 1)} MB, all of them model-written prose *about* licences
   rather than notices *of* one, with {len(zero_rel)}/8 releases at zero. That is a threat test the headline survived,
   not a proof of absence: the scan covers a random subset of files per release (table8 records the coverage), so a
   rights notice confined to unread files would still be missed.""", 1)
    LIM.write_text(lt, encoding="utf-8", newline="")
    print("[e53] updated limitations L2")

CL = PAP / "claims_evidence_matrix.csv"
hdr = list(csv.DictReader(open(CL, encoding="utf-8")))[0]
have = {r["claim_id"] for r in csv.DictReader(open(CL, encoding="utf-8"))}
K8 = dict(zip(hdr, ["K8", "头线条款经受住了值级威胁检验：语料负载的值文本里没有关于该语料本身的权利声明",
                    "否证性检验（限定 L2 的直接威胁）", "EXP-0053", "supports",
                    f"{TOT_HITS} 条负载命中全部集中在 {len(nz_rel)} 个发行（{'、'.join(nz_rel) or '无'}），"
                    f"{len(zero_rel)}/8 为 0；{sum(rows.values()):,} 行 / "
                    f"{round(sum(r['chars_scanned'] for r in R.values())/1e6,1)} MB 被扫描；"
                    f"逐条查验后均判定为模型撰写的第三方资产许可讨论，而非语料权利声明；"
                    f"脚本按规则记为 {D['verdict']}，未上调",
                    "tables/table8_value_level_scan.csv", "",
                    "无（枚举与逐条查验；判据在脚本 docstring 中先于运行固定）",
                    f"results_raw/EXP0053_value_level_rights_*.json;results_raw/{NAME}",
                    "Appendix A7; Limitations L2", "supported (threat test survived; formal verdict not upgraded)"]))
if "K8" not in have:
    with open(CL, "a", newline="", encoding="utf-8") as fh:
        csv.DictWriter(fh, fieldnames=hdr).writerow(K8)
    print("[e53] appended claim K8")

RA = PAP / "reviewer_attack.md"
ra = RA.read_text(encoding="utf-8")
lastA = max([int(x) for x in re.findall(r"(?m)^\| A(\d+) ", ra)] or [0])
if "EXP-0053" not in ra:
    RA.write_text(ra.rstrip() + f"\n| A{lastA+1} | \"Your absence result only looked at column names; a licence could "
                  f"be sitting inside a value.\" | Tested, and the test could have passed | EXP-0053 scanned "
                  f"{sum(rows.values()):,} rows / {round(sum(r['chars_scanned'] for r in R.values())/1e6,1)} MB of "
                  f"cell text over randomly chosen files and row groups: {TOT_HITS} payload hits, all in "
                  f"model-written quality rationales about third-party assets, {len(zero_rel)}/8 releases at zero, and "
                  f"{TOT_INSTR:,} instruction-field hits excluded by rule because a user asking about licensing is not "
                  f"the corpus declaring a licence. Building the test also exposed two of our own errors (D-P8 counted "
                  f"the card as payload; D-P9 gave the jsonl release no coverage) | New experiment; claim K8; "
                  f"appendix A7; limitation L2 rewritten from an admission into a tested statement |\n",
                  encoding="utf-8", newline="")
    print(f"[e53] appended A{lastA+1}")

FA = PAP / "final_audit.md"
fa = FA.read_text(encoding="utf-8")
if "EXP-0053" not in fa:
    # the sentence wraps across lines in the generated file, so match it with a pattern rather than a literal
    fa = re.sub(r"\(b\) the value-level rights scan[^.]*\.",
                "(b) ~~the value-level rights scan~~ **DONE (EXP-0053, claim K8, appendix A7)** — the headline "
                "survived a test that could have refuted it; what remains of limitation L2 is only the unread-file "
                "residue, which table8 now bounds with explicit coverage.", fa, count=1, flags=re.S)
    FA.write_text(fa, encoding="utf-8", newline="")
    print("[e53] updated final_audit gate")

DV = PAP / "deviations.md"
dt = DV.read_text(encoding="utf-8")
D8 = (f"| D-P8 | {NOW} | 值级扫描不再把语料自身的 README.md 当作负载证据 | 首版命中的 7 条里有 6 条就是卡片第一行的 "
      f"`license:`；卡片正是本实验要威胁的 L2/L4 层级，把它当负载等于让威胁检验自己给自己送分 | 否（只看命中字符串，未据此改结论） "
      f"| 剔除后负载命中由 7 → {TOT_HITS}；README 是否含权利文字单列为 `card_self_hits_excluded` 字段保留 |")
D9 = (f"| D-P9 | {NOW} | 值级扫描补上 jsonl 负载覆盖 | 首版只扫 parquet，MMAT-1M 扫到 0 行，其『负命中』是抽样口径造成的假象 "
      f"| 否 | 补 3,000 行 jsonl 后 MMAT-1M 命中 0（原为 1，即卡片自身），覆盖问题消除 |")
D10 = (f"| D-P10 | {NOW} | 值级扫描的文件上限（40/发行，随机行组，覆盖写入结果） | 第一次尝试对最大发行（1,230 个文件）"
       f"逐文件读取整个 row group，九分钟未完成且内存不稳 | 否 | 检验在 2 分钟内完成 8 个发行；覆盖率显式记入 table8，"
       f"论文只把结论说成\"在被抽样的文件里未发现\" |")
if "| D-P8 " not in dt:
    DV.write_text(dt.replace("\n## 未变更项", D8 + "\n" + D9 + "\n" + D10 + "\n## 未变更项", 1), encoding="utf-8", newline="")
    print("[e53] appended D-P8, D-P9, D-P10")

SR = ROOT / "results_raw" / "SUPERSEDED_ARTIFACTS.json"
sj = json.loads(SR.read_text(encoding="utf-8"))
have_f = {e["file"] for e in sj["superseded"]}
for f in sup:
    if f.name not in have_f:
        sj["superseded"].append({"file": f.name, "exp_id": "EXP-0053", "at": NOW,
                                 "reason": "counted the release's own README as payload evidence (D-P8) and gave the "
                                           "jsonl-only release no value coverage (D-P9); replaced by " + NAME,
                                 "was_it_quoted": "no - superseded before any package text used it"})
SR.write_text(json.dumps(sj, indent=1, ensure_ascii=False), encoding="utf-8", newline="")

p = REG / "experiment_registry.csv"
hdr2 = list(csv.reader(io.StringIO(p.read_text(encoding="utf-8"))))[0]
txt = p.read_text(encoding="utf-8")
if "EXP-0053" not in txt:
    buf = io.StringIO()
    _row = dict(zip(hdr2, [
        "EXP-0053", "P005", "value_level_threat_test_DONE",
        "02_shared_code/data_audit/governance_value_level_scan_p005.py",
        f"{sum(rows.values()):,} rows / {sum(r['cells_sampled'] for r in R.values()):,} cells / "
        f"{round(sum(r['chars_scanned'] for r in R.values())/1e6,1)} MB over up to "
        f"{max(r.get('parquet_files_read',0) for r in R.values())} randomly chosen parquet files per release "
        "(one random row group each) + jsonl lines; nested JSON decoded one level; instruction fields and the release's "
        "own card excluded by rule; seed 2026; CHANGE/CONFIRM/sparse rule fixed in the module docstring", "2026",
        D["started_at"], D["finished_at"], "success_headline_survived_value_test_formal_verdict_sparse",
        f"{NAME}; results_processed/EXP0053_value_hits.csv; papers/P005_governance_metadata_verifiability/"
        "tables/table8_value_level_scan.csv",
        f"{TOT_HITS} payload hits, {len(zero_rel)}/8 releases at zero, every hit inspected and rejected as a corpus "
        f"rights notice (they are model-written rationales about third-party assets); {TOT_INSTR:,} instruction-field "
        f"hits excluded by rule. Three instrument fixes found by looking: D-P8 card counted as payload, D-P9 jsonl "
        f"uncovered, D-P10 unbounded file reads. Landed as K8, appendix A7, limitation L2 rewritten, reviewer A"
        f"{lastA+1}, final_audit item (b) closed.",
        "yes - K8, A7, L2, final_audit"]))
    csv.writer(buf, lineterminator="\r\n").writerow([_row[c] for c in hdr2])
    p.write_text(txt.rstrip("\r\n") + "\r\n" + buf.getvalue().rstrip("\r\n") + "\r\n", encoding="utf-8", newline="")
    print("[e53] registered EXP-0053")
import pandas as pd
d = pd.read_csv(p)
assert not d.exp_id.duplicated().any()
print(f"[e53] registry rows={len(d)}")
for q in (TBL, CL, ap, LIM, RA, FA, DV):
    assert q.exists() and q.stat().st_size > 0
print("[e53] OK")
