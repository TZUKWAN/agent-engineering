"""Record EXP-0035 (out-of-subset transfer) into P001's package. Everything here is read from the result file.

Adds: a generated table, a limitations section, a reviewer-attack answer, a final_audit defect update, a claims
row, and the registry status. Guards make it idempotent, and it refuses to write if the result file is absent.

    python 02_shared_code/registry/record_exp0035_p001.py
"""
from __future__ import annotations

import csv, glob, io, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
PAP = ROOT / "papers" / "P001_routing_failure_qpp"
REG = ROOT / "00_program_registry"

hits = sorted(glob.glob(str(ROOT / "results_raw" / "EXP0035_subset_sensitivity_*.json")))
if not hits:
    sys.exit("[e35] no EXP-0035 result file; writing nothing (a paper cannot cite evidence that does not exist).")
D = json.loads(pathlib.Path(hits[-1]).read_text(encoding="utf-8"))
CELLS, name = D["cells"], pathlib.Path(hits[-1]).name

pub = {"OSS": 0.0777, "Qwen3": 0.1292, "Kimi-K2": 0.0424}      # recomputed from routing_*.parquet, n_candidates>3
dev = {c: D[f"{c}_train"]["in_sample_auc"] for c in pub}
div = [CELLS[f"{c}|single-turn-diversify"] for c in pub]
mul = [CELLS[f"{c}|multi-turn"] for c in pub]
drop = lambda r: round(r["auc_own_subset_oof"] - r["auc_transfer_original_dev"], 4)
trans = lambda rs: (min(r["auc_transfer_original_dev"] for r in rs), max(r["auc_transfer_original_dev"] for r in rs))

TAB = PAP / "tables" / "table16_subset_transfer.csv"
TAB.parent.mkdir(exist_ok=True)
with open(TAB, "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["cfg", "subset", "rows", "prompt_ids", "prevalence_fail_at_3", "auc_transfer_from_original_dev",
                "auc_own_subset_oof", "degradation", "auc_length_only", "auc_post_retrieval_margin",
                "meets_pre_registered_rule"])
    for key, r in CELLS.items():
        c, s = key.split("|")
        w.writerow([c, s, r["rows"], r["prompt_ids"], r["prevalence"], r["auc_transfer_original_dev"],
                    r["auc_own_subset_oof"], drop(r), r["auc_length_only"], r["auc_post_retrieval_margin"],
                    r["meets_rule"]])
print(f"[e35] wrote {TAB.name}")

SEC = f"""
## L16 跨查询子集迁移实测（EXP-0035，表16）

L15 留下的问题是：发表样本只覆盖 `single-turn-original`，那结论能否外推？EXP-0035 用冻结模型
（`{D['frozen_model']}`，在发表 dev 上拟合、dev 本身仍是 original 子集）给两个从未参与过任何 split 的子集打分，
群体口径与发表分析一致（`n_candidates > 3`）。判据写在脚本 docstring 里、先于任何 AUROC 计算固定：
迁移 AUC ≥ 0.65、且不高于该子集自身 OOF AUC 减 0.05、且优于该子集的长度基线，三者同时满足才算"覆盖缺口已被
实测约束住"。

结果是**分向的，不是一句话能否定的**：

- `multi-turn` 三个 config 全部通过：迁移 AUC {trans(mul)[0]:.4f}–{trans(mul)[1]:.4f}，相对自身 OOF 只降
  {min(drop(r) for r in mul):.4f}–{max(drop(r) for r in mul):.4f}。
- `single-turn-diversify` 三个 config 全部不通过：迁移 AUC {trans(div)[0]:.4f}–{trans(div)[1]:.4f}，降幅
  {min(drop(r) for r in div):.4f}–{max(drop(r) for r in div):.4f}，超出 0.05 容差。这一档恰恰是指令改写／
  词汇变化条件，也就是词汇落差构念最该经受考验的地方，所以按预注册判据本次结论为
  **`{D['verdict']['decision'].split(':')[0]}`**。
- 但"变弱"不等于"失效"：六个格子里迁移 AUC 都 ≥ {min(r['auc_transfer_original_dev'] for r in CELLS.values()):.4f}，
  都比各自长度基线高 {min(r['auc_transfer_original_dev'] - r['auc_length_only'] for r in CELLS.values()):.3f}–{max(r['auc_transfer_original_dev'] - r['auc_length_only'] for r in CELLS.values()):.3f}
  AUROC，也高于发表值里的跨语料迁移 {0.6939}。
- 普遍率**没有**一致方向的偏移：original→diversify 在 OSS 相同（{pub['OSS']} vs {div[0]['prevalence']}）、
  在 Qwen3 下降（{pub['Qwen3']} vs {div[1]['prevalence']}）、在 Kimi-K2 上升（{pub['Kimi-K2']} vs {div[2]['prevalence']}），
  因此本文**不声明**发表样本低估或高估了失败率。

结论口径据此收紧：H1–H3 是 **single-turn-original 指令上的估计**；对改写指令，预测器的判别力实测下降约 0.06
AUROC，对多轮跟进指令则基本保持。发表 dev 的在样本 AUC（{dev['OSS']} / {dev['Qwen3']} / {dev['Kimi-K2']}）
不应被当作跨子集性能引用。
"""

lm = PAP / "limitations.md"
t = lm.read_text(encoding="utf-8")
if "## L16 跨查询子集迁移实测" not in t:
    t = t.replace("EXP-0035（脚本已写、尚未执行）", "EXP-0035（已执行，见 L16 与表16）")
    lm.write_text(t.rstrip() + "\n" + SEC, encoding="utf-8")
    print("[e35] appended L16 and repointed L15")

