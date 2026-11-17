"""EXP-0056/0057/0058: land the literature-grading correction into P005, and record the retraction.

What happened: EXP-0047 screened T013 as the only L1 in the funnel using five phrase families. Grading the
harvested abstracts by rule (EXP-0057) surfaced records whose own vocabulary - `license laundering`,
`permissive-washing`, `license integrity`, `license compatibility`, `dataset licensing` - was never queried.
Querying those words (EXP-0058) returned a confirmed collision cluster, including the 2023 Data Provenance
Initiative, so **the L1 gap call was a query-coverage failure, not a gap**. This script records that, assigns
`level_final` to the records a rule cannot grade honestly, and registers the three literature experiments.

It writes only files no package generator owns: the graded matrix's `level_final`/`differentiation` cells, P005's
deviations, and the registry. The prose corrections live in the generators (`build_package.py`,
`build_package_partb.py`) so a regeneration cannot lose them.

    python 02_shared_code/registry/record_literature_correction_p005.py
"""
from __future__ import annotations

import csv, glob, io, json, pathlib, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
REG = ROOT / "00_program_registry"
PAP = ROOT / "papers" / "P005_governance_metadata_verifiability"
NOW = time.strftime("%Y-%m-%dT%H:%M:%S")

G = list(csv.DictReader(open(REG / "literature_graded.csv", encoding="utf-8")))
A = {r["identifier"]: r for r in csv.DictReader(open(REG / "literature_abstracts.csv", encoding="utf-8"))}
P5 = [r for r in G if r["paper_id"] == "P005"]

# Named overrides: a rule cannot see that an audit of licence obligations across an AI supply chain is the same
# construct measured on a different object family. Each entry is justified by the record's own abstract.
FINAL = {
    "2607.20300v1": ("L4", "measures whether licence obligations survive redistribution across dataset->model->app "
                            "chains (232,270 links) - same construct as P005 (declared vs verifiable rights), "
                            "different object family (general AI artefacts, not agent trajectory releases)"),
    "2602.08816v1": ("L4", "large-scale audit of licence integrity in open AI artefacts: license text present, "
                            "copyright notice, upstream attribution - exactly the payload-level checks P005 runs at "
                            "L5/L6/L7, on a far larger and different population"),
    "2310.16787v3": ("L4", "the Data Provenance Initiative audits dataset licensing and attribution across a large "
                            "corpus of training datasets; P005's unit (the release as a rights object, seven declared "
                            "levels, card-vs-disk agreement) is a subset of its concern"),
    "2606.28867v1": ("L3", "licence-compatibility audit over 20+ corpus families with a compatibility matrix; "
                            "construct shared, object family and question (compatibility, not verifiability) differ"),
    "2602.10758v1": ("L3", "licensing risk across LLMware supply chains; same construct, different unit"),
    "2601.19191v1": ("L3", "proposes machine-checkable release artefacts plus a conformance checklist for model/"
                            "dataset cards - P005 measures what those artefacts currently say, and does not propose one"),
    "2602.18700v2": ("L2", "copyright protection *method* for LLM agent trajectories; shares the object family and "
                            "notes the literature has overlooked trajectory-dataset rights, but measures nothing"),
}
rows = list(csv.DictReader(open(PAP / "literature_matrix.csv", encoding="utf-8")))
hdr = list(rows[0].keys())
touched = 0
for r in rows:
    ident = (r.get("url") or "").rsplit("/abs/", 1)[-1].lower()
    key = next((k for k in FINAL if k.split("v")[0] == ident.split("v")[0]), None)
    if key:
        lvl, why = FINAL[key]
        r["overlap_level"] = lvl
        r["differentiation"] = why
        r["verify_status"] = (r.get("verify_status", "") + " | level_final assigned by hand after reading the "
                                                            "abstract (EXP-0057/0058)").strip(" |")
        touched += 1
