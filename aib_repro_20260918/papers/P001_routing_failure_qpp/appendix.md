# Appendix — P001: Predicting Tool-Routing Failure Before Retrieval, Without Any Language Model in the Loop

Every number in this appendix is read from a file listed in `tables/table7_experiment_provenance.csv`
or from the raw JSON named in the section header. Nothing here is hand-entered.

---

## A1 Dataset construction and the gold-label join

| stage | experiment | what changed | measured outcome |
|---|---|---|---|
| naive name join | EXP-0004 | gold item matched to catalog by identifier-prefix heuristic | rejected **26.7%** of OSS rows — a parser artifact, not a data fact |
| deterministic join | EXP-0005→EXP-0009 | `metadata.mcp_servers[i].remote_server_response.tools` gives each server's real tool names, so `"<Server>::<func>"` resolves on (server, function) and a bare `"<func>"` resolves to the unique server owning it | rejection **0.00–0.04%**; only `reject_ambiguous_by_suffix: 6` remains in Kimi-K2 |
| grouped split | EXP-0008 | `md5(uuid)` → `md5(prompt_id)` | a prompt and its `_follow_up` rows share `prompt_id` but differ in `uuid`; uuid splitting leaked paraphrase-adjacent rows across the boundary |
| lossless persistence | EXP-0013 | `question` and full `catalog_json` stored per row | enables re-scoring and intervention without re-reading 79 GB; row set verified unchanged (A9) |

Two identifier conventions coexist in the corpus. This is a property of Toucan-1.5M, not of our parser:
`target_tools` sometimes carries `"<server-slug>::<function>"` and sometimes a bare function name.

## A2 Exclusion rules and realised sample sizes

| rule | reason | dev rows retained (OSS / Qwen3 / Kimi-K2) |
|---|---|---|
| `n_candidates > k` for fail@k | with a catalog that fits inside the top-k, "no gold in top-3" is undefined-by-construction: EXP-0005 measured `fail@3 = 0.0000` **and** `chance_hit@3 = 0.0000` on that stratum | 5,714 / 5,512 / 7,972 (from 10,500 dev rows per config) |
| join failure | gold item cannot be resolved to a catalog entry | 0.00–0.04% of rows, itemised in EXP-0009 `rejection_accounting` |

25.0–47.6% of queries are excluded by the first rule. This is disclosed in the abstract, not hidden.

## A3 Feature definitions

Instruction-only (linguistic) features are computed from the user's question text alone.
Collection-aware QPP features are computed from the question and the **whole** per-query catalog,
never from the gold item's own description, and never from a gold label.

The frozen model uses the 32-column canonical list in `configs/P001_frozen_model.json`, decided on the
**development** intersection across configs (deviation D9) plus one size control, `log n_candidates`.

QPP block: `qpp_coverage`, `qpp_idf_weighted_coverage`, `qpp_clarity_meanmax`, `qpp_clarity_sd`,
`qpp_ecle`, `qpp_max_doc_sim`, `qpp_mean_doc_sim`, `qpp_doc_sim_spread`, `qpp_missing_term_n`,
`qpp_n_query_terms`. Lexical baseline: BM25 with k1=1.4, b=0.4, frozen and deliberately **not** tuned
(deviation D8: the dependent variable is defined on that ranker, so tuning it would move the metric by
changing the question being asked).

## A4 Development selection grid (EXP-0010)

Grid: feature set {all, qpp, linguistic} × C {0.1, 1.0, 10.0}, 5 seeds, OOF 5-fold, dev only.
Per-config winners were 0.8233 / 0.8309 / 0.7951, but a **single global** configuration was frozen by
mean dev AUC (`all_C0.1`, mean 0.8159) rather than taking each config's own winner — per-dataset
best-config selection would be selecting the best configuration across datasets on the way to a
cross-dataset claim. Ordering `all ≈ qpp ≫ linguistic` held in every config.

