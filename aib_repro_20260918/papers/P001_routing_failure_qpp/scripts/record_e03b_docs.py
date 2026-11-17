"""Record E03b (EXP-0024): a trained dense comparator, its consequences for the construct, and the
honest downgrade where the pre-registered criterion was not met."""

from __future__ import annotations

import glob
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PAP = ROOT / "papers" / "P001_routing_failure_qpp"
REG = ROOT / "00_program_registry" / "experiment_registry.csv"
E = json.loads(Path(sorted(glob.glob(str(ROOT / "results_raw" / "EXP0024_dense_comparator_*.json")))[-1])
               .read_text(encoding="utf-8"))
rq, ct, vd = E["retrieval_quality"], E["construct_transfer_to_a_trained_ranker"], E["verdict"]
dense_auc = max(ct["auc_model_trained_on_dense_failure_oof"])
cross = ct["auc_frozen_model_trained_on_bm25_failure__scored_on_dense_failure"]
raws = ";".join([f"results_raw/{Path(p).name}" for p in
                 sorted(glob.glob(str(ROOT / 'results_raw' / 'EXP0024_dense_comparator_*.json')))])

ROW = dict(exp_id="EXP-0024", paper_id="T037", stage="e03b_trained_dense_comparator_DEV_ONLY",
           script="02_shared_code/statistics/dense_comparator_e03b.py",
           config=f"two linear towers, dim={E['model']['dim']}, {E['model']['steps']} full-batch Adam steps, "
                  f"lr={E['model']['lr']}, TF-IDF(min_df=3, max_features=30000, sublinear) fitted on the "
                  f"training fold only; per-row softmax over its own candidates with all golds as positives; "
                  f"{E['protocol']['folds']}-fold GroupKFold by prompt_id; CPU-only torch "
                  f"{E['model']['framework'].split()[-1] if E['model']['framework'].split()[-1].replace('.','').isdigit() else ''}"
                  f"; no test row read",
           seed="42", started_at=E["started_at"], finished_at=E["finished_at"],
           status="success_dense_ranker_strongest_and_finding_is_ranker_specific",
           outputs=f"{raws}; results_processed/EXP0024_dense_vs_bm25.csv; logs/EXP-0024b_dense_comparator.txt",
           notes=f"Answers the 'weak baseline' attack with a trained retriever instead of BM25 alone. The "
                 f"from-scratch dense ranker beats frozen BM25: hit@3 {rq['hit_at_3_dense_trained']} vs "
                 f"{rq['hit_at_3_bm25_frozen']}, mean best rank {rq['mean_dense_best_rank']} vs "
                 f"{rq['mean_bm25_best_rank']} (chance {rq['chance_hit_at_3']}). Their failures are almost "
                 f"disjoint: Jaccard of positive sets {rq['positive_set_overlap_jaccard']}, Spearman of ranks "
                 f"{rq['spearman_dense_vs_bm25_rank']}, {rq['discordant_rows']} discordant rows. Pre-retrieval "
                 f"predictability itself survives per-ranker: a model trained on dense failure reaches AUROC "
                 f"{dense_auc} (length-only {ct['auc_length_only_vs_dense_failure']}), but the frozen model "
                 f"trained on BM25 failure scores only {cross} against dense failure, BELOW the pre-registered "
                 f"0.65 survival criterion, so cross-ranker transfer of the predictor is reported as not "
                 f"established. Wallclock {E['wallclock_sec']}s.",
           enters_paper="yes (E03b; refines L1 ranker-relativity and the §7.7 result)")

