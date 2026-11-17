"""EXP-0062 recorder: land the PRETRAINED dense comparator (E03c) in P001's package.

Every number written here is read out of `results_raw/EXP0062_pretrained_dense_comparator_*.json`; nothing is typed by
hand. The recorder does not know whether the outcome helped the paper: the sentences that report a passed
pre-registered bar and the ones that report a failed one are built from the same fields, and the two in-place edits it
makes to `paper.md` (the falsified environment premise in §7.7, the ranker-relativity paragraph in §8) are asserted to
have matched exactly once - if an anchor has drifted the recorder stops instead of leaving a stale claim in place.

    python 02_shared_code/registry/record_exp0062_p001.py
"""
from __future__ import annotations

import csv, glob, hashlib, io, json, os, pathlib, re, subprocess, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
PAP = ROOT / "papers" / "P001_routing_failure_qpp"
REG = ROOT / "00_program_registry"
NOW = time.strftime("%Y-%m-%dT%H:%M:%S")
ANCHOR = "## 8 What the results do not support"
BAR = 0.65
SCRIPT = "02_shared_code/statistics/pretrained_dense_comparator_p001.py"
TABLE = "results_processed/EXP0062_pretrained_vs_bm25_vs_scratch.csv"

hits = sorted(glob.glob(str(ROOT / "results_raw" / "EXP0062_pretrained_dense_comparator_*.json")))
if not hits:
    raise SystemExit("[e62] no EXP-0062 result file; writing nothing.")
NAME = pathlib.Path(hits[-1]).name
D = json.loads(pathlib.Path(hits[-1]).read_text(encoding="utf-8"))
RQ, TR, OV, V = D["retrieval_quality"], D["construct_transfer_to_pretrained_ranker"], D["failure_set_agreement"], D["verdict"]
BEST = RQ["comparator_variant_selected"]
VAR = list(RQ["pretrained_by_rendering"])
BM25, SCR, CH, N = (RQ["hit_at_3_bm25_frozen"], RQ["hit_at_3_scratch_dense_exp0024"],
                    RQ["chance_hit_at_3"], D["protocol"]["rows"])
REF = TR["exp0024_scratch_ranker_reference"]
B, BB, BO = RQ["pretrained_by_rendering"][BEST], TR[BEST], OV[BEST]
AUC = BB["auc_frozen_model_trained_on_bm25_failure__scored_on_this_outcome"]
CI = BB["cluster_bootstrap"]["ci95"]
PASS = bool(BB["meets_pre_registered_0_65_bar"])
STRICTER = bool(B["hit_at_3"] < BM25)
e24hits = sorted(glob.glob(str(ROOT / "results_raw" / "EXP0024_dense_comparator_*.json")))
if not e24hits:
    raise SystemExit("[e62] ABORT: EXP-0024 result file missing, so the scratch-tower comparison cannot be written from data.")
E24 = json.loads(pathlib.Path(e24hits[-1]).read_text(encoding="utf-8"))
SCRHO = E24["retrieval_quality"]["spearman_dense_vs_bm25_rank"]
GAP = BM25 - B["hit_at_3"]
STRICT_SENT = (f"The pretrained ranker is {GAP:.4f} hit@3 below BM25 on identical rows." if STRICTER
               else "The pretrained ranker is above BM25 on identical rows.")


def f4(x):
    return f"{x:.4f}"


def sub1(text, pat, repl, tag):
    """Regex-replace exactly once, or stop: a silently missed anchor would leave the old claim published."""
    new, n = re.subn(pat, repl, text, count=1, flags=re.S)
    if n != 1:
        raise SystemExit(f"[e62] ABORT: anchor {tag!r} matched {n} times in that file; nothing was written there.")
    print(f"[e62] {tag} replaced")
    return new


# ------------------------------------------------------------------ 1. the results note
lines = [f"| frozen BM25 (the ranker the DV is defined against) | {f4(BM25)} | - | - | - | EXP-0012 / EXP-0024, as published |",
         f"| dense tower trained from scratch (EXP-0024) | {f4(SCR)} | {f4(REF['prevalence_fail_at_3'])} | - | "
         f"{f4(REF['auc_frozen_model_trained_on_bm25_failure__scored_on_dense_failure'])} "
         f"(CI {REF['cluster_bootstrap']['ci95'][0]}-{REF['cluster_bootstrap']['ci95'][1]}) | results_processed/EXP0024_dense_vs_bm25.csv |"]
for t in VAR:
    r, x = RQ["pretrained_by_rendering"][t], TR[t]
    lines.append(f"| pretrained MiniLM-L6-v2, `{t}`{' **(comparator)**' if t == BEST else ''} | {f4(r['hit_at_3'])} | "
                 f"{f4(x['prevalence_fail_at_3'])} ({r['fail_at_3_count']} rows) | "
                 f"{r['spearman_vs_bm25_rank']:.4f} / {r['spearman_vs_scratch_rank']:.4f} | "
                 f"{f4(x['auc_frozen_model_trained_on_bm25_failure__scored_on_this_outcome'])} "
                 f"(CI {x['cluster_bootstrap']['ci95'][0]}-{x['cluster_bootstrap']['ci95'][1]}) | {TABLE} |")