## A5 Alternative operationalisations of the dependent variable (EXP-0011)

| alternative | OSS | Qwen3 | Kimi-K2 |
|---|---|---|---|
| AUC under fail@1 / fail@3 / fail@5 | 0.729 / 0.823 / 0.885 | 0.759 / 0.829 / 0.904 | 0.704 / 0.795 / 0.833 |
| Spearman ρ(predicted risk, norm_rank) | 0.33 | 0.42 | 0.26 |
| DV from a description-only BM25 ranker | 0.816 | 0.830 | 0.795 |
| +5% random label noise | 0.706 | 0.743 | 0.644 |
| 50% subsample | 0.813 | 0.838 | 0.786 |

**Construct-validity warning, reported not concealed:** the full-ranker DV and the description-only DV
share only **3.4–10.6%** of their positive rows. "Routing failure" is therefore ranker-relative, and
the paper's claims are stated that way.

## A6 H4 — is the failure label an artifact of non-exhaustive gold? (EXP-0014, EXP-0015)

The gold set is the tool a teacher agent actually called, i.e. one realised choice rather than the set
of admissible choices. If a functionally equivalent tool sat in the top-3, a row counted as a failure is
a labelling artifact. ToolEX-style relabelling normally asks a model to judge equivalence; no inference
API is permitted in this project, so equivalence is decided by deterministic, inspectable criteria at
three pre-registered strictness levels. The criterion and the rules were fixed in the script before any
H4 output existed.

`conservative` : param_jaccard = 1.0 ∧ name_jaccard ≥ 0.5 ∧ desc_cosine ≥ 0.5
`moderate` : (param_jaccard ≥ 0.6 ∨ name_jaccard ≥ 0.4) ∧ desc_cosine ≥ 0.35
`liberal` : name_jaccard ≥ 0.25 ∨ desc_cosine ≥ 0.60

A first data fact had to be recorded before the rules could be written: all three configs' `available_tools`
column stores **bare function names** with no server namespace (`create_plugin`, not `framer::create_plugin`),
so a `same_server` conjunct is not derivable from the persisted catalog and was dropped (deviation D12).

**Guard before any analysis.** The persisted question and catalog were re-scored with the frozen BM25 and
the reproduced best-gold rank compared against the stored column: replication rate **1.000000 / 0.999637 /
0.999122**. Below 0.999 the script aborts. (An earlier draft of the persistence layer capped descriptions at
600 characters and failed this check on 16–18% of rows, which is why the cap was removed.)

| rule | positives relabelled (dev rows) | dev AUC original → broadened | prevalence |
|---|---|---|---|
| conservative — OSS | **0.68%** (3/444) | 0.8233 → 0.8236 | 0.0777 → 0.0772 |
| conservative — Qwen3 | **3.09%** (22/712) | 0.8294 → 0.8305 | 0.1292 → 0.1252 |
| conservative — Kimi-K2 | **7.10%** (24/338) | 0.7951 → 0.7996 | 0.0424 → 0.0394 |
| moderate — OSS / Qwen3 / Kimi | 15.5% / 75.4% / 60.4% | 0.8118 / 0.8225 / 0.8222 | 0.0656 / 0.0317 / 0.0168 |
| liberal — OSS / Qwen3 / Kimi | 68.2% / 99.7% / 99.1% | 0.8499 / **0.4146** / 0.6875 | 0.0247 / **0.0004** / 0.0004 |

Pre-registered criterion: H4 is supported iff the conservative rule relabels ≥10% of positives in any
config. Maximum observed **7.10%** → **H4 is not supported**, and the AUC does not fall; it rises by
0.0003–0.0045.

**Why the moderate/liberal numbers are not evidence for H4.** They are artifacts of lexical similarity,
established by reading the pairs. EXP-0015 drew a fixed random sample (`random_state=42`) of the
conservative rule's relabellings of real positives and the annotator read each pair together with the
user instruction that produced it. Of **40 adjudicated pairs (3 of 43 were not read in this pass and are
reported as missing rather than guessed)**:

