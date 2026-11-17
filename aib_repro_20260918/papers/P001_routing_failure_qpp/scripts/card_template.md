

## E08 round (EXP-0020..EXP-0023): two additional sources, verified from the files

**Toucan `SFT` config** - same repository, revision and apache-2.0 licence as the published three. Columns
actually present: `uuid, subset_name, question, target_tools, tools, messages`; the catalogue column is `tools`
(not `available_tools`) and there is **no `metadata`**, so gold labels resolve by exact name / unique suffix only
and cannot be cross-checked against a per-row MCP server tool index. Sampled `subset_name` is uniformly
`single-turn-original`. Built at seed 42 with the frozen invocation
(`--rows-per-config 15000 --shards-per-config 10`); its uuid digest is auto-anchored in
`01_datasets/manifests/routing_sample_identity.json`. Measured <<sft_kept>>/<<sft_seen>> kept, catalogue mean
<<sft_cat_mean>>, dev fail@3 prevalence <<sft_prev>>. EXP-0021 then falsified the assumption that it is external:
it shares <<ov_names>> tool names and <<ov_fp>> catalogue fingerprints with the source dev pool.

**lambda/hermes-agent-reasoning-traces** (apache-2.0 per the dataset registry; 4 shards, 22,347 rows measured).
Columns: `id, conversations, tools, category, subcategory, task`. Verified from the files rather than the card:
`tools` is a JSON array of `{name, description, parameters}` present for only part of the rows; the reference
model's invocations appear inside `gpt` messages as a `tool_call` block holding
`{"name": ..., "arguments": {...}}`, and a `tool` role returns the observation. Catalogue sizes 6-17 tools but only
<<e23a_fps>> distinct catalogues over <<e23a_rows>> sampled rows, and category is dominated by
`Terminal & Coding`. After the n_candidates>3 rule: <<hc_rows>> rows, fail@3 prevalence <<hc_prev>>, extraction
rejections <<hc_rej>>. Gold here is the tool the reference model actually invoked - the same construct as
Toucan's `target_tools`, and likewise not a human-verified admissible set. Licence and provenance of this corpus
were taken from the dataset registry; its README claims were not used anywhere in the analysis.
