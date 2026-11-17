# Predicting Tool-Routing Failure Before Retrieval, Without Any Language Model in the Loop

**Paper ID** P001 (topic T037) · **Type** B (prediction/method) · **Target** SIGIR / CHIIR / Information Processing & Management
**Status** main result complete on a single held-out evaluation, and all four pre-registered hypotheses now adjudicated (H1–H3 supported, **H4 rejected as a pre-registered null**, appendix A6); three robustness/baseline studies outstanding (`limitations.md` L6)
**Provenance** every number below is produced by the scripts listed in `tables/table7_experiment_provenance.csv`; claim-to-evidence mapping in `claims_evidence_matrix.csv`; protocol frozen at 2026-09-18 18:31 before any test read (`protocol_freeze.md`), ten pre-test amendments logged in `deviations.md`.

---

## Abstract

Before an LLM agent can act on a user's instruction, a tool-retrieval stage must surface the relevant tools from a catalog whose entries are described in a technical register that users do not share. Prior work treats this as a ranking-accuracy problem and answers it by training better encoders, motivating the failure with the observation that colloquial, underspecified queries do not match API vocabulary. We ask the complementary question that none of that literature answers: **can the failure be predicted before retrieval, using no language model at all?** We build a 45,000-query dataset from three corpora of Toucan-1.5M (OSS / Qwen3 / Kimi-K2, 1,527,259 rows, HF revision `0df3cf37f2ab…`), in which every query carries a gold set of required tools over a per-query candidate catalog of 1–70 tools. Defining failure as "a frozen BM25 ranker misses every gold tool from its top 3", we predict it from instruction-only features plus collection-aware query-performance-prediction (QPP) features — coverage, IDF-weighted coverage, CLARITY-style term dispersion, ECLE — with the gold labels never entering the feature space. A regularised logistic model reaches test AUROC **0.808 / 0.819 / 0.790** across the three corpora, beating the trivial length-only baseline (**0.668 / 0.532 / 0.544**) and, in all three, a post-retrieval quasi-local QPP baseline built on the ranker's own score margin (**0.752 / 0.806 / 0.649**). Trained on two corpora and tested on the third it still reaches **0.748–0.798**. An ablation locates most of that signal in query–catalog lexical reachability rather than instruction style per se (**0.794–0.821** vs **0.669–0.732**). We also report what weakens the construct: the definition of failure is ranker-relative (positive sets of two plausible rankers overlap only **3.4–10.6%**), and **25.0–47.6%** of queries are structurally uninformative because their whole catalog fits in the top-k. All queries are model-synthesised, so we state our results as properties of recorded agent-instruction data, not of human information behaviour. We also quantify how far the numbers can be pushed: the test AUROC is an **upper bound for unseen catalogues**, because 63.7-88.1% of test rows share a candidate catalogue with a development row and catalogue-grouped cross-validation costs up to 0.111 AUROC (0.807/0.718/0.790 when grouped), while a controlled catalog intervention shows the mechanism directly - injecting lexically confusable siblings raises failure by up to 0.224 and moves the frozen predictor's mean risk by the same amount, and the same metadata edit applied to a non-gold tool makes routing worse rather than better. E08 replaces that bound with a measurement: on an independent corpus (lambda/hermes-agent-reasoning-traces, 69% of its tool names absent from training) the frozen model transfers at AUROC **0.6939** (row-bootstrap CI 0.6797-0.7097), about 0.118 below the in-domain figure, yet still above that corpus' length baseline (0.4413) and its post-retrieval margin baseline (0.6481).

## 1 Introduction

Agent systems that act on graphical interfaces or external services do not read the whole tool universe: a retrieval stage selects a handful of candidate tools per instruction, and only those candidates reach the model's context. When the required tool is not among them, no amount of downstream reasoning can recover it. This makes tool retrieval a genuine information-retrieval problem inside the agent loop — with a classic IR pathology at its centre: the user writes "why isn't my package installing" while the catalog advertises `mcp-server-validatePhoneNumber`, a *vocabulary mismatch* between a natural-language need and a technical resource description.

Recent literature has converged on that diagnosis. ToolRet (Findings ACL 2025) established that general-purpose retrieval models are poor at tools; CoHyDE, the Tool Retrieval Bridge and Tool-DE all motivate their methods with underspecified queries versus technical API vocabulary, and report gains by rewriting the query or enriching the tool description. Every one of these papers improves the retriever. **None of them lets a system know, before retrieving, whether retrieving will work.** That gap matters operationally: a deployable agent should be able to triage — expand the candidate set, rewrite the instruction, ask the user, or fall back to a catalog search — *before* spending a context window and a model call.