| verdict | n | meaning |
|---|---|---|
| equivalent | **0** | the alternative tool genuinely satisfies this instruction |
| sibling_different | 32 | same server, identical parameter schema, materially different operation or scope |
| different_domain | 6 | different target system or object type |
| unsure | 2 | instruction too unspecific to decide |

Rule precision for genuine equivalence is **0.00 in all three configs**, so the conservative rates above
are an **upper bound** on label noise from gold non-exhaustiveness. Illustrative adjudicated pairs:
`firestore-delete-document` vs `firestore-get-document` (an instruction to archive a document while
preserving every field needs the read); `semantic-scholar-papers-references` ("papers cited by X") vs
`-papers-citations` ("papers that cite X") against an instruction explicitly asking for work that has
cited "Attention Is All You Need"; `get-npm-package-details` vs `get-pypi-package-details` for a Python
package; `search-models` vs `search-datasets`; `create_futures_market_order` vs `create_spot_market_order`;
`calc-subtract` vs `calc-multiply`. The degenerate liberal behaviour confirms the direction of the effect:
relabelling on loose lexical similarity drives prevalence to 0.0004 and AUROC to 0.4146 — it destroys the
construct rather than cleaning the label.

**Positive side-result.** The pairs the rule does surface are not noise, they are the mechanism: catalogs
are dense with same-server sibling tools that share a parameter schema and differ by a single token. That
is precisely the structure a pre-retrieval lexical predictor can key on, and it explains why instruction
style alone (0.669–0.732) underperforms query–catalog reachability (0.794–0.821).

## A7 Inference (EXP-0011)

Cluster bootstrap over `prompt_id`, 1000 resamples, because EXP-0008f measured that 4.5–9.4% of
prompt_ids recur across configs and up to 3 rows share one prompt_id inside a config.
ΔAUC of the frozen pre-retrieval model: vs length-only **+0.1595 / +0.2799 / +0.2366**; vs post-retrieval
margin **+0.0858 / +0.0322 / +0.1660**; all p < 0.001. Univariate odds ratios per SD with Holm
correction are in `tables/table6_univariate_OR.csv`; where a joint logistic was attempted it was
ill-conditioned (`LinAlgError: Singular matrix`) and the per-feature form is reported instead
(deviation D10).

## A8 Split integrity and contamination (EXP-0008f)

3,003 rows per config sampled from 3 shards each: OSS 3003 rows / 2770 distinct prompt_ids / 2964
distinct questions (219 prompt_ids hold >1 row, max 3); Qwen3 3003/2909/3001; Kimi-K2 3003/2907/2999.
Cross-config prompt_id overlap **4.5–9.4%**; exact question overlap 10–30 pairs; uuid overlap 0–1.
All queries are model-synthesised, so results are stated as properties of recorded agent-instruction
data, not of human information behaviour.

## A9 Reproduction evidence (EXP-0013, E18)

Rebuilding from source with the frozen invocation
`--rows-per-config 15000 --shards-per-config 10` reproduces all three published `sha256(sorted uuid)[:16]`
digests (`0127733aaaa4b132` / `75c2ccf4cd36d365` / `0494a683650e0972`) and all published prevalences
(0.0423 / 0.0677 / 0.0318 unrestricted; 0.0777 / 0.1292 / 0.0424 on the `n_candidates>3` subset).

The guard exists because of a real incident, logged as D11: a rebuild using the builder's *default*
`--shards-per-config 8` silently replaced the sample (OSS dev fail@3 0.0423 → 0.0354). It was caught by
comparing uuid sets against `01_datasets/snapshots/exp0009_published/`, the published files were restored,
and the builder now aborts on any digest mismatch unless `--allow-resample` is passed explicitly.

## A10 Cost and runtime (E13)