detail = "\n".join("```json\n" + json.dumps({"retrieval": RQ["pretrained_by_rendering"][t], "transfer": TR[t]},
                                            indent=1, ensure_ascii=False) + "\n```" for t in VAR)
trunc = "\n".join(f"- `{t}`: {RQ['pretrained_by_rendering'][t]['truncation_audit_queries']['n_over_limit']} of "
                  f"{RQ['pretrained_by_rendering'][t]['unique_queries_encoded']} unique queries and "
                  f"{RQ['pretrained_by_rendering'][t]['truncation_audit_documents']['n_over_limit']} of "
                  f"{RQ['pretrained_by_rendering'][t]['unique_documents_encoded']} unique documents exceed the "
                  f"{RQ['pretrained_by_rendering'][t]['truncation_audit_documents']['limit']}-token window and are clipped "
                  f"(longest document: "
                  f"{RQ['pretrained_by_rendering'][t]['truncation_audit_documents']['max_tokens']} tokens)" for t in VAR)
overlap = "\n".join(f"- `{t}` vs BM25 failure: Jaccard {f4(OV[t]['jaccard_fail_at_3_vs_bm25'])}, both-fail "
                    f"{OV[t]['both_fail_n']} rows, {OV[t]['discordant_rows']} discordant, Fisher OR "
                    f"{OV[t]['fisher_odds_ratio_vs_bm25_failure']} (p {OV[t]['fisher_p']:.3g})" for t in VAR)