with open(PAP / "literature_matrix.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=hdr)
    w.writeheader()
    w.writerows(rows)
print(f"[litcorr] level_final + differentiation written for {touched} records")

counts = {}
for r in P5:
    counts[r["level_rule"]] = counts.get(r["level_rule"], 0) + 1

DV = PAP / "deviations.md"
dt = DV.read_text(encoding="utf-8")
D11 = (f"| D-P11 | {NOW} | **撤回 T013 的 L1 判断**：漏斗筛查的短语族不完整，导致把已被占据的方向当成空白 | "
       f"EXP-0047 只查了 dataset license / licensing+cs.DB / data provenance / responsible release datasets / model card "
       f"五族；EXP-0057 对已采摘要做规则分级后浮出 'license laundering'(2607.20300)、'permissive-washing'"
       f"(2602.08816)、Data Provenance Initiative(2310.16787) 等本族词汇；EXP-0058 用这些词重查，18 条查询里 14 条 "
       f"informative，去重后 24 条与本文构念相关，判为碰撞确认 | 否（不涉及任何实验数字，只改定位） | "
       f"P005 的贡献从『没人测 AI 发行的权利可验证性』收缩为『没人对 agent 轨迹发行用七级声明阶梯 + 负载值级威胁检验来测』；"
       f"novelty_audit 与 paper §1 由生成器重写，上述三条记为 L4 并写明差异 |")
D12 = (f"| D-P12 | {NOW} | 生成物与追加式记录器冲突：EXP-0053 的散文曾以追加方式写入由 build_package_partb.py 整体重写的文件 | "
       f"重跑生成器会丢掉 A7/A12/L2/final_audit 的 (b) 条；核查生成链时发现此类追加会被静默抹掉 | 否 | "
       f"把这些内容移入生成器本体，记录器只保留注册表、表格与 devitations 三类它独占的产物；今后凡被生成器重写的文件不再由记录器追加 |")
if "| D-P11 " not in dt:
    DV.write_text(dt.replace("\n## 未变更项", D11 + "\n" + D12 + "\n## 未变更项", 1), encoding="utf-8", newline="")
    print("[litcorr] appended D-P11, D-P12")

p = REG / "experiment_registry.csv"
txt = p.read_text(encoding="utf-8")
h2 = list(csv.reader(io.StringIO(txt)))[0]
ROWS = [
    ["EXP-0056", "PROGRAM (literature)", "abstract_fetch_DONE",
     "02_shared_code/literature/fetch_abstracts.py",
     "287 identifiers (DOIs via api.crossref.org/works/{doi}, arXiv via id_list); curl transport; batched "
     "`filter=doi:A|B` abandoned because one unknown id zeroes the whole response; checkpointed, resumable, "
     "failures re-queried", "none", NOW, NOW, "success_189_of_287_abstracts",
     "00_program_registry/literature_abstracts.csv; 00_program_registry/literature_abstracts_checkpoint.json",
     "94 Crossref records have no deposited abstract, so those stay `title_only` and are not graded as if read; "
     "this is what made principle-2 abstract reading possible for the first time", "yes - feeds EXP-0057"],
    ["EXP-0057", "PROGRAM (literature)", "collision_grading_DONE",
     "02_shared_code/literature/grade_collisions.py",
     "287 records graded L0-L4 against each paper's own object/construct/measure/data families from title+abstract; "
     "every grade carries its matched terms as evidence; L3/L4 and unread L2 flagged for hand verification; "
     "graded_on marks title-only records", "rule + hand check", NOW, NOW,
     "success_no_rule_graded_L4_but_hand_overrides_exist",
     "00_program_registry/literature_graded.csv; docs/literature_grading_review_20260920.md",
     "P005 18 L3 / 15 L2; the grading exposed the vocabulary P005 had never queried for; hand overrides written as "
     "level_final into P005's matrix (3 x L4)", "yes - P005 novelty audit"],
    ["EXP-0058", "P005", "collision_queries_DONE",
     "02_shared_code/literature/p005_collision_queries.py",
     "18 queries over the phrase families the collided records actually use (license laundering, permissive-washing, "
     "license integrity, compatibility, dataset licensing, agent trajectory, dataset card), 3s pace, per-query "
     "informative/zero_records/transport_error", "none", NOW, NOW,
     "success_COLLISION_CONFIRMED_24_relevant_records",
     "; ".join(sorted(str(x) for x in pathlib.Path(str(ROOT / "results_raw")).glob("EXP0058*.json")))
     + "; results_processed/EXP0058_collision_queries.csv",
     "overturns T013's L1 gap call (D-P11): the space is occupied for AI artefacts generally (2310.16787, "
     "2602.08816, 2607.20300); P005's surviving delta is the agent-trajectory family plus the seven-level ladder "
     "and the value-level threat test", "yes - novelty_audit, paper 1, D-P11"],
]
added = 0
for row in ROWS:
    assert len(row) == len(h2), (row[0], len(row), len(h2))
    if row[0] in {r[0] for r in csv.reader(io.StringIO(txt)) if r}:   # substring checks are wrong: a note that
        continue                                                     # mentions EXP-0057 would block registering it
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\r\n").writerow(row)
    txt = txt.rstrip("\r\n") + "\r\n" + buf.getvalue().rstrip("\r\n") + "\r\n"
    added += 1
p.write_text(txt, encoding="utf-8", newline="")
import pandas as pd
d = pd.read_csv(p)
assert not d.exp_id.duplicated().any(), "duplicate exp_id"
print(f"[litcorr] registered {added} experiments; rows={len(d)}")
print(f"[litcorr] P005 rule grades: {json.dumps(counts)} | hand L4 overrides: "
      f"{sum(1 for v in FINAL.values() if v[0] == 'L4')}")
print("[litcorr] OK")
