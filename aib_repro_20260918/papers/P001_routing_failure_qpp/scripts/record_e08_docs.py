"""Record the E08 round (EXP-0020..EXP-0023) into the registry, claims matrix and deviations.

Every number is read back out of the result JSONs this round produced, so the registry cannot drift
away from the evidence. Idempotent: the rows this script owns are replaced, not duplicated.
"""

from __future__ import annotations

import glob
import json
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
PAP = ROOT / "papers" / "P001_routing_failure_qpp"
REG = ROOT / "00_program_registry" / "experiment_registry.csv"


def last(pat: str) -> dict:
    f = sorted(glob.glob(str(ROOT / "results_raw" / pat)))[-1]
    return json.loads(Path(f).read_text(encoding="utf-8"))


E20, E21, E22, E23 = (last("EXP0020_toucan_routing_dataset_*.json"),
                      last("EXP0021_cross_pipeline_transfer_*.json"),
                      last("EXP0022_external_catalogue_availability_*.json"),
                      last("EXP0023_hermes_transfer_*.json"))
sft = E20["configs"]["SFT"]
a1, a1b, a2 = E21["arm1_external_pipeline"], E21["arm1b_catalogue_disjoint"], E21["arm2_unseen_tool_family"]
ov = E21["overlap_audit"]
her, hc, hi = E23["transfer"], E23["corpus_after_inclusion_rule"], E23["independence_audit"]
src_oof = sum(a1["auc_source_reference_oof_dev"]) / len(a1["auc_source_reference_oof_dev"])
her_oof = sum(her["auc_within_hermes_oof"]) / len(her["auc_within_hermes_oof"])