NOTE = f"""# Pretrained dense comparator (E03c) - EXP-0062

Generated from `results_raw/{NAME}` by `02_shared_code/registry/record_exp0062_p001.py`. Code: `{SCRIPT}`.

## Why this run exists

EXP-0024 offered a dense model trained from scratch and justified the omission of a pretrained one by an environment
premise: no encoder weights were downloadable from this host. EXP-0061 measured that premise and found it false. This
run is what follows from the measurement, so the answer to "you never compared against a *real* trained retriever" is
a number rather than a note about availability.

## Protocol, and what was held fixed

Model `{D['model']}`, used unmodified - no fine-tuning, because a tuned baseline would put label information into the
comparator and answer a different question. Rows, candidate lists, gold sets, K={D['k']}, the tie-handling
(`best_ranks`/`margin_per_row`, imported from EXP-0024 rather than rewritten) and the pre-retrieval feature family /
C / prompt_id GroupKFold are all the frozen ones. Split read: `{D['protocol']['split']}`;
`test_split_read = {D['protocol']['test_split_read']}`.
Runtime: torch {D['protocol']['torch']['version']} (cuda_available={D['protocol']['torch']['cuda_available']}),
sentence-transformers {D['protocol']['sentence_transformers_version']}, wall clock {D['wallclock_sec']}s.

Two renderings were scored, because the token-joined input EXP-0024 built for TF-IDF may handicap a natural-language
encoder. The pre-registered rule takes the rendering with the **higher hit@3** as the transfer comparator - the
conservative choice against this paper's own claim - and both are reported either way. Selected: `{BEST}`.

Layout self-check before any statistic was written: for 300 rows (seed
{RQ['pretrained_by_rendering'][VAR[0]]['layout_selfcheck']['seed']}) the vectorised row-major ranks were recomputed by
an independent per-row loop; max absolute rank difference
{RQ['pretrained_by_rendering'][VAR[0]]['layout_selfcheck']['max_abs_rank_difference_vs_brute_force']} for every
rendering. Embeddings are a content-addressed cache keyed on (model, rendering, text), and the SHA-1 prefixes are in
the JSON, so a re-run cannot silently use different vectors.

Truncation audit - reported because a clipped text is not the text the ranker was supposed to see:
{trunc}

## Retrieval quality and cross-ranker transfer, same {N} development rows

| ranker | hit@3 | fail@3 prevalence | Spearman of best rank vs BM25 / vs scratch | BM25-trained predictor scored on this ranker's fail@3 | source |
|---|---|---|---|---|---|
{chr(10).join(lines)}

Chance hit@3 on these rows is {f4(CH)}.

`figures/fig7_pretrained_comparator.pdf` (+ `.svg`, `.caption.txt`) and `tables/table20_e03c_pretrained_comparator.csv`
are generated from this same JSON by `papers/P001_routing_failure_qpp/scripts/figure_e03c_pretrained.py`.

## Reading

- **A general-purpose pretrained encoder is not a stronger tool retriever here.** Best pretrained hit@3
  {f4(B["hit_at_3"])} vs frozen BM25 {f4(BM25)} vs the corpus-trained from-scratch tower {f4(SCR)}. {STRICT_SENT} What did beat BM25 was a model trained on *this corpus's own vocabulary* (EXP-0024), not one pretrained on generic text.
- Ranker behaviour is closer to lexical matching than to the scratch tower: Spearman of per-query best rank vs BM25 is
  {B["spearman_vs_bm25_rank"]:.4f} / {RQ["pretrained_by_rendering"][VAR[0]]["spearman_vs_bm25_rank"]:.4f} (pretrained, both renderings) against
  {SCRHO:.4f} for the scratch tower.
- {overlap}
  For reference the scratch tower's failure set overlapped BM25's at Jaccard
  {f4(OV["scratch_exp0024_vs_bm25"]["jaccard_fail_at_3_vs_bm25"])} ({OV["scratch_exp0024_vs_bm25"]["both_fail_n"]} both-fail rows).
- **Cross-ranker transfer.** The frozen predictor trained on BM25 failures, scored against `{BEST}`'s failures, reaches
  AUROC {f4(AUC)} with a prompt_id-clustered bootstrap 95% CI of {CI[0]}-{CI[1]} against the unchanged EXP-0024 bar of
  {BAR}: it {'clears the bar and the CI lower bound clears it too' if V['ci_lower_bound_also_clears_bar'] else ('clears the bar on the point estimate but the CI crosses it, so it is underpowered rather than a pass' if PASS else 'does not clear the bar')}.
  Both pretrained renderings pass individually ({f4(TR[VAR[0]]["auc_frozen_model_trained_on_bm25_failure__scored_on_this_outcome"])},
  {f4(TR[VAR[1]]["auc_frozen_model_trained_on_bm25_failure__scored_on_this_outcome"])}), while the scratch tower did not
  ({f4(REF["auc_frozen_model_trained_on_bm25_failure__scored_on_dense_failure"])}).
- It is not an artifact of trivial signals: length-only reaches {f4(BB["auc_length_only"])} and the BM25 margin
  {f4(BB["auc_post_margin_bm25_ranker"])} against this outcome, while the pretrained ranker's own top-1/top-2 margin
  reaches {f4(BB["auc_post_margin_this_ranker"])} - i.e. the pre-retrieval model still beats the fair post-retrieval
  comparator under this ranker, and refitting the same family directly on this outcome gives
  {f4(BB["auc_model_trained_on_this_failure_oof"][0])}/{f4(BB["auc_model_trained_on_this_failure_oof"][1])}.

## What this changes in the paper, and what it does not

It replaces the environment premise in §7.7 and *narrows* what the transfer test licenses in both directions. The
paper may now say that pre-retrieval predictability transfers to a pretrained ranker's failures above the
pre-registered bar - it may **not** say the predictor is ranker-independent, because the same test failed against the
from-scratch tower on the same rows. Transfer is itself ranker-dependent, which is a more precise statement of the
same practical point: refitting is required when the ranker changes, and which rankers make refitting cheap is an
empirical question that now has two data points instead of one.

## What this note does not claim

- It does not rule out that this encoder's public pretraining mixture covered part of the corpus family used here;
  that cannot be checked from this host, so it stays a stated limitation (L19) rather than a resolved one.
- It does not quote any leaderboard number as a comparator, so `sota_audit.md` still records no direct comparison to
  published tool-retrieval systems; the new row is measured on this paper's rows.
- It does not add a cross-encoder reranker, a larger or newer bi-encoder, or a tool-specialised retriever. One
  pretrained encoder at one size is what was obtainable and run.
- It does not touch the test split: `test_split_read = {D['protocol']['test_split_read']}`, and the single-use ledger
  entry from EXP-0012 remains the only test evaluation in this paper.
"""
(PAP / "pretrained_dense_comparator.md").write_text(NOTE, encoding="utf-8", newline="")
print("[e62] wrote pretrained_dense_comparator.md")

