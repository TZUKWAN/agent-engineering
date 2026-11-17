"""Fold E03b (EXP-0024) into manuscript, appendix, limitations, SOTA audit, reviewer attack, final audit.

Every number is read from results_raw/EXP0024_dense_comparator_*.json; every edit asserts its anchor.
"""

from __future__ import annotations

import glob
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PAP = ROOT / "papers" / "P001_routing_failure_qpp"
E = json.loads(Path(sorted(glob.glob(str(ROOT / "results_raw" / "EXP0024_dense_comparator_*.json")))[-1])
               .read_text(encoding="utf-8"))
rq, ct = E["retrieval_quality"], E["construct_transfer_to_a_trained_ranker"]
DENSE_HIT, BM25_HIT = rq["hit_at_3_dense_trained"], rq["hit_at_3_bm25_frozen"]
JAC, SPEA = rq["positive_set_overlap_jaccard"], rq["spearman_dense_vs_bm25_rank"]
PER = max(ct["auc_model_trained_on_dense_failure_oof"])
CROSS = ct["auc_frozen_model_trained_on_bm25_failure__scored_on_dense_failure"]
LEN, DM = ct["auc_length_only_vs_dense_failure"], ct["auc_post_margin_dense_ranker_vs_dense_failure"]
PREV, WALL = ct["prevalence_fail_at_3_dense"], E["wallclock_sec"]
TOK = {"dense_hit": DENSE_HIT, "bm25_hit": BM25_HIT, "dense_rank": rq["mean_dense_best_rank"],
       "bm25_rank": rq["mean_bm25_best_rank"], "chance": rq["chance_hit_at_3"], "jaccard": JAC,
       "spearman": SPEA, "discordant": rq["discordant_rows"], "per_ranker_auc": PER, "len_auc": LEN,
       "dense_margin_auc": DM, "cross_auc": CROSS}


def sub(fname, old, new):
    p = PAP / fname
    t = p.read_text(encoding="utf-8")
    if new[:60] in t:
        print("  " + fname + ": already patched")
        return
    assert old in t, fname + ": anchor missing -> " + old[:55]
    p.write_text(t.replace(old, new, 1), encoding="utf-8")
    print("  " + fname + ": patched")


pm = PAP / "paper.md"
t = pm.read_text(encoding="utf-8")
if "## 7.7 E03b" not in t:
    body = (PAP / "scripts" / "a13_dense_template.md").read_text(encoding="utf-8")
    for k, v in TOK.items():
        body = body.replace("<<" + k + ">>", str(v))
    assert "<<" not in body, "unfilled token in the 7.7 template"
    pm.write_text(t.replace("## 8 What the results do not support",
                            body.strip() + "\n\n## 8 What the results do not support"), encoding="utf-8")
    print("  paper.md: 7.7 inserted")

OLD2 = ("Second, **failure is ranker-relative**: the positive sets of the primary and description-only DVs "
        "overlap only **3.4\u201310.6%**, so we describe our outcome as *lexical unreachability*, not as an "
        "objective routing failure.")
NEW2 = ("Second, **failure is ranker-relative**, and that now includes a trained ranker, not only a second frozen "
        "one: the primary and description-only DVs overlap only **3.4\u201310.6%**, and a two-tower dense model "
        "trained from scratch \u2014 the stronger ranker (hit@3 " + str(DENSE_HIT) + " vs " + str(BM25_HIT) +
        ") \u2014 shares only **" + str(JAC) + "** of its failure set with BM25. Refitting the same feature family "
        "on the dense outcome still predicts it (AUROC " + str(PER) + ", against length-only " + str(LEN) +
        " and the dense ranker's own score margin " + str(DM) + "), but the predictor trained on BM25 failures "
        "reaches only " + str(CROSS) + " on dense failures, below the 0.65 survival criterion fixed before "
        "training. We therefore describe the outcome as *lexical unreachability under a specified ranker* and do "
        "not claim a ranker-independent failure predictor (\u00a77.7, appendix A13).")
sub("paper.md", OLD2, NEW2)