We take the complementary position and ask whether the failure is predictable from language alone, under the deliberate constraint that no language model is used at any point (no embedding model, no LLM judge, no generated labels). Methodologically we transplant query-performance prediction (QPP) — the IR literature's machinery for estimating whether retrieval will succeed for a given query — from document collections to tool catalogs.

Contributions, each checkable against `claims_evidence_matrix.csv`:

1. **A reproducible routing-failure dataset** built from a public agentic corpus with an objectively grounded gold-label join: `target_tools` resolves to catalog entries through server-level tool listings, with measured item-level grounding of 1.0000 in three of four source configs and 0.8880 in the fourth, which we therefore exclude (C9).
2. **The first LLM-free pre-retrieval predictor of tool-routing failure**, which matches or beats a post-retrieval quasi-local QPP baseline in three independent teacher-model corpora (C1, C2, C3).
3. **A decomposition of where the signal lives**: collection-aware lexical-reachability features, not instruction pragmatics alone, carry most of it (C4), with univariate directions reported alongside effect sizes (C5).
4. **An explicit account of the construct's fragility**, quantified rather than hedged: ranker-relative DV (C6), structural exclusions (C7), split-integrity properties (C8), and the unresolved non-exhaustivity of gold labels (C11).

## 2 Related work

**Tool retrieval as an accuracy problem.** ToolRet benchmarked 43k-tool retrieval and reported BM25 nDCG@10 of 22.32 against dense encoders at 40.54–48.70; COLT/ToolLens pushed completeness-oriented training; Seal-Tools compared BM25 with DPR on self-instruct data; Tool-DE attributed difficulty to incomplete and heterogeneous tool documentation and trained dedicated encoders. These works define the accuracy frontier; our comparison to them is *not directly comparable* (five-condition analysis in `sota_audit.md`), because we use 1–70-candidate per-query shortlists, a different metric, and no trained encoder.

**Vocabulary mismatch as a diagnosis.** CoHyDE, the Tool Retrieval Bridge and HumanMCP all name the underspecified-query mechanism; the first two use it to motivate query rewriting (CoHyDE: +6.3pp NDCG@5 on held-out vague queries; the Bridge: BM25 nDCG 9.73→19.59). **We do not claim this mechanism as a contribution**; we claim the prediction problem built on top of it, which this literature leaves open.

**Catalog size and description quality.** A 2026 chance-corrected evaluation of shortlist depth established that exposing fewer well-chosen candidates is itself an evaluation target (registries 20→3,251 tools), while MCP-description-smell analysis and description-rewriting work intervene on the catalog directly (median task success +5.85%; execution steps +67.46%). Our catalog-size strata are therefore treated as a moderator, and the intervention design is deferred rather than claimed.

**Agentic failure prediction.** Adjacent to our task, the agent-failure literature predicts *execution* failure: verbal-confidence tracking reaches AUROC 0.85 at trajectory completion but nothing above 0.60 at 50% progress; non-LLM telemetry monitors reach 0.872 AUROC and collapse to 0.527 when cold-deployed. Our setting differs in three ways that matter to a reviewer: the prediction happens **before any agent step**, it uses **only surface language**, and its label is **retrieval-side**, not execution-side.

**Where the LIS question sits.** In information-management terms, the tool catalog is a controlled-vocabulary resource description system, the user instruction is a query formulation, and a top-k miss is a failure of *accessibility* rather than of availability. QPP is the standard instrument for anticipating that failure in classical IR; porting it to agentic catalogs is the bridge this paper builds.

## 3 Conceptual framework

Let `q` be the instruction, `C(q) = {t_1..t_n}` the candidate catalog shipped with that query (n from 1 to 70, mean 6.10–8.76), `G(q) ⊆ C(q)` the gold tools, and `R` a fixed lexical ranker. Two quantities are separated throughout:

* **Availability** — is `G(q)` inside `C(q)`? Measured by the grounding join: item-level 1.0000 in OSS/Qwen3/Kimi-K2, 0.8880 in SFT.
* **Reachability** — does `R` place some element of `G(q)` within its top k? This is our dependent variable.