CPU-only in practice: an RTX 3060 is present but the installed torch is a CPU-only build and no encoder library or pretrained weights are available offline. No API calls, no token spend. Python 3.11.7, 16 logical CPUs, 31.9 GB RAM
(`environment/system_info.json`). Wall clock actually measured: routing dataset build 102–127 s per run;
dev selection grid (45 configurations × 5 seeds) ≈ 73 s; dev robustness + inference ≈ 60 s; single gated
test evaluation ≈ 32 s; H4 relabelling including 45 refits and 3 TF-IDF fits ≈ 55 s; BM25 re-scoring of the
persisted catalogs is the dominant cost inside EXP-0014.

## A11b Controlled catalog interventions (EXP-0016, E17 + E12)

Development rows only; every condition re-scores the persisted catalog with the frozen BM25. The
harness refuses to run unless its `control` condition reproduces the published labels and dev AUROC
exactly — after a bug that overwrote the instruction-only `n_tokens` it did not (0.8238 vs the published
0.8233), and the corrected run reproduces **0.8233 / 0.8294 / 0.7951** with **0 label drift**.

| condition | what is changed | prevalence OSS / Qwen3 / Kimi | mean predicted risk Δ vs control |
|---|---|---|---|
| control | nothing | 0.0777 / 0.1292 / 0.0424 | — |
| distract_8 | +8 decoys built from the gold tool's own non-stopword vocabulary | **0.2585 / 0.3534 / 0.1433** | **+0.1808 / +0.2243 / +0.1010** |
| enrich_gold | gold description gains the instruction's top-IDF catalog-absent terms | **0.0012 / 0.0022 / 0.0010** | −0.0765 / −0.1270 / −0.0414 |
| enrich_sham | the same edit applied to a random **non-gold** tool | **0.1083 / 0.1593 / 0.0676** | +0.0308 / +0.0301 / +0.0252 |
| namespace_prefix | every tool renamed `srv-<rand>-<name>` | 0.0777 / 0.1288 / 0.0420 | ≈0 |
| order_shuffle | catalog order permuted | 0.0735 / 0.1083 / 0.0444 | ≈0 |

Three readings, in the order the evidence supports them:

1. **Competition is causal and monotone.** Inserting lexically confusable siblings at k=2/4/8 raises
   failure in every config (dose-response slope reported per config), and the frozen predictor's mean
   risk rises by essentially the same amount (+0.181/+0.224/+0.101 for the 1:1 correspondence above).
   The predictor is not merely correlating with a ranker quirk; it tracks an experimentally induced
   change in the outcome.
2. **The curation lever works, and only when aimed correctly.** Enriching the gold description collapses
   failure to ~0.001-0.002, while the identical edit on a non-gold tool makes routing *worse*
   (+0.031/+0.030/+0.025 prevalence) — the injected words become new competition. This is the LIS
   result: unfocused metadata editing backfires.
3. **Not a formatting artifact.** Namespace renaming and order shuffling are near-no-ops.

**AUROC under enrichment is deliberately not quoted as a model result.** With prevalence at ~0.001 the
refit AUROC approaches 1 by construction (positives fall to 7-12 rows), so the artifact marks those arms
`auc_is_informative = false`; they are read for prevalence only. Transfer AUROC of the control-fitted
model onto the crowded catalogs is 0.742 / 0.720 / 0.716, the honest generalisation figure under
intervention.

## A11c Statistical unit, split straddling and corrected inference (EXP-0017/0018/0019)

The dominant dependence structure in this corpus is the **catalogue**, not the prompt.

| grouping | k groups (OSS/Qwen3/Kimi) | ICC | design effect |
|---|---|---|---|
| prompt_id | 3992 / 3864 / 4690 | 0.0009 / 0.0000 / 0.0309 | 1.00 / 1.00 / 1.02 |
| catalogue fingerprint | 2186 / 1283 / 3603 | 0.0674 / 0.1879 / 0.2941 | 1.11 / 1.60 / 1.35 |
| gold-tool stem | 620 / 681 / 869 | 0.2625 / **0.4842** / 0.1041 | 3.12 / **4.39** / 1.85 |
| subset_name | 1 / 1 / 1 | degenerate — one level per corpus | — |