A13 = ("## A13 E03b: a trained dense comparator (EXP-0024)\n\n"
       "**Why it exists.** Every ranking number in the paper is defined against one frozen lexical ranker, so "
       "\"failure\" could be an artifact of that ranker being weak. Pretrained encoders are unavailable here (no "
       "inference-API policy; torch is a CPU-only build although an RTX 3060 is present; no encoder library or "
       "weights downloadable \u2014 measured in EXP-0022 and recorded in the deviations correction). A "
       "from-scratch dense model is the strongest comparator this environment can actually produce, and it is "
       "reproducible from one script.\n\n"
       "**Model.** TF-IDF (min_df 3, cap 30k features, sublinear, l2) shared by both towers; two linear maps to " +
       str(E["model"]["dim"]) + " dimensions; cosine score; softmax over each row's own candidate set with every "
       "gold tool as a positive; Adam, " + str(E["model"]["steps"]) + " full-batch steps, lr " +
       str(E["model"]["lr"]) + ", seed 42; vocabulary fitted on the training fold only (" +
       str(E["model"]["vocab_size_per_fold"]) + " features). " + str(E["protocol"]["folds"]) + "-fold GroupKFold "
       "grouped on `prompt_id`, so every dense rank is out-of-fold. Wallclock " + str(WALL) + "s on CPU; no test "
       "row is read at any point.\n\n"
       "**Retrieval comparison.** hit@3 " + str(DENSE_HIT) + " (dense) vs " + str(BM25_HIT) + " (frozen BM25) "
       "against chance " + str(rq["chance_hit_at_3"]) + "; mean best gold rank " + str(rq["mean_dense_best_rank"]) +
       " vs " + str(rq["mean_bm25_best_rank"]) + "; dense failure prevalence " + str(PREV) + ". Spearman "
       "correlation between the rankers' per-query best ranks is " + str(SPEA) + " and the Jaccard overlap of "
       "their failure sets is " + str(JAC) + " (" + str(rq["discordant_rows"]) + " discordant rows).\n\n"
       "**Predictability, and where it breaks.** Refitting the frozen feature family on the dense outcome gives "
       "AUROC " + str(PER) + " (out-of-fold, two seeds) against length-only " + str(LEN) + " and the dense "
       "ranker's own top-1/top-2 cosine margin " + str(DM) + ". The predictor trained on BM25 failures and scored "
       "on dense failures gives " + str(CROSS) + ", i.e. no better than the ranker's own margin, so the "
       "pre-registered 0.65 criterion is **not met**; it is reported as a negative result rather than moving the "
       "threshold. Per-row ranks, margins and predicted risks: "
       "`results_processed/EXP0024_dense_vs_bm25.csv`; summary: `tables/table13_dense_comparator.csv`.\n\n")
sub("appendix.md", "## A11 Experiment inventory", A13 + "## A11 Experiment inventory")

L6NEW = ("| E03/B2 稠密强基线 | **已做（从零训练版，EXP-0024）**：双塔稠密模型在同一 dev 行集、同一 prompt_id 分组"
         "交叉验证下训练并与冻结 BM25 比较，dense hit@3 " + str(DENSE_HIT) + " > BM25 " + str(BM25_HIT) +
         "；两者失败集合 Jaccard 仅 " + str(JAC) + "；针对 dense 失败重训 AUROC " + str(PER) +
         "，但跨排序器迁移仅 " + str(CROSS) + "（低于事先设定的 0.65 判据，按负面结果报告，见 A13/§7.7）。"
         "预训练编码器仍不可得，原判定文字保留如下：**未做；已给出可核查的可行性判定（不是回避）**")
sub("limitations.md", "| E03/B2 稠密编码器强基线 | **未做；已给出可核查的可行性判定（不是回避）**", L6NEW)

SNEW = ("| B2+ 自训双塔稠密检索器（E03b/EXP-0024） | 同一 dev 行集、同一 prompt_id 分组交叉验证、无预训练权重 | "
        "**已运行**：dense hit@3 " + str(DENSE_HIT) + " vs BM25 " + str(BM25_HIT) + "（chance " +
        str(rq["chance_hit_at_3"]) + "）。因此本文不把\"优于 BM25\"当作贡献，也不与预训练编码器榜单比较；"
        "跨排序器预测迁移未达判据（见 A13） |\n"
        "| B2 强通用模型 | 稠密编码器（DPR/BGE 级）")
sub("sota_audit.md", "| B2 强通用模型 | 稠密编码器（DPR/BGE 级）", SNEW)

sub("reviewer_attack.md", "| A9 | **Are the baselines too weak?** | Mixed |",
    "| A9 | **Are the baselines too weak?** | **Answered with a trained ranker (EXP-0024, D16)** |")

FA1 = ("1. **No *pretrained* dense baseline.** A from-scratch two-tower dense comparator is now trained and "
       "compared (EXP-0024: hit@3 " + str(DENSE_HIT) + " vs BM25 " + str(BM25_HIT) + ") and it is stronger, which "
       "is reported as such; cross-ranker transfer of the predictor is not established (" + str(CROSS) +
       " < 0.65). Pretrained encoders remain unavailable, so no leaderboard comparison is made and the outcome "
       "stays ranker-relative.")
sub("final_audit.md", "1. **No dense/neural retrieval baseline.**", FA1)
sub("final_audit.md", "dense-baseline feasibility note \u2192 clean-environment",
    "~~dense-baseline feasibility note~~ **DONE (EXP-0024 trained comparator; cross-ranker transfer " +
    str(CROSS) + " < 0.65 reported as negative)** \u2192 pretrained-encoder availability note \u2192 "
    "clean-environment")
print("E03b documentation complete")