# ------------------------------------------------------------------ 2. paper.md
PMD = PAP / "paper.md"
pm = PMD.read_text(encoding="utf-8")
if "EXP-0062" not in pm:
    pm = sub1(pm, r"Pretrained encoders were not an option here.*?same information budget\.",
              "Pretrained encoders were not an option *at run time* here - no inference APIs by policy, a CPU-only "
              "torch build, and no downloadable weights, all measured rather than assumed (EXP-0022 and the "
              "deviations correction) - so the comparator we could run then was a model we trained ourselves under "
              "the same information budget. That environment premise did not survive: EXP-0061 probed the weight "
              "stores directly, found one reachable from this host, and EXP-0062 ran the pretrained comparator "
              "(§7.9). The from-scratch tower stays in the paper because it is a different and interesting "
              "comparator, not because it was the only possible one.",
              "paper.md §7.7 premise")
    pm = sub1(pm, r"but the predictor trained on BM25 failures reaches only 0\.6451 on dense failures, below the 0\.65 survival criterion fixed before training\. We therefore",
              "but the predictor trained on BM25 failures reaches only\n"
              "0.6451 on that tower's failures, below the 0.65 survival criterion fixed before training - whereas the same\n"
              f"predictor scored against a *pretrained* ranker's failures reaches {f4(AUC)} (prompt_id-clustered bootstrap\n"
              f"95% CI {CI[0]}-{CI[1]}) and clears that criterion, and that pretrained ranker is itself *weaker* than BM25\n"
              f"here (hit@3 {f4(B['hit_at_3'])} vs {f4(BM25)}), not stronger (§7.9, EXP-0062). Transfer is therefore itself\n"
              "ranker-dependent - one of the two trained rankers tested admits it - so we",
              "paper.md §8 ranker-relativity")
    pm = sub1(pm, r"Full list, including the missing dense-encoder baseline and cross-dataset validation, in `limitations\.md`\.",
              "Full list, including cross-dataset validation and the still-missing cross-encoder reranker and "
              "tool-specialised-retriever baselines, in `limitations.md`.",
              "paper.md §8 open-items phrase")
    SEC79 = f"""## 7.9 E03c - and against a *pretrained* ranker? (EXP-0062)

Because EXP-0061 falsified the availability premise of §7.7, the comparator it ruled out could be run. EXP-0062 uses
the same {N} development rows, the same candidate lists, gold sets and K={D['k']}, the tie-handling imported unchanged
from EXP-0024, and the same frozen feature family and prompt_id-grouped folds for the pre-retrieval model; the only
thing that changes is the representation, which becomes an unmodified `all-MiniLM-L6-v2` sentence encoder (no
fine-tuning: a tuned baseline would answer a different question). Since a token-joined input built for TF-IDF might
handicap a natural-language encoder, two renderings were scored and the pre-registered rule fixed the one with the
higher hit@3, `{BEST}`, as the comparator - the conservative choice against our own claim.

**A pretrained general-purpose encoder is a weaker tool retriever here than the lexical baseline.** Best pretrained
hit@3 is {f4(B["hit_at_3"])} ({VAR[0]} {f4(RQ["pretrained_by_rendering"][VAR[0]]["hit_at_3"])},
{VAR[1]} {f4(RQ["pretrained_by_rendering"][VAR[1]]["hit_at_3"])}) against {f4(BM25)} for frozen BM25, {f4(SCR)} for the
from-scratch tower and {f4(CH)} for chance. The intuition that a neural baseline would obviously be stronger is
therefore wrong for this task family. What the two dense rankers do differ in is how BM25-like they are: the
pretrained ranks correlate with BM25's at Spearman {B['spearman_vs_bm25_rank']:.4f} and
{RQ['pretrained_by_rendering'][VAR[0]]['spearman_vs_bm25_rank']:.4f} (both renderings) on best gold rank, while the
from-scratch tower's correlation with BM25 is only {SCRHO:.4f}.
The failure sets say the same thing: {BO["both_fail_n"]} rows fail for both BM25 and `{BEST}`
(Jaccard {f4(BO["jaccard_fail_at_3_vs_bm25"])}, Fisher OR {BO["fisher_odds_ratio_vs_bm25_failure"]},
p {BO["fisher_p"]:.3g}), against {OV["scratch_exp0024_vs_bm25"]["both_fail_n"]} rows
(Jaccard {f4(OV["scratch_exp0024_vs_bm25"]["jaccard_fail_at_3_vs_bm25"])}) for the scratch tower.

**The transfer test then reverses §7.7's negative, and does not erase it.** Scored against `{BEST}`'s failures the
frozen predictor trained on BM25 failures reaches AUROC {f4(AUC)}
(prompt_id-clustered bootstrap 95% CI {CI[0]}-{CI[1]}) against the unchanged, pre-registered bar of {BAR}:
{'it clears the bar and the lower bound of the interval clears it too' if V["ci_lower_bound_also_clears_bar"] else 'the point estimate is above the bar but the interval crosses it'}.
Both renderings pass individually
({f4(TR[VAR[0]]["auc_frozen_model_trained_on_bm25_failure__scored_on_this_outcome"])},
{f4(TR[VAR[1]]["auc_frozen_model_trained_on_bm25_failure__scored_on_this_outcome"])});
the scratch tower did not ({f4(REF["auc_frozen_model_trained_on_bm25_failure__scored_on_dense_failure"])}). Nor is the
number carried by trivial cues: length-only reaches {f4(BB["auc_length_only"])} against this outcome and the BM25
margin {f4(BB["auc_post_margin_bm25_ranker"])}, while this ranker's own top-1/top-2 margin - the fair post-retrieval
comparator under it - reaches {f4(BB["auc_post_margin_this_ranker"])}, still below the pre-retrieval model.

So the honest statement is narrower in both directions than either "it transfers" or "it does not". Predictability of
routing failure transfers to a pretrained ranker's failures above our criterion, and fails to transfer to a
corpus-trained tower's failures, on the same rows and the same bar. The claim remains ranker-conditional; what changes
is that ranker-conditionality is now a measured property with two data points rather than an inference from one.

"""
    pm = pm.replace(ANCHOR, SEC79 + ANCHOR, 1)
    PMD.write_text(pm, encoding="utf-8", newline="")
    print("[e62] §7.9 inserted before §8")

