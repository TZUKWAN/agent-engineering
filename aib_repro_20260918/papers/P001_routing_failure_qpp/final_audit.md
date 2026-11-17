# Final Audit — P001, pre-submission (G18 gate)

Audited 2026-09-18 19:53 against §18 of the programme checklist. Every checkbox carries the file or
experiment that settles it, or is marked **FAILED / OPEN** rather than being talked around.

---

## G18-A Data authenticity

| item | status | evidence |
|---|---|---|
| data really downloaded | PASS | `01_datasets/raw/Agent-Ark/Toucan-1.5M` on disk; `01_datasets/manifests/*.audit.json` produced by scanning the actual shards |
| version / revision recorded | PASS | HF revision `0df3cf37f2ab…`, license and row counts in `dataset_card.md` and `tables/table2_dataset_card.csv` |
| no fabrication | PASS | 18 registry rows EXP-0001…EXP-0015 + 0014b with raw JSON for each; three failed EXP-0013 rebuild attempts and EXP-0002's 0.0 parse rate are still in the registry |
| filters reproducible | PASS | EXP-0013 rebuild reproduces all three published uuid digests and all published prevalences (appendix A9) |
| README claims verified against files | PASS | two identifier conventions for `target_tools` were found by reading rows, not by the card; the catalog column was measured to carry **bare function names with no server namespace** (D12) |

## G18-B Experiment completeness

| item | status | evidence |
|---|---|---|
| main experiment | PASS | EXP-0012 single gated test evaluation |
| trivial + classic + closest-prior baselines | PASS | B0 length, B1 post-retrieval margin, B1b/B1c/B1d ablation blocks, B2 trees (`table3_main_test.csv`) |
| strong neural / dense-encoder baseline | **FAILED — OPEN** | not run; the project's no-inference-API constraint blocks a dense tool retriever, and this is the paper's main weakness (`reviewer_attack.md` A9) |
| cross-dataset external validation | **FAILED — OPEN** | three configs of one corpus family only; ToolRet set not yet downloaded (`limitations.md` L6) |
| ablation | PASS | EXP-0010 grid; `all ≈ qpp ≫ linguistic` in all three configs |
| robustness | PASS | EXP-0011 (alternative DV, label noise, subsampling) + EXP-0014/0015 (alternative DV *definition* via equivalence relabelling) + EXP-0016 (controlled catalog interventions with a sham control) |
| error analysis | PARTIAL | EXP-0015 adjudication + fig6; a larger manual review of main predictions still open |
| intervention / counterfactual | PASS (after D13/D14 round) | EXP-0016: decoy ladder with dose–response, gold-description enrichment, a **sham** arm (same edit on a non-gold tool), namespace and order controls. The mechanism is now identified by manipulation with a specificity control, not by correlation |
| cost | PASS | appendix A10, CPU-only wall clocks from the logs |
| statistical inference | **AMENDED (D14)** | cluster bootstrap ΔAUC re-run on the catalogue as resampling unit (EXP-0019); 5 seeds; Holm-corrected ORs; chance-corrected LLR in bits. Earlier prompt_id-only intervals were too narrow |

## G18-C Statistics

Multi-seed PASS (seeds 42–46 everywhere, per-seed values in raw JSON). CIs **AMENDED** (D14): re-run with the **catalogue** as resampling unit (EXP-0019) - widths up to 2.955x larger, and 9/9 headline contrasts still exclude zero. The prompt_id-only intervals were too narrow: GEE showed naive SEs up to 7.33x too small.

Effect sizes PASS (AAUROC, OR per SD, Spearman rho, bits over chance). Effect sizes PASS (ΔAUC, OR per SD, Spearman ρ, bits over chance).
Multiple comparisons PASS (Holm). Hierarchical dependence **PARTIAL**: clustering fixes the bootstrap,
but the mixed-effects model for query-within-catalog promised in the research plan is **OPEN**.

## G18-D SOTA discipline

Search date recorded in `sota_audit.md` and per-row `retrieved_on` in `literature_matrix.csv`. The five
fair-comparison conditions fail on split and metric for every external number, so **the paper contains
no SOTA claim and never writes "outperforms"**; only internal same-protocol baselines are compared.
`demoted_L4_taken` / `killed_L4_and_unidentifiable` in the topic registry record topics abandoned
*because* they were already taken.

## G18-E Reproducibility

