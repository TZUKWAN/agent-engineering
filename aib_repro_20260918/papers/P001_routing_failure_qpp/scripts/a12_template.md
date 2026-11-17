## A12 E08: cross-pipeline, cross-family and cross-corpus generalisation (EXP-0020..EXP-0023)

**Why it exists.** D13 could only assert that the published test AUROC is an upper bound for catalogues never seen
in training. E08 was designed to replace that bound with a measurement. EXP-0022 established at file level that
(i) of the eight local corpora only `Agent-Ark/Toucan-1.5M` and `lambda/hermes-agent-reasoning-traces` carry a
per-query candidate catalogue, and (ii) no host that could serve a new corpus was reachable from this machine
(each probed three times, at its root *and* at a concrete dataset file URL; huggingface.co times out, the mirror
answers 200 at its root and 404 at `resolve/`). The round measures what is measurable locally and logs the rest
rather than asserting it.

**EXP-0020 - build.** Toucan's fourth config `SFT`, never referenced by the frozen protocol, built through the
identical code path: <<sft_kept>>/<<sft_seen>> rows kept, join rejections <<sft_rej>>, catalogue mean
<<sft_cat_mean>>, dev fail@3 prevalence <<sft_prev>>. `SFT` has no `metadata` column, so gold could not be
verified against a per-row MCP server tool index (disclosed in the card). The D11 guard was generalised: a config
built for the first time writes its own uuid digest, so a later rebuild cannot silently swap the sample.

**EXP-0021 - the premise fails, and what does bite.** `SFT` is *not* an unseen catalogue: <<ov_names>> tool names,
<<ov_tokens>> of catalogue tokens and <<ov_fp>> catalogue fingerprints coincide with the source dev pool.
Pipeline transfer AUROC <<a1_auc>> (catalogue-clustered CI <<a1_ci>>) against source OOF <<src_oof>>; on the
<<a1b_rows>> rows whose whole catalogue is absent from training, <<a1b_auc>> - catalogue *composition* novelty
costs nothing detectable. What does bite is tool vocabulary: leave-one-tool-family-out over <<a2_n>> families
(<<a2_cons>> considered, >=<<a2_minpos>> failures required) moves <<a2_seen>> -> <<a2_unseen>>, a degradation of
<<a2_drop>> against the 0.02 criterion, with length-only at <<a2_len>>. Per-family values:
`results_processed/EXP0021_transfer_families.csv`; summary: `tables/table12_external_transfer.csv`.

**EXP-0023 - independent corpus.** Catalogue = each row's `tools` array; gold = the tool the reference model
invoked in its `tool_call` block (encoding established by EXP-0023a, whose first parser returned zero calls and was
fixed rather than reported as absence of tool use). <<hc_rows>> rows pass the n_candidates>3 inclusion rule,
fail@3 prevalence <<hc_prev>>, extraction rejections <<hc_rej>>; <<hi_unseen>> of the corpus' <<hi_names>> tool
names never occur in the source corpus and <<hi_tokens>> of its catalogue tokens do. Transfer AUROC
**<<her_auc>>** (row bootstrap CI <<her_ci>>) vs in-domain <<src_oof>> and within-hermes OOF <<her_oof>>; on the
same rows length-only scores <<her_len>>, the post-retrieval margin baseline <<her_post>>, and IDF-weighted
coverage alone <<her_cov>>. The decision rule (>=0.65 transfers / 0.55-0.65 partial / <0.55 does not) was fixed in
the script before any external label was read; outcome **<<her_verdict>>**. Caveat kept visible:
<<hc_cats>> distinct catalogues means no catalogue-clustered interval is estimable here, so that CI is row-level
and understates dependence.

**Reading for the paper.** The construct survives an unseen tool universe; the level does not. Quote <<her_auc>>
as the cross-corpus expectation and <<src_oof>> / <<a1b_auc>> as same-family figures. Two implementation bugs
surfaced in this round and are recorded in the registry instead of being quietly fixed: an inverted
family-exclusion mask that silently returned zero families, and single-class CV folds inside the family holdout.