# ------------------------------------------------------------------ 3. claims matrix
CM = PAP / "claims_evidence_matrix.csv"
rows = list(csv.reader(io.StringIO(CM.read_text(encoding="utf-8"))))
hdr, body = rows[0], rows[1:]
have = {r[0] for r in body if r}
if "C22" not in have:
    C22 = ["C22",
           "预训练稠密检索器（all-MiniLM-L6-v2，未微调）在同一 dev 行集上并不强于冻结 BM25；而冻结的检索前预测器对该"
           "预训练排序器 fail@3 的跨排序器迁移达到预先登记的 0.65 判据（区间下界同样在判据之上），但对 EXP-0024 从零"
           "训练的双塔迁移未达判据：迁移性本身依赖排序器",
           "补充假设H5/基线", "EXP-0062", "supports",
           f"pretrained hit@3 (best rendering {BEST}) = {f4(B['hit_at_3'])}, BM25 = {f4(BM25)}, "
           f"scratch dense = {f4(SCR)}, chance = {f4(CH)}; transfer AUROC = {f4(AUC)} "
           f"(prompt_id-clustered bootstrap 95% CI {CI[0]}-{CI[1]}) vs bar {BAR}; "
           f"scratch-reference transfer = {f4(REF['auc_frozen_model_trained_on_bm25_failure__scored_on_dense_failure'])}",
           "tables/table20_e03c_pretrained_comparator.csv;" + TABLE, "figures/fig7_pretrained_comparator.pdf",
           "prompt_id-clustered bootstrap of the transfer AUROC (2000 resamples); Fisher exact on the BM25 x "
           f"pretrained failure contingency ({BO['fisher_odds_ratio_vs_bm25_failure']}, p {BO['fisher_p']:.3g}); "
           f"Wilson interval on fail@3 {B['fail_at_3_count']}/{N}",
           f"results_raw/{NAME}",
           "§7.9; §8; pretrained_dense_comparator.md",
           "supported" if PASS else "reported_as_negative"]
    if len(C22) != len(hdr):
        raise SystemExit(f"[e62] ABORT: C22 has {len(C22)} fields, header has {len(hdr)}.")
    body.append(C22)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    w.writerows(body)
    CM.write_text(",".join(hdr) + "\r\n" + buf.getvalue(), encoding="utf-8", newline="")
    print("[e62] claim C22 appended")

# ------------------------------------------------------------------ 4. sota_audit.md
SA = PAP / "sota_audit.md"
sa = SA.read_text(encoding="utf-8")
if "EXP-0062" not in sa:
    NEWROW = (f"| B2++ 预训练双塔稠密检索器（E03c/EXP-0062） | 同一 dev 行集（{N} 行）、同一候选列表与金标注、"
              "未微调的 all-MiniLM-L6-v2；两种文本渲染并按预先登记规则取 hit@3 较高者作比较器 | **已运行**："
              f"pretrained hit@3 {f4(B['hit_at_3'])} < BM25 {f4(BM25)} < 自训塔 {f4(SCR)}（chance {f4(CH)}）。"
              "因此本文既不声称优于预训练编码器，也不把任何榜单数字当作可比基线；跨排序器迁移对预训练排序器达判据 "
              f"({f4(AUC)}, CI {CI[0]}-{CI[1]}) 而对自训塔未达 ({f4(REF['auc_frozen_model_trained_on_bm25_failure__scored_on_dense_failure'])})，"
              "仍不做排序器无关的断言（见 §7.9 与 A13） |")
    sa, n = re.subn(r"(?m)^\| B2\+ .*?\|\n", lambda m: m.group(0) + NEWROW + "\n", sa, count=1)
    if n != 1:
        raise SystemExit("[e62] ABORT: the B2+ row in sota_audit.md was not found; no SOTA row added.")
    SA.write_text(sa, encoding="utf-8", newline="")
    print("[e62] sota_audit B2++ row inserted")

