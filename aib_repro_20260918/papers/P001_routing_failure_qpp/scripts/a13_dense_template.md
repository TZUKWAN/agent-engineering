## 7.7 E03b — what happens when the ranker is trained rather than frozen? (EXP-0024)

A reviewer may reasonably object that a frozen BM25 is a straw man, so we trained a dense retriever from
scratch on the same development rows (TF-IDF input, two linear towers to 128 dimensions, cosine score,
per-row softmax with every gold tool as a positive) and scored it out-of-fold under the same prompt-grouped
cross-validation. Pretrained encoders were not an option here — no inference APIs by policy, a CPU-only torch
build, and no downloadable weights, all measured rather than assumed (EXP-0022 and the deviations correction) —
so the comparator is a model we trained ourselves under the same information budget.

The objection is **partly right, and the answer is more interesting than a defence**. The trained dense ranker
does beat BM25: hit@3 <<dense_hit>> vs <<bm25_hit>>, mean best gold rank <<dense_rank>> vs <<bm25_rank>>.
But the two rankers then fail on almost disjoint sets of queries: the Jaccard overlap of their failure sets is
<<jaccard>> and the Spearman correlation between their per-query best ranks is only <<spearman>>
(<<discordant>> discordant rows) — as different from each other as BM25 is from a description-only ranker
(§8, where that comparison gave 3.4-10.6%). So *which* instruction gets its gold tool missed is strongly
ranker-dependent.

That has a precise consequence for the paper's claim. Pre-retrieval predictability is not an artifact of BM25:
refitting the same feature family against the dense ranker's failures gives AUROC <<per_ranker_auc>>
(length-only <<len_auc>>; the dense ranker's own top-1/top-2 margin, the fair post-retrieval comparator under
that ranker, gives <<dense_margin_auc>>). But the frozen predictor trained on BM25 failures scores only
<<cross_auc>> against dense failures, **below our pre-registered 0.65 survival criterion**. We therefore claim
that lexical query-catalogue reachability makes a *specified ranker's* failures predictable, and we do **not**
claim a ranker-independent failure predictor. That is a narrower, and we think more useful, statement: a
deployment that changes ranker must refit the predictor, exactly as it must re-tune thresholds today.