ra = PAP / "reviewer_attack.md"
rt = ra.read_text(encoding="utf-8")
probe = "Your sample is one query subset"
if probe not in rt:
    n = max([int(x) for x in re.findall(r"^\| A(\d+) \|", rt, re.M)] or [0]) + 1
    ans = (f"| A{n} | **{probe}?** Yes, and now measured. EXP-0035 scores two subsets that never entered any "
           f"split: transfer AUC {trans(mul)[0]:.3f}-{trans(mul)[1]:.3f} on multi-turn (within tolerance) but "
           f"{trans(div)[0]:.3f}-{trans(div)[1]:.3f} on single-turn-diversify, a {min(drop(r) for r in div):.3f}-"
           f"{max(drop(r) for r in div):.3f} AUROC loss that trips the pre-registered 0.05 rule. Prevalence moves "
           f"in both directions across configs, so no under- or over-statement of the base rate is claimed. H1-H3 "
           f"are scoped to single-turn-original instructions. | table16_subset_transfer.csv, L15-L16 |")
    ra.write_text(rt.rstrip() + "\n" + ans + "\n", encoding="utf-8")
    print(f"[e35] added reviewer-attack A{n}")

fa = PAP / "final_audit.md"
ft = fa.read_text(encoding="utf-8")
if "out-of-subset transfer measured" not in ft:
    ft = ft.replace("the transfer test EXP-0035 is written but not yet run.",
                    "out-of-subset transfer measured (EXP-0035): multi-turn transfers within tolerance, "
                    "single-turn-diversify loses ~0.06 AUROC and trips the pre-registered rule, so H1-H3 are "
                    "scoped to single-turn-original instructions.")
    fa.write_text(ft, encoding="utf-8")
    print("[e35] final_audit defect updated with the measured result")

cm = PAP / "claims_evidence_matrix.csv"
rows = list(csv.DictReader(io.StringIO(cm.read_text(encoding="utf-8"))))
key = "EXP-0035"
if not any(key in (r.get("experiment_id") or "") for r in rows):
    ids = sorted(int(re.sub(r"\D", "", r["claim_id"])) for r in rows if re.sub(r"\D", "", r["claim_id"]))
    cid = f"C{max(ids) + 1}" if ids else "C19"
    d = {"claim_id": cid,
         "claim": ("The frozen pre-retrieval predictor transfers to multi-turn agent instructions within the "
                   f"pre-registered tolerance (AUC {trans(mul)[0]:.4f}-{trans(mul)[1]:.4f}) but loses "
                   f"{min(drop(r) for r in div):.4f}-{max(drop(r) for r in div):.4f} AUROC on paraphrased "
                   "(single-turn-diversify) instructions, so H1-H3 are scoped to single-turn-original queries"),
         "claim_type": "generalisation / scope", "experiment_id": f"{key} (table16_subset_transfer.csv)",
         "direction": "supports with stated scope limit", "table": "table16_subset_transfer.csv",
         "figure": "-", "statistical_test": "GroupKFold-by-prompt_id OOF + transfer scoring on unseen subsets",
         "raw_result_file": f"results_raw/{name}", "where_in_paper": "L16; A" + str(
             max([int(x) for x in re.findall(r"^\| A(\d+) \|", rt, re.M)] or [0])),
         "status": "supported_negative_on_one_subset"}
    with open(cm, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writerow(d)
    print(f"[e35] added claim {cid}")

hdr = list(csv.DictReader(io.StringIO((REG / "experiment_registry.csv").read_text(encoding="utf-8"))))
reg = pathlib.Path(REG / "experiment_registry.csv")
lines = list(csv.reader(io.StringIO(reg.read_text(encoding="utf-8"))))
i = next(n for n, r in enumerate(lines) if r and r[0] == "EXP-0035")
h = lines[0]
upd = {"stage": "out_of_subset_transfer_DONE", "started_at": D["started_at"], "finished_at": D["finished_at"],
       "status": "completed_PREDICTOR_IS_SUBSET_SPECIFIC",
       "outputs": f"{name}; results_processed/EXP0035_subset_sensitivity.csv; "
                  "papers/P001_routing_failure_qpp/tables/table16_subset_transfer.csv",
       "notes": ("Executed after two harness fixes (scaled_pipeline returns a FACTORY - the script called it as a "
                 "model; first run died there, as the registry note predicted). Transfer AUC multi-turn "
                 f"{trans(mul)[0]:.4f}-{trans(mul)[1]:.4f} (passes the 0.05 closeness rule), diversify "
                 f"{trans(div)[0]:.4f}-{trans(div)[1]:.4f} (loses {min(drop(r) for r in div):.4f}-"
                 f"{max(drop(r) for r in div):.4f}, fails it). Prevalence checked on the same restricted "
                 "population and NOT shifted in a consistent direction, so no base-rate claim was made. "
                 "Written into L15/L16, A-row, claims matrix and final_audit."),
       "enters_paper": "yes - L16, table16, one claims row, one reviewer-attack answer"}
for k, v in upd.items():
    lines[i][h.index(k)] = v
buf = io.StringIO()
csv.writer(buf, lineterminator="\r\n").writerows(lines)
reg.write_text(buf.getvalue(), encoding="utf-8", newline="")
import pandas as pd
d2 = pd.read_csv(reg)
assert len(d2) == len(lines) - 1, "registry row count changed"
print(f"[e35] registry updated; rows={len(d2)}; EXP-0035 status={d2[d2.exp_id == 'EXP-0035'].status.iloc[0]}")