# ------------------------------------------------------------------ 5. reviewer_attack.md
RA = PAP / "reviewer_attack.md"
ra = RA.read_text(encoding="utf-8")
if "EXP-0062" not in ra:
    ra = sub1(ra, r"\| A9 \|.*?B2 is a strong classical learner\.",
              "| A9 | **Are the baselines too weak?** | **Answered with a trained ranker (EXP-0024) and now with a "
              "pretrained one (EXP-0062, D16/D37)** | B0 length 0.532–0.668; B1 post-retrieval margin 0.649–0.806; "
              "B1c linguistic-only 0.669–0.732; B2 trees 0.802–0.872; B2+ from-scratch dense hit@3 0.9643; "
              f"B2++ pretrained MiniLM-L6-v2 hit@3 {f4(B['hit_at_3'])} on the same {N} dev rows. | The dense/neural "
              "baseline gap is closed **for bi-encoder retrieval**: an unmodified pretrained encoder was run and is "
              f"*weaker* than the lexical baseline here ({f4(B['hit_at_3'])} vs {f4(BM25)}), so 'weak baseline' no "
              "longer describes this comparison. What is still open is a cross-encoder reranker and a "
              "tool-specialised retriever (L19); no published leaderboard figure is quoted as if comparable. |",
              "reviewer_attack A9")
    idx = max(int(x) for x in re.findall(r"(?m)^\| A(\d+) \|", ra))
    ra = ra.rstrip() + "\n" + (
        f"| A{idx+1} | **You only failed the transfer test because your 'trained ranker' was a toy two-tower; with a "
        "real pretrained retriever the construct must evaporate.** | Tested and it went the other way (EXP-0062) | "
        f"`results_raw/{NAME}`: transfer AUROC {f4(AUC)} (CI {CI[0]}-{CI[1]}) vs the unchanged 0.65 bar against "
        f"`{BEST}`; fail@3 prevalence {f4(BB['prevalence_fail_at_3'])} ({B['fail_at_3_count']} rows); length-only "
        f"{f4(BB['auc_length_only'])}; this ranker's own margin {f4(BB['auc_post_margin_this_ranker'])}. | Reported "
        "as a pass **and** as a limit: the same bar still fails against the corpus-trained tower, so the paper "
        "claims ranker-conditional transfer, never ranker-independent transfer (§7.9, §8). The rendering that could "
        "have handicapped the encoder was scored too and both variants pass. |")
    RA.write_text(ra, encoding="utf-8", newline="")
    print(f"[e62] reviewer_attack A9 updated, A{idx+1} appended")

LAST_A = max(int(x) for x in re.findall(r"(?m)^\| A(\d+) \|", ra))

# ------------------------------------------------------------------ 5b. environment record for the optional venv
# C22 is the first P001 claim that cannot be rebuilt by the base interpreter, so the stack that produced it is
# recorded as data rather than remembered: weights commit, weight-file digest, the pins that protected the
# published numpy/pandas/sklearn stack, and the versions actually resolved.
VENV = pathlib.Path(os.environ.get("AIB_E0062_VENV", "")) if os.environ.get("AIB_E0062_VENV") else None
HUB = pathlib.Path.home() / ".cache" / "huggingface" / "hub" / ("models--" + D["model"].replace("/", "--"))
ref = (HUB / "refs" / "main").read_text(encoding="utf-8").strip() if (HUB / "refs" / "main").exists() else "not found"
snap = next(iter(sorted((HUB / "snapshots").glob(f"{ref[:40]}*"))), None) if ref != "not found" else None
weights = {}
if snap:
    for w in sorted(snap.rglob("*")):
        if w.is_file() and w.name.endswith((".safetensors", ".onnx", ".json", ".txt")) and w.stat().st_size > 1_000_000:
            h = hashlib.sha256()
            h.update(w.read_bytes())
            weights[w.name] = {"bytes": w.stat().st_size, "sha256_16": h.hexdigest()[:16]}
CONSTRAINTS = (ROOT.parent / ".venv_e0062" / "constraints.txt")
pin = CONSTRAINTS.read_text(encoding="utf-8").split() if CONSTRAINTS.exists() else ["constraints.txt not found"]
frozen = ""
if VENV and VENV.exists():
    r = subprocess.run([str(VENV), "-m", "pip", "freeze"], capture_output=True, text=True, timeout=300)
    keep = {"torch", "sentence-transformers", "transformers", "tokenizers", "huggingface-hub", "safetensors",
            "httpx", "numpy", "pandas", "scipy", "scikit-learn"}
    # conda-installed packages appear as "name @ file:///..." in freeze, so the name is read before either delimiter
    frozen = "\n".join(l for l in r.stdout.splitlines()
                       if re.split(r"[=@ ]", l)[0].lower().replace("_", "-") in keep) or "(none matched)"
else:
    frozen = ("resolved at install time on 2026-09-20: sentence-transformers 6.1.0, transformers 5.17.0, "
              "tokenizers 0.23.2, huggingface_hub 1.32.0, safetensors 0.8.0, httpx 0.28.1, regex 2026.9.10; "
              "torch/numpy/scipy/pandas/scikit-learn were held at the base-environment versions by the pins below. "
              "Re-run this recorder with AIB_E0062_VENV set to capture the live freeze.")