Re-grouping the development cross-validation, versus the published stratified split
(OSS 0.8233 / Qwen3 0.8294 / Kimi 0.7951):

| CV grouped by | AUROC delta OSS / Qwen3 / Kimi |
|---|---|
| prompt_id | +0.0009 / −0.0000 / +0.0039 |
| catalogue | **−0.0164 / −0.1110 / −0.0048** |
| gold-tool stem | −0.0271 / −0.1000 / −0.0129 |
| catalogue AND gold stem | −0.0220 / −0.1113 / −0.0043 |

A pre-registered rule (a drop >0.02 under *any* grouping ⇒ memorisation contributed) is **triggered**.
The published split lets 887/498/837 catalogues straddle dev and test, so **80.9% / 88.1% / 63.7% of
test rows are evaluated on a competitive situation present in training** (0 prompts straddle, so the
prompt_id grouping did its job). A catalogue-disjoint split is *not constructible*: the connected
component containing the most-shared catalogue holds 14,187 / 14,699 / 12,912 of 15,000 rows, so
disjointness leaves 553/221/641 dev rows. Consequences adopted rather than argued away:

* the test AUROC is reported as an **upper bound for unseen catalogues**, and the catalogue-grouped dev
  AUROC (0.807 / 0.718 / 0.790) is the conservative figure;
* GEE robust standard errors reach **7.33x** the naive ones, so all headline contrasts were re-inferred
  with the **catalogue** as resampling unit (EXP-0019): CI widths inflate up to **2.955x**, and **all
  nine** contrasts (pre>length, pre>post-margin, pre>linguistic × three corpora) still exclude zero.
  Direction survives; the earlier intervals were too narrow.

## A12 E08: cross-pipeline, cross-family and cross-corpus generalisation (EXP-0020..EXP-0023)

**Why it exists.** D13 could only assert that the published test AUROC is an upper bound for catalogues never seen
in training. E08 was designed to replace that bound with a measurement. EXP-0022 established at file level that
(i) of the eight local corpora only `Agent-Ark/Toucan-1.5M` and `lambda/hermes-agent-reasoning-traces` carry a
per-query candidate catalogue, and (ii) no host that could serve a new corpus was reachable from this machine
(each probed three times, at its root *and* at a concrete dataset file URL; huggingface.co times out, the mirror
answers 200 at its root and 404 at `resolve/`). The round measures what is measurable locally and logs the rest
rather than asserting it.

**EXP-0020 - build.** Toucan's fourth config `SFT`, never referenced by the frozen protocol, built through the
identical code path: 15000/15000 rows kept, join rejections {}, catalogue mean
5.14, dev fail@3 prevalence 0.0201. `SFT` has no `metadata` column, so gold could not be
verified against a per-row MCP server tool index (disclosed in the card). The D11 guard was generalised: a config
built for the first time writes its own uuid digest, so a later rebuild cannot silently swap the sample.

**EXP-0021 - the premise fails, and what does bite.** `SFT` is *not* an unseen catalogue: 1797/1797 tool names,
100% of catalogue tokens and 848 catalogue fingerprints coincide with the source dev pool.
Pipeline transfer AUROC 0.8138 (catalogue-clustered CI [0.7576, 0.8545]) against source OOF 0.8118; on the
801 rows whose whole catalogue is absent from training, 0.8316 - catalogue *composition* novelty
costs nothing detectable. What does bite is tool vocabulary: leave-one-tool-family-out over 12 families
(33 considered, >=10 failures required) moves 0.7823 -> 0.7282, a degradation of
0.0541 against the 0.02 criterion, with length-only at 0.6332. Per-family values:
`results_processed/EXP0021_transfer_families.csv`; summary: `tables/table12_external_transfer.csv`.