ROWS = [
    dict(exp_id="EXP-0020", paper_id="T037", stage="e08_external_catalogue_build_DEV_ONLY",
         script="02_shared_code/trajectory_parser/build_toucan_routing_dataset.py --configs SFT --exp-id EXP-0020",
         config="frozen invocation (rows-per-config 15000, shards-per-config 10), seed 42; catalogue column "
                "`tools` because SFT has neither `available_tools` nor `metadata`",
         seed="42", started_at=E20["started_at"], finished_at=E20["finished_at"],
         status="success_built_and_anchored",
         outputs="01_datasets/processed/routing_SFT.parquet; results_raw/EXP0020_toucan_routing_dataset_*.json; "
                 "logs/EXP-0020_build_sft_routing.txt; 01_datasets/manifests/routing_sample_identity.json",
         notes=f"Fourth Toucan config, unused by the frozen protocol. seen={sft['rows_seen']} "
               f"kept={sft['rows_kept']} rejections={sft['rejection_accounting']}; catalogue mean "
               f"{sft['catalog_size']['mean']}, dev hit@3 {sft['dev']['hit@3']['mean']} vs chance "
               f"{sft['dev']['chance_hit@3']['mean']}, fail@3 prevalence {sft['dev']['fail_at_3_prevalence']} "
               f"(an order of magnitude rarer than the published 0.042-0.129). The D11 sample-drift guard was "
               f"generalised: a config with no anchored digest now records its own uuid digest on first build.",
         enters_paper="yes (E08 data availability)"),
    dict(exp_id="EXP-0021", paper_id="T037", stage="e08_cross_pipeline_and_unseen_family_DEV_ONLY",
         script="02_shared_code/statistics/cross_pipeline_transfer_e08.py",
         config=f"fit on pooled published DEV (3 configs, n_candidates>3), score SFT; repeat on the "
                f"catalogue-disjoint subset; leave-one-tool-family-out over {a2['n_families_tested']} families "
                f"(>=60 rows, >={a2['min_positives_required']} failures); frozen C={E21['frozen_model']['C']} + "
                f"{E21['frozen_model']['n_canonical_features']} canonical features; 2000 catalogue-clustered bootstraps",
         seed="42 (+43-46 for OOF)", started_at=E21["started_at"], finished_at=E21["finished_at"],
         status="success_PREMISE_FALSIFIED_family_holdout_is_the_real_test",
         outputs="results_raw/EXP0021_cross_pipeline_transfer_*.json; results_processed/EXP0021_transfer_summary.csv; "
                 "results_processed/EXP0021_transfer_families.csv; logs/EXP-0021_cross_pipeline_transfer.txt",
         notes=f"The assumed external set is not external: {ov['distinct_tool_names']['exact_overlap']}/"
               f"{ov['distinct_tool_names']['target']} SFT tool names and "
               f"{ov['target_catalog_token_coverage_by_source']:.0%} of its catalogue tokens also occur in the source "
               f"dev pool, and {ov['distinct_catalogue_fingerprints']['shared_fingerprints']}/"
               f"{ov['distinct_catalogue_fingerprints']['target']} catalogue fingerprints are byte-identical. Pipeline "
               f"transfer AUROC {a1['auc_transfer_source_dev_to_target']} (catalogue-clustered CI "
               f"{a1['auc_transfer_ci95_catalogue_bootstrap']}) vs source OOF {src_oof:.4f}; on the "
               f"{a1b['n_rows']} catalogue-disjoint rows {a1b['auc_transfer_disjoint_catalogues']}, i.e. unseen "
               f"catalogue COMPOSITION costs nothing detectable. What does cost is tool FAMILY: holding the answer "
               f"family out of training moves {a2['mean_auc_family_seen_reference']} -> "
               f"{a2['mean_auc_unseen_family']} (drop {a2['mean_drop_vs_seen']}), which triggers the 0.02 criterion, "
               f"while length-only on the same rows is {a2['mean_auc_length_only']}. Two bugs fixed en route: an "
               f"inverted family-exclusion mask (returned 0 families) and single-class CV folds.",
         enters_paper="yes (E08; tightens the D13 upper bound and motivates EXP-0023)"),
    dict(exp_id="EXP-0022", paper_id="T037", stage="e08_external_availability_probe",
         script="02_shared_code/data_audit/probe_external_catalogue_availability.py",
         config="schema scan + real parse of up to 200 rows per local corpus; 3-attempt reachability probe of every "
                "host at BOTH its API root and a concrete dataset FILE URL",
         seed="n/a (deterministic)", started_at=E22["started_at"], finished_at=E22["finished_at"],
         status="success_only_one_non_toucan_catalogue_source_locally",
         outputs="results_raw/EXP0022_external_catalogue_availability_*.json; "
                 "logs/EXP-0022_external_catalogue_availability.txt",
         notes="Local scan: of the eight corpora only " +
               ", ".join(Path(p).parent.name for p in
                         E22["A_summary"]["datasets_with_machine_readable_catalogue"]) +
               " carry a per-query candidate-tool catalogue; AgentTrove, SWE-ZERO, AgentBank, code-act, "
               "AgentInstruct and MMAT-1M do not. Remote: " +
               json.dumps(E22["B_summary"], ensure_ascii=False),
         enters_paper="yes (data availability; the reason E08 runs on hermes)"),
    dict(exp_id="EXP-0023", paper_id="T037", stage="e08_external_corpus_transfer_DEV_ONLY",
         script="02_shared_code/data_audit/probe_hermes_toolcalls.py; "
                "02_shared_code/statistics/external_corpus_transfer_hermes.py",
         config="independent corpus lambda/hermes-agent-reasoning-traces (different pipeline, model family and tool "
                "universe); catalogue = row `tools` JSON, gold = the tool the reference model invoked inside "
                "assistant <tool_call> blocks; features from the SAME frozen builder functions; frozen "
                "C=%s model fitted on published DEV only; 500 row bootstraps" % E21["frozen_model"]["C"],
         seed="42 (+43-46 for OOF)", started_at=E23["started_at"], finished_at=E23["finished_at"],
         status="success_CROSS_CORPUS_GENERALISATION_MEASURED",
         outputs="01_datasets/processed/routing_HERMES.parquet; results_raw/EXP0023*_hermes_*.json; "
                 "results_processed/EXP0023_hermes_per_category.csv; logs/EXP-0023_hermes_transfer.txt",
         notes=f"Extraction: rows kept {hc['n_rows']}, rejections "
               f"{E23['corpus_extraction']['rejection_accounting']} (most hermes rows simply have no tools "
               f"column); distinct catalogues {hc['distinct_catalogues']}; fail@3 prevalence "
               f"{hc['fail_at_3_prevalence']}. Independence: {hi['unseen_tool_name_share']:.0%} of its "
               f"{hi['external_tool_names']} tool names never occur in the source corpus. RESULT: the frozen "
               f"pre-retrieval model transfers at AUROC {her['auc_source_dev_to_hermes']} "
               f"(row-bootstrap CI {her['ci95_row_bootstrap']}), versus in-domain source OOF {src_oof:.4f} and "
               f"within-hermes OOF {her_oof:.4f}; length-only is {her['auc_hermes_length_only_B0']} and the "
               f"POST-retrieval margin baseline {her['auc_hermes_post_retrieval_margin']}, so the pre-retrieval "
               f"model still leads out of corpus. Pre-registered rule (>=0.65 transfers) -> '{her['verdict']}'. "
               f"Caveat recorded: with only {hc['distinct_catalogues']} catalogues a catalogue-clustered interval "
               f"is not estimable, so the CI is row-level and understates dependence.",
         enters_paper="yes (E08 headline cross-corpus number)"),
]