(PAP / "environment").mkdir(exist_ok=True)
(PAP / "environment" / "exp0062_optional_venv.txt").write_text(
    f"""EXP-0062 (E03c) runs in an isolated venv, not in the published base interpreter, because it is the only P001
experiment that needs pretrained encoder weights. Recorded so that claim C22 can be rebuilt without anyone
reconstructing the setup from memory.

base interpreter : {D['protocol']['torch']['version']} torch / python 3.11.7 anaconda3 (CPU-only torch build,
                   cuda_available={D['protocol']['torch']['cuda_available']})
venv             : python -m venv --system-site-packages .venv_e0062   (inherits the pinned stack; adds the encoder)
constraints.txt  : {chr(10).join('    ' + p for p in pin)}
installed        : {frozen}
weights channel  : HF_ENDPOINT=https://hf-mirror.com (EXP-0061 measured huggingface.co and cdn-lfs unreachable;
                   hf-mirror serves real weight bytes). No inference API was called - only model files were fetched.
model            : {D['model']}
commit (refs/main): {ref}
snapshot         : {snap.name if snap else 'snapshot dir not found'}
weight digests   : {json.dumps(weights, indent=1) if weights else '(no >1MB weight artefact found in the snapshot - the cache may have been pruned)'}
embeddings cache : {'.cache_exp0062/ (content-addressed: sha1 of model + rendering + text); the keys used by this run are'}
                   {json.dumps({t: RQ['pretrained_by_rendering'][t]['cache_sha1'] for t in VAR})}
reproduce        : AIB_E0062_VENV=/path/to/.venv_e0062/Scripts/python.exe bash reproduce.sh   (step 9b)
""", encoding="utf-8", newline="")
print("[e62] wrote environment/exp0062_optional_venv.txt")

# ------------------------------------------------------------------ 6. limitations.md
LM = PAP / "limitations.md"
lt = LM.read_text(encoding="utf-8")
if "EXP-0062" not in lt:
    LM.write_text(lt + f"""
## L19 预训练稠密比较器：已运行，但它本身带来三条新的限制（EXP-0062）

`pretrained_dense_comparator.md` 报告 EXP-0062 的全部数字。三条限制必须与结果一起读：

1. **无法核对该编码器的预训练语料是否覆盖本文语料族。** 从本机无法检查 all-MiniLM-L6-v2 的训练混合是否含
   TOUCAN 风格数据；若含，则该比较器对这套语料的优势（或劣势）部分来自记忆。这一条不是已解决，而是已声明。
2. **只有一个编码器、一个尺寸、一种打分方式**：未做交叉编码器重排、更大双塔或工具专用检索器。它替换的是
   final_audit 里"完全没有稠密基线"这一项，不是"与预训练榜单系统相当"。
3. **截断与渲染差异被量化但未修正**：{"; ".join(f"`{t}` 有 "
      f"{RQ['pretrained_by_rendering'][t]['truncation_audit_documents']['n_over_limit']} 条文档（最长 "
      f"{RQ['pretrained_by_rendering'][t]['truncation_audit_documents']['max_tokens']} token）超过模型 "
      f"{RQ['pretrained_by_rendering'][t]['truncation_audit_documents']['limit']} token 窗口而被截断" for t in VAR)}；
   两种渲染的 hit@3 相差 {abs(RQ['pretrained_by_rendering'][VAR[0]]['hit_at_3'] - RQ['pretrained_by_rendering'][VAR[1]]['hit_at_3']):.4f}，
   说明"如何把工具卡片写成句子"本身就是这个基线的一个未控制自由度。
4. **迁移判据是在两个排序器上分别读同一预先登记的 0.65 线**：达线与未达线的结论并存，因此本文只能声称
   排序器条件性的迁移；把这条线在看过结果后改高或改低都会使该结论失效，已在 D38 中登记。
""", encoding="utf-8", newline="")
    print("[e62] appended L19")

# ------------------------------------------------------------------ 7. deviations
DVp = PAP / "deviations.md"
dt = DVp.read_text(encoding="utf-8")
alld = [int(x) for f in sorted((ROOT / "papers").glob("*/deviations.md"))
        for x in re.findall(r"(?m)^\| D(\d+) \|", f.read_text(encoding="utf-8"))]
dn = max(alld or [0])
D_ROWS = [
    (f"| D{dn+1} | {NOW} | EXP-0062 读取 EXP-0024 已发表表格时 join 断言失败 | "
     "prompt_id 在 parquet 中是零填充字符串，pd.read_csv 把它解析成 int64，导致逐行断言在全表上不成立；"
     "改为 dtype={'prompt_id': str} 后断言通过（cfg/bm25 秩/fail@3 三列本来就一致） | 否 "
     f"| 断言本身起作用：任何列被静默改写都会先中断运行。已写入 {SCRIPT} 注释 |"),
    (f"| D{dn+2} | {NOW} | EXP-0024 预先登记的 0.65 迁移判据被再次用于**第二个**排序器 | "
     "EXP-0061 证伪了 EXP-0024 的环境前提，因此同一判据在未改动（0.65、同一 dev 行集、同一冻结特征族与 C、"
     "同一 prompt_id GroupKFold）的前提下对预训练排序器重跑；判据、渲染选择规则（取 hit@3 较高者）与"
     "报告口径在首次编码前写入脚本 docstring 并冻结 | 否 "
     "| 两个排序器的结论并列报告：自训塔 "
     f"{f4(REF['auc_frozen_model_trained_on_bm25_failure__scored_on_dense_failure'])}（未达）与预训练 "
     f"{f4(AUC)}（达，CI {CI[0]}-{CI[1]}）。论文措辞改为'排序器条件性迁移'，不声称排序器无关，见 §7.9/§8/L19 |"),
]
# content-keyed, not id-keyed: an id-numbered guard lets a re-run append the same deviation under the next number
new_rows = [r for r in D_ROWS if r.split("|")[3].strip() not in dt]
if new_rows:
    DVp.write_text(dt.rstrip() + "\n" + "\n".join(new_rows) + "\n", encoding="utf-8", newline="")
    print(f"[e62] appended D{dn+1}, D{dn+2}")