Predictors are partitioned by whether they may see the catalog: *instruction-only* features (token counts, constraint-marker density, sequence markers, epistemic and vague-word markers, demonstratives, quoted spans, entity/file/URL mentions, imperative opening) and *collection-aware* features computed from `q` and `C(q)` jointly but never from `G(q)` (term coverage, IDF-weighted coverage, CLARITY mean-max and SD, ECLE, document-similarity spread). The latter are legitimately pre-retrieval in the QPP sense: in deployment the catalog is known when the user types.

## 4 Data

Toucan-1.5M, HF revision `0df3cf37f2abefb380370cfb02eabea2a35ae782`, license apache-2.0, **1,646,546 rows** measured from parquet footers (the repo name says 1.5M; we use measured values). Configs used: OSS 457,130 / Qwen3 551,613 / Kimi-K2 518,516.

Three findings from reading the files rather than the card shaped the design:

1. **Two identifier conventions coexist.** Gold labels are written `Movie Recommender::get_movies` while catalog entries are flattened slugs `movie-recommender-get_movies`. A naive name join grounds 0% of items. The join we use is deterministic: server-slug+function equality, else unique function-suffix match inside the row's own server→tool listings carried in `metadata.mcp_servers[i].remote_server_response.tools`. Under a first, prefix-only rule 26.7% of OSS rows were wrongly rejected; the corrected rule rejects **0.00% / 0.01% / 0.04%**.
2. **The catalogs are small.** Median 4 (OSS/Qwen3) and 6 (Kimi-K2) candidates; chance hit@3 for a uniform ranker is 0.2646 / 0.2464 / 0.3526 on development. Raw hit@k is therefore nearly uninformative — measured random-ranking hit@1 reached 0.44–0.55 — so all inference is chance-corrected.
3. **Splits leak by construction if keyed on `uuid`.** Identical prompt texts recur at only 0.3–1.0% across configs, but `prompt_id` recurs at 4.5–9.4%, and inside a config 219/2770 prompt_ids in OSS hold several rows (original plus `_follow_up`) with *different* uuids. Splitting on `md5(uuid)` therefore places paraphrase-adjacent rows on both sides; we split on `md5(prompt_id)` (70/30).

Excluded: SFT (grounding 0.8880 < 0.90 threshold, and its catalog column is named `tools`); and, for the DV, all queries with `n_candidates ≤ k` (25.0–47.6% of development), where top-k is the entire catalog: that stratum has fail@3 = 0.0000 and chance hit@3 = 0.0000, so keeping it would silently dilute the outcome. Prevalence on the informative subset is 7.77% / 12.92% / 4.24% (fail@3, dev).

## 5 Methods

Model ladder (development only for selection): **B0** constant and length-only; **B1** post-retrieval quasi-local QPP from the ranker's score margin and top-1 score; **B1b** regularised logistic on all features + log candidate count; **B1c** instruction-only; **B1d** collection-aware only; **B2** gradient-boosted trees. All estimates are 5-fold stratified **out-of-fold** AUROC, repeated over seeds 42–46; zero-variance columns are dropped and logged, boundary NaNs imputed by training-fold medians inside each fold.

Hyperparameter search is restricted to the classifier penalty C ∈ {0.1, 1, 10} and the feature set, and a **single global configuration** is frozen by mean development AUROC across the three corpora (`all_C0.1`, mean dev AUROC 0.8159) rather than one per corpus, to avoid best-config selection. BM25's k1/b are deliberately *not* tuned: tuning the ranker would redefine the dependent variable (logged as D8).

Inference: cluster bootstrap over `prompt_id` groups (1,000 resamples) for ΔAUROC with two-sided p, Holm correction across the univariate feature family, effect sizes reported as OR per SD plus Cohen's d for hit-versus-miss means. Statistical-significance reporting is capped at p < 0.001 by the resample count; the substantive claim rests on effect sizes.

## 6 Experimental setup