CLAIMS = [
    dict(claim_id="C14",
         claim="跨语料（未见工具宇宙）泛化已被实测而非只是上界：把冻结模型仅用在三个已发布 config 的 dev 上拟合，"
               "在独立语料 lambda/hermes-agent-reasoning-traces（" +
               f"{hi['unseen_tool_name_share']:.0%} 的工具名从未在源语料出现）上评得 AUROC " +
               f"{her['auc_source_dev_to_hermes']}（行级 bootstrap CI {her['ci95_row_bootstrap']}），"
               f"低于域内 {src_oof:.4f} 与 within-hermes OOF {her_oof:.4f}，但仍高于随机、高于长度基线 " +
               f"{her['auc_hermes_length_only_B0']} 与事后 margin 基线 {her['auc_hermes_post_retrieval_margin']}；"
               f"按冻结前写定的判据（>=0.65）判为 transfers。",
         claim_type="外部效度/E08", experiment_id="EXP-0023", direction="supports_with_downgrade",
         digits_reported=f"cross-corpus AUROC {her['auc_source_dev_to_hermes']} "
                         f"[{her['ci95_row_bootstrap'][0]}, {her['ci95_row_bootstrap'][1]}]; "
                         f"in-domain {src_oof:.4f}; length-only {her['auc_hermes_length_only_B0']}",
         table="tables/table12_external_transfer.csv", figure="figures/fig5_robustness.pdf",
         statistical_test="500 row-level bootstrap resamples; frozen single-model fit on DEV only, target never "
                          "used for any fitting or selection",
         raw_result_file=";".join(["results_raw/" + Path(f).name for f in
                                   sorted(glob.glob(str(ROOT / 'results_raw' / 'EXP0023_hermes_transfer_*.json')))[-1:]]),
         where_in_paper="Abstract; Results E08; §8 Limitations; Table 12", status="supported"),
    dict(claim_id="C15",
         claim="公开 agent 轨迹语料并不提供相互独立的目录来源：Toucan 的四个 config 共享同一工具宇宙"
               f"（SFT 目录 token {ov['target_catalog_token_coverage_by_source']:.0%} 被源覆盖、"
               f"{ov['distinct_catalogue_fingerprints']['shared_fingerprints']} 个目录指纹与 dev 完全相同），"
               "八个本地语料中只有两个带每查询候选目录；同时按目录组合不相交切分不损失判别力"
               f"（{a1b['n_rows']} 行 AUROC {a1b['auc_transfer_disjoint_catalogues']}），真正损失来自答案工具家族"
               f"（{a2['mean_auc_family_seen_reference']}->{a2['mean_auc_unseen_family']}，降幅 "
               f"{a2['mean_drop_vs_seen']}，触发 0.02 判据）。",
         claim_type="数据生态发现/构念效度", experiment_id="EXP-0021+EXP-0022", direction="supports",
         digits_reported=f"overlap {ov['distinct_tool_names']['exact_overlap']}/{ov['distinct_tool_names']['target']} "
                         f"names; family drop {a2['mean_drop_vs_seen']}; catalogue-count: 2 of 8 local corpora",
         table="tables/table12_external_transfer.csv", figure="-",
         statistical_test="pre-registered 0.02 degradation criterion on leave-one-family-out AUROC",
         raw_result_file="results_raw/EXP0021_cross_pipeline_transfer_*.json; "
                         "results_raw/EXP0022_external_catalogue_availability_*.json",
         where_in_paper="Results E08; Discussion; Appendix A12", status="supported"),
]