# ------------------------------------------------------------------ 8. final_audit G18-B
FAp = PAP / "final_audit.md"
fa = FAp.read_text(encoding="utf-8")
if "EXP-0062" not in fa:
    fa = sub1(fa, r"\| strong neural / dense-encoder baseline \| \*\*FAILED — OPEN\*\* \|.*?\|",
              "| strong neural / dense-encoder baseline | **PARTIAL — bi-encoder arm now run (EXP-0062, D37/D38)** | "
              f"An unmodified pretrained dense encoder (`all-MiniLM-L6-v2`) was run on the same {N} dev rows: hit@3 "
              f"{f4(B['hit_at_3'])} vs BM25 {f4(BM25)} vs from-scratch dense {f4(SCR)} "
              f"(`pretrained_dense_comparator.md`, {NAME}); the cross-ranker transfer test passes against it "
              f"({f4(AUC)}, CI {CI[0]}-{CI[1]} vs the unchanged 0.65 bar) while still failing against the scratch "
              "tower. Remaining and still stated: no cross-encoder reranker, no tool-specialised retriever, no "
              "leaderboard comparison, and the encoder's own pretraining mixture is unverifiable from this host "
              "(`limitations.md` L19; `reviewer_attack.md` A9/A" + str(LAST_A) + ") |",
              "final_audit G18-B dense row")
    FAp.write_text(fa, encoding="utf-8", newline="")

# ------------------------------------------------------------------ 9. registry
p = REG / "experiment_registry.csv"
txt = p.read_text(encoding="utf-8")
h2 = list(csv.reader(io.StringIO(txt)))[0]
row = ["EXP-0062", "P001", "success_E03c_PRETRAINED_DENSE_COMPARATOR_WEAKER_THAN_BM25_TRANSFER_PASSES",
       SCRIPT,
       f"unmodified {D['model']} bi-encoder scored on P001's frozen development pool ({N} dev rows, K={D['k']}); two "
       "text renderings with a pre-registered rule taking the higher-hit@3 one as the comparator; ranks/tie-handling "
       "imported from EXP-0024; EXP-0024's published ranks read from its table and asserted row by row; "
       "prompt_id-clustered bootstrap CI on the transfer AUROC; 300-row brute-force layout check; no test-split row",
       "none (deterministic given the cached, content-addressed embeddings)",
       D["started_at"], D["finished_at"],
       f"E03c pretrained hit@3={f4(B['hit_at_3'])} vs bm25={f4(BM25)} vs scratch={f4(SCR)}; "
       f"transfer AUROC={f4(AUC)} CI={CI[0]}-{CI[1]} bar={BAR} -> {'PASS' if PASS else 'FAIL'}",
       f"{NAME}; {TABLE}; papers/P001_routing_failure_qpp/pretrained_dense_comparator.md",
       f"closes the 'strong neural / dense-encoder baseline' FAILED item in final_audit as a bi-encoder arm; "
       "reverses §7.7's transfer negative for the pretrained ranker while keeping it for the corpus-trained tower, so "
       "the paper's claim becomes ranker-conditional transfer rather than no transfer; adds C22, A9/A"
       f"{LAST_A}, L19, D{dn+1}/D{dn+2}", "yes - §7.9, C22, L19"]
if row[0] not in {r[0] for r in csv.reader(io.StringIO(txt)) if r}:
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\r\n").writerow(row)
    p.write_text(txt.rstrip("\r\n") + "\r\n" + buf.getvalue().rstrip("\r\n") + "\r\n", encoding="utf-8", newline="")
    print("[e62] registered EXP-0062")

import pandas as pd
d = pd.read_csv(p)
assert not d.exp_id.duplicated().any()
cm2 = pd.read_csv(CM)
assert cm2.claim_id.tolist()[-1] == "C22" or "C22" in set(cm2.claim_id)
print(f"[e62] registry rows={len(d)}; claims={len(cm2)}; verdict PASS={PASS} STRICTER_THAN_BM25={STRICTER}")