**EXP-0023 - independent corpus.** Catalogue = each row's `tools` array; gold = the tool the reference model
invoked in its `tool_call` block (encoding established by EXP-0023a, whose first parser returned zero calls and was
fixed rather than reported as absence of tool use). 6000 rows pass the n_candidates>3 inclusion rule,
fail@3 prevalence 0.1777, extraction rejections {'reject_catalog_empty': 13646}; 69% of the corpus' 26 tool
names never occur in the source corpus and 86% of its catalogue tokens do. Transfer AUROC
**0.6939** (row bootstrap CI [0.6797, 0.7097]) vs in-domain 0.8118 and within-hermes OOF 0.8432; on the
same rows length-only scores 0.4413, the post-retrieval margin baseline 0.6481, and IDF-weighted
coverage alone 0.3674. The decision rule (>=0.65 transfers / 0.55-0.65 partial / <0.55 does not) was fixed in
the script before any external label was read; outcome **transfers**. Caveat kept visible:
6 distinct catalogues means no catalogue-clustered interval is estimable here, so that CI is row-level
and understates dependence.

**Reading for the paper.** The construct survives an unseen tool universe; the level does not. Quote 0.6939
as the cross-corpus expectation and 0.8118 / 0.8316 as same-family figures. Two implementation bugs
surfaced in this round and are recorded in the registry instead of being quietly fixed: an inverted
family-exclusion mask that silently returned zero families, and single-class CV folds inside the family holdout.

## A13 E03b: a trained dense comparator (EXP-0024)

**Why it exists.** Every ranking number in the paper is defined against one frozen lexical ranker, so "failure" could be an artifact of that ranker being weak. Pretrained encoders are unavailable here (no inference-API policy; torch is a CPU-only build although an RTX 3060 is present; no encoder library or weights downloadable — measured in EXP-0022 and recorded in the deviations correction). A from-scratch dense model is the strongest comparator this environment can actually produce, and it is reproducible from one script.

**Model.** TF-IDF (min_df 3, cap 30k features, sublinear, l2) shared by both towers; two linear maps to 128 dimensions; cosine score; softmax over each row's own candidate set with every gold tool as a positive; Adam, 80 full-batch steps, lr 0.005, seed 42; vocabulary fitted on the training fold only ([9285, 9295, 9297, 9327, 9330] features). 5-fold GroupKFold grouped on `prompt_id`, so every dense rank is out-of-fold. Wallclock 607.2s on CPU; no test row is read at any point.

**Retrieval comparison.** hit@3 0.9643 (dense) vs 0.9222 (frozen BM25) against chance 0.4718; mean best gold rank 1.354 vs 1.614; dense failure prevalence 0.0357. Spearman correlation between the rankers' per-query best ranks is 0.1608 and the Jaccard overlap of their failure sets is 0.0846 (1839 discordant rows).

**Predictability, and where it breaks.** Refitting the frozen feature family on the dense outcome gives AUROC 0.7816 (out-of-fold, two seeds) against length-only 0.5653 and the dense ranker's own top-1/top-2 cosine margin 0.6471. The predictor trained on BM25 failures and scored on dense failures gives 0.6451, i.e. no better than the ranker's own margin, so the pre-registered 0.65 criterion is **not met**; it is reported as a negative result rather than moving the threshold. Per-row ranks, margins and predicted risks: `results_processed/EXP0024_dense_vs_bm25.csv`; summary: `tables/table13_dense_comparator.csv`.

## A11 Experiment inventory

`00_program_registry/experiment_registry.csv` lists EXP-0001 … EXP-0015 with stage, script, config, seed,
timestamps, status and outputs — **including the runs that failed**: EXP-0002's 0.0 gold-parsing rate,
EXP-0004's 26.7% over-rejection, and three failed EXP-0013 rebuild attempts. No result version was deleted.