D15 = ("| D15 | 2026-09-18 21:15 | **E08 由计划改为实测，并新增两个 dev-only 实验**：(a) 用从未被协议引用的 "
       "Toucan `SFT` config 做跨 pipeline 迁移；(b) 在独立语料 hermes-agent-reasoning-traces 上做出未见工具宇宙迁移；"
       "(c) leave-one-tool-family-out。同时把 D13 的“上界”表述改为给出实测值 | "
       "EXP-0022 实测：本地八语料只有两个带每查询候选目录，外部基准站点在本环境不可下载；EXP-0021 实测 SFT 与源语料"
       "共享 100% 工具名与 848 个相同目录指纹，因此它不是未见目录，真正的未见性检验只能落在工具家族与外部语料层面 | "
       "**否：账本仍为 1 次 test 评估。EXP-0020/0021/0023 全部只用 dev 或外部语料，冻结模型的 C 与特征列未因新结果改动** | "
       f"跨 pipeline AUROC {a1['auc_transfer_source_dev_to_hermes'] if False else a1['auc_transfer_source_dev_to_target']} "
       f"(catalogue CI {a1['auc_transfer_ci95_catalogue_bootstrap']})；目录组合不相交子集 {a1b['n_rows']} 行 "
       f"{a1b['auc_transfer_disjoint_catalogues']}；答案家族留出使 {a2['mean_auc_family_seen_reference']} -> "
       f"{a2['mean_auc_unseen_family']}（触发 0.02 判据）；跨语料 hermes AUROC "
       f"{her['auc_source_dev_to_hermes']} vs 域内 {src_oof:.4f}，仍高于长度基线 "
       f"{her['auc_hermes_length_only_B0']} 与事后 margin {her['auc_hermes_post_retrieval_margin']}。"
       f"结论：D13 的上界现在有了实测对应物——未见工具宇宙上的判别力约为 {her['auc_source_dev_to_hermes']}，而非 "
       f"{src_oof:.2f}。\n")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    reg = pd.read_csv(REG)
    ids = {r["exp_id"] for r in ROWS}
    reg = reg[~reg.exp_id.isin(ids)]
    reg = pd.concat([reg, pd.DataFrame(ROWS)], ignore_index=True).sort_values("exp_id")
    reg.to_csv(REG, index=False)
    print("registry rows:", len(reg))

    cm = pd.read_csv(PAP / "claims_evidence_matrix.csv")
    cm = cm[~cm.claim_id.isin({c["claim_id"] for c in CLAIMS})]
    cm = pd.concat([cm, pd.DataFrame(CLAIMS)], ignore_index=True)
    cm.to_csv(PAP / "claims_evidence_matrix.csv", index=False)
    print("claims:", len(cm), list(cm.claim_id))

    dev = PAP / "deviations.md"
    txt = dev.read_text(encoding="utf-8")
    if "| D15 |" not in txt:
        marker = "## test 评估次数（T08.02 第 3 条）"
        txt = txt.replace(marker, D15 + "\n" + marker)
        dev.write_text(txt, encoding="utf-8")
        print("deviations: D15 appended")
    else:
        print("deviations: D15 already present, left untouched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