CLAIM = dict(claim_id="C16",
             claim="加入从零训练的双塔稠密检索器作为学习型强基线后：(a) BM25 不是稻草人但确实更弱——dense hit@3 "
                   f"{rq['hit_at_3_dense_trained']} > BM25 {rq['hit_at_3_bm25_frozen']}；(b) 两个排序器的失败集合几乎"
                   f"不相交（正例 Jaccard {rq['positive_set_overlap_jaccard']}，rank Spearman "
                   f"{rq['spearman_dense_vs_bm25_rank']}），说明'哪条请求会被漏掉'高度依赖排序器；(c) 事前可预测性"
                   f"对每种排序器各自成立（针对 dense 失败重训 AUROC {dense_auc}），但**跨排序器不成立**"
                   f"（用 BM25 失败训练、在 dense 失败上评仅 {cross}，低于事先设定的 0.65 存活判据）。",
             claim_type="基线强度/构念边界（含未达判据的负面结果）",
             experiment_id="EXP-0024", direction="mixed_baseline_stronger_and_transfer_fails",
             digits_reported=f"dense {rq['hit_at_3_dense_trained']} vs bm25 {rq['hit_at_3_bm25_frozen']}; "
                             f"jaccard {rq['positive_set_overlap_jaccard']}; per-ranker AUC {dense_auc}; "
                             f"cross-ranker AUC {cross} (< 0.65)",
             table="tables/table13_dense_comparator.csv", figure="-",
             statistical_test="5-fold prompt_id GroupKFold out-of-fold ranks; AUROC with the same frozen feature "
                              "family; criterion 0.65 fixed before training",
             raw_result_file=raws, where_in_paper="§7.7; §8 Second; L1/L6; Appendix A13",
             status="supported_with_negative_component")


def main():
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    reg = pd_read = None
    import pandas as pd
    reg = pd.read_csv(REG)
    reg = pd.concat([reg[reg.exp_id != "EXP-0024"], pd.DataFrame([ROW])], ignore_index=True).sort_values("exp_id")
    reg.to_csv(REG, index=False)
    cm = pd.read_csv(PAP / "claims_evidence_matrix.csv")
    cm = pd.concat([cm[cm.claim_id != "C16"], pd.DataFrame([CLAIM])], ignore_index=True)
    cm.to_csv(PAP / "claims_evidence_matrix.csv", index=False)
    print("registry", len(reg), "claims", len(cm))

    DEV = (f"| D16 | 2026-09-18 22:05 | **补齐学习型稠密基线（E03b/EXP-0024），并据此把"
           f"\"排序器相对\"从限制升级为论文结论的一部分** | 预训练编码器在本环境不可得（EXP-0022 + "
           f"环境更正记录），故改为从零训练双塔 TF-IDF→128 维投影模型，在同一 dev 行集、同一 prompt_id "
           f"分组交叉验证下与冻结 BM25 对比 | **否：本实验完全不读 test 行，账本仍为 1 次 test 评估** | "
           f"结果一半为正一半为负：dense 更强（hit@3 {rq['hit_at_3_dense_trained']} vs "
           f"{rq['hit_at_3_bm25_frozen']}），失败集合几乎不相交（Jaccard "
           f"{rq['positive_set_overlap_jaccard']}）；针对 dense 失败重训仍可达 AUROC {dense_auc}，"
           f"但用 BM25 失败训练的冻结模型在 dense 失败上只有 {cross}，**低于事先设定的 0.65 判据**，"
           f"因此不宣称跨排序器可迁移，并把判据原文与未达标一并写入正文与附录。|\n")
    dv = PAP / "deviations.md"
    t = dv.read_text(encoding="utf-8")
    if "| D16 |" not in t:
        t = t.replace("## test 评估次数（T08.02 第 3 条）", DEV + "\n## test 评估次数（T08.02 第 3 条）")
        dv.write_text(t, encoding="utf-8")
        print("deviations: D16 appended")

    import pandas as pd
    pd.DataFrame([{"quantity": k, "value": v} for k, v in list(rq.items()) + list(ct.items()) + list(vd.items())]
                 ).to_csv(PAP / "tables" / "table13_dense_comparator.csv", index=False)
    print("wrote tables/table13_dense_comparator.csv")


main()