Development: 10,441 / 10,465 / 10,628 rows, informative subsets 5,714 / 5,512 / 7,972. Test reserved and evaluated **exactly once**, recorded in `test_eval_ledger.json` (timestamp 2026-09-18T18:58:02, config hash `9c0c3344e0a0cf62`, no override reason). Cost: the entire pipeline for 45,000 rows runs in ~57 s for dataset construction and ~90 s for the model ladder on a CPU-only Windows host; no usable GPU for encoders (the installed torch is a CPU-only build), no API call, no paid inference (per the project's data boundary).

## 7 Results

**RQ1 — is pre-retrieval failure predictable without a model?** Yes, and by a clear margin over trivial baselines. On the held-out test split, the frozen pre-retrieval model reaches AUROC **0.8080 (SD 0.0042)** on OSS, **0.8190 (0.0024)** on Qwen3 and **0.7897 (0.0068)** on Kimi-K2, against length-only **0.6677 / 0.5322 / 0.5439** and a constant baseline of 0.5 (Table 3, Figure 3). Development cluster-bootstrap deltas versus length are **+0.1595 / +0.2799 / +0.2366**, all p < 0.001 (Table 5). Prevalence is 7.78% pooled, so a 0.79 AUROC is a practical triage signal, not a base-rate artefact.

**RQ2 — does it beat a post-retrieval baseline?** In all three corpora. The same-protocol quasi-local baseline built from the ranker's own margin and top-1 score scores **0.7523 / 0.8061 / 0.6489** on test, versus **0.8080 / 0.8190 / 0.7897** for the pre-retrieval model; development paired deltas **+0.0858 / +0.0322 / +0.1660**, p < 0.001. The QPP transfer to agentic catalogs therefore does not merely approximate post-retrieval prediction — on this data it exceeds it, while being available earlier in the pipeline.

**RQ3 — does it replicate across teacher-model corpora, and does it transfer?** Yes. AUROC is within 0.03 of each other across three corpora generated by different teacher models, frameworks and quality filters, and leave-one-config-out training gives test AUROC **0.7977 (OSS) / 0.7585 (Qwen3) / 0.7476 (Kimi-K2)** (Table 3). Dev-to-test movement is ≤0.011 in mean AUROC, consistent with a protocol frozen before any test read.

**Where the signal lives (ablation, Figure 5b, Table 4).** At the frozen configuration (`all_C0.1`, 32 canonical features, development split), instruction-only features reach AUROC **0.7039 / 0.6643 / 0.7331**; collection-aware features alone reach **0.8214 / 0.8100 / 0.7947**; the union **0.8233 / 0.8294 / 0.7951**. Most predictive strength is thus *query–catalog lexical reachability*, not instruction style — and the ordering is stable: an independent earlier ladder (EXP-0006b, C=1.0, per-frame column filtering) gives 0.7018 / 0.6694 / 0.7322, 0.8212 / 0.8110 / 0.7939 and 0.8218 / 0.8309 / 0.7924, agreeing to within 0.004. Univariately, catalog term coverage is protective (**OR 0.7374–0.8949** per SD, Holm-significant), as are CLARITY mean-max (**0.8357–0.9058**) and query length (**0.8540–0.9013**), with Cohen's d reported per feature (Table 6, Figure 4).

**Robustness (development).** The predictor transfers to an alternative DV defined by a description-only ranker (AUROC **0.7945–0.8297**), survives 5% random label noise (**0.6435–0.7430**) and 50% subsampling (**0.7855–0.8380**), and is monotone in how strict the miss definition is (fail@1 **0.7041–0.7594**, fail@3 **0.7951–0.8294**, fail@5 **0.8330–0.9040**). Predicted risk also tracks the continuous ordinal outcome (Spearman ρ 0.26–0.42, p < 1e-125).

## 7.6 E08 — does the predictor hold outside the corpus? (EXP-0020..EXP-0023)

D13 left this as an upper bound, so we measured it on two axes. **Catalogue composition** turns out not to be the
binding constraint: transfer from the pooled development splits to Toucan's untouched fourth config scores
**0.8138** (catalogue-clustered CI 0.7576-0.8545) against 0.8118 in domain, and the 801 rows whose entire
catalogue is absent from training score **0.8316** — no detectable cost. But that config is not an external
catalogue at all: 1797/1797 of its tool names and 848 of its catalogue fingerprints coincide with the training
pool, which is itself a finding about this corpus family (EXP-0022: only two of the eight local corpora carry a
per-query candidate catalogue, and no external benchmark host was reachable from the analysis environment). The
two things that *do* cost are tool identity and tool universe. Holding an answer **tool family** out of training
degrades AUROC from 0.7823 to **0.7282** over 12 families (our pre-registered 0.02 criterion triggered), and on
an **independent corpus** — lambda/hermes-agent-reasoning-traces, a different pipeline, model family and toolbox
whose tool names are 69% absent from training — the frozen model scores **0.6939** (row bootstrap CI
0.6797-0.7097) against 0.8118 in domain and 0.8432 when it is refitted within that corpus. Even there it beats
every comparator on the same rows: length-only 0.4413, post-retrieval score margin 0.6481, IDF-weighted coverage
alone 0.3674. Verdict by the rule fixed before reading any external label (≥0.65 transfers): the construct
transfers, the effect size does not — **0.69, not 0.81, is the number to quote before deployment**.

## 7.7 E03b — what happens when the ranker is trained rather than frozen? (EXP-0024)

A reviewer may reasonably object that a frozen BM25 is a straw man, so we trained a dense retriever from
scratch on the same development rows (TF-IDF input, two linear towers to 128 dimensions, cosine score,
per-row softmax with every gold tool as a positive) and scored it out-of-fold under the same prompt-grouped
cross-validation. Pretrained encoders were not an option here — no inference APIs by policy, a CPU-only torch
build, and no downloadable weights, all measured rather than assumed (EXP-0022 and the deviations correction) —
so the comparator is a model we trained ourselves under the same information budget.

The objection is **partly right, and the answer is more interesting than a defence**. The trained dense ranker
does beat BM25: hit@3 0.9643 vs 0.9222, mean best gold rank 1.354 vs 1.614.
But the two rankers then fail on almost disjoint sets of queries: the Jaccard overlap of their failure sets is
0.0846 and the Spearman correlation between their per-query best ranks is only 0.1608
(1839 discordant rows) — as different from each other as BM25 is from a description-only ranker
(§8, where that comparison gave 3.4-10.6%). So *which* instruction gets its gold tool missed is strongly
ranker-dependent.

That has a precise consequence for the paper's claim. Pre-retrieval predictability is not an artifact of BM25:
refitting the same feature family against the dense ranker's failures gives AUROC 0.7816
(length-only 0.5653; the dense ranker's own top-1/top-2 margin, the fair post-retrieval comparator under
that ranker, gives 0.6471). But the frozen predictor trained on BM25 failures scores only
0.6451 against dense failures, **below our pre-registered 0.65 survival criterion**. We therefore claim
that lexical query-catalogue reachability makes a *specified ranker's* failures predictable, and we do **not**
claim a ranker-independent failure predictor. That is a narrower, and we think more useful, statement: a
deployment that changes ranker must refit the predictor, exactly as it must re-tune thresholds today.

## 8 What the results do not support

Four limits are quantified rather than gestured at. First, **generalisation to unseen catalogues is weaker than the headline**. The catalogue, not the prompt, is the dominant dependence structure (intraclass correlation up to 0.484, design effect up to 4.39), and the published split leaves 63.7-88.1% of test rows sharing a catalogue with development rows. Grouping the cross-validation by catalogue costs 0.016 / 0.111 / 0.005 AUROC, and no catalogue-disjoint split exists to test this on held-out data, because one connected component of the catalogue-prompt graph contains 86-98% of all rows. The test figures are therefore an upper bound for unseen catalogues; 0.807 / 0.718 / 0.790 is the conservative within-corpus estimate. All confidence intervals here are bootstrapped on catalogues, which widens them up to 2.96x; every headline contrast still excludes zero. Second, **failure is ranker-relative**, and that now includes a trained ranker, not only a second frozen one: the primary and description-only DVs overlap only **3.4–10.6%**, and a two-tower dense model trained from scratch — the stronger ranker (hit@3 0.9643 vs 0.9222) — shares only **0.0846** of its failure set with BM25. Refitting the same feature family on the dense outcome still predicts it (AUROC 0.7816, against length-only 0.5653 and the dense ranker's own score margin 0.6471), but the predictor trained on BM25 failures reaches only 0.6451 on dense failures, below the 0.65 survival criterion fixed before training. We therefore describe the outcome as *lexical unreachability under a specified ranker* and do not claim a ranker-independent failure predictor (§7.7, appendix A13). Third, **the informative population is a selected subset** (25.0–47.6% of development queries have catalogs small enough that top-k cannot miss). Fourth, **gold sets are non-exhaustive in principle** — a teacher trajectory records one realised choice, not the set of admissible ones — but this does not explain the outcome. Relabelling failures via deterministic equivalence criteria (identical parameter schema, name-token Jaccard ≥ 0.5, description cosine ≥ 0.5) changes only **0.68–7.10%** of positives on development and leaves AUROC unchanged to marginally higher (**0.823→0.824, 0.829→0.831, 0.795→0.800**), and of 40 sampled relabellings read against their instructions **none** is a genuine equivalent: they are same-server *sibling* tools differing by one token (`delete` vs `get`, `references` vs `citations`, `npm` vs `pypi`). That sibling density is the mechanism, not the artifact (appendix A6). Full list, including the missing dense-encoder baseline and cross-dataset validation, in `limitations.md`. Section 7.6 replaces the original phrasing of this first limit — the bound is now a measurement: unseen catalogue *composition* costs nothing detectable, while unseen tool *vocabulary* costs about 0.12 AUROC (§7.6, L12).

## 9 Discussion

The practical implication for information management is a **pre-flight governance signal**: a catalog owner can compute, from the user's wording and their own tool descriptions alone, which instructions are likely to be unmatched, and act before invoking a model — expanding the candidate set, normalising the description vocabulary, or asking for clarification. This reframes a slice of agentic retrieval from an accuracy race into a *serviceability* question, which is where LIS tooling (metadata quality, thesaurus alignment, request-point triage) already has standing practice.

For computational linguistics, the ablation is the informative result: instruction-pragmatic features alone are not where the leverage lies — the interaction between instruction wording and resource-description wording is. Studies of user instructions to agents that treat the instruction in isolation therefore measure only part of the mechanism; the unit of analysis has to be the query–catalog pair.

For agentic information behaviour, our design deliberately refrains from the term. Every instruction here is model-synthesised from a tool set, so the "vocabulary mismatch" we detect is partly manufactured by the generation process, and the protective effect of length is plausibly a generation artefact as much as a behavioural one. What generalises is the *structural* finding — that a lexical-reachability estimate is computable pre-retrieval and informative — not the descriptive linguistics of the queries.

## 10 Implications for computational linguistics

1. Instruction-level pragmatics is a *moderator* in retrieval outcomes, not the primary driver; annotation schemes for agent instructions should co-encode the resource side.
2. QPP-style lexico-statistical features are interpretable linguistic measurements (coverage, term dispersion, expected context likelihood estimate) and give a cheap, auditable account of why a request fails, in place of model-score confabulation.
3. Reporting must be chance-corrected: with median 4–6 candidates, raw hit@k is close to a coin flip, and uncorrected accuracy tables would overstate the linguistics by a wide margin.

## 11 Implications for information management

1. Catalog description quality becomes an *operational* metric: reachability is measurable before deployment, and its deficit is attributable to description vocabulary rather than user behaviour.
2. Triage policies (expand, rewrite, ask, abstain) can be scheduled by predicted risk, which is the agent-catalog analogue of reference-interventions triggered by difficult queries.
3. Corpus governance is part of the research agenda: our dataset-card work surfaced identifier inconsistencies, label non-exhaustiveness, missing licences and broken external references in public agent corpora, all of which bear on reuse and citation practice.

## 12 Limitations

See `limitations.md` (L1–L9): ranker-relative construct; non-exhaustive gold labels tested and rejected as an explanation (H4 null, appendix A6 — sibling-tool density is the mechanism, not label noise); synthetic queries and the resulting external-validity ceiling; structural exclusions; teacher/framework confounding; missing dense-encoder and cross-dataset baselines; p-value resolution capped at 0.001; ten logged implementation corrections; path/interpreter constraints on reproduction.

## 13 Conclusion

Tool-catalog reachability can be estimated before retrieval, from surface language and catalog text, with no model in the loop, at AUROC 0.79–0.82 in three independently generated corpora and above a post-retrieval QPP baseline. The signal is chiefly the match between how users write and how resources are described, which is exactly the layer that information management has always owned. The constructs are fragile in specific, measured ways — ranker-relative, sparsely labelled, partly generated — and we prefer to report those numbers than to smooth them away.

---

*Artifacts*: `figures/fig1–fig6` (PDF+SVG, auto-generated, captions in sidecars), `tables/table1–table8`, `results_raw/EXP0003, 0005–0012`, `01_datasets/processed/routing_*.parquet`, `configs/P001_frozen_model.json`, `test_eval_ledger.json`, `reproduce.sh` (test stage excluded by design).