| item | status | evidence |
|---|---|---|
| one command regenerates the main tables and figures | PASS | `scripts/make_figures_tables.py` → 14 tables + 6 figures (SVG/PDF), all read from raw JSON |
| dependency + system record | PASS | `environment/{dependencies.txt,system_info.json,code_manifest.json}` — Python 3.11.7, 16 logical CPUs, 31.9 GB RAM, GPU RTX 3060 12 GB present but the installed torch 2.5.1 is a CPU-only build, so the analysis is CPU-only in practice (corrected 2026-09-18; this row previously said "GPU none", which was wrong) |
| code provenance | PASS | `environment/code_manifest.json` sha256[:16] per source file |
| catalogue-disjoint held-out check | **MEASURED (D15)** | EXP-0021: unseen catalogue *composition* costs nothing detectable (801 disjoint rows at 0.8316); leave-one-tool-family-out degrades 0.7823 -> 0.7282. EXP-0023 scores the frozen model on an independent corpus: 0.6939 [0.6797, 0.7097] vs 0.8118 in domain. The EXP-0018 structural finding still stands and is still disclosed: one connected component of the catalogue-prompt graph holds 86-98% of rows, so no disjoint split exists and 63.7-88.1% of test rows share a catalogue with dev — hence the published AUROC remains labelled a same-family figure, and **no second test evaluation was run** (the ledger still records exactly one). EXP-0013 rebuilt the dataset from source on this machine only; a fresh-environment run is still required |
| silent-drift protection | PASS (after an incident) | D11: a rebuild with the builder's default `--shards-per-config 8` replaced the sample and was caught by uuid comparison; the builder now aborts on digest mismatch |
| persistence reproduces the published DV | PASS | EXP-0014b: 2/19,198 dev rows differ in rank order, both from BM25 score ties at the cut, **0 changes to `fail_at_3`** |

## G18-F Writing

Conclusions match the numbers: H1–H3 supported, **H4 reported as a pre-registered null**, ranker-relative
construct and 25.0–47.6% structural exclusion stated in the abstract. No causal language (§8 lists what
the data do not support). Citations resolve to rows with URLs and verification status; no invented DOIs.
Limitations and appendix complete.

## Known defects, kept visible

1. **No *pretrained* dense baseline.** A from-scratch two-tower dense comparator is now trained and compared (EXP-0024: hit@3 0.9643 vs BM25 0.9222) and it is stronger, which is reported as such; cross-ranker transfer of the predictor is not established (0.6451 < 0.65). Pretrained encoders remain unavailable, so no leaderboard comparison is made and the outcome stays ranker-relative. "Predicts failure" is therefore relative to BM25 and cannot be
   read as an absolute difficulty claim. Blocked by the project's own policy boundary (no model inference API
   during analysis), an unusable GPU for this purpose (RTX 3060 present, torch is a CPU-only build, encoder libraries absent) and no downloadable pretrained weights. The corrected note with the feasible alternative (a from-scratch two-tower dense baseline, E03b) is in L6.
2. **Positive-set overlap of 3.4–10.6%** between the two rankers: the outcome is ranker-relative by construction.
3. **Single annotator, no second coder** for EXP-0015 → no κ. 3 of 43 sampled pairs unread and reported as missing.
4. **Equivalence judged lexically**, because no model API is permitted; the negative finding (0/40 genuine
   equivalents) is a statement about same-server sibling tools, and a semantic judge could still shift it.
5. **All queries synthetic**; no human-instruction validation set.
6. **The cross-corpus interval (EXP-0023) is row-level**, because the external corpus has only 6 distinct
   catalogues; it therefore understates dependence and is the loosest interval in the package.
7. 16 of 37 registered topics still sit at `w0_audit`; the pool meets the 30–50 requirement but the
   funnel is not finished.

## Gate decision

**Not submittable yet.** The empirical core is sound, the H4 hole is closed, and what was D13's *bound* is now a
*measurement* (§7.6, EXP-0020..0023): the construct transfers across corpora at AUROC 0.6939 while the headline
0.80-0.83 figures are explicitly labelled same-family. What still keeps G18-B open is the missing
dense/neural baseline, whose absence is a policy/resource decision that must be written up as a feasibility
note, plus the clean-environment replication. Next actions, in order of what they buy:
~~E08 external dataset~~ **DONE (EXP-0022 probe + EXP-0023 cross-corpus AUROC 0.6939)** →
~~E17 catalog intervention~~ **DONE (EXP-0016)** → ~~dense-baseline feasibility note~~ **DONE (EXP-0024 trained comparator; cross-ranker transfer 0.6451 < 0.65 reported as negative)** → pretrained-encoder availability note → clean-environment
replication (E20, `reproduce.sh` stage 1-10 from raw) → second-coder κ on EXP-0015 → larger error review (E15).

